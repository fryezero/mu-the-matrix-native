"""AUDIO-003: world-object callers, session delivery, loop PCM and zone music."""
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
ROOT = NATIVE.parent
sys.path.insert(0, str(HERE))
from test_native_audio import constant_wav

HARNESS = r'''
#include "session/session_internal.h"
#include "core/mu_session_audio.h"
#include "core/mu_object_audio.h"
#include "worlds_b.h"
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
int main(int argc,char **argv) {
    assert(argc==3); char error[512]; mu_audio_table table;
    assert(!mu_audio_table_load(argv[1],&table,error,sizeof error));
    mu_audio_host_config cfg={0};cfg.table=&table;cfg.skip_options=1;cfg.engine.game_root="/";cfg.engine.rate=8000;
    mu_audio_host *saved=mu_audio_host_new(&cfg,error,sizeof error);assert(saved);
    mu_audio_host *host=!strcmp(argv[2],"disabled")?NULL:saved;
    mu_session *session=calloc(1,sizeof *session);assert(session);session->tick=7;
    mu_cue_cursor audio={0},other={0};
    int muted=!strcmp(argv[2],"muted");
    if(muted)mu_audio_set_group_mute(mu_audio_host_client(saved),MU_AUDIO_GROUP_EFFECT,1);
    if(!strcmp(argv[2],"all")) {
        const int worlds[]={2,2,51,51,51,51,51,51,51,100,143,143,143,143,143,143};
        const int ids[]={0x12,0x11,0x317,0x318,0x319,0x314,0x316,0x315,0x313,0x442,0x5a6,0x5a9,0x5a7,0x5a8,0x5a4,0x5a5};
        for(int k=0;k<16;++k)assert(mu_object_audio_deliver(session,host,worlds[k],ids[k]));
        assert(!mu_object_audio_deliver(session,host,80,0x5a5));
        assert(!mu_object_audio_deliver(session,host,138,0x570));
        mu_session_audio_drain(session,&audio,host);mu_session_audio_drain(session,&audio,host);
        mu_cue cues[32];uint32_t lost;assert(mu_session_cues(session,&other,cues,32,&lost)==16 && !lost);
    } else if(!strcmp(argv[2],"detached")) {
        assert(mu_object_audio_deliver(NULL,NULL,51,0x317));
        assert(mu_object_audio_deliver(NULL,host,51,0x318));
    } else {
        /* The unchanged caller owns the safe-zone gate. Held ambience requests
         * repeat; SND_Play, rather than the adapter, suppresses an active id. */
        uint8_t object[MU_OBJ_SIZE]={0};mu_obj_set_i32(object,MU_OBJF_TYPE,2);
        mu_obj_event events[8];mu_obj_log log={0,8,0,events};mu_obj_move_inputs in={0};in.world=51;
        in.hero_safe=1;mu_elbeland_move(object,0,&in,&log);assert(log.count==0);
        in.hero_safe=0;
        for(int k=0;k<2;++k) {
            log.count=0;mu_elbeland_move(object,0,&in,&log);assert(log.count==1);
            assert(events[0].call==MU_OBJ_CALL_SOUND && events[0].args[0]==0x317);
            assert(mu_object_audio_deliver(session,host,51,(int32_t)events[0].args[0]));
            mu_session_audio_drain(session,&audio,host);mu_session_audio_drain(session,&audio,host);
        }
        /* Disabled delivery is drained now and cannot replay on attachment. */
        if(!host)mu_session_audio_drain(session,&audio,saved);
    }
    float pcm[4000];mu_audio_engine_mix(mu_audio_host_engine(saved),pcm,2000);
    int nonzero=0;for(int k=0;k<4000;++k)nonzero+=pcm[k]!=0;
    if(!host || muted)assert(!nonzero);
    else {assert(nonzero);if(!strcmp(argv[2],"normal"))assert(pcm[3999]!=0);}
    printf("{\"nonzero\":%d}\n",nonzero);
    free(session);mu_audio_host_free(saved);mu_audio_table_free(&table);return 0;
}
'''


