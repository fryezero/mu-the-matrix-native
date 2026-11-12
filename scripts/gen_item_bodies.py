#!/usr/bin/env python3
"""Generate reviewed rendering parameter recipes from pinned instructions.

Probes infer constants, copies of draw inputs and copies of the shared armour pulse. Independent randomized
full-function comparisons in validate_item_clusters.py decide which types may
be enabled. Unknown recipes fail regeneration. This is finite instruction
comparison, not symbolic proof of every input or record kind.
"""
import argparse
import json
import ctypes as C
from pathlib import Path
import random
import subprocess
import original_cache
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

# Part 12: clock chains sliced from the pinned bytes; independent full streams checked.
CHAIN_TYPES = [
    0x0afb, 0x0aff, 0x0b1f, 0x0b26, 0x0b3c, 0x0b3d, 0x0b3e, 0x0b46, 0x0b48, 0x0b55,
    0x0b5a, 0x0b5b, 0x0b5d, 0x0b5e, 0x0b5f, 0x0b60, 0x0b63, 0x0b64, 0x0b65, 0x0b66,
    0x0b69, 0x0b6c, 0x0ef1, 0x0ef3, 0x0efe, 0x0f05, 0x0f06, 0x0f07, 0x0f12, 0x0f13,
    0x0f15, 0x0f16, 0x0f18, 0x0f1a, 0x10f0, 0x10fe, 0x1100, 0x1107, 0x12f8, 0x130c,
    0x131c, 0x1320, 0x1326, 0x1329, 0x14f0, 0x14f3, 0x151b, 0x151c, 0x151d, 0x151e,
    0x1547, 0x154b, 0x154d, 0x154f, 0x1552, 0x1579, 0x171b, 0x171c, 0x1720, 0x172a,
    0x172b, 0x1734, 0x1740, 0x1741, 0x1745, 0x1754,
]
# Part 12: the part-9 level split (extra draws above the +7 quality cap) for the
# neighbouring armour members; independent full streams checked.
LEVEL_TYPES = [
    0x1a25, 0x1a29, 0x1a2b, 0x1a31, 0x1a32, 0x1e25, 0x1e29, 0x1e2b, 0x1e31, 0x1e32,
    0x2025, 0x2029, 0x202b, 0x2031, 0x2032, 0x2225, 0x2229, 0x222b, 0x2231, 0x2232,
]
LEVEL_SPLIT = CLOCK_TYPES + LEVEL_TYPES

# Part 13: bodies whose later helpers start from the model fields of the body's
# last draw (carry), and bodies with immediate glColor records; independent full
# streams checked.
CARRY_TYPES = [
    0x0b00, 0x0b03, 0x0b04, 0x0b0a, 0x0b14, 0x0b1a, 0x0b1b, 0x0b1c, 0x0b1d, 0x0b1e,
    0x0eef, 0x0ef9, 0x0efb, 0x0efc, 0x10f5, 0x10f9, 0x10fb, 0x10fc, 0x1302, 0x1305,
    0x130a, 0x1504, 0x150a, 0x150b, 0x150f, 0x1511, 0x1519, 0x1529, 0x152a, 0x152b,
    0x152c, 0x152d, 0x152e, 0x152f, 0x1530, 0x1531, 0x1532, 0x1533, 0x1534, 0x1535,
    0x153b, 0x153c, 0x153d, 0x153e, 0x153f, 0x1540, 0x1541, 0x1542, 0x1543, 0x1548,
    0x1553, 0x1555, 0x1558, 0x1559, 0x155a, 0x155c, 0x155d, 0x155e, 0x155f, 0x1560,
    0x1561, 0x1562, 0x1565, 0x1566, 0x1567, 0x1568, 0x1575, 0x16ff, 0x1721, 0x1729,
    0x1733, 0x1753, 0x2319, 0x231a, 0x2331, 0x2332, 0x2339, 0x233a, 0x2380, 0x24bd,
    0x24c9, 0x24ca, 0x24ea, 0x24eb, 0x26e3, 0x2703, 0x283c, 0x283d, 0x286c,
]
COLOUR_TYPES = [
    0x0afa, 0x0ef8, 0x10f1, 0x10f6, 0x10f7, 0x16fb, 0x1700, 0x1704, 0x1706, 0x170c,
    0x170d, 0x1921, 0x1922, 0x1923, 0x1939, 0x1b1d, 0x1b1f, 0x1b32, 0x1f1d, 0x2702,
]

# Part 14: bodies fitted with the supplementary probes (records 0x26/0x5b, qualities
# 0-2, further clocks and scripted rand results); EXIT_TYPES also infer the model
# fields each helper call leaves. Independent full streams checked.
QUALITY_TYPES = [
    0x0b10, 0x0b12, 0x0b22, 0x0f0c, 0x0f0d, 0x1105, 0x1108, 0x1328, 0x1546, 0x1569,
    0x156a, 0x156b, 0x156c, 0x156d, 0x156e, 0x156f, 0x1570, 0x1571, 0x1572, 0x1573,
    0x1574, 0x170f, 0x1718, 0x1728, 0x1732, 0x1752, 0x230a, 0x230e, 0x230f, 0x2310,
    0x2317, 0x2318, 0x2381, 0x2392, 0x2393, 0x23ec, 0x23fd, 0x2402, 0x248e, 0x2490,
    0x2491, 0x2492, 0x2495, 0x2498, 0x249a, 0x2504, 0x251a, 0x251b, 0x270f, 0x2711,
    0x2712,
]
# Part 15: body random scaling a constant body-light vector (0x00cfcead, 0x00cfcd74).
PRODUCT_TYPES = [0x171d, 0x171e, 0x171f, 0x1742, 0x1743, 0x1744]
# Part 16: draw words one binary32 operation away from another input or program (kind-6
# derived programs, gen_item_bodies.derive). Independent full streams checked.
DERIVED_TYPES = [
    0x0afd, 0x0b0c, 0x0b4a, 0x0b56, 0x0b6d, 0x0b6e, 0x0b6f, 0x0b70, 0x0b71, 0x0b72,
    0x0b73, 0x0f2d, 0x0f2f, 0x0f30, 0x110a, 0x12f9, 0x12ff, 0x1300, 0x132e, 0x1554,
    0x1556, 0x1557, 0x1585, 0x1586, 0x1587, 0x1589, 0x158a, 0x158b, 0x158c, 0x158d,
    0x158e, 0x16fc, 0x16fd, 0x16fe, 0x1757, 0x1759, 0x175a, 0x175b, 0x175c, 0x175d,
    0x1afa, 0x1afd, 0x1b33, 0x1be6, 0x1cfa, 0x1cfd, 0x1efa, 0x1efd, 0x20fa, 0x20fd,
    0x23ac, 0x24ad, 0x24b5, 0x25fa, 0x25fb, 0x2789, 0x278a,
]
# Part 16 types that also carry the model fields of their last draw (the part-13 rule).
DERIVED_CARRY = [
    0x0afd, 0x0b0c, 0x0b56, 0x12ff, 0x1300, 0x1554, 0x1556, 0x1557, 0x16fc, 0x16fd,
    0x16fe, 0x23ac, 0x25fa,
]
# Part 17 (RENDER-ITEMS-002Q): bodies whose type case ends in an owner-effect block (gen_item_owner_fx). Their
# draws are generated here with the effect requests set aside; renderchar.c runs the effect program.
from gen_item_owner_fx import OWNER_FX_TYPES
# Part 18 (RENDER-ITEMS-002R): bodies whose RenderObjDraw case creates effects before the body draws (pre-draw
# programs, gen_item_owner_fx.PRE_FX_TYPES); their draws fit with the effect requests set aside.
from gen_item_owner_fx import PRE_FX_TYPES, OBJDRAW as PRE_DRAW_RAND
# Part 21 (RENDER-ITEMS-002T): owner blocks after the draws with the pre-draw idioms (gen_item_owner_fx.POST_FX_TYPES);
# their draws fit the default probes with the effect requests set aside.
from gen_item_owner_fx import POST_FX_TYPES, READ_PROGRAM_TYPES, LATER_READ_PROGRAM_TYPES
_SAMPLE_TYPE = [None]
# Their probes, chosen by the 292-state comparison: the part-14 supplementary probes (records 0x26/0x5b,
# qualities 0-2) and the part-13 carry rule. The rand sites of the pre-draw block itself belong to the effect
# program and are left out of the body probes.
PRE_EXTENDED = [0x0b4b, 0x0b4c, 0x0b59, 0x0f1c, 0x0f1d, 0x0f2e, 0x1312, 0x1316, 0x1748, 0x1749, 0x1758, 0x230b,
                0x2311, 0x2382, 0x2383, 0x2384, 0x2385, 0x2394, 0x2395, 0x2494, 0x2499,
                # RENDER-ITEMS-002S (part 19), chosen the same way
                0x0b50, 0x22ec, 0x230c, 0x23ef, 0x2400, 0x2405, 0x248f, 0x2496, 0x24cf, 0x24d6,
                0x0f24, 0x0f28, 0x0f29, 0x0f2b, 0x0f2c, 0x1588]
PRE_CARRY = [0x0b4b, 0x0b4c, 0x0b59, 0x0f1c, 0x0f1d, 0x0f2e, 0x1748, 0x1749, 0x1758, 0x2311, 0x2382, 0x2383,
             0x2384, 0x2385, 0x2394, 0x2395, 0x2499,
             0x0b53, 0x22ec, 0x23ef, 0x2400, 0x2405, 0x248f, 0x24cf, 0x24d6,
             # RENDER-ITEMS-002T (part 21)
             0x0f1f, 0x0f20,
             # RENDER-ITEMS-002U (part 23)
             0x0f2a, 0x0f24, 0x0f28, 0x0f29, 0x0f2b, 0x0f2c]

EXIT_TYPES = [
    0x1588,
    0x0b10, 0x0b12, 0x0b22, 0x1569, 0x156a, 0x156b, 0x156c, 0x156d, 0x156e, 0x156f,
    0x1570, 0x1571, 0x1572, 0x1573, 0x1574, 0x170f, 0x1718, 0x1728, 0x1732, 0x1752,
    0x230a, 0x230e, 0x2310, 0x2318, 0x2381, 0x2392, 0x2393, 0x23ec, 0x23fd, 0x2402,
    0x2491, 0x2495, 0x2498, 0x249a,
]

PROBE_SEEDS = (3401, 7254, 9874, 3404, 7257, 9877, 3407, 7260, 9880, 3413, 7266, 9886)
# Part 14 supplementary probes (QUALITY_TYPES only; see supplement()).
SUPPLEMENT_SEEDS = (5101, 5102, 5103, 5104, 5105, 5106)
SUPPLEMENT_RECORDS = ((0, 0, 0), (0, 0x26, 0), (0, 0x5b, 0))
SUPPLEMENT_QUALITIES = (0, 1, 2, 9)

DIM_TYPES = [0xae6 + group * 512 + index for group in (7, 8, 9, 11)
             for index in (*range(0x11c, 0x12c), 0x13a, 0x15d, 0x193)]
PLAIN_TYPES = [*range(0x234a, 0x2368), *range(0x241d, 0x2477), *WING_TYPES]

