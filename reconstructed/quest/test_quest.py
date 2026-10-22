"""Portable checks of the quest system (reconstructed/quest, NATIVE-QUEST-001).

The client comparison is scripts/validate_quest.py (Unicorn, private captures
and a live snapshot).  These checks build libquest and drive it with
synthetic MUQuest / MUQuestString / ItemLevelTooltip plaintext: the category
rule, first-wins parsing with the converter's escapes, the dialogue assembly
(last title wins, pages in string-index order), the goal and reward texts
and the HTML line against an independent Python statement, the quest packets
(accept, progress, complete, list, values) and the windows' event log
(NpcQuestProgress pages and the accept request, MyQuestInfo's list).
"""
import ctypes
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
LIB = HERE/('libquest.dylib' if sys.platform == 'darwin' else 'libquest.so')

TEXT_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)   # returns a kept buffer's address
KIND_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32)


class Host(ctypes.Structure):
    _fields_ = [('user', ctypes.c_void_p), ('data', ctypes.c_void_p), ('text', TEXT_FN), ('npc_name', TEXT_FN),
                ('map_name', TEXT_FN), ('item_name', TEXT_FN), ('item_kind', KIND_FN), ('item_byte', KIND_FN),
                ('to_utf8', ctypes.c_void_p),
                # NATIVE-QUEST-002 (NULL)
                ('item_record_name', ctypes.c_void_p), ('measure', ctypes.c_void_p), ('path_reset', ctypes.c_void_p),
                ('path_start', ctypes.c_void_p), ('send_move', ctypes.c_void_p), ('helper_running', ctypes.c_void_p),
                ('helper_available', ctypes.c_void_p), ('classic_item', ctypes.c_void_p),
                ('classic_kills', ctypes.c_void_p)]


class Data(ctypes.Structure):
    _fields_ = [('records', ctypes.c_void_p), ('nrecords', ctypes.c_size_t), ('strings', ctypes.c_void_p),
                ('nstrings', ctypes.c_size_t), ('level_tips', ctypes.c_void_p), ('nlevel_tips', ctypes.c_size_t),
                # NATIVE-QUEST-002: the guide tables and the classic quests
                ('guide_chapters', ctypes.c_void_p), ('nguide_chapters', ctypes.c_size_t),
                ('guide_titles', ctypes.c_void_p), ('nguide_titles', ctypes.c_size_t),
                ('guide_names', ctypes.c_void_p), ('nguide_names', ctypes.c_size_t), ('classic', ctypes.c_void_p)]


class Line(ctypes.Structure):
    _fields_ = [('font', ctypes.c_uint32), ('color', ctypes.c_uint32), ('text', ctypes.c_char * 1024)]


class Dialogue(ctypes.Structure):
    _fields_ = [('index', ctypes.c_int32), ('title', ctypes.c_char_p), ('progress', ctypes.c_char_p),
                ('complete', ctypes.c_char_p), ('summary', ctypes.c_char_p),
                ('pages', ctypes.POINTER(ctypes.c_char_p)), ('npages', ctypes.c_int32)]


GT = {0x551: b'None', 0x1244: b'Obtained', 0x1077: b'Elimination', 0xafc: b'Minimum', 0xcb1: b'Finding an NPC',
      0x153d: b'Talk to NPC', 0x153f: b'Use Card Deck x %d time(s) / %d', 0x153c: b'Hunt monsters in %s x %d / %d',
      0x1078: b'Item.', 0xbb2: b'Contribution: %lu', 0x40d: b'Yes', 0x1521: b'Accept', 0x40e: b'No',
      0xaf9: b'Requirements', 0xafa: b'Reward', 0xd84: b'NPC Quest', 0x3ea: b'Close', 0x119f: b'Complete',
      0xe4: b'OK', 0x118b: b'Not enough zen.', 0x474: b'Quest', 0xb09: b'There are no active quests.',
      0x1522: b'Tutorial Quest', 0xe81: b'(Fire element)'}
