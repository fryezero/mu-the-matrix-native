"""Populate authored tracks for the rank-5 item's real pose caller.

This oracle advances beyond the old absent-action stop. It compares the pose
builder at its actual caller boundary, not the unresolved named-mesh draw rules.
No pose or geometry instruction is stubbed. The heap reserves the seeded tracks.
"""
import ctypes as C
from pathlib import Path
import random
import struct
import validate_pose_builder as pose
import validate_renderchar as v

ROOT = Path(__file__).resolve().parents[1]
TYPES = (*range(0x1c24,0x1c35),0x1c44,0x1c7a)
LIBRARY = ROOT/'reconstructed/model-codec/libposebuilder.dylib'


def seed():
    bones = [dict(dummy=0, name=b'root' if i==0 else b'child', parent=i-1,
                  tracks=[([(float(i+k+a),float(i*2+k),float(k*3-a)) for k in range(3)],
                            [(0.,0.,float(k+a)*0.2) for k in range(3)]) for a in range(2)]) for i in range(2)]
    case=pose.tracks.build_case('rank-5-item',[3,3],bones)
    authored=pose.Authored(LIBRARY)
    return pose.seed_authored(authored,case)['window']


def compare_pose(machine, library, model, arguments, expected=None):
    """Snapshot declared regions for production C; compare bone output exactly."""
    P=pose.Authored
    spans=((model,0xd0),(pose.WINDOW,0x10000),(0x06fce398,96),
           (pose.QUATERNIONS,32),(pose.ROOT_MATRIX,48),(v.OBJ,0x400))
    buffers=[(C.c_ubyte*n).from_buffer_copy(machine.read(base,n)) for base,n in spans]
    images=(P.Image*len(spans))(*[P.Image(C.addressof(buf),base,n) for (base,n),buf in zip(spans,buffers)])
    args=P.Arguments(*arguments)
    fn=library.mu_pose_build
    fn.argtypes=[C.POINTER(P.Memory),C.c_uint32,C.POINTER(P.Arguments),C.POINTER(P.Globals)]
    status=fn(C.byref(P.Memory(images,len(spans))),model,C.byref(args),C.byref(P.Globals(pose.QUATERNIONS,pose.ROOT_MATRIX)))
    if status:raise AssertionError(('authored rank-5 pose',status))
    return bytes(buffers[2]) if expected is None else bytes(buffers[2])==expected


def cases(wa):
    from unicorn import UC_HOOK_CODE
    payload=seed()
    lib=C.CDLL(str(LIBRARY))
    particles=C.CDLL(str(ROOT/'reconstructed/particles/libclient_particles.dylib'))
    particles.mu_pt_transform_position.argtypes=[C.POINTER(C.c_float)]*3+[C.c_int,C.c_float,C.POINTER(C.c_float)]
    vectors=[]
    for t in TYPES:
        for index in range(32):
            rng=random.Random(t*100+index)
            observation={}
            class World(v.World):
                def __init__(self,*args):
                    super().__init__(*args)
                    m=self.m
                    m.write(pose.WINDOW,payload)
                    # The CRT allocator starts at the same synthetic base. Reserve
                    # the track arrays rather than allowing STL temporaries to alias them.
                    m.heap=pose.WINDOW+0x100000
                    m.ensure(pose.ROOT_MATRIX,48)
                    root=(1,0,0,rng.uniform(-30,30),0,1,0,rng.uniform(-30,30),0,0,1,rng.uniform(-30,30))
                    m.write(pose.ROOT_MATRIX,struct.pack('<12f',*root))
                    m.ensure(0x06fce398,0x1000)
                    m.ensure(pose.QUATERNIONS,32)
                    def before(uc,address,size,context):
                        arguments=[m.arg(i) for i in range(8)]
                        if arguments[0]!=0x06fce398 or arguments[4:6]!=[v.OBJ+0x164,v.OBJ+0x170] or arguments[6:]!=[1,1]:
                            raise AssertionError(('rank-5 pose ABI',arguments))
                        observation['c']=compare_pose(m,lib,v.MODEL,arguments)
                        observation['snapshot']=(m.read(v.MODEL,0xd0),m.read(pose.WINDOW,0x10000),
                            m.read(0x06fce398,96),m.read(pose.QUATERNIONS,32),m.read(pose.ROOT_MATRIX,48),
                            m.read(v.OBJ,0x400),arguments)
                    def after(uc,address,size,context):
                        observation['original']=m.read(0x06fce398,96)
                    m.uc.hook_add(UC_HOOK_CODE,before,begin=0x012b5064,end=0x012b5064)
                    m.uc.hook_add(UC_HOOK_CODE,after,begin=0x01747a0a,end=0x01747a0a)
                def add_model(self,*args,**kwargs):
                    super().add_model(*args,**kwargs)
                    m=self.m
                    m.write(v.MODEL+0x22,struct.pack('<hhh',2,6,2))
                    m.write(v.MODEL+0x2c,payload[0x2c:0x34])
                    m.w32(v.MODEL+0x60,0xffffffff)
                    m.write(v.MODEL+0xa8,struct.pack('<H',index%3))
                    m.write(v.OBJ+0x2c,struct.pack('<H',(index//3)%3))
                    m.write(v.OBJ+0xd0,struct.pack('<2f',(-1.,0.,0.5,1.25,2.75,4.)[index%6],(index%5)*0.5))
                    m.write(v.OBJ+0x164,struct.pack('<5f',0,0,0,0,0))
                    m.w32(v.MODEL+0x74,v.f2u(0.5+(index%4)*0.5))
            case=v.classify_case(t,v.CLASSIFY[index%len(v.CLASSIFY)])
            result,stream,other,m=v.client_stream(wa,case,World)
            if not result['ok'] or other or observation.get('original')!=observation.get('c') or 'original' not in observation:
                raise AssertionError(('rank-5 pose',hex(t),index,result,other,observation.keys()))
            # Real TransformPosition on two authored nonzero vertices. This
            # checks point geometry after the pose, not named-mesh dispatch/GL.
            for bone in range(2):
                point=v.F3(2.5,-4.0,float(index%7))
                m.write(v.LIGHT+0x80,bytes(point))
                expected=v.F3()
                matrix=(C.c_float*12).from_buffer_copy(observation['c'][48*bone:48*(bone+1)])
                scale=v.u2f(m.r32(v.MODEL+0x74))
                origin=v.F3.from_buffer_copy(m.read(v.MODEL+0x78,12))
                particles.mu_pt_transform_position(matrix,point,expected,1,scale,origin)
                result=m.run(0x012b6ef1,[0x06fce398+48*bone,v.LIGHT+0x80,v.LIGHT+0xc0,1],v.MODEL)
                import renderchar_machine as machine
                checks=dict(result['checks'])
                checks['esp']=m.uc.reg_read(m.x86.UC_X86_REG_ESP)==machine.ENTRY_ESP+20
                if result['error'] or result['stopped'] or not all(checks.values()) or m.read(v.LIGHT+0xc0,12)!=bytes(expected):
                    raise AssertionError(('rank-5 posed point',hex(t),index,bone,result))
            vectors.append((observation['snapshot'],observation['original']))
    return {'cases':len(vectors),'mismatches':0,'types':len(TYPES),'posed_point_cases':len(vectors)*2,
            'boundary':'real pose caller only; mesh streams compared separately by validate_item_next'},vectors
