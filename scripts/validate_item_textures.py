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
                 immediate .jpg/.tga path runs from its first push and must load exactly the listed path.
  registrations  every LoadBitmap 0x0185baac site of the item bitmap table (native/core/mu_item_bitmaps.inc) runs
                 from its first push: path, index, filter, wrap and the two flags must equal the table entry, and
                 every static site of an index in the table must agree.

--emit-table PATH --ids 0x84d9,... writes the item bitmap table: each index's static LoadBitmap sites (immediate
path), the routine that holds them and whether the startup loader 0x0182049e reaches it by direct calls.
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
BODIES = {'item_open': (ITEM_OPEN, ITEM_OPEN_END), 'get_model': (0x00eaa8cf, 0x00eaaa3e)}

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
    lib.mu_it_open.argtypes = [C.POINTER(Host), C.c_char_p, C.c_char_p, C.POINTER(C.c_int32), C.POINTER(C.c_int),
                               C.POINTER(C.c_int)]
    lib.mu_it_open.restype = C.c_int32
    return lib


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


def registrations_for(text, data, ids):
    out = {}
    for site, first, args in scan_calls(text, LOAD_BITMAP):
        if args[1] in ids and args[0] is not None:
            path = string_at(data, args[0])
            if path:
                out.setdefault(args[1], []).append({'site': site, 'first': first, 'path': path, 'filter': args[2],
                                                     'wrap': args[3], 'flags': (args[4], args[5])})
    return out


def c_string(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def emit_table(path, text, data, ids):
    regs = registrations_for(text, data, ids)
    reach = startup_reach(text)
    lines = ['/* Generated by scripts/validate_item_textures.py --emit-table: the LoadBitmap 0x0185baac registrations of',
             ' * the client bitmaps the item body draws name (RENDER-ITEMS-TEX-001) and of the wearer skin bitmaps',
             ' * 0x7725..0x790a that skin/hair mesh names bind with the model\'s +0xa4 shift (RENDER-ITEMS-TEX-002,',
             ' * --skins). index, path under Data, filter, wrap;',
             ' * the comment gives the call site, its routine and whether the startup loader 0x0182049e reaches that',
             ' * routine by direct calls. */',
             'static const item_bitmap item_bitmaps[] = {']
    missing = []
    for index in sorted(ids):
        entries = regs.get(index)
        if not entries:
            missing.append(index)
            continue
        e = entries[0]
        routine = routine_of(text, e['site'])
        when = ('startup' if routine in reach else 'startup opener, no direct caller' if routine == STARTUP_OPENER
                else 'not reached from startup')
        lines.append(f'    {{0x{index:04x}, {c_string(e["path"])}, 0x{e["filter"]:04x}, 0x{e["wrap"]:04x}}},'
                     f' /* 0x{e["site"]:08x} in 0x{routine:08x}, {when}; {len(entries)} site(s) */')
    lines += ['};', '']
    if missing:
        lines.insert(-2, '/* not registered by an immediate LoadBitmap call: ' +
                     ', '.join(f'0x{i:04x}' for i in missing) + ' */')
    Path(path).write_text('\n'.join(lines))
    return missing


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
    tally = Tally('registrations')
    regs = registrations_for(text, data, {e[0] for e in entries})
    for index, path, filt, wrap in entries:
        sites = regs.get(index, [])
        if not sites:
            tally.add(False, {'index': hex(index), 'sites': 0})
            continue
        for s in sites:
            calls = []

            def load(mm):
                calls.append([mm.cstring(mm.argument(0)), *[mm.argument(i) for i in range(1, 6)]])
                return 1
            r = machine.execute(s['first'], [], [], {LOAD_BITMAP: load, s['site'] + 8: lambda mm: 0})
            tally.add(am_ok(r) and calls == [[path, index, filt, wrap, 1, 0]],
                      {'index': hex(index), 'site': hex(s['site']), 'client': calls, 'table': [path, filt, wrap]})
            tally.count('sites')
        tally.count('indices')
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
        line = next(l for l in s.split('\n') if old in l)
        flipped = line.replace('0x2900}', '0x2901}') if '0x2900}' in line else line.replace('0x2901}', '0x2900}')
        out = dest / file
        out.write_text(s.replace(line, flipped))
        return out
    for f in ('item_texture.c', 'item_texture.h', 'texture_lookup.h'):
        shutil.copy(ROOT / 'reconstructed/objects' / f, dest / f)
    path = dest / file
    s = path.read_text()
    assert s.count(old) == 1, old
    path.write_text(s.replace(old, new))
    out = dest / f'libit.{SUFFIX}'
    subprocess.run(['clang', '-std=c11', '-O2', '-shared', '-fPIC', str(dest / 'item_texture.c'), '-o', str(out)],
                   check=True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--text', type=Path, default=pins.TEXT.default())
    ap.add_argument('--data', type=Path, default=pins.DATA.default())
    ap.add_argument('--section3', type=Path, default=pins.SECTION3.default())
    ap.add_argument('--cases', type=int, default=3000)
    ap.add_argument('--mutations', action='store_true')
    ap.add_argument('--emit-table', type=Path)
    ap.add_argument('--ids', default='')
    ap.add_argument('--skins', action='store_true', help='--emit-table: add every registered skin index')
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
        ids = {int(x, 16) for x in a.ids.split(',') if x}
        if a.skins:
            ids |= {i for i in registrations_for(text, data, set(range(SKIN_FIRST, SKIN_LAST + 1)))}
        missing = emit_table(a.emit_table, text, data, ids)
        print('wrote', a.emit_table, 'unregistered', [hex(i) for i in missing])
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
    for name, r in fam.items():
        print(name, {k: r[k] for k in ('cases', 'equal', 'stopped', 'mismatch_count')}, flush=True)
    if a.mutations:
        for file, old, new, family in MUTANTS:
            with tempfile.TemporaryDirectory(prefix='items-tex-') as tmp:
                path = build_mutant(tmp, file, old, new)
                if family == 'item_open':
                    r = family_open(machine, bind(C.CDLL(str(path))), min(a.cases, 1500), sec3)
                elif family == 'startup_names':
                    r = family_names(machine, text, data, names_entries(path))
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
