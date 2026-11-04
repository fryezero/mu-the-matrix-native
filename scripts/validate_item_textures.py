#!/usr/bin/env python3
"""RENDER-ITEMS-TEX-001: item model texture loading and the item bitmap registrations against pinned instructions.

Families (docs/research/client-render-items-tex.md):
  item_open      the item model loader 0x00cd558e(index, folder, file) runs as client code on synthetic models: the
                 BMD open 0x012b3812 installs the mesh names, LoadImage 0x00c97689 answers from a synthetic file set,
                 the name map 0x00c97e0c from a synthetic cache, 0x00c97730 records; the CRT strcmp, strncmp,
                 _strnicmp and memset run as client code, sprintf (%s/%d), _splitpath and the std::string members
                 are service stubs. The C mu_it_open must make the same requests in the same order and store the same
                 IndexTexture, TextureType and model +0xa6 values; the message counts as a request.
  startup_names  the generated name list (native/core/mu_startup_bitmaps.inc): each startup LoadBitmap site with an
                 immediate .jpg/.tga path runs from its first push and must load exactly the listed path, filter and
                 wrap (RENDER-ITEMS-TEX-002: a name-map hit keeps them).
  part_skin      RENDER-ITEMS-TEX-002: RenderCharacter's part-model store 0x0136a4a9..0x0136a4c3 for all 256 class
                 bytes (0x0139d6a2 and its callees as client code): model +0xa4 equals mu_it_part_skin.
  skin_bitmap    the mesh draw's skin substitution 0x012b8e78..0x012b9471 for every +0xa4 byte and twelve
                 IndexTextures: the index it binds equals mu_it_skin_bitmap.
  registrations  RENDER-ITEMS-TEX-003: the item bitmap table (native/core/mu_item_bitmaps.inc) is every LoadBitmap
                 0x0185baac call of the startup routines (those the startup loader 0x0182049e reaches by direct
                 calls, and the startup opener). Each immediate site runs from its first push; the five computed
                 runs (loops whose path is sprintf'd and whose index is base + i) run as client code with sprintf,
                 OpenTexture and LoadBitmap as stubs. The calls (index, path, filter, wrap, flags 1/0), in table
                 order, must equal the table; every startup LoadBitmap site must be covered.
  reregister     RENDER-ITEMS-TEX-003: 0x00c97730(index, path, filter, wrap), the step LoadBitmap ends in, runs as
                 client code (_stricmp, memset and 0x00c99025 as client code; the std::map members, _splitpath, the
                 string members, the unload 0x00c97916 and the jpg/tga loaders are stubs) on synthetic slot states
                 and call sequences, against mu_it_register: the same unload/load requests, return value and slot.
                 Then every table index replays its calls through 0x00c97730 from an empty slot; the bitmap it holds
                 must equal mu_it_registration over the table.

--emit-table PATH writes the item bitmap table: every startup LoadBitmap call, sorted by index (stable: the calls of
an index in the client's call order), with its site, its routine and whether the startup loader reaches it.
--emit-names PATH writes the startup name list. --mutations compiles planted mistakes that a family must catch. Inputs: the pinned text, data and section-3
captures (scripts/pins.py; section 3 holds the CRT locale state _strnicmp reads).
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile

import actor_machine as am
import pins
import validate_objects as vo

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
TABLE = ROOT / 'native/core/mu_item_bitmaps.inc'

ITEM_OPEN, ITEM_OPEN_END = 0x00cd558e, 0x00cd5c91
NEW, CTOR, BMD_OPEN = 0x0191ba7b, 0x00cd877f, 0x012b3812
LOAD, FIND, REUSE = 0x00c97689, 0x00c97e0c, 0x00c97730
STR_CTOR, STR_DTOR, STR_SUBSTR, STR_SIZE, STR_REPLACE, STR_CSTR = (0x0094997e, 0x008e83a0, 0x00a92460,
                                                                     0x00950d4d, 0x00971de9, 0x008e7940)
FORMAT, SPLITPATH, LOG, MESSAGE_EXIT = 0x009619dd, 0x0198b9e3, 0x01206598, 0x0120f2ee
LOAD_BITMAP, STARTUP_LOADER = 0x0185baac, 0x0182049e
MESSAGE_BOX, WINDOW = 0x688cd550, 0x06fc9c94   # the import [0x01a7c830] holds; the window handle global
LOCALE_CHANGED, SSE2_FLAG = 0x0bdcf8ec, 0x0bdcb284
SECTION3_BASE, SECTION3_INIT = 0x01ced000, 0x20000
# RENDER-ITEMS-TEX-002: RenderCharacter's part-model store of the wearer skin index (model = GetModel(slot type) at
# [ebp-0x2ec], character at [ebp+8]) and the mesh draw's skin substitution (model at [ebp-0x10], IndexTexture at
# [ebp-0x1c]; 0x012b9471 continues, 0x012bb34b returns without drawing).
PART_SKIN, PART_SKIN_END = 0x0136a4a9, 0x0136a4c3
SKIN_SWITCH, SKIN_SWITCH_END, SKIN_SWITCH_RETURN = 0x012b8e78, 0x012b9471, 0x012bb34b
BODIES = {'item_open': (ITEM_OPEN, ITEM_OPEN_END), 'get_model': (0x00eaa8cf, 0x00eaaa3e),
          'part_skin': (PART_SKIN, PART_SKIN_END), 'skin_switch': (SKIN_SWITCH, SKIN_SWITCH_END)}
WEARER_MODEL, WEARER_CHARACTER = 0x44000000, 0x44001000

MODEL, NAMES, INDEX, TYPES, ENTRY, HEAP, ARGS = (0x42000000, 0x42001000, 0x42002000, 0x42003000, 0x42004000,
                                                0x42010000, 0x42008000)

LOAD_FN = C.CFUNCTYPE(C.c_int32, C.c_void_p, C.c_char_p, C.c_uint32, C.c_uint32)
FIND_FN = C.CFUNCTYPE(C.c_int32, C.c_void_p, C.c_char_p, C.POINTER(C.c_char_p))
REUSE_FN = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.c_char_p, C.c_uint32, C.c_uint32)
ERROR_FN = C.CFUNCTYPE(None, C.c_void_p, C.c_char_p)


class Host(C.Structure):
    _fields_ = [('context', C.c_void_p), ('load', LOAD_FN), ('find', FIND_FN), ('reuse', REUSE_FN),
                ('error', ERROR_FN)]


def bind(lib):
    lib.mu_it_part_skin.argtypes = [C.c_uint8]
    lib.mu_it_part_skin.restype = C.c_int8
    lib.mu_it_skin_bitmap.argtypes = [C.c_int32, C.c_int8]
    lib.mu_it_skin_bitmap.restype = C.c_int32
    lib.mu_it_open.argtypes = [C.POINTER(Host), C.c_char_p, C.c_char_p, C.POINTER(C.c_int32), C.POINTER(C.c_int),
                               C.POINTER(C.c_int)]
    lib.mu_it_open.restype = C.c_int32
    lib.mu_it_register.argtypes = [C.POINTER(Bitmap), C.c_char_p, C.c_uint32, C.c_uint32]
    lib.mu_it_register.restype = C.c_int
    lib.mu_it_registration.argtypes = [C.POINTER(Call), C.c_size_t, C.c_int32, C.POINTER(Bitmap)]
    lib.mu_it_registration.restype = C.c_int
    return lib


class Call(C.Structure):   # mu_it_call
    _fields_ = [('index', C.c_int32), ('path', C.c_char_p), ('filter', C.c_uint32), ('wrap', C.c_uint32)]


class Bitmap(C.Structure):   # mu_it_bitmap
    _fields_ = [('path', C.c_char_p), ('filter', C.c_uint32), ('wrap', C.c_uint32), ('refs', C.c_uint8)]


class Tally:
    def __init__(self, name):
        self.name, self.cases, self.equal, self.stopped, self.examples, self.cover = name, 0, 0, 0, [], {}

    def add(self, ok, detail=None, stopped=None):
        self.cases += 1
        if stopped is not None:
            self.stopped += 1
        elif ok:
            self.equal += 1
            return
        if len(self.examples) < 6:
            self.examples.append({'stopped': stopped, **(detail or {})} if stopped else (detail or {}))

    def count(self, label, n=1):
        self.cover[label] = self.cover.get(label, 0) + n

    def report(self):
        return {'cases': self.cases, 'equal': self.equal, 'stopped': self.stopped,
                'mismatch_count': self.cases - self.equal - self.stopped, 'examples': self.examples,
                'coverage': self.cover}


# ---------------------------------------------------------------- 0x00cd558e under Unicorn
PREFIXED = ['nude_body.jpg', 'NUDE_x.tga', 'Nude_a.jpg', 'nudeA.jpg', 'Nudes.tga', 'cottonx.jpg', 'skinA.jpg',
            'hairA.jpg', 'HQskin.jpg', 'cotton_a.jpg', 'Cotton_b.tga', 'cotton2_c.jpg',
            'COTTON2_d.jpg', 'cotton2x.jpg', 'skin_01.jpg', 'SKIN_a.jpg', 'skin.jpg', 'level1.jpg', 'LEVEL_a.jpg',
            'levex.jpg', 'hid', 'Hide.jpg', 'hidden.tga', 'hair_r.jpg', 'HAIR_a.jpg', 'hair.jpg', 'field_wood.jpg',
            'field_abcd', 'field_ab.jpgx', 'Field_wood.jpg', 'field.jpg', 'HQskin_a.jpg', 'hqskin_b.jpg',
            'HQskin3a.jpg', 'HQskin2.tga', 'hqSKIN.jpg', 'HQlevel1.jpg', 'HQlevelx.jpg', 'HQhair_r.jpg',
            'HQhairA.jpg', 'hqhai.jpg', 'nude_skin_1.jpg', 'cotton_hair_.jpg', 'cotton2_HQskin3.jpg']
STEMS = ['Sword01', 'Item1161_Blue', 'Gra3', 'black_gold_crom05', 'x', 'tree.a', 'Axes02', 'medicine1',
         'longname_texture_0123456789ab']
EXTS = ['.jpg', '.JPG', '.tga', '.TGA', '.bmp', '.ozj', '', '.', '.j', '.JpG']
FOLDERS = ['Data\\Item\\', 'Data\\Player\\', 'Data\\Item\\xmas\\', 'Data\\Item\\partCharge1\\', 'Data\\',
           'data\\item\\']
FILES = ['Sword01.bmd', 'ArmorMale161.bmd', 'Wing01.bmd']


def tga_variant(name):
    rest = name[6:]
    return rest[:-4] + '.tga'


def synthetic_case(g):
    names = []
    for _ in range(g.choice([0, 1, 1, 2, 3, 4, 6])):
        names.append(g.choice(PREFIXED) if g.random() < 0.4 else g.choice(STEMS) + g.choice(EXTS))
    folder = g.choice(FOLDERS)
    files = {}
    for n in names:
        paths = [f'{folder}Texture\\{n}']
        if n.startswith('field_') and len(n) >= 10:
            paths.append(f'{folder}Texture\\{tga_variant(n)}')
        for p in paths:
            if g.random() < 0.45:
                files[p] = g.choice([0, 1, 0x9000 + g.randrange(0x400)])
    cache = {}
    for n in names:
        if g.random() < 0.35:
            cache[n] = (g.choice([0, 0x8800 + g.randrange(0x400)]), 'Data\\Skill\\' + n)
    return {'names': names, 'folder': folder, 'file': g.choice(FILES), 'files': files, 'cache': cache,
            'model_index': 0xae6 + g.randrange(0, 0x2f00)}


class Strings:
    """std::string objects as the stubs see them: dword 0 of the object points to a heap copy."""

    def __init__(self, m):
        self.m, self.next, self.value = m, HEAP, {}

    def put(self, this, text):
        raw = text.encode('latin1') + b'\0'
        at = self.next
        self.next += (len(raw) + 15) & ~15
        self.m.uc.mem_write(at, raw.ljust((len(raw) + 15) & ~15, b'\0'))
        self.m.uc.mem_write(this, struct.pack('<I', at) + bytes(0x14))
        self.value[this] = text

    def get(self, this):
        return self.value[this]


def run_client(machine, case, sec3):
    events = []
    m = machine
    strings = Strings(m)
    names = bytearray(0x1000)
    for i, n in enumerate(case['names']):
        raw = n.encode('latin1')[:31]
        names[i * 32:i * 32 + len(raw)] = raw
    count = len(case['names'])

    def ecx():
        return m.uc.reg_read(m.x86.UC_X86_REG_ECX)

    def bmd_open(mm):
        if (mm.cstring(mm.argument(0)), mm.cstring(mm.argument(1)), mm.argument(2)) != \
                (case['folder'], case['file'], 1):
            raise ValueError('BMD open arguments')
        mm.uc.mem_write(MODEL + 0x24, struct.pack('<h', count))
        mm.uc.mem_write(MODEL + 0x34, struct.pack('<III', NAMES, INDEX, TYPES))
        return 1, 0xc

    def str_ctor(mm):
        strings.put(ecx(), mm.cstring(mm.argument(0), 300))
        return ecx(), 4

    def substr(mm):
        out, pos, n = mm.argument(0), mm.argument(1), mm.argument(2)
        text = strings.get(ecx())
        if pos > len(text):
            raise ValueError('substr out_of_range')
        strings.put(out, text[pos:] if n == 0xffffffff else text[pos:pos + n])
        return out, 0xc

    def size(mm):
        return len(strings.get(ecx())), 0

    def replace(mm):
        pos, n, s = mm.argument(0), mm.argument(1), mm.cstring(mm.argument(2))
        text = strings.get(ecx())
        if pos > len(text):
            raise ValueError('replace out_of_range')
        strings.put(ecx(), text[:pos] + s + text[pos + n:])
        return ecx(), 0xc

    def c_str(mm):
        return mm.read32(ecx()), 0

    def fmt(mm):
        out, form = mm.argument(0), mm.cstring(mm.argument(1))
        values, k = [], 2

        def piece(match):
            nonlocal k
            spec = match.group(1)
            value = mm.argument(k)
            k += 1
            if spec == 's':
                return mm.cstring(value, 300)
            if spec == 'd':
                return str(struct.unpack('<i', struct.pack('<I', value))[0])
            raise ValueError('format ' + spec)
        text = re.sub(r'%([sd])', piece, form)
        if len(text) >= 256:
            raise ValueError('sprintf overflow')
        mm.uc.mem_write(out, text.encode('latin1') + b'\0')
        values.append(text)
        return len(text)

    def splitpath(mm):
        path, drive, directory, fname, ext = (mm.argument(k) for k in range(5))
        if drive or directory or fname:
            raise ValueError('unmodelled _splitpath outputs')
        name = mm.cstring(path, 300)
        base = max(name.rfind('\\'), name.rfind('/'))
        dot = name.rfind('.')
        out = name[dot:] if dot > base else ''
        mm.uc.mem_write(ext, out.encode('latin1')[:255] + b'\0')
        return 0

    def load(mm):
        path = strings.get(mm.argument(0))
        events.append(('load', path, mm.argument(1), mm.argument(2)))
        return case['files'].get(path, 0x7530), 0xc

    def find(mm):
        name = strings.get(mm.argument(0))
        events.append(('find', name))
        hit = case['cache'].get(name)
        if not hit:
            return 0, 4
        index, path = hit
        mm.write(ENTRY, struct.pack('<I', index) + path.encode('latin1')[:250] + b'\0')
        return ENTRY, 4

    def reuse(mm):
        events.append(('reuse', mm.argument(0), strings.get(mm.argument(1)), mm.argument(2), mm.argument(3)))
        return 1, 0x10

    def log(mm):
        events.append(('error', mm.cstring(mm.argument(2), 400)))
        return 0

    stubs = {NEW: lambda mm: MODEL, CTOR: lambda mm: (ecx(), 0), BMD_OPEN: bmd_open, STR_CTOR: str_ctor,
             STR_DTOR: lambda mm: (0, 0), STR_SUBSTR: substr, STR_SIZE: size, STR_REPLACE: replace, STR_CSTR: c_str,
             FORMAT: fmt, SPLITPATH: splitpath, LOAD: load, FIND: find, REUSE: reuse, LOG: log,
             MESSAGE_BOX: lambda mm: (0, 0x10), MESSAGE_EXIT: lambda mm: 0}
    if not getattr(machine, 'message_box_page', False):   # the MessageBoxA import [0x01a7c830] is outside the image
        from unicorn import UC_PROT_ALL
        machine.uc.mem_map(MESSAGE_BOX & ~0xfff, 0x1000, UC_PROT_ALL)
        machine.uc.mem_write(MESSAGE_BOX & ~0xfff, b'\xcc' * 0x1000)
        machine.message_box_page = True
    pad = lambda s: s.encode('latin1').ljust(0x110, b'\0')   # strcmp reads whole dwords
    regions = [am.undefined_region('model', MODEL, 0xd0),
               am.defined_region('names', NAMES, bytes(names), writable=False),
               am.undefined_region('index', INDEX, 0x100), am.defined_region('types', TYPES, b'\xa5' * 0x100),   # zeroed with AND (a read)
               am.undefined_region('entry', ENTRY, 0x400),
               am.defined_region('args', ARGS, pad(case['folder']) + pad(case['file']), writable=False),
               am.defined_region('heap', HEAP, bytes(0x10000)),
               am.defined_region('window', WINDOW, bytes(4), writable=False),
               am.defined_region('locale-changed', LOCALE_CHANGED, bytes(4), writable=False),
               am.defined_region('sse2-flag', SSE2_FLAG, bytes(4), writable=False),
               am.defined_region('section3-init', SECTION3_BASE, sec3[:SECTION3_INIT], writable=False)]
    result = machine.execute(ITEM_OPEN, [case['model_index'], ARGS, ARGS + 0x110], regions, stubs,
                             ecx=0x43000000, cleanup=0xc)
    stop = None if result['ok'] else {'stopped': result['stopped'], 'error': result['error'],
                                      'checks': {k: v for k, v in result['checks'].items() if not v}}
    r = result['regions']
    indices = list(struct.unpack_from(f'<{count}i', r['index'])) if count else []
    types = list(struct.unpack_from(f'<{count}i', r['types'])) if count else []
    field = r['model'][0xa6]
    return events, indices, types, field, result['eax'] == MODEL, stop


def run_c(lib, case):
    events = []

    def load(ctx, path, filt, wrap):
        p = path.decode('latin1')
        events.append(('load', p, filt, wrap))
        return case['files'].get(p, 0x7530)
    keep = []

    def find(ctx, name, out):
        n = name.decode('latin1')
        events.append(('find', n))
        hit = case['cache'].get(n)
        if not hit:
            return -1
        buf = C.create_string_buffer(hit[1].encode('latin1'))
        keep.append(buf)
        out[0] = C.cast(buf, C.c_char_p)
        return hit[0]

    def reuse(ctx, index, path, filt, wrap):
        events.append(('reuse', index, path.decode('latin1'), filt, wrap))

    def error(ctx, path):
        events.append(('error', f'ItemTextureFile does not exist : [{case["file"]} - {path.decode("latin1")}]'))
    host = Host(None, LOAD_FN(load), FIND_FN(find), REUSE_FN(reuse), ERROR_FN(error))
    indices, types, field = [], [], C.c_int(0)
    for n in case['names']:
        t, step = C.c_int32(), C.c_int()
        indices.append(lib.mu_it_open(C.byref(host), case['folder'].encode('latin1'), n.encode('latin1')[:31],
                                      C.byref(t), C.byref(field), C.byref(step)))
        types.append(t.value)
    return events, indices, types, field.value


def family_open(machine, lib, cases, sec3, seed='items-tex-open'):
    g = random.Random(seed)
    tally = Tally('item_open')
    for n in range(cases):
        case = synthetic_case(g)
        events, indices, types, field, returned, stop = run_client(machine, case, sec3)
        c_events, c_indices, c_types, c_field = run_c(lib, case)
        tally.add(stop is None and returned and (events, indices, types, field) ==
                  (c_events, c_indices, c_types, c_field),
                  {'case': n, 'names': case['names'], 'folder': case['folder'], 'client': events[:6],
                   'c': c_events[:6], 'indices': (indices, c_indices), 'types': (types, c_types),
                   'field': (field, c_field)}, stop)
        for e in events:
            tally.count(e[0])
        tally.count('meshes', len(indices))
        tally.count('specials', sum(1 for v in indices if v in (0x7725, 0x791a, 0x7776, 0x7869, 0x7818, 0x77c7,
                                                                  0x78ba)))
        tally.count('typed meshes', sum(1 for v in types if v))
        tally.count('field models', field)
    return tally.report()


# ---------------------------------------------------------------- the wearer skin (RENDER-ITEMS-TEX-002)
def fragment(machine, start, ends, regions, slots, arguments=(), frame=0x1000):
    """Runs client code from start inside a built EBP frame until one of ends; returns (end reached, stop)."""
    reached = []

    def end(address):
        def stub(mm):
            reached.append(address)
            return 0
        return stub
    slots = dict(slots)
    slots[-frame] = am.SENTINEL   # [esp] at every end: the stub returns there
    r = machine.execute(start, list(arguments), regions, {a: end(a) for a in ends}, frame=(frame, slots))
    stop = None if am_ok(r) and len(reached) == 1 else {'stopped': r['stopped'], 'error': r['error'],
                                                       'ends': [hex(a) for a in reached]}
    return (reached[0] if reached else None), r, stop


def family_part_skin(machine, lib):
    """0x0136a4a9..0x0136a4c3 for every class byte (0x0139d6a2, 0x0095f5cc and 0x0139cb8a as client code): the byte
    written to model +0xa4 equals mu_it_part_skin."""
    tally = Tally('part_skin')
    for class_byte in range(256):
        character = bytearray(0x400)
        character[0x12] = class_byte
        regions = [am.defined_region('model', WEARER_MODEL, b'\x5a' * 0xd0),
                   am.defined_region('character', WEARER_CHARACTER, bytes(character), writable=False)]
        _, r, stop = fragment(machine, PART_SKIN, [PART_SKIN_END], regions, {-0x2ec: WEARER_MODEL},
                              arguments=[WEARER_CHARACTER])
        client = struct.unpack('<b', r['regions']['model'][0xa4:0xa5])[0]
        native = lib.mu_it_part_skin(class_byte)
        tally.add(client == native, {'class': hex(class_byte), 'client': client, 'c': native}, stop)
        tally.count(f'tier {1 + (class_byte >> 4).bit_length() if class_byte >> 4 else 1}')
    return tally.report()


SKIN_INDICES = [0x7725, 0x7776, 0x77c7, 0x7818, 0x7869, 0x78ba,   # shifted
                0x7724, 0x7726, 0x7777, 0x78b9, 0x791a, 0x7530]   # unchanged (0x791a returns)


def family_skin_bitmap(machine, lib):
    """The mesh draw's substitution 0x012b8e78..0x012b9471 for every +0xa4 byte and twelve IndexTextures (model
    +0xa5 = +0xca = 0): the index it binds equals mu_it_skin_bitmap."""
    tally = Tally('skin_bitmap')
    ebp = am.ENTRY_ESP - 4
    for shift in range(256):
        for index in SKIN_INDICES:
            model = bytearray(0xd0)
            model[0xa4] = shift
            regions = [am.defined_region('model', WEARER_MODEL, bytes(model), writable=False)]
            seen = {}

            def capture(address):
                def stub(mm):
                    seen['index'] = struct.unpack('<i', bytes(mm.uc.mem_read(ebp - 0x1c, 4)))[0]
                    seen['end'] = address
                    return 0
                return stub
            slots = {-0x10: WEARER_MODEL, -0x1c: index, -0x1000: am.SENTINEL}
            r = machine.execute(SKIN_SWITCH, [], regions,
                                {a: capture(a) for a in (SKIN_SWITCH_END, SKIN_SWITCH_RETURN)},
                                frame=(0x1000, slots))
            stop = None if am_ok(r) and 'end' in seen else {'stopped': r['stopped'], 'error': r['error']}
            signed = shift - 256 if shift >= 128 else shift
            native = lib.mu_it_skin_bitmap(index, signed)
            tally.add(seen.get('index') == native,
                      {'index': hex(index), 'shift': shift, 'client': seen.get('index'), 'c': native}, stop)
            tally.count('returns' if seen.get('end') == SKIN_SWITCH_RETURN else 'continues')
    return tally.report()


# ---------------------------------------------------------------- LoadBitmap registrations
def scan_calls(text, target):
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    sites = []
    for match in re.finditer(b'\xe8', text):
        o = match.start()
        if o + 5 > len(text):
            break
        if am.TEXT_BASE + o + 5 + struct.unpack_from('<i', text, o + 1)[0] == target:
            sites.append(am.TEXT_BASE + o)
    out = []
    for site in sites:
        best = None
        for back in range(12, 90):
            ins = list(md.disasm(text[site - back - am.TEXT_BASE:site + 5 - am.TEXT_BASE], site - back))
            if ins and ins[-1].address == site:
                best = ins
        if not best:
            continue
        pushes = [i for i in best if i.mnemonic == 'push'][-6:]
        if len(pushes) < 6:
            continue
        args = [p.operands[0].imm & 0xffffffff if p.operands[0].type == capstone.x86.X86_OP_IMM else None
                for p in reversed(pushes)]
        out.append((site, pushes[0].address, args))
    return out


def string_at(data, address):
    if not am.DATA_BASE <= address < am.DATA_BASE + len(data):
        return None
    raw = data[address - am.DATA_BASE:address - am.DATA_BASE + 260].split(b'\0')[0]
    return raw.decode('latin1') if raw and all(32 <= c < 127 for c in raw) else None


def routine_of(text, address):
    return am.TEXT_BASE + text.rfind(b'\x55\x8b\xec', 0, address - am.TEXT_BASE)


def startup_reach(text, start=STARTUP_LOADER, limit=200000):
    """Routines the startup loader reaches by direct calls (static). A routine ends at a ret followed by int3
    padding or the next standard prologue."""
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    seen, todo = set(), [start]
    while todo and len(seen) < limit:
        f = todo.pop()
        if f in seen or not am.TEXT_BASE <= f < am.TEXT_BASE + len(text):
            continue
        seen.add(f)
        offset = f - am.TEXT_BASE
        for i in md.disasm(text[offset:offset + 0x20000], f):
            if i.mnemonic == 'call' and i.op_str.startswith('0x'):
                todo.append(int(i.op_str, 16))
            if i.mnemonic == 'ret':
                after = i.address + i.size - am.TEXT_BASE
                if text[after] == 0xcc or text[after:after + 3] == b'\x55\x8b\xec':
                    break
    return seen


# The startup opener has no direct caller in the restored text (RENDER-WORLDS-G2: the routine before the world
# pass; its models are in the map when a world opens).
STARTUP_OPENER = 0x01832af3


def c_string(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


# RENDER-ITEMS-TEX-003: the startup LoadBitmap calls whose index or path is computed. Each run is a loop (or two
# sprintf'd constants) inside a startup routine's EBP frame, executed from its first instruction to the first one
# after it: (start, end, routine).
COMPUTED_RUNS = [
    (0x01825019, 0x0182506d, 0x0182049e),   # 0x83d7 + i, "Effect\ad00%d.jpg" (i + 1), i = 0..5
    (0x0182c344, 0x0182c4ec, 0x0182bb43),   # 0x7935 + i / 0x793e + i, "Player\InvenArmorMale%d.tga" / Pants (i + 40),
                                            # i = 0..5, then 0x7946/0x7947 (succubus files, sprintf without arguments)
    (0x018327d3, 0x01832825, 0x0183220e),   # 0x8300 + i, "Item\texture\fire_sq_%05d.jpg" (i), i = 0..11
    (0x01835dd8, 0x01835e26, STARTUP_OPENER),   # 0x8100 + i, "Effect\xsuper000%d.jpg" (i + 1), i = 0..5
]
SPRINTF, OPEN_TEXTURE, ACCESS_MODEL = 0x009619dd, 0x0181fbe9, 0x018202b4


def c_format(form, values):
    """sprintf's %d / %0Nd / %s as the computed runs use them."""
    k = 0

    def piece(match):
        nonlocal k
        value = values[k]
        k += 1
        if match.group(2) == 's':
            return value
        return f'%{match.group(1)}d' % struct.unpack('<i', struct.pack('<I', value))[0]
    return re.sub(r'%(0?\d*)([ds])', piece, form)


