#!/usr/bin/env python3
"""RENDER-WORLDS-E: compiled world C against the pinned original instructions."""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import shutil
import struct
import subprocess
import tempfile
import actor_machine as am
import pins
import validate_object_render as v
import validate_environment as ve
import validate_particles as vp
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
F3 = C.c_float * 3


def boid(machine, lib, cases, typ):
    tally = v.Tally(hex(typ))
    g = random.Random(20261027)
    lib.boid.argtypes = [C.c_void_p, C.c_float, C.POINTER(C.c_uint32)]
    for n in range(cases):
        o = v.move_object(g, 0, 'full')
        v.put_i(o, 0x5c, typ)
        v.put_i(o, 0x60, n % 4)
        o[0x29] = (n // 4) % 4
        v.put_f(o, 0xd0, [0, 23, 24, 25][(n // 16) % 4])
        v.put_f(o, 0x170, g.uniform(-10, 10), g.uniform(-10, 10), n % 3)
        time = v.f32(g.uniform(-20000, 3e6))
        seed = g.getrandbits(32)
        # Force rare random branches as well as ordinary random cases.
        if n % 3 == 0:
            while v.MsvcRand(seed)() % (120 if typ == 0x1a3 else 500):
                seed = (seed + 1) & 0xffffffff
        rnd = v.MsvcRand(seed)
        regions = v.global_regions(51, 6, [am.defined_region('object', v.OBJECTS, o),
            am.defined_region('time', v.TIME, v.pack_f(time))])
        result = v.run(machine, 0xca33c3 if typ == 0x1a3 else 0xca3ce1, [v.OBJECTS], regions,
                       {0x1989721: lambda m: rnd()})
        stop = v.stopped_reason(result)
        if stop:
            tally.add(False, {'case': n}, stop)
            continue
        out = C.create_string_buffer(bytes(o), len(o))
        cr = C.c_uint32(seed)
        lib.boid(out, time, C.byref(cr))
        diffs = [hex(k) for k in range(len(o)) if out.raw[k] != result['regions']['object'][k]]
        tally.add(not diffs and cr.value == rnd.seed, {'case': n, 'offsets': diffs[:12]})
    return tally.report()


def timer(machine, lib, cases, kind):
    tally = v.Tally(kind)
    # Bind only the captured timeGetTime import to an executable recording stub.
    machine.uc.mem_write(0x1a7c49c, struct.pack('<I', am.TEXT_BASE))
    g = random.Random(20261028)
    for name in ['arm', 'step', 'emit']:
        getattr(lib, 'mu_raklion_event_'+name).argtypes = [C.c_void_p] if name == 'arm' else (
            [C.c_void_p] + ([C.c_uint32] if name == 'step' else []) +
            [F3, F3, C.POINTER(C.c_float), v.RAND_FN, C.c_void_p, C.POINTER(v.Log)])
    for n in range(cases):
        s = bytearray(g.randbytes(0x28))
        s[0x20] = n % 6
        s[0x23] = (n // 6) % 2
        start = g.choice([0, 1, 0xfffffff0, 10000])
        duration = g.choice([0, 500, 1000, 0xffffffff])
        now = (start + g.choice([0, 1, duration, duration+1])) & 0xffffffff
        struct.pack_into('<II', s, 0x14, start, duration)
        seed = g.getrandbits(32); rnd = v.MsvcRand(seed); cr = v.MsvcRand(seed)
        hero = [v.f32(g.uniform(-1000, 20000)) for _ in range(3)]
        angle = [v.f32(g.uniform(-360, 360)) for _ in range(3)]
        quake = v.f32(g.uniform(-2, 2)); calls = []
        def event(m, call):
            a = [m.argument(k) for k in range(14 if call == 0x13c0eaa else 8)]
            assert a[5:] == [0, 0xffffffff, 0, 0, 0, a[10], 0xffffffff, 0, 0] if call == 0x13c0eaa else a[6:] == [0, 0]
            calls.append([call, -1, [a[0]] + list(v.read_vec(m,a[1])) + list(v.read_vec(m,a[2])) +
                          list(v.read_vec(m,a[3])) + [a[4], a[10] if call == 0x13c0eaa else a[5]]])
            return 0
        regions = v.global_regions(57, 6, [am.defined_region('state', v.FAKE, s),
            am.defined_region('hero-ptr', v.HERO_PTR, struct.pack('<I', v.HERO)),
            am.defined_region('hero', v.HERO+0x33ac, v.pack_f(*hero)+v.pack_f(*angle)),
            am.defined_region('quake', 0xbdb588c, v.pack_f(quake))])
        result = v.run(machine, {'arm':0xea176f,'step':0xea17c0,'emit':0xea186c}[kind], [], regions,
            {0x1989721:lambda m:rnd(),am.TEXT_BASE:lambda m:now,
             0x13c0eaa:lambda m:event(m,0x13c0eaa),0x168fafd:lambda m:event(m,0x168fafd)}, ecx=v.FAKE)
        stop = v.stopped_reason(result)
        if stop: tally.add(False, {'case':n}, stop); continue
        buf = C.create_string_buffer(bytes(s),len(s)); q = C.c_float(quake); log = v.new_log()
        if kind == 'arm': lib.mu_raklion_event_arm(buf)
        else:
            args = [buf] + ([now] if kind == 'step' else [])
            getattr(lib,'mu_raklion_event_'+kind)(*args,F3(*hero),F3(*angle),C.byref(q),v.RAND_FN(lambda _:cr()),None,C.byref(log))
        native = [[e.call,e.object,list(e.args)[:e.count]] for e in log.events[:log.count]]
        tally.count('events',len(calls))
        tally.add(buf.raw == result['regions']['state'] and v.pack_f(q.value) == result['regions']['quake']
                  and rnd.seed == cr.seed and native == calls and not log.overflow,
                  {'case':n,'state':buf.raw.hex() if buf.raw != result['regions']['state'] else 'equal',
                   'calls':calls[:2], 'native':native[:2]})
    return tally.report()


def build(root, out):
    env = root / 'reconstructed/environment'
    wrapper = root / 'boid.c'
    wrapper.write_text('''#include "reconstructed/environment/env_internal.h"
void boid(uint8_t *image, float time, uint32_t *seed) {
 mu_env e; mu_env_init(&e,*seed,0); mu_env_inputs in={0}; in.world=51;in.world_time=time;
 mu_env_object o;mu_env_object_load(&o,image);env_elbeland_move(&e,&in,&o);
 mu_env_object_store(&o,image);*seed=e.rand_state;
}
''')
    subprocess.run(['clang', '-std=c11', '-O2', '-shared', '-fPIC', '-ffp-contract=off',
        str(wrapper), str(env/'env_core.c'), str(env/'env_elbeland.c'), str(root/'reconstructed/objects/raklion_event.c'),
        str(root/'reconstructed/objects/objects.c'), str(root/'reconstructed/model-codec/model_codec.c'), '-lm', '-o', str(out)], check=True)
    return C.CDLL(str(out))


def sessions(machine, lib, cases=40):
    g = random.Random(20261029)
    ve.BOID_WORLDS = list(set(ve.BOID_WORLDS + [51]))
    results = []
    for n in range(cases):
        case = ve.make_case(g, n, lib, [51], fuzz=False)
        pool = bytearray(case['boids'])
        for slot, typ in [(0, 0x1a4), (1, 0x1a3)]:
            o = bytearray(ve.random_object(g, lib, 51, case['hero']))
            o[0] = 1; o[0x0a] = int(slot == 0); o[0x29] = 0
            v.put_i(o, 0x5c, typ)
            v.put_f(o, 0x158, *case['hero'])
            v.put_f(o, 0xa0, 1.0);v.put_f(o, 0xbc, 0.0)
            v.put_f(o, 0x170, 0.1, 0, 0)
            pool[slot*ve.OBJ:(slot+1)*ve.OBJ] = o
        case['boids'] = bytes(pool)
        case['missing_models'] = [0x1a3] if n % 10 == 0 else []
        if n % 8 == 0: case['teleport'] = 5
        results.append(ve.run_case(machine, lib, case, 20, 2, random.Random(case['seed'])))
    return {'cases': cases, 'equal': sum(not r['mismatch'] and not r['stopped'] for r in results),
        'mismatch_count': sum(bool(r['mismatch']) for r in results), 'stopped': sum(bool(r['stopped']) for r in results),
        'steps': sum(r['steps'] for r in results), 'host_calls': sum(r['events'] for r in results),
        'rand_calls': sum(r['rand_calls'] for r in results),
        'examples': [r for r in results if r['mismatch'] or r['stopped']][:4]}


def cloud(machine, lib, cases, name):
    vp.KINDS = [(0x7f89,18)]
    original = vp.random_particle
    def particle(g, kind):
        p = original(g,kind);p.owner=0;p.tex_type=0x7f21
        p.lifetime=g.choice([160,91,90,30,29,1])
        return p
    vp.random_particle = particle
    try:
        r = vp.vc.Report()
        getattr(vp,'family_'+name)(machine,lib,random.Random(20261030),cases,r,defaultdict(int))
        t = r.families[name]
        return {'cases':t['cases'],'equal':t['equal'],'mismatch_count':t['cases']-t['equal'],
                'stopped':sum(bool(e.get('stopped') or e.get('error')) for e in t['first_failures']),
                'examples':t['first_failures']}
    finally:
        vp.random_particle = original


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--text', type=Path, default=pins.TEXT.default_str())
    ap.add_argument('--data', type=Path, default=pins.DATA.default_str())
    ap.add_argument('--cases', type=int, default=600)
    ap.add_argument('--mutations', action='store_true')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    text = am.load_pinned(a.text, am.TEXT_BYTES, am.TEXT_SHA256, 'text')
    data = am.load_pinned(a.data, am.DATA_BYTES, am.DATA_SHA256, 'data')
    m = am.ActorMachine(text, data)
    report = {'pins': {'text': am.TEXT_SHA256, 'data': am.DATA_SHA256}, 'families': {}, 'mutants': []}
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for folder in ['environment','objects','model-codec','record-math','particles']:
            shutil.copytree(ROOT/'reconstructed'/folder, root/'reconstructed'/folder)
        lib = build(root, root/'env.dylib')
        for typ in [0x1a3, 0x1a4]:
            report['families'][hex(typ)] = boid(m, lib, a.cases, typ)
        for kind in ['arm','step','emit']:
            report['families'][kind] = timer(m, lib, a.cases, kind)
        if a.mutations:
            p = root/'reconstructed/environment/env_elbeland.c'
            original = p.read_text()
            for n, (old, new, typ) in enumerate([('o->frame == 24.0f', 'o->frame == 23.0f', 0x1a3),
                ('yaw + 270.0f', 'yaw + 260.0f', 0x1a3), ('% 500', '% 499', 0x1a4),
                ('* 2.0f + o->position[0]', '* 3.0f + o->position[0]', 0x1a4)]):
                assert old in original
                p.write_text(original.replace(old, new))
                r = boid(m, build(root, root/f'mut{n}.dylib'), min(a.cases, 300), typ)
                report['mutants'].append({'name': old, 'cases': r['cases'], 'differences': r['mismatch_count'],
                    'caught': r['mismatch_count'] > 0 and not r['stopped']})
            p.write_text(original)
            p = root/'reconstructed/objects/raklion_event.c'; original = p.read_text()
            for n, (old, new, kind) in enumerate([
                ('? 500 : 1000', '? 400 : 1000', 'arm'),
                ('now - start > duration', 'now - start >= duration', 'step'),
                ('if (!s[0x23]) return;', 'if (s[0x23]) return;', 'step'),
                ('0x512, p', '0x513, p', 'emit'),
                ('% 2 - 2', '% 2 - 1', 'emit')]):
                assert old in original; p.write_text(original.replace(old, new))
                r = timer(m, build(root, root/f'timer-mut{n}.dylib'), min(a.cases, 300), kind)
                report['mutants'].append({'name': old, 'cases': r['cases'], 'differences': r['mismatch_count'],
                    'caught': r['mismatch_count'] > 0 and not r['stopped']})
            p.write_text(original)
        pm = vp.PtMachine(text,data)
        def plib():
            subprocess.run(['make','-s','-B','-C',str(root/'reconstructed/particles')],check=True)
            return None
        # Unique dylib paths keep dlopen from returning a previously loaded mutant.
        def particle_library(name):
            plib()
            out=root/(name+'.dylib')
            shutil.copyfile(root/'reconstructed/particles/libclient_particles.dylib',out)
            return vp.load_library(out)
        libp = particle_library('cloud')
        for name in ['create','move','render']:
            report['families']['cloud_'+name] = cloud(pm,libp,a.cases,name)
        if a.mutations:
            p = root/'reconstructed/particles/elbeland.c';original=p.read_text()
            for n,(old,new,name) in enumerate([
                ('p->lifetime = 160','p->lifetime = 150','create'),
                ('p->lifetime > 90','p->lifetime > 91','move'),
                ('time * 0.02f','time * 0.03f','render')]):
                assert old in original;p.write_text(original.replace(old,new))
                r=cloud(pm,particle_library('cloud-mut'+str(n)),min(a.cases,300),name)
                report['mutants'].append({'name':old,'cases':r['cases'],'differences':r['mismatch_count'],
                    'caught':r['mismatch_count']>0 and not r['stopped']})
            p.write_text(original)
        ve.ROOT = root
        elib = ve.Library(ve.build_library(0, root/'sessions.dylib'))
        report['families']['elbeland_sessions'] = sessions(ve.EnvMachine(text, data), elib)
    report['bodies'] = {name: {'start':hex(x), 'end':hex(y),
        'sha256':hashlib.sha256(text[x-am.TEXT_BASE:y-am.TEXT_BASE]).hexdigest()}
        for name,x,y in [('circle',0xca33c3,0xca3ce1),('typhoon',0xca3ce1,0xca3e2f),
            ('arm',0xea176f,0xea17c0),('step',0xea17c0,0xea186c),('emit',0xea186c,0xea233c),
            ('timer',0xc9b482,0xc9b508),('cloud_create',0x15ec345,0x15ec6a4),
            ('cloud_move',0x1660886,0x1660d51),('cloud_render',0x15995aa,0x1599629)]}
    if a.output: a.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return int(any(r['mismatch_count'] or r['stopped'] for r in report['families'].values()) or
               any(not r['caught'] for r in report['mutants']))

if __name__ == '__main__':
    raise SystemExit(main())
