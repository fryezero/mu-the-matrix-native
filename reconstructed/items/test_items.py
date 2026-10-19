"""Dropped items: viewport, CreateItem, ItemObjectAttribute, ItemAngle, the name builder, MoveItems,
RenderItems, SelectItem, TestFrustrum, labels (NATIVE-ITEMS-001).

Portable: the library through ctypes with the validator's structures
(scripts/validate_items.py); worked examples restate the client branches of
docs/research/client-ground-items.md and compare bit for bit.
Private (MU_RECOVERY_INTEGRATION=1 and the restored text/data): a short
Unicorn comparison through scripts/validate_items.py.
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
LIB = HERE/f'libclient_items.{SUFFIX}'


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


def setUpModule():
    subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)


def vi():
    import validate_items
    return validate_items


class Env:
    """Records by code, rand() answers, sin/sqrt from libm, a terrain height function."""

    def __init__(self, records=None, height=100.0, rands=(7, 3, 11, 5), socket=False, world=0, world_time=0.0):
        self.records, self.height, self.rands, self.calls = records or {}, height, list(rands), 0
        self.sounds, self.socket, self.world, self.world_time = [], socket, world, world_time
        self._keep, self._recs = [], {}

    def host(self):
        v = vi()

        def record(ctx, code):
            if code not in self.records:
                return None
            if code not in self._recs:
                ka, kb, ty = self.records[code]
                self._recs[code] = v.Record(1, ka, kb, ty, 0, None)
            return ctypes.addressof(self._recs[code])

        def rand(ctx):
            r = self.rands[self.calls % len(self.rands)]
            self.calls += 1
            return r
        fns = (v.RECORD_FN(record), v.HEIGHT_FN(lambda c, x, y: f32(self.height)),
               v.LIGHT_FN(lambda c, x, y, out: [out.__setitem__(k, 0.5) for k in range(3)] and None),
               v.RAND_FN(rand), v.FLOAT_FN(lambda c, x: f32(math.sin(x))), v.FLOAT_FN(lambda c, x: f32(math.sqrt(x))),
               v.SOUND_FN(lambda c, i: self.sounds.append(i)), v.SOCKET_FN(lambda c, it: int(self.socket)))
        self._keep.append(fns)
        return v.Host(None, *fns, f32(self.world_time), self.world)


def item_bytes(code, level=0, b2=0, b3=0, b4=0, b5_low=0, b6=0, tail=(0xff,)*8):
    b = [code & 0xff, level, b2, (b3 & 0x7f) | (((code >> 8) & 1) << 7), b4,
         (((code >> 9) & 0xf) << 4) | (b5_low & 0x0e) | ((code >> 13) & 1), b6] + list(tail)
    return bytes(b)


class ItemsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = vi().load_library(LIB)

    def create(self, code, drop=1, env=None, **kw):
        v = vi()
        env = env or Env({code: (0, 0, 0)})
        host = env.host()
        it = v.Item()
        calls = []
        hooks = v.CreateHooks(None, v.RESET_FN(lambda c, d: calls.append('reset')),
                              v.LIVE_FN(lambda c, o, l: (calls.append('live'), setattr(o.contents, 'live', l))),
                              v.OBJ_FN(lambda c, o: calls.append('attr')), v.OBJ_FN(lambda c, o: calls.append('angle')),
                              v.ITEM_FN(lambda c, i: calls.append('name')),
                              v.EFFECT_FN(lambda c, t, p, o, s: calls.append(('effect', t))), v.PENTA_FN(0))
        status = self.lib.mu_gi_create(ctypes.byref(it), item_bytes(code, **kw), (ctypes.c_float*3)(1250.0, 2350.0, 0.0),
                                       drop, ctypes.byref(host), ctypes.byref(hooks))
        return status, it, calls, env

    def test_item_code_and_viewport(self):
        lib = self.lib
        lib.mu_gi_item_code.argtypes = [ctypes.c_char_p]
        self.assertEqual(lib.mu_gi_item_code(item_bytes(0x1c0f)), 0x1c0f)
        self.assertEqual(lib.mu_gi_item_code(item_bytes(0x2abc)), 0x2abc)
        entry = lambda key, x, y, code: bytes([key >> 8, key & 0xff, x, y]) + item_bytes(code)
        packet = bytes([0xc2, 0, 0, 0x20, 3]) + entry(0x8005, 12, 23, 1) + entry(1500, 0, 0, 2) + entry(7, 255, 1, 3)
        out = (vi().ViewportEntry*8)()
        n = lib.mu_gi_viewport_parse(packet, out, 8)
        self.assertEqual(n, 3)
        self.assertEqual((out[0].index, out[0].drop, out[0].x, out[0].y), (5, 1, 1250.0, 2350.0))
        self.assertEqual((out[1].index, out[1].drop), (0, 0))       # keys of 1000 and more become slot 0
        self.assertEqual((out[2].x, out[2].y), (25550.0, 150.0))
        many = bytes([0xc2, 0, 0, 0x20, 200]) + entry(1, 1, 1, 1)*200
        self.assertEqual(lib.mu_gi_viewport_parse(many, (vi().ViewportEntry*100)(), 100), 75)

    def test_sounds(self):
        drop, pick = self.lib.mu_gi_drop_sound, self.lib.mu_gi_pickup_sound
        pick.argtypes = [ctypes.c_int32]
        self.assertEqual([drop(c, 1) for c in (0x1c0f, 0x1c0d, 0x180f, 0x1c29, 0x1d03, 0x1d0a, 1)],
                         [0x1f, 0x45, 0x45, 0x2d3, 0x5a, 0x5a, 0x1e])
        self.assertEqual(drop(1, 0), -1)
        self.assertEqual([pick(c) for c in (0x1c0e, 0x1c29, 0x200)], [0x45, 0x2d3, 0x1d])

    def test_create_zen_and_drop(self):
        status, it, calls, env = self.create(0x1c0f, b2=0x02, b4=0x05, level=0x01, b6=0x00)
        self.assertEqual(status, 1)
        self.assertEqual(it.data.level, (0x01 << 16) + (0x02 << 8) + 0x05)
        self.assertEqual(it.object.type, 0x1c0f + 0xae6)
        self.assertEqual((it.object.position[2], it.object.gravity), (280.0, 20.0))   # height + 180, gravity 20
        self.assertEqual(calls, ['reset', 'live', 'attr', 'angle', 'name'])
        self.assertEqual(env.sounds, [0x1f])
        self.assertEqual(list(it.object.bbox_min) + list(it.object.bbox_max), [-30.0]*3 + [30.0]*3)
        status, it, calls, env = self.create(1, drop=0, level=0x48, b2=9, b3=0x83, b4=5)
        self.assertEqual((it.data.level, it.data.durability, it.data.excellent, it.data.ancient), (0x48, 9, 3, 5))
        self.assertEqual(it.object.position[2], 100.0)            # no drop flag: on the terrain
        self.assertEqual(env.sounds, [])
        status, it, calls, env = self.create(5, env=Env({}))
        self.assertEqual((status, calls), (0, ['reset']))          # no record: nothing after the reset

    def test_create_remaps(self):
        cases = [(0x1c0b, 8, 0x3894), (0x1c0b, 40, 0x3898), (0x1c0b, 104, 0x3895), (0x1c0b, 32, 0x1c0b+0xae6),
                 (0x1c20, 8, 0x38a5), (0x1c22, 8, 0x38a7), (0x1a14, 0, 0x389f), (0x1a14, 16, 0x389e),
                 (0x1c29, 0, 0x270f)]
        for code, level, model in cases:
            status, it, calls, env = self.create(code, level=level)
            self.assertEqual(it.object.type, model, hex(code))
        status, it, calls, env = self.create(0x1a13, level=8)
        self.assertEqual((it.object.type, it.data.level), (0xaf9, 0))
        status, it, calls, env = self.create(0x1c0b, level=40)          # firecracker box: two effects, gravity 50
        self.assertIn(('effect', 0x467), calls)
        self.assertEqual((it.object.position[2], it.object.gravity), (103.0, 50.0))

    def test_object_attribute(self):
        v = vi()
        env = Env(rands=(23,), world_time=1000.0)
        for t, blend, hidden, scale in ((0xae6, -1, -1, 0.8), (0x10e6, 1, -1, 0.7), (0xb05, -1, 2, 0.8),
                                        (0x26fb, -1, -1, 0.5), (0xa9c, -1, -1, 1.0)):
            o = v.Object()
            o.type = t
            self.lib.mu_gi_object_attribute(ctypes.byref(o), ctypes.byref(env.host()))
            self.assertEqual((o.blend_mesh, o.hidden_mesh, o.scale, o.alpha), (blend, hidden, f32(scale), 1.0), hex(t))
            self.assertEqual(list(o.light), [f32(0.3)]*3)
        o = v.Object()
        o.type = 0x14ed                                           # blend light = (rand % 11) * 0.1
        self.lib.mu_gi_object_attribute(ctypes.byref(o), ctypes.byref(env.host()))
        self.assertEqual(o.blend_light, f32(f32(23 % 11) * f32(0.1)))

    def test_item_angle(self):
        v = vi()

        def angle(t, record=None):
            o = v.Object()
            o.type = t
            e = v.AngleEnv()
            if record:
                e.record = v.Record(1, *record, 0, None)
            self.lib.mu_gi_item_angle(ctypes.byref(o), ctypes.byref(e))
            return list(o.angle)
        self.assertEqual(angle(0xae7), [60.0, 0.0, -45.0])        # weapons 0xae6..0xee5: 60 degrees up
        self.assertEqual(angle(0x26f5), [0.0, 0.0, -45.0])        # zen: the default pose

    def test_name_builder(self):
        v = vi()

        def name(code, level, exc=0, anc=0, flag98=0, record=(0, 0, 0)):
            texts = {0xb0: ' +Skill', 0xb1: ' +Option', 0xb2: ' +Luck'}
            keep = {}

            def cstr(key, s):
                keep[key] = ctypes.create_string_buffer(s.encode())
                return ctypes.addressof(keep[key])
            nbuf = ctypes.create_string_buffer(b'Thing')
            rec = v.Record(1, *record, 0, ctypes.cast(nbuf, ctypes.c_char_p))
            fns = [v.RECORD_FN(lambda c, k: ctypes.addressof(rec)),
                   v.TEXT_FN(lambda c, i: cstr(i, texts.get(i, f'G{i}'))), v.PREFIX_FN(lambda c, it: cstr('p', '')),
                   v.INT_FN(lambda c, k: 0), v.TEXT_FN(lambda c, k: cstr('e', 'E')), v.TEXT_FN(lambda c, k: cstr('s', 'S')),
                   v.INT_FN(lambda c, k: k), v.TEXT_FN(lambda c, k: cstr('l', 'L'))]
            env = v.NameEnv(None, *fns, 1)
            it = v.Item()
            it.data.code, it.data.level, it.data.excellent, it.data.ancient, it.data.flag_98 = code, level, exc, anc, flag98
            it.object.type = code + 0xae6
            sink = v.NameSink()
            self.lib.mu_gi_name_build(ctypes.byref(it), ctypes.byref(env), ctypes.byref(sink))
            return it.name.decode(), it.name_class, sink.label_add
        self.assertEqual(name(0x1c0f, 1234), ('Thing 1234', 3, 1))           # zen: "%s %d", gold
        self.assertEqual(name(1, 0), ('Thing', 10, 1))                      # +0: grey
        self.assertEqual(name(1, 2 << 3), ('Thing +2', 0, 1))               # +1..+2: white
        self.assertEqual(name(1, 4 << 3), ('Thing +4', 13, 1))              # +3..+4: orange
        self.assertEqual(name(1, 6 << 3), ('Thing +6', 1, 1))               # +5..+6: blue
        self.assertEqual(name(1, 9 << 3), ('Thing +9', 3, 1))               # +7 and up: gold
        self.assertEqual(name(1, (2 << 3) | 0x84), ('Thing +2 +Skill +Luck', 1, 1))
        self.assertEqual(name(1, 2 << 3, anc=5)[1], 9)                       # ancient: green
        lib = self.lib
        lib.mu_gi_label_color.argtypes = [ctypes.c_int32]
        lib.mu_gi_label_color.restype = ctypes.c_char_p
        self.assertEqual([lib.mu_gi_label_color(c) for c in (0, 1, 3, 4, 9, 10, 13, 99)],
                         [b'#FFFFFF', b'#7FB2FF', b'#FFCC19', b'#19FF7F', b'#00FF00', b'#B2B2B2', b'#E56B0A',
                          b'#FFFFFF'])

    def test_move_items(self):
        v = vi()
        env = Env(height=100.0, rands=(0, 31))
        host = env.host()
        o = v.Object()
        o.live, o.type, o.gravity, o.sparkle = 1, 0x26f5, 20.0, 1
        o.position[2] = 280.0
        lands, particles = [], []
        hooks = v.MoveHooks(None, v.OBJ_FN(lambda c, ob: lands.append(1)),
                            v.PARTICLE_FN(lambda c, t, p, a, l, s, sc: particles.append((t, s))))
        zs = []
        for step in range(60):
            self.lib.mu_gi_move_item(ctypes.byref(o), ctypes.byref(host), ctypes.byref(hooks))
            zs.append(o.position[2])
        # 280 + 20 + 14 + 8 + 2 - 4 - 10 ... reaches the floor 130 on the step after z drops below it
        expected, z, g = [], 280.0, 20.0
        for step in range(60):
            z, g = f32(z + g), f32(g - 6.0)
            z = max(z, 130.0) if z <= 130.0 else z
            expected.append(z)
        self.assertEqual(zs, expected)
        self.assertEqual(len(lands), sum(1 for z in zs if z == 130.0))
        self.assertEqual(particles, [(0x7f66, 0), (0x7f66, 1)])       # the sparkle on the 48th step
        weapon = v.Object()
        weapon.live, weapon.type, weapon.gravity = 1, 0xae7, -30.0
        weapon.position[2] = 175.0
        self.lib.mu_gi_move_item(ctypes.byref(weapon), ctypes.byref(host), ctypes.byref(hooks))
        self.assertEqual(weapon.position[2], 170.0)                   # weapons rest 40 higher

    def test_render_zen_pile_and_labels(self):
        v = vi()
        env = Env()
        host = env.host()
        it = v.Item()
        it.data.level = 900                                           # sqrt 30 / 2 = 15 coins
        it.object.live, it.object.type, it.object.alpha = 1, 0x26f5, 1.0
        table = (ctypes.c_int32*100)(*[(i * 37) % 360 for i in range(100)])
        renv = v.RenderEnv(1, 1, 1, 0, 0, 0.0, table, v.PROJECT_FN(lambda c, w, x, y: None), None, 0)
        plan = v.RenderPlan()
        self.lib.mu_gi_render_plan(ctypes.byref(it), 7, ctypes.byref(host), ctypes.byref(renv), ctypes.byref(plan))
        self.assertEqual(plan.call_count, 15)
        self.assertEqual(list(plan.calls[14].position), [0.0, 0.0, 0.0])   # the last call at the item's own place
        armour = v.Item()
        armour.object.live, armour.object.type = 1, 0x18e6 + 5
        self.lib.mu_gi_render_plan(ctypes.byref(armour), 0, ctypes.byref(host), ctypes.byref(renv), ctypes.byref(plan))
        self.assertEqual((plan.pose_model, plan.render_model, plan.pose_head_offset), (0xa91, 0x18eb, -160.0))
        class Box(ctypes.Structure):
            _fields_ = [(n, ctypes.c_float) for n in ('tx', 'ty', 'tw', 'th', 'bx', 'by', 'bw', 'bh')]
        b = Box()
        self.lib.mu_gi_label_layout.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.POINTER(Box)]
        self.lib.mu_gi_label_layout(41.0, 12.0, ctypes.byref(b))    # ItemNameMC: +6/+4, centred, 14 above
        self.assertEqual([b.tx, b.ty, b.tw, b.th, b.bx, b.by, b.bw, b.bh], [-23, -30, 47, 16, -26, -32, 53, 20])

    def test_frustum_and_select(self):
        v = vi()
        lib = self.lib
        lib.mu_gi_test_frustum.argtypes = [ctypes.POINTER(ctypes.c_float*15), ctypes.POINTER(ctypes.c_float*5),
                                           ctypes.POINTER(ctypes.c_float*3), ctypes.c_float]
        normals = (ctypes.c_float*15)(*([0.0, 0.0, 1.0]*5))
        dist = (ctypes.c_float*5)(*([-100.0]*5))
        self.assertEqual(lib.mu_gi_test_frustum(normals, dist, (ctypes.c_float*3)(0, 0, -299.0), 400.0), 1)
        self.assertEqual(lib.mu_gi_test_frustum(normals, dist, (ctypes.c_float*3)(0, 0, -301.0), 400.0), 0)
        items = (v.Item*4)()
        for i in range(4):
            items[i].object.live, items[i].object.visible = 1, i != 2
        hits = v.RAY_FN(lambda c, i: int(i >= 1))
        self.assertEqual(lib.mu_gi_select(items, 4, hits, None), 1)
        self.assertEqual([round(items[i].object.light[0], 2) for i in range(4)], [0.2, 1.5, 0.0, 0.2])


class MonsterVoiceTest(unittest.TestCase):
    """SetPlayerShock / SetPlayerDie monster sounds over the extracted SetMonsterSound slots."""

    def test_bull_fighter(self):
        for d in ('combat', 'actors'):
            subprocess.run(['make', '-C', str(ROOT/'reconstructed'/d)], check=True, capture_output=True)
        v = vi()
        combat = ctypes.CDLL(str(ROOT/f'reconstructed/combat/libcombat.{SUFFIX}'))
        actors = ctypes.CDLL(str(ROOT/f'reconstructed/actors/libactors.{SUFFIX}'))
        slots = (ctypes.c_int16*10)()
        self.assertEqual(actors.mu_monster_sound_slots(0, slots), 1)
        self.assertEqual(list(slots), [0, 1, 2, 3, 4, -1, -1, -1, -1, -1])   # mBull1/2, Attack1/2, Die
        P = ctypes.POINTER
        combat.mu_monster_shock.argtypes = [P(v.MonsterVoice), ctypes.c_int32, ctypes.c_int32, P(ctypes.c_int32),
                                            ctypes.c_int32, P(ctypes.c_int32), P(ctypes.c_int32)]
        combat.mu_monster_die.argtypes = [P(v.MonsterVoice), P(ctypes.c_int32), ctypes.c_int32, P(ctypes.c_int32),
                                          P(ctypes.c_int32)]
        voice = v.MonsterVoice(0x7a5, 0, 0.0, 1, slots, 0)
        act, snd = ctypes.c_int32(), ctypes.c_int32()
        used = combat.mu_monster_shock(ctypes.byref(voice), 0, 0, (ctypes.c_int32*1)(7), 1, ctypes.byref(act),
                                       ctypes.byref(snd))
        self.assertEqual((used, act.value, snd.value), (1, 5, 0xd2 + 3))   # slot 2 + rand % 2
        combat.mu_monster_die(ctypes.byref(voice), (ctypes.c_int32*1)(0), 0, ctypes.byref(act), ctypes.byref(snd))
        self.assertEqual((act.value, snd.value), (6, 0xd2 + 4))            # mBullDie
        voice.field_3324 = f32(0.001)
        combat.mu_monster_die(ctypes.byref(voice), (ctypes.c_int32*1)(0), 0, ctypes.byref(act), ctypes.byref(snd))
        self.assertEqual(snd.value, -1)                                     # once


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private client capture comparison')
class PrivateUnicornTest(unittest.TestCase):
    def test_validator(self):
        out = subprocess.run([sys.executable, str(ROOT/'scripts/validate_items.py'), '--cases', '60',
                              '--heavy-cases', '6'], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout[-3000:] + out.stderr[-2000:])


if __name__ == '__main__':
    unittest.main()
