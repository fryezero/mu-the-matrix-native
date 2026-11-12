#!/usr/bin/env python3
"""EFFECTS-026: five later item particle consumers, original instructions and native raster."""
import argparse
from collections import defaultdict
import ctypes as C
import json
from pathlib import Path
import random
import subprocess
import tempfile
import time

import pins
import actor_machine as am
import validate_particles as pt
import validate_render_effects11 as re11
import validate_render_effects23 as re23
import validate_render_effects24 as re24
import validate_render_effects25 as re25

ROOT = Path(__file__).resolve().parents[1]
KINDS = [(0x8500, 2), (0x810b, 8), (0x810a, 12), (0x81cf, 1), (0x8569, 0)]
BITMAPS = [(0x01827a23, 0x8500, 'Skill\\wing_hetachi2.jpg'),
           (0x01825e21, 0x8569, 'Effect\\Damage_ring_2.jpg')]
CENSUS_PROGRAMS = re25.CENSUS_PROGRAMS | {0xb29,0xb52,0xf1e,0x174a,0x2301,0x2302,
    0x23a8,0x23a9,0x23ed,0x23ee,0x23fe,0x23ff,0x2403,0x2404}


def particle_family(text, data, lib, name, cases, report):
    if name == 'render':
        render_family(pt.PtMachine(text,data),lib,random.Random('effects26-render'),
                      cases*len(KINDS),report,defaultdict(int))
        report.families['particle_render'] = report.families.pop('render')
        report.coverage['particle_render'] = report.coverage.pop('render',{})
        return
    saved = re25.KINDS
    try:
        re25.KINDS = KINDS
        re25.particle_family(text,data,lib,name,cases,report)
    finally:
        re25.KINDS = saved


def request_census(lib):
    saved = re25.CENSUS_PROGRAMS
    try:
        re25.CENSUS_PROGRAMS = CENSUS_PROGRAMS
        return re25.request_census(lib)
    finally:
        re25.CENSUS_PROGRAMS = saved


