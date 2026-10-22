"""Portable worked examples for reconstructed/helpers (NATIVE-HELPERS-001).

The comparison with the client's instructions is scripts/validate_helpers.py
(Unicorn, private captures); these tests pin facts it established on
synthetic inputs through the same ctypes view (no client data).
"""
import ctypes
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_helpers as v  # noqa: E402


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


class Rand:
    def __init__(self, seed):
        self.state = seed

    def __call__(self):
        self.state = (self.state * 214013 + 2531011) & 0xffffffff
        return (self.state >> 16) & 0x7fff


def owner(**kw):
    o = {'live': 1, 'fade': 0, 'kind': 1, 'action': 1, 'type': 0xa91, 'position': [5000.0, 6000.0, 100.0],
         'angle': [0.0, 0.0, 45.0], 'buff_12': 0, 'class_byte': 1, 'safe_zone': 0, 'hidden': 0, 'ring': 0,
         'weapon': [-1, -1], 'weapon_kind': [0, 0], 'weapon_54': 0}
    o.update(kw)
    return o


class Library(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = v.load_library()

    def native(self, owners, seed=1, **case):
        c = {'seed': seed, 'owners': owners, 'height_base': 10.0, 'frustum_salt': 0, 'bone_salt': 3}
        c.update(case)
        n = v.Native(self.lib, c)
        n.set_owners(owners)
        return n


class Mounts(Library):
    def test_factory_classes(self):
        lib = self.lib
        expect = {0x1a02: 1, 0x1a03: 2, 0x1a04: 3, 0x1a25: 4, 0x19d7: 5, 0x19e3: 6, 0x184b: 8, 0x1853: 10,
                  0x185d: 12, 0x1833: 14, 0x1835: 16, 0x28f7: 18}
        for item, cls in expect.items():
            self.assertEqual(lib.mu_hp_mount_class(lib.mu_hp_mount_kind(item, 0, 0), item, 0), cls)
        # no ride item: the ride state picks the transformation classes (kind 2)
        self.assertEqual(lib.mu_hp_mount_kind(0xffff, 2, 0), 2)
        self.assertEqual(lib.mu_hp_mount_class(2, 0xffff, 2), 20)
        self.assertEqual(lib.mu_hp_mount_kind(0xffff, 0, 0), -1)
        self.assertEqual(lib.mu_hp_mount_class(-1, -1, -1), 0)
        self.assertEqual(lib.mu_hp_mount_class(0, 0x1a00, 0), 0)   # the angel is no mount

    def test_models_bones_and_speeds(self):
        lib = self.lib
        uniria = lib.mu_hp_mount_class_info(1).contents
        self.assertEqual((uniria.model, uniria.file, uniria.bone, uniria.lift), (0x417, b'Rider01', b'Bip01 Spine', 20.0))
        self.assertEqual([lib.mu_hp_mount_model(4, s) for s in (0, 1, 2, 3, 4)], [0x4a9, 0x4a8, 0x4aa, 0x4a9, 0x4ab])
        self.assertEqual(f32(lib.mu_hp_mount_speed(1, 2)), f32(0.34))
        self.assertEqual(f32(lib.mu_hp_mount_speed(1, 9)), f32(0.4))      # no key: 0x0103dbf4's default
        self.assertEqual(f32(lib.mu_hp_mount_speed(3, 8)), 1.0)           # Dark Horse 8..10
        self.assertEqual(f32(lib.mu_hp_mount_speed(4, 3)), f32(0.6))      # Fenrir run
        tauros = lib.mu_hp_mount_class_info(16).contents
        self.assertEqual((tauros.scale_offset, f32(tauros.scale), tauros.shadow_mode), (1, f32(1.85), 1))

    def test_action_category_and_rider_actions(self):
        lib = self.lib
        cat = lib.mu_hp_action_category
        self.assertEqual([cat(a) for a in (0, 1, 0x31, 0x32, 0x4e, 0x4f, 0x6f, 0x89, 0x133, 0x142, 0x148, 0x186)],
                         [0, 0, 0, 1, 1, 2, 3, 4, 6, 7, 8, 0])
        unarmed = self.native([owner()])
        self.assertEqual([lib.mu_hp_rider_action(ctypes.byref(unarmed.h), 0, how) for how in (0, 1, 2, 6, 3)],
                         [0x26, 0x47, 0x67, 0x13b, 0])
        armed = self.native([owner(weapon=[0xae6, 0xae7])])
        self.assertEqual(lib.mu_hp_rider_action(ctypes.byref(armed.h), 0, 1), 0x4a)   # both hands
        right = self.native([owner(weapon=[0xae6, -1], class_byte=0x19)])
        self.assertEqual(lib.mu_hp_rider_action(ctypes.byref(right.h), 0, 0), 0x2a)   # class nibble 9 stands 0x2a
        lance = self.native([owner(weapon=[0xae6, 0xae7], weapon_kind=[0x5a, 0])])
        self.assertEqual(lib.mu_hp_rider_action(ctypes.byref(lance.h), 0, 2), 0x6c)
        safe = self.native([owner(weapon=[0xae6, -1], safe_zone=1)])
        self.assertEqual(lib.mu_hp_rider_action(ctypes.byref(safe.h), 0, 0), 0x26)    # the safe zone rides unarmed

    def test_move_lifts_the_rider(self):
        lib = self.lib
        n = self.native([owner(action=0x26)])
        mt = v.Mount()
        mt.live, mt.cls, mt.kind, mt.item, mt.state, mt.model, mt.owner, mt.has_model = 1, 1, 0, 0x1a02, 0, 0x417, 0, 1
        mt.object.alpha, mt.object.scale = 1.0, 1.0
        n.mount = mt
        inputs = v.Inputs(0, 6, 0, 0)
        self.assertEqual(lib.mu_hp_mount_move(ctypes.byref(n.h), ctypes.byref(mt), ctypes.byref(inputs)), 1)
        self.assertEqual(tuple(mt.object.position), (5000.0, 6000.0, 100.0))   # the base move copies the rider
        bone = v.bone_answer('Bip01 Spine', (0.0, 0.0, 0.0), 3)
        self.assertEqual(tuple(mt.offset), (bone[0], bone[1], f32(bone[2] + 20.0)))
        lib.mu_hp_mount_place_owner(ctypes.byref(n.h), ctypes.byref(mt), 1)
        self.assertEqual(tuple(n.owners[0].position), (f32(5000.0 + bone[0]), f32(6000.0 + bone[1]),
                                                        f32(100.0 + f32(bone[2] + 20.0))))
        n.owners[0].action = 1   # not a ride action: no lift
        lib.mu_hp_mount_place_owner(ctypes.byref(n.h), ctypes.byref(mt), 1)
        self.assertEqual(tuple(n.owners[0].position), (5000.0, 6000.0, 100.0))


class Bugs(Library):
    def test_angel_spawns_around_its_owner(self):
        lib = self.lib
        n = self.native([owner()], seed=77)
        inputs = v.Inputs(0, 6, 0, 0)
        pos = v.V3(5000.0, 6000.0, 100.0)
        slot = lib.mu_hp_create_bug(ctypes.byref(n.h), ctypes.byref(inputs), 0x24e6, ctypes.addressof(pos), 0, 0)
        self.assertEqual(slot, 0)
        r = Rand(77)
        b = n.h.bugs[0]
        self.assertEqual((b.live, b.type, b.blend_mesh, b.lifetime), (1, 0x24e6, 1, 30))
        self.assertEqual((f32(b.scale), b.alpha, b.alpha_target, f32(b.velocity)), (f32(0.7), 0.0, 1.0, 0.5))
        self.assertEqual(tuple(b.position), (float(r() % 512 - 256) + 5000.0, float(r() % 512 - 256) + 6000.0,
                                             float(r() % 128 + 128) + 100.0))
        # the next one takes the next free slot; the run-speed worlds refuse
        self.assertEqual(lib.mu_hp_create_bug(ctypes.byref(n.h), ctypes.byref(inputs), 0x24e6, ctypes.addressof(pos),
                                              0, 0), 1)
        self.assertEqual(lib.mu_hp_create_bug(ctypes.byref(n.h), ctypes.byref(v.Inputs(0x12, 6, 0, 0)), 0x24e6,
                                              ctypes.addressof(pos), 0, 0), -1)

    def test_only_the_angel_follows_a_non_player(self):
        lib = self.lib
        n = self.native([owner(type=0x7a5)])
        inputs = v.Inputs(0, 6, 0, 0)
        pos = v.V3(0.0, 0.0, 0.0)
        self.assertEqual(lib.mu_hp_create_bug(ctypes.byref(n.h), ctypes.byref(inputs), 0x24e7, ctypes.addressof(pos),
                                              0, 0), -1)
        self.assertEqual(lib.mu_hp_create_bug(ctypes.byref(n.h), ctypes.byref(inputs), 0x24e6, ctypes.addressof(pos),
                                              0, 0), 0)

    def test_move_and_delete(self):
        lib = self.lib
        n = self.native([owner()], seed=5)
        inputs = v.Inputs(0, 6, 0, 0)
        pos = v.V3(5000.0, 6000.0, 100.0)
        lib.mu_hp_create_bug(ctypes.byref(n.h), ctypes.byref(inputs), 0x24e6, ctypes.addressof(pos), 0, 0)
        for _ in range(50):
            lib.mu_hp_move_bugs(ctypes.byref(n.h), ctypes.byref(inputs))
        b = n.h.bugs[0]
        self.assertGreater(b.alpha, 0.9)   # FadeAlpha toward 1 (alpha speed 0.1 of ObjectInit)
        sparkles = [e for e in n.log if e[0] == 'particle' and e[1] == 0x7f25]
        self.assertEqual(len(sparkles), 4 * 50)   # four Spark02 per step without the buff 0x12
        self.assertTrue(all(e[2] == 1 for e in sparkles))
        lib.mu_hp_delete_bug(ctypes.byref(n.h), 0)
        self.assertEqual(n.h.bugs[0].live, 0)


if __name__ == '__main__':
    unittest.main()


class MountVisuals(unittest.TestCase):
    """NATIVE-HELPERS-002: the registry functors (scripts/validate_mount_visuals.py compares them in Unicorn)."""

    @classmethod
    def setUpClass(cls):
        import validate_mount_visuals as mv
        cls.mv = mv
        cls.lib = mv.load_library(str(v.LIB))

    def run_functor(self, typ, **kw):
        case = {'type': typ, 'subtype': 0, 'action': 0, 'frame': 0.0, 'alpha': 1.0, 'blend_mesh': -1,
                'blend_light': 1.0, 'a4': 0.0, 'u': 0.0, 'v': 0.0, 'o68': -1, 'position': [100.0, 200.0, 0.0],
                'angle': [0.0, 0.0, 0.0], 'world': 0, 'time': 0.0, 'w9b0418': False, 'event': False,
                'color': [0.5, 0.5, 0.5], 'm94': 0xff, 'rand': []}
        case.update(kw)
        return self.mv.native_log(self.lib, case)

    def test_wave(self):
        # 0x0185bdc4(-4, 0) at time 0: x = 0 -> (1 - cos 0) / 2 = 0; half a period later the top
        self.assertEqual(self.lib.mu_hp_wave(-4.0, 0.0, 0.0), 0.0)
        self.assertAlmostEqual(self.lib.mu_hp_wave(1.0, 0.0, 3141.0), 1.0, places=5)

    def test_uniria_draws_the_default_body(self):
        r, calls, rands = self.run_functor(0x417)
        self.assertEqual((r, calls), (0, []))

    def test_dark_horse_gold_neck_and_second_shadow(self):
        r, calls, _ = self.run_functor(0x410)
        self.assertEqual(r, 1)
        self.assertEqual(calls[0][0], 'body')
        meshes = [c for c in calls if c[0] == 'mesh']
        self.assertEqual([c[1] for c in meshes], [0xc, 0xd, 0xe, 0xf])
        self.assertEqual(meshes[0][2], 0x44)
        self.assertEqual(tuple(round(x, 3) for x in meshes[0][9]), (1.0, 0.8, 0.3))
        self.assertEqual(calls[-1], ('shadow', (-1, -1, 8, 9, 0)))
        # no second shadow in the flying worlds
        r, calls, _ = self.run_functor(0x410, world=10)
        self.assertNotIn('shadow', [c[0] for c in calls])

    def test_fenrir_flares_effects_and_sparks(self):
        r, calls, rands = self.run_functor(0x4ab, action=4)
        kinds = [c[0] for c in calls]
        self.assertEqual(kinds.count('sprite'), 6)
        self.assertEqual(kinds.count('effect'), 2)
        self.assertEqual([c for c in calls if c[0] == 'particle'][0][1:2], (0x7f26,))
        self.assertEqual(rands, 2)
        light = [c for c in calls if c[0] == 'effect'][0][4]
        self.assertEqual(tuple(round(x, 3) for x in light), (0.8, 0.8, 0.1))

    def test_ghost_horse_glow_by_level(self):
        low = self.run_functor(0x671, subtype=0)[1]
        high = self.run_functor(0x671, subtype=2)[1]
        self.assertLess(len(low), len(high))   # levels 1+ add the 5/7 passes, 2+ the 6 pass

    def test_object_subtype_from_state(self):
        self.assertEqual(self.lib.mu_hp_mount_object_subtype(10, 7, 0), 7)      # Shining Tail
        self.assertEqual(self.lib.mu_hp_mount_object_subtype(3, 7, 0), 0)       # Dark Horse keeps it
        self.assertEqual(self.lib.mu_hp_mount_object_subtype(19, 7, 0), -1)     # the transformations
