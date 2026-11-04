#!/usr/bin/env python3
"""AUDIO-002B: compiled native adapters against original NPC voice/talk calls.

Voice fragments exclude motion/effects. Object families execute the four
recovered sound-producing handlers on finite geometry, with surrounding model
services outside the comparison. Ambient mapping is static; its decision gates
remain covered by validate_environment unchanged. ReceiveTalk executes its full body with the
existing NPC machine's explicit GFx/packet/cursor hosts. Record original return
addresses as source sites. Only authored C and synthetic state enter the adapter.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import re
import struct
import subprocess
import tempfile
import pins
from validate_audio import Machine, STACK, STACK_SIZE, ARENA
from validate_npc import TalkMachine, talk_cases, cm

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = r'''
#include <string.h>
#include "core/mu_session_audio.h"
#include "core/mu_world_audio.h"
#include "../reconstructed/npc/npc_talk.h"
#include "../reconstructed/objects/object_render.h"
typedef struct decision { uint32_t routine, site; int32_t id, key, loop, missing; } decision;
static decision rows[32]; static int count;
void mu_session_sound_emit(mu_session *s, uint32_t routine, uint32_t site, int32_t id, int16_t key, int loop)
{ (void)s; rows[count++] = (decision){routine,site,id,key,loop,0}; }
void mu_session_sound_missing(mu_session *s, uint32_t routine, uint32_t site, uint32_t input)
{ (void)s; rows[count++] = (decision){routine,site,(int32_t)input,-2,0,1}; }
int voice(int32_t model, int32_t r, uint16_t action, float frame, int buff, decision *out)
{
    count=0; mu_session_npc_voice(NULL,model,r,action,frame,buff);
    for (int i=0;i<count;++i) out[i]=rows[i]; return count;
}
int talk(const mu_talk_input *in, decision *out)
{
    count=0; mu_talk_output events; mu_npc_talk_result(in,&events);
    for (int i=0;i<events.count;++i)
        if (events.events[i].callee==MU_TALK_SND_PLAY)
            mu_session_npc_talk_sound(NULL,(int32_t)events.events[i].args[0]);
    for (int i=0;i<count;++i) out[i]=rows[i]; return count;
}
int walk(const mu_walk_sound_state *state, const uint16_t *attributes, decision *out)
{
    count=0; mu_walk_sound_decision d=mu_walk_sound_select(state,attributes);
    if (d.id>=0) mu_session_sound_emit(NULL,0x013b1f61u,d.site,d.id,-2,0);
    for (int i=0;i<count;++i) out[i]=rows[i]; return count;
}
int objects(const uint8_t *original, const mu_obj_move_inputs *in, decision *out)
{
    uint8_t object[MU_OBJ_SIZE]; memcpy(object, original, sizeof object);
    mu_obj_event events[64]; mu_obj_log log={0,64,0,events};
    mu_obj_move(object,0,in,&log);
    count=0;
    for (int i=0;i<log.count;++i)
        if (events[i].call==MU_OBJ_CALL_SOUND) mu_session_object_sound(NULL,(int32_t)events[i].args[0]);
    for (int i=0;i<count;++i) out[i]=rows[i]; return count;
}
int ambient(int id, decision *out)
{
    count=0; mu_session_ambient_sound(NULL,id);
    for (int i=0;i<count;++i) out[i]=rows[i]; return count;
}
'''

class Decision(C.Structure):
    _fields_ = [('routine',C.c_uint32),('site',C.c_uint32),('id',C.c_int32),
                ('key',C.c_int32),('loop',C.c_int32),('missing',C.c_int32)]


def tuples(rows, count):
    return [tuple(getattr(rows[i], n) for n, _ in Decision._fields_) for i in range(count)]


def object_sources():
    """reconstructed/objects/Makefile's SOURCES (with its $(wildcard ...) expanded), as paths."""
    folder = ROOT/'reconstructed/objects'
    text = (folder/'Makefile').read_text()
    line = next(l for l in text.splitlines() if l.startswith('SOURCES :='))
    out = []
    for word in re.sub(r'\$\(wildcard ([^)]*)\)', lambda m: ' '.join(
            sorted(p.name for p in folder.glob(m.group(1)))), line.split(':=', 1)[1]).split():
        out.append((folder/word).resolve())
    return out


