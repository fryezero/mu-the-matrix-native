#!/usr/bin/env python3
"""RENDER-EFFECTS-024: original loader calls, Ferea fire emitter and native sprite consumers.

Pinned original CreateEffect/MoveEffect and CreateParticle/MoveParticles/RenderParticles run under
Unicorn through the existing strict machines. Native loader checks use authored JPEG fixtures.
"""
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import actor_machine as am
import pins
import validate_render_effects as base
import validate_render_effects11 as re11
import validate_particles as pt
import validate_skill_fx as fx

ROOT = Path(__file__).resolve().parents[1]
BITMAPS = [(0x01823365, 0x81ec, 'Effect\\lightmarks_red.jpg'),
           (0x0182ec0d, 0x854a, 'Effect\\light_blue.jpg')]
CHILDREN = [(0x8084, 3), (0x806e, 4), (0x8085, 0)]
FX_MUTANTS = [
    ('admit_fire', 'sub == 0 || sub == 1 || sub == 10;', 'sub == 0 || sub == 1;', 'effect_create'),
    ('emitter_life', 'e->lifetime = 1;\n            break;\n        }\n        /* 0x013d2f05',
     'e->lifetime = 2;\n            break;\n        }\n        /* 0x013d2f05', 'effect_create'),
    ('emitter_blend', 'if (subtype == 10) {\n            e->blend_mesh = 1;',
     'if (subtype == 10) {\n            e->blend_mesh = 0;', 'effect_create'),
    ('emitter_choice', 'const int32_t choice = smod(env_rand(env), 3);',
     'const int32_t choice = smod(env_rand(env), 2);', 'effect_move'),
    ('emitter_bitmap', '{0x8084, 0x806e, 0x8085}', '{0x8085, 0x806e, 0x8084}', 'effect_move'),
    ('emitter_subtype', 'subtype[3] = {3, 4, 0}', 'subtype[3] = {0, 4, 0}', 'effect_move'),
    ('emitter_scale', 'subtype[choice], e->scale, MU_SFX_NO_OWNER);',
     'subtype[choice], 1.0f, MU_SFX_NO_OWNER);', 'effect_move'),
]
PT_MUTANTS = [
    ('admit_child', '(sub == 0 || sub == 3)', '(sub == 0 || sub == 2)', 'create'),
    ('child_size', '(ferea ? 52 : 72)', '(ferea ? 72 : 72)', 'create'),
    ('child_rise_range', '(ferea ? 14 : 24)', '(ferea ? 24 : 24)', 'create'),
    ('child_rise_offset', '(ferea ? 44 : 64)', '(ferea ? 64 : 64)', 'create'),
    ('child_shrink', '(p->subtype == 3 ? 2 : 5)', '(p->subtype == 3 ? 5 : 5)', 'move'),
]
NATIVE_MUTANTS = [
    ('red_id', '0x81ec, 0x854a,', '0x81ed, 0x854a,'),
    ('blue_id', '0x81ec, 0x854a,', '0x81ec, 0x854b,'),
    ('red_file', 'Data/Effect/lightmarks_red.OZJ', 'Data/Effect/light_blue.OZJ'),
    ('blue_file', 'Data/Effect/light_blue.OZJ', 'Data/Effect/lightmarks_red.OZJ'),
    ('filter', 't->filter[i] = bitmap_ids[i] == MU_PT_BITMAP_IMPACK03 ||',
     't->filter[i] = bitmap_ids[i] == 0x81ec || bitmap_ids[i] == MU_PT_BITMAP_IMPACK03 ||'),
    ('wrap', 't->wrap[i] = bitmap_ids[i] == 0x84d1 ||',
     't->wrap[i] = bitmap_ids[i] == 0x854a || bitmap_ids[i] == 0x84d1 ||'),
]


def build_host(directory, particles=None):
    directory = Path(directory)
    native = ROOT/'native'
    source = (native/'tests/effects24_host.c').read_text().replace(
        '#include "../core/mu_particles.c"', f'#include "{particles or native/"core/mu_particles.c"}"')
    (directory/'host.c').write_text(source)
    obj, host = directory/'host.o', directory/'host'
    flags = ['clang', '-std=c11', '-O1', '-ffp-contract=off', '-I', str(native/'build/gen'),
             '-I', str(native/'session'), '-iquote', str(native/'core')]
    subprocess.run(flags + ['-c', str(directory/'host.c'), '-o', str(obj)], check=True, capture_output=True)
    command = ['clang++', str(obj), str(native/'build/libmunative.a'),
               str(native/'build/libmusession_world.a'), '-lm', '-o', str(host)]
    if sys.platform == 'darwin':
        command += ['-L/opt/homebrew/opt/cryptopp/lib', '-lcryptopp', '-L/opt/homebrew/opt/jpeg-turbo/lib', '-ljpeg',
                    '-framework', 'CoreText', '-framework', 'CoreGraphics', '-framework', 'CoreFoundation']
    else:
        command += ['-lcryptopp', '-ljpeg']
    subprocess.run(command, check=True, capture_output=True)
    return host


