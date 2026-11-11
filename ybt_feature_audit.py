"""Descriptive repeat variation and fixed processing perturbations; no model tuning.
All generated trial-level tables are private research data.
"""
from pathlib import Path
from itertools import combinations
import json, tempfile, hashlib, platform, importlib.metadata
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from ybt_complete_analysis import NORM, DIRECTIONAL, extract_features
from ybt_complete_pipeline import compare_intervals

FEATURES=list(dict.fromkeys(NORM+DIRECTIONAL))
FILTERED_FEATURES=set(NORM+['gyro_x_rms','gyro_y_rms','gyro_z_rms','acc_x_centered_rms','acc_y_centered_rms','acc_z_centered_rms'])
KEY=['recording','interval_index']
SCENARIOS={'shift_minus_100ms':(-.1,-.1),'shift_plus_100ms':(.1,.1),
    'shift_minus_250ms':(-.25,-.25),'shift_plus_250ms':(.25,.25),
    'trim_100ms':(.1,-.1),'expand_100ms':(-.1,.1),
    'trim_250ms':(.25,-.25),'expand_250ms':(-.25,.25)}
UNITS={f:('deg/s' if f.startswith('gyro') else 'm/s^3' if f=='sensor_acc_derivative_rms' else
    'm/s^2' if f.startswith('acc') else 's' if f=='duration_s' else 'deg') for f in FEATURES}


def check_inputs(annotations,features,records):
    if annotations.duplicated(KEY).any():raise ValueError('Duplicate annotation keys')
    if features.duplicated(KEY+['cutoff_hz']).any():raise ValueError('Duplicate feature keys')
    if not np.isfinite(features[FEATURES].to_numpy()).all():raise ValueError('Nonfinite features')
    if set(features.cutoff_hz)!={4,6,10}:raise ValueError('Expected 4, 6, 10 Hz features')
    if features.include_primary.dtype!=bool or annotations.include_primary.dtype!=bool:raise ValueError('Primary flags must be boolean')
    for row in annotations.itertuples():
        if row.recording not in records:raise ValueError('Missing recording')
        t=records[row.recording]['t']
        if not 0<=row.start_s<row.end_s<=t[-1]:raise ValueError('Invalid annotation bounds')
    for cutoff,g in features.groupby('cutoff_hz'):
        if set(map(tuple,g[KEY].to_numpy()))!=set(map(tuple,annotations[KEY].to_numpy())):raise ValueError('Feature / annotation mismatch')


def reference_scales(features):
    d=features[(features.cutoff_hz==6)&features.include_primary]
    rows=[]
    for f in FEATURES:
        x=d[f].to_numpy(float);q25,q75=np.percentile(x,[25,75]);scale=q75-q25
        rows.append({'feature':f,'unit':UNITS[f],'reference_q25':q25,'reference_q75':q75,
            'reference_iqr':scale if scale>1e-12 else np.nan,'n_reference':len(d)})
    return pd.DataFrame(rows)


def repeat_variation(features,scales):
    refs=scales.set_index('feature').reference_iqr.to_dict();cells=[];subjects=[]
    d=features[features.cutoff_hz==6]
    for dataset in ['observed_only','with_recovery_proposals']:
        x=d[d.include_primary] if dataset=='observed_only' else d
        for keys,g in x.groupby(['imu_subject','session','stance_leg','direction']):
            if len(g)!=3 or set(g.trial)!={1,2,3}:continue
            g=g.sort_values('trial')
            for f in FEATURES:
                values=g[f].to_numpy(float);pair=np.array([abs(a-b) for a,b in combinations(values,2)])
                cells.append(dict(zip(['imu_subject','session','stance_leg','direction'],keys),dataset=dataset,feature=f,
                    n_trials=3,trial_mean=values.mean(),trial_sd=values.std(ddof=1),trial_range=np.ptp(values),
                    median_pair_abs_diff=np.median(pair),median_pair_diff_pct_iqr=100*np.median(pair)/refs[f],
                    signed_trial3_minus_trial1=values[2]-values[0]))
    c=pd.DataFrame(cells)
    for keys,g in c.groupby(['dataset','feature','imu_subject']):
        subjects.append({'dataset':keys[0],'feature':keys[1],'imu_subject':keys[2],'n_cells':len(g),
            'median_pair_abs_diff':g.median_pair_abs_diff.median(),
            'median_pair_diff_pct_iqr':g.median_pair_diff_pct_iqr.median()})
    s=pd.DataFrame(subjects)
    summary=s.groupby(['dataset','feature']).agg(subjects=('imu_subject','nunique'),cells=('n_cells','sum'),
        median_subject_pair_abs_diff=('median_pair_abs_diff','median'),
        median_subject_pair_diff_pct_iqr=('median_pair_diff_pct_iqr','median'),
        min_subject_pair_diff_pct_iqr=('median_pair_diff_pct_iqr','min'),
        max_subject_pair_diff_pct_iqr=('median_pair_diff_pct_iqr','max')).reset_index()
    return c,s,summary