def render_family(m, lib, rng, cases, report, negatives, owned_points=True):
    for n in range(cases):
        kind = KINDS[n % len(KINDS)]
        p = pt.random_particle(rng, kind)
        p.live = 1
        p.owner = -1
        mode = rng.choice([0, 0, 1, 2, 3])
        bm = pt.Bitmap(pt.f32(rng.choice([64.0, 128.0, 256.0, 32.0])), pt.f32(rng.choice([64.0, 128.0, 32.0])),
                    rng.choice([3, 3, 4]))
        if rng.random() < 0.3:
            p.position[2] = pt.f32(rng.choice([300.0, 350.0, 299.99997, 350.00003, 1e9]))
        case = pt.Case(rng)
        owner_regions = []
        point = None
        if owned_points and kind == (0x8569, 0):
            p.owner = rng.choice([-1, 0, 0, 0])
            p.arg8 = n % 4
            points = [pt.rf(rng, -100, 500) for _ in range(12)]
            case.owners = [[0.0, 0.0, 0.0]]
            owner_regions = case.owner_regions()
            owner_regions[0].define(pt.OBJECTS + 0x1f4, pt.struct.pack('<12f', *points))
            point = pt.F3(*points[3*p.arg8:3*p.arg8+3]) if p.owner >= 0 else None
        world_time = pt.f32(rng.uniform(0, 1e6))
        record = pt.particle_region(lib, p)
        bmr = pt.am.Region('bitmap', pt.BITMAP_RECORD, pt.am.poison(0x220, 0x44), bytes(0x220), writable=False)
        bmr.define(pt.BITMAP_RECORD+0x204, pt.struct.pack('<ff', bm.width, bm.height))
        bmr.define(pt.BITMAP_RECORD+0x214, pt.struct.pack('<b', bm.components))
        calls = []

        def bitmap_get(mm):
            calls.append(('bitmap', mm.argument(0)))
            return pt.BITMAP_RECORD, 4

        def wrapper(address, args):
            def stub(mm):
                calls.append(('state', address, mm.argument(0) if args else 0))
                return 0
            return stub

        def sprite(mm):
            a = [mm.argument(i) for i in range(11)]
            calls.append(('sprite', a[0], mm.floats(a[1], 3), pt.from_bits(a[2]), pt.from_bits(a[3]), mm.floats(a[4], 3),
                          pt.from_bits(a[5]), pt.from_bits(a[6]), pt.from_bits(a[7]), pt.from_bits(a[8]), pt.from_bits(a[9]), a[10]))
            return 0
        stubs = pt.shared_stubs(case, m, {0x015ae351: pt.jump_stub(0x015ae363), 0x01591282: pt.jump_stub(0x015ae363),
                                         pt.BITMAP_GET: bitmap_get, pt.RENDER_SPRITE: sprite,
                                         pt.STATE_ADD: wrapper(pt.STATE_ADD, 0), pt.STATE_ALPHA: wrapper(pt.STATE_ALPHA, 1),
                                         pt.STATE_SUB: wrapper(pt.STATE_SUB, 0), pt.STATE_6B7: wrapper(pt.STATE_6B7, 0),
                                         pt.STATE_6DA: wrapper(pt.STATE_6DA, 0), pt.STATE_BLEND: wrapper(pt.STATE_BLEND, 0)})
        r = m.execute(0x015912e9, [0x5500 | mode], [record, bmr] + owner_regions + pt.globals_region(world_time=world_time), stubs, ecx=pt.POOL, frame=pt.mid_frame(pt.RENDER_FRAME, {-0x60: n}),
                      cleanup=4)
        rc = pt.RenderCall()
        if owned_points and kind == (0x8569, 0) and not (
                (mode == 1 and p.position[2] > 350.0) or (mode == 2 and 300.0 >= p.position[2])):
            # The split-pass height test precedes RenderParticles' owner-relative position write.
            lib.mu_pt_item_later_follow(C.byref(p), point)
            # mu_pt_render_record repeats the filter, so draw the already selected record in mode 0.
            mode_for_c = 0
        else:
            mode_for_c = mode
        drawn = lib.mu_pt_render_record(C.byref(p), C.byref(bm), mode_for_c, world_time, n, C.byref(rc))
        mine = []
        if drawn == 1:
            mine.append(('bitmap', p.tex_type))
            for k in range(rc.state_count):
                if rc.state[k] == pt.STATE_SUB:
                    continue
                mine.append(('state', rc.state[k], rc.state_arg[k]))
            for k in range(rc.state_count):
                if rc.state[k] == pt.STATE_SUB:
                    mine.append(('state', rc.state[k], rc.state_arg[k]))
            sp = rc.sprite
            if rc.sprites:   # RENDER-EFFECTS-006: a kind may set its blend state and draw nothing
                mine.append(('sprite', sp.bitmap, list(sp.position), sp.width, sp.height, list(sp.light),
                             sp.rotation, sp.u, sp.v, sp.uw, sp.vh, sp.axes))
        mismatch = None
        if pt.vc.ok(r) and (len(calls) != len(mine) or not all(pt.vc._same_call(a, b) for a, b in zip(calls, mine))):
            mismatch = ('calls', calls, mine)
        if owned_points and pt.vc.ok(r):
            raw, mask = pt.particle_bytes(lib, p)
            mismatch = mismatch or pt.compare_masked(raw, r['regions']['particle'], record.defined, mask, pt.PARTICLE_FLOATS)
        equal = drawn != 2 and pt.vc.ok(r) and mismatch is None
        report.add('render', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mode': mode, 'mismatch': mismatch,
                                     'stopped': r['stopped'], 'error': r['error'], 'checks': r['checks']})
        report.cover('render', f'{kind[0]:#x}/{kind[1]}' + ('' if drawn == 1 else ' skipped'))


