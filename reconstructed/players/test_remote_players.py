"""Worked examples of reconstructed/players (NATIVE-PLAYERS-001), portable.

The library is built with make and driven through ctypes; the values are
read from the client routines (see docs/research/client-remote-players.md).
The Unicorn comparison lives in scripts/validate_players.py (private).
"""
import ctypes
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_players as vp  # noqa: E402  (ctypes views only; Unicorn is not needed)


class Library(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        cls.lib = vp.load_library()

    def character(self, **kw):
        c = vp.Character()
        c.model = 0xa91
        c.live = 1
        c.kind = 1
        c.helper = 0xffff
        c.pet_index = 0
        for i in range(3):
            c.pets[i] = -1
        for k in range(11):
            c.slots[k].type = -1
        for k, v in kw.items():
            setattr(c, k, v)
        return c

    def test_class_byte_swaps_the_nibbles(self):
        # 0x0139ca62: bit 3 -> bit 4, high nibble -> low, bits 2/1/0 -> bits 5/6/7
        self.assertEqual(self.lib.mu_rp_class_byte(0x10), 0x01)   # Dark Knight (packet 0x10)
        self.assertEqual(self.lib.mu_rp_class_byte(0x20), 0x02)   # Dark Wizard
        self.assertEqual(self.lib.mu_rp_class_byte(0x18), 0x11)   # Blade Knight: packet bit 3 -> class bit 4
        self.assertEqual(self.lib.mu_rp_class_byte(0x1c), 0x31)   # bit 2 -> bit 5
        self.assertEqual(self.lib.mu_rp_class_byte(0x01), 0x80)

    def test_item_level_table(self):
        self.assertEqual([self.lib.mu_rp_item_level(n) for n in range(9)], [0, 3, 5, 7, 9, 11, 13, 15, 0])

    def test_class_skin_index(self):
        # 0x0139d6a2: low nibble | (tier - 1) << 4; tier 1 for a base class, highest set bit of the high nibble + 2
        self.assertEqual(self.lib.mu_rp_class_skin(0x01), 0x01)
        self.assertEqual(self.lib.mu_rp_class_skin(0x11), 0x11)   # second tier
        self.assertEqual(self.lib.mu_rp_class_skin(0x31), 0x21)   # bit 1 set: tier 3
        self.assertEqual(self.lib.mu_rp_class_skin(0x71), 0x31)

    def test_equipment_decode(self):
        e = bytearray(18)
        e[0] = 0x0c              # weapon 0: Sword 12 (+0xae6)
        e[1] = 0xff
        e[0xb] = 0x00            # weapon 0 high nibble 0; bit 1 clear
        e[0xc] = 0xf0            # weapon 1: none (0xfff); helm high bits 0
        e[2] = 0xa0 | 0x0a       # helm index 10 (low nibble 0xa), armour low nibble 0xa
        e[3] = 0xa0 | 0x0a       # pants 10, gloves 10
        e[4] = 0xa0 | 0x03       # boots 10; no group-12 pet (3)
        e[5], e[6], e[7] = 0x00, 0x49, 0x04   # levels: codes 4 (+9) for weapon 0 (bits 0-2), helm, armour, pants
        e[9] = 0x80 | 0x04       # helm excellent, weapon 0 excellent
        e[0xa] = 0x40            # armour ancient
        c = self.character(class_byte=0x01)
        env = vp.Env()
        env.scene_state = 6
        calls = vp.Calls()
        self.lib.mu_rp_change_equipment(ctypes.byref(c), bytes(e), 0, ctypes.byref(env), ctypes.byref(calls))
        types = [c.slots[k].type for k in range(9)]
        self.assertEqual(types[6], 0xae6 + 12)
        self.assertEqual(types[7], -1)
        self.assertEqual(types[1:6], [0x18e6 + 10, 0x1ae6 + 10, 0x1ce6 + 10, 0x1ee6 + 10, 0x20e6 + 10])
        self.assertEqual([c.slots[k].level for k in (6, 7, 1, 2, 3, 4, 5)], [9, 0, 9, 9, 9, 0, 0])
        self.assertEqual([c.slots[k].option for k in (1, 2, 6)], [1, 0, 1])
        self.assertEqual([c.slots[k].ext for k in (1, 2)], [0, 1])
        self.assertEqual(c.slots[8].type, -1)              # wing index 0
        self.assertEqual(c.slots[10].type, -1)             # pet code 3: the helper slot is left alone
        kinds = [calls.list[i].kind for i in range(calls.count)]
        self.assertEqual(kinds[:2], [vp.K['C9EA70'], vp.K['HELPER_EFFECT_OFF']])
        self.assertIn(vp.K['X9EBF04'], kinds)

    def test_class_parts_for_code_0x1ff(self):
        e = bytearray(18)
        e[0] = e[1] = 0xff
        e[0xb] = e[0xc] = 0xff   # weapons none; helm high bits 0xf
        e[2] = 0xff
        e[3] = 0xff
        e[4] = 0xf3
        e[8] = 0xf8              # the bit-4s of every part
        e[0xd] = e[0xe] = 0xff
        c = self.character(class_byte=0x02)
        env = vp.Env()
        env.scene_state = 6
        calls = vp.Calls()
        self.lib.mu_rp_change_equipment(ctypes.byref(c), bytes(e), 0, ctypes.byref(env), ctypes.byref(calls))
        self.assertEqual([c.slots[k].type for k in range(1, 6)], [0x3702, 0x3752, 0x37a2, 0x37f2, 0x3842])

    def test_wing_switch(self):
        c = self.character()
        e = bytearray(18)
        # index 1 -> 0x22e6 (bits: e[4] bits 2-3 = idx >> 4, e[8] bits 0-2 = idx >> 3, e[0xf] bits 2-4 = idx & 7)
        e[0xf] = 1 << 2
        self.lib.mu_rp_wing(bytes(e), ctypes.byref(c))
        self.assertEqual(c.slots[8].type, 0x22e6)
        self.assertEqual(c.slots[8].level, 0)
        e = bytearray(18)        # index 0x28: bits 6-7 from e[4] (0), bits 3-5 from e[8] (5), bits 0-2 from e[0xf]
        e[4] = ((0x28 >> 6) & 3) << 2
        e[8] = (0x28 >> 3) & 7
        e[0xf] = (0x28 & 7) << 2
        e[0x11] = 0x0b
        self.lib.mu_rp_wing(bytes(e), ctypes.byref(c))
        self.assertEqual((c.slots[8].type, c.slots[8].level), (0x2484, 11))

    def test_move_packet_walks_to_the_target(self):
        c = self.character(class_byte=1)
        c.tile[0], c.tile[1] = 120, 120
        recorded = []

        def path(_, sx, sy, tx, ty, p, mode):
            recorded.append((sx, sy, tx, ty, mode))
            p.contents.count = 2
            return 1
        env = vp.Env()
        env.world = 0
        env.scene_state = 6
        env.path_finding2 = vp.PATHFN(path)
        calls = vp.Calls()
        packet = bytes([0xc1, 8, 0x3d, 0x02, 0x00, 125, 118, 0x30])
        self.assertEqual(self.lib.mu_rp_move_packet(packet, ctypes.byref(c), ctypes.byref(env), ctypes.byref(calls)), 1)
        self.assertEqual((c.direction, list(c.target), c.movement, c.path.count), (3, [125, 118], 1, 2))
        self.assertEqual(recorded, [(120, 120, 125, 118, 2)])

    def test_move_packet_teleports_without_a_path(self):
        c = self.character(class_byte=1)
        c.tile[0], c.tile[1] = 10, 10
        env = vp.Env()
        env.world = 0x55     # worlds 0x52..0x5a: mode 4 first
        env.scene_state = 6
        env.path_finding2 = vp.PATHFN(lambda *_: 0)
        calls = vp.Calls()
        self.lib.mu_rp_move_packet(bytes([0xc1, 8, 0x3d, 0, 1, 12, 14, 0x10]), ctypes.byref(c), ctypes.byref(env),
                                   ctypes.byref(calls))
        self.assertEqual((list(c.tile), c.movement), ([12, 14], 0))
        self.assertAlmostEqual(c.position[0], 1250.0)
        modes = [calls.list[i].c for i in range(calls.count) if calls.list[i].kind == vp.K['PATH']]
        self.assertEqual(modes, [4, 4])

    def test_remote_step_arrives_and_turns(self):
        c = self.character(class_byte=1)
        c.movement = 1
        c.direction = 5
        events = []
        env = vp.Env()
        env.scene_state = 6
        env.move_path = vp.MOVEFN(lambda *_: 1)
        env.set_player_walk = vp.VOIDFN(lambda *_: events.append('walk'))
        env.set_player_stop = vp.VOIDFN(lambda *_: events.append('stop'))
        env.move_character_position = vp.VOIDFN(lambda *_: events.append('position'))
        calls = vp.Calls()
        self.lib.mu_rp_move_step(ctypes.byref(c), ctypes.byref(env), ctypes.byref(calls))
        self.assertEqual(events, ['walk', 'stop', 'position'])
        self.assertEqual(c.movement, 0)
        self.assertAlmostEqual(c.angle[2], (5 - 1) * 45.0)

    def test_remote_step_ignores_the_hero_and_dead_characters(self):
        c = self.character(class_byte=1, movement=1, dead=3)
        env = vp.Env()
        env.scene_state = 6
        calls = vp.Calls()
        self.lib.mu_rp_move_step(ctypes.byref(c), ctypes.byref(env), ctypes.byref(calls))
        self.assertEqual(calls.count, 0)
        env.is_hero = 1
        c.dead = 0
        self.lib.mu_rp_move_step(ctypes.byref(c), ctypes.byref(env), ctypes.byref(calls))
        self.assertEqual(calls.count, 0)


if __name__ == '__main__':
    unittest.main()
