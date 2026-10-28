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

# Part 8: next ranked armour clusters, independently compared.
NEXT_TYPES = [0x1f8b, 0x1f8f, 0x1fbe, 0x1fdb, 0x1b8b, 0x1b8f, 0x1bbe, 0x1bdb]

# Part 9: cosine mesh-light branches at ranks 21, 36, 46 and 49.
CLOCK_TYPES = [
    0x1a24, 0x1a28, 0x1a2a, 0x1a2d, 0x1a30, 0x1a34, 0x1a7a,
    0x1e24, 0x1e28, 0x1e2a, 0x1e2d, 0x1e30, 0x1e34, 0x1e7a,
    0x2024, 0x2028, 0x202a, 0x202d, 0x2030, 0x2034, 0x207a,
    0x2224, 0x2228, 0x222a, 0x222d, 0x2230, 0x2234, 0x227a,
]

CLUSTER_TYPES = [
    0x0b3f, 0x0f00, 0x0f01, 0x151a, 0x1528, 0x198d, 0x1991, 0x19c4, 0x19c8, 0x19ca,
    0x19d0, 0x19dd, 0x1b91, 0x1d91, 0x1dc6, 0x1dca, 0x1dcd, 0x1dce, 0x1fa4, 0x1fa8,
    0x24e4, 0x2519, 0x252c, 0x2537, 0x2538, 0x2549, 0x2553, 0x2554, 0x2555, 0x2556,
    0x2557, 0x2558, 0x2559, 0x2560, 0x26fa, 0x271d, 0x271e, 0x271f, 0x2720, 0x2721,
    0x2722, 0x2723, 0x2724, 0x272c, 0x272d, 0x2739, 0x2744, 0x274a, 0x2756, 0x2757,
    0x275e, 0x275f, 0x2760, 0x2761, 0x2762, 0x2764, 0x2765, 0x2766, 0x2767, 0x2768,
    0x2769, 0x276a, 0x276c, 0x276d, 0x276e, 0x276f, 0x2770, 0x2771, 0x2773, 0x2774,
    0x2775, 0x2776, 0x27db, 0x27dc, 0x27dd, 0x2894, 0x28a0, 0x28a1, 0x28db,
]

WING_TYPES = list(range(0x2322, 0x2328))

ATLAS_TYPES = [8194, 8196, 8197, 8198, 8200, 8202, 8203, 8204, 8205, 8206, 8209, 8224, 8259, 8313]

VISIBLE_TYPES = [
    0x0af9, 0x197b, 0x1b7b, 0x1b7e, 0x1b7f, 0x1b83, 0x1b9c, 0x1b9f, 0x1ba3, 0x1ba4,
    0x1ba5, 0x1ba6, 0x1ba7, 0x1ba8, 0x1ba9, 0x1baa, 0x1bab, 0x1bac, 0x1bad, 0x1bb3,
    0x1bbf, 0x1bdc, 0x1bee, 0x1c1d, 0x1c3d, 0x1c40, 0x1c76, 0x1d7b, 0x1d7c, 0x1d80,
    0x1d82, 0x1d8b, 0x1d8f, 0x1d9f, 0x1da3, 0x1da4, 0x1da5, 0x1da6, 0x1da7, 0x1da8,
    0x1da9, 0x1daa, 0x1dab, 0x1dac, 0x1dad, 0x1db0, 0x1db3, 0x1dbe, 0x1dbf, 0x1ddb,
    0x1ddc, 0x1dee, 0x1e1a, 0x1e1d, 0x1e40, 0x1e73, 0x1e76, 0x1f9f, 0x1fa3, 0x1fa5,
    0x1fa6, 0x1fa7, 0x1fa9, 0x1faa, 0x1fab, 0x1fac, 0x1fad, 0x1fb3, 0x1fee, 0x2002,
    0x2004, 0x2005, 0x2006, 0x2008, 0x200a, 0x200b, 0x200c, 0x200d, 0x200e, 0x2011,
    0x201d, 0x2020, 0x2040, 0x2043, 0x2076, 0x2079, 0x219f, 0x21a3, 0x21a4, 0x21a5,
    0x21a6, 0x21a7, 0x21a8, 0x21a9, 0x21aa, 0x21ab, 0x21ac, 0x21ad, 0x21b3, 0x21bf,
    0x21dc, 0x21ee, 0x221d, 0x2240, 0x2276,
]

