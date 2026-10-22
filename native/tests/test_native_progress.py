"""Character progression in the native session (NATIVE-PROGRESS-001) checks.

Portable (synthetic data only): the NATIVE-WORLD-001 open-ground fixture and `mu-walk` (headless, software
rasterizer) with --progress:
  * kills give the DEMO server's experience through the client's kill handler (opcode 0x16); the
    experience bar's setExpData object follows the client's rule (0x00c5125b);
  * enough experience brings the DEMO level up (opcode 0xA0 sub 0x06): level, free points, the level's
    experience reset (0x00a00f4a), the effect, sound and chat lines of the client's handler;
  * a "+" button (CharacterInfoSetup row id) sends the client's request; the DEMO server's answers
    (0xA0 sub 0x11, 0x55 sub 0x57) raise the stat and spend the point; rows other than the five stat
    rows and a hero without points send nothing;
  * the class formula (reconstructed/progress, verified in Unicorn) gives the derived values.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
from test_native_world import write_open_world  # noqa: E402

WALK = NATIVE / 'build/mu-walk'


def walk(root, *args):
    result = subprocess.run([str(WALK), '--game-root', str(root), '--headless', '--backend', 'soft', '--no-audio',
                             *[str(a) for a in args]], capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    summary = next(r['progress'] for r in rows if 'progress' in r)
    lines = [r['progress_line'] for r in rows if 'progress_line' in r]
    return summary, lines, rows


@unittest.skipUnless(WALK.exists(), 'mu-walk not built (make -C native)')
class SyntheticProgress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name) / 'game'
        write_open_world(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_join_values(self):
        s, lines, _ = walk(self.root, '--frames', '4', '--progress', '--progress-class', '0')
        self.assertEqual((s['class'], s['level'], s['points'], s['exp'], s['next_exp']), (0, 1, 0, 0, 100))
        self.assertEqual(s['stats'], [18, 18, 15, 30, 0])
        # the Dark Wizard formula (0x0099a917) at level 1: damage str/8 ~ str/4, attack rate 5 + 27 + 4
        self.assertEqual(s['damage'], [18 // 8, 18 // 4])
        self.assertEqual(s['attack_rate'], 5 + 18 * 3 // 2 + 18 // 4)
        self.assertEqual(s['exp_bar'], {'ClassLevel': 1, 'curExp': '0', 'maxExp': '100', 'page': 0, 'rate': 0})
        # the speed row (0x00b40380): the magic speed for class 0 (DEMO: agility / 10), the class maximum 0x11c
        self.assertEqual(s['speed'], '%d / %d' % (18 // 10, 0x11c))

    def test_kill_experience_and_bar(self):
        s, lines, _ = walk(self.root, '--frames', '12', '--progress', '--progress-class', '1', '--progress-level', '30',
                           '--progress-script', '2:kill:3')
        gain = (4 + 25) * 4 // 3   # DEMO: monster level 1 + 3 % 40
        self.assertEqual((s['level'], s['exp'], s['level_ups']), (30, gain, 0))
        self.assertIn('call 01219a39 "Obtained %d Exp"' % gain, lines)
        nxt = s['next_exp']
        seg = nxt / 10
        page = int(gain / seg)
        self.assertEqual(s['exp_bar'], {'ClassLevel': 1, 'curExp': str(gain), 'maxExp': str(nxt), 'page': page,
                                        'rate': int((gain - page * seg) / seg * 100)})

    def test_level_up(self):
        s, lines, _ = walk(self.root, '--frames', '16', '--progress', '--progress-class', '0', '--progress-script',
                           '2:kill:20')
        self.assertEqual((s['level'], s['points'], s['exp'], s['next_exp'], s['level_ups']), (2, 5, 0, 340, 1))
        self.assertIn('call 00a6ac96 98 0 0', lines)   # the level-up sound
        self.assertIn('call 013c0eaa 7f84 o+158 o+164 o+ec 0 o ffffffff 0 0 0 00000000 ffffffff 0 0', lines)
        # the client refreshes the bar only from the experience handlers: it keeps the kill's values
        self.assertEqual(s['exp_bar']['maxExp'], '100')
        s, _, _ = walk(self.root, '--frames', '20', '--progress', '--progress-class', '0', '--progress-script',
                       '2:kill:20 10:kill:0')
        self.assertEqual((s['exp_bar']['maxExp'], s['exp_bar']['curExp']), ('340', str(26 // 3)))

    def test_stat_points(self):
        s, lines, _ = walk(self.root, '--frames', '30', '--progress', '--progress-class', '0', '--progress-points', '3',
                           '--progress-script', '2:add:0 6:add:3 10:button:9 14:add:3 18:add:3')
        # row 9 is not a stat button; with the three points spent the client sends nothing more
        self.assertEqual((s['requests'], s['accepted'], s['points']), (3, 3, 0))
        self.assertEqual(s['stats'], [19, 18, 15, 32, 0])
        self.assertIn('call 00b3e773 1d 20', lines)   # the energy row's new value (0x00b3ee5e)

    def test_no_points_no_request(self):
        s, _, _ = walk(self.root, '--frames', '10', '--progress', '--progress-class', '0', '--progress-script', '2:add:0')
        self.assertEqual((s['requests'], s['stats'][0]), (0, 18))


if __name__ == '__main__':
    unittest.main()
