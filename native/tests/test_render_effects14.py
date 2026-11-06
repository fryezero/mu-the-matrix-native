"""RENDER-EFFECTS-014: portable native routes; pinned instruction comparisons run separately."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]

class Native(unittest.TestCase):
    def test_flare_writeback_particles_rings_and_volley(self):
        native = ROOT/'native'
        subprocess.run(['make','-s','-C',str(native),'build/libmunative.a','build/libmusession_world.a'],check=True,capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            host=tmp/'host'
            obj=tmp/'host.o'
            command=['clang','-std=c11','-O2','-ffp-contract=off','-I',str(native/'build/gen'),
                     '-I',str(native/'session'),'-c',str(native/'tests/effects14_host.c'),'-o',str(obj)]
            p=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            command=['clang++',str(obj),str(native/'build/libmunative.a'),str(native/'build/libmusession_world.a'),'-lm','-o',str(host)]
            if sys.platform=='darwin':
                command += ['-L/opt/homebrew/opt/cryptopp/lib','-lcryptopp',
                            '-L/opt/homebrew/opt/jpeg-turbo/lib','-ljpeg',
                            '-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation']
            else: command += ['-lcryptopp','-ljpeg']
            p=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            p=subprocess.run([str(host),str(tmp)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertIn('Flare/b write-back, Flare02/e particles, 0x70c rings and volley verb through native routes: OK',p.stdout)


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions_and_compiled_mutants(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_render_effects14.py'),
                            '--cases','20','--mutations','--output',str(out)],check=True,capture_output=True)
            report=json.loads(out.read_text())
        self.assertTrue(report['all_equal'])
        self.assertTrue(report['all_mutants_caught'])
        self.assertEqual(report['instruction_cases'],660)
        self.assertEqual(len(report['mutants']),48)
