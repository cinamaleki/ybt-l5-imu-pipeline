"""Artificial signals only: no fitting to or copying of participant recordings."""
from pathlib import Path
import json,importlib.metadata
import numpy as np
import pandas as pd
from scipy.signal import butter,sosfiltfilt
from scipy.ndimage import gaussian_filter1d
from ybt_complete_pipeline import FS,validate_recording,recovery_analysis
from ybt_complete_analysis import CYCLE,label_intervals,extract_features,direction_models,reach_models


def synthetic_inputs(seed=20261104):
    rng=np.random.default_rng(seed);records={};scores=[]
    t=np.arange(0,78,1/FS);centers=4+4*np.arange(18)
    for subject in range(1,8):
        for session in ['PRE','POST']:
            roll=np.zeros(len(t));pitch=np.zeros(len(t))
            scale=1+.025*subject+rng.uniform(-.02,.02)
            for j,c in enumerate(centers):
                leg,direction=CYCLE[j%6]
                a,b={'ANT':(4,20),'PM':(15,12),'PL':(-17,10)}[direction]
                shape=np.exp(-.5*((t-c)/.5)**2)
                roll+=a*scale*shape;pitch+=b*scale*shape
                length=82+subject
                target=({'ANT':67,'PM':88,'PL':83}[direction]+.3*subject+rng.normal(0,1))
                scores.append({'ID':subject,'Group':2 if subject==3 else 1 if subject==4 else (subject-1)%3+1,
                    'session':session,'stance_leg_AS_LABELED':leg,'direction':direction,'trial':j//6+1,
                    'reach_cm':target/100*length,'leg_length_cm':length})
            roll+=rng.normal(0,.025,len(t));pitch+=rng.normal(0,.025,len(t))
            gyro=np.c_[np.gradient(roll,1/FS),np.gradient(pitch,1/FS),.15*np.gradient(roll+pitch,1/FS)]
            acc=np.c_[20*np.sin(np.deg2rad(pitch)),20*np.sin(np.deg2rad(roll)),1000+2*np.sin(np.deg2rad(pitch))]
            # Scalar-first unit quaternion for Euler roll and pitch, yaw=0.
            cr=np.cos(np.deg2rad(roll)/2);sr=np.sin(np.deg2rad(roll)/2)
            cp=np.cos(np.deg2rad(pitch)/2);sp=np.sin(np.deg2rad(pitch)/2)
            quat=np.c_[cr*cp,sr*cp,cr*sp,-sr*sp]
            pulses=np.c_[centers-1,centers+1].ravel()
            if (subject,session)==(1,'PRE'):pulses=np.array([])
            if (subject,session) in [(2,'POST'),(7,'PRE')]:pulses=np.sort(np.r_[pulses,10.5])
            r={'t':t.copy(),'gyro':gyro,'acc_sensor':acc,'quat':quat,'roll':roll[:,None],'pitch':pitch[:,None],
                'pulses':pulses,'subject':f'IMU{subject:02d}','session':session,'is_synthetic':True}
            validate_recording(r)
            r['gyro6']=sosfiltfilt(butter(4,6,fs=FS,output='sos'),gyro,axis=0)
            r['speed']=np.linalg.norm(r['gyro6'],axis=1)
            r['envelope']=gaussian_filter1d(r['speed'],FS*.15)
            records[f'IMU{subject:02d}_{session}']=r
    return records,pd.DataFrame(scores)


def run_demo(output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise ValueError('Demo output directory must be empty, to avoid mixing synthetic and real results')
    print('SYNTHETIC DEMO: generating artificial motion; no participant data used.',flush=True)
    records,scores=synthetic_inputs()
    intervals=recovery_analysis(records,out)
    ann=label_intervals(intervals,scores);ann['is_synthetic']=True
    ann.to_csv(out/'trial_annotations_all_sources.csv',index=False)
    features=extract_features(records,ann,out)
    directions=direction_models(features,out/'models');reaches=reach_models(features,out/'models')
    fold=pd.read_csv(out/'models/fold_membership_audit.csv')
    if any(str(x.test_subject) in str(x.train_subjects).split(',') for x in fold.itertuples()):raise RuntimeError('Participant overlap')
    validation=pd.read_csv(out/'marker_hidden_validation_by_recording.csv')
    summary={'data_origin':'ENTIRELY_SYNTHETIC','seed':20261104,'participants':7,'recordings':len(records),
        'intervals':len(ann),'observed':int(ann.include_primary.sum()),'proposed':int((~ann.include_primary).sum()),
        'feature_rows':len(features),'finite_features':True,'participant_overlap':False,
        'marker_hidden_matched':int(validation.matches_iou_0p5.sum()),'marker_hidden_reference':int(validation.n_reference.sum()),
        'direction_results':directions.to_dict('records'),'reach_results':reaches.to_dict('records'),
        'versions':{p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','scikit-learn']},
        'interpretation':'Simulated execution test only. Scores are not evidence of validity on humans.'}
    (out/'synthetic_summary.json').write_text(json.dumps(summary,indent=2))
    primary=directions.query("dataset=='observed_only' and cutoff_hz==6")
    report='<html lang="en"><meta charset="utf-8"><title>Synthetic YBT-L5 demo</title><style>body{font:16px/1.6 system-ui;max-width:1000px;margin:40px auto;padding:20px;color:#17374c}aside{background:#fff1d6;padding:20px}table{border-collapse:collapse}th,td{padding:10px;border:1px solid #c9d9e1}</style><h1>YBT-L5: entirely synthetic demonstration</h1><aside>No participant recordings or scores were used. These artificial motions are deliberately simple. Demo accuracy is not a scientific result or clinical validation.</aside>'
    report+=f'<p>7 simulated participants; 14 recordings; {len(ann)} intervals; {len(features)} feature rows. Whole participants were held out.</p><h2>Artificial direction task, 6 Hz</h2>'
    report+=primary[['model','mean_subject_balanced_accuracy']].to_html(index=False,escape=True)
    report+='<h2>Example simulated segmentation</h2><img style="width:100%" alt="Simulated movement segmentation" src="figures/IMU01_PRE_segmentation.png"><p>CSV tables and full metadata are in this output directory. All files generated by this command are artificial.</p></html>'
    (out/'SYNTHETIC_REPORT.html').write_text(report)
    print(json.dumps({k:summary[k] for k in ['data_origin','recordings','intervals','observed','proposed','feature_rows','participant_overlap']},indent=2),flush=True)
    return summary
