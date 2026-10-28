#!/usr/bin/env python3
"""Part 4 body/skin recipes and two link callers versus pinned instructions."""
import argparse
import ctypes as C
import json
from pathlib import Path
import subprocess
import tempfile
import gen_item_bodies as gen
import gen_item_glow as glow
import pins
import validate_item_clusters as clusters
import validate_item_types as previous
import validate_renderchar as v

ROOT = Path(__file__).resolve().parents[1]
SKINS = glow.SKIN_TYPES


def mutations(directory, bodies, links):
    source = (ROOT/'reconstructed/renderchar/renderchar.c').read_text()
    changes = {
        'armour-pulse': ('* 0.5f + 0.2f;', '* 0.5f + 0.3f;'),
        'mesh-index': ('d.mesh = (int32_t)words[0];', 'd.mesh = (int32_t)words[0] + 1;'),
        'skin-level': ('level = mu_rc_skin_glow_rows[i].levels[level];', 'level = mu_rc_skin_glow_rows[i].levels[level] + 1;'),
        'skin-record-bound': ('(uint32_t)(it->type - 0xae6) <= 0x2c00u && it->kind_a', 'it->kind_a'),
        'axe-offset': ('-100.0f + jitter', '-99.0f + jitter'),
        'axe-rotation': ('i ? 90.0f : 0.0f', 'i ? 91.0f : 0.0f'),
        'sword-clock': ('client_sin(time * 0.4f)', 'client_sin(time * 0.3f)'),
    }
    caught = {}
    for name, (old, new) in changes.items():
        if source.count(old) != (2 if name == 'axe-offset' else 1):
            raise AssertionError(('mutant anchor', name))
        path, library = directory/f'{name}.c', directory/f'{name}.dylib'
        path.write_text(source.replace(old, new))
        subprocess.run(['clang', '-shared', '-fPIC', '-O2', '-std=c11', '-ffp-contract=off',
                        '-I', str(ROOT/'reconstructed/renderchar'), str(path),
                        str(ROOT/'reconstructed/record-math/record_math.c'), '-lm', '-o', str(library)], check=True)
        lib = C.CDLL(str(library))
        detected = sum(v.c_stream(lib, case) != (0, expected) for case, expected in bodies)
        detected += sum(clusters.c_effects(lib, t, values, time) != expected
                        for t, values, time, expected in links)
        if not detected:
            raise AssertionError(('surviving mutant', name))
        caught[name] = detected
    return caught


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mutations', action='store_true')
    args = parser.parse_args()
    wa = tuple(pin.read() for pin in (pins.TEXT, pins.DATA, pins.FLAG, pins.FEATURE))
    subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/renderchar')], check=True)
    lib = C.CDLL(str(v.LIBRARY))
    report = {'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'families': {}}
    report['families']['skin_remaps'] = previous.scalar_cases(wa[0], lib, SKINS)
    if report['families']['skin_remaps']['mismatches']:
        raise AssertionError('skin scalar rules differ')
    report['families']['links'], links = clusters.link_cases(wa, lib, (0x0ef4, 0x0afc))
    report['families']['bodies'], bodies, failures = clusters.body_cases(wa, lib, gen.ADDITIONAL_TYPES)
    assert not failures
    report['body_types'] = [t for t in gen.ADDITIONAL_TYPES if t < 0x3700]
    report['skins'] = [t for t in gen.ADDITIONAL_TYPES if t >= 0x3700]
    if gen.generate() != (ROOT/'reconstructed/renderchar/item_bodies.h').read_text():
        raise AssertionError('body table drifted')
    if glow.generate(wa[0], SKINS, 'mu_rc_skin_glow_rows') != (ROOT/'reconstructed/renderchar/skin_glow.h').read_text():
        raise AssertionError('skin scalar table drifted')
    if args.mutations:
        with tempfile.TemporaryDirectory() as temp:
            report['mutants'] = mutations(Path(temp), bodies, links)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'families': report['families'], 'mutants': report.get('mutants', {})}))


if __name__ == '__main__':
    main()
