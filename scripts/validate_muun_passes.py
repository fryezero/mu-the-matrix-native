#!/usr/bin/env python3
"""MUUN-VISUAL-002: ordinary Muun mesh passes and same-owner command actions.

Runs the whole 0x017f76ec caller with item/render lookups and vector access recorded, the pulse
0x0185bdc4 executed and only CRT cosine supplied as a math service. Special-model branches are excluded.
Runs 0x009c2539 with equal owner keys and an absent authored target, isolating the category/action branch.
No remote target, packet, bonus, damage or protection code is executed.
"""
import argparse
import ctypes as C
import hashlib
import json
import itertools
import math
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import time
import actor_machine as am
import pins
import validate_combat as vc

ROOT = Path(__file__).resolve().parents[1]
F3 = C.c_float * 3
MODEL, OBJ, ITEM, INFO, ROW, POINTER, AUX = [0x22000000 + 0x10000*k for k in range(7)]
BODIES = {'mesh': (0x17f76ec, 0x17f919e), 'command': (0x9c2539, 0x9c29dc),
          'wave': (0x185bdc4, 0x185be96), 'shadow': (0x9aa54b, 0x9aa6ed)}


class Pass(C.Structure):
    _fields_ = [(n, C.c_int32) for n in ('mesh','flags','blend','texture')] + [
        ('alpha', C.c_float), ('light', C.c_float), ('color', F3)]


def build(folder, source):
    p = Path(folder)
    (p/'passes.c').write_text(source)
    output = p/('passes.dylib' if sys.platform == 'darwin' else 'passes.so')
    subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wconversion','-fPIC',
                    '-ffp-contract=off','-fno-fast-math','-shared','-I',str(ROOT/'reconstructed/muun'),
                    str(p/'passes.c'),'-lm','-o',str(output)],check=True,capture_output=True)
    lib = C.CDLL(str(output))
    lib.mu_mv_mesh_pass.argtypes = [C.c_void_p,C.POINTER(C.c_float),C.c_float,C.c_int32,C.c_float,
                                   C.c_int32,C.c_float,C.POINTER(Pass)]
    lib.mu_mv_command_action.argtypes = [C.c_int32]
    lib.mu_mv_shadow_alpha.argtypes = [C.c_int32,C.c_int,C.c_int,C.c_float,C.c_float]
    lib.mu_mv_shadow_alpha.restype = C.c_float
    return lib


def decoded(name):
    # Reuse the independently instruction-verified table decoder; decoded bytes stay in memory.
    import validate_data_tables as dt
    suffix = 'dylib' if sys.platform == 'darwin' else 'so'
    lib = dt.Library(ROOT/f'reconstructed/data/libdatatables.{suffix}')
    spec = lib.dll.mu_data_find(name.lower().encode())
    image = (Path(os.environ['MU_GAME_ROOT'])/'Data/Local'/name).read_bytes()
    status, result, _, payload = lib.decode(spec,image)
    if status: raise ValueError(f'{name}: decode status {status}')
    size = dt.MuDataSpec.from_address(spec).record_size
    return [payload[result.records_offset+k*size:result.records_offset+(k+1)*size] for k in range(result.records)]


def samples(count, installed):
    rng = random.Random('muun-visual-002')
    for k in range(count):
        row = bytearray(300)
        struct.pack_into('<ii',row,0,8347,k%6)
        struct.pack_into('<7fI',row,0x108,*[rng.uniform(0,1) for _ in range(4)],
                         rng.choice([0.5,1,2,4]),rng.uniform(0,0.2),rng.uniform(0.4,1),rng.choice([2,4,8,0x42]))
        row[0x128:0x12c] = bytes((k>>b)&1 for b in range(4))
        yield 0x2b81, k%2, [bytes(row)], rng.choice([0,1,20,3141,6283,123456,-1000])
    if installed:
        records = decoded('MuunRenderInfo.bmd')
        meshes = decoded('MuunMeshInfo.bmd')
        # The 15 codes with attachment records. No decoded records are serialized in reports.
        for code in (173,174,175,176,177,178,183,184,189,190,214,215,234,235,363):
            r = next(x for x in records if struct.unpack_from('<i',x)[0] == code)
            item = struct.unpack_from('<i',r,4)[0]
            for clock in (0,3141,123456):
                yield item+0xae6,r[0x258],[m for m in meshes if struct.unpack_from('<i',m)[0] == item],clock