def perturb_annotations(annotations,records,start_delta,end_delta):
    a=annotations.copy();a['start_s']+=start_delta;a['end_s']+=end_delta
    valid=pd.Series(True,index=a.index)
    for ix,row in a.iterrows():
        t=records[row.recording]['t']
        valid.loc[ix]=bool(row.start_s>=0 and row.end_s<=t[-1] and row.end_s>row.start_s and ((t>=row.start_s)&(t<=row.end_s)).sum()>=40)
    # Reject rather than silently clip overlapping / out-of-record perturbations.
    for _,g in a.groupby('recording'):
        g=g.sort_values('interval_index');idx=g.index.to_numpy()
        overlaps=g.start_s.to_numpy()[1:]<g.end_s.to_numpy()[:-1]
        for j in np.flatnonzero(overlaps):valid.loc[[idx[j],idx[j+1]]]=False
    a['duration_s']=a.end_s-a.start_s
    return a.loc[valid].copy(),a.loc[~valid,KEY].copy()


def paired_changes(baseline,alternative,scales,scenario,extra=None):
    refs=scales.set_index('feature').reference_iqr.to_dict()
    merged=baseline.merge(alternative,on=KEY,suffixes=('_ref','_alt'),validate='one_to_one')
    rows=[]
    for f in FEATURES:
        diff=merged[f+'_alt']-merged[f+'_ref']
        for i,row in merged.iterrows():
            z={'recording':row.recording,'interval_index':row.interval_index,'imu_subject':row.imu_subject_ref,
               'include_primary':bool(row.include_primary_ref),'feature':f,'scenario':scenario,
               'reference_value':row[f+'_ref'],'alternative_value':row[f+'_alt'],
               'signed_change':diff.iloc[i],'abs_change':abs(diff.iloc[i]),'abs_change_pct_iqr':100*abs(diff.iloc[i])/refs[f]}
            if extra is not None:z['iou']=extra[(row.recording,row.interval_index)]
            rows.append(z)
    return pd.DataFrame(rows)


def summarize_changes(changes):
    subject=[];scenarios=[]
    for keys,g in changes.groupby(['scenario','feature','imu_subject']):
        subject.append({'scenario':keys[0],'feature':keys[1],'imu_subject':keys[2],'n_pairs':len(g),
            'median_abs_change':g.abs_change.median(),'median_abs_change_pct_iqr':g.abs_change_pct_iqr.median(),
            'p95_abs_change_pct_iqr':g.abs_change_pct_iqr.quantile(.95)})
    subject=pd.DataFrame(subject)
    for keys,g in changes.groupby(['scenario','feature']):
        s=subject[(subject.scenario==keys[0])&(subject.feature==keys[1])]
        rho=float(spearmanr(g.reference_value,g.alternative_value).statistic) if g.reference_value.nunique()>1 and g.alternative_value.nunique()>1 else np.nan
        scenarios.append({'scenario':keys[0],'feature':keys[1],'n_pairs':len(g),'subjects':len(s),
            'median_subject_abs_change':s.median_abs_change.median(),
            'median_subject_change_pct_iqr':s.median_abs_change_pct_iqr.median(),
            'pooled_p95_change_pct_iqr':g.abs_change_pct_iqr.quantile(.95),'pooled_spearman_rho':rho})
    return subject,pd.DataFrame(scenarios)


