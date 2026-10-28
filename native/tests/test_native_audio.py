"""Native audio module (NATIVE-AUDIO-001) checks.

Portable (synthetic WAV files only, CI-safe on macOS and Linux):
  * WAV decoding against independent Python statements: PCM 8/16/24/32,
    IEEE float, WAVE_FORMAT_EXTENSIBLE, MS-ADPCM and IMA-ADPCM blocks, odd
    chunk padding, truncated data and malformed headers;
  * the mixer: exact gains through the client's groups and Option.ini, linear
    resampling, loops, one instance per sound id, voice stealing at 16;
  * the reconstructed per-frame world selection driving music and ambience
    from a synthetic table, OpenWorld volume and the options-window controls;
  * `mu-audio list/decode/render` behaviour, script errors and a regression
    hash of a synthetic render; the SDL2 live player builds and runs on the
    dummy driver when sdl2-config is present.
Private (MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT): every installed WAV
decodes, the platform decoder opens installed MP3/OGG music, and, with
MU_AUDIO_TABLE (scripts/extract_audio_tables.py --tsv), the installed sound
table lists and a scripted scene renders. Outputs stay in temporary folders.
"""
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
TOOL = NATIVE/'build/mu-audio'
LIVE = NATIVE/'build/mu-audio-live'
LIBRARY = NATIVE/('build/libmuaudio.dylib' if sys.platform == 'darwin' else 'build/libmuaudio.so')
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
RATE = 44100


def riff(chunks):
    body = b'WAVE' + b''.join(cid + struct.pack('<I', len(data)) + data + (b'\0' if len(data) & 1 else b'')
                              for cid, data in chunks)
    return b'RIFF' + struct.pack('<I', len(body)) + body


def fmt_chunk(tag, channels, rate, bits, block_align=None, extra=b''):
    block_align = block_align if block_align is not None else channels*bits//8
    payload = struct.pack('<HHIIHH', tag, channels, rate, rate*block_align, block_align, bits)
    if extra or tag != 1:
        payload += struct.pack('<H', len(extra)) + extra
    return (b'fmt ', payload)


def pcm16_wav(samples, channels=1, rate=RATE):
    data = b''.join(struct.pack('<h', max(-32768, min(32767, int(round(s*32768))))) for s in samples)
    return riff([fmt_chunk(1, channels, rate, 16), (b'data', data)])


def constant_wav(level, frames, channels=1, rate=RATE):
    return pcm16_wav([level]*(frames*channels), channels, rate)


class Pcm(ctypes.Structure):
    _fields_ = [('samples', ctypes.POINTER(ctypes.c_float)), ('frames', ctypes.c_uint32),
                ('channels', ctypes.c_uint16), ('rate', ctypes.c_uint32), ('format', ctypes.c_uint16),
                ('bits', ctypes.c_uint16)]


# ---- independent ADPCM statements -----------------------------------------

MS_ADAPT = [230, 230, 230, 230, 307, 409, 512, 614, 768, 614, 512, 409, 307, 230, 230, 230]
MS_COEFFS = [(256, 0), (512, -256), (0, 0), (192, 64), (240, 0), (460, -208), (392, -232)]


