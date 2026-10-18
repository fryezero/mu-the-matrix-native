"""Native click-to-move (NATIVE-PATH-001, NATIVE-PATH-002) checks.

Portable (synthetic attribute maps only): `mu-path find` on the built-in
synthetic maps (open ground, maze, safe zone with characters), the 15-node
client path, repeated clicks, render determinism and the PNG output, the batch
mode, the attribute dump refusing a missing game root, the run-counter rule (class, boots,
safe zone) and the long-distance auto move (NATIVE-PATH-002).
Private (MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT): the Lorencia attribute
dump, a walk in the Lorencia safe zone and a rendered path over the terrain.
The instruction-level comparison with the client is scripts/validate_path.py.
"""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

NATIVE = Path(__file__).resolve().parent.parent
TOOL = NATIVE / 'build/mu-path'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
GAME_ROOT = os.environ.get('MU_GAME_ROOT')


def run(*args, check=True):
    result = subprocess.run([str(TOOL), *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        raise AssertionError(result.stderr)
    return result


def find(*args):
    lines = run('find', *args).stdout.strip().splitlines()
    return json.loads(lines[-1])


@unittest.skipUnless(TOOL.exists(), 'native/build/mu-path not built (make -C native)')
class NativePathTests(unittest.TestCase):
    def test_open_ground_walk_reaches_the_target(self):
        r = find('--synthetic', 'open', '--from', '10,10', '--to', '20,14')
        self.assertEqual(r['found'], 1)
        self.assertEqual(r['path'][0], [10, 10])
        self.assertEqual(r['path'][-1], [20, 14])
        self.assertEqual(r['reached'], 1)
        self.assertEqual(r['end_position'], [2050, 1450])
        self.assertEqual((r['clicks'], r['sent'], r['arrivals']), (1, 1, 1))
        # 10 tiles diagonal-then-straight at 12 units per 40 ms step
        self.assertTrue(70 <= r['steps'] <= 110, r['steps'])

    def test_long_click_stops_after_fifteen_nodes_and_repath_continues(self):
        r = find('--synthetic', 'open', '--from', '10,10', '--to', '40,10')
        self.assertEqual(len(r['path']), 15)
        self.assertEqual(r['full_path_nodes'], 31)
        self.assertEqual(r['end_tile'], [24, 10])
        self.assertEqual(r['reached'], 0)
        r = find('--synthetic', 'open', '--from', '10,10', '--to', '40,10', '--repath')
        self.assertEqual(r['reached'], 1)
        self.assertEqual(r['clicks'], 3)

    def test_running_is_faster(self):
        walk = find('--synthetic', 'open', '--from', '10,10', '--to', '24,10')
        running = find('--synthetic', 'open', '--from', '10,10', '--to', '24,10', '--run')
        self.assertLess(running['steps'], walk['steps'])

    def test_run_counter_rules(self):
        """NATIVE-PATH-002: SetPlayerWalk's run rule. A class-0 hero without gear walks at 12; base class 3
        or boots of item level 5 run at 15 from the 40th moving step; level-4 boots do not; a safe zone
        keeps the counter at 0."""
        base = ('--synthetic', 'open', '--from', '10,10', '--to', '60,10')
        walk = find(*base)
        self.assertEqual((walk['max_speed'], walk['first_run_step'], walk['run_steps']), (12, -1, 0))
        for extra in (('--class', '3'), ('--boots', '5'), ('--run',)):
            r = find(*base, *extra)
            self.assertEqual((r['max_speed'], r['first_run_step']), (15, 40), extra)
            self.assertEqual(r['run_steps'], r['steps'] - 40)   # every step from the 40th on
            self.assertLess(r['steps'], walk['steps'])
        self.assertEqual(find(*base, '--boots', '4')['max_speed'], 12)
        r = find('--synthetic', 'safezone', '--seed', '4', '--from', '120,120', '--to', '135,121', '--class', '3')
        self.assertEqual(r['max_speed'], 12)

    def test_long_distance_auto_move(self):
        """NATIVE-PATH-002: the client's long-distance auto move (0x0129c6be): one search of up to 500 nodes,
        handed to the follower three nodes at a time, searched again where the list ends."""
        r = find('--synthetic', 'open', '--from', '10,10', '--to', '200,150', '--long')
        self.assertEqual((r['found'], r['reached'], r['long']), (1, 1, 1))
        self.assertEqual(r['full_path_nodes'], 191)
        self.assertEqual((r['segments'], r['searches']), (64, 1))      # ceil(191 / 3)
        self.assertEqual(r['end_position'], [20050, 15050])
        r = find('--synthetic', 'maze', '--seed', '3', '--from', '5,5', '--to', '250,250', '--long')
        self.assertEqual(r['reached'], 1)
        self.assertEqual(r['full_path_nodes'], 499)                     # the trimmed first search
        self.assertGreater(r['searches'], 1)
        self.assertGreater(r['segments'], 499 // 3)

    def test_maze_and_unreachable_targets(self):
        r = find('--synthetic', 'maze', '--seed', '3', '--from', '5,5', '--to', '30,30')
        self.assertEqual(r['found'], 1)
        self.assertEqual(r['pops'], 500)          # the search budget
        self.assertEqual(r['reached'], 0)
        r = find('--synthetic', 'noise', '--seed', '9', '--from', '100,100', '--to', '101,100')
        self.assertIn(r['found'], (0, 1))

    def test_safe_zone_characters(self):
        r = find('--synthetic', 'safezone', '--seed', '4', '--from', '120,120', '--to', '128,121')
        self.assertEqual(r['found'], 1)

    def test_zero_coordinate_is_refused(self):
        r = find('--synthetic', 'open', '--from', '0,10', '--to', '5,10')
        self.assertEqual(r['found'], 0)
        self.assertEqual(r['steps'], 0)

    def test_render_is_deterministic(self):
        with tempfile.TemporaryDirectory() as folder:
            outs = []
            for name in ('a.png', 'b.png'):
                out = Path(folder) / name
                result = run('render', '--synthetic', 'rooms', '--seed', '2', '--from', '40,40', '--to', '52,47',
                             '--out', str(out), '--size', '256')
                self.assertTrue(out.read_bytes().startswith(b'\x89PNG'))
                outs.append(result.stderr.split('sha256 ')[1].split()[0])
            self.assertEqual(outs[0], outs[1])

    def test_batch(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run('batch', '--synthetic', 'noise', '--seed', '5', '--count', '3', '--out-dir', folder,
                         '--size', '128')
            self.assertEqual(len(result.stdout.strip().splitlines()), 3)
            self.assertEqual(len(list(Path(folder).glob('*.png'))), 3)

    def test_usage_and_missing_root(self):
        self.assertEqual(run('find', check=False).returncode, 2)
        with tempfile.TemporaryDirectory() as folder:
            self.assertNotEqual(run('att', folder, '--world', '0', '--out', '-', check=False).returncode, 0)

    @unittest.skipUnless(PRIVATE and GAME_ROOT, 'MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
    def test_lorencia(self):
        raw = subprocess.run([str(TOOL), 'att', GAME_ROOT, '--world', '0', '--out', '-'], capture_output=True).stdout
        self.assertEqual(len(raw), 0x20000)
        cells = struct.unpack('<65536H', raw)
        self.assertTrue(all(c & 0x0500 == 0 for c in cells))   # stored & 0xfaff
        safe = sum(1 for c in cells if c & 1)
        self.assertGreater(safe, 100)
        r = find(GAME_ROOT, '--world', '0', '--from', '130,125', '--to', '136,128')
        self.assertEqual(r['found'], 1)
        self.assertEqual(r['reached'], 1)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'lorencia.png'
            run('render', GAME_ROOT, '--world', '0', '--from', '130,125', '--to', '136,128', '--out', str(out),
                '--size', '256')
            self.assertGreater(len(out.read_bytes()), 1000)
            self.assertNotEqual(hashlib.sha256(out.read_bytes()).hexdigest(), '')


if __name__ == '__main__':
    unittest.main()
