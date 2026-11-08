"""Installed entry point; raw inputs and generated real-data outputs are private."""
from pathlib import Path
import argparse

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',action='version',version='%(prog)s 0.1.0')
    sub=parser.add_subparsers(dest='command',required=True)
    demo=sub.add_parser('demo',help='Run entirely synthetic demonstration')
    demo.add_argument('--output-dir',type=Path,default=Path('demo_output'))
    run=sub.add_parser('run',help='Run the study-specific authorized private-data analysis')
    run.add_argument('--input-dir',type=Path,required=True)
    run.add_argument('--output-dir',type=Path,required=True)
    run.add_argument('--review-csv',type=Path)
    args=parser.parse_args()
    if args.command=='demo':
        from ybt_synthetic import run_demo
        run_demo(args.output_dir)
    else:
        if args.input_dir.resolve()==args.output_dir.resolve():parser.error('Inputs and outputs must use separate directories')
        from run_complete_ybt import main as analyze
        analyze(args.input_dir,args.output_dir,args.review_csv)

if __name__=='__main__':main()
