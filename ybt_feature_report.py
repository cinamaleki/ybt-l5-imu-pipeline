"""Standalone bilingual report and scientific plots; generated outputs remain private."""
from pathlib import Path
import base64,html,json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

LABELS={'gyro_rms':'شدت معمول سرعت چرخش','gyro_p95':'مقدار بالای سرعت چرخش',
'acc_centered_rms':'تغییرات شتاب حول میانگین','sensor_acc_derivative_rms':'سرعت تغییر شتاب در دستگاه مختصات حسگر',
'roll_p05':'صدک پایین زاویه Roll نسبت به شروع','roll_p95':'صدک بالای زاویه Roll نسبت به شروع',
'pitch_p05':'صدک پایین زاویه Pitch نسبت به شروع','pitch_p95':'صدک بالای زاویه Pitch نسبت به شروع',
'gyro_x_rms':'شدت سرعت چرخش محور x حسگر','gyro_y_rms':'شدت سرعت چرخش محور y حسگر','gyro_z_rms':'شدت سرعت چرخش محور z حسگر',
'acc_x_centered_rms':'تغییرات شتاب محور x حسگر','acc_y_centered_rms':'تغییرات شتاب محور y حسگر','acc_z_centered_rms':'تغییرات شتاب محور z حسگر',
'quaternion_excursion_p95_deg':'مقدار بالای تغییر جهت‌گیری حسگر','duration_s':'مدت حرکت'}


