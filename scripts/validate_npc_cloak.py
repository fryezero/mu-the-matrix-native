#!/usr/bin/env python3
"""CLOAK-004: NPC/monster constructor 0x01362755 and its real MoveCloth/RenderCloth callers.

Original code executes with authored bones, models and shared rand state. Model lookup, allocator and GL
services are the existing cloth harness's. Compare all cloth fields, springs, vertices, rand state and ordered
GL streams. No original-client process or network input. --mutations compiles mistakes in the added constructor.
"""
from __future__ import annotations
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import shutil
import struct
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_armour_cloak as a
import validate_item_cloak as v
import pins

ROOT = v.ROOT
NPC_CREATE = 0x01362755
# Positive cases, adjacent exclusions, a common NPC and player class-index sentinel.
INDICES = (0x37, 0x169, 0x3a9, 0x3ab, 0x3ac, 0x3ad, 0x36, 0x38, 0x168, 0x16a, 0x3a8, 0x3aa, 0x3ae, 251, -1)


def configure(lib):
    lib.mu_cloth_npc_create.argtypes = [C.POINTER(v.CCloth), C.c_int16, C.POINTER(v.CHost)]
    lib.mu_cloth_npc_cloths.argtypes = [C.c_int16]
    lib.mu_cloth_npc_model.argtypes = [C.c_int16, C.c_int32, C.POINTER(C.c_float)]
    return lib


class Client(a.Client):
    def __init__(self, args, case):
        super().__init__(args, case)
        # Exercise lookup on the actor model, rather than silently using Player for every NPC.
        if case['model'] != 0xa91 and case['has_model']:
            self.w.add_model(case['model'], v.vr.PLAYER_MODEL, bones=case['bone_count'], meshes=0, actions=390)
        self.m.w32(self.o + 0x5c, case['model'])

    def create(self, st):
        self.apply(st)
        return self.m.run(NPC_CREATE, [v.vr.CHAR, self.o, v.LIGHT_VEC])


class CSide(v.CSide):
    def create(self, st):
        self.apply(st)
        self.count = self.lib.mu_cloth_npc_create(self.cloths, self.case['class_index'], C.byref(self.host))
        return self.count

    def frame(self, st, first):
        self.apply(st)
        self.stream.clear()
        self.move_cloth()
        if not self.count and self.create(st):
            self.move_cloth()
        c = self.case
        if (self.lib.mu_cloth_draw_allowed(c['class'], c['subtype'], 1, 1, c['class_index']) and
                self.lib.mu_cloth_armour_draw_allowed(c['class'], c['subtype'])):
            for cloth in self.cloths[:self.count]:
                if cloth.owner:
                    self.lib.mu_cloth_render(C.byref(cloth), C.byref(self.host), C.byref(self.g), None, C.byref(self.sink))
        return list(self.stream)


