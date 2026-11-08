"""Release guard must inspect the staged bytes, including deleted working copies."""
from pathlib import Path
import shutil,subprocess,sys,tempfile,unittest

@unittest.skipUnless(shutil.which('git'),'Git required for staged-tree checks')
class ReleaseGuard(unittest.TestCase):
    def check_tree(self,files,working_edit=None):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'tools').mkdir()
            source=Path(__file__).resolve().parents[1]/'tools/check_public_tree.py'
            shutil.copyfile(source,root/'tools/check_public_tree.py')
            for name,content in files.items():(root/name).write_text(content)
            subprocess.run(['git','init','-q'],cwd=root,check=True)
            subprocess.run(['git','add','.'],cwd=root,check=True)
            if working_edit:
                for name,content in working_edit.items():(root/name).write_text(content)
            return subprocess.run([sys.executable,str(root/'tools/check_public_tree.py')],cwd=root,capture_output=True,text=True)

    def test_source_text_passes(self):
        result=self.check_tree({'README.md':'Synthetic research source only.'})
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_staged_participant_format_is_rejected(self):
        result=self.check_tree({'scores.csv':'id,score\n1,99\n'})
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Unapproved format',result.stdout)

    def test_secret_in_index_remains_detected_after_worktree_cleanup(self):
        artificial_token='gh'+'p_'+'A'*36
        result=self.check_tree({'README.md':artificial_token},{'README.md':'Removed from working copy only.'})
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Possible credential',result.stdout)

if __name__=='__main__':unittest.main()
