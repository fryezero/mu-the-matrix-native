#!/usr/bin/env python3
"""Item HiddenMesh inputs and ItemObjectAttribute versus the pinned original instructions."""
import argparse
import ctypes as C
import itertools
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile

import pins
import validate_renderchar as v
import validate_item_quality as quality
from item_body_machine import ResetWorld

ROOT = Path(__file__).resolve().parents[1]
TYPES = [0x0b1d, 0x0b1e, 0x0b1f, 0x0eee, 0x0f00, 0x0f01, 0x0f0e, 0x1305,
         0x151a, 0x151b, 0x151c, 0x230a, 0x2495, 0x252b, 0x252c, 0x2537,
         0x2538, 0x280b, 0x280e, 0x2837, 0x2838, 0x2839, 0x283a]
VISIBILITY_TYPES = [
    0x0afa, 0x0afb, 0x0b06, 0x0b07, 0x0b08, 0x0b0e, 0x0b18, 0x0eef, 0x0ef1, 0x0ef2,
    0x0ef3, 0x0efb, 0x0efe, 0x10f0, 0x10f6, 0x10f7, 0x10f8, 0x190d, 0x190e, 0x190f,
    0x1910, 0x1911, 0x1912, 0x1917, 0x1918, 0x191b, 0x1921, 0x1922, 0x1923, 0x1938,
    0x1939, 0x196d, 0x1af5, 0x1b05, 0x1b0a, 0x1b0d, 0x1b0e, 0x1b0f, 0x1b10, 0x1b11,
    0x1b12, 0x1b17, 0x1b1b, 0x1b38, 0x1cf5, 0x1d05, 0x1d0a, 0x1d0d, 0x1d0e, 0x1d0f,
    0x1d10, 0x1d11, 0x1d12, 0x1d38, 0x1d7a, 0x1ef5, 0x1f0a, 0x1f12, 0x1f78, 0x1f79,
    0x1f7a, 0x1f7b, 0x20f5, 0x2178, 0x2179, 0x217a, 0x217b, 0x2310, 0x2491, 0x2514,
    0x2515, 0x2516, 0x251c, 0x251d, 0x251e, 0x251f, 0x2520, 0x2521, 0x2522, 0x2523,
    0x2524, 0x2525, 0x2526, 0x2527, 0x2549, 0x2553, 0x2554, 0x2555, 0x2556, 0x2557,
    0x2558, 0x2559, 0x255f, 0x2560, 0x2566, 0x2567, 0x271b, 0x271c, 0x271d, 0x271e,
    0x271f, 0x2720, 0x2721, 0x2722, 0x2723, 0x2724, 0x2727, 0x2728, 0x2729, 0x272a,
    0x272e, 0x272f, 0x2730, 0x2731, 0x2732, 0x2733, 0x2734, 0x2735, 0x2736, 0x2737,
    0x2738, 0x2739, 0x2742, 0x2743, 0x2745, 0x2746, 0x2747, 0x2748, 0x2756, 0x2757,
    0x275e, 0x275f, 0x2760, 0x278b, 0x278c, 0x278d, 0x278e, 0x27a3, 0x280c, 0x280d,
    0x2894, 0x28a0, 0x28a1, 0x28f9, 0x28fa, 0x28fb, 0x28fc, 0x28fd, 0x28fe, 0x28ff,
    0x2900, 0x2901, 0x2904, 0x2905, 0x2906, 0x2907, 0x2908, 0x2909, 0x290a,
]
CONTROLS = [0x0ae6, 0x0ae7, 0x0ae8, 0x0ae9, 0x0aff, 0x0b02, 0x131f,
            0x171d, 0x171e, 0x171f, 0x18fe, 0x1cfe, 0x2381]
EXCEPTIONS = {0x0b05: 2, 0x0eed: 2, 0x0f0b: 2, 0x1711: 2, 0x16f6: 2, 0x10f0: 1}


def attributes(wa, lib):
    """Sweep every survey type and the six explicit exceptions in 0x016da00b."""
    import validate_items as vi
    import actor_machine as am
    m = vi.Machine(wa[0], wa[1])
    types = {int(line.split('\t')[0], 16) for line in
             (ROOT/'docs/research/item-body-types.tsv').read_text().splitlines()[1:]}
    pairs = []
    for t in sorted(types | EXCEPTIONS.keys()):
        hc = vi.HostCase(random.Random(t), world_time=123456.0)
        obj = am.undefined_region('object', vi.OBJ, 0x400, 0x47)
        obj.define(vi.OBJ+0x5c, struct.pack('<i', t))
        poison = bytes(am.poison(0x400, 0x47))
        for offset in (0x68, 0x74):
            obj.define(vi.OBJ+offset, poison[offset:offset+4])
        regions = [obj, am.defined_region('time', vi.TIME, struct.pack('<f', 123456.0), writable=False)]
        stubs = hc.stubs()
        stubs[0x01295f18] = lambda mm: 0
        result = m.execute_regions(vi.OBJECT_ATTR, [vi.OBJ], regions, stubs)
        if not vi.vc.ok(result):
            raise AssertionError(('attribute stop', hex(t), result['error'], result['stopped']))
        expected = struct.unpack_from('<i', result['regions']['object'], 0x68)[0]
        if lib.mu_rc_item_hidden_mesh(t) != expected:
            raise AssertionError(('attribute', hex(t), expected))
        pairs.append((t, expected))
    return {'cases': len(pairs), 'mismatches': 0,
            'exceptions': {hex(t): h for t, h in pairs if h != -1}}, pairs


