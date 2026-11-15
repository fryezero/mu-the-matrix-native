"""AUDIO-004: caller-selected commands, independent cursors and silent drains."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
sys.path.insert(0,str(HERE))
from test_native_audio import constant_wav

HARNESS=r'''
#include "session/session_internal.h"
#include "core/mu_session_audio.h"
#include "core/mu_object_audio.h"
#include "worlds_p2.h"
#include "worlds_p_internal.h"
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
static int32_t zero(void *c){(void)c;return 0;}
int main(int argc,char **argv){
 assert(argc==3);char error[512];mu_audio_table table;
 assert(!mu_audio_table_load(argv[1],&table,error,sizeof error));
 mu_audio_host_config cfg={0};cfg.table=&table;cfg.skip_options=1;cfg.engine.game_root="/";cfg.engine.rate=8000;
 mu_audio_host *saved=mu_audio_host_new(&cfg,error,sizeof error);assert(saved);
 int disabled=!strcmp(argv[2],"disabled"),detached=!strcmp(argv[2],"detached"),muted=!strcmp(argv[2],"muted");
 mu_audio_host *host=disabled?NULL:saved;
 if(muted)mu_audio_set_group_mute(mu_audio_host_client(saved),MU_AUDIO_GROUP_EFFECT,1);
 mu_session *session=calloc(1,sizeof *session);assert(session);session->tick=11;
 mu_cue_cursor cursor={0},other={0};
 uint8_t object[MU_OBJ_SIZE]={0};mu_obj_set_i32(object,MU_OBJF_TYPE,177);
 mu_obj_event events[8];mu_obj_log log={0,8,0,events};mu_obj_move_inputs in={0};in.world=138;in.rand_fn=zero;
 /* Two independently drained gates intentionally request the same active id. */
 for(int n=0;n<2;++n){
  mu_obj_set_u16(object,MU_OBJF_ACTION,n?3:1);mu_obj_set_f32(object,MU_OBJF_FRAME,n?28.5f:7.9f);
  log.count=0;assert(mu_ignis_move(object,0,&in,&log));assert(log.count==1);
  assert(events[0].args[14]==(n?0xe05f09u:0xe05eddu));
  assert(mu_object_audio_command_deliver(detached?NULL:session,detached?NULL:host,138,&events[0]));
  if(!detached)mu_session_audio_drain(session,&cursor,host);
 }
 if(disabled || detached)mu_session_audio_drain(session,&cursor,saved); /* cannot replay */
 if(!detached){mu_cue c[8];uint32_t lost;assert(mu_session_cues(session,&other,c,8,&lost)==2 && !lost);}
 /* Exact frame edge is quiet. No annotation may turn a refusal into a play. */
 log.count=0;mu_obj_set_u16(object,MU_OBJF_ACTION,1);mu_obj_set_f32(object,MU_OBJF_FRAME,8);
 assert(!mu_ignis_move(object,0,&in,&log));assert(!log.count);
 /* Kethotum source context is captured before SetAction changes 0 to 1. */
 float speeds[8]={.3f,.3f,.3f,.3f};int16_t keys[8]={8,8,8,8};mu_wp_model model={8,speeds,keys};
 mu_wp_move_inputs wp={0};wp.world=135;wp.model=&model;wp.rand_fn=zero;
 mu_obj_set_i32(object,MU_OBJF_TYPE,0x77);mu_obj_set_u16(object,MU_OBJF_ACTION,0);
 log.count=0;assert(mu_old_kethotum_move(object,0,&wp,&log));assert(mu_obj_u16(object,MU_OBJF_ACTION)==1);
 assert(events[0].args[14]==0xe3aceau);
 assert(mu_object_audio_command_deliver(NULL,host,135,&events[0]));
 /* Metadata and command kinds are mandatory, including on id collisions. */
 mu_cue cue;mu_obj_event bad=events[0];bad.call=0xa6ad76;
 assert(!mu_object_audio_command_cue(135,&bad,&cue));bad=events[0];bad.args[15]=0;
 assert(!mu_object_audio_command_cue(135,&bad,&cue));
 assert(!mu_object_audio_command_cue(136,&events[0],&cue));
 float pcm[320];mu_audio_engine_mix(mu_audio_host_engine(saved),pcm,160);
 int nonzero=0;for(int i=0;i<320;++i)nonzero+=pcm[i]!=0;
 if(disabled || muted)assert(!nonzero);else assert(nonzero);
 printf("%d\n",nonzero);free(session);mu_audio_host_free(saved);mu_audio_table_free(&table);return 0;
}
'''

class ObjectCommands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-s','-j4','-C',str(ROOT/'native'),'audio','build/mu-session'],check=True)
        cls.tmp=tempfile.TemporaryDirectory(prefix='audio-004-native-');cls.folder=Path(cls.tmp.name)
        source=cls.folder/'host.c';source.write_text(HARNESS);obj=cls.folder/'host.o';cls.exe=cls.folder/'host'
        subprocess.run(['clang','-std=c11','-DMU_SESSION_SEED','-I',str(ROOT/'native'),'-I',str(ROOT/'native/session'),
                        '-I',str(ROOT/'native/build/gen'),'-I',str(ROOT/'reconstructed/objects'),'-c',str(source),'-o',str(obj)],check=True)
        command=['clang++',str(obj),str(ROOT/'native/build/libmusession.a'),str(ROOT/'native/build/libmunative.a'),
                 str(ROOT/'native/build/libmuaudio.a'),'-lm','-o',str(cls.exe)]
        for library in ('cryptopp','jpeg-turbo'):
            prefix=subprocess.check_output(['brew','--prefix',library],text=True).strip() if shutil.which('brew') else '/usr'
            command+=['-L'+prefix+'/lib','-l'+('cryptopp' if library=='cryptopp' else 'jpeg')]
        if sys.platform=='darwin':
            for framework in ('CoreText','CoreGraphics','CoreFoundation','AudioToolbox'):command+=['-framework',framework]
        subprocess.run(command,check=True)
        wav=cls.folder/'sound.wav';wav.write_bytes(constant_wav(.125,800,rate=8000));cls.table=cls.folder/'table.tsv'
        cls.table.write_text(''.join(f'sound\t{id}\t{wav}\t1\t0\t0\n' for id in (0x570,0x55b)))
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def run_host(self,mode):
        log=self.folder/(mode+'.jsonl');result=subprocess.run([str(self.exe),str(self.table),mode],capture_output=True,text=True,
            cwd=ROOT,env=dict(os.environ,MU_AUDIO_CUE_LOG=str(log)))
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        return [json.loads(line) for line in log.read_text().splitlines() if json.loads(line)['op']=='play']
    def test_order_provenance_suppression_and_action_transition(self):
        rows=self.run_host('normal');self.assertEqual([r['site'] for r in rows],[0xe05edd,0xe05f09,0xe3acea])
        self.assertEqual([r['result'] for r in rows],[1,0,1]);self.assertEqual([r['at_key'] for r in rows],[-3,-3,-2])
    def test_muted(self):self.assertEqual(len(self.run_host('muted')),3)
    def test_disabled_drains_without_replay(self):self.assertEqual(self.run_host('disabled'),[])
    def test_detached_has_no_backlog(self):self.assertEqual([r['site'] for r in self.run_host('detached')],[0xe3acea])

class WorldCommands(unittest.TestCase):
    def test_actual_object_runtime_preserves_command_and_pixels(self):
        from test_native_npc import write_npc_world, PLACE
        from test_native_terrain import write_world
        from test_native_objects import obj_plain, write_models
        subprocess.run(['make','-s','-j4','-C',str(ROOT/'native'),'build/mu-walk'],check=True)
        with tempfile.TemporaryDirectory(prefix='audio-004-world-') as temp:
            folder=Path(temp);root=write_npc_world(folder/'game')
            placement=folder/'placement.txt';placement.write_text(PLACE)
            for world,typ,sound,site in [(80,0x3a,0x3db,0xe189d8),(122,0xa1,0x4d3,0xe5e270),(135,0x77,0x55b,0xe3acea)]:
                write_world(root,world+1,rgb=world in (122,135));write_models(root,world+1,[f'Object{typ+1}.bmd'])
                objects=folder/f'objects{world}';objects.mkdir()
                (objects/f'EncTerrain{world+1}.plain').write_bytes(obj_plain(world+1,[(typ,12000.,12000.,0.,0.,1.)]))
                wav=root/f'sound{world}.wav';wav.write_bytes(constant_wav(.125,8000,rate=8000))
                table=folder/f'table{world}.tsv';table.write_text(f'sound\t{sound}\t{wav.name}\t1\t0\t0\n')
                hashes=[]
                for enabled in (True,False):
                    tag=f'{world}-{enabled}';log=folder/(tag+'.jsonl')
                    cmd=[str(ROOT/'native/build/mu-walk'),'--game-root',str(root),'--headless','--backend','soft',
                         '--world',str(world),'--placement',str(placement),'--objects-dir',str(objects),
                         '--width','64','--height','64','--frames','24','--every','12','--tile','120,120',
                         '--hero-name','Preview','--out-dir',str(folder/tag),'--sound-table',str(table)]
                    if not enabled:cmd+=['--no-audio']
                    result=subprocess.run(cmd,capture_output=True,text=True,env=dict(os.environ,MU_AUDIO_CUE_LOG=str(log),MU_GFX_PUBLIC_DEMO='1'))
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                    reports=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
                    hashes.append([r['sha256'] for r in reports if 'sha256' in r])
                    if enabled:
                        plays=[json.loads(line) for line in log.read_text().splitlines() if json.loads(line)['op']=='play' and json.loads(line)['site']==site]
                        self.assertTrue(plays,(world,result.stderr))
                        self.assertTrue(all(r['id']==sound and r['cue_seq']>=0 for r in plays))
                        self.assertEqual([r['result'] for r in plays],[1]+[0]*(len(plays)-1))
                self.assertTrue(hashes[0]);self.assertEqual(hashes[0],hashes[1])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','Installed AUDIO-004 decode is opt-in')
    def test_installed_new_ids_decode(self):
        import re
        ids=sorted({int(row,16) for row in re.findall(r'MU_OBJECT_AUDIO_SITE\(\d+, 0x[0-9a-f]+u, 0x[0-9a-f]+u, (0x[0-9a-f]+),',
            (ROOT/'reconstructed/audio/object_audio_sites.inc').read_text())})
        data=os.environ.get('MU_NATIVE_DATA_DIR');game=os.environ.get('MU_GAME_ROOT')
        self.assertTrue(data and game,'Canonical private-env.sh is required')
        subprocess.run(['make','-s','-j4','-C',str(ROOT/'native'),'audio'],check=True)
        with tempfile.TemporaryDirectory(prefix='audio-004-installed-') as temp:
            folder=Path(temp);script=folder/'script.txt';script.write_text(''.join(f'0 play {id} 0\n' for id in ids)+'80 end\n')
            log=folder/'audio.jsonl'
            result=subprocess.run([str(ROOT/'native/build/mu-audio'),'render','--table',str(Path(data)/'sound/audio-tables.tsv'),
                '--root',game,'--script',str(script),'--out',str(folder/'audio.wav'),'--no-options'],capture_output=True,text=True,
                env=dict(os.environ,MU_AUDIO_CUE_LOG=str(log)))
            self.assertEqual(result.returncode,0,result.stderr);self.assertGreater(json.loads(result.stdout)['peak'],0)
            plays=[json.loads(line) for line in log.read_text().splitlines() if json.loads(line)['op']=='play']
            self.assertEqual([r['id'] for r in plays],ids);self.assertTrue(all(r['result']==1 for r in plays))


class Original(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','Pinned AUDIO-004 inputs are opt-in')
    def test_original_commands(self):
        with tempfile.TemporaryDirectory(prefix='audio-004-proof-') as temp:
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_audio_objects4.py'),'--cases','1000','--report',str(Path(temp)/'report.json')],cwd=ROOT,check=True,capture_output=True)

if __name__=='__main__':unittest.main()