def caller_points(cases, report, lib=None):
    from item_body_machine import ResetWorld
    pre, quality = re25.pre, re25.quality
    lib = lib or C.CDLL(str(re25.rc.LIBRARY))
    plib = pre.ownerfx.particles_library()
    wa = tuple(p.read() for p in (pins.TEXT,pins.DATA,pins.FLAG,pins.FEATURE))
    reset = ResetWorld(wa,pre.ItemWorld)
    names,consts = pre.program_names()
    rng = random.Random('effects26-four-points')
    for n in range(cases):
        t = (0x23a8,0x23a9)[n % 2]
        case = dict(list(quality.state_cases(t))[n % 292][1])
        o = pre.item_setup(rng,t,3,names[t],consts[t])
        o['records'] = True
        o['point_words'] = 12
        for i,name in enumerate(names[t]):o['names'][i]=name
        o['attached'] = n % 2 == 1
        o['owner_matrices'] = [pre.f32(-x) for x in o['matrices']]
        o['hidden'] = n % 7 == 6
        o['frame'] = [0,1,24,25,26,49,50,51,0xffffffff][n % 9]
        case['frame'] = o['frame']
        expected = pre.original(wa,reset,case,o)
        actual = pre.run_c(lib,plib,case,o,expected[3])
        ok,refused = pre.same(expected,actual)
        report.add('caller_points',ok and o['client_points']==o['native_points'],
                   dict(case=n,type=hex(t),requests_equal=ok,refused=refused,
                        points_equal=o['client_points']==o['native_points']))


def configure(lib):
    lib.mu_pt_item_later_follow.argtypes = [C.POINTER(pt.Particle), C.POINTER(C.c_float)]
    lib.mu_pt_item_later_follow.restype = C.c_int
    return lib


def build_host(directory, particles=None):
    # Same real-native link as EFFECTS-024, with this lane's host.
    native = ROOT/'native'
    directory = Path(directory)
    source = (native/'tests/effects26_host.c').read_text().replace(
        '#include "../core/mu_particles.c"', f'#include "{particles or native/"core/mu_particles.c"}"').replace(
        '#include "../core/mu_png.h"', f'#include "{native/"core/mu_png.h"}"').replace(
        '#include "../core/mu_renderchar.h"', f'#include "{native/"core/mu_renderchar.h"}"')
    (directory/'host.c').write_text(source)
    obj, host = directory/'host.o', directory/'host'
    subprocess.run(['clang','-std=c11','-O1','-ffp-contract=off','-I',str(native/'build/gen'),
                    '-I',str(native/'session'),'-iquote',str(native/'core'),'-c',str(directory/'host.c'),
                    '-o',str(obj)],check=True,capture_output=True)
    subprocess.run(['clang','-std=c11','-c',str(native/'core/mu_png.c'),'-o',str(directory/'png.o')],check=True,capture_output=True)
    command = ['clang++',str(obj),str(directory/'png.o'),str(native/'build/libmunative.a'),
               str(native/'build/libmusession_world.a'),'-lm','-o',str(host)]
    import sys
    if sys.platform == 'darwin':
        command += ['-L/opt/homebrew/opt/cryptopp/lib','-lcryptopp','-L/opt/homebrew/opt/jpeg-turbo/lib','-ljpeg',
                    '-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation']
    else:
        command += ['-lcryptopp','-ljpeg']
    subprocess.run(command,check=True,capture_output=True)
    return host


def bitmap_fixture(directory):
    from PIL import Image
    import io
    root = Path(directory)/'game'
    files = ['Skill/wing_hetachi2','Effect/pin_star02_red','Effect/pin_star03',
             'Effect/magic_ground12','Effect/Damage_ring_2']
    for n,name in enumerate(files):
        path = root/'Data'/(name+'.OZJ')
        path.parent.mkdir(parents=True,exist_ok=True)
        buf=io.BytesIO();Image.new('RGB',(32,32),((n+1)*40,)*3).save(buf,format='JPEG',quality=100)
        path.write_bytes(bytes(24)+buf.getvalue())
    return root


def native_check(host, root, report, renders=None):
    run=subprocess.run([str(host),str(root)]+([str(renders)] if renders else []),capture_output=True,text=True)
    rows=[json.loads(s) for s in run.stdout.splitlines() if s.startswith('{')]
    for n,kind in enumerate(KINDS):
        report.add('native',run.returncode == 0 and len(rows)==5 and rows[n]['kind']==kind[0]
                   and rows[n]['fragments']>0,dict(kind=kind,exit=run.returncode,stderr=run.stderr[-1000:]))


