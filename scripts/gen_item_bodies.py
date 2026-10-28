#!/usr/bin/env python3
"""Generate reviewed rendering parameter recipes from pinned instructions.

Probes infer constants, copies of draw inputs and copies of the shared armour pulse. Independent randomized
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
ADDITIONAL_TYPES = [
    0x0b01, 0x0b06, 0x0b07, 0x0b08, 0x0b0e, 0x0b18, 0x0b44, 0x0ef6, 0x0f04, 0x0f0a,
    0x12fc, 0x12fe, 0x1325, 0x1507, 0x1508, 0x1536, 0x1537, 0x1538, 0x1539, 0x153a,
    0x1545, 0x154e, 0x1551, 0x16f7, 0x16f8, 0x16fa, 0x170e, 0x1917, 0x1918, 0x191b,
    0x191c, 0x191e, 0x1930, 0x1931, 0x1933, 0x1978, 0x1979, 0x197a, 0x19de, 0x19f0,
    0x19f5, 0x19f6, 0x19f7, 0x19f9, 0x19fc, 0x19fe, 0x19ff, 0x1a01, 0x1a42, 0x1b05,
    0x1b0a, 0x1b17, 0x1b1b, 0x1b1e, 0x1b21, 0x1b22, 0x1b23, 0x1b31, 0x1b39, 0x1b78,
    0x1b79, 0x1b7a, 0x1cf9, 0x1d05, 0x1d0a, 0x1d1e, 0x1d31, 0x1d78, 0x1d79, 0x1dde,
    0x1de6, 0x1df0, 0x1df4, 0x1df5, 0x1df6, 0x1df7, 0x1df8, 0x1df9, 0x1dfa, 0x1dfb,
    0x1dfc, 0x1dfd, 0x1dfe, 0x1dff, 0x1e00, 0x1e01, 0x1e1f, 0x1e36, 0x1e42, 0x1e78,
    0x1f0a, 0x1f12, 0x1f1b, 0x1f7b, 0x1fde, 0x1ff4, 0x1ff5, 0x1ff8, 0x1ff9, 0x1ffa,
    0x1ffd, 0x2000, 0x2001, 0x201f, 0x2078, 0x217b, 0x21de, 0x21f4, 0x21f5, 0x21f8,
    0x21f9, 0x21fa, 0x21fd, 0x2200, 0x2201, 0x221f, 0x2278, 0x3700, 0x3890, 0x3891,
    0x3894, 0x3897, 0x3898, 0x3899, 0x389a, 0x389f, 0x38a0, 0x38a2,
]
# Size-rank 3, shared armour mesh pulse at 0x01705471.
PULSE_TYPES = [
    0x1950, 0x1951, 0x1954, 0x1955, 0x1956, 0x1959, 0x19b1, 0x19bd, 0x19da, 0x1a1b,
    0x1a74, 0x1b50, 0x1b51, 0x1b54, 0x1b55, 0x1b56, 0x1b59, 0x1bb1, 0x1bbd, 0x1bda,
    0x1c1b, 0x1c74, 0x1d50, 0x1d54, 0x1d56, 0x1d59, 0x1db1, 0x1e1b, 0x1e74, 0x1f50,
    0x1f51, 0x1f54, 0x1f55, 0x1f56, 0x1f59, 0x1fb1, 0x1fbd, 0x1fda, 0x201b, 0x2074,
    0x2150, 0x2154, 0x2156, 0x2159, 0x21b1, 0x221b, 0x2274,
]
ADDITIONAL_TYPES += PULSE_TYPES

# Part 5: independent full-function comparisons passed for every enabled type.
CONTINUATION_TYPES = [
    0x1dc3, 0x1dc7, 0x1dc9, 0x1dcc, 0x1dcf, 0x1e1e, 0x1e77, 0x1fc3, 0x1fc4, 0x1fc7,
    0x1fc8, 0x1fc9, 0x1fca, 0x1fcc, 0x1fcf, 0x1fd0, 0x1fdd, 0x201e, 0x2077, 0x21c3,
    0x21c4, 0x21c5, 0x21c6, 0x21c7, 0x21c8, 0x21c9, 0x21ca, 0x21cb, 0x21cc, 0x21cd,
    0x21ce, 0x21cf, 0x21d0, 0x21dd, 0x21ef, 0x221e, 0x2241, 0x2277, 0x22f5, 0x24e9,
    0x24f0, 0x251c, 0x251d, 0x251e, 0x251f, 0x2520, 0x2521, 0x2522, 0x26f2, 0x26f3,
    0x26f4, 0x26f6, 0x26fc, 0x26ff, 0x2700, 0x2705, 0x272e, 0x272f, 0x2730, 0x2731,
    0x2732, 0x2733, 0x2734, 0x2735, 0x2736, 0x2737, 0x2738, 0x280b, 0x280c, 0x280d,
    0x280e, 0x2837, 0x2838, 0x2839, 0x283a,
]

# Part 6: rank-9 and subsequent ranked shapes, independently compared.
RANKED_TYPES = [
    0x199f, 0x19a3, 0x19a4, 0x19a5, 0x19a6, 0x19a7, 0x19a8, 0x19a9, 0x19aa, 0x19ab,
    0x19ac, 0x19ad, 0x1dc4, 0x1dc5, 0x1dc8, 0x1dcb, 0x1dd0, 0x1ddd, 0x1def, 0x1e41,
    0x1fc5, 0x1fc6, 0x1fcb, 0x1fcd, 0x1fce, 0x1fef, 0x2041, 0x250d, 0x250e, 0x250f,
    0x2510, 0x2524, 0x2525, 0x2526, 0x2527, 0x252d, 0x252e, 0x252f, 0x2530, 0x2531,
    0x256c, 0x2719, 0x273a, 0x273b, 0x273c, 0x273d, 0x273e, 0x273f, 0x2740, 0x2746,
    0x2747, 0x2748, 0x2758, 0x2759, 0x275a, 0x275b, 0x275c, 0x275d,
]

# Part 7: stress mace and ranked clock-driven bodies. Independent full streams checked.
EXPANDED_TYPES = [
    0x0eee, 0x18fe, 0x1967, 0x198c, 0x1992, 0x199e, 0x19ed, 0x1a3f, 0x1b67, 0x1b8a,
    0x1b8c, 0x1b8d, 0x1b8e, 0x1b90, 0x1b92, 0x1b93, 0x1b9e, 0x1bb2, 0x1bed, 0x1c1c,
    0x1c3f, 0x1c75, 0x1cfe, 0x1d67, 0x1d8a, 0x1d8c, 0x1d8d, 0x1d8e, 0x1d90, 0x1d92,
    0x1d93, 0x1d9e, 0x1db2, 0x1ded, 0x1e1c, 0x1e3f, 0x1e75, 0x1f8a, 0x1f8e, 0x1f90,
    0x1f93, 0x1fb2, 0x201c, 0x2075, 0x218a, 0x218e, 0x2190, 0x2193, 0x21b2, 0x221c,
    0x2275, 0x2517, 0x257e, 0x257f, 0x2580, 0x2581, 0x2582, 0x2583, 0x2584, 0x2585,
    0x28f9, 0x28fa, 0x28fb, 0x28fc, 0x28fd, 0x28fe, 0x28ff, 0x2900, 0x2901, 0x2904,
    0x2905, 0x2906, 0x2907, 0x2908, 0x2909, 0x290a,
]

PROBE_SEEDS = (3401, 7254, 9874, 3404, 7257, 9877, 3407, 7260, 9880, 3413, 7266, 9886)

DIM_TYPES = [0xae6 + group * 512 + index for group in (7, 8, 9, 11)
             for index in (*range(0x11c, 0x12c), 0x13a, 0x15d, 0x193)]
PLAIN_TYPES = [*range(0x234a, 0x2368), *range(0x241d, 0x2477)]

def body_scalars(time):
    """Reviewed SSE scalar paths: 0x016ecaf5, 0x016eec41, 0x01713552."""
    import math
    f = lambda x: v.u2f(v.f2u(x))
    tick = int(time) if -2147483648 <= time < 2147483648 else -2147483648
    rem = tick - int(tick/2000)*2000
    # The -4 wave uses a different signed period from the scrolling UV.
    pulse_rem = tick - int(tick / -1570) * -1570
    x = f(f(pulse_rem * f(0.001)) * -4)
    w = f(math.cos(x))
    if f(3.1415927) > x: w = -w
    wave = f(f(w + 1) * f(0.5))
    return (f(f(f(math.sin(f(time*f(0.0015)))) + 1)*f(0.5)),
            f(f(f(math.sin(f(time*f(0.002))))*f(0.3)) + f(0.7)),
            f(rem*f(0.0005)), min(f(f(wave*f(0.65))+f(0.2)), f(0.65)))

def flat(d):
    return [*d[1], *d[2], d[3], *d[4], d[5]]

_sample_state = None


def sample(wa, lib, t, lv, seed, opt=0, ext=0):
    import math
    global _sample_state
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
    if _sample_state is None or _sample_state[0] is not wa:
        from item_body_machine import ResetWorld
        _sample_state = (wa, ResetWorld(wa, W), tags)
    else:
        tags = _sample_state[2]
        tags.clear()
    factory = _sample_state[1]
    case = v.random_case_any(random.Random(seed), t)
    case.update(item_level=lv << 3, quality=9, option1=opt, ext=ext, record=(0, 0, 0), a10=0xffffffff, a11=0xffffffff, render_type=(2, 0x102, 0x40042)[seed % 3])
    (r, st, other, m) = v.client_stream(wa, case, factory)
    generic_case = dict(case)
    if t in (0x0eee, 0x18fe, 0x1cfe):
        f = lambda x: v.u2f(v.f2u(x))
        wave = f(math.sin(f(v.u2f(case['time'])*f(0.001))))
        mul, add = (0.6, 0.4) if t == 0x0eee else (0.4, 0.6)
        generic_case['blend_light'] = v.f2u(f(f(wave*f(mul)) + f(add)))
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
    # Some armour branches return without the generic ancient helper. Keep an
    # empty recipe for that phase rather than inventing an extra draw.
    if ext and len(groups) + 1 == len(generic) and generic[-1][1][0] & 0x800:
        groups.append(('omitted-ancient', []))
    if t == 0x0eee and other == [('gl', 'glPushMatrix', []), ('gl', 'glPopMatrix', [])]:
        other = []
    if not r['ok'] or other or len(groups) != len(generic):
        return None
    # 0x0185bdc4(-4,0) + 0.2. Each operation rounds to binary32.
    f = lambda x: v.u2f(v.f2u(x))
    time = v.u2f(case['time'])
    tick = int(time) if -2147483648 <= time < 2147483648 else -2147483648
    rem = tick - int(tick / -1570) * -1570
    x = f(f(rem * f(0.001)) * -4)
    w = f(math.cos(x))
    if f(3.1415927) > x:
        w = -w
    pulse = f(f(f(w + 1) * 0.5) + f(0.2))
    wave = f(f(w + 1) * 0.5)
    blend = f(wave * 0.7 + f(0.3))
    if blend > 1: blend = 1.0
    return [(flat(a) + [case['object_alpha']] +
             [v.f2u(f(v.u2f(word) * pulse)) for word in flat(a)[8:11]] + [v.f2u(blend)] + [v.f2u(x) for x in body_scalars(time)],
             [(b[0], flat(b)) for b in bs]) for (a, (_, bs)) in zip(generic, groups)]

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
            order = ([preferred] if preferred is not None else []) + [i for i in range(len(samples[0][0])) if len({s[0][i] for s in samples}) > 1]
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
    for t in REVIEWED_TYPES + ADDITIONAL_TYPES + CONTINUATION_TYPES + RANKED_TYPES + EXPANDED_TYPES:
        levels = range(16) if t >= 0x3700 else (0, 7, 13)
        ss = [sample(wa, lib, t, lv, seed) for lv in levels
              for seed in PROBE_SEEDS]
        if any(s is None for s in ss):
            continue
        phases = [[] for _ in range(6)]
        for index, stream in enumerate(ss):
            phases[5 if index % 3 == 0 else 0].append(stream[0])
            for pair in stream[1:]:
                flags = pair[0][0] & ~0x100
                if flags not in (0x44, 0x48, 0x240, 0x1040):
                    raise ValueError(f'unclassified helper flags {flags:#x}')
                phase = 1 if flags in (0x44, 0x48) else 2
                phases[phase].append(pair)
        for opt, ext, phase in ((1, 0, 3), (0, 1, 4)):
            if ext and t in DIM_TYPES:
                continue
            extra = [sample(wa, lib, t, 0, seed, opt, ext)
                     for seed in PROBE_SEEDS]
            if any(s is None for s in extra):
                break
            phases[phase] = [s[-1] for s in extra]
        else:
            rules = [infer(pairs) if pairs else [] for pairs in phases]
            if all(rule is not None for rule in rules):
                types[t] = rules
    if set(types) != set(REVIEWED_TYPES + ADDITIONAL_TYPES + CONTINUATION_TYPES + RANKED_TYPES + EXPANDED_TYPES):
        raise ValueError("reviewed recipe no longer fits the pinned instructions: " + str([hex(t) for t in sorted(set(REVIEWED_TYPES + ADDITIONAL_TYPES + CONTINUATION_TYPES + RANKED_TYPES + EXPANDED_TYPES) - set(types))]))
    return types


def render(types):
    recipes, rows = [], []
    for t, rules in sorted(types.items()):
        indices = []
        for rule in rules:
            if len(rule) > 16:
                raise ValueError('recipe exceeds sixteen draws')
            if rule not in recipes:
                recipes.append(rule)
            indices.append(recipes.index(rule))
        rows.append((t, indices))
    lines = ['/* Generated by scripts/gen_item_bodies.py. Rendering rules only.',
             ' * source=0 selects value; source=1..16 copies the generic draw word;',
             ' * source=17 copies OBJECT alpha. source=18..20 copies pulsed body light; source=21 copies armour blend pulse. source=22..25 selects clock scalars. See client-render-items.md. */',
             'typedef struct { uint8_t count; struct { int32_t entry; uint8_t source[16]; uint32_t value[16]; } draw[16]; } mu_rc_body_recipe;',
             'static const mu_rc_body_recipe mu_rc_body_recipes[] = {']
    for rule in recipes:
        lines.append('    {%d, {' % len(rule))
        for entry, cells in rule:
            sources = ', '.join(str(v + 1 if op == 'in' else 0) for op, v in cells)
            values = ', '.join('0' if op == 'in' else '0x%08xu' % (v & 0xffffffff) for op, v in cells)
            lines.append('        {%d, {%s}, {%s}},' % (1 if entry == 'BODY' else 2, sources, values))
        lines.append('    }},')
    lines += ['};', 'static const struct { int32_t type; uint16_t recipe[6]; uint8_t dim, plain, pulse, blend_pulse; uint8_t scalar_mask; } mu_rc_body_types[] = {']
    for t, indices in rows:
        lines.append('    {0x%04x, {%s}, %d, %d, %d, %d, %d},' %
                     (t, ', '.join(map(str, indices)), t in DIM_TYPES, t in PLAIN_TYPES, t in PULSE_TYPES,
                      any(op == 'in' and value == 20 for rule in types[t] for _, cells in rule for op, value in cells),
                      sum(1 << k for k in range(4) if any(op == 'in' and value == 21+k for rule in types[t] for _, cells in rule for op,value in cells))))
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
