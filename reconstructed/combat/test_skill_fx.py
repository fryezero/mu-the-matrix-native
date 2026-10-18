"""Portable checks of reconstructed/combat/skill_fx.c and the hero's voices (NATIVE-COMBAT-002).

Worked examples and independent Python statements of the client rules,
without client bytes. The instruction-level comparison with the client is
scripts/validate_skill_fx.py (Unicorn); a short private run of it is gated on
MU_RECOVERY_INTEGRATION=1 with the pinned evidence present.
"""
import ctypes
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_skill_fx as v  # noqa: E402  (ctypes layouts and the call recorder; no client bytes)

SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
TEXT = ROOT/'evidence/x86-text-capture-09/client-text.bin'
DATA = ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
F3 = ctypes.c_float*3


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def rotate_z(angle, vec):
    """AngleMatrix(0, 0, angle) * vec (Rz only), binary32 steps."""
    r = f32(f32(angle)*f32(0.017453292))
    s, c = f32(math.sin(r)), f32(math.cos(r))
    x = f32(f32(vec[0]*c) + f32(vec[1]*-s))
    y = f32(f32(vec[0]*s) + f32(vec[1]*c))
    return x, y, f32(vec[2])


class Lib(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        cls.lib = v.load_library(HERE/f'libcombat.{SUFFIX}')

    def case(self, rands=(0,)*40, height=0.0, objects=()):
        return v.Case(None, list(objects), list(rands), height)


class EffectTests(Lib):
    def create(self, kind, pos=(1000.0, 2000.0, 150.0), angle=(0.0, 0.0, 45.0), owner=-1, rands=(5,)*40,
               objects=(), word4=0):
        case = self.case(rands, objects=objects)
        info = v.Info()
        info.word4 = word4
        e = v.Effect()
        env = case.env(serial=7)
        ok = self.lib.mu_sfx_effect_create(ctypes.byref(e), kind[0], kind[1], F3(*pos), F3(*angle), F3(1, 1, 1),
                                           owner, 0.0, ctypes.byref(info), ctypes.byref(env))
        self.assertEqual(ok, 1)
        return e, case

    def test_arrow_starts_at_the_bow_and_flies_70_per_step(self):
        e, _ = self.create((0x43b, 0))
        off = rotate_z(45.0, (-10.0, -60.0, 135.0))
        self.assertAlmostEqual(e.position[0], 1000.0 + off[0], places=3)
        self.assertAlmostEqual(e.position[1], 2000.0 + off[1], places=3)
        self.assertEqual(e.position[2], 285.0)
        self.assertEqual((e.lifetime, e.blend_mesh, list(e.direction)), (30, 1, [0.0, -70.0, 0.0]))
        self.assertAlmostEqual(e.scale, 0.8, places=6)
        self.assertEqual(e.velocity, 1.0)
        # the skills 0x7e7, 0x7fc, 0x7fd, 0x7fe, 0x2d7 (info word 4) skip the bow offset
        e2, _ = self.create((0x43b, 0), word4=0x2d7)
        self.assertEqual(list(e2.position), [1000.0, 2000.0, 150.0])

    def test_arrow_motion_and_lifetime(self):
        e, case = self.create((0x43b, 0))
        before = list(e.position)
        env = case.env()
        self.lib.mu_sfx_effect_move(ctypes.byref(e), ctypes.byref(env))
        step = rotate_z(45.0, (0.0, -70.0, 0.0))
        self.assertAlmostEqual(e.position[0], before[0] + step[0], places=3)
        self.assertAlmostEqual(e.position[1], before[1] + step[1], places=3)
        # trail: a Fire01 particle (subtype 0) and a terrain light (0.8, 0.5, 0.2) * L of range 2
        kinds = [c[0] for c in case.c_calls]
        self.assertEqual(kinds[:3], ['light', 'particle', 'check'])
        self.assertEqual(case.c_calls[1][1], 0x7f3c)
        # LifeTime is tested before the decrement: 31 steps, deleted on the last
        steps = 1
        while e.live:
            self.lib.mu_sfx_effect_move(ctypes.byref(e), ctypes.byref(env))
            steps += 1
        self.assertEqual(steps, 31)

    def test_fire_ball_decrements_first(self):
        e, case = self.create((0x413, 1), rands=(1,)*40)
        self.assertEqual((e.lifetime, e.position[2]), (60, 270.0))
        self.assertAlmostEqual(e.scale, 0.9, places=6)            # (8 + 1 % 4) * 0.1
        env = case.env()
        steps = 0
        while e.live:
            self.lib.mu_sfx_effect_move(ctypes.byref(e), ctypes.byref(env))
            steps += 1
        self.assertEqual(steps, 60)
        self.assertEqual(e.blend_light, 0.0)                     # the blend mesh goes dark

    def test_energy_ball_light_follows_its_lifetime(self):
        e, case = self.create((0x7f2b, 0))
        self.assertEqual((e.lifetime, e.position[2], list(e.direction)), (20, 250.0, [0.0, -60.0, 0.0]))
        env = case.env()
        self.lib.mu_sfx_effect_move(ctypes.byref(e), ctypes.byref(env))
        lum = f32(20*f32(0.2))
        particles = [c for c in case.c_calls if c[0] == 'particle']
        self.assertEqual([(p[1], p[6]) for p in particles], [(0x7f2b, 1.0), (0x7f26, 4.0)])
        light = [c for c in case.c_calls if c[0] == 'light'][0]
        self.assertEqual(light[3], [f32(lum*f32(0.2)), f32(lum*f32(0.4)), lum])
        self.assertEqual(light[4], 2)

    def test_spell_hit_check(self):
        target = v.Object(1, 1, 0, F3(1050.0, 2000.0, 0.0))
        e, case = self.create((0x413, 1), owner=0, objects=[target])
        e.position[0], e.position[1] = 1000.0, 2000.0
        env = case.env(report_checks=0)
        self.lib.mu_sfx_check_magic(ctypes.byref(e), ctypes.byref(env))
        self.assertEqual(e.lifetime, 1)                          # within 100 in x/y: it ends next step
        stones = [c for c in case.c_calls if c[0] == 'effect']
        self.assertEqual(len(stones), 2)
        self.assertTrue(all(s[1] in (0x419, 0x41a) for s in stones))
        far, case2 = self.create((0x7f2b, 0), owner=0, objects=[v.Object(1, 1, 0, F3(1101.0, 2000.0, 0.0))])
        far.position[0], far.position[1] = 1000.0, 2000.0
        env = case2.env(report_checks=0)
        self.lib.mu_sfx_check_magic(ctypes.byref(far), ctypes.byref(env))
        self.assertEqual(far.lifetime, 20)

    def test_area_effects(self):
        circle, _ = self.create((0x41c, 0))
        light, _ = self.create((0x41d, 0))
        inferno, _ = self.create((0x457, 0))
        self.assertEqual((circle.lifetime, light.lifetime, inferno.lifetime), (45, 40, 15))
        self.assertEqual((circle.blend_mesh, inferno.blend_mesh), (0, -2))
        laser, _ = self.create((0x421, 0))
        self.assertEqual((laser.lifetime, laser.field_80), (1, 0x80))   # RenderObject draws it bright
        swirl, _ = self.create((0x454, 0))
        self.assertEqual((swirl.lifetime, swirl.serial), (25, 7))


class ParticleTests(Lib):
    def test_fire_trail(self):
        rands = [3, 70, 7] + [0]*10
        case = self.case(rands)
        p = v.Particle()
        env = case.env()
        self.lib.mu_sfx_particle_create(ctypes.byref(p), 0x7f3c, F3(0, 0, 100), F3(0, 0, 0), F3(1, 1, 1), 0, 5.0, -1,
                                        0, ctypes.byref(env))
        self.assertEqual(p.lifetime, 24)
        self.assertEqual(p.velocity[1], f32(f32(-(3 % 16 + 32))*f32(0.1)))
        self.assertEqual(p.scale, f32(f32(70 % 64 + 128)*f32(0.01)))   # subtype 0 ignores the scale argument
        self.assertEqual(p.rotation, 7.0)
        z = p.position[2]
        self.lib.mu_sfx_particle_move(ctypes.byref(p), 0.1)
        g = f32(0.004)
        self.assertEqual(p.frame, (23 - 24) // 6 if (23 - 24) >= 0 else int((23 - 24)/6))
        self.assertAlmostEqual(p.position[2], z + g*10, places=4)
        bitmap = v.BitmapInfo(64.0, 64.0, 3)
        sprite = v.Sprite()
        self.assertEqual(self.lib.mu_sfx_particle_render(ctypes.byref(p), ctypes.byref(bitmap), 0, ctypes.byref(sprite)), 1)
        self.assertEqual(sprite.width, f32(f32(64.0*p.scale)*0.25))    # the 4-cell strip
        self.assertEqual((sprite.uw, sprite.additive), (0.25, 1))

    def test_spark_burst_dies_below_0_2(self):
        case = self.case([0, 0, 0])
        p = v.Particle()
        env = case.env()
        self.lib.mu_sfx_particle_create(ctypes.byref(p), 0x7f26, F3(0, 0, 0), F3(0, 0, 0), F3(1, 1, 1), 1, 6.0, -1, 0,
                                        ctypes.byref(env))
        lives = 0
        while self.lib.mu_sfx_particle_move(ctypes.byref(p), 0.1):
            lives += 1
            p.lifetime = 2      # keep the lifetime out of the way: the scale ends it
        self.assertEqual(lives, 3)   # 6 -> 4 -> 2 -> 0 (< 0.2: not live)


class JointTests(Lib):
    def test_first_tail_uses_the_previous_width(self):
        j = v.Joint()
        j.scale = 40.0
        case = self.case()
        env = case.env()
        self.lib.mu_sfx_joint_create(ctypes.byref(j), 0x7fd8, F3(0, 0, 0), F3(0, 0, 0), F3(0, 0, 0), 1, -1, 5.0, 0, 0,
                                     0, 0xffff, 0, ctypes.byref(env))
        self.assertEqual(j.scale, 5.0)
        self.assertEqual(j.tails[0], -20.0)          # corner 0 from the old width 40
        self.assertEqual((j.lifetime, j.max_tails, j.render_type), (12, 2, 1))

    def test_evil_spirit_joint_and_ribbon(self):
        j = v.Joint()
        case = self.case([16]*40, height=0.0, objects=[v.Object(1, 1, 0, F3(0.0, 0.0, 0.0))])
        env = case.env(serial=3)
        self.lib.mu_sfx_joint_create(ctypes.byref(j), 0x7fd3, F3(0, 0, 100), F3(0, 0, 0), F3(0, 0, 90), 0, 0, 20.0,
                                     1, 9, 0, 0xffff, 0, ctypes.byref(env))
        self.assertEqual((j.lifetime, j.velocity, j.max_tails, j.render_type, j.serial), (49, 70.0, 6, 3, 3))
        for _ in range(3):
            self.lib.mu_sfx_joint_move(ctypes.byref(j), ctypes.byref(env), 0.1, 0, 0, 0)
        self.assertEqual(j.num_tails, 3)
        color = F3()
        rt = ctypes.c_int32()
        quads = (v.JointQuad*16)()
        n = self.lib.mu_sfx_joint_render(ctypes.byref(j), 0, color, ctypes.byref(rt), quads, 16)
        self.assertEqual((n, rt.value), (6, 3))     # two faces per segment, (ZERO, ONE_MINUS_SRC_COLOR)
        self.assertEqual(quads[0].uv[0], f32(3/5))   # u = (tails - i) / (max - 1)


class VoiceTests(Lib):
    def state(self, **kw):
        st = v.PlayerState()
        for k, value in kw.items():
            setattr(st, k, value)
        return st

    def test_hit_actions_and_voices(self):
        act, snd = ctypes.c_int32(), ctypes.c_int32()
        r = (ctypes.c_int32*4)(2, 0, 0, 0)
        for kw, action in ((dict(), 0x134), (dict(state_59=1), 0x136), (dict(state_5a=1), 0x138),
                           (dict(state_72=1), 0x13a)):
            self.lib.mu_player_shock(ctypes.byref(self.state(**kw)), r, 4, ctypes.byref(act), ctypes.byref(snd))
            self.assertEqual(act.value, action)
        self.lib.mu_player_shock(ctypes.byref(self.state(class_byte=1)), r, 4, ctypes.byref(act), ctypes.byref(snd))
        self.assertEqual(snd.value, 0x69 + 2 % 3)
        self.lib.mu_player_shock(ctypes.byref(self.state(class_byte=2, class_check=1)), r, 4, ctypes.byref(act),
                                 ctypes.byref(snd))
        self.assertEqual(snd.value, 0x6d + 2 % 2)
        self.lib.mu_player_shock(ctypes.byref(self.state(field_3324=0.001)), r, 4, ctypes.byref(act), ctypes.byref(snd))
        self.assertEqual(snd.value, -1)

    def test_death_actions_and_voices(self):
        act = ctypes.c_int32()
        snds = (ctypes.c_int32*2)()
        r = (ctypes.c_int32*4)()
        self.lib.mu_player_die(ctypes.byref(self.state(class_byte=1)), r, 4, ctypes.byref(act), snds)
        self.assertEqual((act.value, list(snds)), (0x142, [0x6c, -1]))
        self.lib.mu_player_die(ctypes.byref(self.state(class_byte=13, class_check=1, transform=0x1a25)), r, 4,
                               ctypes.byref(act), snds)
        self.assertEqual((act.value, list(snds)), (0x146, [0x6e, 0x2b9]))
        self.assertTrue(self.lib.mu_class_check(2) and self.lib.mu_class_check(14) and not self.lib.mu_class_check(1))

    def test_attack_sounds(self):
        snd = ctypes.c_int32()
        r = (ctypes.c_int32*2)(1, 0)
        cases = [(1, 0x12e6, -1, 0x55), (2, 0x12ee, -1, 0x56), (0, 0x12f3, -1, 0x76), (0, 0xaf0, -1, 0x3e),
                 (0, 0xae6, -1, 0x3d), (0, -1, 0xae6, 0x3d), (0, -1, -1, -1)]
        for bow, w0, w1, expected in cases:
            self.lib.mu_player_attack_sound(ctypes.byref(self.state()), bow, w0, w1, 0, r, 2, ctypes.byref(snd))
            self.assertEqual(snd.value, expected, (bow, hex(w0), hex(w1)))
        self.lib.mu_player_attack_sound(ctypes.byref(self.state()), 0, 0xae6, -1, 0x49, r, 2, ctypes.byref(snd))
        self.assertEqual(snd.value, -1)


class Private(unittest.TestCase):
    @unittest.skipUnless(PRIVATE and TEXT.exists() and DATA.exists(), 'set MU_RECOVERY_INTEGRATION=1 with the evidence')
    def test_client_comparison(self):
        try:
            import unicorn  # noqa: F401
        except ImportError:
            self.skipTest('Unicorn is not installed')
        result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_skill_fx.py'), '--text', str(TEXT),
                                 '--data', str(DATA), '--cases', '60'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])


if __name__ == '__main__':
    unittest.main()
