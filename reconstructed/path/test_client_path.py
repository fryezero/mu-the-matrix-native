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


# Moved from reconstructed/movement/test_client_movement.py (NATIVE-WORLD-001): an independent
# Python statement of FindPath (distance 0) with an arbitrary neighbour order.
OTHER_DIRECTIONS = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]


def reference_find(walls, sx, sy, tx, ty, error_check, wall, directions, limit=500, mask=0x1e, trim=False):
    """Independent statement of FindPath 0x012b1c45 (distance 0): returns the path or None. trim: BuildPath's
    variant for budgets above 500 (NATIVE-PATH-002): a target reached by n >= 500 nodes keeps the 499 nodes
    nearest the start."""
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
            if trim:
                chain, (px, py) = [(x, y)], (x, y)
                while (px, py) != (sx, sy):
                    px, py = prev[py * 256 + px]
                    chain.append((px, py))
                if len(chain) >= 500:
                    best_xy = chain[len(chain) - 499]
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

    def test_retry_level_needs_a_target_without_character(self):
        # 0x012b0f2c..0x012b0f7a: level 4 only when (start or target safe) and the target has no
        # character. A safe start with a character on the target keeps level 2.
        g = self.grid()
        g.set(150, 150, 0x01)
        for dx, dy in ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)):
            g.set(150 + dx, 150 + dy, 0x02)
        g.set(150, 156, 0x03)
        ok, nodes, _ = g.find2(150, 150, 150, 156)
        self.assertFalse(ok)          # level 2: the ring of characters is closed
        g.set(150, 156, 0x01)
        ok, nodes, _ = g.find2(150, 150, 150, 156)
        self.assertTrue(ok)           # level 4 passes the ring
        self.assertEqual(nodes[-1], (150, 156))

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
        self.assertGreaterEqual(len(parsed['families']), 15)