def run_computed(machine, start, end):
    """One computed run as client code; returns (LoadBitmap calls [(site, path, index, filter, wrap, f5, f6)], stop)."""
    calls = []

    def sprintf(mm):
        out, form = mm.argument(0), mm.cstring(mm.argument(1))
        n = len(re.findall(r'%0?\d*[ds]', form))
        values = [mm.argument(2 + i) for i in range(n)]
        values = [mm.cstring(v) if f == 's' else v for v, f in zip(values, re.findall(r'%0?\d*([ds])', form))]
        text = c_format(form, values)
        mm.uc.mem_write(out, text.encode('latin1') + b'\0')
        return len(text)

    def load_bitmap(mm):
        ret = mm.read32(mm.uc.reg_read(mm.x86.UC_X86_REG_ESP))
        calls.append((ret - 5, mm.cstring(mm.argument(0)), *[mm.argument(i) for i in range(1, 6)]))
        return 1
    reached = []

    def stop_at(mm):
        reached.append(end)
        return 0
    stubs = {SPRINTF: sprintf, LOAD_BITMAP: load_bitmap, OPEN_TEXTURE: lambda mm: 0, ACCESS_MODEL: lambda mm: 0,
             end: stop_at}
    r = machine.execute(start, [], [], stubs, frame=(0x1000, {-0x1000: am.SENTINEL}))
    stop = None if am_ok(r) and reached == [end] else {'stopped': r['stopped'], 'error': r['error'],
                                                      'run': hex(start)}
    return calls, stop


