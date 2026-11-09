#!/usr/bin/env python3
"""Part 14 bodies (supplementary record/quality probes, exit model fields, body random) versus pinned instructions."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import subprocess
import tempfile
import gen_item_bodies as gen
import pins
import validate_item_carry as carry
import validate_renderchar as v

ROOT = Path(__file__).resolve().parents[1]
TYPES = gen.QUALITY_TYPES


class RandomWorld(carry.ColourWorld):
    """glColor recorded; CRT rand 0x01989721 returns the case's scripted sequence and counts the calls."""
    def install(self):
        super().install()
        self.sequence, self.drawn = [], 0

        def rand(m):
            self.drawn += 1
            return self.sequence[self.drawn - 1] if self.drawn <= len(self.sequence) else 0
        self.m.stub(gen.RAND, rand, 0)


def compare(wa, lib, reset, case, sequence):
    """Client and C streams with the same rand results; both must consume the same count."""
    def factory(*args):
        world = reset(*args)
        world.sequence, world.drawn = sequence, 0
        return world
    result, expected, other, _ = v.client_stream(wa, case, factory)
    used = [0]

    def draw():
        used[0] += 1
        return sequence[used[0] - 1] if used[0] <= len(sequence) else 0
    status, actual = v.c_stream(lib, case, random=draw)
    ok = result['ok'] and not other and status == 0 and actual == expected and used[0] == reset.world.drawn
    return ok, expected, (result, other, status, actual, used[0], reset.world.drawn)


def sequence_for(rng):
    return [rng.choice((0, 32767, rng.randrange(32768), rng.randrange(32768))) for _ in range(48)]


def state_cases(t):
    """The 292 states of validate_item_clusters.body_cases, same seeds."""
    rng = random.Random(0x2002c + t)
    for k in range(292):
        case = v.random_case_any(rng, t)
        if k < 192:
            state, level = divmod(k, 16)
            case.update(item_level=(level << 3) | (state % 8), quality=(0, 1, 2, 3, 4, 5)[state % 6],
                        render_type=(2, 0x102, 0x402, 0x40042)[state % 4],
                        option1=state % 3, ext=(0, 1, 2, 0x10, 0x20, 0x33)[state % 6])
        case.update(record=rng.choice([None, (0, 0, 0), (6, 0, 0), (0, 0x26, 0), (0, 0x5b, 0)]),
                    a10=0xffffffff, a11=0xffffffff)
        yield k, case


