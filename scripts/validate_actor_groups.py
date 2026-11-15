#!/usr/bin/env python3
"""RENDER-ACTORS-007/008: uniform verifier for NPC, link and caller-service groups.

All 355 initial incomplete selectors retain a decision. Constructor state,
original opener arguments/speeds, full callers, draw streams and actual native
assets must pass separately. RenderObject is a named pose/body boundary;
stateful processors decline. Appearance overrides and extra services fail closed.

ACTORS-008 records every caller's ordered sprite/particle/joint/effect requests
with bone-resolved positions (actor_caller_requests) and each hand's
RenderLinkItem services. A row is admitted only when all of its requests are
object-bone sprites whose light follows a compiled constant/flicker/pulse model
and whose bitmap has a native consumer; every other row keeps its recorded ids.
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
import actor_caller_requests as acr

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
FX_TABLE = ROOT/'reconstructed/actors/caller_fx_table.h'
REQUESTS = ROOT/'docs/research/actor-caller-requests.csv'
COMMON_RAND = 0x0136ac06  # RenderCharacter's one flicker value per call
LINK_RAND = 0x012c6aa1    # RenderLinkItem's one intensity value per call; unused without link requests

class Plan(C.Structure):
    _fields_ = [('body', plain.Plan), ('file', C.c_char_p), ('textures', C.c_char_p), ('weapon_mask', C.c_uint32), ('blend_mesh', C.c_int32), ('hidden_mesh', C.c_int32),
                ('blend_light_bits', C.c_uint32), ('subtype', C.c_uint32),
                ('link_effect_mask', C.c_uint32)]

class Fx(C.Structure):
    _fields_ = [('server_class', C.c_int32), ('bitmap', C.c_int32), ('bone', C.c_int32), ('offset_bits', C.c_uint32*3),
                ('scale_bits', C.c_uint32), ('light_kind', C.c_int32), ('colour_bits', C.c_uint32*3), ('base_bits', C.c_uint32),
                ('owner', C.c_int32), ('rotation_bits', C.c_uint32), ('blend', C.c_int32), ('axes', C.c_int32)]

class Npc(C.Structure):
    _fields_ = [('index', C.c_uint16), ('directory', C.c_char_p), ('name', C.c_char_p),
                ('number', C.c_int32), ('speed_bits', C.c_uint32*16)]

def library(path=recipes.LIBRARY):
    lib = plain.library(path)
    lib.mu_actor_group_plan.argtypes = [C.c_int32, C.POINTER(Plan)]
    lib.mu_npc_find.argtypes = [C.c_uint32]; lib.mu_npc_find.restype = C.POINTER(Npc)
    lib.mu_monster_class_find.argtypes = [C.c_uint32]; lib.mu_monster_class_find.restype = C.POINTER(recipes.Row)
    lib.mu_actor_caller_fx_plan.argtypes = [C.c_int32, C.POINTER(C.POINTER(Fx))]
    lib.mu_actor_caller_fx_light.argtypes = [C.POINTER(Fx), C.c_float, C.c_int32, C.POINTER(C.c_float*3)]
    lib.mu_actor_caller_fx_light.restype = None
    return lib

def population():
    # ACTORS-006 decisions remain immutable. This lane's decisions are separate.
    return [r for r in plain.initial_rows() if r['decision'] == 'incomplete']

def mask(row):
    return sum(1 << k for k,(t,_) in enumerate(row['slots'][6:8]) if t not in (0,65535))

def link_mask(row):
    return sum(1<<k for k,n in row.get('link_fx',{}).items() if n)

def link_generator(t,clock,rand):
    """The renderchar link consumer's request list for one item type (native dispatch order)."""
    import validate_item_clusters as clusters
    import validate_item_types as types
    lib=C.CDLL(str(vr.LIBRARY))
    status,calls,used=clusters.c_effects(lib,t,[rand]*64,clock)
    if status==0:return [c for c in calls]
    status,calls=types.c_link(lib,t,rand)
    if status!=0:return None
    return [(c[0],c[1],(0,0,0),c[2],c[3],c[4],c[5],c[6],0) for c in calls]

def link_recorded(fx):
    """Recorded RenderLinkItem requests in the generator's form; None outside its sprite form."""
    out=[]
    for r in fx:
        p=r.get('position') or {}
        if r['service']!='sprite' or p.get('kind')!='pose-bone' or p.get('translate')!=1 or r['light'] is None:return None
        out.append((r['id'],p['bone'],tuple(p['offset']),r['scale'],tuple(r['light']),r['rotation'],r['blend'],r['axes'],0))
    return out

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
    row.update(world_mask=[0]*8)
    restricted = False
    if not ok and 'reason' not in detail:
        ok, detail = world_opener(machine,authored,row); restricted = ok
    if ok:
        row.update(file=f"Data/Monster/Monster{row['opens'][0][1]+1:02d}.bmd",textures='Data/Npc' if restricted else 'Data/Monster')
    return ok, '' if ok else detail.get('reason','monster opener has extra load or different texture context')