def bodies(wa, lib, types, cases):
    """Compare complete draw streams. Older recipes use the inherited zero-rand service;
    random consumption for those recipes is outside this HiddenMesh comparison.
    Product controls still compare their modelled random consumption.
    """
    reset = ResetWorld(wa, quality.RandomWorld)
    vectors = []
    for t in types:
        rng = random.Random(0x68 + t)
        for k, state in itertools.islice(quality.state_cases(t), cases):
            seq = [0]*48 if t in TYPES + VISIBILITY_TYPES else quality.sequence_for(rng)
            for hidden in ((0, -1, EXCEPTIONS[t]) if t in EXCEPTIONS else (0, -1)):
                case = dict(state, object_hidden=hidden)
                def factory(*args):
                    w = reset(*args)
                    w.sequence, w.drawn = seq, 0
                    return w
                result, expected, other, _ = v.client_stream(wa, case, factory)
                # The 0x0eee body brackets its draws in a matrix push/pop, as in gen_item_bodies.
                allowed = [('gl', 'glPushMatrix', []), ('gl', 'glPopMatrix', [])] if t == 0x0eee else []
                actual = quality.run_c(lib, case, seq)
                if (not result['ok'] or other != allowed or actual[:2] != (0, expected) or
                        (t in CONTROLS and actual[2] != reset.world.drawn)):
                    raise AssertionError(('body', hex(t), k, hidden, result, other, expected, actual))
                vectors.append((case, seq, expected))
    return {'cases': len(vectors), 'mismatches': 0, 'types': len(types)}, vectors


def rank5_controls(wa, lib):
    rank = v.Rank5(wa, lib, 0x68)
    count = 0
    for t in sorted(rank.types):
        for config in v.CLASSIFY:
            for hidden in (0, -1):
                case = dict(v.classify_case(t, config), object_hidden=hidden)
                status, actual, result, expected, _ = rank.compare(case)
                if status or not result['ok'] or actual != expected:
                    raise AssertionError(('rank5', hex(t), hidden, status, result))
                count += 1
    return {'cases': count, 'mismatches': 0, 'types': len(rank.types)}


def mutations(vectors, pairs):
    source = (ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    changes = {
        'hidden-input-zero': ('input[34] = (uint32_t)s->item->object_hidden;', 'input[34] = 0;'),
        'hidden-minus-one-refused': ('*count = 0;\n    if (mu_rc_item_special(it->type))',
                                     '*count = 0;\n    if (it->object_hidden == -1) return MU_RC_UNSUPPORTED;\n    if (mu_rc_item_special(it->type))'),
        'attribute-default-zero': ('default: return -1;\n    }\n}\n\nint mu_rc_item_special',
                                   'default: return 0;\n    }\n}\n\nint mu_rc_item_special'),
        'attribute-exception-zero': ('case 0x10f0: return 1;', 'case 0x10f0: return 0;'),
        'body-hidden-zero': ('d.hidden = (int32_t)words[6];', 'd.hidden = 0;'),
        'mesh-texture-zero': ('d.texture = (int32_t)words[7];', 'd.texture = 0;'),
    }
    caught = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, (old, new) in changes.items():
            assert source.count(old) == 1, name
            path, so = Path(tmp)/(name+'.c'), Path(tmp)/(name+'.dylib')
            path.write_text(source.replace(old, new))
            subprocess.run(['clang', '-shared', '-fPIC', '-O2', '-std=c11', '-ffp-contract=off',
                            '-I', str(ROOT/'reconstructed/renderchar'), str(path),
                            str(ROOT/'reconstructed/record-math/record_math.c'), '-lm', '-o', str(so)], check=True)
            mutant = C.CDLL(str(so))
            n = sum(mutant.mu_rc_item_hidden_mesh(t) != h for t, h in pairs)
            n += sum(quality.run_c(mutant, c, seq)[:2] != (0, expected) for c, seq, expected in vectors)
            if not n:
                raise AssertionError(('surviving mutant', name))
            caught[name] = n
    return caught


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=int, default=292, help='states per type, each at hidden 0 and -1')
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/renderchar')], check=True)
    wa = tuple(p.read() for p in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE))
    lib = C.CDLL(str(v.LIBRARY))
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': {}}
    report['families']['attributes'], pairs = attributes(wa, lib)
    report['families']['affected'], affected = bodies(wa, lib, TYPES, args.cases)
    report['families']['visibility'], visibility = bodies(wa, lib, VISIBILITY_TYPES, args.cases)
    report['families']['controls'], controls = bodies(wa, lib, CONTROLS, args.cases)
    report['families']['rank5'] = rank5_controls(wa, lib)
    if args.mutations:
        report['mutants'] = mutations(affected + visibility + controls, pairs)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
