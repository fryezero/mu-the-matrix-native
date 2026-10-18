#!/usr/bin/env python3
"""Compare the reconstructed in-game interface routines with the client (NATIVE-HUD-001).

Every case runs actual client code in Unicorn over the pinned restored text
and second image section (scripts/client_ui_machine.py) and the
reconstruction in reconstructed/hud through ctypes, then compares results
word for word.

Sections:

* grid: the item grid of the GFx item windows (constructor 0x00ad322b,
  Init 0x00ad341d, fit tests, free-slot searches, counting, pixel mapping,
  place/remove).  Compared after every step: return values, the grid's
  scalar fields at the client offsets, the cell array, the item vector (as
  item indices) and every item's cell, plus the event stream (status
  refresh 0x00c94193 and the GFx page refresh 0x00ad86dc, recorded as
  markers).
* slots: the item-slot pass of the GFx item windows 0x00ab6130 and the
  slot wrapper 0x016c23d5, up to the RenderItem3D call 0x016c154e (whose
  argument words are recorded).
* item3d: RenderItem3D 0x016c154e's projection and model-transform set-up
  with the model render recorded as a marker.
* tooltip: the tooltip-text formatter 0x00f1098a for the reconstructed
  types, the line appender 0x011ffb3a and the HTML line builder 0x00ab4dc0.

Modelled explicitly (not client code): operator new/new[]/delete, memset,
memmove and memcpy, the GFx manager and frame accessors the slot pass reads, and
the calls named per section (markers).  Any other call outside the
allowlisted closure stops the case.
"""
import argparse
import ctypes
from ctypes import (CFUNCTYPE, POINTER, Structure, c_int, c_int16, c_int32, c_uint8, c_uint32, c_void_p)
import json
import os
from pathlib import Path
import random
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import client_ui_machine as cm  # noqa: E402

DEFAULT_TEXT = ROOT/'evidence/x86-text-capture-09/client-text.bin'
DEFAULT_DATA = ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'
TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_SHA256 = 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'

OP_NEW, OP_NEW_ARRAY, OP_DELETE, OP_DELETE_ARRAY = 0x0191ba7b, 0x0191bab9, 0x0191baab, 0x0191bac2
MEMSET, MEMMOVE, MEMCPY = 0x0194cd00, 0x0194c200, 0x0194c780
STRLEN, STRCMP, FREE = 0x0195a4b0, 0x0195a3d0, 0x0191c490
SECURITY_COOKIE = 0x01cf65c0


# functions whose linear extent scan is defeated by a runtime-patched jump
EXTENTS = {0x016c154e: 0x016c23d5, 0x00b8d94b: 0x00b8dd11, 0x00f1098a: 0x00f134a8}


def closure(text, roots, stops):
    """Static direct-call closure of `roots`, minus `stops`.  Functions without a
    reachable return (the C++ library's throw helpers) are returned separately."""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    engine = Cs(CS_ARCH_X86, CS_MODE_32)
    seen, noreturn, todo = {}, set(), list(roots)
    while todo:
        start = todo.pop()
        if start in seen or start in stops or start in noreturn:
            continue
        try:
            end = EXTENTS.get(start) or cm.function_extent(text, start)
        except ValueError:
            noreturn.add(start)
            continue
        seen[start] = end
        offset = start - cm.TEXT_BASE
        for _, _, mnemonic, operands in engine.disasm_lite(text[offset:end - cm.TEXT_BASE], start):
            if mnemonic == 'call' and operands.startswith('0x'):
                todo.append(int(operands, 16))
    return seen, noreturn


class Client:
    """A client machine with the common C runtime models installed."""

    def __init__(self, text, data):
        self.text, self.data = text, data
        self.machine = cm.Machine(text, data)
        self.events = []

    def prepare(self, roots, stops):
        m = self.machine
        functions, noreturn = closure(self.text, roots, set(stops))
        for start, end in functions.items():
            m.allow((start, end))
        for start in noreturn:
            m.stub(start, lambda mm, s=start: mm.fail(f'client throw helper {s:#x} reached'))
        m.allow((0x0191d71e, 0x0191d721))     # guard-check-icall no-op
        self.functions = functions

    def common_stubs(self):
        m = self.machine

        def new(mm):
            size = mm.args(1)[0]
            return mm.alloc(size)

        def memset(mm):
            target, value, size = mm.args(3)
            mm.write(target, bytes([value & 0xff])*size)
            return target

        def memmove(mm):
            target, source, size = mm.args(3)
            mm.write(target, mm.read(source, size))
            return target
        m.stub(OP_NEW, new)
        m.stub(OP_NEW_ARRAY, new)
        m.stub(OP_DELETE, lambda mm: 0)
        m.stub(OP_DELETE_ARRAY, lambda mm: 0)
        m.stub(FREE, lambda mm: 0)
        m.stub(MEMSET, memset)
        m.stub(MEMMOVE, memmove)
        m.stub(MEMCPY, memmove)

        def strlen(mm):
            return len(read_cstr(mm, mm.args(1)[0]))

        def strcmp(mm):
            a, b = (read_cstr(mm, x) for x in mm.args(2))
            return 0 if a == b else (1 if a > b else 0xffffffff)
        m.stub(STRLEN, strlen)
        m.stub(STRCMP, strcmp)

    def reset(self):
        self.machine.reset()
        self.machine.put32(SECURITY_COOKIE, 0xbb40e64e)
        self.events = []


def library(path=None):
    path = path or (ROOT/'reconstructed/hud'/('libmu_hud.dylib' if sys.platform == 'darwin' else 'libmu_hud.so'))
    return ctypes.CDLL(str(path))