# Part 11: per-type wave/sine scalar programs; independent full streams checked.
SCALAR_TYPES = [
    0x0b02, 0x0b20, 0x0b24, 0x0b25, 0x0b67, 0x0b6a, 0x0b6b, 0x0f0e, 0x0f0f, 0x0f14,
    0x0f1b, 0x10f8, 0x10ff, 0x1109, 0x1310, 0x1322, 0x132b, 0x132c, 0x14f9, 0x1549,
    0x154c, 0x157d, 0x157e, 0x157f, 0x1580, 0x1581, 0x1582, 0x1583, 0x1705, 0x1708,
    0x1719, 0x171a, 0x1739, 0x173a, 0x173b, 0x173c, 0x173d, 0x173e, 0x173f, 0x1747,
    0x1756, 0x1945, 0x19b7, 0x19c1, 0x19c2, 0x1a15, 0x1b45, 0x1bb7, 0x1bc1, 0x1bc2,
    0x1c14, 0x1c15, 0x1c16, 0x1c17, 0x1c22, 0x1c23, 0x1d45, 0x1e17, 0x1f45, 0x1fb7,
    0x1fc1, 0x1fc2, 0x2217, 0x2514, 0x2515, 0x2516, 0x2523, 0x2528, 0x252b, 0x255f,
    0x2566, 0x2567, 0x26f7, 0x271b, 0x271c, 0x2727, 0x2728, 0x2729, 0x272a, 0x2742,
    0x2743, 0x2745, 0x278b, 0x278c, 0x278d, 0x278e, 0x27a3,
]

PROBE_SEEDS = (3401, 7254, 9874, 3404, 7257, 9877, 3407, 7260, 9880, 3413, 7266, 9886)

DIM_TYPES = [0xae6 + group * 512 + index for group in (7, 8, 9, 11)
             for index in (*range(0x11c, 0x12c), 0x13a, 0x15d, 0x193)]
PLAIN_TYPES = [*range(0x234a, 0x2368), *range(0x241d, 0x2477), *WING_TYPES]

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
    slow_rem = tick - int(tick / -6283) * -6283
    slow_x = f(f(slow_rem * f(0.001)) * -1)
    slow_w = f(math.cos(slow_x))
    if f(3.1415927) > slow_x: slow_w = -slow_w
    slow = f(f(f(f(slow_w + 1) * f(0.5)) * f(0.8)) + f(0.2))
    fast_rem = tick - int(tick / -1047) * -1047
    fast_x = f(f(fast_rem * f(0.001)) * -6)
    fast_w = f(math.cos(fast_x))
    if f(3.1415927) > fast_x: fast_w = -fast_w
    fast = min(f(f(f(fast_w+1)*f(0.5)) * 0.9 + f(0.1)), 1.0)
    sine = f(math.sin(f(time*f(0.0008))))
    if 0 > sine: sine = -sine
    atlas30 = int((tick - int(tick/600)*600)/20)
    atlas13 = int((tick - int(tick/455)*455)/35)
    return (f(f(f(math.sin(f(time*f(0.0015)))) + 1)*f(0.5)),
            f(f(f(math.sin(f(time*f(0.002))))*f(0.3)) + f(0.7)),
            f(rem*f(0.0005)), min(f(f(wave*f(0.65))+f(0.2)), f(0.65)), slow, f(time*f(0.0001)),
            f((atlas30-int(atlas30/6)*6)*f(0.167)), f(int(atlas30/6)*f(0.2)),
            f((atlas13-int(atlas13/4)*4)*f(0.25)), f(int(atlas13/4)*f(0.25)), sine, fast, wave)

# Part 11: per-type straight-line SSE scalars after the wave helper 0x0185bdc4(a,b)
# or the sin wrapper 0x009681bd(time*k). Sites are the return addresses hit by the
# probes; the pinned bytes must match exactly or the site is ignored.
WAVE_HELPER, SINE_WRAPPER = 0x0185bdc4, 0x009681bd
SCALAR_OPS = {0x59: 1, 0x58: 2, 0x5c: 3, 0x5e: 4}   # mulss, addss, subss, divss
MOVSS_ESP = bytes.fromhex('f30f110424')


def _word(wa, address):
    import struct
    base = 0x01a7c000
    if not base <= address <= base + len(wa[1]) - 4:
        return None
    return struct.unpack_from('<I', wa[1], address - base)[0]


def _text(wa, address, size):
    return wa[0][address - 0x00401000:address - 0x00401000 + size]


def _load(wa, address):
    """movss xmm0,[abs] at address; returns the constant word."""
    import struct
    code = _text(wa, address, 8)
    return _word(wa, struct.unpack_from('<I', code, 4)[0]) if code[:4] == bytes.fromhex('f30f1005') else None


