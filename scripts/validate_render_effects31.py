#!/usr/bin/env python3
"""RENDER-EFFECTS-031: existing world producers' refused native consumers."""
import argparse
import io
import ctypes as C
import subprocess
import sys
from collections import defaultdict
import json
from pathlib import Path
import random
import struct
import shutil
import re
import validate_combat as vc
import tempfile
import time

import actor_machine as am
import pins
import validate_joints as jt
import validate_skill_fx as fx
import validate_particles as pt
import validate_render_effects11 as re11

ROOT = Path(__file__).resolve().parents[1]
KINDS = [(0x801c, 3), (0x801c, 4), (0x801c, 7), (0x7f89, 7), (0x7f89, 10), (0x7f89, 26), (0x7f89, 16), (0x7f42, 7), (0x802a, 1), (0x7f42, 12), (0x7f26, 2)]
JOINTS = [(0x7f7d, 8), (0x7f7d, 9), (0x7f7d, 10), (0x7fd5, 5), (0x7fd3, 2), (0x7f78, 2)]
EFFECTS = [(0x7f84, 4), (0x47a, 0), (0x47a, 1), (0x7fd0, 0), (0x7f42, 6)]
# Per-pair missing constructor, update and draw controls are compiled production changes.
# Extra arithmetic/state controls below protect the newly reconstructed branches.
MUTANTS = []
for kind in KINDS:
    cond=f'p->type == {kind[0]} && p->subtype == {kind[1]}'
    for family,anchor,body,file in [
        ('create','static void mu_pt_world_inner_create(mu_pt_particle *p, const mu_pt_host *h, float scale)\n{',
         'p->lifetime=0; return;','world_inner_kinds.inc'),
        ('move','static void mu_pt_world_inner_move(mu_pt_particle *p, const mu_pt_host *h)\n{',
         'p->scale=p->scale+1.0f; return;','world_inner_kinds.inc'),
        ('render','    memset(out, 0, sizeof *out);','return 0;','particles.c')]:
        MUTANTS.append(('pt',f'p{kind[0]:x}_{kind[1]}_{family}',file,anchor,
                        anchor+f'\n    if ({cond}) {{ {body} }}',family,kind))
for kind in JOINTS:
    cond=f'j->type == {kind[0]} && j->subtype == {kind[1]}'
    for family,anchor,body,file in [
        ('create','static void create_world_inner_joint(mu_jt_joint *j, float scale, const float target[3], const mu_jt_env *env)\n{',
         'j->lifetime=0; return;','world_inner_joints.inc'),
        ('move','static void move_world_inner_joint(mu_jt_joint *j, const mu_jt_env *env)\n{',
         'j->scale=j->scale+1.0f; return;','world_inner_joints.inc'),
        ('render','int mu_jt_render(const mu_jt_joint *j, uint8_t mode, float world_time, const mu_jt_gl *gl)\n{',
         'return 0;','joints.c')]:
        MUTANTS.append(('jt',f'j{kind[0]:x}_{kind[1]}_{family}',file,anchor,
                        anchor+f'\n    if ({cond}) {{ {body} }}','joint_'+family,kind))
for label,old,new,family,kind in [
    ('charge_life','e->lifetime = 10;\n        const float offset[3]','e->lifetime = 11;\n        const float offset[3]','effect_create',(0x7fd0,0)),
    ('charge_children','for (int n = 0; n < 3; ++n) {\n            const float offset[3]','for (int n = 0; n < 2; ++n) {\n            const float offset[3]','effect_move',(0x7fd0,0)),
    ('flame_life','case 0x7f42: e->lifetime = 40;','case 0x7f42: e->lifetime = 41;','effect_create',(0x7f42,6)),
    ('flame_child','e->light,12,e->scale,-1);','e->light,11,e->scale,-1);','effect_move',(0x7f42,6)),
    ('ground_life','e->lifetime = 40;\n            e->scale = ((float)(env_rand(env) % 50','e->lifetime = 41;\n            e->scale = ((float)(env_rand(env) % 50','effect_create',(0x7f84,4)),
    ('ground_skip','if (sub == 4) break;','if (sub == 5) break;','effect_move',(0x7f84,4)),
    ('transition_y','(float)subtype * -90.0f + 45.0f','(float)subtype * 90.0f + 45.0f','effect_create',(0x47a,1)),
    ('transition_size','e->lifetime = 10; e->scale = 0.2f;','e->lifetime = 10; e->scale = 0.3f;','effect_create',(0x47a,0)),
    ('transition_fade','e->blend_light = e->blend_light / 1.8f;','e->blend_light = e->blend_light / 1.7f;','effect_move',(0x47a,0)),
    ('transition_accel','e->velocity = e->velocity + 0.02f;','e->velocity = e->velocity + 0.01f;','effect_move',(0x47a,1)),
]: MUTANTS.append(('fx',label,'skill_fx.c',old,new,family,kind))


