#!/usr/bin/env python3
"""SESSION-VIEWPORT-001: bounded 0x12 field/default instruction comparisons.

Runs original instruction ranges, never an independent Python decoder oracle.
The entry-to-return cases compare record fields with explicit engine/table
host answers. Effects, C++ string/guild services, pet eligibility, muun table
lookup and pose branches remain outside the equality claim.
"""
import argparse
import ctypes as C
import json
import random
import struct
import tempfile
import subprocess
from pathlib import Path
import validate_players as vp

class Viewport(C.Structure):
    _fields_ = [('size', C.c_int32), ('key', C.c_uint16), ('created', C.c_uint8),
                ('x', C.c_uint8), ('y', C.c_uint8), ('packet_class', C.c_uint8),
                ('equipment', C.c_uint8 * 18), ('name', C.c_char * 11), ('target', C.c_uint8 * 2),
                ('direction', C.c_uint8), ('pk', C.c_uint8), ('elemental', C.c_uint8),
                ('pet_code', C.c_uint16 * 3), ('pet_level', C.c_uint8 * 3), ('pet_index', C.c_uint8),
                ('helper', C.c_uint16), ('byte_32', C.c_uint8), ('server', C.c_uint16),
                ('flags', C.c_uint8), ('muun', C.c_uint8), ('muun_level', C.c_uint8),
                ('buff_count', C.c_uint8), ('buff_type', C.c_uint16 * 56),
                ('buff_value', C.c_uint32 * 56), ('pose_state', C.c_uint8)]

RANGES = [(0x122d486, 0x122d4b6), (0x122d660, 0x122d6a9),
          (0x122d8a1, 0x122d996), (0x122da8e, 0x122db06),
          (0x122e211, 0x122e22d), (0x137d8a1, 0x137db3e), (0x122dc47, 0x122dd87),
          (0x122d4b6, 0x122d4dc), (0x122d996, 0x122da8e),
          (0x122df8a, 0x122e018), (0x122e10e, 0x122e11c)]


def library(path):
    lib = vp.load_library(path)
    lib.mu_rp_viewport_record.argtypes = [C.c_char_p, C.c_int32, C.POINTER(Viewport)]
    lib.mu_rp_character_create.argtypes = [C.POINTER(vp.Character), C.c_int16, C.c_int32,
                                           C.c_uint8, C.c_uint8, C.c_float]
    lib.mu_rp_viewport_apply.argtypes = [C.POINTER(Viewport), C.POINTER(vp.Character),
                                        C.POINTER(vp.Env), C.POINTER(vp.Calls)]
    return lib


