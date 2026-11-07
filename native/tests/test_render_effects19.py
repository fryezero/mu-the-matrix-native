"""RENDER-EFFECTS-019: map-object records through 0x0129f671's matrix (reconstructed/objects/map_effects.c, used by
the native map-object update) and Test Area 121's particle kinds 0x801e/7, 0x801c/9, 0x801b/5
(reconstructed/particles/test_area_kinds.inc). The portable tests build the authored C alone; the pinned instruction
comparison runs separately (scripts/validate_render_effects19.py)."""
import ctypes as C
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

NATIVE = Path(__file__).resolve().parents[1]
ROOT = NATIVE.parent
sys.path.insert(0, str(ROOT/'scripts'))
sys.path.insert(0, str(ROOT/'reconstructed/particles'))
import validate_render_effects19 as r19  # noqa: E402
from test_particles import Fixed, f32, vp  # noqa: E402

PARTICLES = ROOT/'reconstructed/particles'


def image(position, scale=1.0, angle=(0.0, 0.0, 0.0)):
    img = bytearray(r19.OBJ_SIZE)
    struct.pack_into('<f', img, 0xa0, scale)
    struct.pack_into('<6f', img, 0x158, *position, *angle)
    return bytes(img)


def as_floats(words):
    return list(struct.unpack('<16f', struct.pack('<16I', *words)))


class MapRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.lib = r19.build_map(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def world(self, lists):
        total = sum(len(m) for m in lists.values())
        nxt = (C.c_int32 * total)(*([-1] * total))
        w = r19.ObjWorld()
        for s in range(r19.SECTORS):
            w.head[s] = -1
        for s, members in lists.items():
            w.head[s] = members[0]
            for a, b in zip(members, members[1:]):
                nxt[a] = b
        w.count, w.next = total, nxt
        self._keep = nxt
        return w

    def test_sector_predicate_is_false_only_for_an_object_alone(self):
        w = self.world({3: [2, 0, 4], 200: [1], 17: [3]})
        self.assertEqual([self.lib.mu_map_effects_in_sector(C.byref(w), k) for k in range(5)], [1, 0, 1, 0, 1])

    def matrix(self, follow, bone, in_sector, pose=None, pose_bones=0, scale=1.0):
        out = (C.c_uint32 * 16)()
        img = image((1000.0, 2000.0, 50.0), scale)
        status = self.lib.mu_map_effect_matrix(out, img, in_sector, pose, pose_bones, bone, follow)
        return status, as_floats(out)

    def test_unfollowed_bone_takes_the_pose_translation(self):
        bones = [0.0] * (12 * 30)
        bones[12 * 29 + 3], bones[12 * 29 + 7], bones[12 * 29 + 11] = 1007.0, 1996.0, 305.0
        pose = (C.c_float * len(bones))(*bones)
        address = C.cast(pose, C.c_void_p).value
        status, m = self.matrix(0, 29, 1, address, 30, scale=1.5)
        self.assertEqual(status, r19.OK)
        self.assertEqual(m[12:15], [1007.0, 1996.0, 305.0])           # in a sector list: the bone alone
        self.assertEqual((m[0], m[5], m[10], m[15]), (1.5, 1.5, 1.5, 1.0))
        status, m = self.matrix(0, 29, 0, address, 30)
        self.assertEqual(m[12:15], [2007.0, 3996.0, 355.0])           # alone in its sector: plus the position
        status, m = self.matrix(1, 29, 0, address, 30)                 # following, alone: placed by the position
        self.assertEqual((status, m[12:15]), (r19.OK, [2007.0, 3996.0, 355.0]))
        self.assertEqual(self.matrix(0, 30, 1, address, 30)[0], r19.UNPOSED)
        self.assertEqual(self.matrix(0, 0, 1, None, 30)[0], r19.UNPOSED)

    def test_bone_minus_one_and_below(self):
        status, m = self.matrix(0, -1, 1)
        self.assertEqual((status, m[12:15]), (r19.OK, [1000.0, 2000.0, 50.0]))
        status, m = self.matrix(0, -3, 1)
        self.assertEqual((status, m[12:15]), (r19.OK, [0.0, 0.0, 0.0]))
        self.assertEqual(self.matrix(1, -3, 1)[0], r19.UNDEFINED)
        status, m = self.matrix(1, -1, 1)
        self.assertEqual((status, m[0], m[12:15]), (r19.OK, 1.0, [1000.0, 2000.0, 50.0]))


class TestAreaKinds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(PARTICLES)], check=True, capture_output=True)
        cls.v = vp()
        cls.lib = cls.v.load_library(PARTICLES/('libclient_particles.' + r19.SUFFIX))

    def create(self, kind, rands, scale=1.0, scene=6):
        fx = Fixed(rands)
        host = fx.host(scene=scene)
        p = self.v.Particle()
        ok = self.lib.mu_pt_create_record(C.byref(p), C.byref(host), kind[0], self.v.F3(1000.0, 2000.0, 150.0),
                                          self.v.F3(0.0, 0.0, 0.0), self.v.F3(1.0, 0.5, 0.25), kind[1], f32(scale),
                                          -1, 7)
        return p, ok, fx

    def test_kinds_are_served_and_neighbours_are_not(self):
        for kind in r19.TA_PT:
            self.assertEqual(self.lib.mu_pt_kind_supported(*kind), 1, kind)
        for kind in ((0x801e, 5), (0x801c, 10), (0x801b, 6), (0x801d, 7)):
            self.assertEqual(self.lib.mu_pt_kind_supported(*kind), 0, kind)

    def test_waterfall5_draws_waterfall4_on_even_rand(self):
        p, ok, fx = self.create((0x801e, 7), [4, 361, 10, 1, 1, 2])
        self.assertEqual((ok, p.tex_type, p.lifetime, p.rotation), (1, 0x801d, 30, 1.0))
        self.assertAlmostEqual(p.scale, 1.5, places=6)
        self.assertEqual(list(p.velocity), [-2.0, -4.0, 5.0])
        p, ok, fx = self.create((0x801e, 7), [3])
        self.assertEqual(p.tex_type, 0x801e)
        self.assertEqual(fx.calls, 6)

    def test_spray_and_mist_create_and_move(self):
        p, ok, fx = self.create((0x801b, 5), [0] * 15, scale=0.5, scene=5)
        self.assertEqual((ok, p.lifetime, p.gravity, list(p.light)), (1, 40, 2.0, [0.25] * 3))
        self.assertEqual(fx.calls, 15)
        self.assertEqual(list(p.position), [960.0, 1960.0, 130.0])
        host = fx.host()
        p.moving = 0
        self.assertEqual(self.lib.mu_pt_move_record(C.byref(p), C.byref(host)), 1)
        self.assertEqual(p.position[2], f32(f32(2.0 + f32(1.0 + f32(0.1))) + 130.0))
        m, ok, fx = self.create((0x801c, 9), [0] * 7, scale=2.0)
        self.assertEqual((ok, m.lifetime, m.velocity[2], fx.calls), (1, 30, 2.0, 7))
        self.assertEqual(list(m.position), [980.0, 1980.0, 140.0])


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions_and_compiled_mutants(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects19.py'),
                            '--cases', '20', '--mutations', '--output', str(out)], check=True, capture_output=True)
            report = json.loads(out.read_text())
        self.assertTrue(report['all_equal'])
        self.assertTrue(report['all_mutants_caught'])
        self.assertEqual(report['instruction_cases'], CASES)
        self.assertEqual(len(report['mutants']), MUTANTS)


CASES, MUTANTS = 260, 25   # the registry row (scripts/validators.toml)


if __name__ == '__main__':
    unittest.main()
