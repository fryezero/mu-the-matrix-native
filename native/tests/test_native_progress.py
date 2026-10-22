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
Options window and system menu: native/tests/options_host.c (stub GFx layer and audio, the real game side) over
native/world/world_gfx_options.c.  Respawn: the answer 0xA0 sub 0x30 and the DEMO town (mu_map_respawn).
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
        # the speed row (0x00b40380): the magic speed for class 0 (DEMO: 20 + agility / 10) and the server's
        # maximum 400 (live)
        self.assertEqual(s['speed'], '%d / %d' % (20 + 18 // 10, 400))

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


ROOT = NATIVE.parent
CC = next((c for c in ('cc', 'clang', 'gcc') if subprocess.run(['which', c], capture_output=True).returncode == 0), None)
ON_CHANGE = ('["onChange",{"effectLimit":3.0,"isAutoAttack":false,"isMonsterInfo":false,"isMusicPlay":false,'
             '"isMute":false,"isPlayerInfo":true,"isSlideHelp":true,"isSwitchMode":false,"isWhisperSound":false,'
             '"switchModeTime":10.0,"volum":7.0}]')


@unittest.skipUnless(CC, 'no C compiler')
class OptionsWindow(unittest.TestCase):
    """winOption / winSystemMenu over native/world/world_gfx_options.c (stub layer and audio, real game side):
    the settings file in the client's option.ini format, the audio groups, the menu's requests."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.exe = cls.dir / 'options-host'
        subprocess.run([CC, '-std=c11', '-O1', '-Wall', '-Wextra', '-DMU_GFX_NO_GL', '-o', str(cls.exe),
                        str(HERE / 'options_host.c'), str(NATIVE / 'world/world_gfx_options.c'),
                        str(ROOT / 'reconstructed/progress/progress_options.c'),
                        str(ROOT / 'reconstructed/charsel/charcreate.c'),
                        str(ROOT / 'reconstructed/charsel/charsel_gfx.c')], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def host(self, settings, *ops):
        r = subprocess.run([str(self.exe), str(settings), *ops], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.splitlines()
        return lines, [json.loads(l) for l in lines if l.startswith('{')]

    def test_defaults_open_and_change(self):
        settings = self.dir / 'a'
        lines, rows = self.host(settings, 'audio', 'load', 'step', '40', 'key', '0', 'step', '40', 'print',
                                'call', '0', ON_CHANGE, 'print')
        # the join's values through the setters: setDatas at the first visible frame, the volume read back
        # from the Effect group ((int)(1.0 * 9 + 0.5) = 9)
        data = next(l for l in lines if ' setDatas ' in l)
        self.assertIn('"isAutoAttack":true', data)
        self.assertIn('"volum":9', data)
        self.assertIn('"effectLimit":5', data)
        self.assertEqual(rows[0]['volume'], 9)
        # onChange: apply 0x00c7635f (Effect group volume / 9, Music mute, monster info) and the file
        self.assertIn('audio volume 2 0.7778', lines)
        self.assertIn('audio mute 0 1', lines)
        self.assertIn('monster_info 0', lines)
        self.assertEqual((rows[1]['volume'], rows[1]['effect'], rows[1]['music_play']), (7, 2, 0))
        ini = (settings / 'option.ini').read_text()
        self.assertIn('[OPTION]\nEffect=2\n', ini)
        for key in ('Volum=7', 'IsMusicPlay=0', 'IsMonsterInfo=0', 'IsAutoAttack=0', 'IsSlideHelp=1'):
            self.assertIn(key, ini)
        # the next session: the loader reads the file back and the stored volume reaches the audio module
        lines, rows = self.host(settings, 'audio', 'step', '40', 'print')
        self.assertIn('audio volume 2 0.7778', lines)
        self.assertEqual((rows[0]['volume'], rows[0]['monster_info'], rows[0]['effect']), (7, 0, 2))

    def test_effect_clamp_and_missing_file(self):
        settings = self.dir / 'b'
        settings.mkdir()
        (settings / 'option.ini').write_text('[OPTION]\nEffect=9\n')
        _, rows = self.host(settings, 'print')
        self.assertEqual(rows[0]['effect'], 4)   # 0x00c76314 clamps 0..4
        _, rows = self.host(self.dir / 'none', 'print')
        self.assertEqual((rows[0]['volume'], rows[0]['auto_attack'], rows[0]['effect']), (5, 1, 4))
        self.assertFalse((self.dir / 'none' / 'option.ini').exists())

    def test_menu_requests(self):
        settings = self.dir / 'c'
        lines, rows = self.host(settings, 'load', 'key', '1', 'call', '1', '["onCharSelectClick",{}]', 'print',
                                'key', '1', 'call', '1', '["onServerSelectClick",{}]', 'print',
                                'key', '1', 'call', '1', '["onExit",{}]', 'step', '4900', 'print', 'step', '200',
                                'print')
        self.assertIn('invoke 29 _level0.instance1 SceneChange [6]', lines)
        self.assertEqual([r['request'] for r in rows], [1, 2, -1, 0])   # exit after the 5 s countdown
        self.assertIn('chat You will exit game in 5 seconds.', lines)

    def test_esc_closes_the_options_window_first(self):
        lines, _ = self.host(self.dir / 'd', 'load', 'key', '0', 'key', '1')
        tail = lines[lines.index('show 28 1'):]
        self.assertIn('show 28 0', tail)
        self.assertNotIn('show 29 1', tail)


@unittest.skipUnless(WALK.exists(), 'mu-walk not built (make -C native)')
class Respawn(unittest.TestCase):
    """The respawn answer (0xA0 sub 0x30, mu_prg_recv_respawn) and the DEMO town (mu_map_respawn: gate 17 for
    a world without its own town): a death in world 1 lands in world 0's town rectangle."""

    @classmethod
    def setUpClass(cls):
        from test_native_map import GATES, MOVES, TEXT, second_world
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name) / 'game'
        write_open_world(cls.root)
        second_world(cls.root)
        cls.lang = Path(cls.tmp.name) / 'lang'
        cls.lang.mkdir()
        (cls.lang / 'gates.tsv').write_text(GATES + '17\t0\t0\t100\t100\t102\t101\t0\t1\t0\t-1\n')
        (cls.lang / 'moves.tsv').write_text(MOVES)
        (cls.lang / 'globaltext.txt').write_text(TEXT)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_walk(self, *args):
        import os
        env = dict(os.environ, MU_LANG_DIR=str(self.lang))
        r = subprocess.run([str(WALK), '--game-root', str(self.root), '--headless', '--backend', 'soft', '--no-audio',
                            *[str(a) for a in args]], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{')], r

    def test_respawn_in_town_of_another_world(self):
        rows, r = self.run_walk('--world', '1', '--tile', '42,41', '--frames', '12', '--progress',
                                '--progress-level', '30', '--travel-script', '3:respawn')
        respawn = next(x['respawn'] for x in rows if 'respawn' in x)
        self.assertEqual(respawn['world'], 0)
        self.assertTrue(100 <= respawn['tile'][0] <= 102 and 100 <= respawn['tile'][1] <= 101, respawn)
        summary = next(x for x in rows if x.get('summary'))
        self.assertEqual(summary['world'], 0, r.stderr)
        line = next(x['progress_line'] for x in rows if str(x.get('progress_line', '')).startswith('respawn'))
        self.assertEqual(line, 'respawn 0 %d %d 0' % tuple(respawn['tile']))
        progress = next(x['progress'] for x in rows if 'progress' in x)
        self.assertEqual(progress['level'], 30)   # no death penalty (DEMO): the experience is kept

    def test_respawn_in_the_same_world(self):
        rows, r = self.run_walk('--tile', '80,80', '--frames', '8', '--progress', '--travel-script', '3:respawn')
        respawn = next(x['respawn'] for x in rows if 'respawn' in x)
        self.assertEqual((respawn['world'], respawn['town']), (0, 1))
        self.assertTrue(100 <= respawn['tile'][0] <= 102 and 100 <= respawn['tile'][1] <= 101, respawn)
        m = [x for x in rows if x.get('map')][0]
        self.assertEqual(m['tile'], respawn['tile'], r.stderr)


if __name__ == '__main__':
    unittest.main()
