"""YBT-L5 pilot audit. Group corrections and identity mapping confirmed by researcher.
Run: python ybt_imu_audit.py --input-dir upload --output-dir output/YBT_L5_Pilot_v1
Requires numpy, pandas, scipy, matplotlib, openpyxl (read-only workbook access).
"""
from pathlib import Path
import argparse, csv, io, json, re, hashlib, zipfile
import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import openpyxl


def read_signal(z, name):
    b = z.read(name)
    meta = next(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
    return meta, pd.read_csv(io.BytesIO(b), skiprows=3)


def feature_values(g, a, fs):
    # Descriptors of a proposed marker interval, not validated balance scores.
    sos = butter(4, 6, fs=fs, output='sos')
    gf = sosfiltfilt(sos, g, axis=0)
    af = sosfiltfilt(sos, a * 0.00980665, axis=0)  # mG -> m/s^2
    ac = af - af.mean(axis=0)
    jerk = np.gradient(af, 1/fs, axis=0)
    return {'gyro_rms_deg_s': float(np.sqrt(np.mean(np.sum(gf**2, axis=1)))),
            'gyro_p95_deg_s': float(np.percentile(np.linalg.norm(gf, axis=1),95)),
            'sensor_acc_centered_rms_m_s2': float(np.sqrt(np.mean(np.sum(ac**2, axis=1)))),
            'sensor_frame_acc_derivative_rms_m_s3': float(np.sqrt(np.mean(np.sum(jerk**2, axis=1))))}


def audit(input_dir, out):
    out.mkdir(parents=True, exist_ok=True)
    (out/'figures').mkdir(exist_ok=True)
    ybt = audit_ybt(input_dir,out)
    group_by_id=pd.read_csv(out/'ybt_all39_scores_recomputed.csv').set_index('ID').Group.to_dict()
    streams, records, events, candidates, features, identities, provenance = [], [], [], [], [], [], []
    plotted = []
    for p in sorted(input_dir.glob('*.zip')):
        match = re.search(r'subject\s*(\d+)', p.name, re.I)
        if not match: continue
        sid = f'IMU{int(match.group(1)):02d}'
        provenance.append({'imu_subject':sid,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
        identities.append({'imu_subject':sid,'ybt_id':int(match.group(1)),
            'group':group_by_id[int(match.group(1))],'mapping_verified':True,
            'source':'Researcher confirmation, 2026-11-04'})
        with zipfile.ZipFile(p) as z:
            roots = sorted({n.rsplit('/',1)[0] for n in z.namelist() if n.endswith('Pelvis-Gyroscope.csv')})
            for root in roots:
                session = 'POST' if 'post' in root.lower() else 'PRE' if 'pre' in root.lower() else 'UNKNOWN'
                rid = f'{sid}_{session}'
                names = [n for n in z.namelist() if n.startswith(root+'/') and n.endswith('.csv') and not n.endswith('info.csv')]
                loaded = {}
                for name in names:
                    meta, df = read_signal(z,name)
                    channel = name.rsplit('/',1)[-1].replace('.csv','')
                    loaded[channel] = (meta,df)
                    times = df.iloc[:,0].to_numpy(float)
                    vals = df.iloc[:,1:].to_numpy(float)
                    dt = np.diff(times)
                    fs = float(meta['frequency'])
                    streams.append({'recording':rid,'channel':channel,'units':meta['units'],
                        'declared_hz':fs,'declared_count':int(meta['count']),'rows':len(df),
                        'count_matches':int(meta['count'])==len(df),'start_s':times[0],'end_s':times[-1],
                        'median_dt_s':float(np.median(dt)), 'effective_hz':float(1/np.median(dt)),
                        'nonincreasing_steps':int(np.sum(dt<=0)),
                        'steps_gt_1p5_nominal':int(np.sum(dt>1.5/fs)),
                        'nonfinite_values':int(np.sum(~np.isfinite(vals))),
                        'max_abs_value':float(np.nanmax(np.abs(vals)))})
                def get(suffix):
                    found = [(m,d) for k,(m,d) in loaded.items() if k.endswith(suffix)]
                    return found[0] if found else (None,None)
                gm,g = get('Pelvis-Gyroscope'); am,a = get('Pelvis-Sensor_Acceleration')
                qm,q = get('Pelvis-Orientation'); sm,sw = get('Switch_1')
                fs=float(gm['frequency']); t=g.time.to_numpy(); gv=g.iloc[:,1:].to_numpy()
                av=a.iloc[:,1:].to_numpy(); pulses=[]
                if sw is not None:
                    high=sw.iloc[:,1].to_numpy()>0
                    starts=np.flatnonzero(high & ~np.r_[False,high[:-1]])
                    ends=np.flatnonzero(high & ~np.r_[high[1:],False])
                    for j,(start,end) in enumerate(zip(starts,ends),1):
                        pulses.append(float(sw.time.iloc[start]))
                        events.append({'recording':rid,'pulse_index':j,'time_s':pulses[-1],
                                       'pulse_width_s':float((end-start+1)/float(sm['frequency'])),
                                       'meaning':'START_END_SWITCH; pulse assignment pending count check'})
                marker_status='MISSING' if sw is None else '36_START_END_PULSES_RESEARCHER_CONFIRMED' if len(pulses)==36 else 'ODD_OR_UNEXPECTED_COUNT'
                if len(pulses)==36:
                    for j,event in enumerate(events[-36:]):event['meaning']='MOVEMENT_START' if j%2==0 else 'MOVEMENT_END'
                # Never silently discard an extra event or infer which leg/direction it means.
                if len(pulses)==36:
                    for j in range(18):
                        start,end=pulses[2*j:2*j+2]
                        row={'recording':rid,'imu_subject':sid,'session':session,'candidate_index':j+1,
                             'ybt_id':int(sid[3:]),'group':group_by_id[int(sid[3:])],
                             'start_s':start,'end_s':end,'duration_s':end-start,
                             'stance_leg':'','direction':'','trial_number':'','reach_cm':'',
                             'start_end_semantics_confirmed':True,'successful_trial_reported':True,
                             'annotation_verified':False,'candidate_rule':'consecutive start/end pulse pairs; exact leg/direction order pending'}
                        candidates.append(row)
                        mask=(t>=start)&(t<=end)
                        if mask.sum()>30 and np.isfinite(gv[mask]).all() and np.isfinite(av[mask]).all():
                            features.append({**{k:row[k] for k in ['recording','imu_subject','session','ybt_id','group','candidate_index','start_s','end_s','duration_s']},
                                **feature_values(gv[mask],av[mask],fs),
                                'status':'PROVISIONAL_NOT_FOR_INFERENCE'})
                qnorm=np.linalg.norm(q.iloc[:,1:].to_numpy(),axis=1)
                aligned=all(np.array_equal(d.time.to_numpy(),t) for m,d in loaded.values() if float(m['frequency'])==fs)
                r={'recording':rid,'imu_subject':sid,'session':session,'rows':len(g),'fs_hz':fs,
                   'duration_s':float(t[-1]-t[0]),'signal_files':len(names),'aligned_200hz_time_grids':aligned,
                   'switch_present':sw is not None,'rising_pulses':len(pulses),
                   'first_pulse_s':pulses[0] if pulses else np.nan,'last_pulse_s':pulses[-1] if pulses else np.nan,
                   'marker_status':marker_status,'record_info_present':root+'/info.csv' in z.namelist(),
                   'gyro_rms_whole_record_deg_s':float(np.sqrt(np.mean(np.sum(gv**2,axis=1)))),
                   'sensor_acc_magnitude_mean_g':float(np.mean(np.linalg.norm(av,axis=1))/1000),
                   'quaternion_max_norm_error':float(np.max(np.abs(qnorm-1)))}
                records.append(r)
                plotted.append((rid,t,np.linalg.norm(gv,axis=1),pulses))
    for name,data in [('recording_qc',records),('stream_qc',streams),('switch_events_review',events),
                      ('candidate_annotations_UNVERIFIED',candidates),('candidate_features_PROVISIONAL',features),
                      ('subject_mapping_CONFIRMED',identities),('input_checksums',provenance)]:
        pd.DataFrame(data).to_csv(out/f'{name}.csv',index=False)
    recorddf=pd.DataFrame(records).sort_values('recording')
    fig,axs=plt.subplots(7,2,figsize=(12,16),sharey=False)
    for rid,t,v,pulses in plotted:
        i=int(rid[3:5])-1; j=int(rid.endswith('POST'))
        ax=axs[i,j]; ax.plot(t[::10],v[::10],color='#167d9a',lw=.6)
        for x in pulses:ax.axvline(x,color='#e5a23c',alpha=.45,lw=.5)
        ax.set_title(f'{rid} | {len(pulses)} switch pulses',loc='left',fontsize=10)
        ax.set_ylabel('|angular velocity| (deg/s)',fontsize=8)
        ax.spines[['top','right']].set_visible(False)
        ax.set_xlabel('Recording time (s)',fontsize=8)
    fig.suptitle('YBT-L5 pilot: raw gyroscope magnitude and start/end switch events\nEvent-count exceptions remain unresolved; traces include setup/rest',fontsize=14)
    fig.tight_layout(rect=(0,0,1,.96));fig.savefig(out/'figures/all_recordings.png',dpi=150);plt.close(fig)
    # Detailed segment view illustrates why a pulse-count check alone does not establish ground truth.
    rid,t,v,pulses=next(x for x in plotted if x[0]=='IMU05_PRE')
    fig,ax=plt.subplots(figsize=(11,3.6));mask=(t>=8)&(t<=42)
    ax.plot(t[mask],v[mask],color='#167d9a',lw=1)
    for k in range(0,12,2):
        ax.axvspan(pulses[k],pulses[k+1],color='#e5a23c',alpha=.2)
    ax.set(xlabel='Recording time (s)',ylabel='Gyroscope magnitude (deg/s)',title='IMU05 PRE: first six pulse-pair candidates (labels unverified)')
    ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(out/'figures/candidate_intervals.png',dpi=180);plt.close(fig)
    summary={'participants':7,'recordings':len(records),'signal_streams':len(streams),
        'gyro_total_samples':int(recorddf.rows.sum()),'total_minutes':float(recorddf.duration_s.sum()/60),
        'recording_min_s':float(recorddf.duration_s.min()),'recording_max_s':float(recorddf.duration_s.max()),
        'recordings_36_pulses':int((recorddf.rising_pulses==36).sum()),
        'recordings_37_pulses':int((recorddf.rising_pulses==37).sum()),
        'recordings_no_switch':int((~recorddf.switch_present).sum()),
        'unverified_candidate_intervals':len(candidates),'ybt':ybt,
        'model_status':'NOT_TRAINED: exact leg/direction trial order and event-count exceptions unresolved',
        'researcher_confirmations':{'date':'2026-11-04','switch_semantics':'start and end of movement',
            'recorded_attempts':'successful trials only','imu_to_ybt_id':'identity mapping 1..7 confirmed',
            'group_corrections':{'3':2,'4':1},'order_reported':'standard YBT recommendation',
            'exact_leg_direction_permutation':None},
        'metadata_note':'Sampling-grid regularity verifies export continuity only, not absence of upstream packet loss/interpolation. Sensor model and anatomical axes not established.'}
    (out/'audit_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary


def audit_ybt(input_dir,out):
    p=input_dir/'YBT_Clean_Scoring_Workbook-39 subjects.xlsx'
    w=openpyxl.load_workbook(p,data_only=True)
    vals=list(w['Raw_YBT'].values); headers=vals[0]
    rows=[dict(zip(headers,row)) for row in vals[1:] if row[0] is not None]
    # Explicit researcher corrections; no measurements or other group assignments are changed.
    for r in rows:
        if r['ID'] in [3,4]:r['Group']={3:2,4:1}[r['ID']]
    trialrows=[]; summaryrows=[]; errors=[]; formula_checks=[]
    for r in rows:
        summ={'ID':r['ID'],'Group':r['Group'],'LegLength_cm':r['LegLength_cm']}
        for ses in ['Pre','Post']:
            norms={}
            for leg in ['L','R']:
                norm=[]
                for direction in ['ANT','PM','PL']:
                    reaches=[r[f'{ses}_{leg}_{direction}_t{i}'] for i in [1,2,3]]
                    for i,x in enumerate(reaches,1):
                        trialrows.append({'ID':r['ID'],'Group':r['Group'],'session':ses.upper(),'stance_leg_AS_LABELED':leg,
                            'direction':direction,'trial':i,'reach_cm':x,'leg_length_cm':r['LegLength_cm']})
                    valid_reaches=[x for x in reaches if isinstance(x,(int,float)) and x>0]
                    if len(valid_reaches)<3:
                        errors.append({'ID':r['ID'],'session':ses,'leg':leg,'direction':direction,'issue':'missing/nonpositive reach'})
                    # Match workbook MAX-of-available scoring; flag incomplete trial sets separately.
                    best=max(valid_reaches) if valid_reaches else np.nan
                    value=best/r['LegLength_cm']*100;norm.append(value)
                    for key,computed in [(f'{ses}_{leg}_Max_{direction}_cm',best),(f'{ses}_{leg}_{direction}_%',value)]:
                        cached=r.get(key);formula_checks.append({'ID':r['ID'],'column':key,'cached':cached,'recomputed':computed,'match':isinstance(cached,(int,float)) and abs(cached-computed)<1e-8})
                norms[leg]=norm
                key=f'{ses}_{leg}_Composite_%';computed=float(np.mean(norm)); cached=r.get(key)
                formula_checks.append({'ID':r['ID'],'column':key,'cached':cached,'recomputed':computed,'match':isinstance(cached,(int,float)) and abs(cached-computed)<1e-8})
            for k,direction in enumerate(['Ant','PM','PL']):summ[f'YBT_{direction}_{ses}']=float(np.mean([norms['L'][k],norms['R'][k]]))
            summ[f'YBT_Composite_{ses}']=float(np.mean(list(norms.values())))
        for m in ['Ant','PM','PL','Composite']:summ[f'YBT_{m}_Delta']=summ[f'YBT_{m}_Post']-summ[f'YBT_{m}_Pre']
        summaryrows.append(summ)
    d=pd.DataFrame(summaryrows);pd.DataFrame(trialrows).to_csv(out/'ybt_all39_trial_values.csv',index=False)
    d.to_csv(out/'ybt_all39_scores_recomputed.csv',index=False)
    pd.DataFrame(formula_checks).to_csv(out/'ybt_formula_cache_checks.csv',index=False)
    pd.DataFrame(errors).to_csv(out/'ybt_incomplete_trial_sets.csv',index=False)
    groupnames={1:'Breathing',2:'Eye',3:'Combined'}; stats=[]
    for measure in ['Ant','PM','PL','Composite']:
        for group,g in d.groupby('Group'):
            stat={'Measure':f'YBT_{measure}','Group':groupnames[group],'N':len(g)}
            for s in ['Pre','Post','Delta']:
                stat[f'{s}_Mean']=g[f'YBT_{measure}_{s}'].mean();stat[f'{s}_SD']=g[f'YBT_{measure}_{s}'].std(ddof=1)
            stats.append(stat)
    st=pd.DataFrame(stats);st.to_csv(out/'ybt_group_descriptives_recomputed.csv',index=False)
    # The separate descriptive file's own delta identity is checked independently of all grouping assumptions.
    other=openpyxl.load_workbook(input_dir/'YBT_Descriptive_with_ErrorBars.xlsx',data_only=True)
    checks=[]
    for r in list(other['Descriptive_Means'].values)[1:]:
        measure,group,pre,pre_sd,post,post_sd,delta,delta_sd=r
        expected=post-pre
        checks.append({'Measure':measure,'Group':group,'stated_delta_mean':delta,
            'post_minus_pre_from_same_row':expected,'identity_matches':abs(delta-expected)<1e-8})
    pd.DataFrame(checks).to_csv(out/'supplied_descriptive_file_errors.csv',index=False)
    return {'participants':len(rows),'groups':{str(k):int(v) for k,v in d.groupby('Group').size().items()},
        'trial_values':len(trialrows),'nonpositive_or_missing_trial_cells':len(errors),
        'raw_formula_cache_checks':len(formula_checks),'raw_formula_cache_mismatches':sum(not x['match'] for x in formula_checks),
        'descriptive_delta_identity_failures':sum(not x['identity_matches'] for x in checks),
        'imu_to_ybt_mapping':'CONFIRMED by researcher: IMU01..07 correspond to YBT IDs 1..7',
        'group_corrections':{'ID3':2,'ID4':1}}


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--input-dir',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True)
    args=ap.parse_args();print(json.dumps(audit(args.input_dir,args.output_dir),indent=2))
