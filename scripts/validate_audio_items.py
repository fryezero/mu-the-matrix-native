#!/usr/bin/env python3
"""AUDIO-002D: six CreateItem drop sites against the full existing caller family.

The unchanged family compares complete original/reconstructed CreateItem outputs,
including missing records, non-drop calls and call order. Record original sound
return addresses and compare the compiled session audio adapter for those inputs.
The delete handler has no sound; pickup answers remain unrouted.
"""
import argparse
import ctypes as C
from collections import defaultdict
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import pins
import validate_items as vi
from validate_audio_domains import Decision
ROOT=Path(__file__).resolve().parents[1]
WRAPPER=r'''
#include "items_audio.h"
typedef struct decision { unsigned routine,site; int id,key,loop,missing; } decision;
static decision rows[8];static int count;
void mu_session_sound_emit(mu_session *s,unsigned routine,unsigned site,int id,int16_t key,int loop)
{(void)s;rows[count++]=(decision){routine,site,id,key,loop,0};}
void mu_session_sound_missing(mu_session *s,unsigned routine,unsigned site,unsigned input)
{(void)s;rows[count++]=(decision){routine,site,(int)input,-2,0,1};}
int drop(int code,int flag,int present,int slot,decision *out) {
 count=0;mu_session_items_drop_audio(NULL,code,flag,present,(int16_t)slot);
 for(int i=0;i<count;++i)out[i]=rows[i];return count;
}
'''
def build(tmp,name,header=None):
    folder=tmp/name;folder.mkdir();src=folder/'wrapper.c';src.write_text(WRAPPER)
    (folder/'items_audio.h').write_text((header or (ROOT/'native/session/domains/items_audio.h').read_text()).replace('"../mu_audio_cue.h"','"mu_audio_cue.h"').replace('"../../../reconstructed/items/ground_items.h"','"ground_items.h"'))
    out=folder/'adapter.dylib'
    subprocess.run(['cc','-shared','-O2','-I',str(folder),'-I',str(ROOT/'native/session'),'-I',str(ROOT/'native/build/gen'),
                    '-I',str(ROOT/'reconstructed/items'),str(src),str(ROOT/'reconstructed/items/ground_items.c'),str(ROOT/'reconstructed/items/item_sets.c'),str(ROOT/'reconstructed/record-math/record_math.c'),'-lm','-o',str(out)],check=True)
    lib=C.CDLL(str(out));lib.drop.argtypes=[C.c_int]*4+[C.POINTER(Decision)];return lib
class Sites(vi.Machine):
    def execute_regions(self,start,arguments,regions,stubs,**kw):
        self.sounds=[];self.slot=(arguments[0]-vi.POOL)//vi.STRIDE
        if vi.SOUND in stubs:
            stubs=dict(stubs);original=stubs[vi.SOUND]
            def sound(m):
                ret=struct.unpack('<I',m.uc.mem_read(m.uc.reg_read(m.x86.UC_X86_REG_ESP),4))[0]
                obj=m.argument(1);assert m.argument(2)==0
                self.sounds.append((start,ret-5,m.argument(0),-2 if obj==0 else self.slot,0,0))
                return original(m)
            stubs[vi.SOUND]=sound
        return super().execute_regions(start,arguments,regions,stubs,**kw)
class Corpus(vi.Report):
    def __init__(self,m):super().__init__();self.m=m;self.rows=[]
    def add(self,family,equal,failure=None):
        assert equal,(family,failure)
        super().add(family,equal,failure)
        self.rows.append(((int(failure['code'],16),int(failure['drop']),int(failure['present']),self.m.slot),self.m.sounds[:]))
def check(lib,corpus):
    for args,want in corpus:
        out=(Decision*8)();n=lib.drop(*args,out)
        got=[tuple(getattr(out[i],k) for k,_ in Decision._fields_) for i in range(n)]
        if got!=want:return args,want,got
    return None

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=int,default=3000)
    p.add_argument('--mutations',action='store_true');p.add_argument('--report');a=p.parse_args()
    text,data=pins.TEXT.read(),pins.DATA.read();m=Sites(text,data);m.uc.mem_write(vi.PATCHED_SITE,vi.PATCHED_BYTES);r=Corpus(m)
    vi.family_create(m,vi.load_library(ROOT/'reconstructed/items/libclient_items.dylib'),random.Random(20024),a.cases,r,defaultdict(int))
    seen={v[1] for args,rows in r.rows for v in rows}
    assert seen=={0x16daafd,0x16dadde,0x16dae04,0x16dae36,0x16dae5f,0x16dae76},seen
    report={'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,'cases':len(r.rows),'mismatches':0,'sites':[hex(s) for s in sorted(seen)],'mutants':{}}
    with tempfile.TemporaryDirectory(prefix='audio-items-') as folder:
        tmp=Path(folder);lib=build(tmp,'base');assert check(lib,r.rows) is None
        header=(ROOT/'native/session/domains/items_audio.h').read_text()
        if a.mutations:
            plants=[('drop-gate','mu_gi_drop_sound(code, drop)','mu_gi_drop_sound(code, 1)'),
                    ('record-gate','available == 0','available == 1'),
                    ('zen-site','0x016daafdu','0x016daddeu'),
                    ('jewel-site','0x016daddeu','0x016dae04u'),
                    ('special-boundary','code >= 0x1d09','code >= 0x1d00'),
                    ('plain-site','0x016dae76u','0x016dae5fu'),
                    ('loop','? -2 : slot, 0','? -2 : slot, 1'),
                    ('null-object','id == 0x1f ? -2 : slot','slot')]
            for name,old,new in plants:
                assert old in header;bad=build(tmp,name,header.replace(old,new,1))
                assert check(bad,r.rows) is not None,name;report['mutants'][name]='caught'
        # Missing static input stays explicit; this is a native boundary, not
        # an additional original-instruction comparison.
        out=(Decision*8)();assert lib.drop(1,1,-1,999,out)==1 and out[0].missing==1
    if a.report:Path(a.report).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
