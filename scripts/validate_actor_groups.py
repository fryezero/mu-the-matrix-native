#!/usr/bin/env python3
"""RENDER-ACTORS-007: extend ACTORS-006's uniform verifier to NPCs and hand links.

All 355 initial incomplete selectors retain a decision. Constructor state,
original opener arguments/speeds, full callers, draw streams and actual native
assets must pass separately. RenderObject is a named pose/body boundary;
stateful processors decline. Appearance overrides and extra services fail closed.
"""
import argparse
import collections
import csv
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import struct
import actor_group_body_reader as body_reader

import actor_machine as am
import pins
import validate_actor_plain as plain
import validate_actor_monsters as monsters
import validate_actor_recipes as recipes
import validate_actors as va
import validate_renderchar as vr

ROOT = plain.ROOT
TABLE = ROOT/'reconstructed/actors/group_body_table.h'
DECISIONS = ROOT/'docs/research/actor-group-decisions.csv'

class Plan(C.Structure):
    _fields_ = [('body', plain.Plan), ('file', C.c_char_p), ('textures', C.c_char_p), ('weapon_mask', C.c_uint32), ('blend_mesh', C.c_int32), ('hidden_mesh', C.c_int32),
                ('blend_light_bits', C.c_uint32), ('subtype', C.c_uint32)]

class Npc(C.Structure):
    _fields_ = [('index', C.c_uint16), ('directory', C.c_char_p), ('name', C.c_char_p),
                ('number', C.c_int32), ('speed_bits', C.c_uint32*16)]

def library(path=recipes.LIBRARY):
    lib = plain.library(path)
    lib.mu_actor_group_plan.argtypes = [C.c_int32, C.POINTER(Plan)]
    lib.mu_npc_find.argtypes = [C.c_uint32]; lib.mu_npc_find.restype = C.POINTER(Npc)
    lib.mu_monster_class_find.argtypes = [C.c_uint32]; lib.mu_monster_class_find.restype = C.POINTER(recipes.Row)
    return lib

def population():
    # ACTORS-006 decisions remain immutable. This lane's decisions are separate.
    return [r for r in plain.initial_rows() if r['decision'] == 'incomplete']

def mask(row):
    return sum(1 << k for k,(t,_) in enumerate(row['slots'][6:8]) if t not in (0,65535))

def npc_opener(machine, lib, row):
    index = row['opens'][0][1]; native = lib.mu_npc_find(index)
    if not native: return False, 'NPC registration unavailable'
    native = native.contents
    file = None; textures = None
    for world in (0,3,2,51,18,30):
        case = va.monster_case('npc', 0, actions=16, world=world); case['index'] = index
        run = va.run_client_open(machine, case, va.OPEN_NPC, index)
        row['opener_calls']=run['calls'];row['opener_loaders']=run['loaders']
        own = ('access', index, native.directory.decode(), native.name.decode(), native.number)
        loads = [c for c in run['calls'] if c[0] == 'access']
        tex = [c for c in run['calls'] if c[0] == 'texture']
        speeds = [int.from_bytes(run['regions']['actions0'][16*a+4:16*a+8], 'little') for a in range(16)]
        # The native NPC loader implements only these speed writes, no mesh override.
        before = bytearray(case['regions'][1].data)
        for a,bits in enumerate(native.speed_bits):
            if bits: before[16*a+4:16*a+8] = int(bits).to_bytes(4,'little')
        model0 = bytearray(case['regions'][0].data); actual = run['regions']['model0']
        # AccessModel supplies counts; no other native NPC field override is claimed.
        model0[0x24:0x28] = bytes([case['meshes'],0,case['actions'],0])
        model0[0x30:0x34] = (va.MODEL_BASE+0x100).to_bytes(4,'little')
        ok = run['ok'] and not any(c[0]=='bitmap' for c in run['loaders']) and loads == [own] and tex and all(c == ('texture',index,'Npc\\',0x2901,0x2600) for c in tex) and \
            run['regions']['actions0'] == bytes(before) and actual == bytes(model0)
        if not ok: return False, 'NPC opener file/texture/action/model state differs'
        directory,name,number = own[2:]
        file = (directory+name+('' if number == -1 else f'{number:02d}')+'.bmd').replace('\\','/')
        textures = 'Data/Npc'
    row.update(file=file, textures=textures)
    return True, ''

