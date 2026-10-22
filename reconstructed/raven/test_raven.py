"""Portable worked examples for reconstructed/raven (NATIVE-HELPERS-002).

The comparison with the client's instructions is scripts/validate_raven.py
(Unicorn, private captures); these tests pin facts it established on
synthetic inputs through the same ctypes view (no client data).
"""
import ctypes
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_raven as v  # noqa: E402


def owner(**kw):
    o = {'safe': 0, 'tile': [50, 60], 'pet_item': -1, 'pet_level': 0, 'ride': 0, 'action': 1, 'type': 0xa91,
         'scale': 1.0, 'frame': 2.0, 'position': [5020.0, 6030.0, 100.0], 'buff_12': 0, 'buff_3d': 0, 'buff_b2': 0,
         'buff_118': 0, 'has_mount': 0, 'mount_offset_z': 0.0, 'mount_state2': 0, 'has_info': 1, 'info_type': 5,
         'info_level': 1, 'bones': 0x40}
    o.update(kw)
    return o


def case(owners, **kw):
    c = {'seed': 7, 'owners': owners, 'height_base': 20.0, 'frustum_salt': 1, 'bone_salt': 2, 'keys_salt': 3,
         'anim_salt': 4, 'wall_salt': 5, 'world': 0, 'model_types': [0xa91, 0x411, 0x748], 'hero': 1, 'requested': 1,
         'pet_bones': [0x50]*len(owners), 'body_angle': [0.0, 0.0, 0.0], 'tick': 9, 'time': 1000.0}
    c.update(kw)
    return c


class Raven(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = v.load_library()

    def native(self, owners, **kw):
        c = case(owners, **kw)
        n = v.Native(self.lib, c)
        n.set_owners(c['owners'])
        self.inputs = v.Inputs(c['world'], c['tick'])
        return n

    def set(self, n, k, value, owners=None):
        self.lib.mu_rv_set_type(ctypes.byref(n.r), ctypes.byref(self.inputs), k, value)
        if owners is not None:
            n.read_owners(owners)   # the pet item and level word the routine wrote

    def move(self, n, k, owners, steps=1):
        for _ in range(steps):
            n.set_owners(owners)
            self.lib.mu_rv_move(ctypes.byref(n.r), ctypes.byref(self.inputs), k)

    def test_pet_byte(self):
        """0x00c92bea: 1 / 2 / 3 are the Dark Raven with the level word 1 / 20 / 40 (2 and 3 copy it to the pet)."""
        owners = [owner()]
        n = self.native(owners)
        for value, level, pet_level in ((1, 1, 0), (2, 20, 20), (3, 40, 40)):
            self.set(n, 0, value)
            self.assertEqual((n.owners[0].pet_item, n.owners[0].pet_level), (0x1a05, level))
            p = n.r.pets[0]
            self.assertEqual((p.live, p.level, p.object.type), (1, pet_level, 0x411))
            self.assertEqual((p.fade_in, p.fade_out), (1, 0))
            self.assertAlmostEqual(p.object.alpha, 0.1, places=6)
        self.set(n, 0, 0)
        self.assertEqual((n.owners[0].pet_item, n.r.pets[0].live), (-1, 0))

    def test_safe_zone_soul(self):
        """In a safe zone the constructor picks the soul model 0x748 and MovePet switches the AI to 3 (sit)."""
        owners = [owner(safe=1)]
        n = self.native(owners)
        self.set(n, 0, 1, owners)
        self.assertEqual(n.r.pets[0].object.type, 0x748)
        self.move(n, 0, owners)
        self.assertEqual(n.r.pets[0].object.ai, 3)

    def test_fade_and_swap(self):
        """Leaving the safe zone: the model check 0x00c92e04 fails, the soul fades out and the raven is re-created."""
        owners = [owner(safe=1)]
        n = self.native(owners)
        self.set(n, 0, 1, owners)
        self.move(n, 0, owners, 12)   # faded in
        self.assertEqual(n.r.pets[0].fade_in, 0)
        owners[0]['safe'] = 0
        self.move(n, 0, owners)
        self.assertEqual(n.r.pets[0].fade_out, 1)
        for _ in range(400):
            self.move(n, 0, owners)
            if n.r.pets[0].object.type == 0x411:
                break
        self.assertEqual(n.r.pets[0].object.type, 0x411)
        self.assertEqual(n.r.pets[0].fade_in, 1)

    def test_fly_band(self):
        """AI 0 / 1: the raven turns its pitch to climb below the band (owner z + 250) and to sink above it."""
        owners = [owner()]
        n = self.native(owners)
        self.set(n, 0, 1, owners)
        o = n.r.pets[0].object
        o.position[2] = 0.0
        self.move(n, 0, owners)
        self.assertLess(n.r.pets[0].object.angle[0], 0.0)
        n.r.pets[0].object.angle[0] = 0.0
        n.r.pets[0].object.position[2] = 1000.0
        self.move(n, 0, owners)
        self.assertGreater(n.r.pets[0].object.angle[0], 0.0)

    def draw(self, model, level, angle_z=10.0):
        c = {'model': model, 'world': 0, 'time': 5000.0, 'shadow_world': 0, 'event_block': 0, 'dim_world': 0,
             'color': [1.0, 1.0, 1.0], 'wave': 0.5, 'rsalt': 1, 'height_base': 0.0,
             'object': {name: ((0.0,)*count if count > 1 else 0) for name, _, _, count in v.OBJECT_FIELDS}}
        c['object'].update({'type': model, 'level': level, 'alpha': 1.0, 'blend_mesh': -1, 'hidden_mesh': -1,
                            'angle': (0.0, 0.0, angle_z), 'position': (100.0, 200.0, 300.0)})
        return v.native_draw_log(self.lib, c)

    def test_raven_meshes_by_level(self):
        """0x00a2eea5: mesh 3, then mesh 2 below level 20, mesh 1 below 40, else mesh 0 with the chrome passes."""
        def meshes(level):
            return [(d.mesh, d.flags) for d in self.draw(0x411, level)[2] if d.kind == 5]
        self.assertEqual(meshes(19), [(3, 2), (2, 2)])
        self.assertEqual(meshes(20), [(3, 2), (1, 2)])
        self.assertEqual(meshes(0x81), [(3, 2), (2, 2)])   # the level byte is signed
        self.assertEqual(meshes(40), [(3, 2), (0, 2), (0, 0x44), (3, 0x42)])

    def test_soul_turns(self):
        """0x00a55f03 turns the soul by 2 degrees a frame and wraps at 360."""
        o, _, draws = self.draw(0x748, 0, 358.5)
        self.assertEqual(o.angle[2], 0.0)
        o, _, draws = self.draw(0x748, 0, 100.0)
        self.assertEqual(o.angle[2], 102.0)
        self.assertEqual([d.kind for d in draws], [4, 5, 5, 5, 6, 7])


if __name__ == '__main__':
    unittest.main()
