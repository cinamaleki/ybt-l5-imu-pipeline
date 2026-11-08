"""Build a standalone local review viewer, scientific PDF and reproducibility notes."""
from pathlib import Path
import json,html,shutil
import numpy as np
import pandas as pd


def write_viewer(records,out,summary):
    out=Path(out);ann=pd.read_csv(out/'trial_annotations_all_sources.csv')
    alternatives=pd.read_csv(out/'signal_detector_intervals_all.csv')
    cand=pd.read_csv(out/'all_signal_candidates.csv');decisions=pd.read_csv(out/'recovery_decisions.csv')
    data={'records':{},'summary':summary}
    for rid,r in records.items():
        intervals=ann[ann.recording==rid].replace({np.nan:None}).to_dict('records')
        data['records'][rid]={'t':np.round(r['t'][::10],3).tolist(),
            'speed':np.round(r['envelope'][::10],2).tolist(),'roll':np.round(r['roll'][::10,0],2).tolist(),
            'pitch':np.round(r['pitch'][::10,0],2).tolist(),'pulses':r['pulses'].tolist(),
            'intervals':intervals,'alternatives':alternatives[alternatives.recording==rid].to_dict('records'),
            'candidates':cand[cand.recording==rid].to_dict('records'),
            'decision':decisions[decisions.recording==rid].replace({np.nan:None}).to_dict('records')}
    payload=json.dumps(data,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
    template=r'''<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>YBT-L5 — مرور داده و بازیابی</title><style>
:root{--navy:#17374c;--teal:#0f766e;--ink:#203648;--muted:#5a7080;--line:#d9e5eb;--amber:#b45309}*{box-sizing:border-box}body{margin:0;background:#f3f7fa;color:var(--ink);font:15px/1.8 Tahoma,Arial,sans-serif}header{background:var(--navy);color:white;padding:26px max(4vw,20px)}h1{font-size:25px;margin:0 0 4px}header p{margin:0;color:#cbe1ea}main{max-width:1380px;margin:22px auto;padding:0 18px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.card,.panel{background:white;border:1px solid var(--line);border-radius:12px;padding:18px}.card strong{display:block;font:28px Arial;color:var(--teal)}.card span{font-size:13px;color:var(--muted)}.panel{margin-top:16px}.toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:12px}button,select,input{font:inherit;border:1px solid #b7cbd5;border-radius:7px;padding:7px 11px;background:white;color:var(--ink)}button{cursor:pointer}button.primary{background:var(--teal);color:white;border-color:var(--teal)}button:hover{filter:brightness(.96)}select{min-width:185px}input[type=number]{width:100px;direction:ltr}.note{background:#fff8e9;border-right:4px solid #f59e0b;padding:11px 15px;margin:14px 0;border-radius:7px}.small{font-size:12px;color:var(--muted)}.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:12px;margin:10px 0}.dot{display:inline-block;width:12px;height:12px;border-radius:3px;margin-left:5px;vertical-align:middle}canvas{display:block;width:100%;height:340px;background:white;direction:ltr}.grid{display:grid;grid-template-columns:2fr 1fr;gap:16px}h2{font-size:17px;margin:0 0 12px}.tablewrap{max-height:390px;overflow:auto}table{border-collapse:collapse;width:100%;font-size:12px;white-space:nowrap}th,td{padding:7px 10px;text-align:right;border-bottom:1px solid #e5edf1}th{background:#f0f5f8;position:sticky;top:0}tbody tr{cursor:pointer}tr.selected{background:#dff3ee}tr:hover{background:#f3f8fa}code,.ltr{direction:ltr;unicode-bidi:embed;font-family:Arial}#status{font-size:13px;min-height:25px}.ok{color:#0f766e}.bad{color:#b91c1c}footer{padding:20px;color:var(--muted);font-size:12px}#reviewCount{font-weight:bold}.metrics{display:grid;grid-template-columns:1fr 1fr;gap:8px}.metrics div{background:#f4f7fa;padding:10px;border-radius:7px}.metrics b{display:block;font:23px Arial;color:var(--navy)}@media(max-width:850px){.cards{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}canvas{height:280px}.toolbar{gap:7px}}@media print{button,input,select{display:none}.tablewrap{max-height:none}header{background:white;color:black}.grid{display:block}}
</style><header><h1>مرور داده و بازیابی YBT–L5</h1><p>نسخهٔ ۲ · هفت شرکت‌کننده · مارکر واقعی و مرز بازسازی‌شده با منشأ مشخص</p></header><main>
<div class="cards"><div class="card"><strong>14</strong><span>ضبط پیش و پس</span></div><div class="card"><strong>198</strong><span>بازه با Switch واقعی</span></div><div class="card"><strong>54</strong><span>بازهٔ پیشنهادی برای مرور</span></div><div class="card"><strong>160 / 198</strong><span>تطابق بازه‌ها در آزمون پنهان‌کردن مارکر؛ IoU ≥ 0.5</span></div></div>
<div class="note">چرخهٔ تأییدشده سه بار تکرار می‌شود: <span class="ltr">R–ANT → L–ANT → R–PM → L–PM → R–PL → L–PL</span>. راست/چپ، پای اتکاست. آخرین «چپ PM» در پیام اخیر، مطابق ترتیب قبلی «چپ PL» در نظر گرفته شده؛ نتایج وابسته به برچسب‌ها مشروط به این تفسیرند.</div>
<section class="panel"><div class="toolbar"><label>ضبط <select id="record"></select></label><label>نمایش <select id="signal"><option value="speed">اندازهٔ سرعت زاویه‌ای</option><option value="angles">Roll و Pitch خروجی Noraxon</option></select></label><button id="full">کل ضبط</button><button id="zoom">بزرگ‌نمایی تلاش انتخاب‌شده</button><label><input type="checkbox" id="alternative"> پیشنهاد مستقلِ آشکارساز</label></div>
<div class="legend"><span><i class="dot" style="background:#8cd5c5"></i>مرز مبتنی بر Switch</span><span><i class="dot" style="background:#f6c773"></i>بازهٔ بازسازی‌شده</span><span><i class="dot" style="background:#c2410c"></i>پالس ثبت‌شده</span><span><i class="dot" style="background:#94a3b8"></i>گزینهٔ آشکارساز</span></div><canvas id="plot"></canvas><p id="recordNote" class="small"></p></section>
<div class="grid"><section class="panel"><h2>تلاش‌ها — انتخاب برای دیدن و اصلاح مرز</h2><div class="tablewrap"><table><thead><tr><th>تلاش</th><th>پای اتکا</th><th>جهت</th><th>تکرار</th><th>شروع (s)</th><th>پایان (s)</th><th>منشأ</th><th>مرور</th></tr></thead><tbody id="trials"></tbody></table></div></section>
<section class="panel"><h2 id="editTitle">اصلاح بازه</h2><div class="toolbar"><label>شروع <input id="start" type="number" step="0.005"></label><label>پایان <input id="end" type="number" step="0.005"></label></div><p class="small">بازسازی خودکار، تأیید مستقل حرکت نیست. شکل موج و پالس‌ها را مرور کن؛ در دو ضبطِ ۳۷ پالسی، فرض حذف یک پالس ممکن است کافی نباشد.</p><div class="toolbar"><button id="apply" class="primary">اعمال مرز</button><button id="review">مرور شد</button><button id="reset">بازگردانی</button></div><p id="status"></p><button id="useAlternative">جایگزینی با پیشنهاد آشکارساز</button><p class="small">مرور انسانی، منشأ «بازسازی‌شده» را به «مارکر واقعی» تبدیل نمی‌کند.</p><hr style="border:0;border-top:1px solid #d9e5eb"><h2>خروجی مرور</h2><p class="small"><span id="reviewCount">0</span> بازه مرور شده. تغییرها در همین مرورگر نگه‌داری می‌شوند؛ برای حفظ آن‌ها فایل خروجی را دانلود کن.</p><button id="exportCsv" class="primary">دریافت CSV اصلاح‌ها</button> <button id="exportJson">دریافت JSON</button></section></div>
<section class="panel"><h2>شواهد و محدودیت‌ها</h2><div class="metrics"><div><b>80.8%</b><span class="small">تطابق ۱۶۰ بازه از ۱۹۸ بازهٔ مرجع در آستانهٔ IoU=0.5؛ داده‌های فرد آزمون از آموزش خارج بودند.</span></div><div><b>55.0%</b><span class="small">حذف درست پالس مصنوعیِ اضافه در ۲۲۰ آزمون؛ برای تأیید خودکارِ پالس اضافه کافی نیست.</span></div></div><p class="small">انتخاب ۱۸ قله از تعداد مورد انتظار پروتکل استفاده می‌کند؛ رسیدن به عدد ۱۸، صحت بازیابی را ثابت نمی‌کند. پیشنهادهای ۵۴ بازه جدا از ۱۹۸ بازهٔ واقعی در تحلیل حساسیت بررسی شده‌اند. ارزیابی‌ها اکتشافی و روی همین پایلوت هفت‌نفره‌اند؛ برآورد تشخیصی یا خطر آسیب نیستند.</p></section>
</main><footer>نمایشگر مستقل و بدون وابستگی شبکه · برای جزئیات مدل‌ها، اعتبارسنجی و بازاجرای تحلیل، گزارش PDF و README را ببین.</footer><script id="embedded" type="application/json">__DATA__</script><script>
'use strict';const D=JSON.parse(document.getElementById('embedded').textContent),S={rid:Object.keys(D.records).sort()[0],selected:0,x0:0,x1:0},E=id=>document.getElementById(id),original=structuredClone(D.records);let cache={};try{cache=JSON.parse(localStorage.getItem('ybt_l5_v2_review')||'{}')}catch{}for(const [key,v] of Object.entries(cache)){const [rid,index]=key.split('|');const q=D.records[rid]?.intervals.find(t=>t.interval_index==index);if(q)Object.assign(q,v)}
function rec(){return D.records[S.rid]}function current(){return rec().intervals[S.selected]}function save(){let x={};for(const [rid,r] of Object.entries(D.records))for(const z of r.intervals)if(z.user_reviewed||z.user_edited)x[rid+'|'+z.interval_index]={start_s:z.start_s,end_s:z.end_s,user_reviewed:!!z.user_reviewed,user_edited:!!z.user_edited};try{localStorage.setItem('ybt_l5_v2_review',JSON.stringify(x))}catch{}E('reviewCount').textContent=Object.values(D.records).flatMap(r=>r.intervals).filter(z=>z.user_reviewed).length}
function selectRecord(){S.rid=E('record').value;S.selected=0;S.x0=0;S.x1=rec().t.at(-1);render()}
function status(text,bad=false){E('status').textContent=text;E('status').className=bad?'bad':'ok'}
function render(){const r=rec(),z=current();E('editTitle').textContent='تلاش '+z.interval_index;E('start').value=z.start_s.toFixed(3);E('end').value=z.end_s.toFixed(3);E('trials').replaceChildren();for(let j=0;j<r.intervals.length;j++){const q=r.intervals[j],tr=document.createElement('tr');if(j===S.selected)tr.className='selected';const source=q.boundary_source==='observed_switch'?'Switch واقعی':'پیشنهادی';for(const text of [q.interval_index,q.stance_leg,q.direction,q.trial,q.start_s.toFixed(3),q.end_s.toFixed(3),source,q.user_reviewed?'✓':'—']){const td=document.createElement('td');td.textContent=text;tr.appendChild(td)}tr.onclick=()=>{S.selected=j;status('');render()};E('trials').appendChild(tr)}const v=r.decision[0];E('recordNote').textContent=v?(v.observed_pulses===0?'Switch موجود نیست؛ ۱۸ بازه از سیگنال پیشنهاد شده‌اند.':'۳۷ پالس ثبت‌شده؛ پالس پیشنهادی برای حذف: '+v.proposed_removed_pulse+' در '+v.proposed_removed_time_s.toFixed(3)+' ثانیه. این حذف قطعی نشده است.'):'۳۶ پالس ثبت‌شده، متناظر با ۱۸ جفت شروع و پایان.';save();draw()}
function draw(){const c=E('plot'),r=rec(),ratio=window.devicePixelRatio||1,w=c.clientWidth,h=c.clientHeight;c.width=w*ratio;c.height=h*ratio;const ctx=c.getContext('2d');ctx.scale(ratio,ratio);ctx.clearRect(0,0,w,h);const L=62,R=18,T=18,B=38,W=w-L-R,H=h-T-B,x=t=>L+(t-S.x0)/(S.x1-S.x0)*W,angles=E('signal').value==='angles';let vv=[];for(let i=0;i<r.t.length;i++)if(r.t[i]>=S.x0&&r.t[i]<=S.x1){vv.push(angles?r.roll[i]:r.speed[i]);if(angles)vv.push(r.pitch[i])}let ymin=angles?Math.min(...vv)-3:0,ymax=Math.max(...vv)+5;const y=v=>T+H-(v-ymin)/(ymax-ymin)*H;ctx.font='11px Arial';for(let k=0;k<=4;k++){let v=ymin+(ymax-ymin)*k/4,yy=y(v);ctx.strokeStyle='#e5edf1';ctx.beginPath();ctx.moveTo(L,yy);ctx.lineTo(w-R,yy);ctx.stroke();ctx.fillStyle='#64748b';ctx.fillText(v.toFixed(0),8,yy+3)}for(let k=0;k<=6;k++){let t=S.x0+(S.x1-S.x0)*k/6;ctx.fillText(t.toFixed(1),x(t)-12,h-12)}ctx.save();ctx.beginPath();ctx.rect(L,T,W,H);ctx.clip();for(let j=0;j<r.intervals.length;j++){const z=r.intervals[j];ctx.fillStyle=z.boundary_source==='observed_switch'?'#14b8a62b':'#f59e0b2f';ctx.fillRect(x(z.start_s),T,x(z.end_s)-x(z.start_s),H);if(j===S.selected){ctx.strokeStyle='#0f766e';ctx.lineWidth=2;ctx.strokeRect(x(z.start_s),T,x(z.end_s)-x(z.start_s),H)}ctx.fillStyle='#475569';ctx.fillText(String(z.interval_index),x((z.start_s+z.end_s)/2)-3,T+11)}if(E('alternative').checked){ctx.strokeStyle='#64748b';ctx.setLineDash([3,3]);for(const z of r.alternatives)ctx.strokeRect(x(z.start_s),T+18,x(z.end_s)-x(z.start_s),H-18);ctx.setLineDash([])}ctx.strokeStyle='#c2410c88';ctx.lineWidth=.7;for(const t of r.pulses){ctx.beginPath();ctx.moveTo(x(t),T);ctx.lineTo(x(t),T+H);ctx.stroke()}let drop=r.decision[0]?.proposed_removed_time_s;if(drop!=null){ctx.strokeStyle='#dc2626';ctx.lineWidth=1.8;ctx.setLineDash([5,3]);ctx.beginPath();ctx.moveTo(x(drop),T);ctx.lineTo(x(drop),T+H);ctx.stroke();ctx.setLineDash([])}function line(values,color){ctx.strokeStyle=color;ctx.lineWidth=1;ctx.beginPath();let began=false;for(let i=0;i<r.t.length;i++){if(r.t[i]<S.x0-.1||r.t[i]>S.x1+.1)continue;if(!began){ctx.moveTo(x(r.t[i]),y(values[i]));began=true}else ctx.lineTo(x(r.t[i]),y(values[i]))}ctx.stroke()}if(angles){line(r.roll,'#2563eb');line(r.pitch,'#e8790b')}else line(r.speed,'#155e75');ctx.restore();ctx.fillStyle='#475569';ctx.fillText(angles?'Roll (blue), Pitch (orange) / deg':'Angular speed / deg/s',L,T+H+25)}
function valid(a,b){if(!(a>=0&&b>a&&b<=rec().t.at(-1)))return 'مرزها باید در محدودهٔ ضبط و پایان بعد از شروع باشد.';let all=rec().intervals,j=S.selected;if(j>0&&a<all[j-1].end_s)return 'با تلاش قبلی هم‌پوشانی دارد.';if(j+1<all.length&&b>all[j+1].start_s)return 'با تلاش بعدی هم‌پوشانی دارد.';return ''}
E('apply').onclick=()=>{const a=Number(E('start').value),b=Number(E('end').value),error=valid(a,b);if(error)return status(error,true);Object.assign(current(),{start_s:a,end_s:b,user_edited:true,user_reviewed:false});status('مرز اصلاح شد؛ برای تأیید مرور، «مرور شد» را بزن.');render()};E('review').onclick=()=>{current().user_reviewed=true;status('مرور این بازه ثبت شد.');render()};E('reset').onclick=()=>{Object.assign(current(),structuredClone(original[S.rid].intervals[S.selected]),{user_edited:false,user_reviewed:false});status('مرز اولیه بازگردانده شد.');render()};E('useAlternative').onclick=()=>{let z=rec().alternatives[S.selected];E('start').value=z.start_s.toFixed(3);E('end').value=z.end_s.toFixed(3);status('پیشنهاد آشکارساز در ورودی‌ها قرار گرفت؛ برای پذیرش، اعمال مرز را بزن.')};
function exportRows(){return Object.entries(D.records).flatMap(([rid,r])=>r.intervals.map(z=>({recording:rid,interval_index:z.interval_index,start_s:z.start_s,end_s:z.end_s,duration_s:z.end_s-z.start_s,boundary_source:z.boundary_source,user_reviewed:!!z.user_reviewed,user_edited:!!z.user_edited,stance_leg:z.stance_leg,direction:z.direction,trial:z.trial,last_condition_assumption:z.last_condition_assumption}))) }function download(name,text,type){const a=document.createElement('a'),url=URL.createObjectURL(new Blob([text],{type}));a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}E('exportCsv').onclick=()=>{let rows=exportRows(),cols=Object.keys(rows[0]);let esc=v=>'"'+String(v??'').replaceAll('"','""')+'"';download('YBT_reviewed_boundaries.csv','\ufeff'+cols.map(esc).join(',')+'\r\n'+rows.map(r=>cols.map(k=>esc(r[k])).join(',')).join('\r\n'),'text/csv;charset=utf-8')};E('exportJson').onclick=()=>download('YBT_reviewed_boundaries.json',JSON.stringify({protocol:D.summary.protocol,intervals:exportRows()},null,2),'application/json');E('record').onchange=selectRecord;E('signal').onchange=draw;E('alternative').onchange=draw;E('full').onclick=()=>{S.x0=0;S.x1=rec().t.at(-1);draw()};E('zoom').onclick=()=>{const z=current();S.x0=Math.max(0,z.start_s-5);S.x1=Math.min(rec().t.at(-1),z.end_s+5);draw()};E('plot').onclick=e=>{const rect=E('plot').getBoundingClientRect(),t=S.x0+(e.clientX-rect.left-62)/(rect.width-80)*(S.x1-S.x0);let j=rec().intervals.findIndex(z=>t>=z.start_s&&t<=z.end_s);if(j>=0){S.selected=j;render()}};window.addEventListener('resize',draw);for(const rid of Object.keys(D.records).sort()){const o=document.createElement('option');o.value=rid;o.textContent=rid;E('record').appendChild(o)}E('record').value=S.rid;selectRecord();
</script></html>'''
    (out/'Review_Viewer.html').write_text(template.replace('__DATA__',payload),encoding='utf-8')


def build(records,out,summary):
    write_viewer(records,out,summary)
    write_report(out,summary)
    write_docs(out,summary)


def write_report(out,summary):
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import matplotlib
    out=Path(out)
    font_dir=Path(matplotlib.get_data_path())/'fonts'/'ttf'
    pdfmetrics.registerFont(TTFont('DV',str(font_dir/'DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont('DV-Bold',str(font_dir/'DejaVuSans-Bold.ttf')))
    pdfmetrics.registerFontFamily('DV',normal='DV',bold='DV-Bold',italic='DV',boldItalic='DV-Bold')
    styles=getSampleStyleSheet()
    styles['BodyText'].fontName='DV';styles['BodyText'].fontSize=9;styles['BodyText'].leading=13;styles['BodyText'].spaceAfter=8
    styles['Heading2'].fontName='DV-Bold';styles['Heading2'].fontSize=12;styles['Heading2'].leading=16;styles['Heading2'].textColor=colors.HexColor('#17374c');styles['Heading2'].spaceBefore=12
    styles.add(ParagraphStyle(name='Cover',fontName='DV-Bold',fontSize=25,leading=30,textColor=colors.HexColor('#17374c'),spaceAfter=14))
    styles.add(ParagraphStyle(name='TitleSmall',fontName='DV-Bold',fontSize=21,leading=25,textColor=colors.HexColor('#17374c'),spaceAfter=15))
    styles.add(ParagraphStyle(name='SmallDV',fontName='DV',fontSize=7.5,leading=10.5,spaceAfter=6))
    story=[]
    def p(text,style='BodyText'):story.append(Paragraph(text,styles[style]))
    def h(text):p(text,'Heading2')
    def table(rows,widths):
        data=[[Paragraph(html.escape(str(c)),styles['SmallDV']) for c in row] for row in rows]
        t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e4eef3')),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#f6f9fb'),colors.white]),
            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),3),('LEFTPADDING',(0,0),(-1,-1),6)]))
        story.append(t);story.append(Spacer(1,6))
    direction=pd.read_csv(out/'models/direction_summary.csv');reach=pd.read_csv(out/'models/reach_summary.csv')
    val=pd.read_csv(out/'marker_hidden_validation_by_recording.csv');dec=pd.read_csv(out/'recovery_decisions.csv')
    observed=direction.query("dataset=='observed_only' and cutoff_hz==6").set_index('model')
    primary=observed.loc['logistic_directional'];rf=observed.loc['forest_directional']
    rr=reach.query("dataset=='observed_only'").set_index('model')
    seg=summary['recovery_validation']
    p('YBT-L5<br/>Complete Exploratory Pipeline','Cover')
    p('<b>Sina Maleki | Release 2.0 | 4 November 2026</b>')
    p('A reproducible workflow for single-lumbar-IMU Y-Balance recordings: exported-data QC, event recovery proposals, participant-held-out model evaluation and a local review interface.')
    table([['Analysis layer','Completed output'],['Data and scores','14 recordings; 7 participants; 321 exported signal streams; conventional YBT scores for 39 participants'],
        ['Observed movement boundaries','198 intervals from 11 recordings with 36 start/end pulses'],['Recovery layer','54 explicitly provisional intervals from 3 event-count exceptions; all candidates and rankings retained'],
        ['Validation','Marker-hidden evaluation of 198 reference intervals; 220 synthetic extra-event tests'],['Models','Fixed logistic and random-forest direction models; Ridge reach estimation; 4/6/10-Hz sensitivity'],
        ['Deliverables','Code, tables, plots for all recordings, editable offline viewer, model predictions and this report']], [155,350])
    h('Main findings')
    p(f'<b>Segmentation:</b> {seg["matched_iou_ge_0p5"]}/198 marker-hidden reference intervals matched at intersection-over-union (IoU) >= 0.5 ({seg["pooled_recall_iou_ge_0p5"]:.1%}). Participant-averaged recall was {seg["mean_subject_recall_iou_ge_0p5"]:.1%}. Selecting 18 peaks uses the protocol count and is not itself evidence of recovery accuracy.')
    p(f'<b>Direction:</b> mean held-out-participant balanced accuracy was {primary.mean_subject_balanced_accuracy:.1%} for the prespecified directional logistic model, {rf.mean_subject_balanced_accuracy:.1%} for the fixed forest, and 33.3% for the dummy. These small-pilot results do not establish a reliable direction classifier.')
    p(f'<b>Normalized reach:</b> participant-average MAE was {rr.loc["ridge_signals_plus_protocol","mean_subject_mae_pp"]:.2f} percentage points for Ridge versus {rr.loc["direction_leg_mean","mean_subject_mae_pp"]:.2f} for a training-only direction/leg mean baseline. This is contemporaneous estimation, not future performance or clinical-risk prediction.')
    h('Protocol and provenance')
    p('The researcher confirmed a six-position cycle repeated three times: R-ANT, L-ANT, R-PM, L-PM, R-PL, L-PL; right/left denotes the stance leg. The latest message ends in L-PM, interpreted as a typing error for the previously confirmed L-PL. All label-dependent results are conditional on that interpretation. Trial labels are protocol-derived; no per-trial video verification is available.')
    story.append(PageBreak())
    p('01 / Recovery and validation','TitleSmall')
    table([['Recording','Observed events','Current proposal / status'],['IMU01 PRE','No Switch channel','18 highest-prominence excursions; signal-only proposal'],
        ['IMU02 POST','37 pulses',f'One-extra-event hypothesis: remove pulse 37 at 147.185 s; not verified'],
        ['IMU07 PRE','37 pulses','Top rankings: remove pulse 26 at 126.205 s or pulse 25 at 117.020 s; nearly tied']], [90,85,330])
    p('The odd-count explanation is a hypothesis: 37 events need not mean exactly one false event. An extra attempt combined with a missing event, for example, could yield the same count. Original pulses are retained, and an independent signal-detector alternative is supplied. All 54 proposed intervals remain outside the primary observed-boundary dataset.')
    story.append(Image(str(out/'figures/IMU01_PRE_segmentation.png'),width=505,height=180))
    p('IMU01 PRE: amber regions are proposed movements. No recorded marker was manufactured. Unselected movement candidates remain available in the CSV for review.','SmallDV')
    rows=[['Hidden-marker test','IoU >= 0.5','Mean IoU']]
    for row in val.itertuples():rows.append([row.recording,f'{row.matches_iou_0p5}/18',f'{row.mean_matched_iou:.3f}'])
    table(rows,[180,150,175])
    p(f'The boundary classifier removed the exact injected event in {seg["synthetic_exact_removal_rate"]:.1%} of {seg["synthetic_extra_event_trials"]} synthetic tests. This performance does not justify automatic acceptance of a real deletion. Ranking margins are scores, not calibrated correctness probabilities. Boundary timing MAEs are reported only for matches with IoU >= 0.3 in the detailed validation CSV.','SmallDV')
    story.append(PageBreak())
    p('02 / Direction decoding','TitleSmall')
    p('Four fixed specifications were evaluated. No search over hyperparameters or label ordering was performed. All data from the test participant, including both sessions, were held out. Scaling and encoder parameters were learned on training subjects only. This avoids subject overlap, but the complete study remains exploratory development on the same small pilot [2,3].')
    names={'dummy':'Most-frequent dummy','logistic_magnitudes':'Logistic: 4 magnitude features','logistic_directional':'Logistic: 12 directional descriptors','forest_directional':'Forest: 12 directional descriptors'}
    rows=[['Fixed model','4 Hz, observed','6 Hz, observed','10 Hz, observed','6 Hz + proposals']]
    for name in names:
        values=[]
        for dataset,cutoff in [('observed_only',4),('observed_only',6),('observed_only',10),('with_recovery_proposals',6)]:
            z=direction[(direction.dataset==dataset)&(direction.cutoff_hz==cutoff)&(direction.model==name)].iloc[0]
            values.append(f'{z.mean_subject_balanced_accuracy:.1%}')
        rows.append([names[name],*values])
    table(rows,[190,79,79,79,78])
    h('Feature definitions')
    p('Magnitude features are gyroscope RMS and p95, centered sensor-acceleration RMS, and sensor-frame acceleration-derivative RMS. Directional descriptors add robust Roll/Pitch excursions, axis-specific gyroscope RMS and centered acceleration RMS, relative quaternion excursion and interval duration. Vendor axes are not relabeled as anatomical AP/ML without a verified calibration convention. Manufacturer documentation distinguishes sensor and Earth reference frames [4].')
    p('Raw gyroscope and sensor acceleration are filtered over each complete recording with a fourth-order, zero-phase Butterworth filter, then segmented. This removes the prior implementation\'s per-interval filtering transients. Therefore the updated four-feature baseline is not numerically identical to release 1.2. Acceleration derivatives include gravity/orientation effects and are not asserted to be validated smoothness scores.')
    metrics=pd.read_csv(out/'models/direction_per_subject.csv').query("dataset=='observed_only' and cutoff_hz==6 and model=='logistic_directional'")
    table([['Held-out participant','Test intervals','Balanced accuracy','Macro-F1']]+[[r.held_out_subject,r.n_test,f'{r.balanced_accuracy:.1%}',f'{r.macro_f1:.3f}'] for r in metrics.itertuples()], [155,100,130,120])
    h('Interpretation')
    p('Direction decoding is a technical demonstration under this fixed protocol. It is not a measure of balance quality. Fixed order can confound direction with time, fatigue and drift; participant holdout does not remove this confounding. There are seven independent people, regardless of how many intervals or windows are extracted. Fold dispersion is not presented as a reliable population confidence interval [2,3].')
    story.append(PageBreak())
    p('03 / Reach estimation and YBT scores','TitleSmall')
    p('The normalized target is trial reach distance / recorded leg length x 100. Ridge (alpha=10) uses the 12 descriptors plus encoded direction and stance leg. The comparator is the direction/leg mean computed from training participants only. Group, identity, session and reach score are not predictors. Results below use only observed boundaries.')
    reg=pd.read_csv(out/'models/reach_per_subject.csv').query("dataset=='observed_only'")
    pivot=reg.pivot(index='held_out_subject',columns='model',values='mae_percentage_points')
    table([['Held-out participant','Mean baseline MAE (pp)','Ridge MAE (pp)']]+[[i,f'{row.direction_leg_mean:.2f}',f'{row.ridge_signals_plus_protocol:.2f}'] for i,row in pivot.iterrows()]+[['Participant mean',f'{rr.loc["direction_leg_mean","mean_subject_mae_pp"]:.2f}',f'{rr.loc["ridge_signals_plus_protocol","mean_subject_mae_pp"]:.2f}']], [165,170,170])
    sensitivity=reach.query("dataset=='with_recovery_proposals'").set_index('model')
    p(f'With recovery proposals included, the corresponding MAEs were {sensitivity.loc["direction_leg_mean","mean_subject_mae_pp"]:.2f} and {sensitivity.loc["ridge_signals_plus_protocol","mean_subject_mae_pp"]:.2f} percentage points. That is sensitivity analysis using uncertain boundaries and ordinal trial linkage, not stronger validation. Improvement in a participant-average error does not establish a clinically useful estimator or consistent benefit for every individual.')
    h('Conventional YBT: corrected groups, all 39 participants')
    p('ID3 is group 2 (Eye); ID4 is group 1 (Breathing). Group sizes remain 13. Individual measurements and scoring rules are preserved, including MAX of available trials for ID39 POST R PL (trial 3 missing). A balanced 2-time x 3-group mixed ANOVA was recomputed using subject means and within-person differences; df2=36. Holm correction is applied across the four outcomes separately within each effect family.')
    anova=pd.read_csv(out/'ybt_39_mixed_anova_corrected_groups.csv')
    table([['Outcome','Effect','F','Raw p','Holm p']]+[[r.outcome,r.effect,f'{r.F:.3f}',f'{r.p_unadjusted:.4f}',f'{r.p_holm_within_effect_family:.4f}'] for r in anova.itertuples()], [105,130,80,95,95])
    p('No tested Group, Time or Group x Time effect reached p < 0.05 even before adjustment. This does not demonstrate equivalence or absence of an effect. These model-based analyses assume suitable residual distributions and variance structure; the pilot IMU subset is not used to infer intervention efficacy.','SmallDV')
    story.append(PageBreak())
    p('04 / Reproducibility and use','TitleSmall')
    table([['File / folder','Purpose'],['Review_Viewer.html','Offline signal review; select a recording/trial, edit boundaries, mark reviewed and export CSV/JSON'],
        ['trial_annotations_all_sources.csv','252 intervals with original/proposed boundary source, protocol labels and assumptions'],
        ['marker_hidden_validation_*.csv','Held-out-subject segmentation agreement and boundary errors'],
        ['all_extra_event_rankings.csv','All 37 deletion hypotheses for each odd-event recording'],
        ['models/','Per-person results, predictions, cutoff sensitivity and fold membership audit'],
        ['raw_audit/','321-stream QC, recomputed 39-person scores and explicit source formula checks'],
        ['run_complete_ybt.py','One-command data analysis; optional --review-csv applies reviewed boundary edits']], [190,315])
    h('How to use the review interface')
    p('Open the HTML locally; no network is required. Observed pulses remain visible. Reconstructed intervals have a different color and status. Review edits can be exported and passed back to the pipeline with --review-csv. Visual review does not turn reconstructed boundaries into observed markers; they remain sensitivity data. Keep the CSV/JSON export to preserve edits outside browser storage.')
    h('What this portfolio can support')
    p('A defensible description is: "Developed a reproducible Python workflow for lumbar-IMU Y-Balance recordings, including signal QC, provenance-aware event-recovery proposals, marker-hidden participant-held-out validation, and exploratory direction/reach models." The current evidence supports a technical pilot and methods demonstration. A clinical predictor, definitive biomarker, treatment conclusion, or publication acceptance is not established.')
    h('Material limits')
    p('Seven participants; one lumbar sensor; fixed execution order; only successful attempts; no independent per-trial video labels; uncertain boundaries in three recordings; and a conditional interpretation of the last L-PL entry. Development and internal evaluation used the same pilot. New independent data and reviewed event labels are needed for stronger scientific claims. No marker was fabricated, and no label ordering was chosen by model accuracy.')
    h('Primary references')
    p('[1] Johnston W et al. Quantifying Y Balance Test performance with multiple and single inertial sensors. EMBC. 2020:4243-4247. DOI: 10.1109/EMBC44109.2020.9176416.','SmallDV')
    p('[2] Dehghani A et al. Subject Cross Validation in Human Activity Recognition. 2019. https://arxiv.org/abs/1904.02666.','SmallDV')
    p('[3] Varoquaux G. Cross-validation failure: Small sample sizes lead to large error bars. NeuroImage. 2018;180:68-77. DOI: 10.1016/j.neuroimage.2017.06.061.','SmallDV')
    p('[4] Noraxon. Ultium Motion Hardware User Manual, Revision G. Manufacturer documentation, accelerations/reference frames. <link href="https://www.noraxon.com/download/ultium-motion-user-manual/?filename=P-8708+Ultium+Motion+User+Manual+%28Rev+G%29.pdf&amp;ind=1750805814140&amp;wpdmdl=23822" color="#0f766e">Official manual</link>. [5] scikit-learn official documentation: <link href="https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.LeaveOneGroupOut.html" color="#0f766e">LeaveOneGroupOut</link> and <link href="https://scikit-learn.org/stable/common_pitfalls.html#data-leakage" color="#0f766e">data leakage</link>.','SmallDV')
    def footer(c,d):
        c.setStrokeColor(colors.HexColor('#d9e5eb'));c.line(45,39,550,39);c.setFont('DV',7)
        c.drawString(45,26,'YBT-L5 | Complete exploratory pipeline v2.0 | Reconstructed boundaries remain proposals')
        c.drawRightString(550,26,str(d.page))
    SimpleDocTemplate(str(out/'YBT_L5_Complete_Report.pdf'),pagesize=A4,leftMargin=45,rightMargin=45,topMargin=42,bottomMargin=51,
        title='YBT-L5 Complete Exploratory Pipeline',author='Sina Maleki').build(story,onFirstPage=footer,onLaterPages=footer)


