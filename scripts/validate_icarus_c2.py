#!/usr/bin/env python3
"""Icarus persistent cover and emitter ribbons against pinned client instructions.
No client processes. Engine calls record arguments; original scalar/vector helpers execute.
"""
import argparse
from collections import defaultdict
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import shutil
import struct
import sys
import subprocess
import tempfile
import actor_machine as am
import pins
import validate_particles as vp
import validate_joints as vj
import validate_object_render as vo

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'


def cover(machine, lib, cases):
    lib.mu_icarus_cover.argtypes = [C.c_void_p, C.c_int32, C.POINTER(vo.Log)]
    tally = vo.Tally('cover')
    rng = random.Random(20261028)
    for n in range(cases):
        obj = bytearray(0x3d8)
        typ = [-1, 0, 1, 2, 3, 4, 5, 6][n % 8]
        vo.put_i(obj, 0x5c, typ)
        vo.put_i(obj, 0x68, [-2, -1, 0, 4][n // 8 % 4])
        for offset in [0x158, 0x164]:
            vo.put_f(obj, offset, *[vp.rf(rng, -1000, 20000) for _ in range(3)])
        vo.put_f(obj, 0xa0, vp.rf(rng, 0.1, 8))
        calls, random_calls = [], []
        def particle(m):
            a = [m.argument(i) for i in range(8)]
            assert a[6:] == [vp.OBJECTS, 0]
            vec = lambda p: list(struct.unpack('<3I', m.uc.mem_read(p, 12)))
            calls.append([a[0]] + vec(a[1]) + vec(a[2]) + vec(a[3]) + [a[4], a[5]])
            return 0
        def rnd(m):
            random_calls.append(1)
            return 7
        regions = vp.globals_region(10) + [am.defined_region('object', vp.OBJECTS, obj)]
        stubs = {vp.MODEL_CONTAINER: lambda m: (0x29500000, 0),
                 vp.MODEL_GET: lambda m: (vp.MODEL, 4), vp.RAND: rnd, vp.CREATE_PARTICLE: particle}
        result = machine.execute(vp.VISUAL, [vp.OBJECTS], regions, stubs)
        buf = C.create_string_buffer(bytes(obj))
        log = vo.new_log()
        lib.mu_icarus_cover(buf, 0, C.byref(log))
        native = [list(e.args)[:e.count] for e in log.events[:log.count]]
        ok = vp.vc.ok(result) and buf.raw[:0x3d8] == result['regions']['object'] and calls == native
        ok = ok and len(random_calls) == 1 and not log.overflow
        tally.count('particles', len(calls))
        tally.add(ok, {'case': n, 'type': typ, 'client': calls[:1], 'native': native[:1]}, vo.stopped_reason(result))
    return tally.report()


def compare(machine, lib, name, cases, joints=False):
    module = vj if joints else vp
    class CountedReport(module.vc.Report):
        stopped = 0
        def add(self, family, equal, failure=None):
            if failure and (failure.get('stopped') or failure.get('error')): self.stopped += 1
            super().add(family, equal, failure)
    report = CountedReport()
    dict(module.FAMILIES)[name](machine, lib, random.Random(20261028), cases, report, defaultdict(int))
    t = report.families[name]
    return {'cases': t['cases'], 'equal': t['equal'], 'mismatch_count': t['cases']-t['equal'],
            'stopped': report.stopped, 'details': t}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--text', type=Path, default=pins.TEXT.default_str())
    ap.add_argument('--data', type=Path, default=pins.DATA.default_str())
    ap.add_argument('--cases', type=int, default=1200)
    ap.add_argument('--mutations', action='store_true')
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    text, data = pins.TEXT.read(args.text), pins.DATA.read(args.data)
    vp.KINDS = [(0x7f89, s) for s in range(6)]
    vj.KINDS = [(0x472, 1)]
    pm, jm = vp.PtMachine(text, data), vj.sf.FxMachine(text, data)
    report = {'bodies': {name: {'start':hex(a), 'end':hex(z), 'sha256':hashlib.sha256(text[a-am.TEXT_BASE:z-am.TEXT_BASE]).hexdigest()} for name,a,z in [('cover',0x17fba5e,0x17fbf34),('cloud-create',0x15ea60e,0x15ee692),('cloud-move',0x1662551,0x166283e),('emitter-create',0x154888f,0x15496cb),('emitter-move',0x1569cda,0x156c465)]}, 'pins': {'text': pins.TEXT.sha256, 'data': pins.DATA.sha256}, 'families': {}, 'mutants': []}
    with tempfile.TemporaryDirectory() as td:
        frozen = Path(td)
        for folder in ['objects', 'particles', 'joints', 'movement', 'record-math', 'model-codec', 'terrain']:
            shutil.copytree(ROOT/'reconstructed'/folder, frozen/folder)
        for folder in ['objects', 'particles', 'joints']:
            subprocess.run(['make', '-s', '-B', '-C', str(frozen/folder)], check=True)
        objlib = C.CDLL(str(frozen/f'objects/libobjects.{SUFFIX}'))
        plib = vp.load_library(frozen/f'particles/libclient_particles.{SUFFIX}')
        jlib = vj.load_library(frozen/f'joints/libclient_joints.{SUFFIX}')
        report['families']['cover'] = cover(pm, objlib, args.cases)
        for name in ['create', 'move', 'render']:
            report['families']['cloud_'+name] = compare(pm, plib, name, args.cases)
        for name, _ in vj.FAMILIES:
            report['families'][name] = compare(jm, jlib, name, args.cases, True)
        if args.mutations:
            specs = [('cover count', 'objects/icarus.c', 'type < 3 ? 20 : 10', 'type < 3 ? 19 : 9', 'cover'),
                     ('cover hidden guard', 'objects/icarus.c', '!= -2', '== -2', 'cover'),
                     ('cloud size', 'particles/icarus_clouds.inc', '+ 180)', '+ 170)', 'cloud_create'),
                     ('cloud owner refresh', 'particles/icarus_clouds.inc', 'p->lifetime = 50', 'p->lifetime = 40', 'cloud_move'),
                     ('cloud rotation', 'particles/particles.c', 'ordinal % 2 == 0', 'ordinal % 2 != 0', 'cloud_render'),
                     ('emitter bitmap', 'joints/joints.c', 'j->tex_type = MU_JT_BITMAP_SPIRIT; j->scale', 'j->tex_type = MU_JT_BITMAP_THUNDER; j->scale', 'joint_create'),
                     ('emitter clock parity', 'joints/icarus_joints.inc', 'index % 2 ? clock', 'index % 2 == 0 ? clock', 'joint_move'),
                     ('emitter render fade', 'joints/joints.c', 'j->lifetime < 20 ? j->lifetime : 20', 'j->lifetime < 10 ? j->lifetime : 10', 'joint_render')]
            for i, (label, file, old, new, family) in enumerate(specs):
                p = frozen/file; original = p.read_text(); assert old in original
                p.write_text(original.replace(old, new, 1))
                folder = file.split('/')[0]
                subprocess.run(['make', '-s', '-B', '-C', str(frozen/folder)], check=True)
                src = frozen/folder/({'objects':f'libobjects.{SUFFIX}', 'particles':f'libclient_particles.{SUFFIX}', 'joints':f'libclient_joints.{SUFFIX}'}[folder])
                unique = frozen/f'mutant{i}.{SUFFIX}'; shutil.copyfile(src, unique)
                if family == 'cover': r = cover(pm, C.CDLL(str(unique)), min(args.cases, 240))
                elif family.startswith('cloud_'): r = compare(pm, vp.load_library(unique), family[6:], min(args.cases, 240))
                else: r = compare(jm, vj.load_library(unique), family, min(args.cases, 240), True)
                report['mutants'].append({'name':label, 'caught':r['equal']<r['cases'] and not r['stopped'],
                                          'differences':r['cases']-r['equal'], 'cases':r['cases']})
                p.write_text(original)
    if args.output: args.output.write_text(json.dumps(report, indent=2)+'\n')
    for k, r in report['families'].items(): print(k, r['equal'], '/', r['cases'], 'stopped', r['stopped'])
    print('mutants', report['mutants'])
    return int(any(r['equal'] != r['cases'] or r['stopped'] for r in report['families'].values()) or any(not m['caught'] for m in report['mutants']))

if __name__ == '__main__': raise SystemExit(main())