MUTANTS += [
    ('pt','cloud16_early_death','world_inner_kinds.inc','p->subtype == 16 && p->lifetime <= 10','p->subtype == 16 && p->lifetime < 10','move',(0x7f89,16)),
    ('pt','cloud16_cap','world_inner_kinds.inc','p->light[0] >= 0.2f) p->light[0] = p->light[1] = p->light[2] = 0.2f','p->light[0] >= 0.3f) p->light[0] = p->light[1] = p->light[2] = 0.3f','move',(0x7f89,16)),
    ('pt','water_extra_state','particles.c','if (p->type == 0x802a && p->subtype == 1)\n        state(out, MU_PT_STATE_ADD, 0);','if (0)\n        state(out, MU_PT_STATE_ADD, 0);','render',(0x802a,1)),
    ('jt','remain_return_axes','world_inner_joints.inc','const int first_axis = j->subtype == 9 ? 1 : 0;','const int first_axis = 0;','joint_move',(0x7f7d,9)),
]


def particle_family(text, data, lib, name, cases, report, kinds=None):
    saved = pt.KINDS, pt.OWNED_KINDS, pt.random_particle, pt.Case, pt.globals_region
    current_case,original=[None],[None]
    class Machine(pt.PtMachine):
        def execute(self,*args,**kwargs):
            result=super().execute(*args,**kwargs); original[0]=result; return result
    class Report:
        def add(self,family,equal,failure=None):
            if family=='move' and failure and failure.get('kind') in [['0x7f89',7],['0x7f89',26]] and vc.ok(original[0]):
                owner=struct.unpack_from('<i',original[0]['regions']['owner0'],0x68)[0]
                if owner!=current_case[0].owner_hidden:
                    equal=False; failure=dict(failure,owner_hidden=[owner,current_case[0].owner_hidden])
            report.add(family,equal,failure)
        def cover(self,*args): report.cover(*args)
    def particle(rng, kind):
        p = saved[2](rng, kind)
        if kind in ((0x7f89, 7), (0x7f89, 26), (0x7f26, 2)): p.owner = 0
        if name == 'move':
            if kind[0] == 0x7f89 and kind[1] in (10,16):
                distance = rng.choice([0,49.999,50,50.001,99.999,100,100.001,299.999,300,300.001,499.999,500,500.001])
                p.start[:] = [0,0,0]; p.position[:] = [distance,0,0]; p.velocity[:] = [0,0,0]
                p.light[:] = [rng.choice([0,0.0009,0.001,0.149,0.15,0.29,0.3]),0.1,0.2]
            if kind == (0x7f26,2): p.lifetime = rng.choice([0,1,4,5,6,7,15])
        return p
    class Case(re11.OwnerCase):
        def owner_regions(self):
            self.visible = random.Random(str(self.rand_values[:4])).choice([0,1,2])
            return super().owner_regions()
        def host(self, world=0, world_time=0.0, *a, **kw):
            current_case[0]=self
            host = super().host(world, world_time, *a, **kw)
            host.world_time = re11.WORLD_TIME[0] if name == 'move' else world_time
            return host
    def globals_region(world=0, world_time=0.0, *a, **kw):
        return saved[4](world, re11.WORLD_TIME[0] if name == 'move' else world_time, *a, **kw)
    try:
        pt.KINDS = kinds or KINDS
        pt.OWNED_KINDS = {(0x7f89, 7), (0x7f89, 26), (0x7f26, 2)}
        pt.random_particle, pt.Case, pt.globals_region = particle, Case, globals_region
        getattr(pt, 'family_'+name)(Machine(text, data), lib,
            random.Random('effects31-'+name), cases * len(pt.KINDS), Report(), defaultdict(int))
    finally:
        pt.KINDS, pt.OWNED_KINDS, pt.random_particle, pt.Case, pt.globals_region = saved


