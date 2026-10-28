"""AUDIO-002 portable boundary checks and opt-in original instruction families."""
import ctypes as C
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from validate_audio_events import State, native as events
class Audio002(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-C',str(ROOT/'reconstructed/audio')],check=True,capture_output=True)
        cls.lib=C.CDLL(str(ROOT/'reconstructed/audio'/('libclient_audio.dylib' if sys.platform=='darwin' else 'libclient_audio.so')))
    def test_unknown_event_inputs_are_reported(self):
        s=State(39,0,0,3,0,0,0)
        self.assertEqual(events(self.lib,0xe8e857,s),[(6,0xe8e857,0)])
        s.known=2
        self.assertEqual(events(self.lib,0xe8e857,s),[(4,26,0),(4,24,0),(3,25,0)])
    def test_no_stop_managers_and_empty_manager(self):
        s=State(0,0,0,0,0,0,0)
        for addr in [0xe42ad0,0xdd306c,0xdd8891,0xdde543,0xde5467,0xe6dd22]:
            self.assertEqual(events(self.lib,addr,s),[])
    def test_partial_raklion_input_preserves_prior_call(self):
        s=State(58,0,0,0,0,0,0)
        self.assertEqual(events(self.lib,0xe9e9c5,s),[(4,34,0),(6,0xe9e9c5,0)])
    def test_doppelganger_manager(self):
        from validate_audio_music import State as MusicState, native as music
        s=MusicState(65,0,0,0,0,0,0,1)
        self.assertEqual(music(self.lib,0xe305ee,s),[(6,0xe305ee,0)])
        for world in (0,65,68,200):
            for value,want in ((0,[]),(1,[(3,43,0)]),(-1,[(3,43,0)]),(0x100,[(3,43,0)])):
                s=MusicState(world,0,0,0,0,0,16,value)
                self.assertEqual(music(self.lib,0xe305ee,s),want)
    def test_music_layout_names_every_index(self):
        from extract_audio_tables import MUSIC_LAYOUT
        self.assertEqual(len(MUSIC_LAYOUT),76)
        self.assertNotIn(None,MUSIC_LAYOUT)
        self.assertEqual((MUSIC_LAYOUT[43],MUSIC_LAYOUT[44]),(40,40))
        self.assertEqual(sorted(set(MUSIC_LAYOUT)),list(range(72)))
    def test_npc_voice_edges(self):
        f=self.lib.mu_audio_npc_voice;f.argtypes=[C.c_int32,C.c_int32,C.c_uint16,C.c_float,C.c_int]
        self.assertEqual(f(0xa0b,-64,0,0,0),161)
        self.assertEqual(f(0xa06,255,0,0,0),-1)
        self.assertEqual(f(0xa01,0,0,10,0),160)
        self.assertEqual(f(0xa01,0,0,float('nan'),0),-1)
        self.assertEqual(f(0xa01,0,0,7,1),-1)
        self.assertEqual(f(0xa00,0,0,7,0),-1)
    def compare(self,name):
        with tempfile.TemporaryDirectory(prefix='audio-002-') as tmp:
            subprocess.run([sys.executable,str(ROOT/f'scripts/{name}.py'),'--mutations','--report',str(Path(tmp)/'report.json')],check=True,capture_output=True)
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','Pinned Unicorn audio events are opt-in')
    def test_original_events(self):self.compare('validate_audio_events')
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','Pinned Unicorn audio registration is opt-in')
    def test_original_registration(self):self.compare('validate_audio_registration')
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','Pinned Unicorn music table is opt-in')
    def test_original_music_table(self):self.compare('validate_audio_music')
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','Pinned Unicorn NPC voices are opt-in')
    def test_original_voices(self):self.compare('validate_audio_voices')
if __name__=='__main__':unittest.main()