# RENDER-ITEMS-002X: these cases bypass the level-glow helper chain.
NO_GLOW_TYPES = [0x232c, 0x232d, 0x232e, 0x232f, 0x2330, 0x26f5]
OMITTED_BASE_TYPES = [0x2368]
LATE_GLOW_TYPES = list(range(0x26e6, 0x26ed))
HELPER_TYPES = OMITTED_BASE_TYPES + LATE_GLOW_TYPES
OTHER_TYPES = [0x0b09, 0x0b0b, 0x0b28, 0x0b40, 0x0b42, 0x0b43, 0x0b45, 0x0b61,
               0x0eed, 0x0efa, 0x0f0b, 0x10f2, 0x1102, 0x1505, 0x1506, 0x1509,
               0x1576, 0x1577, 0x1736, 0x1746, 0x192f, 0x1b2f, 0x212f,
               0x2568, 0x2569, 0x256a, 0x256b]
OTHER_CARRY = [0x0b09, 0x0b0b, 0x0eed, 0x0efa, 0x0f0b, 0x10f2, 0x1506, 0x1509,
               0x2568, 0x2569, 0x256a, 0x256b]
OTHER_EXIT = []
PRE_CARRY += OTHER_CARRY
EXIT_TYPES += OTHER_EXIT


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

# Part 11: per-type straight-line SSE scalars after the wave helper 0x0185bdc4(a,0)
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
    """Return (kind, a, ops) or None. kind 1 = wave(a,0), 2 = sin(time*a)."""
    import struct
    call = ret - 5
    if _text(wa, call, 1) != b'\xe8' or _text(wa, call - 5, 5) != MOVSS_ESP:
        return None
    if helper == WAVE_HELPER:
        a = _load(wa, call - 13)
        if a is None or _text(wa, call - 14, 1) != b'\x51' or _text(wa, call - 19, 5) != MOVSS_ESP:
            return None
        # A constant phase is a separate input to the helper, in degrees.
        phase = None
        if _text(wa, call - 22, 3) == bytes.fromhex('0f57c0') and _text(wa, call - 23, 1) == b'\x51':
            phase = 0
        elif _text(wa, call - 28, 1) == b'\x51':
            phase = _load(wa, call - 27)
        if phase is None:
            return None
        a_value = v.u2f(a)
        if a_value == 0 or not 2 <= abs(6283.185546875 / a_value) < 2**31:
            return None
        kind, pops = (1 if phase == 0 else 9), b'\x59\x59'
    elif helper == SINE_WRAPPER:
        if (_text(wa, call - 6, 1) != b'\x51' or _text(wa, call - 14, 4) != bytes.fromhex('f30f5905') or
                _text(wa, call - 22, 8) != bytes.fromhex('f30f1005') + (0x06fce370).to_bytes(4, 'little')):
            return None
        a = _word(wa, struct.unpack_from('<I', _text(wa, call - 14, 8), 4)[0])
        if a is None:
            return None
        kind, pops = 2, b'\x59'
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
    ops = [(5, phase)] if kind == 9 else []
    reloaded = reload[:4] == (bytes.fromhex('f20f1085') if double else bytes.fromhex('f30f1085')) and fstp[2:] == reload[4:]
    if double and not reloaded:
        return None
    at += 14 if reloaded else 6
    while reloaded and len(ops) < 4:
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
    # A constant minus the saved helper result, each rounded to binary32.
    if not double and kind != 9 and not ops and _load(wa, at) is not None and \
            _text(wa, at + 8, 4) == bytes.fromhex('f30f5c85') and \
            _text(wa, at + 12, 4) == fstp[2:]:
        ops.append((5, _load(wa, at)))
    if not double:
        # comiss k,[saved result]; jbe L; movss k; movss [saved result],k.
        import capstone.x86 as X
        seq = list(_capstone().disasm(_text(wa, ret + len(pops) + 6, 40), ret + len(pops) + 6))
        if len(seq) >= 5:
            load, cmp, jump, again, store = seq[:5]
            if (load.mnemonic == again.mnemonic == 'movss' and cmp.mnemonic == 'comiss' and
                    jump.mnemonic == 'jbe' and store.mnemonic == 'movss' and
                    load.op_str == again.op_str and load.operands[1].type == X.X86_OP_MEM and
                    load.operands[1].mem.base == 0 and load.operands[1].mem.index == 0 and
                    cmp.operands[0].reg == load.operands[0].reg and
                    cmp.operands[1].type == store.operands[0].type == X.X86_OP_MEM and
                    cmp.operands[1].mem.base == store.operands[0].mem.base == X.X86_REG_EBP and
                    cmp.operands[1].mem.disp == store.operands[0].mem.disp == struct.unpack('<i', fstp[2:])[0] and
                    store.operands[1].reg == load.operands[0].reg and
                    jump.operands[0].imm == store.address + store.size):
                k = _word(wa, load.operands[1].mem.disp)
                if k is not None:
                    ops.append((6, k))
    return kind, a, tuple(ops)


# Part 14: body random. CRT rand 0x01989721, then at the return site
# cdq; (push n; pop ecx | mov ecx, n); idiv ecx; cvtsi2ss xmm0, edx and up to four
# binary32 mulss/addss/subss/divss data constants: (float)(rand() % n) op k ...
RAND = 0x01989721
RANGE, RANDOM_SCALE = 0x011ff622, 0x0185caa4


def parse_range(wa, ret):
    """Constant-argument 0x011ff622 / 0x0185caa4 call. Keep the integer offset before conversion,
    division and both clamps; the wrapper then divides and adds in binary32."""
    import struct
    call = ret - 5
    code = _text(wa, call, 5)
    if code[:1] != b'\xe8':
        return None
    target = ret + struct.unpack_from('<i', code, 1)[0]
    if target not in (RANGE, RANDOM_SCALE):
        return None
    at, args = call, []
    for _ in range(3 if target == RANGE else 4):
        # Pushes are read backwards, so the last push is argument 0.
        if _text(wa, at - 5, 5) == MOVSS_ESP:
            word = _load(wa, at - 13)
            if word is not None and _text(wa, at - 14, 1) == b'\x51':
                at -= 14
            elif _text(wa, at - 9, 9) == b'\x51\x0f\x57\xc0' + MOVSS_ESP:
                word, at = 0, at - 9
            else:
                return None
        elif _text(wa, at - 2, 1) == b'\x6a':
            word, at = struct.unpack_from('<b', _text(wa, at - 1, 1))[0] & 0xffffffff, at - 2
        elif _text(wa, at - 5, 1) == b'\x68':
            word, at = struct.unpack('<I', _text(wa, at - 4, 4))[0], at - 5
        else:
            return None
        args.append(word)
    f = lambda x: v.u2f(v.f2u(x))
    lo, hi = map(v.u2f, args[:2])
    steps = args[2] if target == RANGE else 1
    if not 0 < steps < 0x10000 or not -2**30 < lo <= hi < 2**30:
        return None
    low, high = int(f(f(float(steps)) * lo)), int(f(f(float(steps)) * hi))
    if not 0 < high - low + 1 < 2**31:
        return None
    ops = [(5, low & 0xffffffff), (4, v.f2u(f(float(steps)))), (6, args[0]), (7, args[1])]
    if target == RANDOM_SCALE:
        if v.u2f(args[2]) == 0.0:
            return None
        ops += [(4, args[2]), (2, args[3])]
    at = ret
    if target == RANDOM_SCALE and _text(wa, at, 6) == bytes.fromhex('83c40cd91c24'):
        return 4, high - low + 1, tuple(ops)
    pops = bytes.fromhex('83c40c') if target == RANGE else bytes.fromhex('83c410')
    if _text(wa, at, len(pops)) != pops:
        return None
    at += len(pops)
    fstp, reload = _text(wa, at, 6), _text(wa, at + 6, 8)
    if fstp[:2] == b'\xd9\x9d' and reload[:4] == bytes.fromhex('f30f1085') and fstp[2:] == reload[4:]:
        at += 14
        while len(ops) < CLOCK_OPS:
            code = _text(wa, at, 8)
            if code[:2] != b'\xf3\x0f' or code[2] not in SCALAR_OPS or code[3] != 0x05:
                break
            word = _word(wa, struct.unpack_from('<I', code, 4)[0])
            if word is None:
                return None
            ops.append((SCALAR_OPS[code[2]], word))
            at += 8
    return 4, high - low + 1, tuple(ops)


def parse_random(wa, ret, end=False):
    """Return (4, n, ops) for the idiom at a rand return site, or None (with end: and its end address)."""
    import struct
    at = ret
    if _text(wa, at, 1) != b'\x99':
        return None if end else parse_range(wa, ret)
    at += 1
    code = _text(wa, at, 5)
    if code[:1] == b'\x6a' and code[2:3] == b'\x59':
        n, at = struct.unpack_from('<b', code, 1)[0], at + 3
    elif code[:1] == b'\xb9':
        n, at = struct.unpack_from('<i', code, 1)[0], at + 5
    else:
        return None
    if n <= 0 or _text(wa, at, 6) != bytes.fromhex('f7f9f30f2ac2'):
        return None
    at += 6
    ops = []
    while len(ops) < 4:
        code = _text(wa, at, 8)
        if code[:2] != b'\xf3\x0f' or code[2] not in SCALAR_OPS or code[3] != 0x05:
            break
        word = _word(wa, struct.unpack_from('<I', code, 4)[0])
        if word is None:
            return None
        ops.append((SCALAR_OPS[code[2]], word))
        at += 8
    return ((4, n, tuple(ops)), at) if end else (4, n, tuple(ops))


# Part 15: body light set to a constant vector and scaled by the random value.
# 0x00cfcead is vec3::set(x, y, z) (binary32 stores), 0x00cfcd74 vec3::operator*=(float)
# (0x00cfcb3c multiplies each component in binary32, 0x00cfc8f2 assigns). At the site:
#   3 x (push ecx; movss xmm0, [k]; movss [esp], xmm0)  mov ecx,[ebp+8]; add ecx,0x54
#   call 0x00cfcead; call rand; <kind-4 idiom>; push ecx; movss [esp], xmm0
#   mov ecx,[ebp+8]; add ecx,0x54; call 0x00cfcd74
VEC_SET, VEC_SCALE = 0x00cfcead, 0x00cfcd74
MODEL_LIGHT_ECX = bytes.fromhex('8b4d0883c154')       # mov ecx,[ebp+8]; add ecx,0x54


def _calls(wa, at, target):
    import struct
    code = _text(wa, at, 5)
    return code[:1] == b'\xe8' and (at + 5 + struct.unpack_from('<i', code, 1)[0]) & 0xffffffff == target


def parse_scale(wa, ret):
    """The constant body-light words (x, y, z) a kind-4 value scales at this rand site, or None."""
    import struct
    parsed = parse_random(wa, ret, end=True)
    if parsed is None:
        return None
    at = parsed[1]
    if (_text(wa, at, 6) != bytes.fromhex('51f30f110424') or _text(wa, at + 6, 6) != MODEL_LIGHT_ECX or
            not _calls(wa, at + 12, VEC_SCALE)):
        return None
    start = ret - 5 - 5 - 6
    if not _calls(wa, ret - 10, VEC_SET) or _text(wa, start, 6) != MODEL_LIGHT_ECX:
        return None
    words = []
    for k in range(3):   # pushed z, y, x
        code = _text(wa, start - 14 * (3 - k), 14)
        if code[:5] != bytes.fromhex('51f30f1005') or code[9:] != bytes.fromhex('f30f110424'):
            return None
        word = _word(wa, struct.unpack_from('<I', code, 5)[0])
        if word is None:
            return None
        words.append(word)
    return tuple(reversed(words))


