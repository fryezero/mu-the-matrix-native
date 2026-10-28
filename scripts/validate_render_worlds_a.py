#!/usr/bin/env python3
"""RENDER-WORLDS-A instruction comparisons. See client-world-fidelity.md section 5.
C is compiled and called via ctypes; leaves (particle/sprite, bone transform, draw) are recorded.
All other instructions in the bounded routines execute under the strict pinned Unicorn machine.
"""
import ctypes
import re
import argparse, ctypes as C, hashlib, json, random, shutil, struct, subprocess, sys, tempfile
from pathlib import Path
import actor_machine as am
import validate_object_render as v
import validate_login_world as login
ROOT=Path(__file__).resolve().parents[1]
BONE=login.BONE_FN
BODIES={'kanturu':(0xe75089,0xe760aa),'karutan':(0xe13be4,0xe14596),
        'after_pass':(0x16d6949,0x16d6e87),'predicate':(0x17fe909,0x17ff238),
        'elbeland_flags':(0xe31ab1,0xe31b11),'raklion_flags':(0xe95c89,0xe96536),
        'karutan_flags':(0xe145f4,0xe14727),'noria_after':(0x16d67c7,0x16d6949),
        'elbeland_after':(0xe321bb,0xe326cd),'raklion_after':(0xe96536,0xe9683d),
        'karutan_after':(0xe1543e,0xe15b69),'particle_create':(0x15ae7b0,0x1615f39),
        'particle_move':(0x1616c80,0x168eeb2),'particle_render':(0x159123f,0x15ae373)}
class Library(v.Library):
    def __init__(self,p):
        super().__init__(p);d=self.dll;P=C.c_void_p;I=C.c_int32;F=C.c_float;L=C.POINTER(v.Log)
        d.mu_kanturu_flames.argtypes=[P,I,I,F,v.RAND_FN,BONE,P,L]
        d.mu_karutan_flames.argtypes=[P,I,v.RAND_FN,P,L]
        d.mu_world_defer.argtypes=[P,I]
        d.mu_raklion_before.argtypes=[P,I,L]
        d.mu_world_after_render.argtypes=[P,I,I,F,L,BONE,P]
        d.mu_world_after_pass.argtypes=[C.POINTER(v.World),C.POINTER(v.RenderInputs),C.POINTER(I),L]

def flames(machine,lib,g,cases,karutan=False):
    t=v.Tally('karutan' if karutan else 'kanturu')
    for n in range(cases):
        world=g.choice([0x50,0x51]) if karutan else g.choice([0x25,0x28])
        typ=0x71 if karutan else g.choice([0x3b,0x3c,0x3d,0x46])
        o=bytearray(v.poison_object(g));v.put_i(o,0x5c,typ);v.put_i(o,0x68,g.choice([-2,-1,0]))
        v.put_f(o,0xa0,v.f32(g.uniform(0.1,3)))
        time=v.f32(g.uniform(0,100000));seed=g.randrange(2**32);a=v.MsvcRand(seed);b=v.MsvcRand(seed)
        pos=[v.f32(g.uniform(-1000,1000)) for _ in range(3)];calls=[]
        def particle(m):
            calls.append((0x168fafd,0,m.argument(0),*v.read_vec(m,m.argument(1)),*v.read_vec(m,m.argument(2)),
                          *v.read_vec(m,m.argument(3)),m.argument(4),m.argument(5),int(m.argument(6)==v.OBJECTS)))
            if m.argument(7)!=0: raise AssertionError('particle extra')
            return 0
        def sprite(m):
            calls.append((0x1692eb7,0,m.argument(0),*v.read_vec(m,m.argument(1)),m.argument(2),
                          *v.read_vec(m,m.argument(3)),m.argument(5),int(m.argument(4)==v.OBJECTS),m.argument(6),m.argument(7)))
            return 0
        def bone(m):
            assert m.argument(0)==0x6fce398+6*48
            assert v.read_vec(m,m.argument(1))==(0,0,0)
            m.uc.mem_write(m.argument(2),v.pack_f(*pos));return (0,16)
        stubs={0x1989721:lambda m:a(),0x168fafd:particle,0x1692eb7:sprite,0x12b6ef1:bone}
        regions=v.global_regions(world,6,[am.defined_region('object',v.OBJECTS,bytes(o)),
                                          am.defined_region('time',v.TIME,v.pack_f(time),writable=False)])
        start=0xe13be4 if karutan else 0xe75089
        result=v.run(machine,start,[v.OBJECTS,v.MODEL],regions,stubs,ecx=v.FAKE,cleanup=8 if karutan else 0)
        stop=v.stopped_reason(result)
        if stop:t.add(False,{'case':n,'type':typ},stop);continue
        co=C.create_string_buffer(bytes(o),v.OBJ_SIZE);log=v.new_log()
        rnd=v.RAND_FN(lambda c:b())
        def cb(c,k,local,out):
            pass
            for q in range(3):out[q]=pos[q]+float(k-6)
        bonefn=BONE(cb)
        if karutan:lib.dll.mu_karutan_flames(co,0,rnd,None,C.byref(log))
        else:lib.dll.mu_kanturu_flames(co,0,world,time,rnd,bonefn,None,C.byref(log))
        native=v.log_events(log)
        t.count(f'type {typ:#x} world {world:#x}');t.count('particles',sum(x[0]==0x168fafd for x in calls))
        t.count('sprites',sum(x[0]==0x1692eb7 for x in calls))
        t.add(calls==native and result['regions']['object']==co.raw and a.seed==b.seed,
              {'case':n,'type':typ,'world':world,'client':calls[:2],'native':native[:2]})
    return t