def opener(machine, lib, authored, row):
    if row['opens'][0][0] == 'npc': return npc_opener(machine,lib,row)
    run=va.run_client_open(machine,va.monster_case('group',row['opens'][0][1],actions=16))
    row['opener_calls']=run['calls'];row['opener_loaders']=run['loaders']
    if any(c[0]=='bitmap' for c in run['loaders']):
        return False,'extra bitmap consumer remains unchecked'
    ok, detail = plain.opener(machine,authored,row)
    if ok:
        row.update(file=f"Data/Monster/Monster{row['opens'][0][1]+1:02d}.bmd",textures='Data/Monster')
    return ok, '' if ok else detail.get('reason','monster opener has extra load or different texture context')

def constructor(machine,cl):
    original=va.class_record
    def capture(server_class,via,record,run):
        row=original(server_class,via,record,run)
        raw=run['regions']['character'][0x3254:]
        row['appearance_state']={a:raw[a:a+n].hex() for a,n in plain.APPEARANCE_FIELDS}
        return row
    try:
        va.class_record=capture
        row=plain.constructor(machine,cl)
    finally:va.class_record=original
    if 'error' not in row:
        def value(off,default,signed=False):
            return int.from_bytes(bytes.fromhex(row['appearance_state'][off]),'little',signed=signed) if off in row['appearance_writes'] else default
        row.update(blend_mesh=value(0x74,-1,True),hidden_mesh=value(0x68,-1,True),
            blend_light_bits=value(0xa8,vr.f2u(1)),subtype=value(0x60,0))
    return row

def caller(args,row,bones,world,action,alpha,frame):
    old = vr.CHAR_SKIPS;old_record=vr.character_record
    def record(**kw):
        raw=old_record(**kw)
        for off in row['appearance_writes']:
            raw[0x3254+off:0x3254+off+len(bytes.fromhex(row['appearance_state'][off]))]=bytes.fromhex(row['appearance_state'][off])
        return raw
    try:
        vr.character_record=record
        vr.CHAR_SKIPS = {a:n for a,n in old.items() if a not in (0x01362f24,0x01363098)}
        run,calls,w = monsters.client_plan(args,row,bones,row['class'],action,world,vr.f2u(alpha),vr.f2u(frame))
    finally: vr.CHAR_SKIPS = old;vr.character_record=old_record
    expected = [('LINK',k,t,lv,0,(0,0,0),0,1,0,1,bones[k],0,0,0,0)
        for k,(t,lv) in enumerate(row['slots'][6:8]) if t not in (0,65535)]
    links = [c for c in calls if c[0]=='LINK']
    shadows = [c for c in calls if c[0]=='SHADOW']
    base = [c for c in w.calls if c[0]=='base-body']
    extra = [c for c in w.calls if c[0] not in ('base-body','RPO','skip','LINK')]
    ok = run['ok'] and links == expected and len(calls)==len(links)+len(shadows) and \
        len(shadows)<=1 and all(c==('SHADOW',row['model'],1) for c in shadows) and not extra and \
        base==[('base-body',[vr.CHAR+0x3254,1,0,0,0xffffffff,0xffffffff])]
    reason = 'unresolved caller at '+str(run.get('pc')) if not run['ok'] else \
        'additional caller services: '+','.join(sorted({c[0] for c in extra})) if extra else \
        'caller body/link/pass arguments differ' if not ok else ''
    return ok,dict(cl=row['class'],world=world,action=action,reason=reason,calls=calls,extra=extra,
                   stop=None if run['ok'] else str(run)[:500])

def emit(rows):
    lines=['/* Generated by validate_actor_groups.py --generate after original/native checks. */',
           'static const mu_actor_group_body_plan mu_actor_group_plans[] = {']
    for cl,r in sorted(rows.items()):
        lines.append('    {{%d, %#x, %d, %#xu, 2, 1}, "%s", "%s", %du, %d, %d, %#xu, %#xu},' %
            (cl,r['model'],r['opens'][0][1],r['scale_bits'] or vr.f2u(.9),r['file'],r['textures'],mask(r),r['blend_mesh'],r['hidden_mesh'],r['blend_light_bits'],r['subtype']))
    return '\n'.join(lines+['};',''])

