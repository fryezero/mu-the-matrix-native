#!/usr/bin/env python3
"""AUDIO-005: complete Kubera move, explicit stop/play command order."""
import argparse
import ctypes as C
import json
import shutil
import struct
import math
from pathlib import Path
import subprocess
import tempfile
import time
import pins
import validate_object_render as v
import validate_worlds_q as q
import validate_audio_objects as old
ROOT=Path(__file__).resolve().parents[1]
class Command(C.Structure):_fields_=[('op',C.c_uint32),('routine',C.c_uint32),('site',C.c_uint32),('id',C.c_uint32),('object',C.c_uint32),('loop',C.c_uint32)]
WRAPPER=r'''
#include "core/mu_object_audio.h"
typedef struct command {unsigned op,routine,site,id,object,loop;} command;
void mu_session_sound_emit(mu_session *s,uint32_t r,uint32_t p,int32_t i,int16_t k,int l){(void)s;(void)r;(void)p;(void)i;(void)k;(void)l;}
void mu_session_sound_stop_emit(mu_session *s,uint32_t r,uint32_t p,int32_t i){(void)s;(void)r;(void)p;(void)i;}
int mu_audio_host_cue(mu_audio_host *h,const mu_cue *c,uint32_t t){(void)h;(void)c;(void)t;return 1;}
int decode(int w,const int32_t *i,int n,void *o){(void)w;(void)i;(void)n;(void)o;return 0;}
int command_cue(int w,const mu_obj_event *e,command *out){mu_cue c;if(!mu_object_audio_command_cue(w,e,&c))return 0;
 *out=(command){c.kind==MU_CUE_SOUND_STOP?0xa6ad76:0xa6ac96,c.handler,c.u.sound.site,(unsigned)c.u.sound.id,c.u.sound.at_key==-2?0:1,(unsigned)c.u.sound.loop};return 1;}
'''
def build(folder,header=None):
 saved=old.WRAPPER;old.WRAPPER=WRAPPER
 try:lib=old.build(folder,header or old.HEADER.read_text())
 finally:old.WRAPPER=saved
 lib.command_cue.argtypes=[C.c_int,C.POINTER(v.Event),C.POINTER(Command)];return lib

def commands(lib,world,events):
 out=[]
 for e in events:
  c=Command()
  if lib.command_cue(world,C.byref(e),C.byref(c)):out.append(tuple(getattr(c,k) for k,_ in Command._fields_))
 return out
def annotation_controls(dll):
 table=C.create_string_buffer(64)
 for n in range(4):struct.pack_into('<fh',table,16*n+4,0.,8)
 def actions(ctx,typ,count):count[0]=4;return C.addressof(table)
 callback=q.ACTIONS_FN(actions);inputs=q.Inputs();inputs.world=123;inputs.actions=callback
 cases=[(0,0.,0.),(2,0.,0.),(1,2.001,0.),(3,2.001,0.),(1,math.nan,0.),(1,0.,900.01),(1,2.,0.),(3,2.,0.)]
 for action,frame,distance in cases:
  raw=bytearray(v.OBJ_SIZE);struct.pack_into('<i',raw,0x5c,47);struct.pack_into('<H',raw,0x2a,action);struct.pack_into('<f',raw,0xd0,frame)
  obj=C.create_string_buffer(bytes(raw));inputs.hero[0]=distance;log=v.new_log(8);log.count=1
  log.events[0].call=q.SOUND;log.events[0].count=3;log.events[0].args[0]=0x4f4;before=bytes(log.events[0])
  assert dll.mu_kubera_move(obj,0,C.byref(inputs),C.byref(log))
  assert bytes(log.events[0])==before,(action,frame,distance,'prior event changed')
  sounding=action in (1,3) and frame<=2. and distance<=900.
  assert log.count==1+int(sounding),(action,frame,distance,log.count)
  if sounding:assert log.events[1].args[15] and log.events[1].args[14] in (0xe1a071,0xe1a0a4)
 return len(cases)

class Original(v.Machine):
 def execute(self,start,arguments,regions,stubs,**kwargs):
  self.commands=[];stubs=dict(stubs)
  for op in (q.SOUND,q.STOP):
   fn=stubs.get(op)
   if not fn:continue
   def record(m,fn=fn,op=op):
    site=int.from_bytes(m.uc.mem_read(m.uc.reg_read(m.x86.UC_X86_REG_ESP),4),'little')-5
    self.commands.append((op,q.BODIES['kubera_move'][0],site,m.argument(0),0,m.argument(2) if op==q.SOUND else 0));return fn(m)
   stubs[op]=record
  return super().execute(start,arguments,regions,stubs,**kwargs)
