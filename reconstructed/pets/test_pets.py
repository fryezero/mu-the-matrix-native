"""Portable worked examples for reconstructed/pets (NATIVE-HELPERS-002, the pet process).

The comparison with the client's instructions is scripts/validate_pets.py
(Unicorn, private captures); these tests pin facts it established on synthetic
inputs through the same ctypes view (no client data).
"""
import ctypes
import math
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_pets as v  # noqa: E402


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def owner(**kw):
    o = {'live': 1, 'kind': 1, 'action': 1, 'key': 7, 'position': [5000.0, 6000.0, 100.0], 'angle': [0.0, 0.0, 45.0],
         'scale': 1.0, 'buff_12': 0, 'alt_pet': -1}
    o.update(kw)
    return o


def info(item, move, rng=50.0, follow=1, scale=0.5, blend=-1, speed=0.5):
    i = v.Info()
    i.item, i.slot, i.move, i.range, i.follow, i.scale, i.blend_mesh = item - 0x1a00, 8, move, rng, follow, scale, blend
    for k in range(5):
        i.speed[k] = speed + 0.1 * k
    return i


class Pets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = v.load_library()

    def make(self, item, record, owners=None, clock=100000):
        owners = owners or [owner()]
        case = {'seed': 1, 'owners': owners, 'bone_salt': 5, 'frustum_salt': 0}
        n = v.Native(self.lib, case)
        n.set_owners(owners)
        n.s = {'clock': clock}
        n.p.table[0] = record
        n.pet.info = ctypes.pointer(n.p.table[0])
        self.lib.mu_hp_object_init(ctypes.addressof(n.pet.object))
        pos = v.V3(*owners[0]['position'])
        ok = self.lib.mu_pet_create_object(ctypes.byref(n.p), ctypes.byref(n.pet), item, 0x24e6 + item - 0x1a00,
                                           ctypes.addressof(pos), 0, 0)
        self.assertEqual(ok, 1)
        return n

    def inputs(self, n, hero=0, helper_type=0x1a43, world_time=0.0, items=True):
        i = v.Inputs()
        i.scene, i.hero, i.helper_type, i.world_time = 6, hero, helper_type, world_time
        i.items = ctypes.cast(n.ground, ctypes.POINTER(v.Ground)) if items else None
        return i

    def test_petdata_file(self):
        lib = self.lib
        plain = bytearray(0x600)
        plain[0:0x30] = bytes(info(0x1a40, 0))
        plain[0x30:0x60] = bytes(info(0x1a43, 1, 10.0, 0, 0.8))
        enc = bytes(b ^ (0xfc, 0xcf, 0xab)[i % 3] for i, b in enumerate(plain[:0x30])) + \
            bytes(b ^ (0xfc, 0xcf, 0xab)[i % 3] for i, b in enumerate(plain[0x30:0x60])) + \
            b''.join(bytes(b ^ (0xfc, 0xcf, 0xab)[i % 3] for i, b in enumerate(plain[r*0x30:(r+1)*0x30]))
                     for r in range(2, 32))
        buf = ctypes.create_string_buffer(enc, len(enc))
        total = lib.mu_pet_checksum(buf, 0x600, 0x3bb2)
        table = (v.Info * 32)()
        good = enc + struct.pack('<I', total)
        self.assertEqual(lib.mu_pet_data_load(ctypes.create_string_buffer(good, len(good)), len(good), table), 0)
        self.assertEqual((table[0].item, table[1].item, table[1].move, f32(table[1].scale)), (0x40, 0x43, 1, f32(0.8)))
        bad = enc + struct.pack('<I', total ^ 1)
        self.assertEqual(lib.mu_pet_data_load(ctypes.create_string_buffer(bad, len(bad)), len(bad), table), 2)
        self.assertEqual(bytes(table), bytes(ctypes.sizeof(table)))   # the table stays zero (memset first)
        self.assertEqual(lib.mu_pet_data_load(None, 0, table), 1)
        # the checksum starts from key << 9 and xor-folds every 16 bytes
        self.assertEqual(lib.mu_pet_checksum(ctypes.create_string_buffer(bytes(16), 16), 16, 0x3bb2),
                         (0x3bb2 << 9) ^ (((0x3bb2 << 9) + 0x3bb2) >> 1))

    def test_create_fields(self):
        n = self.make(0x1a7b, info(0x1a7b, 1, 10.0, 0, 0.5, blend=0), [owner(scale=1.2)])
        o = n.pet.object
        self.assertEqual((o.live, o.lighting, o.type, o.blend_mesh, f32(o.scale), o.lifetime), (1, 1, 0x2561, 0, 0.5, 30))
        self.assertEqual((tuple(o.light), f32(o.alpha), f32(o.alpha_target), f32(o.velocity)), ((3.0,)*3, 0.0, 1.0, 0.5))
        self.assertEqual(f32(o.position[1]), f32(6000.0 + f32(60.0 * f32(1.2))))   # model 0x2561's y offset
        self.assertEqual((n.pet.created, n.pet.item, n.pet.owner), (100000, 0x1a7b, 0))

    def test_fly_follow(self):
        n = self.make(0x1a40, info(0x1a40, 0, 50.0), [owner(position=[5000.0, 6000.0, 100.0])])
        o = n.pet.object
        o.position[0] = 5100.0
        i = self.inputs(n)
        self.lib.mu_pet_update(ctypes.byref(n.p), ctypes.byref(n.pet), ctypes.byref(i))
        self.assertEqual(f32(o.position[2]), f32(100.0 + 230.0))      # 230 * owner scale above the owner
        dist2 = 100.0 * 100.0
        self.assertEqual(f32(o.direction[1]), -f32(f32(math.log(dist2)) * f32(1.8)))   # ln(dist^2) * 1.8
        # beyond range^4 the pet jumps onto the owner, 200 above it
        o.position[0], o.position[1] = 9000.0, 9000.0
        n.s = {'clock': 100040}
        self.lib.mu_pet_update(ctypes.byref(n.p), ctypes.byref(n.pet), ctypes.byref(i))
        self.assertAlmostEqual(o.position[2], 300.0, places=3)

    def test_collector_states(self):
        n = self.make(0x1a43, info(0x1a43, 1, 10.0, 0, 0.8), [owner()], clock=50000)   # the 100 s wait not due
        n.set_items([None]*3 + [{'live': 1, 'visible': 1, 'type': 0x1c0f, 'position': [5100.0, 6050.0, 100.0]}] +
                    [None]*996)
        i = self.inputs(n)
        self.lib.mu_pet_update(ctypes.byref(n.p), ctypes.byref(n.pet), ctypes.byref(i))
        q = n.pet
        self.assertEqual((q.has_target, q.target_item, q.state), (1, 3, 1))   # zen within 300 of the owner
        self.assertEqual(f32(q.object.position[2]), f32(120.0))              # owner + 20
        elapsed = 3   # GetTickCount - created: the test clock advances 3 per call
        self.assertEqual(f32(q.angle1), f32(f32(float(elapsed % 4000)) * f32(0.00157)))
        # an owner that is not the hero only follows (state 4)
        i.hero = -1
        self.lib.mu_pet_update(ctypes.byref(n.p), ctypes.byref(n.pet), ctypes.byref(i))
        self.assertEqual(q.state, 4)

    def test_pickup_request(self):
        n = self.make(0x1a50, info(0x1a50, 1, 10.0, 0, 0.8), [owner()])
        n.set_items([{'live': 1, 'visible': 1, 'type': 0x1c0f, 'position': [5000.0, 6000.0, 100.0]}] + [None]*999)
        q = n.pet
        q.state, q.has_target, q.target_item = 2, 1, 0
        q.target[0], q.target[1], q.target[2] = 5000.0, 6000.0, 100.0
        q.pick_tick, q.wait_tick = 0, 5000   # the 1 s pick interval is due, the 3 s wait is not
        n.s = {'clock': 5000}
        i = self.inputs(n)
        self.lib.mu_pet_update(ctypes.byref(n.p), ctypes.byref(n.pet), ctypes.byref(i))
        self.assertIn(('pickup', (('head', 0xc1, 0), 0, 0)), n.log)
        self.assertEqual((n.p.pending_pickup, q.target_item), (0, -1))
        self.assertIn(('sound', 0x1f, 0, 0), n.log)   # 0x00eaeacf in state 2

    def test_visuals(self):
        lib = self.lib
        n = self.make(0x1a40, info(0x1a40, 0), [owner()])
        r = n.render_host()
        i = self.inputs(n)
        lib.mu_pet_visuals(ctypes.byref(n.p), ctypes.byref(n.pet), ctypes.byref(i), ctypes.byref(r), 0)
        kinds = [(e[0], e[1]) for e in n.log]
        self.assertEqual(kinds[0], ('remember', 0xffffffff))
        self.assertEqual(kinds[1:3], [('sprite', 0x8099), ('sprite', 0x7f78)])
        self.assertEqual(kinds.count(('particle', 0x7ffd)), 5)
        self.assertEqual(kinds[-3:], [('remember', 0x8085), ('sprite', 0x7f78), ('sprite', 0x7f78)])
        # the skeleton's flames only while its owner is not in the actions 1..0x31, 0x133..0x141, 0x148..0x185
        for action, particles in ((1, 0), (0x150, 0), (0, 1), (0x90, 1)):
            n = self.make(0x1a7b, info(0x1a7b, 1, 10.0, 0, 0.5), [owner(action=action)])
            r = n.render_host()
            lib.mu_pet_visuals(ctypes.byref(n.p), ctypes.byref(n.pet), ctypes.byref(i), ctypes.byref(r), 0)
            got = sum(1 for e in n.log if e[0] == 'particle')
            self.assertEqual(got > 0, bool(particles), action)

    def test_render_hidden_by_the_other_pet_slot(self):
        n = self.make(0x1a6a, info(0x1a6a, 1, 12.0), [owner(alt_pet=2)])
        r = n.render_host()
        i = self.inputs(n)
        self.lib.mu_pet_render(ctypes.byref(n.p), ctypes.byref(n.pet), ctypes.byref(i), ctypes.byref(r))
        self.assertEqual(n.log, [])


if __name__ == '__main__':
    unittest.main()