def build(tmp, name, header=None, world=None, talk=None, hero=None, objects=None):
    # Header mutations compile the actual production inline adapters in a mirror
    # include tree. Symlinks reference authored headers only, never private inputs.
    folder = tmp/name
    (folder/'core').mkdir(parents=True)
    (folder/'core/mu_session_audio.h').write_text(header or (ROOT/'native/core/mu_session_audio.h').read_text())
    for source in (ROOT/'native/core').glob('*.h'):
        if source.name != 'mu_session_audio.h': (folder/'core'/source.name).symlink_to(source)
    for source in (ROOT/'native').iterdir():
        if source.is_dir() and source.name != 'core': (folder/source.name).symlink_to(source)
    (tmp/'reconstructed').symlink_to(ROOT/'reconstructed') if not (tmp/'reconstructed').exists() else None
    (folder/'wrapper.c').write_text(WRAPPER)
    world_src = folder/'audio_world.c'
    world_src.write_text(world or (ROOT/'reconstructed/audio/audio_world.c').read_text())
    talk_src = folder/'npc_talk.c'
    talk_src.write_text(talk or (ROOT/'reconstructed/npc/npc_talk.c').read_text())
    hero_src = folder/'hero_sound.c'
    hero_src.write_text(hero or (ROOT/'reconstructed/audio/hero_sound.c').read_text())
    object_src = folder/'object_render.c'
    object_src.write_text(objects or (ROOT/'reconstructed/objects/object_render.c').read_text())
    # Compile the deciding production routine, with its authored dependencies: the objects library's own
    # SOURCES, so world methods merged later link here too (INTEGRATION-GREEN-002).
    object_deps = [d for d in object_sources() if d.name != 'object_render.c']
    out = folder/'adapter.dylib'
    subprocess.run(['clang','-std=c11','-O2','-shared','-ffp-contract=off','-I',str(folder),
                    '-I',str(ROOT/'native/core'),'-I',str(ROOT/'reconstructed/audio'),
                    '-I',str(ROOT/'reconstructed/npc'),str(folder/'wrapper.c'),str(world_src),str(talk_src),str(hero_src),
                    str(object_src), *map(str,object_deps), '-I',str(ROOT/'reconstructed/objects'),
                    '-I',str(ROOT/'native/build/gen'),'-I',str(ROOT/'native/session'),'-o',str(out)], check=True)
    lib=C.CDLL(str(out))
    lib.voice.argtypes=[C.c_int32,C.c_int32,C.c_uint16,C.c_float,C.c_int,C.POINTER(Decision)]
    from validate_npc import TalkInput
    lib.talk.argtypes=[C.POINTER(TalkInput),C.POINTER(Decision)]
    from validate_hero_sound import WalkSoundState
    lib.walk.argtypes=[C.POINTER(WalkSoundState),C.c_void_p,C.POINTER(Decision)]
    lib.ambient.argtypes=[C.c_int32,C.POINTER(Decision)]
    from validate_object_render import MoveInputs
    lib.objects.argtypes=[C.c_void_p,C.POINTER(MoveInputs),C.POINTER(Decision)]
    return lib


class TalkSites(TalkMachine):
    def _rec(self, callee, words):
        base=super()._rec(callee,words)
        def record(m):
            if callee==0xa6ac96:
                ret=struct.unpack('<I',m.read(m.uc.reg_read(cm.UC_X86_REG_ESP),4))[0]
                self.sounds.append((0x1280659,ret-5,m.args(3)[0],-2,m.args(3)[2],0))
            return base(m)
        return record


