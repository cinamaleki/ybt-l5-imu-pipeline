"""Complete YBT-L5 exploratory pipeline; recovery provenance is always explicit."""
from pathlib import Path
import argparse,csv,io,json,re,zipfile
import numpy as np
import pandas as pd
from scipy.signal import butter,sosfiltfilt,find_peaks,peak_widths
from scipy.optimize import linear_sum_assignment
from scipy.ndimage import gaussian_filter1d
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE=Path(__file__).resolve().parent
FS=200.0

def validate_recording(r):
    """Enforce the study's fixed-rate contract before filtering or indexing."""
    required={'gyro':3,'acc_sensor':3,'quat':4,'roll':1,'pitch':1}
    t=np.asarray(r.get('t',[]),dtype=float)
    if len(t)<100 or not np.isfinite(t).all() or abs(t[0])>1e-6 or not np.allclose(np.diff(t),1/FS,rtol=1e-3,atol=1e-6):
        raise ValueError('Expected a finite, zero-origin, regular 200 Hz time grid')
    for key,width in required.items():
        x=np.asarray(r.get(key,[]))
        if x.shape!=(len(t),width) or not np.isfinite(x).all():
            raise ValueError(f'Missing, misaligned or invalid {key} stream')
    if np.any(np.linalg.norm(r['quat'],axis=1)<1e-12):
        raise ValueError('Zero-norm quaternion')
    pulses=np.asarray(r.get('pulses',[]),dtype=float)
    if len(pulses) not in (0,36,37):
        raise ValueError('Expected 0, 36 or 37 Switch pulses; other counts need explicit review')
    if len(pulses) and (not np.isfinite(pulses).all() or np.any(np.diff(pulses)<=0) or pulses[0]<0 or pulses[-1]>t[-1]):
        raise ValueError('Invalid Switch event times')


def load_recordings(input_dir):
    records={}
    for p in sorted(Path(input_dir).glob('*.zip')):
        m=re.search(r'subject\s*(\d+)',p.name,re.I)
        if not m:continue
        sid=f'IMU{int(m.group(1)):02d}'
        with zipfile.ZipFile(p) as z:
            roots=sorted({n.rsplit('/',1)[0] for n in z.namelist() if n.endswith('Pelvis-Gyroscope.csv')})
            for root in roots:
                session='POST' if 'post' in root.lower() else 'PRE' if 'pre' in root.lower() else None
                if session is None:raise ValueError('Recording path must identify PRE or POST')
                channels={};time_grids={}
                for key,suffix in [('gyro','Pelvis-Gyroscope.csv'),('acc_sensor','Pelvis-Sensor_Acceleration.csv'),
                    ('acc_vendor','Pelvis-Acceleration.csv'),('quat','Pelvis-Orientation.csv'),('roll','Pelvis-Roll.csv'),
                    ('pitch','Pelvis-Pitch.csv'),('tilt','Pelvis-Tilt_Fwd.csv'),('switch','Switch_1.csv')]:
                    name=next((n for n in z.namelist() if n.startswith(root+'/') and n.endswith(suffix)),None)
                    if name:
                        blob=z.read(name)
                        meta=next(csv.DictReader(io.StringIO(blob.decode('utf-8-sig'))))
                        if not np.isclose(float(meta['frequency']),FS):raise ValueError(f'{key} must be exported at 200 Hz')
                        df=pd.read_csv(io.BytesIO(blob),skiprows=3)
                        if len(df)!=int(meta['count']):raise ValueError(f'{key} declared count mismatch')
                        time_grids[key]=df.time.to_numpy(float)
                        channels[key]=df.iloc[:,1:].to_numpy(float)
                        if key=='gyro':channels['t']=df.time.to_numpy(float)
                if 'switch' in channels:
                    high=channels['switch'][:,0]>0
                    channels['pulses']=time_grids['switch'][np.flatnonzero(high&~np.r_[False,high[:-1]])]
                else:channels['pulses']=np.array([])
                validate_recording(channels)
                if any(len(grid)!=len(channels['t']) or not np.allclose(grid,channels['t'],rtol=0,atol=1e-6) for grid in time_grids.values()):raise ValueError('Channel timestamps are not aligned')
                if f'{sid}_{session}' in records:raise ValueError('Duplicate participant/session recording')
                channels['subject']=sid;channels['session']=session
                channels['gyro6']=sosfiltfilt(butter(4,6,fs=FS,output='sos'),channels['gyro'],axis=0)
                channels['speed']=np.linalg.norm(channels['gyro6'],axis=1)
                channels['envelope']=gaussian_filter1d(channels['speed'],FS*.15)
                records[f'{sid}_{session}']=channels
    return records