def joint_family(text, data, lib, name, cases, report, kinds=None):
    saved = jt.KINDS
    try:
        jt.KINDS = kinds or JOINTS
        getattr(jt, 'family_joint_'+(name[6:] if name.startswith('joint_') else name))(fx.FxMachine(text, data), lib,
            random.Random('effects31-joint-'+name), cases*len(jt.KINDS), report, defaultdict(int))
    finally:
        jt.KINDS = saved


def bitmap_fixture(directory):
    from PIL import Image
    root = Path(directory)/'game'
    effect = root/'Data/Effect'
    effect.mkdir(parents=True)
    names = ['WATERFALL3','clouds','Flame01','water','JointThunder01','Spark01','JointSpirit01','Flare','flare01','Spark03','Shiny02']
    for name in names:
        buf = io.BytesIO()
        grey = 64 if name=='Flame01' else 192 if name=='water' else 128
        Image.new('RGB',(32,32),(grey,grey,grey)).save(buf,format='JPEG',quality=100)
        (effect/(name+'.OZJ')).write_bytes(bytes(24)+buf.getvalue())
    sys.path.insert(0,str(ROOT/'native/tests'))
    import native_fixtures as nf
    skill=root/'Data/Skill'; skill.mkdir()
    (skill/'DarkLordSkill.bmd').write_bytes(nf.synthetic_layout(731,actions=1,keys=(4,)))
    return root


def build_host(directory, mutation=None):
    directory = Path(directory)
    native = ROOT/'native'
    obj, host = directory/'host.o', directory/'host'
    source=native/'tests/effects31_host.c'
    if mutation:
        old,new=mutation
        original=native/'core/mu_particles.c'; code=original.read_text()
        if code.count(old)!=1: raise ValueError(old)
        code=code.replace(old,new)
        code=re.sub(r'#include "(\.\./[^"\n]+)"',lambda m:'#include "'+str((original.parent/m[1]).resolve())+'"',code)
        core=directory/'mutant.c'; core.write_text(code)
        source=directory/'host.c'
        source.write_text((native/'tests/effects31_host.c').read_text().replace('../core/mu_particles.c',str(core)).replace('../core/mu_png.h',str(native/'core/mu_png.h')))
    subprocess.run(['clang','-std=c11','-O1' ,'-ffp-contract=off','-I',str(native/'build/gen'),
        '-I',str(native/'session'),'-I',str(native/'core'),'-c',str(source),'-o',str(obj)],
        check=True,capture_output=True)
    command=['clang++',str(obj),str(native/'build/libmunative.a'),str(native/'build/libmusession_world.a'),'-lm','-o',str(host)]
    if sys.platform=='darwin':
        command += ['-L/opt/homebrew/opt/cryptopp/lib','-lcryptopp','-L/opt/homebrew/opt/jpeg-turbo/lib','-ljpeg',
                    '-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation']
    else: command += ['-lcryptopp','-ljpeg']
    subprocess.run(command,check=True,capture_output=True)
    return host


def native_checks(host, root, report, images=None):
    run=subprocess.run([str(host),str(root)]+([str(images)] if images else []),capture_output=True,text=True)
    if run.returncode:
        report.add('native_particles',False,dict(exit=run.returncode,stderr=run.stderr[-2000:]))
        return
    for line in run.stdout.splitlines():
        row=json.loads(line)
        report.add('native_effects' if row.get('effect') else 'native_joints' if row.get('joint') else 'native_particles',row.get('equal',row['fragments']>0),row)


def effect_family(text, data, lib, name, cases, report, kinds=None):
    saved=fx.EFFECT_KINDS
    try:
        fx.EFFECT_KINDS=kinds or EFFECTS
        getattr(fx,'family_'+name)(fx.FxMachine(text,data),lib,random.Random('effects31-'+name),
                                 cases*len(fx.EFFECT_KINDS),report,defaultdict(int))
    finally: fx.EFFECT_KINDS=saved


