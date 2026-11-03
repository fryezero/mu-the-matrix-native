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
        # Only the zero phase argument (xorps) is in the supported domain.
        if _text(wa, call - 22, 3) != bytes.fromhex('0f57c0') or _text(wa, call - 23, 1) != b'\x51':
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
    if reload[:4] != (bytes.fromhex('f20f1085') if double else bytes.fromhex('f30f1085')) or fstp[2:] != reload[4:]:
        # The stored binary32 local itself, as at 0x01711064.
        return None if double else (kind, a, ())
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
    return kind, a, tuple(ops)


def wave_helper(a, time):
    """0x0185bdc4(a, 0): signed cosine wave, binary32 steps. The zero phase
    term adds a signed zero to time, which cannot change the truncated tick."""
    import math
    f = lambda x: v.u2f(v.f2u(x))
    tick = int(time) if -2147483648 <= time < 2147483648 else -2147483648
    period = int(f(f(6283.1855) / a))
    rem = int(math.fmod(tick, period))
    y = f(f(rem * f(0.001)) * a)
    w = f(math.cos(y))
    if f(3.1415927) > y:
        w = -w
    return f(f(w + f(1.0)) * f(0.5))


def scalar_value(program, time):
    import math
    f = lambda x: v.u2f(v.f2u(x))
    kind, a, ops = program
    if kind == 3:
        return clock_value(ops, time)
    if kind == 1:
        value = wave_helper(v.u2f(a), time)
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
CLOCK_OPS = 9
_md = None
_clock_sites = None
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


def slice_block(wa, block):
    """Static walk from one block start. Returns (entry locals read, outputs) where
    each output is a chain whose integer local reads are ('local', offset)."""
    if block in _slices:
        return _slices[block]
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
        return x if x and x[0] in ('k', 'e') else None

    def lin(x, mul, add):
        if x[0] == 'k':
            return ('k', _i32(x[1] * mul + add))
        return ('e', x[1], x[2] * mul, x[3] * mul + add)

    at, steps, cdq = block, 0, None
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
        if name.startswith('j') or name in ('call', 'ret', 'retn', 'int3', 'leave'):
            break
        if name == 'mov' and dname in gpr:
            result = value(ins, src, 4)
            if result == 'clock':
                result = None
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
                local[r[1]] = x if name == 'movss' else None
            elif r[0] == 'abs' and r[1] == CLOCK:
                break
            handled = 'stored'
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
            if x == 'clock' and name == 'cvttss2si':
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
            if x and x[0] == 'c' and x[1] == kind and const(y):
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
            regs['edx'] = ('cdq', x) if x and x[0] == 'c' and x[1] == 'i' else None
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
            if (mask & 0x80000000 and low and low & (low + 1) == 0 and x and x[0] == 'c' and x[1] == 'i' and
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
                result = chain(x[1], 'i', (C_I_DIV, ('i', ('k', x[2]))))
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
    _slices[block] = (tuple(sorted(entry)), tuple(dict.fromkeys(outputs)))
    return _slices[block]


def resolve_clock(wa, program, values):
    """Substitute entry-local values; ('i', n) operands become 32-bit words."""
    ops = []
    for op, k in program:
        if isinstance(k, tuple) and k[0] == 'w':
            ops.append((op, k[1]))
        elif isinstance(k, tuple):
            n = k[1]
            if n[0] == 'k':
                word = n[1]
            else:
                base = values[n[1]]
                if not _local_stored(wa, n[1], base):
                    return None
                word = _i32(base * n[2] + n[3])
            if k[0] == 'i' and op in (C_F_MUL, C_F_DIV, C_F_ADD, C_F_SUB, C_F_RSUB, C_F_RDIV):
                word = v.f2u(_f32(float(word)))
            elif k[0] == 'i' and op in (C_D_MUL, C_D_DIV, C_D_ADD, C_D_SUB, C_D_RSUB, C_D_RDIV):
                word = _d64(float(word))
            if op in (C_I_MOD, C_I_DIV) and word in (0, -1):
                return None
            ops.append((op, word & 0xffffffffffffffff))
        else:
            ops.append((op, 0))
    return tuple(ops) if len(ops) <= CLOCK_OPS else None


def clock_value(ops, time):
    """Reference evaluation of a clock chain; returns the binary32 word."""
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
COLOUR_SLOTS = {0x1a7c76c: (1, 3), 0x1a7c770: (2, 1), 0x1a7c754: (3, 4)}


def record_colours(world, tags=None):
    m = world.m
    for slot, (kind, count) in COLOUR_SLOTS.items():
        def colour(m, kind=kind):
            if kind == 2:
                rgb, alpha = tuple(m.r32(m.arg(0) + 4 * k) for k in range(3)), v.f2u(1.0)
            else:
                rgb, alpha = tuple(m.arg(k) for k in range(3)), m.arg(3) if kind == 3 else v.f2u(1.0)
            world.calls.append(('COLOR', v.colour_record(kind, alpha, rgb)))
            if tags is not None:
                tags.append(m.backtrace()[1])
            return 0
        m.stub(m.r32(slot), colour, 4 * count)

_sample_state = None
_site_sink = None


def sample(wa, lib, t, lv, seed, opt=0, ext=0, params=(), sites=None, carry=False):
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
            def block(uc, address, size, context):
                if _site_sink is None:
                    return
                k = bisect.bisect_left(clocks, address)
                if k == len(clocks) or clocks[k] >= address + size:
                    return
                entry, outputs = slice_block(wa, address)
                if not outputs:
                    return
                m = self.m
                ebp = uc.reg_read(m.x86.UC_X86_REG_EBP)
                values = {off: _i32(m.r32((ebp + off) & 0xffffffff)) for off in entry}
                for output in outputs:
                    ops = resolve_clock(wa, output[2], values)
                    if ops is not None:
                        _site_sink.add(('clock', ops))
            self.m.uc.hook_add(UC_HOOK_BLOCK, block, begin=clocks[0], end=clocks[-1])
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
    if carry:
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
             NEXT_TYPES + CLOCK_TYPES + CLUSTER_TYPES + WING_TYPES + VISIBLE_TYPES + SCALAR_TYPES +
             CHAIN_TYPES + LEVEL_TYPES + COLOUR_TYPES + CARRY_TYPES)