def sha256_file(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ==========================================================================
# grid

GRID_ROOTS = (0xad322b, 0xad32d7, 0xad341d, 0xad4e69, 0xad4ee4, 0xad4ff4, 0xad49fb, 0xad4994, 0xad4a6d,
              0xad4ad9, 0xad4cb1, 0xad4f11, 0xad4f51, 0xad4d43, 0xad4da5, 0xad5037, 0xad4c51, 0xad4cf6,
              0xad37c9, 0xad3775, 0xad3a4e, 0xad403c, 0xad3fd9, 0xad3c57, 0xad47f1)
GRID_STOPS = {OP_NEW, OP_NEW_ARRAY, OP_DELETE, OP_DELETE_ARRAY, MEMSET, MEMMOVE, MEMCPY,
              0xc94193, 0xad86dc, 0xadaccf, 0xc06911, 0xccc51e}
GRID_CELLS = 1024
GRID_ITEMS = 256
EVENTFN = CFUNCTYPE(None, c_void_p, c_int, c_void_p)


class GridItem(Structure):
    _fields_ = [('id', c_uint32), ('code', c_int32), ('col', c_uint8), ('row', c_uint8), ('width', c_uint8),
                ('height', c_uint8)]


class Grid(Structure):
    _fields_ = [('field_00', c_uint32), ('owner', c_uint32), ('x', c_int32), ('y', c_int32), ('pixel_w', c_int32),
                ('pixel_h', c_int32), ('cols', c_int32), ('rows', c_int32), ('page', c_int32),
                ('has_cells', c_int32), ('field_3c', c_int32), ('flag_40', c_uint8), ('type', c_int32),
                ('flag_48', c_uint8), ('flag_49', c_uint8), ('cells', c_uint32*GRID_CELLS),
                ('items', POINTER(GridItem)*GRID_ITEMS), ('item_count', c_int32), ('owner_pages', c_int32),
                ('overflow', c_int), ('event', EVENTFN), ('user', c_void_p)]


def grid_lib(lib):
    i32, u32, p = c_int32, c_uint32, c_void_p
    sig = {
        'mu_grid_construct': (None, [p]), 'mu_grid_reset': (None, [p]),
        'mu_grid_init': (c_int, [p, i32, u32, i32, i32, i32, i32, i32]),
        'mu_grid_fits_index': (c_int, [p, i32, i32, i32]), 'mu_grid_fits': (c_int, [p, i32, i32, i32, i32]),
        'mu_grid_item_fits': (c_int, [p, i32, i32, p]),
        'mu_grid_find_free': (c_int, [p, i32, i32, POINTER(i32), POINTER(i32)]),
        'mu_grid_find_free_index': (i32, [p, i32, i32]), 'mu_grid_count_empty': (i32, [p]),
        'mu_grid_count_fits': (i32, [p, i32, i32, i32, POINTER(c_int)]),
        'mu_grid_rect': (None, [p, POINTER(i32)]), 'mu_grid_pt_in': (c_int, [p, i32, i32]),
        'mu_grid_rect_in': (c_int, [p, POINTER(i32)]),
        'mu_grid_pixel_cell': (c_int, [p, i32, i32, POINTER(i32), POINTER(i32)]),
        'mu_grid_pixel_index': (i32, [p, i32, i32]), 'mu_grid_item_fits_pixel': (c_int, [p, i32, i32, p]),
        'mu_grid_set_position': (None, [p, i32, i32]), 'mu_grid_set_pixel_size': (None, [p, i32, i32]),
        'mu_grid_place': (c_int, [p, i32, i32, p]), 'mu_grid_place_index': (c_int, [p, i32, p]),
        'mu_grid_remove': (None, [p, p]), 'mu_grid_find_id': (p, [p, u32]), 'mu_grid_item_at': (p, [p, i32]),
        'mu_grid_has_code': (c_int, [p, c_int16]), 'mu_grid_can_move': (c_int, [p, i32, i32, i32]),
    }
    for name, (res, args) in sig.items():
        fn = getattr(lib, name)
        fn.restype = res
        fn.argtypes = args
    return lib


ITEM_OBJ_SIZE = 0x70
RECORD_SIZE = 0x2c4


class GridCase:
    """One grid in the client machine and one in the reconstruction, driven together."""

    def __init__(self, client, lib, rng, items, type_=1, owner=0):
        self.client, self.lib, self.rng = client, lib, rng
        m = client.machine
        client.reset()
        self.events_c, self.events_a = [], []
        m.stub(0xc94193, self._status, 0)
        m.stub(0xad86dc, self._refresh, 0)
        self.owner_pages = 0
        m.stub(0xadaccf, lambda mm: self.owner_pages, 0)
        m.stub(0xc06911, lambda mm: (self.events_c.append(('lastpage', None)), 0)[1], 0)
        m.stub(0xccc51e, lambda mm: mm.fail('item record not cached'), 0)
        self.grid_c = m.alloc(0x4c, define=False)
        # client item objects: +0 record pointer (cached), +0x10 code, +0x64 id, +0x69/+0x6a cell
        self.items_c, self.items_a = [], []
        self._item_at = {}
        for spec in items:
            record = m.alloc(RECORD_SIZE, define=True)
            m.write(record + 0x25a, bytes([spec['w'], spec['h']]))
            obj = m.alloc(ITEM_OBJ_SIZE, define=True)
            m.put32(obj, record)
            m.put32(obj + 0x10, spec['code'])
            m.put32(obj + 0x64, spec['id'])
            m.write(obj + 0x69, bytes([spec.get('col', 0), spec.get('row', 0)]))
            self.items_c.append(obj)
            self._item_at[obj] = len(self.items_c) - 1
            item = GridItem(spec['id'], spec['code'], spec.get('col', 0), spec.get('row', 0), spec['w'], spec['h'])
            self.items_a.append(item)
        self.grid_a = Grid()

        def event(user, kind, item):
            index = None
            if item:
                index = [ctypes.addressof(x) for x in self.items_a].index(item)
            self.events_a.append(({1: 'status', 2: 'refresh', 3: 'lastpage'}[kind], index))
        self._event = EVENTFN(event)
        self.grid_a.event = self._event
        self.steps = 0

    def _status(self, m):
        item, type_, minus = m.args(3)
        self.events_c.append(('status', self._item_at.get(item, f'?{item:#x}')))
        if type_ != self.client.machine.u32(self.grid_c + 0x44) or minus != 0xffffffff:
            return m.fail('status refresh arguments')
        return 0

    def _refresh(self, m):
        if m.uc.reg_read(cm.UC_X86_REG_ECX) != self.grid_c:
            return m.fail('refresh on another object')
        self.events_c.append(('refresh', None))
        return 0

    # ---- state -------------------------------------------------------
    def state_c(self):
        m = self.client.machine
        g = self.grid_c
        raw = m.read(g, 0x4c)
        w = lambda o: struct.unpack_from('<i', raw, o)[0]  # noqa: E731
        cols, rows = w(0x2c), w(0x30)
        cells_ptr = struct.unpack_from('<I', raw, 0x38)[0]
        cells = list(struct.unpack(f'<{cols*rows}I', m.read(cells_ptr, 4*cols*rows))) if cells_ptr else []
        first, last = struct.unpack_from('<II', raw, 0x10)
        items = [self._item_at.get(p, f'?{p:#x}') for p in struct.unpack(f'<{(last-first)//4}I', m.read(first, last - first))] \
            if first else []
        positions = [tuple(m.read(o + 0x69, 2)) for o in self.items_c]
        return dict(field_00=struct.unpack_from('<I', raw, 0)[0], owner=struct.unpack_from('<I', raw, 0xc)[0],
                    x=w(0x1c), y=w(0x20), pixel_w=w(0x24), pixel_h=w(0x28), cols=cols, rows=rows, page=w(0x34),
                    has_cells=int(cells_ptr != 0), field_3c=w(0x3c), flag_40=raw[0x40], type=w(0x44),
                    flag_48=raw[0x48], flag_49=raw[0x49], cells=cells, items=items, positions=positions)

    def state_a(self):
        g = self.grid_a
        n = g.cols*g.rows if g.has_cells else 0
        addrs = [ctypes.addressof(x) for x in self.items_a]
        items = [addrs.index(ctypes.addressof(g.items[i].contents)) for i in range(g.item_count)]
        return dict(field_00=g.field_00, owner=g.owner, x=g.x, y=g.y, pixel_w=g.pixel_w, pixel_h=g.pixel_h,
                    cols=g.cols, rows=g.rows, page=g.page, has_cells=g.has_cells, field_3c=g.field_3c,
                    flag_40=g.flag_40, type=g.type, flag_48=g.flag_48, flag_49=g.flag_49,
                    cells=list(g.cells[:n]), items=items,
                    positions=[(x.col, x.row) for x in self.items_a])

    def compare(self, label):
        a, c = self.state_a(), self.state_c()
        if a != c:
            diff = {k: (c[k], a[k]) for k in c if c[k] != a.get(k)}
            raise cm.CaseError(f'{label}: state differs (client, authored): {str(diff)[:600]}')
        if self.events_a != self.events_c:
            raise cm.CaseError(f'{label}: events differ: client {self.events_c[-6:]} authored {self.events_a[-6:]}')
        self.steps += 1

    def call(self, address, args=()):
        return self.client.machine.call(address, args, ecx=self.grid_c)

    def both(self, label, address, args, authored, compare_result=True):
        result_c = self.call(address, args)
        result_a = authored()
        if compare_result:
            if isinstance(result_a, bool):
                rc, ra = result_c & 0xff, int(result_a)
            else:
                rc, ra = result_c & 0xffffffff, result_a & 0xffffffff
            if rc != ra:
                raise cm.CaseError(f'{label}: result client {rc:#x} authored {ra:#x}')
        self.compare(label)
        return result_c


def grid_items(rng, count):
    """Synthetic items: sizes 1..4 x 1..4 (Item.bmd range), distinct nonzero ids, random codes."""
    out = []
    ids = rng.sample(range(1, 0x7fffffff), count)
    for k in range(count):
        out.append(dict(id=ids[k], code=rng.choice([rng.randrange(0, 0x2c00), rng.randrange(-5, 5)]),
                        w=rng.choice([1, 1, 1, 2, 2, 3, 4]), h=rng.choice([1, 1, 2, 2, 3, 4])))
    return out


def validate_grid(client, lib, rng, report, cases):
    client.prepare(GRID_ROOTS, GRID_STOPS)
    client.common_stubs()
    totals = {'cases': 0, 'steps': 0, 'places': 0, 'removes': 0, 'fit_tests': 0, 'searches': 0, 'pixel_tests': 0,
              'counts': 0, 'wraps': 0, 'events': 0}
    i32 = c_int32
    for case in range(cases):
        shape = rng.choice([(8, 8), (8, 8), (8, 4), (4, 2), (1, 1), (5, 7), (10, 3), (8, 15)])
        cols, rows = shape
        items = grid_items(rng, rng.randrange(1, 24))
        g = GridCase(client, lib, rng, items, type_=1)
        ga = ctypes.byref(g.grid_a)
        lib.mu_grid_construct(ga)
        g.grid_a.event = g._event
        g.call(0xad322b)
        g.compare('construct')
        type_ = rng.choice([1, 1, 2, 4, 0xc])
        owner = rng.choice([0, 0x12345678])
        g.owner_pages = rng.randrange(0, 3)
        g.grid_a.owner_pages = g.owner_pages
        x, y, page = rng.randrange(-40, 600), rng.randrange(-40, 400), rng.randrange(0, 3)
        g.both('init', 0xad341d, (type_, owner, x, y, cols, rows, page),
               lambda: bool(lib.mu_grid_init(ga, type_, owner, x, y, cols, rows, page)))
        # a second Init must fail
        g.both('init again', 0xad341d, (type_, owner, x, y, cols, rows, page),
               lambda: bool(lib.mu_grid_init(ga, type_, owner, x, y, cols, rows, page)))
        placed = []
        for step in range(rng.randrange(20, 70)):
            op = rng.random()
            if op < 0.30:                       # place an unplaced item at a free spot (or at random)
                free = [k for k in range(len(items)) if k not in placed]
                if not free:
                    continue
                k = rng.choice(free)
                it = items[k]
                if rng.random() < 0.8:
                    col, row = i32(), i32()
                    ok = lib.mu_grid_find_free(ga, it['w'], it['h'], ctypes.byref(col), ctypes.byref(row))
                    if not ok:
                        continue
                    col, row = col.value, row.value
                else:
                    col, row = rng.randrange(-1, cols + 1), rng.randrange(-1, rows + 1)
                # the client writes past its cell block for items sticking out at the bottom: skip those
                if 0 <= col < cols and 0 <= row < rows and \
                        (row + it['h'] - 1)*cols + col + it['w'] - 1 >= cols*rows:
                    continue
                if 0 <= col < cols and 0 <= row < rows and col + it['w'] > cols:
                    totals['wraps'] += 1
                obj = g.items_c[k]
                if rng.random() < 0.5:
                    g.both(f'place {k}', 0xad37c9, (col, row, obj),
                           lambda: bool(lib.mu_grid_place(ga, col, row, ctypes.byref(g.items_a[k]))))
                else:
                    index = row*cols + col if 0 <= col < cols and 0 <= row < rows else rng.choice([-1, cols*rows])
                    g.both(f'place index {k}', 0xad3775, (index, obj),
                           lambda: bool(lib.mu_grid_place_index(ga, index, ctypes.byref(g.items_a[k]))))
                if g.grid_a.item_count > len(placed):
                    placed.append(k)
                totals['places'] += 1
            elif op < 0.40 and placed:          # remove (sometimes an absent item)
                k = rng.choice(placed) if rng.random() < 0.85 else rng.randrange(len(items))
                g.both(f'remove {k}', 0xad3a4e, (g.items_c[k],),
                       lambda: lib.mu_grid_remove(ga, ctypes.byref(g.items_a[k])), compare_result=False)
                if k in placed:
                    placed.remove(k)
                totals['removes'] += 1
            elif op < 0.60:                     # fit tests
                w, h = rng.randrange(0, 5), rng.randrange(0, 5)
                col, row = rng.randrange(-1, cols + 2), rng.randrange(0, rows + 2)
                index = row*cols + col
                if index < 0:
                    continue
                g.both('fits', 0xad4ee4, (col, row, w, h), lambda: bool(lib.mu_grid_fits(ga, col, row, w, h)))
                g.both('fits index', 0xad4e69, (index, w, h),
                       lambda: bool(lib.mu_grid_fits_index(ga, index, w, h)))
                k = rng.randrange(len(items))
                obj = g.items_c[k] if rng.random() < 0.9 else 0
                g.both('item fits', 0xad4ff4, (col, row, obj),
                       lambda: bool(lib.mu_grid_item_fits(ga, col, row,
                                                          ctypes.byref(g.items_a[k]) if obj else None)))
                totals['fit_tests'] += 3
            elif op < 0.72:                     # searches
                m = client.machine
                w, h = rng.randrange(1, 5), rng.randrange(1, 5)
                out = m.alloc(8, define=False)
                rc = g.call(0xad49fb, (w, h, out, out + 4)) & 0xff
                col, row = i32(), i32()
                ra = lib.mu_grid_find_free(ga, w, h, ctypes.byref(col), ctypes.byref(row))
                if rc != ra or (rc and struct.unpack('<ii', m.read(out, 8)) != (col.value, row.value)):
                    raise cm.CaseError('find free differs')
                g.compare('find free')
                g.both('find free index', 0xad4994, (w, h), lambda: lib.mu_grid_find_free_index(ga, w, h))
                g.both('count empty', 0xad4a6d, (), lambda: lib.mu_grid_count_empty(ga))
                limit = rng.choice([1, 2, 3, 5, 100])
                if cols*rows <= 128:
                    g.both('count fits', 0xad4ad9, (w, h, limit),
                           lambda: lib.mu_grid_count_fits(ga, w, h, limit, None))
                    totals['counts'] += 1
                index = rng.randrange(0, cols*rows)
                g.both('can move', 0xad47f1, (w, h, index), lambda: bool(lib.mu_grid_can_move(ga, w, h, index)))
                totals['searches'] += 4
            elif op < 0.88:                     # pixel mapping
                m = client.machine
                px, py = x + rng.randrange(-30, cols*26 + 30), y + rng.randrange(-30, rows*26 + 30)
                g.both('pt in', 0xad4f11, (px, py), lambda: bool(lib.mu_grid_pt_in(ga, px, py)))
                out = m.alloc(8, define=False)
                rc = g.call(0xad4d43, (px, py, out, out + 4)) & 0xff
                col, row = i32(), i32()
                ra = lib.mu_grid_pixel_cell(ga, px, py, ctypes.byref(col), ctypes.byref(row))
                if rc != ra or (rc and struct.unpack('<ii', m.read(out, 8)) != (col.value, row.value)):
                    raise cm.CaseError('pixel cell differs')
                g.both('pixel index', 0xad4da5, (px, py), lambda: lib.mu_grid_pixel_index(ga, px, py))
                k = rng.randrange(len(items))
                g.both('item fits pixel', 0xad5037, (px, py, g.items_c[k]),
                       lambda: bool(lib.mu_grid_item_fits_pixel(ga, px, py, ctypes.byref(g.items_a[k]))))
                rect = [x + rng.randrange(-5, 40), y + rng.randrange(-5, 40), 0, 0]
                rect[2], rect[3] = rect[0] + rng.randrange(0, cols*26 + 5), rect[1] + rng.randrange(0, rows*26 + 5)
                rbuf = m.alloc(16, define=True)
                m.write(rbuf, struct.pack('<4i', *rect))
                g.both('rect in', 0xad4f51, (rbuf,), lambda: bool(lib.mu_grid_rect_in(ga, (i32*4)(*rect))))
                totals['pixel_tests'] += 4
            else:                               # lookups
                index = rng.randrange(0, cols*rows)
                rc = g.call(0xad3fd9, (index,))
                ra = lib.mu_grid_item_at(ga, index)
                if g._item_at.get(rc) != (None if not ra else [ctypes.addressof(x) for x in g.items_a].index(ra)):
                    raise cm.CaseError('item at differs')
                k = rng.randrange(len(items))
                ident = items[k]['id'] if rng.random() < 0.8 else rng.randrange(0, 5)
                rc = g.call(0xad403c, (ident,))
                ra = lib.mu_grid_find_id(ga, ident)
                if g._item_at.get(rc) != (None if not ra else [ctypes.addressof(x) for x in g.items_a].index(ra)):
                    raise cm.CaseError('find id differs')
                code = items[k]['code'] if rng.random() < 0.8 else rng.randrange(-3, 3)
                g.both('has code', 0xad3c57, (code & 0xffff,), lambda: bool(lib.mu_grid_has_code(ga, code)))
                g.compare('lookups')
        totals['cases'] += 1
        totals['steps'] += g.steps
        totals['events'] += len(g.events_c)
    report['grid'] = totals
    return totals


# ==========================================================================
# slots and item3d

SLOT_ROOTS = (0xab6130,) + GRID_ROOTS
SLOT_STOPS = GRID_STOPS | {0xac3bf7, 0xaadd42, 0xaaeadc, 0x16c23d5}
SCREEN_W, SCREEN_H = 0x01cf1624, 0x01cf1628
F = cm.fbits
B = cm.bits_f


class SlotPage(Structure):
    _fields_ = [('grid', c_void_p), ('x', ctypes.c_float), ('y', ctypes.c_float), ('cell_w', ctypes.c_float),
                ('cell_h', ctypes.c_float), ('gap_x', ctypes.c_float), ('gap_y', ctypes.c_float)]


class SlotFrame(Structure):
    _fields_ = [('visible', c_int), ('align', c_int32), ('movie_x', ctypes.c_float), ('movie_y', ctypes.c_float),
                ('alpha', ctypes.c_float), ('scale', ctypes.c_float), ('pages', POINTER(SlotPage)),
                ('page_count', c_int32), ('frame_id', c_uint32)]


class SlotCall(Structure):
    _fields_ = [('item', c_void_p), ('page', c_int32), ('x', ctypes.c_float), ('y', ctypes.c_float),
                ('w', ctypes.c_float), ('h', ctypes.c_float), ('page_type', c_int32), ('page_flag', c_uint8),
                ('type8_seen', c_uint8), ('frame_id', c_uint32)]


class ItemTRS(Structure):
    _fields_ = [('offset_x', ctypes.c_float), ('offset_y', ctypes.c_float), ('rotation', ctypes.c_float*3),
                ('scale', ctypes.c_float)]


class Item3dIn(Structure):
    _fields_ = [('x', ctypes.c_float), ('y', ctypes.c_float), ('w', ctypes.c_float), ('h', ctypes.c_float),
                ('code', c_int32), ('level_word', c_int32), ('excellent', c_int32), ('set_bits', c_int32),
                ('a28', c_int32), ('a2c', c_int32), ('a30', c_int32), ('select', c_uint8),
                ('scale_override', ctypes.c_float), ('flip_y', c_uint8), ('no_select', c_uint8), ('a44', c_int32),
                ('a48', c_int32), ('code2', c_int32), ('gfx_busy', c_uint8), ('cursor_in', c_uint8),
                ('ui_3e_visible', c_uint8), ('ui_b602', c_uint8), ('kind_b_6a', c_uint8), ('kind_a_22', c_uint8),
                ('code2_kind_b_6a', c_uint8), ('trs', ItemTRS), ('frame_scale', ctypes.c_float),
                ('rate_x', ctypes.c_float), ('rate_y', ctypes.c_float)]


class Item3dOut(Structure):
    _fields_ = [('model', c_int32), ('level_word', c_int32), ('excellent', c_int32), ('set_bits', c_int32),
                ('position', ctypes.c_float*3), ('select', c_uint8), ('a28', c_int32), ('a2c', c_int32),
                ('a30', c_int32), ('scale', ctypes.c_float), ('a44', c_int32), ('a48', c_int32),
                ('angle', ctypes.c_float*3)]


class WrapperIn(Structure):
    _fields_ = [('code', c_int32), ('level_word', c_int32), ('set_bits', c_uint8), ('excellent', c_uint8),
                ('element', c_int32), ('item_108', c_uint32), ('x', ctypes.c_float), ('y', ctypes.c_float),
                ('w', ctypes.c_float), ('h', ctypes.c_float), ('a1c', c_int32), ('a20', c_int32), ('a24', c_int32),
                ('a28', c_int32), ('a2c', c_uint32), ('a30', c_int32), ('a34', ctypes.c_float), ('a38', c_int32),
                ('a3c', c_int32), ('a40', c_int32), ('a44', c_int32), ('frame_active', c_uint8),
                ('gfx_busy', c_uint8), ('gfx_cc', c_uint8), ('cursor_in', c_uint8)]


class WrapperOut(Structure):
    _fields_ = [('status', c_uint8), ('hover', c_uint8), ('hover_rect', c_int32*4), ('element_value', c_int32*2),
                ('element_unmodelled', c_uint8), ('item3d', Item3dIn), ('overlay_scale', ctypes.c_float)]


COLORFN = CFUNCTYPE(None, c_void_p, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float)
EMITFN = CFUNCTYPE(None, c_void_p, POINTER(SlotCall))


def slot_lib(lib):
    lib.mu_frame_x.restype = ctypes.c_float
    lib.mu_frame_x.argtypes = [c_int32, ctypes.c_float, c_int32]
    lib.mu_frame_y.restype = ctypes.c_float
    lib.mu_frame_y.argtypes = [c_int32, ctypes.c_float, c_int32]
    lib.mu_slot_pass.restype = c_int
    lib.mu_slot_pass.argtypes = [POINTER(SlotFrame), c_int32, c_int32, ctypes.c_float, ctypes.c_float, COLORFN,
                                 EMITFN, c_void_p]
    lib.mu_item3d.restype = c_int
    lib.mu_item3d.argtypes = [POINTER(Item3dIn), POINTER(Item3dOut)]
    lib.mu_item3d_is_special.restype = c_int
    lib.mu_item3d_is_special.argtypes = [c_int32]
    lib.mu_slot_wrapper.restype = c_int
    lib.mu_slot_wrapper.argtypes = [c_int, POINTER(WrapperIn), POINTER(Item3dIn), POINTER(WrapperOut)]
    return lib


def rand_float(rng, lo, hi, step=None):
    v = rng.uniform(lo, hi)
    if step:
        v = round(v/step)*step
    return cm.f32(v)


SCREENS = [(640, 480), (800, 600), (1024, 768), (1280, 1024), (1722, 1048), (1920, 1080), (1366, 768),
           (2560, 1440)]


def validate_slots(client, lib, rng, report, cases):
    client.prepare(SLOT_ROOTS, SLOT_STOPS)
    client.common_stubs()
    m = client.machine
    totals = {'cases': 0, 'pages': 0, 'slot_calls': 0, 'colors': 0, 'invisible': 0, 'alignments': {}}
    for case in range(cases):
        client.reset()
        sw, sh = rng.choice(SCREENS)
        m.put32(SCREEN_W, sw)
        m.put32(SCREEN_H, sh)
        gfx = m.alloc(0x300, define=True)
        rate_x, rate_y = cm.f32(640.0/sw), cm.f32(480.0/sh)
        m.putf(gfx + 0x2cc, rate_x)
        m.putf(gfx + 0x2d0, rate_y)
        m.stub(0xac3bf7, lambda mm: gfx, 0)
        m.stub(0xc94193, lambda mm: 0, 0)
        m.stub(0xad86dc, lambda mm: 0, 0)
        m.stub(0xadaccf, lambda mm: 0, 0)
        visible = 1 if rng.random() < 0.95 else 0
        align = rng.choice(range(10))
        m.stub(0xaadd42, lambda mm: visible, 0)
        m.stub(0xaaeadc, lambda mm: align, 0)
        frame = m.alloc(0x80, define=True)
        movie_x, movie_y = rand_float(rng, -200, 1100, 0.25), rand_float(rng, -200, 800, 0.25)
        alpha, scale = rand_float(rng, 0, 1), rng.choice([cm.f32(1.0), rand_float(rng, 0.5, 2.0)])
        m.putf(frame + 0x50, alpha)
        m.putf(frame + 0x58, scale)
        m.putf(frame + 0x70, movie_x)
        m.putf(frame + 0x74, movie_y)
        npages = rng.choice([1, 1, 2, 3])
        records = m.alloc(0x1c*npages, define=True)
        m.put32(frame + 0x78, records)
        m.put32(frame + 0x7c, records + 0x1c*npages)
        pages_a = (SlotPage*npages)()
        keep, item_map = [], {}
        for p in range(npages):
            cols, rows = rng.choice([(8, 8), (8, 4), (4, 4)])
            gtype = rng.choice([1, 2, 8, 4])
            grid_c = m.alloc(0x4c)
            m.call(0xad322b, (), ecx=grid_c)
            m.call(0xad341d, (gtype, 0, 0, 0, cols, rows, p), ecx=grid_c)
            ga = Grid()
            lib.mu_grid_construct(ctypes.byref(ga))
            lib.mu_grid_init(ctypes.byref(ga), gtype, 0, 0, 0, cols, rows, p)
            flag48 = rng.choice([0, 1])
            m.write(grid_c + 0x48, bytes([flag48]))
            ga.flag_48 = flag48
            items = grid_items(rng, rng.randrange(0, 12))
            for it in items:
                if rng.random() < 0.15:
                    it['code'] = -1 - rng.randrange(3)
                col, row = c_int32(), c_int32()
                if not lib.mu_grid_find_free(ctypes.byref(ga), it['w'], it['h'], ctypes.byref(col), ctypes.byref(row)):
                    continue
                if (row.value + it['h'] - 1)*cols + col.value + it['w'] - 1 >= cols*rows:
                    continue
                record = m.alloc(RECORD_SIZE, define=True)
                m.write(record + 0x25a, bytes([it['w'], it['h']]))
                obj = m.alloc(ITEM_OBJ_SIZE, define=True)
                m.put32(obj, record)
                m.put32(obj + 0x10, it['code'] & 0xffffffff)
                m.put32(obj + 0x64, it['id'])
                m.call(0xad37c9, (col.value, row.value, obj), ecx=grid_c)
                ia = GridItem(it['id'], it['code'], 0, 0, it['w'], it['h'])
                keep.append(ia)
                lib.mu_grid_place(ctypes.byref(ga), col.value, row.value, ctypes.byref(ia))
                item_map[obj] = len(item_map)
                item_map[ctypes.addressof(ia)] = item_map[obj]
            keep.append(ga)
            geo = [rand_float(rng, -20, 300, 0.5), rand_float(rng, -20, 400, 0.5), rand_float(rng, 18, 40, 0.25),
                   rand_float(rng, 18, 40, 0.25), rng.choice([0.0, 1.0, rand_float(rng, 0, 4, 0.25)]),
                   rng.choice([0.0, 1.0, rand_float(rng, 0, 4, 0.25)])]
            m.write(records + 0x1c*p, struct.pack('<I6f', grid_c, *geo))
            pages_a[p] = SlotPage(ctypes.cast(ctypes.pointer(ga), c_void_p), *geo)
        calls_c = []

        m.stub(0x16c23d5, lambda mm: (calls_c.append(('slot',) + tuple(mm.args(16))), 0)[1], 0)
        m.calls = []
        rc = m.call(0xab6130, (), ecx=frame) & 0xff
        seq_c = []
        for name, words in m.calls:
            if name == 'glColor4f':
                seq_c.append(('color',) + tuple(words))
        stream_c = []
        # merge the recorded slot calls and colours in order: one colour precedes each slot call
        slots_c = [c for c in calls_c]
        if len(seq_c) != len(slots_c):
            raise cm.CaseError(f'slots case {case}: {len(seq_c)} colours, {len(slots_c)} slot calls')
        for col_, sl in zip(seq_c, slots_c):
            w = sl[1:]
            stream_c.append(col_)
            stream_c.append(('slot', item_map.get(w[0], '?'), w[1], w[2], w[3], w[4], w[5], w[6] & 0xff, w[7],
                             w[8] & 0xff, w[9], w[10], w[11], w[12], w[13], w[14], w[15]))
        stream_a = []

        def color(user, r, g, b, a):
            stream_a.append(('color', F(r), F(g), F(b), F(a)))

        def emit(user, call):
            c = call.contents
            stream_a.append(('slot', item_map.get(c.item, '?'), F(c.x), F(c.y), F(c.w), F(c.h), c.page_type & 0xffffffff,
                             c.page_flag, 0, c.type8_seen, frame, 0, F(0.0), 0xffffffff, 0, 1, 0))
        fa = SlotFrame(visible, align, movie_x, movie_y, alpha, scale, pages_a, npages, frame)
        cf, ef = COLORFN(color), EMITFN(emit)
        ra = lib.mu_slot_pass(ctypes.byref(fa), sw, sh, rate_x, rate_y, cf, ef, None)
        if rc != ra or stream_c != stream_a:
            for k, (x, y) in enumerate(zip(stream_c, stream_a)):
                if x != y:
                    raise cm.CaseError(f'slots case {case} entry {k}: client {x} authored {y}')
            raise cm.CaseError(f'slots case {case}: rc {rc}/{ra}, lengths {len(stream_c)}/{len(stream_a)}')
        totals['cases'] += 1
        totals['pages'] += npages
        totals['slot_calls'] += len(slots_c)
        totals['colors'] += len(seq_c)
        totals['invisible'] += int(not visible)
        totals['alignments'][align] = totals['alignments'].get(align, 0) + 1
    report['slots'] = totals
    return totals


ITEM3D_ROOTS = (0x16c23d5,)
ITEM3D_STOPS = {0xac3bf7, 0xc08654, 0xaae6f9, 0xec4bf2, 0xc94193, 0xcda1cf, 0x10d2013, 0xf2bb92, 0xf2aba9,
                0xf2b602, 0x11204db, 0xcd4ea8, 0xcd6017, 0xcd5fac, 0x16c2d82, 0x16bf1fb, 0xf2c0d5,
                OP_NEW, OP_DELETE, MEMSET, MEMMOVE, MEMCPY}
ITEM_ANGLE = 0x0b5e3c2c


def validate_item3d(client, lib, rng, report, cases):
    client.prepare(ITEM3D_ROOTS, ITEM3D_STOPS)
    client.common_stubs()
    m = client.machine
    totals = {'cases': 0, 'draws': 0, 'hovers': 0, 'selected': 0, 'flip_y': 0, 'kind_b_6a': 0, 'kind_a_22': 0,
              'overrides': 0, 'none': 0}
    for case in range(cases):
        client.reset()
        sw, sh = rng.choice(SCREENS)
        rate_x, rate_y = cm.f32(640.0/sw), cm.f32(480.0/sh)
        gfx = m.alloc(0x300, define=True)
        busy_obj, cc_obj, scale_obj = (m.alloc(0x60, define=True) for _ in range(3))
        frame = m.alloc(0x80, define=True)
        frame_active = rng.random() < 0.7
        m.put32(gfx + 0x2e4, frame if frame_active else frame + 4)
        m.put32(gfx + 0xd4, busy_obj)
        m.put32(gfx + 0xcc, cc_obj)
        m.put32(gfx + 0xa0, scale_obj)
        frame_scale = rng.choice([cm.f32(1.0), rand_float(rng, 0.5, 2.0)])
        m.putf(scale_obj + 0x58, frame_scale)
        m.putf(gfx + 0x2cc, rate_x)
        m.putf(gfx + 0x2d0, rate_y)
        m.stub(0xac3bf7, lambda mm: gfx, 0)
        busy = rng.random() < 0.15
        cc = rng.random() < 0.15
        cursor_in = rng.random() < 0.5
        ui3e, uib602 = rng.random() < 0.3, rng.random() < 0.3
        m.stub(0xc08654, lambda mm: int(busy), 0)
        m.stub(0xaae6f9, lambda mm: int(cc), 0)
        m.stub(0xec4bf2, lambda mm: int(cursor_in), 0)
        newui = m.alloc(0x10, define=True)
        m.stub(0xf2bb92, lambda mm: newui, 0)
        m.stub(0xf2aba9, lambda mm: int(ui3e) if mm.args(1)[0] == 0x3e else mm.fail('NewUI id'), 4)
        m.stub(0xf2b602, lambda mm: int(uib602), 0)
        events_c = []
        m.stub(0xc94193, lambda mm: (events_c.append(('status',) + tuple(mm.args(3))), 0)[1], 0)
        m.stub(0xcda1cf, lambda mm: (events_c.append(('hover',) + tuple(mm.args(10))), 0)[1], 0)
        # item: synthetic object
        code = rng.randrange(0, 0x2c00)
        while lib.mu_item3d_is_special(code):
            code = rng.randrange(0, 0x2c00)
        if rng.random() < 0.05:
            code = -1
        kind_b6a, kind_a22 = rng.random() < 0.15, rng.random() < 0.15
        m.stub(0xcd4ea8, lambda mm: newui, 0)
        m.stub(0xcd6017, lambda mm: int(kind_b6a and mm.args(2)[0] == code & 0xffffffff and mm.args(2)[1] == 0x6a), 8)
        m.stub(0xcd5fac, lambda mm: int(kind_a22 and mm.args(2)[0] == code & 0xffffffff and mm.args(2)[1] == 0x22), 8)
        trs = ItemTRS(rand_float(rng, 0.3, 1.0, 0.01), rand_float(rng, 0.3, 1.0, 0.01),
                      (ctypes.c_float*3)(*[cm.f32(rng.choice([0, 90, 180, 270, -90, -10, 15, 359])) for _ in range(3)]),
                      rand_float(rng, 0.001, 0.005, 0.0001))
        trs_rec = m.alloc(0x18, define=True)
        m.write(trs_rec, bytes(trs))
        m.stub(0x11204db, lambda mm: trs_rec if mm.args(1)[0] == code & 0xffffffff else mm.fail('TRS key'), 4)
        obj = m.alloc(0x120, define=True)
        level_word = rng.randrange(0, 0x80) | (rng.randrange(0, 16) << 3)
        set_bits, excellent = rng.randrange(256), rng.random() < 0.3
        m.put32(obj, m.alloc(RECORD_SIZE, define=True))
        m.put32(obj + 0x10, code & 0xffffffff)
        m.put32(obj + 0x14, level_word)
        m.write(obj + 0x3b, bytes([set_bits]))
        m.write(obj + 0x92, b'\0')
        m.write(obj + 0x98, bytes([1 if excellent else 0]))
        m.put32(obj + 0x84, 0xffffffff)
        x, y = rand_float(rng, 0, 640, 0.125), rand_float(rng, 0, 480, 0.125)
        w, h = rand_float(rng, 5, 80, 0.125), rand_float(rng, 5, 100, 0.125)
        a1c, a20, a28 = rng.choice([1, 2, 4, 8]), rng.choice([0, 1]), rng.choice([0, 1])
        a24 = 0 if rng.random() < 0.85 else 1
        a30 = 0 if rng.random() < 0.85 else 1
        a34 = cm.f32(0.0) if rng.random() < 0.8 else rand_float(rng, -0.01, 0.01, 0.0005)
        a3c = 0 if rng.random() < 0.8 else 1
        a44 = 0 if rng.random() < 0.9 else 1
        a2c = frame if rng.random() < 0.95 else 0
        args = (obj, F(x), F(y), F(w), F(h), a1c, a20, a24, a28, a2c, a30, F(a34), 0xffffffff, a3c, 1, a44)
        ros_c, overlay_c = [], []

        def ros(mm):
            wd = mm.args(12)
            pos = struct.unpack('<3I', mm.read(wd[4], 12))
            angle = struct.unpack('<3I', mm.read(ITEM_ANGLE, 12))
            ros_c.append(tuple(wd[:4]) + pos + tuple(wd[5:]) + angle)
            return 0
        m.stub(0x16c2d82, ros, 0)
        m.stub(0x16bf1fb, lambda mm: (overlay_c.append(tuple(mm.args(16))), 0)[1], 0)
        m.call(0x16c23d5, args)
        # authored
        win = WrapperIn(code, level_word, set_bits, int(excellent), -1, obj + 0x108, x, y, w, h, a1c, a20, a24, a28,
                        a2c, a30, a34, -1, a3c, 1, a44, int(frame_active), int(busy), int(cc), int(cursor_in))
        sysin = Item3dIn()
        sysin.gfx_busy, sysin.cursor_in, sysin.ui_3e_visible, sysin.ui_b602 = int(busy), int(cursor_in), int(ui3e), int(uib602)
        sysin.kind_b_6a, sysin.kind_a_22 = int(kind_b6a), int(kind_a22)
        sysin.trs, sysin.frame_scale, sysin.rate_x, sysin.rate_y = trs, frame_scale, rate_x, rate_y
        wout = WrapperOut()
        lib.mu_slot_wrapper(1, ctypes.byref(win), ctypes.byref(sysin), ctypes.byref(wout))
        events_a = []
        if wout.status:
            events_a.append(('status', obj, a1c, 0xffffffff))
        if wout.hover:
            events_a.append(('hover', obj, a2c) + tuple(v & 0xffffffff for v in wout.hover_rect) + (a1c, a20, a28, 0))
        out = Item3dOut()
        kind = lib.mu_item3d(ctypes.byref(wout.item3d), ctypes.byref(out))
        ros_a = []
        if kind == 1:
            ros_a.append((out.model, out.level_word, out.excellent & 0xffffffff, out.set_bits & 0xffffffff)
                         + tuple(F(v) for v in out.position) + (out.select, out.a28 & 0xffffffff,
                                                                  out.a2c & 0xffffffff, out.a30 & 0xffffffff,
                                                                  F(out.scale), out.a44 & 0xffffffff,
                                                                  out.a48 & 0xffffffff) + tuple(F(v) for v in out.angle))
        overlay_a = [(obj, a1c, F(x), F(y), F(w), F(h), wout.item3d.excellent, a24, 0xffffffff, 0xffffffff, a30, F(a34),
                      F(wout.overlay_scale), a3c, a44, 1)]
        for label, c, a in (('events', events_c, events_a), ('RenderObjectScreen', ros_c, ros_a),
                            ('overlay', overlay_c, overlay_a)):
            if c != a:
                raise cm.CaseError(f'item3d case {case} {label}: client {c} authored {a}')
        totals['cases'] += 1
        totals['draws'] += len(ros_c)
        totals['none'] += int(code == -1)
        totals['hovers'] += int(wout.hover)
        totals['selected'] += int(bool(ros_a) and ros_a[0][7] == 1)
        totals['flip_y'] += a3c
        totals['kind_b_6a'] += int(kind_b6a)
        totals['kind_a_22'] += int(kind_a22)
        totals['overrides'] += int(a34 > 0)
    report['item3d'] = totals
    return totals


# ==========================================================================
# pass: the per-window GFx render pass 0x00abfcca

EXTRA_SLOTS = {0x01a7c6d8: ('glPushAttrib', 'i'), 0x01a7c6dc: ('glPopAttrib', ''), 0x01a7c6e0: ('glOrtho', 'dddddd'),
               0x01a7c784: ('glGetFloatv', 'ip'), 0x01a7c698: ('glTranslatef', 'fff')}
PASS_ROOTS = (0xabfcca,)
PASS_STOPS = {0xac3bf7, 0x95f5d7, 0x9e819e, 0xac16af, 0xac16d0, 0xf2bb92, 0xf2aba9, OP_NEW, OP_DELETE}
HUD_OPS = {100: 'glPushAttrib', 101: 'glPopAttrib', 102: 'glOrtho', 103: 'glGetFloatv', 104: 'glTranslatef',
           105: 'Display', 106: 'Items', 107: 'Overlay'}
CAMERA_MATRIX, CAMERA_SAVED, CAMERA_POSITION, CAMERA_EYE = 0x0bdc5918, 0x0bdc5948, 0x0bdc5ab4, 0x0bdc5984
RATES = 0x0bdc58cc


class HudWindow(Structure):
    _fields_ = [('id', c_uint32), ('identity', c_uint8), ('excluded', c_uint8), ('alpha', ctypes.c_float)]


class HudCamera(Structure):
    _fields_ = [('matrix', ctypes.c_float*12), ('saved', ctypes.c_float*12), ('position', ctypes.c_float*3),
                ('eye', ctypes.c_float*3), ('rate', ctypes.c_float*2), ('saved_rate', ctypes.c_float*2)]


MODELVIEWFN = CFUNCTYPE(None, c_void_p, POINTER(ctypes.c_float))


def validate_pass(client, lib, rng, report, cases):
    import validate_ui as vu
    client.prepare(PASS_ROOTS, PASS_STOPS)
    client.common_stubs()
    m = client.machine
    lib.mu_ui_state_init.argtypes = [c_void_p, c_uint32, c_uint32]
    lib.mu_hud_window_pass.argtypes = [c_void_p, POINTER(HudCamera), POINTER(HudWindow), c_int32, c_int,
                                       MODELVIEWFN, c_void_p]
    totals = {'cases': 0, 'windows': 0, 'drawn': 0, 'calls': 0}
    for case in range(cases):
        client.reset()
        m.calls = []
        sw, sh = rng.choice(SCREENS)
        calls_a = []

        def record(user, op, words, count, data, size):
            name = vu.OPS[op] if op < len(vu.OPS) else HUD_OPS[op]
            calls_a.append((name, tuple(words[i] for i in range(count))))
        sinkfn = vu.SINKFN(record)
        state = vu.State()
        state.sink.call = sinkfn
        lib.mu_ui_state_init(ctypes.byref(state), sw, sh)
        for flag in ('depth_test', 'depth_mask', 'alpha_test', 'texture_2d', 'cull_face', 'fog'):
            setattr(state, flag, rng.choice([0, 1]))
        state.fov, state.znear, state.zfar = rand_float(rng, 30, 60, 1), rand_float(rng, 10, 30, 1), rand_float(rng, 1000, 3000, 10)
        for name, address in vu.GLOBALS.items():
            value = getattr(state, name)
            if name in vu.BYTE_FLAGS:
                m.write(address, bytes([value]))
            elif name in vu.FLOAT_GLOBALS:
                m.putf(address, value)
            else:
                m.put32(address, value)
        cam = HudCamera()
        for i in range(12):
            cam.matrix[i] = rand_float(rng, -2, 2, 0.001)
        for i in range(3):
            cam.position[i] = rand_float(rng, -5000, 5000, 0.5)
        cam.rate[0], cam.rate[1] = rand_float(rng, 0.5, 3, 0.01), rand_float(rng, 0.5, 3, 0.01)
        m.write(CAMERA_MATRIX, bytes(cam.matrix))
        m.write(CAMERA_POSITION, bytes(cam.position))
        m.write(RATES, bytes(cam.rate))
        matrices = [[rand_float(rng, -3, 3, 0.001) for _ in range(16)] for _ in range(64)]
        queue_c, queue_a = list(matrices), list(matrices)

        def get_c(mm, words):
            mm.write(words[1], struct.pack('<16f', *queue_c.pop(0)))
            return 0
        m.handlers['glGetFloatv'] = get_c

        def get_a(user, out):
            for i, v in enumerate(queue_a.pop(0)):
                out[i] = v
        getfn = MODELVIEWFN(get_a)
        # windows and the manager's std::list
        manager = m.alloc(0x40, define=True)
        specials = [m.alloc(0x60, define=True) for _ in range(4)]
        for k, getter in enumerate((0x95f5d7, 0x9e819e, 0xac16af, 0xac16d0)):
            m.stub(getter, lambda mm, v=specials[k]: v, 0)
        m.stub(0xac3bf7, lambda mm: manager, 0)
        ui_hidden = rng.random() < 0.3
        newui = m.alloc(0x10, define=True)
        m.stub(0xf2bb92, lambda mm: newui, 0)
        hidden_ids = rng.sample([0x45, 0x37, 0x3e], 1) if ui_hidden else []
        m.stub(0xf2aba9, lambda mm: int(mm.args(1)[0] in hidden_ids), 4)
        vtable = m.alloc(0x40, define=True)
        for off, name in ((0x1c, 'Display'), (0x20, 'Items'), (0x24, 'Overlay')):
            stub = m._new_stub()
            m.put32(vtable + off, stub)
            m.stub(stub, lambda mm, n=name: (mm.calls.append((n, (mm.uc.reg_read(cm.UC_X86_REG_ECX),))), 0)[1], 0)
        nwin = rng.randrange(0, 6)
        wins_a = (HudWindow*max(nwin, 1))()
        objs = []
        for k in range(nwin):
            r = rng.random()
            if r < 0.1:
                obj, ident, excl = 0, 0, 0
            elif r < 0.25:
                obj, ident, excl = specials[rng.randrange(3)], 1, 0
            elif r < 0.33:
                obj, ident, excl = specials[3], 0, 1
            else:
                obj, ident, excl = m.alloc(0x60, define=True), 0, 0
            alpha = rand_float(rng, 0, 1, 0.01)
            if obj in objs:                    # the same window twice: one +0x50
                alpha = [w.alpha for w in list(wins_a)[:k] if w.id == obj][0]
            if obj and obj not in specials:
                m.put32(obj, vtable)
                m.putf(obj + 0x50, alpha)
            elif obj:
                m.put32(obj, vtable)
                m.putf(obj + 0x50, alpha)
            objs.append(obj)
            wins_a[k] = HudWindow(obj, ident, excl, alpha)
        head = m.alloc(12, define=True)
        nodes = [m.alloc(12, define=True) for _ in objs]
        chain = [head] + nodes
        for i, node in enumerate(chain):
            m.put32(node, chain[(i + 1) % len(chain)])
            m.put32(node + 4, chain[i - 1])
            if node != head:
                m.put32(node + 8, objs[i - 1])
        m.put32(manager + 4, head)
        m.call(0xabfcca, (), ecx=manager)
        # the client walks the list with reverse iterators (last window first)
        drawn = (HudWindow*max(nwin, 1))(*reversed(list(wins_a)[:nwin]))
        wins_a = drawn
        lib.mu_hud_window_pass(ctypes.byref(state), ctypes.byref(cam), wins_a, nwin, int(ui_hidden), getfn, None)
        calls_c = []
        for name, words in m.calls:
            if name == 'glGetFloatv':
                words = (words[0],)
            calls_c.append((name, tuple(words)))
        if calls_c != calls_a:
            for k, (x, y) in enumerate(zip(calls_c, calls_a)):
                if x != y:
                    raise cm.CaseError(f'pass case {case} call {k}: client {x} authored {y}')
            raise cm.CaseError(f'pass case {case}: {len(calls_c)} client calls, {len(calls_a)} authored')
        # globals after the pass
        for label, address, values in (('matrix', CAMERA_MATRIX, cam.matrix), ('eye', CAMERA_EYE, cam.eye),
                                       ('rates', RATES, cam.rate)):
            got = m.read(address, 4*len(values))
            if got != bytes(values) and (label != 'eye' or any(c[0] == 'Items' for c in calls_c)):
                raise cm.CaseError(f'pass case {case}: {label} differs')
        for flag in ('depth_test', 'depth_mask'):
            if m.read(vu.GLOBALS[flag], 1)[0] != getattr(state, flag):
                raise cm.CaseError(f'pass case {case}: {flag} cache differs')
        totals['cases'] += 1
        totals['windows'] += nwin
        totals['drawn'] += sum(1 for c in calls_c if c[0] == 'Items')
        totals['calls'] += len(calls_c)
    report['pass'] = totals
    return totals


# ==========================================================================
# html: the InfoPopup tooltip assembly 0x00b8d94b and the HTML line builder 0x00ab4dc0

TEXT_LIST, TEXT_COLOR, TEXT_BOLD, TEXT_RAW = 0x10c76988, 0x10c7b938, 0x10c7ba78, 0x10c7bbb8
MODULE_BASE, MODULE_SIZE = 0x10c70000, 0x10000
HTML_ROOTS = (0xb8d94b, 0xab4dc0)
# C++ library pieces modelled in Python: ostringstream (ctor, <<, str, dtor),
# Boost.Format-style formatter (ctor, %, str, dtor), stoi and the ANSI->UTF-8
# conversion; the GFx invoke is recorded.
STREAM_CTOR, STREAM_PUT_STRING, STREAM_PUT_CSTR, STREAM_STR, STREAM_DTOR = 0x969613, 0x94437f, 0x944605, 0x96a5b7, 0x969a1b
FORMAT_CTOR, FORMAT_ARG, FORMAT_STR, FORMAT_DTOR = 0x96e8c7, 0x96c702, 0x97258c, 0x96f4ae
STOI, TO_UTF8, GFX_INVOKE = 0x96a4f9, 0xa99d93, 0xaae7e0
HTML_STOPS = {FREE, OP_NEW, OP_DELETE, OP_NEW_ARRAY, OP_DELETE_ARRAY, MEMSET, MEMMOVE, MEMCPY, STRLEN, STRCMP, 0xac3bf7, STREAM_CTOR,
              STREAM_PUT_STRING, STREAM_PUT_CSTR, STREAM_STR, STREAM_DTOR, FORMAT_CTOR, FORMAT_ARG, FORMAT_STR,
              FORMAT_DTOR, STOI, TO_UTF8, GFX_INVOKE}
POPUP_PATCH = 0x00b8dcc2      # runtime patch; original: push eax; push [ebp-0x44]; push [ebp-0x48]


def read_cstr(m, address, limit=1 << 16):
    out = bytearray()
    while len(out) < limit:
        chunk = m.read(address + len(out), 64)
        k = chunk.find(b'\0')
        if k >= 0:
            out += chunk[:k]
            return bytes(out)
        out += chunk
    raise cm.CaseError('unterminated string')


def read_string(m, obj):
    size, cap = struct.unpack('<II', m.read(obj + 0x10, 8))
    data = obj if cap < 16 else m.u32(obj)
    return m.read(data, size)


def write_string(m, obj, value):
    if len(value) < 16:
        m.write(obj, value + b'\0' + b'\0'*(15 - len(value)))
        cap = 15
    else:
        size = len(value) + 1
        if size >= 0x1000:            # MSVC big block: 32-byte aligned, raw pointer stored at [ptr-4]
            raw = m.alloc(size + 0x23, define=True)
            buf = (raw + 0x23) & ~0x1f
            m.put32(buf - 4, raw)
        else:
            buf = m.alloc(size, define=True)
        m.write(buf, value + b'\0')
        m.write(obj, struct.pack('<I', buf) + b'\0'*12)
        cap = len(value)
    m.write(obj + 0x10, struct.pack('<II', len(value), cap))


class HtmlModels:
    def __init__(self, client):
        self.m = client.machine
        self.streams, self.formats, self.invokes = {}, {}, []
        m = self.m
        ecx = lambda: m.uc.reg_read(cm.UC_X86_REG_ECX)  # noqa: E731

        # the ostringstream object; its ostream base (the << target) is at +0x10
        def stream_ctor(mm):
            self.streams[ecx()] = bytearray()
            self.streams[ecx() + 0x10] = self.streams[ecx()]
            return ecx()

        def put_string(mm):
            stream, string = mm.args(2)
            self.streams[stream] += read_string(mm, string)
            return stream

        def put_cstr(mm):
            stream, text = mm.args(2)
            self.streams[stream] += read_cstr(mm, text)
            return stream

        def stream_str(mm):
            ret = mm.args(1)[0]
            write_string(mm, ret, bytes(self.streams[ecx()]))
            return ret

        def format_ctor(mm):
            self.formats[ecx()] = [read_cstr(mm, mm.args(1)[0]), []]
            return ecx()

        def format_arg(mm):
            self.formats[ecx()][1].append(read_string(mm, mm.args(1)[0]))
            return ecx()

        def format_str(mm):
            fmt, args = self.formats[ecx()]
            parts = fmt.split(b'%s')
            if len(parts) != len(args) + 1:
                return mm.fail('format arity')
            out = parts[0] + b''.join(a + p for a, p in zip(args, parts[1:]))
            ret = mm.args(1)[0]
            write_string(mm, ret, out)
            return ret

        def stoi(mm):
            string, index, base = mm.args(3)
            text = read_string(mm, string).decode('latin1').lstrip()
            digits = ''
            for ch in text:
                if ch.isdigit():
                    digits += ch
                else:
                    break
            if not digits or index or base != 10:
                return mm.fail('stoi would throw')
            return int(digits)

        def to_utf8(mm):
            dst, src = mm.args(2)
            write_string(mm, dst, read_string(mm, src).decode('latin1').encode('utf-8'))
            return dst

        def invoke(mm):
            words = mm.args(8)
            this, name, fmt = words[:3]
            self.invokes.append((this, read_cstr(mm, name), read_cstr(mm, fmt), tuple(words[3:7]),
                                 read_cstr(mm, words[7])))
            return 0
        for address, fn, cleanup in ((STREAM_CTOR, stream_ctor, 4), (STREAM_PUT_STRING, put_string, 0),
                                     (STREAM_PUT_CSTR, put_cstr, 0), (STREAM_STR, stream_str, 4),
                                     (STREAM_DTOR, lambda mm: 0, 0), (FORMAT_CTOR, format_ctor, 4),
                                     (FORMAT_ARG, format_arg, 4), (FORMAT_STR, format_str, 4),
                                     (FORMAT_DTOR, lambda mm: 0, 0), (STOI, stoi, 0), (TO_UTF8, to_utf8, 0),
                                     (GFX_INVOKE, invoke, 0)):
            m.stub(address, fn, cleanup)

        def patched(uc, address, size, user):
            esp = uc.reg_read(cm.UC_X86_REG_ESP)
            ebp = uc.reg_read(cm.UC_X86_REG_EBP)
            for value in (uc.reg_read(cm.UC_X86_REG_EAX), m.u32(ebp - 0x44), m.u32(ebp - 0x48)):
                esp -= 4
                m.uc.mem_write(esp, struct.pack('<I', value))
            uc.reg_write(cm.UC_X86_REG_ESP, esp)
            uc.reg_write(cm.UC_X86_REG_EIP, POPUP_PATCH + 7)
        m.uc.hook_add(cm.UC_HOOK_CODE, patched, begin=POPUP_PATCH, end=POPUP_PATCH)
        m.allow((POPUP_PATCH, POPUP_PATCH + 7))


class TooltipLine(Structure):
    _fields_ = [('text', ctypes.c_char_p), ('color', c_int32), ('bold', c_int32), ('raw', c_uint8)]


def html_lib(lib):
    lib.mu_tooltip_html_line.restype = ctypes.c_size_t
    lib.mu_tooltip_html_line.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, c_int32, c_int32]
    lib.mu_tooltip_html.restype = ctypes.c_size_t
    lib.mu_tooltip_html.argtypes = [ctypes.c_char_p, ctypes.c_size_t, POINTER(TooltipLine), c_int32, POINTER(c_int)]
    lib.mu_tooltip_popup_rect.argtypes = [ctypes.c_float, ctypes.c_float, POINTER(c_int32), ctypes.c_float,
                                          ctypes.c_float, POINTER(c_int32)]
    lib.mu_latin1_to_utf8.restype = ctypes.c_size_t
    lib.mu_latin1_to_utf8.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p]
    return lib


