"""AUDIO-005: original scalar owners and native cue delivery."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'native/tests'))
from test_native_audio import constant_wav
HARNESS=r'''
#include "session/session_internal.h"
#include "core/mu_session_audio.h"
#include "core/mu_monster_audio.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char **argv){
 assert(argc==3);char error[512];mu_audio_table table;
 assert(!mu_audio_table_load(argv[1],&table,error,sizeof error));
 mu_audio_host_config cfg={0};cfg.table=&table;cfg.skip_options=1;cfg.engine.game_root="/";cfg.engine.rate=8000;
 mu_audio_host *saved=mu_audio_host_new(&cfg,error,sizeof error);assert(saved);
 int disabled=!strcmp(argv[2],"disabled"),detached=!strcmp(argv[2],"detached"),muted=!strcmp(argv[2],"muted");
 mu_audio_host *host=disabled?NULL:saved;
 if(muted)mu_audio_set_group_mute(mu_audio_host_client(saved),MU_AUDIO_GROUP_EFFECT,1);
 mu_session *s=calloc(1,sizeof *s);assert(s);s->tick=17;mu_cue_cursor cursor={0},other={0};
 mu_combat *c=calloc(1,sizeof *c);mu_world_actors actors={0};mu_world_actor actor={0};mu_world map={0};mu_walk walk={0};
 c->session=detached?NULL:s;c->actors=&actors;c->walk=&walk;c->map=&map;actors.count=1;actors.list=&actor;
 map.world=138;walk.map=&map;actor.actor.loaded=1;actor.actor.bmd.action_count=8;actor.actor.spec.model_index=2374;actor.session_key=7;
 actor.actor.object[0x2a]=5;
 assert(mu_monster_audio_combat(c,0,0,210)==210);
 mu_session_audio_drain(s,&cursor,host);mu_session_audio_drain(s,&cursor,host);
 /* Each actual shock is a new trigger. An already-playing id suppresses PCM,
  * while a played marker suppresses the caller itself, as in SetPlayerDie. */
 assert(mu_monster_audio_combat(c,0,.001f,210)==210);
 assert(mu_monster_audio_combat(c,0,0,210)==210);mu_session_audio_drain(s,&cursor,host);
 if(disabled || detached)mu_session_audio_drain(s,&cursor,saved);
 if(!detached){mu_cue cues[8];uint32_t lost;assert(mu_session_cues(s,&other,cues,8,&lost)==2 && !lost);}
 /* The real caller byte aliases OBJECT frame. Nonzero frame is not a fresh
  * shock/attack/death trigger even if the native audio latch is still zero. */
 float blocked=.001f;memcpy(actor.actor.object+0xd0,&blocked,4);
 assert(mu_monster_audio_combat(c,0,0,210)==210);mu_session_audio_drain(s,&cursor,host);
 blocked=0;memcpy(actor.actor.object+0xd0,&blocked,4);
 actor.actor.object[0x2a]=6;c->monsters[0].voice_3324=0;mu_monster_audio_die_complete(c,0);
 assert(c->monsters[0].voice_3324==.001f && mu_actor_frame(&actor.actor)==0.0f);
 c->monsters[0].voice_3324=0;actor.actor.object[0x2a]=5;
 /* Distance consumes the class dispatch. Combat still continues to its shared
  * voice, because these callers discard the dispatch return value. */
 actor.position[0]=500.01f;assert(mu_monster_audio_combat(c,0,0,210)==210);
 actor.position[0]=500;actor.actor.object[0x2a]=3;assert(mu_monster_audio_combat(c,0,0,210)==210);
 actor.actor.object[0x2a]=0;assert(mu_monster_audio_combat(c,0,0,210)==210);
 /* SetPlayerWalk/MoveCharacter sound gates use their actual action/frame;
  * walking requests recur at eligible frames, rather than at frame zero only. */
 map.world=142;actor.actor.spec.model_index=2400;actor.actor.object[0x2a]=2;
 float f=1.5f;memcpy(actor.actor.object+0xd0,&f,4);mu_rp_character record={0};record.live=1;record.movement=1;
 mu_monster_audio_motion(detached?NULL:s,&walk,&actor,&record);mu_session_audio_drain(s,&cursor,host);
 actor.actor.bmd.action_count=2;mu_monster_audio_motion(detached?NULL:s,&walk,&actor,&record);mu_session_audio_drain(s,&cursor,host);
 record.movement=0;mu_monster_audio_motion(detached?NULL:s,&walk,&actor,&record);
 mu_monster_audio_tick(detached?NULL:s,&walk,&actor);mu_session_audio_drain(s,&cursor,host);
 float pcm[320];mu_audio_engine_mix(mu_audio_host_engine(saved),pcm,160);int nonzero=0;
 for(int n=0;n<320;++n)nonzero+=pcm[n]!=0;
 if(disabled||muted||detached)assert(!nonzero);else assert(nonzero);
 free(c);free(s);mu_audio_host_free(saved);mu_audio_table_free(&table);return 0;
}
'''
class Native(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  subprocess.run(['make','-s','-j4','-C',str(ROOT/'native'),'audio','build/mu-session'],check=True)
  cls.temp=tempfile.TemporaryDirectory(prefix='audio-005-native-');cls.folder=Path(cls.temp.name)
  src=cls.folder/'host.c';src.write_text(HARNESS);obj=cls.folder/'host.o';cls.exe=cls.folder/'host'
  subprocess.run(['clang','-std=c11','-DMU_SESSION_SEED','-I',str(ROOT/'native'),'-I',str(ROOT/'native/session'),'-I',str(ROOT/'native/build/gen'),'-I',str(ROOT/'reconstructed/objects'),'-c',str(src),'-o',str(obj)],check=True)
  cmd=['clang++',str(obj),str(ROOT/'native/build/libmusession.a'),str(ROOT/'native/build/libmunative.a'),str(ROOT/'native/build/libmuaudio.a'),'-lm','-o',str(cls.exe)]
  for lib in ('cryptopp','jpeg-turbo'):
   prefix=subprocess.check_output(['brew','--prefix',lib],text=True).strip() if shutil.which('brew') else '/usr'
   cmd+=['-L'+prefix+'/lib','-l'+('cryptopp' if lib=='cryptopp' else 'jpeg')]
  if sys.platform=='darwin':
   for f in ('CoreText','CoreGraphics','CoreFoundation','AudioToolbox'):cmd+=['-framework',f]
  subprocess.run(cmd,check=True)
  wav=cls.folder/'sound.wav';wav.write_bytes(constant_wav(.125,800,rate=8000));cls.table=cls.folder/'table.tsv'
  cls.table.write_text(''.join(f'sound\t{id}\t{wav}\t1\t0\t0\n' for id in (1385,973)))
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def run_host(self,mode):
  log=self.folder/(mode+'.jsonl');run=subprocess.run([str(self.exe),str(self.table),mode],capture_output=True,text=True,env=dict(os.environ,MU_AUDIO_CUE_LOG=str(log)),cwd=ROOT)
  self.assertEqual(run.returncode,0,run.stdout+run.stderr)
  return [json.loads(s) for s in log.read_text().splitlines() if json.loads(s)['op']=='play']
 def test_provenance_order_trigger_and_suppression(self):
  rows=self.run_host('normal');self.assertEqual([r['site'] for r in rows],[0xe0807b,0xe0807b,0xe6b31e]);self.assertEqual([r['result'] for r in rows],[1,0,1]);self.assertEqual([r['at_key'] for r in rows], [7,7,-2])
 def test_muted(self):self.assertEqual(len(self.run_host('muted')),3)
 def test_disabled_drain(self):self.assertEqual(self.run_host('disabled'),[])
 def test_detached_no_replay(self):self.assertEqual(self.run_host('detached'),[])

from contextlib import contextmanager
from unittest.mock import patch
@contextmanager
def patch_builder(harness):
 class Host: pass
 host=Host()
 with patch.dict(globals(),{'HARNESS':harness}):Native.setUpClass.__func__(Host)
 try:yield Host
 finally:Host.temp.cleanup()


class Installed(unittest.TestCase):
 @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','Installed actor/audio inputs are opt-in')
 def test_all_admitted_models_load_and_sounds_decode(self):
  import re
  rows=re.findall(r'MU_AUDIO_MONSTER_SOUND\(0x[0-9a-f]+u, (\d+), .*?, 0x[0-9a-f]+u, (\d+), \d+, \d+\)',(ROOT/'reconstructed/audio/monster_audio_table.inc').read_text())
  models=sorted({int(m) for m,_ in rows if 0x7a5<=int(m)<0x9fe});ids=sorted({int(i) for m,i in rows if 0x7a5<=int(m)<0x9fe}|{0x4f1,0x4f2,0x4f3,0x4f4})
  self.assertGreater(len(models),57)
  # Use the existing BY_MONSTER loader. These later world models are not in
  # the generic world-0 server-class table, so no class construction is claimed.
  harness=r'''#include "core/mu_actor.h"
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
int main(int argc,char **argv){assert(argc==2);int models[]={MODELS};char error[512];int bad=0;
 for(unsigned k=0;k<sizeof models/sizeof models[0];++k){mu_actor_spec spec;mu_model_params p;mu_model_scene_params(&p);
  if(mu_actor_resolve(argv[1],MU_ACTOR_BY_MONSTER,models[k]-0x7a5,&spec,error,sizeof error)){if(models[k]==0x90a||models[k]==0x90b||models[k]==0x90c)continue;fprintf(stderr,"resolve model %#x failed\n",models[k]);++bad;continue;}
  mu_actor *a=calloc(1,sizeof *a);assert(a);assert(!mu_actor_load(a,&spec,&p,1,error,sizeof error));
  assert(a->loaded && a->spec.model_index==models[k]);mu_actor_free(a);free(a);}
 return bad?1:0;}'''.replace('MODELS',','.join(map(str,models)))
  with patch_builder(harness) as built:
   r=subprocess.run([str(built.exe),os.environ['MU_GAME_ROOT']],capture_output=True,text=True,cwd=ROOT);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   script=built.folder/'installed.txt';script.write_text(''.join(f'0 play {id} 0\n' for id in ids)+'80 end\n');log=built.folder/'installed.jsonl'
   r=subprocess.run([str(ROOT/'native/build/mu-audio'),'render','--table',str(Path(os.environ['MU_NATIVE_DATA_DIR'])/'sound/audio-tables.tsv'),'--root',os.environ['MU_GAME_ROOT'],'--script',str(script),'--out',str(built.folder/'audio.wav'),'--no-options'],capture_output=True,text=True,env=dict(os.environ,MU_AUDIO_CUE_LOG=str(log)),cwd=ROOT)
   self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertGreater(json.loads(r.stdout)['peak'],0)
   plays=[json.loads(line) for line in log.read_text().splitlines() if json.loads(line)['op']=='play'];self.assertEqual([r['id'] for r in plays],ids);self.assertTrue(all(r['result']==1 for r in plays))


class Original(unittest.TestCase):
 @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','Pinned AUDIO-005 inputs are opt-in')
 def test_whole_table(self):
  with tempfile.TemporaryDirectory(prefix='audio-005-proof-') as tmp:
   subprocess.run([sys.executable,str(ROOT/'scripts/validate_audio_monsters.py'),'--cases','1000','--report',str(Path(tmp)/'report.json')],cwd=ROOT,check=True,capture_output=True)
if __name__=='__main__':unittest.main()
