"""Audit files actually staged/tracked, or the source tree when outside Git.
This is a conservative release guard, not a complete anonymization scanner.
"""
from pathlib import Path
import re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
ALLOWED_SUFFIX={'.py','.md','.toml','.txt','.cff','.yml','.yaml'}
ALLOWED_NAMES={'.gitignore','LICENSE'}
EXCLUDED={'__pycache__','.venv','venv','build','dist','demo_output','output','outputs','private_data','data','.git'}

def check():
    try:result=subprocess.run(['git','ls-files','-z','--cached'],cwd=ROOT,capture_output=True)
    except FileNotFoundError:result=None
    tracked=[ROOT/p for p in result.stdout.decode().split('\0') if p] if result is not None and result.returncode==0 else []
    paths=tracked or [p for p in ROOT.rglob('*') if p.is_file() and not any(x in EXCLUDED or x.endswith('.egg-info') for x in p.relative_to(ROOT).parts)]
    errors=[]
    for p in paths:
        rel=p.relative_to(ROOT)
        if p.suffix not in ALLOWED_SUFFIX and p.name not in ALLOWED_NAMES:errors.append(f'Unapproved format: {rel}')
        if any(x in EXCLUDED for x in rel.parts):errors.append(f'Private/generated path is tracked: {rel}')
        if not p.exists():errors.append(f'Missing indexed file: {rel}');continue
        blob=subprocess.run(['git','show',':'+rel.as_posix()],cwd=ROOT,capture_output=True,check=True).stdout if tracked else p.read_bytes()
        if len(blob)>1_000_000:errors.append(f'Unexpected large source file: {rel}')
        try:text=blob.decode('utf-8')
        except UnicodeError:errors.append(f'Non-text file: {rel}');continue
        # Prefixes assembled to avoid the scanner matching its own source.
        patterns=[r'gh'+'p_[A-Za-z0-9]{30,}',r'github_'+'pat_[A-Za-z0-9_]{30,}',r'-----BEGIN '+'(?:RSA |OPENSSH )?PRIVATE KEY-----']
        if any(re.search(x,text) for x in patterns):errors.append(f'Possible credential: {rel}')
    if errors:print('\n'.join(errors));return 1
    print(f'Public source-tree check passed: {len(paths)} text files; no disallowed formats or obvious credentials.');return 0
if __name__=='__main__':sys.exit(check())