def random_value(program, value):
    """Reference evaluation of a kind-4 program for one rand() result."""
    f = lambda x: v.u2f(v.f2u(x))
    _, n, ops = program[:3]
    integer = value - int(value / n) * n
    if ops and ops[0][0] == 5:
        integer = _i32(integer + ops[0][1])
        ops = ops[1:]
    x = f(float(integer))
    for op, word in ops:
        k = v.u2f(word)
        x = f(max(k, x) if op == 6 else min(x, k) if op == 7 else
              x * k if op == 1 else x + k if op == 2 else x - k if op == 3 else math_div(x, k))
    return v.f2u(x)


def range_colour_programs(wa, ret, source):
    """0x0f24: each component is constant * range-local * constant, rounding at both mulss sites."""
    import re
    md = _capstone()
    ins = list(md.disasm(_text(wa, ret, 192), ret))
    if len(ins) < 2 or (ins[0].mnemonic, ins[0].op_str) != ('add', 'esp, 0xc') or ins[1].mnemonic != 'fstp':
        return []
    local = ins[1].op_str
    out = []
    for i in range(2, len(ins) - 2):
        a, b, c = ins[i:i + 3]
        if a.mnemonic != 'movss' or b.mnemonic != 'mulss' or b.op_str != 'xmm0, ' + local or c.mnemonic != 'mulss':
            continue
        words = []
        for ii in (a, c):
            m = re.fullmatch(r'xmm0, dword ptr \[(0x[0-9a-f]+)\]', ii.op_str)
            word = _word(wa, int(m[1], 16)) if m else None
            if word is None:
                break
            words.append(word)
        if len(words) == 2:
            out.append((6, source, tuple((1, word) for word in words)))
    return out


def counter_colour_seeds(wa, t, programs):
    """0x1588 sets (0.5, 0.35, 0.75), scales it by a wave, then by 0x0185caa4.
    Seed the intermediate component products so the next fit can retain the rounding before the random scale."""
    if t != 0x1588:
        return []
    call = 0x01736abc
    if not _calls(wa, call, VEC_SET) or _text(wa, call - 6, 6) != MODEL_LIGHT_ECX:
        raise ValueError('staff colour setter differs')
    words = []
    for k in range(3):
        at = call - 6 - 14 * (k + 1)
        if _text(wa, at, 1) != b'\x51' or _text(wa, at + 9, 5) != MOVSS_ESP:
            raise ValueError('staff colour arguments differ')
        word = _load(wa, at + 1)
        if word is None:
            raise ValueError('staff colour is not constant')
        words.append(word)
    return [(6, 35 + i, ((1, word),)) for i, p in enumerate(programs) if p[0] == 1 for word in words]


def derived_value(program, word):
    """Reference evaluation of a kind-6 program: input word as binary32, then binary32 operations."""
    f = lambda x: v.u2f(v.f2u(x))
    x = v.u2f(word)
    for op, k_word in program[2]:
        k = v.u2f(k_word)
        x = f(x * k if op == 1 else x + k if op == 2 else x - k if op == 3 else math_div(x, k))
    return v.f2u(x)


# Part 16: float words of each draw entry, and the float inputs a derived program may read
# (generic float words, object alpha, pulsed light, blend pulse, clock scalars; programs at 35..).
DERIVED_FIELDS = {'BODY': (1, 3, 4, 5, 8, 9, 10, 12, 13, 14), 'MESH': (2, 4, 5, 6, 8, 9, 10, 12, 13, 14)}
DERIVED_SOURCES = (1, 3, 4, 5, 8, 9, 10, 12, 13, 14, *range(16, 34))
_operands = None


def sse_operands(wa):
    """(op, constant word) of every binary32 mulss/addss/subss/divss xmm, [abs] in the text."""
    global _operands
    if _operands is None or _operands[0] is not wa:
        import re
        import struct
        found = set()
        for m in re.finditer(rb'\xf3\x0f([\x58\x59\x5c\x5e])([\x05\x0d\x15\x1d\x25\x2d\x35\x3d])', wa[0], re.S):
            word = _word(wa, struct.unpack_from('<I', wa[0], m.end())[0]) if m.end() + 4 <= len(wa[0]) else None
            if word is not None:
                found.add((SCALAR_OPS[m.group(1)[0]], word))
        _operands = (wa, found)
    return _operands[1]


def derive(wa, phases, width, products=False):
    """Kind-6 candidates (6, a, ((op, k),)) for the words no input or constant explains: the same
    binary32 operation with one constant maps input a to the word in every probe of the phase, and
    the text holds that operation on that constant (sse_operands)."""
    import math
    f = lambda x: v.u2f(v.f2u(x))
    found = []
    for pairs in phases:
        if not pairs or len({len(p[1]) for p in pairs}) != 1 or len({tuple(e for e, _ in p[1]) for p in pairs}) != 1:
            continue
        for k, (entry, _) in enumerate(pairs[0][1]):
            for field in DERIVED_FIELDS.get(entry, ()):
                ys = [p[1][k][1][field] for p in pairs]
                if len(set(ys)) == 1 or any([p[0][i] for p in pairs] == ys for i in range(width)):
                    continue
                order = [field] + list(range(35, width)) + [i for i in DERIVED_SOURCES if i != field]
                for source in order:
                    xs = [v.u2f(p[0][source]) for p in pairs]
                    if len(set(xs)) == 1 or any(math.isnan(x) or math.isinf(x) for x in xs):
                        continue
                    y0, x0 = v.u2f(ys[0]), xs[0]
                    hit = None
                    for op in (1, 2, 3, 4):
                        guess = (y0 / x0 if x0 else None, y0 - x0, x0 - y0, x0 / y0 if y0 else None)[op - 1]
                        if guess is None or math.isinf(guess) or math.isnan(guess) or abs(guess) > 3e38:
                            continue
                        for word in range(v.f2u(f(guess)) - 2, v.f2u(f(guess)) + 3):
                            word &= 0xffffffff
                            if (op, word) not in sse_operands(wa):
                                continue
                            program = (6, source, ((op, word),))
                            if all(derived_value(program, p[0][source]) == y for p, y in zip(pairs, ys)):
                                hit = program
                                break
                        if hit:
                            break
                    if hit:
                        if hit not in found:
                            found.append(hit)
                        break
                else:
                    if products:
                        # vec3::operator*= may scale a clock-dependent colour by a random range.
                        # Both operands are already modelled inputs, with one binary32 multiplication.
                        hit = None
                        for left in order:
                            for right in range(35, width):
                                if right == left:
                                    continue
                                xs = [v.u2f(p[0][left]) for p in pairs]
                                zs = [v.u2f(p[0][right]) for p in pairs]
                                if len(set(xs)) < 2 or len(set(zs)) < 2 or any(
                                        not math.isfinite(x * z) or abs(x * z) > 3e38 for x, z in zip(xs, zs)):
                                    continue
                                if all(v.f2u(f(x * z)) == y for x, z, y in zip(xs, zs, ys)):
                                    hit = (7, left, ((1, right),))
                                    break
                            if hit:
                                break
                        if hit and hit not in found:
                            found.append(hit)
    return found


def wave_helper(a, time, phase=0.0):
    """0x0185bdc4(a, 0): signed cosine wave, binary32 steps. The zero phase
    term adds a signed zero to time, which cannot change the truncated tick."""
    import math
    f = lambda x: v.u2f(v.f2u(x))
    shifted = f(f(f(f(phase * f(0.017453292)) * f(1000.0)) / a) + time) if phase else time
    tick = int(shifted) if -2147483648 <= shifted < 2147483648 else -2147483648
    period = int(f(f(6283.1855) / a))
    rem = int(math.fmod(tick, period))
    y = f(f(rem * f(0.001)) * a)
    w = f(math.cos(y))
    if f(3.1415927) > y:
        w = -w
    return f(f(w + f(1.0)) * f(0.5))


def scalar_value(program, time, frame=0):
    import math
    f = lambda x: v.u2f(v.f2u(x))
    kind, a, ops = program
    if kind == 3:
        return clock_value(ops, time, frame)
    if kind in (1, 9):
        value = wave_helper(v.u2f(a), time, v.u2f(ops[0][1]) if kind == 9 else 0.0)
        if kind == 9:
            ops = ops[1:]
    else:
        value = f(math.sin(f(time * v.u2f(a))))
    import struct
    double = bool(ops) and ops[0][0] & 8
    for op, word in ops:
        k = struct.unpack('<d', struct.pack('<Q', word))[0] if double else v.u2f(word)
        op &= 7
        value = (value * k if op == 1 else value + k if op == 2 else value - k if op == 3 else
                 k - value if op == 5 else max(value, k) if op == 6 else value / k)
        if not double:
            value = f(value)
    return v.f2u(f(value))


# Part 12: straight-line clock programs. The probes record every executed basic
# block that reads the clock global 0x06fce370. A static walk of the pinned bytes
# from the block start follows the SSE/integer data flow of each clock read into a
# linear operation chain. Constants come from the data image, immediates and
# compiler idioms (signed power-of-two remainder/quotient, cdq/idiv). A local read
# before any write in the walk takes the value of that local at block entry; it
# must also be stored as that immediate somewhere in the text. Any other
# instruction only clears what it writes. Chains whose result is stored as
# binary32 become candidate inputs; the full comparisons decide admission.
CLOCK = 0x06fce370
(C_TIME_F, C_TIME_D, C_TICK, C_F_MUL, C_F_DIV, C_F_ADD, C_F_SUB, C_F_RSUB, C_F_RDIV, C_D_MUL, C_D_DIV,
 C_D_ADD, C_D_SUB, C_D_RSUB, C_D_RDIV, C_F2D, C_D2F, C_F2I, C_D2I, C_I2F, C_I2D, C_I_MOD, C_I_DIV,
 C_I_ADD, C_I_MUL, C_F_NEG, C_I_NEG, C_D_NEG, C_I_RSUB) = range(1, 30)