def family_kanturu(m,l,g,n):return flames(m,l,g,n)
def family_karutan(m,l,g,n):return flames(m,l,g,n,True)

from validate_login_world import (Tally, frustum_polygon, put_i, put_f, f32, object_list, OBJECTS, FAKE,
    fake_object, CHAIN_AFTER, global_regions, am, WORLD, SECTORS, sector_bytes, X2D, Y2D, pack_f, TOP_VIEW,
    COUNTER, run, stopped_reason, c_world, RenderInputs, ANSWER_FN, new_log, log_events, OBJ_SIZE, LOGIN_VTABLE)
def family_after_pass(machine, lib, g, cases):
    t = Tally('after_pass')
    for n in range(cases):
        world = g.choice([3, 0x33, 0x39, 0x3a, 0x50, 0x51])
        scene = g.choice([3, 5, 6])
        top = 1 if g.random() < 0.1 else 0
        count = g.randrange(0, 50)
        x2d, y2d = frustum_polygon(g)
        cx, cy = sum(x2d) / 4, sum(y2d) / 4

        def fields(g, o, k):
            o[0] = g.choice([0, 1, 1, 1, 1])
            o[0xa] = g.choice([0, 1, 1, 2])
            o[0xb] = g.choice([0, 1])
            put_i(o, 0x5c, g.choice([0x13,0x35,0x4c,0x53,0x59,0x5c,3,0x38] + [g.randrange(0, 300)]))
            put_f(o, 0x158, f32((cx + g.uniform(-45, 45)) * 100), f32((cy + g.uniform(-45, 45)) * 100),
                  f32(g.uniform(0, 300)))
            put_f(o, 0xc0, f32(g.choice([-30.0, -428.571, g.uniform(-600, 50)])))
        objects, heads, nxt = object_list(g, count, fields)
        counter = g.choice([0, 5, 40, 41, 100])
        calls = []
        index = lambda a: (a - OBJECTS) // 0x400

        def draw(m):
            calls.append((0x016d6791, index(m.argument(0))) + tuple(m.argument(i) for i in range(1, 4)))
            return 0
        # the first-draw predicate's default asks the world manager (0x00ea27b4, client code) for the
        # handler's slot 0x14: the manager +0x10 holds an object with the real CGMLogInScene_Ex vtable
        stubs = {0x016d6791: draw, 0x00db747f: lambda m: FAKE, 0x0095fba9: lambda m: 0, 0x009a6ef3: lambda m: FAKE,
                 0x00ea594b: lambda m: FAKE + 0x100}
        fake = bytearray(fake_object())
        struct.pack_into('<I', fake, 0x110, FAKE + 0x380)
        struct.pack_into('<I', fake, 0x380, LOGIN_VTABLE)
        for address in CHAIN_AFTER:
            if address in (0x00e18ae9,0x00ea233c): continue
            stubs[address] = (lambda a: lambda m: 0)(address)
        regions = global_regions(world, scene, [
            am.defined_region('sectors', SECTORS, bytes(sector_bytes(heads))),
            am.defined_region('x2d', X2D, pack_f(*x2d), writable=False),
            am.defined_region('y2d', Y2D, pack_f(*y2d), writable=False),
            am.defined_region('top-view', TOP_VIEW, bytes([top]), writable=False),
            am.defined_region('counter', COUNTER, struct.pack('<i', counter)),
            am.defined_region('fake', FAKE, bytes(fake), writable=False)] +
            [am.defined_region(f'object{k}', OBJECTS + 0x400 * k, bytes(o)) for k, o in enumerate(objects)])
        result = run(machine, 0x016d6949, [], regions, stubs)
        stop = stopped_reason(result)
        if stop:
            t.add(False, {'case': n}, stop)
            continue
        w, bufs = c_world(objects, heads, nxt)
        xs, ys = (ctypes.c_float * 4)(*x2d), (ctypes.c_float * 4)(*y2d)
        inputs = RenderInputs(world, scene, top, xs, ys, ANSWER_FN(lambda c, k: 0), ANSWER_FN(lambda c, k: 0), None,
                              0.0)
        ccounter = ctypes.c_int32(counter)
        log = new_log()
        status = lib.dll.mu_world_after_pass(ctypes.byref(w), ctypes.byref(inputs), ctypes.byref(ccounter),
                                             ctypes.byref(log))
        c_calls = log_events(log)
        table = result['regions']['sectors']
        blocks_ok = all(table[s * 16 + 0xc] == w.block_visible[s] for s in range(256))
        objs_ok = all(result['regions'][f'object{k}'] == bufs[k].raw[:OBJ_SIZE] for k in range(count))
        counter_ok = struct.unpack('<i', result['regions']['counter'])[0] == ccounter.value
        t.count('drawn', len(calls))
        t.add(status == 0 and calls == c_calls and blocks_ok and objs_ok and counter_ok,
              {'case': n, 'world':world, 'calls': calls[:4], 'c': c_calls[:4], 'blocks': blocks_ok, 'objects': objs_ok,
               'counter': counter_ok})
    return t

