"""RENDER-EFFECTS-010: the pets' six particle kinds, arrows 0x615/0x617's particle kinds, the render-registry
functors of arrows 0x613..0x617 and the demon pet in a synthetic session.

Portable: worked examples on reconstructed/particles and reconstructed/combat through ctypes (the validators'
structures), and mu-walk in a synthetic world. Private (MU_RECOVERY_INTEGRATION=1): the short original-instruction
run of scripts/validate_render_effects10.py with its compiled mutants."""
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
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT/'scripts'))
from test_native_combat import write_combat_world
from test_native_pets import write_pet_models

SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


class Host:
    """rand() from a list, a terrain height of 0 and one owner whose position the test moves."""

    def __init__(self, values):
        import validate_particles as pt
        self.pt = pt
        self.values, self.calls = list(values), 0
        self.owner = [100.0, 200.0, 300.0]

        def rand(ctx):
            r = self.values[self.calls % len(self.values)]
            self.calls += 1
            return r

        def owner(ctx, index, out):
            out[0], out[1], out[2] = self.owner

        def zero(*a):
            return 0.0
        self.fns = (pt.RAND_FN(rand), pt.HEIGHT_FN(zero), pt.OWNER_FN(owner), pt.BITMAP_HEIGHT_FN(zero),
                    pt.CLOUD_OWNER_FN(lambda c, o, r: 1), pt.SOUND_FN(lambda c, i: None),
                    pt.LIGHT_FN(lambda c, x, y, rgb, r: None))
        self.host = pt.Host(None, self.fns[0], self.fns[1], self.fns[2], 0, 0.0, 0.1, 1, 6, self.fns[3], self.fns[4],
                            self.fns[5], self.fns[6])