WORDS = [b'Damage', b'Defense', b'Durability', b'Kris', b'+7', b'Excellent', b'Wizardry', b'%d', b'[30/30]', b'<',
         b'<b>', b'a<b', b'Lv.8', b'\xe9t\xe9', b'Increases', b'by', b'10%', b'&', b'>', b'starGrade*', b'"', b"'"]


def tooltip_text(rng):
    r = rng.random()
    if r < 0.05:
        return b''
    if r < 0.12:
        return b'\n'
    if r < 0.17:
        return b'\n' + b' '.join(rng.choice(WORDS) for _ in range(rng.randrange(1, 4)))
    if r < 0.24:
        return b'x starGrade*' + bytes([0x30 + rng.randrange(10)])
    text = b' '.join(rng.choice(WORDS) for _ in range(rng.randrange(1, 9)))
    return text[:250]


def validate_html(client, lib, rng, report, cases):
    client.prepare(HTML_ROOTS, HTML_STOPS)
    client.common_stubs()
    m = client.machine
    m.uc.mem_map(MODULE_BASE, MODULE_SIZE)
    totals = {'cases': 0, 'lines': 0, 'single_lines': 0, 'stars': 0, 'raw': 0, 'bold': 0, 'html_bytes': 0}
    for case in range(cases):
        client.reset()
        m.uc.mem_write(MODULE_BASE, b'\0'*MODULE_SIZE)
        models = HtmlModels(client)
        sw, sh = rng.choice(SCREENS)
        rate_x, rate_y = cm.f32(640.0/sw), cm.f32(480.0/sh)
        gfx = m.alloc(0x300, define=True)
        m.putf(gfx + 0x2cc, rate_x)
        m.putf(gfx + 0x2d0, rate_y)
        m.stub(0xac3bf7, lambda mm: gfx, 0)
        # single HTML lines through 0x00ab4dc0 (bold 0/1/other, all colours and some outside)
        for k in range(8):
            text = tooltip_text(rng)
            color = rng.choice(list(range(23)) + [-1, 0x7fffffff, 100])
            bold = rng.choice([0, 1, 1, 2, 0x101])
            src = m.alloc(len(text) + 1, define=True)
            m.write(src, text + b'\0')
            out = m.alloc(0x18, define=True)
            write_string(m, out, b'')
            m.call(0xab4dc0, (out, src, color & 0xffffffff, bold))
            got = read_string(m, out)
            buf = ctypes.create_string_buffer(8192)
            lib.mu_tooltip_html_line(buf, 8192, text, color, bold)
            if got != buf.value:
                raise cm.CaseError(f'html line case {case}: client {got!r} authored {buf.value!r}')
            totals['single_lines'] += 1
            totals['bold'] += int((bold & 0xff) == 1)
        # a whole tooltip through 0x00b8d94b
        count = rng.randrange(0, 24)
        lines = []
        for i in range(count):
            text = tooltip_text(rng)
            if b'starGrade*' in text and not text[-1:].isdigit():
                text += b'1'
            color = rng.randrange(0, 23)
            raw = 1 if rng.random() < 0.08 else rng.choice([0, 0, 0, 2])
            bold = rng.choice([0, 1])
            m.write(TEXT_LIST + 0xff*i, text + b'\0')
            m.put32(TEXT_COLOR + 4*i, color)
            m.put32(TEXT_BOLD + 4*i, bold)
            m.write(TEXT_RAW + i, bytes([raw]))
            lines.append(TooltipLine(text, color, bold, raw))
            totals['stars'] += int(b'starGrade*' in text and raw != 1 and text[:1] not in (b'', b'\n'))
            totals['raw'] += int(raw == 1)
        popup = m.alloc(0x200, define=True)
        px, py = rand_float(rng, 0, 640, 0.25), rand_float(rng, 0, 480, 0.25)
        rect = [rng.randrange(0, 600), rng.randrange(0, 400), 0, 0]
        rect[2], rect[3] = rect[0] + rng.randrange(0, 200), rect[1] + rng.randrange(0, 200)
        m.putf(popup + 0x9c, px)
        m.putf(popup + 0xa0, py)
        m.write(popup + 0x7c, struct.pack('<4i', *rect))
        m.call(0xb8d94b, (count,), ecx=popup)
        arr = (TooltipLine*max(count, 1))(*lines)
        buf = ctypes.create_string_buffer(1 << 18)
        bad = c_int()
        lib.mu_tooltip_html(buf, 1 << 18, arr, count, ctypes.byref(bad))
        utf = ctypes.create_string_buffer(1 << 19)
        lib.mu_latin1_to_utf8(utf, 1 << 19, buf.value)
        out4 = (c_int32*4)()
        lib.mu_tooltip_popup_rect(px, py, (c_int32*4)(*rect), rate_x, rate_y, out4)
        expected = [(popup, b'SetInfoPopup', b'%d %d %d %d %s', tuple(v & 0xffffffff for v in out4), utf.value)]
        if models.invokes != expected:
            got = models.invokes[0] if models.invokes else None
            raise cm.CaseError(f'tooltip case {case}: client {str(got)[:400]} authored {str(expected[0])[:400]}')
        totals['cases'] += 1
        totals['lines'] += count
        totals['html_bytes'] += len(utf.value)
    report['html'] = totals
    return totals


