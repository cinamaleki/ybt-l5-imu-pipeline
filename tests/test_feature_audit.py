"""Analytical checks for descriptive variability and perturbation provenance."""
from pathlib import Path
import tempfile,unittest
import numpy as np
import pandas as pd
from ybt_feature_audit import (FEATURES,reference_scales,repeat_variation,perturb_annotations,
    paired_changes,summarize_changes,detector_annotations,check_inputs,rank_features)

class FeatureAuditTests(unittest.TestCase):
    def annotations(self):
        return pd.DataFrame([{'recording':'IMU01_PRE','imu_subject':'IMU01','interval_index':i+1,
            'start_s':a,'end_s':b,'duration_s':b-a,'include_primary':True} for i,(a,b) in enumerate([(1.,2.),(3.,4.)])])
    def records(self):return {'IMU01_PRE':{'t':np.arange(0,5,.005)}}

    def test_perturbation_recomputes_duration_and_preserves_source(self):
        a=self.annotations();b,excluded=perturb_annotations(a,self.records(),.1,-.1)
        np.testing.assert_allclose(b.duration_s,.8)
        np.testing.assert_allclose(a.duration_s,1.)
        self.assertEqual(len(excluded),0);self.assertTrue(b.include_primary.all())
        c,_=perturb_annotations(a,self.records(),.25,.25)
        np.testing.assert_allclose(c.start_s,a.start_s+.25);np.testing.assert_allclose(c.duration_s,1.)

    def test_invalid_perturbations_are_rejected_not_clipped(self):
        a=self.annotations();b,e=perturb_annotations(a,self.records(),-.6,.6)
        self.assertTrue(b.empty);self.assertEqual(len(e),2)
        a.loc[0,'start_s']=.1
        b,e=perturb_annotations(a,self.records(),-.2,0)
        self.assertEqual(len(e),1);self.assertEqual(b.iloc[0].start_s,2.8)

    def test_reference_scale_excludes_proposals_and_other_filters(self):
        rows=[]
        for value,primary,cutoff in [(1.,True,6),(3.,True,6),(1e9,False,6),(1e10,True,4)]:
            rows.append({**{f:value for f in FEATURES},'include_primary':primary,'cutoff_hz':cutoff})
        scales=reference_scales(pd.DataFrame(rows))
        np.testing.assert_allclose(scales.reference_iqr,1.)
        self.assertTrue((scales.n_reference==2).all())

    def test_repeat_dispersion_uses_real_three_trial_cells(self):
        rows=[]
        for trial,value in enumerate([-1.,0.,1.],1):
            rows.append({**{f:value for f in FEATURES},'recording':'IMU01_PRE','imu_subject':'IMU01','session':'PRE',
                'direction':'ANT','stance_leg':'R','trial':trial,'cutoff_hz':6,'include_primary':True})
        f=pd.DataFrame(rows);scales=pd.DataFrame({'feature':FEATURES,'reference_iqr':2.})
        cells,subjects,summary=repeat_variation(f,scales)
        self.assertEqual(len(cells),2*len(FEATURES))
        np.testing.assert_allclose(cells.median_pair_abs_diff,1.)
        np.testing.assert_allclose(cells.median_pair_diff_pct_iqr,50.)
        np.testing.assert_allclose(cells.trial_sd,1.)
        self.assertTrue((summary.subjects==1).all())
        # Repeated trial numbers must not silently masquerade as a complete cell.
        f.loc[2,'trial']=2
        # The caller validates such inputs; completeness itself requires {1,2,3}.
        valid=f.groupby(['imu_subject','session','stance_leg','direction']).trial.apply(lambda x:set(x)=={1,2,3})
        self.assertFalse(valid.any())

    def test_signed_features_use_fixed_scale_and_keyed_pairing(self):
        a=self.annotations()
        for f in FEATURES:a[f]=[-2.,2.]
        b=a.iloc[::-1].copy()
        for f in FEATURES:b[f]+=1.
        scales=pd.DataFrame({'feature':FEATURES,'reference_iqr':4.})
        changes=paired_changes(a,b,scales,'example')
        np.testing.assert_allclose(changes.abs_change_pct_iqr,25.)
        sub,summary=summarize_changes(changes)
        self.assertEqual(len(summary),len(FEATURES));np.testing.assert_allclose(summary.median_subject_change_pct_iqr,25.)

    def test_detector_pairs_by_time_overlap_instead_of_label_index(self):
        a=self.annotations()
        # Reverse labels: numerical ordering does not identify the corresponding movement.
        alt=pd.DataFrame({'recording':['IMU01_PRE']*2,'interval_index':[1,2],'start_s':[3.,1.],'end_s':[4.,2.]})
        annotations,matches=detector_annotations(a,alt,self.records())
        self.assertEqual(len(matches),2);np.testing.assert_allclose(matches.iou,1.)
        self.assertEqual(dict(zip(matches.interval_index,matches.detector_interval_index)),{1:2,2:1})
        for row in annotations.itertuples():self.assertEqual(row.start_s,1. if row.interval_index==1 else 3.)

    def test_unfiltered_orientation_is_not_rewarded_by_zero_sensitivity(self):
        summary=pd.DataFrame({'feature':FEATURES,'median_subject_pair_diff_pct_iqr':1.,
            'boundary_worst_median_pct_iqr':2.,'filter_worst_median_pct_iqr':0.,'filter_worst_p95_pct_iqr':0.})
        result=rank_features(summary).set_index('feature')
        self.assertTrue(np.isnan(result.loc['roll_p95','filter_worst_median_pct_iqr']))
        self.assertTrue(np.isnan(result.loc['roll_p95','exploratory_average_rank']))
        self.assertTrue(np.isnan(result.loc['duration_s','exploratory_average_rank']))
        self.assertTrue(np.isfinite(result.loc['gyro_rms','exploratory_average_rank']))

if __name__=='__main__':unittest.main()
