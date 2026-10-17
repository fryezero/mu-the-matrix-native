"""Native actor checks (NATIVE-ACTOR-001, `mu-render actor` and `--pose`).

Portable (synthetic data only): a synthetic game root holds synthetic models
under the client's file names (lower-case on disk, to exercise the
case-insensitive lookup). `mu-render actor` must resolve a monster type, a
server class and an NPC index to the expected file, model index and scale,
give the actions the client's play speeds (reconstructed opener, scale rule,
NPC table), and advance the frame exactly as an independent binary32 model of
the tick does, one step per 40 ms; the strip and GIF outputs have the
requested geometry and frame count. Player-model classes and missing files
are refused.
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): installed monsters, NPCs
and a posed character render with every texture found (renders stay in a
temporary directory).
"""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
import native_fixtures as nf  # noqa: E402

TOOL = NATIVE/'build/mu-render'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def run(*args, check=True):
    result = subprocess.run([str(TOOL), *[str(a) for a in args]], capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f'mu-render {args[0]} failed: {result.stderr}')
    return result


def png_size(path):
    data = Path(path).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    return struct.unpack('>II', data[16:24])


def gif_frames(path):
    """Width, height and number of image descriptors of a GIF89a written by mu_gif."""
    data = Path(path).read_bytes()
    assert data[:6] == b'GIF89a'
    width, height, flags = struct.unpack('<HHB', data[6:11])
    position = 13 + (3 << ((flags & 7)+1) if flags & 0x80 else 0)
    frames = 0
    while position < len(data):
        marker = data[position]
        if marker == 0x3b:
            break
        if marker == 0x21:
            position += 2
            while data[position]:
                position += data[position]+1
            position += 1
        elif marker == 0x2c:
            frames += 1
            position += 10 + 1   # descriptor, LZW minimum code size
            while data[position]:
                position += data[position]+1
            position += 1
        else:
            raise AssertionError(f'bad GIF block {marker:#x}')
    return width, height, frames


def tick_frames(speed, keys, steps, start=0.0):
    """Independent binary32 model of the tick for an action without stop/lock flags."""
    frame = f32(start)
    for _ in range(steps):
        frame = f32(frame+speed)
        if frame >= keys:
            whole = int(frame)
            frame = f32(float(whole % keys)+f32(frame-whole))
    return frame


class ActorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.directory = tempfile.TemporaryDirectory()
        root = cls.root = Path(cls.directory.name)/'game'
        (root/'data'/'monster').mkdir(parents=True)
        (root/'data'/'npc').mkdir(parents=True)
        # Monster type 3 (file Monster04) and type 9 (Monster10, server class 3); NPC 0xa01 (Smith01).
        layout = nf.synthetic_layout(7, actions=7, keys=(9,))
        (root/'data'/'monster'/'monster04.bmd').write_bytes(layout)
        (root/'data'/'monster'/'MONSTER10.BMD').write_bytes(nf.synthetic_layout(8, actions=7, keys=(6,)))
        (root/'data'/'npc'/'smith01.bmd').write_bytes(nf.synthetic_layout(9, actions=3, keys=(5,)))

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def actor(self, *args):
        return json.loads(run('actor', '--game-root', self.root, '--no-textures', '--size', 48, 40, *args).stdout)

    def test_monster_type_speeds_and_frames(self):
        report = self.actor('--monster', 3, '--action', 2, '--time', 0.4, '--frames', 3, '--frame-steps', 2)
        self.assertTrue(report['file'].endswith('monster04.bmd'))
        self.assertEqual((report['monster_type'], report['model_index'], report['actions']), (3, 0x7a8, 7))
        speed = f32(f32(0.34)*f32(1.2))   # default walk speed, type 3 scale rule
        self.assertEqual(f32(report['action_speed']), speed)
        self.assertEqual(report['steps'], 10)
        self.assertEqual(f32(report['first_frame']), tick_frames(speed, 9, 10))
        self.assertEqual(f32(report['last_frame']), tick_frames(speed, 9, 14))
        self.assertEqual(report['unset_actions'], 0)

    def test_server_class_and_npc(self):
        report = self.actor('--type', 3, '--action', 0, '--time', 0.2)
        self.assertTrue(report['file'].endswith('MONSTER10.BMD'))
        self.assertEqual((report['server_class'], report['monster_type'], report['model_index']), (3, 9, 0x7ae))
        self.assertEqual(f32(report['scale']), f32(0.4))
        self.assertEqual(f32(report['action_speed']), f32(0.25))
        report = self.actor('--npc', 0xa01, '--action', 1, '--time', 0.2)
        self.assertTrue(report['file'].endswith('smith01.bmd'))
        self.assertEqual((report['npc_index'], report['action']), (0xa01, 1))
        self.assertEqual(f32(report['action_speed']), f32(0.25))
        self.assertEqual(f32(report['first_frame']), tick_frames(f32(0.25), 5, 5))

    def test_die_action_stops_on_the_last_key(self):
        report = self.actor('--monster', 3, '--action', 6, '--time', 2.0)
        self.assertEqual(report['action_loop'], 1)
        self.assertEqual(f32(report['first_frame']), f32(9-0.01))
        self.assertEqual(report['loop'], 0)

    def test_strip_and_gif(self):
        tmp = Path(self.directory.name)
        report = self.actor('--monster', 3, '--action', 2, '--frames', 4, '--out', tmp/'a.png',
                            '--strip', tmp/'s.png', '--gif', tmp/'a.gif')
        self.assertEqual(report['frames'], 4)
        self.assertEqual(png_size(tmp/'a.png'), (48, 40))
        self.assertEqual(png_size(tmp/'s.png'), (48*4, 40))
        self.assertEqual(gif_frames(tmp/'a.gif'), (48, 40, 4))
        again = self.actor('--monster', 3, '--action', 2, '--frames', 4)
        self.assertEqual(again['sha256_first'], report['sha256_first'])

    def test_refusals(self):
        for args in (('--type', 14), ('--monster', 0), ('--npc', 0x9fd), ('--type', 0xffff)):
            result = run('actor', '--game-root', self.root, '--no-textures', *args, check=False)
            self.assertNotEqual(result.returncode, 0, args)
        self.assertNotEqual(run('actor', '--game-root', self.root, check=False).returncode, 0)

    @unittest.skipUnless(PRIVATE, 'Private installed actor renders are opt-in')
    def test_installed_actors_render_with_textures(self):
        game_root = os.environ.get('MU_GAME_ROOT')
        self.assertTrue(game_root, 'Requested integration needs MU_GAME_ROOT')
        with tempfile.TemporaryDirectory() as directory:
            for args in (('--type', 0, '--action', 2), ('--type', 7, '--action', 6), ('--npc', 0xa01, '--action', 0),
                         ('--type', 256, '--action', 0), ('--monster', 9, '--action', 3)):
                report = json.loads(run('actor', '--game-root', game_root, *args, '--time', 0.4, '--frames', 3,
                                        '--size', 96, 96, '--gif', Path(directory)/'a.gif').stdout)
                self.assertEqual(report['textures_missing'], 0, args)
                self.assertEqual(report['open_status'], 0, args)
                self.assertGreater(report['meshes'], 0, args)
            report = json.loads(run('character', '--game-root', game_root, '--class', 1, '--pose', 'walk', '--time',
                                    0.3, '--frames', 2, '--size', 96, 96).stdout)
            self.assertEqual(report['action'], 0x32)
            self.assertEqual(report['textures_missing'], 0)


if __name__ == '__main__':
    unittest.main()
