"""The joint pool: CreateJoint, MoveJoint, RenderJoints (NATIVE-JOINT-001).

Portable: the library through ctypes with the validator's structures (scripts/validate_joints.py); worked
examples restate the client branches of docs/research/client-joints.md with fixed rand() answers and compare bit
for bit (binary32 arithmetic in Python through struct), and NATIVE-COMBAT-002's entry points (skill_fx) give the
same records as the module (one implementation).
Private (MU_RECOVERY_INTEGRATION=1 and the restored text/data): a short Unicorn comparison through
scripts/validate_joints.py.
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
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
LIB = HERE/f'libclient_joints.{SUFFIX}'
F3 = ctypes.c_float*3


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


def setUpModule():
    subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)


def vj():
    import validate_joints
    return validate_joints


class Fixed:
    """rand() answers from a list, objects with a light, the calls the code reports."""

    def __init__(self, values, world_time=0.0, light=(0.59, 0.59, 1.0)):
        v = vj()
        self.values, self.rands, self.calls = list(values), 0, []
        o = v.Object()
        o.live = o.visible = 1
        for k in range(3):
            o.light[k] = f32(light[k])
        self.objects = (v.Object*1)(o)

        def rand(ctx):
            r = self.values[self.rands % len(self.values)]
            self.rands += 1
            return r

        def height(ctx, x, y):
            return 0.0

        def obj(ctx, index):
            return ctypes.addressof(self.objects[0]) if index == 0 else None

        def call(ctx, cp):
            c = cp.contents
            self.calls.append((c.routine, c.type, list(c.position), c.scale, list(c.light), c.owner, c.angle[0],
                               c.subtype, c.range))
        self.keep = (v.RAND_FN(rand), v.HEIGHT_FN(height), v.OBJECT_FN(obj), v.CALL_FN(call))
        self.env = v.Env(None, *self.keep, 0, f32(world_time))


class JointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = vj()
        cls.lib = cls.v.load_library(LIB)

    def create(self, kind, rands, scale=1.0, angle=(0.0, 0.0, 0.0), position=(1000.0, 2000.0, 300.0), target=0,
               world_time=0.0, previous=None):
        v = self.v
        j = v.Joint()
        if previous:
            for k, val in previous.items():
                setattr(j, k, val)
        fx = Fixed(rands, world_time)
        ok = self.lib.mu_jt_create(ctypes.byref(j), kind[0], F3(*position), F3(*position), F3(*angle), kind[1], target,
                                   f32(scale), 0xffff, 0, 0, 0xffff, 0, ctypes.byref(fx.env))
        return j, ok, fx

    def test_supported_kinds(self):
        for sub in range(0x10, 0x1b):
            self.assertEqual(self.lib.mu_jt_kind_supported(0x7f7d, sub), 1)
        for kind in ((0x7f7d, 0), (0x7f7d, 0x1b), (0x7fd5, 5), (0x7fd6, 4), (0x7f79, 8)):
            self.assertEqual(self.lib.mu_jt_kind_supported(*kind), 0)

    def test_create_bolt_target_and_light(self):
        j, ok, fx = self.create((0x7f7d, 0x1a), [30, 170], scale=2.0)
        self.assertEqual((ok, j.live, j.type, j.tex_type, j.max_tails, j.lifetime), (1, 1, 0x7f7d, 0x7f7c, 50, 20))
        # target = start + R(angle 0) (rand % 100 - 50, rand % 100 - 50, -scale * 50)
        self.assertEqual(list(j.target_position), [f32(1000.0 - 20.0), f32(2000.0 + 20.0), f32(300.0 - 100.0)])
        self.assertEqual(list(j.light), [f32(0.59), f32(0.59), 1.0])   # the object's light
        self.assertEqual((j.render_type, j.faces, j.num_tails), (1, 3, 0))
        # 0x12/0x13: +-100 and an unscaled 300
        j, ok, fx = self.create((0x7f7d, 0x12), [30, 170], scale=2.0)
        self.assertEqual(list(j.target_position), [f32(1000.0 - 70.0), f32(2000.0 + 70.0), f32(300.0 - 300.0)])

    def test_create_width_zero_returns_early(self):
        j, ok, fx = self.create((0x7f7d, 0x10), [1], scale=0.0, previous={'max_tails': 7, 'lifetime': 3})
        self.assertEqual((ok, j.live, j.tex_type, j.max_tails, j.lifetime, fx.rands), (1, 1, 0x7f7c, 7, 3, 0))

    def test_ring_phase(self):
        j, ok, fx = self.create((0x7f7d, 0x16), [0], world_time=12345.9)
        self.assertEqual(j.phase, 12345 % 25)
        self.assertEqual(list(j.target_position), list(j.start))

    def test_spark_streak(self):
        j, ok, fx = self.create((0x7fd5, 0), [33, 5], scale=10.0)
        self.assertEqual((j.scale, j.velocity, j.lifetime, j.max_tails), (2.0, float(33 % 20 + 6), 5 % 8 + 8, 2))

    def move(self, j, rands, world_time=0.0):
        v = self.v
        fx = Fixed(rands, world_time)
        ok = self.lib.mu_jt_move(ctypes.byref(j), ctypes.byref(fx.env), ctypes.byref(v.MoveInputs(0.1, 0, 0, 0)))
        return ok, fx

    def test_bolt_rebuilds_from_the_start(self):
        j, ok, fx = self.create((0x7f7d, 0x19), [10, 20], scale=1.0)
        ok, fx = self.move(j, [123] + [7, 3]*60)
        # the start flash: CreateSprite(Shiny02, start, 1, light, NULL, rand % 360, blend 0, axes 4)
        self.assertEqual(fx.calls[0][:2], (0x01692eb7, 0x7f67))
        self.assertEqual(fx.calls[0][2], [1000.0, 2000.0, 300.0])
        self.assertEqual(fx.calls[0][3:], (1.0, [f32(0.59), f32(0.59), 1.0], -1, 123.0, 0, 4))
        # 49 tails (the walk's 49 shifts, the first one and the closing one, capped at max_tails - 1)
        self.assertEqual((j.num_tails, j.lifetime, j.scale), (49, 19, 1.0))
        # the last tail is the first step from the start: start + d + R(jitter), d = (target - start) / |.| * 10/50
        self.assertEqual(fx.rands, 1 + 2*24 + 2*15)   # the flash, then jitters at i = 1..24 and 30..44

    def test_ring_tails(self):
        j, ok, fx = self.create((0x7f7d, 0x14), [0], scale=1.0)
        ok, fx = self.move(j, [2, 4, 1, 1]*60, world_time=500.0)
        self.assertEqual(fx.calls, [])        # the rings create no sprite
        self.assertEqual(j.num_tails, 49)
        # the width while the points are laid: (LifeTime + 1) * 60 / 20, restored after
        self.assertEqual(j.scale, 1.0)
        self.assertEqual(fx.rands, 48*4)      # two radius jitters, the sign, the height per point

    def render(self, j, world_time):
        v = self.v
        out = []
        fns = (v.STATE_FN(lambda c, w, a: out.append(('state', w, a))), v.BIND_FN(lambda c, b: out.append(('bind', b))),
               v.COLOR_FN(lambda c, r, g, b: out.append(('color', f32(r), f32(g), f32(b)))),
               v.BEGIN_FN(lambda c, m: out.append(('begin', m))),
               v.TEX_FN(lambda c, s, t: out.append(('tex', f32(s), f32(t)))),
               v.VERTEX_FN(lambda c, p: out.append(('vertex', p[0], p[1], p[2]))),
               v.END_FN(lambda c: out.append(('end',))))
        n = self.lib.mu_jt_render(ctypes.byref(j), 0, f32(world_time), ctypes.byref(v.Gl(None, *fns)))
        return n, out

    def test_render_bolt_colour_and_texture_scroll(self):
        j, ok, fx = self.create((0x7f7d, 0x10), [0, 0])
        j.num_tails, j.lifetime = 3, 10
        n, out = self.render(j, 2250.0)
        self.assertEqual(n, 6)                                  # two faces per segment
        self.assertEqual(out[0], ('state', 0x0184aa2b, 0))      # render type 1: (ONE, ONE)
        self.assertEqual(out[1], ('color', f32(0.59), f32(0.59), 1.0))   # light * brightness
        self.assertEqual(out[2], ('bind', 0x7f7c))
        colours = [o for o in out if o[0] == 'color'][1:]
        f = f32(f32(f32(f32(10.0) / f32(3.0)) * f32(10.0)) * f32(0.08))   # (i + 10) / num_tails * LifeTime * 0.08
        self.assertEqual(colours[0][1], f32(f32(0.59) * f))
        t = f32(250 * f32(0.001))
        u0 = f32(f32(f32(3.0) / f32(49.0)) * 2.0)
        u0 = f32(f32(f32(t + 1.0) * f32(0.33)) + f32(u0 - t))
        self.assertEqual([o for o in out if o[0] == 'tex'][0], ('tex', u0, 1.0))

    def test_render_spark_keeps_the_colour(self):
        j, ok, fx = self.create((0x7fd5, 0), [0, 0])
        j.num_tails = 1
        n, out = self.render(j, 0.0)
        self.assertEqual(n, 2)
        self.assertEqual([o for o in out if o[0] == 'color'], [])   # 0x7fd5 sets no colour

    def test_skill_fx_wraps_the_module(self):
        # NATIVE-COMBAT-002's mu_sfx_joint_create is mu_jt_create: one implementation
        sf = self.v.sf
        combat = sf.load_library(ROOT/f'reconstructed/combat/libcombat.{SUFFIX}')
        for kind, scale in (((0x7fd8, 1), 5.0), ((0x7fd3, 0), 80.0), ((0x7f7d, 0x11), 1.0)):
            mine, ok, fx = self.create(kind, [5, 9], scale=scale, target=-1)
            theirs = self.v.Joint()
            fx2 = Fixed([5, 9])
            senv = sf.Env()
            senv.rand = sf.RAND_FN(lambda ctx, f=fx2: f.keep[0](None))
            combat.mu_sfx_joint_create(ctypes.byref(theirs), kind[0], F3(1000.0, 2000.0, 300.0),
                                       F3(1000.0, 2000.0, 300.0), F3(0.0, 0.0, 0.0), kind[1], -1, f32(scale), 0xffff,
                                       0, 0, 0xffff, 0, ctypes.byref(senv))
            self.assertEqual(bytes(theirs), bytes(mine))


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'set MU_RECOVERY_INTEGRATION=1')
class ClientComparison(unittest.TestCase):
    def test_unicorn_comparison(self):
        v = vj()
        text = Path(v.default_evidence('x86-text-capture-09/client-text.bin'))
        if not text.exists():
            self.skipTest('restored text capture not present')
        result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_joints.py'), '--cases', '60'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-2000:])


if __name__ == '__main__':
    unittest.main()
