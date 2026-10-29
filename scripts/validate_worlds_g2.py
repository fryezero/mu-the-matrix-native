#!/usr/bin/env python3
"""RENDER-WORLDS-G2: object texture lookup and the Vulcanus far plane against pinned original instructions.

Families (docs/research/client-worlds-g2.md):
  open_texture    OpenTexture 0x0181fbe9 with its resolver 0x0181fead run as client code on synthetic models. The
                  bitmap services are recording stubs: LoadImage 0x00c97689 answers from a synthetic file set, the
                  name map 0x00c97e0c from a synthetic cache, 0x00c97730 and the 0xeaa message only record. The C
                  mu_tl_open must make the same requests in the same order and store the same IndexTexture values.
  startup_table   the startup opener 0x01832af3 recorded (AccessModel/OpenTexture calls; other callees return a
                  dummy object): its (model file, texture subfolder) pairs in OpenTexture order, first occurrence,
                  must equal mu_tl_startup.
  world_preloads  the world pass 0x018392db for worlds 0..199: the models outside 0..299 it opens textures for,
                  all before the first object texture, must equal mu_tl_world_preloads.
  event_world     0x00e94004() || 0x00e3068f() for worlds -8..300 against mu_world_camera_event_world.

--emit-table PATH writes the preload table from the two recordings. --mutations compiles planted mistakes that a
family must catch. Inputs: the pinned text, data and section-3 captures (scripts/pins.py).
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
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

OPEN_TEXTURE, RESOLVE = 0x0181fbe9, 0x0181fead
MODEL_CONTAINER, MODEL_GET = 0x00966cc4, 0x00eaa8cf
LOAD, FIND, REUSE = 0x00c97689, 0x00c97e0c, 0x00c97730
STR_CTOR, STR_DTOR = 0x0094997e, 0x008e83a0
TEXT, FORMAT, MESSAGE = 0x0095f027, 0x009619dd, 0x0185bc31
SPLITPATH = 0x0198b9e3   # CRT _splitpath: a service stub (its multibyte checks read heap-held locale state)
STARTUP, STARTUP_END = 0x01832af3, 0x018392db
EVENT_A, EVENT_B, WORLD = 0x00e94004, 0x00e3068f, 0x01cf15fc
LOCALE_CHANGED = 0x0bdcf8ec   # _strnicmp's __locale_changed (0: the C locale path)
SECTION3_BASE, SECTION3_INIT = 0x01ced000, 0x20000   # section-3 bytes of capture-04 (CRT locale/multibyte state)
SSE2_FLAG = 0x0bdcb284        # memset's CPU-feature flag (0: the plain store path)
BODIES = {'open_texture': (OPEN_TEXTURE, RESOLVE), 'resolve': (RESOLVE, 0x01820173),
          'startup': (STARTUP, STARTUP_END), 'event_a': (EVENT_A, 0x00e94018), 'event_b': (EVENT_B, 0x00e306b5)}

# harness memory
MODEL, NAMES, INDEX, CONTAINER, ENTRY, STRINGS, MSG = (0x42000000, 0x42001000, 0x42002000, 0x42003000,
                                                      0x42004000, 0x42005000, 0x42006000)

LOAD_FN = C.CFUNCTYPE(C.c_int32, C.c_void_p, C.c_char_p, C.c_uint32, C.c_uint32)
FIND_FN = C.CFUNCTYPE(C.c_int32, C.c_void_p, C.c_char_p, C.POINTER(C.c_char_p))
REUSE_FN = C.CFUNCTYPE(None, C.c_void_p, C.c_int32, C.c_char_p, C.c_uint32, C.c_uint32)
ERROR_FN = C.CFUNCTYPE(None, C.c_void_p, C.c_char_p)


class Host(C.Structure):
    _fields_ = [('context', C.c_void_p), ('load', LOAD_FN), ('find', FIND_FN), ('reuse', REUSE_FN),
                ('error', ERROR_FN)]


class Preload(C.Structure):
    _fields_ = [('folder', C.c_char_p), ('name', C.c_char_p), ('number', C.c_int32), ('subfolder', C.c_char_p)]


def bind(lib):
    lib.mu_tl_open.argtypes = [C.POINTER(Host), C.c_char_p, C.c_char_p, C.c_uint32, C.c_uint32,
                               C.POINTER(C.c_int)]
    lib.mu_tl_open.restype = C.c_int32
    lib.mu_tl_startup_count.restype = C.c_int32
    lib.mu_tl_startup.argtypes = [C.c_int32]
    lib.mu_tl_startup.restype = C.POINTER(Preload)
    lib.mu_tl_world_preloads.argtypes = [C.c_int32, C.POINTER(C.POINTER(Preload))]
    lib.mu_tl_world_preloads.restype = C.c_int32
    return lib


def bind_camera(lib):
    lib.mu_world_camera_event_world.argtypes = [C.c_int32]
    lib.mu_world_camera_event_world.restype = C.c_int
    return lib


# ---------------------------------------------------------------- recordings (0x01832af3, 0x018392db)
def recorder(a):
    text = vo.load_pinned(a.text, vo.TEXT_BYTES, vo.TEXT_SHA256, 'restored text (capture09)')
    data = vo.load_pinned(a.data, vo.DATA_BYTES, vo.DATA_SHA256, 'second image section (run10)')
    sec3 = vo.load_pinned(a.section3, vo.SECTION3_BYTES, vo.SECTION3_SHA256, 'third section')
    return vo.Machine(text, data, sec3), sec3


def record_startup(machine):
    """0x01832af3 with the world-pass recorder. One skipped service's dummy result is stored through a null
    pointer; that write lands in a zero page mapped on demand (counted in the report)."""
    from unicorn import UC_HOOK_MEM_UNMAPPED, UC_PROT_ALL
    mapped = []

    def on_demand(uc, access, address, size, value, ignored):
        if address >= 0x1000:
            return False
        uc.mem_map(0, 0x1000, UC_PROT_ALL)
        mapped.append(address)
        return True
    hook = machine.uc.hook_add(UC_HOOK_MEM_UNMAPPED, on_demand)
    saved = vo.OPEN_MODELS, vo.OPEN_MODELS_END
    vo.OPEN_MODELS, vo.OPEN_MODELS_END = STARTUP, STARTUP_END
    try:
        run = vo.ModelRun(machine)
        log = run.run(0)
        run.close()
    finally:
        vo.OPEN_MODELS, vo.OPEN_MODELS_END = saved
        machine.uc.hook_del(hook)
        if mapped:
            machine.uc.mem_unmap(0, 0x1000)
    return log, len(mapped)


def texture_pairs(log, extras_only=False):
    """(folder, name, number, subfolder) per OpenTexture call of a recorded model, first occurrence; and the number
    of OpenTexture calls for models the routine did not open itself."""
    model, out, seen, foreign, objects_seen, late = {}, [], set(), 0, 0, 0
    for e in log:
        if e[0] == 'model':
            model[e[1]] = (e[2], e[3], e[4])
        elif e[0] == 'texture':
            if extras_only and e[1] < 300:
                objects_seen += 1
                continue
            if e[1] not in model:
                foreign += 1
                continue
            key = model[e[1]] + (e[2],)
            if extras_only and objects_seen:
                late += 1
            if key not in seen:
                seen.add(key)
                out.append(key)
    return out, foreign, late


def c_entry(p):
    q = p.contents
    return (q.folder.decode('latin1'), q.name.decode('latin1'), q.number, q.subfolder.decode('latin1'))


def c_string(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def emit_table(path, startup, worlds):
    lines = ['/* Generated by scripts/validate_worlds_g2.py --emit-table from the recorded AccessModel/OpenTexture',
             ' * calls of the startup opener 0x01832af3 and the world pass 0x018392db (RENDER-WORLDS-G2). */',
             'static const mu_tl_preload startup[] = {']
    lines += [f'    {{{c_string(f)}, {c_string(n)}, {k}, {c_string(s)}}},' for f, n, k, s in startup]
    lines += ['};', 'static const mu_tl_preload world_extra[] = {']
    index, ranges = 0, []
    for world, entries in worlds:
        ranges.append((world, index, len(entries)))
        lines += [f'    {{{c_string(f)}, {c_string(n)}, {k}, {c_string(s)}}},' for f, n, k, s in entries]
        index += len(entries)
    lines += ['};', 'static const struct {', '    int16_t world, first, count;', '} world_preloads[] = {']
    lines += [f'    {{{w}, {i}, {n}}},' for w, i, n in ranges]
    lines += ['};', '']
    Path(path).write_text('\n'.join(lines))


def family_tables(lib, startup, worlds, report_late):
    tally = vo_tally('startup_table')
    count = lib.mu_tl_startup_count()
    native = [c_entry(lib.mu_tl_startup(i)) for i in range(count)]
    for i, entry in enumerate(startup):
        tally.add(i < len(native) and native[i] == entry, {'entry': i, 'client': entry,
                                                          'c': native[i] if i < len(native) else None})
    tally.add(len(native) == len(startup), {'client_count': len(startup), 'c_count': len(native)})
    tally.count('entries', len(startup))
    wt = vo_tally('world_preloads')
    for world, entries in worlds:
        first = C.POINTER(Preload)()
        n = lib.mu_tl_world_preloads(world, C.byref(first))
        got = [c_entry(C.pointer(first[i])) for i in range(n)] if n > 0 else []
        wt.add(got == entries and not report_late.get(world),
               {'world': world, 'client': entries[:4], 'c': got[:4], 'late': report_late.get(world, 0)})
        wt.count('entries', len(entries))
        if entries:
            wt.count('worlds with preloads')
    return tally.report(), wt.report()


class vo_tally:
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


# ---------------------------------------------------------------- OpenTexture under Unicorn
SPECIAL = ['skin_01.jpg', 'ski.tga', 'Skin01.jpg', 'level_a.jpg', 'LEVEL_a.jpg', 'level.jpg', 'hide.jpg',
           'Hide.jpg', 'hid', 'hair_r.jpg', 'hai.jpg', 'face_01.jpg', 'face.jpg', 'HQskin3_a.jpg', 'hqSKIN3.tga',
           'HQskin2b.jpg', 'HQskin_x.jpg', 'HQskin', 'hqskin4.jpg', 'HQlevel_1.jpg', 'HQlevel1.jpg',
           'HQhair_a.tga', 'hqhair.jpg']
STEMS = ['bons', 'deep_wall01', 'wood01', 'sword02', 'Shield03', 'x', 'tree.a', 'gate_01', 'medicine1',
         'ng01', 'longname_texture_0123456789ab']
EXTS = ['.jpg', '.JPG', '.tga', '.TGA', '.jpeg', '.bmp', '.ozj', '.t', '.j', '', '.', '.tx', '.JpG']
SUBS = ['Object64\\', 'Object117\\', 'Monster\\', 'Item\\', 'Skill\\', 'Item\\texture', '', 'npc\\']


def synthetic_case(g):
    names = []
    for _ in range(g.choice([0, 1, 1, 2, 3, 4, 6])):
        if g.random() < 0.25:
            names.append(g.choice(SPECIAL))
        else:
            names.append(g.choice(STEMS) + g.choice(EXTS))
    sub = g.choice(SUBS)
    files = {}
    for n in names:
        for p in (f'Data\\{sub}{n}', f'Data\\Item\\{n}', f'Data\\Item\\Texture\\{n}'):
            if g.random() < 0.3:
                files[p] = 0x9000 + g.randrange(0x400)
    cache = {}
    for n in names:
        if g.random() < 0.35:
            cache[n] = (g.choice([0, 0x8800 + g.randrange(0x400)]), 'Data\\Skill\\' + n)
    count = len(names)
    if g.random() < 0.06:
        count = -g.randrange(1, 4)
    present = g.random() > 0.04
    wrap, filt = g.choice([(0x2901, 0x2600), (0x2900, 0x2601), (0x2901, 0x2601)])
    return {'names': names, 'sub': sub, 'files': files, 'cache': cache, 'count': count, 'present': present,
            'wrap': wrap, 'filter': filt, 'model_index': g.randrange(0, 0x4000)}


def string_at(m, this):
    return m.cstring(m.read32(this), 300)


def run_client(machine, case, sec3):
    events = []
    strings = {'next': STRINGS}
    names = bytearray(0x1000)
    for i, n in enumerate(case['names']):
        raw = n.encode('latin1')[:31]
        names[i * 32:i * 32 + len(raw)] = raw
    model = bytearray(0x40)
    struct.pack_into('<h', model, 0x24, case['count'])
    struct.pack_into('<I', model, 0x34, NAMES)
    struct.pack_into('<I', model, 0x38, INDEX)
    entry = bytearray(0x400)
    sub = case['sub'].encode('latin1').ljust(0x100, b'\0')   # strcat scans whole dwords

    def ctor(m):
        this, source = m.uc.reg_read(m.x86.UC_X86_REG_ECX), m.argument(0)
        m.uc.mem_write(this, struct.pack('<I', source) + bytes(0x18))
        return this, 4

    def load(m):
        path = string_at(m, m.argument(0))
        events.append(('load', path, m.argument(1), m.argument(2)))
        return case['files'].get(path, 0x7530), 0xc

    def find(m):
        name = string_at(m, m.argument(0))
        events.append(('find', name))
        hit = case['cache'].get(name)
        if not hit:
            return 0, 4
        index, path = hit
        raw = path.encode('latin1')[:250] + b'\0'
        m.write(ENTRY, struct.pack('<I', index) + raw)
        return ENTRY, 4

    def reuse(m):
        events.append(('reuse', m.argument(0), string_at(m, m.argument(1)), m.argument(2), m.argument(3)))
        return 1, 0x10

    def getter(m):
        if m.argument(0) != case['model_index']:
            raise ValueError('model index')
        return (MODEL if case['present'] else 0), 4

    def message(m):
        events.append(('error',))
        return 0

    def splitpath(m):
        # MSVC _splitpath, extension only (drive/dir/fname are NULL here): from the last '.' after the last
        # '\\' or '/', at most 255 characters.
        path, drive, directory, fname, ext = (m.argument(k) for k in range(5))
        if drive or directory or fname:
            raise ValueError('unmodelled _splitpath outputs')
        name = m.cstring(path, 300)
        base = max(name.rfind('\\'), name.rfind('/'))
        dot = name.rfind('.')
        out = name[dot:] if dot > base else ''
        m.uc.mem_write(ext, out.encode('latin1')[:255] + b'\0')
        return 0
    stubs = {MODEL_CONTAINER: lambda m: CONTAINER, MODEL_GET: getter, STR_CTOR: ctor, STR_DTOR: lambda m: 0,
             LOAD: load, FIND: find, REUSE: reuse, SPLITPATH: splitpath, TEXT: lambda m: (MSG, 4), FORMAT: lambda m: 0, MESSAGE: message}
    regions = [am.defined_region('model', MODEL, bytes(model), writable=False),
               am.defined_region('names', NAMES, bytes(names), writable=False),
               am.undefined_region('index', INDEX, 0x100),
               am.defined_region('container', CONTAINER, bytes(0x10), writable=False),
               am.undefined_region('entry', ENTRY, 0x400),
               am.defined_region('subfolder', STRINGS, sub, writable=False),
               am.defined_region('message', MSG, b'missing %s'.ljust(0x40, b'\0'), writable=False),
               am.defined_region('locale-changed', LOCALE_CHANGED, bytes(4), writable=False),
               am.defined_region('sse2-flag', SSE2_FLAG, bytes(4), writable=False),
               am.defined_region('section3-init', SECTION3_BASE, sec3[:SECTION3_INIT], writable=False)]
    result = machine.execute(OPEN_TEXTURE, [case['model_index'], STRINGS, case['wrap'], case['filter']],
                             regions, stubs)
    stop = None if result['ok'] else {'stopped': result['stopped'], 'error': result['error'],
                                      'checks': {k: v for k, v in result['checks'].items() if not v}}
    raw = result['regions'].get('index', bytes(0x100))
    n = max(case['count'], 0) if case['present'] else 0
    indices = list(struct.unpack_from(f'<{n}i', raw)) if n else []
    return events, indices, stop


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
        events.append(('error',))
    host = Host(None, LOAD_FN(load), FIND_FN(find), REUSE_FN(reuse), ERROR_FN(error))
    indices = []
    if case['present']:
        for i in range(max(case['count'], 0)):
            step = C.c_int()
            indices.append(lib.mu_tl_open(C.byref(host), case['sub'].encode('latin1'),
                                          case['names'][i].encode('latin1')[:31], case['wrap'], case['filter'],
                                          C.byref(step)))
    return events, indices


def family_open(machine, lib, cases, sec3, seed='g2-open'):
    g = random.Random(seed)
    tally = vo_tally('open_texture')
    for n in range(cases):
        case = synthetic_case(g)
        events, indices, stop = run_client(machine, case, sec3)
        c_events, c_indices = run_c(lib, case)
        tally.add(stop is None and events == c_events and indices == c_indices,
                  {'case': n, 'names': case['names'], 'sub': case['sub'], 'client': events[:6], 'c': c_events[:6],
                   'indices': (indices, c_indices)}, stop)
        for e in events:
            tally.count(e[0])
        tally.count('meshes', len(indices))
        tally.count('specials', sum(1 for v in indices if v in (0x7725, 0x791a, 0x7776, 0x791c, 0x7869, 0x7818,
                                                                  0x77c7, 0x78ba)))
        if not case['present']:
            tally.count('no model')
        if case['count'] < 0:
            tally.count('negative mesh count')
    return tally.report()


def family_folders(lib, folders):
    """Every OpenTexture call of the world pass for types 0..299 names "Object<mu_objects_folder(world)>\\"."""
    tally = vo_tally('object_texture_folder')
    lib.mu_objects_folder.argtypes = [C.c_int32]
    lib.mu_objects_folder.restype = C.c_int32
    for world, subs in folders:
        want = f'Object{lib.mu_objects_folder(world)}\\'
        tally.add(bool(subs) and all(s == want for s in subs), {'world': world, 'want': want,
                                                                 'client': sorted(set(subs))[:3]})
        tally.count('calls', len(subs))
    return tally.report()


def family_event(machine, camera):
    tally = vo_tally('event_world')
    for world in range(-8, 301):
        got = []
        for start in (EVENT_A, EVENT_B):
            r = machine.execute(start, [], [am.defined_region('world', WORLD, struct.pack('<i', world),
                                                              writable=False)], {})
            got.append(r['eax'] & 0xff if r['ok'] else None)
        stop = None if None not in got else 'stopped'
        client = int(bool(got[0]) or bool(got[1])) if stop is None else None
        tally.add(stop is None and client == camera.mu_world_camera_event_world(world),
                  {'world': world, 'client': got}, stop)
        if client:
            tally.count('event worlds')
    return tally.report()


# ---------------------------------------------------------------- mutants
MUTANTS = [
    ('texture_lookup.c', 'if (hit >= 0) {', 'if (hit > 0) {', 'open_texture'),
    ('texture_lookup.c', '{"Item\\\\", "Item\\\\Texture\\\\"}', '{"Item\\\\Texture\\\\", "Item\\\\"}', 'open_texture'),
    ('texture_lookup.c', 'GL_NEAREST_, GL_CLAMP_);\n            index = hit;', 'GL_NEAREST_, 0x2901u);\n            index = hit;',
     'open_texture'),
    ('texture_lookup.c', 'return h->load(h->context, path, GL_NEAREST_, wrap);',
     'return h->load(h->context, path, filter, wrap);', 'open_texture'),
    ('texture_lookup.c', 'if (strncmp(name, "level_", 6) == 0)', 'if (prefix_nocase(name, "level_"))',
     'open_texture'),
    ('texture_lookup.c', 'if (prefix_nocase(name, "HQskin3"))\n        return MU_TL_HQ_SKIN3;\n', '', 'open_texture'),
    ('texture_lookup.c', "name[2] == 'i' && name[3] == 'r'", "name[2] == 'i'", 'open_texture'),
    ('texture_lookup.c', "if (kind == 'j')", "if (kind == 'j' || kind == 'b')", 'open_texture'),
    ('texture_lookup.c', "            dot = p;\n", "            dot = dot ? dot : p;\n", 'open_texture'),
    ('texture_lookup.c', "                if (h->error)\n", "                if (0)\n", 'open_texture'),
    ('texture_lookup.c', 'k < 2 && index == MU_TL_DEFAULT', 'k < 1 && index == MU_TL_DEFAULT', 'open_texture'),
    ('texture_lookup.c', 'if (name[0] == \'s\' && name[1] == \'k\' && name[2] == \'i\')',
     'if (tolower((unsigned char)name[0]) == \'s\' && name[1] == \'k\' && name[2] == \'i\')', 'open_texture'),
    ('texture_preload.inc', None, 'drop-startup', 'startup_table'),
    ('texture_preload.inc', None, 'swap-world', 'world_preloads'),
    ('objects.c', '        return 131;', '        return 129;', 'object_texture_folder'),
    ('client_world_camera.c', 'world == 0x3f ||', 'world == 0x3e ||', 'event_world'),
    ('client_world_camera.c', 'world <= 0x5a', 'world < 0x5a', 'event_world'),
]


def mutate_preload(text, how):
    lines = text.split('\n')
    if how == 'drop-startup':
        i = next(k for k, l in enumerate(lines) if 'Skeleton' in l)
        del lines[i]
    else:   # the first two world_extra lines of a world with two or more trade places
        start = lines.index('static const mu_tl_preload world_extra[] = {')
        lines[start + 1], lines[start + 2] = lines[start + 2], lines[start + 1]
    return '\n'.join(lines)


def build_mutant(tmp, file, old, new):
    dest = Path(tmp)
    if file == 'client_world_camera.c':
        for d in ('camera', 'record-math'):
            shutil.copytree(ROOT / 'reconstructed' / d, dest / d, ignore=shutil.ignore_patterns('*.dylib', '*.so'))
        path = dest / 'camera' / file
        s = path.read_text()
        assert old in s, old
        path.write_text(s.replace(old, new, 1))
        subprocess.run(['make', '-s', '-C', str(dest / 'camera')], check=True)
        return dest / 'camera' / f'libclient_camera.{SUFFIX}'
    if file == 'objects.c':
        for d in ('objects', 'terrain', 'record-math', 'model-codec', 'movement'):
            shutil.copytree(ROOT / 'reconstructed' / d, dest / d, ignore=shutil.ignore_patterns('*.dylib', '*.so',
                                                                                             '__pycache__'))
        path = dest / 'objects' / file
        s = path.read_text()
        assert old in s, old
        path.write_text(s.replace(old, new, 1))
        subprocess.run(['make', '-s', '-C', str(dest / 'objects')], check=True)
        return dest / 'objects' / f'libobjects.{SUFFIX}'
    for f in ('texture_lookup.c', 'texture_lookup.h', 'texture_preload.inc'):
        shutil.copy(ROOT / 'reconstructed/objects' / f, dest / f)
    path = dest / file
    s = path.read_text()
    if old is None:
        s = mutate_preload(s, new)
    else:
        assert old in s, old
        s = s.replace(old, new, 1)
    path.write_text(s)
    out = dest / f'libtl.{SUFFIX}'
    subprocess.run(['clang', '-std=c11', '-O2', '-shared', '-fPIC', str(dest / 'texture_lookup.c'), '-o', str(out)],
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
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()

    rec, sec3 = recorder(a)
    startup_log, null_pages = record_startup(rec)
    startup, foreign, _ = texture_pairs(startup_log)
    run = vo.ModelRun(rec)
    worlds, late, folders = [], {}, []
    for world in range(200):
        log = run.run(world)
        folders.append((world, [e[2] for e in log if e[0] == 'texture' and e[1] < 300]))
        entries, _, n_late = texture_pairs(log, extras_only=True)
        worlds.append((world, entries))
        if n_late:
            late[world] = n_late
    run.close()
    if a.emit_table:
        emit_table(a.emit_table, startup, [(w, e) for w, e in worlds if e])
        print('wrote', a.emit_table)
        return 0

    text = vo.load_pinned(a.text, vo.TEXT_BYTES, vo.TEXT_SHA256, 'text')
    data = vo.load_pinned(a.data, vo.DATA_BYTES, vo.DATA_SHA256, 'data')
    machine = am.ActorMachine(text, data)
    subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
    subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/camera')], check=True)
    lib = bind(C.CDLL(str(ROOT / f'reconstructed/objects/libobjects.{SUFFIX}')))
    camera = bind_camera(C.CDLL(str(ROOT / f'reconstructed/camera/libclient_camera.{SUFFIX}')))
    report = {'inputs': {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
                         'section3_sha256': vo.SECTION3_SHA256},
              'bodies': {n: {'start': hex(s), 'end': hex(e),
                             'sha256': hashlib.sha256(text[s - am.TEXT_BASE:e - am.TEXT_BASE]).hexdigest()}
                         for n, (s, e) in BODIES.items()},
              'startup_recording': {'texture_pairs': len(startup), 'foreign_texture_calls': foreign,
                                    'null_page_writes': null_pages},
              'families': {}, 'mutants': []}
    fam = report['families']
    fam['open_texture'] = family_open(machine, lib, a.cases, sec3)
    fam['startup_table'], fam['world_preloads'] = family_tables(lib, startup, worlds, late)
    fam['event_world'] = family_event(machine, camera)
    fam['object_texture_folder'] = family_folders(lib, folders)
    for name, r in fam.items():
        print(name, {k: r[k] for k in ('cases', 'equal', 'stopped', 'mismatch_count')}, flush=True)
    if a.mutations:
        for file, old, new, family in MUTANTS:
            with tempfile.TemporaryDirectory(prefix='worlds-g2-') as tmp:
                path = build_mutant(tmp, file, old, new)
                if family == 'event_world':
                    r = family_event(machine, bind_camera(C.CDLL(str(path))))
                elif family == 'object_texture_folder':
                    r = family_folders(bind(C.CDLL(str(path))), folders)
                else:
                    mlib = bind(C.CDLL(str(path)))
                    if family == 'open_texture':
                        r = family_open(machine, mlib, min(a.cases, 1500), sec3)
                    else:
                        r = dict(zip(('startup_table', 'world_preloads'),
                                     family_tables(mlib, startup, worlds, late)))[family]
            m = {'family': family, 'file': file, 'change': new if old is not None else new,
                 'detected': r['mismatch_count'], 'stopped': r['stopped']}
            report['mutants'].append(m)
            print('mutant', m, flush=True)
    if a.output:
        a.output.write_text(json.dumps(report, indent=2) + '\n')
    bad = any(r['equal'] != r['cases'] for r in fam.values())
    bad |= any(not m['detected'] or m['stopped'] for m in report['mutants'])
    return int(bad)


if __name__ == '__main__':
    raise SystemExit(main())
