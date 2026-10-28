"""AUDIO-002E: scene keys -> immediate cue -> existing host, no late replay."""
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
#include "core/mu_charsel.h"
#include "core/mu_audio_host.h"
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
static mu_audio_host *host;
static int calls, nonzero;
static unsigned sites[8];
static uint64_t sequences[8];
static void sound(void *context, const mu_cue *cue, uint32_t tick) {
    assert(context == &calls); assert(tick > 0); assert(cue->handler == 0x01856e6c);
    assert(cue->u.sound.id == 25 && cue->u.sound.at_key == -2 && !cue->u.sound.loop);
    sites[calls] = cue->u.sound.site; sequences[calls++] = cue->seq;
    mu_audio_host_cue(host, cue, tick);
}
static void step(mu_charsel_session *s) {
    s->frame.clock.accumulator = 40;
    assert(mu_charsel_update(s, (s->steps + 1) * 40) == 1);
    if (host) {
        float pcm[4000];
        mu_audio_engine_mix(mu_audio_host_engine(host), pcm, 2000);
        for (int i = 0; i < 4000; ++i) nonzero += pcm[i] != 0;
        mu_audio_host_tick(host);
    }
}
static void press(mu_charsel_session *s, int key) {
    mu_charsel_message(s, 0x100, (uint32_t)key, 0);
    mu_charsel_key(s, key, 1); step(s); step(s); step(s);
    mu_charsel_message(s, 0x101, (uint32_t)key, 0);
    mu_charsel_key(s, key, 0); step(s);
}
int main(int argc, char **argv) {
    assert(argc == 4); char error[512];
    mu_charsel_session *s = calloc(1, sizeof *s); mu_charsel_list list;
    mu_charsel_list_default(&list); list.count = 1;
    assert(!mu_charsel_init(s, argv[1], &list, NULL, 128, 80, 20));
    mu_audio_table table; assert(!mu_audio_table_load(argv[2], &table, error, sizeof error));
    mu_audio_host_config ac = {0}; ac.table = &table; ac.skip_options = 1;
    ac.engine.game_root = argv[1]; ac.engine.rate = 8000;
    mu_audio_host *saved = mu_audio_host_new(&ac, error, sizeof error); assert(saved);
    host = !strcmp(argv[3], "disabled") ? NULL : saved;
    if (!strcmp(argv[3], "muted"))
        mu_audio_set_group_mute(mu_audio_host_client(saved), MU_AUDIO_GROUP_EFFECT, 1);
    mu_charsel_set_sound(s, sound, &calls);
    if (!strcmp(argv[3], "detached")) mu_charsel_set_sound(s, NULL, &calls);
    s->tick.enter_refused = 1; press(s, 0x0d); /* sound precedes refusal */
    assert(s->enter_requests == 0);
    if (!strcmp(argv[3], "detached")) {
        assert(!calls && !s->sound_context);
        mu_charsel_set_sound(s, sound, &calls); step(s); assert(!calls);
    }
    press(s, 0x1b); assert(s->menu_requests == 1);
    s->gfx_create_open = 1; press(s, 0x1b); assert(s->panel_close_requests == 1);
    /* Enter with a panel, and Esc with a busy menu, stay silent. */
    press(s, 0x0d); s->gfx_create_open = 0; s->tick.gfx_menu_flag = 1; press(s, 0x1b);
    assert(s->sound_sequence == 3);
    int detached = !strcmp(argv[3], "detached");
    assert(calls == (detached ? 2 : 3));
    assert(sites[0] == (detached ? 0x01857163 : 0x01857064));
    assert(sites[calls-1] == 0x018571e6);
    for (int i = 0; i < calls; ++i) assert(sequences[i] == (uint64_t)(i+1+detached));
    host = saved;
    mu_audio_set_group_mute(mu_audio_host_client(host), MU_AUDIO_GROUP_EFFECT, 0);
    int before = nonzero; step(s); assert(nonzero == before); /* no replay */
    mu_charsel_free(s); assert(!s->sound && !s->sound_context && !s->sound_sequence);
    printf("{\"calls\":%d,\"nonzero\":%d}\n", calls, nonzero);
    free(s); mu_audio_host_free(saved); mu_audio_table_free(&table); return 0;
}
'''


class CharselAudio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'all', 'build/mu-client'], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory(prefix='audio-charsel-test-')
        cls.folder = Path(cls.tmp.name)
        cls.root = write_root(cls.folder / 'game')
        cls.session = write_session(cls.folder)
        wav = cls.root / 'Data/Sound/click.wav'
        wav.parent.mkdir(parents=True, exist_ok=True)
        wav.write_bytes(constant_wav(.125, 8000))
        cls.table = cls.folder / 'sounds.tsv'
        cls.table.write_text('sound\t25\tData/Sound/click.wav\t1\t1\t0\t0\n')
        source = cls.folder / 'host.c'
        source.write_text(HARNESS)
        obj = cls.folder / 'host.o'
        cls.host = cls.folder / 'host'
        subprocess.run(['cc', '-std=c11', '-I', str(NATIVE), '-c', str(source), '-o', str(obj)], check=True)
        crypto = subprocess.check_output(['brew', '--prefix', 'cryptopp'], text=True).strip()
        jpeg = subprocess.check_output(['brew', '--prefix', 'jpeg-turbo'], text=True).strip()
        subprocess.run(['c++', str(obj), str(NATIVE / 'build/libmunative.a'), str(NATIVE / 'build/libmuaudio.a'),
                        '-L' + crypto + '/lib', '-lcryptopp', '-L' + jpeg + '/lib', '-ljpeg',
                        '-framework', 'CoreText', '-framework', 'CoreGraphics', '-framework', 'CoreFoundation',
                        '-framework', 'AudioToolbox', '-lm', '-o', str(cls.host)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def drive(self, mode):
        log = self.folder / f'{mode}.jsonl'
        p = subprocess.run([str(self.host), str(self.root), str(self.table), mode], capture_output=True, text=True,
                           env={**os.environ, 'MU_AUDIO_CUE_LOG': str(log)})
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return json.loads(p.stdout), [r for r in map(json.loads, log.read_text().splitlines())
                                     if r['op'] == 'play' and r['handler']]

    def test_three_sites_once_per_press_refused_enter_and_close(self):
        result, rows = self.drive('on')
        self.assertEqual(result['calls'], 3)
        self.assertGreater(result['nonzero'], 0)
        self.assertEqual([r['site'] for r in rows], [0x1857064, 0x1857163, 0x18571e6])
        self.assertEqual([r['cue_seq'] for r in rows], [1, 2, 3])
        self.assertTrue(all(r['result'] == 1 for r in rows))

    def test_mute_consumes_decisions_without_replay(self):
        result, rows = self.drive('muted')
        self.assertEqual((result['calls'], result['nonzero'], len(rows)), (3, 0, 3))

    def test_disabled_consumes_decisions_without_replay(self):
        result, rows = self.drive('disabled')
        self.assertEqual((result['calls'], result['nonzero'], rows), (3, 0, []))

    def test_detach_discards_and_rebind_does_not_replay(self):
        result, rows = self.drive('detached')
        self.assertEqual(result['calls'], 2)
        self.assertEqual([r['cue_seq'] for r in rows], [2, 3])

    def test_shell_host_table_hook_and_charsel_hashes(self):
        lib, movies = stub_library(self.folder)
        cases = [('30:enter', 0x1857064), ('30:esc', 0x1857163),
                 ('30:click:create 36:esc', 0x18571e6)]
        for script, site in cases:
            hashes = []
            for enabled in [True, False]:
                with tempfile.TemporaryDirectory(dir=self.folder) as tmp:
                    out = Path(tmp)
                    log = out / 'audio.jsonl'
                    cmd = [str(NATIVE / 'build/mu-client'), '--game-root', str(self.root),
                           '--session', str(self.session), '--headless', '--backend', 'soft',
                           '--frames', '42', '--every', '10', '--width', '640', '--height', '480',
                           '--out-dir', str(out), '--sound-table', str(self.table),
                           '--gfx', str(movies), '--script', f'10:enter 14:enter {script}']
                    if not enabled:
                        cmd.append('--no-audio')
                    p = subprocess.run(cmd, capture_output=True, text=True,
                                       env={**os.environ, 'MU_AUDIO_CUE_LOG': str(log), 'MU_GFX_LIB': str(lib)})
                    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                    frames = [json.loads(l) for l in p.stdout.splitlines() if l.startswith('{')]
                    hashes.append([r['sha256'] for r in frames if 'sha256' in r])
                    if enabled:
                        rows = [r for r in map(json.loads, log.read_text().splitlines())
                                if r['op'] == 'play' and r['handler'] == 0x1856e6c]
                        self.assertEqual([(r['site'], r['id'], r['result']) for r in rows], [(site, 25, 1)])
            self.assertTrue(hashes[0])
            self.assertEqual(hashes[0], hashes[1])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'Pinned charsel instructions are opt-in')
    def test_original_charsel_audio(self):
        report = self.folder / 'original.json'
        p = subprocess.run([sys.executable, str(NATIVE.parent / 'scripts/validate_audio_charsel.py'),
                            '--mutations', '--report', str(report)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        data = json.loads(report.read_text())
        self.assertEqual(data['cases'], 5968)
        self.assertEqual(data['mismatches'], 0)
        self.assertEqual(len(data['mutants']), 11)
        self.assertTrue(all(v == 'caught' for v in data['mutants'].values()))


if __name__ == '__main__':
    unittest.main()
