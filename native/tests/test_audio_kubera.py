"""AUDIO-005: stop/play order through the independent native audio reader."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'native/tests'))
import test_audio_monsters as builder
from test_native_audio import constant_wav
HARNESS=r'''
#include "session/session_internal.h"
#include "core/mu_session_audio.h"
#include "core/mu_object_audio.h"
#include "worlds_q.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
static unsigned char actions[64];
static unsigned char *table(void *p,int32_t type,int32_t *count){(void)p;(void)type;*count=4;return actions;}
int main(int argc,char **argv){
 assert(argc==3);char error[512];mu_audio_table sounds;assert(!mu_audio_table_load(argv[1],&sounds,error,sizeof error));
 mu_audio_host_config cfg={0};cfg.table=&sounds;cfg.skip_options=1;cfg.engine.game_root="/";cfg.engine.rate=8000;
 mu_audio_host *saved=mu_audio_host_new(&cfg,error,sizeof error);assert(saved);
 int disabled=!strcmp(argv[2],"disabled"),detached=!strcmp(argv[2],"detached"),muted=!strcmp(argv[2],"muted");
 mu_audio_host *host=disabled?NULL:saved;if(muted)mu_audio_set_group_mute(mu_audio_host_client(saved),MU_AUDIO_GROUP_EFFECT,1);
 mu_session *s=calloc(1,sizeof *s);assert(s);s->tick=23;mu_cue_cursor cursor={0},other={0};
 for(int n=0;n<4;++n){float speed=.3f;short keys=8;memcpy(actions+16*n+4,&speed,4);memcpy(actions+16*n+8,&keys,2);}
 unsigned char object[MU_OBJ_SIZE]={0};mu_obj_set_i32(object,MU_OBJF_TYPE,52);mu_q_inputs in={0};in.world=123;in.actions=table;in.frame_time=.1f;
 mu_obj_event events[8];mu_obj_log log={0,8,0,events};
 for(int n=0;n<3;++n){
  log.count=0;
  if(n==2){in.hero[0]=501;mu_obj_set_u16(object,MU_OBJF_ACTION,3);mu_obj_set_f32(object,MU_OBJF_FRAME,4);}
  assert(mu_kubera_move(object,0,&in,&log));assert(log.count==2);
  assert(events[0].call==MU_Q_STOP_SOUND && events[1].call==MU_OBJ_CALL_SOUND);
  for(int k=0;k<log.count;++k)assert(mu_object_audio_command_deliver(detached?NULL:s,detached?NULL:host,123,&events[k]));
  mu_session_audio_drain(s,&cursor,host);
 }
 if(disabled||detached)mu_session_audio_drain(s,&cursor,saved);
 if(!detached){mu_cue cues[8];uint32_t lost;assert(mu_session_cues(s,&other,cues,8,&lost)==6 && !lost);for(int k=0;k<6;k+=2)assert(cues[k].kind==MU_CUE_SOUND_STOP && cues[k+1].kind==MU_CUE_SOUND);}
 mu_cue c;mu_obj_event bad=events[0];bad.count=3;assert(!mu_object_audio_command_cue(123,&bad,&c));bad=events[0];bad.args[15]=0;assert(!mu_object_audio_command_cue(123,&bad,&c));assert(!mu_object_audio_command_cue(122,&events[0],&c));
 if(!disabled&&!detached)assert(mu_audio_engine_active_voices(mu_audio_host_engine(saved))==1);
 mu_audio_system_update(mu_audio_host_client(saved));
 const mu_audio_entry *near=mu_audio_snd_find(mu_audio_host_client(saved),0x4f1),*far=mu_audio_snd_find(mu_audio_host_client(saved),0x4f2);
 if(!disabled&&!detached){assert(near&&!near->playing);assert(far&&far->playing);}
 float pcm[320];mu_audio_engine_mix(mu_audio_host_engine(saved),pcm,160);int nonzero=0;for(int k=0;k<320;++k)nonzero+=pcm[k]!=0;
 if(disabled||detached||muted)assert(!nonzero);else assert(nonzero);
 free(s);mu_audio_host_free(saved);mu_audio_table_free(&sounds);return 0;
}
'''
class Native(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  with patch.object(builder,'HARNESS',HARNESS):builder.Native.setUpClass.__func__(cls)
  wav=cls.folder/'sound.wav';cls.table.write_text(''.join(f'sound\t{id}\t{wav}\t1\t0\t0\n' for id in (0x4f1,0x4f2,0x4f3,0x4f4)))
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def rows(self,mode):
  log=self.folder/(mode+'.jsonl');r=subprocess.run([str(self.exe),str(self.table),mode],cwd=ROOT,capture_output=True,text=True,env=dict(os.environ,MU_AUDIO_CUE_LOG=str(log)))
  self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  return [json.loads(s) for s in log.read_text().splitlines() if json.loads(s)['op'] in ('play','stop')]
 def test_order_stops_opposite_voice_and_active_suppression(self):
  rows=self.rows('normal');self.assertEqual([r['op'] for r in rows],['stop','play']*3);self.assertEqual([r['id'] for r in rows],[0x4f2,0x4f1,0x4f2,0x4f1,0x4f1,0x4f2]);self.assertEqual([r['result'] for r in rows if r['op']=='play'],[1,0,1]);self.assertEqual([r['site'] for r in rows],[0xe1a2ba,0xe1a2ca]*2+[0xe1a37d,0xe1a38d])
 def test_muted_order(self):self.assertEqual(len(self.rows('muted')),6)
 def test_disabled_drains_both_operations(self):self.assertEqual(self.rows('disabled'),[])
 def test_detached_drops_both_operations(self):self.assertEqual(self.rows('detached'),[])

class World(unittest.TestCase):
 def test_object_runtime_delivers_order_and_preserves_pixels(self):
  from test_native_npc import write_npc_world,PLACE
  from test_native_terrain import write_world
  from test_native_objects import obj_plain,write_models
  subprocess.run(['make','-s','-j4','-C',str(ROOT/'native'),'build/mu-walk'],check=True)
  with tempfile.TemporaryDirectory(prefix='audio-kubera-world-') as tmp:
   folder=Path(tmp);root=write_npc_world(folder/'game');write_world(root,124,rgb=True);write_models(root,124,['Object53.bmd'])
   placement=folder/'placement.txt';placement.write_text(PLACE);objects=folder/'objects';objects.mkdir();(objects/'EncTerrain124.plain').write_bytes(obj_plain(124,[(52,12000.,12000.,0.,0.,1.)]))
   wav=root/'kubera.wav';wav.write_bytes(constant_wav(.125,80000,rate=8000));table=folder/'table.tsv';table.write_text(''.join(f'sound\t{id}\t{wav.name}\t1\t0\t0\n' for id in (0x4f1,0x4f2)))
   hashes=[]
   for enabled in (True,False):
    log=folder/f'{enabled}.jsonl';cmd=[str(ROOT/'native/build/mu-walk'),'--game-root',str(root),'--headless','--backend','soft','--world','123','--placement',str(placement),'--objects-dir',str(objects),'--width','64','--height','64','--frames','24','--every','12','--tile','120,120','--hero-name','Preview','--out-dir',str(folder/str(enabled)),'--sound-table',str(table)]
    if not enabled:cmd+=['--no-audio']
    r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,env=dict(os.environ,MU_AUDIO_CUE_LOG=str(log),MU_GFX_PUBLIC_DEMO='1'));self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    hashes.append([json.loads(line)['sha256'] for line in r.stdout.splitlines() if line.startswith('{') and 'sha256' in json.loads(line)])
    if enabled:
     rows=[json.loads(line) for line in log.read_text().splitlines() if json.loads(line)['handler']==0xe19ed0 and json.loads(line)['op'] in ('stop','play')]
     self.assertTrue(rows);self.assertEqual([row['op'] for row in rows],['stop','play']*(len(rows)//2));self.assertEqual({row['site'] for row in rows},{0xe1a2ba,0xe1a2ca})
   self.assertTrue(hashes[0]);self.assertEqual(hashes[0],hashes[1])

class Original(unittest.TestCase):
 @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','Pinned AUDIO-005 Kubera inputs are opt-in')
 def test_stop_play_commands(self):
  with tempfile.TemporaryDirectory(prefix='audio-kubera-proof-') as tmp:
   subprocess.run([sys.executable,str(ROOT/'scripts/validate_audio_kubera.py'),'--cases','1000','--report',str(Path(tmp)/'report.json')],cwd=ROOT,check=True,capture_output=True)
if __name__=='__main__':unittest.main()
