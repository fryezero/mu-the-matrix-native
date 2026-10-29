#!/usr/bin/env python3
"""Part 12 clock-chain and level-split bodies versus pinned instructions."""
import argparse
import ctypes as C
import json
from pathlib import Path
import re
import subprocess
import tempfile
import gen_item_bodies as gen
import pins
import validate_item_clusters as clusters
import validate_item_ranked as ranked
import validate_item_wings_next as previous
import validate_renderchar as v

ROOT = Path(__file__).resolve().parents[1]
TYPES = gen.CHAIN_TYPES + gen.LEVEL_TYPES
# Table additions: 0x0ef3 chain row at 0x012cc846, 0x0f0b pulse row at 0x012cbb43.
LINKS = (0x0ef3, 0x0f0b)


def programs():
    """First part-12 type for every distinct clock chain in the table."""
    source = (ROOT/'reconstructed/renderchar/item_bodies.h').read_text()
    table = source[source.index('mu_rc_body_scalars[] = {'):]
    table = table[:table.index('};')]
    entries = re.findall(r'\n    \{(\d), (\d), 0x[0-9a-f]{8}u, \{([^}]*)\}, \{([^}]*)\}\},', table)
    rows = re.findall(r'\n    \{(0x[0-9a-f]{4}), \{[^}]*\}(?:, \d+){7}, (\d+), (\d+)\},', source)
    first = {}
    for t, start, count in rows:
        if int(t, 16) not in TYPES:
            continue
        for k in range(int(start), int(start) + int(count)):
            kind, n, ops, ks = entries[k]
            if kind == '3':
                ops = [int(x) for x in ops.split(', ')][:int(n)]
                ks = [int(x[:-3], 16) for x in ks.split(', ')][:int(n)]
                first.setdefault(tuple(zip(ops, ks)), int(t, 16))
    return first


def clock_cases(wa, lib, first):
    """Divisor edges of every chain, INT_MIN, 2^31 and negative zero."""
    from item_body_machine import ResetWorld
    reset, vectors = ResetWorld(wa), []
    for ops, t in sorted(first.items(), key=lambda item: item[1]):
        edges = {abs(gen._i32(k & 0xffffffff)) for op, k in ops if op in (gen.C_I_MOD, gen.C_I_DIV)} or {1000}
        times = {-2147483648.0, -2147483520.0, -1.0, -0.0, 0.0, 0.5, 2147483520.0, 2147483648.0}
        for n in sorted(edges)[:3]:
            times |= {-n - 1.0, -float(n), -n + 0.5, n - 1.0, n - 0.25, float(n), n + 1.0, 2.0 * n}
        for time in sorted(times, key=lambda x: (x, str(x))):
            for flags in (2, 0x40042):
                case = v.classify_case(t, v.CLASSIFY[0])
                case.update(time=v.f2u(time), render_type=flags, item_level=13 << 3)
                result, expected, other, _ = v.client_stream(wa, case, reset)
                if not result['ok'] or other or v.c_stream(lib, case) != (0, expected):
                    raise AssertionError(('clock', hex(t), time, flags, result, other))
                vectors.append((case, expected))
    return {'cases': len(vectors), 'mismatches': 0, 'programs': len(first)}, vectors


def level_cases(wa, lib):
    """Every level, quality and flag word at the split boundary of the level types."""
    import random
    from item_body_machine import ResetWorld
    reset, vectors = ResetWorld(wa, previous.BodyWorld), []
    for t in gen.LEVEL_TYPES:
        rng = random.Random(0x2002d + t)
        for level in range(16):
            for quality in (0, 1, 2, 3, 4, 5, 9):
                for flags in (2, 0x102, 0x402):
                    case = v.random_case_any(rng, t)
                    case.update(item_level=level << 3, quality=quality, render_type=flags, option1=0, ext=0,
                                record=(0, 0, 0), a10=0xffffffff, a11=0xffffffff)
                    result, expected, other, _ = v.client_stream(wa, case, reset)
                    if not result['ok'] or other or v.c_stream(lib, case) != (0, expected):
                        raise AssertionError(('level', hex(t), level, quality, flags, result, other))
                    vectors.append((case, expected))
    return {'cases': len(vectors), 'mismatches': 0}, vectors