def check_plans(lib,rows):
    fam=recipes.family()
    for cl in range(-1,1025):
        p=Plan(); status=lib.mu_actor_group_plan(cl,C.byref(p)); r=rows.get(cl)
        expected=(cl,r['model'],r['opens'][0][1],r['scale_bits'] or vr.f2u(.9),2,1) if r else None
        actual=tuple(getattr(p.body,n) for n,_ in plain.Plan._fields_)
        recipes.note(fam,status==int(r is not None) and (not r or actual==expected and p.file.decode()==r['file'] and
            p.textures.decode()==r['textures'] and p.weapon_mask==mask(r) and (p.blend_mesh,p.hidden_mesh,p.blend_light_bits,p.subtype)==
                (r['blend_mesh'],r['hidden_mesh'],r['blend_light_bits'],r['subtype'])),dict(cl=cl,actual=actual,expected=expected))
    return fam

def build_host(directory,rows=None,source=None,weapon=False):
    d=Path(directory); n=ROOT/'native'
    code=(ROOT/('native/tests/actor_monster_host.c' if weapon else 'native/tests/actor_group_host.c')).read_text()
    prefix=''
    if rows is not None:
        # Candidate plans are compiled only into this disposable host. Production
        # tables are written only after native assets, drawing and cleanup pass.
        prefix='#include "'+str(n/'core/mu_world_actors.h')+'"\n'+emit(rows).replace('mu_actor_group_plans','bootstrap_plans')+'''
static int bootstrap_group_plan(int32_t cl, mu_actor_group_body_plan *out) {
    for (size_t i=0;i<sizeof bootstrap_plans/sizeof bootstrap_plans[0];++i)
        if (bootstrap_plans[i].body.server_class==cl) { if(out)*out=bootstrap_plans[i]; return 1; }
    return 0;
}
#define mu_actor_group_plan bootstrap_group_plan
'''
    if weapon:
        code=code.replace('mu_monster_class row; mu_actor_monster_recipe(cl, &row);',
                          'mu_monster_class row = *mu_monster_class_find((uint32_t)cl);')
    code=prefix+code.replace('#include "../core/mu_world_actors.c"','#include "'+str(source or n/'core/mu_world_actors.c')+'"')
    (d/'host.c').write_text(code)
    subprocess.run(['clang','-std=c11','-O1','-ffp-contract=off','-iquote',str(n/'core'),'-I',str(n/'build/gen'),
        '-I',str(n/'session'),'-c',str(d/'host.c'),'-o',str(d/'host.o')],check=True,capture_output=True)
    subprocess.run(['clang++',str(d/'host.o'),str(n/'build/libmunative.a'),str(n/'build/libmusession_world.a'),
        '-L/opt/homebrew/opt/cryptopp/lib','-lcryptopp','-L/opt/homebrew/opt/jpeg-turbo/lib','-ljpeg',
        '-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation','-lm','-o',str(d/'host')],check=True,capture_output=True)
    return d/'host'

def native_checks(host,rows):
    result={}
    # One process per selector isolates pre-existing unsafe assets and publishes
    # only after host cleanup. No native crash is a successful negative control.
    for cl,row in rows.items():
        run=subprocess.run([str(host),os.environ['MU_GAME_ROOT']],input=str(cl)+'\n',capture_output=True,text=True)
        v=json.loads(run.stdout) if run.returncode==0 and run.stdout else dict(native_exit=run.returncode)
        ok=v.get('model')==row['model'] and abs(v.get('scale',0)-vr.u2f(row['scale_bits'] or vr.f2u(.9)))<1e-7 and \
            v.get('file','').lower()==row['file'].lower() and v.get('missing')==0 and v.get('textures_equal')==1 and \
            v.get('meshes',0)>0 and v.get('vertices',0)>0 and v.get('status')==0 and v.get('refused')==0 and \
            v.get('alpha')==[.375,.375] and v.get('admitted')==1 and v.get('flags')==2 and v.get('attach')==mask(row) and \
            v.get('transform_translate')==1 and v.get('guards')==[0,0,0] and v.get('plan_state_equal')==1
        result[cl]=(ok,v)
    return result

