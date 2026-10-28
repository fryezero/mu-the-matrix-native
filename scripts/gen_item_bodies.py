#!/usr/bin/env python3
"""Generate reviewed rendering parameter recipes from pinned instructions.

Probes infer only constants and copies of draw inputs. Independent randomized
full-function comparisons in validate_item_clusters.py decide which types may
be enabled. Unknown recipes fail regeneration. This is finite instruction
comparison, not symbolic proof of every input or record kind.
"""
import argparse
import ctypes as C
from pathlib import Path
import random
import subprocess
import pins
import validate_renderchar as v
ROOT = Path(__file__).resolve().parents[1]

REVIEWED_TYPES = [
    0x0ef2, 0x0f03, 0x130f, 0x131f, 0x14eb, 0x14f8, 0x150c, 0x1513, 0x1584, 0x18f9,
    0x190d, 0x190e, 0x190f, 0x1910, 0x1911, 0x1912, 0x1938, 0x1957, 0x196d, 0x19bb,
    0x19bc, 0x19be, 0x19bf, 0x1a02, 0x1a03, 0x1a04, 0x1a05, 0x1a06, 0x1a07, 0x1a08,
    0x1a09, 0x1a0a, 0x1a0b, 0x1a0c, 0x1a0d, 0x1a0e, 0x1a0f, 0x1a10, 0x1a11, 0x1a20,
    0x1a43, 0x1a79, 0x1af5, 0x1b0d, 0x1b0e, 0x1b0f, 0x1b10, 0x1b11, 0x1b12, 0x1b38,
    0x1b57, 0x1c02, 0x1c03, 0x1c04, 0x1c05, 0x1c06, 0x1c07, 0x1c08, 0x1c09, 0x1c0a,
    0x1c0b, 0x1c0c, 0x1c0d, 0x1c0e, 0x1c0f, 0x1c10, 0x1c11, 0x1c20, 0x1c43, 0x1c79,
    0x1cf5, 0x1d0d, 0x1d0e, 0x1d0f, 0x1d10, 0x1d11, 0x1d12, 0x1d38, 0x1d57, 0x1d7a,
    0x1e02, 0x1e03, 0x1e04, 0x1e05, 0x1e06, 0x1e07, 0x1e08, 0x1e09, 0x1e0a, 0x1e0b,
    0x1e0c, 0x1e0d, 0x1e0e, 0x1e0f, 0x1e10, 0x1e11, 0x1e20, 0x1e43, 0x1e79, 0x1ef5,
    0x1ef9, 0x1f78, 0x1f79, 0x1f7a, 0x20f5, 0x20f9, 0x2157, 0x2178, 0x2179, 0x217a,
    0x2202, 0x2203, 0x2204, 0x2205, 0x2206, 0x2207, 0x2208, 0x2209, 0x220a, 0x220b,
    0x220c, 0x220d, 0x220e, 0x220f, 0x2210, 0x2211, 0x2220, 0x2243, 0x2279, 0x234a,
    0x234b, 0x234c, 0x234d, 0x234e, 0x234f, 0x2350, 0x2351, 0x2352, 0x2353, 0x2354,
    0x2355, 0x2356, 0x2357, 0x2358, 0x2359, 0x235a, 0x235b, 0x235c, 0x235d, 0x235e,
    0x235f, 0x2360, 0x2361, 0x2362, 0x2363, 0x2364, 0x2365, 0x2366, 0x2367, 0x241d,
    0x241e, 0x241f, 0x2420, 0x2421, 0x2422, 0x2423, 0x2424, 0x2425, 0x2426, 0x2427,
    0x2428, 0x2429, 0x242a, 0x242b, 0x242c, 0x242d, 0x242e, 0x242f, 0x2430, 0x2431,
    0x2432, 0x2433, 0x2434, 0x2435, 0x2436, 0x2437, 0x2438, 0x2439, 0x243a, 0x243b,
    0x243c, 0x243d, 0x243e, 0x243f, 0x2440, 0x2441, 0x2442, 0x2443, 0x2444, 0x2445,
    0x2446, 0x2447, 0x2448, 0x2449, 0x244a, 0x244b, 0x244c, 0x244d, 0x244e, 0x244f,
    0x2450, 0x2451, 0x2452, 0x2453, 0x2454, 0x2455, 0x2456, 0x2457, 0x2458, 0x2459,
    0x245a, 0x245b, 0x245c, 0x245d, 0x245e, 0x245f, 0x2460, 0x2461, 0x2462, 0x2463,
    0x2464, 0x2465, 0x2466, 0x2467, 0x2468, 0x2469, 0x246a, 0x246b, 0x246c, 0x246d,
    0x246e, 0x246f, 0x2470, 0x2471, 0x2472, 0x2473, 0x2474, 0x2475, 0x2476, 0x24ab,
    0x24b3,
]
DIM_TYPES = [0xae6 + group * 512 + index for group in (7, 8, 9, 11)
             for index in (*range(0x11c, 0x12c), 0x13a, 0x15d, 0x193)]
PLAIN_TYPES = [*range(0x234a, 0x2368), *range(0x241d, 0x2477)]

def flat(d):
    return [*d[1], *d[2], d[3], *d[4], d[5]]