# ==========================================================================
# format: tooltip-text formatter cases 0x00f1098a

FORMATTER = 0xf1098a
SPRINTF = 0x9619dd
FORMAT_TYPES = (1, 2, 4, 5, 6, 7, 9, 11, 13, 101, 201, 202, 203, 205)
GETTERS = {'req_strength': 0xcd27eb, 'req_agility': 0xcd2832, 'req_energy': 0xcd2879, 'req_level': 0xcd298d}
FORMAT_STOPS = {FREE, OP_NEW, OP_DELETE, OP_NEW_ARRAY, OP_DELETE_ARRAY, MEMSET, MEMMOVE, MEMCPY, STRLEN, STRCMP,
                SPRINTF, 0xf1425b, 0xf142b1, 0xa00367, 0xf13774, 0x11df8b9, 0xcbc335, 0xcd248c, 0xcd25ec, 0x95fc2e,
                0x987982} | set(GETTERS.values())
HERO, SOCKET_MANAGER = 0x01d1df1c, 0x06fc31f4
SYNTHETIC_FORMATS = {1: [b'Count %d', b'HP %d'], 2: [b'Def %d'], 4: [b'Dur [%d/%d]'], 5: [b'Lv %d'],
                     6: [b'Str %d'], 7: [b'Agi %d'], 9: [b'Ene %d'], 11: [b'Magic +%d%%'], 13: [b'Swim', b'Run fast'],
                     101: [b'Speed %d'], 201: [b'(need %d lv)'], 202: [b'(need %d str)'], 203: [b'(need %d agi)'],
                     205: [b'(need %d ene)']}


