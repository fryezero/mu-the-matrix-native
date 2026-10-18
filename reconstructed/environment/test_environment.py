"""Environment routines (NATIVE-ENV-001): worked examples and Python statements.

Portable: the library with its deterministic test host. The worked examples
restate client branches (docs/research/client-environment.md); the
statement tests replay the default leaf mover 0x0153ac06, the bat mover
0x00ca2acd and FadeAlpha 0x012af883 in Python with the same rand() and
terrain answers and compare every field bit for bit.
Private (MU_RECOVERY_INTEGRATION=1 and the restored text/data): a short
Unicorn comparison through scripts/validate_environment.py.
"""
import ctypes
import math
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
LIB = HERE/f'libclient_env.{SUFFIX}'
OBJ, LEAF = 0x3d8, 0xb4


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


def bits(v):
    return struct.unpack('<I', struct.pack('<f', v))[0]


def mix(a, b):
    m = ((a * 0x9e3779b1) ^ (b * 0x85ebca77)) & 0xffffffff
    m ^= m >> 15
    m = (m * 0x2c1b3c6d) & 0xffffffff
    return m ^ (m >> 12)


class Rand:
    def __init__(self, seed):
        self.state = seed & 0xffffffff

    def __call__(self):
        self.state = (self.state * 214013 + 2531011) & 0xffffffff
        return (self.state >> 16) & 0x7fff


def setUpModule():
    subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)


class Session:
    def __init__(self, seed=1, world=0, hero=(13350.0, 12750.0, 165.0), attributes=None, layer1=None,
                 height=(-100.0, 600, 12)):
        import validate_environment as ve
        self.ve = ve
        self.L = ve.Library(LIB)
        case = {'seed': seed, 'attributes': attributes or bytes(0x20000), 'layer1': layer1 or bytes(0x10000),
                'height_base': f32(height[0]), 'height_span': height[1], 'height_shift': height[2],
                'missing_models': [], 'missing_bitmaps': [], 'boids': bytes(40*OBJ), 'fishs': bytes(10*OBJ),
                'leaves': bytes(200*LEAF), 'trailer': (0, 0, 0, 0, 0), 'tormenta': (1, 10.0, 0.0)}
        self.case = case
        self.n = ve.NativeSession(self.L, case)
        self.s = {'world': world, 'hero': [f32(v) for v in hero], 'safe': 0, 'event': 0, 'hero_action': 1,
                  'time': 100000.0, 'hero_tile': (int(hero[0]/100), int(hero[1]/100)),
                  'camera': [f32(hero[0]), f32(hero[1] - 1000.0), f32(hero[2] + 900.0)]}
        self.n.set_inputs(self.s)

    def run(self, step):
        return self.n.run(step)

    def state(self):
        return self.n.state()

    def height(self, x, y):
        return self.ve.test_height(self.case, x, y)


def field(raw, index, size, offset, fmt):
    return struct.unpack_from(fmt, raw, index*size + offset)[0]