def write_docs(out,summary):
    out=Path(out)
    text='''# YBT-L5 complete exploratory pipeline v2.0

Prepared for Sina Maleki on 4 November 2026.

Start with **YBT_L5_Complete_Report.pdf** and **Review_Viewer.html**. The viewer is self-contained and runs locally without a network connection.

## Current scientific status

- All 14 recordings are processed. There are 198 observed-marker intervals and 54 explicitly provisional intervals. A proposal is not an observed or independently validated event.
- The researcher confirmed six positions in a cycle repeated three times: R ANT, L ANT, R PM, L PM, R PL, L PL; right/left denotes the stance leg. The final L PM in the latest message was interpreted as a typo for the previously stated L PL. Every label-dependent result remains conditional on that interpretation.
- ID3 belongs to group2 (Eye), ID4 to group1 (Breathing). The corrected scoring workbook is included. Other assignments and measurements are preserved.
- The 11 complete-marker recordings contain 36 pulses each. Marker-hidden segmentation matched 160/198 intervals at IoU >= 0.5. Marker timings are a manual reference, not a force-platform/video measurement of true movement onset.
- The exact synthetic extra event was removed in only 55% of 220 tests. Consequently neither real deletion is automatically accepted. The two 37-event cases retain every ranking, observed pulse and an independent signal-detector alternative.
- IMU01 PRE has 18 signal-only proposals. Selecting 18 peaks uses the known protocol count; count alone is not evidence of accurate recovery. Unselected candidates remain in all_signal_candidates.csv.
- Primary models use the 198 observed-marker intervals. All-252 models are sensitivity analyses. Human waveform review does not automatically promote reconstructed boundaries into the observed-marker dataset.
- Direction models remain weak under this protocol. Participant-average normalized-reach MAE improved from 10.10 to 8.61 percentage points in the fixed Ridge comparison; seven people do not establish a clinical predictor.

## Recovery methods

The markerless detector uses smoothed vendor Roll/Pitch excursion relative to a robust low-angular-speed baseline. Peak detection is fixed (3-degree prominence, 1.25-second minimum separation, 0.3-second minimum half-prominence width), and the 18 highest-prominence candidates are selected using the expected trial count. Boundaries use 90%-prominence widths, corrected by training-subject median offsets. Overlaps are clipped at the midpoint between peaks.

For every hidden-marker test, all recordings of that participant are excluded while fitting boundary offsets. Interval matches use a one-to-one maximum-IoU assignment. Precision and recall at IoU=0.5 are both reported; because 18 predictions are requested, this count is not a free detection result. Timing MAEs in the detailed file are conditional on IoU>=0.3 matches.

For 37 pulses, a training-subject-only logistic classifier scores START/END patterns from local gyroscope/angle context. All 37 single-deletion hypotheses are ranked. This assumes exactly one extra event; other acquisition errors can produce the same count. Ranking margins are not calibrated correctness probabilities.

This is internal evaluation of algorithms developed on the same pilot, not untouched external validation. The synthetic event distribution is not known to reproduce actual acquisition mistakes.

## Models and measurements

All participant-level folds keep both sessions of the test person outside training. Scaling/encoding is fitted on training participants only. Fixed models: dummy, C=1 logistic with four magnitude features, C=1 logistic with 12 directional descriptors, and a 200-tree depth-4 forest with leaf minimum 3. No hyperparameter search, label-order optimization or independent clinical-risk labels are used.

Core signals are filtered over the **complete recording** before segmentation at 4, 6 and 10 Hz (4th-order zero-phase Butterworth). This corrects the earlier per-interval filtering edge issue and slightly changes the prior magnitude-model result. All cutoff/model combinations are reported, including poor ones.

Gyroscope units are deg/s. Raw sensor acceleration is mG, converted with 0.00980665 m/s^2 per mG. Centering does not remove changing gravity projections. Acceleration derivatives are sensor-frame signal descriptors, not validated movement smoothness. Vendor axes, Roll/Pitch, quaternion outputs and model-derived COM must not be confused with independently validated anatomical AP/ML or force-platform COP measurements.

Ridge alpha=10 predicts concurrent trial normalized reach (reach/leg length x 100) from the 12 descriptors plus direction/stance leg. Its baseline uses training-only direction/leg means. This is not prediction of future improvement or injury. No group, identity, session, measured reach or absolute time is a predictor.

## Conventional YBT analysis

The corrected 39-person 2-time x 3-group analysis uses subject means for Group and within-person differences for Group x Time; the Time test uses the pooled within-group variance of differences. Holm adjustment is applied across four outcomes within each effect family. Effect sizes and unadjusted p values are provided. None of the 12 tests reached unadjusted p<0.05. No equivalence or treatment-absence claim is made.

The separate original YBT_Descriptive_with_ErrorBars.xlsx remains an unreliable legacy summary; its 12 delta-mean identities fail. Use raw_audit/ybt_group_descriptives_recomputed.csv instead. ID39 POST R PL trial3 remains missing; the source's MAX-of-available scoring rule is retained and flagged.

## Reproduce

Dependencies: numpy, pandas, scipy, scikit-learn, matplotlib, openpyxl (read-only workbook access), reportlab. environment_versions.json records the actual versions. No raw participant names or raw recordings are redistributed here.

Place the seven original ZIP archives and the two original scoring XLSX files under upload with their original filenames. Then run:

```bash
python run_complete_ybt.py --input-dir upload --output-dir output/YBT_L5_Complete_v2
```

To apply exported, user-reviewed boundaries:

```bash
python run_complete_ybt.py --input-dir upload --output-dir output/YBT_L5_Reviewed --review-csv YBT_reviewed_boundaries.csv
```

Review edits must be valid, chronological and nonoverlapping. Feature extraction and all models are rerun after boundary changes. Observed/reconstructed provenance is retained. The HTML stores edits in browser local storage as a convenience; download the CSV/JSON to preserve them reliably.

## Main outputs

- trial_annotations_all_sources.csv: all 252 intervals with IDs, protocol labels, recovery source, conditional assumptions and score linkage.
- trial_features_all_cutoffs.csv: 756 feature rows (252 intervals x 3 cutoffs).
- marker_hidden_validation_by_recording.csv and marker_hidden_validation_matches.csv: the independent participant folds for segmentation.
- synthetic_extra_pulse_validation.csv: all 220 synthetic tests, including errors.
- recovery_decisions.csv, all_extra_event_rankings.csv and signal_detector_intervals_all.csv: proposals and alternatives.
- figures/: a segmentation plot for every recording.
- models/: fold membership, predictions, per-participant metrics, processing sensitivity, confusion matrix and reach estimates.
- raw_audit/: export QC for all 321 streams and independently recomputed conventional YBT scores.
- ybt_39_mixed_anova_corrected_groups.csv: the corrected conventional-score analysis.
- Complete_Analysis.ipynb: a compact notebook for inspecting supplied outputs without raw recordings.

## Defensible portfolio statement

Developed a reproducible Python workflow for lumbar-IMU Y-Balance recordings, including exported-signal QC, provenance-aware event-recovery proposals, participant-held-out segmentation validation, and exploratory direction/reach models.

## Primary sources

1. Johnston et al. (2020). https://doi.org/10.1109/EMBC44109.2020.9176416
2. Dehghani et al. (2019). https://arxiv.org/abs/1904.02666
3. Varoquaux (2018). https://doi.org/10.1016/j.neuroimage.2017.06.061
4. Noraxon, Ultium Motion Hardware User Manual Revision G, acceleration reference frames.
5. scikit-learn official LeaveOneGroupOut and common-pitfalls documentation. https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.LeaveOneGroupOut.html
'''
    results={r['model']:r for r in summary['reach_results'] if r['dataset']=='observed_only'}
    text=text.replace('10.10 to 8.61',f"{results['direction_leg_mean']['mean_subject_mae_pp']:.2f} to {results['ridge_signals_plus_protocol']['mean_subject_mae_pp']:.2f}")
    text+='\n## Verification limits\n\nThe PDF was rendered and visually checked. Viewer application logic (record selection, boundary validation/editing, review/reset, persistence and 252-row export) was checked without a browser engine. Browser launch/file navigation is restricted in the authoring environment, so actual browser rendering and download behavior were not verified there. The full CLI was rerun with an exported, reviewed missing-marker edit; the edit was applied, reconstructed provenance and the 198/54 split were retained, and primary model results remained unchanged. Mixed-ANOVA F statistics were independently reconciled with SciPy one-way tests and a group-mean linear contrast.\n'
    text+='\nIf using the included YBT_Corrected_Groups.xlsx, place a copy in upload named YBT_Clean_Scoring_Workbook-39 subjects.xlsx. The two confirmed group overrides are applied explicitly by the analysis code.\n'
    (out/'README.md').write_text(text)
    fa='''# خلاصهٔ نسخهٔ کامل YBT-L5

هر ۱۴ ضبط پردازش شده است: ۱۹۸ بازه با مارکر واقعی و ۵۴ بازهٔ پیشنهادی. فایل‌های بدون مارکر کنار گذاشته نشده‌اند؛ نتیجهٔ بازیابی و گزینه‌های جایگزین همراه با محدودیت‌ها موجود است.

چرخهٔ شش‌تایی سه بار تکرار شده در نظر گرفته شده است. آخرین «چپ PM» در پیام اخیر، مطابق ترتیب قبلی «چپ PL» تفسیر شده؛ نتایج برچسب‌دار مشروط به این تفسیرند.

در آزمون پنهان‌کردن مارکر، ۱۶۰ از ۱۹۸ بازه با مرجع حداقل ۵۰٪ هم‌پوشانی داشتند. این دقتِ مورد تضمین‌شده برای ضبطِ بدون مارکر نیست. حذف پالس مصنوعی فقط در ۵۵٪ آزمون‌ها درست بود؛ بنابراین حذف‌های پیشنهادی قطعی نیستند.

برای مرور، Review_Viewer.html را باز کن. هر ضبط و هر تلاش را انتخاب کن؛ مرزها، مارکرها و پیشنهاد جایگزین دیده می‌شوند. مرزهای اصلاح‌شده را به CSV یا JSON خروجی بگیر. دستور بازاجرای تحلیل با این اصلاح‌ها در README آمده است.

مدل اصلی جهت با ویژگی‌های جهت‌دار دقت متوازن ۳۶٫۵٪ داشت؛ جنگل تصادفی ۳۹٫۷٪ و مدل مبنا ۳۳٫۳٪. خطای برآورد هم‌زمان مسافت نرمال‌شده از ۱۰٫۱۰ به ۸٫۶۱ واحد درصد رسید. این‌ها نتایج اکتشافی هفت نفرند و اعتبارسنجی بالینی نیستند.

گروه سابجکت ۳ به ۲ و سابجکت ۴ به ۱ اصلاح شده است. بازتحلیل YBT هر ۳۹ نفر نیز در گزارش و CSV موجود است. نمره‌های فردی تغییر نکرده‌اند.
'''
    (out/'خلاصه.txt').write_text(fa)
    cells=[{'cell_type':'markdown','metadata':{},'source':['# YBT-L5 complete pilot\n','Inspect real outputs; reconstructed boundaries remain proposals. Read README before interpreting results.']},
        {'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':['from pathlib import Path\n','import pandas as pd\n','root = Path.cwd()\n','pd.read_csv(root / "marker_hidden_validation_by_recording.csv")']},
        {'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':['pd.read_csv(root / "models/direction_summary.csv").query("cutoff_hz == 6")']},
        {'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':['pd.read_csv(root / "models/reach_per_subject.csv").query("dataset == \'observed_only\'")']},
        {'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':['pd.read_csv(root / "ybt_39_mixed_anova_corrected_groups.csv")']},
        {'cell_type':'markdown','metadata':{},'source':['No claim of clinical prediction, population generalization or verified marker recovery follows from these outputs. Use the viewer to review uncertain boundaries; preserve provenance in any export.']}]
    for i,cell in enumerate(cells):cell['id']=f'cell{i:03d}'
    (out/'Complete_Analysis.ipynb').write_text(json.dumps({'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3'}},'nbformat':4,'nbformat_minor':5},indent=2))
    versions=json.loads((out/'environment_versions.json').read_text())
    (out/'requirements.txt').write_text('\n'.join(f'{k}=={v}' for k,v in versions.items())+'\n')
