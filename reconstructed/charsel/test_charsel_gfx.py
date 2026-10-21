"""Portable checks of the character-select GFx window (NATIVE-CHARSEL-003), no client bytes: worked
examples of reconstructed/charsel/charsel_gfx.c through the validator's ctypes side.  The instruction
comparison is scripts/validate_charsel_gfx.py (private, MU_RECOVERY_INTEGRATION=1 with Unicorn)."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('validate_charsel_gfx', ROOT / 'scripts/validate_charsel_gfx.py')
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)


def record(live=1, cls=1, flags=0, guild=0xff, level=400, name='Nighty', key=0):
    r = bytearray(V.RECORD)
    r[V.OBJECT] = live
    r[0x12], r[0x14], r[0x17], r[0x3e] = cls, flags, guild, key
    struct.pack_into('<H', r, 0x144, level)
    b = name.encode()
    r[0x3658:0x3658 + len(b)] = b
    struct.pack_into('<II', r, 0x3658 + 0x10, len(b), 15)
    return bytes(r)


def case(records, slots=None, **kw):
    c = {'records': records, 'slots': slots or list(range(10)), 'row': 0, 'count': 10, 'selected': -1,
         'shown': -1, 'slot_mode': 0, 'slot_limit': 10, 'enter_refused': 0, 'gfx_busy': 0, 'flag_79': 0,
         'base_ready': 1}
    c.update(kw)
    for i in c['slots']:
        c['records'].setdefault(i, record(live=0, key=i))
    return c


class CharselGfxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = V.load_library()

    def run_family(self, c, family, args=None):
        return V.CSide(self.lib, c).run(family, args or {})

    def rows(self, out):
        line = next(x for x in out['lines'] if x.startswith('invoke SetSelectText '))
        return json.loads(line[len('invoke SetSelectText '):])[0]

    def test_list_rows(self):
        out = self.run_family(case({0: record(name='a<b', key=0), 2: record(cls=0x22, guild=0x80, level=7, key=2,
                                                                             flags=1)}), 'list')
        rows = self.rows(out)
        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[0], {'type': 0, 'index': 0, 'textJob': 'CLASS1', 'textState': 'GT488',
                                   'textName': "<font color='#FFCC19'>a&lt;b</font><br>",
                                   'textLevel': "<font color='#FFCC19'>400</font><br>"})
        self.assertEqual(rows[1], {'type': 1, 'textCreat': 'GT5220'})
        self.assertEqual((rows[2]['textJob'], rows[2]['textState']), ('CLASS34', 'GT1300'))
        # the dead name colour: only its "webzen" test is a call, and only without flags
        self.assertEqual([x for x in out['lines'] if x.startswith('call')], ['call 0129debb r0'])

    def test_locked_rows(self):
        rows = self.rows(self.run_family(case({}, slot_mode=1, slot_limit=5), 'list'))
        self.assertEqual([r['type'] for r in rows], [1] * 5 + [2] * 5)
        self.assertEqual(rows[9]['textCreat'], 'GT5221')

    def test_select_and_enter(self):
        out = self.run_family(case({3: record(key=3)}), 'select', {'row': 3, 'enter': 1})
        self.assertEqual((out['selected'], out['shown'], out['row']), (3, 3, 3))
        self.assertEqual(out['lines'], ['call 009a4dd7', 'call 009a5029 3', 'call 0185a75a 0',
                                        'invoke SetCharSelArrow []'])
        refused = self.run_family(case({3: record(key=3)}, enter_refused=1), 'select', {'row': 3, 'enter': 1})
        self.assertNotIn('call 0185a75a 0', refused['lines'])

    def test_empty_row_opens_create(self):
        out = self.run_family(case({}, selected=4, shown=4), 'select', {'row': 6, 'enter': 0})
        self.assertEqual((out['selected'], out['shown']), (-1, -1))
        self.assertIn('call 00b49bf4 1', out['lines'])
        self.assertEqual(self.run_family(case({}), 'select', {'row': 10, 'enter': 1})['lines'], [])

    def test_arrow_moves_the_character(self):
        out = self.run_family(case({0: record(key=0), 1: record(key=1, name='Two')}, row=1), 'arrow', {'up': 1})
        self.assertEqual(out['row'], 0)
        self.assertEqual(out['slots'][:2], [1, 0])
        self.assertIn('invoke SelectIndex [0]', out['lines'])

    def test_callbacks(self):
        c = case({3: record(key=3)})
        out = self.run_family(c, 'dispatch', {'name': 'OnCharSelectedDClick', 'values': [(3, 3.7)]})
        self.assertEqual(out['lines'][0], 'call 00aaf5d3 OnCharSelectedDClick')
        self.assertIn('call 0185a75a 0', out['lines'])
        busy = self.run_family(case({}, gfx_busy=1, flag_79=1), 'dispatch',
                               {'name': 'OnCharSelectedClick', 'values': [(3, 0.0)]})
        self.assertEqual(busy['lines'], [])

    def test_init(self):
        out = self.run_family(case({}), 'init')
        methods = [x.split(' ')[1] for x in out['lines']]
        self.assertEqual(methods, ['00aadbc3', 'SetInputBoxLength', 'InitText', 'InitStat', 'SetInputBoxLength',
                                   'InitClassInfo', 'SetClassInfo', 'SetnumViewableSelctedWin'])
        text = json.loads(out['lines'][2][len('invoke InitText '):])[0]
        self.assertEqual(text['MoveCharText'], "<font color='#ffc8b4'>GT1241\nGT1242\nGT1243</font>")
        classes = json.loads(out['lines'][5][len('invoke InitClassInfo '):])[0]
        self.assertEqual(len(classes), 16)
        self.assertEqual(classes[6]['Charisma'], 25)
        self.assertEqual(self.run_family(case({}, base_ready=0), 'init')['ret'], 0)

    def test_html_helpers(self):
        self.assertEqual(V.html('x', 99, 1), "<font color='#FFFFFF'><b>x</b></font><br>")
        self.assertEqual(V.html('\n', 3, 0), '')


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private: MU_RECOVERY_INTEGRATION=1')
class PrivateCharselGfxValidation(unittest.TestCase):
    def test_instruction_comparison(self):
        try:
            import unicorn  # noqa: F401
        except ImportError:
            self.skipTest('unicorn is not installed')
        if not V.EVIDENCE.joinpath('x86-text-capture-09/client-text.bin').exists():
            self.skipTest('pinned evidence missing')
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_charsel_gfx.py'), '--cases', '60',
                            '--mutations'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main()