NPCS = {257: b'Shadow Phantom Soldier', 589: b'Devil Fairy'}


def ints(values, n):
    return ' '.join(str(v) for v in (list(values) + [0] * n)[:n])


def record_line(index, name, accept, goal):
    return f'{index}\t{name}\t0\t0\t{ints(accept, 30)}\t{ints(goal, 26)}\n'


def accept_block(group=1, npc=257, kind=1):
    return [0, group, 2, 1, kind, npc, 5, 1700, 0, -1, -1, -1, -1, 0] + [1] * 16


def goal_block(kind=2, a=589, b=-1, need=30, world=0, exp=0, zen=0, contribution=0, items=()):
    g = [1, kind, a, b, need, -1, -1, 0, world, 0, 0, exp, zen, contribution] + [-1] * 12
    for i, (group, index, level) in enumerate(items):
        g[14 + 3 * i:17 + 3 * i] = [group, index, level]
    return g


RECORDS = (
    '# comment line\n' +
    record_line(5, 'Hunt the fairies', accept_block(group=8), goal_block(kind=2, a=589, need=30, exp=100000,
                                                                          items=[(12, 145, 1)])) +
    record_line(7, 'Bring an apple', accept_block(), goal_block(kind=1, a=14, b=23, need=2, zen=500)) +
    record_line(5, 'duplicate keeps the first', accept_block(), goal_block()) +
    record_line(250, 'Reward\\tquest', accept_block(group=15, kind=2), goal_block(kind=8, world=3, need=80,
                                                                                  contribution=7)) +
    record_line(450, 'Repeat', accept_block(), goal_block(kind=7, need=5)) +
    record_line(820, 'Odd', accept_block(), goal_block(kind=17)))
STRINGS = (
    '10\t1\t5\tFirst title\n'
    '11\t1\t5\tFairy hunt\n'
    '14\t2\t5\tPage two;more\n'
    '12\t2\t5\tPage one\n'
    '15\t3\t5\tNot done yet.\n'
    '16\t4\t5\tWell done.\n'
    '17\t5\t5\tSummary of 5\n'
    '20\t1\t7\tApples\n'
    '21\t2\t7\tPlease bring\\x80 apples\n'
    '30\t1\t250\tAtlans\n')
TIPS = '0\t14\t23\t0\tApple of Wisdom\n1\t12\t145\t1\tFairy Wing\n'


def build():
    subprocess.run(['make', '-C', str(HERE), '-s'], check=True)
    L = ctypes.CDLL(str(LIB))
    for name in ('mu_quest_parse_records', 'mu_quest_parse_strings', 'mu_quest_parse_level_tips'):
        getattr(L, name).argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        getattr(L, name).restype = ctypes.c_long
    L.mu_quest_category.argtypes = [ctypes.c_int32]
    L.mu_quest_category.restype = ctypes.c_int32
    L.mu_quest_client_size.restype = ctypes.c_size_t
    L.mu_quest_client_init.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    L.mu_quest_client_free.argtypes = [ctypes.c_void_p]
    L.mu_quest_log_text.argtypes = [ctypes.c_void_p]
    L.mu_quest_log_text.restype = ctypes.c_char_p
    L.mu_quest_client_log_clear.argtypes = [ctypes.c_void_p]
    L.mu_quest_receive.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
    L.mu_quest_fields.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)]
    L.mu_quest_set_fields.argtypes = [ctypes.c_void_p] + [ctypes.c_int32] * 4
    L.mu_quest_maps_text.argtypes = [ctypes.c_void_p]
    L.mu_quest_maps_text.restype = ctypes.c_char_p
    L.mu_quest_get.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    L.mu_quest_get.restype = ctypes.c_void_p
    L.mu_quest_dialogue_get.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    L.mu_quest_dialogue_get.restype = ctypes.c_void_p
    L.mu_quest_condition.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(Line)]
    L.mu_quest_reward.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                                  ctypes.POINTER(Line)]
    L.mu_quest_html_line.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_int, ctypes.c_char_p,
                                     ctypes.c_size_t]
    L.mu_quest_client_field.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int32]
    L.mu_quest_client_field.restype = ctypes.c_int32
    for name in ('mu_quest_progress_set', 'mu_quest_progress_select'):
        getattr(L, name).argtypes = [ctypes.c_void_p, ctypes.c_int32]
    for name in ('mu_quest_progress_open', 'mu_quest_progress_refresh', 'mu_quest_progress_confirm',
                 'mu_quest_info_open', 'mu_quest_info_close'):
        getattr(L, name).argtypes = [ctypes.c_void_p]
    L.mu_quest_info_select_tab.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    L.mu_quest_set_hero.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    return L


class QuestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = build()

    def setUp(self):
        L = self.L
        self.data = Data()
        self.assertEqual(L.mu_quest_parse_records(ctypes.byref(self.data), RECORDS.encode()), 5)
        self.assertEqual(L.mu_quest_parse_strings(ctypes.byref(self.data), STRINGS.encode()), 10)
        self.assertEqual(L.mu_quest_parse_level_tips(ctypes.byref(self.data), TIPS.encode()), 2)
        self.keep = {}
        self.items = {14 * 512 + 23: b'Apple', 12 * 512 + 145: b'Wing'}
        self.kinds = {}
        h = self.host = Host()
        h.text = TEXT_FN(lambda u, i: self._keep(('t', i), GT.get(i)))
        h.npc_name = TEXT_FN(lambda u, i: self._keep(('n', i), NPCS.get(i, b'')))
        h.map_name = TEXT_FN(lambda u, i: self._keep(('m', i), b'Map %d' % i))
        h.item_name = TEXT_FN(lambda u, i: self._keep(('i', i), self.items.get(i, b'')))
        h.item_kind = KIND_FN(lambda u, c, k: self.kinds.get((c, k), 0))
        h.item_byte = KIND_FN(lambda u, c, k: 0)
        h.data = ctypes.addressof(self.data)
        self.c = ctypes.create_string_buffer(L.mu_quest_client_size())
        self.assertEqual(L.mu_quest_client_init(self.c, ctypes.byref(self.data), ctypes.byref(h)), 0)
        L.mu_quest_set_hero(self.c, b'Nighty')

    def tearDown(self):
        self.L.mu_quest_client_free(self.c)

    def _keep(self, key, value):
        if value is None:
            return None
        if key not in self.keep or self.keep[key].value != value:
            self.keep[key] = ctypes.create_string_buffer(value)
        return ctypes.addressof(self.keep[key])

    def log(self):
        text = self.L.mu_quest_log_text(self.c).decode('latin1').splitlines()
        self.L.mu_quest_client_log_clear(self.c)
        return text

    def fields(self, index):
        out = (ctypes.c_int32 * 4)()
        return list(out) if self.L.mu_quest_fields(self.c, index, out) else None

    def test_category(self):
        def model(i):
            if 1 <= i <= 199:
                return 2
            if i < 400:
                return 3
            if i < 600:
                return 4
            return 3 if i < 1000 else -1
        for i in list(range(-5, 1005)) + [random.Random(1).randint(-10**6, 10**6) for _ in range(100)]:
            self.assertEqual(self.L.mu_quest_category(i), model(i), i)

    def test_parse_and_dialogue(self):
        self.assertIsNotNone(self.fields(5))
        self.assertEqual(self.fields(5)[3], 2)
        self.assertEqual(self.fields(250)[3], 3)
        self.assertEqual(self.fields(450)[3], 4)
        self.assertIsNone(self.fields(6))
        g = Dialogue.from_address(self.L.mu_quest_dialogue_get(self.c, 5))
        self.assertEqual(g.title, b'Fairy hunt')               # the last title of the quest wins
        self.assertEqual([g.pages[i] for i in range(g.npages)], [b'Page one', b'Page two;more'])
        self.assertEqual((g.progress, g.complete, g.summary), (b'Not done yet.', b'Well done.', b'Summary of 5'))
        g7 = Dialogue.from_address(self.L.mu_quest_dialogue_get(self.c, 7))
        self.assertEqual(g7.pages[0], b'Please bring\x80 apples')   # \xHH escape kept as the byte

    def test_texts(self):
        L = self.L
        line = Line()
        q5 = L.mu_quest_get(self.c, 5)
        L.mu_quest_set_fields(self.c, 5, 1, 12, 0)
        L.mu_quest_condition(ctypes.byref(self.host), q5, 0x1111, ctypes.byref(line))
        self.assertEqual((line.font, line.color, line.text), (0x1111, 0xff1e1eff, b'Devil Fairy Elimination x 12/30'))
        L.mu_quest_set_fields(self.c, 5, 2, 30, 0)
        L.mu_quest_condition(ctypes.byref(self.host), q5, 0x1111, ctypes.byref(line))
        self.assertEqual(line.color, 0xff67bfdf)
        L.mu_quest_reward(ctypes.byref(self.host), q5, 0x1111, 0x2222, ctypes.byref(line))
        self.assertEqual((line.font, line.text), (0x2222, b'Exp.: 100000\nItem.: Fairy Wing'))   # level tip names it
        q7 = L.mu_quest_get(self.c, 7)
        L.mu_quest_condition(ctypes.byref(self.host), q7, 0, ctypes.byref(line))
        self.assertEqual(line.text, b'Apple Obtained x 0/2')
        L.mu_quest_reward(ctypes.byref(self.host), q7, 0, 0, ctypes.byref(line))
        self.assertEqual(line.text, b'Zen: 500')
        q250 = L.mu_quest_get(self.c, 250)
        L.mu_quest_condition(ctypes.byref(self.host), q250, 0, ctypes.byref(line))
        self.assertEqual(line.text, b'Hunt monsters in Map 3 x 0 / 80')
        L.mu_quest_reward(ctypes.byref(self.host), q250, 0, 0, ctypes.byref(line))
        self.assertEqual(line.text, b'Contribution: 7')
        q820 = L.mu_quest_get(self.c, 820)
        L.mu_quest_condition(ctypes.byref(self.host), q820, 0, ctypes.byref(line))
        self.assertEqual((line.color, line.text), (0xff67bfdf, b'None'))     # an unknown goal type
        self.kinds[(12 * 512 + 145, 0x19)] = 1                               # an element item
        L.mu_quest_reward(ctypes.byref(self.host), q5, 0, 0, ctypes.byref(line))
        self.assertEqual(line.text, b'Exp.: 100000\nItem.: Wing (Fire element) x 1')

    def test_html(self):
        buf = ctypes.create_string_buffer(512)
        self.L.mu_quest_html_line(b'a<b', 0xff67bfdf, 0, 1, buf, 512)
        self.assertEqual(buf.value, b"<font color='#dfbf67'>a&lt;b</font><BR>")
        self.L.mu_quest_html_line(b'x', 0xff1e1eff, 1, 0, buf, 512)
        self.assertEqual(buf.value, b"<font color='#ff1e1e'><b>x</b></font>")
        self.L.mu_quest_html_line(b'\n', 0, 0, 1, buf, 512)
        self.assertEqual(buf.value, b'')

    def test_accept_flow(self):
        L = self.L
        # the NPC's pages, then the accept request when none is left
        L.mu_quest_progress_set(self.c, 5)
        lines = self.log()
        self.assertIn('invoke NpcQuestProgress SetQuestMentDivide ["Page one","#"]', lines)
        L.mu_quest_progress_open(self.c)
        lines = self.log()
        self.assertIn('invoke NpcQuestProgress SetSelectBtnContent ["1. Yes;2. No;"]', lines)
        self.assertIn('invoke NpcQuestProgress SetUIOpenText ["NPC Quest","Fairy hunt","Shadow Phantom Soldier","Nighty"]',
                      lines)
        L.mu_quest_progress_select(self.c, 0)
        self.assertIn('invoke NpcQuestProgress SetSelectBtnContent ["1. Accept;2. No;"]', self.log())
        L.mu_quest_progress_select(self.c, 0)
        self.assertEqual(self.log(), ['send c1 08 f6 72 08 00 05 00 | 1 0'])
        # the server's answer: in progress, the conditions shown, the quest active
        self.assertEqual(L.mu_quest_receive(self.c, bytes.fromhex('c109f67200000500') + b'\0', 9), 1)
        self.assertEqual(self.fields(5)[:2], [1, 0])
        lines = self.log()
        self.assertIn('invoke NpcQuestProgress SetQuestMentDivide ["Not done yet.","#"]', lines)
        self.assertIn('active2:5,', L.mu_quest_maps_text(self.c).decode())
        # progress to complete, then the complete request and its answer
        L.mu_quest_receive(self.c, bytes.fromhex('c10bf67500000500') + struct.pack('<HB', 30, 2)[0:2] + b'\x02', 11)
        self.assertEqual(self.fields(5)[:2], [2, 30])
        self.assertIn('invoke NpcQuestProgress InitText ["Complete"]', self.log())
        L.mu_quest_progress_confirm(self.c)
        self.assertEqual(self.log(), ['send c1 0a f6 74 01 01 08 00 05 00 | 1 0'])
        L.mu_quest_receive(self.c, bytes.fromhex('c109f67400000500') + b'\0', 9)
        self.assertEqual(self.log(), ['send c1 03 54 | 0 0', 'hide NpcQuestProgress'])
        self.assertNotIn('5,', L.mu_quest_maps_text(self.c).decode().split('active2:')[1].split(' ')[0])

    def test_list_values_and_info(self):
        L = self.L
        body = bytearray(b'\xc1\x00\xf6\x70' + struct.pack('<H', 2))
        body += struct.pack('<HHHHBB', 0, 7, 0, 1, 1, 0) + struct.pack('<HHHHBB', 0, 5, 0, 30, 2, 1)
        body += bytes(4)
        body[1] = len(body)
        L.mu_quest_receive(self.c, bytes(body), len(body))
        self.assertEqual(self.fields(7)[:3], [1, 1, 0])
        self.assertEqual(self.fields(5)[:3], [2, 30, 1])
        maps = L.mu_quest_maps_text(self.c).decode()
        self.assertIn('items:7191=1,', maps)                    # the item goal of quest 7 (14 * 512 + 23)
        self.assertIn('active2:5,7,', maps)
        L.mu_quest_receive(self.c, b'\xc1\x0c\xf6\x82\0\0' + struct.pack('<HI', 7, 99), 12)
        self.assertIn('values:7=99,', L.mu_quest_maps_text(self.c).decode())
        L.mu_quest_receive(self.c, b'\xc1\x09\xf6\x83\0\0' + struct.pack('<HB', 7, 0), 9)
        self.assertIn('values: ', L.mu_quest_maps_text(self.c).decode())
        self.log()
        L.mu_quest_info_open(self.c)
        L.mu_quest_info_select_tab(self.c, 2)
        lines = self.log()
        listing = [l for l in lines if l.startswith('value MyQuestInfo SetMyQuestList')][-1]
        items = json.loads(listing.split(' ', 3)[3])[0]
        self.assertEqual([(i['QuestIndex'], i['Name'], i['NewQuest']) for i in items],
                         [(5, '1. Fairy hunt', False), (7, '2. Apples', True)])


if __name__ == '__main__':
    unittest.main()
