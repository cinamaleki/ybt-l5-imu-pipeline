"""Scientific and provenance contracts, using artificial inputs only."""
from pathlib import Path
import copy,tempfile,unittest,zipfile
from unittest.mock import patch
import numpy as np
import pandas as pd
from scipy.stats import f_oneway
from ybt_synthetic import synthetic_inputs
from ybt_complete_pipeline import (validate_recording,load_recordings,observed_intervals,
    signal_intervals,interval_iou,compare_intervals,fit_boundary_padding)
from ybt_complete_analysis import (CYCLE,NORM,DIRECTIONAL,label_intervals,extract_features,
    mixed_ybt_analysis,reach_models)
from run_complete_ybt import apply_review
from ybt_imu_audit import audit_ybt


class Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.records,cls.scores=synthetic_inputs()

    def annotations(self,rid='IMU03_PRE'):
        r=self.records[rid];bounds=observed_intervals(r)
        return pd.DataFrame([dict(recording=rid,imu_subject=r['subject'],session=r['session'],ybt_id=int(r['subject'][3:]),
            interval_index=j+1,start_s=float(a),end_s=float(b),duration_s=float(b-a),boundary_source='observed_switch',include_primary=True)
            for j,(a,b) in enumerate(bounds)])

    def test_simulation_has_no_real_inputs_and_explicit_exceptions(self):
        self.assertEqual(len(self.records),14)
        self.assertTrue(all(r['is_synthetic'] for r in self.records.values()))
        self.assertEqual(sorted(len(r['pulses']) for r in self.records.values()),[0]+[36]*11+[37]*2)
        self.assertEqual(len(self.scores),252)

    def test_fixed_sampling_rejects_irregular_or_wrong_rate(self):
        for change in [lambda t:t*2, lambda t:np.r_[t[:50],t[50:]+.0001]]:
            r=copy.deepcopy(self.records['IMU03_PRE']);r['t']=change(r['t'])
            with self.assertRaises(ValueError):validate_recording(r)

    def test_rejects_zero_quaternion_missing_stream_and_bad_events(self):
        for key,value in [('quat',np.zeros_like(self.records['IMU03_PRE']['quat'])),('roll',np.zeros((3,1))),('pulses',np.arange(35))]:
            r=dict(self.records['IMU03_PRE']);r[key]=value
            with self.assertRaises(ValueError):validate_recording(r)

    def test_export_loader_enforces_metadata_not_just_array_length(self):
        with tempfile.TemporaryDirectory() as d:
            with zipfile.ZipFile(Path(d)/'subject 1.zip','w') as z:
                z.writestr('PRE/Pelvis-Gyroscope.csv','frequency,units,count\n100,deg/s,1\n\ntime,x,y,z\n0,0,0,0\n')
            with self.assertRaisesRegex(ValueError,'200 Hz'):load_recordings(Path(d))

    def test_iou_assignment_is_one_to_one_and_order_independent(self):
        a=np.array([[0.,2.],[3.,5.]])
        np.testing.assert_allclose(interval_iou(a,a),np.eye(2))
        matches=compare_intervals(a[::-1],a)
        self.assertEqual(len({x['ref_index'] for x in matches}),2)
        self.assertTrue(all(x['iou']==1 for x in matches))
        self.assertAlmostEqual(interval_iou(np.array([[0.,2.]]),np.array([[1.,3.]]))[0,0],1/3)

    def test_signal_detector_does_not_use_switch_events(self):
        r=self.records['IMU03_PRE'];prediction=signal_intervals(r,np.array([0.,0.]))[0]
        hidden=dict(r);hidden['pulses']=np.array([])
        np.testing.assert_allclose(prediction,signal_intervals(hidden,np.array([0.,0.]))[0])
        self.assertEqual(len(prediction),18)
        self.assertTrue(np.all(prediction[:,1]>prediction[:,0]))
        self.assertTrue(np.all(prediction[1:,0]>=prediction[:-1,1]))

    def test_boundary_padding_reads_training_recordings_only(self):
        training={k:v for k,v in self.records.items() if v['subject']!='IMU03'}
        # A guarded mapping raises if fitting accidentally reads a held-out session.
        class Guard(dict):
            def __getitem__(self,key):
                if key.startswith('IMU03'):raise AssertionError('Held-out participant accessed')
                return super().__getitem__(key)
        got=fit_boundary_padding(Guard(self.records),list(training))
        self.assertEqual(got.shape,(2,));self.assertTrue(np.isfinite(got).all())

    def test_cycle_normalization_and_corrected_groups(self):
        for rid,group in [('IMU03_PRE',2),('IMU04_POST',1)]:
            a=label_intervals(self.annotations(rid),self.scores)
            self.assertEqual(list(zip(a.stance_leg,a.direction)),CYCLE*3)
            self.assertEqual(a.trial.tolist(),[1]*6+[2]*6+[3]*6)
            self.assertTrue((a.group==group).all())
            self.assertTrue((a.stance_leg!=a.reaching_leg).all())
            source=self.scores
            first=a.iloc[0];ref=source[(source.ID==first.ybt_id)&(source.session==first.session)&(source.stance_leg_AS_LABELED=='R')&(source.direction=='ANT')&(source.trial==1)].iloc[0]
            self.assertAlmostEqual(first.normalized_reach_percent,100*ref.reach_cm/ref.leg_length_cm)

    def test_reviewed_recovery_stays_outside_primary(self):
        a=self.annotations().iloc[:2].copy();a.loc[0,'include_primary']=False;a.loc[0,'boundary_source']='signal_only'
        review=a[['recording','interval_index','start_s','end_s']].copy();review['user_reviewed']=True
        review.loc[0,'start_s']+=.05
        b=apply_review(a,self.records,review)
        self.assertFalse(b.iloc[0].include_primary)
        self.assertEqual(b.iloc[0].boundary_source,'user_reviewed_recovery')
        self.assertTrue(b.iloc[0].user_edited)
        self.assertTrue(b.iloc[1].include_primary)
        self.assertEqual(b.iloc[1].boundary_source,'user_reviewed_observed')
        self.assertEqual(a.iloc[0].boundary_source,'signal_only')

    def test_review_rejects_overlap_unknown_duplicate_and_nan(self):
        a=self.annotations().iloc[:2].copy();review=a[['recording','interval_index','start_s','end_s']].copy();review['user_reviewed']=True
        variants=[]
        z=review.copy();z.loc[0,'end_s']=z.loc[1,'start_s']+.1;variants.append(z)
        z=review.copy();z.loc[0,'interval_index']=99;variants.append(z)
        variants.append(pd.concat([review,review.iloc[:1]]))
        z=review.copy();z.loc[0,'start_s']=np.nan;variants.append(z)
        for z in variants:
            with self.assertRaises(ValueError):apply_review(a,self.records,z)

    def test_feature_units_and_complete_record_filtering(self):
        rid='IMU03_PRE';r=copy.deepcopy(self.records[rid]);t=r['t']
        r['acc_sensor']=np.c_[1000*np.sin(2*np.pi*t),np.zeros(len(t)),np.ones(len(t))*1000]
        ann=label_intervals(self.annotations(rid).iloc[:1],self.scores)
        ann.loc[:,['start_s','end_s','duration_s']]=[10.,20.,10.]
        with tempfile.TemporaryDirectory() as d:
            f=extract_features({rid:r},ann,Path(d))
        self.assertEqual(len(f),3)
        self.assertTrue(np.isfinite(f[NORM+DIRECTIONAL]).all().all())
        # 1000 mG sinusoid -> 9.80665/sqrt(2) m/s² RMS; zero-centered gravity contributes zero.
        row=f.query('cutoff_hz==6').iloc[0]
        self.assertAlmostEqual(row.acc_x_centered_rms,9.80665/np.sqrt(2),delta=.03)
        self.assertAlmostEqual(row.acc_z_centered_rms,0,delta=1e-9)
        self.assertAlmostEqual(row.sensor_acc_derivative_rms,2*np.pi*9.80665/np.sqrt(2),delta=.3)

    def test_anova_matches_independent_change_score_test(self):
        rng=np.random.default_rng(14);groups=np.repeat([1,2,3],13);scores=pd.DataFrame({'Group':groups})
        for measure in ['Ant','PM','PL','Composite']:
            pre=rng.normal(75,5,39);post=pre+rng.normal(groups,2,39)
            scores[f'YBT_{measure}_Pre']=pre;scores[f'YBT_{measure}_Post']=post
        with tempfile.TemporaryDirectory() as d:ans=mixed_ybt_analysis(scores,Path(d))
        for measure in ['Ant','PM','PL','Composite']:
            delta=scores[f'YBT_{measure}_Post']-scores[f'YBT_{measure}_Pre']
            expected=f_oneway(*(delta[groups==g] for g in [1,2,3]))
            row=ans[(ans.outcome==measure)&(ans.effect=='Group_x_Time')].iloc[0]
            self.assertAlmostEqual(row.F,expected.statistic,places=10)
            self.assertAlmostEqual(row.p_unadjusted,expected.pvalue,places=12)
        self.assertTrue((ans.p_holm_within_effect_family>=ans.p_unadjusted-1e-12).all())
        self.assertTrue(ans.p_holm_within_effect_family.between(0,1).all())

    def test_workbook_corrections_and_max_available_are_applied(self):
        raw=[]
        for sid,group in [(1,1),(3,1),(4,2)]:
            row={'ID':sid,'Group':group,'LegLength_cm':100.}
            for ses in ['Pre','Post']:
                for leg in ['L','R']:
                    for direction in ['ANT','PM','PL']:
                        for trial,value in enumerate([50.,60.,70.],1):row[f'{ses}_{leg}_{direction}_t{trial}']=value
            raw.append(row)
        raw[2]['Post_R_PL_t3']=None
        class Sheet:
            def __init__(self,values):self.values=values
        scorebook={'Raw_YBT':Sheet([list(raw[0])]+[list(x.values()) for x in raw])}
        descbook={'Descriptive_Means':Sheet([['Measure','Group','Pre','PreSD','Post','PostSD','Delta','DeltaSD'],['Ant','Eye',70.,1.,71.,1.,1.,1.]])}
        with tempfile.TemporaryDirectory() as d,patch('ybt_imu_audit.openpyxl.load_workbook',side_effect=[scorebook,descbook]):
            out=Path(d);audit_ybt(out,out)
            scores=pd.read_csv(out/'ybt_all39_scores_recomputed.csv').set_index('ID')
            trials=pd.read_csv(out/'ybt_all39_trial_values.csv')
            self.assertEqual(scores.loc[3,'Group'],2);self.assertEqual(scores.loc[4,'Group'],1)
            self.assertEqual(scores.loc[1,'YBT_Ant_Pre'],70.)
            self.assertEqual(scores.loc[4,'YBT_PL_Post'],65.)
            self.assertEqual(len(trials),108)
            self.assertEqual(len(pd.read_csv(out/'ybt_incomplete_trial_sets.csv')),1)

    def test_reach_baseline_excludes_test_participant_targets(self):
        tables=[]
        for sid in [3,4,5]:
            a=label_intervals(self.annotations(f'IMU{sid:02d}_PRE'),self.scores)
            a['cutoff_hz']=6
            for col in DIRECTIONAL:
                if col!='duration_s':a[col]=float(sid)
            tables.append(a)
        f=pd.concat(tables,ignore_index=True)
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);reach_models(f,out)
            p=pd.read_csv(out/'reach_predictions.csv')
            for sid in [3,4,5]:
                subject=f'IMU{sid:02d}';test=f[f.imu_subject==subject];train=f[f.imu_subject!=subject]
                pred=p[(p.dataset=='observed_only')&(p.model=='direction_leg_mean')&(p.held_out_subject==subject)]
                means=train.groupby(['direction','stance_leg']).normalized_reach_percent.mean()
                expected=[means.loc[(x.direction,x.stance_leg)] for x in test.itertuples()]
                np.testing.assert_allclose(pred.predicted_percent,expected)

if __name__=='__main__':unittest.main()
