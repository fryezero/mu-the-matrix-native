"""The living walk-around world (NATIVE-WORLD-002) checks.

Portable (synthetic data only), through `mu-walk` (headless, software
rasterizer) on the synthetic world of test_native_world.py plus synthetic
sounds, a synthetic sound table, synthetic monster/NPC models and a synthetic
effect:
  * footsteps: every PlayWalkSound call follows the client's trigger (frames
    1.5 and 4.5 of a walk cycle, flags cleared when the animation wraps), with
    pWalk(Grass) on layer-1 tile 0 and pWalk(Soil) elsewhere in world 0, and
    none while standing;
  * the per-frame audio block plays the Lorencia wind; the WAV file has the
    run's length and contains the wind and the footstep sounds;
  * the demo placement: actors resolve through the class tables, monsters
    wander with the walk action and the client move speed and stand with
    action 0, the effect class gets its EffectManager instance, bad lines are
    refused;
  * the terrain uses the client frustum (box around the camera view, fewer
    faces than the legacy square), and runs are deterministic.
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, optional MU_AUDIO_TABLE):
a Lorencia walk into the pub and out to the field with the demo placement:
main theme then the pub music, grass and soil footsteps, the actors and
their effects.
"""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import wave

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
import native_fixtures as nf  # noqa: E402
from test_native_world import write_open_world  # noqa: E402
from test_native_effect import particle_system  # noqa: E402

WALK = NATIVE/'build/mu-walk'
PLACEMENT = NATIVE/'world/lorencia-demo-placement.txt'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')
RATE = 22050


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def constant_wav(level, frames, rate=RATE):
    data = struct.pack('<h', int(level*32767))*frames
    header = struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36+len(data), b'WAVE', b'fmt ', 16, 1, 1, rate, 2*rate, 2, 16,
                         b'data', len(data))
    return header + data