DEFER_TYPES={3:[0x13],0x33:[2,0x35,0x37,0x6e,0x59,0x4e,0x4f,0x7d,0x80],
             0x39:[0x2e,0x35,0x4c,0x53,0x59,0x5c],
             0x50:[1,3,0x36,0x37,0x38,0x39,0x3a,0x3e,0x3f,0x42,0x77]}
def family_after_draw(machine,lib,g,cases):
    t=v.Tally('after_draw')
    for n in range(cases):
        world=list(DEFER_TYPES)[n%4];typ=g.choice(DEFER_TYPES[world]);o=bytearray(v.poison_object(g))
        v.put_i(o,0x5c,typ);v.put_i(o,0x68,-1);v.put_f(o,0xdc,v.f32(g.uniform(0.01,1)))
        for offset in [0xa8,0xac,0xb0,0xc0,0xec,0xf0,0xf4]:v.put_f(o,offset,v.f32(g.uniform(0.1,2)))
        model=bytearray(0x100);time=v.f32(g.uniform(0,100000));calls=[]
        def body(m):
            calls.append((0x966def,0)+tuple(m.argument(k) for k in range(8)));return (0,32)
        def mesh(m):
            calls.append((0x966e4a,0)+tuple(m.argument(k) for k in range(8)));return (0,32)
        stubs={0x966def:body,0x966e4a:mesh,0x966cc4:lambda m:v.FAKE,0xeaa8cf:lambda m:(v.MODEL,4),
                0x12b6ef1:lambda m:(m.uc.mem_write(m.argument(2),v.pack_f(*([float((m.argument(0)-0x6fce398)//48)]*3))),(0,16))[1],
                0x1692eb7:lambda m:calls.append((0x1692eb7,0,m.argument(0),*v.read_vec(m,m.argument(1)),m.argument(2),*v.read_vec(m,m.argument(3)),m.argument(5),int(m.argument(4)==v.OBJECTS),m.argument(6),m.argument(7))) or 0}
        regions=v.global_regions(world,6,[am.defined_region('object',v.OBJECTS,bytes(o)),
                   am.defined_region('model',v.MODEL,bytes(model)),am.defined_region('time',v.TIME,v.pack_f(time),writable=False),
                   am.defined_region('bounds',v.BOUNDS,struct.pack('<i',0),writable=False)])
        start={3:0x16d67c7,0x33:0xe321bb,0x39:0xe96536,0x50:0xe1543e}[world]
        args=[v.OBJECTS,0,0,0] if world==3 else [v.OBJECTS,v.MODEL,0]
        result=v.run(machine,start,args,regions,stubs,ecx=v.FAKE,cleanup=12 if world in (0x39,0x50) else 0)
        stop=v.stopped_reason(result)
        if stop:t.add(False,{'case':n,'world':world,'type':typ},stop);continue
        co=C.create_string_buffer(bytes(o),v.OBJ_SIZE);log=v.new_log()
        def bone(c,k,local,out):
            for q in range(3):out[q]=float(k)
        bonefn=BONE(bone)
        lib.dll.mu_world_after_render(co,0,world,time,C.byref(log),bonefn,None);native=v.log_events(log)
        t.count(f'world {world:#x} type {typ:#x}')
        t.add(calls==native and result['regions']['object']==co.raw,
              {'case':n,'world':world,'type':typ,'client':calls,'native':native,
               'obj':result['regions']['object']==co.raw})
    return t

def family_first_draw(machine,lib,g,cases):
    t=v.Tally('first_draw')
    for n in range(cases):
        world=0x39;typ=g.choice([0x53,0x5c]);o=bytearray(v.poison_object(g))
        v.put_i(o,0x5c,typ);v.put_i(o,0x68,-1);v.put_f(o,0xdc,v.f32(g.uniform(0.01,1)))
        for offset in [0xa8,0xac,0xb0,0xc0,0xec,0xf0,0xf4]:v.put_f(o,offset,v.f32(g.uniform(0.1,2)))
        model=bytearray(0x100);time=v.f32(g.uniform(0,100000));calls=[]
        def body(m):
            calls.append((0x966def,0)+tuple(m.argument(k) for k in range(8)));return (0,32)
        def mesh(m):
            calls.append((0x966e4a,0)+tuple(m.argument(k) for k in range(8)));return (0,32)
        stubs={0x966def:body,0x966e4a:mesh,0x966cc4:lambda m:v.FAKE,0xeaa8cf:lambda m:(v.MODEL,4),
                0x12b6ef1:lambda m:(m.uc.mem_write(m.argument(2),v.pack_f(*([float((m.argument(0)-0x6fce398)//48)]*3))),(0,16))[1],
                0x1692eb7:lambda m:calls.append((0x1692eb7,0,m.argument(0),*v.read_vec(m,m.argument(1)),m.argument(2),*v.read_vec(m,m.argument(3)),m.argument(5),int(m.argument(4)==v.OBJECTS),m.argument(6),m.argument(7))) or 0}
        regions=v.global_regions(world,6,[am.defined_region('object',v.OBJECTS,bytes(o)),
                   am.defined_region('model',v.MODEL,bytes(model)),am.defined_region('time',v.TIME,v.pack_f(time),writable=False),
                   am.defined_region('bounds',v.BOUNDS,struct.pack('<i',0),writable=False)])
        start=0xe949f8
        args=[v.OBJECTS,0,0,0] if world==3 else [v.OBJECTS,v.MODEL,0]
        result=v.run(machine,start,args,regions,stubs,ecx=v.FAKE,cleanup=12 if world in (0x39,0x50) else 0)
        stop=v.stopped_reason(result)
        if stop:t.add(False,{'case':n,'world':world,'type':typ},stop);continue
        co=C.create_string_buffer(bytes(o),v.OBJ_SIZE);log=v.new_log()
        def bone(c,k,local,out):
            for q in range(3):out[q]=float(k)
        bonefn=BONE(bone)
        lib.dll.mu_raklion_before(co,0,C.byref(log));lib.dll.mu_world_defer(co,world);native=v.log_events(log)
        t.count(f'world {world:#x} type {typ:#x}')
        t.add(calls==native and result['regions']['object']==co.raw,
              {'case':n,'world':world,'type':typ,'client':calls,'native':native,
               'obj':result['regions']['object']==co.raw})
    return t

def family_flags(machine,lib,g,cases):
    t=v.Tally('flags')
    for n in range(cases):
        world=[0x33,0x39,0x50][n%3];typ=g.choice(DEFER_TYPES[world]+[0x100])
        o=bytearray(v.poison_object(g));v.put_i(o,0x5c,typ);v.put_f(o,0xd0,0);o[0xa]=g.choice([0,1,2])
        model=bytes(0x100)
        stubs={0x966def:lambda m:(0,32),0x966e4a:lambda m:(0,32),0x1989721:lambda m:0}
        regions=v.global_regions(world,6,[am.defined_region('object',v.OBJECTS,bytes(o)),
                    am.defined_region('model',v.MODEL,model),am.defined_region('time',v.TIME,v.pack_f(1234),writable=False)])
        start={0x33:0xe31985,0x39:0xe949f8,0x50:0xe14596}[world]
        result=v.run(machine,start,[v.OBJECTS,v.MODEL,0],regions,stubs,ecx=v.FAKE,cleanup=12 if world in (0x39,0x50) else 0)
        stop=v.stopped_reason(result)
        if stop:t.add(False,{'case':n,'world':world,'type':typ},stop);continue
        co=C.create_string_buffer(bytes(o),v.OBJ_SIZE);lib.dll.mu_world_defer(co,world)
        t.count(f'world {world:#x} type {typ:#x}')
        t.add(result['regions']['object'][0xa]==co.raw[0xa],{'case':n,'world':world,'type':typ})
    return t

# Reuse the particle oracle's record/GL comparisons with only this lane's five emitted kinds.
import validate_particles as vp
FLAME_KINDS=[(0x7f5a,21),(0x8016,0),(0x8084,0),(0x806e,4),(0x8085,0)]
def particle_family(machine,lib,g,cases,family):
    old=vp.KINDS;vp.KINDS=FLAME_KINDS
    report=vp.Report()
    try:dict(vp.FAMILIES)[family](machine,lib.particles,g,cases,report,{k:0 for k in vp.NEGATIVES})
    finally:vp.KINDS=old
    result=report.families[family];t=v.Tally('particle_'+family);t.cases=result['cases'];t.equal=result['equal']
    t.mismatches=result['first_failures'];t.cover=report.coverage
    return t
def family_particle_create(m,l,g,n):return particle_family(m,l,g,n,'create')
def family_particle_move(m,l,g,n):return particle_family(m,l,g,n,'move')
def family_particle_render(m,l,g,n):return particle_family(m,l,g,n,'render')

FAMILIES={'kanturu':family_kanturu,'karutan':family_karutan,'after_pass':family_after_pass,'after_draw':family_after_draw,'flags':family_flags,'first_draw':family_first_draw,
 'particle_create':family_particle_create,'particle_move':family_particle_move,'particle_render':family_particle_render}
MUTATIONS=[('Kanturu fire bitmap','world_kanturu_visual.c','0x8016,0','0x8017,0','kanturu'),
 ('Kanturu bone','world_kanturu_visual.c','bone(c,6','bone(c,5','kanturu'),
 ('Karutan fire subtype','world_karutan_visual.c','0x806e,4','0x806e,0','karutan'),
 ('Karutan sprite size','world_karutan_visual.c','2.0f*mu_obj','3.0f*mu_obj','karutan'),
 ('After byte equals one','world_after.c','o[MU_OBJF_AFTER_CHARACTER]!=1','!o[MU_OBJF_AFTER_CHARACTER]','after_pass'),
 ('After special visibility','world_after.c','if(special || o[MU_OBJF_VISIBLE]','if(o[MU_OBJF_VISIBLE]','after_pass'),
 ('Elbeland after flag','world_elbeland_visual.c','o[MU_OBJF_AFTER_CHARACTER]=1','o[MU_OBJF_AFTER_CHARACTER]=0','flags'),
 ('Raklion glow mesh','world_raklion_visual.c','wv_mesh(o,i,1,0x42,1','wv_mesh(o,i,0,0x42,1','after_draw'),
 ('Karutan scrolling period','world_karutan_visual.c','%10000','%1000','after_draw'),
 ('Raklion first blend','world_raklion_visual.c','wv_mesh(o,i,2,0x42,2','wv_mesh(o,i,2,2,2','first_draw'),
 ('Karutan flame lifetime','../particles/world_flames.c','?27:', '?26:','particle_create'),
 ('Karutan flame rise','../particles/world_flames.c','p->position[2]+=p->gravity','p->position[2]-=p->gravity','particle_move'),
 ('Kanturu smoke blend','../particles/particles.c','p->subtype == 2 || p->subtype == 21','p->subtype == 2','particle_render')]
def build(root):
 subprocess.run(['make','-s','-C',str(root/'particles')],check=True)
 subprocess.run(['make','-s','-C',str(root/'objects')],check=True)
 lib=Library(root/'objects'/('libobjects.'+v.SUFFIX))
 lib.particles=vp.load_library(root/'particles'/('libclient_particles.'+v.SUFFIX))
 return lib
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=int,default=1000);p.add_argument('--only')
 p.add_argument('--text',default=v.pins.TEXT.default_str());p.add_argument('--data',default=v.pins.DATA.default_str());
 p.add_argument('--mutations',action='store_true');p.add_argument('--output');a=p.parse_args()
 text=am.load_pinned(a.text,am.TEXT_BYTES,am.TEXT_SHA256,'text')
 data=am.load_pinned(a.data,am.DATA_BYTES,am.DATA_SHA256,'data')
 m=vp.PtMachine(text,data);lib=build(ROOT/'reconstructed');names=a.only.split(',') if a.only else list(FAMILIES)
 report={'text_sha256':am.TEXT_SHA256,'data_sha256':am.DATA_SHA256,'families':{},'mutations':[],
 'bodies':{k:{'start':hex(b),'end':hex(e),'sha256':hashlib.sha256(text[b-am.TEXT_BASE:e-am.TEXT_BASE]).hexdigest()} for k,(b,e) in BODIES.items()}}
 for name in names:
  t=FAMILIES[name](m,lib,random.Random(0xa017+list(FAMILIES).index(name)),a.cases);report['families'][name]=t.report()
  print(name,json.dumps(t.report()),flush=True)
 if a.mutations:
  for name,file,old,new,family in MUTATIONS:
   if family not in names:continue
   with tempfile.TemporaryDirectory(prefix='world-a-mut-') as tmp:
    root=Path(tmp)
    for d in ['objects','terrain','record-math','model-codec','particles','movement']:
     shutil.copytree(ROOT/'reconstructed'/d,root/d,ignore=shutil.ignore_patterns('*.dylib','*.so','__pycache__'))
    file=root/'objects'/file;s=file.read_text();pattern=''.join(re.escape(ch)+r'\s*' for ch in old)
    s,count=re.subn(pattern,lambda m:new,s,count=1);assert count==1,(name,old);file.write_text(s)
    t=FAMILIES[family](m,build(root),random.Random(0xa017+list(FAMILIES).index(family)),300)
    item={'name':name,'cases':t.cases,'detected':t.cases-t.equal-t.stopped};report['mutations'].append(item);print(item,flush=True)
 report['ok']=all(x['mismatch_count']==0 and x['stopped']==0 for x in report['families'].values()) and all(x['detected']>0 for x in report['mutations'])
 if a.output:Path(a.output).write_text(json.dumps(report,indent=1))
 return 0 if report['ok'] else 1
if __name__=='__main__':sys.exit(main())
