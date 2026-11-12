#!/usr/bin/env python3
"""Fixture aura caller, records, GL streams and independent lifecycles vs pinned x86.

RenderCharacter is executed as a bounded inline slice with a declared frame.
Buff presence, bone lookup/TransformPosition and joint existence are authored
services. MoveJoint's ordinary context answers its equipment lookup with NULL.
No stat, service or protected code is involved.
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
import subprocess
import tempfile
import time
import actor_machine as am
import pins
import validate_combat as vc
import validate_skill_fx as fx
import validate_joints as jt
import validate_particles as pt
ROOT=Path(__file__).resolve().parents[1]
F3=C.c_float*3
CHAR=0x28000000
BUFFS={1:1,2:2,3:4,18:8,346:16,347:32}
class Input(C.Structure):
    _fields_=[('buffs',C.c_uint32),('owner',C.c_int32),('key',C.c_int32),('link',C.c_int32*2),
              ('existing4',C.c_uint8),('existing9',C.c_uint8),('position',F3),('angle',F3)]
BONE=C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_int32,C.POINTER(C.c_float))
class Env(C.Structure):
    _fields_=[('joint',C.POINTER(jt.Env)),('bone',BONE)]
class Machine(fx.FxMachine):
    def stub_entry(self,uc,address,size,ignored):
        if address==0x1371132 and address in self.stubs:
            # End of the declared slice; caller-owned register restore is outside it.
            for reg,value in self.preserved.items(): uc.reg_write(reg,value)
            uc.mem_write(am.TIB,struct.pack('<I',am.SEH_HEAD))
            uc.reg_write(self.x86.UC_X86_REG_ESP,am.ENTRY_ESP+4)
            uc.reg_write(self.x86.UC_X86_REG_EIP,am.SENTINEL)
            return
        super().stub_entry(uc,address,size,ignored)
def load(path):
    lib=jt.load_library(path)
    lib.mu_aura_plan.argtypes=[C.POINTER(Input),C.POINTER(Env)]
    lib.mu_aura_create.argtypes=[C.POINTER(jt.Joint),C.POINTER(Input),C.POINTER(jt.Env)]
    lib.mu_aura_create.restype=C.c_int
    lib.mu_aura_move.argtypes=[C.POINTER(jt.Joint),C.c_uint32,C.POINTER(jt.Env),C.c_int32,C.c_float]
    lib.mu_aura_move.restype=C.c_int
    lib.mu_aura_render.argtypes=[C.POINTER(jt.Joint),C.c_uint8,C.c_float,C.POINTER(jt.Env),C.POINTER(jt.Gl)]
    lib.mu_aura_render.restype=C.c_int
    return lib
def input_state(rng,n):
    s=Input(); s.buffs=n%64; s.owner=0; s.key=rng.choice([-1,0,1234]); s.link[:]=[33,42]
    s.existing4=int(n%7==0); s.existing9=int(n%11==0)
    s.position[:]=[vc.rfloat(rng,0.05,30000) for _ in range(3)]
    s.angle[:]=[vc.rfloat(rng,0.1,360) for _ in range(3)]
    return s
def caller(m,lib,rng,cases,report):
    for n in range(cases):
        s=input_state(rng,n); missing=rng.choice([-1,-1,-1,33,27,26,42,36,35])
        char=am.undefined_region('character',CHAR,0x3670)
        char.define(CHAR+0x40,struct.pack('<h',s.key))
        for k in range(2):char.define(CHAR+0x19b1+k*0x3fc,bytes([s.link[k]]))
        obj=am.undefined_region('object',fx.OBJECTS,0x400)
        obj.define(fx.OBJECTS+0x158,struct.pack('<3f',*s.position))
        obj.define(fx.OBJECTS+0x164,struct.pack('<3f',*s.angle))
        rand=jt.rand_values(rng,4); ci=0; ni=0; client=[]; mine=[]; cbones=[]; nbones=[]; current=[0]
        def crand(mm):
            nonlocal ci
            r=rand[ci];ci+=1;return r
        def nrand(ctx):
            nonlocal ni
            r=rand[ni];ni+=1;return r
        def lookup(mm):
            bone=mm.argument(0);cbones.append(bone);current[0]=bone
            return (0 if bone==missing else fx.MODEL,4)
        def point(bone):return [fx.f32(s.position[k]+float(bone*(k+1))) for k in range(3)]
        def transform(mm):
            assert mm.argument(3)==1 and mm.floats(mm.argument(1),3)==[0.,0.,0.]
            mm.uc.mem_write(mm.argument(2),struct.pack('<3f',*point(current[0])));return 0,16
        def nbone(ctx,bone,p):
            nbones.append(bone)
            if bone==missing:return 0
            for k,v in enumerate(point(bone)):p[k]=v
            return 1
        def csprite(mm):
            axes=mm.argument(8)
            client.append(['s',mm.argument(0),mm.floats(mm.argument(1),3),mm.float_argument(2),
                mm.floats(mm.argument(3),3),mm.argument(4),mm.float_argument(5),mm.argument(6),mm.argument(7),
                list(struct.unpack('<IIf',mm.uc.mem_read(axes,12)))])
            return 0
        def cjoint(mm):
            a=[mm.argument(k) for k in range(14)]
            client.append(['j',a[0],mm.floats(a[1],3),mm.floats(a[2],3),mm.floats(a[3],3),a[4],a[5],fx.from_bits(a[6]),a[7:]])
            return 0
        def ncall(ctx,cp):
            c=cp.contents
            if c.routine==jt.sf.CREATE_SPRITE:
                mine.append(['s',c.type,list(c.position),c.scale,list(c.light),fx.OBJECTS,c.angle[0],0,c.range,[1,1,1.]])
            else:
                mine.append(['j',c.type,list(c.position),list(c.target),list(c.angle),c.subtype,fx.OBJECTS,c.scale,
                    [c.arg7&0xffffffff,c.arg8&0xffffffff,0,c.range&0xffffffff,0,0xffffffff,0]])
        stubs={0x1295ade:lambda mm:(int(bool(s.buffs & BUFFS[mm.argument(0)])),4),
               0x1553b41:lambda mm:int(bool(s.existing4 if mm.argument(2)==4 else s.existing9)),
               fx.RAND:crand,0x129f12c:lookup,fx.TRANSFORM_POSITION:transform,
               fx.CREATE_SPRITE:csprite,fx.CREATE_JOINT:cjoint,0x1371132:lambda mm:0}
        # model and zero source point are defined caller locals, all other locals start poisoned.
        frame={-0x14:fx.MODEL,-0x48:0,-0x44:0,-0x40:0}
        r=m.execute(0x1370ccc,[CHAR,fx.OBJECTS],[char,obj],stubs,frame=(0xe00,frame))
        keeps=(jt.RAND_FN(nrand),jt.CALL_FN(ncall),BONE(nbone))
        je=jt.Env();je.rand=keeps[0];je.call=keeps[1]
        env=Env(C.pointer(je),keeps[2]);lib.mu_aura_plan(C.byref(s),C.byref(env))
        ok=vc.ok(r) and vc._same_call(client,mine) and ci==ni and cbones==nbones
        report.add('caller',ok,dict(case=n,buffs=s.buffs,stopped=r['stopped'],error=r['error'],
            checks=r['checks'],client=client[:2],mine=mine[:2],counts=[len(client),len(mine)],rand=[ci,ni],bones=[cbones,nbones]))

def create(m,lib,rng,report,n):
    s=input_state(rng,n);obj=jt.random_object(rng);obj.live=1
    previous=bytearray(am.poison(jt.JOINT_BYTES,n%100));previous[0]=0
    struct.pack_into('<f',previous,0x14,fx.f32(rng.uniform(0,40)))
    record=am.defined_region('joint',jt.JOINT_POOL,previous)
    inp=am.defined_region('inputs',fx.INPUTS,struct.pack('<9f',*s.position,*s.position,*s.angle))
    case=jt.Case(rng,[obj],jt.rand_values(rng),0.,1000.)
    stubs=case.stubs(m);del stubs[fx.CREATE_JOINT];stubs[fx.JOINT_MANAGER_A]=lambda mm:(0,12)
    r=m.execute(jt.CREATE_JOINT_CORE,[0x472,fx.INPUTS,fx.INPUTS+12,fx.INPUTS+24,4,fx.OBJECTS,
        fx.bits(20.),0xffff,0,0,s.key&0xffffffff,0,0xffff,0],[record,inp,jt.object_region([obj])],stubs)
    j=jt.Joint();jt.joint_from_bytes(previous,j);env=case.jenv()
    lib.mu_aura_create(C.byref(j),C.byref(s),C.byref(env))
    mismatch=jt.compare_joint(j,r['regions']['joint'],record.defined,jt.ALL_NAMES) if vc.ok(r) else None
    report.add('joint_create',vc.ok(r) and mismatch is None,dict(case=n,mismatch=mismatch,stopped=r['stopped'],error=r['error']))
    return j,r['regions']['joint'],record.defined,obj

def move(m,lib,rng,report,j,raw,mask,obj,buffs,index,clock,label):
    record=am.Region('joint',jt.JOINT_POOL,raw,mask)
    record.define(jt.JOINT_POOL+0xa40,struct.pack('<i',0))
    case=jt.Case(rng,[obj],jt.rand_values(rng),0.,1000.);stubs=case.stubs(m)
    stubs.update({0x95f6db:lambda mm:(0,4),0x9a13f4:lambda mm:0,
        0x1295ade:lambda mm:(int(bool(buffs & BUFFS[mm.argument(0)])),4)})
    regions=[record,jt.object_region([obj]),am.defined_region('step',fx.TIME_STEP,struct.pack('<f',.1)),
        am.defined_region('clock',0xbdc5eb0,struct.pack('<i',clock))]
    r=m.execute(jt.MOVE_JOINT,[jt.JOINT_POOL,index],regions,stubs)
    env=case.jenv();env.ambient_clock=clock
    lib.mu_aura_move(C.byref(j),buffs,C.byref(env),index,.1)
    mismatch=jt.compare_joint(j,r['regions']['joint'],record.defined,jt.ALL_NAMES) if vc.ok(r) else None
    report.add(label,vc.ok(r) and mismatch is None and case.c_rand==case.client_rand,
        dict(mismatch=mismatch,stopped=r['stopped'],error=r['error'],buffs=buffs,index=index))
    return r['regions']['joint'],record.defined

def render(m, lib, rng, cases, report):
    negatives=defaultdict(int)
    pool_bytes = 500*jt.JOINT_BYTES
    empty = bytearray(am.poison(pool_bytes, 0x61))
    empty_mask = bytearray(pool_bytes)
    for i in range(500):
        base = i*jt.JOINT_BYTES
        empty[base] = 0
        struct.pack_into('<ii', empty, base+4, 0, 0)
        empty_mask[base:base+0x10] = b'\1'*0x10
    for n in range(cases):
        kind = jt.KINDS[n % len(jt.KINDS)]
        j = jt.random_joint(rng, kind)
        j.faces = rng.choice([3, 3, 1, 2, 0])
        mode = rng.choice([0, 0, 1, 2])
        raw, mask = jt.joint_to_bytes(j, jt.ALL_NAMES | {'target'})
        pool = bytearray(empty)
        pmask = bytearray(empty_mask)
        pool[0:jt.JOINT_BYTES] = raw
        pmask[0:jt.JOINT_BYTES] = mask
        region = am.Region('joints', jt.JOINT_POOL, bytes(pool), bytes(pmask))
        world_time = jt.world_time_value(rng)
        wt_region = am.defined_region('world-time', jt.WORLD_TIME, struct.pack('<f', world_time), writable=False)
        calls = []

        def rec(name):
            def stub(mm):
                calls.append((name,))
                return 0
            return stub

        def bind(mm):
            calls.append(('bind', mm.argument(0)))
            return 0

        def blend_alpha(mm):
            calls.append(('blend', 2, mm.argument(0)))
            return 0
        stubs = {fx.JOINT_MANAGER_COUNT: lambda mm: (0, 0), fx.BIND_TEXTURE: bind, fx.BLEND_ADD: rec('blend1'),
                 fx.BLEND_ALPHA: blend_alpha, fx.BLEND_SUB: rec('blend3'), fx.BLEND_INV: rec('blend4'),
                 fx.DEPTH_OFF: rec('depth_off')}
        for slot, (name, argc) in fx.GL_IMPORTS.items():
            def gl(mm, name=name, argc=argc):
                a = [mm.argument(i) for i in range(argc)]
                if name in ('glVertex3fv', 'glColor3fv'):
                    calls.append(('glColor3f' if name=='glColor3fv' else name, mm.floats(a[0], 3)))
                elif name in ('glColor3f', 'glColor4f', 'glTexCoord2f'):
                    calls.append((name, [jt.from_bits(x) for x in a]))
                else:
                    calls.append((name, a))
                return 0, 4*argc
            stubs[m.gl_target[slot]] = gl
        objects=[jt.random_object(rng) for _ in range(2)]
        def sprite(mm):
            calls.append(('sprite',mm.argument(0),mm.floats(mm.argument(1),3),mm.float_argument(2),
                mm.floats(mm.argument(3),3),mm.argument(4),mm.float_argument(5),mm.argument(6),mm.argument(7),
                list(struct.unpack('<IIf',mm.uc.mem_read(mm.argument(8),12)))))
            return 0
        stubs[fx.CREATE_SPRITE]=sprite
        r = m.execute(jt.RENDER_JOINTS, [0x5500 | mode], [region, wt_region,jt.object_region(objects)], stubs)
        mine = []
        names = {0x0184aa2b: ('blend1',), 0x0184aab7: ('blend3',), 0x0184ab46: ('blend4',)}

        def c_state(ctx, wrapper, argument):
            mine.append(('blend', 2, argument) if wrapper == 0x0184a990 else names.get(wrapper, ('state', wrapper)))

        def c_bind(ctx, bitmap):
            mine.append(('bind', bitmap))

        def c_color(ctx, r_, g, b):
            mine.append(('glColor3f', [r_, g, b]))

        def c_begin(ctx, mode_):
            mine.append(('glBegin', [mode_]))

        def c_tex(ctx, u, v):
            mine.append(('glTexCoord2f', [u, v]))

        def c_vertex(ctx, p):
            mine.append(('glVertex3fv', [p[0], p[1], p[2]]))

        def c_end(ctx):
            mine.append(('glEnd', []))
        keep = (jt.STATE_FN(c_state), jt.BIND_FN(c_bind), jt.COLOR_FN(c_color), jt.BEGIN_FN(c_begin), jt.TEX_FN(c_tex),
                jt.VERTEX_FN(c_vertex), jt.END_FN(c_end))
        glc = jt.Gl(None, *keep)
        case=jt.Case(rng,objects,[],0.,world_time)
        env=case.jenv()
        def ccall(ctx,cp):
            c=cp.contents
            mine.append(('sprite',c.type,list(c.position),c.scale,list(c.light),0,0.,0,c.range,[1,1,1.]))
        keep_call=jt.CALL_FN(ccall);env.call=keep_call
        count_q = lib.mu_aura_render(C.byref(j), mode, world_time,C.byref(env), C.byref(glc))
        mismatch = None
        if vc.ok(r):
            if len(calls) != len(mine) or not all(vc._same_call(a, b) for a, b in zip(calls, mine)):
                diff = next(((i, a, b) for i, (a, b) in enumerate(zip(calls, mine)) if not vc._same_call(a, b)),
                            ('count', len(calls), len(mine)))
                mismatch = ('calls', diff, calls[:4], mine[:4])
        equal = vc.ok(r) and mismatch is None
        report.add('joint_render', equal, {'case': n, 'kind': [hex(kind[0]), kind[1]], 'mode': mode,
                                           'mismatch': mismatch, 'stopped': r['stopped'], 'error': r['error'],
                                           'checks': r['checks']})
        report.cover('joint_render', f'{kind[0]:#x}/{kind[1]:#x} quads {min(count_q, 9)}')
        if vc.ok(r) and count_q and kind[0] == 0x7f7d:
            colours = [c for c in calls if c[0] == 'glColor3f']
            if len(colours) > 1:
                f = jt.f32(j.lifetime * jt.f32(0.08)) if kind[1] in (0x14, 0x15, 0x16, 0x17) else jt.f32(j.lifetime * jt.f32(0.1))
                # negative control: the ring's and the bolt's tail factors exchanged
                negatives['render_factor_swapped'] += not jt.same(colours[1][1][0], jt.f32(j.light[0]*f))


def compare(text,data,lib,cases):
    am.STACK_BYTES,am.ENTRY_ESP=0x80000,am.STACK+0x7c000
    report=pt.Report();rng=random.Random('effects28');m=Machine(text,data)
    caller(m,lib,rng,cases,report)
    for n in range(cases):
        j,raw,mask,obj=create(m,lib,rng,report,n)
        obj.live=n%5!=0;buffs=n%64
        raw,mask=move(m,lib,rng,report,j,raw,mask,obj,buffs,n%5,rng.randint(-2147483648,2147483647),'joint_move')
    for event in ['expiry','death']:
        for index in range(5):
            j,raw,mask,obj=create(m,lib,rng,report,index)
            for tick in range(37):
                buffs=2 if tick<36 or event=='death' else 0
                obj.live=int(tick<36 or event=='expiry')
                for k in range(3):obj.position[k]=fx.f32(obj.position[k]+5.)
                raw,mask=move(m,lib,rng,report,j,raw,mask,obj,buffs,index,100+tick,'lifecycle')
            report.add('lifecycle',not j.live and not raw[0],dict(event=event,retired=not j.live))
    old_random=jt.random_joint
    def aura_random(rng,kind):
        j=old_random(rng,(0x472,1));j.subtype=4;j.target=0;j.tex_type=0x7fdd;j.max_tails=30;j.num_tails=min(j.num_tails,29)
        return j
    jt.KINDS=[(0x472,4)];jt.random_joint=aura_random
    try:render(m,lib,rng,cases,report)
    finally:jt.random_joint=old_random
    return report
MUTANTS=[
 ('n<5','n<4'),('pulse*0.3f','pulse*0.4f'),('in->existing4 || in->existing9','in->existing4 && in->existing9'),
 ('MU_AURA_HIDDEN))','MU_AURA_HIDDEN) && 0)'),('0,-6,-7','0,-5,-7'),
 ('j->lifetime=10000','j->lifetime=1000'),('j->max_tails=30','j->max_tails=20'),
 ('j->light[1]=0.8f','j->light[1]=0.7f'),('!o->live','!o->live && 0'),
 ('MU_AURA_DEFENSE|MU_AURA_DEFENSE_UP|MU_AURA_COMBINED','MU_AURA_ATTACK|MU_AURA_DEFENSE_UP|MU_AURA_COMBINED'),
 ('j->lifetime=100;','j->lifetime=90;'),('j->tails[i][c][k]-=j->target_position[k]','j->tails[i][c][k]+=j->target_position[k]'),
 ('index%2 ? clock','index%2 ? 0u-clock'),('(co*y-sc*z)*80.0f','(co*y-sc*z)*70.0f'),('110.0f+j->target_position[2]','100.0f+j->target_position[2]'),
]
MUTANTS += [('(o->position[2]+50.0f))*0.01f','(o->position[2]+50.0f))*0.02f'),
 ('c.scale=0.7f','c.scale=0.8f'),('0.25f*c.position[k]','0.2f*c.position[k]')]

def run(cases,mutations):
    text=am.load_pinned(pins.TEXT.default_str(),am.TEXT_BYTES,am.TEXT_SHA256,'text')
    data=am.load_pinned(pins.DATA.default_str(),am.DATA_BYTES,am.DATA_SHA256,'data')
    start=time.monotonic();rep=compare(text,data,load(ROOT/f'reconstructed/combat/libcombat.{fx.SUFFIX}'),cases)
    out=dict(families=rep.families,text_sha256=pins.TEXT.sha256,data_sha256=pins.DATA.sha256,mutants=[])
    out['all_equal']=all(f['cases']==f['equal'] for f in rep.families.values())
    if mutations and out['all_equal']:
        src=(ROOT/'reconstructed/combat/aura_fx.c').read_text()
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);shutil.copytree(ROOT/'reconstructed',tmp/'reconstructed',ignore=shutil.ignore_patterns('*.dylib','*.so','__pycache__'))
            dest=tmp/'reconstructed/combat/aura_fx.c'
            for n,(old,new) in enumerate(MUTANTS):
                assert src.count(old)==1,(old,src.count(old))
                dest.write_text(src.replace(old,new));lib=tmp/f'mutant{n}.{fx.SUFFIX}'
                subprocess.run(['clang','-std=c11','-O2','-shared','-fPIC','-ffp-contract=off','-fno-fast-math',
                    str(dest),str(tmp/'reconstructed/joints/joints.c'),str(tmp/'reconstructed/record-math/record_math.c'),
                    str(tmp/'reconstructed/movement/client_movement.c'),'-lm','-o',str(lib)],check=True,capture_output=True)
                r=compare(text,data,load(lib),128)
                failures=[f for f in r.families.values() if f['equal']!=f['cases']]
                stopped=sum(bool(v.get('stopped')) for f in r.families.values() for v in f['first_failures'])
                out['mutants'].append(dict(index=n,detected=sum(f['cases']-f['equal'] for f in failures),stopped=stopped))
                lib.unlink()
    out['all_mutants_caught']=(not mutations or len(out['mutants'])==len(MUTANTS)) and all(m['detected'] and not m['stopped'] for m in out['mutants'])
    out['cases']=sum(f['cases'] for f in rep.families.values());out['seconds']=time.monotonic()-start
    out['bodies']={name:dict(start=hex(a),end=hex(b),sha256=hashlib.sha256(text[a-am.TEXT_BASE:b-am.TEXT_BASE]).hexdigest())
        for name,a,b in [('caller',0x1370ccc,0x1371132),('create4',0x1548998,0x1548a09),('move4',0x1569cda,0x156c46a)]}
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=int,default=1000)
    p.add_argument('--mutations',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    if a.cases<1:p.error('--cases must be positive')
    out=run(a.cases,a.mutations)
    if a.output:a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2));raise SystemExit(not(out['all_equal'] and out['all_mutants_caught']))
