"""RENDER-EFFECTS-011: the bows' remaining particle kinds and effects, RenderEffects' case 0x45e and the ground
skills' effect 0x70c.

Portable: worked examples on reconstructed/particles and reconstructed/combat through ctypes (the validators'
structures), and bow 0x1304 (arrow 0x45e) in a synthetic world. Private (MU_RECOVERY_INTEGRATION=1): the short
original-instruction run of scripts/validate_render_effects11.py with its compiled mutants."""
import ctypes
import json
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
import native_fixtures as nf

SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
F3 = ctypes.c_float * 3


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


class Host:
    """rand() from a list, a terrain height of 0, one owner (position and live byte) and the move's CreateParticle."""

    def __init__(self, values, alive=1):
        import validate_particles as pt
        self.values, self.calls, self.alive, self.created = list(values), 0, alive, []
        self.owner = [100.0, 200.0, 300.0]

        def rand(ctx):
            r = self.values[self.calls % len(self.values)]
            self.calls += 1
            return r

        def owner(ctx, index, out):
            out[0], out[1], out[2] = self.owner

        def create(ctx, kind, position, angle, light, subtype, scale):
            self.created.append((kind, list(position[:3]), list(light[:3]), subtype, scale))
            return 1

        def zero(*a):
            return 0.0
        self.fns = (pt.RAND_FN(rand), pt.HEIGHT_FN(zero), pt.OWNER_FN(owner), pt.BITMAP_HEIGHT_FN(zero),
                    pt.CLOUD_OWNER_FN(lambda c, o, r: 1), pt.SOUND_FN(lambda c, i: None),
                    pt.LIGHT_FN(lambda c, x, y, rgb, r: None), pt.OWNER_LIVE_FN(lambda c, o: self.alive),
                    pt.PT_CREATE_FN(create))
        self.host = pt.Host(None, self.fns[0], self.fns[1], self.fns[2], 0, 0.0, 0.1, 1, 6, self.fns[3], self.fns[4],
                            self.fns[5], self.fns[6], F3(0.0, 0.0, 0.0), self.fns[7], self.fns[8])


