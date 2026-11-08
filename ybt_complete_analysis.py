"""Fixed exploratory grouped models, processing sensitivity and corrected YBT scores."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.signal import butter,sosfiltfilt
from scipy.stats import f as fdist
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression,Ridge
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.metrics import balanced_accuracy_score,f1_score,confusion_matrix,mean_absolute_error,mean_squared_error

CYCLE=[('R','ANT'),('L','ANT'),('R','PM'),('L','PM'),('R','PL'),('L','PL')]
NORM=['gyro_rms','gyro_p95','acc_centered_rms','sensor_acc_derivative_rms']
DIRECTIONAL=['roll_p05','roll_p95','pitch_p05','pitch_p95','gyro_x_rms','gyro_y_rms','gyro_z_rms',
             'acc_x_centered_rms','acc_y_centered_rms','acc_z_centered_rms','quaternion_excursion_p95_deg','duration_s']


def label_intervals(intervals,raw_scores):
    d=intervals.copy()
    lookup=raw_scores.set_index(['ID','session','stance_leg_AS_LABELED','direction','trial'])
    groups=raw_scores.groupby('ID').Group.first().to_dict()
    for ix,row in d.iterrows():
        j=int(row.interval_index)-1;leg,direction=CYCLE[j%6];trial=j//6+1
        d.loc[ix,'stance_leg']=leg;d.loc[ix,'reaching_leg']='L' if leg=='R' else 'R'
        d.loc[ix,'direction']=direction;d.loc[ix,'trial']=trial
        d.loc[ix,'group']=groups[int(row.ybt_id)]
        val=lookup.loc[(int(row.ybt_id),row.session,leg,direction,trial)]
        d.loc[ix,'reach_cm']=val.reach_cm
        d.loc[ix,'normalized_reach_percent']=100*val.reach_cm/val.leg_length_cm
    d['label_source']='Researcher confirmed six-position cycle repeated three times'
    d['last_condition_assumption']='L PL follows earlier protocol; latest L PM interpreted as typing error'
    d['per_trial_video_verified']=False
    d['trial']=d.trial.astype(int);d['group']=d.group.astype(int)
    return d

def extract_features(records,annotations,out):
    rows=[]
    for cutoff in [4,6,10]:
        filtered={}
        for rid,r in records.items():
            sos=butter(4,cutoff,fs=200,output='sos')
            # Filter the complete recording to avoid artificial per-interval edge transients.
            filtered[rid]=(sosfiltfilt(sos,r['gyro'],axis=0),sosfiltfilt(sos,r['acc_sensor']*.00980665,axis=0))
        for _,row in annotations.iterrows():
            r=records[row.recording];mask=(r['t']>=row.start_s)&(r['t']<=row.end_s)
            gyro,acc=[v[mask] for v in filtered[row.recording]]
            centered=acc-acc.mean(axis=0);speed=np.linalg.norm(gyro,axis=1)
            deriv=np.gradient(acc,.005,axis=0)
            z={k:row[k] for k in ['recording','imu_subject','session','ybt_id','interval_index','start_s','end_s','duration_s',
                'boundary_source','include_primary','direction','stance_leg','trial','group','reach_cm','normalized_reach_percent']}
            z['cutoff_hz']=cutoff
            z.update({'gyro_rms':float(np.sqrt(np.mean(speed**2))),'gyro_p95':float(np.percentile(speed,95)),
                'acc_centered_rms':float(np.sqrt(np.mean(np.sum(centered**2,axis=1)))),
                'sensor_acc_derivative_rms':float(np.sqrt(np.mean(np.sum(deriv**2,axis=1))))})
            for k,axis in enumerate('xyz'):
                z[f'gyro_{axis}_rms']=float(np.sqrt(np.mean(gyro[:,k]**2)))
                z[f'acc_{axis}_centered_rms']=float(np.sqrt(np.mean(centered[:,k]**2)))
            for angle in ['roll','pitch']:
                x=r[angle][mask,0];x=x-np.median(x[:min(len(x),40)])
                z[f'{angle}_p05']=float(np.percentile(x,5));z[f'{angle}_p95']=float(np.percentile(x,95))
            q=r['quat'][mask];q=q/np.linalg.norm(q,axis=1,keepdims=True)
            excursion=np.rad2deg(2*np.arccos(np.clip(np.abs(q@q[0]),0,1)))
            z['quaternion_excursion_p95_deg']=float(np.percentile(excursion,95))
            rows.append(z)
    f=pd.DataFrame(rows)
    assert np.isfinite(f[NORM+DIRECTIONAL].to_numpy(float)).all()
    f.to_csv(Path(out)/'trial_features_all_cutoffs.csv',index=False)
    return f

def direction_models(features,out):
    out=Path(out);out.mkdir(exist_ok=True,parents=True)
    metrics=[];predictions=[];membership=[]
    for setname in ['observed_only','with_recovery_proposals']:
        subset=features[features.include_primary] if setname=='observed_only' else features
        for cutoff,d in subset.groupby('cutoff_hz'):
            d=d.reset_index(drop=True);groups=d.imu_subject.to_numpy();y=d.direction.to_numpy()
            for train,test in LeaveOneGroupOut().split(d,y,groups):
                assert set(groups[train]).isdisjoint(groups[test])
                sid=groups[test][0]
                membership.append({'dataset':setname,'cutoff_hz':cutoff,'test_subject':sid,
                    'train_subjects':','.join(sorted(set(groups[train]))),'n_train':len(train),'n_test':len(test),
                    'subject_overlap':False})
                specs=[('dummy',[],DummyClassifier(strategy='most_frequent')),
                    ('logistic_magnitudes',NORM,make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=3000,class_weight='balanced'))),
                    ('logistic_directional',DIRECTIONAL,make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=3000,class_weight='balanced'))),
                    ('forest_directional',DIRECTIONAL,RandomForestClassifier(n_estimators=200,max_depth=4,min_samples_leaf=3,class_weight='balanced',random_state=20261104,n_jobs=1))]
                for name,cols,model in specs:
                    X=d[cols].to_numpy() if cols else np.zeros((len(d),1))
                    model.fit(X[train],y[train]);yp=model.predict(X[test])
                    metrics.append({'dataset':setname,'cutoff_hz':cutoff,'model':name,'held_out_subject':sid,
                        'n_test':len(test),'balanced_accuracy':balanced_accuracy_score(y[test],yp),
                        'macro_f1':f1_score(y[test],yp,labels=['ANT','PM','PL'],average='macro',zero_division=0)})
                    for ix,answer in zip(test,yp):
                        predictions.append({'dataset':setname,'cutoff_hz':cutoff,'model':name,'held_out_subject':sid,
                            'recording':d.iloc[ix].recording,'interval_index':int(d.iloc[ix].interval_index),
                            'true_protocol_label':y[ix],'predicted':answer})
    m=pd.DataFrame(metrics);p=pd.DataFrame(predictions)
    m.to_csv(out/'direction_per_subject.csv',index=False);p.to_csv(out/'direction_predictions.csv',index=False)
    pd.DataFrame(membership).to_csv(out/'fold_membership_audit.csv',index=False)
    summary=m.groupby(['dataset','cutoff_hz','model']).agg(mean_subject_balanced_accuracy=('balanced_accuracy','mean'),
        min_subject_balanced_accuracy=('balanced_accuracy','min'),max_subject_balanced_accuracy=('balanced_accuracy','max'),
        mean_subject_macro_f1=('macro_f1','mean'),subjects=('held_out_subject','nunique')).reset_index()
    summary.to_csv(out/'direction_summary.csv',index=False)
    primary=p.query("dataset=='observed_only' and cutoff_hz==6 and model=='logistic_directional'")
    cm=confusion_matrix(primary.true_protocol_label,primary.predicted,labels=['ANT','PM','PL'])
    pd.DataFrame(cm,index=['true_ANT','true_PM','true_PL'],columns=['pred_ANT','pred_PM','pred_PL']).to_csv(out/'primary_direction_confusion.csv')
    return summary

def reach_models(features,out):
    """Contemporaneous normalized-reach estimation, not future balance or treatment prediction."""
    out=Path(out);rows=[];predictions=[]
    for dataset in ['observed_only','with_recovery_proposals']:
        d=features[features.cutoff_hz==6].copy()
        if dataset=='observed_only':d=d[d.include_primary]
        d=d.reset_index(drop=True);y=d.normalized_reach_percent.to_numpy();groups=d.imu_subject.to_numpy()
        for train,test in LeaveOneGroupOut().split(d,y,groups):
            assert set(groups[train]).isdisjoint(groups[test])
            training=d.iloc[train];testdata=d.iloc[test]
            means=training.groupby(['direction','stance_leg']).normalized_reach_percent.mean()
            baseline=np.array([means.loc[(r.direction,r.stance_leg)] for r in testdata.itertuples()])
            pre=ColumnTransformer([('signals',StandardScaler(),DIRECTIONAL),
                ('protocol',OneHotEncoder(handle_unknown='ignore'),['direction','stance_leg'])])
            model=make_pipeline(pre,Ridge(alpha=10,solver='lsqr'))
            model.fit(training,y[train]);estimated=model.predict(testdata)
            for name,yp in [('direction_leg_mean',baseline),('ridge_signals_plus_protocol',estimated)]:
                rows.append({'dataset':dataset,'model':name,'held_out_subject':groups[test][0],'n_test':len(test),
                    'mae_percentage_points':mean_absolute_error(y[test],yp),
                    'rmse_percentage_points':np.sqrt(mean_squared_error(y[test],yp))})
                for ix,answer in zip(test,yp):predictions.append({'dataset':dataset,'model':name,'held_out_subject':groups[ix],
                    'recording':d.iloc[ix].recording,'interval_index':int(d.iloc[ix].interval_index),
                    'actual_percent':y[ix],'predicted_percent':answer})
    r=pd.DataFrame(rows);r.to_csv(out/'reach_per_subject.csv',index=False)
    pd.DataFrame(predictions).to_csv(out/'reach_predictions.csv',index=False)
    summary=r.groupby(['dataset','model']).agg(mean_subject_mae_pp=('mae_percentage_points','mean'),
        mean_subject_rmse_pp=('rmse_percentage_points','mean')).reset_index()
    summary.to_csv(out/'reach_summary.csv',index=False);return summary

def mixed_ybt_analysis(scores,out):
    """Balanced 2-time x 3-group ANOVA via subject means and within-person differences."""
    rows=[];n=len(scores);g=3;df2=n-g
    for measure in ['Ant','PM','PL','Composite']:
        pre=scores[f'YBT_{measure}_Pre'].to_numpy();post=scores[f'YBT_{measure}_Post'].to_numpy()
        delta=post-pre;average=(post+pre)/2;groups=scores.Group.to_numpy()
        def between(x):
            grand=x.mean();ssb=sum(np.sum(groups==k)*(x[groups==k].mean()-grand)**2 for k in [1,2,3])
            sse=sum(np.sum((x[groups==k]-x[groups==k].mean())**2) for k in [1,2,3])
            return (ssb/(g-1))/(sse/df2),sse/df2
        fg,_=between(average);fi,mse=between(delta);ft=n*delta.mean()**2/mse
        for effect,F,df1 in [('Group',fg,2),('Time',ft,1),('Group_x_Time',fi,2)]:
            rows.append({'outcome':measure,'effect':effect,'F':F,'df1':df1,'df2':df2,
                'p_unadjusted':float(fdist.sf(F,df1,df2)),'partial_eta_squared':F*df1/(F*df1+df2)})
    d=pd.DataFrame(rows)
    for effect in d.effect.unique():
        mask=d.effect==effect
        p=d.loc[mask,'p_unadjusted'].to_numpy();order=np.argsort(p)
        adjusted=np.clip(np.maximum.accumulate((len(p)-np.arange(len(p)))*p[order]),0,1)
        restored=np.empty_like(adjusted);restored[order]=adjusted
        d.loc[mask,'p_holm_within_effect_family']=restored
    d.to_csv(Path(out)/'ybt_39_mixed_anova_corrected_groups.csv',index=False)
    return d
