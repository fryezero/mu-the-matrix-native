"""AUDIO-002: real hero handler -> ring -> independent audio reader -> PCM/log."""
import json
import os
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
#include <assert.h>
#include <stdlib.h>
#include <string.h>
mu_apply hero_levelup(mu_session *, const mu_frame *);
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
        cmd=['clang++',str(obj),str(NATIVE/'build/libmusession.a'),str(NATIVE/'build/libmunative.a'),str(NATIVE/'build/libmuaudio.a'),'-lm','-o',str(cls.exe)]
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
    def test_log_open_failure_is_reported(self):
        r=subprocess.run([str(self.exe),str(self.table),'silent'],capture_output=True,text=True,env=dict(os.environ,MU_AUDIO_CUE_LOG=str(self.folder/'missing/log')))
        self.assertEqual(r.returncode,2);self.assertIn('cannot open audio cue log',r.stderr)
if __name__=='__main__':unittest.main()
