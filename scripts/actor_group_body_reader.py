"""Original RenderObject reader for actor constructor appearance groups.

Uses the existing object-render machine boundaries. Animation and Transform
are recorded services; custom/registry/map handlers explicitly decline. This
checks selected body options, not native/original pixels or shadow parity.
"""
import random
import struct
import actor_machine as am
import validate_object_render as ob
import validate_renderchar as vr


def check(machine,row,world,alpha,frame):
    o=ob.body_light_object(random.Random(20261115))
    o[3]=0;o[0xd]=1;o[0xe]=1;o[0x3b]=1
    o[5:8]=bytes([1,1,1]);struct.pack_into('<HH',o,0x2a,0,0)
    ob.put_f(o,0x158,100,200,50);ob.put_f(o,0x164,0,0,0);ob.put_f(o,0x170,0,0,0);ob.put_f(o,0xec,.2,.2,.2)
    for off,value in ((0x5c,row['model']),(0x60,row['subtype']),(0x68,row['hidden_mesh']),
        (0x74,row['blend_mesh']),(0x80,0),(0x318,ob.BONES),(0x34c,0)):
        struct.pack_into('<I',o,off,value & 0xffffffff)
    for off,value in ((0xa0,vr.u2f(row['scale_bits'] or vr.f2u(.9))),(0xa8,vr.u2f(row['blend_light_bits'])),
        (0xac,0),(0xb0,0),(0xdc,alpha),(0xd0,frame),(0xd4,0),(0xe4,.8),(0xe8,.2)):
        ob.put_f(o,off,value)
    calls=[]
    def record(name,count,cleanup):
        return lambda m:(calls.append((name,[m.argument(i) for i in range(count)])) or 0,cleanup)
    stubs={0x00966cc4:lambda m:ob.FAKE,0x00eaa8cf:lambda m:(ob.MODEL,4),
        0x012b5064:record('pose',8,0x20),0x0129f11a:lambda m:ob.BONES,
        0x00966ea5:record('transform',9,0x24),0x017f9375:record('buff-tint-boundary',0,0),
        0x017f76ec:lambda m:0,0x00a170f2:lambda m:(m.argument(0),4),
        0x00a1711c:lambda m:(m.argument(0),8),0x01807a11:lambda m:(0,4),
        0x00a16bc0:lambda m:(ob.FAKE+0x10,4),ob.VSTUB_C:lambda m:(0,0),
        0x00966def:record('body',8,0x20),0x017f919e:record('after-visual-boundary',0,0),
        0x012bc07a:record('bounding',5,0x14),0x0184a990:lambda m:0,
        0x009a6ef3:lambda m:ob.FAKE,0x009a645f:lambda m:0,
        0x0103ec05:lambda m:0,0x016a88ae:lambda m:0,0x017f746f:record('extra',0,0)}
    grid=struct.pack('<f',.5)*(3*256*256)
    regions=ob.global_regions(world,6,[
        am.defined_region('frame-light',ob.FRAME_LIGHT,grid,writable=False),
        am.defined_region('primary-light',ob.PRIMARY_LIGHT,grid,writable=False),
        am.defined_region('terrain-ready',ob.TERRAIN_READY,b'\1',writable=False),
        am.defined_region('time',ob.TIME,struct.pack('<f',123456),writable=False),
        am.defined_region('bounds',ob.BOUNDS,bytes(4),writable=False),
        am.defined_region('hero-pointer',ob.HERO_PTR,struct.pack('<I',ob.HERO),writable=False),
        am.defined_region('hero',ob.HERO,bytes(0x3300),writable=False),
        am.undefined_region('bone-scale',0x01cf104c,4),
        am.defined_region('object',ob.OBJECTS,bytes(o)),
        am.defined_region('model',ob.MODEL,bytes(0x100)),
        am.defined_region('fake',ob.FAKE,bytes(ob.fake_object()),writable=False),
        am.undefined_region('gl-color',0x41030000,16)])
    run=ob.run(machine,ob.RENDER,[ob.OBJECTS,1,0,0,0xffffffff,0xffffffff],regions,stubs)
    body=[args for name,args in calls if name=='body']
    expected=[2,vr.f2u(alpha),row['blend_mesh'] & 0xffffffff,row['blend_light_bits'],0,0,row['hidden_mesh'] & 0xffffffff,0xffffffff]
    transforms=[args for name,args in calls if name=='transform']
    ok=run['ok'] and body==[expected] and len(transforms)==1 and transforms[0][4:]==[1,0,vr.f2u(.4),vr.f2u(.8),vr.f2u(.2)] and \
        not any(name in ('extra','bounding') for name,args in calls)
    return ok,dict(cl=row['class'],world=world,calls=calls,expected=expected,stop=None if run['ok'] else str(run)[:500])
