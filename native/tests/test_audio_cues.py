"""AUDIO-002: real hero handler -> ring -> independent audio reader -> PCM/log."""
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_native_audio import constant_wav
NATIVE=Path(__file__).resolve().parents[1]
HARNESS=r'''
#include "session/session_internal.h"
#include "session/domains/audio_cue.h"
#include "core/mu_session_audio.h"
#include "core/mu_world_audio.h"
#include "core/mu_objects.h"
#include "core/mu_world_players.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
mu_apply hero_levelup(mu_session *, const mu_frame *);
static void foot_cue(void *s, uint32_t site, int32_t id) {
    mu_session_sound_emit(s,0x13b1f61,site,id,-2,0);
}
static void object_cue(void *s, int32_t id) {
    assert(mu_session_object_sound(s,id));
}
int main(int argc, char **argv) {
    assert(argc == 3);
    mu_audio_table table;
    char error[256];
    assert(mu_audio_table_load(argv[1], &table, error, sizeof error) == 0);
    mu_audio_host_config cfg = {0}; cfg.table=&table; cfg.skip_options=1; cfg.engine.game_root="/";
    mu_audio_host *h=mu_audio_host_new(&cfg,error,sizeof error);
    if (!h) { fprintf(stderr,"%s\n",error); return 2; }
    mu_session *s=calloc(1,sizeof *s); assert(s); mu_dom_hero_init(s); s->tick=7;
    mu_cue_cursor audio={0},view={0};
    if (!strcmp(argv[2],"route")) {
        uint8_t bytes[32]={0xc1,24,0xa0,6,2}; mu_frame f={0}; memcpy(f.bytes,bytes,sizeof bytes);
        s->route.client_handler=0x1250b05; hero_levelup(s,&f);
        s->route.client_handler=0xbe906d;
        assert(mu_domain_sound_cue(s,"call 00a6ac96 99 o 1"));
        assert(!mu_domain_sound_cue(s,"call 00a6ac96 99"));
        assert(!mu_domain_sound_cue(s,"invoke quest hello"));
        mu_session_audio_drain(s,&audio,h); mu_session_audio_drain(s,&audio,h);
        mu_cue cues[64]; uint32_t lost=0; size_t n=mu_session_cues(s,&view,cues,64,&lost);
        unsigned sounds=0; for(size_t i=0;i<n;i++) sounds+=cues[i].kind==MU_CUE_SOUND;
        assert(sounds==2 && !lost);
        assert(mu_audio_engine_active_voices(mu_audio_host_engine(h))==2);
        float pcm[2];mu_audio_engine_mix(mu_audio_host_engine(h),pcm,1);
        assert(pcm[0]==0.375f && pcm[1]==0.375f);
    } else if (!strcmp(argv[2],"remote_combat")) {
        mu_world_players *p=calloc(1,sizeof *p);assert(p);
        mu_world map={0};p->map=&map;p->session=s;p->count=1;p->rng=123;
        mu_world_player *q=&p->list[0];q->key=q->c.key=0x200;q->in_view=1;
        q->c.model=0xa91;q->c.slots[MU_RP_SLOT_WEAPON0].type=0xae6;
        q->c.slots[MU_RP_SLOT_WEAPON1].type=-1;
        s->combat.next=4;
        s->combat.events[0]=(mu_combat_frame_event){.kind=3,.key=0x200};
        s->combat.events[1]=(mu_combat_frame_event){.kind=1,.key=0x200,.damage={.shock=1,.amount=10}};
        s->combat.events[2]=(mu_combat_frame_event){.kind=1,.key=0x200,.damage={.shock=0,.amount=10}};
        s->combat.events[3]=(mu_combat_frame_event){.kind=2,.key=0x200};
        mu_world_players_combat_audio(p);mu_world_players_combat_audio(p);
        assert(p->rng==123 && q->c.action==0 && q->c.hp==0 && p->audio_receive_cursor==4);
        q->c.transformed=1;s->combat.next=5;
        s->combat.events[4]=(mu_combat_frame_event){.kind=3,.key=0x200};
        mu_world_players_combat_audio(p);
        mu_session_audio_drain(s,&audio,h);mu_session_audio_drain(s,&audio,h);
        mu_cue cues[8];uint32_t lost=0;assert(mu_session_cues(s,&view,cues,8,&lost)==3 && !lost);
        assert(cues[0].kind==MU_CUE_SOUND && cues[1].kind==MU_CUE_SOUND && cues[2].kind==MU_CUE_AUDIO_INPUT);
        free(p);
    } else if (!strcmp(argv[2],"ambient")) {
        int ids[]={12,13,14,138,15};
        for (int i=0;i<5;++i) assert(mu_session_ambient_sound(s,ids[i]));
        assert(!mu_session_ambient_sound(s,9999));
        mu_session_audio_drain(s,&audio,h);mu_session_audio_drain(s,&audio,h);
    } else if (!strcmp(argv[2],"objects")) {
        mu_objects objects; mu_objects_init(&objects,0x8d);
        objects.count=1; objects.records=calloc(1,sizeof *objects.records); assert(objects.records);
        objects.records[0].type=6; objects.records[0].scale=1;
        objects.records[0].position[0]=12000;objects.records[0].position[1]=12000;
        objects.models[6]=calloc(1,sizeof *objects.models[6]);assert(objects.models[6]);
        objects.models[6]->loaded=1;
        assert(!mu_objects_start(&objects,NULL));
        objects.sound=object_cue;objects.sound_context=s;
        memset(objects.rt.world.block_visible,1,sizeof objects.rt.world.block_visible);
        objects.rt.images[MU_OBJF_LIVE]=1; objects.rt.images[MU_OBJF_VISIBLE]=1;
        mu_obj_set_f32(objects.rt.images,MU_OBJF_ALPHA,1);
        mu_obj_set_f32(objects.rt.images,MU_OBJF_ALPHA_TARGET,1);
        mu_objects_step_inputs in={0};in.scene_state=6;in.hero[0]=12000;in.hero[1]=12000;
        mu_objects_step(&objects,&in);
        assert(objects.rt.sound_events==1);
        assert(mu_audio_engine_active_voices(mu_audio_host_engine(h))==0);
        mu_session_audio_drain(s,&audio,h); mu_session_audio_drain(s,&audio,h);
        in.hero[0]=20000;mu_objects_step(&objects,&in);
        mu_session_audio_drain(s,&audio,h);
        assert(objects.rt.sound_events==1);
        mu_objects_free(&objects);
    } else if (!strcmp(argv[2],"foot")) {
        mu_world_sound sound={0};sound.world=0;sound.host=h;sound.sound_cue=foot_cue;sound.sound_context=s;
        mu_world_sound_hero hero={{12000,12000},{120,120},0x32,5,1,0,0xa91};
        uint8_t *layer=calloc(65536,1);uint16_t *attr=calloc(65536,sizeof *attr);assert(layer && attr);
        assert(mu_world_sound_hero_step(&sound,&hero,layer,attr)==9);
        assert(mu_audio_engine_active_voices(mu_audio_host_engine(h))==0);
        assert(sound.footsteps==2);
        mu_session_audio_drain(s,&audio,h);mu_session_audio_drain(s,&audio,h);
        free(layer);free(attr);
    } else if (!strcmp(argv[2],"npc")) {
        mu_session_npc_voice(s,0xa0b,64,0,0,-1);
        mu_session_npc_voice(s,0xa0b,63,0,0,-1);
        mu_session_npc_voice(s,0xa06,-256,0,0,-1);
        mu_session_npc_voice(s,0xa01,0,0,7,-1);
        mu_session_npc_voice(s,0xa01,0,0,7,1);
        mu_session_npc_voice(s,0xa01,0,0,7,0);
        mu_session_npc_voice(s,0xa91,0,0,7,0);
        mu_session_npc_talk_sound(s,25); mu_session_npc_talk_sound(s,28);
        mu_session_audio_drain(s,&audio,h); mu_session_audio_drain(s,&audio,h);
        mu_cue cues[32]; uint32_t lost=0;
        assert(mu_session_cues(s,&view,cues,32,&lost)==6 && !lost);
        assert(mu_session_rev(s,MU_DOMAIN_CHARACTERS)==0);
    } else if (!strcmp(argv[2],"model_cache")) {
        mu_audio_host_register_actor(h,-1,0xa06);
        mu_audio_host_register_actor(h,-1,0xa01);
        mu_audio_host_register_actor(h,-1,0xa06);
        mu_audio_host_register_actor(h,-1,0xa01);
        assert(mu_audio_host_play(h,160,0));
        float pcm[2]; mu_audio_engine_mix(mu_audio_host_engine(h),pcm,1); assert(pcm[0]==0.25f);
    } else if (!strcmp(argv[2],"loss")) {
        for(int i=0;i<1050;i++) assert(mu_domain_sound_cue(s,"call 00a6ac96 98 0 0"));
        mu_session_audio_drain(s,&audio,h); mu_session_audio_drain(s,&audio,h);
    } else if (!strcmp(argv[2],"silent")) {
        assert(mu_domain_sound_cue(s,"call 00a6ac96 98 0 0"));
        mu_session_audio_drain(s,&audio,NULL); mu_session_audio_drain(s,&audio,h);
    } else if (!strcmp(argv[2],"registration")) {
        assert(!mu_audio_host_register_npc(h,0xa06,0));
        assert(!mu_audio_host_register_npc(h,0xa01,0));
        assert(mu_audio_host_play(h,160,0));
        float pcm[2];mu_audio_engine_mix(mu_audio_host_engine(h),pcm,1);
        assert(pcm[0]==0.25f); /* first registered site, despite reversed TSV order */
    } else if (!strcmp(argv[2],"hosts")) {
        mu_audio_host *other=mu_audio_host_new(&cfg,error,sizeof error);assert(other);
        mu_audio_host_play(h,152,0);mu_audio_host_play(other,152,0);
        mu_audio_host_free(other);mu_audio_host_play(h,153,0);
    } else if (!strcmp(argv[2],"literal")) {
        mu_audio_host_music_literal(h,table.rows[0].path,1234,1);
        assert(mu_audio_engine_active_voices(mu_audio_host_engine(h))==1);
        mu_audio_host_music_literal(h,table.rows[0].path,1234,0);
        assert(mu_audio_engine_active_voices(mu_audio_host_engine(h))==0);
    } else if (!strcmp(argv[2],"event")) {
        mu_world_audio_state w={0}; w.scene=6;w.world=39;
        mu_audio_host_set_world(h,&w,0);mu_audio_host_tick(h);
        mu_event_music_state e={0};e.known=MU_AUDIO_KANTURU;e.kanturu=3;
        mu_audio_host_set_event_music(h,&e);mu_audio_host_tick(h);
        w.world=0;mu_audio_host_set_world(h,&w,0);mu_audio_host_tick(h);
        w.world=39;mu_audio_host_set_world(h,&w,0);mu_audio_host_tick(h);
    }
    mu_dom_hero_free(s);free(s);mu_audio_host_free(h);mu_audio_table_free(&table);return 0;
}
'''
class AudioCues(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-C',str(NATIVE),'audio','build/mu-session'],check=True)
        cls.tmp=tempfile.TemporaryDirectory(prefix='audio-cues-'); cls.folder=Path(cls.tmp.name)
        src=cls.folder/'test.c'; src.write_text(HARNESS)
        obj=cls.folder/'test.o';cls.exe=cls.folder/'test'
        subprocess.run(['clang','-std=c11','-DMU_SESSION_SEED','-I',str(NATIVE),'-I',str(NATIVE/'build/gen'),'-I',str(NATIVE/'session'),'-c',str(src),'-o',str(obj)],check=True)
        cmd=['clang++',str(obj),str(NATIVE/'build/libmusession.a'),str(NATIVE/'build/libmunative.a'),str(NATIVE/'build/libmuaudio.a'),*(['-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation'] if sys.platform=='darwin' else []),'-lm','-o',str(cls.exe)]
        crypto_prefix = subprocess.check_output(['brew','--prefix','cryptopp'],text=True).strip() if shutil.which('brew') else '/usr'
        cmd += ['-L'+crypto_prefix+'/lib','-lcryptopp']
        jpeg_prefix = '/usr'
        if shutil.which('brew'):
            jpeg = subprocess.run(['brew','--prefix','jpeg-turbo'],capture_output=True,text=True)
            if jpeg.returncode == 0: jpeg_prefix = jpeg.stdout.strip()
        if (Path(jpeg_prefix)/'include/jpeglib.h').exists(): cmd += ['-L'+jpeg_prefix+'/lib','-ljpeg']
        if sys.platform=='darwin':cmd+=['-framework','AudioToolbox','-framework','CoreFoundation']
        subprocess.run(cmd,check=True)
        for name,value in [('a',.125),('b',.25)]: (cls.folder/(name+'.wav')).write_bytes(constant_wav(value,8000))
        cls.table=cls.folder/'table.tsv'
        cls.table.write_text(''.join(f'sound\t{id}\t{cls.folder/name}\t1\t1\t0\t{site}\n' for id,name,site in
                           [(152,'a.wav',0),(153,'b.wav',0),(160,'a.wav',0x1808e5a),(160,'b.wav',0x1808f26)]))
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def run_case(self,name):
        log=self.folder/(name+'.jsonl');log.unlink(missing_ok=True)
        r=subprocess.run([str(self.exe),str(self.table),name],capture_output=True,text=True,env=dict(os.environ,MU_AUDIO_CUE_LOG=str(log)))
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        rows=[json.loads(line) for line in log.read_text().splitlines()]
        for host in {r['host'] for r in rows}:
            stream=[r for r in rows if r['host']==host]
            self.assertEqual([r['seq'] for r in stream],list(range(len(stream))))
        self.assertTrue(all(r['audio']==1 for r in rows));return rows
    def test_hero_ring_and_shared_domain_adapter_play_once(self):
        plays=[r for r in self.run_case('route') if r['op']=='play']
        self.assertEqual([(r['id'],r['loop'],r['handler'],r['at_key'],r['session_tick']) for r in plays],[(152,0,0x1250b05,-2,7),(153,1,0xbe906d,-1,7)])
        self.assertLess(plays[0]['cue_seq'],plays[1]['cue_seq'])
    def test_remote_combat_reads_results_once_and_preserves_visual_state(self):
        rows=self.run_case('remote_combat');plays=[r for r in rows if r['op']=='play']
        self.assertEqual([r['site'] for r in plays],[0x1393a3f,0x138fcf5])
        self.assertTrue(all(r['at_key']==0x200 and r['session_tick']==7 for r in plays))
        missing=[r for r in rows if r['op']=='unrecovered']
        self.assertEqual([(r['handler'],r['site'],r['id']) for r in missing],[(0x1392bde,0x139389a,0x139f3db)])
    def test_environment_cues_keep_all_five_sites(self):
        rows=[r for r in self.run_case('ambient') if r['op']=='play']
        self.assertEqual([(r['id'],r['site'],r['at_key']) for r in rows],
                         [(12,0xc9fcd5,-3),(13,0xc9fcfb,-3),(14,0xc9fd2f,-3),(138,0xc9fd74,-3),(15,0xca1c80,-3)])
        self.assertEqual([r['handler'] for r in rows],[0xc9eb04]*4+[0xca05b3])
    def test_object_runtime_emits_selected_sound_once_and_obeys_distance(self):
        rows=[r for r in self.run_case('objects') if r['op']=='play']
        self.assertEqual([(r['id'],r['handler'],r['site'],r['at_key']) for r in rows],
                         [(0x581,0xe4c95e,0xe4ca6a,-2)])
    def test_native_footsteps_emit_before_audio_reader(self):
        rows=[r for r in self.run_case('foot') if r['op']=='play']
        self.assertEqual([(r['id'],r['handler'],r['site']) for r in rows],[(9,0x13b1f61,0x13b202f)]*2)
        self.assertEqual([r['cue_seq'] for r in rows],[0,1])
    def test_npc_voice_and_talk_use_ring_with_site_and_missing_input(self):
        rows=self.run_case('npc')
        plays=[r for r in rows if r['op']=='play']
        self.assertEqual([(r['id'],r['handler'],r['site'],r['at_key']) for r in plays],
                         [(161,0x13b23f8,0x13b5402,-2),(160,0x13b23f8,0x13b542f,-2),
                          (160,0x13b23f8,0x13b5494,-2),(25,0x1280659,0x12811ca,-2),
                          (28,0x1280659,0x12811d8,-2)])
        missing=[r for r in rows if r['op']=='unrecovered']
        self.assertEqual([(r['id'],r['site'],r['handler']) for r in missing],[(0x1295ade,0x13b5494,0x13b23f8)])
        self.assertEqual([r['cue_seq'] for r in plays],[0,1,3,4,5])
        self.assertTrue(all(r['session_tick']==7 for r in plays+missing))
    def test_model_audio_registration_survives_viewport_cache_rebuild(self):
        rows=self.run_case('model_cache')
        self.assertEqual([(r['id'],r['site']) for r in rows if r['op']=='register'],[(160,0x1808f26),(160,0x1808e5a)])
    def test_loss_and_duplicate_suppression_are_logged(self):
        rows=self.run_case('loss');loss=[r for r in rows if r['op']=='cue_loss'];plays=[r for r in rows if r['op']=='play']
        self.assertEqual([r['id'] for r in loss],[26]);self.assertEqual(len(plays),1024)
        self.assertEqual([r['result'] for r in plays],[1]+[0]*1023)
    def test_silent_reader_does_not_replay_history(self):
        self.assertFalse([r for r in self.run_case('silent') if r['op']=='play'])
    def test_registration_uses_site_and_first_registration(self):self.run_case('registration')
    def test_event_state_is_explicit_and_resets_on_travel(self):
        rows=self.run_case('event');missing=[r for r in rows if r['op']=='unrecovered' and r['id']==0xe8e857]
        self.assertEqual([r['time_ms'] for r in missing],[0,120])
        music=[r['id'] for r in rows if r['op']=='music' and r['time_ms']==40]
        self.assertIn(25,music)
    def test_overlapping_hosts_have_distinct_streams(self):
        rows=self.run_case('hosts')
        hosts={r['host'] for r in rows};self.assertEqual(len(hosts),2)
        for host in hosts:
            self.assertEqual([r['op'] for r in rows if r['host']==host and r['op'] in ['open','close']],['open','close'])
    def test_scene_music_literal_identity_is_logged(self):
        rows=[r for r in self.run_case('literal') if 'music_literal' in r['op']]
        self.assertEqual([(r['op'],r['id']) for r in rows],[('music_literal',1234),('stopmusic_literal',1234)])
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1', 'Pinned audio callers are opt-in')
    def test_original_domain_audio_callers(self):
        report=self.folder/'original.json'
        subprocess.run([sys.executable,str(NATIVE.parent/'scripts/validate_audio_callers.py'),
                        '--mutations','--report',str(report)],check=True,capture_output=True)
        data=json.loads(report.read_text())
        self.assertEqual(data['cases'],5528)
        self.assertEqual(data['mismatches'],0)
        self.assertEqual(len(data['mutants']),18)
        self.assertTrue(all(v=='caught' for v in data['mutants'].values()))
    def test_log_open_failure_is_reported(self):
        r=subprocess.run([str(self.exe),str(self.table),'silent'],capture_output=True,text=True,env=dict(os.environ,MU_AUDIO_CUE_LOG=str(self.folder/'missing/log')))
        self.assertEqual(r.returncode,2);self.assertIn('cannot open audio cue log',r.stderr)
if __name__=='__main__':unittest.main()
