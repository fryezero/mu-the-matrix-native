"""Checks for the reconstructed client audio logic (NATIVE-AUDIO-001).

Portable: the authored C runs against a recording FMOD stand-in and must issue
the boundary calls an independent statement of the client rules expects
(sound table, path cache, music, init, settings, options file, per-frame world
selection, OpenWorld music volume, options-UI conversions).
Private (MU_RECOVERY_INTEGRATION=1): the Unicorn comparison against the
restored client instructions, and the installed Option.ini round trip.
"""
import ctypes
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_audio as va  # noqa: E402  (no Unicorn at import time)

LIBRARY = HERE/('libclient_audio.dylib' if sys.platform == 'darwin' else 'libclient_audio.so')
SYS, MASTER, MUSIC_G, ENV_G, EFFECT_G = 0x5100, 0x8000, 0x8001, 0x8002, 0x8003


def fmod_only(trace):
    return [r for r in trace if r[0] not in ('op', 'ret')]


class ClientAudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        cls.lib = va.load_library(LIBRARY)
        va.configure_library(cls.lib)
        L = cls.lib
        L.mu_audio_options_parse.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_void_p]
        L.mu_audio_options_parse.restype = ctypes.c_int
        L.mu_audio_options_format.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
        L.mu_audio_options_format.restype = ctypes.c_size_t
        L.mu_audio_world_full_music_volume.argtypes = [ctypes.c_int32]
        L.mu_audio_full_volume_worlds.argtypes = [ctypes.c_void_p]
        L.mu_audio_full_volume_worlds.restype = ctypes.c_size_t
        L.mu_audio_stricmp.argtypes = [ctypes.c_char_p, ctypes.c_char_p]

    def run_native(self, ops, fmod=None):
        recorder = va.Recorder(fmod)
        side = va.NativeSide(self.lib, recorder)
        returns = []
        try:
            for op in ops:
                recorder.records.append(('op', op[0]))
                value = side.op(op)
                returns.append(value)
                recorder.records.append(('ret', value))
        finally:
            side.close()
        return recorder.records, returns

    def segment(self, trace, index):
        """FMOD calls made by the index-th operation."""
        ops = [i for i, r in enumerate(trace) if r[0] == 'op']
        end = ops[index + 1] if index + 1 < len(ops) else len(trace)
        return [r for r in trace[ops[index]:end] if r[0] not in ('op', 'ret')]

    # ---- init --------------------------------------------------------------
    def expected_init_tail(self):
        return [('System::getMasterChannelGroup', SYS), ('System::createChannelGroup', SYS, 'Music'),
                ('ChannelGroup::addGroup', MASTER, MUSIC_G), ('System::createChannelGroup', SYS, 'Environment'),
                ('ChannelGroup::addGroup', MASTER, ENV_G), ('System::createChannelGroup', SYS, 'Effect'),
                ('ChannelGroup::addGroup', MASTER, EFFECT_G)]

    def test_init_with_driver(self):
        trace, returns = self.run_native([('init', 0)], {'drivers': 2, 'caps': 2, 'speaker': 3, 'name': 'X SigmaTel Y'})
        self.assertEqual(returns, [1])
        self.assertEqual(fmod_only(trace), [
            ('System_Create',), ('System::getNumDrivers', SYS), ('System::setOutput', SYS, 6),
            ('System::getDriverCaps', SYS, 0, False, False), ('System::setSpeakerMode', SYS, 3),
            ('System::setDSPBufferSize', SYS, 1024, 10), ('System::getDriverInfo', SYS, 0, 256, False),
            ('System::setSoftwareFormat', SYS, 48000, 5, 0, 0, 1), ('System::init', SYS, 16, 0, 0)]
            + self.expected_init_tail())

    def test_init_without_driver_and_retry(self):
        trace, returns = self.run_native([('init', 0), ('init', 0)],
                                         {'drivers': 0, 'fail': {'System::init': [0x3a]}})
        self.assertEqual(returns, [1, 1])
        self.assertEqual(fmod_only(trace), [
            ('System_Create',), ('System::getNumDrivers', SYS), ('System::setOutput', SYS, 2),
            ('System::init', SYS, 16, 0, 0), ('System::setSpeakerMode', SYS, 2), ('System::init', SYS, 16, 0, 0)]
            + self.expected_init_tail())
        trace, returns = self.run_native([('init', 0)], {'drivers': 0, 'fail': {'System::init': [0x1f]}})
        self.assertEqual(returns, [0])

    # ---- sound table -------------------------------------------------------
    def test_one_instance_per_id_and_end_callback(self):
        ops = [('init', 0), ('load', 7, 'Data\\Sound\\aWind.wav', 3, 0), ('load', 7, 'other.wav', 1, 1),
               ('play', 7, 1), ('play', 7, 0), ('end', 0x7000, 1), ('play', 7, 0), ('end', 0x7000, 0),
               ('play', 7, 0), ('stop', 7), ('play', 99, 0)]
        trace, returns = self.run_native(ops)
        self.assertEqual(returns[1:], [1, 1, 1, 1, 0, 1, 0, 1, None, 0])
        self.assertEqual(self.segment(trace, 1), [('System::createStream', SYS, 'Data\\Sound\\aWind.wav',
                                                   '0x8000029', 0)])
        self.assertEqual(self.segment(trace, 2), [])  # already registered: no reload
        self.assertEqual(self.segment(trace, 3), [
            ('System::playSound', SYS, -1, 0x6000, 1), ('Channel::setChannelGroup', 0x7000, EFFECT_G),
            ('Channel::setPriority', 0x7000, 2), ('Channel::setMode', 0x7000, '0x2'),
            ('Channel::setPaused', 0x7000, 0), ('Channel::setUserData', 0x7000, ('entry', 7)),
            ('Channel::setCallback', 0x7000, 'end-callback')])
        self.assertEqual(self.segment(trace, 4), [])  # still playing
        self.assertEqual(self.segment(trace, 5), [])  # non-END callback types are ignored
        self.assertEqual(self.segment(trace, 7), [('Channel::getUserData', 0x7000)])
        self.assertEqual(self.segment(trace, 8)[0], ('System::playSound', SYS, -1, 0x6000, 1))
        self.assertNotIn(('Channel::setMode', 0x7001, '0x2'), self.segment(trace, 8))
        self.assertEqual(self.segment(trace, 9), [('Channel::stop', 0x7001)])

    def test_path_cache_is_case_insensitive_and_owned(self):
        ops = [('init', 0), ('load', 1, 'Data\\Sound\\A.wav', 1, 1), ('load', 2, 'DATA\\sound\\a.WAV', 1, 1),
               ('remove', 1), ('remove', 2), ('load', 3, 'data\\sound\\a.wav', 1, 1)]
        trace, _ = self.run_native(ops)
        self.assertEqual(self.segment(trace, 2), [])
        self.assertEqual(self.segment(trace, 3), [])
        self.assertEqual(self.segment(trace, 4), [('Sound::release', 0x6000)])
        self.assertEqual(self.segment(trace, 5), [('System::createStream', SYS, 'data\\sound\\a.wav', '0x8000029', 0)])

    def test_failed_open_registers_nothing(self):
        ops = [('init', 0), ('load', 1, 'missing.wav', 1, 1), ('play', 1, 0), ('load', 1, 'missing.wav', 1, 1)]
        trace, returns = self.run_native(ops, {'fail': {'System::createStream': [0x17]}})
        self.assertEqual(returns[1:], [0, 0, 1])
        self.assertEqual(len([r for r in trace if r[0] == 'System::createStream']), 2)

    def test_without_system_nothing_reaches_fmod(self):
        trace, returns = self.run_native([('load', 1, 'a.wav', 1, 1), ('play', 1, 1), ('mp3', 'x.mp3'), ('read',)])
        self.assertEqual(fmod_only(trace), [])
        self.assertEqual(returns[:2], [0, 0])

    # ---- music ---------------------------------------------------------------
    def test_music_switching(self):
        ops = [('init', 0), ('mp3', 'data\\music\\Pub.mp3'), ('mp3', 'DATA\\MUSIC\\pub.MP3'),
               ('stopmp3', 'data\\music\\Noria.mp3'), ('mp3', 'data\\music\\Noria.mp3'),
               ('stopmp3', 'Data\\Music\\NORIA.mp3'), ('stopmp3', 'Data\\Music\\NORIA.mp3')]
        trace, _ = self.run_native(ops)
        self.assertEqual(self.segment(trace, 1), [
            ('System::createSound', SYS, 'data\\music\\Pub.mp3', '0x8000029', 0),
            ('System::playSound', SYS, -1, 0x6000, 1), ('Channel::setChannelGroup', 0x7000, MUSIC_G),
            ('Channel::setPriority', 0x7000, 0), ('Channel::setMode', 0x7000, '0x2'), ('Channel::setPaused', 0x7000, 0)])
        self.assertEqual(self.segment(trace, 2), [])
        self.assertEqual(self.segment(trace, 3), [])
        self.assertEqual(self.segment(trace, 4)[:3], [('ChannelGroup::stop', MUSIC_G), ('Sound::release', 0x6000),
                                                      ('System::createSound', SYS, 'data\\music\\Noria.mp3',
                                                       '0x8000029', 0)])
        self.assertEqual(self.segment(trace, 5), [('ChannelGroup::stop', MUSIC_G), ('Sound::release', 0x6001)])
        self.assertEqual(self.segment(trace, 6), [])

    def test_stricmp(self):
        self.assertEqual(self.lib.mu_audio_stricmp(b'ABC', b'abc'), 0)
        self.assertLess(self.lib.mu_audio_stricmp(b'a', b'B'), 0)
        self.assertLess(self.lib.mu_audio_stricmp(b'_', b'A'), 0)  # folds to lower case: '_' < 'a'

    # ---- settings --------------------------------------------------------------
    def test_apply_and_read_settings(self):
        half = va.f32_bits(0.5)
        ops = [('init', 0), ('apply', (1, half, (0, 1, 0), (va.f32_bits(0.4), half, va.f32_bits(1.0)))), ('read',)]
        trace, returns = self.run_native(ops)
        self.assertEqual(self.segment(trace, 1), [
            ('ChannelGroup::setMute', MASTER, 1), ('ChannelGroup::setVolume', MASTER, hex(half)),
            ('ChannelGroup::setMute', MUSIC_G, 0), ('ChannelGroup::setVolume', MUSIC_G, '0x3ecccccd'),
            ('ChannelGroup::setMute', ENV_G, 1), ('ChannelGroup::setVolume', ENV_G, hex(half)),
            ('ChannelGroup::setMute', EFFECT_G, 0), ('ChannelGroup::setVolume', EFFECT_G, '0x3f800000')])
        self.assertEqual(returns[2], (1, hex(half), (0, 1, 0), ('0x3ecccccd', hex(half), '0x3f800000')))

    def test_options_file_round_trip(self):
        L = self.lib
        text = (b'\r\n{\r\n\t"ChannelMutes" : [ false, true, false ],\r\n'
                b'\t"ChannelVolumes" : [ 0.4000000059604645, 1.0, 0.50 ],\r\n'
                b'\t"MasterMute" : false,\r\n\t"MasterVolume" : 1.0\r\n}\r\n')
        settings = (ctypes.c_int32*8)()
        self.assertEqual(L.mu_audio_options_parse(text, len(text), settings), 1)
        values = list(settings)
        self.assertEqual(values[:5], [0, va.f32_bits(1.0), 0, 1, 0])
        self.assertEqual([v & 0xffffffff for v in values[5:]], [0x3ecccccd, 0x3f800000, 0x3f000000])
        buffer = ctypes.create_string_buffer(512)
        length = L.mu_audio_options_format(settings, buffer, 512)
        self.assertEqual(buffer.raw[:length], text)
        for bad in (b'{', b'{"MasterVolume": "loud"}', b'[1] x', b''):
            self.assertEqual(L.mu_audio_options_parse(bad, len(bad), settings), 0, bad)
        sparse = b'{"MasterVolume": 0.25, "ChannelVolumes": [0.75]} // comment'
        self.assertEqual(L.mu_audio_options_parse(sparse, len(sparse), settings), 1)
        self.assertEqual([v & 0xffffffff for v in settings],
                         [0, va.f32_bits(0.25), 0, 0, 0, va.f32_bits(0.75), 0, 0])

    def test_ui_level_conversions(self):
        L = self.lib
        for level in range(10):
            self.assertEqual(va.f32_bits(L.mu_audio_level_to_volume(level)), va.f32_bits(level/9.0))
            self.assertEqual(L.mu_audio_volume_to_level(L.mu_audio_level_to_volume(level)), level)
        self.assertEqual(L.mu_audio_volume_to_level(0.4), 4)       # 4.1 truncated
        self.assertEqual(L.mu_audio_volume_to_level(-0.05), 0)     # -0.45 + 0.5 truncates toward zero
        self.assertEqual(L.mu_audio_volume_to_level(-0.1), 0)      # -0.4 truncates to 0
        self.assertEqual(L.mu_audio_volume_to_level(float('nan')), -2**31)
        self.assertEqual(L.mu_audio_volume_to_level(1e30), -2**31)

    # ---- world selection --------------------------------------------------------
    def frame(self, **fields):
        case = dict(scene=6, world=0, tile=0, rain=0, safe=1, x=128, y=128, attribute=0, rand=1, boss=0)
        case.update(fields)
        return va.c_frame(self.lib, case)

    def test_world_frame_examples(self):
        a, b = self.frame(world=0, tile=4)
        self.assertEqual(a[:2], [('snd_stop', 0), ('snd_stop', 1)])
        self.assertIn(('mp3_play', 0), a)
        a, _ = self.frame(world=0, tile=1, rain=2)
        self.assertEqual(a[:2], [('snd_play', 0, 1), ('snd_play', 1, 1)])
        self.assertIn(('mp3_play', 21), a)
        self.assertIn(('mp3_play', 2), self.frame(world=2, x=0xd0, y=0x10)[0])
        self.assertIn(('mp3_play', 3), self.frame(world=2, x=0xd7, y=0x10)[0])
        self.assertNotIn(('mp3_play', 3), self.frame(world=2, x=0xd7, y=0x10, safe=0)[0])
        a, _ = self.frame(world=3, rand=1024)
        self.assertEqual(a[:3], [('snd_play', 0, 1), ('rand',), ('snd_play', 2, 0)])
        a, _ = self.frame(world=0x7a, boss=1, x=5, y=6)
        self.assertEqual(a[0], ('boss_query', 0x7a, 5, 6))
        self.assertEqual(a[1], ('mp3_play', 58))
        self.assertEqual(self.frame(scene=5), ([], None))
        a, b = self.frame(world=0x33)
        self.assertEqual(b[0], ('mp3_play', 31))
        self.assertEqual(sum(1 for e in b if e[0] == 'delegate'), 10)
        self.assertEqual(a[-1], ('delegate', 0xdb747f, -1))

    def test_world_frame_stops_everything_elsewhere(self):
        a, b = self.frame(world=0x99)
        self.assertFalse([e for e in a + b if e[0] in ('snd_play', 'mp3_play')])
        stops = {e[1] for e in a if e[0] == 'snd_stop'}
        self.assertTrue({0, 1, 2, 3, 5, 6, 7, 0x14, 0x313, 0x319, 0x3da, 0x5b2} <= stops)

    def test_openworld_music_volume(self):
        L = self.lib
        self.assertEqual(L.mu_audio_full_volume_worlds(None), 57)
        for world, full in ((0, 0), (6, 1), (9, 1), (0x0b, 1), (0x18, 0), (0x8b, 1), (0x8c, 0), (-1, 0)):
            self.assertEqual(L.mu_audio_world_full_music_volume(world), full, world)
            self.assertEqual(va.f32_bits(L.mu_audio_world_music_volume(world)),
                             va.f32_bits(1.0 if full else va.f32(0.4)))

    # ---- private --------------------------------------------------------------
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'Installed Option.ini check is opt-in')
    def test_private_installed_option_ini_round_trip(self):
        root = os.environ.get('MU_GAME_ROOT')
        self.assertTrue(root, 'Requested integration needs MU_GAME_ROOT')
        text = (Path(root)/'Data/Sound/Option.ini').read_bytes()
        settings = (ctypes.c_int32*8)()
        self.assertEqual(self.lib.mu_audio_options_parse(text, len(text), settings), 1)
        buffer = ctypes.create_string_buffer(1024)
        length = self.lib.mu_audio_options_format(settings, buffer, 1024)
        self.assertEqual(buffer.raw[:length], text)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'Private audio instruction comparison is opt-in')
    def test_private_original_audio_instructions(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA', ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_audio.py'), '--text', str(text),
                            '--data', str(data), '--library', str(LIBRARY), '--random', '200',
                            '--report', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
        self.assertEqual(result['frame']['equal'], result['frame']['cases'])
        self.assertGreaterEqual(result['frame']['cases'], 600)
        self.assertEqual(result['frame_sensitivity']['missed'], 0)
        for key, total in (('openworld', 'cases'), ('manager', 'scripts'), ('init', 'scripts'), ('settings', 'cases')):
            self.assertEqual(result[key]['equal'], result[key][total], key)

    def test_validator_rejects_unpinned_input(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory)/'not-client-text.bin'
            fake.write_bytes(b'\0'*64)
            result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_audio.py'), '--text', str(fake),
                                     '--data', str(fake)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('pinned restored text', result.stderr)


if __name__ == '__main__':
    unittest.main()