class ParticleKinds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(ROOT/'reconstructed/particles')], check=True, capture_output=True)
        import validate_particles as pt
        cls.pt = pt
        cls.lib = pt.load_library(ROOT/f'reconstructed/particles/libclient_particles.{SUFFIX}')

    def create(self, host, kind, position=(10.0, 20.0, 30.0), light=(0.6, 0.4, 0.2), scale=0.5, owner=-1):
        pt = self.pt
        p = pt.Particle()
        F3 = ctypes.c_float * 3
        ok = self.lib.mu_pt_create_record(ctypes.byref(p), ctypes.byref(host.host), kind[0], F3(*position),
                                          F3(0.0, 0.0, 0.0), F3(*light), kind[1], scale, owner, 0)
        self.assertEqual(ok, 1)
        return p

    def test_clud64_cloud(self):
        """Clud64 0x7ffd/0xb (the Demon): three in four drawn with smoke01, 30 steps, a sinking, shrinking cloud
        drawn subtractively."""
        h = Host([1, 100, 15, 30, 2])
        p = self.create(h, (0x7ffd, 0xb))
        self.assertEqual((p.tex_type, p.lifetime), (0x7f5a, 30))
        self.assertEqual((p.rotation, p.gravity), (100.0, -1.5))
        self.assertEqual(list(p.position), [15.0, 20.0, 22.0])
        self.assertEqual(self.create(Host([4, 0, 10, 10, 10]), (0x7ffd, 0xb)).tex_type, 0x7ffd)   # rand % 4 == 0
        self.assertEqual(self.lib.mu_pt_move_record(ctypes.byref(p), ctypes.byref(h.host)), 1)
        self.assertEqual(list(p.light), [3.0, 3.0, 3.0])                  # LifeTime / 10
        self.assertEqual(p.gravity, f32(-1.5 - f32(0.01)))
        self.assertEqual(p.position[2], f32(22.0 - p.gravity))
        self.assertEqual(p.scale, f32(0.5 - f32(0.03)))
        call = self.pt.RenderCall()
        bm = self.pt.Bitmap(64.0, 64.0, 3)
        self.assertEqual(self.lib.mu_pt_render_record(ctypes.byref(p), ctypes.byref(bm), 0, 0.0, 0,
                                                      ctypes.byref(call)), 1)
        self.assertIn(0x0184aab7, list(call.state)[:call.state_count])  # EnableAlphaBlendMinus

    def test_skeleton_flame_follows_the_pet(self):
        """firehik_mono 0x8086/4: starts at the owner's +0x158, fades in from the saved colour, is pushed 8 along
        its angle's -y and carried by the owner's move."""
        h = Host([0, 0, 0])
        p = self.create(h, (0x8086, 4), owner=0)
        self.assertEqual((p.lifetime, p.alpha), (8, 0.0))
        self.assertEqual(list(p.light), [0.0, 0.0, 0.0])
        self.assertEqual([p.field_7c, p.field_80, p.field_84], [f32(0.6), f32(0.4), f32(0.2)])
        self.assertEqual(list(p.start), [100.0, 200.0, 300.0])
        h.owner = [110.0, 195.0, 300.0]
        self.lib.mu_pt_move_record(ctypes.byref(p), ctypes.byref(h.host))
        self.assertEqual(list(p.position), [20.0, f32(20.0 - 8.0 - 5.0), 30.0])
        self.assertEqual(list(p.start), [110.0, 195.0, 300.0])
        self.assertEqual(p.alpha, f32(0.2))                                # (rand % 2 + 2) / 10
        self.assertEqual(p.rotation, 5.0)
        other = self.create(Host([0, 0, 0]), (0x8089, 5), owner=0)
        other.lifetime, other.alpha = 4, 0.5
        self.lib.mu_pt_move_record(ctypes.byref(other), ctypes.byref(h.host))
        self.assertEqual(other.alpha, f32(0.5 + f32(0.2)))                 # 0x8089 fades below 4 steps, not 5

    def test_impack01_draws_no_sprite(self):
        """The Panda's Impack01 0x7efa/1: RenderParticles' subtype table sends it past the sprite."""
        p = self.create(Host([0] * 12), (0x7efa, 1))
        self.assertEqual((p.scale, p.start[0]), (f32(0.1), f32(0.1)))
        call = self.pt.RenderCall()
        bm = self.pt.Bitmap(64.0, 64.0, 3)
        self.assertEqual(self.lib.mu_pt_render_record(ctypes.byref(p), ctypes.byref(bm), 0, 0.0, 0,
                                                      ctypes.byref(call)), 1)
        self.assertEqual(call.sprites, 0)

    def test_arrow_kinds(self):
        """0x615's sparks live 5 steps with alpha = LifeTime / 5; 0x617's trails fly along the angle argument."""
        h = Host([7])
        p = self.create(h, (0x8082, 8), scale=0.35)
        self.assertEqual((p.lifetime, p.initial_lifetime, p.alpha), (5, 5, 1.0))
        p.lifetime = 3
        self.lib.mu_pt_move_record(ctypes.byref(p), ctypes.byref(h.host))
        self.assertEqual((p.alpha, p.scale), (f32(3 / 5), f32(f32(0.35) - f32(0.018))))
        pt = self.pt
        q = pt.Particle()
        F3 = ctypes.c_float * 3
        self.lib.mu_pt_create_record(ctypes.byref(q), ctypes.byref(Host([0, 3]).host), 0x85fb, F3(0.0, 0.0, 0.0),
                                     F3(0.0, 1.0, 0.0), F3(0.5, 0.2, 1.0), 2, 0.1, -1, 0)
        self.assertEqual((q.lifetime, list(q.angle)), (20, [0.0, 0.0, 0.0]))
        self.assertEqual(list(q.velocity), [0.0, f32(7.3), 0.0])           # rand_range(7, 10, 10) = 73 / 10