def families(args, lib, opts):
    rng = random.Random(opts.seed)
    fam = {k: v.new_family() for k in ('create', 'existing', 'step', 'render')}
    for i in range(opts.cases):
        index = INDICES[i % len(INDICES)]
        case = v.random_case(rng, -1, i)
        case.update({'class': 0, 'armour': -1, 'pants': -1, 'pants_level': 0, 'enabled': 0,
                     'class_index': index, 'color': [1, 1, 1], 'quality': 5, 'subtype': 0, 'arg4': 0,
                     'model': (0xa91 if index == 0x37 else 0x95a if index == 0x3a9 else 0xa8b if index >= 0x3ab else 0x81e)})
        if i < len(INDICES):
            case.update(bones=1, bone_count=60, has_model=1)
        fr = random.Random(case['seed'])
        base = {'time0': case['time0'], 'steps0': case['steps0'], 'origin0': case['origin0']}
        bones = case['bones0']
        st = v.frame_state(fr, 0, base); st['bones'] = bones
        client, side = Client(args, case), CSide(lib, case)
        run = client.create(st); side.create(st)
        count, ptr, original = client.read()
        diff = v.first_difference(original, [v.c_cloth_view(c) for c in side.cloths[:side.count]])
        if not run['ok']: fam['create']['stopped'] += 1
        v.note(fam['create'], run['ok'] and count == side.count and ptr == bool(side.count) and not diff,
               {'case': i, 'index': hex(index), 'diff': diff, 'run': run})
        if count:
            again = client.create(st)
            after = client.read()
            v.note(fam['existing'], again['ok'] and (client.m.uc.reg_read(client.m.x86.UC_X86_REG_EAX) & 0xff) == 0 and after == (count, ptr, original),
                   {'case': i, 'run': again})
        client, side = Client(args, case), CSide(lib, case)
        for frame in range(opts.frames):
            st = v.frame_state(fr, frame, base)
            if frame: bones = v.perturb(fr, bones, 0.5)
            st['bones'] = bones
            ok, stream, runs = client.frame(st, False)
            native = side.frame(st, False)
            count, ptr, original = client.read()
            diff = v.first_difference(original, [v.c_cloth_view(c) for c in side.cloths[:side.count]])
            if not ok: fam['step']['stopped'] += 1; fam['render']['stopped'] += 1
            v.note(fam['step'], ok and count == side.count and not diff and client.state['seed'] == side.g.rand_seed,
                   {'case': i, 'frame': frame, 'diff': diff, 'runs': runs if not ok else None})
            x, y = v.stream_bits(stream), v.stream_bits(native)
            v.note(fam['render'], ok and x == y, {'case': i, 'frame': frame, 'length': [len(x), len(y)],
                   'first': next(([j, x[j], y[j]] for j in range(min(len(x), len(y))) if x[j] != y[j]), None)})
    fam['models'] = model_family(args, lib)
    return fam


def model_family(args, lib):
    # Execute through the real CreateCharacter argument setup and following scale store. Stop before
    # post-create effects. These entries never cross the opaque CreateMonster chain boundary.
    from unicorn import UC_HOOK_CODE
    fam = v.new_family()
    for index, world, entry, stop_at in ((0x169, 39, 0xe879ad, 0xe87a5a),
                                        (0x3a9, 0, 0xd5a9d3, 0xd5adab)):
        w = v.vr.World(*args); m = w.m
        m.ensure(v.WORLD, 4); m.w32(v.WORLD, world)
        m.stub(0x180b0f4, lambda mm: 0, 0)
        found, reached = [], []
        def create(mm):
            found.append([mm.arg(i) for i in range(5)])
            return v.vr.CHAR
        m.stub(0x137f6c2, create, 0)
        # Class 937's name constructor/assignment, not part of the model/scale decision.
        m.stub(0x94997e, lambda mm: mm.uc.reg_read(mm.x86.UC_X86_REG_ECX), 4)
        m.stub(0x8e83a0, lambda mm: 0, 0)
        m.stub(0x129de8d, lambda mm: 0, 4)
        def stop(uc, address, size, user):
            reached.append(address)
            uc.emu_stop()
        hook = m.uc.hook_add(UC_HOOK_CODE, stop, begin=stop_at, end=stop_at)
        m.run(entry, [index, 10, 20, 1000], ecx=0x20000000)
        m.uc.hook_del(hook)
        scale = C.c_float()
        model = lib.mu_cloth_npc_model(index, world, C.byref(scale))
        v.note(fam, bool(reached) and len(found) == 1 and found[0][1] == model,
               {'index': index, 'model': model, 'original': found, 'reached': reached})
        v.note(fam, bool(reached) and v.f2u(scale.value) == m.r32(v.vr.CHAR + 0x32f4),
               {'index': index, 'scale': scale.value})
    for world in (0, 2, 3, 38, 40):
        scale = C.c_float(7)
        v.note(fam, lib.mu_cloth_npc_model(0x169, world, C.byref(scale)) == -1 and scale.value == 7,
               {'world': world})
    return fam