def startup_calls(machine, text, data):
    """Every LoadBitmap call of the startup routines, as client code: each immediate site from its first push, each
    computed run whole. Returns (calls, stops, uncovered sites); a call is a dict with the call's index, path,
    filter, wrap, flags, site, routine and order (the client's call order inside its routine)."""
    reach = startup_reach(text)
    calls, stops, sites = [], [], set()
    for site, first, args in scan_calls(text, LOAD_BITMAP):
        routine = routine_of(text, site)
        if routine not in reach and routine != STARTUP_OPENER:
            continue
        sites.add(site)
        if args[1] is None or args[0] is None or not string_at(data, args[0]):
            continue   # a computed run
        got = []

        def load(mm):
            got.append([mm.cstring(mm.argument(0)), *[mm.argument(i) for i in range(1, 6)]])
            return 1
        r = machine.execute(first, [], [], {LOAD_BITMAP: load, site + 8: lambda mm: 0})
        if not am_ok(r) or len(got) != 1:
            stops.append({'site': hex(site), 'stopped': r['stopped'], 'error': r['error']})
            continue
        path, index, filt, wrap, f5, f6 = got[0]
        calls.append({'index': index, 'path': path, 'filter': filt, 'wrap': wrap, 'flags': (f5, f6), 'site': site,
                      'routine': routine, 'order': (site, 0), 'run': None})
    for start, end, routine in COMPUTED_RUNS:
        got, stop = run_computed(machine, start, end)
        if stop:
            stops.append(stop)
        for k, (site, path, index, filt, wrap, f5, f6) in enumerate(got):
            calls.append({'index': index, 'path': path, 'filter': filt, 'wrap': wrap, 'flags': (f5, f6),
                          'site': site, 'routine': routine, 'order': (start, k), 'run': start})
    covered = {c['site'] for c in calls}
    calls.sort(key=lambda c: (c['index'], c['order']))
    return calls, stops, sorted(sites - covered)


