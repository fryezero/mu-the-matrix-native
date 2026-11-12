#!/usr/bin/env python3
"""ITEMS-UI-001: equipment cursor arithmetic and icon-bit draw streams.

Executes the slot wrapper's CVTTSS2SI arguments and 0x00ec4bf2 together,
plus the original WM_MOUSEMOVE normalization/clamp ranges. Option/luck bits
are tested through the original RenderObjDraw and native item pass recorder.
Only captured client text/data and authored records are used.
"""
from __future__ import annotations
import argparse
import ctypes as C
import hashlib
import json
import random
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pins
from validate_item_callers import Client

HEADER = ROOT / 'native/gfx/items_ui.h'
MUTANTS = {
    'left_edge': ('mouse_x >= x', 'mouse_x > x'),
    'right_edge': ('mouse_x < mu_items_ui_add(x, w)', 'mouse_x <= mu_items_ui_add(x, w)'),
    'top_edge': ('mouse_y >= y', 'mouse_y > y'),
    'bottom_edge': ('mouse_y < mu_items_ui_add(y, h)', 'mouse_y <= mu_items_ui_add(y, h)'),
    'width_axis': ('w = mu_items_ui_trunc(slot[2])', 'w = mu_items_ui_trunc(slot[3])'),
    'endpoint_rounding': ('mu_items_ui_add(x, w)', '(mu_items_ui_trunc(slot[0] + slot[2]) + (w & 0))'),
    'mouse_rounding': ('mu_items_ui_trunc((float)point /', 'mu_items_ui_trunc(0.5f + (float)point /'),
    'mouse_clamp': ('value > extent ? extent : value', 'value > extent ? extent - 1 : value'),
}

def build(work, source, name):
    header = work / (name + '.h')
    header.write_text(source)
    host = work / (name + '.c')
    host.write_text('#include "' + header.name + '"\n'
                    'int cursor(const float *r,int x,int y){return mu_items_ui_cursor(r,x,y);}\n'
                    'int mouse(double p,int s,int e){return mu_items_ui_mouse(p,s,e);}\n')
    path = work / (name + ('.dylib' if sys.platform == 'darwin' else '.so'))
    subprocess.run(['clang', '-std=c11', '-O2', '-ffp-contract=off', '-fno-fast-math', '-Wall', '-Wextra',
                    '-Werror', '-shared', '-fPIC', str(host), '-o', str(path)], check=True, capture_output=True)
    lib = C.CDLL(str(path))
    lib.cursor.argtypes = [C.POINTER(C.c_float), C.c_int32, C.c_int32]
    lib.mouse.argtypes = [C.c_double, C.c_int32, C.c_int32]
    return lib

def family():
    return {'cases': 0, 'mismatches': 0, 'examples': []}

def check(fam, got, want, context=None):
    fam['cases'] += 1
    if got != want:
        fam['mismatches'] += 1
        if len(fam['examples']) < 3:
            fam['examples'].append({'got': got, 'want': want, 'context': context})

def put(client, address, *values):
    client.uc.mem_write(address, struct.pack('<' + 'I' * len(values), *(v & 0xffffffff for v in values)))

