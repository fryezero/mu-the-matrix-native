"""RENDER-WORLDS-Q: public dispatch, the Kubera light name, bounded logging and private instruction comparisons."""
import ctypes as C
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_object_render as v  # noqa: E402
import validate_worlds_q as q  # noqa: E402
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
LIGHT, PARTICLE, SPRITE, SOUND = 0x16cacfc, 0x168fafd, 0x1692eb7, 0xa6ac96


def table(*records):
    """Action records (PlaySpeed, keys) in client layout."""
    return C.create_string_buffer(b''.join(struct.pack('<4xfhBB4x', s, k, 1, 0) for s, k in records),
                                  16 * max(len(records), 1))


class WorldsQTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/terrain')], check=True)
        cls.lib = q.bind(v.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}')).dll
        for name, args in {'mu_worlds_q_owns': [C.c_int32],
                           'mu_worlds_q_create': [C.c_void_p, C.c_int32, C.POINTER(q.Inputs), C.POINTER(v.Log)],
                           'mu_worlds_q_move': [C.c_void_p, C.c_int32, C.POINTER(q.Inputs), C.POINTER(v.Log)],
                           'mu_worlds_q_visual': [C.c_void_p, C.c_int32, C.c_int, C.POINTER(q.Inputs),
                                                  C.POINTER(v.Log)]}.items():
            getattr(cls.lib, name).argtypes = args
            getattr(cls.lib, name).restype = C.c_int
        cls.terrain = C.CDLL(str(ROOT / f'reconstructed/terrain/libterrain.{v.SUFFIX}'))
        cls.terrain.mu_terrain_light_name.argtypes = [C.c_int32]
        cls.terrain.mu_terrain_light_name.restype = C.c_char_p

    def inputs(self, world, actions=None, rand=lambda: 0, bone=True, now=0, hero=(0, 0, 0), tile=(0, 0)):
        self.handler = q.Handler(0, None, 1, None)
        self._keep = [q.ACTIONS_FN(lambda ctx, t, out: (out.__setitem__(0, len(actions.raw) // 16) or
                                                       C.addressof(actions)) if actions is not None else None),
                      v.RAND_FN(lambda ctx: rand()),
                      q.BONE_FN(lambda ctx, k, local, out: [out.__setitem__(i, float(k * 10 + i)) for i in range(3)])
                      if bone else q.BONE_FN()]
        return q.Inputs(world, 0.0, 0.1, now, (C.c_float * 3)(*hero), (C.c_int32 * 2)(*tile), self._keep[0],
                        self._keep[1], self._keep[2], None, C.pointer(self.handler))

    def obj(self, typ, **fields):
        o = C.create_string_buffer(v.OBJ_SIZE)
        struct.pack_into('<i', o, 0x5c, typ)
        struct.pack_into('<ii', o, 0x68, -1, -1)
        struct.pack_into('<f', o, 0xc0, -30.0)
        struct.pack_into('<3f', o, 0x158, 1000.0, 2000.0, 0.0)
        struct.pack_into('<f', o, 0xa0, 1.0)
        for offset, fmt, value in fields.values():
            struct.pack_into(fmt, o, offset, value)
        return o

    def f(self, o, offset):
        return struct.unpack_from('<f', o.raw, offset)[0]

    def i(self, o, offset):
        return struct.unpack_from('<i', o.raw, offset)[0]

    def test_ownership_and_light_name(self):
        self.assertEqual([w for w in range(85, 135) if self.lib.mu_worlds_q_owns(w)], [91, 112, 122, 123, 124, 125,
                                                                                         126, 127])
        self.assertEqual([self.terrain.mu_terrain_light_name(w).decode() for w in (0, 122, 123, 124, 125, 126, 127,
                                                                                   128)],
                         ['TerrainLight', 'TerrainLight', 'TerrainLight_Fire', 'TerrainLight_Water',
                          'TerrainLight_Earth', 'TerrainLight_Wind', 'TerrainLight_Dark', 'TerrainLight'])

    def test_create(self):
        log = v.new_log()
        cases = [(91, 61, 0xc0, -428.571442), (91, 27, 0xc0, -3000.0), (112, 152, 0xc0, -400.0),
                 (122, 49, 0xc0, -400.0), (123, 29, 0xc0, -300.0), (125, 158, 0xc0, -600.0)]
        for world, typ, offset, value in cases:
            o = self.obj(typ)
            self.assertEqual(self.lib.mu_worlds_q_create(o, 0, C.byref(self.inputs(world)), C.byref(log)), 1)
            self.assertAlmostEqual(self.f(o, offset), value, places=3)
        o = self.obj(88)   # Swamp of Darkness: variant byte 1 (constructor) keeps type 88
        self.lib.mu_worlds_q_create(o, 0, C.byref(self.inputs(122)), C.byref(log))
        self.assertEqual((self.i(o, 0x5c), o.raw[0x0a]), (88, 1))
        o = self.obj(173)
        self.lib.mu_worlds_q_create(o, 0, C.byref(self.inputs(123)), C.byref(log))
        self.assertEqual(self.i(o, 0x68), -1)   # 173/174 are the jump table's default entries
        actions = table((1.0, 9), (0.5, 4))      # Kubera types 15/47/52: every action plays at 0.3, no loop
        o = self.obj(47)
        self.lib.mu_worlds_q_create(o, 0, C.byref(self.inputs(124, actions)), C.byref(log))
        for k in range(2):
            self.assertEqual(struct.unpack_from('<fhB', actions.raw, 16 * k + 4), (v.f32(0.3), (9, 4)[k], 0))
        self.assertEqual(self.lib.mu_ferea_create(None, C.byref(self.inputs(112))), 0)

    def test_move(self):
        log = v.new_log()
        o = self.obj(22)   # Acheron blend-mesh scroll
        self.lib.mu_worlds_q_move(o, 0, C.byref(self.inputs(91)), C.byref(log))
        self.assertEqual(self.f(o, 0xb0), v.f32(-0.01))
        o = self.obj(9)
        self.lib.mu_worlds_q_move(o, 0, C.byref(self.inputs(91, rand=lambda: 1)), C.byref(log))
        light = v.log_events(log)[-1]
        self.assertEqual((light[0], light[2:4], light[-1]), (LIGHT, (v.bits(1000.0), v.bits(2000.0)), 2))
        self.assertEqual(light[4], v.bits(v.f32(v.f32(0.4) * v.f32(1.2))))
        for tile, alpha in (((30, 120), 0.1), ((49, 120), 1.0)):   # Ferea type 51 fades near the hero
            o = self.obj(51)
            self.lib.mu_worlds_q_move(o, 0, C.byref(self.inputs(112, tile=tile)), C.byref(log))
            self.assertEqual(self.f(o, 0xd8), v.f32(alpha))
        o = self.obj(131, frame=(0xd0, '<f', 9.0), counter=(0x64, '<i', 0))   # Swamp of Darkness cycle
        self.lib.mu_worlds_q_move(o, 0, C.byref(self.inputs(122, table((0.0, 9), (0.0, 9)), rand=lambda: 3)),
                                  C.byref(log))
        self.assertEqual((struct.unpack_from('<H', o.raw, 0x2a)[0], self.i(o, 0x64), self.f(o, 0xd0)), (1, 18, 0.0))
        o = self.obj(52, action=(0x2a, '<H', 0))   # Kubera type 52: the hero within 500 starts action 1
        start = len(v.log_events(log))
        self.lib.mu_worlds_q_move(o, 0, C.byref(self.inputs(123, table(*[(0.0, 9)] * 4), hero=(1300, 2000, 0))),
                                  C.byref(log))
        self.assertEqual(struct.unpack_from('<H', o.raw, 0x2a)[0], 1)
        self.assertEqual([e[0] for e in v.log_events(log)[start:]], [q.Q_STOP, SOUND])
        o = self.obj(52)
        self.assertEqual(self.lib.mu_worlds_q_move(o, 0, C.byref(self.inputs(123)), C.byref(log)), 0)   # no model

    def test_visual(self):
        log = v.new_log()
        o = self.obj(55)
        self.assertEqual(self.lib.mu_worlds_q_visual(o, 0, 1, C.byref(self.inputs(91)), C.byref(log)), 1)
        self.assertEqual(v.log_events(log)[-1][:3], (PARTICLE, 0, 0x801c))
        o = self.obj(9)
        start = len(v.log_events(log))
        self.lib.mu_worlds_q_visual(o, 0, 1, C.byref(self.inputs(91)), C.byref(log))
        sprites = v.log_events(log)[start:]
        self.assertEqual([(e[0], e[2], e[3]) for e in sprites], [(SPRITE, 0x8155, v.bits(k * 10.0)) for k in (6, 11, 17)])
        self.assertEqual(self.lib.mu_worlds_q_visual(o, 0, 1, C.byref(self.inputs(91, bone=False)), C.byref(log)), -1)
        o = self.obj(176)
        start = len(v.log_events(log))
        for now in (5, 30, 1024 + 29):
            self.lib.mu_worlds_q_visual(o, 0, 1, C.byref(self.inputs(122, rand=lambda: 6, now=now)), C.byref(log))
        effects = v.log_events(log)[start:]
        self.assertEqual([(e[0], e[2]) for e in effects], [(q.Q_KEYED_EFFECT, 0x199)] * 2)
        self.assertEqual(effects[0][-1], 1)   # key: (u16)(int)scale
        o = self.obj(161)
        self.lib.mu_worlds_q_visual(o, 0, 1, C.byref(self.inputs(126, rand=lambda: 81)), C.byref(log))
        self.assertEqual(v.log_events(log)[-1][:3], (q.Q_KEYED_EFFECT, 0, 0x195))
        self.assertEqual(self.lib.mu_worlds_q_visual(o, 0, 1, C.byref(self.inputs(112)), C.byref(log)), -1)

    def test_log_capacity_preserves_state(self):
        for world, typ in ((91, 16), (123, 47), (112, 123)):
            results = []
            for capacity in (0, 1, 64):
                o = self.obj(typ, frame=(0xd0, '<f', 30.0), action=(0x2a, '<H', 1))
                self.lib.mu_worlds_q_move(o, 0, C.byref(self.inputs(world, table(*[(0.0, 9)] * 4), rand=lambda: 5,
                                                                       hero=(1000, 2000, 0))),
                                          C.byref(v.new_log(capacity)))
                results.append(o.raw)
            self.assertEqual(results[0], results[1])
            self.assertEqual(results[0], results[2])

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-q-test-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_q.py'), '--cases', '1000',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(sum(r['cases'] for r in result['families'].values()), 11000)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), 45)
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_light_name(self):
        with tempfile.TemporaryDirectory(prefix='worlds-q-light-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_world_light_name.py'), '--mutations',
                            '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            family = result['families']['light_name']
            self.assertEqual((family['cases'], family['equal'], family['stopped']), (304, 304, 0))
            self.assertEqual(result['old_rule_mismatches'], 5)
            self.assertEqual(sorted(result['kubera_names']), ['123', '124', '125', '126', '127'])
            self.assertTrue(all(m['detected'] > 0 for m in result['mutants']))


if __name__ == '__main__':
    unittest.main()