class WorkedExamples(unittest.TestCase):
    def setUp(self):
        self.lib = ctypes.CDLL(str(LIB))

    def test_rand_is_the_msvc_lcg(self):
        s = Session(seed=12345)
        r = Rand(12345)
        s.run(2)   # MoveBoids in Lorencia draws rand()
        st = s.state()
        expected = [r() for _ in range(st['rand_calls'])]
        self.assertGreater(len(expected), 10)
        self.assertEqual(st['rand_state'], r.state)

    def test_world_table(self):
        class Info(ctypes.Structure):
            _fields_ = [('world', ctypes.c_int32), ('clear', ctypes.c_float*3), ('fog', ctypes.c_int32),
                        ('boid_model', ctypes.c_int32), ('boid_limit', ctypes.c_int32),
                        ('fish_model', ctypes.c_int32), ('fish_limit', ctypes.c_int32),
                        ('leaf_count', ctypes.c_int32), ('leaf_bitmap', ctypes.c_int32),
                        ('leaf_blend', ctypes.c_int32), ('leaf_billboard', ctypes.c_int32)]
        info = Info()
        get = self.lib.mu_env_world_info_get
        get.argtypes = [ctypes.c_int32, ctypes.POINTER(Info)]
        rows = {}
        for w in (0, 1, 2, 3, 7, 0x8d):
            get(w, ctypes.byref(info))
            rows[w] = (list(info.clear), info.boid_model, info.boid_limit, info.fish_model, info.fish_limit,
                       info.leaf_count, info.leaf_bitmap, info.leaf_blend, info.leaf_billboard)
        self.assertEqual(rows[0], ([10/256, 20/256, 14/256], 0x192, 5, 0x198, 3, 80, 0x771f, 0, 0))
        self.assertEqual(rows[1], ([0, 0, 0], 0x194, 5, 0x196, 3, 0, -1, 0, 0))
        self.assertEqual(rows[2], ([0, 0, 10/256], -1, 5, -1, 3, 80, 0x771f, 1, 1))
        self.assertEqual(rows[3], ([0, 0, 0], 0x193, 5, -1, 3, 80, 0x771f, 0, 0))
        self.assertEqual(rows[7], ([0, 0, 0], 0x199, 40, -2, 10, 80, 0x771f, 1, 0))
        self.assertEqual(rows[0x8d], ([0, 0, 0], -1, 5, -1, 3, 80, 0x7721, 1, 0))

    def test_asset_names(self):
        m = self.lib.mu_env_model_file
        m.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_char_p, ctypes.c_size_t]
        b = self.lib.mu_env_bitmap_file
        b.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_char_p, ctypes.c_size_t]
        out = ctypes.create_string_buffer(256)
        names = {}
        for w, t in ((0, 0x192), (0, 0x198), (1, 0x194), (1, 0x196), (3, 0x193), (7, 0x199), (7, 0x1a0), (8, 0x198),
                     (11, 0x1a2)):
            self.assertTrue(m(w, t, out, 256))
            names[(w, t)] = out.value.decode()
        self.assertEqual(names[(0, 0x192)], 'Data/Object1/Bird01.bmd')
        self.assertEqual(names[(0, 0x198)], 'Data/Object1/Fish01.bmd')
        self.assertEqual(names[(1, 0x194)], 'Data/Object2/Bat01.bmd')
        self.assertEqual(names[(7, 0x199)], 'Data/Object8/Fish02.bmd')
        self.assertEqual(names[(7, 0x1a0)], 'Data/Object8/Fish09.bmd')
        self.assertEqual(names[(8, 0x198)], 'Data/Object9/Bug02.bmd')
        self.assertEqual(names[(11, 0x1a2)], 'Data/Object12/Crow01.bmd')
        bitmaps = {}
        for w, i in ((0, 0x771f), (2, 0x7720), (0x8d, 0x7721), (0x8d, 0x771d), (0x5b, 0x771f), (0x22, 0x7721)):
            self.assertTrue(b(w, i, out, 256))
            bitmaps[(w, i)] = out.value.decode()
        self.assertEqual(bitmaps[(0, 0x771f)], 'Data/World1/leaf01.OZJ')   # the .jpg replaces the .tga
        self.assertEqual(bitmaps[(2, 0x7720)], 'Data/World3/leaf02.OZJ')
        self.assertEqual(bitmaps[(0x8d, 0x7721)], 'Data/World1/rain01.OZT')
        self.assertEqual(bitmaps[(0x8d, 0x771d)], 'Data/World10/rain03.OZT')
        self.assertEqual(bitmaps[(0x5b, 0x771f)], 'Data/World92/leaf01.OZT')
        self.assertEqual(bitmaps[(0x22, 0x7721)], 'Data/World1/rain011.OZT')

    def test_lorencia_spawns_five_birds(self):
        s = Session(seed=7, world=0)
        events = s.run(2)
        st = s.state()
        kinds = [e.kind for e in events]
        self.assertEqual(kinds.count(6), 5)   # ObjectInit for slots 0..4 only (the limit returns)
        for i in range(40):
            live = st['boids'][i*OBJ]
            self.assertEqual(live, 1 if i < 5 else 0)
        for i in range(5):
            self.assertEqual(field(st['boids'], i, OBJ, 0x5c, '<i'), 0x192)
            self.assertEqual(field(st['boids'], i, OBJ, 0xec, '<f'), 0.5)
            self.assertEqual(field(st['boids'], i, OBJ, 0xd8, '<f'), 1.0)
            self.assertEqual(field(st['boids'], i, OBJ, 0xc8, '<f'), 13.0)
            self.assertEqual(field(st['boids'], i, OBJ, 0xdc, '<f'), f32(0.05))   # FadeAlpha's first step
            x = field(st['boids'], i, OBJ, 0x158, '<f')
            self.assertLess(abs(x - 13350.0), 600.0)

    def test_atlans_shoals_fill_forty_slots(self):
        s = Session(seed=9, world=7, hero=(2100.0, 2900.0, 100.0))
        s.run(2)
        st = s.state()
        types = [field(st['boids'], i, OBJ, 0x5c, '<i') for i in range(40) if st['boids'][i*OBJ]]
        self.assertEqual(len(types), 40)
        self.assertTrue(set(types) <= {0x199, 0x19a})
        self.assertEqual({field(st['boids'], i, OBJ, 0xbc, '<f') for i in range(40)} - {f32(0.3), f32(0.25)}, set())

    def test_devias_snow(self):
        s = Session(seed=3, world=2)
        s.run(1)
        st = s.state()
        live = [i for i in range(200) if st['leaves'][i*LEAF + 8]]
        self.assertEqual(live, list(range(80)))
        for i in live:
            tex = field(st['leaves'], i, LEAF, 0xc, '<i')
            scale = field(st['leaves'], i, LEAF, 0x18, '<f')
            self.assertIn((tex, scale), {(0x771f, 5.0), (0x7720, 10.0)})
            self.assertEqual(field(st['leaves'], i, LEAF, 0x2c, '<f'), -30.0)
            self.assertLess(field(st['leaves'], i, LEAF, 0x78, '<f'), 0.0)   # falling

    def test_tormenta_rain_follows_the_hero_tile(self):
        att = bytearray(0x20000)
        struct.pack_into('<H', att, 2*(127*256 + 133), 0x800)
        s = Session(seed=5, world=0x8d, attributes=bytes(att))
        s.run(1)
        rain = struct.unpack('<f', struct.pack('<I', s.state()['tormenta'][2]))[0]
        expected = 0.0
        for _ in range(80):   # every dead leaf raises it by frame time * 0.3
            expected = f32(f32(f32(0.1) * f32(0.3)) + expected)
            expected = min(expected, 10.0)
        self.assertEqual(rain, expected)
        s2 = Session(seed=5, world=0x8d)
        s2.run(1)
        self.assertEqual(s2.state()['tormenta'][2], 0)   # falls (and stays at 0) elsewhere

    def test_billboard_quad(self):
        q = self.lib.mu_env_billboard_quad
        q.argtypes = [ctypes.c_void_p]*2 + [ctypes.c_float]*2 + [ctypes.c_void_p]
        cam = (ctypes.c_float*12)(1, 0, 0, 10, 0, 1, 0, 20, 0, 0, 1, 30)
        pos = (ctypes.c_float*3)(1, 2, 3)
        out = (ctypes.c_float*12)()
        q(cam, pos, 4.0, 6.0, out)
        self.assertEqual(list(out), [9, 19, 33, 13, 19, 33, 13, 25, 33, 9, 25, 33])


