#!/usr/bin/env python3
"""CLOAK-003: armour cloth creation, steps and render streams against the pinned original.

CreateClothArmour 0x0135ea29 runs as restored code, including the class/part tests and setters. MoveCloth and
RenderCloth run the complete second-list path. Services are validate_item_cloak's, plus CreateSprite (records the
request including pointed-to position and light) and EnchantEffect (authored case colour). No live client inputs.
"""
from __future__ import annotations
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import shutil
import struct
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_item_cloak as v
import pins

ROOT = v.ROOT
ARMOUR_CREATE = 0x0135ea29

class CArmourIn(C.Structure):
    _fields_ = [('class_byte', C.c_uint8), ('enabled', C.c_uint8), ('armour_type', C.c_int16),
                ('pants_type', C.c_int16), ('wing_type', C.c_int16), ('class_index', C.c_int16),
                ('pants_level', C.c_int8), ('mesh_color', C.c_float * 3)]

# Every constructor branch, the bitmap switch's 18 cases, aliases and negative boundaries.
PARTS = [0x1d94 + i for i in range(15)] + [0x1dce, 0x1dff, 0x1e0d, 0x1e2f, 0x1e54, 0x1e8b,
          0x37a9, 0x37b9, 0x37c9, 0x37d9, 0x37e9, -1]
CASES = ([(0, 0x3760, -1), (0, 0x375f, -1)] +
         [(4, p, -1) for p in (-1, 0x3754, 0x3774, 0x3784, 0x3794)] +
         [(c, -1, p) for c, p in [(3, -1), (0x13, -1), (0x23, -1), (0x43, 0x37d3),
                                  (0x43, -1), (0x83, 0x37e3), (0x83, 0x37d3)]] +
         [(c, -1, p) for c in (8, 0x18, 0x28, 0x48, 0x88) for p in (-1, 0x37a8, 0x37b8, 0x37c8, 0x37d8, 0x37e8)] +
         [(9, -1, p) for p in PARTS] +
         [(12, -1, p) for p in (0x1de6, 0x1de7, 0x1de5, -1)] +
         [(15, p, -1) for p in (0x375f, 0x376f, 0x377f, 0x378f, 0x379f, -1)] +
         [(c, 0x3760, 0x1e54) for c in (1, 2, 5, 6, 7, 10, 11, 13, 14)])


def configure(lib):
    lib.mu_cloth_armour_create.argtypes = [C.POINTER(v.CCloth), C.POINTER(CArmourIn), C.POINTER(v.CHost)]
    lib.mu_cloth_armour_update.argtypes = [C.POINTER(v.CCloth), C.c_int, C.POINTER(CArmourIn), C.POINTER(v.CHost)]
    lib.mu_cloth_armour_cloths.argtypes = [C.POINTER(CArmourIn)]
    lib.mu_cloth_armour_draw_allowed.argtypes = [C.c_uint8, C.c_int32]
    return lib


class Client(v.ClientCloth):
    def __init__(self, args, case):
        super().__init__(args, case)
        m = self.m
        m.write(self.o + 0x3b, bytes([case['enabled']]))
        m.write(v.vr.CHAR + 0x9bc, struct.pack('<h', case['armour']))
        m.write(v.vr.CHAR + 0xdb8, struct.pack('<hb', case['pants'], case['pants_level']))
        m.write(v.vr.CHAR + 0x146, struct.pack('<h', case['class_index']))
        m.write(v.vr.ENCH, struct.pack('<3f', *case['color']))
        m.w32(v.vr.OPTS + 0x2c, case['quality'])
        def sprite(mm):
            p = struct.unpack('<3I', mm.read(mm.arg(1), 12))
            light = struct.unpack('<3I', mm.read(mm.arg(3), 12))
            self.w.calls.append(('sprite', mm.arg(0), *p, mm.arg(2), *light))
            assert [mm.arg(i) for i in (4, 5, 6, 7)] == [0, 0, 0, 4]
            return 0
        m.stub(0x01692eb7, sprite, 0)

    def create(self, st):
        self.apply(st)
        return self.m.run(ARMOUR_CREATE, [v.vr.CHAR, self.o])

    def read(self):
        count, base = self.m.read(self.o + 0x3e, 1)[0], self.m.r32(self.o + 0x48)
        return count, base != 0, [v.read_cloth(self.m, base + i * 0xe8) for i in range(count if base else 0)]

    def frame(self, st, first):
        ok, _, runs = super().frame(st, first)
        stream = []
        for c in self.w.calls:
            if c[0] in ('state', 'bind', 'sprite'):
                stream.append(c)
            elif c[0] == 'gl' and c[1] in ('glColor4f', 'glBegin', 'glTexCoord2f', 'glVertex3f', 'glEnd'):
                stream.append((c[1], *c[2]))
        return ok, stream, runs