def c_sprintf(fmt, args):
    """The printf subset the tooltip formats use: flags 0-+ space, width, %d %i %u %s %c %x %%."""
    import re
    out, k = b'', 0
    for m in re.finditer(rb'%%|%([-+ 0#]*)(\d*)([diuscxX])|[^%]+|%', fmt):
        tok = m.group(0)
        if tok == b'%%':
            out += b'%'
        elif m.group(3):
            flags, width, conv = m.group(1).decode(), m.group(2).decode(), m.group(3).decode()
            a = args[k]
            k += 1
            if conv in 'di':
                a = a - (1 << 32) if a & 0x80000000 else a
                piece = ('%' + flags + width + 'd') % a
            elif conv == 'u':
                piece = ('%' + flags + width + 'd') % (a & 0xffffffff)
            elif conv in 'xX':
                piece = ('%' + flags + width + conv) % (a & 0xffffffff)
            elif conv == 'c':
                piece = chr(a & 0xff)
            else:
                piece = None
            out += piece.encode('latin1') if piece is not None else a
        else:
            out += tok
    return out, k


def installed_formats(game_root):
    """type -> list of format strings from the installed itemtooltiptext (local use only)."""
    import subprocess
    import tempfile
    tool = ROOT/'native/build/mu-data'
    table = Path(game_root)/'Data/Local/itemtooltiptext.bmd'
    if not tool.exists() or not table.exists():
        return {}
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)/'t.json'
        subprocess.run([str(tool), 'dump', str(table), '--out', str(out)], check=True, capture_output=True)
        records = json.loads(out.read_text())['data']
    found = {}
    for r in records:
        f = r['fields']
        if f['type'] in FORMAT_TYPES:
            found.setdefault(f['type'], []).append(f['text'].encode('latin1', 'replace'))
    return found