def voice_corpus(text, data):
    m=Machine(text,data)
    m.hook(0x1989721,lambda m:(random_value,0))
    m.hook(0x1295ade,lambda m:(buff,4))
    def sound(m):
        sounds.append((0x13b23f8,m.read32(m.reg('esp'))-5,m.arg(0),-2,m.arg(2),0))
        assert m.arg(1)==0
        return 1,0
    m.hook(0xa6ac96,sound)
    ebp=STACK+STACK_SIZE-0x8000
    corpus=[]
    for model,start,end in [(0xa0b,0x13b53e4,0x13b540a),(0xa06,0x13b540f,0x13b5437),(0xa01,0x13b543c,0x13b549c)]:
        values=[-2**31,-1024,-257,-256,-64,-1,0,1,63,64,255,256,2**31-1]+list(range(1024))
        inputs=[(r,0,0.,0) for r in values] if model!=0xa01 else [(0,act,f,b) for act in [0,1,65535] for f in [float('nan'),-float('inf'),0.,4.9999995,5.,7.,10.,10.000001,float('inf')] for b in [0,1,2,255]]
        for random_value,action,frame,buff in inputs:
            sounds=[]
            m.write32(ebp+12,ARENA)
            m.write(ARENA+0x2a,struct.pack('<H',action));m.write(ARENA+0xd0,struct.pack('<f',frame))
            m.run(start,end,ebp=ebp,esp=ebp-0x1000,stops=(0x13b8058,))
            assert m.reg('eip') in (end,0x13b8058)
            corpus.append(((model,random_value,action,frame,buff),sounds))
    return corpus


def talk_corpus(text,data):
    from validate_npc import TalkInput
    m=TalkSites(text,data)
    cases=talk_cases(random.Random(2002),8)
    # Every result also receives an explicit plaintext refusal, independent of
    # the older family's sparse encrypted=False samples.
    cases += [dict(c,encrypted=0) for c in cases[::8]]
    corpus=[]
    for c in cases:
        m.sounds=[];m.run(c)
        buf=(C.c_uint8*16)(*c['packet']);has=c['has']
        inp=TalkInput(buf,16,c['encrypted'],c['entrance_visible'],has.get(0xb0,1),has.get(0xb4,1),
                      has.get(0xac,1),c['hero_x'],c['hero_y'],c['cursor_lock'],c['mouse_x'],c['mouse_y'],c['screen_w'],c['screen_h'])
        corpus.append(((inp,buf),m.sounds[:]))
    return corpus


def walk_corpus(text,data):
    import validate_hero_sound as h
    machine=h.am.ActorMachine(text,data)
    grids=[bytes(0x20000),struct.pack('<H',0x8000)*0x10000]
    cases=h.walk_sound_cases(random.Random(2002),600,grids)
    for world,tile,safe,attributes in [(2,0,0,grids[0]),(0,0,0,grids[0]),(3,0,0,grids[0]),
        (7,0,0,grids[0]),(57,0,0,grids[0]),(121,0,0,grids[0]),(62,0,0,grids[0]),
        (122,0,0,grids[1]),(122,0,0,grids[0]),(1,0,0,grids[0])]:
        cases.append(dict(world=world,tile=tile,safe=safe,attributes=attributes,action=0x32,x=1,y=1,manager=0))
    corpus=[];seen=set()
    for case in cases:
        sounds=[];stubs=h.walk_sound_stubs(case,[])
        def sound(m):
            site=m.read32(m.uc.reg_read(m.x86.UC_X86_REG_ESP))-5
            assert m.argument(1)==0
            seen.add(site)
            sounds.append((0x13b1f61,site,m.argument(0),-2,m.argument(2),0))
            return 0
        stubs[h.SND_PLAY]=sound
        result=machine.execute(h.PLAY_WALK_SOUND,[],[*h.walk_sound_regions(case),h.hero_regions(case)],stubs)
        assert result['ok'],result
        state=h.WalkSoundState(case['world'],case['tile'],case['action'],case['safe'],case['x'],case['y'],case['manager'])
        grid=C.create_string_buffer(case['attributes'])
        corpus.append(((state,grid),sounds))
    assert len(seen)==10,seen
    return corpus