def body_cases(wa, lib, types, screen=False):
    from item_body_machine import ResetWorld
    reset, vectors, failed = ResetWorld(wa, RandomWorld), [], []
    # Fresh-machine controls over the eleven survey states.
    for t in types[::max(1, len(types) // 12)]:
        for config in v.CLASSIFY:
            case = v.classify_case(t, config)
            fresh = v.client_stream(wa, case, RandomWorld)
            reused = v.client_stream(wa, case, reset)
            if fresh[:3] != reused[:3]:
                raise AssertionError(('reset-world control', hex(t), config))
    for t in types:
        rng, pending = random.Random(0x2002e + t), []
        for k, case in state_cases(t):
            sequence = sequence_for(rng)
            ok, expected, detail = compare(wa, lib, reset, case, sequence)
            if not ok:
                if not screen:
                    raise AssertionError(('body', hex(t), k, case, expected, detail))
                failed.append((t, k, case, expected, detail))
                break
            pending.append((case, sequence, expected))
        else:
            vectors.extend(pending)
        print(f'body {t:#x}: {len(pending)}/292', flush=True)
    return {'cases': len(vectors), 'mismatches': 0, 'types': len(vectors) // 292}, vectors, failed


def record_cases(wa, lib):
    """Kind-B 0x26/0x5b records (glow level 9) at every level, qualities 0-2 and 9, tail options and flags."""
    from item_body_machine import ResetWorld
    reset, vectors = ResetWorld(wa, RandomWorld), []
    for t in TYPES:
        rng = random.Random(0x2002f + t)
        for kind_b in (0x26, 0x5b):
            for quality in (0, 1, 2, 9):
                for level in range(16):
                    for option1, ext in ((0, 0), (1, 1)):
                        case = v.random_case_any(rng, t)
                        case.update(item_level=level << 3, quality=quality, option1=option1, ext=ext,
                                    render_type=(2, 0x40042)[level & 1], record=(rng.choice((0, 6)), kind_b, 0),
                                    a10=0xffffffff, a11=0xffffffff)
                        sequence = sequence_for(rng)
                        ok, expected, detail = compare(wa, lib, reset, case, sequence)
                        if not ok:
                            raise AssertionError(('record', hex(t), kind_b, quality, level, detail))
                        vectors.append((case, sequence, expected))
    return {'cases': len(vectors), 'mismatches': 0}, vectors


def random_types():
    return [t for t in TYPES if any(p[0] == 4 for p in table_programs(t))]


_programs = {}


def table_programs(t):
    """(kind, a) of each scalar program of one type, from the generated table."""
    if not _programs:
        import re
        source = (ROOT/'reconstructed/renderchar/item_bodies.h').read_text()
        rows = source[source.index('mu_rc_body_scalars[] = {'):source.index('mu_rc_body_types[] = {')]
        programs = [(int(kind), int(a, 16)) for kind, a in re.findall(r'\n    \{(\d+), \d+, (0x[0-9a-f]+)u', rows)]
        for row in re.findall(r'\n    \{(0x[0-9a-f]{4}), \{[^}]*\}, ([^}]*)\},', source[source.index('mu_rc_body_types[] = {'):]):
            fields = [int(x) for x in row[1].split(', ')]
            _programs[int(row[0], 16)] = programs[fields[-2]:fields[-2] + fields[-1]]
    return _programs.get(t, [])


def random_cases(wa, lib):
    """Random types in the eleven survey states with edge rand sequences (0, 32767, multiples of n, n-1)."""
    from item_body_machine import ResetWorld
    reset, vectors, draws = ResetWorld(wa, RandomWorld), [], 0
    for t in random_types():
        moduli = [a for kind, a in table_programs(t) if kind == 4]
        edges = sorted({x for n in moduli for x in (n - 1, n, 2 * n - 1, 32767 - 32767 % n, 32767 - 32767 % n - 1)
                        if 0 <= x <= 32767} | {0, 1, 32767})
        rng = random.Random(0x20031 + t)
        for config in v.CLASSIFY:
            for k in range(6):
                case = v.classify_case(t, config)
                sequence = [edges[(k + i) % len(edges)] for i in range(48)] if k < 3 else sequence_for(rng)
                case['record'] = (None, (0, 0, 0), (0, 0x26, 0), (0, 0x5b, 0), (6, 0, 0), (0, 0, 0))[k]
                ok, expected, detail = compare(wa, lib, reset, case, sequence)
                if not ok:
                    raise AssertionError(('random', hex(t), config, k, detail))
                draws += detail[4]
                vectors.append((case, sequence, expected))
    if not draws:
        raise AssertionError('no rand result was compared')
    return {'cases': len(vectors), 'mismatches': 0, 'rand_draws': draws}, vectors


MUTANTS = {
    'exit-off': ('            memcpy(s->model->body_light, &words[8], 12);\n            s->model->level_field',
                 '            continue;\n            memcpy(s->model->body_light, &words[8], 12);\n            s->model->level_field'),
    'exit-light': ('            memcpy(s->model->body_light, &words[8], 12);\n            s->model->level_field',
                   '            memcpy(s->model->body_light, &words[8], 8);\n            s->model->level_field'),
    # Omitting the level write is equivalent here: RenderObjDraw rewrites the level word before any
    # helper reads it. A wrong level, shade or flag value is caught.
    'exit-level': ('            s->model->level_field = (int32_t)words[11];\n            memcpy(s->model->shade',
                   '            s->model->level_field = (int32_t)words[11] + 1;\n            memcpy(s->model->shade'),
    'exit-shade': ('            memcpy(s->model->shade, &words[12], 12);\n            s->model->flag_ca = (uint8_t)words[15];',
                   '            memcpy(s->model->shade, &words[8], 12);\n            s->model->flag_ca = (uint8_t)words[15];'),
    'exit-flag': ('            s->model->flag_ca = (uint8_t)words[15];\n            continue;',
                  '            s->model->flag_ca = (uint8_t)(words[15] ^ 1u);\n            continue;'),
    'random-modulus': ('int32_t integer = value % (int32_t)p->a;', 'int32_t integer = value % ((int32_t)p->a + 1);'),
    'random-op': ('        default: x = x / k; break;', '        default: x = x * k; break;'),
    'random-phase': ('if (p->phases & (1u << phase))', 'if (p->phases)'),
    'random-value': ('value = random_program(p, rank5_random(s));', 'value = random_program(p, rank5_random(s) + 1);'),
    'mesh-index': ('d.mesh = (int32_t)words[0];', 'd.mesh = (int32_t)words[0] + 1;'),
    'object-alpha': ('&s->item->object_alpha, 4', '&base.alpha, 4'),
}


def run_c(lib, case, sequence):
    used = [0]

    def draw():
        used[0] += 1
        return sequence[used[0] - 1] if used[0] <= len(sequence) else 0
    status, actual = v.c_stream(lib, case, random=draw)
    return status, actual, used[0]


def mutations(vectors):
    source = (ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    # Rand results consumed by the validated library; equal to the client's count (compare()).
    reference = C.CDLL(str(v.LIBRARY))
    counts = [run_c(reference, case, sequence)[2] for case, sequence, _ in vectors]
    caught = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, (old, new) in MUTANTS.items():
            if source.count(old) != 1:
                raise AssertionError(('mutant anchor', name, source.count(old)))
            path, library = Path(tmp)/(name + '.c'), Path(tmp)/(name + '.dylib')
            path.write_text(source.replace(old, new))
            subprocess.run(['clang', '-shared', '-fPIC', '-O2', '-std=c11', '-ffp-contract=off',
                            '-I', str(ROOT/'reconstructed/renderchar'), str(path),
                            str(ROOT/'reconstructed/record-math/record_math.c'), '-lm', '-o', str(library)], check=True)
            lib = C.CDLL(str(library))
            detected = 0
            for (case, sequence, expected), count in zip(vectors, counts):
                status, actual, used = run_c(lib, case, sequence)
                detected += status != 0 or actual != expected or used != count
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
    report['families']['bodies'], bodies, failures = body_cases(wa, lib, TYPES, args.screen)
    if args.screen:
        report.update(rejected=[hex(f[0]) for f in failures])
    else:
        assert not failures
        report['families']['records'], records = record_cases(wa, lib)
        report['families']['random'], randoms = random_cases(wa, lib)
        if args.mutations:
            report['mutants'] = mutations(bodies + records + randoms)
        if gen.generate() != (ROOT/'reconstructed/renderchar/item_bodies.h').read_text():
            raise AssertionError(('table drift', 'item_bodies.h'))
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