def write_life(root):
    """Sounds, table, models and an effect on top of the synthetic world."""
    sound = root/'Data'/'Sound'
    sound.mkdir(parents=True, exist_ok=True)
    (sound/'awind.wav').write_bytes(constant_wav(0.05, RATE))          # looped ambient
    (sound/'pwalk(soil).wav').write_bytes(constant_wav(0.3, RATE//10))
    (sound/'pwalk(grass).wav').write_bytes(constant_wav(0.6, RATE//10))
    table = root/'table.tsv'
    table.write_text('# kind\tid\tpath\tch\t3d\tloader\n'
                     'sound\t0\tData\\Sound\\aWind.wav\t1\t1\t0x18433ed\n'
                     'sound\t8\tData\\Sound\\pWalk(Soil).wav\t2\t1\t0x18433ed\n'
                     'sound\t9\tData\\Sound\\pWalk(Grass).wav\t2\t1\t0x18433ed\n')
    monster, npc, effect = root/'Data'/'Monster', root/'Data'/'Npc', root/'Data'/'Effect'
    for d in (monster, npc, effect):
        d.mkdir(parents=True, exist_ok=True)
    (monster/'monster10.bmd').write_bytes(nf.synthetic_layout(8, actions=7, keys=(6,)))   # class 3 -> type 9
    (npc/'smith01.bmd').write_bytes(nf.synthetic_layout(9, actions=3, keys=(5,)))         # class 251 -> 0xa01
    (npc/'new_maple.bmd').write_bytes(nf.synthetic_layout(10, actions=2, keys=(4,)))      # class 873 -> 0xa52
    (effect/'leaf_particle_f2e.ein').write_text(json.dumps(particle_system()))
    return table


def run(root, *args, check=True):
    result = subprocess.run([str(WALK), '--game-root', str(root), '--headless', '--backend', 'soft',
                             *[str(a) for a in args]], capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    return {'frames': [r for r in rows if 'frame' in r and 'tick' in r],
            'summary': next((r for r in rows if r.get('summary')), None),
            'sound': next((r for r in rows if r.get('sound')), None),
            'actors': next((r for r in rows if 'actor_steps' in r), None),
            'actor': [r for r in rows if 'actor' in r and 'class' in r],
            'result': result}


def expected_footsteps(frames):
    """Independent statement of the trigger and reset over per-step reports
    (one logic step per headless frame): the foot flags clear when the frame
    went backwards (the tick wrapped), a step sounds at 1.5 and at 4.5."""
    foot, count, previous = [0, 0], [], None
    for f in frames:
        if previous is not None and f['frame_anim'] < previous:
            foot = [0, 0]
        previous = f['frame_anim']
        walking = 0x32 <= f['action'] <= 0x3e or 0x4f <= f['action'] < 0x6f
        n = 0
        if walking:
            if f['frame_anim'] >= 1.5 and not foot[0]:
                foot[0], n = 1, n+1
            if f['frame_anim'] >= 4.5 and not foot[1]:
                foot[1], n = 1, n+1
        count.append(n)
    return count


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = write_open_world(Path(cls.tmp.name)/'game')
        cls.table = write_life(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()


class SoundTests(Build):
    def test_footsteps_follow_the_client_trigger(self):
        out = run(self.root, '--tile', '120,120', '--walk', '125,123', '--frames', '140', '--every', '1',
                  '--width', '160', '--height', '100', '--out-dir', Path(self.tmp.name)/'f',
                  '--sound-table', self.table)
        frames, sound = out['frames'], out['sound']
        self.assertEqual(out['summary']['arrivals'], 1)
        steps = [b['footsteps'] - a['footsteps'] for a, b in zip(frames, frames[1:])]
        self.assertEqual(steps, expected_footsteps(frames)[1:])
        self.assertGreaterEqual(sound['footsteps'], 4)
        self.assertEqual(sound['footsteps'], sound['soil'] + sound['grass'])
        self.assertGreater(sound['soil'], 0)
        self.assertGreater(sound['grass'], 0)          # layer-1 tiles 0 and 2 alternate in the synthetic map
        self.assertGreater(sound['foot_resets'], 0)
        standing = [s for s, f in zip(steps, frames[1:]) if not f['moving'] and f['action'] == 1]
        self.assertEqual(set(standing), {0})

    def test_hero_tile_is_the_layer1_tile_under_the_hero(self):
        out = run(self.root, '--tile', '120,120', '--frames', '3', '--every', '1', '--width', '64', '--height', '64',
                  '--out-dir', Path(self.tmp.name)/'t')
        self.assertIn(out['frames'][-1]['hero_tile'], (0, 2))

    def test_wav_has_the_wind_and_the_footsteps(self):
        wav_path = Path(self.tmp.name)/'run.wav'
        out = run(self.root, '--tile', '120,120', '--walk', '126,120', '--frames', '100', '--audio-rate', RATE,
                  '--sound-table', self.table, '--wav', wav_path, '--quiet')
        with wave.open(str(wav_path)) as w:
            self.assertEqual((w.getnchannels(), w.getframerate()), (2, RATE))
            frames = w.getnframes()
            samples = struct.unpack(f'<{2*frames}h', w.readframes(frames))
        self.assertEqual(frames, out['sound']['wav_frames'])
        self.assertAlmostEqual(frames/RATE, 100*0.040, delta=0.05)   # 40 ms frames
        self.assertGreater(out['sound']['ambient_plays'], 0)
        left = [abs(s)/32767 for s in samples[0::2]]
        wind = sum(1 for v in left if 0.04 < v < 0.06)
        steps = sum(1 for v in left if v > 0.3)
        self.assertGreater(wind, RATE)                   # the looped wind alone, most of the run
        self.assertGreater(steps, 0)                     # wind plus a footstep
        self.assertGreater(out['sound']['footsteps'], 0)

    def test_silent_without_table_and_no_audio(self):
        out = run(self.root, '--tile', '120,120', '--walk', '124,120', '--frames', '60', '--quiet')
        self.assertGreater(out['sound']['footsteps'], 0)     # decisions still run, nothing resolves
        self.assertFalse(out['sound']['table'])
        out = run(self.root, '--tile', '120,120', '--frames', '5', '--quiet', '--no-audio')
        self.assertIsNone(out['sound'])
        bad = run(self.root, '--frames', '5', '--no-audio', '--wav', Path(self.tmp.name)/'x.wav', check=False)
        self.assertNotEqual(bad['result'].returncode, 0)


class ActorTests(Build):
    def placement(self, text):
        path = Path(self.tmp.name)/'placement.txt'
        path.write_text(text)
        return path

    def test_demo_placement_runs_the_client_actor_rules(self):
        path = self.placement('# demo\nactor 3 140 140 2 wander 3 label spider\nactor 251 118 118 4 label smith\n'
                              'actor 873 116 118 0 label maple\n')
        out = run(self.root, '--tile', '120,120', '--frames', '400', '--every', '0', '--placement', path,
                  '--sound-table', self.table, '--quiet')
        actors, rows = out['actors'], out['actor']
        self.assertEqual(actors['actors'], 3)
        self.assertEqual(actors['effect_instances'], 1)
        spider, smith, maple = rows
        self.assertEqual((spider['class'], spider['model']), (3, 0x7ae))
        self.assertEqual((smith['class'], smith['model']), (251, 0xa01))
        self.assertEqual((maple['class'], maple['model'], maple['effects']), (873, 0xa52, 1))
        self.assertGreater(spider['moves'], 0)
        self.assertGreater(spider['arrivals'], 0)
        self.assertLessEqual(max(abs(spider['tile'][0]-140), abs(spider['tile'][1]-140)), 3)
        self.assertEqual(smith['action'], 0)
        self.assertEqual((smith['moves'], smith['tile']), (0, [118, 118]))
        self.assertEqual(f32(smith['speed']), f32(0.25))            # OpenNpc default speed

    def test_monster_moves_at_the_character_create_speed(self):
        path = self.placement('actor 3 140 140 2 wander 4\n')
        out = run(self.root, '--tile', '120,120', '--frames', '300', '--every', '1', '--width', '64', '--height',
                  '64', '--out-dir', Path(self.tmp.name)/'m', '--placement', path, '--quiet', '--no-audio')
        self.assertGreater(out['actors']['actor_moves'], 0)

    def test_bad_placement_lines_are_refused(self):
        for text in ('actor 3 140\n', 'actor 3 300 140 2\n', 'actor 3 140 140 2 sprint 4\n', 'actor 999 1 1 0\n',
                     'monster 3 140 140 2\n'):
            out = run(self.root, '--frames', '2', '--placement', self.placement(text), '--no-audio', check=False)
            self.assertNotEqual(out['result'].returncode, 0, text)
            self.assertIn('placement', out['result'].stderr)

    def test_the_shipped_placement_is_labelled_demo(self):
        text = PLACEMENT.read_text()
        self.assertIn('DEMO PLACEMENT', text.splitlines()[0])
        self.assertIn('NOT client data', text.splitlines()[0])
        lines = [line for line in text.splitlines() if line.startswith('actor ')]
        self.assertGreaterEqual(len(lines), 8)


class TerrainTests(Build):
    def test_client_frustum_box_and_determinism(self):
        args = ['--tile', '120,120', '--frames', '3', '--every', '1', '--width', '320', '--height', '200', '--no-audio']
        a = run(self.root, *args, '--out-dir', Path(self.tmp.name)/'c1')['frames']
        b = run(self.root, *args, '--out-dir', Path(self.tmp.name)/'c2')['frames']
        legacy = run(self.root, *args, '--out-dir', Path(self.tmp.name)/'c3', '--legacy-box')['frames']
        self.assertEqual([f['sha256'] for f in a], [f['sha256'] for f in b])
        box = a[-1]['box']
        self.assertTrue(all(v % 4 == 0 or v == 251 for v in box))
        self.assertLess(box[0], 120)
        self.assertLess(box[1], 120)
        self.assertNotEqual(box, legacy[-1]['box'])
        self.assertGreater(a[-1]['tiles'], 0)
        self.assertLess(a[-1]['tiles'], legacy[-1]['tiles'])     # the tile tests cull the square's corners


@unittest.skipUnless(PRIVATE, 'installed-data walk is opt-in (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT)')
class InstalledTests(unittest.TestCase):
    def test_lorencia_pub_and_field(self):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        root = os.environ['MU_GAME_ROOT']
        table = os.environ.get('MU_AUDIO_TABLE')
        route = '130,124 125,131 130,131 134,129 138,128 142,127 146,127 150,127 154,127 158,127 162,127 166,127 ' \
                '170,127 174,127 178,127 182,128'
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        args = ['--tile', '133,127', '--walk', route, '--frames', '1400', '--placement', PLACEMENT, '--every', '5',
                '--width', '160', '--height', '100', '--out-dir', tmp.name]
        if table:
            args += ['--sound-table', table]
        out = run(root, *args)
        sound, actors = out['sound'], out['actors']
        self.assertEqual(out['summary']['arrivals'], 16)
        self.assertGreater(sound['soil'], 0)        # town stone and the pub floor
        self.assertGreater(sound['grass'], 0)       # the field east of town
        self.assertEqual(actors['actors'], 12)
        self.assertEqual(actors['effect_instances'], 3)
        tiles = {f['hero_tile'] for f in out['frames']}
        self.assertTrue({0, 3, 4} <= tiles, tiles)
        if table:
            self.assertEqual(sound['last_music'], 21)   # main theme again after the pub
            self.assertGreater(sound['music_plays'], 0)


if __name__ == '__main__':
    unittest.main()
