"""Portable checks of reconstructed/movement (NATIVE-WORLD-001).

Analytic statements of the client rules, independent of the client bytes. The
instruction-level comparison with the client is scripts/validate_movement.py;
its private run is gated by MU_RECOVERY_INTEGRATION. The path finder and its
independent reference statement moved to reconstructed/path (NATIVE-PATH-001).
"""
import ctypes
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


class Path_(ctypes.Structure):
    _fields_ = [('current', ctypes.c_uint8), ('current_float', ctypes.c_uint8), ('count', ctypes.c_uint8),
                ('x', ctypes.c_uint8 * 15), ('y', ctypes.c_uint8 * 15)]


class SpeedInput(ctypes.Structure):
    _fields_ = [('move_speed', ctypes.c_uint16), ('object_type', ctypes.c_int32), ('object_kind', ctypes.c_uint8),
                ('special_state', ctypes.c_uint8), ('helper_type', ctypes.c_uint16), ('mount_type', ctypes.c_int32),
                ('helper_option', ctypes.c_uint8), ('safe_zone', ctypes.c_uint8), ('subtype', ctypes.c_int32),
                ('mounted_item', ctypes.c_uint8), ('wing_type', ctypes.c_int16), ('transformed', ctypes.c_uint8),
                ('world_runs', ctypes.c_uint8), ('stunned', ctypes.c_uint8), ('buffs', ctypes.c_uint32),
                ('buff_18b_bonus', ctypes.c_double)]


class PositionInput(ctypes.Structure):
    _fields_ = [('speed', ctypes.c_float), ('world', ctypes.c_int32), ('helper_type', ctypes.c_uint16),
                ('safe_zone', ctypes.c_uint8), ('object_type', ctypes.c_int32),
                ('height', ctypes.POINTER(ctypes.c_float)), ('wall', ctypes.POINTER(ctypes.c_uint16)),
                ('special_height', ctypes.c_float), ('scene_state', ctypes.c_int32)]


def load():
    subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
    suffix = 'dylib' if sys.platform == 'darwin' else 'so'
    lib = ctypes.CDLL(str(HERE / f'libclient_movement.{suffix}'))
    F, I, U8, P = ctypes.c_float, ctypes.c_int32, ctypes.c_uint8, ctypes.POINTER
    for name, args, result in [
            ('mu_create_angle', [F, F, F, F], F), ('mu_far_angle', [F, F, U8], F), ('mu_turn_angle2', [F, F, F], F),
            ('mu_move_path', [P(Path_), P(I), P(F), P(F), U8], ctypes.c_int),
            ('mu_request_terrain_height', [P(F), P(ctypes.c_uint16), F, I, F, F], F),
            ('mu_character_move_speed', [P(SpeedInput), P(U8)], F),
            ('mu_move_character_position', [P(PositionInput), P(F), P(F), P(F)], None),
            ('mu_move_set_action', [P(ctypes.c_uint16), P(ctypes.c_uint16), P(F), P(F), I, I], ctypes.c_int),
            ('mu_player_walk_run', [U8, U8, I, U8], U8), ('mu_player_walk_action', [U8, U8, P(F)], I),
            ('mu_player_stop_action', [U8], I), ('mu_player_stop_speed', [I], F)]:
        function = getattr(lib, name)
        function.argtypes, function.restype = args, result
    return lib


def player_speed_input(**fields):
    s = SpeedInput(object_type=0xa91, object_kind=1, helper_type=0xffff, mount_type=0xffff, wing_type=-1)
    for key, value in fields.items():
        setattr(s, key, value)
    return s


class MovementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = load()

    def test_create_angle_axes_and_quadrants(self):
        a = self.lib.mu_create_angle
        self.assertEqual(a(0, 0, 0, -10), 0.0)      # |dx| tiny, dy < 0
        self.assertEqual(a(0, 0, 0, 10), 180.0)
        self.assertEqual(a(0, 0, -10, 0), 270.0)
        self.assertEqual(a(0, 0, 10, 0), 90.0)
        self.assertEqual(a(0, 0, 0.00005, 10), 180.0)   # below the 0.0001 threshold
        for dx, dy in [(3, 4), (-3, 4), (-3, -4), (3, -4)]:
            expected = f32(f32(f32(f32(math.atan(f32(dy / dx))) / f32(math.pi)) * 180) + 90)
            if dx < 0:
                expected = f32(expected + 180)
            self.assertEqual(a(0, 0, dx, dy), expected)

    def test_far_and_turn_angle(self):
        far, turn = self.lib.mu_far_angle, self.lib.mu_turn_angle2
        self.assertEqual(far(10, 350, 0), 20.0)    # across 0: the wrapped distance
        self.assertEqual(far(350, 10, 0), 20.0)
        self.assertEqual(far(90, 10, 0), -80.0)    # otherwise target - angle
        self.assertEqual(far(90, 10, 1), 80.0)
        self.assertEqual(far(-90, 90, 1), 180.0)
        self.assertEqual(turn(0, 90, 10), 10.0)
        self.assertEqual(turn(10, 350, 15), 355.0)   # through 0
        self.assertEqual(turn(80, 90, 15), 90.0)     # would pass the target
        self.assertEqual(turn(200, 100, 30), 170.0)

    def walk_path(self, cells, start, angle=0.0, limit=400, speed=12.0):
        p = Path_(0, 0, len(cells), (ctypes.c_uint8 * 15)(*[c[0] for c in cells]),
                  (ctypes.c_uint8 * 15)(*[c[1] for c in cells]))
        tile = (ctypes.c_int32 * 2)(*cells[0])
        pos = (ctypes.c_float * 3)(*start)
        ang = (ctypes.c_float * 3)(0.0, 0.0, angle)
        height = (ctypes.c_float * 65536)()
        wall = (ctypes.c_uint16 * 65536)()
        position_input = PositionInput(speed=speed, world=0, helper_type=0xffff, safe_zone=1, object_type=0xa91,
                                       height=height, wall=wall, special_height=0.0, scene_state=6)
        timer = ctypes.c_float(0.0)
        for step in range(limit):
            if self.lib.mu_move_path(ctypes.byref(p), tile, pos, ang, 1):
                return step, list(tile), list(pos), list(ang), timer.value
            self.lib.mu_move_character_position(ctypes.byref(position_input), pos, ang, ctypes.byref(timer))
        self.fail('never arrived')

    def test_straight_walk_arrives_at_the_cell_centre(self):
        cells = [(100, 100 + i) for i in range(6)]
        steps, tile, pos, ang, timer = self.walk_path(cells, (10050.0, 10050.0, 0.0), angle=180.0)
        self.assertEqual(tile, [100, 105])
        self.assertEqual(pos[:2], [10050.0, 10550.0])   # snapped to the last spline point
        self.assertEqual(ang[2], 180.0)                  # +y is heading 180 (velocity (0, -speed) rotated)
        self.assertTrue(38 <= steps <= 46, steps)         # 500 units at 12 per step, arrival radius 30
        self.assertAlmostEqual(timer, 0.15 * steps, delta=1e-3)

    def test_turning_walk_snaps_or_halves(self):
        cells = [(50, 50), (51, 50), (52, 51), (52, 52), (51, 53)]
        steps, tile, pos, _, _ = self.walk_path(cells, (5050.0, 5050.0, 0.0), angle=0.0)
        self.assertEqual(tile, [51, 53])
        self.assertEqual(pos[:2], [5150.0, 5350.0])

    def test_request_height_bilinear_and_special(self):
        height = (ctypes.c_float * 65536)()
        wall = (ctypes.c_uint16 * 65536)()
        for y in range(4):
            for x in range(4):
                height[y * 256 + x] = float(10 * x + 100 * y)
        r = self.lib.mu_request_terrain_height
        self.assertEqual(r(height, wall, 7.0, 6, 150.0, 250.0), 265.0)
        self.assertEqual(r(height, wall, 7.0, 2, 150.0, 250.0), 0.0)   # scene 1, 2, 4: 0
        self.assertEqual(r(height, wall, 7.0, 6, -1.0, 250.0), 0.0)
        self.assertEqual(r(height, wall, 7.0, 6, 30000.0, 30000.0), 7.0)   # index >= 0x10000
        wall[2 * 256 + 1] = 0x40
        self.assertEqual(r(height, wall, 7.0, 6, 150.0, 250.0), 7.0)

    def test_move_speed(self):
        speed = self.lib.mu_character_move_speed
        for run, expected in [(0, 12.0), (39, 12.0), (40, 15.0)]:
            r = ctypes.c_uint8(run)
            self.assertEqual(speed(ctypes.byref(player_speed_input()), ctypes.byref(r)), expected)
        r = ctypes.c_uint8(0)
        self.assertEqual(speed(ctypes.byref(player_speed_input(wing_type=0x1800)), ctypes.byref(r)), 15.0)
        self.assertEqual(r.value, 40)   # wings outside a safe zone set the run counter
        r = ctypes.c_uint8(0)
        self.assertEqual(speed(ctypes.byref(player_speed_input(wing_type=0x1800, safe_zone=1)), ctypes.byref(r)), 12.0)
        r = ctypes.c_uint8(25)
        self.assertEqual(speed(ctypes.byref(player_speed_input(helper_type=0x1a25, helper_option=1)),
                               ctypes.byref(r)), 19.0)
        r = ctypes.c_uint8(0)
        self.assertEqual(speed(ctypes.byref(player_speed_input(buffs=1 << 1)), ctypes.byref(r)), 6.0)
        r = ctypes.c_uint8(0)
        self.assertEqual(speed(ctypes.byref(SpeedInput(move_speed=7, object_type=5)), ctypes.byref(r)), 7.0)

    def test_set_action(self):
        a, b = ctypes.c_uint16(1), ctypes.c_uint16(0)
        f, g = ctypes.c_float(3.5), ctypes.c_float(1.0)
        self.assertEqual(self.lib.mu_move_set_action(a, b, f, g, 0x186, 0x32), 1)
        self.assertEqual((a.value, b.value, f.value, g.value), (0x32, 1, 0.0, 3.5))
        self.assertEqual(self.lib.mu_move_set_action(a, b, f, g, 0x186, 0x32), 0)   # same action: unchanged
        self.assertEqual(self.lib.mu_move_set_action(a, b, f, g, 0x186, 0x186), 0)  # out of range

    def test_minimal_walk_and_stand_tables(self):
        speed = ctypes.c_float()
        self.assertEqual(self.lib.mu_player_walk_run(0x03, 1, 0, 39), 0)      # safe zone resets
        self.assertEqual(self.lib.mu_player_walk_run(0x03, 0, 0, 39), 40)     # class 3 grows
        self.assertEqual(self.lib.mu_player_walk_run(0x01, 0, 0, 10), 10)     # class 1 does not
        self.assertEqual(self.lib.mu_player_walk_run(0x03, 1, 0x84, 10), 11)  # world 0x84 keeps growing
        self.assertEqual(self.lib.mu_player_walk_action(0x01, 0, ctypes.byref(speed)), 0x32)
        self.assertAlmostEqual(speed.value, 0.33, places=6)
        self.assertEqual(self.lib.mu_player_walk_action(0x22, 0, ctypes.byref(speed)), 0x33)
        self.assertEqual(self.lib.mu_player_walk_action(0x06, 40, ctypes.byref(speed)), 0x4f)
        self.assertAlmostEqual(speed.value, 0.28, places=6)
        self.assertEqual(self.lib.mu_player_walk_action(0x0b, 40, ctypes.byref(speed)), 0x63)
        self.assertEqual([self.lib.mu_player_stop_action(c) for c in range(16)],
                         [1, 1, 2, 1, 1, 3, 1, 5, 6, 6, 1, 1, 2, 1, 6, 8])
        self.assertAlmostEqual(self.lib.mu_player_stop_speed(1), 0.28, places=6)
        self.assertAlmostEqual(self.lib.mu_player_stop_speed(3), 0.24, places=6)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private pinned client captures')
    def test_instruction_comparison(self):
        text = os.environ.get('MU_CLIENT_TEXT', str(ROOT / 'evidence/x86-text-capture-09/client-text.bin'))
        data = os.environ.get('MU_IMAGE_DATA',
                              str(ROOT / 'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'movement.json'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_movement.py'), '--text', text,
                                     '--data', data, '--cases', '60', '--mutations', '--output', str(report)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
            parsed = json.loads(report.read_text())
        self.assertTrue(all(r['mismatches'] == 0 for r in parsed['results'].values()))
        self.assertTrue(all(m['mismatches'] > 0 for m in parsed['mutations']))


if __name__ == '__main__':
    unittest.main()