def compare(lib,machine,count,installed):
    rows = {'mesh': {'cases':0,'mismatches':0}, 'command': {'cases':0,'mismatches':0}, 'shadow': {'cases':0,'mismatches':0}}
    for model,body,records,clock in samples(count,installed):
        obj,mdl,item,info = bytearray(0x3d8),bytearray(0x100),bytearray(0x260),bytearray(0x27c)
        color = F3(0.7,0.5,0.3)
        struct.pack_into('<i',obj,0x5c,model)
        struct.pack_into('<i',obj,0x74,-1)
        struct.pack_into('<f',obj,0xa8,0.75)
        struct.pack_into('<f',obj,0xdc,0.8)
        struct.pack_into('<3f',mdl,0x54,*color)
        item[0x250:0x252] = bytes([12,1]);info[0x258] = body
        calls=[]
        def record(m,mesh):
            args=[m.argument(k) for k in range(8)]
            calls.append((mesh,args,bytes(m.uc.mem_read(MODEL+0x54,12))))
            return 0,32
        rs=[]
        textures=[-1 if k%2 else 0xa000+k for k in range(len(records))]
        ptr=bytearray(max(4,len(records)*4))
        for k,r in enumerate(records):
            struct.pack_into('<I',ptr,k*4,ROW+0x1000*k)
            rs.append(am.defined_region(f'row{k}',ROW+0x1000*k,r+struct.pack('<i',textures[k])))
        stubs={0xcd4ea8:lambda m:0,0xcd5d29:lambda m:(ITEM,4),0x1807c1f:lambda m:0,
               0x9c2aea:lambda m:0,0x1807c32:lambda m:(INFO,4),0x9beaa7:lambda m:len(records),
               0x9bca89:lambda m:(POINTER+4*m.argument(0),4),
               0x966def:lambda m:record(m,False),0x966e4a:lambda m:record(m,True),
               0x9fa223:lambda m:m.x87_return(vc.f32(math.cos(m.float_argument(0))))}
        regions=[am.defined_region(n,a,p) for n,a,p in [('object',OBJ,obj),('model',MODEL,mdl),
            ('item',ITEM,item),('info',INFO,info),('pointers',POINTER,ptr),
            ('clock',0x6fce370,struct.pack('<f',clock))]]+rs
        result=machine.execute(0x17f76ec,[MODEL,OBJ,1,0,0,0xffffffff,0xffffffff],regions,stubs)
        expected=[]
        f=lambda x:struct.unpack('<I',struct.pack('<f',x))[0]
        if body:expected.append((False,[2,f(0.8),0xffffffff,f(0.75),0,0,0,0xffffffff],struct.pack('<3f',*color)))
        # Base OBJECT hidden_mesh is zero; body call uses it, mesh wrapper's last argument is texture.
        for k,r in enumerate(records):
            p=Pass();lib.mu_mv_mesh_pass(r,color,0.8,-1,0.75,textures[k],float(clock),C.byref(p))
            expected.append((True,[p.mesh & 0xffffffff,p.flags & 0xffffffff,f(p.alpha),p.blend & 0xffffffff,
                                   f(p.light),0,0,p.texture & 0xffffffff],struct.pack('<3f',*p.color)))
        row=rows['mesh'];row['cases']+=1
        if not result['ok'] or calls!=expected or result['regions']['model'][0x54:0x60]!=struct.pack('<3f',*color):
            row['mismatches']+=1
            if 'first' not in row:row['first']={'ok':result['ok'],'checks':result['checks'],'error':str(result.get('error')),
                'stopped':str(result.get('stopped')),'got':repr(calls),'expected':repr(expected)}
    for category in list(range(-1,102))+[2**31-1,-2**31]:
        aux=bytearray(0x54);char=bytearray(0x40);obj=bytearray(0x3d8)
        struct.pack_into('<i',aux,8,77);struct.pack_into('<i',aux,12,category)
        stubs={0x95f6db:lambda m:(ITEM,4),0x9a1927:lambda m:77,0x137c724:lambda m:0,
               0x9a13f4:lambda m:0}
        actions=[]
        def action(m):actions.append(m.argument(1));return 0
        stubs[0x12affa4]=action
        r=machine.execute(0x9c2539,[123,0], [am.defined_region('aux',AUX,aux),
            am.defined_region('char',ITEM,char),am.defined_region('object',OBJ,obj)],stubs,ecx=AUX,cleanup=8)
        got=lib.mu_mv_command_action(category)
        row=rows['command'];row['cases']+=1
        if not r['ok'] or actions != ([] if got==-1 else [got]):
            row['mismatches']+=1
            if 'first' not in row:row['first']={'got':actions,'expected':got,'checks':r['checks'],'error':str(r.get('error')),'stopped':str(r.get('stopped'))}
    color_import=vc.HELPER+0x500
    machine.uc.mem_write(0x1a7c754,struct.pack('<I',color_import))
    worlds=(-1,0,7,10,23,24,29,30,35,36,127,128,129,130,131,132)
    for world,option,kind,alpha in itertools.product(worlds,(0,1),(1,2),(-0.5,0,0.4,0.8)):
        slot=bytearray(0xbc);obj=bytearray(0x3d8);info=bytearray(0x27c);owner=bytearray(0x3d8)
        struct.pack_into('<III',slot,4,0,OBJ,INFO)
        struct.pack_into('<i',obj,0x5c,0x2b81);struct.pack_into('<I',obj,0x34c,ITEM)
        struct.pack_into('<f',obj,0xdc,alpha);owner[0x3a]=kind
        struct.pack_into('<f',info,0x254,0.6)
        colors=[];calls=[]
        def color(m):colors.append(m.float_argument(3));return 0,16
        def shadow(m):calls.append([m.argument(k) for k in range(5)]);return 0,20
        stubs={0x966cc4:lambda m:(MODEL,4),0xeaa8cf:lambda m:MODEL,0x9a6ef3:lambda m:MODEL,
               0x9a645f:lambda m:option,0x184a990:lambda m:0,color_import:color,0x12bc07a:shadow}
        regions=[am.defined_region(n,a,p) for n,a,p in [('slot',AUX,slot),('object',OBJ,obj),
            ('info',INFO,info),('owner',ITEM,owner),('world',0x1cf15fc,struct.pack('<i',world))]]
        r=machine.execute(0x9aa54b,[],regions,stubs,ecx=AUX)
        got=lib.mu_mv_shadow_alpha(world,option,kind,alpha,0.6)
        expected=[] if got==0 else [got]
        row=rows['shadow'];row['cases']+=1
        if not r['ok'] or colors!=expected or (calls and calls!=[[0xffffffff,0xffffffff,0xffffffff,0xffffffff,0]]):
            row['mismatches']+=1
            if 'first' not in row:row['first']={'world':world,'got':colors,'expected':expected,
                'checks':r['checks'],'stopped':str(r.get('stopped')),'error':str(r.get('error'))}
    return rows