class ObjectAudio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-j4', '-C', str(NATIVE), 'audio', 'build/mu-session'], check=True)
        cls.tmp = tempfile.TemporaryDirectory(prefix='audio-objects-native-')
        cls.folder = Path(cls.tmp.name)
        source = cls.folder/'host.c'; source.write_text(HARNESS)
        obj = cls.folder/'host.o'; cls.exe = cls.folder/'host'
        subprocess.run(['clang', '-std=c11', '-DMU_SESSION_SEED', '-I', str(NATIVE), '-I', str(NATIVE/'session'),
                        '-I', str(NATIVE/'build/gen'), '-I', str(ROOT/'reconstructed/objects'),
                        '-c', str(source), '-o', str(obj)], check=True)
        command = ['clang++', str(obj), str(NATIVE/'build/libmusession.a'), str(NATIVE/'build/libmunative.a'),
                   str(NATIVE/'build/libmuaudio.a'), '-lm', '-o', str(cls.exe)]
        for library in ('cryptopp', 'jpeg-turbo'):
            prefix = subprocess.check_output(['brew', '--prefix', library], text=True).strip() if shutil.which('brew') else '/usr'
            command += ['-L'+prefix+'/lib', '-l'+('cryptopp' if library == 'cryptopp' else 'jpeg')]
        if sys.platform == 'darwin':
            for framework in ('CoreText', 'CoreGraphics', 'CoreFoundation', 'AudioToolbox'):
                command += ['-framework', framework]
        subprocess.run(command, check=True)
        wav = cls.folder/'sound.wav'; wav.write_bytes(constant_wav(.125, 80, rate=8000))
        cls.table = cls.folder/'table.tsv'
        cls.table.write_text(''.join(f'sound\t{id}\t{wav}\t1\t0\t0\n' for id in
            [0x12,0x11,0x317,0x318,0x319,0x314,0x316,0x315,0x313,0x442,0x5a6,0x5a9,0x5a7,0x5a8,0x5a4,0x5a5]))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_host(self, mode):
        log = self.folder/(mode+'.jsonl')
        result = subprocess.run([str(self.exe), str(self.table), mode], capture_output=True, text=True,
                                env=dict(os.environ, MU_AUDIO_CUE_LOG=str(log)))
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        return [json.loads(line) for line in log.read_text().splitlines() if json.loads(line)['op'] == 'play']

    def test_all_sites_keep_order_and_independent_reader(self):
        rows = self.run_host('all')
        self.assertEqual([r['site'] for r in rows], [0x180041b,0x18005be,0xe3425f,0xe3427c,0xe34290,
            0xe342aa,0xe342be,0xe342d8,0xe342ec,0xe6f4a6,0xe0f41b,0xe0f43d,0xe0f465,0xe0f478,0xe0f48b,0xe0f49e])
        self.assertEqual([r['loop'] for r in rows], [0,0]+[1]*7+[0]*7)
        self.assertTrue(all(r['session_tick'] == 7 for r in rows))
        self.assertEqual(len({r['cue_seq'] for r in rows}), 16)
        self.assertTrue(all(r['result'] == 1 for r in rows))

    def test_original_safe_gate_duplicate_suppression_and_loop_pcm(self):
        rows = self.run_host('normal')
        self.assertEqual([r['result'] for r in rows], [1,0])
        self.assertTrue(all(r['loop'] == 1 and r['at_key'] == -3 for r in rows))

    def test_muted_delivery_decodes_silently(self):
        self.assertEqual([r['result'] for r in self.run_host('muted')], [1,0])

    def test_disabled_reader_does_not_replay(self):
        self.assertEqual(self.run_host('disabled'), [])

    def test_detached_standalone_delivery_does_not_replay(self):
        self.assertEqual([r['id'] for r in self.run_host('detached')], [0x318])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'Installed object audio is opt-in')
    def test_installed_added_sounds_decode(self):
        game = os.environ.get('MU_GAME_ROOT')
        data = os.environ.get('MU_NATIVE_DATA_DIR')
        self.assertTrue(game and data, 'Requested smoke needs MU_GAME_ROOT and MU_NATIVE_DATA_DIR')
        table = Path(data)/'sound/audio-tables.tsv'
        self.assertTrue(table.is_file(), 'Requested smoke needs the manifest-bearing audio table')
        ids = [0x12,0x11,0x317,0x318,0x319,0x314,0x316,0x315,0x313,0x442,0x5a6,0x5a9,0x5a7,0x5a8,0x5a4,0x5a5]
        script = self.folder/'installed.txt'
        script.write_text(''.join(f'0 play {id} {int(2 <= n < 9)}\n' for n,id in enumerate(ids)) + '400 end\n')
        log = self.folder/'installed.jsonl'
        command = [str(NATIVE/'build/mu-audio'), 'render', '--table', str(table), '--root', game,
                   '--script', str(script), '--out', str(self.folder/'installed.wav'), '--no-options']
        result = subprocess.run(command, capture_output=True, text=True,
                                env=dict(os.environ, MU_AUDIO_CUE_LOG=str(log)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreater(json.loads(result.stdout)['peak'], 0)
        plays = [json.loads(line) for line in log.read_text().splitlines() if json.loads(line)['op']=='play']
        self.assertEqual([row['id'] for row in plays], ids)
        self.assertTrue(all(row['result']==1 for row in plays))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'Pinned object audio comparison is opt-in')
    def test_original_object_audio(self):
        with tempfile.TemporaryDirectory(prefix='audio-objects-original-') as temp:
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_audio_objects.py'), '--cases', '1000',
                            '--report', str(Path(temp)/'report.json')], cwd=ROOT, check=True, capture_output=True)