def object_corpus(text, data):
    import validate_object_render as o
    m=o.Machine(text,data)
    g=random.Random(2002)
    corpus=[]; seen=set()
    worlds={0x21:(0xd6202f,[0,0x1e,0x47]),0x36:(0xd6202f,[0,0x1e,0x47]),
            0x25:(0xe74ae0,[0,0x2e,0x4d,0x5c,0x62,0x61]),
            0x28:(0xe74ae0,[0,0x2e,0x4d,0x5c,0x62,0x61]),
            0x50:(0xe13a9e,[0,0x71,0x87]),0x51:(0xe13a9e,[0,0x71,0x87]),
            0x8d:(0xe4c95e,[0,6,0xb7,0xc8])}
    for world,(routine,types) in worlds.items():
        for typ in types:
            for scale in [0.5,1.,2.]:
                limit=1300.*scale if typ==6 else 450. if typ==0xb7 else 800.
                for distance in [0.,limit-0.001,limit,limit+0.001,2000.]:
                    obj=bytearray(o.OBJ_SIZE)
                    o.put_i(obj,0x5c,typ);o.put_f(obj,0xd8,1.,1.,0.1)
                    o.put_f(obj,0xa0,scale);o.put_f(obj,0xbc,0.2)
                    o.put_f(obj,0x158,10000.,10000.,0.)
                    o.put_f(obj,0xb4,g.choice([4.9999,5.,10.]))
                    hero=(o.f32(10000.+distance),10000.,0.)
                    time=o.f32(g.uniform(0,100000));seed=g.getrandbits(32)
                    rnd=o.MsvcRand(seed);sounds=[]
                    def sound(m):
                        site=m.read32(m.uc.reg_read(m.x86.UC_X86_REG_ESP))-5
                        seen.add(site)
                        assert m.argument(1)==0
                        sounds.append((routine,site,m.argument(0),-2,m.argument(2),0))
                        return 0
                    stubs={0xa6ac96:sound,0x1989721:lambda m:rnd(),
                           0x16cacfc:lambda m:0,0x168fafd:lambda m:0}
                    regions=o.global_regions(world,6,[
                        o.am.defined_region('object',o.OBJECTS,bytes(obj)),
                        o.am.defined_region('time',o.TIME,o.pack_f(time),writable=False),
                        o.am.defined_region('hero-pointer',o.HERO_PTR,struct.pack('<I',o.HERO),writable=False),
                        o.am.defined_region('hero',o.HERO+0x33ac,o.pack_f(*hero),writable=False)])
                    result=o.run(m,routine,[o.OBJECTS],regions,stubs,
                                 ecx=o.FAKE if world in (0x50,0x51,0x8d) else 0,
                                 cleanup=4 if world in (0x50,0x51,0x8d) else 0)
                    assert result['ok'],(hex(routine),typ,result.get('stopped'))
                    corpus.append(((bytes(obj),world,hero,time,seed),sounds))
    assert len(seen)==10,seen
    return corpus