# RENDER-ITEMS-002U (part 23): the rendered-frame counter [0x0bdc5ebc] as a chain source (the integer register),
# unsigned remainder/quotient (xor edx, edx; div) and the unsigned binary64 conversion (cvtsi2sd, then
# shr r, 31; addsd [r*8 + 0x01bd3050] with the table {0.0, 2^32}).
C_FRAME, C_U_MOD, C_U_DIV, C_U2D = range(30, 34)
C_F_SIN, C_F_ABS, C_F_FABS = 34, 35, 36
FRAME_COUNTER, U32_FIX = 0x0bdc5ebc, 0x01bd3050
COUNTER_RANGE_TYPES = [0x0f24, 0x0f28, 0x0f29, 0x0f2b, 0x0f2c, 0x1588]
VECTOR_SETTERS = (0x00cfcead, 0x00cfcede)   # (this)[0..2] = (a, b, c) / (a, a, a); ret 0xc / ret 4
# The bodies whose draws read the counter (found by comparing the client's streams at different counter values over
# the 1,691 survey types; their probes vary it). Fifty-one were admitted with recipes right only at counter 0.
FRAME_TYPES = [
    0x0b66, 0x0b67, 0x0b69, 0x0b6a, 0x0b6b, 0x0b6c, 0x0b6d, 0x0b6e, 0x0b6f, 0x0b70, 0x0b71, 0x0b72, 0x0b73, 0x0f2f,
    0x0f30, 0x1109, 0x110a, 0x132b, 0x132c, 0x132e, 0x1560, 0x1561, 0x1574, 0x157d, 0x157f, 0x1580, 0x1581, 0x1582,
    0x1583, 0x1584, 0x1585, 0x1586, 0x1587, 0x1589, 0x158a, 0x158b, 0x158c, 0x158d, 0x158e, 0x1739, 0x173a, 0x173b,
    0x173c, 0x1747, 0x1756, 0x1757, 0x1759, 0x175a, 0x175b, 0x175c, 0x175d,
    0x0f2a,
    # RENDER-ITEMS-002V: counter mesh scrolls plus quantised random body-light scalars.
    0x0f24, 0x0f28, 0x0f29, 0x0f2b, 0x0f2c, 0x1588,
]
CLOCK_OPS = 12   # RENDER-ITEMS-002U: 10 for 0x1109's counter atlas (was 9)
_md = None
_clock_sites = None
_frame_sites = []   # RENDER-ITEMS-002U: text addresses of the counter's address bytes (filled with the clock sites)
_slices = {}


def _capstone():
    global _md
    if _md is None:
        import capstone
        _md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        _md.detail = True
    return _md


def clock_sites(wa):
    """Sorted addresses of instructions whose memory operand is the clock global."""
    global _clock_sites
    if _clock_sites is None or _clock_sites[0] is not wa:
        import re
        md, text, found = _capstone(), wa[0], []
        for m in re.finditer(re.escape(CLOCK.to_bytes(4, 'little')), text):
            for back in range(8, 1, -1):
                start = m.start() - back
                ins = next(md.disasm(text[start:start + 16], 0x00401000 + start), None)
                if ins and ins.address + ins.size == 0x00401000 + m.start() + 4 and '0x6fce370]' in ins.op_str:
                    found.append(ins.address)
                    break
        # RENDER-ITEMS-002U: where the counter's address bytes lie (a block reads it when its bytes contain them)
        _frame_sites[:] = [0x00401000 + m.start() for m in re.finditer(re.escape(FRAME_COUNTER.to_bytes(4, 'little')),
                                                                      text)]
        _clock_sites = (wa, sorted(found))
    return _clock_sites[1]


def _f32(x):
    return v.u2f(v.f2u(x))


def _i32(x):
    return (x + 2**31) % 2**32 - 2**31


def _f64(word):
    import struct
    return struct.unpack('<d', struct.pack('<Q', word))[0]


def _d64(x):
    import struct
    return struct.unpack('<Q', struct.pack('<d', x))[0]


def _local_stored(wa, offset, value):
    """mov dword [ebp+offset], value exists in the pinned text."""
    import struct
    imm = struct.pack('<I', value & 0xffffffff)
    if -128 <= offset < 128:
        if b'\xc7\x45' + struct.pack('<b', offset) + imm in wa[0]:
            return True
    return b'\xc7\x85' + struct.pack('<i', offset) + imm in wa[0]


