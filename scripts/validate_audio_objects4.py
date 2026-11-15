#!/usr/bin/env python3
"""AUDIO-004: original object gates/order and explicit request provenance.

Full existing owning comparisons retain OBJECT/AL/action records/RNG and call
order. Original SND_Play return addresses and arguments independently supply the
expected command, including identical-id sites and the pre-SetAction state.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import time
import pins
import validate_object_render as v
import validate_worlds_p as p
import validate_worlds_p2 as p2
import validate_worlds_after2 as a2
import validate_audio_objects as old
ROOT = Path(__file__).resolve().parents[1]
WRAPPER = r'''
#include "core/mu_object_audio.h"
typedef struct decision { uint32_t handler,site; int32_t id,key,loop; } decision;
void mu_session_sound_emit(mu_session *s,uint32_t r,uint32_t site,int32_t id,int16_t k,int l)
{(void)s;(void)r;(void)site;(void)id;(void)k;(void)l;}
int mu_audio_host_cue(mu_audio_host *h,const mu_cue *c,uint32_t t) {(void)h;(void)c;(void)t;return 1;}
int decode(int w,const int32_t *i,int n,decision *o) {(void)w;(void)i;(void)n;(void)o;return 0;}
int command(int world,const mu_obj_event *e,decision *out) {
 mu_cue c;if(!mu_object_audio_command_cue(world,e,&c))return 0;
 *out=(decision){c.handler,c.u.sound.site,c.u.sound.id,c.u.sound.at_key,c.u.sound.loop};return 1;
}
'''
# Original routine extents, independent of authored command/tag tables.
BODIES = {'ok_move':p.BODIES['ok_move'], 'bk_move':p.BODIES['bk_move'],
          'ignis_move':p2.BODIES['ignis_move'],
          'guardian':(0xdd2fae,0xdd306c), 'karutan':(0xe189af,0xe189e4),
          'darkness':(0xe5e1a4,0xe5e2d5)}
NAMES = ('mu_old_kethotum_move','mu_burning_kethotum_move','mu_ignis_move','mu_class_premove')


def adapter(folder, header=None):
    saved = old.WRAPPER
    old.WRAPPER = WRAPPER
    try:
        lib = old.build(folder, header or old.HEADER.read_text())
    finally:
        old.WRAPPER = saved
    lib.command.argtypes = [C.c_int32,C.POINTER(v.Event),C.POINTER(old.Decision)]
    return lib


def commands(lib, world, events):
    rows=[]
    for e in events:
        row=old.Decision()
        if lib.command(world,C.byref(e),C.byref(row)):
            rows.append(tuple(getattr(row,k) for k,_ in old.Decision._fields_))
    return rows


class Original(v.Machine):
    def execute(self,start,arguments,regions,stubs,**kwargs):
        self.sounds=[]
        sound=stubs.get(0xa6ac96)
        if sound:
            def record(m):
                site=int.from_bytes(m.uc.mem_read(m.uc.reg_read(m.x86.UC_X86_REG_ESP),4),'little')-5
                owners=[lo for lo,hi in BODIES.values() if lo<=site<hi]
                assert len(owners)==1,hex(site)
                obj=m.argument(1)
                assert obj in (0,v.OBJECTS),(hex(site),hex(obj))
                self.sounds.append((owners[0],site,m.argument(0),-3 if obj else -2,m.argument(2)))
                return sound(m)
            stubs=dict(stubs);stubs[0xa6ac96]=record
        return super().execute(start,arguments,regions,stubs,**kwargs)


class Calls:
    def __init__(self,dll,machine,decoder):
        self.dll,self.machine,self.decoder=dll,machine,decoder
        self.corpus=[];self.errors=[]
    def __getattr__(self,name):
        fn=getattr(self.dll,name)
        if name not in NAMES:return fn
        def call(*args):
            answer=fn(*args)
            if name=='mu_class_premove':world=args[0]
            else:world=C.cast(args[2],C.POINTER(v.MoveInputs)).contents.world # world is first in all inputs
            log=C.cast(args[-1],C.POINTER(v.Log)).contents
            events=[v.Event.from_buffer_copy(log.events[k]) for k in range(log.count) if log.events[k].call==0xa6ac96]
            expected=list(self.machine.sounds)
            actual=commands(self.decoder,world,events)
            self.corpus.append((world,events,expected))
            if actual!=expected:self.errors.append({'function':name,'world':world,'original':expected,'native':actual})
            return answer
        return call


def directed_keth(machine,lib):
    """Deterministic coverage of the narrow frame/gate sites and their edges."""
    import struct
    import actor_machine as am
    tally=v.Tally('keth_directed')
    # type, action, frame, hero distance. Sites with the same id are separate.
    cases=[(0x17,0,0,800),(0x19,0,0,800),(0x28,0,0,1300),
           (0x16,1,0,1000),(0x5c,1,.9,1000),
           (0x77,1,8,300),(0x77,2,0,300),(0x77,0,0,299),(0x77,3,8,299),
           (0xa0,0,0,400),(0xa5,0,0,400),(0xb5,0,3.5,1199),(0xb5,2,7.5,1200)]
    for world,name in [(135,'ok_move'),(136,'bk_move')]:
        for typ,action,frame,distance in cases:
            for delta in (-.01,0,.01):
                raw=bytearray(v.OBJ_SIZE);v.put_i(raw,0x5c,typ)
                struct.pack_into('<H',raw,0x2a,action);v.put_f(raw,0xd0,frame)
                hero=[v.f32(distance+delta),0.,0.];speeds=[.3]*p.MODEL_ACTIONS;keys=[8]*p.MODEL_ACTIONS
                rnd,crnd=v.MsvcRand(7),v.MsvcRand(7);calls=[]
                stubs=p.common_stubs(calls,rnd,True);stubs.update(p.ein_stubs(calls,True,15))
                regs=v.global_regions(world,6,[am.defined_region('object',v.OBJECTS,bytes(raw)),
                    am.defined_region('time',v.TIME,v.pack_f(0),writable=False),
                    am.defined_region('frame-time',p.FRAME_TIME,v.pack_f(.1),writable=False),
                    am.defined_region('hero-pointer',v.HERO_PTR,struct.pack('<I',v.HERO),writable=False),
                    am.defined_region('hero',v.HERO+0x33ac,v.pack_f(*hero),writable=False)]+
                    p.model_regions(8,speeds,keys,False))
                result=v.run(machine,p.BODIES[name][0],[v.OBJECTS],regs,stubs,ecx=v.FAKE,cleanup=4)
                stop=v.stopped_reason(result)
                if stop:tally.add(False,{'world':world,'type':typ},stop);continue
                obj=C.create_string_buffer(bytes(raw),v.OBJ_SIZE);model=p.c_model(8,speeds,keys)
                inputs=p.Inputs(world,(C.c_float*3)(*hero),.1,C.pointer(model),v.RAND_FN(lambda c:crnd()),None,1,15)
                log=v.new_log();fn=lib.dll.mu_old_kethotum_move if world==135 else lib.dll.mu_burning_kethotum_move
                answer=fn(obj,0,C.byref(inputs),C.byref(log))
                tally.add(obj.raw[:v.OBJ_SIZE]==result['regions']['object'] and answer==(result['eax']&255) and
                          calls==v.log_events(log) and rnd.seed==crnd.seed,{'world':world,'type':typ,'action':action})
    return tally.report()


def directed_premove(machine,lib):
    import struct
    import actor_machine as am
    tally=v.Tally('premove_directed')
    cases=[(69,69,k,0,0) for k in range(-1,5)]+[(69,72,0,0,0),(80,80,0,0x3a,0)]+[
        (122,122,0,typ,action) for typ,action in [(0x1a,0),(0x83,0),(0x83,1),(0x84,1),(0x85,0),(0xa1,0),(0xa8,0)]]
    for cls,world,state,typ,action in cases:
        raw=bytearray(v.OBJ_SIZE);v.put_i(raw,0x5c,typ);struct.pack_into('<H',raw,0x2a,action)
        handler=bytearray(0x40);struct.pack_into('<I',handler,0,a2.VTABLE69);struct.pack_into('<i',handler,0x14,state)
        calls=[]
        def sound(m):calls.append((0xa6ac96,0,m.argument(0),int(m.argument(1)!=0),m.argument(2)));return 0
        regions=v.global_regions(world,6,[am.defined_region('object',v.OBJECTS,bytes(raw),writable=False),
            am.defined_region('handler69',a2.HANDLER69,bytes(handler),writable=False),
            am.defined_region('fake',v.FAKE,v.fake_object(),writable=False)])
        result=v.run(machine,a2.PREMOVE[cls],[v.OBJECTS],regions,
            {0xa6ac96:sound,0x1989721:lambda m:0,0xdd8a3c:lambda m:a2.HANDLER69},
            ecx=a2.HANDLER69 if cls==69 else v.FAKE,cleanup=4)
        stop=v.stopped_reason(result)
        if stop:tally.add(False,{'class':cls,'type':typ},stop);continue
        obj=C.create_string_buffer(bytes(raw),v.OBJ_SIZE);log=v.new_log()
        lib.dll.mu_class_premove(cls,obj,0,world,state,v.RAND_FN(lambda c:0),None,C.byref(log))
        tally.add(calls==v.log_events(log),{'class':cls,'type':typ,'state':state})
    return tally.report()


def check(cases,dll_path,decoder,text,data):
    machine=Original(text,data)
    lib=a2.Library(dll_path);p.bind(lib);p2.bind(lib)
    proxy=Calls(lib.dll,machine,decoder);lib.dll=proxy
    families={}
    for name in ('ok_move','bk_move'):families[name]=p.family(machine,lib,name,cases)
    families['premove_directed']=directed_premove(machine,lib)
    families['keth_directed']=directed_keth(machine,lib)
    families['ignis_move']=p2.family(machine,lib,'ignis_move',cases)
    for world in (69,70,71,72,80,81,122):
        families[f'premove_{world}']=a2.premove_family(machine,lib,random.Random(0xA004+world),cases,world).report()
    return families,proxy.corpus,proxy.errors


MUTANTS=[
 ('tag','audio_request.h','e->args[15] = MU_AUDIO_OBJECT_TAG;','e->args[15] = 0;'),
 ('ignis site','audio_request.h','action == 1 ? 0x00e05eddu','action != 1 ? 0x00e05eddu'),
 ('gate pre-action','audio_request.h','action == 0 ? 0x00e3aceau','action == 1 ? 0x00e3aceau'),
 ('close branches','audio_request.h','action == 1 ? 0x00d940a3u','action == 2 ? 0x00d940a3u'),
 ('brazier site','audio_request.h','type == 0xa5 ? 0x00d94361u','type == 0xa0 ? 0x00d94361u'),
 ('swamp repeated id','audio_request.h','case 0x85: site = 0x00e5e25du','case 0x85: site = 0x00e5e236u'),
 ('guardian site','audio_request.h','case 0x38d: site = 0x00dd304du','case 0x38d: site = 0x00dd303au'),
 ('owner','core','cue->u.sound.at_key = event->args[1] ? -3 : -2;','cue->u.sound.at_key = -2;'),
 ('loop','core','cue->u.sound.loop = (int32_t)event->args[2];','cue->u.sound.loop = 1;'),
 ('id','core','cue->u.sound.id = (int32_t)event->args[0];','cue->u.sound.id = (int32_t)event->args[0]+1;'),
]


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cases',type=int,default=1000)
    ap.add_argument('--mutations',action='store_true');ap.add_argument('--report',type=Path,required=True)
    args=ap.parse_args();start=time.monotonic()
    subprocess.run(['make','-s','-j4','-C',str(ROOT/'reconstructed/objects')],check=True)
    text,data=pins.TEXT.read(),pins.DATA.read()
    with tempfile.TemporaryDirectory(prefix='audio-004-') as temp:
        folder=Path(temp);decoder=adapter(folder/'base')
        lib_path=ROOT/f'reconstructed/objects/libobjects.{v.SUFFIX}'
        families,corpus,errors=check(args.cases,lib_path,decoder,text,data)
        seen={row[1] for _,_,rows in corpus for row in rows}
        if args.cases >= 1000 and len(seen)!=33:errors.append({'original_site_coverage':len(seen),'expected':33})
        # Refuse a stop command and missing/forged provenance, even with a known id.
        example=next((w,e[0]) for w,e,rows in corpus if rows)
        for world,event in [(0,example[1]),(example[0],v.Event.from_buffer_copy(example[1]))]:
            if world:event.call=0xa6ad76
            if commands(decoder,world,[event]):errors.append({'refusal':world})
        mutants=[]
        if args.mutations:
            for n,(name,file,before,after) in enumerate(MUTANTS):
                if file=='core':
                    header=old.HEADER.read_text();assert before in header
                    changed=adapter(folder/f'adapter{n}',header.replace(before,after,1))
                    detected=sum(commands(changed,w,e)!=expected for w,e,expected in corpus)
                    stopped=0
                else:
                    dest=folder/f'source{n}'
                    for directory in ('objects','terrain','model-codec','record-math','movement'):
                        shutil.copytree(ROOT/'reconstructed'/directory,dest/directory,
                                        ignore=shutil.ignore_patterns('*.dylib','*.so','__pycache__'))
                    path=dest/'objects'/file;source=path.read_text();assert before in source
                    path.write_text(source.replace(before,after,1))
                    changed_path=v.build_library(dest)
                    fs,_,es=check(args.cases,changed_path,decoder,text,data)
                    detected=len(es);stopped=sum(f['stopped'] for f in fs.values())
                    shutil.rmtree(dest)
                mutants.append({'name':name,'detected':detected,'stopped':stopped})
                print('mutant',mutants[-1],flush=True)
        report={'cases':sum(f['cases'] for f in families.values()),'original_sites':len(seen),
                'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,
                'bodies':{k:{'start':hex(lo),'end':hex(hi),'sha256':hashlib.sha256(text[lo-v.am.TEXT_BASE:hi-v.am.TEXT_BASE]).hexdigest()} for k,(lo,hi) in BODIES.items()},
                'families':families,'mismatches':len(errors),'examples':errors[:10],'mutants':mutants,
                'wall_seconds':round(time.monotonic()-start,2)}
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:report[k] for k in ('cases','original_sites','mismatches','examples','mutants','wall_seconds')}))
        return int(bool(errors) or any(f['mismatch_count'] or f['stopped'] for f in families.values()) or
                   any(not m['detected'] or m['stopped'] for m in mutants))
if __name__=='__main__':raise SystemExit(main())
