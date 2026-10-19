"""Portable checks of reconstructed/npc (NATIVE-NPC-001).

The client comparison is scripts/validate_npc.py (Unicorn, private
captures).  These checks build libnpc and test it against independent
statements: the talk result's window table and common tail, the cursor
arithmetic, the unencrypted report, the talk-case rules, the segment/OBB
test against a Python slab test on axis-aligned boxes, the pick's nearest
rule and box adjustments, and the box table's default.
"""
import ctypes
import math
from pathlib import Path
import random
import struct
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
LIB = HERE/('libnpc.dylib' if sys.platform == 'darwin' else 'libnpc.so')


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


class TalkInput(ctypes.Structure):
    _fields_ = [('packet', ctypes.POINTER(ctypes.c_uint8)), ('length', ctypes.c_size_t), ('encrypted', ctypes.c_int),
                ('entrance_visible', ctypes.c_int), ('has_b0', ctypes.c_int), ('has_b4', ctypes.c_int),
                ('has_ac', ctypes.c_int), ('hero_x', ctypes.c_int32), ('hero_y', ctypes.c_int32),
                ('cursor_lock', ctypes.c_int32), ('mouse_x', ctypes.c_int32), ('mouse_y', ctypes.c_int32),
                ('screen_w', ctypes.c_int32), ('screen_h', ctypes.c_int32)]


class TalkEvent(ctypes.Structure):
    _fields_ = [('callee', ctypes.c_uint32), ('self', ctypes.c_uint32), ('n', ctypes.c_int32),
                ('args', ctypes.c_uint32*6)]


class TalkOutput(ctypes.Structure):
    _fields_ = [('events', TalkEvent*24), ('count', ctypes.c_int32), ('returned', ctypes.c_int32)]


class TalkWindow(ctypes.Structure):
    _fields_ = [('kind', ctypes.c_int), ('slot', ctypes.c_uint16), ('movie', ctypes.c_char_p),
                ('method', ctypes.c_uint32), ('arg', ctypes.c_int32), ('dialogue', ctypes.c_int32),
                ('mix_type', ctypes.c_int32), ('shop', ctypes.c_int)]


class TalkGate(ctypes.Structure):
    _fields_ = [('npc_class', ctypes.c_int32), ('hero_level', ctypes.c_int32), ('divide_visible', ctypes.c_int),
                ('mumix_visible', ctypes.c_int)]


class Obb(ctypes.Structure):
    _fields_ = [('v', ctypes.c_float*12)]


class PickCharacter(ctypes.Structure):
    _fields_ = [('live', ctypes.c_uint8), ('visible', ctypes.c_uint8), ('alpha', ctypes.c_float),
                ('kind', ctypes.c_uint8), ('type', ctypes.c_int32), ('highlight', ctypes.c_uint16),
                ('c1f', ctypes.c_uint8), ('dead', ctypes.c_uint8), ('c10', ctypes.c_uint8), ('buff_1b', ctypes.c_uint8),
                ('is_hero', ctypes.c_uint8), ('position', ctypes.c_float*3), ('obb', Obb), ('marked', ctypes.c_uint8),
                ('light', ctypes.c_float*3), ('light_set', ctypes.c_uint8)]


class PickScene(ctypes.Structure):
    _fields_ = [('scene', ctypes.c_int32), ('world', ctypes.c_int32), ('ray_start', ctypes.c_float*3),
                ('ray_end', ctypes.c_float*3), ('camera', ctypes.c_float*3), ('map', ctypes.POINTER(ctypes.c_uint8)),
                ('map_value', ctypes.c_int32)]


KIND = {0: 'none', 1: 'open', 2: 'show', 3: 'method', 4: 'dialogue', 5: 'newui', 6: 'entrance', 7: 'packet', 8: 'other'}