def parse_scalar(wa, helper, ret):
    """Return (kind, a, b, ops) or None. kind 1 = wave(a,b), 2 = sin(time*a)."""
    import struct
    call = ret - 5
    if _text(wa, call, 1) != b'\xe8' or _text(wa, call - 5, 5) != MOVSS_ESP:
        return None
    if helper == WAVE_HELPER:
        a = _load(wa, call - 13)
        if a is None or _text(wa, call - 14, 1) != b'\x51' or _text(wa, call - 19, 5) != MOVSS_ESP:
            return None
        if _text(wa, call - 22, 3) == bytes.fromhex('0f57c0') and _text(wa, call - 23, 1) == b'\x51':
            b = 0
        else:
            b = _load(wa, call - 27)
            if b is None or _text(wa, call - 28, 1) != b'\x51':
                return None
        a_value = v.u2f(a)
        if a_value == 0 or not 2 <= abs(6283.185546875 / a_value) < 2**31:
            return None
        kind, pops = 1, b'\x59\x59'
    elif helper == SINE_WRAPPER:
        if (_text(wa, call - 6, 1) != b'\x51' or _text(wa, call - 14, 4) != bytes.fromhex('f30f5905') or
                _text(wa, call - 22, 8) != bytes.fromhex('f30f1005') + (0x06fce370).to_bytes(4, 'little')):
            return None
        a = _word(wa, struct.unpack_from('<I', _text(wa, call - 14, 8), 4)[0])
        if a is None:
            return None
        b, kind, pops = 0, 2, b'\x59'
    else:
        return None
    at = ret
    if _text(wa, at, len(pops)) != pops:
        return None
    at += len(pops)
    fstp, reload = _text(wa, at, 6), _text(wa, at + 6, 8)
    double = fstp[:2] == b'\xdd\x9d'
    if fstp[:2] not in (b'\xd9\x9d', b'\xdd\x9d'):
        return None
    if reload[:4] != (bytes.fromhex('f20f1085') if double else bytes.fromhex('f30f1085')) or fstp[2:] != reload[4:]:
        # The stored binary32 local itself, as at 0x01711064.
        return None if double else (kind, a, b, ())
    at += 14
    ops = []
    while len(ops) < 4:
        code = _text(wa, at, 8)
        if code[:2] != (b'\xf2\x0f' if double else b'\xf3\x0f') or code[2] not in SCALAR_OPS or code[3] != 0x05:
            break
        address = struct.unpack_from('<I', code, 4)[0]
        word = _word(wa, address)
        if word is None:
            return None
        if double:
            high = _word(wa, address + 4)
            if high is None:
                return None
            word |= high << 32
        ops.append((SCALAR_OPS[code[2]] | (8 if double else 0), word))
        at += 8
    if double and (not ops or _text(wa, at, 4) != bytes.fromhex('f20f5ac0')):
        return None
    return kind, a, b, tuple(ops)


def wave_helper(a, b, time):
    """0x0185bdc4: signed cosine wave with its degree phase, binary32 steps."""
    import math
    f = lambda x: v.u2f(v.f2u(x))
    def cvtt(x):
        return int(x) if -2147483648 <= x < 2147483648 else -2147483648
    x = f(f(f(f(b * f(0.017453292)) * f(1000.0)) / a) + time)
    tick, period = cvtt(x), cvtt(f(f(6283.1855) / a))
    rem = int(math.fmod(tick, period))
    y = f(f(rem * f(0.001)) * a)
    w = f(math.cos(y))
    if f(3.1415927) > y:
        w = -w
    return f(f(w + f(1.0)) * f(0.5))


def scalar_value(program, time):
    import math
    f = lambda x: v.u2f(v.f2u(x))
    kind, a, b, ops = program
    if kind == 1:
        value = wave_helper(v.u2f(a), v.u2f(b), time)
    else:
        value = f(math.sin(f(time * v.u2f(a))))
    import struct
    double = bool(ops) and ops[0][0] & 8
    for op, word in ops:
        k = struct.unpack('<d', struct.pack('<Q', word))[0] if double else v.u2f(word)
        op &= 7
        value = value * k if op == 1 else value + k if op == 2 else value - k if op == 3 else value / k
        if not double:
            value = f(value)
    return v.f2u(f(value))


def flat(d):
    return [*d[1], *d[2], d[3], *d[4], d[5]]

_sample_state = None
_site_sink = None


