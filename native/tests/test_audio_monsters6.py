"""AUDIO-006: fixture-loaded class owners, delivery and read-only asset smoke."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'native/tests'))
import test_audio_monsters as prior
from test_native_audio import constant_wav

HARNESS=prior.HARNESS.replace('#include "core/mu_monster_audio.h"','#include "core/mu_monster_audio.h"\n#include "core/mu_monster_audio_extra.h"')
HARNESS=HARNESS.replace('int main(','''static int combined(mu_combat *c,int i,float played,int fallback){
 mu_monster_audio_extra_combat(c,i,played);return mu_monster_audio_combat(c,i,played,fallback);
}
int main(''').replace('assert(mu_monster_audio_combat(', 'assert(combined(')
HARNESS=HARNESS.replace('map.world=138','map.world=80').replace('model_index=2374','model_index=0x876')
HARNESS=HARNESS.replace('float pcm[320];','float pcm[320];')

class Native(prior.Native):
 @classmethod
 def setUpClass(cls):
  from unittest.mock import patch
  with patch.object(prior,'HARNESS',HARNESS):super().setUpClass()
  wav=cls.folder/'sound.wav'
  cls.table.write_text(''.join(f'sound\t{id}\t{wav}\t1\t0\t0\n' for id in (0x3c0,0x3be,973)))
 def test_provenance_order_trigger_and_suppression(self):
  rows=self.run_host('normal')
  self.assertEqual([r['site'] for r in rows],[0xe1840b,0xe1840b,0xe183cd,0xe6b31e])
  self.assertEqual([r['result'] for r in rows],[1,0,1,1])
  self.assertEqual([r['at_key'] for r in rows],[-2,-2,-2,-2])
 def test_muted(self):self.assertEqual(len(self.run_host('muted')),4)

class Installed(unittest.TestCase):
 @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','AUDIO-006 installed inputs are opt-in')
 def test_models_and_decoded_sounds(self):
  sys.path.insert(0,str(ROOT/'scripts'))
  import monster_audio_extended as lift
  import pins
  groups,nodes=lift.recover(pins.TEXT.read(),pins.DATA.read())
  models=sorted({r['model'] for g in groups.values() for r in g['rows'] if 0x7a5<=r['model']<0x9fe})
  ids=sorted({s[1] for node in nodes if node[0]=='leaf' for s in node[2]})
  self.assertEqual(len({s[0] for node in nodes if node[0]=='leaf' for s in node[2]}),182)
  harness=r'''#include "core/mu_actor.h"
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
int main(int argc,char **argv){assert(argc==2);int models[]={MODELS};char error[512];
 for(unsigned n=0;n<sizeof models/sizeof models[0];++n){mu_actor_spec spec;mu_model_params p;mu_model_scene_params(&p);
  if(mu_actor_resolve(argv[1],MU_ACTOR_BY_MONSTER,models[n]-0x7a5,&spec,error,sizeof error)){fprintf(stderr,"model %#x: %s\n",models[n],error);return 1;}
  mu_actor *a=calloc(1,sizeof *a);assert(a);assert(!mu_actor_load(a,&spec,&p,1,error,sizeof error));
  assert(a->loaded && a->spec.model_index==models[n]);mu_actor_free(a);free(a);}
 return 0;}'''.replace('MODELS',','.join(map(str,models)))
  with prior.patch_builder(harness) as built:
   run=subprocess.run([str(built.exe),os.environ['MU_GAME_ROOT']],capture_output=True,text=True,cwd=ROOT)
   self.assertEqual(run.returncode,0,run.stdout+run.stderr)
   script=built.folder/'sound.txt';script.write_text(''.join(f'0 play {id} 0\n' for id in ids)+'80 end\n')
   log=built.folder/'audio.jsonl'
   run=subprocess.run([str(ROOT/'native/build/mu-audio'),'render','--table',str(Path(os.environ['MU_NATIVE_DATA_DIR'])/'sound/audio-tables.tsv'),'--root',os.environ['MU_GAME_ROOT'],'--script',str(script),'--out',str(built.folder/'audio.wav'),'--no-options'],capture_output=True,text=True,cwd=ROOT,env=dict(os.environ,MU_AUDIO_CUE_LOG=str(log)))
   self.assertEqual(run.returncode,0,run.stdout+run.stderr);self.assertGreater(json.loads(run.stdout)['peak'],0)
   rows=[json.loads(s) for s in log.read_text().splitlines() if json.loads(s)['op']=='play']
   self.assertEqual([r['id'] for r in rows],ids);self.assertTrue(all(r['result']==1 for r in rows))
   print(f'AUDIO-006 {len(models)} loaded models; {len(ids)} decoded ids')

class Original(unittest.TestCase):
 @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','AUDIO-006 pinned instructions are opt-in')
 def test_whole_table(self):
  with tempfile.TemporaryDirectory(prefix='audio-006-proof-') as tmp:
   subprocess.run([sys.executable,str(ROOT/'scripts/validate_audio_monsters6.py'),'--cases','1000','--report',str(Path(tmp)/'report.json')],cwd=ROOT,check=True,capture_output=True)
if __name__=='__main__':unittest.main()
