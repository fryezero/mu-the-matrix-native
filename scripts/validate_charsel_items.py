#!/usr/bin/env python3
"""CHARSEL-ITEMS-001: selection equipment caller arguments against pinned instructions.

Executes the ordinary part caller 0x0136a661..0x0136a6d7, the hand caller
0x0136c3e7..0x0136c428, the wing caller 0x0139eeb6..0x0139eefc,
and RenderLinkItem's common RenderObjDraw caller
0x012c6a1f..0x012c6a83. The vector-address getter is an authored identity stub.
No packet handler, account state, or live process is used. The native adapter
reads authored records only; absent records keep the pre-existing mesh path.
"""
from __future__ import annotations
import argparse
import ctypes as C
import json
import hashlib
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pins
from validate_item_callers import Client

HEADER = ROOT / 'native/charsel/charsel_items.h'
MUTANTS = {
    'model_base': ('0xae6 + record->code', '0xae7 + record->code'),
    'level': ('glow->level = record->level;', 'glow->level = record->level >> 1;'),
    'excellent': ('record->option != 0', 'record->option == 0'),
    'part_ext': ('? record->ext : 0', '? 0 : 0'),
    'link_ext': ('? record->ext : 0', '? record->ext : record->ext'),
    'unset': ('|| !record->set', '|| record->set'),
    'slot_zero': ('slot < 1 ||', 'slot < 0 ||'),
}

class Record(C.Structure):
    _fields_ = [('set', C.c_uint8), ('level', C.c_uint8), ('option', C.c_uint8), ('ext', C.c_uint8),
                ('code', C.c_int32)]

class Glow(C.Structure):
    _fields_ = [('type', C.c_int32), ('level', C.c_int32), ('option', C.c_int32), ('ext', C.c_int32),
                ('has_record', C.c_int32), ('kind_a', C.c_uint8), ('kind_b', C.c_uint8), ('kind', C.c_uint8)]


def build(work, source, name):
    # Keep the header's real include resolution while compiling only the pure adapter.
    header = work / (name + '.h')
    header.write_text(source)
    host = work / (name + '.c')
    host.write_text('#include "' + header.name + '"\n'
                    'int record_glow(const mu_charsel_item_record *r, int s, mu_renderchar_glow *g) '
                    '{ return mu_charsel_record_glow(r, s, g); }\n')
    libpath = work / (name + ('.dylib' if sys.platform == 'darwin' else '.so'))
    subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-shared', '-fPIC',
                    '-I', str(ROOT / 'native/charsel'), str(host), '-o', str(libpath)], check=True,
                   capture_output=True)
    lib = C.CDLL(str(libpath))
    lib.record_glow.argtypes = [C.POINTER(Record), C.c_int, C.POINTER(Glow)]
    return lib


def family():
    return {'cases': 0, 'mismatches': 0, 'examples': []}


def check(fam, got, want):
    fam['cases'] += 1
    if got != want:
        fam['mismatches'] += 1
        if len(fam['examples']) < 3:
            fam['examples'].append({'got': got, 'want': want})


def original(client, slot, record):
    """Return type, encoded level, excellent, ext at the original draw call."""
    uc, ebp = client.uc, client.FRAME
    char, obj, part = client.WORK + 0x4000, client.OBJ, client.WORK + 0x7000
    def w(at, *values):
        uc.mem_write(at, struct.pack('<' + 'I' * len(values), *(v & 0xffffffff for v in values)))
    w(ebp + 8, char, obj, 0)
    uc.mem_write(part, struct.pack('<hBBB', 0xae6 + record.code, record.level, record.option, record.ext))
    w(obj + 0xdc, 0x3f800000)
    w(ebp - 0x3c, 1)
    if slot < 6:
        w(ebp - 0x80, part)
        w(ebp - 0x90, 0xae6 + record.code)
        start, stop, count = 0x0136a661, 0x0136a6d7, 16
    elif slot < 8:
        w(ebp - 0x10, part)
        start, stop, count = 0x0136c3e7, 0x0136c428, 12
    else:
        w(ebp - 0x24, part)
        start, stop, count = 0x0139eeb6, 0x0139eefc, 12
    error = client.run(start, stop, client.STACK + 0x20000, ebp)
    if error:
        raise RuntimeError(error)
    esp = uc.reg_read(client.x86.UC_X86_REG_ESP)
    args = struct.unpack('<' + 'I' * count, uc.mem_read(esp, count * 4))
    if slot < 6:
        return args[1], args[5], args[6], args[7]
    # Feed the actual link caller's output into the shared RenderObjDraw call.
    w(ebp + 0x14, char, part, args[5], args[6], args[7])
    w(ebp + 0x30, 2)
    w(ebp - 0x110, obj)
    w(ebp - 0x120, obj)
    error = client.run(0x012c6a1f, 0x012c6a83, client.STACK + 0x20000, ebp)
    if error:
        raise RuntimeError(error)
    esp = uc.reg_read(client.x86.UC_X86_REG_ESP)
    args = struct.unpack('<13I', uc.mem_read(esp, 52))
    return args[1], args[4], args[5], args[6]