def compare(client, lib, n):
    m = client.m
    rng = random.Random(20261027)
    counts = dict(key=0, apply=0, stride=0, create=0, placement=0, record=0, bounds=0)
    for _ in range(n):
        b = bytearray(rng.randbytes(0x44 + 56 * 8))
        b[0x43] %= 57
        v = Viewport()
        assert lib.mu_rp_viewport_record(bytes(b), len(b), C.byref(v)) == 0x44 + 8 * b[0x43]
        for short in (0, 0x43, v.size - 1):
            assert lib.mu_rp_viewport_record(bytes(b), short, C.byref(Viewport())) == 0
            counts['bounds'] += 1
        client.reset()
        p = m.alloc(len(b), define=True)
        m.write(p, bytes(b))
        rec = m.alloc(0x3700, define=True)
        frame = m.alloc(0x400, define=True) + 0x200
        m.write(rec, bytes(0x3700))
        m.put32(frame - 0x14, p)
        m.put32(frame - 0x10, rec)
        m.put32(frame - 0x18, rec + 0x3254)
        m.put32(frame - 0x58, 5)
        m.uc.reg_write(vp.cm.UC_X86_REG_EBP, frame)
        m.uc.reg_write(vp.cm.UC_X86_REG_ESP, frame - 0x180)
        def run(start, end):
            # Explicit stop hook also handles a cached translation block whose
            # natural end lies beyond this range's exclusive boundary.
            hook=m.uc.hook_add(vp.cm.UC_HOOK_CODE,lambda uc,*a:uc.emu_stop(),begin=end,end=end)
            try:
                m.uc.emu_start(start, end, count=100000)
            finally:
                m.uc.hook_del(hook)
            assert not m.errors, m.errors
            assert m.uc.reg_read(vp.cm.UC_X86_REG_EIP)==end
        # Name, pet words/levels and buff records through original handler reads.
        observed=[]
        m.stub(0x194c200, lambda mm: (mm.write(mm.args(3)[0], mm.read(mm.args(3)[1], mm.args(3)[2])),mm.args(3)[0])[1],0)
        m.stub(0xcd4ea8,lambda mm:0,0)
        m.stub(0xcd5fac,lambda mm:1,8)
        m.stub(0x99536d,lambda mm:0,0)
        m.stub(0x9b46d4,lambda mm:0,4)
        def pet(mm):
            code,char,index,enabled=mm.args(4)
            observed.append(('pet',code,index,mm.read(frame-0x25,1)[0],enabled))
            return 0
        m.stub(0x9b9ab9,pet,16)
        m.stub(0x10de7a3,lambda mm:mm.args(1)[0]&1,4)
        m.stub(0x128723b,lambda mm:observed.append(('buff',mm.args(4)[0],mm.args(4)[3])),0)
        m.stub(0xd8b849,lambda mm:observed.append(('buff_owner',mm.args(2)[1])),0)
        run(*RANGES[7])
        assert m.read(frame-0xcc,11).split(b'\0')[0] == bytes(v.name).split(b'\0')[0]
        run(*RANGES[8])
        assert [x for x in observed if x[0]=='pet'] == [
            ('pet',v.pet_code[i],i,v.pet_level[i],0) for i in range(3) if v.pet_code[i]!=65535]
        run(*RANGES[9])
        assert [x for x in observed if x[0]=='buff'] == [
            ('buff',v.buff_type[i],v.buff_value[i] if v.buff_type[i]&1 else 0) for i in range(v.buff_count)]
        assert [x[1] for x in observed if x[0]=='buff_owner'] == list(v.buff_type[:v.buff_count])
        run(*RANGES[10])
        assert struct.unpack('<H',m.read(rec+0x42,2))[0] == v.server
        counts['record']+=1
        run(*RANGES[0])
        assert struct.unpack('<H',m.read(frame - 0x24,2))[0] == v.key
        assert m.u32(frame - 0x98) == v.created
        counts['key'] += 1
        run(*RANGES[1])
        run(*RANGES[2])
        # The mount and pet managers are explicit host answers; the character's
        # helper setter and ride-state decoder execute original code.
        run(*RANGES[3])
        c = vp.Character()
        env = vp.Env(); env.scene_state = 6
        path = vp.PATHFN(lambda *a: 1); env.path_finding2 = path
        calls = vp.Calls()
        lib.mu_rp_viewport_apply(C.byref(v), C.byref(c), C.byref(env), C.byref(calls))
        fields = [(0x12,'B',c.class_byte), (0x13,'B',c.byte_13), (0x1f,'B',c.pk),
                  (0x328f,'B',c.kind), (0x180,'i',c.tile[0]), (0x184,'i',c.tile[1]),
                  (0x2d,'B',c.target[0]), (0x2e,'B',c.target[1]), (0x33c0,'f',c.angle[2]),
                  (0x3268,'i',c.elemental), (0x327c,'B',c.byte_327c), (0x190,'B',c.stunned),
                  (0x3230,'i',c.field_3230), (0x3234,'B',c.transformed),
                  (0x3244,'i',c.pet_index), (0x322e,'H',c.helper), (0x322c,'B',c.ride_state)]
        for off, fmt, value in fields:
            actual = bytes(m.uc.mem_read(rec + off, struct.calcsize('<'+fmt)))
            assert actual == struct.pack('<'+fmt,value), (hex(off), actual.hex(),value)
        assert m.u32(frame - 0x50) == v.pose_state
        counts['apply'] += 1
        run(*RANGES[4])
        assert m.u32(frame - 0x58) == 5 + v.size
        counts['stride'] += 1
        # Walk-in placement uses 2 then fallback 4 even in a mode-4 world.
        m.write(rec, bytes(0x3700))
        m.put32(rec+0x180,v.x); m.put32(rec+0x184,v.y)
        m.write(rec+0x2d,bytes(v.target))
        m.put32(vp.WORLD,0x52)
        client.path_answers=[0,0]
        run(*RANGES[6])
        v.created=0; env.world=0x52; env.path_finding2=vp.PATHFN()
        c=vp.Character()
        lib.mu_rp_viewport_apply(C.byref(v),C.byref(c),C.byref(env),C.byref(calls))
        assert [(x[1],x[2],x[3],x[4],x[5]) for x in client.records if x[0]=='path'] == [
            (v.x,v.y,v.target[0],v.target[1],2),(v.x,v.y,v.target[0],v.target[1],4)]
        assert [x.c for x in calls.list[:calls.count] if x.kind==14][-2:] == [2,4]
        for off,fmt,value in [(0x180,'i',c.tile[0]),(0x184,'i',c.tile[1]),
                              (0x33ac,'f',c.position[0]),(0x33b0,'f',c.position[1])]:
            assert m.read(rec+off,struct.calcsize('<'+fmt)) == struct.pack('<'+fmt,value),hex(off)
        counts['placement']+=1
        # Execute the character-create prefix, with synthetic host services.
        m.write(rec, bytes(0x3700))
        x,y = rng.randrange(256), rng.randrange(256)
        sp = frame - 0x180
        m.write(sp, struct.pack('<6I', vp.cm.RETURN_SENTINEL, rec, 0xa91, x, y, 0))
        m.uc.reg_write(vp.cm.UC_X86_REG_ESP, sp)
        run(*RANGES[5])
        c = vp.Character()
        lib.mu_rp_character_create(C.byref(c), 12, 0xa91, x, y, 0)
        for off,fmt,value in [(0x180,'i',c.tile[0]),(0x184,'i',c.tile[1]),(0x2d,'B',c.target[0]),
                              (0x2e,'B',c.target[1]),(0x23,'B',c.dead),(0x38,'B',c.movement),
                              (0x3c,'h',c.guild),(0x1f,'B',c.pk),(0x32b0,'i',c.model),
                              (0x17,'B',c.guild_bytes[0]),(0x1a,'B',c.guild_bytes[3])]:
            assert bytes(m.uc.mem_read(rec+off,struct.calcsize('<'+fmt))) == struct.pack('<'+fmt,value), hex(off)
        counts['create'] += 1
    return counts


