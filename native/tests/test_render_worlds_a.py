"""RENDER-WORLDS-A: synthetic world paths consume visual calls and draw the second pass."""
import ctypes
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_fixtures as nf
from test_native_world import write_open_world
from test_native_terrain import write_world
from test_native_objects import obj_plain
from test_native_particles import ozj_jpeg

ROOT = Path(__file__).resolve().parents[2]

class Runtime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT/'native'), 'world'], check=True)
        subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/objects')], check=True)
        cls.lib = ctypes.CDLL(str(ROOT/'reconstructed/objects/libobjects.dylib'))
        cls.lib.mu_objects_model_file.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_void_p, ctypes.c_size_t]

    def session(self, world, typ, backend="gl"):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = write_open_world(base/'game')
            write_world(root, world+1)
            buf = ctypes.create_string_buffer(1024)
            self.lib.mu_objects_model_file(world, typ, buf, 1024)
            model = root/buf.value.decode().replace('\\', '/')
            model.parent.mkdir(parents=True, exist_ok=True)
            generated = nf.write_textured_model(model.parent, 1)
            generated.rename(model)
            effect = root/'Data/Effect'
            effect.mkdir(exist_ok=True)
            for name in ('fantaF', 'firehik01', 'firehik02', 'firehik03', 'flare01', 'smoke01'):
                (effect/(name+'.OZJ')).write_bytes(ozj_jpeg(32,32))
            plain = base/'plain'
            plain.mkdir()
            (plain/f'EncTerrain{world+1}.plain').write_bytes(obj_plain(world+1,
                [(typ,13650,13650,60,0,1)]))
            run = subprocess.run([str(ROOT/'native/build/mu-world'), '--game-root', str(root), '--world', str(world),
                '--tile', '136,136', '--objects-dir', str(plain), '--headless', '--backend', backend, '--frames', '25',
                '--every', '1', '--width', '160', '--height', '100', '--no-audio', '--out-dir', str(base/'out')],
                capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            rows = [json.loads(line) for line in run.stdout.splitlines() if line.startswith('{')]
            return next(row for row in rows if 'objects_created' in row), next(row for row in rows if row.get('particles') is True)

    def test_karutan_flames_reach_particle_pool_and_draw(self):
        objects, particles = self.session(0x50, 0x71)
        self.assertGreater(objects['object_particles'], 0)
        self.assertGreater(particles['created'], 0)
        self.assertEqual(particles['unsupported'], 0)
        self.assertGreater(particles['drawn_particles'], 0)
        self.assertGreater(particles['drawn_sprites'], 0)

    def test_kanturu_hidden_flame_reaches_particle_pool(self):
        objects, particles = self.session(0x25, 0x3d)
        self.assertGreater(objects['object_particles'], 0)
        self.assertGreater(particles['created'], 0)
        self.assertEqual(particles['unsupported'], 0)
        self.assertGreater(particles['drawn_particles'], 0)

    def test_after_character_body_reaches_renderer(self):
        for backend in ('gl', 'soft'):
            for world, typ in ((3,0x13),(0x33,2),(0x39,0x2e),(0x50,3)):
                with self.subTest(world=world, backend=backend):
                    objects, _ = self.session(world,typ,backend)
                    self.assertGreater(objects['object_after_meshes'],0)