class ParticleKinds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(ROOT/'reconstructed/particles')], check=True, capture_output=True)
        import validate_particles as pt
        cls.pt = pt
        cls.lib = pt.load_library(ROOT/f'reconstructed/particles/libclient_particles.{SUFFIX}')

    def create(self, host, kind, position=(10.0, 20.0, 30.0), light=(0.6, 0.4, 0.2), scale=0.5, owner=-1,
               angle=(0.0, 0.0, 0.0)):
        p = self.pt.Particle()
        ok = self.lib.mu_pt_create_record(ctypes.byref(p), ctypes.byref(host.host), kind[0], F3(*position),
                                          F3(*angle), F3(*light), kind[1], scale, owner, 0)
        self.assertEqual(ok, 1)
        return p

    def move(self, p, host):
        return self.lib.mu_pt_move_record(ctypes.byref(p), ctypes.byref(host.host))

    def render(self, p):
        call = self.pt.RenderCall()
        bm = self.pt.Bitmap(64.0, 64.0, 3)
        drawn = self.lib.mu_pt_render_record(ctypes.byref(p), ctypes.byref(bm), 0, 0.0, 0, ctypes.byref(call))
        return drawn, call

    def test_admitted_kinds(self):
        """The sixteen kinds are admitted; neighbours stay refused."""
        kinds = [(0x7f78, 5), (0x83b3, 1), (0x8155, 2), (0x7f5a, 0x18), (0x7f5a, 0x4e), (0x7f5a, 0x7a),
                 (0x8085, 0x11), (0x810c, 0), (0x83b8, 2), (0x8084, 0x1e), (0x8184, 1), (0x8081, 0), (0x8082, 0),
                 (0x8083, 0), (0x7f5a, 0x6d), (0x8108, 3)]
        for kind in kinds:
            self.assertEqual(self.lib.mu_pt_kind_supported(*kind), 1, kind)
        for kind in [(0x7f78, 6), (0x810c, 1), (0x8184, 3), (0x7f5a, 0x19), (0x8108, 4), (0x83b8, 1)]:
            self.assertEqual(self.lib.mu_pt_kind_supported(*kind), 0, kind)

    def test_lighting_mega_keeps_its_colour(self):
        """0x8081..0x8083/0 (0x60e's sparks): light 0 at creation, the colour kept at +0x7c; alpha -0.15 a step
        lights it, and it dies below 0.1."""
        h = Host([90])
        p = self.create(h, (0x8082, 0))
        self.assertEqual((p.lifetime, p.rotation, p.alpha), (5, 90.0, 1.0))
        self.assertEqual(list(p.light), [0.0, 0.0, 0.0])
        self.assertEqual([p.field_7c, p.field_80, p.field_84], [f32(0.6), f32(0.4), f32(0.2)])
        self.move(p, h)
        a = f32(1.0 - f32(0.15))
        self.assertEqual(list(p.light), [f32(f32(0.6) * a), f32(f32(0.4) * a), f32(f32(0.2) * a)])
        p.alpha = f32(0.2)
        self.move(p, h)
        self.assertEqual(p.live, 0)

    def test_firehik03_dies_with_its_owner(self):
        """0x8085/0x11 (0x45d's flame) flies 300 units a second along its angle while the owner lives; a dead or
        missing owner ends it at once."""
        h = Host([5])
        p = self.create(h, (0x8085, 0x11), owner=0)
        self.assertEqual((p.lifetime, p.initial_lifetime, p.rotation), (10, 10, 5.0))
        p.moving = 0
        self.move(p, h)
        self.assertEqual(p.live, 1)
        self.assertEqual(list(p.position), [10.0, f32(20.0 - f32(0.1 * 300.0)), 30.0])   # (0, -1, 0) x 30
        self.assertEqual(list(p.light), [f32(0.8), f32(0.9), 1.0])
        dead = Host([5], alive=0)
        q = self.create(dead, (0x8085, 0x11), owner=0)
        self.move(q, dead)
        self.assertEqual((q.live, q.lifetime), (0, -1))
        r = self.create(h, (0x8085, 0x11))
        self.move(r, h)
        self.assertEqual(r.live, 0)                                        # no owner

    def test_purple_star_lifetime_and_end(self):
        """0x810c/0 (0x610's glints): jitter from lifetime 30 on; the lifetime loses 0.1 (truncated: one step)
        besides the tail's step, so it ends at half its life; a shrunk star dies."""
        h = Host([0, 10, 20, 180])
        p = self.create(h, (0x810c, 0), scale=0.4)
        self.assertEqual((p.lifetime, p.rotation), (50, 180.0))
        self.assertEqual(list(p.velocity), [-1.0, 0.0, 1.0])               # rand_range(-1, 1, 10)
        self.move(p, h)
        self.assertEqual(p.lifetime, 48)
        p.scale = f32(0.001)
        self.move(p, h)
        self.assertEqual(p.live, 0)

    def test_smoke_trail_spawns_toward_its_owner(self):
        """0x7f5a/0x6d (0x45e's smoke): an owned record asks for an unowned one halfway to its owner each step."""
        h = Host([3, 5])
        p = self.create(h, (0x7f5a, 0x6d), position=(0.0, 0.0, 0.0), owner=0)
        self.assertEqual((p.lifetime, p.initial_lifetime), (10, 10))
        p.moving = 0
        self.move(p, h)
        self.assertEqual(len(h.created), 1)
        kind, position, light, subtype, scale = h.created[0]
        self.assertEqual((kind, subtype), (0x7f5a, 0x6d))
        self.assertEqual(position, [50.0, 100.0, 150.0])
        self.assertEqual(light, [f32(0.3), f32(0.4), f32(0.5)])
        self.assertEqual(scale, f32(f32(5 % 8 * f32(0.07)) + f32(0.8)))
        q = self.create(h, (0x7f5a, 0x6d))
        self.move(q, h)
        self.assertEqual(len(h.created), 1)                                # unowned: no trail

    def test_render_rules(self):
        """Smoke_line/1 draws its light (its 0x83b3/6 sibling takes alpha); Spark04/2 and firehik01/0x1e take alpha;
        Flare/5 draws nothing at lifetime 60."""
        h = Host([1, 2, 3, 4, 5])
        line = self.create(h, (0x83b3, 1))
        line.alpha = 0.5
        self.assertEqual(list(self.render(line)[1].sprite.light), [f32(0.6), f32(0.4), f32(0.2)])
        spark = self.create(h, (0x8155, 2))
        spark.alpha = 0.5
        self.assertEqual(list(self.render(spark)[1].sprite.light), [f32(0.3), f32(0.2), f32(0.1)])
        flare = self.create(h, (0x7f78, 5))
        self.assertEqual(self.render(flare)[1].sprites, 1)
        flare.lifetime = 60
        drawn, call = self.render(flare)
        self.assertEqual((drawn, call.sprites), (1, 0))