def render_dispatch(text,data,cases,report):
    # The original default dispatch enters with [ebp-0x10] = this OBJECT.
    # High bitmap IDs do not draw their own body; 0x47a calls RenderObject once.
    machine=fx.FxMachine(text,data)
    for n in range(cases):
        kind=EFFECTS[n%len(EFFECTS)]
        e=fx.Effect(); e.type,e.subtype=kind
        raw,mask=fx.effect_to_bytes(e,{'type','subtype'})
        calls=[]
        def draw(mm):
            calls.append([mm.argument(i) for i in range(6)]); return 0
        result=machine.execute(0x015183c2,[0],[am.Region('effect',fx.POOL,raw,mask)],
             {re11.RENDER_OBJECT:draw,re11.RENDER_NEXT:fx.jump_stub(re11.RENDER_END)},
             frame=pt.mid_frame(re11.RENDER_FRAME,{-0x10:fx.POOL}),cleanup=4)
        expected=[[fx.POOL,0,0,0,0xffffffff,0xffffffff]] if kind[0]==0x47a else []
        report.add('effect_render_dispatch',vc.ok(result) and calls==expected,
                   dict(kind=kind,calls=calls,stopped=result['stopped'],error=result['error'],checks=result['checks']))
        report.cover('effect_render_dispatch',str(kind))


def census_and_bitmaps(text,data,plib,jlib,flib,report):
    import validate_render_effects26 as previous
    saved=previous.BITMAPS
    try:
        previous.BITMAPS=[(0x01821539,0x7f42,'Effect\\Flame01.jpg'),
                          (0x01823025,0x802a,'effect\\water.jpg')]
        previous.bitmap_checks(text,data,report)
    finally: previous.BITMAPS=saved
    from capstone import Cs,CS_ARCH_X86,CS_MODE_32
    ins=list(Cs(CS_ARCH_X86,CS_MODE_32).disasm(text[0x01833c5d-am.TEXT_BASE:0x01833c73-am.TEXT_BASE],0x01833c5d))
    pushes=[int(i.op_str,0) for i in ins if i.mnemonic=='push']
    strings=[data[p-am.DATA_BASE:].split(b'\0')[0] for p in pushes[1:3]]
    report.add('model_loader',pushes[0]==-1 and pushes[3]==0x47a
               and strings==[b'DarkLordSkill',b'Data\\Skill\\'] and ins[-1].op_str=='0x18202b4',
               dict(pushes=pushes,strings=[str(s) for s in strings]))
    old=previous.request_census(plib)
    report.add('frozen_item_census',old['programs']==110 and old['particle_pairs']==37
               and not old['unresolved'] and not old['missing_programs']
               and all(r['supported'] for r in old['pairs'].values()),
               dict(programs=old['programs'],pairs=old['particle_pairs']))
    rows=[]
    for category,kinds in [('particle',KINDS),('joint',JOINTS),('effect',EFFECTS+[(0x46c,0),(0x583,0),(0x584,0)])]:
        for kind in kinds:
            expected=kind not in [(0x46c,0),(0x583,0),(0x584,0)]
            if category=='particle': supported=plib.mu_pt_kind_supported(*kind)
            elif category=='joint': supported=jlib.mu_jt_kind_supported(*kind)
            else:
                e=fx.Effect(); info=fx.Info(); env=fx.Env(); z=pt.F3(0,0,0); light=pt.F3(1,1,1)
                supported=flib.mu_sfx_effect_create(C.byref(e),*kind,z,z,light,-1,1,C.byref(info),C.byref(env))
            row=dict(category=category,type=hex(kind[0]),subtype=kind[1],supported=bool(supported))
            rows.append(row); report.add('world_skill_census',bool(supported)==expected,row)
    return dict(frozen_items=dict(programs=old['programs'],particle_pairs=old['particle_pairs']),
                world_skill=dict(pairs=len(rows),supported=sum(r['supported'] for r in rows),rows=rows))