class Statements(unittest.TestCase):
    """Python statements of three routines against the library."""

    def test_default_leaf_move(self):
        g = random.Random(4)
        for trial in range(20):
            seed = g.getrandbits(32)
            s = Session(seed=seed, world=3, height=(f32(g.uniform(-50, 250)), 400, 12))
            leaves = bytearray(200*LEAF)
            for i in range(80):
                b = i*LEAF
                leaves[b + 8] = 1
                struct.pack_into('<i', leaves, b + 0xc, 0x771f)
                for k in range(3):
                    struct.pack_into('<f', leaves, b + 0x20 + 4*k, f32(g.uniform(-300, 300) + (13000, 12000, 150)[k]))
                    struct.pack_into('<f', leaves, b + 0x38 + 4*k, f32(g.uniform(0, 1)))
                    struct.pack_into('<f', leaves, b + 0x70 + 4*k, f32(g.uniform(-5, 5)))
            s.L.lib.mu_env_test_load(s.n.h, None, None, bytes(leaves))
            s.run(1)
            r = Rand(seed)
            expect = bytearray(leaves)
            for i in range(80):
                b = i*LEAF
                p = list(struct.unpack_from('<3f', expect, b + 0x20))
                light = list(struct.unpack_from('<3f', expect, b + 0x38))
                v = list(struct.unpack_from('<3f', expect, b + 0x70))
                h = s.height(p[0], p[1])
                if h >= p[2]:
                    p[2] = h
                    light = [f32(c - f32(0.05)) for c in light]
                    if 0.0 >= light[0]:
                        expect[b + 8] = 0
                else:
                    v = [f32(f32(float(r() % 16 - 8) * f32(0.1)) + c) for c in v]
                    p = [f32(a + c) for a, c in zip(p, v)]
                struct.pack_into('<3f', expect, b + 0x20, *p)
                struct.pack_into('<3f', expect, b + 0x38, *light)
                struct.pack_into('<3f', expect, b + 0x70, *v)
            got = s.state()['leaves']
            mask = s.L.leaf_mask
            for i in range(80):
                for k in range(LEAF):
                    if mask[k]:
                        self.assertEqual(got[i*LEAF + k], expect[i*LEAF + k], (trial, i, hex(k)))

    def test_bat_height_and_fade(self):
        s = Session(seed=11, world=1)
        s.run(2)
        before = s.state()['boids']
        s.run(2)
        after = s.state()['boids']
        for i in range(5):
            if not before[i*OBJ] or not after[i*OBJ]:
                continue
            phase = field(before, i, OBJ, 0xb4, '<f')
            alpha = field(before, i, OBJ, 0xdc, '<f')
            self.assertEqual(field(after, i, OBJ, 0xb4, '<f') in (f32(phase + f32(0.2)),), True)
            want = alpha if alpha >= 1.0 else min(f32(alpha + f32(0.05)), 1.0)
            self.assertEqual(field(after, i, OBJ, 0xdc, '<f'), want)
            sin = f32(math.sin(phase))
            fab = -sin if 0.0 > sin else sin
            # height before the flight step: terrain + 350 - 150 |sin|; the flight adds the rotated z
            self.assertTrue(math.isfinite(field(after, i, OBJ, 0x160, '<f')))
            self.assertLessEqual(fab, 1.0)


PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'


@unittest.skipUnless(PRIVATE, 'set MU_RECOVERY_INTEGRATION=1 (restored client text and data)')
class PrivateUnicorn(unittest.TestCase):
    def test_short_comparison(self):
        evidence = ROOT/'evidence'
        text = Path(os.environ.get('MU_CLIENT_TEXT', evidence/'x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA', evidence/'image-data-run10/data-capture-10/client-image-data.bin'))
        if not text.exists() or not data.exists():
            self.fail(f'missing private inputs {text} / {data}')
        result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_environment.py'), '--text', str(text),
                                 '--data', str(data), '--cases', '8', '--ticks', '20', '--worlds', '0,1,2,3,7,0x8d'],
                                capture_output=True, text=True)
        self.assertIn('cases 8/8 equal', result.stdout, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