def handler_cases(text,data,lib,n):
    cl=vp.Client(text,data);m=cl.m
    m.allow((0x122d413,0x122e25c),(0x129dc78,vp.extent(text,0x129dc78)))
    addresses=[0x9c2aea,0x9ba774,0x185c95d,0x137aafe,0xc92a29,0xc92bea,0x13c0eaa,0x153b02c,0x94997e,0x129de8d,0x94f183,0x129d1e5,0xd8b3e3,0x9dacb8,0x9a16a6,0x95f75d,0x1072152,0x1072ba0,0x95248d,0x9a1760,0x15338e3,0x952714]
    for a in addresses:
     try: m.stub(a,lambda m:0,cl.cleanup(a))
     except Exception: raise
    m.stub(0x95f75d,lambda m:cl.hero_state,0)
    m.stub(0x1177e1c,lambda m:0xffffffff,4)
    m.stub(0x129d1e5,lambda m:(m.write(cl.ecx(),b'\xff\xff\0\0\0'),0)[1],0)
    m.stub(0x194c200,lambda m:(m.write(m.args(3)[0],m.read(m.args(3)[1],m.args(3)[2])),m.args(3)[0])[1],0)
    m.stub(0x7f0f0000,lambda m:123,0)
    # Explicit CreateCharacter host. Its reconstructed defaults are independently
    # compared with the original create prefix by the other family.
    def create(m):
     key,model,x,y,angle=m.args(5)
     c=vp.Character();lib.mu_rp_character_create(C.byref(c),key,model,x,y,vp.cm.bits_f(angle))
     addr=m.alloc(0x3700,define=True);m.write(addr,bytes(0x3700))
     # reconstruct defaults used by this bounded Player-model route
     for off,fmt,val in [(0x3e,'h',c.key),(0x180,'i',c.tile[0]),(0x184,'i',c.tile[1]),(0x3c,'h',c.guild),(0x1f,'B',c.pk),(0x146,'h',c.class_word),(0x14c,'H',c.move_speed),(0x3254,'B',1),(0x328f,'B',1),(0x32b0,'i',model),(0x327e,'H',c.action),(0x3280,'H',c.prior_action),(0x33ac,'f',c.position[0]),(0x33b0,'f',c.position[1])]:m.write(addr+off,struct.pack('<'+fmt,val))
     for i in range(11):m.write(addr+0x1c4+i*0x3fc,b'\xff\xff\0\0\0')
     m.write(addr+0x17,bytes(c.guild_bytes));cl.char=addr;cl.key_index[key]=0;cl.index_char[0]=addr
     return addr
    m.stub(0x137f6c2,create,0)
    for i in range(n):
     cl.reset();m.put32(0x1a7c49c,0x7f0f0000)
     b=bytearray(random.Random(i).randbytes(0x44));b[0]=(b[0]&0x7f)|(0x80 if i%2 else 0)
     b[4]=random.Random(i+1).randrange(256);b[5:0x17]=vp.random_equipment(random.Random(i+2))
     b[0x15]&=0x1f;b[0x41]=0xff;b[0x43]=0
     b[0x18:0x22]=b'Synthetic\0';b[0x26:0x2f]=b'\xff\xff\0'*3
     cl.path_answers=[0,0]
     a=m.alloc(5+len(b),define=True);m.write(a,bytes([0xc2,0,5+len(b),0x12,1])+b)
     m.call(0x122d413,[a])
     v=Viewport();lib.mu_rp_viewport_record(bytes(b),len(b),C.byref(v))
     c=vp.Character();lib.mu_rp_character_create(C.byref(c),v.key,0xa91,v.x,v.y,0)
     calls=vp.Calls();env=vp.Env();env.scene_state=6
     lib.mu_rp_viewport_apply(C.byref(v),C.byref(c),C.byref(env),C.byref(calls))
     actual=vp.read_fields(m,cl.char);expected=vp.lib_fields(c)
     for k in expected:
      assert actual[k]==expected[k],(i,k,actual[k],expected[k])
     return_value = i+1

    return return_value