def sample(wa, lib, t, lv, seed, opt=0, ext=0, params=(), sites=None):
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
            from unicorn import UC_HOOK_CODE
            def site(uc, address, size, context):
                if _site_sink is not None:
                    m = self.m
                    _site_sink.add((address, m.r32(uc.reg_read(m.x86.UC_X86_REG_ESP))))
            for addr in (WAVE_HELPER, SINE_WRAPPER):
                self.m.uc.hook_add(UC_HOOK_CODE, site, begin=addr, end=addr)
    global _site_sink
    _site_sink = sites
    if _sample_state is None or _sample_state[0] is not wa:
        from item_body_machine import ResetWorld
        _sample_state = (wa, ResetWorld(wa, W), tags)
    else:
        tags = _sample_state[2]
        tags.clear()
    factory = _sample_state[1]
    case = v.random_case_any(random.Random(seed), t)
    case.update(item_level=lv << 3, quality=9, option1=opt, ext=ext, record=(0, 0, 0), a10=0xffffffff, a11=0xffffffff, render_type=(2, 0x102, 0x40042)[seed % 3])
    case['object_hidden'] = (-1, 0, 2)[(seed // 3) % 3] if t in WING_TYPES else 0
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
             [v.f2u(f(v.u2f(word) * pulse)) for word in flat(a)[8:11]] + [v.f2u(blend)] + [v.f2u(x) for x in body_scalars(time)] + [case['object_hidden'] & 0xffffffff] +
             [scalar_value(program, time) for program in params],
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

ALL_TYPES = (REVIEWED_TYPES + ADDITIONAL_TYPES + CONTINUATION_TYPES + RANKED_TYPES + EXPANDED_TYPES +
             NEXT_TYPES + CLOCK_TYPES + CLUSTER_TYPES + WING_TYPES + VISIBLE_TYPES + SCALAR_TYPES)


def fit(wa, lib, t, scalars=False):
    """Probe one type; return (phase rules, scalar programs), or None if no recipe fits.

    With scalars, a type that does not fit the shared inputs is probed again with
    the parsed per-type scalar sites appended as further inputs."""
    sites = set()
    rules = _fit(wa, lib, t, (), sites)
    if rules is not None or not scalars:
        return None if rules is None else (rules, ())
    programs = []
    for helper, ret in sorted(sites):
        program = parse_scalar(wa, helper, ret)
        if program is not None and program not in programs:
            programs.append(program)
    if not programs:
        return None
    rules = _fit(wa, lib, t, tuple(programs), None)
    if rules is None:
        return None
    # Keep only referenced programs, renumbered in first-use order.
    used = sorted({value - 35 for rule in rules for _, cells in rule for op, value in cells if op == 'in' and value >= 35})
    remap = {old: 35 + new for new, old in enumerate(used)}
    rules = [[(entry, [(op, remap.get(value - 35, value) if op == 'in' and value >= 35 else value) for op, value in cells])
              for entry, cells in rule] for rule in rules]
    return rules, tuple(programs[k] for k in used)


def _fit(wa, lib, t, params, sites):
    levels = range(16) if t >= 0x3700 else (0, 7, 13)
    ss = [sample(wa, lib, t, lv, seed, params=params, sites=sites) for lv in levels
          for seed in PROBE_SEEDS]
    if any(s is None for s in ss) and sites is None:
        return None
    phases = [[] for _ in range(8)]
    for index, stream in enumerate(ss):
        if stream is None:
            continue
        phase = 5 if index % 3 == 0 else 0
        if t in CLOCK_TYPES and index // len(PROBE_SEEDS) == 2:
            phase = 7 if phase == 5 else 6
        phases[phase].append(stream[0])
        for pair in stream[1:]:
            flags = pair[0][0] & ~0x100
            if flags not in (0x44, 0x48, 0x240, 0x1040):
                raise ValueError(f'unclassified helper flags {flags:#x}')
            phase = 1 if flags in (0x44, 0x48) else 2
            phases[phase].append(pair)
    for opt, ext, phase in ((1, 0, 3), (0, 1, 4)):
        if ext and t in DIM_TYPES:
            continue
        extra = [sample(wa, lib, t, 0, seed, opt, ext, params=params, sites=sites)
                 for seed in PROBE_SEEDS]
        if any(s is None for s in extra):
            ss.append(None)
            if sites is None:
                return None
            continue
        phases[phase] = [s[-1] for s in extra]
    if any(s is None for s in ss):
        return None
    rules = [infer(pairs) if pairs else [] for pairs in phases]
    if any(rule is None for rule in rules):
        return None
    if t in ATLAS_TYPES:
        # These ancient mesh branches retain the preceding body light.
        rules[4] = [(entry, [(op, value-4 if 8 <= field <= 10 and op == 'in' and 12 <= value <= 14 else value)
                             for field,(op,value) in enumerate(cells)]) for entry,cells in rules[4]]
    return rules


def extract():
    wa = tuple((pin.read() for pin in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE)))
    lib = C.CDLL(str(v.LIBRARY))
    types = {}
    for t in ALL_TYPES:
        fitted = fit(wa, lib, t, scalars=True)
        if fitted is not None:
            types[t] = fitted
    if set(types) != set(ALL_TYPES):
        raise ValueError("reviewed recipe no longer fits the pinned instructions: " + str([hex(t) for t in sorted(set(ALL_TYPES) - set(types))]))
    return types


def render(types):
    recipes, rows, programs = [], [], []
    for t, (rules, scalars) in sorted(types.items()):
        indices = []
        for rule in rules:
            if len(rule) > 16:
                raise ValueError('recipe exceeds sixteen draws')
            if rule not in recipes:
                recipes.append(rule)
            indices.append(recipes.index(rule))
        if len(scalars) > 8:
            raise ValueError('more than eight scalar programs')
        rows.append((t, indices, len(programs), len(scalars)))
        programs.extend(scalars)
    lines = ['/* Generated by scripts/gen_item_bodies.py. Rendering rules only.',
             ' * source=0 selects value; source=1..16 copies the generic draw word;',
             ' * source=17 copies OBJECT alpha. source=18..20 copies pulsed body light; source=21 copies armour blend pulse. source=22..34 selects clock scalars; source=35 copies OBJECT hidden mesh;',
             ' * source=36.. selects the type\'s own scalar program (kind 1 = wave 0x0185bdc4(a,b), 2 = sin(time*a), then mul/add/sub/div, binary32 or op|8 binary64 with one final rounding). See client-render-items.md. */',
             '#define MU_RC_BODY_SCALARS 8',
             'typedef struct { uint8_t count; struct { int32_t entry; uint8_t source[16]; uint32_t value[16]; } draw[16]; } mu_rc_body_recipe;',
             'static const mu_rc_body_recipe mu_rc_body_recipes[] = {']
    for rule in recipes:
        lines.append('    {%d, {' % len(rule))
        for entry, cells in rule:
            sources = ', '.join(str(v + 1 if op == 'in' else 0) for op, v in cells)
            values = ', '.join('0' if op == 'in' else '0x%08xu' % (v & 0xffffffff) for op, v in cells)
            lines.append('        {%d, {%s}, {%s}},' % (1 if entry == 'BODY' else 2, sources, values))
        lines.append('    }},')
    lines += ['};', 'typedef struct { uint8_t kind, count; uint32_t a, b; uint8_t op[4]; uint64_t k[4]; } mu_rc_body_scalar;',
              'static const mu_rc_body_scalar mu_rc_body_scalars[] = {']
    for kind, a, b, ops in programs:
        ops = list(ops) + [(0, 0)] * (4 - len(ops))
        lines.append('    {%d, %d, 0x%08xu, 0x%08xu, {%s}, {%s}},' % (
            kind, sum(1 for op, _ in ops if op), a, b, ', '.join(str(op) for op, _ in ops),
            ', '.join('0x%xull' % k for _, k in ops)))
    if not programs:
        lines.append('    {0, 0, 0, 0, {0, 0, 0, 0}, {0, 0, 0, 0}},')
    lines += ['};', 'static const struct { int32_t type; uint16_t recipe[8]; uint8_t level_split, retain_ancient; uint8_t dim, plain, pulse, blend_pulse; uint16_t scalar_mask; uint16_t scalar_first; uint8_t scalar_count; } mu_rc_body_types[] = {']
    for t, indices, first, count in rows:
        rules = types[t][0]
        lines.append('    {0x%04x, {%s}, %d, %d, %d, %d, %d, %d, %d, %d, %d},' %
                     (t, ', '.join(map(str, indices)), t in CLOCK_TYPES, t in ATLAS_TYPES, t in DIM_TYPES, t in PLAIN_TYPES, t in PULSE_TYPES,
                      any(op == 'in' and value == 20 for rule in rules for _, cells in rule for op, value in cells),
                      sum(1 << k for k in range(13) if any(op == 'in' and value == 21+k for rule in rules for _, cells in rule for op,value in cells)),
                      first, count))
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