def sample(wa, lib, t, lv, seed, opt=0, ext=0):
    tags = []

    class W(v.World):

        def install(self):
            super().install()
            for addr in (0x00966def, 0x00966e4a):
                old = self.m.stubs[addr][0]

                def h(m, old=old):
                    tags.append(m.backtrace()[1])
                    return old(m)
                self.m.stub(addr, h, 32)
    factory = W
    case = v.random_case_any(random.Random(seed), t)
    case.update(item_level=lv << 3, quality=9, option1=opt, ext=ext, record=(0, 0, 0), a10=0xffffffff, a11=0xffffffff, render_type=(2, 0x102, 0x40042)[seed % 3])
    (r, st, other, m) = v.client_stream(wa, case, factory)
    generic_case = dict(case)
    if t in PLAIN_TYPES:
        generic_case['item_level'] = 0
    (_, generic) = v.c_stream(lib, generic_case, True)
    groups = []
    for (d, tag) in zip(st, tags):
        if not groups or tag != groups[-1][0]:
            groups.append((tag, []))
        groups[-1][1].append(d)
    if len(groups) == 3 and len(generic) == 5:
        groups[1:1] = [('empty', []), ('empty', [])]
    if not r['ok'] or other or len(groups) != len(generic):
        return None
    return [(flat(a) + [case['object_alpha']], [(b[0], flat(b)) for b in bs]) for (a, (_, bs)) in zip(generic, groups)]

def infer(samples):
    if any((s is None for s in samples)):
        return None
    n = len(samples[0][1])
    outs = []
    if any((len(s[1]) != n for s in samples)):
        return None
    for k in range(n):
        if len({s[1][k][0] for s in samples}) != 1:
            return None
        cells = []
        for f in range(16):
            ys = [s[1][k][1][f] for s in samples]
            preferred = f if samples[0][1][k][0] == 'BODY' or f >= 7 else f - 1 if f > 0 else None
            order = ([preferred] if preferred is not None else []) + [i for i in range(17) if len({s[0][i] for s in samples}) > 1]
            match = next((i for i in order if [s[0][i] for s in samples] == ys), None)
            if match is not None:
                cells.append(('in', match))
            elif len(set(ys)) == 1:
                cells.append(('const', ys[0]))
            else:
                return None
        outs.append((samples[0][1][k][0], cells))
    return outs

def extract():
    wa = tuple((pin.read() for pin in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE)))
    lib = C.CDLL(str(v.LIBRARY))
    types = {}
    for t in REVIEWED_TYPES:
        ss = [sample(wa, lib, t, lv, seed) for lv in (0, 7, 13) for seed in (3401, 7254, 9874, 3404, 7257, 9877)]
        if any((s is None for s in ss)) or any((len(s) != n for (s, n) in zip(ss, [1] * 18 if t in PLAIN_TYPES else [1] * 6 + [2] * 6 + [5] * 6))):
            continue
        rr = []
        for pairs in ([s[0] for (i, s) in enumerate(ss) if i % 3 != 0], [s[0] for s in ss] if t in PLAIN_TYPES else [s[1] for s in ss[6:12]] + [p for s in ss[12:] for p in s[3:5]], [s[0] for s in ss] if t in PLAIN_TYPES else [p for s in ss[12:] for p in s[1:3]]):
            recipe = infer(pairs)
            if recipe is None:
                break
            rr.append(recipe)
        if len(rr) != 3:
            continue
        for (opt, ext) in ((1, 0), (0, 1)):
            if ext and t in DIM_TYPES:
                rr.append([])
                continue
            extra = [sample(wa, lib, t, 0, seed, opt, ext) for seed in (3401, 7254, 9874, 3404, 7257, 9877)]
            if any((s is None or len(s) != 2 for s in extra)):
                break
            r = infer([s[-1] for s in extra])
            if r is None:
                break
            rr.append(r)
        if len(rr) != 5:
            continue
        r = infer([s[0] for (i, s) in enumerate(ss) if i % 3 == 0])
        if r is None:
            continue
        rr.append(r)
        types[t] = rr
    if set(types) != set(REVIEWED_TYPES):
        raise ValueError("reviewed recipe no longer fits the pinned instructions")
    return types


def render(types):
    recipes, rows = [], []
    for t, rules in sorted(types.items()):
        indices = []
        for rule in rules:
            if len(rule) > 8:
                raise ValueError('recipe exceeds eight draws')
            if rule not in recipes:
                recipes.append(rule)
            indices.append(recipes.index(rule))
        rows.append((t, indices))
    lines = ['/* Generated by scripts/gen_item_bodies.py. Rendering rules only.',
             ' * source=0 selects value; source=1..16 copies the generic draw word;',
             ' * source=17 copies OBJECT alpha. See client-render-items.md part 3. */',
             'static const struct { uint8_t count; struct { int32_t entry; uint8_t source[16]; uint32_t value[16]; } draw[8]; } mu_rc_body_recipes[] = {']
    for rule in recipes:
        lines.append('    {%d, {' % len(rule))
        for entry, cells in rule:
            sources = ', '.join(str(v + 1 if op == 'in' else 0) for op, v in cells)
            values = ', '.join('0' if op == 'in' else '0x%08xu' % (v & 0xffffffff) for op, v in cells)
            lines.append('        {%d, {%s}, {%s}},' % (1 if entry == 'BODY' else 2, sources, values))
        lines.append('    }},')
    lines += ['};', 'static const struct { int32_t type; uint16_t recipe[6]; uint8_t dim, plain; } mu_rc_body_types[] = {']
    for t, indices in rows:
        lines.append('    {0x%04x, {%s}, %d, %d},' %
                     (t, ', '.join(map(str, indices)), t in DIM_TYPES, t in PLAIN_TYPES))
    return '\n'.join(lines + ['};', ''])


def generate():
    subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/renderchar')], check=True)
    return render(extract())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--check', action='store_true')
    a = p.parse_args()
    result = generate()
    if a.check:
        if a.output.read_text() != result:
            raise SystemExit('body recipe table differs from pinned instructions')
    else:
        a.output.write_text(result)


if __name__ == '__main__':
    main()