def explore(records,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    for rid in ['IMU01_PRE','IMU02_POST','IMU07_PRE']:
        r=records[rid];t=r['t']
        fig,axs=plt.subplots(3,1,figsize=(16,8),sharex=True)
        axs[0].plot(t[::5],r['speed'][::5],lw=.7);axs[0].plot(t[::5],r['envelope'][::5],lw=1)
        axs[1].plot(t[::5],r['roll'][::5,0],label='Vendor Roll');axs[1].plot(t[::5],r['pitch'][::5,0],label='Vendor Pitch');axs[1].legend()
        axs[2].plot(t[::5],r['gyro6'][::5]);axs[2].set_xlabel('Recording time (s)')
        for ax in axs:
            for j,p in enumerate(r['pulses']):
                ax.axvline(p,c='orange',alpha=.6,lw=.7)
                if ax is axs[0]:ax.text(p,ax.get_ylim()[1]*.8,str(j+1),fontsize=6,rotation=90)
            ax.spines[['right','top']].set_visible(False)
        axs[0].set_title(rid+' | gyroscope magnitude; orange = observed pulses')
        fig.tight_layout();fig.savefig(out/f'{rid}_exploration.png',dpi=150);plt.close(fig)

def observed_intervals(r):
    return r['pulses'].reshape(-1,2) if len(r['pulses'])==36 else None

def candidates_from_signal(r):
    """Fixed detector; never receives marker times or reach-direction labels."""
    angles=np.c_[r['roll'][:,0],r['pitch'][:,0]]
    quiet=r['speed']<5
    baseline=np.median(angles[quiet],axis=0) if quiet.sum()>200 else np.median(angles,axis=0)
    amp=gaussian_filter1d(np.linalg.norm(angles-baseline,axis=1),FS*.1)
    peaks,prop=find_peaks(amp,prominence=3,distance=int(FS*1.25),width=int(FS*.3))
    widths=peak_widths(amp,peaks,rel_height=.9)
    cand=[]
    for j,k in enumerate(peaks):
        cand.append({'peak_s':float(r['t'][k]),'amplitude_deg':float(amp[k]),
            'prominence_deg':float(prop['prominences'][j]),'raw_start_s':float(widths[2][j]/FS),
            'raw_end_s':float(widths[3][j]/FS),'rank_score':float(prop['prominences'][j])})
    return cand,amp

def select_candidates(r):
    cand,amp=candidates_from_signal(r)
    # Protocol count is used explicitly, so obtaining 18 intervals is not validation.
    rank=sorted(range(len(cand)),key=lambda i:cand[i]['rank_score'],reverse=True)
    chosen=set(rank[:18])
    for i,c in enumerate(cand):c['selected']=i in chosen
    selected=sorted([c for c in cand if c['selected']],key=lambda c:c['peak_s'])
    return selected,cand,amp

def fit_boundary_padding(records,train_ids):
    """Median participant-weighted correction learned only from training subjects."""
    by_subject={}
    for rid in train_ids:
        r=records[rid];ref=observed_intervals(r)
        if ref is None:continue
        cand,amp=candidates_from_signal(r)
        for start,end in ref:
            valid=[c for c in cand if start<=c['peak_s']<=end]
            if not valid:continue
            c=max(valid,key=lambda c:c['prominence_deg'])
            by_subject.setdefault(r['subject'],[]).append([c['raw_start_s']-start,end-c['raw_end_s']])
    if not by_subject:return np.array([0.,0.])
    return np.clip(np.median([np.median(x,axis=0) for x in by_subject.values()],axis=0),-1,1)

def signal_intervals(r,padding):
    selected,all_candidates,amp=select_candidates(r)
    intervals=[]
    for c in selected:
        intervals.append([max(0,c['raw_start_s']-padding[0]),min(r['t'][-1],c['raw_end_s']+padding[1])])
    intervals=np.asarray(intervals)
    for j in range(len(intervals)-1):
        if intervals[j,1]>intervals[j+1,0]:
            mid=(selected[j]['peak_s']+selected[j+1]['peak_s'])/2
            intervals[j,1]=min(intervals[j,1],mid);intervals[j+1,0]=max(intervals[j+1,0],mid)
    return intervals,selected,all_candidates,amp

def interval_iou(a,b):
    inter=np.maximum(0,np.minimum(a[:,None,1],b[None,:,1])-np.maximum(a[:,None,0],b[None,:,0]))
    union=(a[:,1]-a[:,0])[:,None]+(b[:,1]-b[:,0])[None,:]-inter
    return inter/np.maximum(union,1e-12)

def compare_intervals(pred,ref):
    iou=interval_iou(pred,ref);ii,jj=linear_sum_assignment(-iou)
    rows=[]
    for i,j in zip(ii,jj):
        rows.append({'pred_index':i+1,'ref_index':j+1,'iou':float(iou[i,j]),
            'start_error_s':float(pred[i,0]-ref[j,0]),'end_error_s':float(pred[i,1]-ref[j,1])})
    return rows

def boundary_features(r,times):
    out=[];t=r['t'];v=r['speed'];roll=r['roll'][:,0];pitch=r['pitch'][:,0]
    for time in times:
        row=[]
        for lo,hi in [(-.8,-.25),(-.25,0),(0,.25),(.25,.8)]:
            mask=(t>=time+lo)&(t<time+hi)
            z=v[mask]
            row.extend([np.mean(z) if len(z) else 0,np.percentile(z,90) if len(z) else 0])
        i=max(0,min(len(t)-1,int(round(time*FS))))
        before=max(0,i-80);after=min(len(t)-1,i+80)
        row.extend([roll[i]-roll[before],roll[after]-roll[i],pitch[i]-pitch[before],pitch[after]-pitch[i]])
        out.append(row)
    return np.asarray(out)

def fit_boundary_classifier(records,train_ids):
    X=[];y=[]
    for rid in train_ids:
        r=records[rid]
        if len(r['pulses'])!=36:continue
        X.append(boundary_features(r,r['pulses']));y.extend(np.arange(36)%2)
    model=make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=2000))
    model.fit(np.vstack(X),np.array(y));return model

