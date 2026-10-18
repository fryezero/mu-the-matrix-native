"""Native effect module (NATIVE-FX-001) checks.

Portable: `mu-effect` runs a synthetic particle system and billboard (authored
here, no client data) through the reconstructed effect system and the software
rasterizer: deterministic summaries and images, the vertex dump layout, the
client's divide fault on an emitter without Frequency, and the directory scan.
Private (MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT): every installed
Data/Effect .ein loads and runs, and a contact sheet is written to a temporary
directory.
"""
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
TOOL = NATIVE / 'build/mu-effect'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')


def particle_system(**overrides):
    d = {'Type': 0, 'Name': 'synthetic', 'Texture': 'Data\\Effect\\none.ozj', 'Scale': 1.0, 'Duration': 2.0,
         'Looping': True, 'SpaceIsLocal': False, 'MaxParticle': 16, 'Blending': 2, 'Billboarding': 0,
         'LengthScale': 1.0, 'SpeedScale': 0.3,
         'Components': [{'Type': 0, 'Frequency': 1, 'Delay': 0.0, 'MinEmissionCount': 1, 'MaxEmissionCount': 3,
                         'Components': [{'Type': 0, 'Shape': 1, 'Radius': 0.5},
                                        {'Type': 1, 'MinColor': [1, 0.5, 0.2, 1], 'MaxColor': [1, 0.8, 0.3, 1],
                                         'ColorGradation': None, 'AlphaGradation': None,
                                         'MinBrightness': 1.0, 'MaxBrightness': 1.0, 'BrightnessGradation': None},
                                        {'Type': 2, 'Min': 0.5, 'Max': 1.0, 'Curve': None},
                                        {'Type': 4, 'Min': 0.2, 'Max': 0.4, 'Curve': None},
                                        {'Type': 5, 'Min': 1.0, 'Max': 2.0, 'Curve': None}]}]}
    d.update(overrides)
    return d


def billboard():
    return {'Type': 1, 'Name': 'synthetic-billboard', 'Texture': 'Data\\Effect\\none.ozj', 'Scale': 1.0,
            'Duration': 1.0, 'Looping': True, 'Width': 2.0, 'Height': 1.0, 'RotationAngle': 0.3, 'Blending': 1,
            'Billboarding': 0, 'Brightness': 1.0, 'Components': []}


def tool(*args, check=True):
    result = subprocess.run([str(TOOL), *[str(a) for a in args]], capture_output=True, text=True)
    if check:
        assert result.returncode == 0, result.stderr
    return result


def summary(*args):
    return json.loads(tool(*args).stdout.splitlines()[-1])


class NativeEffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'build/mu-effect'], check=True, capture_output=True)

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        (self.root / 'Data/Effect').mkdir(parents=True)

    def tearDown(self):
        self.folder.cleanup()

    def write(self, name, document):
        path = self.root / 'Data/Effect' / name
        path.write_text(json.dumps(document, indent=1))
        return path

    def test_render_is_deterministic(self):
        effect = self.write('syn.ein', particle_system())
        a = summary('render', effect, '--out', self.root / 'a.png', '--frames', 10, '--size', '96x96')
        b = summary('render', effect, '--out', self.root / 'b.png', '--frames', 10, '--size', '96x96')
        c = summary('render', effect, '--out', self.root / 'c.png', '--frames', 10, '--size', '96x96', '--seed', 5)
        self.assertEqual((a['type'], a['particles'], a['vertices'], a['faulted']), (0, 16, 64, 0))
        self.assertEqual(a['texture'], 'Data\\Effect\\none.ozj')
        self.assertEqual(a['texture_loaded'], 0)
        self.assertEqual(a['sha256'], b['sha256'])
        self.assertEqual((self.root / 'a.png').read_bytes(), (self.root / 'b.png').read_bytes())
        self.assertNotEqual(a['sha256'], c['sha256'])
        self.assertEqual((self.root / 'a.png').read_bytes()[:8], b'\x89PNG\r\n\x1a\n')

    def test_dump_layout(self):
        effect = self.write('syn.ein', particle_system())
        out = self.root / 'dump.bin'
        tool('dump', effect, '--out', out, '--frames', 6)
        raw = out.read_bytes()
        offset, frames = 0, []
        while offset < len(raw):
            vertices, particles = struct.unpack_from('<II', raw, offset)
            offset += 8 + 36 * vertices
            frames.append((vertices, particles))
        self.assertEqual(offset, len(raw))
        self.assertEqual(len(frames), 6)
        self.assertEqual(frames[0], (0, 0))
        self.assertTrue(all(v == 4 * p for v, p in frames))
        self.assertGreater(frames[-1][1], 0)

    def test_billboard_and_sheet(self):
        effect = self.write('bb.ein', billboard())
        s = summary('sheet', effect, '--out', self.root / 'sheet.png', '--frames', 6, '--every', 2, '--columns', 3,
                    '--size', '64x64')
        self.assertEqual((s['type'], s['vertices'], s['faulted']), (1, 4, 0))
        self.assertTrue((self.root / 'sheet.png').stat().st_size > 0)

    def test_missing_frequency_faults_like_the_client(self):
        document = particle_system()
        del document['Components'][0]['Frequency']
        s = summary('render', self.write('nofreq.ein', document), '--out', self.root / 'f.png', '--frames', 5,
                    '--size', '32x32')
        self.assertEqual((s['faulted'], s['particles'], s['rand_calls']), (1, 0, 1))

    def test_tree_render_draws_every_node(self):
        document = particle_system(Children=[billboard(), particle_system(Name='child')])
        s = summary('render', self.write('tree.ein', document), '--out', self.root / 't.png', '--frames', 8,
                    '--size', '64x64')
        self.assertEqual(s['nodes'], 3)
        self.assertGreater(s['vertices'], 4 * s['particles'])   # the children's quads are drawn too

    def test_scene_factory_octree_and_culling(self):
        self.write('a.ein', particle_system(Children=[billboard()]))
        self.write('b.ein', billboard())
        args = ['scene', self.root, '--flat', '--target', '13000,13000', '--size', '96x64', '--frames', 6,
                '--effect', 'Data\\Effect\\a.ein@0,0,50@20', '--effect', 'Data\\Effect\\A.EIN@150,0,50@20',
                '--effect', 'Data\\Effect\\b.ein@-30000,0,0@10']
        a = summary(*args, '--out', self.root / 's1.png')
        b = summary(*args, '--out', self.root / 's2.png')
        self.assertEqual((a['instances'], a['templates'], a['nodes']), (3, 2, 5))
        self.assertEqual(a['visible'], 4)                         # b lies outside the manager's world box
        self.assertEqual(a['sha256'], b['sha256'])
        self.assertEqual((self.root / 's1.png').read_bytes(), (self.root / 's2.png').read_bytes())
        missing = tool('scene', self.root, '--flat', '--effect', 'Data\\Effect\\none.ein@0,0,0', check=False)
        self.assertNotEqual(missing.returncode, 0)

    def test_scan(self):
        self.write('a.ein', particle_system())
        self.write('b.ein', billboard())
        s = json.loads(tool('scan', self.root).stdout)
        self.assertEqual((s['files'], s['particle_systems'], s['billboards'], s['failed']), (2, 1, 1, 0))
        (self.root / 'Data/Effect/broken.ein').write_text('{"Type": 0, ')
        self.assertNotEqual(tool('scan', self.root, check=False).returncode, 0)


@unittest.skipUnless(PRIVATE, 'Installed effect checks are opt-in (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT)')
class PrivateNativeEffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'build/mu-effect'], check=True, capture_output=True)

    def test_installed_effects(self):
        root = Path(os.environ['MU_GAME_ROOT'])
        s = json.loads(tool('scan', root).stdout)
        self.assertGreater(s['files'], 0)
        self.assertEqual(s['failed'], 0)
        self.assertEqual(s['files'], s['particle_systems'] + s['billboards'])
        first = sorted((root / 'Data/Effect').glob('*.ein'))[0]
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'sheet.png'
            tool('sheet', first, '--out', out, '--frames', 10, '--size', '96x96')
            self.assertGreater(out.stat().st_size, 0)

    def test_demo_scene_over_terrain(self):
        root = Path(os.environ['MU_GAME_ROOT'])
        with tempfile.TemporaryDirectory() as folder:
            s = summary('scene', root, '--world', 0, '--demo', '--frames', 12, '--size', '160x100',
                        '--out', Path(folder) / 'scene.png')
        self.assertEqual((s['instances'], s['templates'], s['world']), (10, 10, 0))
        self.assertGreater(s['visible'], 0)


if __name__ == '__main__':
    unittest.main()