class TtfItem(Structure):
    _fields_ = [('durability', c_uint8), ('max_durability', c_uint8), ('field_3a', c_uint8),
                ('defense', ctypes.c_uint16), ('magic_power', c_int32), ('attack_speed', c_uint8)]


class TtfInputs(Structure):
    _fields_ = [('req_strength', ctypes.c_uint16), ('req_agility', ctypes.c_uint16), ('req_energy', ctypes.c_uint16),
                ('req_level', ctypes.c_uint16), ('special_level_item', c_uint8), ('special_level', c_int32),
                ('hero_level', c_int32), ('hero_strength', ctypes.c_uint16), ('hero_agility', ctypes.c_uint16),
                ('hero_energy', ctypes.c_uint16), ('stat_cut_strength', c_int32), ('stat_cut_agility', c_int32),
                ('socket_defense', c_int32), ('harmony_defense', c_int32), ('kind_a_3', c_uint8), ('kind_b_f', c_uint8),
                ('manager_1c', c_int32)]


def validate_format(client, lib, rng, report, cases, formats):
    lib.mu_tooltip_format.restype = c_int
    lib.mu_tooltip_format.argtypes = [ctypes.c_char_p, ctypes.c_char_p, c_int32, POINTER(TtfItem), c_int32,
                                      POINTER(TtfInputs), c_int32, POINTER(c_int32), POINTER(c_int32)]
    client.prepare((FORMATTER,), FORMAT_STOPS)
    client.common_stubs()
    m = client.machine
    m.uc.mem_map(MODULE_BASE, MODULE_SIZE)
    totals = {'cases': 0, 'by_type': {}, 'red': 0, 'text_bytes': 0}
    for case in range(cases):
        client.reset()
        m.uc.mem_write(MODULE_BASE, b'\0'*MODULE_SIZE)
        type_ = rng.choice(FORMAT_TYPES)
        fmt = rng.choice(formats.get(type_) or SYNTHETIC_FORMATS[type_])
        small = lambda: rng.choice([0, 0, 1, rng.randrange(0, 50), rng.randrange(0, 3000)])  # noqa: E731
        inp = TtfInputs(rng.randrange(0, 2000), rng.randrange(0, 2000), rng.choice([0, rng.randrange(0, 2000)]),
                        rng.randrange(0, 1500), int(rng.random() < 0.1), rng.randrange(0, 1500),
                        rng.randrange(1, 2000), rng.randrange(0, 2500), rng.randrange(0, 2500), rng.randrange(0, 2500),
                        small(), small(), 0, 0, int(rng.random() < 0.4), int(rng.random() < 0.3),
                        rng.choice([-1, -1, 0, 3]))
        item = TtfItem(rng.randrange(256), rng.randrange(256), rng.randrange(256), rng.randrange(0, 2000),
                       rng.randrange(0, 300), rng.randrange(256))
        level = rng.randrange(0, 16)
        threshold = rng.randrange(0, 20)
        socket_flag, socket_value = rng.random() < 0.5, small()
        harm_on, harm_type, h1, h2 = rng.random() < 0.4, rng.choice([1, 3, 3]), small(), small()
        inp.socket_defense = socket_value if (level >= threshold and socket_flag) else 0
        inp.harmony_defense = (h1 + h2) if (harm_on and harm_type == 3) else 0
        # client objects
        record = m.alloc(RECORD_SIZE, define=True)
        m.write(record + 0x266, bytes([item.attack_speed]))
        obj = m.alloc(0x200, define=True)
        m.put32(obj, record)
        m.put32(obj + 0x10, rng.randrange(0, 0x2c00))
        m.write(obj + 0x22, struct.pack('<H', item.defense))
        m.put32(obj + 0x28, item.magic_power)
        m.write(obj + 0x38, bytes([item.durability, item.max_durability, item.field_3a]))
        m.write(obj + 0x70, struct.pack('<H', threshold))
        hero = m.alloc(0x200, define=True)
        m.write(hero + 0x18a, struct.pack('<HH', inp.hero_strength, inp.hero_agility))
        m.write(hero + 0x190, struct.pack('<H', inp.hero_energy))
        m.put32(HERO, hero)
        m.put32(SOCKET_MANAGER, m.alloc(0x10, define=True))
        mgr = m.alloc(0x40, define=True)
        m.put32(mgr + 0x1c, inp.manager_1c)
        for name, address in GETTERS.items():
            m.stub(address, lambda mm, v=getattr(inp, name): v, 0)
        m.stub(0xf1425b, lambda mm: inp.special_level_item, 4)
        m.stub(0xf142b1, lambda mm: inp.special_level, 4)
        m.stub(0xa00367, lambda mm: inp.hero_level, 0)

        def cuts(mm):
            a, b, lvl, it = mm.args(4)
            mm.put32(a, inp.stat_cut_strength)
            mm.put32(b, inp.stat_cut_agility)
            return 0
        m.stub(0xf13774, cuts, 0x10)

        def socket(mm):
            info, it, kind = mm.args(3)
            mm.write(info + 0x34, bytes([int(socket_flag)]))
            mm.put32(info + 0x24, socket_value)
            return info
        m.stub(0x11df8b9, socket, 0xc)
        harmony = [h1, h2]
        m.stub(0xcd248c, lambda mm: int(harm_on), 4)
        m.stub(0xcd25ec, lambda mm: harm_type, 0)
        m.stub(0xcbc335, lambda mm: harmony[0 if mm.args(2)[1] == 2 else 1], 8)
        m.stub(0x95fc2e, lambda mm: int(inp.kind_a_3) if mm.args(1)[0] == 3 else mm.fail('kind A probe'), 4)
        m.stub(0x987982, lambda mm: int(inp.kind_b_f) if mm.args(1)[0] == 0xf else mm.fail('kind B probe'), 4)

        def sprintf(mm):
            esp_args = mm.args(8)
            buf, fmtp = esp_args[:2]
            text, used = c_sprintf(read_cstr(mm, fmtp), esp_args[2:])
            if len(text) >= 0x100:
                return mm.fail('sprintf past the buffer')
            mm.write(buf, text + b'\0')
            return len(text)
        m.stub(SPRINTF, sprintf, 0)
        line = rng.randrange(1, 20)
        color0 = rng.randrange(0, 22)
        prev = rng.randrange(0, 22)
        m.put32(TEXT_COLOR + 4*(line - 1), prev)
        m.put32(TEXT_COLOR + 4*line, color0)
        fmtp = m.alloc(len(fmt) + 1, define=True)
        m.write(fmtp, fmt + b'\0')
        colorp = m.alloc(4, define=True)
        m.put32(colorp, color0)
        ret = m.alloc(0x18, define=True)
        m.call(FORMATTER, (ret, fmtp, line, colorp, type_, obj, level, 0xffffffff), ecx=mgr)
        got = (read_string(m, ret), m.u32(colorp), m.u32(TEXT_COLOR + 4*(line - 1)), m.u32(TEXT_COLOR + 4*line))
        out = ctypes.create_string_buffer(0x100)
        color = c_int32(color0)
        tc = (c_int32*32)()
        tc[line - 1], tc[line] = prev, color0
        rc = lib.mu_tooltip_format(out, fmt, type_, ctypes.byref(item), level, ctypes.byref(inp), line,
                                   ctypes.byref(color), tc)
        want = (out.value, color.value & 0xffffffff, tc[line - 1] & 0xffffffff, tc[line] & 0xffffffff)
        if rc != 0 or got != want:
            raise cm.CaseError(f'format case {case} type {type_}: client {got} authored {want}')
        totals['cases'] += 1
        totals['by_type'][type_] = totals['by_type'].get(type_, 0) + 1
        totals['red'] += int(want[1] == 2 and color0 != 2)
        totals['text_bytes'] += len(want[0])
    report['format'] = totals
    return totals


