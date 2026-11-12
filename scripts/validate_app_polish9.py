#!/usr/bin/env python3
"""APP-POLISH-009: original resize dispatch and the bounded native viewport adaptation.

Unicorn executes the original collection resize 0x00ac09b2 and handler
0x00aae4ae. Container iteration and the GFx API are explicit recording stubs.
The native fit has no original equivalent: it extends the fixed original scales
to the native minimum size. Its bounds/scale invariants have compiled mutants.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import random
import subprocess
import tempfile
import time

import pins
import validate_gfx3 as gfx

ROOT = Path(__file__).resolve().parents[1]


def original_resize(text, data, width, height, occupied):
    m = gfx.machine(text, data)
    result, index = [], [0]
    owner = m.alloc(0x40, define=True)
    slot = m.alloc(4, define=True)
    windows = [m.alloc(0x80, define=True) if present else 0 for present in occupied]
    def stub(address, fn):
        m.stub(address, fn, gfx.cm.stdcall_cleanup(text, address))
    stub(0x00ac1a17, lambda _: m.args(1)[0])  # begin iterator, index starts at zero
    stub(0x00ac1ab9, lambda _: m.args(1)[0])  # end iterator
    stub(0x00ac14bf, lambda _: int(index[0] < len(windows)))
    def increment(_):
        index[0] += 1
        return 0
    stub(0x00ac159a, increment)
    def dereference(_):
        m.put32(slot, windows[index[0]])
        return slot
    stub(0x00ac152e, dereference)
    stub(0x00ab03cf, lambda _: 1)
    stub(0x00ab041b, lambda _: 0x30000100)
    stub(0x00ab0d72, lambda _: 0)
    def invoke(_):
        window, method, fmt, w, h = m.args(5)
        result.append([windows.index(window), gfx.Values(m, text).cstr(method), w, h])
    m.stub(gfx.WINDOW_INVOKE, invoke, 0)
    gfx.allow_functions(m, text, 0x00ac09b2, gfx.SET_WINDOW_SIZE)
    m.call(0x00ac09b2, args=(width, height), ecx=owner)
    assert (m.u32(owner + 0x10), m.u32(owner + 0x14)) == (width, height)
    return result


MUTANTS = {
    'grow': ('fmin(1.0,', 'fmax(1.0,'),
    'width': ('available_w / w', 'available_w * w'),
    'height': ('available_h / h', 'available_h * h'),
    'right': ('available_w - w * out.scale', 'available_w'),
    'bottom': ('available_h - h * out.scale', 'available_h'),
    'left': ('fmax(0.0, fmin(x,', 'fmin(0.0, fmin(x,'),
    'top': ('fmax(0.0, fmin(y,', 'fmin(0.0, fmin(y,'),
}


def native_fit(work, mutation=None):
    header = (ROOT / 'native/gfx/mu_gfx_layout.h').read_text()
    if mutation:
        old, new = MUTANTS[mutation]
        assert header.count(old) == 1, mutation
        header = header.replace(old, new)
    source = work / 'fit.c'
    source.write_text(header + '''
void probe(const double *a, double *out) {
    mu_gfx_fit f = mu_gfx_fit_window(a[0],a[1],a[2],a[3],a[4],a[5]);
    out[0]=f.x; out[1]=f.y; out[2]=f.scale;
}
''')
    lib = work / 'fit.so'
    subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-O2', '-shared', '-fPIC',
                    str(source), '-lm', '-o', str(lib)], check=True, capture_output=True)
    api = ctypes.CDLL(str(lib))
    api.probe.argtypes = [ctypes.POINTER(ctypes.c_double)] * 2
    def run(a):
        out = (ctypes.c_double * 3)()
        api.probe((ctypes.c_double * 6)(*a), out)
        return list(out)
    return run


def fit_errors(run, cases):
    errors = []
    for a in cases:
        x, y, w, h, aw, ah = a
        ox, oy, scale = run(a)
        # Independently check containment, no enlargement, maximal fit and
        # preservation of already-valid positions, rather than restating C.
        valid = 0 < scale <= 1 and -1e-7 <= ox <= aw - w*scale + 1e-7
        valid &= -1e-7 <= oy <= ah - h*scale + 1e-7
        valid &= scale == 1 or abs(w*scale-aw) < 1e-7 or abs(h*scale-ah) < 1e-7
        if 0 <= x <= aw-w*scale:
            valid &= abs(ox-x) < 1e-7
        if 0 <= y <= ah-h*scale:
            valid &= abs(oy-y) < 1e-7
        if not valid:
            errors.append([a, [ox, oy, scale]])
    return errors


def run(args):
    started = time.monotonic()
    text, data = pins.TEXT.read(args.text), pins.DATA.read(args.data)
    rng = random.Random(9)
    sizes = [(640,480),(800,600),(1024,600),(1024,699),(1024,700),(1024,768),
             (1280,720),(1280,800),(1280,1024),(1366,768),(1440,900),(1600,1000),
             (1680,1050),(1920,1080),(2560,1440)]
    checked = 0
    for w, h in sizes:
        for occupied in ([], [False], [True], [True, False, True, True]):
            expected = [[i, 'SetWindowSize', w, h] for i, v in enumerate(occupied) if v]
            assert original_resize(text, data, w, h, occupied) == expected
            checked += 1
    cases = [(-100, -100, 900, 700, 640, 406), (800, 600, 300, 600, 1024, 650),
             (50, 50, 300, 600, 1920, 970)]
    for _ in range(args.cases - len(cases)):
        cases.append(tuple(rng.uniform(-1500, 2500) for _ in range(2)) +
                     tuple(rng.uniform(1, 3000) for _ in range(4)))
    caught = {}
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        errors = fit_errors(native_fit(work), cases)
        assert not errors, errors[:3]
        if args.mutants:
            for name in MUTANTS:
                d = work / name
                d.mkdir()
                caught[name] = len(fit_errors(native_fit(d, name), cases))
                assert caught[name] > 0, name
    return {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
            'families': {'resize': {'cases': checked, 'mismatches': 0},
                         'native_fit': {'cases': len(cases), 'mismatches': 0}},
            'mismatches': 0, 'mutants_caught': caught, 'wall_seconds': time.monotonic()-started}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--text')
    ap.add_argument('--data')
    ap.add_argument('--cases', type=int, default=4096)
    ap.add_argument('--mutants', action='store_true')
    ap.add_argument('--out')
    args = ap.parse_args()
    result = run(args)
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
