#!/usr/bin/env python3
"""RENDER-ACTORS-005: ordinary monster body/weapon plans, original instructions.

RenderCharacter executes from entry. Base RenderObject and stateful map services
are named recorders/declining fixtures, as in ACTORS-004. Link bones execute the
original constructor switch. RenderObjDraw streams and actual native body/weapon
files, per-hand poses, draw alpha and cleanup are checked separately.
"""
import argparse
import ctypes as C
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import time

import actor_census as census
import actor_machine as am
import pins
import validate_actor_composites as composites
import validate_actor_recipes as recipes
import validate_actors as va
import validate_renderchar as vr

ROOT = Path(__file__).resolve().parents[1]
CLASSES = census.MONSTER_BODIES


def library(path=recipes.LIBRARY):
    lib = recipes.library(path)
    lib.mu_actor_monster_recipe.argtypes = [C.c_int32, C.POINTER(recipes.Row)]
    return lib


def originals(args):
    machine = am.ActorMachine(*args[:2]); rows = {}
    for cl in CLASSES:
        row = va.extract_class(machine, cl)
        regions, stubs, _ = va.class_case(0, 0)
        create = stubs[va.CREATE_CHARACTER]
        def initialized(m):
            value = create(m)
            m.uc.mem_write(va.CLASS_CHARACTER+0x328f, b'\1')
            return value
        stubs[va.CREATE_CHARACTER] = initialized
        run = machine.execute(va.CREATE_GENERIC, [cl, 10, 20, 1000+cl, 0], regions, stubs,
                              frame=(0x1dd4+0xc, {-0x10:0}))
        if not run['ok']: raise RuntimeError({k:v for k,v in run.items() if k!='regions'})
        row['object_kind'] = run['regions']['character'][0x328f]
        rows[cl] = row
    bones = vr.extract_link_bones(args, sorted({r['model'] for r in rows.values()}))
    return rows, bones, machine


def check_recipes(lib, rows):
    fam = recipes.family()
    for cl in range(-1, 1025):
        actual = recipes.Row(); status = lib.mu_actor_monster_recipe(cl, C.byref(actual))
        if cl not in rows:
            recipes.note(fam, status==0, {'class':cl, 'status':status}); continue
        expected = rows[cl]
        recipes.note(fam, status==1 and actual.model==expected['model'] and actual.kind==1 and
            actual.opened==expected['opens'][0][1] and actual.scale_bits==expected['scale_bits'] and
            [[s.type,s.level] for s in actual.slots]==[list(s) for s in expected['slots']], {'class':cl})
    return fam


def check_openers(machine, rows):
    fam = recipes.family()
    for t in sorted({r['opens'][0][1] for r in rows.values()}):
        run = va.run_client_open(machine, va.monster_case(str(t), t, actions=16))
        access = [c for c in run['calls'] if c[0]=='access']
        recipes.note(fam, run['ok'] and access==[('access', t+0x7a5, 'Data\\Monster\\', 'Monster', t+1)],
                     {'type':t, 'calls':access})
    return fam