def link_cases(wa, lib):
    """Pinned RenderLinkItem callers with random sequences, clocks and hand variants."""
    import random
    rng, vectors = random.Random(0x2002e), []
    for t in LINKS:
        if not lib.mu_rc_link_supported(t):
            raise AssertionError(('native admission', hex(t)))
        for k in range(100):
            values = [k]*32 if k < 30 else [rng.randrange(32768) for _ in range(32)]
            for variant, time in enumerate((0, 700.25, 123456, -150.5)):
                expected = ranked.original_link(wa, t, values, time, variant)
                if clusters.c_effects(lib, t, values, time) != expected:
                    raise AssertionError(('link', hex(t), k, variant))
                vectors.append((t, values, time, expected))
    return {'cases': len(vectors), 'mismatches': 0}, vectors


def mutations(vectors, links):
    source = (ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    changes = {
        'chain-kind': ('if (p->kind == 3)', 'if (p->kind == 4)'),
        'chain-tick': ('case 3: i = clock_trunc((double)time);', 'case 3: i = clock_trunc((double)time + 1.0);'),
        'chain-indefinite': ('? INT32_MIN : (int32_t)x;', '? INT32_MAX : (int32_t)x;'),
        'chain-remainder': ('case 22: i = i % ki;', 'case 22: i = i % (ki + 1);'),
        'chain-quotient': ('case 23: i = i / ki;', 'case 23: i = (i + 1) / ki;'),
        'chain-convert': ('case 20: f = (float)i;', 'case 20: f = (float)(i + 1);'),
        'chain-multiply': ('case 4: f = f * kf;', 'case 4: f = f * -kf;'),
        'chain-divide': ('case 5: f = f / kf;', 'case 5: f = kf / f;'),
        'chain-negate': ('case 26: f = -f;', 'case 26: break;'),
        'chain-reverse': ('case 8: f = kf - f;', 'case 8: f = f - kf;'),
        'chain-int-negate': ('case 27: i = (int32_t)(0u - (uint32_t)i);', 'case 27: break;'),
        'chain-slot': ('scalar_first + k]', 'scalar_first]'),
        'level-split': ('((s->item->item_level >> 3) & 15) >= 9)', '((s->item->item_level >> 3) & 15) >= 10)'),
        'mesh-index': ('d.mesh = (int32_t)words[0];', 'd.mesh = (int32_t)words[0] + 1;'),
        'object-alpha': ('&s->item->object_alpha, 4', '&base.alpha, 4'),
        'link-flash': ('chain->flash && random(context) % 3 == 0', 'chain->flash && random(context) % 3 == 1'),
        'link-pulse': ('sin2 * 0.35f + 0.65f, sin2, sin1', 'sin2 * 0.35f + 0.65f, sin1, sin1'),
    }
    caught = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, (old, new) in changes.items():
            if source.count(old) != 1:
                raise AssertionError(('mutant anchor', name, source.count(old)))
            path, library = Path(tmp)/(name+'.c'), Path(tmp)/(name+'.dylib')
            path.write_text(source.replace(old, new))
            subprocess.run(['clang', '-shared', '-fPIC', '-O2', '-std=c11', '-ffp-contract=off',
                            '-I', str(ROOT/'reconstructed/renderchar'), str(path),
                            str(ROOT/'reconstructed/record-math/record_math.c'), '-lm', '-o', str(library)], check=True)
            lib = C.CDLL(str(library))
            detected = sum(v.c_stream(lib, case) != (0, expected) for case, expected in vectors)
            detected += sum(clusters.c_effects(lib, t, values, time) != expected for t, values, time, expected in links)
            if not detected:
                raise AssertionError(('surviving mutant', name))
            caught[name] = detected
    return caught


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--screen', action='store_true', help='candidate rejection, not a passing validation')
    args = parser.parse_args()
    subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/renderchar')], check=True)
    wa = tuple(p.read() for p in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE))
    lib = C.CDLL(str(v.LIBRARY))
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': {}}
    report['families']['bodies'], bodies, failures = clusters.body_cases(
        wa, lib, TYPES, args.screen, world_class=previous.BodyWorld)
    if args.screen:
        report.update(rejected=[hex(f[0]) for f in failures])
    else:
        assert not failures
        first = programs()
        report['programs'] = len(first)
        report['families']['clocks'], clocks = clock_cases(wa, lib, first)
        report['families']['levels'], levels = level_cases(wa, lib)
        report['families']['links'], links = link_cases(wa, lib)
        if args.mutations:
            report['mutants'] = mutations(bodies + clocks + levels, links)
        import gen_item_links, gen_item_pulse_links
        for name, text in (('item_bodies.h', gen.generate()), ('item_links.h', gen_item_links.generate()),
                           ('item_pulse_links.h', gen_item_pulse_links.generate())):
            if text != (ROOT/'reconstructed/renderchar'/name).read_text():
                raise AssertionError(('table drift', name))
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
