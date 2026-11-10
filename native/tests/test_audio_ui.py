"""AUDIO-002G: legacy controller decisions reach the native mixer immediately."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_native_shell import write_root, write_session, stub_library
from test_native_audio import constant_wav

NATIVE = Path(__file__).resolve().parents[1]
HARNESS = r'''
#include "core/mu_ui_audio.h"
#include "core/mu_audio_host.h"
#include "core/mu_charsel_ui.h"
#include "ui_widget.h"
#include "ui_credit.h"
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
static mu_ui_audio delivery;
static mu_audio_host *host;
static mu_ui_ctx ctx;
static mu_ui_credit_win credits;
static int events, calls, nonzero;
static uint32_t tick;
static void sound(void *context, const mu_cue *cue, uint32_t step) {
    assert(context==&calls && step==tick);
    assert(cue->u.sound.id==25 && cue->u.sound.at_key==-2 && !cue->u.sound.loop);
    ++calls; mu_audio_host_cue(host,cue,step);
}
static void sink(void *user,int op,const uint32_t *words,int count,const void *data,size_t size) {
    (void)user;
    mu_ui_audio_event(&delivery,op,words,count,data,size,tick);
    if (op==MU_UI_EVENT) {
        /* The native fixture owns presentation closure only; no request route. */
        if (words[0]==MU_UI_EVENT_HIDE_WINDOW) mu_ui_credit_win_show(&ctx,&credits.win,0);
        ++events;
    }
}
static void mix(mu_audio_host *saved) {
    float pcm[4000]; mu_audio_engine_mix(mu_audio_host_engine(saved),pcm,2000);
    for (int i=0;i<4000;++i) nonzero+=pcm[i]!=0;
    mu_audio_host_tick(saved);
}
static void button(mu_ui_button *b,int down,int up,int x) {
    ctx.input.cursor_x=x;ctx.input.cursor_y=5;ctx.input.lbutton_down=(uint8_t)down;
    ctx.input.lbutton_up=(uint8_t)up;++tick;mu_ui_button_update(&ctx,b,40.);
}
int main(int argc,char **argv) {
    assert(argc==4);char error[512];
    mu_audio_table table;assert(!mu_audio_table_load(argv[2],&table,error,sizeof error));
    mu_audio_host_config config={0};config.table=&table;config.skip_options=1;
    config.engine.game_root=argv[1];config.engine.rate=8000;
    mu_audio_host *saved=mu_audio_host_new(&config,error,sizeof error);assert(saved);
    host=!strcmp(argv[3],"disabled")?NULL:saved;
    int detached=!strcmp(argv[3],"detached");
    int muted=!strcmp(argv[3],"muted");
    if (muted) mu_audio_set_group_mute(mu_audio_host_client(saved),MU_AUDIO_GROUP_EFFECT,1);
    if (!strcmp(argv[3],"controls")) {
        mu_charsel_session *session=calloc(1,sizeof *session);assert(session);
        session->records=calloc(MU_CHARSEL_CHARACTERS,MU_CHARSEL_RECORD);assert(session->records);
        mu_charsel_list_default(&session->list);session->list.count=1;session->selected=0;session->steps=1;
        session->records[MU_CHARSEL_OBJECT+MU_OBJ_LIVE]=1;
        mu_charsel_ui *ui=calloc(1,sizeof *ui);assert(ui);
        assert(!mu_charsel_ui_init(ui,argv[1],640,480,"@box",session,NULL));
        mu_ui_audio_set_sound(&ui->audio,sound,&calls);tick=1;
        for (int i=0;i<4;++i) {
            int x=mu_ui_sprite_x(&ui->win.buttons[i].sprite)+5;
            int y=mu_ui_sprite_y(&ui->win.buttons[i].sprite)+5;
            int before=calls;
            mu_charsel_ui_update(ui,session,x,y,1,0);
            mu_charsel_ui_update(ui,session,x,y,0,0);assert(calls==before);
            mu_charsel_ui_update(ui,session,x,y,0,1);assert(calls==before+1);
            mu_charsel_ui_update(ui,session,x,y,0,1);assert(calls==before+1);mix(saved);
        }
        assert(ui->audio.sequence==4);mu_charsel_ui_free(ui);assert(!ui->audio.sound);
        free(ui);free(session->records);free(session);
        printf("{\"calls\":%d,\"nonzero\":%d,\"sequence\":4}\n",calls,nonzero);
        mu_audio_host_free(saved);mu_audio_table_free(&table);return 0;
    }
    mu_ui_audio_set_sound(&delivery,detached?NULL:sound,&calls);
    mu_ui_state state={0};state.sink=(mu_ui_sink){NULL,sink};mu_ui_state_init(&state,640,480);
    ctx.state=&state;ctx.input.screen_width=640;ctx.input.screen_height=480;
    mu_ui_button b;mu_ui_button_init(&b);
    mu_ui_button_create(&ctx,&b,10,10,-1,1,0,0,0,-1,-1,-1,-1);
    mu_ui_sprite_set_position(&b.sprite,0,0,3);mu_ui_button_show(&b,1);
    button(&b,1,0,5);button(&b,0,0,5);button(&b,0,0,5);
    assert(!delivery.sequence); /* held is silent */
    button(&b,0,1,5);mix(saved);assert(delivery.sequence==1);
    button(&b,0,1,5);assert(delivery.sequence==1); /* consumed release */
    button(&b,1,0,5);button(&b,0,1,20); /* drag outside */
    b.enable=0;button(&b,1,0,5);button(&b,0,1,5);b.enable=1;
    b.active=0;button(&b,1,0,5);button(&b,0,1,5);b.active=1;
    mu_ui_button_show(&b,0);button(&b,1,0,5);button(&b,0,1,5);
    assert(delivery.sequence==1);
    /* A host must honor credits closure. It emits no service answer. */
    const mu_ui_credit_record rows[]={{MU_UI_CREDIT_END,""}};
    const mu_ui_credits records={1,rows};mu_ui_credit_win_init(&credits,&records);
    mu_ui_credit_win_create(&ctx,&credits);++tick;
    mu_ui_credit_win_show(&ctx,&credits.win,1);mix(saved);
    assert(!credits.win.show && delivery.sequence==2 && events==4);
    for (int i=0;i<200;++i) mu_ui_win_update(&ctx,&credits.win,40.);
    assert(delivery.sequence==2 && events==4);
    assert(calls==(detached?0:2));
    /* Legacy unlabelled/foreign requests cannot be assigned guessed provenance. */
    uint32_t id=25;mu_ui_sound_source bad={0x9867e3,0x98689e,0,1};
    assert(!mu_ui_audio_event(&delivery,MU_UI_SOUND,&id,1,NULL,0,tick));
    assert(!mu_ui_audio_event(&delivery,MU_UI_SOUND,&id,1,&bad,sizeof bad,tick));
    bad.loop=0;bad.site++;
    assert(!mu_ui_audio_event(&delivery,MU_UI_SOUND,&id,1,&bad,sizeof bad,tick));
    mu_ui_audio_set_sound(&delivery,NULL,&calls);assert(!delivery.context);
    mu_ui_audio_set_sound(&delivery,sound,&calls);host=saved;
    mu_audio_set_group_mute(mu_audio_host_client(saved),MU_AUDIO_GROUP_EFFECT,0);
    int before=nonzero;mix(saved);assert(nonzero==before); /* no late replay */
    printf("{\"calls\":%d,\"nonzero\":%d,\"sequence\":%llu}\n",calls,nonzero,
           (unsigned long long)delivery.sequence);
    mu_audio_host_free(saved);mu_audio_table_free(&table);return 0;
}
'''


class UIAudio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-j4','-C',str(NATIVE),'all','build/mu-client'],check=True,capture_output=True)
        cls.tmp=tempfile.TemporaryDirectory(prefix='audio-ui-test-')
        cls.folder=Path(cls.tmp.name);cls.root=write_root(cls.folder/'game');cls.session=write_session(cls.folder)
        wav=cls.root/'Data/Sound/click.wav';wav.parent.mkdir(parents=True,exist_ok=True)
        wav.write_bytes(constant_wav(.125,8000));cls.table=cls.folder/'sounds.tsv'
        cls.table.write_text('sound\t25\tData/Sound/click.wav\t1\t1\t0\t0\n')
        source=cls.folder/'host.c';source.write_text(HARNESS);obj=cls.folder/'host.o';cls.host=cls.folder/'host'
        subprocess.run(['cc','-std=c11','-I',str(NATIVE),'-I',str(NATIVE.parent/'reconstructed/ui'),
                        '-c',str(source),'-o',str(obj)],check=True)
        crypto=subprocess.check_output(['brew','--prefix','cryptopp'],text=True).strip()
        jpeg=subprocess.check_output(['brew','--prefix','jpeg-turbo'],text=True).strip()
        subprocess.run(['c++',str(obj),str(NATIVE/'build/libmunative.a'),str(NATIVE/'build/libmuaudio.a'),
                        '-L'+crypto+'/lib','-lcryptopp','-L'+jpeg+'/lib','-ljpeg','-framework','CoreText',
                        '-framework','CoreGraphics','-framework','CoreFoundation','-framework','AudioToolbox',
                        '-lm','-o',str(cls.host)],check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def drive(self,mode,root=None,table=None):
        log=self.folder/(mode+'.jsonl')
        p=subprocess.run([str(self.host),str(root or self.root),str(table or self.table),mode],capture_output=True,
                         text=True,env={**os.environ,'MU_AUDIO_CUE_LOG':str(log)})
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        rows=[r for r in map(json.loads,log.read_text().splitlines()) if r['op']=='play' and r['handler']]
        return json.loads(p.stdout),rows

    def test_press_hold_release_refusals_and_credits_close(self):
        result,rows=self.drive('on')
        self.assertEqual((result['calls'],result['sequence']), (2,2));self.assertGreater(result['nonzero'],0)
        self.assertEqual([r['site'] for r in rows],[0x98689e,0x9d9eed])
        self.assertEqual([r['cue_seq'] for r in rows],[1,2])

    def test_four_native_charsel_controls_use_selected_fixture(self):
        result,rows=self.drive('controls')
        self.assertEqual(result['calls'],4);self.assertGreater(result['nonzero'],0)
        self.assertEqual([r['site'] for r in rows],[0x98689e]*4)

    def test_muted_consumes_without_replay(self):
        result,rows=self.drive('muted');self.assertEqual(result['nonzero'],0);self.assertEqual(len(rows),2)

    def test_disabled_consumes_without_replay(self):
        result,rows=self.drive('disabled');self.assertEqual(result['nonzero'],0);self.assertEqual(rows,[])

    def test_detach_rebind_discards_without_replay(self):
        result,rows=self.drive('detached');self.assertEqual(result['calls'],0);self.assertEqual(rows,[])

    def test_shell_server_and_charsel_buttons(self):
        lib,movies=stub_library(self.folder)
        scripts=[('10:click:group:0 14:click:server:0',2)] + [
            ('10:enter 14:enter 30:click:'+name,0 if name=='connect' else 1)
            for name in ['create','menu','connect','delete']]
        for i,(script,expected) in enumerate(scripts):
            hashes=[]
            for enabled in [True,False]:
                with tempfile.TemporaryDirectory(dir=self.folder) as tmp:
                    out=Path(tmp);log=out/'audio.jsonl'
                    cmd=[str(NATIVE/'build/mu-client'),'--game-root',str(self.root),'--session',str(self.session),
                         '--headless','--backend','soft','--frames','44','--every','10','--width','640','--height','480',
                         '--out-dir',str(out),'--sound-table',str(self.table),'--gfx',str(movies),'--script',script]
                    if not enabled:cmd.append('--no-audio')
                    p=subprocess.run(cmd,capture_output=True,text=True,
                                     env={**os.environ,'MU_AUDIO_CUE_LOG':str(log),'MU_GFX_LIB':str(lib)})
                    self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                    hashes.append([r['sha256'] for r in map(json.loads,[l for l in p.stdout.splitlines()
                                   if l.startswith('{')]) if 'sha256' in r])
                    if enabled:
                        rows=[r for r in map(json.loads,log.read_text().splitlines())
                              if r['op']=='play' and r['handler']==0x9867e3]
                        self.assertEqual(len(rows),expected,(i,rows,p.stdout[-2500:]))
                        self.assertTrue(all(r['site']==0x98689e and r['id']==25 for r in rows))
            self.assertTrue(hashes[0]);self.assertEqual(*hashes)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','Pinned UI instructions are opt-in')
    def test_original_ui_audio(self):
        report=self.folder/'original.json'
        p=subprocess.run([sys.executable,str(NATIVE.parent/'scripts/validate_audio_ui.py'),'--report',str(report)],
                         capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        data=json.loads(report.read_text());self.assertEqual(data['mismatches'],0)
        self.assertEqual(data['families']['button']['cases'],5763)
        self.assertEqual(data['families']['credits']['cases'],40)

    @unittest.skipUnless(os.environ.get('MU_NATIVE_DATA_DIR') and os.environ.get('MU_GAME_ROOT'),
                         'Installed Native Data audio table and game root required')
    def test_installed_click_decodes(self):
        table=Path(os.environ['MU_NATIVE_DATA_DIR'])/'audio/tables/audio-tables.tsv'
        self.assertTrue(table.is_file(),table)
        result,rows=self.drive('on',Path(os.environ['MU_GAME_ROOT']),table)
        self.assertGreater(result['nonzero'],0);self.assertEqual(len(rows),2)
