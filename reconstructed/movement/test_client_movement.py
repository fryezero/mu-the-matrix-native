"""Portable checks of reconstructed/movement (NATIVE-WORLD-001).

Analytic statements of the client rules, independent of the client bytes. The
instruction-level comparison with the client is scripts/validate_movement.py;
its private run is gated by MU_RECOVERY_INTEGRATION.
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
            ('mu_player_stop_action', [U8], I), ('mu_player_stop_speed', [I], F),
            ('mu_path_finder_bytes', [], ctypes.c_uint32), ('mu_path_finder_init', [ctypes.c_void_p, ctypes.c_void_p], None),
            ('mu_path_finding2', [ctypes.c_void_p, I, I, I, I, P(Path_), F, I, U8, ctypes.c_void_p, ctypes.c_void_p],
             ctypes.c_int)]:
        function = getattr(lib, name)
        function.argtypes, function.restype = args, result
    return lib


def player_speed_input(**fields):
    s = SpeedInput(object_type=0xa91, object_kind=1, helper_type=0xffff, mount_type=0xffff, wing_type=-1)
    for key, value in fields.items():
        setattr(s, key, value)
    return s


DIRECTIONS = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]


def reference_find(walls, sx, sy, tx, ty, error_check, wall, directions, limit=500, mask=0x1e):
    """Independent statement of FindPath 0x012b1c45 (distance 0): returns the path or None."""
    import heapq
    if sx == 0 or sy == 0:
        return None
    target = ty * 256 + tx
    if not 0 <= target < 65536:
        return None
    if error_check and not wall > walls[target] and not walls[target] & 0x20:
        return None
    state, cost, prev = {target: 4}, {}, {}
    start = sy * 256 + sx
    state[start] = state.get(start, 0) | 1
    heap, seq = [(0, 0, start)], 1
    best, best_xy = 0x743aa380, (sx, sy)

    def h(x, y):
        a, b = abs(x - tx), abs(y - ty)
        return (abs(a - b) * 5 + min(a, b) * 7 + 1) * 3 // 4

    for left in range(limit, 0, -1):
        if not heap:
            break
        _, _, c = heapq.heappop(heap)
        x, y = c % 256, c // 256
        cost[c] = 0 if left == limit else 0x743aa380
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < 256 and 0 <= ny < 256 and state.get(ny * 256 + nx, 0) & 2:
                candidate = (7 if dx and dy else 5) + cost[ny * 256 + nx]
                if candidate < cost[c]:
                    cost[c], prev[c] = candidate, (nx, ny)
        state[c] = state.get(c, 0) | 2
        if state[c] & 4:
            best_xy = (x, y)
            break
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < 256 and 0 <= ny < 256):
                continue
            n = ny * 256 + nx
            if state.get(n, 0) & 1 or not wall > (walls[n] & mask):
                continue
            heapq.heappush(heap, (h(nx, ny) + cost[c], seq, n))
            seq += 1
            state[n] = state.get(n, 0) | 1
            prev[n] = (x, y)
        if not error_check and h(x, y) < best:
            best, best_xy = h(x, y), (x, y)
    else:
        if error_check:
            return None
    if error_check and not state.get(best_xy[1] * 256 + best_xy[0], 0) & 4:
        return None
    path, (x, y) = [], best_xy
    while len(path) < 500:
        path.append((x, y))
        if (x, y) == (sx, sy):
            return path[::-1]
        x, y = prev[y * 256 + x]
    return None


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

    def path_finding2(self, walls, sx, sy, tx, ty, wall=2, directions=DIRECTIONS):
        finder = ctypes.create_string_buffer(self.lib.mu_path_finder_bytes())
        grid = (ctypes.c_uint16 * 65536)(*walls)
        self.lib.mu_path_finder_init(finder, grid)
        table = (ctypes.c_int32 * 16)(*[v for pair in directions for v in pair])
        path = Path_()
        found = self.lib.mu_path_finding2(finder, sx, sy, tx, ty, ctypes.byref(path), 0.0, wall, 0, table, None)
        return found, [(path.x[i], path.y[i]) for i in range(path.count)]

    def test_path_finder_open_ground_and_walls(self):
        walls = [0] * 65536
        found, cells = self.path_finding2(walls, 100, 100, 104, 102)
        self.assertEqual(found, 1)
        self.assertEqual((cells[0], cells[-1], len(cells)), ((100, 100), (104, 102), 5))
        for x in range(90, 111):        # a wall with a gap at x = 111
            walls[105 * 256 + x] = 4
        found, cells = self.path_finding2(walls, 100, 100, 100, 110)
        self.assertEqual(found, 1)
        self.assertTrue(all(walls[y * 256 + x] == 0 for x, y in cells))
        self.assertEqual(len(cells), 15)   # the first 15 cells of a longer path
        walls[120 * 256 + 120] = 4         # blocked target: the closest reachable cell instead
        found, cells = self.path_finding2(walls, 116, 120, 120, 120)
        self.assertEqual((found, cells[-1]), (1, (119, 120)))
        found, cells = self.path_finding2(walls, 100, 100, 100, 100)
        self.assertEqual(found, 0)         # a one-cell path does not move

    def test_path_finder_equals_the_reference_statement(self):
        import random
        g = random.Random(7)
        for case in range(40):
            walls = [0] * 65536
            for _ in range(60):
                x0, y0 = g.randint(60, 190), g.randint(60, 190)
                value = g.choice([4, 4, 1, 2, 0x20, 0x40])
                for y in range(y0, y0 + g.randint(1, 8)):
                    for x in range(x0, x0 + g.randint(1, 8)):
                        walls[y * 256 + x] = value
            sx, sy = g.randint(80, 170), g.randint(80, 170)
            tx, ty = sx + g.randint(-16, 16), sy + g.randint(-16, 16)
            directions = g.choice([DIRECTIONS, DIRECTIONS[::-1], DIRECTIONS[2:] + DIRECTIONS[:2]])
            wall = g.choice([2, 4])
            expected = reference_find(walls, sx, sy, tx, ty, 1, wall, directions)
            if expected is None:
                start, goal = walls[sy * 256 + sx], walls[ty * 256 + tx]
                second = 4 if (start & 1) or ((goal & 1) and not goal & 2) else wall
                expected = reference_find(walls, sx, sy, tx, ty, 0, second, directions)
            found, cells = self.path_finding2(walls, sx, sy, tx, ty, wall, directions)
            if expected is None or len(expected) <= 1:
                self.assertEqual(found, 0, case)
            else:
                self.assertEqual((found, cells), (1, expected[:15]), case)

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