class ObjectWorldDelivery(unittest.TestCase):
    def test_actual_world_part_delivers_loop_and_keeps_frames(self):
        from test_native_npc import write_npc_world, PLACE
        from test_native_terrain import write_world
        from test_native_objects import obj_plain, write_models
        subprocess.run(['make','-s','-j4','-C',str(NATIVE),'build/mu-walk'],check=True)
        with tempfile.TemporaryDirectory(prefix='audio-object-world-') as temp:
            folder = Path(temp)
            root = write_npc_world(folder/'game')
            write_world(root,52)
            write_models(root,52,['Object57.bmd'])
            objects = folder/'objects';objects.mkdir()
            (objects/'EncTerrain52.plain').write_bytes(obj_plain(52,[(56,12000.,12000.,0.,0.,1.)]))
            placement = folder/'placement.txt';placement.write_text(PLACE)
            wav = root/'loop.wav';wav.write_bytes(constant_wav(.125,80,rate=8000))
            table = folder/'table.tsv';table.write_text(f'sound\t{0x319}\t{wav.name}\t1\t1\t0\n')
            hashes = []
            for enabled in (True,False):
                tag = 'on' if enabled else 'off';log = folder/(tag+'.jsonl')
                command = [str(NATIVE/'build/mu-walk'),'--game-root',str(root),'--headless','--backend','soft',
                           '--world','51','--placement',str(placement),'--objects-dir',str(objects),
                           '--width','64','--height','64','--frames','24','--every','12','--tile','120,120',
                           '--out-dir',str(folder/tag),'--sound-table',str(table)]
                if not enabled: command += ['--no-audio']
                result = subprocess.run(command,capture_output=True,text=True,
                                        env=dict(os.environ,MU_AUDIO_CUE_LOG=str(log)))
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                reports = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
                hashes.append([row['sha256'] for row in reports if 'sha256' in row])
                if enabled:
                    rows = [json.loads(line) for line in log.read_text().splitlines()]
                    plays = [row for row in rows if row['op']=='play' and row['site']==0xe34290]
                    self.assertGreater(len(plays),1)
                    self.assertTrue(all(row['loop']==1 and row['handler']==0xe34169 and row['cue_seq']>=0 for row in plays))
                    self.assertEqual([row['result'] for row in plays],[1]+[0]*(len(plays)-1))
            self.assertTrue(hashes[0])
            self.assertEqual(hashes[0],hashes[1])


class ZoneMusic(unittest.TestCase):
    def test_static_zones_switch_decode_and_preserve_same_track(self):
        subprocess.run(['make', '-s', '-j4', '-C', str(NATIVE), 'audio'], check=True)
        with tempfile.TemporaryDirectory(prefix='audio-zones-') as temp:
            folder = Path(temp)
            # Distinct authored PCM levels make the resolved track observable.
            tracks = {0: .05, 21: .1, 2: .15, 3: .2, 4: .25, 5: .3, 6: .35, 9: .4, 16: .45, 22: .5}
            table = folder/'table.tsv'
            rows = []
            for index, level in tracks.items():
                path = folder/f'{index}.wav'
                path.write_bytes(constant_wav(level, 80, rate=8000))
                rows.append(f'music\t{index}\t{path.name}\t-\t-\tfixture\n')
            table.write_text(''.join(rows))
            zones = ['0 safe=1 tile=4', '0 safe=1 tile=0', '2 safe=1 x=205 y=13',
                     '2 safe=1 x=204 y=13', '3 safe=1', '1', '7', '4', '33', '37', '5']
            expected = [0,21,2,3,4,5,6,9,16,22,None]
            script = folder/'zones.txt'
            script.write_text(''.join(f'{n*160} openworld {zone.split()[0]}\n{n*160} world {zone}\n'
                                      for n,zone in enumerate(zones)) + f'{len(zones)*160} end\n')
            output = folder/'audio.wav'; log = folder/'audio.jsonl'
            command = [str(NATIVE/'build/mu-audio'), 'render', '--root', str(folder), '--table', str(table),
                       '--script', str(script), '--out', str(output), '--rate', '8000', '--no-options']
            result = subprocess.run(command, capture_output=True, text=True,
                                    env=dict(os.environ, MU_AUDIO_CUE_LOG=str(log)))
            self.assertEqual(result.returncode, 0, result.stderr)
            records = [json.loads(line) for line in log.read_text().splitlines()]
            raw = output.read_bytes(); samples = struct.unpack('<'+'h'*((len(raw)-44)//2),raw[44:])
            for n,index in enumerate(expected):
                selected = [row['id'] for row in records if row['op']=='music' and row['time_ms']==n*160]
                self.assertEqual(selected, [] if index is None else [index])
                sample = samples[(n*160+80)*8*2]
                self.assertAlmostEqual(sample, 0 if index is None else round(tracks[index]*.4*32768), delta=1)
            # Repeated frame requests for a track leave its looping voice alive.
            self.assertEqual([row['id'] for row in records if row['op']=='music' and row['time_ms']==40], [0])


if __name__ == '__main__':
    unittest.main()