def emit_table(path, machine, text, data):
    calls, stops, uncovered = startup_calls(machine, text, data)
    if stops or uncovered:
        raise SystemExit(f'startup LoadBitmap calls not reproduced: {stops[:4]} uncovered {uncovered[:8]}')
    by_index = {}
    for c in calls:
        by_index.setdefault(c['index'], []).append(c)
    for index, group in by_index.items():   # the call order is only known inside one routine
        if len(group) > 1 and len({c['routine'] for c in group}) > 1:
            raise SystemExit(f'index 0x{index:04x}: calls in several startup routines')
    reach = startup_reach(text)
    lines = ['/* Generated by scripts/validate_item_textures.py --emit-table: every LoadBitmap 0x0185baac call of the',
             ' * startup routines (those the startup loader 0x0182049e reaches by direct calls, and the startup opener',
             ' * 0x01832af3), immediate and computed (RENDER-ITEMS-TEX-003). The client registers them all before an',
             ' * item first draws; the body draws and the wearer skin name them by index. index, path under Data,',
             ' * filter, wrap; sorted by index, the calls of one index in the client\'s call order (mu_it_registration',
             ' * replays them through 0x00c97730\'s rule). The comment gives the call site, its routine and whether',
             ' * the startup loader reaches that routine by direct calls. */',
             'static const mu_it_call item_bitmaps[] = {']
    for c in calls:
        when = 'startup' if c['routine'] in reach else 'startup opener, no direct caller'
        run = f', run 0x{c["run"]:08x} call {c["order"][1]}' if c['run'] else ''
        lines.append(f'    {{0x{c["index"]:04x}, {c_string(c["path"])}, 0x{c["filter"]:04x}, 0x{c["wrap"]:04x}}},'
                     f' /* 0x{c["site"]:08x} in 0x{c["routine"]:08x}, {when}{run} */')
    lines += ['};', '']
    Path(path).write_text('\n'.join(lines))
    repeated = {i: len(g) for i, g in by_index.items() if len(g) > 1}
    return len(calls), len(by_index), repeated


