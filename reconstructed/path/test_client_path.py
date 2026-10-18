"""Portable checks of the reconstructed click-to-move path finding and path
following (no client bytes). The instruction comparison against the client is
scripts/validate_path.py; its private run is gated by MU_RECOVERY_INTEGRATION."""
import ctypes
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('validate_path', ROOT / 'scripts/validate_path.py')
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


class Grid:
    def __init__(self, lib, cells=None):
        self.lib = lib
        self.wall = (ctypes.c_uint16 * 65536)(*(cells or [0] * 65536))
        self.objects = (ctypes.c_uint32 * 65536)()
        self.finder = V.Finder()
        assert lib.mu_path_finder_init(ctypes.byref(self.finder), 256, 256, self.wall, self.objects) == 0

    def close(self):
        self.lib.mu_path_finder_free(ctypes.byref(self.finder))

    def set(self, x, y, value):
        self.wall[y * 256 + x] = value

    def find2(self, sx, sy, tx, ty, distance=0.0, level=2, siege=0):
        path = V.ClientPath()
        ok = self.lib.mu_path_finding2(ctypes.byref(self.finder), sx, sy, tx, ty, ctypes.byref(path), distance, level,
                                       siege)
        nodes = [(path.x[i], path.y[i]) for i in range(path.count)] if ok else []
        return ok, nodes, path

    def find(self, sx, sy, tx, ty, error_check=1, level=2, distance=0.0, budget=500, mask=0x1e):
        ok = self.lib.mu_path_find(ctypes.byref(self.finder), sx, sy, tx, ty, error_check, level, 0, distance, budget,
                                   mask)
        f = self.finder
        nodes = [(f.path_x[500 - f.count + i], f.path_y[500 - f.count + i]) for i in range(f.count)] if ok else []
        return ok, nodes


def heuristic(tx, ty, x, y):
    dx, dy = abs(x - tx), abs(y - ty)
    v = (abs(dx - dy) * 5 + min(dx, dy) * 7 + 1) * 3
    return v // 4


class PathFinderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = V.load_library()

    def grid(self, cells=None):
        g = Grid(self.lib, cells)
        self.addCleanup(g.close)
        return g

    def test_heuristic_and_step_cost(self):
        for tx, ty, x, y in [(0, 0, 0, 0), (10, 10, 13, 10), (10, 10, 13, 17), (5, 9, 0, 0), (200, 3, 7, 250)]:
            self.assertEqual(self.lib.mu_path_heuristic(tx, ty, x, y), heuristic(tx, ty, x, y))
        self.assertEqual(self.lib.mu_path_heuristic(0, 0, 0, 0), 0)        # (0 + 0 + 1) * 3 / 4
        self.assertEqual(self.lib.mu_path_heuristic(0, 0, 1, 0), 4)        # 18 / 4
        self.assertEqual(self.lib.mu_path_step_cost(1, 1), 7)
        self.assertEqual(self.lib.mu_path_step_cost(0, -1), 5)
        self.assertEqual(self.lib.mu_path_step_cost(0, 0), 5)

    def test_straight_and_diagonal_paths_on_open_ground(self):
        g = self.grid()
        ok, nodes, path = g.find2(10, 10, 20, 10)
        self.assertTrue(ok)
        self.assertEqual(nodes, [(x, 10) for x in range(10, 21)])
        self.assertEqual((path.current, path.current_float), (0, 0))
        ok, nodes, _ = g.find2(10, 10, 17, 17)
        self.assertEqual(nodes, [(10 + i, 10 + i) for i in range(8)])
        ok, nodes, _ = g.find2(10, 10, 10, 10)   # a one-node path does not start a walk
        self.assertFalse(ok)

    def test_fifteen_node_cap(self):
        g = self.grid()
        ok, nodes, path = g.find2(30, 30, 30, 60)
        self.assertTrue(ok)
        self.assertEqual(path.count, 15)
        self.assertEqual(nodes[0], (30, 30))
        self.assertEqual(nodes[-1], (30, 44))
        self.assertEqual(g.finder.count, 31)    # BuildPath keeps the whole path

    def test_zero_coordinate_start_is_refused(self):
        g = self.grid()
        self.assertFalse(g.find2(0, 10, 5, 10)[0])
        self.assertFalse(g.find2(10, 0, 5, 10)[0])

    def test_walls_block_and_the_detour_is_found(self):
        g = self.grid()
        for y in range(5, 30):
            g.set(20, y, 0x04)
        ok, nodes, _ = g.find2(15, 15, 24, 15)
        self.assertTrue(ok)
        self.assertNotIn((20, 15), nodes)
        for x, y in nodes:
            self.assertLess(g.wall[y * 256 + x] & 0x1e, 2)

    def test_unreachable_target_walks_to_the_closest_explored_tile(self):
        g = self.grid()
        for x in range(45, 56):
            for y in range(45, 56):
                if x in (45, 55) or y in (45, 55):
                    g.set(x, y, 0x04)
        # error-checked search fails (the target is enclosed) ...
        self.assertFalse(g.find(40, 50, 50, 50)[0])
        # ... and PathFinding2's second search returns the path to the explored tile with
        # the smallest heuristic: the wall face next to the target
        ok, nodes, _ = g.find2(40, 50, 50, 50)
        self.assertTrue(ok)
        self.assertEqual(nodes[-1], (44, 50))

    def test_blocked_target_tile_fails_the_error_check_but_not_the_retry(self):
        g = self.grid()
        g.set(60, 60, 0x04)
        self.assertFalse(g.find(55, 60, 60, 60)[0])
        ok, nodes, _ = g.find2(55, 60, 60, 60)
        self.assertTrue(ok)
        self.assertEqual(nodes[-1], (59, 60))
        # the error check compares the whole attribute value with the level: a walkable tile
        # with a high bit (0x40) fails it unless it is an action tile (0x20) ...
        g.set(60, 60, 0x40)
        self.assertFalse(g.find(55, 60, 60, 60)[0])
        g.set(60, 60, 0x60)
        self.assertTrue(g.find(55, 60, 60, 60)[0])
        # ... and the second search reaches it exactly
        g.set(60, 60, 0x40)
        self.assertEqual(g.find2(55, 60, 60, 60)[1][-1], (60, 60))

    def test_safe_zone_retry_passes_through_characters(self):
        g = self.grid()
        for x in range(95, 106):
            for y in range(95, 106):
                g.set(x, y, 0x01)
        for x in range(97, 104):
            for y in range(97, 104):
                if x in (97, 103) or y in (97, 103):
                    g.set(x, y, 0x03)   # safe zone + character ring
        ok, nodes = g.find(100, 100, 110, 100, error_check=1, level=2)
        self.assertFalse(ok)
        ok, nodes, _ = g.find2(100, 100, 110, 100)
        self.assertTrue(ok)
        self.assertIn((103, 100), nodes)   # level 4: through the character tile
        # outside a safe zone the retry keeps level 2 and stops at the ring
        for x in range(95, 106):
            for y in range(95, 106):
                g.set(x, y, g.wall[y * 256 + x] & ~1)
        ok, nodes, _ = g.find2(100, 100, 110, 100)
        self.assertNotIn((103, 100), nodes)

    def test_distance_targets(self):
        g = self.grid()
        ok, nodes, _ = g.find2(70, 70, 80, 70, distance=1.0)
        self.assertTrue(ok)
        self.assertEqual(nodes[-1], (79, 70))   # first popped tile of the plus-shaped target set
        ok, nodes, _ = g.find2(70, 70, 80, 80, distance=f32(math.sqrt(8)))
        self.assertTrue(ok)
        self.assertEqual(nodes[-1], (79, 79))   # (78, 78) lies exactly at sqrt(8): not a target (>)

    def test_object_block_except_target(self):
        g = self.grid()
        for y in range(100, 140):
            g.objects[y * 256 + 130] = 1
        ok, nodes, _ = g.find2(125, 120, 135, 120)
        self.assertTrue(ok)
        self.assertNotIn((130, 120), nodes)
        ok, nodes, _ = g.find2(125, 120, 130, 120)
        self.assertEqual(nodes[-1], (130, 120))

    def test_search_budget_and_reset(self):
        g = self.grid([0x04] * 65536)
        for x in range(1, 255):
            g.set(x, 128, 0)
        ok, nodes, _ = g.find2(2, 128, 250, 128)   # 248 tiles: beyond the 15-node cap, within 500 pops
        self.assertTrue(ok)
        self.assertEqual(len(nodes), 15)
        marks = ctypes.string_at(g.finder.mark, 65536)
        self.assertTrue(any(marks))
        g.find2(2, 128, 3, 128)
        marks = ctypes.string_at(g.finder.mark, 65536)
        self.assertEqual(sum(1 for m in marks if m), 3)   # start, two neighbours: the old marks were cleared


class FollowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = V.load_library()

    def test_create_angle_axes_and_quadrants(self):
        a = self.lib.mu_path_create_angle
        self.assertEqual(a(0, 0, 0, 100), 180.0)
        self.assertEqual(a(0, 0, 0, -100), 0.0)
        self.assertEqual(a(0, 0, 100, 0), 90.0)
        self.assertEqual(a(0, 0, -100, 0), 270.0)
        self.assertEqual(a(0, 0, 100, 100), f32(f32(f32(f32(math.atan(1.0)) / f32(math.pi)) * 180) + 90))
        self.assertAlmostEqual(a(0, 0, -100, 100), 225.0, places=4)
        self.assertAlmostEqual(a(0, 0, -100, -100), 315.0, places=4)
        self.assertAlmostEqual(a(0, 0, 100, -100), 45.0, places=4)

    def test_angle_difference_and_turn(self):
        d, t = self.lib.mu_path_angle_difference, self.lib.mu_path_turn_angle
        self.assertEqual(d(10.0, 350.0, 1), 20.0)
        self.assertEqual(d(350.0, 10.0, 1), 20.0)
        self.assertEqual(d(90.0, 45.0, 0), -45.0)
        self.assertEqual(d(-90.0, 0.0, 1), 90.0)
        self.assertEqual(t(10.0, 90.0, 20.0), 30.0)
        self.assertEqual(t(10.0, 350.0, 5.0), 5.0)
        self.assertEqual(t(5.0, 350.0, 10.0), 355.0)
        self.assertEqual(t(200.0, 190.0, 20.0), 190.0)   # within the step: snaps

    def walk(self, xs, ys, speed=12.0, angle=0.0):
        m = V.Mover()
        m.path.count = len(xs)
        for i, (x, y) in enumerate(zip(xs, ys)):
            m.path.x[i], m.path.y[i] = x, y
        m.tile_x, m.tile_y = xs[0], ys[0]
        m.position[0], m.position[1] = (xs[0] + 0.5) * 100, (ys[0] + 0.5) * 100
        m.angle[2] = angle
        trace = []
        for step in range(1000):
            if self.lib.mu_path_move(ctypes.byref(m), 1, None):
                return step + 1, m, trace
            self.lib.mu_path_step_position(m.position, m.angle, speed)
            trace.append((m.position[0], m.position[1], m.angle[2], m.tile_x, m.tile_y))
        self.fail('no arrival')

    def test_straight_walk_arrives_snapped_with_speed_bound(self):
        xs, ys = list(range(10, 20)), [10] * 10
        steps, m, trace = self.walk(xs, ys, angle=90.0)
        self.assertEqual((m.tile_x, m.tile_y), (19, 10))
        self.assertEqual((m.position[0], m.position[1]), (1950.0, 1050.0))
        self.assertEqual(m.path.current, 9)
        # 900 units at 12 per 40 ms step, arrival within the last 30 units
        self.assertGreaterEqual(steps, 900 // 12 - 3)
        self.assertLessEqual(steps, 900 // 12 + 3)
        self.assertTrue(all(abs(a - 90.0) < 1e-3 for _, _, a, _, _ in trace))
        steps15, _, _ = self.walk(xs, ys, speed=15.0, angle=90.0)
        self.assertLess(steps15, steps)

    def test_walk_turns_toward_the_path(self):
        steps, m, trace = self.walk([10, 11, 12, 12, 12], [10, 10, 11, 12, 13], angle=0.0)
        self.assertEqual((m.tile_x, m.tile_y), (12, 13))
        self.assertGreater(len({round(a) for _, _, a, _, _ in trace}), 2)

    def test_logical_tile_leads_the_object(self):
        _, m, trace = self.walk(list(range(10, 16)), [10] * 6, angle=90.0)
        first = trace[0]
        self.assertEqual(first[3:], (11, 10))   # MovePath sets the next node on the first sub-target

    def test_character_bits(self):
        wall = (ctypes.c_uint16 * 65536)()
        wall[5], wall[6], wall[7] = 0x02, 0x03, 0x01
        self.lib.mu_path_clear_characters(wall, 65536)
        self.assertEqual((wall[5], wall[6], wall[7]), (0, 1, 1))
        self.lib.mu_path_stamp_character(wall, 256 + 3, 2)   # x & 255
        self.assertEqual(wall[2 * 256 + 3], 2)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private pinned client captures')
    def test_instruction_comparison(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'path.json'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_path.py'), '--cases', '80',
                                     '--mutations', '--output', str(report)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-2000:])
            parsed = json.loads(report.read_text())
        self.assertEqual(parsed['mismatches'], 0)
        self.assertTrue(all(m['mismatches'] > 0 for m in parsed['mutations']))
        self.assertGreaterEqual(len(parsed['families']), 9)


if __name__ == '__main__':
    unittest.main()