def client_plan(args, row, bones, cl, action, world_id, alpha, frame):
    original_world, original_record = vr.World, vr.character_record
    try:
        def world(*args):
            w = original_world(*args); m = w.m
            m.ensure(0x01cf15fc,4); m.w32(0x01cf15fc,world_id)
            m.stub(0x009dc2f0,lambda m:0,0)
            m.ensure(0x2f000000,0x200); m.w32(0x2f000000,0x2f000100); m.w32(0x2f000154,0x00401000)
            m.stub(0x00401000,lambda m:0,12); m.stub(0x00db747f,lambda m:0x2f000000,0)
            m.stub(0x00a9c672,lambda m:0,12); m.stub(0x00ea3cae,lambda m:0,12)
            m.stub(0x016d4fe4,lambda m:w.calls.append(('base-body',[m.arg(i) for i in range(6)])) or 0,0)
            w.add_model(row['model'],vr.MODEL+0x4000,bones=60,meshes=1,actions=16,actions_at=vr.ACTIONS)
            write = m.write
            def write_record(address, raw):
                if address==vr.CHAR and len(raw)==0x3700:
                    raw = bytearray(raw)
                    for k in range(2): raw[vr.SLOT_BASES[6+k]+5] = bones[k]
                return write(address,raw)
            m.write = write_record
            return w
        def record(**kw):
            raw = original_record(**kw)
            struct.pack_into('<I',raw,0x32b0,row['model']); struct.pack_into('<h',raw,0x146,cl)
            struct.pack_into('<I',raw,0x32f4,row['scale_bits'] or vr.f2u(.9))
            raw[0x328f] = row['object_kind']
            return raw
        vr.World, vr.character_record = world, record
        slots = [None if t in (0,65535) else dict(type=t,level=lv,option=0,ext=0,kind=0,
            action=0,frame=0,prior=0,speed=0) for t,lv in row['slots']]
        ch = dict({'class':row['class_byte']},action=action,safe=0,frame=frame,alpha=alpha,select=0,
            speeds=[vr.f2u(.25)]*390,slots=slots)
        return vr.character_client(args,ch)
    finally:
        vr.World, vr.character_record = original_world, original_record