class CSide(v.CSide):
    def apply(self, st):
        super().apply(st)
        c = self.case
        self.armour_in = CArmourIn(c['class'], c['enabled'], c['armour'], c['pants'], c['wing'],
                                   c['class_index'], c['pants_level'], (C.c_float * 3)(*c['color']))
        self.g.quality = c['quality']

    def create(self, st):
        self.apply(st)
        self.count = self.lib.mu_cloth_armour_create(self.cloths, C.byref(self.armour_in), C.byref(self.host))
        return self.count

    def frame(self, st, first):
        self.apply(st)
        self.stream.clear()
        self.move_cloth()
        if not self.count:
            again = self.create(st)
        else:
            again = self.lib.mu_cloth_armour_update(self.cloths, self.count, C.byref(self.armour_in), C.byref(self.host))
        if again:
            self.move_cloth()
        c = self.case
        if (not self.lib.mu_cloth_draw_allowed(c['class'], c['subtype'], 1, 1, c['class_index']) or
                not self.lib.mu_cloth_armour_draw_allowed(c['class'], c['subtype'])):
            return list(self.stream)
        for cloth in self.cloths[:self.count]:
            if cloth.owner:
                self.lib.mu_cloth_render(C.byref(cloth), C.byref(self.host), C.byref(self.g), None, C.byref(self.sink))
        return list(self.stream)


def families(args, lib, opts):
    rng = random.Random(opts.seed)
    fam = {k: v.new_family() for k in ('create', 'step', 'render', 'draw_gate')}
    for i in range(opts.cases):
        cls, armour, pants = CASES[i % len(CASES)]
        case = v.random_case(rng, -1, i)
        case.update({'class': cls, 'armour': armour, 'pants': pants, 'pants_level': rng.choice((0, 6, 7, 8, 9, 11, 13, 15)),
                     'class_index': -1, 'enabled': 1, 'quality': rng.choice((0, 1, 2, 3, 4, 5)),
                     'color': [v.u2f(v.f2u(rng.random())) for _ in range(3)], 'subtype': 0, 'arg4': 0})
        # Periodic explicit disabled/bone/model cases, plus all valid constructor branches in the first sweep.
        if i >= len(CASES) and i % 11 == 0:
            case['enabled'] = 0
        if i < len(CASES):
            case.update(bones=1, bone_count=60, has_model=1, pants_level=13, quality=5)
        client, side = Client(args, case), CSide(lib, case)
        fr = random.Random(case['seed'])
        base = {'time0': case['time0'], 'steps0': case['steps0'], 'origin0': case['origin0']}
        bones = case['bones0']
        st = v.frame_state(fr, 0, base); st['bones'] = bones
        result = client.create(st); side.create(st)
        count, ptr, original = client.read()
        cv = [v.c_cloth_view(c) for c in side.cloths[:side.count]]
        diff = v.first_difference(original, cv)
        if not result['ok']: fam['create']['stopped'] += 1
        v.note(fam['create'], result['ok'] and count == side.count and ptr == (side.count > 0) and not diff,
               {'case': [hex(cls), hex(armour), hex(pants)], 'diff': diff, 'run': result})
        client, side = Client(args, case), CSide(lib, case)
        # Fresh twins compare RenderCloth's creation frame, then its existing-list branch.
        for frame in range(opts.frames):
            st = v.frame_state(fr, frame, base)
            if frame: bones = v.perturb(fr, bones, 0.5)
            st['bones'] = bones
            ok, stream, runs = client.frame(st, False)
            native = side.frame(st, False)
            count, ptr, original = client.read()
            cv = [v.c_cloth_view(c) for c in side.cloths[:side.count]]
            diff = v.first_difference(original, cv)
            if not ok: fam['step']['stopped'] += 1; fam['render']['stopped'] += 1
            v.note(fam['step'], ok and count == side.count and not diff and client.state['seed'] == side.g.rand_seed,
                   {'case': i, 'frame': frame, 'diff': diff, 'runs': runs if not ok else None,
                    'seed': [client.state['seed'], side.g.rand_seed]})
            a, b = v.stream_bits(stream), v.stream_bits(native)
            v.note(fam['render'], ok and a == b, {'case': i, 'frame': frame, 'len': [len(a), len(b)],
                   'first': next(([j, a[j], b[j]] for j in range(min(len(a), len(b))) if a[j] != b[j]), None)})
    # All armour visibility sub-types plus clear values, across every base class.
    world = v.vr.World(*args)
    for cls in range(16):
        for sub in (0, 0x421, 0x422, 0x423, 0x424, 0x425, 0x429, 0x3ed, 0x3e9, 0x431, 0x432, 0xa5e,
                    0x541, 0x552, *range(0x5ba, 0x5c0), 0x5c4, 0x5c5, 0x5c6):
            r = v.vr.character_record(cls=cls, action=1)
            struct.pack_into('<i', r, 0x32b4, sub)
            world.m.write(v.vr.CHAR, r)
            run = world.m.run(0x01362edc, [v.vr.CHAR])
            actual = world.m.uc.reg_read(world.m.x86.UC_X86_REG_EAX) & 0xff
            v.note(fam['draw_gate'], run['ok'] and actual == lib.mu_cloth_armour_draw_allowed(cls, sub),
                   {'class': cls, 'subtype': sub, 'run': run})
    return fam