def compile_mutant(directory, category, label, file, old, new):
    if category=='pt': return re11.compile_pt_mutant(directory,label,file,old,new)
    dest=Path(directory)/label
    for sub in ('combat','joints','objects','record-math','movement'):
        shutil.copytree(ROOT/'reconstructed'/sub,dest/sub,
                        ignore=shutil.ignore_patterns('*.dylib','*.so','*.d','__pycache__'))
    path=dest/('joints' if category=='jt' else 'combat')/file
    source=path.read_text()
    if source.count(old)!=1: raise ValueError(f'{label}: expected one site')
    path.write_text(source.replace(old,new))
    sub='joints' if category=='jt' else 'combat'
    subprocess.run(['make','-s','-C',str(dest/sub)],check=True,capture_output=True)
    lib=(jt if category=='jt' else fx).load_library(dest/sub/('libclient_joints.'+pt.SUFFIX if category=='jt' else 'libcombat.'+pt.SUFFIX))
    return lib


def run(cases, mutations=False):
    start = time.monotonic()
    text, data = pins.TEXT.read(), pins.DATA.read()
    lib = pt.load_library(ROOT/('reconstructed/particles/libclient_particles.'+pt.SUFFIX))
    report = pt.Report()
    for name in ('create', 'move', 'render'):
        particle_family(text, data, lib, name, cases, report)
    jlib = jt.load_library(ROOT/('reconstructed/joints/libclient_joints.'+pt.SUFFIX))
    for name in ('create', 'move', 'render'):
        joint_family(text, data, jlib, name, cases, report)
    flib = fx.load_library(ROOT/('reconstructed/combat/libcombat.'+pt.SUFFIX))
    for name in ('effect_create','effect_move'):
        effect_family(text,data,flib,name,cases,report)
    render_dispatch(text,data,cases*len(EFFECTS),report)
    with tempfile.TemporaryDirectory(prefix='effects31-native-') as tmp:
        native_checks(build_host(tmp),bitmap_fixture(tmp),report)
    census=census_and_bitmaps(text,data,lib,jlib,flib,report)
    mutants = []
    if mutations and all(f['cases'] == f['equal'] for f in report.families.values()):
        with tempfile.TemporaryDirectory(prefix='effects31-mutants-') as tmp:
            for category,label,file,old,new,family,kind in MUTANTS:
                mutant=compile_mutant(tmp,category,label,file,old,new)
                r=pt.Report()
                (particle_family if category=='pt' else joint_family if category=='jt' else effect_family)(
                    text,data,mutant,family,80,r,[kind])
                f=r.families[family]
                row=dict(name=label,detected=f['cases']-f['equal'],
                         stopped=sum(bool(v.get('stopped') or v.get('error')) for v in f['first_failures']))
                mutants.append(row)
                print('mutant',json.dumps(row),flush=True)
            for label,old,new in [
                ('native_flame','"Data/Effect/Flame01.OZJ"','"Data/Effect/water.OZJ"'),
                ('native_water','"Data/Effect/water.OZJ"','"Data/Effect/Flame01.OZJ"'),
                ('native_transition','"Data/Skill/DarkLordSkill.bmd"','"Data/Skill/Missing.bmd"'),
                ('native_charge_owner','if (e && e->type == 0x7fd0 && call->owner == -2)',
                                       'if (0 && e && e->type == 0x7fd0 && call->owner == -2)'),
            ]:
                directory=Path(tmp)/label; directory.mkdir()
                host=build_host(directory,(old,new)); r=pt.Report()
                native_checks(host,bitmap_fixture(directory),r)
                mutants.append(dict(name=label,detected=sum(f['cases']-f['equal'] for f in r.families.values()),stopped=0))
    return dict(families=report.families, coverage=report.coverage, census=census,
        all_equal=all(f['cases'] == f['equal'] for f in report.families.values()),
        cases=sum(f['cases'] for f in report.families.values()), mutants=mutants,
        all_mutants_caught=(not mutations or len(mutants)==len(MUTANTS)+4) and all(m['detected'] and not m['stopped'] for m in mutants),
        seconds=round(time.monotonic()-start,3), text_sha256=am.TEXT_SHA256, data_sha256=am.DATA_SHA256)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases',type=int,default=1000)
    p.add_argument('--mutations',action='store_true')
    p.add_argument('--output')
    args=p.parse_args()
    if args.cases < 1: p.error('--cases must be positive')
    r=run(args.cases,args.mutations)
    if args.output: Path(args.output).write_text(json.dumps(r,indent=2))
    print(json.dumps(r,indent=2))
    return 0 if r['all_equal'] and r['all_mutants_caught'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