# The wearer skin bitmaps (RENDER-ITEMS-TEX-002): 0x7725 skin, 0x7776 hair, 0x77c7 HQskin, 0x7818 HQskin2, 0x7869
# HQskin3, 0x78ba HQhair, each plus the skin index 0x0139d6a2 (0..0x4f); registered by the startup routine 0x0182a8fe.
SKIN_FIRST, SKIN_LAST = 0x7725, 0x78ba + 0x50


NAMES_TABLE = ROOT / 'native/core/mu_startup_bitmaps.inc'


def startup_names(text, data):
    """Static LoadBitmap sites with an immediate .jpg/.tga path in routines the startup loader reaches (and the
    startup opener), in address order; the first path per lowercased file name (the name-map key)."""
    reach = startup_reach(text)
    out, keys, conflicts = [], {}, {}
    for site, first, args in scan_calls(text, LOAD_BITMAP):
        routine = routine_of(text, site)
        if routine not in reach and routine != STARTUP_OPENER:
            continue
        path = string_at(data, args[0]) if args[0] is not None else None
        if not path or not path.lower().endswith(('.jpg', '.tga')):
            continue
        key = path.replace('/', '\\').split('\\')[-1].lower()
        if key in keys:
            if keys[key].lower() != path.lower():
                conflicts[key] = conflicts.get(key, 1) + 1
            continue
        keys[key] = path
        out.append((site, first, path, args))
    return out, conflicts


def emit_names(path, text, data):
    names, conflicts = startup_names(text, data)
    lines = ['/* Generated by scripts/validate_item_textures.py --emit-names: the files the startup LoadBitmap 0x0185baac',
             ' * calls load (immediate .jpg/.tga paths in routines the startup loader 0x0182049e reaches, and the startup',
             ' * opener 0x01832af3), in call-site order, the first path per lowercased file name. LoadImage enters each',
             ' * in the bitmap-name map, which the item loader 0x00cd558e asks after Texture\\ (RENDER-ITEMS-TEX-001),',
             ' * with the call\'s filter and wrap, which a reused bitmap keeps (RENDER-ITEMS-TEX-002).',
             f' * {len(names)} names; {len(conflicts)} names are also loaded from another folder (first site kept). */',
             'static const startup_bitmap_entry startup_bitmaps[] = {']
    lines += [f'    {{{c_string(p)}, 0x{a[2]:04x}, 0x{a[3]:04x}}},' for _, _, p, a in names]
    lines += ['};', '']
    Path(path).write_text('\n'.join(lines))
    return len(names), conflicts


def family_names(machine, text, data, table):
    """Every startup name of the generated list runs from its site's first push: the LoadBitmap path, filter and wrap
    must equal it."""
    tally = Tally('startup_names')
    names, conflicts = startup_names(text, data)
    tally.add(len(names) == len(table), {'client_names': len(names), 'table': len(table)})
    for k, (site, first, path, args) in enumerate(names):
        calls = []

        def load(mm):
            calls.append((mm.cstring(mm.argument(0)), mm.argument(2), mm.argument(3)))
            return 1
        r = machine.execute(first, [], [], {LOAD_BITMAP: load, site + 8: lambda mm: 0})
        tally.add(am_ok(r) and k < len(table) and calls == [(path, args[2], args[3])] == [table[k]],
                  {'site': hex(site), 'client': calls, 'table': table[k] if k < len(table) else None})
    tally.count('names', len(names))
    tally.count('conflicting names', len(conflicts))
    return tally.report()