def bitmap_checks(text,data,report):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md=Cs(CS_ARCH_X86,CS_MODE_32)
    for call,bitmap,path in BITMAPS:
        ins=list(md.disasm(text[call-24-am.TEXT_BASE:call+5-am.TEXT_BASE],call-24))
        pushes=[int(i.op_str,0) for i in ins if i.mnemonic=='push']
        actual=data[pushes[-1]-am.DATA_BASE:].split(b'\0')[0]
        report.add('bitmaps',pushes[:5]==[0,1,0x2900,0x2601,bitmap] and actual==path.encode()
                   and ins[-1].op_str=='0x185baac',dict(bitmap=hex(bitmap),call=hex(call)))


PT_MUTANTS = [
    ('admit_8500','subtype == 2)','subtype == 3)','create'),
    ('admit_810b','subtype == 8)','subtype == 9)','create'),
    ('admit_810a','subtype == 12)','subtype == 13)','create'),
    ('admit_81cf','subtype == 1)','subtype == 2)','create'),
    ('admit_8569','(type == 0x8569 && subtype == 0)','(type == 0x8569 && subtype == 1)','create'),
    ('8500_life','mu_pt_rand(h) % 11 + 20','mu_pt_rand(h) % 11 + 21','create'),
    ('8500_velocity','rand_range(h, -2.0f, 0.8f, 100)','rand_range(h, -2.0f, 0.9f, 100)','create'),
    ('8500_spin','p->rotation + p->field_84','p->rotation + p->field_80','move'),
    ('8500_drift','rand_range(h, -0.2f, 0.1f, 100)','rand_range(h, -0.2f, 0.2f, 100)','move'),
    ('810b_life','p->lifetime = 25;','p->lifetime = 24;','create'),
    ('810b_half','scale / (float)(p->lifetime / 2)','scale / (float)p->lifetime','create'),
    ('810b_velocity','rand_range(h, -1.2f, 1.2f, 100)','rand_range(h, -1.2f, 1.2f, 10)','create'),
    ('half_shrink','p->lifetime < p->initial_lifetime / 2','p->lifetime <= p->initial_lifetime / 2','move'),
    ('810a_scale','rand_range(h, 0.5f, 1.0f, 100)','rand_range(h, 0.6f, 1.0f, 100)','create'),
    ('810a_velocity','rand_range(h, -10.0f, 10.0f, 1) * 0.2f','rand_range(h, -10.0f, 10.0f, 1) * 0.3f','create'),
    ('810a_shrink','p->scale = p->scale - p->initial_scale / (float)p->initial_lifetime;',
     'p->scale = p->scale - p->scale / (float)p->initial_lifetime;','move'),
    ('owned_life','p->type == 0x81cf ? 20 : 30','p->type == 0x81cf ? 21 : 31','create'),
    ('owned_null','if (p->owner == MU_PT_NO_OWNER) {','if (0) {','move'),
    ('ring_half','if (p->lifetime < half)','if (p->lifetime <= half)','move'),
    ('ring_growth','if (p->type == 0x81cf) {\n            p->scale = p->initial_scale / (float)p->initial_lifetime + p->scale;',
     'if (p->type == 0x81cf) {\n            p->scale = p->initial_scale / (float)p->initial_lifetime - p->scale;','move'),
    ('point_fade','p->lifetime < p->initial_lifetime)','p->lifetime <= p->initial_lifetime)','move'),
    ('point_copy','copy3(p->position, point);','copy3(p->position, p->start);','render'),
    ('point_offset','copy3(p->position, point);','for (int k=0;k<3;++k) p->position[k]=point[k]+p->start[k];','render'),
    ('render_alpha','s->light[k] = p->light[k] * p->alpha;','s->light[k] = p->light[k];','render'),
]
NATIVE_MUTANTS = [
    ('bitmap_8500','0x8500, 0x8569,','0x8501, 0x8569,'),
    ('bitmap_8569','0x8500, 0x8569,','0x8500, 0x8568,'),
    ('file_8500','Data/Skill/wing_hetachi2.OZJ','Data/Effect/Damage_ring_2.OZJ'),
    ('file_8569','Data/Effect/Damage_ring_2.OZJ','Data/Skill/wing_hetachi2.OZJ'),
    ('point_route','else if (later) mu_pt_item_later_follow(record, point);','else if (later) (void)point;'),
    ('point_index','? it->points[record->arg8] : NULL','? it->points[0] : NULL'),
    ('fourth_bound','point_count = later ? 4 : 3','point_count = later ? 3 : 3'),
    ('fourth_store_bound','word >= 12','word >= 9'),
    ('bitmap_filter','t->filter[i] = bitmap_ids[i] == MU_PT_BITMAP_IMPACK03 ||',
     't->filter[i] = bitmap_ids[i] == 0x8500 || bitmap_ids[i] == MU_PT_BITMAP_IMPACK03 ||'),
    ('bitmap_wrap','t->wrap[i] = bitmap_ids[i] == 0x84d1 ||',
     't->wrap[i] = bitmap_ids[i] == 0x8569 || bitmap_ids[i] == 0x84d1 ||'),
]