def fit(wa, lib, t, scalars=False, carry=False):
    """Probe one type; return (phase rules, scalar programs), or None if no recipe fits.

    With scalars, a type that does not fit the shared inputs is probed again with
    the parsed per-type scalar sites appended as further inputs."""
    sites = set()
    rules = _fit(wa, lib, t, (), sites, carry)
    if rules is not None or not scalars:
        return None if rules is None else (rules, ())
    programs = []
    # Helper programs keep their part-11 order; clock chains follow them.
    ordered = sorted(site for site in sites if site[0] != 'clock') + sorted(site for site in sites if site[0] == 'clock')
    for helper, ret in ordered:
        program = (3, 0, ret) if helper == 'clock' else parse_scalar(wa, helper, ret)
        if program is not None and program not in programs:
            programs.append(program)
    if not programs:
        return None
    rules = _fit(wa, lib, t, tuple(programs), None, carry)
    if rules is None:
        return None
    # Keep only referenced programs, renumbered in first-use order.
    used = sorted({value - 35 for rule in rules for _, cells in rule for op, value in cells if op == 'in' and value >= 35})
    remap = {old: 35 + new for new, old in enumerate(used)}
    rules = [[(entry, [(op, remap.get(value - 35, value) if op == 'in' and value >= 35 else value) for op, value in cells])
              for entry, cells in rule] for rule in rules]
    return rules, tuple(programs[k] for k in used)


def _fit(wa, lib, t, params, sites, carry=False):
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
        fitted = fit(wa, lib, t, scalars=True, carry=t in CARRY_TYPES)
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
             ' * source=36.. selects the type\'s own scalar program (kind 1 = wave 0x0185bdc4(a,0), 2 = sin(time*a), then mul/add/sub/div, binary32 or op|8 binary64 with one final rounding;',
             ' * kind 3 = clock chain of op/k pairs, see gen_item_bodies.C_TIME_F..C_D_NEG). See client-render-items.md. */',
             '#define MU_RC_BODY_SCALARS 8',
             'typedef struct { uint8_t count; struct { int32_t entry; uint8_t source[16]; uint32_t value[16]; } draw[16]; } mu_rc_body_recipe;',
             'static const mu_rc_body_recipe mu_rc_body_recipes[] = {']
    for rule in recipes:
        lines.append('    {%d, {' % len(rule))
        for entry, cells in rule:
            sources = ', '.join(str(v + 1 if op == 'in' else 0) for op, v in cells)
            values = ', '.join('0' if op == 'in' else '0x%08xu' % (v & 0xffffffff) for op, v in cells)
            lines.append('        {%d, {%s}, {%s}},' % ({'BODY': 1, 'MESH': 2, 'COLOR': 3}[entry], sources, values))
        lines.append('    }},')
    lines += ['};', 'typedef struct { uint8_t kind, count; uint32_t a; uint8_t op[%d]; uint64_t k[%d]; } mu_rc_body_scalar;' % (CLOCK_OPS, CLOCK_OPS),
              'static const mu_rc_body_scalar mu_rc_body_scalars[] = {']
    for kind, a, ops in programs:
        ops = list(ops) + [(0, 0)] * (CLOCK_OPS - len(ops))
        lines.append('    {%d, %d, 0x%08xu, {%s}, {%s}},' % (
            kind, sum(1 for op, _ in ops if op), a, ', '.join(str(op) for op, _ in ops),
            ', '.join('0x%xull' % k for _, k in ops)))
    if not programs:
        lines.append('    {0, 0, 0, {0}, {0}},')
    lines += ['};', 'static const struct { int32_t type; uint16_t recipe[8]; uint8_t level_split, retain_ancient; uint8_t dim, plain, pulse, blend_pulse; uint16_t scalar_mask; uint8_t carry; uint16_t scalar_first; uint8_t scalar_count; } mu_rc_body_types[] = {']
    for t, indices, first, count in rows:
        rules = types[t][0]
        lines.append('    {0x%04x, {%s}, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d},' %
                     (t, ', '.join(map(str, indices)), t in LEVEL_SPLIT, t in ATLAS_TYPES, t in DIM_TYPES, t in PLAIN_TYPES, t in PULSE_TYPES,
                      any(op == 'in' and value == 20 for rule in rules for _, cells in rule for op, value in cells),
                      sum(1 << k for k in range(13) if any(op == 'in' and value == 21+k for rule in rules for _, cells in rule for op,value in cells)),
                      t in CARRY_TYPES, first, count))
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