def detector_annotations(annotations,alternatives,records):
    chosen=[];matching=[]
    for rid,g in annotations[annotations.include_primary].groupby('recording'):
        ref=g.sort_values('interval_index').reset_index(drop=True)
        alt=alternatives[alternatives.recording==rid].sort_values('interval_index').reset_index(drop=True)
        if alt.empty:continue
        match=compare_intervals(alt[['start_s','end_s']].to_numpy(),ref[['start_s','end_s']].to_numpy())
        for m in match:
            orig=ref.iloc[m['ref_index']-1];p=alt.iloc[m['pred_index']-1]
            z=orig.to_dict();z.update(start_s=float(p.start_s),end_s=float(p.end_s),duration_s=float(p.end_s-p.start_s))
            t=records[rid]['t']
            if not 0<=z['start_s']<z['end_s']<=t[-1] or ((t>=z['start_s'])&(t<=z['end_s'])).sum()<40:continue
            chosen.append(z);matching.append({'recording':rid,'interval_index':int(orig.interval_index),
                'detector_interval_index':int(p.interval_index),'iou':m['iou'],
                'start_error_s':m['start_error_s'],'end_error_s':m['end_error_s']})
    return pd.DataFrame(chosen),pd.DataFrame(matching)


def rank_features(summary):
    """Only compare features to which all three processing questions apply."""
    summary=summary.copy()
    summary['filter_applicable']=summary.feature.isin(FILTERED_FEATURES)
    summary.loc[~summary.filter_applicable,['filter_worst_median_pct_iqr','filter_worst_p95_pct_iqr']]=np.nan
    metrics=['median_subject_pair_diff_pct_iqr','boundary_worst_median_pct_iqr','filter_worst_median_pct_iqr']
    rankable=summary.filter_applicable
    summary['exploratory_average_rank']=np.nan
    summary.loc[rankable,'exploratory_average_rank']=summary.loc[rankable,metrics].rank(method='average').mean(axis=1)
    return summary