def arithmetic(client, lib, cases, seed):
    fams = {name: family() for name in ('cursor', 'mouse')}
    rng = random.Random(seed)
    x86 = client.x86
    frame, stack = client.FRAME, client.STACK + 0x20000
    vectors = []
    for r in ((10.9, 20.9, 30.9, 40.9), (-10.9, -20.9, 30.9, 40.9), (0, 0, 0, 30),
              (100.75, 200.25, 2.5, 1.75), (0, 0, 30, -1), (2147483520., 0, 256, 20),
              (-2147483648., -2147483648., -1, -1)):
        x, y, w, h = map(int, r)
        for mx in (x-1, x, x+1, x+w-1, x+w):
            for my in (y-1, y, y+1, y+h-1, y+h):
                if -2**31 <= mx < 2**31 and -2**31 <= my < 2**31:
                    vectors.append((r, mx, my))
    for _ in range(cases):
        r = tuple(rng.uniform(-100, 900) for _ in range(2)) + tuple(rng.uniform(-2, 150) for _ in range(2))
        mx = rng.choice((int(r[0]), int(r[0])+int(r[2]), rng.randrange(-100, 1000)))
        my = rng.choice((int(r[1]), int(r[1])+int(r[3]), rng.randrange(-100, 800)))
        vectors.append((r, mx, my))
    for rect, mx, my in vectors:
        slot = (C.c_float * 4)(*rect)
        client.uc.mem_write(frame + 0xc, bytes(slot))
        put(client, 0x0bdc5ad8, mx, my)
        error = client.run(0x016c246e, 0x016c248b, stack, frame)
        if error:
            raise RuntimeError(error)
        want = client.uc.reg_read(x86.UC_X86_REG_EAX) & 255
        check(fams['cursor'], lib.cursor(slot, mx, my), want, [list(rect), mx, my])
    for k in range(cases + 64):
        width, height = rng.choice(((640,480), (1280,800), (1366,768), (1722,1048), (2560,1440)))
        px, py = rng.randrange(-100, width+100), rng.randrange(-100, height+100)
        if k < 64:
            px, py = (k % 8) - 2, height + (k // 8) - 3
        client.uc.mem_write(0x06fbcd94, struct.pack('<2f', width/640, height/480))
        put(client, frame + 0x14, (px & 0xffff) | ((py & 0xffff) << 16))
        for start, stop in ((0x0121012c, 0x0121016b), (0x012101ab, 0x012101f7)):
            error = client.run(start, stop, stack, frame)
            if error:
                raise RuntimeError(error)
        want = struct.unpack('<2i', client.uc.mem_read(0x0bdc5ad8, 8))
        check(fams['mouse'], (lib.mouse(px, width, 640), lib.mouse(py, height, 480)), want)
    return fams

def option_bits(world_args, cases):
    import validate_renderchar as vr
    renderer = C.CDLL(str(vr.LIBRARY))
    fam = family()
    # These are ordinary weapon/armour bodies and the level-14/15 special body.
    # Reuse only each world's engine host; client_stream reseeds its model/record inputs each time.
    world = vr.ColourWorld(*world_args)
    def factory(*unused):
        world.calls.clear()
        world.records.clear()
        return world
    for item_type in (0xae6 + 68, 0xae6 + 8*512, 0x3895):
        for level in range(min(cases, 16)):
            for excellent, ext in ((0, 0), (1, 0), (0, 2)):
                config = dict(item_level=level << 3, option1=excellent, ext=ext, quality=5,
                              time=vr.f2u(1234.0), render_type=2)
                case = vr.classify_case(item_type, config)
                status, plain = vr.c_stream(renderer, case)
                for bits in (0, 1, 2, 3, 4, 5, 6, 7, 128, 129, 130, 131, 132, 133, 134, 135):
                    full = dict(case, item_level=(level << 3) | bits)
                    result, stream, _, _ = vr.client_stream(world_args, full, factory)
                    check(fam, (result['ok'], status, stream), (True, 0, plain), [item_type, level, excellent, ext, bits])
    return fam

def ordering(text):
    from validate_inventory_fx import call_target, direct_callers
    fam = family()
    # This proves the captured per-window sequence, not the opaque main-game hook.
    for site, target in ((0x01859ab6,0x0169270e), (0x01859bb1,0x0169270e),
                         (0x00ac9666,0x00abfcca), (0x01858c99,0x00ac964e)):
        check(fam, call_target(text,site),target,hex(site))
    check(fam, direct_callers(text,0x00abfcca),[0x00ac9666])
    fam['limit'] = 'Main-game UI reaches opaque hook 0x10b3e920 at 0x01859cf1; not followed.'
    return fam

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=int, default=3000)
    parser.add_argument('--seed', type=int, default=0x171001)
    parser.add_argument('--mutations', action='store_true')
    args = parser.parse_args(argv)
    started = time.monotonic()
    text, data = pins.TEXT.read(exit=True), pins.DATA.read(exit=True)
    client = Client(text, data)
    client.uc.mem_map(0x0bdc5000,0x1000)
    client.uc.mem_map(0x06fbc000,0x1000)
    source = HEADER.read_text()
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256}
    with tempfile.TemporaryDirectory(prefix='items-ui-') as tmp:
        work = Path(tmp)
        lib = build(work, source, 'adapter')
        report['families'] = arithmetic(client,lib,args.cases,args.seed)
        report['families']['option_bits'] = option_bits((text,data,pins.FLAG.read(exit=True),pins.FEATURE.read(exit=True)),args.cases)
        report['families']['ordering'] = ordering(text)
        if args.mutations:
            report['mutants'] = {}
            for name,(old,new) in MUTANTS.items():
                if source.count(old) != 1:
                    raise RuntimeError(f'{name}: expected one anchor, found {source.count(old)}')
                mutant = build(work,source.replace(old,new),name)
                report['mutants'][name] = sum(f['mismatches'] for f in arithmetic(client,mutant,200,args.seed).values())
    report['routines'] = {hex(a): {'end':hex(b),'sha256':hashlib.sha256(text[a-0x401000:b-0x401000]).hexdigest()}
                          for a,b in ((0x00ec4bf2,0x00ec4c2d),(0x016c246e,0x016c248b),
                                      (0x0121012c,0x0121016b),(0x012101ab,0x012101f7))}
    report['seconds'] = time.monotonic()-started
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps({'families':{k:{a:f[a] for a in ('cases','mismatches')} for k,f in report['families'].items()},
                      'mutants':report.get('mutants',{}),'seconds':report['seconds']}))
    return int(any(f['mismatches'] for f in report['families'].values()) or
               any(not n for n in report.get('mutants',{}).values()))

if __name__ == '__main__':
    sys.exit(main())
