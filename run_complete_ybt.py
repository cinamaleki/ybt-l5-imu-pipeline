"""Single command for QC, recovery validation, features and grouped models.
python run_complete_ybt.py --input-dir upload --output-dir output/YBT_L5_Complete_v2
"""
from pathlib import Path
import argparse,json,shutil,importlib.metadata
import pandas as pd
import numpy as np
from ybt_imu_audit import audit
from ybt_complete_pipeline import load_recordings,recovery_analysis
from ybt_complete_analysis import label_intervals,extract_features,direction_models,reach_models,mixed_ybt_analysis


def apply_review(intervals,records,review):
    required={'recording','interval_index','start_s','end_s','user_reviewed'}
    if not required.issubset(review.columns):raise ValueError('Missing reviewed-boundary columns')
    if review.duplicated(['recording','interval_index']).any():raise ValueError('Duplicate review keys')
    original=intervals.set_index(['recording','interval_index'])
    unknown=set(map(tuple,review[['recording','interval_index']].to_numpy()))-set(original.index)
    if unknown:raise ValueError('Review contains unknown interval keys')
    result=intervals.copy()
    result[['start_s','end_s','duration_s']]=result[['start_s','end_s','duration_s']].astype(float)
    result['user_reviewed']=False;result['user_edited']=False
    for ix,row in result.iterrows():
        match=review[(review.recording==row.recording)&(review.interval_index==row.interval_index)]
        if len(match) and str(match.iloc[0].user_reviewed).lower() in ('true','1'):
            z=match.iloc[0];start=float(z.start_s);end=float(z.end_s)
            if not np.isfinite([start,end]).all() or not 0<=start<end<=records[row.recording]['t'][-1]:
                raise ValueError('Invalid reviewed interval')
            result.loc[ix,['start_s','end_s','duration_s']]=[start,end,end-start]
            result.loc[ix,'boundary_source']='user_reviewed_recovery' if not row.include_primary else 'user_reviewed_observed'
            result.loc[ix,'boundary_status']='USER_REVIEWED'
            result.loc[ix,'user_reviewed']=True
            result.loc[ix,'user_edited']=bool(abs(start-row.start_s)>1e-9 or abs(end-row.end_s)>1e-9)
    for rid,g in result.groupby('recording'):
        g=g.sort_values('interval_index')
        if (g.start_s.to_numpy()[1:]<g.end_s.to_numpy()[:-1]).any():raise ValueError(f'Overlapping reviewed intervals: {rid}')
    # Eligibility is inherited from the original acquisition, never from human acceptance.
    return result


def main(input_dir,out,review_csv=None):
    out.mkdir(parents=True,exist_ok=True)
    print('Auditing exported streams and recomputing conventional scores...',flush=True)
    raw_summary=audit(input_dir,out/'raw_audit')
    raw_summary['model_status']='QC layer only; see parent complete_summary.json and models folder'
    raw_summary['researcher_confirmations']['exact_leg_direction_permutation']=[['R','ANT'],['L','ANT'],['R','PM'],['L','PM'],['R','PL'],['L','PL']]
    raw_summary['researcher_confirmations']['repetition_layout']='Six-position cycle repeated three times; explicitly confirmed'
    raw_summary['researcher_confirmations']['last_entry_note']='L PL follows prior protocol; latest L PM treated as typing error'
    (out/'raw_audit/audit_summary.json').write_text(json.dumps(raw_summary,indent=2))
    records=load_recordings(input_dir)
    if len(records)!=14 or len({r['subject'] for r in records.values()})!=7:
        raise ValueError('This release expects the seven paired PRE/POST participants; update the study configuration for another cohort.')
    print('Validating marker-hidden recovery and ranking event-count exceptions...',flush=True)
    intervals=recovery_analysis(records,out)
    if review_csv:
        intervals=apply_review(intervals,records,pd.read_csv(review_csv))
        intervals.to_csv(out/'intervals_all_sources.csv',index=False)
    raw_scores=pd.read_csv(out/'raw_audit/ybt_all39_trial_values.csv')
    ann=label_intervals(intervals,raw_scores);ann.to_csv(out/'trial_annotations_all_sources.csv',index=False)
    print('Extracting fixed features at 4, 6 and 10 Hz...',flush=True)
    features=extract_features(records,ann,out)
    print('Evaluating participant-held-out direction models...',flush=True)
    directions=direction_models(features,out/'models')
    print('Evaluating normalized-reach estimates and corrected YBT analyses...',flush=True)
    reaches=reach_models(features,out/'models')
    anova=mixed_ybt_analysis(pd.read_csv(out/'raw_audit/ybt_all39_scores_recomputed.csv'),out)
    v=pd.read_csv(out/'marker_hidden_validation_by_recording.csv');injected=pd.read_csv(out/'synthetic_extra_pulse_validation.csv')
    segmentation={'reference_recordings':len(v),'reference_intervals':int(v.n_reference.sum()),
        'matched_iou_ge_0p5':int(v.matches_iou_0p5.sum()),
        'pooled_recall_iou_ge_0p5':float(v.matches_iou_0p5.sum()/v.n_reference.sum()),
        'mean_subject_recall_iou_ge_0p5':float(v.groupby('held_out_subject').recall_iou_0p5.mean().mean()),
        'mean_recording_iou':float(v.mean_matched_iou.mean()),
        'synthetic_extra_event_trials':len(injected),'synthetic_exact_removal_rate':float(injected.correct_extra_removed.mean()),
        'validation_note':'All recordings of test participant excluded when learning padding or boundary classifier; fixed detector developed on this pilot. No external validation.'}
    summary={'release':'2.0','participants':7,'recordings':14,'intervals_total_with_proposals':len(ann),
        'observed_intervals':int(ann.include_primary.sum()),'recovery_proposals':int((~ann.include_primary).sum()),
        'raw_audit':raw_summary,'recovery_validation':segmentation,
        'protocol':{'sequence':[['R','ANT'],['L','ANT'],['R','PM'],['L','PM'],['R','PL'],['L','PL']],
            'repetitions':'six-position cycle repeated three times; explicitly confirmed by researcher',
            'right_left':'stance leg','last_entry_note':'Latest message ends L PM; interpreted as typo for earlier L PL. All label-dependent results conditional on this interpretation.',
            'recording_success':'successful trials only','source':'Researcher confirmations on 4 November 2026'},
        'direction_results':directions.to_dict('records'),'reach_results':reaches.to_dict('records'),
        'analysis_scope':'Exploratory same-pilot model development. Recovery proposals are sensitivity data, not ground truth.'}
    (out/'complete_summary.json').write_text(json.dumps(summary,indent=2))
    versions={p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','scikit-learn','matplotlib','reportlab','openpyxl']}
    (out/'environment_versions.json').write_text(json.dumps(versions,indent=2))
    print(json.dumps({'segmentation':segmentation,'direction_primary':directions.query("dataset=='observed_only' and cutoff_hz==6").to_dict('records'),
        'reach':reaches.to_dict('records')},indent=2),flush=True)
    print('Building offline viewer and complete report...',flush=True)
    from build_complete_deliverables import build
    build(records,out,summary)
    return records,summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--review-csv',type=Path)
    a=p.parse_args();main(a.input_dir,a.output_dir,a.review_csv)