def check_render(lib,args,rows,bones,count):
    fam = recipes.family(); rng=random.Random(20261114)
    for i in range(count):
        cl=CLASSES[i%len(CLASSES)]; row=rows[cl]; model=row['model']; action=(0,2,3,4,6)[i//24%5]
        world=(0,3,2,51)[i//6%4]; alpha=vr.f2u(rng.uniform(.05,1)); frame=vr.f2u(rng.uniform(0,5))
        run,calls,w=client_plan(args,row,bones[model],cl,action,world,alpha,frame)
        native=recipes.Row(); lib.mu_actor_monster_recipe(cl,C.byref(native))
        expected=[('LINK',k,native.slots[6+k].type,native.slots[6+k].level<<3,0,(0,0,0),0,1,0,1,
            bones[model][k],0,0,0,0) for k in range(2) if native.slots[6+k].type not in (0,65535)]
        links=[c for c in calls if c[0]=='LINK']; base=[c for c in w.calls if c[0]=='base-body']
        effects=[c for c in w.calls if c[0] in ('effect','access-model','load-bitmap')]
        recipes.note(fam,run['ok'] and links==expected and len(base)==1 and base[0][1]==[
            vr.CHAR+0x3254,1,0,0,0xffffffff,0xffffffff] and not effects and
            not any(c[0]=='PART' for c in calls),dict(cl=cl,world=world,action=action,links=links,
            expected=expected,base=base,effects=effects,stop=None if run['ok'] else str(run)[:500]))
    return fam


def check_draw(args, rows):
    fam=recipes.family(); lib=C.CDLL(str(vr.LIBRARY))
    types=sorted({r['model'] for r in rows.values()}|{t for r in rows.values() for t,_ in r['slots'] if t not in (0,65535)})
    for t in types:
        for i in range(8):
            case=vr.classify_case(t,dict(item_level=0,option1=0,ext=0,quality=5,
                time=vr.f2u(i*13579.5),render_type=2))
            case['alpha']=vr.f2u((i+1)/9);case['light']=[vr.f2u((i+1)/7)]*3
            run,stream,_,_=vr.client_stream(args,case)
            status,expected=vr.c_stream(lib,case,generic=t<0xae6)
            recipes.note(fam,run['ok'] and status==0 and stream==expected,
                dict(model=t,actual=stream,expected=expected))
    return fam


def check_links(args, rows, bones):
    fam = recipes.family()
    for cl, row in rows.items():
        for k, (t, level) in enumerate(row['slots'][6:8]):
            if not t: continue
            for alpha in (.125, .375, .75, 1.0):
                w = vr.link_world(args, t)
                m = w.m; part = vr.CHAR+0x19ac
                m.write(part, struct.pack('<hBBBB',t,level,0,0,bones[row['model']][k]))
                m.write(vr.CHAR+0x32b0,struct.pack('<I',row['model']))
                w.add_model(row['model'],vr.PLAYER_MODEL,bones=60,meshes=1,actions=16)
                m.write(vr.CHAR+0x32f4,struct.pack('<I',row['scale_bits'] or vr.f2u(.9)))
                m.write(vr.CHAR+0x3330,struct.pack('<f',alpha))
                result=m.run(0x012bd910,[0,0,0,vr.CHAR,part,t,level,0,0,1,0,1])
                names=[c[0] for c in w.calls]
                draw=[c for c in w.calls if c[0]=='objdraw']
                poses=[c for c in w.calls if c[0]=='pose']
                transforms=[c for c in w.calls if c[0]=='transform']
                recipes.note(fam,result['ok'] and names==['rotpos','tick','pose','transform','objdraw'] and
                    draw[0][1][1]==t and draw[0][1][3:9]==[vr.f2u(alpha),level,0,0,0,2] and
                    poses[0][2][1:4]==[0,0,0] and poses[0][2][-2:]==[1,1] and
                    transforms[0][2][4:]==[1,0,vr.f2u(.4),vr.f2u(.8),vr.f2u(.2)] and
                    m.read(vr.MODEL+0x50,1)==b'\0',dict(cl=cl,slot=k,calls=w.calls))
    return fam


def build_host(directory, source=None):
    directory=Path(directory)
    code=(ROOT/'native/tests/actor_monster_host.c').read_text().replace(
        '#include "../core/mu_world_actors.c"','#include "'+str(source or ROOT/'native/core/mu_world_actors.c')+'"')
    (directory/'monster.c').write_text(code)
    native=ROOT/'native'
    subprocess.run(['clang','-std=c11','-O1','-ffp-contract=off','-iquote',str(native/'core'),'-I',str(native/'build/gen'),
        '-I',str(native/'session'),'-c',str(directory/'monster.c'),'-o',str(directory/'monster.o')],check=True,capture_output=True)
    subprocess.run(['clang++',str(directory/'monster.o'),str(native/'build/libmunative.a'),str(native/'build/libmusession_world.a'),
        '-L/opt/homebrew/opt/cryptopp/lib','-lcryptopp','-L/opt/homebrew/opt/jpeg-turbo/lib','-ljpeg',
        '-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation','-lm','-o',str(directory/'host')],
        check=True,capture_output=True)
    return directory/'host'


def check_native(host, root, rows, bones):
    fam=recipes.family()
    for cl in CLASSES:
        for world in (0,3):
            for action in (0,2,3):
                run=subprocess.run([str(host),root,str(cl),str(world),str(action)],capture_output=True,text=True)
                if run.returncode:
                    recipes.note(fam,False,dict(cl=cl,exit=run.returncode,error=run.stderr));continue
                v=json.loads(run.stdout);r=rows[cl]
                scale=vr.u2f(r['scale_bits'] or vr.f2u(.9))
                ok=v['model']==r['model'] and abs(v['scale']-scale)<1e-7 and v['body_missing']==0 and v['body_file'].lower()==f"data/monster/monster{r['opens'][0][1]+1:02d}.bmd" and v['frame']>0 and \
                    v['alpha']==[.375,.375] and v['invalid']==[1,1]
                for k,p in enumerate(v['weapons']):
                    t=r['slots'][6+k][0]
                    if not t:ok &= p is None;continue
                    ok &= p is not None and p['type']==t and p['bone']==bones[r['model']][k] and p['missing']==0 and \
                        p['same_pose']==1 and p['vertices']>0 and p['refused']==0
                recipes.note(fam,ok,v)
    return fam


def check_secondary(args, machine):
    """Extracted caller controls only. No downstream effect admission."""
    fam = recipes.family(); char = va.CLASS_CHARACTER; obj = char+0x3254
    for counter in (0, 23, 24, 25, 26, 100):
        raw = vr.character_record(); struct.pack_into('<I',raw,0x3254+0x6c,counter)
        calls=[]
        def ecx(m): return m.uc.reg_read(m.x86.UC_X86_REG_ECX)
        def record(name, count):
            return lambda m:calls.append((name,[m.argument(i) for i in range(count)])) or 0
        stubs={0x012affa4:record('action',2),0x013c0eaa:record('effect',14),
               0x0129f4a5:lambda m:(calls.append(('live',[m.argument(0)])) or 0,4),0x01989721:lambda m:0,
               0x00cfc94a:ecx,0x00cfc922:lambda m:(ecx(m)+4*m.argument(0),4),
               0x0168fafd:record('particle',14)}
        run=recipes.bounded(machine,0x01393fd6,(0x0139406e,0x013942be),stubs,
            [am.defined_region('character',char,raw)],frame=(0x100,{-0x10:obj}),arguments=(char,))
        effects=[c for c in calls if c[0]=='effect']; live=[c for c in calls if c[0]=='live']
        particles=[c for c in calls if c[0]=='particle']
        final=struct.unpack_from('<I',run['regions']['character'],0x3254+0x6c)[0]
        emitted=counter>=25
        recipes.note(fam,run['ok'] and len(effects)==int(emitted) and
            (not emitted or effects[0][1][0]==0x5af) and len(live)==int(emitted) and
            len(particles)==0 and final==(0 if emitted else counter+1),
            dict(counter=counter,final=final,effects=effects,live=live,particles=len(particles),
                 stop=None if run['ok'] else str(run)[:500]))
    return fam


def check_secondary_openers(machine):
    fam = recipes.family()
    files = {147:[(0x507+k, f'Data/Monster/icegiantpart_{k+1}.bmd') for k in range(6)],
        226:[(0x5af,'Data/Monster/gnomedie.bmd')],
        **{t:[(0x59f+t-229,f'Data/Monster/Monster{t+1}.bmd')] for t in range(229,234)},
        245:[(0x5ae,'Data/Monster/normusdie.bmd')],
        289:[(0x605,'Data/Effect/Magic_type02.bmd'),(0x603,'Data/Effect/pgunbossspin.bmd')]}
    for t, expected in files.items():
        run = va.run_client_open(machine,va.monster_case(str(t),t,actions=16))
        actual=[]
        for c in run['calls']:
            if c[0]!='access' or c[1]==t+0x7a5:continue
            _,model,directory,name,number=c
            actual.append((model,(directory+name+('' if number==-1 else f'{number:02d}')+'.bmd').replace('\\','/')))
        recipes.note(fam,run['ok'] and actual==expected,dict(type=t,actual=actual,expected=expected))
    return fam


def check_clone_prefix(args, machine):
    fam=recipes.family();obj=va.CLASS_CHARACTER+0x3254;action=0x24000000
    factor=struct.unpack_from('<f',args[1],0x01a7e918-0x01a7c000)[0]
    for model in (0x59f,0x5a0,0x5a1,0x5a2,0x5a3,0x5ae):
        raw=bytearray(0x4000);struct.pack_into('<I',raw,0x3254+0x5c,model)
        calls=[]
        def get_action(m):
            calls.append([m.argument(0),m.argument(1)]);return action,8
        run=recipes.bounded(machine,0x013f408c,0x013f41af,
            {0x012affa4:lambda m:0,0x00966cc4:lambda m:0x24001000,0x00eaaa44:get_action},
            [am.defined_region('character',va.CLASS_CHARACTER,raw),
             am.defined_region('action',action,struct.pack('<If',0,.25))],frame=(0x100,{-0x3c:obj}))
        o=run['regions']['character'][0x3254:]
        base={0x59f:0x88a,0x5a1:0x88c,0x5a2:0x88d,0x5a3:0x88e}.get(model)
        recipes.note(fam,run['ok'] and struct.unpack_from('<I',o,0x6c)[0]==311 and
            struct.unpack_from('<I',o,0xd8)[0]==0 and struct.unpack_from('<f',o,0xbc)[0]==(.25*factor if base else 0) and
            calls==([[base,0]] if base else []),dict(model=model,calls=calls,speed=struct.unpack_from('<f',o,0xbc)[0]))
    return fam


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=int,default=240)
    p.add_argument('--mutations',action='store_true');p.add_argument('--output',type=Path,required=True)
    opts=p.parse_args();start=time.monotonic()
    args=pins.TEXT.read(),pins.DATA.read(),pins.FLAG.read(),pins.FEATURE.read()
    rows,bones,machine=originals(args);lib=library()
    with tempfile.TemporaryDirectory() as tmp:
        d=Path(tmp);host=build_host(d)
        families=dict(secondary_openers=check_secondary_openers(machine),clone_prefix=check_clone_prefix(args,machine),secondary=check_secondary(args,machine),defaults=recipes.check_kind_default(args),recipes=check_recipes(lib,rows),openers=check_openers(machine,rows),
            render=check_render(lib,args,rows,bones,opts.cases),draw=check_draw(args,rows),links=check_links(args,rows,bones),
            native=check_native(host,os.environ['MU_GAME_ROOT'],rows,bones))
        mutants={}
        if opts.mutations:
            src=(ROOT/'reconstructed/actors/actors.c').read_text()
            for name,old,new in [('admission','case 0: case 4: case 6: case 7: case 9: case 17: break;','case 0: break;')]:
                assert src.count(old)==1
                f=d/'actors.c';f.write_text(src.replace(old,new));recipes.build_library(f,d/'changed.dylib')
                changed=library(d/'changed.dylib');checks=check_recipes(changed,rows)
                mutants[name]=dict(caught=checks['equal']<checks['cases'],stopped=0)
            src=(ROOT/'native/core/mu_world_actors.c').read_text()
            for name,old,new in (
                ('load','if (!player && load_weapons','if (player && load_weapons'),
                ('left_pose','memcpy(a->weapons->host.bones, a->weapons->body_bones, MU_MODEL_SHARED_BONE_BYTES);','memset(a->weapons->host.bones, 0, MU_MODEL_SHARED_BONE_BYTES);'),
                ('bone','path, bones[k], no_textures','path, 0, no_textures'),
                ('scale','a->actor.spec.scale, a->actor.model.params.color);','1.0f, a->actor.model.params.color);'),
                ('alpha','alpha, &options, backend, stats, NULL);','1.0f, &options, backend, stats, NULL);'),
                ('hand','row.slots[6+k].type;','row.slots[6].type;'),
                ('draw','alpha, &options, backend, stats, NULL);','alpha, &options, backend, NULL, NULL);')):
                expected_count=2 if name=='left_pose' else 1
                assert src.count(old)==expected_count,(name,src.count(old))
                # Draw omission is a direct zero-return negative control.
                changed_src=src.replace(old,new)
                if name=='left_pose':
                    changed_src=src.replace(old,'if (k == 0) '+old,1)
                if name=='draw':
                    changed_src=src.replace('return mu_renderchar_draw_item(&part->model, &part->glow, env, a->actor.model.params.color,\n        alpha, &options, backend, stats, NULL);','return 0;')
                f=d/'mu_world_actors.c';f.write_text(changed_src)
                checks=check_native(build_host(d,f),os.environ['MU_GAME_ROOT'],rows,bones)
                mutants[name]=dict(caught=checks['equal']<checks['cases'],stopped=0)
    report=dict(pins={k:getattr(pins,k.upper()).sha256 for k in ('text','data','flag','feature')},families=families,
        cases=sum(f['cases'] for f in families.values()),all_equal=all(f['cases']==f['equal'] for f in families.values()),
        mutants=mutants,all_mutants_caught=all(m['caught'] for m in mutants.values()),wall_seconds=time.monotonic()-start)
    opts.output.parent.mkdir(parents=True,exist_ok=True);opts.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report));return 0 if report['all_equal'] and report['all_mutants_caught'] else 1

if __name__=='__main__':raise SystemExit(main())