class RegistryFunctors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(ROOT/'reconstructed/combat')], check=True, capture_output=True)
        import validate_skill_fx as fx
        import validate_render_effects10 as v
        cls.fx, cls.Pass = fx, v.Pass
        cls.lib = v.bind(fx.load_library(ROOT/f'reconstructed/combat/libcombat.{SUFFIX}'))

    def passes(self, type_, blend_mesh=-1, time=0.0):
        e = self.fx.Effect()
        e.type, e.blend_mesh, e.alpha, e.blend_light, e.velocity = type_, blend_mesh, 0.5, 1.0, 0.3
        out = (self.Pass * 8)()
        n = self.lib.mu_sfx_arrow_render_passes(ctypes.byref(e), time, ctypes.byref(out))
        return [out[i] for i in range(n)], self.lib.mu_sfx_arrow_tick_speed(ctypes.byref(e))

    def test_lightning_arrow_glows(self):
        """0x615: mesh 1 plain then chrome-additive, the glow meshes 0, 2 (elec_light on the 0x8551 strip) and 3
        additive (0x42), none through RenderBody."""
        passes, speed = self.passes(0x615, time=60.0)
        self.assertEqual([(p.mesh, p.flags) for p in passes], [(1, 2), (1, 0x44), (0, 0x42), (2, 0x42), (3, 0x42)])
        self.assertEqual((passes[3].texture, passes[3].u, passes[3].v), (0x8551, f32(2 * f32(1 / 6)), 0.0))
        self.assertEqual([round(c, 6) for c in passes[4].color], [0.25, 0.45, 1.0])
        self.assertEqual((passes[0].alpha, speed), (0.5, f32(0.3)))

    def test_imperial_arrow_and_the_others(self):
        passes, _ = self.passes(0x617, blend_mesh=3)
        self.assertEqual([p.mesh for p in passes], [2, 2, 5, 4, 0, 1, 3])
        self.assertEqual((passes[0].select, passes[1].flags), (3, 6))
        self.assertEqual(len(self.passes(0x613)[0]), 4)
        self.assertEqual(self.passes(0x614)[1], f32(0.003))
        self.assertEqual(len(self.passes(0x616)[0]), 3)
        self.assertEqual(self.passes(0x612)[0], [])                       # not registered here: RenderBody


class DemonSession(unittest.TestCase):
    """The Demon pet in a synthetic world: its Clud64 and firehik03 particles are created, none unsupported."""

    def test_demon_particles(self):
        subprocess.run(['make', '-C', str(ROOT/'native'), 'build/mu-walk'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = write_combat_world(Path(tmp)/'game')
            write_pet_models(root)
            out = Path(tmp)/'out'
            out.mkdir()
            p = subprocess.run([str(ROOT/'native/build/mu-walk'), '--game-root', str(root), '--headless', '--backend',
                                'soft', '--no-audio', '--no-env', '--width', '64', '--height', '64', '--every', '40',
                                '--out-dir', str(out), '--tile', '120,120', '--frames', '40', '--helper', 'demon'],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr[-2000:])
        rows = [json.loads(x) for x in p.stdout.splitlines() if x.startswith('{')]
        particles = next(r for r in rows if r.get('particles') is True)
        pets = next(r['pets'] for r in rows if isinstance(r.get('pets'), dict))
        self.assertGreater(pets['particles'], 0)
        self.assertEqual(pets['particles_kept'], pets['particles'])        # was 0: every request unsupported
        self.assertEqual(particles['unsupported'], 0)


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions_and_compiled_mutants(self):
        """validate_render_effects10: the pet and arrow particle kinds, the registry functors, the arc skill's
        create and the ground skills' MoveEffect test."""
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects10.py'), '--cases', '2',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            r = json.loads(report.read_text())
        self.assertTrue(r['all_equal'])
        self.assertTrue(r['all_mutants_caught'])
        self.assertEqual(len(r['mutants']), 44)
        self.assertEqual(r['instruction_cases'], 106)


if __name__ == '__main__':
    unittest.main()