# ==========================================================================

def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--text', default=os.environ.get('MU_CLIENT_TEXT', str(DEFAULT_TEXT)))
    parser.add_argument('--data', default=os.environ.get('MU_IMAGE_DATA', str(DEFAULT_DATA)))
    parser.add_argument('--sections', default='grid')
    parser.add_argument('--cases', type=int, default=40)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--library')
    parser.add_argument('--game-root', default=os.environ.get('MU_GAME_ROOT'),
                        help='format section: use the installed itemtooltiptext formats (never written out)')
    parser.add_argument('--output')
    args = parser.parse_args()
    for path, digest in ((args.text, TEXT_SHA256), (args.data, DATA_SHA256)):
        if sha256_file(path) != digest:
            raise SystemExit(f'{path}: unexpected SHA-256')
    text, data = Path(args.text).read_bytes(), Path(args.data).read_bytes()
    lib = library(args.library)
    rng = random.Random(args.seed)
    report = {'text_sha256': TEXT_SHA256, 'data_sha256': DATA_SHA256, 'seed': args.seed}
    started = time.time()
    sections = args.sections.split(',')
    if 'grid' in sections:
        totals = validate_grid(Client(text, data), grid_lib(lib), rng, report, args.cases)
        print('grid', json.dumps(totals))
    if 'slots' in sections:
        totals = validate_slots(Client(text, data), slot_lib(grid_lib(lib)), rng, report, args.cases)
        print('slots', json.dumps(totals))
    if 'pass' in sections:
        cm.SLOTS.update(EXTRA_SLOTS)
        totals = validate_pass(Client(text, data), lib, rng, report, args.cases)
        print('pass', json.dumps(totals))
    if 'html' in sections:
        totals = validate_html(Client(text, data), html_lib(lib), rng, report, args.cases)
        print('html', json.dumps(totals))
    if 'format' in sections:
        formats = installed_formats(args.game_root) if args.game_root else {}
        totals = validate_format(Client(text, data), lib, rng, report, args.cases, formats)
        totals['formats'] = 'installed' if formats else 'synthetic'
        print('format', json.dumps(totals))
    if 'item3d' in sections:
        totals = validate_item3d(Client(text, data), slot_lib(grid_lib(lib)), rng, report, args.cases)
        print('item3d', json.dumps(totals))
    report['seconds'] = round(time.time() - started, 1)
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2) + '\n')
    print('all cases match', f'({report["seconds"]} s)')


if __name__ == '__main__':
    main()