def names_entries(path=NAMES_TABLE):
    pattern = r'^    \{"((?:[^"\\]|\\.)*)", 0x([0-9a-f]+), 0x([0-9a-f]+)\},$'
    return [(m.group(1).replace('\\\\', '\\'), int(m.group(2), 16), int(m.group(3), 16))
            for m in re.finditer(pattern, Path(path).read_text(), re.M)]


def table_entries(path=TABLE):
    pattern = re.compile(r'\{0x([0-9a-f]+), "((?:[^"\\]|\\.)*)", 0x([0-9a-f]+), 0x([0-9a-f]+)\}')
    out = []
    for m in pattern.finditer(Path(path).read_text()):
        out.append((int(m.group(1), 16), m.group(2).replace('\\\\', '\\'), int(m.group(3), 16),
                    int(m.group(4), 16)))
    return out


def family_registrations(machine, text, data, entries):
    """RENDER-ITEMS-TEX-003: the table is every startup LoadBitmap call, in table order, as client code makes it."""
    tally = Tally('registrations')
    calls, stops, uncovered = startup_calls(machine, text, data)
    for stop in stops:
        tally.add(False, stopped=stop)
    tally.add(not uncovered and len(calls) == len(entries),
              {'uncovered_sites': [hex(x) for x in uncovered[:8]], 'calls': len(calls), 'table': len(entries)})
    for k, c in enumerate(calls):
        client = (c['index'], c['path'], c['filter'], c['wrap'])
        tally.add(c['flags'] == (1, 0) and k < len(entries) and client == entries[k],
                  {'site': hex(c['site']), 'client': client, 'flags': c['flags'],
                   'table': entries[k] if k < len(entries) else None})
        tally.count('computed calls' if c['run'] else 'immediate calls')
    tally.count('indices', len({c['index'] for c in calls}))
    tally.count('indices with several calls', sum(1 for i in {c['index'] for c in calls}
                                                  if sum(1 for d in calls if d['index'] == i) > 1))
    return tally.report()


# ---------------------------------------------------------------- 0x00c97730 (RENDER-ITEMS-TEX-003)
REGISTER = 0x00c97730
MAP_FIND, MAP_END, ITER_NE, ITER_DEREF = 0x00c9d0e8, 0x00c9d05e, 0x00c9b1c9, 0x00c9b287
UNLOAD, LOAD_JPG, LOAD_TGA = 0x00c97916, 0x00c982ea, 0x00c988fc
STR_DEFAULT, STR_ASSIGN = 0x008e6d00, 0x0094afda
REG_THIS, REG_NODE, REG_BITMAP, REG_PATH, REG_END = 0x42020000, 0x42021000, 0x42022000, 0x42023000, 0x42024000
REG_POOL = ['Data\\Item\\Texture\\a.jpg', 'Data\\item\\texture\\A.JPG', 'Data\\Item\\Texture\\a.tga',
            'Data\\Effect\\b.TGA', 'Data\\Effect\\b.tga', 'Data\\Effect\\c.bmp', 'Data\\Effect\\noext',
            'Data\\Effect\\d.', 'Data\\Eff.ect\\e', 'Data\\Effect\\blur_aura002.jpg',
            'Data\\Item\\texture\\blur_aura002.jpg', 'Data\\Effect\\x.jpgx', 'Data\\Effect\\y.Jpg', 'Data\\Effect\\z.tGa']
REG_PARAMS = [(0x2600, 0x2900), (0x2601, 0x2900), (0x2601, 0x2901), (0x2600, 0x2901)]


def run_register_client(machine, slot, index, path, filt, wrap, sec3):
    """0x00c97730(index, path, filter, wrap) as client code on one slot state (None, or dict path/filter/wrap/refs).
    Returns (requests, return byte, slot after, stop)."""
    events = []
    strings = Strings(machine)
    state = {'present': slot is not None, 'filter': slot and slot['filter'], 'wrap': slot and slot['wrap']}
    record = bytearray(0x240)
    if slot:
        raw = slot['path'].encode('latin1')
        record[4:4 + len(raw)] = raw
        record[0x219] = slot['refs']

    def ecx(mm):
        return mm.uc.reg_read(mm.x86.UC_X86_REG_ECX)

    def find(mm):
        out = mm.argument(0)
        if mm.read32(mm.argument(1)) != index:
            raise ValueError('map key')
        mm.uc.mem_write(out, struct.pack('<I', REG_NODE if state['present'] else REG_END))
        return out, 8

    def end(mm):
        mm.uc.mem_write(mm.argument(0), struct.pack('<I', REG_END))
        return mm.argument(0), 4

    def loader(kind):
        def stub(mm):
            if mm.argument(0) != index:
                raise ValueError('load index')
            events.append(('load', kind, index, strings.get(mm.argument(1)), mm.argument(2), mm.argument(3)))
            raw = strings.get(mm.argument(1)).encode('latin1')
            mm.uc.mem_write(REG_BITMAP + 4, raw + b'\0')
            mm.uc.mem_write(REG_BITMAP + 0x219, b'\x01')
            state.update(present=True, filter=mm.argument(2), wrap=mm.argument(3))
            return 1, 0x10
        return stub

    def unload(mm):
        events.append(('unload', mm.argument(0), mm.argument(1)))
        state['present'] = False
        mm.uc.mem_write(REG_BITMAP + 0x219, b'\x00')
        return 0, 8

    def splitpath(mm):
        p, drive, directory, fname, ext = (mm.argument(k) for k in range(5))
        if drive or directory or fname:
            raise ValueError('unmodelled _splitpath outputs')
        name = mm.cstring(p, 300)
        base = max(name.rfind('\\'), name.rfind('/'))
        dot = name.rfind('.')
        mm.uc.mem_write(ext, (name[dot:] if dot > base else '').encode('latin1')[:255] + b'\0')
        return 0

    stubs = {MAP_FIND: find, MAP_END: end,
             ITER_NE: lambda mm: (int(mm.read32(ecx(mm)) != mm.read32(mm.argument(0))), 4),
             ITER_DEREF: lambda mm: (mm.read32(ecx(mm)), 0),
             STR_CSTR: lambda mm: (mm.read32(ecx(mm)), 0), STR_DTOR: lambda mm: (0, 0),
             STR_DEFAULT: lambda mm: (strings.put(ecx(mm), '') or ecx(mm), 0),
             STR_ASSIGN: lambda mm: (strings.put(ecx(mm), mm.cstring(mm.argument(0))) or ecx(mm), 4),
             SPLITPATH: splitpath, LOG: lambda mm: 0, UNLOAD: unload, LOAD_JPG: loader('jpg'), LOAD_TGA: loader('tga')}
    heap = bytearray(0x10000)   # the path argument's text, then the strings the stubs make
    raw = path.encode('latin1') + b'\0'
    heap[:len(raw)] = raw
    strings.next = HEAP + ((len(raw) + 15) & ~15)
    strings.value[REG_PATH] = path
    regions = [am.defined_region('this', REG_THIS, bytes(0x100), writable=False),
               am.defined_region('node', REG_NODE, struct.pack('<II', 0, REG_BITMAP), writable=False),
               am.defined_region('bitmap', REG_BITMAP, bytes(record)),
               am.defined_region('heap', HEAP, bytes(heap)),
               am.defined_region('path-object', REG_PATH, struct.pack('<I', HEAP) + bytes(0x1c), writable=False),
               am.defined_region('locale-changed', LOCALE_CHANGED, bytes(4), writable=False),
               am.defined_region('sse2-flag', SSE2_FLAG, bytes(4), writable=False),
               am.defined_region('section3-init', SECTION3_BASE, sec3[:SECTION3_INIT], writable=False)]
    r = machine.execute(REGISTER, [index, REG_PATH, filt, wrap], regions, stubs, ecx=REG_THIS, cleanup=0x10)
    stop = None if r['ok'] else {'stopped': r['stopped'], 'error': r['error'],
                                 'checks': {k: v for k, v in r['checks'].items() if not v}}
    after = None
    if state['present']:
        raw = r['regions']['bitmap']
        after = {'path': raw[4:0x200].split(b'\0')[0].decode('latin1'), 'filter': state['filter'],
                 'wrap': state['wrap'], 'refs': raw[0x219]}
    return events, r['eax'] & 0xff, after, stop


