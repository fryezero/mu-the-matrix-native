"""Legacy particles, sprites, blob shadow, bone helpers, object visuals (NATIVE-PARTICLE-001).

Portable: the library through ctypes with the validator's structures
(scripts/validate_particles.py); worked examples restate the client branches
of docs/research/client-particles.md with fixed rand() answers and compare
bit for bit (binary32 arithmetic in Python through struct).
Private (MU_RECOVERY_INTEGRATION=1 and the restored text/data): a short
Unicorn comparison through scripts/validate_particles.py.
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
LIB = HERE/f'libclient_particles.{SUFFIX}'


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


def setUpModule():
    subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)


def vp():
    import validate_particles
    return validate_particles


class Fixed:
    """rand() answers from a list, and a constant terrain height."""

    def __init__(self, values, height=0.0):
        self.values, self.calls, self.height = list(values), 0, f32(height)
        self.heights = []

    def host(self, world=0, world_time=0.0, dt=0.1, divisor=1, scene=6):
        v = vp()

        def rand(ctx):
            r = self.values[self.calls % len(self.values)]
            self.calls += 1
            return r

        def height(ctx, x, y):
            self.heights.append((x, y))
            return self.height

        def owner(ctx, index, out):
            out[0], out[1], out[2] = 100.0, 200.0, 300.0
        self.fns = (v.RAND_FN(rand), v.HEIGHT_FN(height), v.OWNER_FN(owner))
        return v.Host(None, *self.fns, world, f32(world_time), f32(dt), divisor, scene)


class ParticleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = vp()
        cls.lib = cls.v.load_library(LIB)
        cls.lib.mu_pt_kind_supported.restype = ctypes.c_int

    def create(self, kind, rands, scale=1.0, world=0, world_time=0.0, owner=-1, angle=(0.0, 0.0, 0.0), scene=6):
        v = self.v
        fx = Fixed(rands, height=55.0)
        host = fx.host(world, world_time, scene=scene)
        p = v.Particle()
        ok = self.lib.mu_pt_create_record(ctypes.byref(p), ctypes.byref(host), kind[0], v.F3(1000.0, 2000.0, 150.0),
                                          v.F3(*angle), v.F3(1.0, 0.5, 0.25), kind[1], f32(scale), owner, 7)
        return p, ok, fx

    def test_supported_kinds(self):
        sup = self.lib.mu_pt_kind_supported
        for kind in self.v.KINDS:
            self.assertEqual(sup(*kind), 1, kind)
        for kind in [(0x7f3c, 7), (0x7f3c, 18), (0x7f5a, 1), (0x771c, 1), (0x7ef7, 0), (0x7f26, 2)]:
            self.assertEqual(sup(*kind), 0, kind)

    def test_common_initialisation(self):
        p, ok, fx = self.create((0x7f26, 0), [5])
        self.assertEqual(ok, 1)
        self.assertEqual((p.live, p.type, p.tex_type, p.subtype, p.lifetime, p.frame, p.moving, p.arg8),
                         (1, 0x7f26, 0x7f26, 0, 2, 0, 1, 7))
        self.assertEqual(list(p.start), [1000.0, 2000.0, 150.0])
        self.assertEqual(list(p.owner_position), [0.0, 0.0, 0.0])
        self.assertEqual(fx.calls, 0)   # Spark03 subtype 0 draws no rand()
        # an owner: its position with z from RequestTerrainHeight
        p, ok, fx = self.create((0x7f26, 0), [5], owner=0)
        self.assertEqual(list(p.owner_position), [100.0, 200.0, 55.0])
        self.assertEqual(fx.heights, [(100.0, 200.0)])

    def test_fire01_subtypes(self):
        p, _, fx = self.create((0x7f3c, 0), [17, 70, 400])
        self.assertEqual(p.lifetime, 24)
        self.assertEqual(p.velocity[1], f32(-f32(17 % 16 + 32) * f32(0.1)))
        self.assertEqual(p.scale, f32(f32(70 % 64 + 128) * f32(0.01)))
        self.assertEqual(p.rotation, 40.0)
        p, _, _ = self.create((0x7f3c, 1), [0, 3, 0])
        self.assertEqual(p.scale, f32(13.0 * f32(0.01)))
        p, _, _ = self.create((0x7f3c, 2), [3, 0], scale=1.5)
        self.assertEqual((p.velocity[1], p.scale), (f32(-f32(-13.0) * f32(0.1)), 1.5))   # the default keeps the scale
        p, _, _ = self.create((0x7f3c, 17), [0, 0, 0], scale=2.0)
        self.assertEqual((p.lifetime, p.scale), (10, f32(f32(128.0 * 2.0) * f32(0.01))))

    def test_smoke01_takes_the_world_time(self):
        p, _, _ = self.create((0x7f5a, 0), [0, 359], world_time=12345.9)
        self.assertEqual((p.lifetime, p.angle[0], p.rotation), (16, 359.0, float(12345 % 360)))
        p, _, _ = self.create((0x7f5a, 2), [10, 20, 31])
        self.assertEqual((p.lifetime, p.rotation, p.gravity), (50, 20.0, f32(91.0 * f32(0.1))))

    def test_rain_splash(self):
        p, _, fx = self.create((0x771c, 0), [5, 9, 0, 4])
        self.assertEqual((p.lifetime, p.scale), (20, f32(13.0 * f32(0.1))))
        self.assertEqual(list(p.position), [1004.0, 1995.0, 149.0])
        host = Fixed([0]).host()
        p.light[0] = 1.0
        scale = p.scale
        self.assertEqual(self.lib.mu_pt_move_record(ctypes.byref(p), ctypes.byref(host)), 1)
        self.assertEqual((p.lifetime, p.scale, p.light[0]), (19, f32(scale + f32(0.03)), f32(1.0 - f32(0.05))))

    def test_fire_move_and_head_erase(self):
        p, _, _ = self.create((0x7f3c, 0), [0, 0, 0])
        p.velocity[1] = 0.0
        host = Fixed([0]).host()
        z = p.position[2]
        self.lib.mu_pt_move_record(ctypes.byref(p), ctypes.byref(host))
        self.assertEqual(p.gravity, f32(0.004))
        self.assertEqual(p.position[2], f32(f32(f32(0.004) * 10.0) + z))
        self.assertEqual((p.frame, p.lifetime), (0, 23))
        p.lifetime = 0
        self.assertEqual(self.lib.mu_pt_move_record(ctypes.byref(p), ctypes.byref(host)), 0)

    def test_login_mist_and_spray(self):
        # NATIVE-JOINT-001: clouds 0x7f89 subtype 0x14 (the login world's mist markers, owner = the object)
        p, ok, fx = self.create((0x7f89, 0x14), [700, 300, 40, 9, 50, 7, 3], owner=0)
        self.assertEqual((ok, p.lifetime, p.gravity, p.alpha), (1, 300, 700.0, f32(0.1)))
        self.assertEqual(list(p.position), [1050.0, 1790.0, 139.0])   # += (r%500-250, r%500-250, r%20-20)
        self.assertEqual((p.start[1], p.start[2]), (f32(50.0 / 100.0), 139.0))
        self.assertEqual(p.scale, f32(f32(f32(7 % 20 + 180) * f32(0.01)) * 1.0))
        self.assertEqual(p.field_7c, f32(3.0 / 100.0))
        self.assertEqual(list(p.owner_position), [100.0, 200.0, 55.0])
        host = Fixed([0]).host()
        p.velocity[2] = 0.0
        self.lib.mu_pt_move_record(ctypes.byref(p), ctypes.byref(host))   # LifeTime > 150: rises, brightens
        self.assertEqual((p.position[2], p.alpha), (140.0, f32(f32(0.1) + 0.04)))
        p.lifetime = 100
        self.lib.mu_pt_move_record(ctypes.byref(p), ctypes.byref(host))   # then sinks and fades
        self.assertEqual((p.position[2], p.alpha), (139.5, f32(f32(f32(0.1) + 0.04) - f32(0.025))))
        rc = self.v.RenderCall()
        self.lib.mu_pt_render_record(ctypes.byref(p), ctypes.byref(self.v.Bitmap(64.0, 64.0, 3)), 0, ctypes.byref(rc))
        self.assertEqual(rc.sprite.light[0], f32(1.0 * p.alpha))           # the light times the alpha
        # WATERFALL1 0x801a subtype 2 (the spray markers)
        p, ok, fx = self.create((0x801a, 2), [100, 3], scale=0.5)
        self.assertEqual((p.lifetime, p.rotation, p.velocity[2], p.scale), (30, 100.0, -10.0, f32(1.6 + 0.5)))
        self.assertEqual(list(p.light), [f32(0.2)]*3)
        p.lifetime = 25
        self.lib.mu_pt_move_record(ctypes.byref(p), ctypes.byref(host))
        self.assertEqual((p.light[0], p.velocity[2], p.scale), (f32(f32(0.2) * f32(1.1)), f32(-10.0 + f32(0.1)),
                                                                f32(f32(1.6 + 0.5) - f32(0.005))))

    def test_charsel_kinds(self):
        # NATIVE-CHARSEL-002: WATERFALL2 0x801b subtype 2 (the falls' spray), dimmer in the character select
        p, ok, fx = self.create((0x801b, 2), [100, 3, 4, 15, 5, 30], scale=0.5, scene=5)
        self.assertEqual((ok, p.lifetime, p.rotation, fx.calls), (1, 40, 100.0, 6))
        self.assertEqual((p.scale, p.velocity[2]), (f32(f32(f32(3 + 6) * f32(0.1)) + 0.5), -4.0))
        self.assertEqual(list(p.light), [0.25]*3)
        self.assertEqual(list(p.position), [1005.0, 1995.0, 160.0])   # += (r%20-10, r%20-10, r%40-20)
        p, ok, fx = self.create((0x801b, 2), [100, 3, 4, 15, 5, 30], scene=6)
        self.assertEqual(list(p.light), [f32(0.4)]*3)
        host = Fixed([13, 2]).host()
        p.lifetime = 9
        p.light[0] = 1.0
        self.lib.mu_pt_move_record(ctypes.byref(p), ctypes.byref(host))   # below 10 steps the light fades
        self.assertEqual((p.velocity[0], p.velocity[1]), (f32(f32(3.0) * f32(0.1)), f32(f32(-8.0) * f32(0.1))))
        self.assertEqual(p.light[0], f32(1.0 / f32(1.1)))
        # WATERFALL3 0x801c subtype 0xe (the falls' mist): no case of its own before the second chain
        p, ok, fx = self.create((0x801c, 0xe), [10, 1, 2, 4, 25, 0, 7], scale=2.0)
        self.assertEqual((ok, p.lifetime, p.rotation, p.velocity[2], fx.calls), (1, 30, 10.0, 7.0, 7))
        self.assertEqual(p.scale, f32(f32(f32(14.0) * f32(0.05)) * 2.0))
        self.assertEqual(list(p.position), [1005.0, 1980.0, 147.0])
        p.light[0] = 1.0
        self.lib.mu_pt_move_record(ctypes.byref(p), ctypes.byref(Fixed([0]).host()))
        self.assertEqual(p.light[0], f32(f32(1.0 / f32(1.1)) / f32(1.1)))   # divided twice
        self.assertEqual(p.velocity[2], f32(f32(7.0 - f32(0.6)) - 2.5))
        # fantaB 0x8017 subtype 0 (the lamps' sparks)
        p, ok, fx = self.create((0x8017, 0), [8, 1])
        self.assertEqual((ok, p.lifetime, p.velocity[0], p.velocity[1], p.velocity[2]),
                         (1, 24, f32(3.0 * f32(0.4)), 0.0, f32(6.0 * f32(0.2))))
        self.assertEqual(list(p.start), list(p.position))
        p.scale = f32(0.01)
        p.lifetime = 20
        self.lib.mu_pt_move_record(ctypes.byref(p), ctypes.byref(Fixed([0]).host()))
        self.assertEqual((p.scale, p.light[0]), (0.0, f32(f32(20.0) / f32(25.0))))
        # chasellight 0x8022 subtype 5 (the selection light): drawn with Impack03, rises by its gravity
        p, ok, fx = self.create((0x8022, 5), [1, 30, 20, 150, 5, 9, 100, 64])
        self.assertEqual((ok, p.lifetime, p.tex_type, fx.calls), (1, 21, 0x7b78, 8))
        self.assertEqual(p.position[0], f32(1000.0 + 5.0))
        self.assertEqual(p.position[1], f32(f32(100 - 65) + f32(2000.0 - 5.0)))
        self.assertEqual(p.position[2], f32(64.0 + 150.0))                   # the argument's z
        self.assertEqual(p.scale, f32(f32(f32(25.0) * f32(0.01)) * f32(1.3)))
        self.assertEqual(p.gravity, f32(f32(f32(29.0) * f32(0.05)) * f32(1.3)))
        z, p.light[0] = p.position[2], 1.0
        self.lib.mu_pt_move_record(ctypes.byref(p), ctypes.byref(Fixed([0]).host()))
        self.assertEqual((p.light[0], p.position[2]), (f32(1.05), f32(z + p.gravity)))

    def test_noria_shiny01(self):
        p, ok, fx = self.create((0x7f66, 1), [0])
        self.assertEqual((ok, p.lifetime, p.angle[0], fx.calls), (1, 18, 45.0, 0))
        host = Fixed([0]).host()
        self.lib.mu_pt_move_record(ctypes.byref(p), ctypes.byref(host))
        self.assertEqual(p.scale, f32(f32(math.sin(f32(f32(18.0 * 10.0) * f32(0.017453292)))) * 0.75))
        self.assertEqual(p.rotation, -12.0)

    def test_wrapper_drops_only_in_world_0x8b(self):
        k = self.lib.mu_pt_wrapper_keeps
        fx = Fixed([3])
        self.assertEqual(k(ctypes.byref(fx.host(0, divisor=4)), 0x7f2b, 0), 1)
        self.assertEqual(fx.calls, 0)
        self.assertEqual(k(ctypes.byref(fx.host(0x8b, divisor=4)), 0x7f2b, 0), 0)   # 3 % 4 != 0
        self.assertEqual(k(ctypes.byref(fx.host(0x8b, divisor=4)), 0x7f3c, 0), 1)   # Fire01 is exempt
        self.assertEqual(fx.calls, 2)

    def test_render_fire_strip(self):
        v = self.v
        p, _, _ = self.create((0x7f3c, 3), [0, 0], angle=(33.0, 0.0, 0.0))
        p.frame = 6
        rc = v.RenderCall()
        bm = v.Bitmap(64.0, 128.0, 3)
        self.assertEqual(self.lib.mu_pt_render_record(ctypes.byref(p), ctypes.byref(bm), 0, ctypes.byref(rc)), 1)
        s = rc.sprite
        self.assertEqual((s.width, s.height, s.rotation, s.u, s.uw, s.axes), (16.0, 128.0, 33.0, 0.5, 0.25, 4))
        self.assertEqual(list(rc.state)[:rc.state_count], [v.STATE_ADD])
        p.position[2] = 351.0
        self.assertEqual(self.lib.mu_pt_render_record(ctypes.byref(p), ctypes.byref(bm), 1, ctypes.byref(rc)), 0)

    def test_sprite_quad_upright(self):
        v = self.v
        gl = v.GLLog()
        camera = (ctypes.c_float*12)(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, -100)
        call = v.SpriteCall(0x7f3c, v.F3(10.0, 20.0, 30.0), 8.0, 4.0, v.F3(1.0, 0.5, 0.25), 0.0, 0.0, 0.0, 1.0, 1.0, 4)
        self.lib.mu_pt_render_sprite(camera, ctypes.byref(call), 3, ctypes.byref(gl.gl))
        names = [e[0] for e in gl.log]
        self.assertEqual(names, ['bind', 'glBegin', 'glColor3fv'] + ['glTexCoord2f', 'glVertex3fv']*4 + ['glEnd'])
        verts = [e[1] for e in gl.log if e[0] == 'glVertex3fv']
        self.assertEqual(verts[0], [6.0, 18.0, -70.0])
        self.assertEqual(verts[2], [14.0, 22.0, -70.0])
        self.assertEqual([e[1] for e in gl.log if e[0] == 'glTexCoord2f'][0], [0.0, 1.0])

    def test_sprites_live_for_one_frame(self):
        v = self.v
        sp = v.Sprites()
        sheet = v.Sheet(1, 1, 1.0)
        i = self.lib.mu_pt_sprite_create(ctypes.byref(sp), 0x7ef7, v.F3(0.0, 0.0, 400.0), 2.0, v.F3(1, 1, 1), -1, 0.0,
                                         0, 4, ctypes.byref(sheet))
        j = self.lib.mu_pt_sprite_create(ctypes.byref(sp), 0x7ef7, v.F3(0.0, 0.0, 100.0), 2.0, v.F3(1, 1, 1), -1, 0.0,
                                         1, 4, ctypes.byref(sheet))
        self.assertEqual((i, j, sp.records[0].alpha), (0, 1, 1.0))
        bitmap = v.BITMAP_FN(lambda c, b, out: (setattr(out[0], 'width', 32.0), setattr(out[0], 'height', 32.0),
                                                setattr(out[0], 'components', 3), 1)[-1])
        kill = v.KILL_FN(lambda c, i: None)
        gl = v.GLLog()
        camera = (ctypes.c_float*12)(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0)
        # mode 1 skips the sprite above z 350 and keeps both alive
        self.assertEqual(self.lib.mu_pt_sprites_render(ctypes.byref(sp), 1, 0.0, camera, bitmap, None,
                                                       ctypes.byref(gl.gl), kill, None), 1)
        self.assertEqual((sp.records[0].live, sp.records[1].live), (1, 1))
        self.assertEqual([e for e in gl.log if e[0] == 'state'], [('state', v.STATE_SUB, 0)])
        self.assertEqual(sp.records[1].alpha, f32(1.0 - f32(0.1)))   # not marked visible: the ramp goes down
        self.lib.mu_pt_sprites_mark_visible(ctypes.byref(sp))
        self.assertEqual(self.lib.mu_pt_sprites_render(ctypes.byref(sp), 0, 0.0, camera, bitmap, None,
                                                       ctypes.byref(gl.gl), kill, None), 2)
        self.assertEqual((sp.records[0].live, sp.records[1].live), (0, 0))   # mode 0 kills every drawn sprite

    def test_body_shadow_projection(self):
        v = self.v
        tri = bytearray(0x24)
        tri[0] = 3
        struct.pack_into('<4h', tri, 2, 0, 1, 2, 0)
        verts = [1000.0, 1000.0, 300.0, 1100.0, 1000.0, 100.0, 1000.0, 1100.0, 0.0]
        c_tri = (ctypes.c_uint8*0x24)(*tri)
        c_v = (ctypes.c_float*9)(*verts)
        mesh = v.ShadowMesh(1, 0, ctypes.cast(c_tri, ctypes.POINTER(ctypes.c_uint8)),
                            ctypes.cast(c_v, ctypes.POINTER(ctypes.c_float)), 3)
        fx = Fixed([0], height=40.0)
        gl = v.GLLog()
        n = self.lib.mu_pt_render_body_shadow(ctypes.byref(mesh), 1, v.F3(1000.0, 1000.0, 0.0), -1, -1, -1, -1, 3,
                                              ctypes.byref(fx.host(0)), ctypes.byref(gl.gl))
        self.assertEqual(n, 3)
        out = [e[1] for e in gl.log if e[0] == 'glVertex3fv']
        x = f32(f32(f32(f32(0.0 + 2000.0) * 300.0) / f32(300.0 - 4000.0)) + 0.0)
        self.assertEqual(out[0], [f32(x + 1000.0), 1000.0, f32(3.0 + f32(40.0 + 2.0))])
        self.assertEqual([e[0] for e in gl.log][:3], ['state', 'state', 'glPushMatrix'])
        self.assertEqual(gl.log[-1], ('state', v.STATE_DEPTH_ON, 0))
        # world 0x91: 10 above the origin, no terrain
        fx = Fixed([0], height=40.0)
        gl = v.GLLog()
        self.lib.mu_pt_render_body_shadow(ctypes.byref(mesh), 1, v.F3(1000.0, 1000.0, 0.0), -1, -1, -1, -1, 0,
                                          ctypes.byref(fx.host(0x91)), ctypes.byref(gl.gl))
        self.assertEqual([e[1] for e in gl.log if e[0] == 'glVertex3fv'][1][2], 10.0)

    def test_transform_position(self):
        v = self.v
        m = (ctypes.c_float*12)(0, -1, 0, 5, 1, 0, 0, 6, 0, 0, 1, 7)
        out = v.F3(0, 0, 0)
        self.lib.mu_pt_transform_position(m, v.F3(1.0, 2.0, 3.0), out, 0, 2.0, v.F3(100.0, 200.0, 300.0))
        self.assertEqual(list(out), [3.0, 7.0, 10.0])
        self.lib.mu_pt_transform_position(m, v.F3(1.0, 2.0, 3.0), out, 1, 2.0, v.F3(100.0, 200.0, 300.0))
        self.assertEqual(list(out), [106.0, 214.0, 320.0])

    def test_find_bone(self):
        names = (ctypes.c_char_p*3)(b'Bip01', b'Box04', b'Box03')
        self.assertEqual(self.lib.mu_pt_find_bone(names, 3, b'Box03'), 2)
        self.assertEqual(self.lib.mu_pt_find_bone(names, 3, b'box03'), -1)

    def visual(self, world, typ, rands, has_model=True):
        v = self.v
        calls = []
        state = {'n': 0}

        def rand(c):
            r = rands[state['n'] % len(rands)]
            state['n'] += 1
            return r

        def bone(c, o, name, vin, vout):
            calls.append(('bone', name.decode(), [vin[0], vin[1], vin[2]]))
            vout[0], vout[1], vout[2] = vin[0] + 1.0, vin[1], vin[2]

        def particle(c, t, p, a, l, sub, sc, owner):
            calls.append(('particle', t, [p[0], p[1], p[2]], sub, sc))

        def sprite(c, b, p, sc, l, owner, rot, blend, axes):
            calls.append(('sprite', b, sc, [l[0], l[1], l[2]], blend, axes))

        def joint(c, b, p, a, sub, owner, sc):
            calls.append(('joint', b, sub, sc))
        fns = (v.RAND_FN(rand), v.HAS_MODEL_FN(lambda c, o: int(has_model)), v.BONE_FN(bone),
               v.VPARTICLE_FN(particle), v.VSPRITE_FN(sprite), v.VJOINT_FN(joint),
               v.VEFFECT_FN(lambda *a: calls.append(('effect',))))
        o = v.VisualObject(3, typ, v.F3(0, 0, 0), v.F3(0, 0, 0), v.F3(0.5, 0.5, 0.5), 1.5, 0.0, 0.0)
        handled = self.lib.mu_pt_object_visual(ctypes.byref(o), ctypes.byref(v.VisualHost(None, *fns, world, 2500.0)))
        return handled, calls, o, state['n']

    def test_lorencia_waterspout_and_merchant(self):
        handled, calls, o, n = self.visual(0, 0x69, [0, 0, 20, 31, 5, 7])
        self.assertEqual((handled, o.blend_light, n), (1, 1.0, 6))
        self.assertEqual(o.blend_v, f32(-500.0 * f32(0.001)))   # C remainder: -2500 % 1000 = -500
        self.assertEqual([c[1] for c in calls if c[0] == 'bone'], ['Box04', 'Box03'])
        self.assertEqual(calls[0][2], [4.0, -20.0, 15.0])
        self.assertEqual([c[:2] for c in calls if c[0] == 'particle'], [('particle', 0x7f5a)]*2)
        handled, calls, o, n = self.visual(0, 0x69, [0, 1])
        self.assertEqual([c for c in calls if c[0] == 'particle'], [])   # rand % 2 != 0: no smoke
        handled, calls, o, n = self.visual(0, 0x38, [29])
        l = f32(f32(99.0) * f32(0.01))
        self.assertEqual([c[1] for c in calls if c[0] == 'bone'], ['Box04', 'Box10'])
        self.assertEqual(calls[1], ('sprite', 0x7ef7, f32(l*5.0), [f32(l*f32(0.6)), f32(l*f32(0.3)), f32(l*f32(0.1))], 0, 4))
        handled, calls, o, n = self.visual(0, 0x69, [0], has_model=False)
        self.assertEqual((handled, calls, n), (1, [], 0))

    def test_tormenta_joints(self):
        handled, calls, o, n = self.visual(0x8d, 0xc3, [5, 100])
        self.assertEqual(calls, [('joint', 0x7f7d, 0x15, 1.5)])
        self.assertEqual(list(o.light), [f32(0.59), f32(0.59), 1.0])
        handled, calls, o, n = self.visual(0x8d, 9, [5, 501])
        self.assertEqual(calls, [('effect',)])
        self.assertEqual(self.visual(4, 0x69, [0])[0], 0)   # worlds without a ported case

    def test_dungeon_devias_noria_visuals(self):
        # NATIVE-JOINT-001: lightning2 pairs and flares; Noria 0x27's sparkles and spark joints
        handled, calls, o, n = self.visual(2, 0x64, [0])
        self.assertEqual([c[1] for c in calls if c[0] == 'bone'], ['Cylinder01'])
        self.assertEqual([c[:3] for c in calls if c[0] == 'sprite'], [('sprite', 0x7f37, 2.5)]*2)
        handled, calls, o, n = self.visual(3, 0x11, [0])
        self.assertEqual([c[1] for c in calls if c[0] == 'bone'], ['Box03', 'Box08', 'Box11', 'Box14'])
        self.assertEqual({c[1] for c in calls if c[0] == 'sprite'}, {0x7ef7})
        # 0x27: the lamp sparkle on the first lamp (rand % 32 == 0), then the light07 fountain (rand % 8 == 0)
        handled, calls, o, n = self.visual(3, 0x27, [5, 0, 1, 1, 1, 1, 0] + [70, 10]*8)
        self.assertEqual([c[1:4] for c in calls if c[0] == 'particle'][:2], [(0x7f66, [1.0, 0.0, 0.0], 0),
                                                                             (0x7f66, [1.0, 0.0, 0.0], 1)])
        self.assertEqual([c[1:] for c in calls if c[0] == 'joint'], [(0x7fd5, 0, 10.0)]*8)
        self.assertEqual(len([c for c in calls if c[0] == 'particle' and c[1] == 0x7f25]), 8)
        handled, calls, o, n = self.visual(1, 0x3d, [0])
        self.assertEqual([c[2] for c in calls if c[0] == 'sprite'], [f32(0.3)]*4 + [1.5]*2)   # bones 15, 19, 21

    def test_layout_round_trip(self):
        v = self.v
        p, _, _ = self.create((0x7f5a, 2), [1, 2, 3])
        raw, mask = v.particle_bytes(self.lib, p)
        q = v.Particle()
        self.lib.mu_pt_particle_load(ctypes.byref(q), raw)
        self.assertEqual(v.particle_bytes(self.lib, q)[0], raw)
        self.assertEqual(mask[0x50:0x54], b'\0'*4)   # the owner pointer is the caller's


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'set MU_RECOVERY_INTEGRATION=1')
class ClientComparison(unittest.TestCase):
    def test_unicorn_comparison(self):
        v = vp()
        text = Path(v.default_evidence('x86-text-capture-09/client-text.bin'))
        if not text.exists():
            self.skipTest('restored text capture not present')
        result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_particles.py'), '--cases', '40',
                                 '--heavy-cases', '4'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-2000:])


if __name__ == '__main__':
    unittest.main()