class Npc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        lib = cls.lib = ctypes.CDLL(str(LIB))
        lib.mu_npc_talk_result.argtypes = [ctypes.POINTER(TalkInput), ctypes.POINTER(TalkOutput)]
        lib.mu_npc_talk_window.argtypes = [ctypes.c_uint8, ctypes.POINTER(TalkWindow)]
        lib.mu_npc_repair_shop.argtypes = [ctypes.c_int32]
        lib.mu_npc_talk_refusal.argtypes = [ctypes.POINTER(TalkGate)]
        lib.mu_npc_talk_refusal.restype = ctypes.c_int32
        lib.mu_pick_segment_obb.argtypes = [ctypes.POINTER(ctypes.c_float)]*2 + [ctypes.POINTER(Obb)]
        lib.mu_npc_pick.argtypes = [ctypes.POINTER(PickCharacter), ctypes.c_int32, ctypes.c_uint8,
                                    ctypes.POINTER(PickScene)]
        lib.mu_npc_pick.restype = ctypes.c_int32
        lib.mu_character_box.argtypes = [ctypes.c_int32, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)]

    # ---- talk result -------------------------------------------------------------------
    def talk(self, packet, **kw):
        buf = (ctypes.c_uint8*16)(*packet)
        args = dict(encrypted=1, entrance_visible=0, has_b0=1, has_b4=1, has_ac=1, hero_x=0, hero_y=0, cursor_lock=0,
                    mouse_x=400, mouse_y=300, screen_w=1280, screen_h=800)
        args.update(kw)
        inp = TalkInput(ctypes.cast(buf, ctypes.POINTER(ctypes.c_uint8)), 16, *args.values())
        out = TalkOutput()
        self.lib.mu_npc_talk_result(ctypes.byref(inp), ctypes.byref(out))
        return [(out.events[i].callee, out.events[i].self, tuple(out.events[i].args[:out.events[i].n]))
                for i in range(out.count)], out.returned

    def window(self, r):
        w = TalkWindow()
        self.lib.mu_npc_talk_window(r, ctypes.byref(w))
        return w

    def test_window_table(self):
        expect = {0x00: ('open', 0xf4, b'NpcShop'), 0x01: ('open', 0xf4, b'NpcShop'), 0x02: ('open', 0x100, b'StorageInven'),
                  0x03: ('open', 0xb0, b'MixGoblinSel'), 0x07: ('open', 0x20c, b'GuardianMix'),
                  0x08: ('open', 0xb4, b'MixAttributeScalp'), 0x0c: ('newui', 0, b''), 0x0d: ('packet', 0, b''),
                  0x13: ('open', 0x260, b'HarmonyMix'), 0x15: ('open', 0xa8, b'MixInventoryFrame'),
                  0x17: ('open', 0x208, b'SocketMix'), 0x18: ('method', 0xac, b'MixSel'),
                  0x20: ('open', 0x270, b'ExchangeLuckCoin'), 0x22: ('open', 0xf4, b'NpcShop'),
                  0x28: ('dialogue', 0xf0, b'npcdialogue'), 0x29: ('open', 0x204, b'ElementalMix'),
                  0x30: ('show', 0x164, b'PersonalShop'), 0x35: ('open', 0x1fc, b'RuudShopFrame'),
                  0x40: ('dialogue', 0xf0, b'npcdialogue'), 0xff: ('none', 0, b''), 0x41: ('open', 0xf4, b'NpcShop')}
        for r, (kind, slot, movie) in expect.items():
            w = self.window(r)
            self.assertEqual((KIND[w.kind], w.slot, w.movie), (kind, slot, movie), hex(r))
        self.assertEqual([self.window(r).mix_type for r in (0x15, 0x16, 0x31, 0x02)], [8, 9, 13, -1])
        self.assertEqual([self.window(r).dialogue for r in (0x28, 0x36, 0x37, 0x39, 0x40)],
                         [0x248, 0x2fc, 0x2fd, 0x3ab, 0x3ac])
        # 39 results are named by the dispatch; the other 217 and 0x22 open NpcShop
        self.assertEqual(sum(self.window(r).shop for r in range(256)), 256 - 39 + 1)

    def test_common_tail_and_cursor(self):
        events, ret = self.talk([0xc1, 16, 0xdf, 2] + [0]*12, mouse_x=400, mouse_y=300)
        self.assertEqual(ret, 1)
        self.assertEqual(events[0], (0x00aae6f9, 0x2ac, ()))                      # EventMapEntranceUI visible?
        self.assertEqual(events[1:3], [(0x00ac9c74, 0xffff, ()), (0x00f2b53d, 0xfffe, ())])   # close all
        self.assertEqual(events[3], (0x80000040, 0x100, ()))                      # StorageInven Open
        self.assertEqual(events[4:6], [(0x00a6ac96, 0, (0x19, 0, 0)), (0x00a6ac96, 0, (0x1c, 0, 0))])
        # SetCursorPos((x*260/640)*W/640, y*H/480)
        self.assertEqual(events[6], (0x01a7c870, 0, (400*260//640*1280//640, 300*800//480)))
        events, _ = self.talk([0xc1, 16, 0xdf, 2] + [0]*12, entrance_visible=1, cursor_lock=1)
        self.assertEqual([e[0] for e in events], [0x00aae6f9, 0x80000040, 0x00a6ac96, 0x00a6ac96])

    def test_unencrypted_answer_is_reported(self):
        events, ret = self.talk([0xc1, 16, 0xdf, 2] + [0]*12, encrypted=0)
        self.assertEqual(ret, 0)
        self.assertEqual(events, [(0x00d51baf, 0xfff9, (0xc1, 0x4d)), (0x00d51c9b, 0xfff9, (2, 1, 1)),
                                  (0x00d51c9b, 0xfff9, (0, 1, 1)), (0x00d51c9b, 0xfff9, (0xb2, 1, 1)),
                                  (0x00d51d4f, 0xfff9, (1, 0))])

    def test_shop_tabs_and_entrance(self):
        events, _ = self.talk([0xc1, 16, 0xdf, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0])
        self.assertIn((0x00bf17c2, 0xf4, (3,)), events)
        events, _ = self.talk([0xc1, 16, 0xdf, 0x23, 2, 5, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0], hero_x=10, hero_y=10)
        self.assertIn((0x00b04ded, 0x2ac, (3, 125, 1, 0, 1)), events)
        events, _ = self.talk([0xc1, 16, 0xdf, 0x23, 2, 5] + [0]*10, hero_x=0x40, hero_y=0xf0)
        self.assertIn((0x00f2abcd, 0xfffe, (0x3f,)), events)
        self.assertIn((0x00ef00b4, 0xfffa, (125,)), events)

    def test_talk_case_rules(self):
        self.assertEqual([c for c in range(1000) if self.lib.mu_npc_repair_shop(c)], [243, 246, 251, 416, 578, 686, 687])

        def refusal(**kw):
            g = TalkGate(**{'npc_class': 251, 'hero_level': 50, 'divide_visible': 0, 'mumix_visible': 0, **kw})
            return self.lib.mu_npc_talk_refusal(ctypes.byref(g))
        self.assertEqual(refusal(), -1)
        self.assertEqual(refusal(divide_visible=1), 0x148c)
        self.assertEqual(refusal(npc_class=238, hero_level=9), 0x297)
        self.assertEqual(refusal(npc_class=238, hero_level=10), -1)
        self.assertEqual(refusal(mumix_visible=1), 0xfd8)
        self.assertEqual(refusal(npc_class=0, mumix_visible=1), -1)

    # ---- picking ---------------------------------------------------------------------------
    @staticmethod
    def slab(p1, p2, lo, hi):
        """Independent statement for an axis-aligned box: does the closed segment meet it?"""
        t0, t1 = 0.0, 1.0
        for k in range(3):
            d = p2[k] - p1[k]
            if abs(d) < 1e-9:
                if p1[k] < lo[k] or p1[k] > hi[k]:
                    return False
                continue
            a, b = (lo[k] - p1[k]) / d, (hi[k] - p1[k]) / d
            a, b = min(a, b), max(a, b)
            t0, t1 = max(t0, a), min(t1, b)
            if t0 > t1:
                return False
        return True

    def test_segment_obb_matches_slab_test(self):
        rng = random.Random(7)
        agree = 0
        for _ in range(3000):
            lo = [rng.uniform(-200, 200) for _ in range(3)]
            ext = [rng.uniform(10, 300) for _ in range(3)]
            hi = [lo[k] + ext[k] for k in range(3)]
            p1 = [rng.uniform(-800, 800) for _ in range(3)]
            p2 = [rng.uniform(-800, 800) for _ in range(3)]
            want = self.slab(p1, p2, lo, hi)
            obb = Obb((ctypes.c_float*12)(*lo, ext[0], 0, 0, 0, ext[1], 0, 0, 0, ext[2]))
            got = self.lib.mu_pick_segment_obb((ctypes.c_float*3)(*p1), (ctypes.c_float*3)(*p2), ctypes.byref(obb))
            # the separating-axis test on 6 axes is exact for segment/box up to binary32 rounding at grazing contact
            margin = min(abs(p[k] - b[k]) for p in (p1, p2) for b in (lo, hi) for k in range(3))
            if bool(got) == want or margin < 1e-2:
                agree += 1
        self.assertGreaterEqual(agree, 2995)

    def scene(self, start, end, camera, world=1):
        return PickScene(6, world, (ctypes.c_float*3)(*start), (ctypes.c_float*3)(*end), (ctypes.c_float*3)(*camera),
                         None, 0)

    def character(self, arr, i, pos, kind=4, typ=0x9fe, **kw):
        c = arr[i]
        c.live = c.visible = c.c10 = 1
        c.alpha = 1.0
        c.kind = kind
        c.type = typ
        c.position = (ctypes.c_float*3)(*pos)
        mn, mx = (ctypes.c_float*3)(), (ctypes.c_float*3)()
        self.lib.mu_character_box(typ, mn, mx)
        c.obb.v = (ctypes.c_float*12)(*(pos[k] + mn[k] for k in range(3)), mx[0]-mn[0], 0, 0, 0, mx[1]-mn[1], 0, 0, 0,
                                      mx[2]-mn[2])
        for k, v in kw.items():
            setattr(c, k, v)
        return c

    def test_pick_nearest_kind_and_flags(self):
        arr = (PickCharacter*400)()
        for i in range(400):
            arr[i].kind = 0xff                                            # never matches the masks
        self.character(arr, 10, (1000.0, 1000.0, 0.0), highlight=2)
        self.character(arr, 20, (1000.0, 1000.0, 40.0), highlight=3)
        self.character(arr, 30, (1000.0, 1000.0, 0.0), kind=2)          # monster kind: not in mask 4
        sc = self.scene((1000.0, 1300.0, 900.0), (1000.0, 700.0, -900.0), (1000.0, 1300.0, 900.0))
        self.assertEqual(self.lib.mu_npc_pick(arr, 400, 4, ctypes.byref(sc)), 20)   # higher one is nearer the camera
        self.assertEqual((arr[10].marked, arr[20].marked, arr[30].marked), (1, 1, 0))
        self.assertEqual([f32(v) for v in arr[10].light], [f32(0.2), f32(-0.6), f32(-0.6)])
        self.assertEqual([f32(v) for v in arr[20].light], [1.5, 1.5, 1.5])
        arr[20].dead = 1
        self.assertEqual(self.lib.mu_npc_pick(arr, 400, 4, ctypes.byref(sc)), 10)
        arr[10].buff_1b = 1
        self.assertEqual(self.lib.mu_npc_pick(arr, 400, 4, ctypes.byref(sc)), -1)
        self.assertEqual(self.lib.mu_npc_pick(arr, 400, 0x22, ctypes.byref(sc)), 30)

    def test_pick_box_adjustment_is_in_place(self):
        arr = (PickCharacter*400)()
        for i in range(400):
            arr[i].kind = 0xff
        c = self.character(arr, 0, (0.0, 0.0, 0.0), typ=0xa40)
        z0 = c.obb.v[2]
        sc = self.scene((0.0, 0.0, 2000.0), (0.0, 0.0, 1000.0), (0.0, 0.0, 2000.0))
        for n in (1, 2, 3):
            self.lib.mu_npc_pick(arr, 400, 4, ctypes.byref(sc))
            self.assertEqual(arr[0].obb.v[2], z0 + 300*n)                # every call raises it again

    def test_box_default_and_table(self):
        mn, mx = (ctypes.c_float*3)(), (ctypes.c_float*3)()
        self.lib.mu_character_box(0x9fe, mn, mx)
        self.assertEqual((list(mn), list(mx)), ([-60, -60, 0], [50, 50, 150]))
        self.lib.mu_character_box(0xa91, mn, mx)                         # the Player model
        self.assertEqual((list(mn), list(mx)), ([-60, -60, 0], [40, 40, 120]))


if __name__ == '__main__':
    unittest.main()
