"""Installed entry point; raw inputs and generated real-data outputs are private."""
from pathlib import Path
import argparse

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',action='version',version='%(prog)s 0.2.0')
    sub=parser.add_subparsers(dest='command',required=True)
    demo=sub.add_parser('demo',help='Run entirely synthetic demonstration')
    demo.add_argument('--output-dir',type=Path,default=Path('demo_output'))
    run=sub.add_parser('run',help='Run the study-specific authorized private-data analysis')
    run.add_argument('--input-dir',type=Path,required=True)
    run.add_argument('--output-dir',type=Path,required=True)
    run.add_argument('--review-csv',type=Path)
    robust=sub.add_parser('robustness',help='Private descriptive feature repeat/processing audit')
    robust.add_argument('--input-dir',type=Path,required=True)
    robust.add_argument('--analysis-dir',type=Path,required=True)
    robust.add_argument('--output-dir',type=Path,required=True)
    rdemo=sub.add_parser('robustness-demo',help='Feature audit of an existing synthetic demo output')
    rdemo.add_argument('--analysis-dir',type=Path,required=True)
    rdemo.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='demo':
        from ybt_synthetic import run_demo
        run_demo(args.output_dir)
    elif args.command in ('robustness','robustness-demo'):
        from ybt_feature_audit import feature_audit
        if args.command=='robustness-demo':
            import json
            if json.loads((args.analysis_dir/'synthetic_summary.json').read_text()).get('data_origin')!='ENTIRELY_SYNTHETIC':parser.error('Expected a synthetic demo analysis')
            from ybt_synthetic import synthetic_inputs
            records,_=synthetic_inputs()
        else:
            from ybt_complete_pipeline import load_recordings
            records=load_recordings(args.input_dir)
        feature_audit(records,args.analysis_dir,args.output_dir,synthetic=args.command=='robustness-demo')
    else:
        if args.input_dir.resolve()==args.output_dir.resolve():parser.error('Inputs and outputs must use separate directories')
        from run_complete_ybt import main as analyze
        analyze(args.input_dir,args.output_dir,args.review_csv)

if __name__=='__main__':main()