RC_MUTANTS = [
    ('fourth_disabled','o->a == 305 && o->b == 16','o->a == 306 && o->b == 16'),
    ('fourth_word','fx.subtype = 9 + k;','fx.subtype = 6 + k;'),
    ('fourth_value','fx.position[0] = r[o->a + k];','fx.position[0] = r[o->a];'),
]


def mutations(directory,text,data,root):
    result=[]
    for name,old,new,family in PT_MUTANTS:
        lib=configure(re11.compile_pt_mutant(directory,name,'item_later_kinds.inc',old,new))
        r=pt.Report();particle_family(text,data,lib,family,80,r)
        f=r.families['particle_'+family]
        result.append(dict(name=name,detected=f['cases']-f['equal'],stopped=sum(
            bool(x.get('stopped')) for x in f['first_failures'])))
    for name,old,new in NATIVE_MUTANTS:
        source=(ROOT/'native/core/mu_particles.c').read_text()
        if source.count(old)!=1: raise ValueError(name+': nonunique anchor')
        folder=Path(directory)/name;folder.mkdir()
        path=folder/'mu_particles.c';path.write_text(source.replace(old,new))
        r=pt.Report();native_check(build_host(folder,path),root,r)
        result.append(dict(name=name,detected=sum(f['cases']-f['equal'] for f in r.families.values()),stopped=0))
    for name,old,new in RC_MUTANTS:
        lib=re25.renderchar_mutant(directory,name,old,new)
        r=pt.Report();caller_points(80,r,lib)
        f=r.families['caller_points']
        result.append(dict(name=name,detected=f['cases']-f['equal'],stopped=0))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases',type=int,default=1000);p.add_argument('--mutations',action='store_true')
    p.add_argument('--output');p.add_argument('--renders');a=p.parse_args();start=time.monotonic()
    text,data=pins.TEXT.read(),pins.DATA.read()
    lib=configure(pt.load_library(ROOT/('reconstructed/particles/libclient_particles.'+pt.SUFFIX)))
    r=pt.Report()
    for name in ('create','move','render'): particle_family(text,data,lib,name,a.cases,r)
    caller_points(a.cases*2,r)
    census=request_census(lib)
    r.add('census',not census['missing_programs'] and not census['unresolved'] and
          all(v['supported'] for v in census['pairs'].values()),census)
    bitmap_checks(text,data,r)
    with tempfile.TemporaryDirectory(prefix='effects26-') as tmp:
        root=bitmap_fixture(tmp);native_check(build_host(tmp),root,r,a.renders)
        ms=mutations(tmp,text,data,root) if a.mutations and all(f['cases']==f['equal'] for f in r.families.values()) else []
    result=dict(families=r.families,coverage=r.coverage,request_census=census,
                all_equal=all(f['cases']==f['equal'] for f in r.families.values()),
                cases=sum(f['cases'] for f in r.families.values()),mutants=ms,
                all_mutants_caught=all(m['detected'] and not m['stopped'] for m in ms),
                seconds=time.monotonic()-start,text_sha256=am.TEXT_SHA256,data_sha256=am.DATA_SHA256)
    if a.output:Path(a.output).write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    return 0 if result['all_equal'] and result['all_mutants_caught'] else 1


if __name__=='__main__':raise SystemExit(main())