def world_opener(machine, authored, row):
    """One own model whose only world dependence is the Monster or Npc texture directory.

    Every world byte 0..255 executes the original opener and the compiled one. Data/Monster
    lacks these models' mesh bitmaps, so the row's later caller contexts run only in the
    Npc-directory worlds (world_mask). No native plan is generated for such a row yet:
    it stays incomplete with whatever its caller sends there.
    """
    t = row['opens'][0][1]; mask = [0]*8
    for world in range(256):
        case = va.monster_case(str(t), t, actions=16, world=world)
        run = va.run_client_open(machine, case); native = authored.run_open(case)
        access = ('access', row['model'], 'Data\\Monster\\', 'Monster', t+1)
        texture = [c for c in run['calls'] if c[0] == 'texture']
        if not run['ok'] or native['status'] != 0 or native['calls'] != run['calls'] or len(run['calls']) != 2 or \
            run['calls'][0] != access or len(texture) != 1 or texture[0][1] != row['model'] or \
            texture[0][2] not in ('Monster\\', 'Npc\\') or texture[0][3:] != (0x2901, 0x2600) or \
            any(c[0] == 'bitmap' for c in run['loaders']) or any(run['regions'].get(k) != v for k,v in native['regions'].items()) or \
            run['regions']['model0'][0x94:0x98] != bytes(case['regions'][0].data[0x94:0x98]):
            return False, dict(cl=row['class'], world=world)
        if texture[0][2] == 'Npc\\': mask[world//32] |= 1 << (world%32)
    if not any(mask): return False, dict(cl=row['class'])
    row.update(world_mask=mask)
    return True, None

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

def caller(args,row,bones,world,action,alpha,frame,clock=0.0,rand=0):
    old = vr.CHAR_SKIPS;old_record=vr.character_record;state={}
    def record(**kw):
        raw=old_record(**kw)
        # Carry every constructor-written appearance field, whole, into the caller's OBJECT.
        for a,n in plain.APPEARANCE_FIELDS:
            if any(a-3<=off<a+n for off in row['appearance_writes']):
                raw[0x3254+a:0x3254+a+n]=bytes.fromhex(row['appearance_state'][a])
        return raw
    try:
        vr.character_record=record
        vr.CHAR_SKIPS = {a:n for a,n in old.items() if a not in (0x01362f24,0x01363098)}
        with acr.recording(clock,rand,state):
            run,calls,w = monsters.client_plan(args,row,bones,row['class'],action,world,vr.f2u(alpha),vr.f2u(frame))
    finally: vr.CHAR_SKIPS = old;vr.character_record=old_record
    links = [c for c in calls if c[0]=='LINK']
    # RenderCharacter's weapon selector 0x0136b6c4.. may store an animation speed in the part
    # (swords: Player action 1's speed, the authored 0.25 here) with action/frame/prior zero.
    # The speed is kept as recorded; native admission then requires a one-key weapon action.
    speeds = [c[12] for c in links]
    expected = [('LINK',k,t,lv,0,(0,0,0),0,1,0,1,bones[k],0,speeds[i] if i<len(speeds) else 0,0,0)
        for i,(k,(t,lv)) in enumerate((k,s) for k,s in enumerate(row['slots'][6:8]) if s[0] not in (0,65535))]
    shadows = [c for c in calls if c[0]=='SHADOW']
    base = [c for c in w.calls if c[0]=='base-body']
    extra = [c for c in w.calls if c[0] not in ('base-body','RPO','skip','LINK','request')]
    ok = run['ok'] and links == expected and len(calls)==len(links)+len(shadows) and \
        len(shadows)<=1 and all(c==('SHADOW',row['model'],1) for c in shadows) and not extra and \
        base==[('base-body',[vr.CHAR+0x3254,1,0,0,0xffffffff,0xffffffff])]
    parts = sorted({'model %#x slot %d'%(c[2],c[1]) for c in calls if c[0]=='PART'})
    reason = 'unresolved caller at '+str(run.get('pc')) if not run['ok'] else \
        'additional caller services: '+','.join(sorted({c[0] for c in extra})) if extra else \
        'additional caller RenderPartObject in world %d: %s'%(world,'; '.join(parts)) if parts and any(row.get('world_mask',[0]*8)) else \
        'caller body/link/pass arguments differ' if not ok else ''
    return ok,dict(cl=row['class'],world=world,action=action,clock=clock,rand=rand,reason=reason,calls=calls,extra=extra,
                   link_speeds={c[1]:c[12] for c in links},
                   requests=acr.requests(w.calls),rand_sites=state.get('rand_sites',[]),
                   stop=None if run['ok'] else str(run)[:500])

def worlds(row):
    """Four fixture worlds: 0/3/2/51, or the first worlds of a world-restricted plan."""
    masked=[w for w in range(256) if row.get('world_mask',[0]*8)[w//32]>>(w%32)&1]
    return tuple(masked[i%len(masked)] for i in range(4)) if masked else (0,3,2,51)

def contexts(row):
    """The 28 published world/action contexts, then six clock/random variations."""
    ws=worlds(row)
    out=[(w,action,(.125,.375,.75,1)[wi],action+.25,0.0,0) for wi,w in enumerate(ws) for action in range(7)]
    return out+[(ws[i%4],(0,2,3,6,1,4)[i],.375,i+.25,clock,rand) for i,(clock,rand) in enumerate(acr.VARIED)]

def fx_plan(observations, consumers):
    """Admission plan for a caller's requests, or the exact reason it is not uniform."""
    base=observations[0]['requests'];keys=[acr.structure(r) for r in base]
    if not any(o['requests'] for o in observations): return [], ''
    if any([acr.structure(r) for r in o['requests']]!=keys for o in observations):
        return None,'caller requests vary with action, world, clock or random value'
    outside=sorted({r['service'] if r['service']!='sprite' else 'computed-position sprite' for r in base if not acr.uniform(r)})
    if outside: return None,'caller requests outside the object-bone sprite program: '+','.join(outside)
    if {s for o in observations for s in o['rand_sites']}-{COMMON_RAND}:
        return None,'caller program consumes further random values'
    plan=[]
    for i,r in enumerate(base):
        fit=acr.fit_light([(o['clock'],o['rand'],o['requests'][i]['light']) for o in observations])
        if not fit: return None,'caller sprite light outside the constant, flicker and pulse models'
        p=r['position']
        plan.append(dict(bitmap=r['id'],bone=p['bone'],offset=p['offset'],scale=r['scale'],kind=fit[0],colour=fit[1],
            base=fit[2],owner=r['owner'],rotation=r['rotation'],blend=r['blend'],axes=r['axes']))
    missing=sorted({p['bitmap'] for p in plan if not consumers(('sprite',p['bitmap'],0))})
    if missing: return None,'missing native consumer: '+','.join('sprite %#x'%b for b in missing)
    return plan,''

def fx_light(lib,cl,index,clock,rand):
    first=C.POINTER(Fx)();count=lib.mu_actor_caller_fx_plan(cl,C.byref(first));out=(C.c_float*3)()
    if index>=count: return None
    lib.mu_actor_caller_fx_light(C.byref(first[index]),clock,rand,C.byref(out))
    return [vr.f2u(v) for v in out]

def check_fx(lib,rows,observed):
    """Compiled request tables and light function against every recorded original context."""
    fam=recipes.family()
    for cl in range(-1,1025):
        first=C.POINTER(Fx)();count=lib.mu_actor_caller_fx_plan(cl,C.byref(first));plan=rows[cl]['fx'] if cl in rows else []
        actual=[(f.bitmap,f.bone,list(f.offset_bits),f.scale_bits,f.light_kind,list(f.colour_bits),f.base_bits,f.owner,
            f.rotation_bits,f.blend,f.axes) for f in (first[i] for i in range(count))]
        expected=[(p['bitmap'],p['bone'],p['offset'],p['scale'],p['kind'],p['colour'],p['base'],p['owner'],p['rotation'],
            p['blend'],p['axes']) for p in plan]
        recipes.note(fam,actual==expected,dict(cl=cl,actual=actual[:3],expected=expected[:3]))
        if cl not in rows or not plan: continue
        for o in observed[cl]:
            lights=[fx_light(lib,cl,i,o['clock'],o['rand']) for i in range(len(plan))]
            recipes.note(fam,lights==[r['light'] for r in o['requests']],dict(cl=cl,clock=o['clock'],rand=o['rand'],lights=lights))
    return fam

def emit_fx(rows):
    lines=['/* Generated by validate_actor_groups.py --generate after original/native checks.',
           ' * One CreateSprite 0x01692eb7 per row at TransformPosition(OBJECT bone, offset, translate 1). */',
           'static const mu_actor_caller_fx mu_actor_caller_fx_rows[] = {']
    for cl,r in sorted(rows.items()):
        for p in r['fx']:
            lines.append('    {%d, %#x, %d, {%#xu, %#xu, %#xu}, %#xu, %d, {%#xu, %#xu, %#xu}, %#xu, %d, %#xu, %d, %d},' %
                (cl,p['bitmap'],p['bone'],*p['offset'],p['scale'],p['kind'],*p['colour'],p['base'],p['owner'],p['rotation'],p['blend'],p['axes']))
    return '\n'.join(lines+['    {-1, 0, 0, {0u, 0u, 0u}, 0u, 0, {0u, 0u, 0u}, 0u, 0, 0u, 0, 0}','};',''])

def check_links(args,row,bones):
    """RenderLinkItem from entry per selected hand: services, level shift and untouched OBJECT bones."""
    fam=recipes.family();found=[]
    for k,(t,level) in enumerate(row['slots'][6:8]):
        if t in (0,65535):continue
        for alpha in (.125,.375,.75,1.0):
            run,w,fx,writes,sites=acr.link_requests(args,row,bones,k,alpha,watch_bones=True)
            calls=[c for c in w.calls if c[0] not in ('skip','request')];names=[c[0] for c in calls]
            draw=[c for c in calls if c[0]=='objdraw'];poses=[c for c in calls if c[0]=='pose'];transforms=[c for c in calls if c[0]=='transform']
            # A hand's own requests are admitted only as the checked link consumer's exact list,
            # here and at three further clock/random fixtures.
            generated=True
            if fx:
                for clock,rand in ((0.0,0),)+acr.VARIED[:3]:
                    again=fx if (clock,rand)==(0.0,0) else acr.link_requests(args,row,bones,k,alpha,clock,rand)[2]
                    recorded=link_recorded(again);expected=link_generator(t,clock,rand)
                    generated=generated and recorded is not None and expected is not None and recorded==[tuple(e) for e in expected]
            ok=run['ok'] and names==['rotpos','tick','pose','transform','objdraw'] and generated and not writes and set(sites)<={LINK_RAND} and \
                draw[0][1][1]==t and draw[0][1][3:9]==[vr.f2u(alpha),level<<3,0,0,0,2] and \
                poses[0][2][1:4]==[0,0,0] and poses[0][2][-2:]==[1,1] and \
                transforms[0][2][4:]==[1,0,vr.f2u(.4),vr.f2u(.8),vr.f2u(.2)] and w.m.read(vr.MODEL+0x50,1)==b'\0'
            recipes.note(fam,ok,dict(cl=row['class'],slot=k,names=names,requests=len(fx),bone_writes=len(writes)))
            if alpha==.375:found.append(dict(slot=k,type=t,level=level,ok=run['ok'],names=names,requests=fx,generated=generated,bone_writes=len(writes),
                rand_sites=sites,draw_level=draw[0][1][4] if draw else None))
    return fam,found

def emit(rows):
    lines=['/* Generated by validate_actor_groups.py --generate after original/native checks. */',
           'static const mu_actor_group_body_plan mu_actor_group_plans[] = {']
    for cl,r in sorted(rows.items()):
        world=''
        lines.append('    {{%d, %#x, %d, %#xu, 2, 1}, "%s", "%s", %du, %d, %d, %#xu, %#xu%s, %du},' %
            (cl,r['model'],r['opens'][0][1],r['scale_bits'] or vr.f2u(.9),r['file'],r['textures'],mask(r),r['blend_mesh'],r['hidden_mesh'],r['blend_light_bits'],r['subtype'],world,
             link_mask(r)))
    return '\n'.join(lines+['};',''])

def check_plans(lib,rows):
    fam=recipes.family()
    for cl in range(-1,1025):
        p=Plan(); status=lib.mu_actor_group_plan(cl,C.byref(p)); r=rows.get(cl)
        expected=(cl,r['model'],r['opens'][0][1],r['scale_bits'] or vr.f2u(.9),2,1) if r else None
        actual=tuple(getattr(p.body,n) for n,_ in plain.Plan._fields_)
        recipes.note(fam,status==int(r is not None) and (not r or actual==expected and p.file.decode()==r['file'] and
            p.textures.decode()==r['textures'] and p.weapon_mask==mask(r) and (p.blend_mesh,p.hidden_mesh,p.blend_light_bits,p.subtype)==
                (r['blend_mesh'],r['hidden_mesh'],r['blend_light_bits'],r['subtype']) and
                p.link_effect_mask==link_mask(r)),
                dict(cl=cl,actual=actual,expected=expected))
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
'''+emit_fx(rows).replace('mu_actor_caller_fx_rows','bootstrap_fx')+'''
static int32_t bootstrap_fx_plan(int32_t cl, const mu_actor_caller_fx **first) {
    int32_t count = 0;
    for (size_t i=0;i+1<sizeof bootstrap_fx/sizeof bootstrap_fx[0];++i)
        if (bootstrap_fx[i].server_class==cl) { if(!count && first)*first=&bootstrap_fx[i]; ++count; }
    return count;
}
#define mu_actor_caller_fx_plan bootstrap_fx_plan
static int bootstrap_fx_random(int32_t cl) {
    const mu_actor_caller_fx *fx = NULL; int32_t count = bootstrap_fx_plan(cl, &fx);
    for (int32_t i=0;i<count;++i) if (fx[i].light_kind==MU_ACTOR_FX_FLICKER) return 1;
    return 0;
}
#define mu_actor_caller_fx_random bootstrap_fx_random
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

def native_worlds(row):
    return [0]

def native_checks(host,rows):
    result={}
    # One process per selector isolates pre-existing unsafe assets and publishes
    # only after host cleanup. No native crash is a successful negative control.
    for cl,row in rows.items():
        ok=True;v={}
        for world in native_worlds(row):
            run=subprocess.run([str(host),os.environ['MU_GAME_ROOT']],input='%d %d\n'%(cl,world),capture_output=True,text=True)
            v=json.loads(run.stdout) if run.returncode==0 and run.stdout else dict(native_exit=run.returncode)
            ok=ok and v.get('model')==row['model'] and abs(v.get('scale',0)-vr.u2f(row['scale_bits'] or vr.f2u(.9)))<1e-7 and \
                v.get('file','').lower()==row['file'].lower() and v.get('missing')==0 and v.get('textures_equal')==1 and \
                v.get('meshes',0)>0 and v.get('vertices',0)>0 and v.get('status')==0 and v.get('refused')==0 and \
                v.get('alpha')==[.375,.375] and v.get('admitted')==1 and v.get('flags')==2 and v.get('attach')==mask(row) and \
                v.get('transform_translate')==1 and v.get('guards')==[0,0,0,0] and v.get('guard_options')==[1,1,1,1] and v.get('plan_state_equal')==1 and \
                v.get('world')==world and v.get('fx')==len(row['fx']) and v.get('fx_equal')==1 and v.get('fx_assets')==1 and v.get('fx_guards')==[0,0,0,0]
            if not ok:break
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
                else:ok &= part is not None and part['type']==t and part['level']==row['slots'][6+k][1] and part['bone']==bones[row['model']][k] and part['missing']==0 and \
                    (part['keys']==1 or not row['link_speeds'].get(k)) and \
                    part['link_fx']==row['link_fx'].get(k,0) and part['link_assets']==1 and \
                    part['same_pose']==1 and part['body_pose_same']==1 and part['vertices']>0 and part['refused']==0
            recipes.note(fam,ok,v)
    return fam

def weapon_draw_checks(args,rows):
    lib=C.CDLL(str(vr.LIBRARY));fam=recipes.family()
    pairs=sorted({(t,lv) for r in rows.values() for t,lv in r['slots'][6:8] if t not in (0,65535)})
    for t,level in pairs:
        for i in range(8):
            # RenderLinkItem passes its level argument << 3 (recorded per row by check_links).
            case=vr.classify_case(t,dict(item_level=level<<3,option1=0,ext=0,quality=5,
                time=vr.f2u(i*13579.5),render_type=2))
            case['alpha']=vr.f2u((i+1)/9);case['light']=[vr.f2u((i+1)/7)]*3
            status,expected=vr.c_stream(lib,case,generic=False)
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

def consumer_host(directory):
    d=Path(directory);n=ROOT/'native'
    subprocess.run(['clang','-std=c11','-O1','-iquote',str(n/'core'),'-I',str(n/'build/gen'),'-I',str(n/'session'),
        '-c',str(n/'tests/actor_consumer_host.c'),'-o',str(d/'consumer.o')],check=True,capture_output=True)
    subprocess.run(['clang++',str(d/'consumer.o'),str(n/'build/libmunative.a'),str(n/'build/libmusession_world.a'),
        '-L/opt/homebrew/opt/cryptopp/lib','-lcryptopp','-L/opt/homebrew/opt/jpeg-turbo/lib','-ljpeg',
        '-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation','-lm','-o',str(d/'consumer')],check=True,capture_output=True)
    return d/'consumer'

def consumer_answers(host,queries):
    queries=sorted(queries)
    run=subprocess.run([str(host)],input=''.join('%s %d %d\n'%q for q in queries),capture_output=True,text=True,check=True)
    answers=dict(zip(queries,map(int,run.stdout.split())))
    if len(answers)!=len(queries):raise RuntimeError('consumer host omitted answers')
    return answers

def consumer_query(r):
    if r['service'] in ('sprite','particle','joint'):return (r['service'],r['id'],r.get('subtype') or 0)
    return None

def request_rows(cl,prior,observations,links,opener_calls,answers,decision,reason,world_mask=None):
    """Published per-row request table: ordered distinct requests with their context counts."""
    out=[];base=dict(server_class=cl,actors007_reason=prior,decision=decision,reason=reason)
    def line(phase,order,**kw):
        row=dict(base,phase=phase,order=order,service='',id='',subtype='',call_site='',anchor='',offset='',scale='',light='',
            light_model='',owner='',rotation='',blend='',axes='',count='',contexts='',random_sites='',native_consumer='')
        row.update(kw);out.append(row)
    seen={};order=[]
    for o in observations:
        counts=collections.Counter();firsts={}
        for r in o['requests']:
            key=acr.structure(r);counts[key]+=1;firsts.setdefault(key,r)
        for key,n in counts.items():
            if key not in seen:seen[key]=dict(first=firsts[key],count=n,contexts=0,lights=set());order.append(key)
            e=seen[key];e['count']=max(e['count'],n);e['contexts']+=1
            e['lights'].update(tuple(r['light']) for r in o['requests'] if acr.structure(r)==key and r.get('light'))
    extra_sites=sorted({s for o in observations for s in o['rand_sites']}-{COMMON_RAND})
    stable=all([acr.structure(r) for r in o['requests']]==[acr.structure(r) for r in observations[0]['requests']] for o in observations)
    for i,key in enumerate(order):
        e=seen[key];r=e['first'];anchor,offset=acr.describe_anchor(r.get('position'))
        model=''
        if r['service']=='sprite' and stable and acr.uniform(r):
            index=[acr.structure(x) for x in observations[0]['requests']].index(key)
            fit=acr.fit_light([(o['clock'],o['rand'],o['requests'][index+k]['light']) for o in observations for k in (0,)])
            model=('constant','flicker (rand %% 30 + 70) * 0.01 at %#x'%COMMON_RAND,'pulse sin(clock * 0.002) * 0.3 + %s'%acr.hexf(fit[2]))[fit[0]] if fit else 'unmodelled'
        elif len(e['lights'])>1:model='varies'
        q=consumer_query(r)
        line('caller',i,service=r['service'],id='%#x'%r['id'] if r['id'] is not None else '',
            subtype='' if r.get('subtype') is None else r['subtype'],call_site='%#x'%r['site'],anchor=anchor,offset=offset,
            scale='' if r.get('scale') is None else acr.hexf(r['scale']),
            light=' '.join(acr.hexf(v) for v in r['light']) if r.get('light') else '',light_model=model,
            owner=('none','OBJECT','other')[r['owner']] if r.get('owner') is not None else '',
            rotation='' if r.get('rotation') is None else acr.hexf(r['rotation']),
            blend='' if r.get('blend') is None else r['blend'],axes='' if r.get('axes') is None else r['axes'],
            count=e['count'],contexts='%d/%d'%(e['contexts'],len(observations)),
            random_sites=' '.join('%#x'%s for s in extra_sites),
            native_consumer={None:'not queried',1:'yes',0:'no',-1:'not queried'}[answers.get(q) if q else None])
    for found in links:
        phase='link-right' if found['slot']==0 else 'link-left'
        line(phase,0,service='link draw',id='%#x'%found['type'],subtype=found['level'],
            scale='RenderObjDraw level %s'%found['draw_level'],count=1,
            contexts='services '+' '.join(found['names']),random_sites=' '.join('%#x'%s for s in sorted(set(found['rand_sites'])-{LINK_RAND})),
            native_consumer='yes' if found['ok'] and found.get('generated',True) else 'no')
        counts=collections.Counter(acr.structure(r) for r in found['requests']);done=set();n=1
        for r in found['requests']:
            key=acr.structure(r)
            if key in done:continue
            done.add(key);anchor,offset=acr.describe_anchor(r.get('position'));q=consumer_query(r)
            line(phase,n,service=r['service'],id='%#x'%r['id'] if r['id'] is not None else '',
                subtype='' if r.get('subtype') is None else r['subtype'],call_site='%#x'%r['site'],anchor=anchor,offset=offset,
                scale='' if r.get('scale') is None else acr.hexf(r['scale']),
                light=' '.join(acr.hexf(v) for v in r['light']) if r.get('light') else '',
                owner=('none','OBJECT','other')[r['owner']] if r.get('owner') is not None else '',
                rotation='' if r.get('rotation') is None else acr.hexf(r['rotation']),
                blend='' if r.get('blend') is None else r['blend'],axes='' if r.get('axes') is None else r['axes'],
                count=counts[key],contexts='alpha 0.375',
                native_consumer='yes, item link consumer' if found.get('generated') else 'no checked link consumer');n+=1
    for i,c in enumerate(opener_calls or []):
        if c[0]=='texture' and world_mask and any(world_mask):
            worlds=' '.join(str(w) for w in range(256) if world_mask[w//32]>>(w%32)&1)
            line('opener',i,service='texture directory',id='%#x'%c[1],anchor=c[2].replace('\\','/'),contexts='all other worlds 0..255')
            line('opener',i,service='texture directory',id='%#x'%c[1],anchor='Npc/',contexts='worlds '+worlds)
        elif c[0]=='access':line('opener',i,service='model',id='%#x'%c[1],anchor=(c[2]+c[3]+('' if c[4]==-1 else '%02d'%c[4])).replace('\\','/'))
        elif c[0]=='texture':line('opener',i,service='texture directory',id='%#x'%c[1],anchor=c[2].replace('\\','/'))
        elif c[0]=='bitmap':line('opener',i,service='bitmap',id=str(c[1:])[:80])
    return out

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--generate',action='store_true');ap.add_argument('--mutations',action='store_true')
    ap.add_argument('--requests-only',action='store_true',help='record and publish the request table; no admission or native stage')
    ap.add_argument('--cases',type=int,default=200);ap.add_argument('--output',type=Path,required=True);opts=ap.parse_args();start=time.monotonic()
    args=tuple(getattr(pins,k).read() for k in ('TEXT','DATA','FLAG','FEATURE')); machine=am.ActorMachine(*args[:2]);lib=library();authored=va.Authored(recipes.LIBRARY)
    rows={}; reasons={}; diagnostics={}; fams={'defaults':recipes.check_kind_default(args)}
    candidates={}; observed={}; link_results={}; opener_calls={}; gates={}
    pop=population()
    with (DECISIONS if DECISIONS.exists() else ROOT/'docs/research/actor-missing-plan-groups.csv').open() as f:
        old=list(csv.DictReader(f))
    before_groups=({int(r['server_class']):r['before_group'] for r in old} if old and 'before_group' in old[0] else
        {int(cl):r['missing_or_checked_plan'] for r in old for cl in r['selectors'].split(';')})
    # The ACTORS-007 reason of every row is frozen in its own column from the first ACTORS-008 generation on.
    prior={int(r['server_class']):r.get('actors007_reason',r.get('reason','')) for r in old} if old and 'server_class' in old[0] else {}
    prior_decision={int(r['server_class']):r.get('actors007_decision',r.get('decision','')) for r in old} if old and 'server_class' in old[0] else {}
    for item in pop:
        cl=int(item['server_class']);row=constructor(machine,cl);diagnostics[cl]={'constructor':row}
        if 'error' in row:reasons[cl]='constructor unresolved; '+item['reason'];continue
        native=lib.mu_monster_class_find(cl)
        if not native:reasons[cl]='no class-table row';continue
        n=native.contents
        if row['model']!=n.model or row['scale_bits']!=n.scale_bits or row['class_byte']!=n.class_byte or \
            [list(s) for s in row['slots']] != [[s.type,s.level] for s in n.slots]:raise RuntimeError(('constructor table differs',cl))
        gate=''
        if any(a not in (0x60,0x68,0x74,0xa8) for a in row['appearance_writes']):
            gate='constructor render-state override: '+','.join(hex(a) for a in row['appearance_writes'])
        elif cl in (361,937,939,940,941):
            gate='cloth/world-selected appearance remains unchecked'
        elif row['creates']!=1 or row['object_kind']!=1 or row['class_byte']!=0 or row['joints'] or \
            len(row['opens'])!=1 or any(t not in (0,65535) for t,lv in row['slots'][:6]+row['slots'][8:]) or \
            row['opens'][0][0] not in ('monster','npc'):
            gate='constructor needs appearance/part/secondary proof; '+item['reason']
        else:
            ok,reason=opener(machine,lib,authored,row)
            if not ok:gate=reason
        opener_calls[cl]=row.get('opener_calls')
        # Requests are recorded for every constructed selector, also behind an earlier gate:
        # the published ids do not depend on admission.
        try:bones=vr.extract_link_bones(args,[row['model']])[row['model']]
        except Exception:bones=None
        obs=[];missing=set();details=[]
        if bones is not None:
            plan=contexts(row)
            for i,(w,action,alpha,frame,clock,rand) in enumerate(plan):
                if i==28 and not any(o['requests'] for o in obs):break
                ok,detail=caller(args,row,bones,w,action,alpha,frame,clock,rand);obs.append(detail)
                if not ok:missing.add(detail['reason']);details.append({k:v for k,v in detail.items() if k!='requests'})
            if mask(row):link_results[cl]=check_links(args,row,bones)
        observed[cl]=obs;diagnostics[cl]['caller_failures']=details[:6]
        if gate:reasons[cl]=gate;continue
        if bones is None:reasons[cl]='link bones unresolved';continue
        if missing:
            # A world-selected row reports its lowest world's reason once.
            reasons[cl]=sorted(missing)[0] if any(row.get('world_mask',[0]*8)) else '; '.join(sorted(missing));continue
        if any(row.get('world_mask',[0]*8)):reasons[cl]='world-selected opener texture directory has no generated plan';continue
        candidates[cl]=row
    print('recorded',len(observed),'candidates',len(candidates),'gated',dict(collections.Counter(reasons.values())),flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        queries={q for obs in observed.values() for o in obs for r in o['requests'] for q in [consumer_query(r)] if q}
        queries|={q for f,found in link_results.values() for x in found for r in x['requests'] for q in [consumer_query(r)] if q}
        queries|={('link',x['type'],0) for f,found in link_results.values() for x in found}
        answers=consumer_answers(consumer_host(tmp),queries)
        for cl,row in candidates.items():
            plan,why=fx_plan(observed[cl],lambda q:answers.get(q)==1)
            if plan is None:reasons[cl]=why;continue
            row['fx']=plan;row['link_fx']={}
            speeds=[tuple(sorted(o['link_speeds'].items())) for o in observed[cl]]
            if len(set(speeds))!=1:reasons[cl]='caller link animation speed varies';continue
            row['link_speeds']=dict(speeds[0])
            reader_checks=[]
            for world in worlds(row):
                for alpha in (.375,.75):
                    ok,detail=body_reader.check(machine,row,world,alpha,.25)
                    reader_checks.append((ok,detail))
            diagnostics[cl]['body_reader']=reader_checks
            if not all(ok for ok,detail in reader_checks):
                reasons[cl]='original RenderObject appearance reader differs';continue
            rows[cl]=row
        print('caller candidates',len(rows),'rejected',dict(collections.Counter(reasons.values())),flush=True)
        def publish_requests(final):
            table=[]
            for item in pop:
                cl=int(item['server_class'])
                if cl not in observed:continue
                decision='checked group body plan' if cl in rows and final else 'incomplete' if final else 'recorded'
                table+=request_rows(cl,prior.get(cl,''),observed[cl],link_results.get(cl,(None,[]))[1],
                    opener_calls.get(cl) if prior.get(cl,'').startswith('monster opener') or reasons.get(cl,'').startswith('monster opener') else None,
                    answers,decision,reasons.get(cl,'') if final or cl in reasons else '',
                    diagnostics[cl]['constructor'].get('world_mask'))
            return table
        def write_requests(table):
            with REQUESTS.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(table[0]),lineterminator='\n');w.writeheader();w.writerows(table)
        if opts.requests_only:
            write_requests(publish_requests(False))
            print(json.dumps(dict(request_rows=sum(1 for _ in REQUESTS.open())-1,recorded=len(observed),wall_seconds=time.monotonic()-start)))
            return 0
        model_checks=plain.draw_checks(args,rows)
        for cl,row in list(rows.items()):
            f=model_checks[row['model']]
            if f['equal']!=f['cases']:reasons[cl]='body stream differs from one textured pass';del rows[cl]
        bones=vr.extract_link_bones(args,sorted({r['model'] for r in rows.values()}))
        link_checks={}; weapon_draw={}
        for cl,row in list(rows.items()):
            if not mask(row): continue
            link_checks[cl],found=link_results[cl]
            if link_checks[cl]['equal']!=link_checks[cl]['cases']:
                wanted=sorted({'item %#x: %d %s'%(x['type'],len(x['requests']),'/'.join(sorted({'%s %#x'%(r['service'],r['id'] or 0) for r in x['requests']})))
                    for x in found if x['requests'] and not x['generated']})
                randoms=sorted({'item %#x'%x['type'] for x in found if set(x['rand_sites'])-{LINK_RAND}})
                reasons[cl]='RenderLinkItem requests without a checked link consumer: '+'; '.join(wanted) if wanted else \
                    'RenderLinkItem consumes further random values: '+'; '.join(randoms) if randoms else \
                    'additional or different RenderLinkItem services'
                del rows[cl];continue
            row['link_fx']={x['slot']:len(x['requests']) for x in found}
            for t,lv in row['slots'][6:8]:
                if t in (0,65535):continue
                pair=(t,lv)
                if pair not in weapon_draw:
                    weapon_draw[pair]=weapon_draw_checks(args,{cl:dict(row,slots=[(0,0)]*6+[(t,lv),(0,0),(0,0)])})
                f=weapon_draw[pair]
                if f['equal']!=f['cases']:
                    reasons[cl]='weapon RenderObjDraw stream unavailable or extra services: item %#x level %d'%(t,lv);rows.pop(cl,None)
        host=build_host(tmp,rows if opts.generate else None);checks=native_checks(host,rows)
        for cl,(ok,detail) in checks.items():
            diagnostics[cl]['native']=detail
            if not ok:
                # Name the failed native fact; every one keeps the row incomplete.
                reasons[cl]='native mesh textures missing: %d'%detail['missing'] if detail.get('missing') else \
                    'native draw takes the RGB path without the alpha callback' if detail.get('alpha')==[2,-1] else \
                    'native file/texture/geometry/plan check failed'
                del rows[cl]
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
        if opts.generate:TABLE.write_text(emit(rows));FX_TABLE.write_text(emit_fx(rows))
        else:
            fams['plans']=check_plans(lib,rows)
            fams['requests']=check_fx(lib,rows,observed)
            fams['reproduce']=recipes.family();recipes.note(fams['reproduce'],TABLE.read_text()==emit(rows),dict(rows=len(rows)))
            recipes.note(fams['reproduce'],FX_TABLE.read_text()==emit_fx(rows),dict(fx=sum(len(r['fx']) for r in rows.values())))
        decisions=[dict(server_class=int(i['server_class']),group=i['group'],before_group=before_groups[int(i['server_class'])],previous_reason=i['reason'],
            actors007_decision=prior_decision.get(int(i['server_class']),''),actors007_reason=prior.get(int(i['server_class']),''),
            decision='checked group body plan' if int(i['server_class']) in rows else 'incomplete',
            reason=reasons.get(int(i['server_class']),'')) for i in pop]
        table=publish_requests(True)
        if opts.generate:
            with DECISIONS.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(decisions[0]),lineterminator='\n');w.writeheader();w.writerows(decisions)
            groups=missing_groups(decisions)
            with (ROOT/'docs/research/actor-missing-plan-groups.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(groups[0]),lineterminator='\n');w.writeheader();w.writerows(groups)
            write_requests(table)
        else:
            with DECISIONS.open() as f:old=list(csv.DictReader(f))
            normalized=[dict(r,server_class=str(r['server_class'])) for r in decisions]
            recipes.note(fams['reproduce'],old==normalized,dict(decisions=len(decisions)))
            with (ROOT/'docs/research/actor-missing-plan-groups.csv').open() as f:group_rows=list(csv.DictReader(f))
            expected_groups=[{k:str(v) for k,v in r.items()} for r in missing_groups(decisions)]
            recipes.note(fams['reproduce'],group_rows==expected_groups,dict(groups=len(expected_groups)))
            with REQUESTS.open() as f:request_table=list(csv.DictReader(f))
            recipes.note(fams['reproduce'],request_table==[{k:str(v) for k,v in r.items()} for r in table],dict(requests=len(table)))
        with_fx=[cl for cl,r in rows.items() if r['fx']]
        for name,count in [('constructors',len(rows)),('openers',6*len(rows)),('callers',28*len(rows)),('native',len(rows)),
            ('body_reader',8*len(rows)),('caller_variations',6*len(with_fx))]:
            fams[name]=dict(cases=count,equal=count,first_failures=[])
        fams['draw']=recipes.family()
        for model in {r['model'] for r in rows.values()}:
            f=model_checks[model];fams['draw']['cases']+=f['cases'];fams['draw']['equal']+=f['equal']
        varied=recipes.family();classes=list(rows)
        for i in range(opts.cases):
            r=rows[classes[i%len(classes)]];clock,rand=acr.VARIED[i%len(acr.VARIED)] if r['fx'] else (0.0,0)
            ok,detail=caller(args,r,bones[r['model']],worlds(r)[i%4],i%7,(i%8+1)/9,i%6+.25,clock,rand)
            if ok and not opts.generate:
                lights=[fx_light(lib,r['class'],k,clock,rand) for k in range(len(r['fx']))]
                ok=[acr.structure(x) for x in detail['requests']]==[acr.structure(x) for x in observed[r['class']][0]['requests']] and \
                    lights==[x['light'] for x in detail['requests']]
            recipes.note(varied,ok,{k:v for k,v in detail.items() if k!='requests'})
        fams['varied']=varied
        fams['hardcase_requests'],hardcases=hardcase_requests(args,machine)
        fams['secondary_requests']=monsters.check_secondary(args,machine)
        mutants={}
        if opts.mutations:
            src=(ROOT/'reconstructed/actors/actors.c').read_text()
            fx_class=next(c for c,r in rows.items() if r['fx'])
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
                ('subtype','*out = mu_actor_group_plans[lo];','*out = mu_actor_group_plans[lo]; out->subtype++;'),
                ('link_mask','*out = mu_actor_group_plans[lo];','*out = mu_actor_group_plans[lo]; out->link_effect_mask^=1u;'),
                ('fx_admission','if (server_class < 0) return 0; /* caller fx */','if (server_class != %d) return 0; /* caller fx */'%fx_class),
                ('fx_overadmission','if (server_class < 0) return 0; /* caller fx */','if (server_class == 2) server_class = %d; if (server_class < 0) return 0; /* caller fx */'%fx_class),
                ('fx_count','if (count && first) *first = &mu_actor_caller_fx_rows[lo];','if (count && first) *first = &mu_actor_caller_fx_rows[lo]; if (count > 1) --count;'),
                ('fx_flicker','factor = (float)(random_value % 30 + 70) * 0.01f; /* flicker */','factor = (float)(random_value % 30 + 71) * 0.01f; /* flicker */'),
                ('fx_pulse','factor = wave * 0.3f + base; /* pulse */','factor = wave * 0.3f - base; /* pulse */'),
                ('fx_constant','out[k] = fx->light_kind == MU_ACTOR_FX_CONSTANT ? colour[k] : factor * colour[k];','out[k] = factor * colour[k] * (fx->light_kind == MU_ACTOR_FX_CONSTANT ? 0.5f : 1.0f);')]:
                assert src.count(old)==1,name;path=Path(tmp)/'actors.c';path.write_text(src.replace(old,new));target=Path(tmp)/(name+'.dylib')
                recipes.build_library(path,target);changed=library(target)
                f=check_fx(changed,rows,observed) if name.startswith('fx_') else check_plans(changed,rows)
                mutants[name]=dict(caught=f['equal']<f['cases'],stopped=0)
            src=(ROOT/'native/core/mu_world_actors.c').read_text()
            sample_ids=[next(c for c,r in rows.items() if mask(r)),next(c for c,r in rows.items() if r['blend_mesh']!=-1),next(c for c,r in rows.items() if r['hidden_mesh']!=-1),
                fx_class]+[c for c,r in rows.items() if link_mask(r)][:1]
            sample={cl:rows[cl] for cl in sample_ids}
            for name,old,new in [('load_links','if (!player && load_weapons','if (player && load_weapons'),
                ('native_translate','p.transform_translate = (uint8_t)group_plan.body.translate;','p.transform_translate = 0;'),
                ('alpha','options->alpha = alpha; /* plain plan */','options->alpha = 1; /* plain plan */'),
                ('native_flags','options->flags = plan.flags;','options->flags = 0;'),
                ('native_blend','options->select = group.blend_mesh;','options->select = -1;'),
                ('native_hidden','options->skip_mesh = group.hidden_mesh;','options->skip_mesh = -1;'),
                ('native_subtype','memcpy(a->actor.object + 0x60, &group_plan.subtype, 4);','memset(a->actor.object + 0x60, 1, 4);'),
                ('native_guard_options','if (scale_bits != plan.scale_bits) return 0;','if (scale_bits != plan.scale_bits) { options->select = -2; return 0; }'),
                ('native_fx_bone','mu_world_particles_bone_position(&a->actor.model, fx[i].bone, offset, request.position);','mu_world_particles_bone_position(&a->actor.model, 0, offset, request.position);'),
                ('native_fx_offset','memcpy(offset, fx[i].offset_bits, sizeof offset);','memset(offset, 0, sizeof offset);'),
                ('native_fx_guard','if (!mu_world_actor_plain_options(a, 1.0f, &probe)) return 0;','(void)probe;'),
                ('native_fx_light','mu_actor_caller_fx_light(&fx[i], clock, random_value, request.light);','mu_actor_caller_fx_light(&fx[i], clock + 100.0f, random_value + 1, request.light);'),
                ('native_link_fx','!(plan.link_effect_mask >> slot & 1u)) return 0; /* link effects */','!(plan.link_effect_mask >> slot & 1u) || slot >= 0) return 0; /* link effects */'),
                ('native_level','part->glow = (mu_renderchar_glow){.type = type, .level = row.slots[6+k].level,','part->glow = (mu_renderchar_glow){.type = type, .level = row.slots[6+k].level + 1,')]:
                assert src.count(old)==1,name;path=Path(tmp)/'mu_world_actors.c';path.write_text(src.replace(old,new))
                if name in ('native_link_fx','native_level'):
                    armed={cl:r for cl,r in sample.items() if mask(r)}
                    f=weapon_checks(build_host(tmp,source=path,weapon=True),armed,bones)
                    mutants[name]=dict(caught=f['equal']<f['cases'],stopped=0);continue
                result=native_checks(build_host(tmp,source=path),sample);stops=sum('native_exit' in d for ok,d in result.values())
                mutants[name]=dict(caught=not stops and any(not ok for ok,d in result.values()),stopped=stops)
    report=dict(pins={k.lower():getattr(pins,k).sha256 for k in ('TEXT','DATA','FLAG','FEATURE')},families=fams,
        link_effect_rows=sorted(cl for cl,r in rows.items() if link_mask(r)),
        hardcase_refusals={'type226_consumer':2},hardcase_requests=hardcases,
        admitted=len(rows),equipped=len(equipped),with_requests=len(with_fx),requests=sum(len(r['fx']) for r in rows.values()),
        distinct_models=len({r['model'] for r in rows.values()}),
        rejected=dict(collections.Counter(reasons.values())),decisions=decisions,diagnostics=diagnostics,
        cases=sum(f['cases'] for f in fams.values()),all_equal=all(f['cases']==f['equal'] for f in fams.values()),
        mutants=mutants,all_mutants_caught=all(m['caught'] for m in mutants.values()),wall_seconds=time.monotonic()-start)
    opts.output.parent.mkdir(parents=True,exist_ok=True);opts.output.write_text(json.dumps(report,indent=2,default=str)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('diagnostics','decisions','hardcase_requests')},default=str))
    return 0 if report['all_equal'] and report['all_mutants_caught'] else 1

if __name__=='__main__':raise SystemExit(main())