def feature_audit(records,analysis_dir,out,synthetic=False):
    analysis_dir=Path(analysis_dir);out=Path(out)
    if out.resolve()==analysis_dir.resolve():raise ValueError('Keep robustness outputs separate from the original analysis')
    out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise ValueError('Output directory must be empty')
    ann=pd.read_csv(analysis_dir/'trial_annotations_all_sources.csv')
    original=pd.read_csv(analysis_dir/'trial_features_all_cutoffs.csv')
    check_inputs(ann,original,records)
    scales=reference_scales(original);scales.to_csv(out/'reference_scales.csv',index=False)
    cells,subject_repeats,repeats=repeat_variation(original,scales)
    for name,d in [('repeat_cells',cells),('repeat_by_subject',subject_repeats),('repeat_summary',repeats)]:d.to_csv(out/(name+'.csv'),index=False)
    with tempfile.TemporaryDirectory() as temp:
        # Reconcile the recovered source table against the installed feature implementation.
        recomputed=extract_features(records,ann,Path(temp))
        left=original.sort_values(KEY+['cutoff_hz']).reset_index(drop=True)
        right=recomputed.sort_values(KEY+['cutoff_hz']).reset_index(drop=True)
        np.testing.assert_allclose(left[FEATURES],right[FEATURES],rtol=1e-9,atol=1e-9)
        base=original[original.cutoff_hz==6].copy();primary=base[base.include_primary]
        comparisons=[];exclusions=[];feature_tables=[]
        for label,(start_delta,end_delta) in SCENARIOS.items():
            changed,excluded=perturb_annotations(ann,records,start_delta,end_delta)
            excluded['scenario']=label;exclusions.extend(excluded.to_dict('records'))
            f=extract_features(records,changed,Path(temp));f['scenario']=label;feature_tables.append(f)
            comparisons.append(paired_changes(primary,f[f.cutoff_hz==6],scales,label))
        for cutoff in [4,10]:comparisons.append(paired_changes(primary,original[original.cutoff_hz==cutoff],scales,f'filter_{cutoff}Hz'))
        pd.concat(feature_tables,ignore_index=True).to_csv(out/'perturbed_features_all_cutoffs.csv',index=False)
        alternatives=pd.read_csv(analysis_dir/'signal_detector_intervals_all.csv')
        detector_ann,matches=detector_annotations(ann,alternatives,records)
        matches.to_csv(out/'detector_matching_observed.csv',index=False)
        f=extract_features(records,detector_ann,Path(temp));f.to_csv(out/'detector_features_all_cutoffs.csv',index=False)
        extra=matches.set_index(KEY).iou.to_dict()
        detector=paired_changes(primary,f[f.cutoff_hz==6],scales,'signal_detector_all_matches',extra)
        comparisons.append(detector)
        good=detector[detector.iou>=.5].copy();good['scenario']='signal_detector_iou_ge_0p5';comparisons.append(good)
    changes=pd.concat(comparisons,ignore_index=True);changes.to_csv(out/'paired_feature_changes.csv',index=False)
    pd.DataFrame(exclusions,columns=KEY+['scenario']).to_csv(out/'excluded_perturbations.csv',index=False)
    sub,scenario=summarize_changes(changes)
    sub.to_csv(out/'processing_changes_by_subject.csv',index=False);scenario.to_csv(out/'processing_summary.csv',index=False)
    summary=repeats.query("dataset=='observed_only'").merge(scales,on='feature',validate='one_to_one')
    for family,labels in [('boundary',list(SCENARIOS)),('filter',['filter_4Hz','filter_10Hz'])]:
        d=scenario[scenario.scenario.isin(labels)]
        s=d.groupby('feature').agg(**{family+'_worst_median_pct_iqr':('median_subject_change_pct_iqr','max'),
            family+'_worst_p95_pct_iqr':('pooled_p95_change_pct_iqr','max')}).reset_index()
        summary=summary.merge(s,on='feature',validate='one_to_one')
    summary=rank_features(summary)
    summary['interpretation']='Exploratory comparison only; not clinical reliability or validity'
    summary.loc[~summary.filter_applicable,'interpretation']='Not refiltered in this audit; excluded from three-criterion ranking'
    summary.loc[summary.feature=='duration_s','interpretation']='Protocol timing descriptor; excluded from movement-feature ranking'
    summary=summary.sort_values('exploratory_average_rank',na_position='last');summary.to_csv(out/'feature_audit_summary.csv',index=False)
    (out/'input_checksums.json').write_text(json.dumps({n:hashlib.sha256((analysis_dir/n).read_bytes()).hexdigest() for n in
        ['trial_features_all_cutoffs.csv','trial_annotations_all_sources.csv','signal_detector_intervals_all.csv']},indent=2))
    metadata={'analysis_date':'2026-11-11','data_origin':'ENTIRELY_SYNTHETIC' if synthetic else 'PRIVATE_PILOT',
        'participants':int(ann.imu_subject.nunique()),'recordings':int(ann.recording.nunique()),
        'observed_trials':int(ann.include_primary.sum()),'proposals':int((~ann.include_primary).sum()),
        'complete_observed_repeat_cells':int(cells.query("dataset=='observed_only'")[['imu_subject','session','stance_leg','direction']].drop_duplicates().shape[0]),
        'features':len(FEATURES),'boundary_scenarios':SCENARIOS,'boundary_excluded_trial_scenarios':len(exclusions),
        'detector_matches':len(matches),'detector_iou_ge_0p5':int((matches.iou>=.5).sum()),
        'original_feature_reconciliation':'rtol=atol=1e-9 passed','python':platform.python_version(),
        'versions':{p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','scikit-learn']},
        'top_exploratory_features':summary.dropna(subset=['exploratory_average_rank']).feature.tolist()[:5],
        'limitations':['Same-pilot descriptive analysis; feature ranking is data-dependent.',
            'Three repeated executions include real movement variation; no independent sensor-error estimate.',
            'Only gyro and acceleration streams are refiltered; orientation/duration filter comparisons are not applicable.',
            'Reference IQR includes between-person and between-condition variation; not a clinical tolerance.',
            'Detector comparison uses internal marker-hidden development; high-IoU subset is selected.',
            'Recovered boundaries remain proposals. No clinical score, intervention effect or new model accuracy claimed.']}
    (out/'robustness_summary.json').write_text(json.dumps(metadata,indent=2))
    from ybt_feature_report import write_audit_report
    write_audit_report(out,metadata,summary,scenario,subject_repeats)
    print(json.dumps({k:metadata[k] for k in ['data_origin','observed_trials','proposals','complete_observed_repeat_cells','boundary_excluded_trial_scenarios','top_exploratory_features']},indent=2))
    return metadata
