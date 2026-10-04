import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class SubmissionSafetyTests(unittest.TestCase):
    def test_environment_files_are_ignored_and_not_tracked(self):
        for name in ('.env','.env.local','.env.production','.vercel/project.json','.aws/credentials','credentials.json','service-account-demo.json','private.key','private.pem','.lifemap-data/accounts.sqlite3','accounts.sqlite3'):
            self.assertEqual(subprocess.run(['git','check-ignore','--no-index','-q',name],cwd=ROOT).returncode,0)
        self.assertEqual(subprocess.check_output(['git','ls-files','.env','.env.local','.env.production'],cwd=ROOT).strip(),b'')

    def test_build_excludes_secrets_and_removes_stale_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'scripts').mkdir();(root/'lifemap-ai-main/src').mkdir(parents=True)
            shutil.copy2(ROOT/'scripts/build_vercel.py',root/'scripts/build_vercel.py')
            (root/'lifemap-ai-main/config.js').write_text("window.LIFEMAP_CONFIG={chatApiUrl:'https://lifemap-ai-live.vercel.app/api/chat',calculateApiUrl:'https://lifemap-ai-live.vercel.app/api/calculate',scenarioApiUrl:'https://lifemap-ai-live.vercel.app/api/scenario',supabaseUrl:'https://public.example.test'};")
            (root/'lifemap-ai-main/index.html').write_text('Synthetic build fixture')
            (root/'lifemap-ai-main/src/.env.local').write_text('SYNTHETIC_SECRET=not-a-real-key')
            (root/'lifemap-ai-main/src/.lifemap-data').mkdir()
            (root/'lifemap-ai-main/src/.lifemap-data/accounts.sqlite3').write_text('Synthetic private accounts')
            (root/'public').mkdir();(root/'public/.env.local').write_text('SYNTHETIC_STALE_SECRET=not-a-real-key')
            subprocess.run([sys.executable,str(root/'scripts/build_vercel.py')],check=True,cwd=root)
            self.assertTrue((root/'public/index.html').exists())
            self.assertFalse(list((root/'public').rglob('.env*')))
            self.assertFalse(list((root/'public').rglob('*.sqlite3')))
            config=(root/'public/config.js').read_text()
            self.assertIn('supabaseUrl',config)
            self.assertIn("window.location.origin + '/api/chat'",config)

if __name__=='__main__':unittest.main()