def main():
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--text',default=str(vp.DEFAULT_TEXT))
    ap.add_argument('--data',default=str(vp.DEFAULT_DATA))
    ap.add_argument('--cases',type=int,default=1000)
    ap.add_argument('--mutations',action='store_true')
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    text,data=vp.pins.TEXT.read(args.text),vp.pins.DATA.read(args.data)
    client=vp.Client(text,data); m=client.m
    for a,b in RANGES: m.allow((a,b))
    m.allow((0x129dc78,vp.extent(text,0x129dc78)))
    # All replaced calls are host services outside the compared field/default ranges.
    for addr,cleanup in [(0x9c2aea,0),(0x9ba774,0),(0xa0b72b,0),(0xc9321b,0),
                         (0x16d34db,0),(0x129de3a,4),(0x129dc61,4),
                         (0x129f484,0),(0xaa0fdd,4)]:
        m.stub(addr,lambda m:0,cleanup)
    # Terrain attribute lookup is supplied a defined synthetic zero tile.
    original_reset=client.reset
    def reset():
        original_reset(); m.write(0xb795420,b'\0\0')
    client.reset=reset
    result={'text_sha256':vp.TEXT_SHA256,'data_sha256':vp.DATA_SHA256,
            'scope':'handler entry-to-return record fields, bounded field blocks and create prefix; engine/table services stubbed',
            'ranges':[[hex(a),hex(b)] for a,b in RANGES],
            'cases':compare(client,library(vp.LIB),args.cases),'mismatches':0,
            'handler_cases':handler_cases(text,data,library(vp.LIB),args.cases)}
    if args.mutations:
        source=(vp.ROOT/'reconstructed/players/remote_players.c').read_text()
        plants=[('key_mask','key & 0x7fff','key & 0x3fff'),
                ('record_stride','8 * v->buff_count','4 * v->buff_count'),
                ('target','c->target[0] = v->target[0]','c->target[0] = v->target[1]'),
                ('flags','(v->flags >> 1) & 0x3f','(v->flags >> 2) & 0x3f'),
                ('guild_default','c->guild = -1','c->guild = 0'),
                ('angle','* 45.0f','* 46.0f'),
                ('name_offset','p + 0x18, 10','p + 0x19, 10'),
                ('buff_value','p[0x48 + 8 * i]','p[0x47 + 8 * i]')]
        caught=[]
        with tempfile.TemporaryDirectory() as tmp:
            for name,old,new in plants:
                assert old in source,old
                src=Path(tmp)/'remote_players.c'; dst=Path(tmp)/(name+'.'+vp.SUFFIX)
                src.write_text(source.replace(old,new))
                subprocess.run(['cc','-shared','-fPIC','-O2','-I',str(vp.ROOT/'reconstructed/players'),str(src),'-o',str(dst)],check=True)
                try: compare(client,library(dst),60)
                except AssertionError: caught.append(name)
        result['mutants']={'planted':len(plants),'caught':len(caught),'names':caught}
        assert len(caught)==len(plants),result
    if args.output: args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__': main()