MUTANTS = {
    'armour_gate': ('case 0: return in->armour_type == 0x3760;', 'case 0: return in->armour_type == 0x3761;'),
    'dl_bone': ('h, 19, 0.0f, 12.0f, 0.0f, 10, 10, 75.0f, 120.0f, 0x7949',
                'h, 18, 0.0f, 12.0f, 0.0f, 10, 10, 75.0f, 120.0f, 0x7949'),
    'flare_type': ('i ? 0x80002205u : 0xc0000205u', 'i ? 0x80002205u : 0x80000205u'),
    'energy_wind': ('i ? 40 : 50', 'i ? 40 : 51'),
    'skin_bitmap': ('case 0x3774: return 0x791d;', 'case 0x3774: return 0x791e;'),
    'slayer_angles': ('{0.0f, 0.0f, -60.0f}', '{0.0f, 0.0f, 60.0f}'),
    'slayer_bitmap': ('0x792d,0x7926,0x7927', '0x792d,0x7925,0x7927'),
    'halves_alpha': ('out[i].alpha = 0.3f;', 'out[i].alpha = 0.4f;'),
    'halves_uv': ('out[i].uv_offset[0] = i ? 1.0f : 0.0f;', 'out[i].uv_offset[0] = 0.0f;'),
    'wing_suppresses': ('in->wing_type == -1 && in->class_index == -1', 'in->wing_type != -1 && in->class_index == -1'),
    'flare_brightness': ('* bright / 5.0f;', '* bright / 6.0f;'),
    'flare_stride': ('c->vertices[index++].position', 'c->vertices[(index++ % c->rows) * c->columns + x].position'),
    'mesh_quality': ('g->quality <= 0', 'g->quality <= 5'),
    'mesh_level': ('{13, 11, 9, 7}', '{14, 12, 10, 8}'),
    'mesh_uv': ('px + py + slide * 3.0f', 'px + py + slide * 2.0f'),
    'glow2_level': ('c->glow2_texture == -1 || c->mesh_level < 9', 'c->glow2_texture == -1 || c->mesh_level < 14'),
    'glow2_pulse': ('glow_wave(-c->glow2[0], g->time)', 'glow_wave(c->glow2[0], g->time)'),
    'release': ('if (!keep && out[0].owner)', 'if (keep && out[0].owner)'),
    'armour_draw_gate': ('(class_byte & 0xf) != 4', '(class_byte & 0xf) != 3'),
}

def mutations(args, opts, work):
    source = (v.DIR / 'cloth.c').read_text()
    result = {}
    small = argparse.Namespace(**vars(opts))
    small.cases, small.frames = len(CASES), 2
    (work / 'record-math').mkdir(exist_ok=True)
    shutil.copy(ROOT / 'reconstructed/record-math/record_math.h', work / 'record-math/record_math.h')
    for name, (old, new) in MUTANTS.items():
        if source.count(old) != 1:
            raise SystemExit(f'{name}: anchor count {source.count(old)}, expected 1')
        directory = work / name
        directory.mkdir()
        (directory / 'cloth.c').write_text(source.replace(old, new))
        shutil.copy(v.DIR / 'cloth.h', directory / 'cloth.h')
        lib, error = v.build(directory, work, name)
        if lib is None: raise SystemExit(error)
        v.STOP['early'] = True
        try:
            families(args, configure(lib), small)
            result[name] = False
        except v.Caught:
            result[name] = True
        finally:
            v.STOP['early'] = False
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--cases', type=int, default=240)
    p.add_argument('--frames', type=int, default=8)
    p.add_argument('--seed', type=int, default=0x135ea29)
    p.add_argument('--mutations', action='store_true')
    for flag in ('text', 'data', 'flag', 'feature', 'section3'): p.add_argument('--' + flag)
    opts = p.parse_args(argv)
    args = (pins.TEXT.read(opts.text), pins.DATA.read(opts.data), pins.FLAG.read(opts.flag), pins.FEATURE.read(opts.feature))
    v.SECTION3_INIT['bytes'] = pins.EFFECTS_INIT.read(opts.section3)
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='armour-cloak-') as tmp:
        lib, error = v.build(v.DIR, Path(tmp), 'armour')
        if lib is None: raise SystemExit(error)
        report = {'families': families(args, configure(lib), opts),
                  'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256,
                  'section3_sha256': pins.EFFECTS_INIT.sha256}
        if opts.mutations:
            report['mutants'] = mutations(args, opts, Path(tmp))
    report['seconds'] = round(time.monotonic() - start, 2)
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps(report))
    return int(any(f['mismatches'] or f['stopped'] for f in report['families'].values()) or
               not all(report.get('mutants', {}).values()))

if __name__ == '__main__':
    sys.exit(main())