def corridor(rows=None):
    """A serpentine corridor (rows y = 2, 6, ..., joined alternately at x = 252 and x = 2)."""
    walls = [4] * 65536
    for row in range(2, 254, 4):
        if rows is not None and row > rows:
            break
        for x in range(2, 253):
            walls[row * 256 + x] = 0
        link = 252 if (row // 4) % 2 == 0 else 2
        for y in range(row, min(254, row + 5)):
            walls[y * 256 + link] = 0
    return walls


class LongPathTests(unittest.TestCase):
    """The long-distance helper 0x012b104c and the auto-move PATH_t methods (NATIVE-PATH-002)."""

    @classmethod
    def setUpClass(cls):
        cls.lib = V.load_library()

    def grid(self, cells=None):
        g = Grid(self.lib, cells)
        self.addCleanup(g.close)
        return g

    def auto(self):
        a = V.AutoPath()
        self.lib.mu_auto_path_init(ctypes.byref(a))
        return a

    def long(self, g, a, sx, sy, tx, ty, error_check=0, distance=0.0, level=4):
        ok = self.lib.mu_path_long(ctypes.byref(g.finder), sx, sy, tx, ty, error_check, ctypes.byref(a), distance,
                                   level)
        return ok, V.c_list(a)

    def test_init_and_reset(self):
        a = self.auto()
        self.assertEqual((a.target_x, a.target_y, a.waypoint_x, a.waypoint_y, a.flag, a.mode, a.list_count),
                         (-1, -1, -1, -1, 0, 0, 0))

    def test_short_path_is_listed_whole(self):
        g, a = self.grid(), self.auto()
        ok, nodes = self.long(g, a, 10, 10, 40, 20)
        self.assertEqual(ok, 1)
        self.assertEqual((nodes[0], nodes[-1], len(nodes)), ((10, 10), (40, 20), 31))
        self.assertEqual((a.target_x, a.target_y), (40, 20))

    def test_characters_do_not_block_but_walls_do(self):
        walls = [0] * 65536
        for y in range(0, 256):
            walls[y * 256 + 50] = 0x02          # a line of characters
        g, a = self.grid(walls), self.auto()
        ok, nodes = self.long(g, a, 40, 100, 60, 100)
        self.assertEqual((ok, len(nodes)), (1, 21))   # straight through (mask 0x1c)
        for y in range(0, 256):
            walls[y * 256 + 50] = 0x04
        g, a = self.grid(walls), self.auto()
        ok, nodes = self.long(g, a, 40, 100, 60, 100, error_check=1)
        self.assertEqual((ok, nodes), (0, []))      # the whole column blocks

    def test_long_corridor_keeps_499_nodes(self):
        walls = corridor()
        g, a = self.grid(walls), self.auto()
        ok, nodes = self.long(g, a, 3, 2, 3, 250)
        self.assertEqual(ok, 1)
        self.assertEqual(len(nodes), 499)
        self.assertEqual(nodes[0], (3, 2))
        self.assertEqual((a.target_x, a.target_y), (3, 250))      # the end tile is the target, not node 499
        self.assertTrue(all(max(abs(p[0] - q[0]), abs(p[1] - q[1])) == 1 for p, q in zip(nodes, nodes[1:])))
        self.assertTrue(all(walls[y * 256 + x] == 0 for x, y in nodes))
        expected = reference_find(walls, 3, 2, 3, 250, 0, 4, V.CLIENT_DIRECTIONS, limit=300000000, mask=0x1c,
                                  trim=True)
        self.assertEqual(nodes, expected)

    def test_unreachable_target(self):
        walls = [0] * 65536
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if max(abs(dx), abs(dy)) == 2:
                    walls[(100 + dy) * 256 + 100 + dx] = 8
        g, a = self.grid(walls), self.auto()
        ok, nodes = self.long(g, a, 60, 100, 100, 100, error_check=1)
        self.assertEqual((ok, nodes), (0, []))
        ok, nodes = self.long(g, a, 60, 100, 100, 100, error_check=0)
        self.assertEqual(ok, 1)
        self.assertEqual(nodes[-1], (a.target_x, a.target_y))
        self.assertEqual(max(abs(nodes[-1][0] - 100), abs(nodes[-1][1] - 100)), 3)   # just outside the ring
        ok, nodes = self.long(g, a, 60, 100, 100, -1)
        self.assertEqual((ok, nodes), (0, []))      # negative target: refused, list cleared

    def test_long_search_equals_the_reference_statement(self):
        import random
        r = random.Random(11)
        for case in range(25):
            walls = [0] * 65536
            for _ in range(80):
                x0, y0 = r.randint(20, 230), r.randint(20, 230)
                value = r.choice([4, 8, 0x10, 2, 0x22, 1])
                for y in range(y0, y0 + r.randint(1, 10)):
                    for x in range(x0, x0 + r.randint(1, 10)):
                        walls[y * 256 + x] = value
            sx, sy = r.randint(30, 220), r.randint(30, 220)
            tx, ty = r.randint(30, 220), r.randint(30, 220)
            walls[sy * 256 + sx] = 0
            error_check = r.choice([0, 1])
            g, a = self.grid(walls), self.auto()
            ok, nodes = self.long(g, a, sx, sy, tx, ty, error_check)
            expected = reference_find(walls, sx, sy, tx, ty, error_check, 4, V.CLIENT_DIRECTIONS, limit=300000000,
                                      mask=0x1c, trim=True)
            if expected is None:
                self.assertEqual(ok, 0, case)
            else:
                self.assertEqual((ok, nodes if len(expected) > 1 else []), (1, expected if len(expected) > 1 else []),
                                 case)

    def test_segments_of_three(self):
        g, a = self.grid(), self.auto()
        self.long(g, a, 10, 10, 17, 10)                 # 8 nodes
        taken = []
        while self.lib.mu_auto_path_next(ctypes.byref(a)):
            taken.append([(a.path.x[i], a.path.y[i]) for i in range(a.path.count)])
            self.assertEqual((a.path.current, a.path.current_float), (0, 0))
            self.assertEqual((a.waypoint_x, a.waypoint_y), taken[-1][-1])
        self.assertEqual([len(t) for t in taken], [3, 3, 2])
        self.assertEqual([p for t in taken for p in t], [(x, 10) for x in range(10, 18)])

    def test_start_flags_and_effects(self):
        g, a = self.grid(), self.auto()
        e = V.AutoEffects()
        start = self.lib.mu_auto_path_start
        self.assertEqual(start(ctypes.byref(a), ctypes.byref(g.finder), 1, 10, 10, 30, 30, 2, 0, ctypes.byref(e)), 0)
        self.assertEqual((a.flag, a.target_x, a.target_y, a.list_count), (1, 30, 30, 0))   # armed only
        self.assertEqual(start(ctypes.byref(a), ctypes.byref(g.finder), 2, 30, 30, 30, 30, 2, 0, ctypes.byref(e)), 0)
        self.assertTrue(e.arrived)
        self.assertEqual(start(ctypes.byref(a), ctypes.byref(g.finder), 2, 10, 10, 30, 30, 2, 0, ctypes.byref(e)), 1)
        self.assertEqual((e.target_set, list(e.target), e.selection_cleared), (1, [12, 12], 1))
        self.assertEqual((a.path.count, a.list_count, a.flag, a.mode), (3, 18, 2, 2))
        walls = [0] * 65536
        walls[50 * 256 + 50] = 4
        g = self.grid(walls)
        self.assertEqual(start(ctypes.byref(a), ctypes.byref(g.finder), 2, 10, 10, 50, 50, 2, 1, ctypes.byref(e)), 0)
        self.assertTrue(e.failure_notice)               # mode 2 failure: notice, then reset
        self.assertEqual((a.flag, a.target_x, a.mode), (0, -1, 0))
        self.lib.mu_auto_path_init(ctypes.byref(a))
        a.mode = 4
        self.lib.mu_auto_path_arrive(ctypes.byref(a))
        self.assertEqual(a.mode, 4)                     # modes 4 and 5 keep their state on arrival
        a.mode = 2
        self.lib.mu_auto_path_arrive(ctypes.byref(a))
        self.assertEqual(a.mode, 0)

    def test_refresh_fills_the_list_without_a_segment(self):
        g, a = self.grid(), self.auto()
        e = V.AutoEffects()
        a.waypoint_x, a.waypoint_y = 7, 8
        self.lib.mu_auto_path_refresh(ctypes.byref(a), ctypes.byref(g.finder), 10, 10, 20, 10, ctypes.byref(e))
        self.assertEqual((a.list_count, a.path.count, list(e.target), e.target_set), (11, 0, [7, 8], 1))


class ReferenceStatementTests(unittest.TestCase):
    """The NATIVE-WORLD-001 reference statement of FindPath against this port, with neighbour orders
    other than the client's table (the finder's `directions`)."""

    @classmethod
    def setUpClass(cls):
        cls.lib = V.load_library()

    def path_finding2(self, walls, sx, sy, tx, ty, wall=2, directions=OTHER_DIRECTIONS):
        g = Grid(self.lib, walls)
        self.addCleanup(g.close)
        table = (ctypes.c_int32 * 16)(*[v for pair in directions for v in pair])
        g.finder.directions = ctypes.addressof(table)
        found, cells, _ = g.find2(sx, sy, tx, ty, level=wall)
        return found, cells

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
        for case in range(60):
            walls = [0] * 65536
            for _ in range(60):
                x0, y0 = g.randint(60, 190), g.randint(60, 190)
                value = g.choice([4, 4, 1, 2, 3, 0x20, 0x40])
                for y in range(y0, y0 + g.randint(1, 8)):
                    for x in range(x0, x0 + g.randint(1, 8)):
                        walls[y * 256 + x] = value
            sx, sy = g.randint(80, 170), g.randint(80, 170)
            tx, ty = sx + g.randint(-16, 16), sy + g.randint(-16, 16)
            directions = g.choice([OTHER_DIRECTIONS, OTHER_DIRECTIONS[::-1], OTHER_DIRECTIONS[2:] + OTHER_DIRECTIONS[:2],
                                   [tuple(d) for d in V.CLIENT_DIRECTIONS]])
            wall = g.choice([2, 4])
            expected = reference_find(walls, sx, sy, tx, ty, 1, wall, directions)
            if expected is None:
                # 0x012b0f2c..0x012b0f7a: level 4 when (start or target safe) and no character on the target
                start, goal = walls[sy * 256 + sx], walls[ty * 256 + tx]
                second = 4 if ((start & 1) or (goal & 1)) and not goal & 2 else wall
                expected = reference_find(walls, sx, sy, tx, ty, 0, second, directions)
            found, cells = self.path_finding2(walls, sx, sy, tx, ty, wall, directions)
            if expected is None or len(expected) <= 1:
                self.assertEqual(found, 0, case)
            else:
                self.assertEqual((found, cells), (1, expected[:15]), case)


if __name__ == '__main__':
    unittest.main()
