#!/usr/bin/env python3
"""RENDER-ACTORS-001: Player-model actor equipment, skeleton body hook and native loading.

The original generic constructor and map processors execute through the existing
actor machine. RenderCharacter executes from its entry with authored Player bones;
the part calls, not original pixels, are compared. No live process or service state.
"""
import argparse
import ctypes as C
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import time

import actor_machine as am
import pins
import validate_actors as va
import validate_renderchar as vr

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT/'reconstructed/actors'/('libactors.dylib' if sys.platform == 'darwin' else 'libactors.so')
FIXED = (14, 15, 16, 34, 55, 56, 229, 236, 247, 249, 257, 258, 297, 371, 375, 414, 464)
SKELETON = (14, 15, 16, 55, 56, 236)
CENSUS = FIXED + (372, 373, 374, 378, 503, 548, 616, 617, 625, 626, 642, 646, 706, 806, 807)


class Slot(C.Structure):
    _fields_ = [('type', C.c_uint16), ('level', C.c_uint8)]


class Row(C.Structure):
    _fields_ = [('server_class', C.c_uint16), ('kind', C.c_uint8), ('model', C.c_uint16),
                ('opened', C.c_uint16), ('scale_bits', C.c_uint32), ('slots', Slot * 9), ('class_byte', C.c_uint8)]


def library(path):
    lib = C.CDLL(str(path))
    lib.mu_actor_player_body.argtypes = [C.c_int32]
    lib.mu_actor_player_recipe.argtypes = [C.c_int32, C.POINTER(Row)]
    return lib


def note(fam, ok, detail):
    fam['cases'] += 1
    fam['equal'] += bool(ok)
    if not ok and len(fam['first_failures']) < 5:
        fam['first_failures'].append(detail)


def family():
    return dict(cases=0, equal=0, first_failures=[])


def originals(args):
    text = pins.TEXT.read(args.text)
    data = pins.DATA.read(args.data)
    machine = am.ActorMachine(text, data)
    rows = {cl: va.extract_class(machine, cl) for cl in CENSUS}
    # The extractor intentionally stubs CreateCharacter and post-create engine
    # metadata. Read the subtype actually written by the six generic constructors.
    for cl in SKELETON:
        regions, stubs, record = va.class_case(0, 0)
        run = machine.execute(va.CREATE_GENERIC, [cl, 10, 20, 1000 + cl, 0], regions, stubs,
                              frame=(0x1dd4 + 0xc, {-0x10: 0}))
        if not run['ok']: raise RuntimeError(run)
        rows[cl]['body'] = struct.unpack_from('<I', run['regions']['character'], 0x32b4)[0]
        rows[cl]['body_level'] = struct.unpack_from('<H', run['regions']['character'], 0x144)[0]
    return (text, data, pins.FLAG.read(args.flag), pins.FEATURE.read(args.feature)), rows


def check_loader(args):
    """Execute the startup loop, returning at its exclusive end boundary."""
    machine = am.ActorMachine(args[0], args[1]); calls = []; fam = family()
    def access(m):
        def string(address):
            out = bytearray()
            while True:
                byte = m.uc.mem_read(address, 1)[0]
                if byte == 0: return out.decode('ascii')
                out.append(byte); address += 1
        calls.append((m.argument(0), string(m.argument(1)), string(m.argument(2)), m.argument(3)))
        return 0
    def end(uc, address, size, ignored):
        m = machine
        uc.reg_write(m.x86.UC_X86_REG_EBP, m.preserved[m.x86.UC_X86_REG_EBP])
        uc.reg_write(m.x86.UC_X86_REG_ESP, am.ENTRY_ESP + 4)
        uc.mem_write(am.TIB, struct.pack('<I', am.SEH_HEAD))
        uc.reg_write(m.x86.UC_X86_REG_EIP, am.SENTINEL)
        uc.emu_stop()
    machine.uc.hook_add(machine.UC_HOOK_CODE, end, begin=0x01832c5d, end=0x01832c5d)
    run = machine.execute(0x01832c28, [], [], {va.ACCESS_MODEL: access}, frame=(0x100, {}))
    for index, number in enumerate((1, 2, 3)):
        expected = (0x422 + index, 'Data\\Skill\\', 'Skeleton', number)
        note(fam, run['ok'] and len(calls) == 3 and calls[index] == expected, {'calls': calls, 'run': run})
    return fam