def run_register_c(lib, slot, index, path, filt, wrap, keep):
    b = Bitmap()
    if slot:
        raw = slot['path'].encode('latin1')
        keep.append(raw)
        b.path, b.filter, b.wrap, b.refs = raw, slot['filter'], slot['wrap'], slot['refs']
    raw = path.encode('latin1')
    keep.append(raw)
    what = lib.mu_it_register(C.byref(b), raw, filt, wrap)
    events = []
    if what & 1:
        events.append(('unload', index, 1))
    for bit, kind in ((2, 'jpg'), (4, 'tga')):
        if what & bit:
            events.append(('load', kind, index, path, filt, wrap))
    after = None if not b.path else {'path': b.path.decode('latin1'), 'filter': b.filter, 'wrap': b.wrap,
                                     'refs': b.refs}
    return events, int(bool(what & 0xe)), after


def family_reregister(machine, lib, entries, sec3, cases, seed='items-tex-register'):
    tally = Tally('reregister')
    g = random.Random(seed)
    for n in range(cases):
        slot = None if g.random() < 0.35 else {'path': g.choice(REG_POOL), 'refs': g.choice([0, 1, 1, 2, 7, 255]),
                                                'filter': g.choice(REG_PARAMS)[0], 'wrap': g.choice(REG_PARAMS)[1]}
        index = g.choice([0x854c, 0x8531, 0x7fe7, g.randrange(0x7530, 0x8700)])
        c_slot = slot
        for _ in range(g.choice([1, 1, 2, 3])):
            path = g.choice(REG_POOL)
            if slot and g.random() < 0.4:   # the same file, often in another case
                path = g.choice([slot['path'], slot['path'].upper(), slot['path'].lower()])
            filt, wrap = g.choice(REG_PARAMS)
            events, ret, after, stop = run_register_client(machine, slot, index, path, filt, wrap, sec3)
            keep = []
            c_events, c_ret, c_after = run_register_c(lib, c_slot, index, path, filt, wrap, keep)
            tally.add(stop is None and (events, ret, after) == (c_events, c_ret, c_after),
                      {'case': n, 'slot': slot, 'call': (path, filt, wrap), 'client': (events, ret, after),
                       'c': (c_events, c_ret, c_after)}, stop)
            tally.count('reference' if not events and ret else 'unload' if any(e[0] == 'unload' for e in events)
                        else 'load' if events else 'nothing loaded')
            slot, c_slot = after, c_after
    # every table index, replayed from an empty slot through 0x00c97730, against mu_it_registration
    keep = [e[1].encode('latin1') for e in entries]
    table = (Call * len(entries))(*[Call(e[0], keep[k], e[2], e[3]) for k, e in enumerate(entries)])
    by_index = {}
    for e in entries:
        by_index.setdefault(e[0], []).append(e)
    for index, group in by_index.items():
        slot, stop = None, None
        for _, path, filt, wrap in group:
            _, _, slot, stop = run_register_client(machine, slot, index, path, filt, wrap, sec3)
            if stop:
                break
        b = Bitmap()
        held = lib.mu_it_registration(table, len(entries), index, C.byref(b))
        native = (b.path.decode('latin1'), b.filter, b.wrap) if held else None
        client = (slot['path'], slot['filter'], slot['wrap']) if slot else None
        tally.add(client == native, {'index': hex(index), 'calls': len(group), 'client': client, 'c': native}, stop)
        tally.count('table indices')
        tally.count('table indices with several calls', len(group) > 1)
    return tally.report()


def am_ok(result):
    return result['stopped'] is None and result['error'] is None


# ---------------------------------------------------------------- mutants
MUTANTS = [
    ('item_texture.c', 'texture_path(char out[256], const char *folder, const char *name)\n{\n    const int n = snprintf(out, 256, "%sTexture\\\\%s", folder, name);',
     'texture_path(char out[256], const char *folder, const char *name)\n{\n    const int n = snprintf(out, 256, "%s%s", folder, name);', 'item_open'),
    ('item_texture.c', 'prefix_nocase(name, "nude_"))', 'prefix_nocase(name, "nude"))', 'item_open'),
    ('item_texture.c', '*type = MU_IT_COTTON2;', '*type = MU_IT_COTTON;', 'item_open'),
    ('item_texture.c', 'prefix_nocase(name, "level"))', 'prefix_nocase(name, "level_"))', 'item_open'),
    ('item_texture.c', 'if (prefix_nocase(name, "hid"))', 'if (strncmp(name, "hid", 3) == 0)', 'item_open'),
    ('item_texture.c', 'strncmp(name, "field_", 6) == 0', 'prefix_nocase(name, "field_")', 'item_open'),
    ('item_texture.c', '        *field = 1;\n', '', 'item_open'),
    ('item_texture.c', '        h->load(h->context, path, GL_NEAREST_, GL_CLAMP_);\n    } else if',
     '    } else if', 'item_open'),
    ('item_texture.c', 'if (prefix_nocase(name, "HQskin_"))', 'if (prefix_nocase(name, "HQskin3"))', 'item_open'),
    ('item_texture.c', 'index = h->load(h->context, path, GL_NEAREST_, GL_CLAMP_);   /* 0x00cd5b50 */',
     'index = h->load(h->context, path, GL_NEAREST_, 0x2901u);   /* 0x00cd5b50 */', 'item_open'),
    ('item_texture.c', 'h->reuse(h->context, hit, cached ? cached : "", GL_NEAREST_, GL_CLAMP_);',
     'h->reuse(h->context, hit, cached ? cached : "", GL_NEAREST_, 0x2901u);', 'item_open'),
    ('item_texture.c', '        if (hit >= 0) {', '        if (hit > 0) {', 'item_open'),
    ('item_texture.c', '            if (h->error)\n', '            if (0)\n', 'item_open'),
    ('mu_startup_bitmaps.inc', '"Effect\\\\lightning2.jpg"', 'drop', 'startup_names'),
    ('mu_startup_bitmaps.inc', '"Effect\\\\lightning2.jpg"', 'flip', 'startup_names'),
    ('mu_item_bitmaps.inc', '{0x84d9, ', None, 'registrations'),
    ('mu_item_bitmaps.inc', '{0x8239, ', None, 'registrations'),
    ('mu_item_bitmaps.inc', '{0x77c7, ', None, 'registrations'),
    ('item_texture.c', 'return (int8_t)mu_character_skin_index(class_byte);',
     'return (int8_t)(class_byte & 0xf);', 'part_skin'),
    ('item_texture.c', 'return (int8_t)mu_character_skin_index(class_byte);',
     'return (int8_t)(mu_character_skin_index(class_byte) & 0x3f);', 'part_skin'),
    ('item_texture.c', 'case MU_TL_HQ_SKIN3: case MU_TL_HQ_HAIR:', 'case MU_TL_HQ_SKIN3:', 'skin_bitmap'),
    ('item_texture.c', 'return index_texture + skin;', 'return index_texture + (uint8_t)skin;', 'skin_bitmap'),
    # RENDER-ITEMS-TEX-003
    ('mu_item_bitmaps.inc', '{0x8531, ', None, 'registrations'),
    ('mu_item_bitmaps.inc', '"Item\\\\texture\\\\fire_sq_00005.jpg"', 'drop', 'registrations'),
    ('mu_item_bitmaps.inc', '{0x854c, ', 'swap', 'registrations'),
    ('item_texture.c', 'if (same_nocase(slot->path, path)) {', 'if (strcmp(slot->path, path) == 0) {', 'reregister'),
    ('item_texture.c', 'if (same_nocase(slot->path, path)) {', 'if (0) {', 'reregister'),
    ('item_texture.c', 'if (slot->path && slot->refs != 0) {', 'if (slot->path) {', 'reregister'),
    ('item_texture.c', 'if (same_nocase(ext, "jpg"))', 'if (strcmp(ext, "jpg") == 0)', 'reregister'),
    ('item_texture.c', '    else\n        return what;\n', '', 'reregister'),
    ('item_texture.c', 'i < count && calls[i].index == index; ++i)', 'i < count && i <= lo && calls[i].index == index; ++i)',
     'reregister'),
]