def slice_block(wa, block, frame=False):
    """Static walk from one block start. Returns (entry locals read, outputs) where
    each output is a chain whose integer local reads are ('local', offset). frame (RENDER-ITEMS-002U): the block
    reads the rendered-frame counter; only then the counter idioms apply (other blocks slice as before)."""
    if (block, frame) in _slices:
        return _slices[(block, frame)]
    import capstone.x86 as X
    md, text = _capstone(), wa[0]
    gpr = {'eax', 'ebx', 'ecx', 'edx', 'esi', 'edi'}
    regs, local, outputs, entry = {}, {}, [], set()

    def ref(op):
        """('abs', a) / ('local', off) / ('other',) for a memory operand."""
        m = op.mem
        if m.base == 0 and m.index == 0:
            return ('abs', m.disp & 0xffffffff)
        if m.base == X.X86_REG_EBP and m.index == 0:
            return ('local', m.disp)
        return ('other',)

    def value(ins, op, size):
        if op.type == X.X86_OP_IMM:
            return ('k', _i32(op.imm))
        if op.type == X.X86_OP_REG:
            return regs.get(ins.reg_name(op.reg))
        r = ref(op)
        if r[0] == 'abs':
            if r[1] == CLOCK and size == 4:
                return 'clock'
            if r[1] == FRAME_COUNTER and size == 4:
                return 'frame'
            word = _word(wa, r[1])
            if word is None:
                return None
            if size == 8:
                high = _word(wa, r[1] + 4)
                return None if high is None else ('kd', word | high << 32)
            if size == 16:
                return ('mask', word)
            return ('kw', word)
        if r[0] == 'local':
            if r[1] in local:
                return local[r[1]]
            if size == 4 and r[1] < 0:
                entry.add(r[1])
                return ('e', r[1], 1, 0)
        return None

    def chain(x, kind, *ops):
        return ('c', kind, x[2] + tuple(ops))

    def as_int(x):
        """Integer constant: ('k', n) or ('e', offset, mul, add) = entry local*mul+add."""
        return x if x and x[0] in ('k', 'e', 'quotient', 'linear') else None

    def lin(x, mul, add):
        if x[0] == 'k':
            return ('k', _i32(x[1] * mul + add))
        if x[0] != 'e':
            return ('linear', x, mul, add)
        return ('e', x[1], x[2] * mul, x[3] * mul + add)

    at, steps, cdq = block, 0, None
    pushed = None   # RENDER-ITEMS-002U: push imm; pop r
    stack_top, x87 = None, None
    while steps < 160:
        ins = next(md.disasm(text[at - 0x00401000:at - 0x00401000 + 16], at), None)
        if ins is None:
            break
        steps += 1
        nxt = at + ins.size
        name, ops = ins.mnemonic, ins.operands
        dst = ops[0] if ops else None
        dname = ins.reg_name(dst.reg) if dst is not None and dst.type == X.X86_OP_REG else None
        handled, result = True, None
        src = ops[1] if len(ops) > 1 else None
        if name in ('jmp',) and dst.type == X.X86_OP_IMM:
            at = dst.imm
            continue
        if frame and name == 'call' and dst.type == X.X86_OP_IMM and dst.imm in VECTOR_SETTERS:
            # RENDER-ITEMS-002U: a vec3 setter (writes three floats through ecx, nothing of the caller's frame)
            regs, pushed = {}, None
            at = nxt
            continue
        if name == 'call' and dst.type == X.X86_OP_IMM and dst.imm in (SINE_WRAPPER, 0x0184f8ff, 0x0098a647):
            if stack_top and stack_top[0] == 'c' and stack_top[1] == 'f':
                operation = C_F_SIN if dst.imm == SINE_WRAPPER else C_F_FABS if dst.imm == 0x0098a647 else C_F_ABS
                x87 = chain(stack_top, 'f', (operation, 0))
                regs = {}
                at = nxt
                continue
            break
        if name == 'fstp' and dst.type == X.X86_OP_MEM and dst.size == 4 and x87 is not None:
            r = ref(dst)
            if r[0] == 'local':
                local[r[1]] = x87
                outputs.append(x87)
            elif dst.mem.base == X.X86_REG_ESP and dst.mem.disp == 0:
                stack_top = x87
            else:
                break
            x87 = None
            at = nxt
            continue
        if name.startswith('j') or name in ('call', 'ret', 'retn', 'int3', 'leave'):
            break
        if name in ('push', 'pop'):
            stack_top = None
        if frame and name == 'push' and dst.type == X.X86_OP_IMM:
            pushed = ('k', _i32(dst.imm))
            at = nxt
            continue
        if name == 'pop' and dname in gpr and pushed is not None:
            regs[dname], pushed = pushed, None
            at = nxt
            continue
        pushed = None
        if name == 'mov' and dname in gpr:
            result = value(ins, src, 4)
            if result == 'clock' or (result == 'frame' and not frame):
                result = None
            elif result == 'frame':
                result = ('c', 'i', ((C_FRAME, 0),))
        elif name == 'mov' and dst.type == X.X86_OP_MEM:
            r = ref(dst)
            if r[0] == 'local':
                local[r[1]] = value(ins, src, 4)
            elif r[0] == 'abs' and r[1] == CLOCK:
                break
            handled = 'stored'
        elif name in ('movss', 'movsd') and dst.type == X.X86_OP_REG:
            size = 4 if name == 'movss' else 8
            x = value(ins, src, size)
            if x == 'clock':
                result = ('c', 'f', ((C_TIME_F, 0),))
            elif x and x[0] == 'kw' and size == 4:
                result = ('kf', x[1])
            elif x and x[0] == 'kd' and size == 8:
                result = x
            elif x and x[0] == 'c' and x[1] == ('f' if size == 4 else 'd'):
                result = x
            elif x and x[0] in ('kf',) and size == 4:
                result = x
        elif name in ('movss', 'movsd') and dst.type == X.X86_OP_MEM:
            x = regs.get(ins.reg_name(src.reg))
            r = ref(dst)
            if x and x[0] == 'c' and x[1] == 'f' and name == 'movss':
                outputs.append(x)
            if r[0] == 'local':
                local[r[1]] = x if name == 'movss' else (
                    x if frame and x and x[0] == 'c' and x[1] == 'd' and any(op == C_FRAME for op, _ in x[2]) else None)
            elif r[0] == 'abs' and r[1] == CLOCK:
                break
            elif dst.mem.base == X.X86_REG_ESP and dst.mem.disp == 0:
                stack_top = x
            handled = 'stored'
        elif (frame and name == 'addsd' and dname and src.type == X.X86_OP_MEM and src.mem.base == 0 and src.mem.index and
              src.mem.scale == 8 and src.mem.disp & 0xffffffff == U32_FIX and _word(wa, U32_FIX) == 0 and
              _word(wa, U32_FIX + 4) == 0 and _word(wa, U32_FIX + 8) == 0 and _word(wa, U32_FIX + 12) == 0x41f00000):
            # RENDER-ITEMS-002U: cvtsi2sd x, n; shr r, 31 (r = n); addsd x, [r*8 + U32_FIX]: (double)(uint32_t)n
            x, sign = regs.get(dname), regs.get(ins.reg_name(src.mem.index))
            result = None
            if (x and x[0] == 'c' and x[1] == 'd' and sign and sign[0] == 'sign' and
                    x[2] == sign[1][2] + ((C_I2D, 0),)):
                result = ('c', 'd', sign[1][2] + ((C_U2D, 0),))
        elif frame and name == 'xor' and dname in gpr and src.type == X.X86_OP_REG and src.reg == dst.reg:
            result = ('zero',)
        elif frame and name == 'div':
            # RENDER-ITEMS-002U: xor edx, edx; div n (unsigned)
            x, high, n = regs.get('eax'), regs.get('edx'), as_int(value(ins, dst, 4))
            if x and x[0] == 'c' and x[1] == 'i' and high == ('zero',) and n:
                regs['eax'] = chain(x, 'i', (C_U_DIV, ('i', n)))
                regs['edx'] = chain(x, 'i', (C_U_MOD, ('i', n)))
            else:
                regs['eax'] = regs['edx'] = None
            at = nxt
            continue
        elif frame and name == 'shr' and dname in gpr and src.type == X.X86_OP_IMM and src.imm == 31:
            x = regs.get(dname)
            result = ('sign', x) if x and x[0] == 'c' and x[1] == 'i' else None
        elif name == 'cvtss2sd':
            x = value(ins, src, 4)
            if x == 'clock':
                result = ('c', 'd', ((C_TIME_D, 0),))
            elif x and x[0] == 'c' and x[1] == 'f':
                result = chain(x, 'd', (C_F2D, 0))
        elif name == 'cvtsd2ss':
            x = value(ins, src, 8)
            if x and x[0] == 'c' and x[1] == 'd':
                result = chain(x, 'f', (C_D2F, 0))
        elif name in ('cvttss2si', 'cvttsd2si') and dname in gpr:
            x = value(ins, src, 4 if name == 'cvttss2si' else 8)
            if frame and name == 'cvttss2si' and x and x != 'frame' and x[0] in ('kf', 'kw'):
                # RENDER-ITEMS-002U: a binary32 constant truncated to an integer constant
                k = v.u2f(x[1])
                result = ('k', int(k)) if -2147483648.0 <= k < 2147483648.0 else ('k', -2147483648)
            elif x == 'clock' and name == 'cvttss2si':
                result = ('c', 'i', ((C_TICK, 0),))
            elif x and x[0] == 'c' and x[1] == ('f' if name == 'cvttss2si' else 'd'):
                result = chain(x, 'i', (C_F2I if name == 'cvttss2si' else C_D2I, 0))
        elif name in ('cvtsi2ss', 'cvtsi2sd'):
            x = value(ins, src, 4)
            kind, op = ('f', C_I2F) if name == 'cvtsi2ss' else ('d', C_I2D)
            if x and x[0] == 'c' and x[1] == 'i':
                result = chain(x, kind, (op, 0))
            elif as_int(x):
                result = ('kint', kind, x)
        elif name in ('mulss', 'divss', 'addss', 'subss', 'mulsd', 'divsd', 'addsd', 'subsd'):
            single = name.endswith('ss')
            x = regs.get(dname)
            y = value(ins, src, 4 if single else 8)
            kind = 'f' if single else 'd'
            base = {'mul': 0, 'div': 1, 'add': 2, 'sub': 3}[name[:3]]
            fops = (C_F_MUL, C_F_DIV, C_F_ADD, C_F_SUB) if single else (C_D_MUL, C_D_DIV, C_D_ADD, C_D_SUB)
            rops = {0: fops[0], 2: fops[2], 1: C_F_RDIV if single else C_D_RDIV, 3: C_F_RSUB if single else C_D_RSUB}
            def const(z):
                if z is None or z == 'clock':
                    return None
                if single and z[0] in ('kf', 'kw'):
                    return ('w', z[1])
                if not single and z[0] == 'kd':
                    return ('w', z[1])
                if z[0] == 'kint' and z[1] == kind:
                    return ('i', z[2])
                return None
            if (frame and single and x and x != 'frame' and x[0] in ('kf', 'kw') and y and y not in ('clock', 'frame')
                    and y[0] in ('kf', 'kw')):
                # RENDER-ITEMS-002U: two binary32 constants fold (one binary32 operation)
                a_, b_ = v.u2f(x[1]), v.u2f(y[1])
                folded = (a_ * b_ if base == 0 else math_div(a_, b_) if base == 1 else a_ + b_ if base == 2 else a_ - b_)
                result = ('kf', v.f2u(_f32(folded)))
            elif x and x[0] == 'c' and x[1] == kind and const(y):
                result = chain(x, kind, (fops[base], const(y)))
            elif y and y != 'clock' and y[0] == 'c' and y[1] == kind and const(x):
                result = chain(y, kind, (rops[base], const(x)))
        elif name in ('xorps', 'xorpd'):
            x, y = regs.get(dname), value(ins, src, 16)
            if src.type == X.X86_OP_REG and src.reg == dst.reg:
                result = ('kf', 0) if name == 'xorps' else ('kd', 0)
            elif x and x[0] == 'c' and y and y[0] == 'mask':
                high = _word(wa, ref(src)[1] + 4)
                if name == 'xorps' and x[1] == 'f' and y[1] == 0x80000000:
                    result = chain(x, 'f', (C_F_NEG, 0))
                elif name == 'xorpd' and x[1] == 'd' and y[1] == 0 and high == 0x80000000:
                    result = chain(x, 'd', (C_D_NEG, 0))
        elif name == 'cdq':
            x = regs.get('eax')
            regs['edx'] = ('cdq', x) if as_int(x) or (x and x[0] == 'c' and x[1] == 'i') else None
            at = nxt
            continue
        elif name == 'idiv':
            x, sign, n = regs.get('eax'), regs.get('edx'), as_int(value(ins, dst, 4))
            if x and x[0] == 'c' and sign == ('cdq', x) and n:
                regs['eax'] = chain(x, 'i', (C_I_DIV, ('i', n)))
                regs['edx'] = chain(x, 'i', (C_I_MOD, ('i', n)))
            else:
                regs['eax'] = regs['edx'] = None
            at = nxt
            continue
        elif name == 'and' and dname in gpr and src.type == X.X86_OP_IMM:
            x, mask = regs.get(dname), src.imm & 0xffffffff
            low = mask & 0x7fffffff
            target = nxt
            follow = next(md.disasm(text[target - 0x00401000:target - 0x00401000 + 16], target), None)
            if (mask & 0x80000000 and low & (low + 1) == 0 and x and x[0] == 'c' and x[1] == 'i' and
                    follow and follow.mnemonic == 'jns'):
                # and r,0x8000000m; jns L; dec r; or r,-(m+1); inc r; L:  ==  r % (m+1)
                fix = text[follow.address + 2 - 0x00401000:follow.operands[0].imm - 0x00401000]
                r = ['eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi'].index(dname)
                minus = (-(low + 1)).to_bytes(4, 'little', signed=True)
                forms = [bytes([0x81, 0xc8 + r]) + minus] + ([b'\x0d' + minus] if r == 0 else [])
                if low < 128:
                    forms.append(bytes([0x83, 0xc8 + r, minus[0]]))
                if follow.size == 2 and fix in [bytes([0x48 + r]) + form + bytes([0x40 + r]) for form in forms]:
                    regs[dname] = chain(x, 'i', (C_I_MOD, ('i', ('k', low + 1))))
                    at = follow.operands[0].imm
                    continue
            elif dname == 'edx' and regs.get('edx') and regs['edx'][0] == 'cdq' and low == mask and low & (low + 1) == 0:
                regs['edx'] = ('bias', regs['edx'][1], low + 1)
                at = nxt
                continue
            result = None
        elif name in ('add', 'sub') and dname in gpr:
            x, y = regs.get(dname), value(ins, src, 4)
            if name == 'add' and dname == 'eax' and y and y[0] == 'bias' and y[1] == x:
                result = ('biased', x, y[2])
            elif name == 'sub' and dname == 'eax' and y and y[0] == 'cdq' and y[1] == x:
                result = ('biased', x, 2)
            elif as_int(x) and y and y[0] == 'k':
                result = lin(x, 1, y[1] if name == 'add' else -y[1])
            elif name == 'sub' and as_int(x) and y and y[0] == 'c' and y[1] == 'i':
                result = chain(y, 'i', (C_I_RSUB, ('i', x)))
            elif name == 'add' and as_int(y) and x and x[0] == 'c' and x[1] == 'i':
                result = chain(x, 'i', (C_I_ADD, ('i', y)))
            elif name == 'add' and as_int(x) and y and y[0] == 'c' and y[1] == 'i':
                result = chain(y, 'i', (C_I_ADD, ('i', x)))
            elif x and x[0] == 'c' and x[1] == 'i' and y and y[0] == 'k':
                result = chain(x, 'i', (C_I_ADD, ('i', ('k', y[1] if name == 'add' else _i32(-y[1])))))
        elif name == 'shl' and dname in gpr and src.type == X.X86_OP_IMM:
            x = regs.get(dname)
            if as_int(x):
                result = lin(x, 1 << src.imm, 0)
            elif x and x[0] == 'c' and x[1] == 'i':
                result = chain(x, 'i', (C_I_MUL, ('i', ('k', _i32(1 << src.imm)))))
        elif name == 'sar' and dname in gpr and src.type == X.X86_OP_IMM:
            x = regs.get(dname)
            if x and x[0] == 'biased' and 1 << src.imm == x[2]:
                result = (('quotient', x[1], x[2]) if as_int(x[1]) else
                          chain(x[1], 'i', (C_I_DIV, ('i', ('k', x[2])))))
        elif name in ('inc', 'dec', 'neg') and dname in gpr:
            x = regs.get(dname)
            step = {'inc': 1, 'dec': -1}.get(name)
            if as_int(x):
                result = lin(x, -1, 0) if step is None else lin(x, 1, step)
            elif x and x[0] == 'c' and x[1] == 'i':
                result = chain(x, 'i', (C_I_NEG, 0) if step is None else (C_I_ADD, ('i', ('k', step))))
        elif name == 'imul' and dname in gpr:
            if len(ops) == 3:
                x, y = value(ins, src, 4), ('k', _i32(ops[2].imm))
            else:
                x, y = regs.get(dname), value(ins, src, 4)
            if as_int(x) and y and y[0] == 'k':
                result = lin(x, y[1], 0)
            elif as_int(y) and x and x[0] == 'k':
                result = lin(y, x[1], 0)
            elif x and x[0] == 'c' and x[1] == 'i' and y and y[0] == 'k':
                result = chain(x, 'i', (C_I_MUL, ('i', y)))
        elif name in ('push', 'nop', 'cmp', 'test', 'comiss', 'ucomiss', 'comisd', 'ucomisd'):
            handled = 'stored'
        else:
            handled = False
        if handled is True:
            regs[dname if dname else ''] = result
        elif handled is False:
            # Clear every written register and local; nothing else is assumed.
            _, written = ins.regs_access()
            for reg in written:
                regs[ins.reg_name(reg)] = None
                if ins.reg_name(reg) == 'esp':
                    pass
            for op in ops:
                if op.type == X.X86_OP_MEM and op.access & 2:
                    r = ref(op)
                    if r[0] == 'local':
                        local[r[1]] = None
                    elif r[0] == 'abs' and r[1] == CLOCK:
                        steps = 999
            if name in ('call',):
                break
        at = nxt
    _slices[(block, frame)] = (tuple(sorted(entry)), tuple(dict.fromkeys(outputs)))
    return _slices[(block, frame)]


def resolve_clock(wa, program, values):
    """Substitute entry-local values; ('i', n) operands become 32-bit words."""
    def integer(n):
        if n[0] == 'k':
            return n[1]
        if n[0] == 'quotient':
            base = integer(n[1])
            return None if base is None else int(base / n[2])
        if n[0] == 'linear':
            base = integer(n[1])
            return None if base is None else _i32(base * n[2] + n[3])
        base = values[n[1]]
        return _i32(base * n[2] + n[3]) if _local_stored(wa, n[1], base) else None
    ops = []
    for op, k in program:
        if isinstance(k, tuple) and k[0] == 'w':
            ops.append((op, k[1]))
        elif isinstance(k, tuple):
            n = k[1]
            word = integer(n)
            if word is None:
                return None
            if k[0] == 'i' and op in (C_F_MUL, C_F_DIV, C_F_ADD, C_F_SUB, C_F_RSUB, C_F_RDIV):
                word = v.f2u(_f32(float(word)))
            elif k[0] == 'i' and op in (C_D_MUL, C_D_DIV, C_D_ADD, C_D_SUB, C_D_RSUB, C_D_RDIV):
                word = _d64(float(word))
            if op in (C_I_MOD, C_I_DIV) and word in (0, -1):
                return None
            if op in (C_U_MOD, C_U_DIV) and word & 0xffffffff == 0:
                return None
            ops.append((op, word & 0xffffffffffffffff))
        else:
            ops.append((op, 0))
    return tuple(ops) if len(ops) <= CLOCK_OPS else None


