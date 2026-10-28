"""AUDIO-002B: installed world parts use the character session's audio reader."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
from test_native_npc import write_npc_world, PLACE, TABLE
from test_native_audio import constant_wav


class DomainWorldAudio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'build/mu-walk'], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory(prefix='audio-domain-world-')
        cls.folder = Path(cls.tmp.name)
        cls.root = write_npc_world(cls.folder/'game')
        cls.place = cls.folder/'placement.txt'; cls.place.write_text(PLACE)
        cls.demo = cls.folder/'npc.txt'; cls.demo.write_text(TABLE)
        wav = cls.folder/'sound.wav'; wav.write_bytes(constant_wav(.125, 8000))
        cls.table = cls.folder/'sounds.tsv'
        # NPC registrations use their original sites; the startup/UI rows are synthetic.
        cls.table.write_text(''.join(f'sound\t{id}\t{wav}\t1\t1\t0\t{site}\n' for id,site in
            [(25,0),(28,0),(8,0),(9,0),(160,0x1808e5a),(161,0x1808ff8)]))

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def run_world(self, name, audio):
        log = self.folder/(name+'.jsonl')
        command = [str(NATIVE/'build/mu-walk'), '--game-root', str(self.root), '--headless', '--backend', 'soft',
                   '--placement', str(self.place), '--npc-demo', str(self.demo), '--npc-script', '3:click:smith',
                   '--width','64','--height','64','--every','12','--frames','240','--tile','120,120',
                   '--out-dir',str(self.folder/name),'--sound-table',str(self.table)]
        if not audio: command += ['--no-audio']
        result = subprocess.run(command, capture_output=True, text=True,
                                env=dict(os.environ, MU_AUDIO_CUE_LOG=str(log)))
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        frames = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
        return frames, [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def test_world_npc_talk_voice_and_walk_have_session_provenance(self):
        _, rows = self.run_world('enabled', True)
        talks = [r for r in rows if r['op']=='play' and r['handler']==0x1280659]
        self.assertEqual([(r['id'],r['site']) for r in talks],[(25,0x12811ca),(28,0x12811d8)])
        voices = [r for r in rows if r['op']=='play' and r['site']==0x13b5402]
        self.assertTrue(voices)
        self.assertTrue(all(r['id']==161 and r['handler']==0x13b23f8 for r in voices))
        missing = [r for r in rows if r['op']=='unrecovered' and r['site']==0x13b5494]
        self.assertTrue(missing)
        self.assertTrue(all(r['id']==0x1295ade for r in missing))
        feet = [r for r in rows if r['op']=='play' and r['handler']==0x13b1f61]
        self.assertTrue(feet)
        self.assertTrue(all(r['site'] in (0x13b202f,0x13b2156) for r in feet))
        cues = [r['cue_seq'] for r in rows if r['handler']]
        self.assertEqual(cues, sorted(set(cues)))
        self.assertTrue(all(r['session_tick']>0 for r in talks+voices))
        # Registration is tied to model-open, not repeated on every tick.
        sites = [r['site'] for r in rows if r['op']=='register']
        self.assertEqual(len(sites), len(set(sites)))

    def test_audio_does_not_change_any_rendered_frame(self):
        on,_ = self.run_world('hash-on', True)
        off,_ = self.run_world('hash-off', False)
        a=[r['sha256'] for r in on if 'sha256' in r]
        b=[r['sha256'] for r in off if 'sha256' in r]
        self.assertEqual(len(a),21)
        self.assertEqual(a,b)


if __name__=='__main__': unittest.main()
