"""INPUT-001: router edge/priority checks with synthetic downstream adapters."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class InputRouter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.host = Path(cls.tmp.name)/'input-host'
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-DMU_WORLD_NO_GL',
                        str(ROOT/'native/tests/input_router_host.c'), str(ROOT/'native/world/input.c'),
                        str(ROOT/'native/world/input_keys.c'), '-o',str(cls.host)],check=True)

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def drive(self, *actions):
        return [json.loads(l) for l in subprocess.check_output([str(self.host),*actions],text=True).splitlines()]

    def test_press_edge_and_release(self):
        rows=self.drive('down:49','down:49','up:49','down:49')
        self.assertEqual([r['casts'] for r in rows],[1,1,1,2])
        self.assertEqual(rows[-1]['skill'],4)

    def test_focus_loss_releases_gameplay(self):
        rows=self.drive('down:49','focus-lost','down:49','focus:1','down:49')
        self.assertEqual(rows[1]['digit_held'],0)
        self.assertEqual(rows[2]['casts'],1)
        self.assertEqual(rows[-1]['casts'],2)

    def test_alt_space_and_modifiers(self):
        rows=self.drive('key:18','key:32','down:17','key:49','up:17','key:49')
        self.assertEqual(rows[-1]['labels'],1)
        self.assertEqual(rows[-1]['picks'],1)
        self.assertEqual(rows[-1]['casts'],1)

    def test_ime_candidate_digit_never_casts(self):
        rows=self.drive('compose:1:%E4%B8%AD','key:49','text:%E4%B8%AD','key:49')
        self.assertEqual(rows[1]['casts'],0)
        self.assertEqual(rows[-1]['casts'],1)

    def test_missing_panel_is_explicit(self):
        for r in self.drive('key:Y','key:G','key:B','key:N','key:K'):
            self.assertEqual(r['result'],-1)
            self.assertEqual(r['casts'],0)

    def test_mouse_message_path(self):
        rows=self.drive('move:32,64','ldown:32,64','lup:32,64','rdown:32,64','rup:32,64')
        self.assertGreater(rows[-1]['messages'],4)
        self.assertEqual(rows[-1]['casts'],0)

    def test_invalid_actions_have_no_effects(self):
        for action in ['key:256','key:0','key:49junk','key:1:2','move:1,2junk','move:32768,0',
                       'compose:one:a','text:%','text:%00','wat:1']:
            r=self.drive(action)[0]
            self.assertEqual(r['result'],-2,action)
            self.assertEqual(r['casts']+r['picks']+r['messages'],0,action)

    def test_schedule_rejects_truncation_overflow_and_negative_time(self):
        for text in ['-1:key:Y','999999999999999999999:key:Y','1:', '1:'+'x'*64,
                     ' '.join('1:key:Y' for _ in range(129))]:
            self.assertEqual(subprocess.check_output([str(self.host),'parse',text],text=True).strip(),'-1')
        self.assertEqual(subprocess.check_output([str(self.host),'parse','0:key:Y; 2:key:32\n3:wheel:1'],text=True).strip(),'3')

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private pinned x86 comparison is opt-in')
    def test_private_original_input_instructions(self):
        subprocess.run([sys.executable,str(ROOT/'scripts/validate_input.py'),'--mutations'],check=True)


if __name__=='__main__': unittest.main()