class Proxy:
 def __init__(self,dll,machine,decoder):self.dll,self.machine,self.decoder=dll,machine,decoder;self.corpus=[];self.errors=[]
 def __getattr__(self,name):
  fn=getattr(self.dll,name)
  if name!='mu_kubera_move':return fn
  def call(*args):
   answer=fn(*args);world=C.cast(args[2],C.POINTER(q.Inputs)).contents.world;log=C.cast(args[-1],C.POINTER(v.Log)).contents
   events=[v.Event.from_buffer_copy(log.events[k]) for k in range(log.count) if log.events[k].call in (q.SOUND,q.STOP)]
   want=self.machine.commands;got=commands(self.decoder,world,events)
   if got!=want:self.errors.append((world,want,got))
   self.corpus.append((world,events,list(want)));return answer
  return call
MUTANTS={
 'stop operation':('cue->kind = stop ? MU_CUE_SOUND_STOP : MU_CUE_SOUND;','cue->kind = MU_CUE_SOUND;'),
 'stop site':('site == 0x00e1a2bau && id == 0x4f2','site == 0x00e1a37du && id == 0x4f2'),
 'near play':('site == 0x00e1a2cau && id == 0x4f1','site == 0x00e1a38du && id == 0x4f1'),
 'far play':('site == 0x00e1a38du && id == 0x4f2','site == 0x00e1a2cau && id == 0x4f2'),
 'world':('world >= 123 && world <= 127','world >= 124 && world <= 127'),
 'order':None,
 'annotation gate':None,
}
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cases',type=int,default=1000);ap.add_argument('--mutations',action='store_true');ap.add_argument('--annotation-mutant-only',action='store_true');ap.add_argument('--report',type=Path,required=True);a=ap.parse_args();start=time.monotonic()
 subprocess.run(['make','-s','-j4','-C',str(ROOT/'reconstructed/objects')],check=True)
 machine=Original(pins.TEXT.read(),pins.DATA.read())
 with tempfile.TemporaryDirectory(prefix='audio-005-kubera-') as tmp:
  folder=Path(tmp);decoder=build(folder/'base');lib=q.bind(v.Library(ROOT/f'reconstructed/objects/libobjects.{v.SUFFIX}'));proxy=Proxy(lib.dll,machine,decoder);lib.dll=proxy
  family=q.family(machine,lib,'kubera_move',a.cases);assert not family['mismatch_count'] and not family['stopped'] and not proxy.errors,(family,proxy.errors[:2])
  control_count=annotation_controls(proxy.dll)
  seen={c[2] for _,_,rows in proxy.corpus for c in rows};assert len(seen)==6,seen
  mutants={}
  if a.mutations or a.annotation_mutant_only:
   source=old.HEADER.read_text()
   for name,pair in MUTANTS.items():
    if a.annotation_mutant_only and name!='annotation gate':continue
    if pair:
     oldtext,newtext=pair;assert oldtext in source;bad=build(folder/name,source.replace(oldtext,newtext,1))
     n=sum(commands(bad,w,e)!=want for w,e,want in proxy.corpus)
    else:
     dest=folder/(name+'-source')
     for directory in ('objects','terrain','model-codec','record-math','movement'):
      shutil.copytree(ROOT/'reconstructed'/directory,dest/directory,ignore=shutil.ignore_patterns('*.dylib','*.so','__pycache__'))
     target=dest/'objects/kubera.c';body=target.read_text()
     if name=='order':
      first='stop_sound(log, index, 0x4f2);\n                wb_sound(log, index, 0x4f1, 0, 0);\n                mu_audio_kubera_request(log);'
      swapped='wb_sound(log, index, 0x4f1, 0, 0);\n                mu_audio_kubera_request(log);\n                stop_sound(log, index, 0x4f2);'
     else:
      first='if ((action == 1 || action == 3) && mu_obj_f32(o, MU_OBJF_FRAME) <= 2.0f) mu_audio_kubera_request(log);'
      swapped='mu_audio_kubera_request(log);'
     assert body.count(first)==1;target.write_text(body.replace(first,swapped))
     badlib=q.bind(v.Library(v.build_library(dest)))
     if name=='order':
      badproxy=Proxy(badlib.dll,machine,decoder);badlib.dll=badproxy
      badfamily=q.family(machine,badlib,'kubera_move',a.cases);assert not badfamily['stopped']
      n=badfamily['mismatch_count']+len(badproxy.errors)
     else:
      try:annotation_controls(badlib.dll);n=0
      except AssertionError:n=1
    assert n,name;mutants[name]=n
  report=dict(cases=family['cases'],annotation_controls=control_count,families={'kubera_move':family},sites=6,play_sites=4,stop_sites=2,mismatches=0,mutants=mutants,wall_seconds=round(time.monotonic()-start,3))
  a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='families'},indent=2))
if __name__=='__main__':main()