MUTANTS=[('texture','out->texture = texture','out->texture = texture ^ 1'),('mesh','integer(r, 4)','integer(r, 0)'),('flags','integer(r, 0x124)','2'),
 ('blend_gate','if (r[0x129])','if (!r[0x129])'),('blend_mesh','out->blend = out->mesh','out->blend = -1'),
 ('wave_gate','r[0x128] ?','!r[0x128] ?'),('wave_sign','wave(-number','wave(number'),
 ('range','number(r, 0x120) - number(r, 0x11c)','number(r, 0x120) + number(r, 0x11c)'),
 ('alpha_gate','if (r[0x12b])','if (!r[0x12b])'),('color_gate','if (r[0x12a])','if (!r[0x12a])'),
 ('command3','case 50: case 53: return 3','case 50: case 53: return 4'),
 ('shadow_world','world == 10','world == 11'),
 ('shadow_owner','owner_kind == 2','owner_kind == 1'),
 ('shadow_water','? 0.2f : 0.0f','? 0.5f : 0.0f'),
 ('command4','case 51: case 52: case 54: case 55: return 4','case 51: case 52: case 54: case 55: return 3')]


def run(count,mutations,installed):
    started=time.monotonic()
    text=pins.load_pinned(pins.TEXT.default_str(),pins.TEXT.size,pins.TEXT.sha256,"text")
    data=pins.load_pinned(pins.DATA.default_str(),pins.DATA.size,pins.DATA.sha256,"data")
    machine=vc.Combat(text,data)
    source=(ROOT/'reconstructed/muun/passes.c').read_text()
    with tempfile.TemporaryDirectory(prefix='muun-passes-') as td:
        base=Path(td)/'base';base.mkdir();families=compare(build(base,source),machine,count,installed)
        mutants={}
        if mutations:
            for name,old,new in MUTANTS:
                if source.count(old)!=1:raise ValueError(f'{name}: ambiguous anchor')
                folder=Path(td)/name;folder.mkdir()
                rows=compare(build(folder,source.replace(old,new)),machine,count,False)
                mutants[name]={'caught':sum(r['mismatches'] for r in rows.values())}
    return {'families':families,'cases':sum(r['cases'] for r in families.values()),
        'all_equal':all(r['mismatches']==0 for r in families.values()),'mutants':mutants,
        'all_mutants_caught':all(r['caught']>0 for r in mutants.values()),
        'installed_codes':15 if installed else 0,
        'bodies':{n:{'start':hex(a),'end':hex(b),'sha256':hashlib.sha256(text[a-am.TEXT_BASE:b-am.TEXT_BASE]).hexdigest()} for n,(a,b) in BODIES.items()},
        'wall_seconds':time.monotonic()-started}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=int,default=1000)
    p.add_argument('--mutations',action='store_true');p.add_argument('--installed',action='store_true')
    p.add_argument('--output',type=Path);a=p.parse_args()
    result=run(a.cases,a.mutations,a.installed)
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));sys.exit(0 if result['all_equal'] and result['all_mutants_caught'] else 1)