def check_recipes(lib, rows):
    fam = family()
    for cl in CENSUS + (-1, 0, 251, 65535):
        row = Row(); status = lib.mu_actor_player_recipe(cl, C.byref(row))
        if cl not in FIXED:
            note(fam, status == 0 and lib.mu_actor_player_body(cl) == 0, {'class': cl, 'status': status})
            continue
        source = rows[cl]
        expected = [list(x) for x in source['slots']]
        if cl in SKELETON: expected[0] = [source['body'], source['body_level'] if cl == 236 else 0]
        actual = [[s.type, s.level] for s in row.slots]
        ok = status == 1 and row.model == source['model'] and row.scale_bits == source['scale_bits'] and \
             row.class_byte == source['class_byte'] and actual == expected
        note(fam, ok, {'class': cl, 'actual': actual, 'expected': expected})
    return fam


def check_render(lib, args, rows, cases):
    fam = family(); rng = random.Random(20261109)
    original_record = vr.character_record
    original_world = vr.World
    try:
        for i in range(cases):
            cl = SKELETON[i % len(SKELETON)]; subtype = rows[cl]['body']
            world_id = (0, 3, 2, 51)[(i // len(SKELETON)) % 4]
            def world(*args):
                w = original_world(*args)
                w.m.ensure(0x01cf15fc, 4)
                w.m.w32(0x01cf15fc, world_id)
                return w
            vr.World = world
            alpha = vr.f2u(rng.uniform(.05, 1)); action = rng.choice((1, 11, 50, 52, 111, 113, 114, 120))
            def record(**kw):
                raw = original_record(**kw)
                struct.pack_into('<I', raw, 0x32b4, subtype)
                struct.pack_into('<h', raw, 0x146, cl)
                struct.pack_into('<H', raw, 0x144, rows[cl]['body_level'])
                raw[0x328f] = 4 if cl == 236 else 2
                return raw
            vr.character_record = record
            ch = {'class': 0, 'action': action, 'safe': 0, 'frame': vr.f2u(rng.uniform(0, 10)),
                  'alpha': alpha, 'select': 0, 'speeds': [vr.f2u(.25)] * 390, 'slots': [None] * 9}
            run, calls, world = vr.character_client(args, ch)
            recipe = Row(); lib.mu_actor_player_recipe(cl, C.byref(recipe))
            level = recipe.slots[0].level if world_id == 0 else 0
            body = [('PART', -1, lib.mu_actor_player_body(cl), level << 3, 0, 0, 1, 0, 2)]
            actual = [c for c in calls if c[0] == 'PART']
            rpo = [c for c in world.calls if c[0] == 'RPO' and c[2] != 1]
            note(fam, run['ok'] and actual == body and len(rpo) == 1 and rpo[0][1][4] == alpha,
                 {'class': cl, 'world': world_id, 'action': action, 'calls': actual, 'expected': body, 'run': run if not run['ok'] else None})
    finally:
        vr.character_record = original_record
        vr.World = original_world
    return fam


def check_equipment(args, rows):
    fam = family(); original_record = vr.character_record
    lib = C.CDLL(str(vr.LIBRARY))
    try:
        for cl in FIXED:
            if cl in SKELETON: continue
            row = rows[cl]
            def record(**kw):
                raw = original_record(**kw)
                struct.pack_into('<h', raw, 0x146, cl)
                raw[0x328f] = 4 if cl in (229, 247, 249, 257, 371, 375, 414, 464) else 2
                return raw
            vr.character_record = record
            slots = [None if t in (0, 65535) else
                     dict(type=t, level=level, option=0, ext=0, kind=0, action=0, frame=0, prior=0, speed=0)
                     for t, level in row['slots']]
            ch = {'class': row['class_byte'], 'action': 1, 'safe': 0, 'frame': 0, 'alpha': vr.f2u(1),
                  'select': 0, 'speeds': [vr.f2u(.25)] * 390, 'slots': slots}
            run, calls, _ = vr.character_client(args, ch)
            status, expected = vr.character_c(lib, ch)
            note(fam, run['ok'] and status == 0 and calls == expected,
                 {'class': cl, 'calls': calls, 'expected': expected})
    finally:
        vr.character_record = original_record
    return fam


def check_body_draw(args):
    # Whole skeleton bodies use the original generic RenderObjDraw path.
    # Compare level zero and Golden Archer's town +8, without item admission.
    fam = family(); lib = C.CDLL(str(vr.LIBRARY)); rng = random.Random(422)
    for t, level in ((0x422, 0), (0x423, 0), (0x424, 0), (0x423, 8)):
        for i in range(12):
            case = vr.classify_case(t, dict(item_level=level << 3, option1=0, ext=0, quality=5,
                                            time=vr.f2u(i * 12345.5), render_type=2))
            case['alpha'] = vr.f2u(rng.uniform(.01, 1))
            case['light'] = [vr.f2u(rng.uniform(.05, 1.5)) for _ in range(3)]
            run, stream, _, _ = vr.client_stream(args, case)
            status, expected = vr.c_stream(lib, case, generic=True)
            note(fam, run['ok'] and status == 0 and stream == expected,
                 {'type': t, 'level': level, 'stream': stream, 'expected': expected})
    return fam


def build_host(directory, source=None, draw_source=None):
    directory = Path(directory); native = ROOT/'native'
    code = (native/'tests/actor_recipe_host.c').read_text().replace(
        '#include "../core/mu_world_actors.c"', '#include "' + str(source or native/'core/mu_world_actors.c') + '"')
    (directory/'host.c').write_text(code)
    subprocess.run(['clang', '-std=c11', '-O1', '-ffp-contract=off', '-iquote', str(native/'core'),
                    '-I', str(native/'build/gen'), '-I', str(native/'session'), '-c', str(directory/'host.c'),
                    '-o', str(directory/'host.o')], check=True, capture_output=True)
    objects = [str(directory/'host.o')]
    if draw_source:
        subprocess.run(['clang', '-std=c11', '-O1', '-ffp-contract=off', '-iquote', str(native/'core'),
                        '-c', str(draw_source), '-o', str(directory/'draw.o')], check=True, capture_output=True)
        objects.append(str(directory/'draw.o'))
    subprocess.run(['clang++', *objects, str(native/'build/libmunative.a'),
                    str(native/'build/libmusession_world.a'), '-L/opt/homebrew/opt/cryptopp/lib', '-lcryptopp',
                    '-L/opt/homebrew/opt/jpeg-turbo/lib', '-ljpeg', '-framework', 'CoreText',
                    '-framework', 'CoreGraphics', '-framework', 'CoreFoundation', '-lm', '-o', str(directory/'host')],
                   check=True, capture_output=True)
    return directory/'host'


def check_native(host, root, rows):
    fam = family()
    for cl, world_id in [(cl, 0) for cl in FIXED] + [(cl, 3) for cl in SKELETON]:
        result = subprocess.run([str(host), root, str(cl), str(world_id)], capture_output=True, text=True)
        if result.returncode:
            note(fam, False, {'class': cl, 'world': world_id, 'exit': result.returncode, 'error': result.stderr[-1500:]}); continue
        value = json.loads(result.stdout); expected = rows[cl]
        slots = [list(x) for x in expected['slots']]
        if cl in SKELETON: slots[0] = [expected['body'], expected['body_level'] if cl == 236 and world_id == 0 else 0]
        correct = value['player'] == 1
        scale = am.from_bits(expected['scale_bits']) if expected['scale_bits'] else am.f32(.9)
        correct &= abs(value['scale'] - scale) < 1e-7
        for k, (t, level) in enumerate(slots):
            loaded = 0 < t < 0xffff
            actual = value['slots'][k]
            correct &= bool(actual[0]) == loaded
            if loaded:
                correct &= actual[1:3] == [t, level] and actual[3] > 0 and actual[4] == 0
                if cl in SKELETON and k == 0:
                    correct &= actual[5:] == [2 if level == 8 else 1, 0]
        note(fam, correct, value)
    return fam


def build_library(source, target):
    directory = ROOT/'reconstructed/actors'
    subprocess.run(['clang', '-shared', '-fPIC', '-std=c11', '-O2', '-ffp-contract=off', '-I', str(directory),
                    str(source), str(ROOT/'reconstructed/model-codec/skinning.c'),
                    str(ROOT/'reconstructed/model-codec/pose_builder.c'), str(ROOT/'reconstructed/model-codec/bone_tracks.c'),
                    str(ROOT/'reconstructed/record-math/record_math.c'), '-lm', '-o', str(target)],
                   check=True, capture_output=True)
    return library(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text', type=Path)
    parser.add_argument('--data', type=Path)
    parser.add_argument('--flag', type=Path)
    parser.add_argument('--feature', type=Path)
    parser.add_argument('--game-root', default=os.environ.get('MU_GAME_ROOT'))
    parser.add_argument('--cases', type=int, default=240)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    opts = parser.parse_args(); started = time.monotonic()
    args, rows = originals(opts)
    lib = library(LIBRARY)
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        fams = {'recipes': check_recipes(lib, rows), 'render': check_render(lib, args, rows, opts.cases),
                'equipment': check_equipment(args, rows), 'body_draw': check_body_draw(args),
                'loader': check_loader(args),
                'native': check_native(build_host(directory), opts.game_root, rows)}
        mutants = {}
        if opts.mutations:
            source = (ROOT/'reconstructed/actors/actors.c').read_text()
            changes = [('body_422', 'case 14: case 55: case 56: return 0x422;', 'case 14: case 55: case 56: return 0x423;'),
                       ('body_423', 'case 15: case 236: return 0x423;', 'case 15: case 236: return 0x424;'),
                       ('body_424', 'case 16: return 0x424;', 'case 16: return 0x422;'),
                       ('body_level', 'server_class == 236 ? 8 : 0', '0'),
                       ('empty_recipe', 'if (!body && !row->slots[1].type)', 'if (!body && row->slots[1].type)'),
                       ('nonplayer', 'row->kind != MU_CLASS_PLAYER_MODEL', 'row->kind == MU_CLASS_PLAYER_MODEL'),
                       ('body_slot', 'out->slots[0].type = (uint16_t)body;', 'out->slots[1].type = (uint16_t)body;')]
            for name, old, new in changes:
                assert source.count(old) == 1, (name, source.count(old))
                path = directory/'actors.c'; path.write_text(source.replace(old, new))
                mutant = build_library(path, directory/(name+'.dylib'))
                check = check_recipes(mutant, rows)
                mutants[name] = {'caught': check['equal'] < check['cases'], 'stopped': 0}
            source = (ROOT/'native/core/mu_world_actors.c').read_text()
            for name, old, new in [('skip_body', 'for (int k = 0; k < MU_CHARACTER_ITEMS; k++)',
                                    'for (int k = 1; k < MU_CHARACTER_ITEMS; k++)'),
                                   ('body_file', 'type - 0x421', 'type - 0x420'),
                                   ('body_directory', 'Data/Skill/Skeleton', 'Data/Player/Skeleton'),
                                   ('body_world', 'params->world == 0 ? row->slots[k].level : 0', 'row->slots[k].level')]:
                assert source.count(old) == 1, (name, source.count(old))
                path = directory/'mu_world_actors.c'; path.write_text(source.replace(old, new))
                check = check_native(build_host(directory, path), opts.game_root, rows)
                mutants[name] = {'caught': check['equal'] < check['cases'], 'stopped': 0}
            source = (ROOT/'native/core/mu_renderchar.c').read_text()
            old = 'glow->type >= 0x422 && glow->type <= 0x424'
            assert source.count(old) == 1
            path = directory/'mu_renderchar.c'; path.write_text(source.replace(old, '0'))
            check = check_native(build_host(directory, draw_source=path), opts.game_root, rows)
            mutants['body_draw_admission'] = {'caught': check['equal'] < check['cases'], 'stopped': 0}
    report = {'text_sha256': am.TEXT_SHA256, 'data_sha256': am.DATA_SHA256,
              'families': fams, 'cases': sum(x['cases'] for x in fams.values()),
              'all_equal': all(x['equal'] == x['cases'] for x in fams.values()), 'mutants': mutants,
              'all_mutants_caught': all(x['caught'] for x in mutants.values()),
              'wall_seconds': time.monotonic() - started}
    opts.output.parent.mkdir(parents=True, exist_ok=True); opts.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
    return 0 if report['all_equal'] and report['all_mutants_caught'] else 1


if __name__ == '__main__': sys.exit(main())
