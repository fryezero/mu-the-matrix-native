#!/usr/bin/env python3
"""RENDER-TERRAIN-002: compiled terrain C against pinned original instructions.

Synthetic inputs only. Reports stay local. Imports, texture lookups, random
numbers, particle allocation, buff predicates and camera singleton are explicit
host boundaries. Terrain arithmetic, reflection, signed-grid updates and mesh
construction run as original instructions. No original client is launched.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
import sys

import pins
import validate_terrain as v


class Grid(C.Structure):
    _fields_ = [('world', C.c_int32), ('grid', C.c_int32 * (4*v.CELLS)), ('active', C.c_int32),
                ('light', C.c_float*3), ('vertex', C.c_float*(1764*3)),
                ('normal', C.c_float*(1764*3)), ('indices', C.c_int32*10584), ('count', C.c_int32)]


def compare(client, lib, scale=1):
    from unicorn import UC_HOOK_CODE
    uc=client.uc
    out={}
    g=random.Random(27002)
    lib.mu_terrain_reflection_uv.argtypes=[v.VOIDP]*3
    lib.mu_terrain_signed_init.argtypes=[v.VOIDP,C.c_int32]
    lib.mu_terrain_signed_step.argtypes=[v.VOIDP]
    lib.mu_terrain_signed_wave.argtypes=[v.VOIDP,C.c_int32,C.c_int32,C.c_float]
    lib.mu_terrain_signed_height.argtypes=[v.VOIDP,C.c_float,C.c_float]
    lib.mu_terrain_signed_height.restype=C.c_float
    lib.mu_terrain_signed_mesh.argtypes=[v.VOIDP,C.c_int32,C.c_int32]
    lib.mu_terrain_signed_draw.argtypes=[v.VOIDP,C.POINTER(v.Sink)]
    base=0x20000000
    uc.mem_map(base,0x200000)
    uc.mem_map(0x72ac000,0x5000)
    obj=Grid()
    def run(addr, words=(), cleanup=0):
        assert client.call(addr,list(words),ecx=base,cleanup=cleanup), (hex(addr),client.error)
    def family(name):
        print(name, flush=True)
        out[name]={'cases':0,'matches':0,'output_controls_detected':0}
        return out[name]
    def check(row, got, expected, mutant=None):
        row['cases']+=1
        if got==expected: row['matches']+=1
        elif 'first_mismatch' not in row:
            row['first_mismatch']={'client':str(got)[:400], 'authored':str(expected)[:400]}
            if isinstance(got,(bytes,list)) and isinstance(expected,type(got)):
                at=next((i for i,(a,b) in enumerate(zip(got,expected)) if a!=b),min(len(got),len(expected)))
                row['first_mismatch'].update(at=at,got=str(got[max(0,at-4):at+4]),expected=str(expected[max(0,at-4):at+4]))

        if mutant is not None and mutant!=got: row['output_controls_detected']+=1
    # Reflection helper, direct inputs avoid replacing either normalization.
    row=family('reflection_uv_016c977c')
    for _ in range(500*scale):
        a=[v.f32(g.uniform(-1,1)) for _ in range(3)]; n=[v.f32(g.uniform(-1,1)) for _ in range(3)]
        uc.mem_write(base,struct.pack('<6f',*a,*n))
        run(0x16c977c,[base,base+12,base+24])
        mine=v.floats([0,0]); lib.mu_terrain_reflection_uv(v.floats(a),v.floats(n),mine)
        got=bytes(uc.mem_read(base+24,8)); expected=bytes(mine)
        check(row,got,expected,struct.pack('<2f',mine[1],mine[0]))
    # Direct RenderFace covers layer/detail/attribute boundaries and reflected UVs.
    # glTexCoord2fv is outside the old validator's import range.
    stub=client.STUBS+0x2000
    uc.mem_write(0x1a7c65c,struct.pack('<I',stub+8)); uc.mem_write(stub+8,b'\xc2\x04\x00');
    uc.mem_write(0x1a7c66c,struct.pack('<I',stub)); uc.mem_write(stub,b'\xc2\x04\x00')
    def tex_hook(uc_,addr,size,unused):
        client.stream.append(('tex',)+client.read_floats(client.arg(0),2))
    uc.hook_add(UC_HOOK_CODE,tex_hook,begin=stub,end=stub)
    row=family('overlay_face_016cf46c')
    authored=v.Authored(lib._name)
    for w in [0x71,0x91]:
        scene=v.synthetic_scene(2700+w,w,extended=True)
        scene['normal']=[0.0,0.0,1.0]*v.CELLS
        scene['reflection_uv']=[v.f32(g.uniform(-1,2)) for _ in range(2*v.CELLS)]
        scene['camera_position']=[12000.0,13000.0,1800.0]
        scene['sizes'][0x7722]=(256.0,256.0)
        client.load_scene(scene)
        built=authored.scene(scene)
        for k in range(120*scale):
            x,y=g.randrange(1,253),g.randrange(1,253); i=y*256+x
            scene['att'][i]=(0x2000 if k%3 else 0)
            uc.mem_write(v.G['att']+i*2,struct.pack('<H',scene['att'][i]))
            C.cast(built[0].attributes,C.POINTER(C.c_uint16))[i]=scene['att'][i]
            # Tile wrapper independently verifies corners and UV setup too.
            built[0].detail=4 if k%5 else 3
            uc.mem_write(client.CONFIG+0x2c,struct.pack('<i',built[0].detail))
            client.write('pass_','i',[0]); client.extra={v.CHAOS_EFFECTS:v.ret_with(0)}
            ok=client.call(v.TILE,[v.fbits(float(x)),v.fbits(float(y)),x,y,v.fbits(1.0),1,0])
            status,expected=authored.draw_tile(built,0,float(x),float(y),x,y)
            check(row,client.stream,expected,[r for r in expected if r[:2]!=('bind',0x7722)])
            if not ok or status: row.setdefault('execution_errors',[]).append([w,x,y,client.error,status])
    client.extra={}
    row=family('reflection_normals_016c936a')
    scene=v.synthetic_scene(111,0x71); client.load_scene(scene)
    run(0x16c936a); run(0x16c95f9)
    built=authored.scene(scene); normal=v.floats([0.0]*(3*v.CELLS)); uv=v.floats([0.0]*(2*v.CELLS))
    lib.mu_terrain_reflection_init.argtypes=[C.POINTER(v.Scene),v.VOIDP,v.VOIDP]
    lib.mu_terrain_reflection_init(C.byref(built[0]),normal,uv)
    check(row,bytes(uc.mem_read(0xb8b5430,12*v.CELLS)),bytes(normal),bytes([0])*(12*v.CELLS))
    row=family('reflection_grid_016c95f9')
    check(row,bytes(uc.mem_read(0xb975430,8*v.CELLS)),bytes(uv),bytes([0])*(8*v.CELLS))
    # Camera FOV and interpolator singletons are substituted, arithmetic stays live.
    row=family('camera_frustum_016d20d9')
    camera,sub,interp=client.OBJECTS+0x8000,client.OBJECTS+0x8100,client.OBJECTS+0x8200
    uc.mem_write(camera,b'\0'*0x100);uc.mem_write(camera+0xc,struct.pack('<I',sub));uc.mem_write(camera+0x10,struct.pack('<f',1))
    uc.mem_write(sub,b'\0'*0x100);uc.mem_write(sub+0x18,struct.pack('<3f',1,1,35));uc.mem_write(v.FOV,struct.pack('<f',35))
    special=[0]
    def boundary(uc_,addr,size,unused):
        if addr==0x94997e: client.ret(uc_.reg_read(client.x86.UC_X86_REG_ECX),4)
        elif addr==0x8e83a0: client.ret(0,0)
        elif addr==0x129debb: client.ret(special[0],4)
        elif addr==0x988c5c: client.ret(interp,0)
    hooks=[uc.hook_add(UC_HOOK_CODE,boundary,begin=a,end=a) for a in [0x94997e,0x8e83a0,0x129debb,0x988c5c]]
    lib.mu_terrain_frustum_2d_camera.argtypes=[C.c_int32,v.VOIDP,v.VOIDP,v.VOIDP,C.c_int,C.c_int,C.c_float,v.VOIDP,v.VOIDP]
    for k in range(120*scale):
        w=[6,0x49][k%2]; special[0]=int(k%4==0); width=[640,1024,1920][k%3]; mode=k%6
        pitch=v.f32(g.uniform(30,90));offset=v.fsub(pitch,89.5)
        uc.mem_write(interp+0x5c,struct.pack('<f',pitch));uc.mem_write(v.SCENE_STATE,struct.pack('<i',5));uc.mem_write(v.ZOOM_MODE,struct.pack('<i',mode))
        uc.mem_write(0x1cf1860,struct.pack('<f',0));uc.mem_write(0xbdc5ef0,struct.pack('<f',1))
        client.write('world','i',[w]);angle=[v.f32(g.uniform(-90,0)),v.f32(g.uniform(-15,15)),v.f32(g.uniform(-180,180))]
        position=[v.f32(g.uniform(2000,20000)),v.f32(g.uniform(2000,20000)),0.0]
        uc.mem_write(v.CAMERA_ANGLE,struct.pack('<3f',*angle));uc.mem_write(client.CONFIG+0x500,struct.pack('<3f',*position))
        client.extra={v.CAMERA_SINGLETON:v.ret_with(camera),v.SCREEN_WIDTH:v.ret_with(width)}
        run(v.FRUSTUM_2D,[client.CONFIG+0x500,k%2])
        got=bytes(uc.mem_read(v.F_X2D,32));client.extra={}
        _,params=authored.params_2d(w,mode,width,v.fdiv(float(width),640.0),2400.0)
        if w==6 and special[0]:params=[8500.0,v.fmul(8500,0.05),v.fmul(8500,0.47),v.fmul(3000,v.fdiv(float(width),640)),v.fmul(540,v.fdiv(float(width),640))]
        xs,ys=v.floats([0]*4),v.floats([0]*4)
        lib.mu_terrain_frustum_2d_camera(w,v.floats(position),v.floats(angle),v.floats(params),k%2,special[0],offset,xs,ys)
        check(row,got,bytes(xs)+bytes(ys),struct.pack('<8f',*([0.0]*8)))
    for h in hooks:uc.hook_del(h)
    # Bounded GL setup region, no camera/projection calls omitted from this comparison.
    row=family('fog_alpha_0184b043_0184b0bb')
    calls=[]
    specs={0x1a7c6d0:('alpha',2),0x1a7c670:('fogi',2),0x1a7c724:('fogf',2),0x1a7c69c:('fogfv',2)}
    saved={a:bytes(uc.mem_read(a,4)) for a in specs}
    stubs={}
    for i,(slot,(name,n)) in enumerate(specs.items()):
        addr=client.STUBS+0x3000+16*i;stubs[addr]=(name,n);uc.mem_write(slot,struct.pack('<I',addr));uc.mem_write(addr,b'\xc2'+struct.pack('<H',n*4))
    def gl_env(uc_,addr,size,unused):
        name,n=stubs[addr];args=[client.arg(i) for i in range(n)]
        if name=='fogfv':args[1:]=list(client.read_floats(args[1],4))
        calls.append((name,*args))
    h=uc.hook_add(UC_HOOK_CODE,gl_env,begin=min(stubs),end=max(stubs))
    class Env(C.Structure):_fields_=[('alpha',C.c_float),('fog',C.c_int32),('density',C.c_float),('color',C.c_float*4)]
    lib.mu_terrain_environment_config.argtypes=[C.c_int,C.c_float,v.VOIDP,C.POINTER(Env)]
    for k in range(100*scale):
        enabled=k%2;density=v.f32(g.random());color=[v.f32(g.random()) for _ in range(4)];calls.clear()
        uc.mem_write(0xbdc597c,bytes([enabled]));uc.mem_write(0x1cf160c,struct.pack('<5f',density,*color))
        assert client.call(0x184b043,[],until=0x184b0bb)
        env=Env();lib.mu_terrain_environment_config(enabled,density,v.floats(color),C.byref(env))
        expected=[('alpha',0x204,v.fbits(env.alpha))]
        if env.fog:expected += [('fogi',0xb65,0x2601),('fogf',0xb62,v.fbits(env.density)),('fogfv',0xb66,*map(v.fbits,env.color))]
        expected_enable=('glEnable' if enabled else 'glDisable',0xb60)
        check(row,(calls,client.gl_state),(expected,[expected_enable]),([],[]))
    uc.hook_del(h)
    for slot,raw in saved.items():uc.mem_write(slot,raw)
    row=family('chaos_face_009dc0b1')
    lib.mu_terrain_chaos_face.argtypes=[C.POINTER(v.Scene),C.c_int32,C.c_int32]
    emitted=shakes=0
    scene=v.synthetic_scene(0,0); client.load_scene(scene)
    for k in range(600*scale):
        w=g.choice([0x12,0x17,0x35,0x61,0,0x18]); state=g.choice([0,3,6,1,5])
        x=g.choice([22,23,24,25,26,27,28,39,40,41,42,43,44,45]); y=g.choice([74,75,76,77,78,79,80,81,102,103,104,105,106,107,108,109])
        seq=[g.randrange(32768) for _ in range(5)]; seq[0]=0 if k%2 else seq[0]
        scene['world']=w; scene['chaos_state']=state; scene['hero_z']=v.f32(g.uniform(-100,1000))
        at=[0]
        def rand():
            val=seq[at[0]]; at[0]+=1; return val
        scene['random']=rand; cb=v.RANDOM_CALLBACK(lambda _:rand()); effects=[]; ecb=v.EFFECT_CALLBACK(lambda _,kind,pos,light:effects.append(('effect',kind,*[v.fbits(pos[i]) for i in range(3)]))); built=(v.Scene(),None); built[0].world_index=w; built[0].random=cb; built[0].effect=ecb; built[0].hero_z=scene['hero_z']; built[0].chaos_state=state; shake=C.c_float(9.0); built[0].camera_shake=C.cast(C.pointer(shake),v.VOIDP)
        lib.mu_terrain_chaos_face(C.byref(built[0]),x,y)
        expected=(list(effects),v.fbits(shake.value),at[0])
        client.write('world','i',[w]); uc.mem_write(client.OBJECTS+0x33ac+8,struct.pack('<f',scene['hero_z'])); uc.mem_write(0x1cf0467,bytes([state])); uc.mem_write(0xbdb588c,struct.pack('<f',9.0))
        at[0]=0; effects=[]
        client.extra={v.CRT_RAND:lambda c:c.ret(rand(),0), v.PARTICLE:lambda c:(effects.append(('effect',c.arg(0))+c.read_floats(c.arg(1),3)),c.ret(0,0))}
        run(v.CHAOS_EFFECTS,[x,y]); got=(effects,struct.unpack('<I',uc.mem_read(0xbdb588c,4))[0],at[0])
        check(row,got,expected,([],v.fbits(9.0),at[0]))
        emitted+=len(effects); shakes+=int(got[1]!=v.fbits(9.0))
    row.update(particles=emitted,shake_writes=shakes); client.extra={}
    # Record layout + clear, wave stencil, signed query, vertex/normal/index build, and full draw stream.
    row=family('signed_init_009f953b')
    for w in [0x18,0x1d,0x24]:
        uc.mem_write(base,b'\xa5'*C.sizeof(Grid)); uc.mem_write(base,struct.pack('<i',w))
        # Constructor owns active and count; Init clears just grids and direction.
        run(0x9f953b); lib.mu_terrain_signed_init(C.byref(obj),w)
        check(row,bytes(uc.mem_read(base+4,0x100000)),bytes(obj)[4:0x100004],bytes([1])*0x100000)
    row=family('signed_ripple_009f9952')
    lib.mu_terrain_signed_ripple.argtypes=[v.VOIDP]+[C.c_int]*5+[v.RANDOM_CALLBACK,v.VOIDP]
    for k in range(40*scale):
        x,y=g.choice([0,1,32,128,254,255,-1]),g.choice([0,1,128,254,255,-1]);rx,ry=g.choice([(20,2),(4,4),(1,1),(10,3)])
        obj.active=k%2;amplitude=g.choice([2000,100,-2000,0]);uc.mem_write(base,bytes(obj));at=[0];seq=[123,456]
        def rand():r=seq[at[0]];at[0]+=1;return r
        client.extra={v.CRT_RAND:lambda c:c.ret(rand(),0)}
        run(0x9f9952,[x,y,rx,ry,amplitude],20);at[0]=0;cb=v.RANDOM_CALLBACK(lambda _:rand())
        lib.mu_terrain_signed_ripple(C.byref(obj),x,y,rx,ry,amplitude,cb,None)
        check(row,bytes(uc.mem_read(base+4,8*v.CELLS)),bytes(obj)[4:4+8*v.CELLS],bytes([0])*(8*v.CELLS))
    client.extra={}
    row=family('signed_step_009f85fc')
    for k in range(12*scale):
        obj.active=k%2
        for i in range(2*v.CELLS): obj.grid[i]=g.randrange(-20000,20000)
        uc.mem_write(base,bytes(obj)); run(0x9f85fc); lib.mu_terrain_signed_step(C.byref(obj))
        check(row,bytes(uc.mem_read(base+4,8*v.CELLS)),bytes(obj)[4:4+8*v.CELLS],bytes(obj)[4+4*v.CELLS:4+8*v.CELLS]*2)
    row=family('signed_wave_009f8318')
    for k in range(12*scale):
        hx,hy=g.choice([0,1,32,64,100,127,128,150]),g.choice([0,1,64,127,150]); t=v.f32(g.uniform(-5000,50000))
        uc.mem_write(base,bytes(obj)); uc.mem_write(v.HERO_POINTER,struct.pack('<I',client.OBJECTS))
        uc.mem_write(client.OBJECTS+0x180,struct.pack('<2i',hx,hy)); client.write('time','f',[t])
        run(0x9f8318); lib.mu_terrain_signed_wave(C.byref(obj),hx,hy,t)
        check(row,bytes(uc.mem_read(base+0x80004,8*v.CELLS)),bytes(obj)[0x80004:0x100004],b'\0'*(8*v.CELLS))
    row=family('signed_height_009f9b67')
    # Store ST0 through a small authored call shim, preserve ret 8.
    shim=base+0x180000
    for k in range(500*scale):
        obj.active=k%2
        x,y=v.f32(g.uniform(0,12799)),v.f32(g.uniform(0,12799))
        i=int(v.fmul(v.fdiv(y,100.0),2))*256+int(v.fmul(v.fdiv(x,100.0),2))
        for layer in range(4):obj.grid[layer*v.CELLS+i]=g.randrange(-10000000,10000000)
        uc.mem_write(base,bytes(obj))
        # cdecl shim pushes floats, ecx is retained, original pops its args.
        code=b'\x68'+struct.pack('<f',y)+b'\x68'+struct.pack('<f',x)+b'\xb8'+struct.pack('<I',0x9f9b67)+b'\xff\xd0\xd9\x1d'+struct.pack('<I',shim+100)+b'\xc3'
        uc.mem_write(shim,code); uc.ctl_remove_cache(shim,shim+100); run(shim)
        expected=v.fbits(lib.mu_terrain_signed_height(C.byref(obj),x,y)); got=struct.unpack('<I',uc.mem_read(shim+100,4))[0]
        check(row,got,expected,v.fbits(float(obj.grid[obj.active*v.CELLS+i])))
        if got!=expected and 'input' not in row:row['input']=[x,y,i,obj.active,[obj.grid[z*v.CELLS+i] for z in range(4)]]
    row=family('signed_mesh_009f86d6')
    for k in range(12*scale):
        hx,hy=g.choice([0,1,32,64,120,127,150]),g.choice([0,1,32,64,127,150]); uc.mem_write(base,bytes(obj))
        run(0x9f86d6,[hx*2,hy*2],8); lib.mu_terrain_signed_mesh(C.byref(obj),hx,hy)
        got=bytes(uc.mem_read(base+0x100014,C.sizeof(Grid)-0x100014)); expected=bytes(obj)[0x100014:]
        check(row,got,expected,bytes(obj)[0x1052c4:])
    row=family('signed_draw_009f9644')
    for k in range(6*scale):
        obj.world=[0x18,0x1d,0x24][k%3]; hx,hy=32+k,64-k
        uc.mem_write(base,bytes(obj)); uc.mem_write(v.HERO_POINTER,struct.pack('<I',client.OBJECTS));uc.mem_write(client.OBJECTS+0x180,struct.pack('<2i',hx,hy))
        run(0x9f9644)
        lib.mu_terrain_signed_mesh(C.byref(obj),hx,hy); expected=[];sink=authored.recorder(expected)
        lib.mu_terrain_signed_draw(C.byref(obj),C.byref(sink))
        check(row,client.stream,expected,[r for r in expected if r[:2]!=('bind',0x7631)])
    out['substitutions']=['CRT random sequence and particle allocation', 'texture lookup and GL import recording',
                          'synthetic signed-grid record and hero state; no original files or process']
    return out


MUTANTS = [
    ('reflection_uv_016c977c','float m = 2.0f *','float m = 3.0f *'),
    ('overlay_face_016cf46c','pass ? 1.0f - 0.4f : 0.4f','pass ? 1.0f - 0.6f : 0.6f'),
    ('reflection_normals_016c936a','{{-1,-1,0.2f}','{{-1,-1,0.3f}'),
    ('reflection_grid_016c95f9','z-25000.0f','z-24900.0f'),
    ('camera_frustum_016d20d9','angle[2] = -camera_angle[2];','angle[2] = camera_angle[2];'),
    ('fog_alpha_0184b043_0184b0bb','out->alpha_reference=0.25f','out->alpha_reference=0.1f'),
    ('chaos_face_009dc0b1','s->random(s->effect_context) % 8','s->random(s->effect_context) % 7'),
    ('signed_init_009f953b','memset(g, 0, sizeof *g);','memset(g, 1, sizeof *g);'),
    ('signed_ripple_009f9952','*(float)amplitude),19)','*(float)amplitude),18)'),
    ('signed_step_009f85fc','sar32(v,4)','sar32(v,3)'),
    ('signed_wave_009f8318','time*0.005f','time*0.006f'),
    ('signed_height_009f9b67','return (b/2.0f+a)/4.0f','return (b/2.0f+a)/2.0f'),
    ('signed_mesh_009f86d6','int diag=((x&1)==(y&1))','int diag=((x&1)!=(y&1))'),
    ('signed_draw_009f9644','{l,l*2.5f,l*3.0f}','{l,l*2.5f,l*2.0f}'),
]

def mutations(output):
    source=(v.ROOT/'reconstructed/terrain/terrain.c').read_text()
    directory=Path(output).resolve().parent/'terrain-mutants';directory.mkdir(exist_ok=True)
    def one(entry):
        family,old,new=entry
        assert old in source,old
        with tempfile.TemporaryDirectory(prefix='mu-terrain-mutant-') as tmp:
            tmp=Path(tmp);c=tmp/'terrain.c';library=tmp/'terrain.dylib';c.write_text(source.replace(old,new))
            subprocess.run(['clang','-std=c11','-O2','-ffp-contract=off','-fPIC','-shared',
                '-I'+str(v.ROOT/'reconstructed/terrain'),str(c),str(v.ROOT/'reconstructed/record-math/record_math.c'),
                '-lm','-o',str(library)],check=True,capture_output=True)
            report=directory/(family+'.json')
            with (directory/(family+'.log')).open('w') as log:
                result=subprocess.run([sys.executable,__file__,'--library',str(library),'--output',str(report)],stdout=log,stderr=log)
            data=json.loads(report.read_text()) if report.exists() else {}
            row=data.get(family,{})
            caught=row.get('matches',0)<row.get('cases',0)
            print('compiled mutant',family,'caught' if caught else 'MISSED',flush=True)
            return {'family':family,'caught':caught,'mismatches':row.get('cases',0)-row.get('matches',0),'exit':result.returncode}
    with ThreadPoolExecutor(max_workers=3) as pool:return list(pool.map(one,MUTANTS))

def main():
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0]);ap.add_argument('--scale',type=int,default=1);ap.add_argument('--output',required=True);ap.add_argument('--library',default=str(v.ROOT/'reconstructed/terrain/libterrain.dylib'));ap.add_argument('--mutations',action='store_true')
    args=ap.parse_args()
    text=pins.TEXT.read();data=pins.DATA.read();flag=pins.FLAG.read()
    c=v.Client(text,data,flag);v.install_crt(c)
    authored=v.Authored(args.library)
    report=compare(c,authored.lib,args.scale)
    if args.mutations: report['compiled_mutations']=mutations(args.output)
    Path(args.output).write_text(json.dumps(report,indent=2,default=str));print(json.dumps(report,indent=2,default=str))
    return int(any(r['cases']!=r['matches'] for r in report.values() if isinstance(r,dict) and 'cases' in r) or any(not r['caught'] for r in report.get('compiled_mutations',[])))

if __name__=='__main__': sys.exit(main())
