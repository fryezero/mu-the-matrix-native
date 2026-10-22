"""Portable checks of reconstructed/map (NATIVE-MAP-001).

The client comparison is scripts/validate_map.py (Unicorn, private captures and
a langread snapshot).  These checks build libmap and test it against
independent statements of the same rules: the map pixel transform, the world
image name, the per-frame cache, the 0xE7 record layout, the blocked areas and
the show request, the move manager's build and sorts (ordering and
permutation; the MSVC algorithm itself is compared with the client in
Unicorn), the availability and row rules, the click and request bytes, the
gate test and the teleport fields.
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
LIB = HERE/('libmap.dylib' if sys.platform == 'darwin' else 'libmap.so')
sys.path.insert(0, str(HERE.parents[1]/'scripts'))
import validate_map as vm  # noqa: E402  (ctypes declarations only; no Unicorn needed)


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


def snapshot_with_move_default():
    """An authored sparse table with a nonzero default and one ordinary row."""
    def record(name, rid, zen, level, x44, x48):
        raw = bytearray(0x50)
        for off, value in ((4, name), (0x1c, b'Default')):
            raw[off:off + len(value)] = value
            struct.pack_into('<II', raw, off + 0x10, len(value), 15)
        for off, value in ((0, rid), (0x34, zen), (0x38, level), (0x3c, 99), (0x40, 8),
                           (0x44, x44), (0x48, x48), (0x4c, 19)):
            struct.pack_into('<i', raw, off, value)
        return raw

    move = bytearray(0xa0)
    struct.pack_into('<II', move, 0x38, 0x1000, 1)
    move[0x4c:0x9c] = record(b'Fallback', 23, 123, 77, -7, 4)
    head, node, gate_head = bytearray(0x20), bytearray(0x64), bytearray(0x20)
    struct.pack_into('<III', head, 0, 0x1100, 0x1100, 0x1100)
    head[0xd] = 1
    struct.pack_into('<III', node, 0, 0x1000, 0x1000, 0x1000)
    struct.pack_into('<i', node, 0x10, 5)
    node[0x14:] = record(b'Regular', 5, 0, 0, 2, -2)
    struct.pack_into('<III', gate_head, 0, 0x1200, 0x1200, 0x1200)
    gate_head[0xd] = 1
    blocks = [(vm.MOVEREQ, move), (0x1000, head), (0x1100, node), (0x1200, gate_head),
              (vm.GATE + 0x38, struct.pack('<II', 0x1200, 0))]
    data = b'MULANGV1' + struct.pack('<I', len(blocks))
    data += b''.join(struct.pack('<II', address, len(raw)) + raw for address, raw in blocks)
    return vm.plain.Snapshot(data)


class Lib:
    def __init__(self):
        subprocess.run(['make', '-s', '-C', str(HERE)], check=True)
        self.n = vm.Native()
        self.L = self.n.L
        L = self.L
        L.mu_map_blocked.argtypes = [ctypes.c_int32] * 3 + [ctypes.POINTER(ctypes.c_int)]
        L.mu_move_required_zen.argtypes = [ctypes.POINTER(vm.MoveRecord), ctypes.POINTER(vm.MoveHero)]
        L.mu_move_special.argtypes = [ctypes.c_int32, ctypes.c_int32]
        L.mu_move_request_packet.argtypes = [ctypes.c_uint32, ctypes.c_uint16, ctypes.c_uint8,
                                             ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
        L.mu_teleport_parse.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(Teleport)]
        L.mu_teleport_angle.argtypes = [ctypes.POINTER(Teleport)]
        L.mu_teleport_angle.restype = ctypes.c_float
        L.mu_teleport_changes_world.argtypes = [ctypes.POINTER(Teleport), ctypes.c_int32]


class Teleport(ctypes.Structure):
    _fields_ = [('number', ctypes.c_uint16), ('world', ctypes.c_uint16), ('x', ctypes.c_uint8), ('y', ctypes.c_uint8),
                ('dir', ctypes.c_uint8)]


class Records:
    def __init__(self, rows):
        self.keep, self.recs = [], {}
        for key, rid, name, zen, level, gate, x44, x48 in rows:
            b = ctypes.create_string_buffer(name.encode())
            self.keep.append(b)
            self.recs[key] = vm.MoveRecord(key, rid, ctypes.addressof(b), ctypes.addressof(b), zen, level, -1, gate,
                                           x44, x48, 0)
        self.lookup = vm.LOOKUP_FN(lambda u, k: ctypes.addressof(self.recs[k]) if k in self.recs else None)
        self.texts = {}

        def text(u, i):
            s = TEXTS.get(i, f'[Text] error index : {i}')
            if i not in self.texts:
                self.texts[i] = ctypes.create_string_buffer(s.encode())
            return ctypes.addressof(self.texts[i])
        self.text = vm.TEXT_FN(text)


TEXTS = {0x37: 'Icarus', 0x25: 'Atlans', 0x29d: 'Kalima', 0xa7e: 'Vulcanus', 0x3a: 'Event', 0xbab: '(Battle)'}


class MapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = Lib()
        cls.L = cls.lib.L

    def test_pixels(self):
        rng = random.Random(1)
        for _ in range(500):
            v = f32(rng.uniform(-300, 300))
            self.assertEqual(self.L.mu_map_px_x(v), f32(v * 2.0))
            self.assertEqual(self.L.mu_map_px_y(v), f32(f32(256.0 - v) * 2.0))

    def test_navimap_name(self):
        buf = ctypes.create_string_buffer(32)
        for world, name in ((0, b'navimap01.ozp'), (3, b'navimap04.ozp'), (145, b'navimap146.ozp')):
            self.L.mu_map_navimap_name(world, buf, 32)
            self.assertEqual(buf.value, name)

    def test_hud_cache(self):
        h, out = vm.Hud(shown=1), vm.HudFrame()
        pos = (ctypes.c_float * 2)(12350.0, 6050.0)
        self.L.mu_map_hud_update(ctypes.byref(h), 1, 1, ctypes.byref(pos), 45.0, ctypes.byref(out))
        self.assertTrue(out.set_rotation and out.set_position)
        self.assertEqual(out.rotation, 180.0)
        self.assertEqual(out.map_x, -247.0)                  # -(123.5 * 2)
        self.assertEqual(out.map_y, -f32((256.0 - 60.5) * 2.0))
        self.L.mu_map_hud_update(ctypes.byref(h), 1, 1, ctypes.byref(pos), 45.0, ctypes.byref(out))
        self.assertFalse(out.set_rotation or out.set_position)   # unchanged values are not sent again
        h.shown = 0
        pos[0] = 1.0
        self.L.mu_map_hud_update(ctypes.byref(h), 1, 1, ctypes.byref(pos), 0.0, ctypes.byref(out))
        self.assertFalse(out.set_rotation or out.set_position)

    def test_unit_records(self):
        u = vm.Unit()
        p = bytes([0xc1, 16, 0xe7, 3, 7, 1, 2, 0, 100, 50]) + b'Guard\0'
        self.assertEqual(self.L.mu_map_unit_packet(p, len(p), 1, ctypes.byref(u)), 1)
        self.assertEqual((u.type, u.key, u.state, u.text, u.x, u.y), (1, 7, 2, b'Guard', 200.0, 412.0))
        self.assertEqual(self.L.mu_map_unit_packet(p, len(p), 0, ctypes.byref(u)), 1)
        self.assertEqual(u.text, b'')
        q = bytearray(p)
        q[7] = 1
        self.assertEqual(self.L.mu_map_unit_packet(bytes(q), len(q), 1, ctypes.byref(u)), 2)
        self.assertEqual((u.type, u.key), (1, 7))
        q[7] = 2
        self.assertEqual(self.L.mu_map_unit_packet(bytes(q), len(q), 1, ctypes.byref(u)), 0)
        self.L.mu_map_detected_unit(4, 2, 10, 20, ctypes.byref(u))
        self.assertEqual((u.type, u.key, u.state, u.x, u.y), (3, 4, 0, 20.0, 472.0))

    def test_blocked_and_show(self):
        n = ctypes.c_int()
        self.assertEqual(self.L.mu_map_blocked(0x72, 0xf0, 0xf0, ctypes.byref(n)), 1)
        self.assertEqual(n.value, 1)
        self.assertEqual(self.L.mu_map_blocked(0x73, 1, 1, ctypes.byref(n)), 1)
        self.assertEqual(n.value, 0)
        self.assertEqual(self.L.mu_map_blocked(0, 0xf0, 0xf0, ctypes.byref(n)), 0)
        h, r = vm.Hud(available=1), vm.ShowResult()
        self.L.mu_map_show(ctypes.byref(h), 1, 0, 10, 10, ctypes.byref(r))
        self.assertEqual((r.set_show, r.shown, bytes(r.packet)), (1, 1, b'\xc1\x04\xe7\x01'))
        self.L.mu_map_show(ctypes.byref(h), 0, 0, 10, 10, ctypes.byref(r))
        self.assertEqual(bytes(r.packet), b'\xc1\x04\xe7\x02')
        h.available = 0
        self.L.mu_map_show(ctypes.byref(h), 1, 0, 10, 10, ctypes.byref(r))
        self.assertEqual((r.notice, r.set_show, h.shown), (1, 0, 0))

    def build(self, recs, keys):
        arr = (vm.MoveEntry * (len(keys) + 1))()
        n = self.L.mu_move_build((ctypes.c_int32 * len(keys))(*keys), len(keys), recs.lookup, None, arr, len(keys))
        return arr, n

    def test_build_and_sort(self):
        rng = random.Random(2)
        rows = [(k, k * 3 % 17, f'Map {k}', 1000 * k, k, k, rng.randint(0, 5), rng.randint(0, 5)) for k in range(1, 80)]
        recs = Records(rows)
        keys = [r[0] for r in rows]
        rng.shuffle(keys)
        arr, n = self.build(recs, keys + [999])
        self.assertEqual(n, 80)
        self.assertEqual([(arr[i].key, arr[i].order, arr[i].key2) for i in range(n)],
                         [(k, i, k) for i, k in enumerate(keys + [999])])
        self.assertEqual((arr[79].x44, arr[79].x48), (0, 0))    # NULL callback result selects the empty fallback
        for order, field in ((0, 'order'), (1, 'x44'), (2, 'x48')):
            before = sorted((arr[i].key, arr[i].order) for i in range(n))
            self.L.mu_move_sort(arr, n, order)
            vals = [getattr(arr[i], field) for i in range(n)]
            self.assertEqual(vals, sorted(vals))
            self.assertEqual(sorted((arr[i].key, arr[i].order) for i in range(n)), before)

    def test_snapshot_default_for_missing_moves(self):
        t = vm.Tables(snapshot_with_move_default())
        self.assertEqual(t.keys, [5])  # the default is not a selectable table row
        for key in (0, 35, 36, 999, -1):
            address = t.lookup(None, key)
            self.assertIsNotNone(address)
            r = vm.MoveRecord.from_address(address)
            self.assertEqual((r.id, r.name, r.server_name, r.zen, r.min_level, r.max_level, r.gate,
                              r.x44, r.x48, r.x4c), (23, b'Fallback', b'Default', 123, 77, 99, 8, -7, 4, 19))
        arr, n = vm.native_build(self.lib.n, t, [5, 999])
        self.assertEqual(vm.native_entries(arr, n), [(5, 2, 0, -2, 5, 0, 0, 0),
                                                     (999, -7, 1, 4, 999, 0, 0, 0)])
        self.L.mu_move_sort(arr, n, 1)
        self.assertEqual([e.key for e in arr[:n]], [999, 5])
        # Use the authored text callback, so no GlobalText snapshot is needed.
        text = Records([]).text
        h = self.hero(level=76, zen=123)
        self.L.mu_move_availability(arr, n, ctypes.byref(h), t.lookup, text, None)
        self.assertEqual([e.enabled for e in arr[:n]], [0, 1])
        h.level, h.pk_level, h.zen = 77, 5, 6150
        self.L.mu_move_availability(arr, n, ctypes.byref(h), t.lookup, text, None)
        self.assertEqual([e.enabled for e in arr[:n]], [1, 1])
        row = vm.MoveRow()
        self.L.mu_move_row_make(ctypes.byref(arr[0]), 0, ctypes.byref(h), 0, t.lookup, text, None, ctypes.byref(row))
        self.assertEqual((row.map, row.level, row.zen, row.map_idx), (b'Fallback', b'77', b'6150', 999))
        result = vm.ClickResult()
        self.L.mu_move_click(arr, n, 0, 0, 0, 0x11223344, ctypes.byref(result))
        self.assertEqual(result.accepted, 1)
        self.assertEqual(bytes(result.packet[:result.packet_length]), bytes.fromhex('c10b8e0244332211e703ff'))

    def hero(self, **kw):
        h = vm.MoveHero(level=400, zen=100000, strife_ok=1)
        for k, v in kw.items():
            setattr(h, k, v)
        return h

    def avail(self, recs, keys, h, strife=()):
        arr, n = self.build(recs, keys)
        for i in strife:
            arr[i].strife = 1
        self.L.mu_move_availability(arr, n, ctypes.byref(h), recs.lookup, recs.text, None)
        return [arr[i].enabled for i in range(n)]

    def test_availability(self):
        recs = Records([(1, 0, 'Lorencia', 2000, 10, 1, 0, 0), (2, 1, 'Icarus', 10000, 160, 1, 0, 0),
                        (3, 2, 'Atlans 2', 4500, 80, 1, 0, 0), (4, 3, 'Kalima 1', 0, 1, 1, 0, 0),
                        (5, 4, 'Vulcanus', 15000, 300, 1, 0, 0), (6, 5, 'Event3', 0, 1, 1, 0, 0),
                        (7, 6, 'Deep', 50000, 500, 1, 0, 0)])
        keys = [1, 2, 3, 4, 5, 6, 7]
        self.assertEqual(self.avail(recs, keys, self.hero()), [1, 0, 1, 0, 1, 0, 0])
        self.assertEqual(self.avail(recs, keys, self.hero(wings_slot=1, kalima=1, server_flag=1, event_b=1)),
                         [1, 1, 1, 1, 0, 1, 0])
        self.assertEqual(self.avail(recs, keys, self.hero(helper_type=0x1a25))[1], 1)
        self.assertEqual(self.avail(recs, keys, self.hero(flying=1))[1], 1)
        self.assertEqual(self.avail(recs, keys, self.hero(pk_level=5, zen=99999))[0], 0)    # 2000 x 50 > 99999
        self.assertEqual(self.avail(recs, keys, self.hero(pk_level=4, zen=99999))[0], 1)
        self.assertEqual(self.avail(recs, keys, self.hero(pk_level=5, zen=99999))[2], 0)    # 4500 x 50
        self.assertEqual(self.avail(recs, keys, self.hero(strife_ok=0), strife=(0,))[0], 0)
        self.assertEqual(self.avail(recs, keys, self.hero(strife_ok=1), strife=(0,))[0], 1)

    def test_rows_and_click(self):
        recs = Records([(1, 0, 'Lorencia', 2000, 10, 17, 0, 0), (48, 1, 'Event Square', 20000, 1, 503, 0, 0)])
        arr, n = self.build(recs, [1, 48])
        arr[0].enabled, arr[1].strife = 1, 1
        row, h = vm.MoveRow(), self.hero(pk_level=6)
        self.L.mu_move_row_make(ctypes.byref(arr[1]), 1, ctypes.byref(h), 1, recs.lookup, recs.text, None,
                                ctypes.byref(row))
        self.assertEqual((row.order_idx, row.strife, row.map, row.level, row.zen, row.checked, row.disabled, row.map_idx),
                         (1, b'(Battle)', b'Event Square', b'1', b'1000000', 1, 1, 48))
        r = vm.ClickResult()
        self.L.mu_move_click(arr, n, 1, 0, 1, 0x11223344, ctypes.byref(r))
        self.assertEqual(r.accepted, 0)                       # not enabled
        self.L.mu_move_click(arr, n, 0, 0x22, 1, 0x11223344, ctypes.byref(r))
        self.assertEqual((r.accepted, r.helper_stop, r.helper_packet, arr[0].clicked), (1, 1, 1, 1))
        self.assertEqual(bytes(r.packet[:r.packet_length]), bytes.fromhex('c10b8e02443322110100ff'))
        self.assertTrue(self.L.mu_move_special(0, 0x30) and not self.L.mu_move_special(0, 0x31))

    def test_gates(self):
        gates = [vm.Gate(1, 1, 0, 120, 230, 122, 233, 2, 0, 20, -1), vm.Gate(2, 2, 1, 100, 240, 102, 242, 0, 1, 0, -1),
                 vm.Gate(3, 1, 0, 10, 10, 11, 11, 4, 0, 0, -1), vm.Gate(4, 2, 10, 5, 5, 5, 5, 0, 0, 0, -1)]
        by = {g.index: g for g in gates}
        fn = vm.GATE_FN(lambda u, i: ctypes.addressof(by[i]) if i in by else None)
        arr = (vm.Gate * len(gates))(*gates)

        def run(**kw):
            h = vm.GateHero(world=0, level=400)
            for k, v in kw.items():
                setattr(h, k, v)
            r = vm.GateResult()
            self.L.mu_gate_check(arr, len(gates), fn, None, ctypes.byref(h), ctypes.byref(r))
            return r
        r = run(tile_x=121, tile_y=233)
        self.assertEqual((r.gate, r.target, r.refused, r.loading_world), (1, 2, 0, 9999999))
        self.assertEqual(bytes(r.packet), bytes.fromhex('c1001c0001000000'))
        self.assertEqual(run(tile_x=123, tile_y=233).gate, -1)
        self.assertEqual((run(tile_x=121, tile_y=233, level=19).refused, run(tile_x=121, tile_y=233, level=19).loading_world), (1, 50))
        self.assertEqual(run(tile_x=10, tile_y=10).refused, 2)              # Icarus (world 10) without wings
        self.assertEqual(run(tile_x=10, tile_y=10, wings_kind6=1).refused, 0)
        self.assertEqual(run(tile_x=121, tile_y=233, throttle=1).packet_length, 0)
        self.assertEqual(run(tile_x=121, tile_y=233, loading_world=30).gate, -1)

    def test_teleport(self):
        t = Teleport()
        p = bytes.fromhex('c30b1c001b0003008c720300')
        self.assertEqual(self.L.mu_teleport_parse(p, len(p), ctypes.byref(t)), 1)
        self.assertEqual((t.number, t.world, t.x, t.y, t.dir), (27, 3, 140, 114, 3))
        self.assertEqual(self.L.mu_teleport_angle(ctypes.byref(t)), 90.0)
        self.assertTrue(self.L.mu_teleport_changes_world(ctypes.byref(t), 0))
        self.assertFalse(self.L.mu_teleport_changes_world(ctypes.byref(t), 3))


if __name__ == '__main__':
    unittest.main()