def weapon_checks(host,rows,bones):
    fam=recipes.family()
    for cl,row in rows.items():
        if not mask(row):continue
        for world,action in ((w,a) for w in (0,3) for a in (0,2,3)):
            run=subprocess.run([str(host),os.environ['MU_GAME_ROOT'],str(cl),str(world),str(action)],capture_output=True,text=True)
            v=json.loads(run.stdout) if run.returncode==0 else dict(native_exit=run.returncode)
            ok=v.get('model')==row['model'] and v.get('body_missing')==0 and v.get('frame',0)>0 and v.get('alpha')==[.375,.375]
            for k,part in enumerate(v.get('weapons',[None,None])):
                t=row['slots'][6+k][0]
                if t in (0,65535):ok &= part is None
                else:ok &= part is not None and part['type']==t and part['bone']==bones[row['model']][k] and part['missing']==0 and \
                    part['same_pose']==1 and part['body_pose_same']==1 and part['vertices']>0 and part['refused']==0
            recipes.note(fam,ok,v)
    return fam

def weapon_draw_checks(args,rows):
    lib=C.CDLL(str(vr.LIBRARY));fam=recipes.family()
    pairs=sorted({(t,lv) for r in rows.values() for t,lv in r['slots'][6:8] if t not in (0,65535)})
    for t,level in pairs:
        for i in range(8):
            case=vr.classify_case(t,dict(item_level=level,option1=0,ext=0,quality=5,
                time=vr.f2u(i*13579.5),render_type=2))
            case['alpha']=vr.f2u((i+1)/9);case['light']=[vr.f2u((i+1)/7)]*3
            native_case=dict(case,item_level=(level>>3)<<3)
            status,expected=vr.c_stream(lib,native_case,generic=False)
            if status != 0:
                recipes.note(fam,False,dict(type=t,level=level,status=status))
                continue
            run,stream,other,_=vr.client_stream(args,case)
            recipes.note(fam,run['ok'] and stream==expected and not other,
                dict(type=t,level=level,stream=stream,expected=expected,other=other))
    return fam

def hardcase_requests(args,machine):
    fam=recipes.family();records=[]
    for cl in (1,5,10):
        row=constructor(machine,cl);bones=vr.extract_link_bones(args,[row['model']])[row['model']]
        for world_id in (0,3,2,51):
            old=vr.CHAR_SKIPS;old_world=vr.World
            def world(*world_args):
                w=old_world(*world_args)
                def sprite(m):
                    values=[m.arg(i) for i in range(4)]
                    w.calls.append(('sprite-request',dict(site=m.r32(m.uc.reg_read(m.x86.UC_X86_REG_ESP))-5,
                        type=values[0],scale=values[2],position=list(struct.unpack('<3I',m.read(values[1],12))),
                        light=list(struct.unpack('<3I',m.read(values[3],12))))))
                    return 0
                w.m.stub(0x01692eb7,sprite,0)
                return w
            try:
                vr.World=world
                vr.CHAR_SKIPS={a:n for a,n in old.items() if a not in (0x01362f24,0x01363098)}
                run,calls,w=monsters.client_plan(args,row,bones,cl,0,world_id,vr.f2u(.375),vr.f2u(.25))
            finally:vr.CHAR_SKIPS=old;vr.World=old_world
            sprites=[c[1] for c in w.calls if c[0]=='sprite-request']
            links=[c for c in calls if c[0]=='LINK']
            ok=run['ok'] and len(sprites)==1 and sprites[0]['type']==0x7ef7 and sprites[0]['scale']==vr.f2u(1.4) and len(links)==mask(row).bit_count()
            detail=dict(cl=cl,world=world_id,sprites=sprites,links=links,
                refusal='link caller records request; weapon pose/sprite placement and slot phase not certified')
            recipes.note(fam,ok,detail);records.append(detail)
    return fam,records

