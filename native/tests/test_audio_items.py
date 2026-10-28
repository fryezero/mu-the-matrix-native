"""Ground viewport arrival -> session sound; deletion/request/rebind stay silent."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_native_items import write_items_world
from test_native_data import item_file,item_record
from test_native_audio import constant_wav
NATIVE=Path(__file__).resolve().parents[1]
CODES=[0x1c0f,0x1c0d,0x1c29,0x1cfe,0x1d09,1]
HARNESS=r'''
#include "session/mu_session_seed.h"
#include "fixture/mu_fixture.h"
#include "core/mu_items.h"
#include "core/mu_session_audio.h"
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
static int direct;
static void unexpected(void *u,int id) {(void)u;(void)id;++direct;}
int main(int argc,char **argv) {
 assert(argc==5);char error[512];mu_fixture_options fo={argv[1],NULL,20024};
 mu_fixture *fx=mu_fixture_open(&fo,error,sizeof error);assert(fx);mu_transport *tr=mu_fixture_transport(fx);
 mu_session_config cfg={0};cfg.transport=tr;mu_fixture_endpoint(fx,"game",&cfg.connect_server);
 mu_session_seed seed={0};mu_session *s=mu_session_open_seeded(&cfg,&seed,error,sizeof error);assert(s);
 mu_world_items *it=calloc(1,sizeof *it);mu_walk walk={0};assert(it);
 assert(!mu_world_items_open(it,argv[2],&walk,NULL,error,sizeof error));
 it->play_sound=unexpected;mu_world_items_bind(it,s,NULL);
 mu_audio_table table;assert(!mu_audio_table_load(argv[3],&table,error,sizeof error));
 mu_audio_host_config ac={0};ac.table=&table;ac.skip_options=1;ac.engine.game_root="/";
 mu_audio_host *host=mu_audio_host_new(&ac,error,sizeof error);assert(host);
 mu_cue_cursor audio={0},view={0};
 for(unsigned tick=1;tick<=9;++tick) {
  if(tick==5)mu_world_items_close(it);
  if(tick==7) {memset(it,0,sizeof *it);assert(!mu_world_items_open(it,argv[2],&walk,NULL,error,sizeof error));
   it->play_sound=unexpected;mu_world_items_bind(it,s,NULL);}
  mu_transport_poll(tr,tick*40);mu_session_pump(s,tick*40);

  if(tick==3) {mu_intent in={.kind=MU_INTENT_ITEM_PICKUP};in.u.item_pickup.slot=1;mu_session_submit(s,&in);}
  mu_session_audio_drain(s,&audio,!strcmp(argv[4],"silent")?NULL:host);mu_session_audio_drain(s,&audio,host);
 }
 mu_cue cues[128];uint32_t lost=0;size_t n=mu_session_cues(s,&view,cues,128,&lost);assert(!lost);
 unsigned sounds=0,missing=0;for(size_t i=0;i<n;++i) {sounds+=cues[i].kind==MU_CUE_SOUND;missing+=cues[i].kind==MU_CUE_AUDIO_INPUT;}
 printf("{\"sounds\":%u,\"missing\":%u,\"direct\":%d,\"voices\":%d}\n",sounds,missing,direct,mu_audio_engine_active_voices(mu_audio_host_engine(host)));
 mu_world_items_close(it);free(it);mu_session_close(s);mu_transport_free(tr);mu_fixture_close(fx);
 mu_audio_host_free(host);mu_audio_table_free(&table);return 0;
}
'''
def entry(slot,code,drop=True):
 b=bytearray(15);b[0]=code&255;b[2]=255;b[3]=(code>>1)&128;b[5]=((code>>5)&0xf0)|((code>>13)&1);b[7:]=bytes([255])*8
 key=slot|(0x8000 if drop else 0)
 return key.to_bytes(2,'big')+bytes([120,120])+b
def viewport(entries):
 n=5+19*len(entries);return bytes([0xc2,n>>8,n&255,0x20,len(entries)])+b''.join(entries)
def delete(slots):
 n=5+2*len(slots);return bytes([0xc2,n>>8,n&255,0x21,len(slots)])+b''.join(s.to_bytes(2,'big') for s in slots)
class ItemAudio(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  subprocess.run(['make','-C',str(NATIVE),'audio','build/mu-session','build/mu-walk'],check=True,capture_output=True)
  cls.tmp=tempfile.TemporaryDirectory(prefix='audio-item-route-');cls.folder=Path(cls.tmp.name);cls.root=write_items_world(cls.folder/'game')
  rec=[]
  for code in CODES:
   r=bytearray(item_record(code,b'Data\\Item\\',b'Sword02.bmd',b'Synthetic'));r[0x250:0x253]=bytes(3);rec.append(bytes(r))
  (cls.root/'Data/Local/item.bmd').write_bytes(item_file(rec))
  wav=cls.folder/'sound.wav';wav.write_bytes(constant_wav(.125,8000));cls.table=cls.folder/'sounds.tsv'
  cls.table.write_text(''.join(f'sound\t{id}\t{wav}\t1\t1\t0\t0\n' for id in [31,69,723,90,30]))
  cls.placement=cls.folder/'placement';cls.placement.write_text('actor 3 130 130 0 label spider\n')
  cls.scenario=cls.folder/'items.scn'
  frames=[(1,viewport([entry(i,c) for i,c in enumerate(CODES[:3])])),
          (1,viewport([entry(i+3,c) for i,c in enumerate(CODES[3:])])),
          (1,viewport([entry(7,1,False),entry(8,0x2c00)])),
          (2,viewport([entry(0,0x1c0f,False)])),(4,delete([*range(6),7,8])),
          (6,viewport([entry(999,1)])),(8,delete([999]))]
  cls.scenario.write_text('endpoint game 127.0.0.1:55906\n'+''.join(f'at {t} send game {b.hex(" ")}\n' for t,b in frames))
  src=cls.folder/'host.c';src.write_text(HARNESS);obj=cls.folder/'host.o';cls.host=cls.folder/'host'
  subprocess.run(['cc','-std=c11','-DMU_SESSION_SEED','-I',str(NATIVE),'-I',str(NATIVE/'session'),'-I',str(NATIVE/'build/gen'),'-c',str(src),'-o',str(obj)],check=True,capture_output=True)
  frameworks=['-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation','-framework','AudioToolbox'] if sys.platform=='darwin' else []
  crypto=subprocess.check_output(['brew','--prefix','cryptopp'],text=True).strip();jpeg=subprocess.check_output(['brew','--prefix','jpeg-turbo'],text=True).strip()
  subprocess.run(['c++',str(obj),str(NATIVE/'build/libmusession.a'),str(NATIVE/'build/libmunative.a'),str(NATIVE/'build/libmuaudio.a'),'-L'+crypto+'/lib','-lcryptopp','-L'+jpeg+'/lib','-ljpeg',*frameworks,'-lm','-o',str(cls.host)],check=True,capture_output=True)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_arrival_sites_no_delete_or_request_sound_and_no_rebind_replay(self):
  log=self.folder/'route.jsonl';p=subprocess.run([str(self.host),str(self.scenario),str(self.root),str(self.table),'on'],capture_output=True,text=True,env={**os.environ,'MU_AUDIO_CUE_LOG':str(log)})
  self.assertEqual(p.returncode,0,p.stdout+p.stderr);r=json.loads(p.stdout);self.assertEqual((r['sounds'],r['missing'],r['direct']),(6,1,0));self.assertEqual(r['voices'],5)
  rows=list(map(json.loads,log.read_text().splitlines()));sounds=[r for r in rows if r['op']=='play' and r['handler']]
  self.assertEqual([(r['site'],r['id'],r['at_key']) for r in sounds],[(0x16daafd,31,-2),(0x16dadde,69,1),(0x16dae04,723,2),(0x16dae36,90,3),(0x16dae5f,90,4),(0x16dae76,30,5)])
  self.assertTrue(all(r['session_tick']==1 for r in sounds));self.assertEqual(len({r['cue_seq'] for r in sounds}),6)
  self.assertEqual(len([r for r in rows if r['op']=='unrecovered' and r['id']==0xccc591]),1)
 def test_silent_arrivals_are_not_replayed(self):
  log=self.folder/'silent.jsonl';p=subprocess.run([str(self.host),str(self.scenario),str(self.root),str(self.table),'silent'],capture_output=True,text=True,env={**os.environ,'MU_AUDIO_CUE_LOG':str(log)})
  self.assertEqual(p.returncode,0,p.stdout+p.stderr);r=json.loads(p.stdout);self.assertEqual((r['sounds'],r['voices'],r['direct']),(6,0,0))
  self.assertFalse(any(r['op']=='play' and r['handler'] for r in map(json.loads,log.read_text().splitlines())))
 def test_real_world_standalone_and_shared_reader_keep_hashes(self):
  for mode in [[],['--combat','--placement',str(self.placement)]]:
   hashes=[]
   for on in [True,False]:
    with tempfile.TemporaryDirectory(dir=self.folder) as out:
     log=Path(out)/'audio.jsonl';cmd=[str(NATIVE/'build/mu-walk'),'--game-root',str(self.root),'--items','--headless','--backend','soft','--tile','120,120','--frames','10','--every','4','--width','64','--height','64','--out-dir',out,'--sound-table',str(self.table),'--item-script','1:drop:1:0:120,120',*mode]
     if not on:cmd+=['--no-audio']
     p=subprocess.run(cmd,capture_output=True,text=True,env={**os.environ,'MU_AUDIO_CUE_LOG':str(log)})
     self.assertEqual(p.returncode,0,p.stdout+p.stderr);hashes.append([r['sha256'] for r in map(json.loads,[l for l in p.stdout.splitlines() if l.startswith('{')]) if 'sha256' in r])
     if on:
      sounds=[r for r in map(json.loads,log.read_text().splitlines()) if r['op']=='play' and r['handler']==0x16daa27]
      self.assertEqual(len(sounds),1);self.assertEqual(sounds[0]['site'],0x16dae76)
   self.assertEqual(hashes[0],hashes[1]);self.assertEqual(len(hashes[0]),4)
 @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','Pinned ground audio instructions are opt-in')
 def test_original_ground_audio(self):
  report=self.folder/'original.json';p=subprocess.run([sys.executable,str(NATIVE.parent/'scripts/validate_audio_items.py'),'--cases','3000','--mutations','--report',str(report)],capture_output=True,text=True)
  self.assertEqual(p.returncode,0,p.stdout+p.stderr);r=json.loads(report.read_text());self.assertEqual((r['cases'],r['mismatches'],len(r['mutants'])),(3000,0,8))
if __name__=='__main__':unittest.main()