def clock_value(ops, time, frame=0):
    """Reference evaluation of a clock chain; returns the binary32 word. frame: [0x0bdc5ebc] (RENDER-ITEMS-002U)."""
    import math
    f = i = d = None
    def trunc(x):
        return int(x) if -2147483648 <= x < 2147483648 else -2147483648
    for op, k in ops:
        kf, kd = v.u2f(k & 0xffffffff), _f64(k)
        if op == C_TIME_F: f = time
        elif op == C_TIME_D: d = float(time)
        elif op == C_TICK: i = trunc(time)
        elif op == C_F_MUL: f = _f32(f * kf)
        elif op == C_F_DIV: f = _f32(f / kf) if kf else _f32(math_div(f, kf))
        elif op == C_F_ADD: f = _f32(f + kf)
        elif op == C_F_SUB: f = _f32(f - kf)
        elif op == C_F_RSUB: f = _f32(kf - f)
        elif op == C_F_RDIV: f = _f32(math_div(kf, f))
        elif op == C_F_SIN: f = _f32(math.sin(f))
        elif op == C_F_ABS: f = -f if 0 > f else f
        elif op == C_F_FABS: f = abs(f)
        elif op == C_D_MUL: d = d * kd
        elif op == C_D_DIV: d = math_div(d, kd)
        elif op == C_D_ADD: d = d + kd
        elif op == C_D_SUB: d = d - kd
        elif op == C_D_RSUB: d = kd - d
        elif op == C_D_RDIV: d = math_div(kd, d)
        elif op == C_F2D: d = float(f)
        elif op == C_D2F: f = _f32(d)
        elif op == C_F2I: i = trunc(f)
        elif op == C_D2I: i = trunc(d)
        elif op == C_I2F: f = _f32(float(i))
        elif op == C_I2D: d = float(i)
        elif op in (C_I_MOD, C_I_DIV):
            # C99/idiv truncation; the generator excludes divisors 0 and -1.
            n = _i32(k & 0xffffffff)
            q = abs(i) // abs(n) * (1 if (i < 0) == (n < 0) else -1)
            i = _i32(q) if op == C_I_DIV else i - q * n
        elif op == C_I_ADD: i = _i32(i + _i32(k & 0xffffffff))
        elif op == C_I_RSUB: i = _i32(_i32(k & 0xffffffff) - i)
        elif op == C_I_MUL: i = _i32(i * _i32(k & 0xffffffff))
        elif op == C_F_NEG: f = -f
        elif op == C_I_NEG: i = _i32(-i)
        elif op == C_D_NEG: d = -d
        elif op == C_FRAME: i = _i32(frame)
        elif op == C_U_MOD: i = _i32((i & 0xffffffff) % (k & 0xffffffff))
        elif op == C_U_DIV: i = _i32((i & 0xffffffff) // (k & 0xffffffff))
        elif op == C_U2D: d = float(i & 0xffffffff)
    return v.f2u(f)


def math_div(a, b):
    import math
    if b == 0:
        if a == 0 or a != a:
            return math.nan
        return math.copysign(math.inf, a) * math.copysign(1, b)
    return a / b


def flat(d):
    return [*d[1], *d[2], d[3], *d[4], d[5]]


# Part 13: immediate glColor3f/3fv/4f calls of the body join the draw stream as
# COLOR records (kind, alpha, RGB read at call time) in call order. The native
# raster keeps the current colour across draws, like GL.
# glColor3f/3fv/4f recorders (part 13) live in validate_renderchar, which compares them too.
COLOUR_SLOTS = v.COLOUR_SLOTS
record_colours = v.record_colours

_sample_state = None
_site_sink = None
# Part 14: model fields when a RenderObjDraw helper call returns, as (site, fields).
_EXITS = []
# Part 14 body random (extended probes only): the scripted rand results, the calls
# as (helper tag, return site, value), and return sites in first-call order.
_RAND = {'on': False, 'seq': [], 'calls': [], 'order': [], 'masks': {}}
RAND_ABSENT = 0x7fc0dead   # input word of a kind-4 program in a group that does not draw it
HELPERS = (0x016e036c, 0x016dc148, 0x016dec15)   # body, BodyColor2, BodyColor
_helper_returns = None


def helper_returns(wa):
    """Return sites of the helper calls inside RenderObjDraw (0x0176ce74)."""
    global _helper_returns
    if _helper_returns is None or _helper_returns[0] is not wa:
        import struct
        text, found = wa[0], []
        start, end = 0x0176ce74 - 0x00401000, 0x017e7000 - 0x00401000
        for i in range(start, end):
            if text[i] == 0xe8:
                target = (0x00401000 + i + 5 + struct.unpack_from('<i', text, i + 1)[0]) & 0xffffffff
                if target in HELPERS:
                    found.append(0x00401000 + i + 5)
        _helper_returns = (wa, tuple(found))
    return _helper_returns[1]


def _original(wa, case, factory, tags):
    """The pinned instructions for one sample: client_stream plus what the world's hooks record (helper tags,
    helper exits, random draws and their sites, wave/clock sites). TEST-SPEED-001: cached by the case and the
    random sequence when MU_VALIDATOR_CACHE is set; the generic C stream is always computed fresh."""
    global _site_sink
    sites = _site_sink

    def run():
        global _site_sink
        _site_sink = set()
        try:
            # This probing world owns the lookup recorder; keep the generic case shim out.
            original_case = dict(case)
            original_case.pop('named_meshes', None)
            r, st, other, _ = v.client_stream(wa, original_case, factory)
            return r['ok'], st, other, list(tags), list(_EXITS), list(_RAND['calls']), frozenset(_site_sink)
        finally:
            _site_sink = sites
    key = (case, _RAND['on'], tuple(_RAND['seq']) if _RAND['on'] else ())
    ok, st, other, tagged, exits, calls, found = original_cache.named('gen_item_bodies', Path(__file__)).get(
        'sample', key, run)
    tags[:] = tagged
    _EXITS[:] = exits
    _RAND['calls'][:] = calls
    for _, site, _ in calls:
        if site not in _RAND['order']:
            _RAND['order'].append(site)
    if sites is not None:
        sites.update(found)
    return {'ok': ok}, st, other


def exit_record(fields):
    """EXIT pseudo-draw in client-stream form: words 8..15 are the model fields."""
    return ('EXIT', [0] * 8, tuple(fields[0]), fields[1], tuple(fields[2]), fields[3])


NAMED_TYPES = v.NAMED_BODY_TYPES
LEVEL_SPLIT += list(NAMED_TYPES)
FRAME_TYPES += [0x0b68]
COUNTER_RANGE_TYPES += [0x0b5c, 0x0b62, 0x1313, 0x1317, 0x1319]
PRE_EXTENDED += [0x1313, 0x1317, 0x1319] + READ_PROGRAM_TYPES
# RENDER-ITEMS-002X: carry the last draw into later helpers, with full supplementary probes.
PRE_CARRY += [t for t in READ_PROGRAM_TYPES if t not in (0x0b29, 0x0b4d, 0x0b52, 0x1314)]
# These probes retain alpha/wave products and attribute nested pre-program ranges correctly.
COUNTER_RANGE_TYPES += READ_PROGRAM_TYPES + OTHER_TYPES
NAMED_NAMES = v.NAMED_MESH_NAMES
_NAMED_VALUES = []

def sample(wa, lib, t, lv, seed, opt=0, ext=0, params=(), sites=None, carry=False, quality=9, record=(0, 0, 0), time_word=None):
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
            record_colours(self, tags)
            from unicorn import UC_HOOK_CODE
            def site(uc, address, size, context):
                if _site_sink is not None:
                    m = self.m
                    _site_sink.add((address, m.r32(uc.reg_read(m.x86.UC_X86_REG_ESP))))
            for addr in (WAVE_HELPER, SINE_WRAPPER):
                self.m.uc.hook_add(UC_HOOK_CODE, site, begin=addr, end=addr)
            from unicorn import UC_HOOK_BLOCK
            import bisect
            clocks = clock_sites(wa)
            frames = list(_frame_sites)
            def block(uc, address, size, context):
                if _site_sink is None:
                    return
                # RENDER-ITEMS-002U: blocks that read the rendered-frame counter, for FRAME_TYPES only
                f = bisect.bisect_left(frames, address)
                counter = (_SAMPLE_TYPE[0] in FRAME_TYPES or _SAMPLE_TYPE[0] in OTHER_TYPES) and f < len(frames) and frames[f] + 4 <= address + size
                k = bisect.bisect_left(clocks, address)
                if not counter and (k == len(clocks) or clocks[k] >= address + size):
                    return
                entry, outputs = slice_block(wa, address, counter)
                if not outputs:
                    return
                m = self.m
                ebp = uc.reg_read(m.x86.UC_X86_REG_EBP)
                values = {off: _i32(m.r32((ebp + off) & 0xffffffff)) for off in entry}
                for output in outputs:
                    ops = resolve_clock(wa, output[2], values)
                    if ops is not None:
                        _site_sink.add(('clock', ops))
            self.m.uc.hook_add(UC_HOOK_BLOCK, block, begin=min(clocks[0], frames[0]), end=max(clocks[-1], frames[-1]))
            import struct
            def returned(uc, address, size, context):
                raw = self.m.read(v.MODEL, 0xd0)
                _EXITS.append((hex(address), (struct.unpack_from('<3I', raw, 0x54), struct.unpack_from('<i', raw, 0x40)[0],
                                              struct.unpack_from('<3I', raw, 0x44), raw[0xca])))
            for address in helper_returns(wa):
                self.m.uc.hook_add(UC_HOOK_CODE, returned, begin=address, end=address)
            def rand(m):
                if not _RAND['on']:
                    return 0
                value = _RAND['seq'].pop(0) if _RAND['seq'] else 0
                site = hex(m.r32(m.uc.reg_read(m.x86.UC_X86_REG_ESP)))
                tag = m.backtrace()[1]
                if site == '0x11ff68d' and _SAMPLE_TYPE[0] in COUNTER_RANGE_TYPES:
                    trace = m.backtrace()
                    k = 2 if trace[1] == '0x185cae2' else 1
                    site, tag = trace[k], trace[k + 1]
                if _SAMPLE_TYPE[0] in PRE_FX_TYPES and (PRE_DRAW_RAND[0] <= int(site, 16) < PRE_DRAW_RAND[1] or
                        (_SAMPLE_TYPE[0] in COUNTER_RANGE_TYPES and 0x00d01fc6 <= int(site, 16) < 0x00d02200 and
                         PRE_DRAW_RAND[0] <= int(tag, 16) < PRE_DRAW_RAND[1])):
                    return value   # part 18: RenderObjDraw's own case draws it for the pre-draw program
                _RAND['calls'].append((tag, site, value))
                if site not in _RAND['order']:
                    _RAND['order'].append(site)
                if _site_sink is not None:
                    _site_sink.add(('rand', site))
                return value
            self.m.stub(RAND, rand, 0)
            def named(m):
                address = m.arg(0)
                name = m.read(address if m.r32(address+20)<16 else m.r32(address), m.r32(address+16)).decode('ascii')
                index = NAMED_NAMES.index(name)
                if _site_sink is not None:
                    _site_sink.add(('named', index))
                return _NAMED_VALUES[index] & 0xffffffff
            self.m.stub(0x012bd4a6, named, 4)
    global _site_sink
    _site_sink = sites
    _SAMPLE_TYPE[0] = t
    if _sample_state is None or _sample_state[0] is not wa:
        from item_body_machine import ResetWorld
        _sample_state = (wa, ResetWorld(wa, W), tags)
    else:
        tags = _sample_state[2]
        tags.clear()
    factory = _sample_state[1]
    _EXITS.clear()
    _RAND['calls'].clear()
    if _RAND['on']:
        draw = random.Random(seed * 131 + lv * 7 + quality * 3 + opt + 2 * ext + 11 * (record[1] & 0xff))
        _RAND['seq'][:] = [draw.randrange(32768) for _ in range(64)]
    draw = random.Random(seed * 17 + lv * 7 + quality * 3 + opt + ext)
    _NAMED_VALUES[:] = [draw.choice((0, 1, 3, 5)) for _ in NAMED_NAMES]
    case = v.random_case_any(random.Random(seed), t)
    if t in NAMED_TYPES:
        case['named_meshes'] = tuple(_NAMED_VALUES)
    case.update(item_level=lv << 3, quality=quality, option1=opt, ext=ext, record=record, a10=0xffffffff, a11=0xffffffff, render_type=(2, 0x102, 0x40042)[seed % 3])
    if time_word is not None:
        case['time'] = time_word
    case['object_hidden'] = (-1, 0, 2)[(seed // 3) % 3]
    if t in FRAME_TYPES or t in OTHER_TYPES:
        # RENDER-ITEMS-002U: the rendered-frame counter varies in these types' probes (others keep the zero page).
        draw = random.Random(seed * 7919 + lv * 104729 + quality * 31 + opt * 3 + ext * 5 + (record[1] & 0xff))
        case['frame'] = draw.choice((0, 1, 2, 3, 15, 59, 60, 61, 0x7fffffff, 0x80000000, 0xffffffff,
                                     draw.randrange(1000), draw.randrange(1 << 32)))
    r, st, other = _original(wa, case, factory, tags)
    generic_case = dict(case)
    if t in (0x0eee, 0x18fe, 0x1cfe):
        f = lambda x: v.u2f(v.f2u(x))
        wave = f(math.sin(f(v.u2f(case['time'])*f(0.001))))
        mul, add = (0.6, 0.4) if t == 0x0eee else (0.4, 0.6)
        generic_case['blend_light'] = v.f2u(f(f(wave*f(mul)) + f(add)))
    if t in PLAIN_TYPES or t in NO_GLOW_TYPES:
        generic_case['item_level'] = 0
    if t in NO_GLOW_TYPES and generic_case['record'] is not None:
        a, b, kind = generic_case['record']
        generic_case['record'] = (a, 0 if b in (0x26, 0x5b) else b, kind)
    (_, generic) = v.c_stream(lib, generic_case, True)
    groups = []
    for (d, tag) in zip(st, tags):
        if not groups or tag != groups[-1][0]:
            groups.append((tag, []))
        groups[-1][1].append(d)
    if t in OMITTED_BASE_TYPES:
        groups.insert(0, ('empty', []))
    if len(groups) == 3 and len(generic) == 5:
        groups[1:1] = [('empty', []), ('empty', [])]
    # Some armour branches return without the generic ancient helper. Keep an
    # empty recipe for that phase rather than inventing an extra draw.
    if ext and len(groups) + 1 == len(generic) and generic[-1][1][0] & 0x800:
        groups.append(('omitted-ancient', []))
    if t == 0x0eee and other == [('gl', 'glPushMatrix', []), ('gl', 'glPopMatrix', [])]:
        other = []
    if t in OWNER_FX_TYPES or t in PRE_FX_TYPES or t in POST_FX_TYPES:
        other = [c for c in other if c[0] != 'effect']
    if not r['ok'] or other or len(groups) != len(generic):
        return None
    if carry == 'exit':
        # Each helper starts from the model fields the previous helper call left
        # (its return site in RenderObjDraw); they join the group as an EXIT record.
        queue, last = list(_EXITS), []
        for index, (tag, bs) in enumerate(groups):
            if tag in ('empty', 'omitted-ancient'):
                last.append(None)
                continue
            k = next((i for i, (site, _) in enumerate(queue) if site == tag), None)
            if k is None and index == len(groups) - 1:
                # The excellent tail draws outside the three helpers; nothing follows it.
                last.append(None)
                continue
            if k is None:
                return None
            last.append(exit_record(queue[k][1]))
            del queue[:k + 1]
            bs.append(last[-1])
        (_, generic) = v.c_stream(lib, generic_case, True, carry=last)
        if len(generic) != len(groups):
            return None
    elif carry:
        # Inputs as the carry executor sees them: each helper starts from the
        # model fields of the previous helper's last client draw.
        last = [next((b for b in reversed(bs) if b[0] != 'COLOR'), None) for _, bs in groups]
        (_, generic) = v.c_stream(lib, generic_case, True, carry=last)
        if len(generic) != len(groups):
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
    calls = {}
    if _RAND['calls']:
        group_tags = [tag for tag, _ in groups]
        for tag, site, value in _RAND['calls']:
            if tag not in group_tags or (tag, site) in calls:
                return None   # random outside a helper group, or one site drawn twice
            calls[(tag, site)] = value
    def program_input(program, tag, row):
        if program[0] == 8:
            return _NAMED_VALUES[program[1]] & 0xffffffff
        if program[0] == 7:
            a, b = row[program[1]], row[program[2][0][1]]
            return RAND_ABSENT if RAND_ABSENT in (a, b) else v.f2u(f(v.u2f(a) * v.u2f(b)))
        if program[0] == 6:
            # Part 16: input a (any earlier input or program) then binary32 operations.
            value = row[program[1]]
            return RAND_ABSENT if value == RAND_ABSENT else derived_value(program, value)
        if program[0] == 5:
            value = program_input(params[program[1]], tag, row)
            return RAND_ABSENT if value == RAND_ABSENT else v.f2u(f(v.u2f(value) * v.u2f(program[2][0][1])))
        if program[0] != 4:
            return scalar_value(program, time, case.get('frame', 0))
        value = calls.get((tag, program[3]))
        return RAND_ABSENT if value is None else random_value(program, value)

    def inputs(a, tag):
        row = (flat(a) + [case['object_alpha']] +
               [v.f2u(f(v.u2f(word) * pulse)) for word in flat(a)[8:11]] + [v.f2u(blend)] + [v.f2u(x) for x in body_scalars(time)] + [case['object_hidden'] & 0xffffffff])
        for program in params:
            row.append(program_input(program, tag, row))
        return row
    return [(inputs(a, tag),
             [(b[0], flat(b)) for b in bs], frozenset(site for (g, site) in calls if g == tag))
            for (a, (tag, bs)) in zip(generic, groups)]

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
             NEXT_TYPES + CLOCK_TYPES + CLUSTER_TYPES + WING_TYPES + VISIBLE_TYPES + SCALAR_TYPES +
             CHAIN_TYPES + LEVEL_TYPES + COLOUR_TYPES + CARRY_TYPES + QUALITY_TYPES + PRODUCT_TYPES + DERIVED_TYPES +
             OWNER_FX_TYPES + PRE_FX_TYPES + POST_FX_TYPES + [0x1588] + list(NAMED_TYPES) + NO_GLOW_TYPES + HELPER_TYPES + OTHER_TYPES)


def fit(wa, lib, t, scalars=False, carry=False, extended=False):
    """Probe one type; return (phase rules, scalar programs), or None if no recipe fits.

    With scalars, a type that does not fit the shared inputs is probed again with
    the parsed per-type scalar sites appended as further inputs."""
    sites = set()
    _RAND['on'], _RAND['order'][:] = extended, []
    try:
        rules = _fit(wa, lib, t, (), sites, carry, extended)
        drawn = list(_RAND['order'])
        if drawn:
            rules = None   # random consumption must be modelled
        if rules is not None or not scalars:
            return None if rules is None else (rules, ())
        programs = []
        # Helper programs keep their part-11 order; clock chains follow them; body
        # random programs come last in first-call order.
        ordered = (sorted(site for site in sites if site[0] not in ('clock', 'rand', 'named')) + sorted(site for site in sites if site[0] == 'named') +
                   sorted(site for site in sites if site[0] == 'clock'))
        for helper, ret in ordered:
            program = (8, ret, ()) if helper == 'named' else (3, 0, ret) if helper == 'clock' else parse_scalar(wa, helper, ret)
            if program is not None and program not in programs:
                programs.append(program)
        for site in drawn:
            program = parse_random(wa, int(site, 16))
            if program is None:
                return None
            programs.append(program + (site, 0))
            if t in COUNTER_RANGE_TYPES:
                programs.extend(range_colour_programs(wa, int(site, 16), 35 + len(programs) - 1))
            scale = parse_scale(wa, int(site, 16)) if t in PRODUCT_TYPES else None
            ref = len(programs) - 1
            for word in scale or ():
                # Kind 5: the value of the kind-4 program at index a times one binary32 light constant.
                programs.append((5, ref, ((1, word),)))
        programs.extend(counter_colour_seeds(wa, t, programs))
        if not programs and t not in DERIVED_TYPES and t not in OTHER_TYPES:
            return None
        rules = _fit(wa, lib, t, tuple(programs), None, carry, extended)
        # Part 16: words one binary32 operation away from an input become kind-6 programs.
        for _ in range(6 if t in COUNTER_RANGE_TYPES else 3 if t in DERIVED_TYPES else 0):
            if rules is not None:
                break
            width = 35 + len(programs)
            extra = [p for p in derive(wa, _PHASES, width, products=t in COUNTER_RANGE_TYPES) if p not in programs]
            if not extra:
                break
            programs.extend(extra)
            rules = _fit(wa, lib, t, tuple(programs), None, carry, extended)
        if rules is None or _RAND['order'] != drawn:
            return None
        masks = dict(_RAND['masks'])
    finally:
        _RAND['on'] = False
    programs = [p[:4] + (masks.get(p[3], 0),) if p[0] == 4 else p for p in programs]
    if any(p[0] == 4 and not p[4] for p in programs):
        return None
    # Keep only referenced programs, renumbered in first-use order; every body
    # random program stays, because each one consumes a rand result.
    used = {value - 35 for rule in rules for _, cells in rule for op, value in cells if op == 'in' and value >= 35} | \
        {k for k, p in enumerate(programs) if p[0] == 4}
    while True:   # a kept kind-6 program keeps the program it reads
        more = {a - 35 for k in used for a in
                ([programs[k][1], programs[k][2][0][1]] if programs[k][0] == 7 else
                 [programs[k][1]] if programs[k][0] == 6 else []) if a >= 35} - used
        if not more:
            break
        used |= more
    used = sorted(used)
    remap = {old: 35 + new for new, old in enumerate(used)}
    rules = [[(entry, [(op, remap.get(value - 35, value) if op == 'in' and value >= 35 else value) for op, value in cells])
              for entry, cells in rule] for rule in rules]
    kept = [programs[k] for k in used]
    kept = [(5, remap[p[1]] - 35, p[2]) if p[0] == 5 else
            (7, remap.get(p[1] - 35, p[1]), ((1, remap.get(p[2][0][1] - 35, p[2][0][1])),)) if p[0] == 7 else
            (6, remap[p[1] - 35] if p[1] >= 35 else p[1], p[2]) if p[0] == 6 else p for p in kept]
    return rules, tuple(kept)


_PHASES = []   # the phases of the last _fit call (part 16 derive)


def _fit(wa, lib, t, params, sites, carry=False, extended=False):
    # A failed probe must not feed the previous type or program width into derive().
    _PHASES.clear()
    levels = range(16) if t >= 0x3700 else (0, 7, 13)
    ss = [sample(wa, lib, t, lv, seed, params=params, sites=sites, carry=carry) for lv in levels
          for seed in PROBE_SEEDS]
    if any(s is None for s in ss) and sites is None:
        return None
    phases = [[] for _ in range(8)]
    for index, stream in enumerate(ss):
        if stream is None:
            continue
        phase = 5 if index % 3 == 0 else 0
        if t in LEVEL_SPLIT and index // len(PROBE_SEEDS) == 2:
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
        extra = [sample(wa, lib, t, 0, seed, opt, ext, params=params, sites=sites, carry=carry)
                 for seed in PROBE_SEEDS]
        if any(s is None for s in extra):
            ss.append(None)
            if sites is None:
                return None
            continue
        phases[phase] = [s[-1] for s in extra]
    if extended and not supplement(wa, lib, t, params, sites, carry, ss, phases):
        return None
    if any(s is None for s in ss):
        return None
    # Phases whose helper call draws each body-random site.
    _RAND['masks'] = {}
    for phase, pairs in enumerate(phases):
        for pair in pairs:
            for site in pair[2]:
                _RAND['masks'][site] = _RAND['masks'].get(site, 0) | 1 << phase
    for phase, pairs in enumerate(phases):
        for pair in pairs:
            if any(_RAND['masks'][site] >> phase & 1 and site not in pair[2] for site in _RAND['masks']):
                return None   # a phase draws a site in some probes only
    _PHASES[:] = phases
    rules = [infer(pairs) if pairs else [] for pairs in phases]
    if any(rule is None for rule in rules):
        return None
    if t in ATLAS_TYPES:
        # These ancient mesh branches retain the preceding body light.
        rules[4] = [(entry, [(op, value-4 if 8 <= field <= 10 and op == 'in' and 12 <= value <= 14 else value)
                             for field,(op,value) in enumerate(cells)]) for entry,cells in rules[4]]
    return rules


def supplement(wa, lib, t, params, sites, carry, ss, phases):
    """Part 14: further probes for QUALITY_TYPES. Records of kind B 0x26/0x5b force glow
    level 9, so they reach helper phases the record-free probes skip (wings map levels
    0/7/13 to 0). Qualities 0-2 cap the glow level, and the further clocks separate
    binary32 programs from the shared binary64 pulse. Later clock bodies also keep negative-zero probes:
    a saved product and that product plus positive zero must remain distinct. False when a probe is unusable."""
    probes = [(seed, None) for seed in SUPPLEMENT_SEEDS]
    if t in LATER_READ_PROGRAM_TYPES or t in OTHER_TYPES:
        # Both base phases, in addition to every existing probe. The actual xorps/addss
        # chain is already parsed; these inputs prevent fitting its pre-add intermediate.
        probes += [(seed, 0x80000000) for seed in SUPPLEMENT_SEEDS[:2]]
    for record in SUPPLEMENT_RECORDS:
        for quality in SUPPLEMENT_QUALITIES:
            for lv in (0, 7, 13):
                for seed, time_word in probes:
                    stream = sample(wa, lib, t, lv, seed, params=params, sites=sites, carry=carry,
                                    quality=quality, record=record, time_word=time_word)
                    if stream is None:
                        ss.append(None)
                        if sites is None:
                            return False
                        continue
                    phase = 5 if seed % 3 == 2 else 0
                    if t in NAMED_TYPES and lv >= 9 and quality > 1:
                        phase = 7 if phase == 5 else 6
                    phases[phase].append(stream[0])
                    for pair in stream[1:]:
                        flags = pair[0][0] & ~0x100
                        if flags not in (0x44, 0x48, 0x240, 0x1040):
                            raise ValueError(f'unclassified helper flags {flags:#x}')
                        phases[1 if flags in (0x44, 0x48) else 2].append(pair)
            if quality == 0:
                continue  # no excellent or ancient pass at quality 0
            for opt, ext, phase, flags in ((1, 0, 3, 0x42), (0, 1, 4, 0x840)):
                if ext and t in DIM_TYPES:
                    continue
                for seed, time_word in probes:
                    stream = sample(wa, lib, t, 0, seed, opt, ext, params=params, sites=sites, carry=carry,
                                    quality=quality, record=record, time_word=time_word)
                    if stream is None:
                        ss.append(None)
                        if sites is None:
                            return False
                        continue
                    if stream[-1][0][0] & ~0x100 == flags:
                        phases[phase].append(stream[-1])
    return True


def extract():
    wa = tuple((pin.read() for pin in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE)))
    lib = C.CDLL(str(v.LIBRARY))
    types = {}
    for t in ALL_TYPES:
        fitted = fit(wa, lib, t, scalars=True,
                     carry='exit' if t in EXIT_TYPES else t in CARRY_TYPES or t in DERIVED_CARRY or t in PRE_CARRY,
                     extended=t in QUALITY_TYPES or t in PRODUCT_TYPES or t in PRE_EXTENDED or t in NAMED_TYPES or t in NO_GLOW_TYPES or t in HELPER_TYPES or t in OTHER_TYPES)
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
        if len(scalars) > 24:   # RENDER-ITEMS-002V: 0x1588 needs 22, including its intermediate colour products.
            raise ValueError('more than twenty-four scalar programs')
        rows.append((t, indices, len(programs), len(scalars)))
        programs.extend(scalars)
    lines = ['/* Generated by scripts/gen_item_bodies.py. Rendering rules only.',
             ' * source=0 selects value; source=1..16 copies the generic draw word;',
             ' * source=17 copies OBJECT alpha. source=18..20 copies pulsed body light; source=21 copies armour blend pulse. source=22..34 selects clock scalars; source=35 copies OBJECT hidden mesh;',
             ' * source=36.. selects the type\'s own scalar program (kind 1 = wave 0x0185bdc4(a,0), 2 = sin(time*a), then mul/add/sub/div, binary32 or op|8 binary64 with one final rounding;',
             ' * kind 3 = clock chain of op/k pairs, see gen_item_bodies.C_TIME_F..C_U2D (30..33: the rendered-frame counter);',
             ' * clock ops 34/35/36 are binary32 sin, conditional abs and CRT fabs (distinct signed-zero rules);',
             ' * kind 9 = wave(a, k[0] degrees), then ops 1..; scalar op 5 is k-value, 6 is a lower clamp;',
             ' * kind 8 = raw 0x012bd4a6 result for mu_rc_body_names[a], including -1;',
             ' * kind 4 = (float)(rand() % a) then binary32',
             ' * mul/add/sub/div, drawn once in each phase of its phases mask; kind 5 = the type\'s program a (kind 4)',
             ' * times the binary32 k[0], one channel of a scaled constant body light; kind 6 = input a (absolute index)',
             ' * then binary32 mul/add/sub/div; kind 7 = input a times input k[0], one binary32 multiply).',
             ' * Kind-4 ops 5/6/7: integer offset before conversion, lower clamp, upper clamp (0x011ff622).',
             ' * Entry 4 (EXIT) writes words 8..15 to the model',
             ' * fields and draws nothing. See client-render-items.md. */',
             '#define MU_RC_BODY_SCALARS 24',
             'typedef struct { uint8_t count; struct { int32_t entry; uint8_t source[16]; uint32_t value[16]; } draw[16]; } mu_rc_body_recipe;',
             'static const mu_rc_body_recipe mu_rc_body_recipes[] = {']
    for rule in recipes:
        lines.append('    {%d, {' % len(rule))
        for entry, cells in rule:
            sources = ', '.join(str(v + 1 if op == 'in' else 0) for op, v in cells)
            values = ', '.join('0' if op == 'in' or not (v & 0xffffffff) else '0x%xu' % (v & 0xffffffff) for op, v in cells)
            lines.append('        {%d, {%s}, {%s}},' % ({'BODY': 1, 'MESH': 2, 'COLOR': 3, 'EXIT': 4}[entry], sources, values))
        lines.append('    }},')
    lines += ['};', 'typedef struct { uint8_t kind, count; uint32_t a; uint8_t op[%d]; uint64_t k[%d]; uint8_t phases; } mu_rc_body_scalar;' % (CLOCK_OPS, CLOCK_OPS),
              'static const mu_rc_body_scalar mu_rc_body_scalars[] = {']
    for program in programs:
        kind, a, ops = program[:3]
        # Kind 4 (body random) also carries the phases whose helper call draws it. RENDER-ITEMS-002U: only the used
        # op/k slots are written (C zero-fills the rest of the CLOCK_OPS arrays), which keeps the table under the
        # audit's size limit.
        used = list(ops) or [(0, 0)]
        lines.append('    {%d, %d, 0x%08xu, {%s}, {%s}, 0x%02x},' % (
            kind, sum(1 for op, _ in ops if op), a, ', '.join(str(op) for op, _ in used),
            ', '.join('0x%xull' % k for _, k in used), program[4] if kind == 4 else 0))
    if not programs:
        lines.append('    {0, 0, 0, {0}, {0}, 0},')
    lines += ['};', 'static const struct { int32_t type; uint16_t recipe[8]; uint8_t level_split, retain_ancient; uint8_t dim, plain, pulse, blend_pulse; uint16_t scalar_mask; uint8_t carry; uint16_t scalar_first; uint8_t scalar_count; } mu_rc_body_types[] = {']
    for t, indices, first, count in rows:
        rules = types[t][0]
        lines.append('    {0x%04x, {%s}, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d},' %
                     (t, ', '.join(map(str, indices)), t in LEVEL_SPLIT, t in ATLAS_TYPES, t in DIM_TYPES, t in PLAIN_TYPES or t in NO_GLOW_TYPES, t in PULSE_TYPES,
                      any(op == 'in' and value == 20 for rule in rules for _, cells in rule for op, value in cells),
                      sum(1 << k for k in range(13) if any(op == 'in' and value == 21+k for rule in rules for _, cells in rule for op,value in cells)),
                      t in CARRY_TYPES or t in DERIVED_CARRY or t in PRE_CARRY, first, count))
    return '\n'.join(lines + ['};', 'static const char *const mu_rc_body_names[] = {'] +
                     ['    ' + json.dumps(name) + ',' for name in NAMED_NAMES] + ['};', ''])


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
