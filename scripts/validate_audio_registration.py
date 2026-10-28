#!/usr/bin/env python3
"""AUDIO-002 ordered SND_Load comparisons of full captured model openers.

Reuses the existing actor machine/fixtures for model and string services. Every
sound call is recorded with its return-site and id/channels/3d arguments. C knows
neither filenames nor pointers. Runs every monster and NPC model type, model
preloaded exits, and two worlds. --mutations compiles wrong C order/id.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import subprocess
import struct
import tempfile
import sys
import pins
import actor_machine as am
import validate_actors as actors
from audio_registration_static import emit
import actor_static
ROOT = Path(__file__).resolve().parents[1]
LOAD = C.CFUNCTYPE(None,C.c_void_p,C.c_uint32,C.c_int32,C.c_int32,C.c_int32)
class Machine(am.ActorMachine):
    def execute(self, entry, args, regions, stubs):
        self.audio=[]
        def wave(m):
            site=m.read32(m.uc.reg_read(m.x86.UC_X86_REG_ESP))-5
            self.audio.append((site,m.argument(0),m.argument(2),m.argument(3)))
            return 0
        stubs[actors.LOAD_WAVE]=wave
        return super().execute(entry,args,regions,stubs)
def native(lib,name,t,preloaded):
    out=[]; cb=LOAD(lambda ctx,site,id,ch,flag:out.append((site,id,ch,flag)))
    getattr(lib,'mu_audio_register_'+name)(C.c_int32(t),C.c_int(preloaded),cb,None)
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report');p.add_argument('--mutations',action='store_true');args=p.parse_args()
    text,data=pins.TEXT.read(),pins.DATA.read()
    assert (ROOT/'reconstructed/audio/audio_registration.inc').read_text()==emit(actor_static.Image(text,data))
    m=Machine(text,data);lib=C.CDLL(str(ROOT/'reconstructed/audio'/('libclient_audio.dylib' if sys.platform == 'darwin' else 'libclient_audio.so')))
    report={'families':{},'mutants':{},'mismatches':0};corpus=[]
    for name,entry,types in [('monster',0x180b0f4,range(0x259)),('npc',0x1808a40,range(0x9fe,0xa90))]:
        count=0
        for t in types:
            for preloaded in (False,True):
                for world in (0,39):
                    case=actors.monster_case('audio',t,actions=16,world=world,preloaded=(1,16) if preloaded else None)
                    if name=='npc':
                        case['index']=t
                        # OpenNpc also shuffles per-mesh texture flags for model a56.
                        # Supply a synthetic 32-byte flag array, no captured model data.
                        case['regions'][0].define(actors.MODEL_BASE+0x34,struct.pack('<I',0x22000000))
                        case['regions'].append(am.defined_region('mesh_flags',0x22000000,bytes(range(32))))
                    result=actors.run_client_open(m,case,entry=entry)
                    if not result['ok']: raise AssertionError((name,t,preloaded,world,result['checks'],result['stopped'],result['error']))
                    want=m.audio; got=native(lib,name,t,preloaded)
                    if want!=got:raise AssertionError((name,t,preloaded,world,want,got))
                    corpus.append((name,t,preloaded,want));count+=1
        report['families'][name]={'cases':count,'mismatches':0}
        print(name,count,'cases, 0 mismatches',flush=True)
    if args.mutations:
        source=(ROOT/'reconstructed/audio/audio_registration.inc').read_text()
        mutations={'wrong-id':('u, 210, 2, 1','u, 211, 2, 1'),
                   'preloaded':('preloaded || !load','!load'),
                   'npc-id':('u, 160, 1, 1','u, 161, 1, 1')}
        # Swap two registrations without changing their payloads.
        lines=source.splitlines();idx=next(i for i,line in enumerate(lines) if 'u, 210, 2, 1' in line)
        order=lines[:];order[idx],order[idx+1]=order[idx+1],order[idx]
        variants={n:source.replace(old,new,1) for n,(old,new) in mutations.items()}
        variants['order']='\n'.join(order)+'\n'
        with tempfile.TemporaryDirectory(prefix='audio-registration-') as tmp:
            for name,body in variants.items():
                assert body!=source
                src,dll=Path(tmp)/'bad.c',Path(tmp)/(name+'.dylib')
                src.write_text('#include <stdint.h>\n'+body)
                subprocess.run(['clang','-shared','-fPIC',str(src),'-o',str(dll)],check=True)
                bad=C.CDLL(str(dll))
                assert any(native(bad,n,t,pre)!=want for n,t,pre,want in corpus),name
                report['mutants'][name]='caught'
    report['cases']=sum(f['cases'] for f in report['families'].values())
    print(json.dumps(report,indent=2))
    if args.report:Path(args.report).write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
