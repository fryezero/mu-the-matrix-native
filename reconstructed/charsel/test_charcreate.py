"""Portable checks of the create-character panel, the delete flow and the system menu (NATIVE-CHARCREATE-001),
no client bytes: worked examples of reconstructed/charsel/charcreate.c through the validator's ctypes side.
The instruction comparison is scripts/validate_charcreate.py (private, MU_RECOVERY_INTEGRATION=1 with Unicorn)."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('validate_charcreate', ROOT / 'scripts/validate_charcreate.py')
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)


def record(live=1, cls=1, name='Nighty', key=0):
    r = bytearray(V.RECORD)
    r[V.OBJECT] = live
    r[0x12], r[0x3e] = cls, key
    b = name.encode()
    r[0x3658:0x3658 + len(b)] = b
    struct.pack_into('<II', r, 0x3658 + 0x10, len(b), 15)
    return bytes(r)


def case(records=None, **kw):
    records = dict(records or {})
    for i in range(10):
        records.setdefault(i, record(live=0, key=i))
    preview = bytearray(V.RECORD)
    c = {'records': records, 'preview': bytes(preview), 'slots': list(range(10)), 'row': 0, 'count': 10,
         'selected': -1, 'shown': -1,
         'window': {'open': 0, 'f79': 0, 'created': 0, 'limit': 5, 'board': [0, 0, 0, 0], 'target': -1,
                    'rename': 0, 'offset': [0.0, 0.0, 0.0]},
         'state': 0x33, 'init': 1, 'fov': 35.0, 'cp949': 0, 'filter': [], 'filter_name': [], 'align': 3,
         'wx': 0.0, 'wy': 0.0, 'wscale': 1.0, 'screen': [1024, 768], 'anim': 1, 'base': 1, 'scene': 5,
         'menu_open': 0, 'menu_check': 1, 'shutdown': 0}
    window = kw.pop('window', {})
    c.update(kw)
    c['window'] = dict(c['window'], **window)
    return c


class CharCreateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = V.load_library()

    def run_family(self, c, family, args=None):
        side = V.CSide(self.lib, c)
        return side, side.run(family, args or {})

    def test_name_checks(self):
        def first(name, **kw):
            _, out = self.run_family(case(**kw), 'name', {'name': name, 'class': 0})
            return out['lines'][0] if out['lines'] else ''
        self.assertIn('"GT6194"', first(b'Nighty', window={'created': 5, 'limit': 5}))   # daily limit
        self.assertIn('"GT390"', first(b'Abc'))                                           # under 4
        self.assertIn('"GT1715"', first(b'xxGMxx', filter_name=[b'GM']))                 # FilterName: substring
        self.assertIn('"GT1715"', first(b'Ad min', filter=[b'Admin']))                   # Filter: spaces removed
        self.assertIn('"GT391"', first(b'sym!bol'))                                      # symbols
        self.assertIn('"GT391"', first(b'\xb0\xa1\xb0\xa2Kim'))                          # SBCS: high bytes refused
        self.assertTrue(first(b'\xb0\xa1\xb0\xa2Kim', cp949=1).startswith('call 009a466c'))  # CP949 Hangul
        self.assertIn('"GT391"', first(b'\xa1\xa1sym', cp949=1))                         # CP949 symbol row
        # the request: name (10 bytes) and (class << 4) + skin of the preview
        c = case()
        p = bytearray(c['preview'])
        p[0x12], p[0x13] = 9, 0
        c['preview'] = bytes(p)
        side, out = self.run_family(c, 'name', {'name': b'TwelveLetters', 'class': 3})
        self.assertEqual(out['lines'], ['call 009a466c "TwelveLett" 144'])
        self.assertEqual(out['globals'][2], 0x34)

    def test_filter_steps_by_character(self):
        # a CP949 trail byte never starts a match (0x0185c95d steps by _mbclen)
        _, out = self.run_family(case(cp949=1, filter=[b'\xa2\xb0']), 'name', {'name': b'\xb0\xa2\xb0\xa1ab',
                                                                                 'class': 0})
        self.assertTrue(out['lines'][0].startswith('call 009a466c'))
        _, out = self.run_family(case(cp949=0, filter=[b'\xa2\xb0']), 'name', {'name': b'\xb0\xa2\xb0\xa1ab',
                                                                                 'class': 0})
        self.assertIn('"GT1715"', out['lines'][0])

    def test_selected_class_pose(self):
        side, out = self.run_family(case(), 'klass', {'class': 9})
        self.assertEqual(out['lines'], ['call 0137d8a1 p 318 0 0 00000000', 'call 012affa4 p+0x3254 1'])
        self.assertEqual(out['window'][7], [V.fhex(10.8), V.fhex(0.0), V.fhex(-1.0)])
        scale = struct.unpack_from('<f', side.preview.raw, V.OBJECT + 0xa0)[0]
        self.assertAlmostEqual(scale, 8.0)

    def test_board_and_render(self):
        c = case(window={'open': 1, 'offset': [10.8, 0.0, -1.0]})
        side, out = self.run_family(c, 'board', {'rect': [100, 200, 300, 400]})
        self.assertEqual(out['window'][4], [100, 200, 300, 400])
        c['window']['board'] = [100, 200, 300, 400]
        _, out = self.run_family(c, 'render')
        walk = next(x for x in out['lines'] if x.startswith('call 01854879'))
        self.assertIn(V.fhex(5.0 - V.f32(10.8)), walk)
        self.assertIn('call 0184b27e 100 200 300 400', out['lines'])
        self.assertEqual(out['globals'][4], V.fhex(10.0))   # CameraFOV
        _, closed = self.run_family(case(), 'render')
        self.assertEqual(closed['lines'], ['call 00aadcbf'])

    def test_created_answer(self):
        c = case()
        packet = {'result': 1, 'name': b'Newbie', 'slot': 2, 'level': 1, 'class': 0x90, 'limit': 5, 'created': 1}
        side, out = self.run_family(c, 'created', {'packet': packet})
        self.assertIn('call 0137f824 2 9 0 00000000 00000000 00000000', out['lines'])
        self.assertIn('call 0129de8d r2 "Newbie"', out['lines'])
        self.assertEqual(out['list'][0], 2)
        self.assertEqual(out['globals'][2:4], [0x35, 0])
        self.assertIn('invoke UpdateCreateCount ["GT6193"]', out['lines'])
        packet['result'] = 0
        _, out = self.run_family(case(), 'created', {'packet': packet})
        self.assertEqual(out['lines'][-1], 'call 00b3967c w 100 "GT1716" "" 0 0 1')

    def test_delete_flow(self):
        c = case({3: record(key=3, name='Old')}, selected=3)
        _, out = self.run_family(c, 'message', {'id': 0x65, 'button': 0, 'text': b''})
        self.assertEqual(out['lines'], ['call 00b39648 w 102 "GT3751\\nGT3752" "" 0 0 0 0'])
        _, out = self.run_family(c, 'message', {'id': 0x66, 'button': 0, 'text': b''})
        self.assertEqual(out['lines'], ['call 00b3974a w 103 "GT1713" "" 20 0 0'])
        _, out = self.run_family(c, 'message', {'id': 0x67, 'button': 0, 'text': b'pw'})
        self.assertEqual(out['lines'], ['call 00b4c76a "Old" "pw"'])
        c['window']['target'] = 3
        _, out = self.run_family(c, 'deleted', {'result': 1})
        self.assertEqual(out['globals'][0], -1)
        self.assertIn('call 00b3967c w 119 "GT1714" "" 0 0 0', out['lines'])
        self.assertEqual(out['window'][5:7], [-1, 0])

    def test_class_names(self):
        self.assertEqual(self.lib.mu_ccr_class_name_text(9, 1), 5526)      # Slayer
        self.assertEqual(self.lib.mu_ccr_class_name_text(10, 1), 5786)     # Gun Crusher
        self.assertEqual(self.lib.mu_ccr_class_name_text(0x19, 1), 5527)
        self.assertEqual(self.lib.mu_ccr_class_name_text(0x13, 1), 2305)   # no case: the default text
        self.assertEqual(self.lib.mu_ccr_class_name_text(11, 0), 0x1750)
        self.assertEqual(self.lib.mu_ccr_class_from_server(0x90), 9)
        self.assertEqual(self.lib.mu_ccr_class_from_server(0x98), 0x19)

    def test_menu(self):
        _, out = self.run_family(case(), 'menu', {'op': 'event', 'event': 'onLoad'})
        text = json.loads(out['lines'][0][len('invoke InitText '):])[0]
        self.assertEqual(text['btnExit'], 'GT381')
        self.assertEqual(out['lines'][1:], ['invoke SceneChange [5]', 'invoke closeWindow []'])
        _, out = self.run_family(case(), 'menu', {'op': 'toggle'})
        self.assertEqual(out['lines'][:2], ['invoke openWindow []', 'call 00000010 4bb0 0'])
        _, out = self.run_family(case(), 'menu', {'op': 'event', 'event': 'onServerSelectClick'})
        self.assertIn('call 009a5ab2 2', out['lines'])


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private: MU_RECOVERY_INTEGRATION=1')
class PrivateCharCreateValidation(unittest.TestCase):
    def test_instruction_comparison(self):
        try:
            import unicorn  # noqa: F401
        except ImportError:
            self.skipTest('unicorn is not installed')
        # 300 main cases yield 60 mutation cases, including CP949 lead bytes.
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_charcreate.py'), '--cases', '300',
                            '--mutations'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main()
