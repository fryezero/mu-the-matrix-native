#!/usr/bin/env python3
"""Part 13 carried-model-field and immediate-glColor bodies versus pinned instructions."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import subprocess
import tempfile
import gen_item_bodies as gen
import pins
import validate_item_clusters as clusters
import validate_item_wings_next as previous
import validate_renderchar as v

ROOT = Path(__file__).resolve().parents[1]
TYPES = gen.CARRY_TYPES + gen.COLOUR_TYPES


class ColourWorld(previous.BodyWorld):
    """Body random trapped; glColor3f/3fv/4f recorded into the draw stream at call time."""
    def install(self):
        super().install()
        gen.record_colours(self)


def colour_types():
    return [t for t in TYPES if any(entry == 'COLOR' for rule in gen_rules(t) for entry, _ in rule)]


_rules = {}


def gen_rules(t):
    """Recipes of one type from the generated table (no refit)."""
    if not _rules:
        import re
        source = (ROOT/'reconstructed/renderchar/item_bodies.h').read_text()
        recipes = source[source.index('mu_rc_body_recipes[] = {'):source.index('mu_rc_body_scalar;')]
        blocks = re.findall(r'\n    \{\d+, \{(.*?)\n    \}\},', recipes, re.S)
        parsed = [[({1: 'BODY', 2: 'MESH', 3: 'COLOR'}[int(entry)], None)
                   for entry in re.findall(r'\n        \{(\d), \{', block)] for block in blocks]
        for row in re.findall(r'\n    \{(0x[0-9a-f]{4}), \{([^}]*)\}', source[source.index('mu_rc_body_types[] = {'):]):
            _rules[int(row[0], 16)] = [parsed[int(k)] for k in row[1].split(', ')]
    return _rules[t]


def boundary_cases(wa, lib):
    """Every level, quality, option/ext pair and flag word for the carry types."""
    from item_body_machine import ResetWorld
    reset, vectors = ResetWorld(wa, ColourWorld), []
    for t in gen.CARRY_TYPES:
        rng = random.Random(0x2002f + t)
        for level in range(16):
            for quality in (0, 1, 2, 3, 4, 5, 9):
                for option1, ext in ((0, 0), (1, 0), (0, 1), (1, 2)):
                    for flags in (2, 0x102):
                        case = v.random_case_any(rng, t)
                        case.update(item_level=level << 3, quality=quality, render_type=flags, option1=option1,
                                    ext=ext, record=(0, 0, 0), a10=0xffffffff, a11=0xffffffff)
                        result, expected, other, _ = v.client_stream(wa, case, reset)
                        if not result['ok'] or other or v.c_stream(lib, case) != (0, expected):
                            raise AssertionError(('carry', hex(t), level, quality, option1, ext, flags, result, other))
                        vectors.append((case, expected))
    return {'cases': len(vectors), 'mismatches': 0}, vectors


def colour_cases(wa, lib):
    """The eleven survey states with extreme, negative-zero and NaN light/alpha words."""
    from item_body_machine import ResetWorld
    reset, vectors, records = ResetWorld(wa, ColourWorld), [], 0
    words = (0, 0x80000000, 0x3f800000, 0x7fc00000, 0x7f7fffff, 0x00000001, 0xbf800000)
    for t in colour_types():
        rng = random.Random(0x20030 + t)
        for config in v.CLASSIFY:
            for k in range(8):
                case = v.classify_case(t, config)
                pick = (lambda: rng.choice(words)) if k < 4 else (lambda: v.f2u(rng.uniform(0, 1.5)))
                case.update(light=[pick() for _ in range(3)], model_light=[pick() for _ in range(3)],
                            enchant=[pick() for _ in range(3)], alpha=pick() if k % 2 else v.f2u(0.9))
                result, expected, other, _ = v.client_stream(wa, case, reset)
                if not result['ok'] or other or v.c_stream(lib, case) != (0, expected):
                    raise AssertionError(('colour', hex(t), config, k, result, other))
                records += sum(1 for d in expected if d[0] == 'COLOR')
                vectors.append((case, expected))
    if not records:
        raise AssertionError('no colour record was compared')
    return {'cases': len(vectors), 'mismatches': 0, 'colour_records': records}, vectors


def mutations(vectors):
    source = (ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    changes = {
        'colour-drop': ('            ++s->count;\n            continue;\n        }', '            continue;\n        }'),
        'colour-rgb': ('memcpy(d.body_light, &words[8], 12);\n            if', 'memcpy(d.body_light, &words[9], 12);\n            if'),
        'colour-alpha': ('memcpy(&d.alpha, &words[2], 4);\n            memcpy(d.body_light',
                         'memcpy(&d.alpha, &words[1], 4);\n            memcpy(d.body_light'),
        'colour-kind': ('d.entry = MU_RC_ENTRY_COLOR;\n            d.flags = words[1];',
                        'd.entry = MU_RC_ENTRY_COLOR;\n            d.flags = 2;'),
        'carry-off': ('mu_rc_body_types[type].carry)', '0)'),
        'carry-first': ('if (last)\n            *last = d;', 'if (last && !drew)\n            *last = d;'),
        'carry-light': ('memcpy(model->body_light, d->body_light, sizeof model->body_light);', ''),
        'carry-channel': ('memcpy(model->body_light, d->body_light, sizeof model->body_light);',
                          'memcpy(model->body_light, d->body_light, 2 * sizeof(float));'),
        'carry-shade': ('memcpy(model->shade, d->shade, sizeof model->shade);',
                        'memcpy(model->shade, d->body_light, sizeof model->shade);'),
        'carry-flag': ('model->flag_ca = d->flag_ca;', 'model->flag_ca = (uint8_t)(d->flag_ca ^ 1u);'),
        'mesh-index': ('d.mesh = (int32_t)words[0];', 'd.mesh = (int32_t)words[0] + 1;'),
        'object-alpha': ('&s->item->object_alpha, 4', '&base.alpha, 4'),
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
        wa, lib, TYPES, args.screen, world_class=ColourWorld)
    if args.screen:
        report.update(rejected=[hex(f[0]) for f in failures])
    else:
        assert not failures
        report['families']['carry'], carry = boundary_cases(wa, lib)
        report['families']['colours'], colours = colour_cases(wa, lib)
        if args.mutations:
            report['mutants'] = mutations(bodies + carry + colours)
        if gen.generate() != (ROOT/'reconstructed/renderchar/item_bodies.h').read_text():
            raise AssertionError(('table drift', 'item_bodies.h'))
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
