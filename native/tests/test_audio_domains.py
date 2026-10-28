"""AUDIO-002D: session inputs -> cue ring -> independent audio cursor/log."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_native_skill import write_lang, write_master
from test_native_audio import constant_wav
NATIVE=Path(__file__).resolve().parents[1]
HARNESS=r'''
#include "session/mu_session_seed.h"
#include "fixture/mu_fixture.h"
#include "core/mu_session_audio.h"
#include "core/mu_lang.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(int argc,char **argv) {
    assert(argc==6);char error[512];
    mu_fixture_options opt={argv[1],NULL,20024};
    mu_fixture *fx=mu_fixture_open(&opt,error,sizeof error);assert(fx);
    mu_transport *tr=mu_fixture_transport(fx);mu_session_config cfg={0};cfg.transport=tr;
    mu_fixture_endpoint(fx,"game",&cfg.connect_server);mu_session_seed seed={0};seed.class_byte=129;
    mu_session *s=mu_session_open_seeded(&cfg,&seed,error,sizeof error);assert(s);
    mu_lang *lang=mu_lang_load(argv[2]);assert(lang);
    assert(!mu_session_skills_bind(s,lang,argv[2],argv[2]));
    mu_skill_book *book=mu_session_skills(s);mu_skill_book_master_build(book);
    mu_audio_table table;assert(!mu_audio_table_load(argv[3],&table,error,sizeof error));
    mu_audio_host_config ac={0};ac.table=&table;ac.skip_options=1;ac.engine.game_root="/";
    mu_audio_host *host=mu_audio_host_new(&ac,error,sizeof error);assert(host);
    mu_cue_cursor audio={0},view={0};
    for(unsigned tick=1;tick<=10;++tick) {
        mu_transport_poll(tr,tick*40);mu_session_pump(s,tick*40);
        if(!strcmp(argv[4],"npc")) {
            mu_characters_view v=mu_session_characters(s);int i=mu_session_character_index(s,0x400);
            if(i>=0) {
                assert(v.records[i].model==0xa01);
                mu_session_npc_viewport_voice(s,v.records[i].model,0,0,7,0,&v.monsters[i]);
            }
            if(tick==7)assert(i<0);
        } else if(tick==2) {
            mu_master_env *env=mu_skill_book_master_env(book);
            env->points=0;
            assert(!mu_master_click(mu_skill_book_master(book),env,mu_skill_book_hero(book),255));
            assert(!mu_master_click(mu_skill_book_master(book),env,mu_skill_book_hero(book),1));
            /* A request is not a click and must not acquire a second sound. */
            mu_intent in={.kind=MU_INTENT_SKILL_MASTER_LEARN};in.u.skill_master_learn.skill=330;
            mu_session_submit(s,&in);
        }
        mu_session_audio_drain(s,&audio,!strcmp(argv[5],"silent")?NULL:host);
        mu_session_audio_drain(s,&audio,host);
    }
    mu_cue cues[128];uint32_t lost=0;size_t n=mu_session_cues(s,&view,cues,128,&lost);assert(!lost);
    unsigned sounds=0,windows=0,missing=0;
    for(size_t i=0;i<n;++i) {sounds+=cues[i].kind==MU_CUE_SOUND;windows+=cues[i].kind==MU_CUE_WINDOW;missing+=cues[i].kind==MU_CUE_AUDIO_INPUT;}
    printf("{\"sounds\":%u,\"windows\":%u,\"missing\":%u,\"voices\":%d}\n",sounds,windows,missing,mu_audio_engine_active_voices(mu_audio_host_engine(host)));
    mu_audio_host_free(host);mu_audio_table_free(&table);mu_session_close(s);mu_lang_free(lang);
    mu_transport_free(tr);mu_fixture_close(fx);return 0;
}
'''
class DomainAudio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-C',str(NATIVE),'build/mu-session','build/mu-walk'],check=True,capture_output=True)
        cls.tmp=tempfile.TemporaryDirectory(prefix='audio-domains-route-');cls.folder=Path(cls.tmp.name)
        cls.lang=cls.folder/'lang';write_lang(cls.lang);write_master(cls.lang)
        src=cls.folder/'host.c';src.write_text(HARNESS);cls.host=cls.folder/'host'
        frameworks=['-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation','-framework','AudioToolbox'] if sys.platform=='darwin' else []
        subprocess.run(['cc','-std=c11','-DMU_SESSION_SEED','-I',str(NATIVE),'-I',str(NATIVE/'session'),'-I',str(NATIVE/'build/gen'),
                        str(src),str(NATIVE/'build/libmusession.a'),str(NATIVE/'build/libmunative.a'),str(NATIVE/'build/libmuaudio.a'),*frameworks,'-lm','-o',str(cls.host)],check=True)
        wav=cls.folder/'sound.wav';wav.write_bytes(constant_wav(.125,8000))
        cls.table=cls.folder/'sounds.tsv';cls.table.write_text(''.join(f'sound\t{id}\t{wav}\t1\t1\t0\t0\n' for id in [25,160]))
        # Complete viewport snapshots, a destroy, and key reuse. No new fixture behavior.
        def packet(buffs):
            import struct
            record=bytearray(28+8*len(buffs));record[:4]=bytes.fromhex('04 00 00 fb')
            record[4:8]=bytes([120]*4);record[26]=len(buffs)
            for i,id in enumerate(buffs):struct.pack_into('<H',record,28+8*i,id)
            size=5+len(record);return bytes([0xc2,size>>8,size&255,0x13,1])+record
        cls.scenario=cls.folder/'route.scn'
        cls.scenario.write_text('endpoint game 127.0.0.1:55905\nuse skills\n'+
            '\n'.join(f'at {t} send game {packet(b).hex(" ")}' for t,b in [(1,[]),(3,[27]),(5,[])])+
            '\nat 7 send game c1 06 14 01 04 00\n'+f'at 8 send game {packet([27]).hex(" ")}\n')
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def drive(self,kind,silent=False):
        log=self.folder/f'{kind}-{silent}.jsonl';log.unlink(missing_ok=True)
        p=subprocess.run([str(self.host),str(self.scenario),str(self.lang),str(self.table),kind,'silent' if silent else 'on'],capture_output=True,text=True,
                         env={**os.environ,'MU_AUDIO_CUE_LOG':str(log)})
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        return json.loads(p.stdout),[r for r in map(json.loads,log.read_text().splitlines()) if r['op']=='play' and r['handler']]
    def test_viewport_absent_present_replace_destroy_and_reuse(self):
        report,rows=self.drive('npc')
        self.assertEqual((report['sounds'],report['missing']),(4,0))
        self.assertEqual(len(rows),4)
        self.assertEqual({(r['handler'],r['site'],r['id'],r['at_key']) for r in rows},{(0x13b23f8,0x13b5494,160,-2)})
        self.assertEqual([r['session_tick'] for r in rows],[1,2,5,6])
        self.assertEqual(len({r['cue_seq'] for r in rows}),4)
    def test_master_click_before_failed_check_and_request_is_silent(self):
        report,rows=self.drive('master')
        self.assertEqual((report['sounds'],report['missing']),(1,0));self.assertGreater(report['windows'],0)
        self.assertEqual([(r['handler'],r['site'],r['id'],r['at_key']) for r in rows],[(0xbb22e1,0xbb23d1,25,-2)])
    def test_silent_reader_does_not_replay_and_second_session_is_independent(self):
        report,rows=self.drive('npc',True);self.assertEqual(report['sounds'],4);self.assertEqual(report['voices'],0);self.assertEqual(rows,[])
        _,rows=self.drive('npc');self.assertEqual(len(rows),4)
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','Pinned audio domain instructions are opt-in')
    def test_original_domain_audio(self):
        report=self.folder/'original.json'
        p=subprocess.run([sys.executable,str(NATIVE.parent/'scripts/validate_audio_domains.py'),'--cases','600','--mutations','--report',str(report)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        data=json.loads(report.read_text());self.assertEqual(data['cases'],2544);self.assertEqual(data['mismatches'],0)
        self.assertEqual(len(data['mutants']),7);self.assertTrue(all(v=='caught' for v in data['mutants'].values()))
        self.assertEqual(len(data['quest_static']),24)
if __name__=='__main__':unittest.main()
