#!/usr/bin/env python3
"""RENDER-ITEMS-002W: rank-5 part draws with declared texture-name lookup results.

Runs complete RenderObjDraw, with 0x012bd4a6 supplied as an independent mesh-index input.
The ordinary classification world's absent texture table is not replaced or reclassified.
It uses the existing recording draw/effect boundaries and compares request words and model writes.
Pose construction, mesh geometry and pixels are outside this body comparison.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile

import pins
import validate_renderchar as v
import validate_item_quality as quality
import original_cache
from item_body_machine import ResetWorld

ROOT = Path(__file__).resolve().parents[1]
TYPES = v.NAMED_BODY_TYPES
NAMES = v.NAMED_MESH_NAMES
VALUES = ((-1, -1, -1), (0, 0, 0), (5, 3, 1), (3, -1, 5),
          (-1, 5, 3), (1, 5, -1), (-1, 0, -1), (5, -1, 0))


def sequence_for(case, context=True):
    if not context:
        return [0] * 48
    if '_random' in case:
        return list(case['_random'])
    seed = case['type'] ^ case['time'] ^ case['item_level'] ^ sum(case['named_meshes'])
    return quality.sequence_for(random.Random(seed))


def c_stream(lib, case, context=True):
    used = []
    actual_case = dict(case)
    if not context:
        actual_case.pop('named_meshes', None)
        status, stream = v.c_stream(lib, actual_case)
    else:
        sequence = sequence_for(case)
        def draw():
            used.append(sequence[len(used)])
            return used[-1]
        status, stream = v.c_stream(lib, actual_case, random=draw)
    return status, stream, len(used)


def compare(wa, lib, reset, case, context=True):
    def factory(*args):
        world = reset(*args)
        world.sequence, world.drawn = sequence_for(case, context), 0
        return world

    def original():
        result, expected, other, _ = v.client_stream(wa, case, factory)
        return result, expected, other, reset.world.drawn
    result, expected, other, consumed = original_cache.named('validate_item_named', Path(__file__)).get(
        'stream', (case, context), original)
    status, actual, used = c_stream(lib, case, context)
    if not result['ok'] or other or status or actual != expected or (context and used != consumed):
        first = next(((k, a, b) for k, (a, b) in enumerate(zip(expected, actual)) if a != b), None)
        raise AssertionError(('named body', hex(case['type']), case, result, other[:2], status,
                              len(expected), len(actual), first, consumed, used))
    return case, context, expected, consumed if context else 0


def cases(wa, lib, count=292, records=True):
    reset, vectors, families = ResetWorld(wa, quality.RandomWorld), [], {}
    for family in ('bodies', 'names', 'without_context', 'records'):
        before = len(vectors)
        for t in TYPES:
            rng = random.Random(0x2002f + t)
            if family == 'bodies':
                states = list(quality.state_cases(t))
                if count < len(states):
                    # Keep directed levels and the independent random tail while iterating.
                    front = min(count // 2, 192)
                    states = states[:front] + states[-(count-front):] if count > front else states[:front]
                for k, case in states:
                    case['lighting'] = k % 2
                    case['frame'] = (0, 1, 59, 60, 0x7fffffff, 0x80000000, 0xfffffffe, 0xffffffff)[k % 8]
                    vectors.append(compare(wa, lib, reset, case))
            elif family == 'names':
                clocks = (-6284.0, -6283.0, -1.0, 0.0, 1.0, 6283.0, 123456.0, 1999999.0)
                for config in v.CLASSIFY:
                    for k, values in enumerate(VALUES):
                        case = dict(v.classify_case(t, config),
                                    named_meshes=tuple(values[i % 3] for i in range(len(NAMES))), lighting=k % 2,
                                    time=v.f2u(clocks[k]),
                                    frame=(0, 1, 59, 60, 0x7fffffff, 0x80000000, 0xfffffffe, 0xffffffff)[k],
                                    _random=((0, 1, 4, 5, 24, 25, 32766, 32767)[k],) * 48)
                        vectors.append(compare(wa, lib, reset, case))
            elif family == 'without_context':
                for config in v.CLASSIFY:
                    case = dict(v.classify_case(t, config), named_meshes=(-1,) * len(NAMES))
                    vectors.append(compare(wa, lib, reset, case, context=False))
            elif records:
                for kind_b in (0x26, 0x5b):
                    for quality_value in (0, 1, 2, 9):
                        for level in range(16):
                            for option, ext in ((0, 0), (1, 1)):
                                case = v.random_case_any(rng, t)
                                case.update(item_level=level << 3, quality=quality_value, option1=option, ext=ext,
                                            record=(0, kind_b, 0), a10=0xffffffff, a11=0xffffffff,
                                            render_type=(2, 0x40042)[level % 2], lighting=level % 2)
                                vectors.append(compare(wa, lib, reset, case))
        families[family] = {'cases': len(vectors) - before, 'mismatches': 0}
        print(f'{family}: {len(vectors)-before} equal', flush=True)
    return families, vectors


MUTANTS = {
    'named-disabled': ('if (p->kind == 8)', 'if (p->kind == 255)'),
    'named-callback-disabled': ('c && c->mesh_named ?', '0 && c && c->mesh_named ?'),
    'named-name': ('mu_rc_body_names[p->a]', 'mu_rc_body_names[0]'),
    'named-context': ('c->mesh_named(c->mesh_context,', 'c->mesh_named(NULL,'),
    'named-missing-context': ('mu_rc_body_names[p->a]) : -1;', 'mu_rc_body_names[p->a]) : 0;'),
    'named-integer-word': ('input[35 + k] = (uint32_t)mesh;',
                           'float cast_mesh = (float)mesh; memcpy(&input[35 + k], &cast_mesh, 4);'),
    'named-level-split': ('mu_rc_body_types[type].level_split &&', 'mu_rc_body_types[type].level_split && 0 &&'),
    'named-body-random': ('random_program(p, rank5_random(s))', 'random_program(p, 0)'),
}


def mutations(vectors):
    source = (ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    caught = {}
    with tempfile.TemporaryDirectory() as folder:
        for name, (old, new) in MUTANTS.items():
            assert source.count(old) == 1, (name, source.count(old))
            path, library = Path(folder)/(name+'.c'), Path(folder)/(name+v.LIBRARY.suffix)
            path.write_text(source.replace(old, new))
            subprocess.run(['clang', '-shared', '-fPIC', '-O2', '-std=c11', '-ffp-contract=off',
                            '-I', str(ROOT/'reconstructed/renderchar'), str(path),
                            str(ROOT/'reconstructed/record-math/record_math.c'), '-lm', '-o', str(library)], check=True)
            lib = C.CDLL(str(library))
            detected = sum(c_stream(lib, case, context) != (0, expected, consumed)
                           for case, context, expected, consumed in vectors)
            if not detected:
                raise AssertionError(('surviving named mutant', name))
            caught[name] = detected
    return caught


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=int, default=292)
    parser.add_argument('--skip-records', action='store_true', help='iteration only')
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/renderchar')], check=True)
    wa = tuple(pin.read() for pin in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE))
    lib = C.CDLL(str(v.LIBRARY))
    families, vectors = cases(wa, lib, args.cases, not args.skip_records)
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': families}
    if args.mutations:
        report['mutants'] = mutations(vectors)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
