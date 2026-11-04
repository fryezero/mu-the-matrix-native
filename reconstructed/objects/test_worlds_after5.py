"""RENDER-WORLDS-AFTER5: the object action registry 0x01ec7d5c (portable synthetic checks) and the private
instruction comparison (validate_worlds_after5)."""
import ctypes as C
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_object_render as v  # noqa: E402
import validate_worlds_after5 as wa5  # noqa: E402
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
LANG_DIR = os.environ.get('MU_ANIM_LANG_DIR')   # optional: a local lang dir with mapanim.tsv (live_rows)


def row(kind, action, speed, handler, param=300, extra=()):
    return {'type': kind, 'action': action, 'speed': v.f32(speed), 'handler': handler, 'param': param,
            'extra': list(extra)}


class WorldsAfter5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = wa5.build(ROOT / 'reconstructed')

    def run_case(self, call, entries, kind=13, current=0, frame=0.0, action=0, records=((20, 0), (10, 0)),
                 hero=(0.0, 0.0), loops=(0, 0), seed=1, model=True):
        obj = bytearray(v.OBJ_SIZE)
        struct.pack_into('<i', obj, 0x5c, kind)
        struct.pack_into('<H', obj, 0x2a, current)
        struct.pack_into('<f', obj, 0xd0, frame)
        struct.pack_into('<f', obj, 0xbc, 0.16)
        struct.pack_into('<ii', obj, 0x30, *loops)
        struct.pack_into('<2f', obj, 0x158, 1000.0, 1000.0)
        case = {'type': kind, 'count': len(records), 'records': list(records), 'action': action,
                'entries': entries, 'has_model': model, 'object': bytes(obj), 'hero': list(hero), 'seed': seed}
        status, found, out, _ = wa5.native(self.lib, case, call)
        get = lambda fmt, off: struct.unpack_from(fmt, out, off)[0]   # noqa: E731
        return status, found, {'velocity': get('<f', 0xbc), 'action': get('<H', 0x2a), 'prior': get('<H', 0x2c),
                               'frame': get('<f', 0xd0), 'loops': get('<i', 0x30), 'limit': get('<i', 0x34),
                               'alpha_rate': get('<f', 0xe0)}

    def test_set_action_speed_and_switch(self):
        entries = [row(13, 0, 0.21, 2, extra=(6, 11, 1)), row(13, 1, 0.27, 2, extra=(1, 2, 0))]
        status, _, o = self.run_case('set', entries, action=0, seed=7)
        self.assertEqual(status, 1)
        self.assertEqual(o['velocity'], v.f32(0.21))
        rand = v.MsvcRand(7)
        self.assertEqual(o['limit'], 6 + rand() % 5)   # extra[0] + rand() % (extra[1] - extra[0])
        status, _, o = self.run_case('set', entries, current=0, frame=12.5, action=1)
        self.assertEqual((o['action'], o['prior'], o['frame'], o['velocity']), (1, 0, 0.0, v.f32(0.27)))

    def test_set_action_refusals(self):
        entries = [row(13, 0, 0.5, 0)]
        self.assertEqual(self.run_case('set', entries, model=False)[0], 0)
        self.assertEqual(self.run_case('set', entries, action=2)[0], 0)   # not below the action count
        status, _, o = self.run_case('set', [row(14, 0, 0.5, 0)], action=0)
        self.assertEqual((status, o['velocity']), (0, v.f32(0.16)))   # no entry for this type: speed kept

    def test_key_alias(self):
        # 1000 * action + type: type 1013 action 0 is the key of type 13 action 1
        status, _, o = self.run_case('set', [row(1013, 0, 0.4, 0)], kind=13, action=1)
        self.assertEqual((status, o['velocity']), (1, v.f32(0.4)))

    def test_alpha_rate_handler(self):
        status, _, o = self.run_case('set', [row(13, 0, 10.0, 8, extra=(830, 200, 770, 0, 0, 0, 7))])
        self.assertEqual((status, o['velocity'], o['alpha_rate']), (1, v.f32(0.16), v.f32(7 * v.f32(0.01))))

    def test_tick_end_of_action(self):
        entries = [row(66, 0, 0.16, 1, extra=(0, 1)), row(66, 1, 0.28, 1, extra=(1, 0))]
        status, found, o = self.run_case('tick', entries, kind=66, frame=20 - v.f32(0.16) - 0.01)
        self.assertEqual((found, o['action']), (1, 0))   # not yet at the end
        status, found, o = self.run_case('tick', entries, kind=66, frame=20 - v.f32(0.16))
        self.assertEqual((found, o['action'], o['velocity']), (1, 1, v.f32(0.28)))

    def test_tick_loops(self):
        entries = [row(13, 0, 0.21, 2, extra=(6, 11, 1)), row(13, 1, 0.27, 2, extra=(1, 2, 0))]
        _, _, o = self.run_case('tick', entries, frame=19.9, loops=(3, 6))
        self.assertEqual((o['action'], o['loops']), (0, 4))
        _, _, o = self.run_case('tick', entries, frame=19.9, loops=(6, 6), seed=3)
        self.assertEqual((o['action'], o['loops'], o['limit']), (1, 1, 1))   # SetAction(1) resets, then counts

    def test_tick_hero_distance(self):
        wake = [row(146, 0, 0.2, 7, 400, (0, 1)), row(146, 1, 0.16, 7, 400, (1, 2))]
        _, _, o = self.run_case('tick', wake, kind=146, hero=(1300.0, 1000.0))
        self.assertEqual(o['action'], 1)   # 400 > 300
        _, _, o = self.run_case('tick', wake, kind=146, hero=(1300.0, 1000.0), loops=(0, 1))
        self.assertEqual(o['action'], 0)   # latched
        _, _, o = self.run_case('tick', wake, kind=146, hero=(1500.0, 1000.0), loops=(0, 1))
        self.assertEqual((o['action'], o['limit']), (0, 0))   # far: the latch clears

    def test_tick_unported_handlers(self):
        for handler in (4, 6, 8):
            status, found, _ = self.run_case('tick', [row(13, 0, 0.16, handler, extra=(0, 1, 2, 3, 4, 5, 6))])
            self.assertEqual((status, found), (2, 1))

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-after5-orig-') as td:
            report = Path(td) / 'report.json'
            args = [sys.executable, str(ROOT / 'scripts/validate_worlds_after5.py'), '--cases', '3000',
                    '--mutations', '--output', str(report)] + (['--lang-dir', LANG_DIR] if LANG_DIR else [])
            subprocess.run(args, check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(result['families']['set_action']['cases'], 3000)
            self.assertEqual(result['families']['tick']['cases'], 3000)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), 29)
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))


if __name__ == '__main__':
    unittest.main()
