"""Portable checks of the NPC dialogue manager (reconstructed/npc/npc_dialogue.c, NATIVE-LANG-002).

The client comparison is scripts/validate_npc_dialogue.py (Unicorn, private
captures and the installed files).  These checks build libnpc and compare it
with an independent Python statement over synthetic decoded NPCDialogue and
QuestWords bytes: the record key (NPC << 16) + state, first-wins inserts,
the text taken to the first NUL of the reused 0x500-byte buffer, the four
lookups with NPC 0 and absent records, and the window's choice rule
(<= 900 and not -1: show; 901..920: server request; otherwise state 999).
"""
import ctypes
from pathlib import Path
import random
import struct
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
LIB = HERE/('libnpc.dylib' if sys.platform == 'darwin' else 'libnpc.so')


def build():
    subprocess.run(['make', '-C', str(HERE), '-s'], check=True)
    lib = ctypes.CDLL(str(LIB))
    lib.mu_dlg_parse_records.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
    lib.mu_dlg_parse_records.restype = ctypes.c_long
    lib.mu_dlg_parse_words.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
    lib.mu_dlg_parse_words.restype = ctypes.c_long
    lib.mu_dlg_free.argtypes = [ctypes.c_void_p]
    lib.mu_dlg_set_npc.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    for name in ('mu_dlg_text', 'mu_dlg_state_text'):
        getattr(lib, name).argtypes = [ctypes.c_void_p, ctypes.c_int32]
        getattr(lib, name).restype = ctypes.c_char_p
    lib.mu_dlg_option_text.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32]
    lib.mu_dlg_option_text.restype = ctypes.c_char_p
    lib.mu_dlg_option_next.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32]
    lib.mu_dlg_option_next.restype = ctypes.c_int32
    lib.mu_dlg_select.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32]
    lib.mu_dlg_select.restype = ctypes.c_uint64
    lib.mu_dlg_option_count.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    lib.mu_dlg_action_closes.argtypes = [ctypes.c_int32]
    return lib


class Model:
    """Independent statement of the manager (std::map inserts, the loader's buffer) and the window's choice."""

    def __init__(self, records, words):
        self.records, self.words, self.npc = {}, {}, 0
        for k in range(0, len(records) - 87, 88):
            v = struct.unpack_from('<22i', records, k)
            self.records.setdefault(v[0], v[1:])
        buffer, off = bytearray(0x500), 0
        while off + 6 <= len(words):
            wid, length = struct.unpack_from('<ih', words, off)
            off += 6
            if length < 0 or length > 0x500 or off + length > len(words):
                break
            buffer[:length] = words[off:off + length]
            off += length
            self.words.setdefault(wid, bytes(buffer).split(b'\0')[0])

    def record(self, state):
        key = struct.unpack('<i', struct.pack('<I', ((self.npc << 16) + state) & 0xffffffff))[0]
        return self.records.get(key)

    def text(self, wid):
        return self.words.get(wid)

    def state_text(self, state):
        if not self.npc:
            return None
        r = self.record(state)
        return None if r is None else self.text(r[0])

    def option_text(self, state, i):
        if not self.npc:
            return None
        r = self.record(state)
        return None if r is None or not r[1 + 2*i] else self.text(r[1 + 2*i])

    def option_next(self, state, i):
        if not self.npc:
            return 0
        r = self.record(state)
        return -1 if r is None or not r[1 + 2*i] else r[2 + 2*i]

    def select(self, state, i):
        n = self.option_next(state, i)
        if n <= 900 and n != -1:
            return (0, n)
        if 901 <= n <= 920:
            return (1, n)
        return (0, 999)


def synthetic(rng):
    words, ids = bytearray(), []
    for k in range(120):
        wid = rng.randrange(1, 3000)
        ids.append(wid)
        text = bytes(rng.choice(b'abcdefgh ;.') for _ in range(rng.randint(0, 60)))
        if rng.random() < 0.8:
            text += b'\0'                         # most texts carry their NUL; the others reuse the buffer
        words += struct.pack('<ih', wid, len(text)) + text
    records = bytearray()
    for k in range(80):
        npc, state = rng.choice([0x101, 0x21f, 0x248, 0x2fc]), rng.randrange(0, 30)
        values = [(npc << 16) + state, rng.choice(ids + [0, 99999])]
        for i in range(10):
            text = rng.choice(ids + [0, 0, 0]) if i < 6 else 0
            values += [text, rng.choice([0, 1, 2, 5, 899, 900, 901, 910, 920, 921, 999, -1, -7])]
        records += struct.pack('<22i', *values)
    return bytes(records), bytes(words)


class DialogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = build()

    def tables(self, records, words):
        t = ctypes.create_string_buffer(64)
        self.lib.mu_dlg_parse_records(t, records, len(records))
        self.lib.mu_dlg_parse_words(t, words, len(words))
        self.addCleanup(self.lib.mu_dlg_free, t)
        return t

    def test_lookups_and_choice_match_the_model(self):
        for seed in range(4):
            records, words = synthetic(random.Random(seed))
            t, model = self.tables(records, words), Model(records, words)
            for wid in list(model.words)[:60] + [0, -1, 123456]:
                self.assertEqual(self.lib.mu_dlg_text(t, wid), model.text(wid))
            for npc in (0, 0x101, 0x21f, 0x248, 0x2fc, 0x333):
                self.lib.mu_dlg_set_npc(t, npc)
                model.npc = npc
                for state in list(range(0, 31)) + [999, -1]:
                    self.assertEqual(self.lib.mu_dlg_state_text(t, state), model.state_text(state), (npc, state))
                    for i in range(10):
                        self.assertEqual(self.lib.mu_dlg_option_text(t, state, i), model.option_text(state, i))
                        self.assertEqual(self.lib.mu_dlg_option_next(t, state, i), model.option_next(state, i))
                        v = self.lib.mu_dlg_select(t, state, i)
                        got = (v & 0xffffffff, struct.unpack('<i', struct.pack('<I', v >> 32))[0])
                        self.assertEqual(got, model.select(state, i), (npc, state, i))

    def test_first_insert_wins_and_the_buffer_is_reused(self):
        rec = struct.pack('<22i', (0x248 << 16) + 0, 10, 11, 1, *([0] * 18))
        rec2 = struct.pack('<22i', (0x248 << 16) + 0, 12, *([0] * 20))
        words = (struct.pack('<ih', 10, 6) + b'long!\0' + struct.pack('<ih', 11, 2) + b'ab' +
                 struct.pack('<ih', 10, 3) + b'no\0' + struct.pack('<ih', 12, -1))
        t = self.tables(rec + rec2 + b'\x01\x02', words)
        self.lib.mu_dlg_set_npc(t, 0x248)
        self.assertEqual(self.lib.mu_dlg_state_text(t, 0), b'long!')           # first record, first text
        self.assertEqual(self.lib.mu_dlg_option_text(t, 0, 0), b'abng!')       # no NUL: the earlier bytes follow
        self.assertIsNone(self.lib.mu_dlg_text(t, 12))                          # a negative length stops the parse
        self.assertEqual(self.lib.mu_dlg_option_count(t, 0), 1)

    def test_npc_zero_and_absent(self):
        t = self.tables(struct.pack('<22i', (5 << 16) + 1, 1, 1, 3, *([0] * 18)), struct.pack('<ih', 1, 2) + b'x\0')
        self.assertEqual(self.lib.mu_dlg_option_next(t, 1, 0), 0)     # NPC 0: 0x00fdcb2f returns 0
        self.assertIsNone(self.lib.mu_dlg_state_text(t, 1))
        self.lib.mu_dlg_set_npc(t, 5)
        self.assertEqual(self.lib.mu_dlg_option_next(t, 1, 0), 3)
        self.assertEqual(self.lib.mu_dlg_option_next(t, 2, 0), -1)    # absent record
        self.assertEqual(self.lib.mu_dlg_option_next(t, 1, 1), -1)    # option text id 0
        self.assertEqual([a for a in range(895, 925) if self.lib.mu_dlg_action_closes(a)],
                         [902, 910, 915, 916, 917, 918, 919, 920])


if __name__ == '__main__':
    unittest.main()