class Effects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(ROOT/'reconstructed/combat')], check=True, capture_output=True)
        import validate_skill_fx as fx
        import validate_render_effects11 as v
        cls.fx = fx
        cls.lib = v.bind_render(fx.load_library(ROOT/f'reconstructed/combat/libcombat.{SUFFIX}'))

    def create(self, kind, key=0, scale=0.5, angle=(0.0, 0.0, 30.0)):
        e = self.fx.Effect()
        info = self.fx.Info()
        info.key = key
        ok = self.lib.mu_sfx_effect_create(ctypes.byref(e), kind[0], kind[1], F3(10.0, 20.0, 30.0), F3(*angle),
                                           F3(1.0, 1.0, 1.0), -1, scale, ctypes.byref(info), None)
        self.assertEqual(ok, 1)
        return e

    def test_ring_grows_from_the_key(self):
        """0x477/3 and /4: scale = info key x 0.05, pitch 90, the angle argument's yaw; growth capped at 1.5/2.5."""
        e = self.create((0x477, 3), key=10)
        self.assertEqual((e.lifetime, e.scale, e.gravity, e.blend_mesh), (15, f32(10 * f32(0.05)), f32(0.01), -2))
        self.assertEqual(list(e.angle), [90.0, 0.0, 30.0])
        self.assertEqual(e.position[2], f32(f32(30.0 + 50.0) - 50.0))
        e.scale = 1.49
        self.lib.mu_sfx_effect_move(ctypes.byref(e), None)
        self.assertEqual((e.scale, e.angle[1]), (1.5, 45.0))
        self.assertEqual(self.create((0x477, 4), key=0).scale, 0.0)

    def test_power_ring_and_landing_mark(self):
        """0x611/0 keeps the scale argument and fades as life / 10; 0x70c pulses at life 30."""
        e = self.create((0x611, 0), scale=0.5)
        self.assertEqual((e.lifetime, e.field_70, e.scale, e.angle[0]), (10, 10, 0.5, -90.0))
        e.lifetime = 7
        self.lib.mu_sfx_effect_move(ctypes.byref(e), None)
        self.assertEqual((e.scale, e.alpha), (0.75, f32(7 / 10)))
        m = self.create((0x70c, 0))
        self.assertEqual((m.lifetime, m.field_70, m.scale, list(m.light)), (50, 20, 0.0, [1.0, 1.0, 1.0]))
        for life, t in ((30, 20.0), (40, 0.0), (21, 38.0)):                # t = |20 - (life - 30) x 2|
            m.lifetime = life
            self.lib.mu_sfx_effect_move(ctypes.byref(m), None)
            x = f32(1.0 - f32(t / 20.0))
            self.assertEqual(m.field_d8, f32(x * x), life)

    def test_gunbow_render_case(self):
        """RenderEffects' 0x45e: twice the tick, two draws for the arrows' subtypes, the decal only for 3..7."""
        e = self.fx.Effect()
        e.type, e.velocity, e.lifetime = 0x45e, 0.25, 30
        speed, decal, draws = ctypes.c_float(), ctypes.c_int(), ctypes.c_int()
        results = {}
        for sub in (0, 2, 0x63, 3, 7, 9):
            e.subtype = sub
            self.assertEqual(self.lib.mu_sfx_arrow_render_extras(ctypes.byref(e), None, ctypes.byref(speed),
                                                                 ctypes.byref(decal), ctypes.byref(draws)), 1)
            results[sub] = (draws.value, decal.value)
        self.assertEqual(speed.value, 0.5)
        self.assertEqual(results, {0: (2, 0), 2: (2, 0), 0x63: (2, 0), 3: (1, 1), 7: (1, 1), 9: (2, 0)})
        e.type = 0x45d
        self.assertEqual(self.lib.mu_sfx_arrow_render_extras(ctypes.byref(e), None, ctypes.byref(speed),
                                                             ctypes.byref(decal), ctypes.byref(draws)), 0)


class GunbowSession(unittest.TestCase):
    """Bow 0x1304 (arrow 0x45e) in a synthetic world: each drawn frame asks for 0x7f5a/0x6d and 0x8108/3 owned by
    the arrow, and they are created (not unsupported)."""

    def test_render_time_particles(self):
        subprocess.run(['make', '-C', str(ROOT/'native'), 'build/mu-walk'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = write_combat_world(Path(tmp)/'game')
            (root/'Data/Skill').mkdir(exist_ok=True)
            (root/'Data/Skill/absolute_gunbow_arrow.bmd').write_bytes(nf.synthetic_layout(413, actions=1, keys=(8,)))
            placement = Path(tmp)/'actors.txt'
            placement.write_text('actor 3 122 120 0 label spider\n')
            out = Path(tmp)/'out'
            out.mkdir()
            p = subprocess.run([str(ROOT/'native/build/mu-walk'), '--game-root', str(root), '--headless', '--backend',
                                'soft', '--no-audio', '--no-items', '--no-players', '--tile', '120,120', '--placement',
                                str(placement), '--combat', '--combat-weapon', 'bow', '--combat-bow', '0x1304',
                                '--class', '2', '--combat-script', '2:skill:24:spider;3:stop', '--frames', '30',
                                '--every', '1', '--width', '96', '--height', '64', '--out-dir', str(out)],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr[-2000:])
        rows = [json.loads(x) for x in p.stdout.splitlines() if x.startswith('{')]
        summary = next(r for r in rows if r.get('combat') is True)
        kinds = next(r['combat_unsupported'] for r in rows if 'combat_unsupported' in r)
        self.assertGreaterEqual(summary['arrows'], 3)
        self.assertGreater(summary['particles_created'], 0)
        self.assertFalse([k for k in kinds if k[0] == 'p'])


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions_and_compiled_mutants(self):
        """validate_render_effects11: the bows' particle kinds and effects, RenderEffects' 0x45e and effect 0x70c."""
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects11.py'), '--cases', '2',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            r = json.loads(report.read_text())
        self.assertTrue(r['all_equal'])
        self.assertTrue(r['all_mutants_caught'])
        self.assertEqual(len(r['mutants']), 75)
        self.assertEqual(r['instruction_cases'], 176)


if __name__ == '__main__':
    unittest.main()