def check(lib, family, corpus):
    rows=(Decision*32)()
    for inputs,want in corpus:
        if family=='voice': count=lib.voice(*inputs,rows)
        elif family=='talk': count=lib.talk(C.byref(inputs[0]),rows)
        elif family=='walk': count=lib.walk(C.byref(inputs[0]),inputs[1],rows)
        elif family=='objects':
            import validate_object_render as o
            obj,world,hero,time,seed=inputs
            rnd=o.MsvcRand(seed)
            rand_fn=o.RAND_FN(lambda c:rnd())
            speed_fn=o.SPEED_FN(lambda c,t,a:0.2)
            state=o.MoveInputs(world,6,0,time,(C.c_float*3)(*hero),1,1,speed_fn,rand_fn,None)
            count=lib.objects(C.create_string_buffer(obj),C.byref(state),rows)
        else: count=lib.ambient(inputs,rows)
        if tuples(rows,count)!=want: return inputs,want,tuples(rows,count)
    return None


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mutations',action='store_true');p.add_argument('--report')
    a=p.parse_args();text,data=pins.TEXT.read(),pins.DATA.read()
    corpora={'voice':voice_corpus(text,data),'talk':talk_corpus(text,data),'walk':walk_corpus(text,data),'objects':object_corpus(text,data)}
    # Original SND_Play instructions and literal ids, independent of the mapper.
    # Environmental decision gates are compared by validate_environment unchanged.
    sites=[(12,0xc9fcd5,0xc9eb04),(13,0xc9fcfb,0xc9eb04),(14,0xc9fd2f,0xc9eb04),
           (138,0xc9fd74,0xc9eb04),(15,0xca1c80,0xca05b3)]
    for id,site,routine in sites:
        push = bytes((0x6a,id)) if id < 128 else b'\x68'+struct.pack('<I',id)
        assert text[site-0x401000-len(push):site-0x401000]==push
        assert text[site-0x401000]==0xe8
        assert site+5+struct.unpack_from('<i',text,site-0x401000+1)[0]==0xa6ac96
    corpora['ambient']=[(id,[(routine,site,id,-3,0,0)]) for id,site,routine in sites]
    corpora['ambient'] += [(id,[]) for id in [-1,0,25,28,160,161,9999]]
    report={'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,
            'families':{},'mismatches':0,'mutants':{}}
    with tempfile.TemporaryDirectory(prefix='audio-callers-') as tmp:
        tmp=Path(tmp);lib=build(tmp,'plain')
        for name,corpus in corpora.items():
            error=check(lib,name,corpus);assert error is None,(name,error)
            report['families'][name]={'cases':len(corpus),'mismatches':0}
        if a.mutations:
            header=(ROOT/'native/core/mu_session_audio.h').read_text()
            variants={
                'voice-route':('voice','model == 0xa0b ? 0x013b5402u','model == 0xa06 ? 0x013b5402u'),
                'voice-site':('voice','0x013b5494u','0x013b5495u'),
                'talk-id':('talk','site, id, -2, 0','site, id + 1, -2, 0'),
                'talk-order':('talk','id == 25 ? 0x012811cau : id == 28 ? 0x012811d8u','id == 28 ? 0x012811cau : id == 25 ? 0x012811d8u'),
                'ambient-site':('ambient','0x00ca1c80u','0x00c9fd74u'),
                'ambient-loop':('ambient','site, id, -3, 0','site, id, -3, 1'),
                'object-site':('objects','0x00e7507du','0x00e75033u'),
                'object-id':('objects','routine, site, id, -2, 0','routine, site, id + 1, -2, 0')}
            for name,(family,old,new) in variants.items():
                assert old in header
                bad=build(tmp,name,header=header.replace(old,new,1))
                assert check(bad,family,corpora[family]) is not None,name
                report['mutants'][name]='caught'
            # Compile mistakes in the deciding code as well as in routing.
            world=(ROOT/'reconstructed/audio/audio_world.c').read_text()
            for name,old,new in [('voice-random','random % 64','random % 63'),
                                 ('voice-frame','frame <= 10.0f','frame < 10.0f'),
                                 ('voice-buff','!buff_1b && action','buff_1b && action')]:
                assert old in world
                bad=build(tmp,name,world=world.replace(old,new,1))
                assert check(bad,'voice',corpora['voice']) is not None,name
                report['mutants'][name]='caught'
            bad=build(tmp,'talk-gate',talk=(ROOT/'reconstructed/npc/npc_talk.c').read_text().replace('if (!in->encrypted)','if (in->encrypted)',1))
            assert check(bad,'talk',corpora['talk']) is not None
            report['mutants']['talk-gate']='caught'
            hero=(ROOT/'reconstructed/audio/hero_sound.c').read_text()
            for name,old,new in [('walk-site','0x013b202fu','0x013b2054u'),
                                 ('walk-world','w == 2 &&','w == 3 &&'),
                                 ('walk-bridge','attributes[index] & 0x8000','attributes[index] & 0x4000')]:
                assert old in hero
                bad=build(tmp,name,hero=hero.replace(old,new,1))
                assert check(bad,'walk',corpora['walk']) is not None,name
                report['mutants'][name]='caught' 
            objects=(ROOT/'reconstructed/objects/object_render.c').read_text()
            for name,old,new in [('object-type','case 0x5c: sound_event','case 0x5d: sound_event'),
                                 ('object-distance','if (limit >= distance)','if (limit > distance)'),
                                 ('object-order','sound_event(log, index, 0x26a);','sound_event(log, index, 0x26c);')]:
                assert old in objects
                bad=build(tmp,name,objects=objects.replace(old,new,1))
                assert check(bad,'objects',corpora['objects']) is not None,name
                report['mutants'][name]='caught'
    report['cases']=sum(f['cases'] for f in report['families'].values())
    if a.report:Path(a.report).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