def bitmap_fixture(directory):
    from PIL import Image
    root = Path(directory)/'game'
    effect = root/'Data/Effect'
    effect.mkdir(parents=True)
    for name, grey in [('lightmarks_red', 48), ('light_blue', 192)]:
        buf = io.BytesIO()
        Image.new('RGB', (32, 32), (grey, grey, grey)).save(buf, format='JPEG', quality=100)
        (effect/(name+'.OZJ')).write_bytes(bytes(24) + buf.getvalue())
    return root


def native_checks(host, root, report):
    run = subprocess.run([str(host), str(root)], capture_output=True, text=True)
    if run.returncode:
        report.add('native', False, {'exit': run.returncode, 'stderr': run.stderr[-1000:]})
        return
    result = json.loads(run.stdout)
    for row, (_, bitmap, _), grey in zip(result['bitmaps'], BITMAPS, (48, 192)):
        report.add('native', row['id'] == bitmap and row['slot'] >= 0 and row['filter'] == 0x2601 and
                   row['wrap'] == 0x2900 and row['loaded'] == 1 and abs(row['pixel'] - grey) <= 2, row)
    report.add('native', result['sprites'] == 2 and result['rain_last'] == 1, result)
    report.add('native', result['children'] == 3 and result['created'] == 1 and result['unsupported'] == 0 and
               result['effect_live'] == 0, result)


def registrations(text, data, report):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for call, bitmap, path in BITMAPS:
        ins = list(md.disasm(text[call-24-am.TEXT_BASE:call+5-am.TEXT_BASE], call-24))
        pushes = [int(i.op_str, 0) for i in ins if i.mnemonic == 'push']
        off = pushes[-1] - am.DATA_BASE
        actual = data[off:off+100].split(b'\0')[0]
        report.add('bitmaps', pushes == [0, 1, 0x2900, 0x2601, bitmap, pushes[-1]] and
                   actual == path.encode() and ins[-1].op_str == '0x185baac', {'bitmap': hex(bitmap)})


def compare(text, data, lib, domain, name, cases, report):
    saved_fx, saved_pt = fx.EFFECT_KINDS, pt.KINDS
    try:
        result = base.compare(text, data, lib, domain, name, [(0x413, 10)] if domain == 'fx' else CHILDREN,
                              cases * (1 if domain == 'fx' else len(CHILDREN)))
        report.families[domain+'_'+name] = result['families'][name]
        report.coverage[domain+'_'+name] = result['coverage'].get(name, {})
    finally:
        fx.EFFECT_KINDS, pt.KINDS = saved_fx, saved_pt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=int, default=1000)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output')
    args = parser.parse_args()
    if args.cases < 1:
        parser.error('--cases must be positive')
    start = time.monotonic()
    text, data = pins.TEXT.read(), pins.DATA.read()
    flib = fx.load_library(ROOT/f'reconstructed/combat/libcombat.{fx.SUFFIX}')
    plib = pt.load_library(ROOT/f'reconstructed/particles/libclient_particles.{fx.SUFFIX}')
    report = pt.Report()
    for domain, lib, names in [('fx', flib, ('effect_create', 'effect_move')), ('pt', plib, ('create', 'move', 'render'))]:
        for name in names:
            compare(text, data, lib, domain, name, args.cases, report)
    registrations(text, data, report)
    mutants = []
    with tempfile.TemporaryDirectory(prefix='effects24-') as tmp:
        root = bitmap_fixture(tmp)
        native_checks(build_host(tmp), root, report)
        equal = all(f['cases'] == f['equal'] for f in report.families.values())
        if args.mutations and equal:
            for domain, rows in [('fx', FX_MUTANTS), ('pt', PT_MUTANTS)]:
                for name, old, new, family in rows:
                    lib = (base.compile_mutant(Path(tmp), name, 'fx', old, new) if domain == 'fx' else
                           re11.compile_pt_mutant(tmp, name, 'world_flames.c', old, new))
                    rr = pt.Report()
                    compare(text, data, lib, domain, family, 120, rr)
                    f = rr.families[domain+'_'+family]
                    mutants.append(dict(name=name, detected=f['cases']-f['equal'],
                                        stopped=sum(bool(x.get('stopped')) for x in f['first_failures'])))
                    print('mutant', json.dumps(mutants[-1]), flush=True)
            for name, old, new in NATIVE_MUTANTS:
                work = Path(tmp)/name
                work.mkdir()
                source = (ROOT/'native/core/mu_particles.c').read_text()
                if source.count(old) != 1:
                    raise ValueError(f'{name}: nonunique anchor')
                path = work/'mu_particles.c'
                path.write_text(source.replace(old, new))
                rr = pt.Report()
                native_checks(build_host(work, path), root, rr)
                f = rr.families['native']
                mutants.append(dict(name=name, detected=f['cases']-f['equal'], stopped=0))
                print('mutant', json.dumps(mutants[-1]), flush=True)
    result = dict(families=report.families, coverage=report.coverage, all_equal=equal,
                  cases=sum(f['cases'] for f in report.families.values()), mutants=mutants,
                  all_mutants_caught=all(m['detected'] and not m['stopped'] for m in mutants),
                  seconds=round(time.monotonic()-start, 3), text_sha256=am.TEXT_SHA256, data_sha256=am.DATA_SHA256)
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0 if equal and result['all_mutants_caught'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