def families(client, lib, cases, seed):
    rng = random.Random(seed)
    out = {name: family() for name in ('part_args', 'link_args', 'fallback')}
    for n in range(cases):
        for slot in range(1, 9):
            r = Record(1, n % 16, (n // 16) % 2, rng.randrange(256), rng.randrange(8192))
            g = Glow()
            active = lib.record_glow(C.byref(r), slot, C.byref(g))
            got = (g.type, g.level << 3, g.option, g.ext) if active else None
            check(out['part_args' if slot < 6 else 'link_args'], got, original(client, slot, r))
    for slot in range(-2, 12):
        for active in (0, 1):
            r = Record(active, 15, 1, 255, 0)
            g = Glow(type=-37, level=-19)
            result = lib.record_glow(C.byref(r), slot, C.byref(g))
            want = int(bool(active) and 1 <= slot < 9)
            check(out['fallback'], result, want)
            if not want:
                check(out['fallback'], (g.type, g.level), (-37, -19))
    return out


def sinks(text):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    fam = family()
    for start, end, expected in ((0x018576b3, 0x01857ed9, 0x01857aee),):
        sites = [i.address for i in md.disasm(text[start-0x401000:end-0x401000], start)
                 if i.mnemonic == 'call' and i.op_str == '0x1363260']
        check(fam, sites, [expected])
    return fam


def mesh_passes(world_args, lib, cases, seed):
    """The adapter's resulting levels/options through the existing item pass port.

    Quality 0..5, levels 0..15, excellent on/off, ancient body controls and
    two fixed clocks. Engine services are the existing renderchar recorders.
    """
    import validate_renderchar as vr
    renderer = C.CDLL(str(vr.LIBRARY))
    class SelectionWorld(vr.ColourWorld):
        def install(self):
            super().install()
            self.m.ensure(0x01d1df70, 4)
            self.m.w32(0x01d1df70, 5)
    fam = family()
    rng = random.Random(seed)
    for slot in (2, 6):
        for level in range(min(cases, 16)):
            for option in (0, 1):
                for quality in range(6):
                    for time in (0.0, 1234.0):
                        record = Record(1, level, option, (2, 16, 32)[level % 3], 8*512 if slot == 2 else 4)
                        glow = Glow()
                        lib.record_glow(C.byref(record), slot, C.byref(glow))
                        case = vr.random_case_any(rng, glow.type)
                        case.update(item_level=glow.level << 3, option1=glow.option, ext=glow.ext,
                                    render_type=2, alpha=vr.f2u(1.0), object_alpha=vr.f2u(1.0),
                                    light=[vr.f2u(1.4)]*3, model_light=[vr.f2u(1.4)]*3,
                                    model_shade=[vr.f2u(1.4)]*3, model_level=0, model_ca=0,
                                    a10=0xffffffff, a11=0xffffffff, a12=3, blend_mesh=0xffffffff,
                                    blend_light=0, u=0, v=0, time=vr.f2u(time), quality=quality,
                                    record=(0, 0, 0), enchant=[vr.f2u(v) for v in (0.4, 0.6, 1.0)],
                                    object_hidden=0, lighting=0 if slot >= 6 else 1)
                        result, original_stream, _, _ = vr.client_stream(world_args, case, SelectionWorld)
                        status, native_stream = vr.c_stream(renderer, case)
                        check(fam, (result['ok'], status, native_stream), (True, 0, original_stream))
    return fam


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--cases', type=int, default=1000)
    p.add_argument('--seed', type=int, default=0xc5e1)
    p.add_argument('--mutations', action='store_true')
    args = p.parse_args(argv)
    text, data = pins.TEXT.read(exit=True), pins.DATA.read(exit=True)
    world_args = text, data, pins.FLAG.read(exit=True), pins.FEATURE.read(exit=True)
    client = Client(text, data)
    # Authored identity implementation of the vector-address getter only.
    client.uc.mem_write(0x00cfc94a, b'\x89\xc8\xc3')
    source = HEADER.read_text()
    with tempfile.TemporaryDirectory(prefix='charsel-items-') as tmp:
        work = Path(tmp)
        lib = build(work, source, 'adapter')
        report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
                  'families': families(client, lib, args.cases, args.seed)}
        report['families']['selection_sink'] = sinks(text)
        report['families']['mesh_passes'] = mesh_passes(world_args, lib, args.cases, args.seed)
        report['routines'] = {hex(a): {'end': hex(b), 'sha256': hashlib.sha256(text[a-0x401000:b-0x401000]).hexdigest()}
                              for a, b in ((0x0136a661, 0x0136a6df), (0x0136c3e7, 0x0136c42d),
                                           (0x0139eeb6, 0x0139ef01), (0x012c6a1f, 0x012c6a88),
                                           (0x018576b3, 0x01857ed9))}
        if args.mutations:
            report['mutants'] = {}
            for name, (old, new) in MUTANTS.items():
                if source.count(old) != 1:
                    raise RuntimeError(f'{name}: expected one anchor, found {source.count(old)}')
                mutant = build(work, source.replace(old, new), name)
                results = families(client, mutant, 32, args.seed)
                report['mutants'][name] = sum(f['mismatches'] for f in results.values())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps(report))
    return int(any(f['mismatches'] for f in report['families'].values()) or
               any(not v for v in report.get('mutants', {}).values()))

if __name__ == '__main__':
    sys.exit(main())