def ms_adpcm_decode(block, channels, frames_per_block):
    def s16(v):
        return v - 65536 if v >= 32768 else v
    p = 0
    predictor = list(block[p:p + channels]); p += channels
    delta = [s16(block[p + 2*c] | block[p + 2*c + 1] << 8) for c in range(channels)]; p += 2*channels
    s1 = [s16(block[p + 2*c] | block[p + 2*c + 1] << 8) for c in range(channels)]; p += 2*channels
    s2 = [s16(block[p + 2*c] | block[p + 2*c + 1] << 8) for c in range(channels)]; p += 2*channels
    out = [s2[:], s1[:]]
    nibbles = []
    for byte in block[p:]:
        nibbles += [byte >> 4, byte & 15]
    k = 0
    while len(out) < frames_per_block and k + channels <= len(nibbles):
        frame = []
        for c in range(channels):
            n = nibbles[k]; k += 1
            c1, c2 = MS_COEFFS[predictor[c]]
            pred = int((s1[c]*c1 + s2[c]*c2)/256)  # C division truncates toward zero
            value = max(-32768, min(32767, pred + (n - 16 if n >= 8 else n)*delta[c]))
            s2[c], s1[c] = s1[c], value
            delta[c] = min(max(16, int(MS_ADAPT[n]*delta[c]/256)), 2147483647//768)
            frame.append(value)
        out.append(frame)
    return [[v/32768 for v in f] for f in out]


IMA_STEPS = [7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80,
             88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598,
             658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327,
             3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289,
             16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767]
IMA_INDEX = [-1, -1, -1, -1, 2, 4, 6, 8]


def ima_decode(block, channels, frames_per_block):
    pred, index = [], []
    for c in range(channels):
        v = block[4*c] | block[4*c + 1] << 8
        pred.append(v - 65536 if v >= 32768 else v)
        index.append(min(88, block[4*c + 2]))
    out = [[pred[c] for c in range(channels)]]
    p = 4*channels
    while len(out) < frames_per_block and len(block) - p >= 4*channels:
        decoded = [[0]*8 for _ in range(channels)]
        for c in range(channels):
            group = block[p + 4*c:p + 4*c + 4]
            for k in range(8):
                n = group[k//2] >> 4 if k & 1 else group[k//2] & 15
                step = IMA_STEPS[index[c]]
                diff = step >> 3
                if n & 1: diff += step >> 2
                if n & 2: diff += step >> 1
                if n & 4: diff += step
                if n & 8: diff = -diff
                pred[c] = max(-32768, min(32767, pred[c] + diff))
                index[c] = max(0, min(88, index[c] + IMA_INDEX[n & 7]))
                decoded[c][k] = pred[c]
        for k in range(8):
            if len(out) < frames_per_block:
                out.append([decoded[c][k] for c in range(channels)])
        p += 4*channels
    return [[v/32768 for v in f] for f in out]


class NativeAudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'audio'], check=True, capture_output=True)
        cls.lib = ctypes.CDLL(str(LIBRARY))
        cls.lib.mu_wav_decode.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(Pcm), ctypes.c_char_p,
                                          ctypes.c_size_t]
        cls.lib.mu_wav_decode.restype = ctypes.c_int
        cls.lib.mu_pcm_free.argtypes = [ctypes.POINTER(Pcm)]
        cls.work = Path(tempfile.mkdtemp(prefix='mu-audio-test-'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def decode(self, data):
        pcm = Pcm()
        error = ctypes.create_string_buffer(256)
        status = self.lib.mu_wav_decode(data, len(data), ctypes.byref(pcm), error, 256)
        if status:
            return None, error.value.decode()
        values = [pcm.samples[i] for i in range(pcm.frames*pcm.channels)]
        info = (pcm.frames, pcm.channels, pcm.rate, pcm.format, pcm.bits)
        self.lib.mu_pcm_free(ctypes.byref(pcm))
        return info, values

    # ---- decoder -------------------------------------------------------------
    def test_pcm_depths_and_float(self):
        generator = random.Random(7)
        ints = [generator.randrange(-32768, 32768) for _ in range(64)]
        info, values = self.decode(riff([fmt_chunk(1, 2, 22050, 16), (b'data', struct.pack('<64h', *ints))]))
        self.assertEqual(info, (32, 2, 22050, 1, 16))
        self.assertEqual(values, [v/32768 for v in ints])
        bytes8 = bytes(generator.randrange(256) for _ in range(33))
        info, values = self.decode(riff([fmt_chunk(1, 1, 8000, 8), (b'data', bytes8)]))  # odd size: padded chunk
        self.assertEqual(info[0], 33)
        self.assertEqual(values, [(b - 128)/128 for b in bytes8])
        ints24 = [generator.randrange(-2**23, 2**23) for _ in range(10)]
        raw24 = b''.join(struct.pack('<i', v)[:3] for v in ints24)
        self.assertEqual(self.decode(riff([fmt_chunk(1, 1, 48000, 24), (b'data', raw24)]))[1], [v/2**23 for v in ints24])
        floats = [0.5, -0.25, 1.5, float('nan'), -1.0]
        info, values = self.decode(riff([fmt_chunk(3, 1, 44100, 32), (b'data', struct.pack('<5f', *floats))]))
        self.assertEqual(values, [0.5, -0.25, 1.5, 0.0, -1.0])
        doubles = struct.pack('<2d', 0.125, -0.5)
        self.assertEqual(self.decode(riff([fmt_chunk(3, 2, 44100, 64), (b'data', doubles)]))[1], [0.125, -0.5])
        sub = struct.pack('<HHIIHH', 0xfffe, 1, 32000, 64000, 2, 16) + struct.pack('<HHI', 22, 16, 4) + \
            struct.pack('<H', 1) + b'\0\0\x00\x00\x10\x00\x80\x00\x00\xaa\x00\x38\x9b\x71'
        info, values = self.decode(riff([(b'fmt ', sub), (b'data', struct.pack('<2h', 16384, -16384))]))
        self.assertEqual((info, values), ((2, 1, 32000, 1, 16), [0.5, -0.5]))

    def test_chunks_truncation_and_errors(self):
        data = struct.pack('<4h', 1000, 2000, 3000, 4000)
        wav = riff([(b'JUNK', b'xyz'), fmt_chunk(1, 1, 11025, 16), (b'LIST', b'abcd'), (b'data', data)])
        self.assertEqual(self.decode(wav)[1], [1000/32768, 2000/32768, 3000/32768, 4000/32768])
        truncated = wav[:-3]  # data chunk claims more than is present
        self.assertEqual(self.decode(truncated)[0][0], 2)
        for bad, message in ((b'RIFF\0\0\0\0WAVX', 'RIFF'), (riff([(b'data', data)]), 'fmt'),
                             (riff([fmt_chunk(1, 1, 8000, 16)]), 'data'),
                             (riff([fmt_chunk(1, 0, 8000, 16), (b'data', data)]), 'channel'),
                             (riff([fmt_chunk(1, 1, 8000, 12), (b'data', data)]), 'bit depth'),
                             (riff([fmt_chunk(0x55, 1, 8000, 16), (b'data', data)]), 'format tag'),
                             (riff([fmt_chunk(2, 1, 8000, 4, 64, struct.pack('<HH', 99, 7) +
                                              b''.join(struct.pack('<hh', *c) for c in MS_COEFFS)),
                                    (b'data', bytes(64))]), 'MS-ADPCM')):
            info, error = self.decode(bad)
            self.assertIsNone(info, message)
            self.assertIn(message, error)

    def test_ms_adpcm(self):
        generator = random.Random(2)
        for channels in (1, 2):
            block_align = 256*channels
            frames_per_block = 2 + (block_align - 7*channels)*2//channels
            blocks = []
            for _ in range(3):
                header = bytes(generator.randrange(7) for _ in range(channels))
                header += b''.join(struct.pack('<h', generator.randrange(16, 2000)) for _ in range(channels))
                header += b''.join(struct.pack('<h', generator.randrange(-30000, 30000)) for _ in range(2*channels))
                blocks.append(header + bytes(generator.randrange(256) for _ in range(block_align - len(header))))
            extra = struct.pack('<HH', frames_per_block, 7) + b''.join(struct.pack('<hh', *c) for c in MS_COEFFS)
            wav = riff([fmt_chunk(2, channels, 22050, 4, block_align, extra), (b'data', b''.join(blocks))])
            info, values = self.decode(wav)
            expected = []
            for block in blocks:
                for frame in ms_adpcm_decode(block, channels, frames_per_block):
                    expected += frame
            self.assertEqual(info[:4], (3*frames_per_block, channels, 22050, 2))
            self.assertEqual(values, [ctypes.c_float(v).value for v in expected])

    def test_ima_adpcm(self):
        generator = random.Random(3)
        for channels in (1, 2):
            block_align = 128*channels
            frames_per_block = 1 + (block_align - 4*channels)*2//channels
            blocks = []
            for _ in range(2):
                header = b''.join(struct.pack('<hBB', generator.randrange(-20000, 20000), generator.randrange(89), 0)
                                  for _ in range(channels))
                blocks.append(header + bytes(generator.randrange(256) for _ in range(block_align - len(header))))
            wav = riff([fmt_chunk(0x11, channels, 16000, 4, block_align, struct.pack('<H', frames_per_block)),
                        (b'data', b''.join(blocks))])
            info, values = self.decode(wav)
            expected = []
            for block in blocks:
                for frame in ima_decode(block, channels, frames_per_block):
                    expected += frame
            self.assertEqual(info[:4], (2*frames_per_block, channels, 16000, 0x11))
            self.assertEqual(values, [ctypes.c_float(v).value for v in expected])

    def test_decode_tool_round_trip(self):
        generator = random.Random(4)
        samples = [generator.randrange(-32768, 32768)/32768 for _ in range(400)]
        source = self.work/'round.wav'
        source.write_bytes(pcm16_wav(samples, 2, 32000))
        out = self.work/'round-out.wav'
        result = subprocess.run([str(TOOL), 'decode', str(source), '--out', str(out)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'format': 'pcm', 'bits': 16, 'channels': 2, 'rate': 32000,
                                                     'frames': 200})
        self.assertEqual(out.read_bytes()[44:], source.read_bytes()[44:])

    # ---- synthetic game root ----------------------------------------------------
    def game(self, name, files, table_rows, options=None):
        root = self.work/name
        for relative, data in files.items():
            path = root/relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        if options is not None:
            (root/'Data/Sound').mkdir(parents=True, exist_ok=True)
            (root/'Data/Sound/Option.ini').write_bytes(options)
        table = root/'table.tsv'
        table.write_text('# kind\tid\tpath\tch\t3d\tloader\n' + ''.join(row + '\n' for row in table_rows))
        return root, table

    def render(self, root, table, script, *extra):
        path = root/'script.txt'
        path.write_text(script)
        out = root/'out.wav'
        result = subprocess.run([str(TOOL), 'render', '--table', str(table), '--root', str(root), '--script', str(path),
                                 '--out', str(out), *extra], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        raw = out.read_bytes()
        count = (len(raw) - 44)//2
        values = struct.unpack(f'<{count}h', raw[44:44 + 2*count])
        return json.loads(result.stdout), values

    @staticmethod
    def options_ini(music=1.0, environment=1.0, effect=1.0, master=1.0, mutes=(False, False, False)):
        def number(v):
            text = '%#.16g' % v
            if text.endswith('0'):
                stripped = text.rstrip('0')
                text = stripped + '0' if stripped.endswith('.') else stripped
            return text
        b = lambda x: 'true' if x else 'false'
        return ('\r\n{\r\n\t"ChannelMutes" : [ %s, %s, %s ],\r\n\t"ChannelVolumes" : [ %s, %s, %s ],\r\n'
                '\t"MasterMute" : false,\r\n\t"MasterVolume" : %s\r\n}\r\n' % (
                    b(mutes[0]), b(mutes[1]), b(mutes[2]), number(music), number(environment), number(effect),
                    number(master))).encode()

    def test_effect_gain_through_groups(self):
        root, table = self.game('gain', {'Data/Sound/c.wav': constant_wav(0.25, RATE)},
                                ['sound\t40\tData\\Sound\\c.wav\t1\t1\t0x18433ed'], self.options_ini(effect=0.5, master=0.5))
        stats, values = self.render(root, table, '0 play 40\n200 end\n')
        self.assertEqual(stats['frames'], RATE*200//1000)
        self.assertTrue(all(v == round(0.25*0.5*0.5*32768) for v in values))  # 2048 in both channels
        stats, values = self.render(root, table, '0 play 40\n0 effectlevel 3\n80 end\n', '--no-options')
        level = ctypes.c_float(ctypes.c_float(3.0).value/9.0).value
        self.assertTrue(all(v == round(ctypes.c_float(0.25*level).value*32768) for v in values))

    def test_resampling_loop_and_single_instance(self):
        ramp = [i/400 for i in range(400)]
        root, table = self.game('resample', {'Data/Sound/r.wav': pcm16_wav(ramp, 1, 22050)},
                                ['sound\t7\tData\\Sound\\r.wav\t1\t1\t0x18433ed'])
        stats, values = self.render(root, table, '0 play 7 1\n20 play 7 1\n120 end\n', '--no-options')
        source = [round(v*32768)/32768 for v in ramp]
        expected = []
        position = 0.0
        for _ in range(stats['frames']):
            index = int(position)
            fraction = position - index
            nxt = (index + 1) % len(source)
            a, b = ctypes.c_float(source[index]).value, ctypes.c_float(source[nxt]).value
            v = ctypes.c_float(a + ctypes.c_float(ctypes.c_float(b - a).value*ctypes.c_float(fraction).value).value).value
            expected.append(max(-32768, min(32767, round(v*32768))))
            position += 0.5
            if position >= len(source):
                position -= len(source)
        self.assertEqual(list(values[0::2]), expected)  # looped, single instance (no doubling at 20 ms)
        self.assertEqual(values[0::2], values[1::2])     # mono feeds both channels

    def test_voice_stealing_keeps_sixteen(self):
        files = {f'Data/Sound/v{i}.wav': constant_wav(0.01, RATE) for i in range(18)}
        rows = [f'sound\t{100 + i}\tData\\Sound\\v{i}.wav\t1\t1\t0x18433ed' for i in range(18)]
        root, table = self.game('steal', files, rows)
        script = ''.join(f'{40*i} play {100 + i}\n' for i in range(18)) + '800 end\n'
        stats, values = self.render(root, table, script, '--no-options')
        level = round(0.01*32768)
        self.assertLessEqual(max(values), 16*level + 1)
        self.assertGreaterEqual(max(values[-200:]), 16*level - 16)

    def test_world_selection_music_and_ambience(self):
        files = {'Data/Sound/wind.wav': constant_wav(0.02, 2000), 'Data/Sound/rain.wav': constant_wav(0.04, 2000),
                 'data/music/pub.wav': constant_wav(0.1, RATE), 'data/music/theme.wav': constant_wav(0.2, RATE)}
        rows = ['sound\t0\tData\\Sound\\wind.wav\t1\t1\t0x18433ed', 'sound\t1\tData\\Sound\\rain.wav\t1\t1\t0x18433ed',
                'music\t0\tdata\\music\\Pub.wav\t-\t-\tstatic', 'music\t21\tdata\\music\\Theme.WAV\t-\t-\tstatic']
        root, table = self.game('world', files, rows, self.options_ini(music=0.4))
        script = ('0 world 0 safe=1 tile=4\n400 world 0 safe=1 tile=0\n800 world 0 safe=0 tile=0 rain=1\n'
                  '1200 openworld 6\n1600 musicon 0\n2000 noworld\n2000 world 5\n2400 end\n')
        stats, values = self.render(root, table, script)
        left = values[0::2]

        def at(ms):
            return left[ms*RATE//1000 + 100]
        music = ctypes.c_float(0.4).value
        self.assertEqual(at(100), round(ctypes.c_float(0.1*music).value*32768))            # pub music only
        self.assertEqual(at(500), round((ctypes.c_float(0.2*music).value + 0.02)*32768))   # theme + wind loop
        self.assertEqual(at(900), round((ctypes.c_float(0.2*music).value + 0.02 + 0.04)*32768))  # + rain
        self.assertEqual(at(1300), round((0.2 + 0.02 + 0.04)*32768))                      # music group 1.0
        self.assertEqual(at(1700), round((0.02 + 0.04)*32768))                            # music muted
        self.assertEqual(at(2200), 0)                                                     # world 5 stops all

    def test_doppelganger_manager_music(self):
        # AUDIO-002F: manager 0x00e305ee plays index 43 only when its event input is known and nonzero.
        files = {'data/music/dop.wav': constant_wav(0.1, RATE)}
        rows = ['music\t43\tdata\\music\\Dop.wav\t-\t-\tlive read']
        root, table = self.game('doppelganger', files, rows, self.options_ini(music=1.0))
        script = ('0 world 65\n0 manager 0x00e305ee\n400 eventmusic doppelganger 0\n400 manager 0x00e305ee\n'
                  '800 eventmusic doppelganger 1\n800 manager 0x00e305ee\n1200 end\n')
        _, values = self.render(root, table, script)
        left = values[0::2]
        self.assertEqual(max(left[:int(0.8*RATE)]), 0)
        self.assertEqual(left[int(1.0*RATE)], round(0.1*32768))
        for bad in ('0 manager 0x1234\n', '0 eventmusic dragons 1\n', '0 eventmusic doppelganger\n'):
            path = root/'bad.txt'
            path.write_text(bad)
            result = subprocess.run([str(TOOL), 'render', '--table', str(table), '--root', str(root), '--script',
                                     str(path), '--out', str(root/'bad.wav')], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, bad)

    def test_list_and_script_errors(self):
        root, table = self.game('list', {'Data/Sound/a.wav': constant_wav(0.1, 10, 2, 22050)},
                                ['sound\t3\tData\\Sound\\A.WAV\t2\t1\t0x18433ed', 'sound\t4\tData\\Sound\\gone.wav\t1\t1\t0x0',
                                 'music\t0\tdata\\music\\x.mp3\t-\t-\tstatic'])
        result = subprocess.run([str(TOOL), 'list', '--table', str(table), '--root', str(root)], capture_output=True,
                                text=True, check=True)
        self.assertIn('wav pcm 16-bit 2ch 22050 Hz', result.stdout)
        self.assertIn('# 2 rows, 2 ids, 1 missing files', result.stdout)
        music = subprocess.run([str(TOOL), 'list', '--table', str(table), '--music'], capture_output=True, text=True,
                               check=True).stdout
        self.assertIn('data\\music\\x.mp3', music)
        self.assertIn('(unresolved)', music)
        for script, message in (('0 dance\n', 'unknown command'), ('100 play 3\n50 end\n', 'must not decrease'),
                                ('x play 3\n', 'expected'), ('0 world 0 hat=1\n', 'unknown world field')):
            path = root/'bad.txt'
            path.write_text(script)
            result = subprocess.run([str(TOOL), 'render', '--table', str(table), '--root', str(root), '--script',
                                     str(path), '--out', str(root/'bad.wav'), '--no-options'], capture_output=True,
                                    text=True)
            self.assertNotEqual(result.returncode, 0, script)
            self.assertIn(message, result.stderr)

    def test_render_regression_hash(self):
        generator = random.Random(9)
        files = {'Data/Sound/n.wav': pcm16_wav([generator.uniform(-0.3, 0.3) for _ in range(5000)], 1, 11025),
                 'Data/Sound/s.wav': pcm16_wav([0.3*math.sin(i/7) for i in range(8000)], 2, 48000),
                 'data/music/m.wav': pcm16_wav([0.2*math.sin(i/50) for i in range(30000)], 1, 22050)}
        rows = ['sound\t0\tData\\Sound\\n.wav\t1\t1\t0x18433ed', 'sound\t25\tData\\Sound\\s.wav\t1\t1\t0x182049e',
                'music\t21\tdata\\music\\m.wav\t-\t-\tstatic']
        root, table = self.game('hash', files, rows, self.options_ini(music=0.4))
        script = '0 world 0 safe=1\n300 play 25\n700 effectlevel 5\n720 play 25\n1500 end\n'
        first, _ = self.render(root, table, script)
        second, _ = self.render(root, table, script)
        self.assertEqual(first, second)
        self.assertEqual(first['pcm_sha256'], '207036b711a07277a68466d736760c9440bab5d325ede5f90ddc298f18232897')

    @unittest.skipUnless(shutil.which(os.environ.get('SDL_CONFIG', 'sdl2-config')), 'SDL2 not installed')
    def test_live_player_on_dummy_driver(self):
        subprocess.run(['make', '-C', str(NATIVE), 'audio-live'], check=True, capture_output=True)
        root, table = self.game('live', {'Data/Sound/c.wav': constant_wav(0.1, 4000)},
                                ['sound\t1\tData\\Sound\\c.wav\t1\t1\t0x18433ed'])
        (root/'s.txt').write_text('0 play 1\n200 end\n')
        env = dict(os.environ, SDL_AUDIODRIVER='dummy')
        result = subprocess.run([str(LIVE), '--script', str(root/'s.txt'), '--table', str(table), '--root', str(root),
                                 '--no-options'], capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    # ---- private -------------------------------------------------------------------
    @unittest.skipUnless(PRIVATE, 'Installed audio checks are opt-in')
    def test_private_installed_audio(self):
        game = os.environ.get('MU_GAME_ROOT')
        self.assertTrue(game, 'Requested integration needs MU_GAME_ROOT')
        result = subprocess.run([str(TOOL), 'scan', '--root', game], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        scan = json.loads(result.stdout)
        self.assertEqual(scan['failed'], 0)
        self.assertGreaterEqual(scan['decoded'], 1300)
        if sys.platform == 'darwin':
            music = sorted((Path(game)/'Data/Music').glob('*.mp3'))[:1] + sorted((Path(game)/'Data/Music').glob('*.ogg'))[:1]
            for path in music:
                out = self.work/'private-music.wav'
                result = subprocess.run([str(TOOL), 'decode', str(path), '--out', str(out)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertGreater(json.loads(result.stdout)['frames'], 44100)
                out.unlink()
        table = os.environ.get('MU_AUDIO_TABLE')
        if table:
            listing = subprocess.run([str(TOOL), 'list', '--table', table, '--root', game], capture_output=True,
                                     text=True, check=True).stdout
            self.assertRegex(listing, r'# 15\d\d rows, 13\d\d ids')
            # AUDIO-002F: all 76 music indices resolve and every named file is installed.
            music = subprocess.run([str(TOOL), 'list', '--table', table, '--root', game, '--music'],
                                   capture_output=True, text=True, check=True).stdout.splitlines()
            rows = [line for line in music if re.match(r'\d+ ', line)]
            self.assertEqual(len(rows), 76)
            self.assertFalse([line for line in rows if 'missing' in line or '(unresolved)' in line])
            self.assertIn('iDoppelganger.mp3', rows[43] + rows[44])
            script = self.work/'private.txt'
            script.write_text('0 openworld 0\n0 world 0 safe=1\n500 play 25\n1000 world 0 safe=1 tile=4\n2000 end\n')
            out = self.work/'private.wav'
            # This checks installed decoding/mixing, independent of personal mute/volume preferences.
            result = subprocess.run([str(TOOL), 'render', '--table', table, '--root', game, '--script', str(script),
                                     '--out', str(out), '--no-options'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            stats = json.loads(result.stdout)
            self.assertEqual(stats['frames'], 88200)
            self.assertGreater(stats['peak'], 0.01)
            out.unlink()


if __name__ == '__main__':
    unittest.main()