def missing_groups(decisions):
    current={r['server_class']:r for r in decisions};groups=collections.defaultdict(list)
    for item in plain.initial_rows():
        cl=int(item['server_class'])
        if item['decision']=='checked plain body plan':
            name='checked ordinary monster body' if item['group']=='plain monster body' else 'checked repeated default body'
            state='checked bounded body plan'
        else:
            r=current[cl];name=r['before_group'];state='incomplete'
            if r['decision']=='checked group body plan':name='checked group: '+name;state='checked bounded body plan'
        groups[(name,state)].append(cl)
    return [dict(missing_or_checked_plan=name,state=state,count=len(classes),selectors=';'.join(map(str,classes)))
            for (name,state),classes in sorted(groups.items())]

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--generate',action='store_true');ap.add_argument('--mutations',action='store_true')
    ap.add_argument('--cases',type=int,default=200);ap.add_argument('--output',type=Path,required=True);opts=ap.parse_args();start=time.monotonic()
    args=tuple(getattr(pins,k).read() for k in ('TEXT','DATA','FLAG','FEATURE')); machine=am.ActorMachine(*args[:2]);lib=library();authored=va.Authored(recipes.LIBRARY)
    rows={}; reasons={}; diagnostics={}; fams={'defaults':recipes.check_kind_default(args)}
    pop=population()
    with (DECISIONS if DECISIONS.exists() else ROOT/'docs/research/actor-missing-plan-groups.csv').open() as f:
        old=list(csv.DictReader(f))
    before_groups=({int(r['server_class']):r['before_group'] for r in old} if old and 'before_group' in old[0] else
        {int(cl):r['missing_or_checked_plan'] for r in old for cl in r['selectors'].split(';')})
    for item in pop:
        cl=int(item['server_class']);row=constructor(machine,cl);diagnostics[cl]={'constructor':row}
        if 'error' in row:reasons[cl]='constructor unresolved; '+item['reason'];continue
        native=lib.mu_monster_class_find(cl)
        if not native:reasons[cl]='no class-table row';continue
        n=native.contents
        if row['model']!=n.model or row['scale_bits']!=n.scale_bits or row['class_byte']!=n.class_byte or \
            [list(s) for s in row['slots']] != [[s.type,s.level] for s in n.slots]:raise RuntimeError(('constructor table differs',cl))
        if any(a not in (0x60,0x68,0x74,0xa8) for a in row['appearance_writes']):
            reasons[cl]='constructor render-state override: '+','.join(hex(a) for a in row['appearance_writes']);continue
        if cl in (361,937,939,940,941):
            reasons[cl]='cloth/world-selected appearance remains unchecked';continue
        if row['creates']!=1 or row['object_kind']!=1 or row['class_byte']!=0 or row['joints'] or \
            len(row['opens'])!=1 or any(t not in (0,65535) for t,lv in row['slots'][:6]+row['slots'][8:]) or \
            row['opens'][0][0] not in ('monster','npc'):
            reasons[cl]='constructor needs appearance/part/secondary proof; '+item['reason'];continue
        ok,reason=opener(machine,lib,authored,row)
        if not ok:reasons[cl]=reason;continue
        bones=vr.extract_link_bones(args,[row['model']])[row['model']];missing=set();details=[]
        for wi,w in enumerate((0,3,2,51)):
            for action in range(7):
                ok,detail=caller(args,row,bones,w,action,(.125,.375,.75,1)[wi],action+.25)
                if not ok:missing.add(detail['reason']);details.append(detail)
        diagnostics[cl]['caller_failures']=details
        if missing:reasons[cl]='; '.join(sorted(missing));continue
        reader_checks=[]
        for world in (0,3,2,51):
            for alpha in (.375,.75):
                ok,detail=body_reader.check(machine,row,world,alpha,.25)
                reader_checks.append((ok,detail))
        diagnostics[cl]['body_reader']=reader_checks
        if not all(ok for ok,detail in reader_checks):
            reasons[cl]='original RenderObject appearance reader differs';continue
        rows[cl]=row
    print('caller candidates',len(rows),'rejected',dict(collections.Counter(reasons.values())),flush=True)
    model_checks=plain.draw_checks(args,rows)
    for cl,row in list(rows.items()):
        f=model_checks[row['model']]
        if f['equal']!=f['cases']:reasons[cl]='body stream differs from one textured pass';del rows[cl]
    bones=vr.extract_link_bones(args,sorted({r['model'] for r in rows.values()}))
    link_checks={}; weapon_draw={}
    for cl,row in list(rows.items()):
        if not mask(row): continue
        link_checks[cl]=monsters.check_links(args,{cl:row},bones)
        if link_checks[cl]['equal']!=link_checks[cl]['cases']:
            reasons[cl]='additional or different RenderLinkItem services';del rows[cl];continue
        for t,lv in row['slots'][6:8]:
            if t in (0,65535):continue
            pair=(t,lv)
            if pair not in weapon_draw:
                weapon_draw[pair]=weapon_draw_checks(args,{cl:dict(row,slots=[(0,0)]*6+[(t,lv),(0,0),(0,0)])})
            f=weapon_draw[pair]
            if f['equal']!=f['cases']:
                reasons[cl]='weapon RenderObjDraw stream unavailable or extra services';rows.pop(cl,None)
    with tempfile.TemporaryDirectory() as tmp:
        host=build_host(tmp,rows if opts.generate else None);checks=native_checks(host,rows)
        for cl,(ok,detail) in checks.items():
            diagnostics[cl]['native']=detail
            if not ok:reasons[cl]='native file/texture/geometry/plan check failed';del rows[cl]
        if not rows:raise RuntimeError('no candidate passed')
        equipped={cl:r for cl,r in rows.items() if mask(r)}
        host=build_host(tmp,rows if opts.generate else None,weapon=True)
        f=weapon_checks(host,equipped,bones)
        # Every failing row remains incomplete; keep successful other groups.
        if f['equal']!=f['cases']:
            # Repeat individually to identify all failures beyond diagnostic cap.
            for cl,r in list(equipped.items()):
                one=weapon_checks(host,{cl:r},bones)
                if one['equal']!=one['cases']:reasons[cl]='native hand pose/texture/draw check failed';del rows[cl]
        equipped={cl:r for cl,r in rows.items() if mask(r)}
        fams['weapons']=f if f['equal']==f['cases'] else weapon_checks(host,equipped,bones)
        fams['links']=recipes.family();fams['weapon_draw']=recipes.family()
        for cl in equipped:
            f=link_checks[cl]
            for key in ('cases','equal'):fams['links'][key]+=f[key]
        for pair in {(t,lv) for r in equipped.values() for t,lv in r['slots'][6:8] if t not in (0,65535)}:
            f=weapon_draw[pair]
            for key in ('cases','equal'):fams['weapon_draw'][key]+=f[key]
        if opts.generate:TABLE.write_text(emit(rows))
        else:
            fams['plans']=check_plans(lib,rows)
            fams['reproduce']=recipes.family();recipes.note(fams['reproduce'],TABLE.read_text()==emit(rows),dict(rows=len(rows)))
        decisions=[dict(server_class=int(i['server_class']),group=i['group'],before_group=before_groups[int(i['server_class'])],previous_reason=i['reason'],
            decision='checked group body plan' if int(i['server_class']) in rows else 'incomplete',
            reason=reasons.get(int(i['server_class']),'')) for i in pop]
        if opts.generate:
            with DECISIONS.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(decisions[0]),lineterminator='\n');w.writeheader();w.writerows(decisions)
            groups=missing_groups(decisions)
            with (ROOT/'docs/research/actor-missing-plan-groups.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(groups[0]),lineterminator='\n');w.writeheader();w.writerows(groups)
        else:
            with DECISIONS.open() as f:old=list(csv.DictReader(f))
            normalized=[dict(r,server_class=str(r['server_class'])) for r in decisions]
            recipes.note(fams['reproduce'],old==normalized,dict(decisions=len(decisions)))
            with (ROOT/'docs/research/actor-missing-plan-groups.csv').open() as f:group_rows=list(csv.DictReader(f))
            expected_groups=[{k:str(v) for k,v in r.items()} for r in missing_groups(decisions)]
            recipes.note(fams['reproduce'],group_rows==expected_groups,dict(groups=len(expected_groups)))
        for name,factor in [('constructors',1),('openers',6),('callers',28),('native',1),('body_reader',8)]:
            fams[name]=dict(cases=len(rows)*factor,equal=len(rows)*factor,first_failures=[])
        fams['draw']=recipes.family()
        for model in {r['model'] for r in rows.values()}:
            f=model_checks[model];fams['draw']['cases']+=f['cases'];fams['draw']['equal']+=f['equal']
        varied=recipes.family();classes=list(rows)
        for i in range(opts.cases):
            r=rows[classes[i%len(classes)]];ok,detail=caller(args,r,bones[r['model']],(0,3,2,51)[i%4],i%7,(i%8+1)/9,i%6+.25)
            recipes.note(varied,ok,detail)
        fams['varied']=varied
        fams['hardcase_requests'],hardcases=hardcase_requests(args,machine)
        fams['secondary_requests']=monsters.check_secondary(args,machine)
        mutants={}
        if opts.mutations:
            src=(ROOT/'reconstructed/actors/actors.c').read_text()
            for name,old,new in [('admission','if (server_class < 0) return 0; /* group plan */','if (server_class != 231) return 0; /* group plan */'),
                ('overadmission','if (server_class < 0) return 0; /* group plan */','if (server_class == 374) return 1; if (server_class < 0) return 0; /* group plan */'),
                ('model','*out = mu_actor_group_plans[lo];','*out = mu_actor_group_plans[lo]; out->body.model++;'),
                ('texture','*out = mu_actor_group_plans[lo];','*out = mu_actor_group_plans[lo]; out->textures="Data/Item";'),
                ('weapon_mask','*out = mu_actor_group_plans[lo];','*out = mu_actor_group_plans[lo]; out->weapon_mask=0;'),
                ('scale','*out = mu_actor_group_plans[lo];','*out = mu_actor_group_plans[lo]; out->body.scale_bits++;'),
                ('file','*out = mu_actor_group_plans[lo];','*out = mu_actor_group_plans[lo]; out->file="Data/Item/unknown.bmd";'),
                ('flags','*out = mu_actor_group_plans[lo];','*out = mu_actor_group_plans[lo]; out->body.flags=0x44;'),
                ('translate','*out = mu_actor_group_plans[lo];','*out = mu_actor_group_plans[lo]; out->body.translate=0;'),
                ('blend_mesh','*out = mu_actor_group_plans[lo];','*out = mu_actor_group_plans[lo]; out->blend_mesh=-2;'),
                ('hidden_mesh','*out = mu_actor_group_plans[lo];','*out = mu_actor_group_plans[lo]; out->hidden_mesh=-2;'),
                ('blend_light','*out = mu_actor_group_plans[lo];','*out = mu_actor_group_plans[lo]; out->blend_light_bits=0;'),
                ('subtype','*out = mu_actor_group_plans[lo];','*out = mu_actor_group_plans[lo]; out->subtype++;')]:
                assert src.count(old)==1;path=Path(tmp)/'actors.c';path.write_text(src.replace(old,new));target=Path(tmp)/(name+'.dylib')
                recipes.build_library(path,target);f=check_plans(library(target),rows);mutants[name]=dict(caught=f['equal']<f['cases'],stopped=0)
            src=(ROOT/'native/core/mu_world_actors.c').read_text()
            sample_ids=[next(c for c,r in rows.items() if mask(r)),next(c for c,r in rows.items() if r['blend_mesh']!=-1),next(c for c,r in rows.items() if r['hidden_mesh']!=-1)]
            sample={cl:rows[cl] for cl in sample_ids}
            for name,old,new in [('load_links','if (!player && load_weapons','if (player && load_weapons'),
                ('native_translate','p.transform_translate = (uint8_t)group_plan.body.translate;','p.transform_translate = 0;'),
                ('alpha','options->alpha = alpha; /* plain plan */','options->alpha = 1; /* plain plan */'),
                ('native_flags','options->flags = plan.flags;','options->flags = 0;'),
                ('native_blend','options->select = group.blend_mesh;','options->select = -1;'),
                ('native_hidden','options->skip_mesh = group.hidden_mesh;','options->skip_mesh = -1;'),
                ('native_subtype','memcpy(a->actor.object + 0x60, &group_plan.subtype, 4);','memset(a->actor.object + 0x60, 1, 4);')]:
                assert src.count(old)==1;path=Path(tmp)/'mu_world_actors.c';path.write_text(src.replace(old,new))
                result=native_checks(build_host(tmp,source=path),sample);stops=sum('native_exit' in d for ok,d in result.values())
                mutants[name]=dict(caught=not stops and any(not ok for ok,d in result.values()),stopped=stops)
    report=dict(pins={k.lower():getattr(pins,k).sha256 for k in ('TEXT','DATA','FLAG','FEATURE')},families=fams,
        hardcase_refusals={'sword_sprite':3,'type226_consumer':2},hardcase_requests=hardcases,
        admitted=len(rows),equipped=len(equipped),distinct_models=len({r['model'] for r in rows.values()}),
        rejected=dict(collections.Counter(reasons.values())),decisions=decisions,diagnostics=diagnostics,
        cases=sum(f['cases'] for f in fams.values()),all_equal=all(f['cases']==f['equal'] for f in fams.values()),
        mutants=mutants,all_mutants_caught=all(m['caught'] for m in mutants.values()),wall_seconds=time.monotonic()-start)
    opts.output.parent.mkdir(parents=True,exist_ok=True);opts.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('diagnostics','decisions')}))
    return 0 if report['all_equal'] and report['all_mutants_caught'] else 1

if __name__=='__main__':raise SystemExit(main())