def rank_single_extra(r,times,model):
    logp=model.predict_log_proba(boundary_features(r,times))
    rows=[]
    for drop in range(len(times)):
        keep=np.delete(np.arange(len(times)),drop)
        labels=np.arange(len(keep))%2
        ll=float(logp[keep,labels].sum())
        rows.append({'drop_index_1based':drop+1,'drop_time_s':float(times[drop]),'log_likelihood':ll})
    rows=sorted(rows,key=lambda x:x['log_likelihood'],reverse=True)
    margin=rows[0]['log_likelihood']-rows[1]['log_likelihood']
    for i,row in enumerate(rows):row['rank']=i+1;row['best_vs_runnerup_loglik_margin']=margin
    return rows

def recovery_analysis(records,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);(out/'figures').mkdir(exist_ok=True)
    references=[rid for rid,r in records.items() if len(r['pulses'])==36]
    validation=[];matches=[];injections=[]
    rng=np.random.default_rng(20261104)
    for rid in references:
        r=records[rid];train=[x for x in references if records[x]['subject']!=r['subject']]
        padding=fit_boundary_padding(records,train)
        predicted,_,_,_=signal_intervals(r,padding);ref=observed_intervals(r)
        comp=compare_intervals(predicted,ref)
        for c in comp:matches.append({'recording':rid,'held_out_subject':r['subject'],**c})
        good=[c for c in comp if c['iou']>=.3]
        n50=sum(c['iou']>=.5 for c in comp)
        validation.append({'recording':rid,'held_out_subject':r['subject'],'n_predicted':len(predicted),'n_reference':18,
            'matches_iou_0p5':n50,'precision_iou_0p5':n50/len(predicted),'recall_iou_0p5':n50/18,
            'mean_matched_iou':np.mean([c['iou'] for c in comp]),
            'start_mae_s_iou_ge_0p3':np.mean([abs(c['start_error_s']) for c in good]) if good else np.nan,
            'end_mae_s_iou_ge_0p3':np.mean([abs(c['end_error_s']) for c in good]) if good else np.nan,
            'padding_start_s':padding[0],'padding_end_s':padding[1]})
        model=fit_boundary_classifier(records,train)
        # Inject one synthetic extra event; all data from this participant stay outside fitting.
        for repeat in range(20):
            for _ in range(1000):
                extra=rng.uniform(max(0,r['pulses'][0]-2),min(r['t'][-1],r['pulses'][-1]+2))
                if np.min(np.abs(r['pulses']-extra))>.15:break
            times=np.sort(np.r_[r['pulses'],extra]);ranking=rank_single_extra(r,times,model)
            chosen=ranking[0]['drop_time_s']
            injections.append({'recording':rid,'held_out_subject':r['subject'],'simulation':repeat+1,
                'injected_time_s':extra,'selected_time_s':chosen,'correct_extra_removed':abs(chosen-extra)<1e-9,
                'selection_error_s':abs(chosen-extra),'margin':ranking[0]['best_vs_runnerup_loglik_margin']})
    pd.DataFrame(validation).to_csv(out/'marker_hidden_validation_by_recording.csv',index=False)
    pd.DataFrame(matches).to_csv(out/'marker_hidden_validation_matches.csv',index=False)
    pd.DataFrame(injections).to_csv(out/'synthetic_extra_pulse_validation.csv',index=False)
    intervals=[];allc=[];rankings=[];decisions=[];detector_rows=[]
    for rid,r in records.items():
        train=[x for x in references if records[x]['subject']!=r['subject']]
        padding=fit_boundary_padding(records,train)
        recovered,selected,candidates,amp=signal_intervals(r,padding)
        for j,(start,end) in enumerate(recovered):
            detector_rows.append({'recording':rid,'interval_index':j+1,'start_s':start,'end_s':end,
                'padding_start_s':padding[0],'padding_end_s':padding[1],'source':'independent_signal_detector'})
        for c in candidates:allc.append({'recording':rid,**c})
        observed=observed_intervals(r);drop_time=None
        if observed is not None:
            chosen=observed;source='observed_switch';status='OBSERVED_BOUNDARIES'
        elif len(r['pulses'])==37:
            model=fit_boundary_classifier(records,train);rank=rank_single_extra(r,r['pulses'],model)
            for row in rank:rankings.append({'recording':rid,**row})
            best=rank[0];drop_time=best['drop_time_s']
            repaired=np.delete(r['pulses'],best['drop_index_1based']-1).reshape(18,2)
            overlap=np.mean([x['iou'] for x in compare_intervals(repaired,recovered)])
            # A ranking margin is not a calibrated probability. The proposal stays separate.
            chosen=repaired;source='single_extra_event_hypothesis';status='PROPOSAL_REQUIRES_REVIEW'
            decisions.append({'recording':rid,'observed_pulses':37,'proposed_removed_pulse':best['drop_index_1based'],
                'proposed_removed_time_s':drop_time,'ranking_margin':best['best_vs_runnerup_loglik_margin'],
                'agreement_with_signal_detector_mean_iou':overlap,
                'assumption':'Exactly one spurious event; other explanations remain possible',
                'status':status})
        else:
            chosen=recovered;source='signal_only';status='PROPOSAL_REQUIRES_REVIEW'
            scores=sorted([c['rank_score'] for c in candidates],reverse=True)
            margin=scores[17]-scores[18] if len(scores)>18 else np.nan
            decisions.append({'recording':rid,'observed_pulses':0,'proposed_removed_pulse':np.nan,
                'proposed_removed_time_s':np.nan,'ranking_margin':margin,
                'agreement_with_signal_detector_mean_iou':np.nan,
                'assumption':'Select 18 highest-prominence movement excursions using the known protocol count',
                'status':status})
        for j,(start,end) in enumerate(chosen):
            intervals.append({'recording':rid,'imu_subject':r['subject'],'session':r['session'],'ybt_id':int(r['subject'][3:]),
                'interval_index':j+1,'start_s':start,'end_s':end,'duration_s':end-start,'boundary_source':source,
                'boundary_status':status,'include_primary':source=='observed_switch','recovery_video_verified':False})
        # Save all 14 review plots, including the hidden-marker detector and original pulses.
        fig,axs=plt.subplots(2,1,figsize=(14,6),sharex=True)
        t=r['t'];axs[0].plot(t[::5],amp[::5],color='#155e75',lw=.9)
        axs[1].plot(t[::5],r['envelope'][::5],color='#475569',lw=.8)
        for j,(start,end) in enumerate(chosen):
            for ax in axs:ax.axvspan(start,end,color='#14b8a6' if observed is not None else '#f59e0b',alpha=.16)
            axs[0].text((start+end)/2,axs[0].get_ylim()[1]*.92,str(j+1),fontsize=7,ha='center')
        for p in r['pulses']:
            for ax in axs:ax.axvline(p,c='#c2410c',alpha=.4,lw=.5)
        if drop_time is not None:
            for ax in axs:ax.axvline(drop_time,c='red',lw=1.5,ls='--')
        axs[0].set(title=rid+' | '+source+' | boundaries highlighted; red dashed = proposed extra event',ylabel='Vendor angle excursion (deg)')
        axs[1].set(ylabel='Angular speed (deg/s)',xlabel='Recording time (s)')
        for ax in axs:ax.spines[['top','right']].set_visible(False)
        fig.tight_layout();fig.savefig(out/'figures'/f'{rid}_segmentation.png',dpi=150);plt.close(fig)
    pd.DataFrame(intervals).to_csv(out/'intervals_all_sources.csv',index=False)
    pd.DataFrame(allc).to_csv(out/'all_signal_candidates.csv',index=False)
    pd.DataFrame(rankings).to_csv(out/'all_extra_event_rankings.csv',index=False)
    pd.DataFrame(decisions).to_csv(out/'recovery_decisions.csv',index=False)
    pd.DataFrame(detector_rows).to_csv(out/'signal_detector_intervals_all.csv',index=False)
    return pd.DataFrame(intervals)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,default=BASE/'upload');p.add_argument('--output-dir',type=Path,default=BASE/'output/YBT_L5_Complete_v2')
    p.add_argument('--explore',action='store_true')
    args=p.parse_args();rr=load_recordings(args.input_dir)
    if args.explore:explore(rr,args.output_dir)
    else:
        intervals=recovery_analysis(rr,args.output_dir)
        print('Processed',len(rr),'recordings;',len(intervals),'intervals including explicit recovery proposals')