def write_audit_report(out,meta,summary,scenarios,subject_repeats):
    out=Path(out);figdir=out/'figures';figdir.mkdir(exist_ok=True)
    metrics=['median_subject_pair_diff_pct_iqr','boundary_worst_median_pct_iqr','filter_worst_median_pct_iqr']
    names=['Repeated-execution variation','Boundary sensitivity (worst scenario)','Filter sensitivity (4/10 vs 6 Hz)']
    labels=summary.feature.tolist();data=summary[metrics].to_numpy()
    origin_label='Synthetic demonstration' if meta['data_origin']=='ENTIRELY_SYNTHETIC' else 'Private pilot'
    fig,ax=plt.subplots(figsize=(11,8));im=ax.imshow(np.maximum(data,.01),aspect='auto',norm=LogNorm(vmin=.1,vmax=max(100,np.nanmax(data))),cmap=plt.colormaps['YlOrRd'].with_extremes(bad='#dbe4e9'))
    ax.set_xticks(range(3),['Repeat variation','Boundary sensitivity','Filter sensitivity']);ax.set_yticks(range(len(labels)),labels)
    for i in range(len(labels)):
        for j in range(3):ax.text(j,i,f'{data[i,j]:.1f}' if np.isfinite(data[i,j]) else 'N/A',ha='center',va='center',fontsize=9,color='black' if not np.isfinite(data[i,j]) or data[i,j]<80 else 'white')
    ax.set_title(origin_label+': descriptive feature audit\nValues = % of observed 6 Hz feature IQR; lower indicates smaller variation')
    fig.colorbar(im,ax=ax,label='% reference IQR (log color scale)');fig.tight_layout();fig.savefig(figdir/'feature_sensitivity.png',dpi=160);plt.close(fig)
    rep=subject_repeats.query("dataset=='observed_only'");fig,ax=plt.subplots(figsize=(11,8))
    for i,f in enumerate(labels):
        vals=rep[rep.feature==f].median_pair_diff_pct_iqr.to_numpy();ax.scatter(vals,np.ones(len(vals))*i,s=28,alpha=.7,color='#0891b2')
        ax.scatter(np.median(vals),i,marker='|',s=180,color='#0f172a')
    ax.set_yticks(range(len(labels)),labels);ax.invert_yaxis();ax.set(xlabel='Within-cell median pair difference / reference IQR (%)',title='One dot per participant; black mark = median participant\nPRE/POST are summarized within participants, not treated as independent people')
    ax.grid(axis='x',alpha=.2);fig.tight_layout();fig.savefig(figdir/'repeat_variation_by_person.png',dpi=160);plt.close(fig)
    det=scenarios[scenarios.scenario.isin(['signal_detector_all_matches','signal_detector_iou_ge_0p5'])]
    fig,ax=plt.subplots(figsize=(11,8));y=np.arange(len(labels))
    for offset,key,color,name in [(-.18,'signal_detector_all_matches','#64748b','All one-to-one matches'),(.18,'signal_detector_iou_ge_0p5','#d97706','Selected matches with IoU >= 0.5')]:
        g=det[det.scenario==key].set_index('feature').reindex(labels)
        ax.barh(y+offset,g.median_subject_change_pct_iqr,height=.34,color=color,label=name)
    ax.set_yticks(y,labels);ax.invert_yaxis();ax.set(xlabel='Median participant absolute change / reference IQR (%)',title='Signal-only detector vs observed Switch boundaries\nThese are internal development comparisons, not independent validation');ax.legend(fontsize=9);fig.tight_layout();fig.savefig(figdir/'detector_feature_changes.png',dpi=160);plt.close(fig)
    def image(name):return '<img class="chart" alt="'+name+'" src="data:image/png;base64,'+base64.b64encode((figdir/name).read_bytes()).decode()+'">'
    def table(d):return '<div class="scroll">'+d.to_html(index=False,escape=True,float_format=lambda x:f'{x:.2f}')+'</div>'
    top=summary.dropna(subset=['exploratory_average_rank']).head(5)
    display=top[['feature','unit','median_subject_pair_diff_pct_iqr','boundary_worst_median_pct_iqr','filter_worst_median_pct_iqr']].copy()
    display.insert(1,'معنی ساده',display.feature.map(LABELS));display.columns=['Feature','معنی ساده','واحد','تفاوت سه تکرار','حساسیت مرز','حساسیت فیلتر']
    ftable=summary[['feature','unit','median_subject_pair_abs_diff','median_subject_pair_diff_pct_iqr',
        'boundary_worst_median_pct_iqr','filter_worst_median_pct_iqr','boundary_worst_p95_pct_iqr','filter_worst_p95_pct_iqr']].copy()
    ftable=ftable.fillna('N/A')
    ftable.columns=['Feature','واحد','تفاوت تکرار در واحد اصلی','تفاوت تکرار %IQR','مرز: میانه %IQR','فیلتر: میانه %IQR','مرز: صدک۹۵ %IQR','فیلتر: صدک۹۵ %IQR']
    lookup=summary.set_index('feature')
    gp=lookup.loc['gyro_p95'];deriv=lookup.loc['sensor_acc_derivative_rms']
    selected='، '.join('<code>'+html.escape(x)+'</code>' for x in top.feature)
    banner='این گزارش فقط روی دادهٔ کاملاً مصنوعی اجرا شده و نتیجهٔ انسانی نیست.' if meta['data_origin']=='ENTIRELY_SYNTHETIC' else 'تحلیل توصیفی همان پایلوت هفت‌نفره؛ بدون اعتبارسنجی مستقل یا ادعای کاربرد بالینی.'
    text=f'''<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>YBT–L5 | گزارش ثبات و حساسیت ویژگی‌ها</title><style>
    body{{font:16px/1.95 Tahoma,Arial,sans-serif;color:#183347;background:#eef4f7;margin:0}}main{{max-width:1150px;margin:30px auto;padding:26px;background:white;border-radius:14px}}h1{{font-size:27px}}h2{{font-size:20px;margin-top:35px;color:#0f766e}}aside{{background:#fff4db;padding:17px;border-right:5px solid #d97706;border-radius:6px}}.cards{{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0}}.cards div{{background:#e8f4f3;padding:15px;min-width:150px;flex:1}}strong{{color:#0f5f59}}table{{border-collapse:collapse;width:100%;font-size:12px;direction:ltr}}td,th{{padding:9px;border:1px solid #d5e2e9}}th{{background:#eaf1f5}}.scroll{{overflow:auto}}code{{direction:ltr;unicode-bidi:embed;font-size:13px}}.chart{{width:100%;height:auto;margin-top:18px}}li{{margin:8px 0}}a{{color:#076e93}}@media print{{body{{background:white}}main{{margin:0;padding:0}}.chart{{break-inside:avoid}}}} </style><main>
    <h1>ویژگی‌های حرکت کمر چقدر به تکرار و پردازش وابسته‌اند؟</h1><p>سینا ملکی | ۱۱ نوامبر ۲۰۲۶ | تحلیل تکمیلی YBT–L5</p><aside>{banner}</aside>
    <div class="cards"><div><strong>{meta['participants']}</strong><br>شرکت‌کننده</div><div><strong>{meta['observed_trials']}</strong><br>بازهٔ مبتنی بر Switch</div><div><strong>{meta['proposals']}</strong><br>مرز پیشنهادیِ جداگانه</div><div><strong>{meta['complete_observed_repeat_cells']}</strong><br>حالتِ دارای سه تکرار در تحلیل اصلی</div></div>
    <h2>۱. دقیقاً چه کاری تمام شد؟</h2><p>۱۶ ویژگی موجود را بررسی کردیم: تفاوت بین سه اجرای یک جهت و پای اتکا در همان جلسه؛ تغییر ویژگی‌ها با هشت جابه‌جاییِ مشخص مرزها؛ تفاوت فیلترهای ۴ و ۱۰ هرتز با مرجع ۶ هرتز؛ و تفاوت ویژگی‌ها هنگام استفاده از مرز پیشنهادی آشکارساز به‌جای Switch. مدل جدیدی آموزش داده یا تنظیم نشده است.</p>
    <p>جدول ویژگی‌های قبلی با محاسبهٔ مجدد از سیگنال‌های اصلی، با تلورانس عددی ۱۰ به توان منفی ۹، تطبیق داده شد. جابه‌جایی‌ها شامل انتقال کل پنجره به اندازهٔ ±۱۰۰ و ±۲۵۰ میلی‌ثانیه، و کوتاه/بلندکردن هر سرِ پنجره به اندازهٔ ۱۰۰ و ۲۵۰ میلی‌ثانیه است. {meta['boundary_excluded_trial_scenarios']} جفتِ حرکت–سناریو به‌علت مرز نامعتبر یا هم‌پوشانی کنار گذاشته شد؛ هیچ مرزی بی‌سروصدا بریده نشده است.</p>
    <h2>۲. این عددها چه معنایی دارند؟</h2><p>برای سه مقدارِ یک حالت، اختلاف مطلق هر جفت محاسبه و میانهٔ آن‌ها گرفته شد. ابتدا حالت‌ها در هر فرد خلاصه شدند و سپس میانهٔ هفت فرد گزارش شد تا فردی که دو جلسهٔ دارای Switch دارد وزن بیشتری نگیرد. پیش و پس‌آزمون به‌عنوان افراد مستقل شمرده نشده‌اند.</p>
    <p>برای مقایسهٔ ویژگی‌هایی با واحد متفاوت، اختلاف بر فاصلهٔ صدک ۲۵ تا ۷۵ همان ویژگی در ۱۹۸ حرکت مرجع تقسیم و در ۱۰۰ ضرب شده است؛ نام این فاصله IQR است. مثلاً عدد ۲۰ یعنی تغییر به اندازهٔ یک‌پنجم IQR همان ویژگی. این عدد درصدِ خطای بالینی، درصدِ نمرهٔ تعادل یا آستانهٔ پذیرش نیست. IQR شامل تفاوت افراد و جهت‌ها هم هست. اعداد در واحد اصلی و دامنهٔ فردی در CSVها آمده‌اند.</p>
    <h2>۳. کدام ویژگی‌ها برای بررسی بعدی جلوتر قرار گرفتند؟</h2><p>{selected}</p><p>رتبه‌بندی فقط برای ۱۰ ویژگیِ ژیروسکوپ و شتاب، با وزن برابرِ سه رتبهٔ توصیفی ساخته شده است: تفاوت تکرار، بدترین میانهٔ حساسیت مرز، و بدترین میانهٔ حساسیت فیلتر. «پنج مورد اول» صرفاً برای خوانایی است؛ مرز آماری برای قابل‌اعتمادبودن نیست. تغییر وزن‌ها یا نمونهٔ افراد می‌تواند رتبه را عوض کند. زاویه‌ها و جهت‌گیری خروجی دستگاه در این مرحله دوباره فیلتر نشده‌اند؛ بنابراین N/A یا خانهٔ خالی یعنی آزمون فیلتر برای آن‌ها کاربرد ندارد، نه اینکه مقاومت عالی دارند. این موارد و مدت حرکت از رتبه‌بندی سه‌معیاری کنار گذاشته شده‌اند.</p>{table(display)}
    {image('feature_sensitivity.png')}
    <h2>برداشت کاربردی از همین داده‌ها</h2><p>ویژگی <code>gyro_p95</code> در مقایسهٔ سه‌معیاری جلوتر قرار گرفت. میانهٔ فردیِ تفاوت تکرارهای آن {gp.median_subject_pair_diff_pct_iqr:.1f}٪ از IQR مرجع بود؛ بدترین میانهٔ تغییر بر اثر جابه‌جایی مرز {gp.boundary_worst_median_pct_iqr:.1f}٪ و بر اثر فیلتر {gp.filter_worst_median_pct_iqr:.1f}٪ بود. با این حال، صدک ۹۵ تغییر مرز در بدترین سناریو {gp.boundary_worst_p95_pct_iqr:.1f}٪ از IQR بود: میانهٔ کوچک، تغییرهای بزرگ در بعضی تلاش‌ها را پنهان می‌کند.</p><p>برای مشتق شتاب، حساسیت میانه به فیلتر به {deriv.filter_worst_median_pct_iqr:.1f}٪ از IQR رسید. بنابراین این ویژگی در این پایلوت برای تفسیرِ مستقل از تنظیم پردازش مناسب‌تر نشده و به احتیاط بیشتری نیاز دارد. کمتر بودن حساسیت پردازشِ یک ویژگی، به معنی کم بودن تغییر طبیعی آن بین سه اجرا یا روایی تعادل نیست.</p><h2>۴. آیا سه تکرار یک فرد شبیه‌اند؟</h2><p>هر نقطه در شکل زیر مربوط به یک شرکت‌کننده است. پراکندگی نقاط نشان می‌دهد یک نتیجهٔ میانگین، رفتار همهٔ افراد را یکسان توصیف نمی‌کند. تفاوت سه اجرای موفق می‌تواند ناشی از تغییر واقعی راهبرد حرکت، تمرین/خستگی، پردازش یا خطای حسگر باشد. دادهٔ فعلی سهم هرکدام را جدا نمی‌کند؛ بنابراین عنوان این بخش «تغییرپذیری اجراهای تکراری» است، نه اثبات پایایی ابزار یا حداقل تغییر واقعی.</p>{image('repeat_variation_by_person.png')}
    <h2>۵. مرزهای پیشنهادی چه اثری داشتند؟</h2><p>در {meta['detector_matches']} جفتِ آشکارساز–Switch، {meta['detector_iou_ge_0p5']} جفت دست‌کم ۵۰٪ هم‌پوشانی از نوع IoU داشتند. تطبیق یک‌به‌یک بر اساس بیشترین مجموع هم‌پوشانی انجام شد، نه با فرضِ درست‌بودن شمارهٔ قله. شکل زیر همهٔ جفت‌ها و زیرمجموعهٔ منتخب IoU≥۰٫۵ را جدا نشان می‌دهد. نتیجهٔ بهترِ زیرمجموعه، به‌علت انتخاب موارد با هم‌پوشانی بیشتر، شاهد موفقیت در فایل بدون Switch نیست.</p>{image('detector_feature_changes.png')}
    <p>۵۴ مرز بازسازی‌شده همچنان پیشنهاد هستند. بررسی حاضر به آن‌ها اعتبار مشاهده‌شده نمی‌دهد. رده‌بندی ویژگی‌ها فقط با ۱۹۸ بازهٔ اصلی انجام شده؛ جدول تکرارهای شامل پیشنهادها جدا ذخیره شده است.</p>
    <h2>۶. جدول کامل برای ارزیابی پژوهشی</h2>{table(ftable)}
    <h2>۷. چه نتیجه‌ای می‌توان گرفت؟</h2><ul><li>ویژگی‌های بالاترِ جدول، نامزدِ بررسی بعدی از نظر این سه معیار توصیفی‌اند؛ برتری تشخیصی، حساسیت به مداخله یا روایی تعادل از رتبهٔ آن‌ها نتیجه نمی‌شود.</li><li>مقادیر Roll/Pitch و محورهای x/y/z به چارچوب حسگر مربوط‌اند؛ انطباق آن‌ها با محورهای آناتومیک تأیید نشده است. مشتق شتاب هم شامل اثر تغییر جهت‌گیری/گرانش است و شاخص معتبر نرمی حرکت فرض نمی‌شود.</li><li>مرجع مستقل مثل ویدئو یا ابزار اندازه‌گیری مناسب برای داوری قطعی مرزها و اعتبار زیست‌مکانیکی لازم است. نبود چنین مرجعی با بازبینی شکل موج برطرف نمی‌شود.</li><li>این تحلیل می‌تواند انتخاب ویژگی و طراحی مطالعهٔ بعدی را راهنمایی کند. از هفت نفر نمی‌توان عملکرد عمومی یک ابزار بالینی یا اثر قطعی گروه‌های مداخله را اثبات کرد.</li></ul>
    <h2>۸. فایل‌های همراه</h2><p>جدول اصلی: <code>feature_audit_summary.csv</code>؛ جزئیات سه تکرار: <code>repeat_cells.csv</code> و <code>repeat_by_subject.csv</code>؛ مقایسهٔ پردازش: <code>processing_summary.csv</code>؛ تمام اختلاف‌های جفت‌شده: <code>paired_feature_changes.csv</code>؛ مرزهای نامعتبر: <code>excluded_perturbations.csv</code>؛ تطبیق آشکارساز: <code>detector_matching_observed.csv</code>. جدول‌های فردی حاوی دادهٔ خصوصی پژوهش‌اند و وارد مخزن عمومی کد نمی‌شوند.</p>
    <h2>۹. منابع و حدود استناد</h2><ol><li>Koo &amp; Li (2016). A guideline of selecting and reporting intraclass correlation coefficients for reliability research. <a href="https://doi.org/10.1016/j.jcm.2016.02.012">DOI</a>. تفکیک تعریف توافق و ثبات در طراحی پایایی؛ در این گزارش ICC محاسبه نشده است.</li><li>Varoquaux (2018). Cross-validation failure: small sample sizes lead to large error bars. <a href="https://doi.org/10.1016/j.neuroimage.2017.06.061">DOI</a>. محدودیت برآورد عملکرد با نمونهٔ کوچک.</li><li>Johnston et al. (2018). Inertial sensor technology can capture changes in dynamic balance control during the Y Balance Test. <a href="https://doi.org/10.1159/000485470">DOI</a>. پشتوانهٔ بررسی اطلاعات مکمل حسگر؛ نتیجهٔ آن مطالعه اعتبار ویژگی‌های فعلی را اثبات نمی‌کند.</li></ol>
    <p>اعداد این گزارش خروجی تحلیل فعلی‌اند؛ رتبه‌بندی اکتشافی و وابسته به همین داده است. همبستگی رتبه‌ای در CSV فقط توصیفی است و جای توافق عددی یا اعتبارسنجی را نمی‌گیرد.</p></main></html>'''
    (out/'YBT_Feature_Audit_FA.html').write_text(text,encoding='utf-8')
    (out/'METHODS_AND_LIMITATIONS.md').write_text('''# Feature audit methods and limits

Primary data: observed-Switch intervals at 6 Hz. Repeated-execution cells require exactly three trials of one participant/session/stance leg/direction. Median absolute pair differences are summarized across cells within each participant, then across participants. Variability includes true movement variation and measurement/processing error; it is not an isolated sensor-error estimate, test-retest reliability coefficient, SEM, or MDC. PRE and POST are not test-retest equivalents.

Reference scale: pooled observed-trial IQR of each 6 Hz feature, fixed for every comparison and both datasets. This includes between-condition/person variation; it is not a clinical acceptance threshold. Natural units are retained. Signed features are not divided by near-zero cell means.

Fixed boundary scenarios: shifts of the entire window by +/-0.10 and +/-0.25 s; trim or expand each end by 0.10 or 0.25 s. Invalid bounds, overlaps and fewer than 40 samples are rejected, never silently clipped. The source table is reconciled to recomputed full-record-filtered features. Features are recomputed, including duration and initial-relative orientation, rather than reused after changing boundaries.

Filter comparison: 4 and 10 Hz versus 6 Hz using the same observed boundaries. Median changes are first summarized within participant. Worst scenario is the maximum across scenario summaries. P95 summaries are pooled trial diagnostics, not independent-participant inference. Spearman correlations describe pooled ranking only; no p-values or reliability interpretation are supplied.

Detector comparison: maximum-total-IoU one-to-one assignment to observed intervals, all matched pairs and the selected IoU>=0.5 subset separately. This uses the previous same-pilot marker-hidden detector outputs; no external reference or independent validation is added. The selected subset excludes difficult overlaps and does not estimate performance in missing-marker files.

Exploratory rank: average of equal-weight ascending feature ranks for repeated-execution dispersion, worst boundary median change, and worst filter median change. Duration is reported but excluded from the movement-feature rank. Orientation and duration were not refiltered; filter sensitivity is marked not applicable and these descriptors are excluded from the three-criterion rank. The ranking is data-dependent, arbitrary in weighting, not a clinical scale or model-performance result, and is not used to retune the previous models.

Sources: Koo & Li, 2016, doi:10.1016/j.jcm.2016.02.012; Varoquaux, 2018, doi:10.1016/j.neuroimage.2017.06.061; Johnston et al., 2018, doi:10.1159/000485470. Original pilot numeric results require access to authorized private inputs. Generated participant-level tables and reports must remain private.
''')