MUTANTS = {
    'nightmare_world': ('class_index == 0x169 && world == 39', 'class_index == 0x169 && world == 38'),
    'nightmare_model': ('return 0x81e;', 'return 0x81f;'),
    'nightmare_scale': ('*scale = 1.6f;', '*scale = 1.5f;'),
    'virtual_model': ('return 0x95a;', 'return 0x95b;'),
    'virtual_scale': ('*scale = 0.9f;', '*scale = 0.8f;'),
    'class55': ('case 0x37: case 0x169: return 1;', 'case 0x38: case 0x169: return 1;'),
    'class937': ('case 0x3a9: case 0x3ab: case 0x3ac: case 0x3ad: return 2;',
                 'case 0x3aa: case 0x3ab: case 0x3ac: case 0x3ad: return 2;'),
    'robe_bone': ('h, 19, 0.0f, 10.0f, 0.0f, 10, 10, 55.0f', 'h, 18, 0.0f, 10.0f, 0.0f, 10, 10, 55.0f'),
    'robe_type': ('0x790d, 0x790d, 0x1001', '0x790d, 0x790d, 0x1005'),
    'robe_sphere': ('-40.0f, 50.0f, 19', '-40.0f, 49.0f, 19'),
    'nightmare_grid': ('0.0f, 6, 6, 180.0f, 100.0f', '0.0f, 5, 6, 180.0f, 100.0f'),
    'nightmare_type': ('0x7ff2, 0x7ff2, 0x1008', '0x7ff2, 0x7ff2, 0x1004'),
    'halves_side': ('const float x = i ? -10.0f : 10.0f;', 'const float x = 10.0f;'),
    'halves_bitmap': ('i ? 0x84e7 : 0x84e6, i ? 0x84e7 : 0x84e6', 'i ? 0x84e6 : 0x84e7, i ? 0x84e7 : 0x84e6'),
    'halves_uv': ('out[i].uv_scale[0] = 0.5f;\n            out[i].uv_scale[1] = 1.0f;', 'out[i].uv_scale[0] = 1.0f;\n            out[i].uv_scale[1] = 1.0f;'),
    'halves_sphere': ('-x, -5.0f, -30.0f, 35.0f, 3', '-x, -5.0f, -30.0f, 35.0f, 4'),
}


def mutations(args, opts, work):
    source = (v.DIR / 'cloth.c').read_text()
    result = {}
    small = argparse.Namespace(**vars(opts)); small.cases = len(INDICES); small.frames = 2
    (work / 'record-math').mkdir(exist_ok=True)
    shutil.copy(ROOT / 'reconstructed/record-math/record_math.h', work / 'record-math/record_math.h')
    for name, (old, new) in MUTANTS.items():
        if source.count(old) != 1: raise SystemExit(f'{name}: anchor count {source.count(old)}, expected 1')
        directory = work / name; directory.mkdir()
        (directory / 'cloth.c').write_text(source.replace(old, new))
        shutil.copy(v.DIR / 'cloth.h', directory / 'cloth.h')
        lib, error = v.build(directory, work, name)
        if lib is None: raise SystemExit(error)
        v.STOP['early'] = True
        try:
            families(args, configure(a.configure(lib)), small)
            result[name] = False
        except v.Caught:
            result[name] = True
        finally:
            v.STOP['early'] = False
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--cases', type=int, default=150)
    p.add_argument('--frames', type=int, default=8)
    p.add_argument('--seed', type=int, default=0x1362755)
    p.add_argument('--mutations', action='store_true')
    for flag in ('text', 'data', 'flag', 'feature', 'section3'): p.add_argument('--' + flag)
    opts = p.parse_args(argv)
    args = (pins.TEXT.read(opts.text), pins.DATA.read(opts.data), pins.FLAG.read(opts.flag), pins.FEATURE.read(opts.feature))
    v.SECTION3_INIT['bytes'] = pins.EFFECTS_INIT.read(opts.section3)
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='npc-cloak-') as tmp:
        lib, error = v.build(v.DIR, Path(tmp), 'npc')
        if lib is None: raise SystemExit(error)
        report = {'families': families(args, configure(a.configure(lib)), opts),
                  'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
                  'section3_sha256': pins.EFFECTS_INIT.sha256,
                  'constructor_sha256': hashlib.sha256(args[0][NPC_CREATE-0x401000:0x1362e1d-0x401000]).hexdigest()}
        if opts.mutations: report['mutants'] = mutations(args, opts, Path(tmp))
    report['seconds'] = round(time.monotonic() - start, 2)
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps(report))
    return int(any(f['mismatches'] or f['stopped'] for f in report['families'].values()) or
               not all(report.get('mutants', {}).values()))

if __name__ == '__main__': sys.exit(main())