def build_mutant(tmp, file, old, new):
    dest = Path(tmp)
    if file == 'mu_startup_bitmaps.inc':
        s = NAMES_TABLE.read_text()
        out = dest / file
        if new == 'flip':   # the wrap of that name's call
            line = next(l for l in s.split('\n') if old in l)
            flipped = line.replace('0x2900}', '0x2901}') if '0x2900}' in line else line.replace('0x2901}', '0x2900}')
            out.write_text(s.replace(line, flipped))
        else:
            out.write_text('\n'.join(l for l in s.split('\n') if old not in l))
        return out
    if file == 'mu_item_bitmaps.inc':
        s = TABLE.read_text()
        lines = s.split('\n')
        out = dest / file
        if new == 'drop':
            out.write_text('\n'.join(l for l in lines if old not in l))
        elif new == 'swap':   # the calls of one index in the other order
            k = [i for i, l in enumerate(lines) if old in l]
            lines[k[0]], lines[k[1]] = lines[k[1]], lines[k[0]]
            out.write_text('\n'.join(lines))
        else:
            line = next(l for l in lines if old in l)
            flipped = line.replace('0x2900}', '0x2901}') if '0x2900}' in line else line.replace('0x2901}', '0x2900}')
            out.write_text(s.replace(line, flipped))
        return out
    for f in ('item_texture.c', 'item_texture.h', 'texture_lookup.h'):
        shutil.copy(ROOT / 'reconstructed/objects' / f, dest / f)
    path = dest / file
    s = path.read_text().replace('"../model-codec/character.h"', f'"{ROOT / "reconstructed/model-codec/character.h"}"')
    assert s.count(old) == 1, old
    path.write_text(s.replace(old, new))
    out = dest / f'libit.{SUFFIX}'
    subprocess.run(['clang', '-std=c11', '-O2', '-shared', '-fPIC', str(dest / 'item_texture.c'),
                    str(ROOT / 'reconstructed/model-codec/character.c'),
                    str(ROOT / 'reconstructed/record-math/record_math.c'), '-o', str(out)], check=True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--text', type=Path, default=pins.TEXT.default())
    ap.add_argument('--data', type=Path, default=pins.DATA.default())
    ap.add_argument('--section3', type=Path, default=pins.SECTION3.default())
    ap.add_argument('--cases', type=int, default=3000)
    ap.add_argument('--mutations', action='store_true')
    ap.add_argument('--emit-table', type=Path)
    ap.add_argument('--register-cases', type=int, default=1000)
    ap.add_argument('--emit-names', type=Path)
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()

    text = vo.load_pinned(a.text, vo.TEXT_BYTES, vo.TEXT_SHA256, 'text')
    data = vo.load_pinned(a.data, vo.DATA_BYTES, vo.DATA_SHA256, 'data')
    if a.emit_names:
        n, conflicts = emit_names(a.emit_names, text, data)
        print('wrote', a.emit_names, n, 'names; conflicts', sorted(conflicts))
        return 0
    if a.emit_table:
        calls, indices, repeated = emit_table(a.emit_table, am.ActorMachine(text, data), text, data)
        print('wrote', a.emit_table, calls, 'calls,', indices, 'indices; several calls',
              {hex(i): n for i, n in repeated.items()})
        return 0
    sec3 = vo.load_pinned(a.section3, vo.SECTION3_BYTES, vo.SECTION3_SHA256, 'third section')
    machine = am.ActorMachine(text, data)
    subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
    lib = bind(C.CDLL(str(ROOT / f'reconstructed/objects/libobjects.{SUFFIX}')))
    entries = table_entries()
    report = {'inputs': {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
                         'section3_sha256': vo.SECTION3_SHA256},
              'bodies': {n: {'start': hex(s), 'end': hex(e),
                             'sha256': hashlib.sha256(text[s - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()}
                         for n, (s, e) in BODIES.items()},
              'table_entries': len(entries), 'families': {}, 'mutants': []}
    fam = report['families']
    fam['item_open'] = family_open(machine, lib, a.cases, sec3)
    fam['registrations'] = family_registrations(machine, text, data, entries)
    fam['startup_names'] = family_names(machine, text, data, names_entries())
    fam['part_skin'] = family_part_skin(machine, lib)
    fam['skin_bitmap'] = family_skin_bitmap(machine, lib)
    fam['reregister'] = family_reregister(machine, lib, entries, sec3, a.register_cases)
    for name, r in fam.items():
        print(name, {k: r[k] for k in ('cases', 'equal', 'stopped', 'mismatch_count')}, flush=True)
    if a.mutations:
        for file, old, new, family in MUTANTS:
            with tempfile.TemporaryDirectory(prefix='items-tex-') as tmp:
                path = build_mutant(tmp, file, old, new)
                if family == 'item_open':
                    r = family_open(machine, bind(C.CDLL(str(path))), min(a.cases, 1500), sec3)
                elif family == 'part_skin':
                    r = family_part_skin(machine, bind(C.CDLL(str(path))))
                elif family == 'skin_bitmap':
                    r = family_skin_bitmap(machine, bind(C.CDLL(str(path))))
                elif family == 'startup_names':
                    r = family_names(machine, text, data, names_entries(path))
                elif family == 'reregister':
                    mutant_lib = lib if file == 'mu_item_bitmaps.inc' else bind(C.CDLL(str(path)))
                    mutant_table = table_entries(path) if file == 'mu_item_bitmaps.inc' else entries
                    r = family_reregister(machine, mutant_lib, mutant_table, sec3, min(a.register_cases, 500))
                else:
                    r = family_registrations(machine, text, data, table_entries(path))
            m = {'family': family, 'file': file, 'change': (new if new is not None else f'wrap flip at {old}'),
                 'detected': r['mismatch_count'], 'stopped': r['stopped']}
            report['mutants'].append(m)
            print('mutant', {k: m[k] for k in ('family', 'detected', 'stopped')}, m['change'][:60], flush=True)
    if a.output:
        a.output.write_text(json.dumps(report, indent=2) + '\n')
    bad = any(r['equal'] != r['cases'] for r in fam.values())
    bad |= any(not m['detected'] or m['stopped'] for m in report['mutants'])
    return int(bad)


if __name__ == '__main__':
    raise SystemExit(main())
