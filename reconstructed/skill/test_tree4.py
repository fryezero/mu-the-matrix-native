"""Portable checks of reconstructed/skill/tree4.c (NATIVE-SKILL-003) over a synthetic 4ThTreeData (no client
data): the row parser's rules, the group states (roots, links, availability, level propagation, branches), the
window's invokes, the click's checks and the 7E answers, stated independently of the C.  The client comparison
is scripts/validate_skill_later.py."""
import ctypes
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
EXT = 'dylib' if sys.platform == 'darwin' else 'so'
LIB = HERE/f'libclientskill.{EXT}'

SKILL_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int),
                            ctypes.POINTER(ctypes.c_int))
HAS_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32)
TEXT_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)
INVOKE_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p)
BOX_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p)
CONFIRM_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p)
EVENT_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int32)
SIDE_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32)
POPUP_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)
NAME_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)


class EnvC(ctypes.Structure):
    _fields_ = [('user', ctypes.c_void_p), ('skill_info', SKILL_FN), ('hero_has', HAS_FN), ('master_level', HAS_FN),
                ('text', TEXT_FN), ('invoke', INVOKE_FN), ('msgbox', BOX_FN), ('confirm', CONFIRM_FN),
                ('event', EVENT_FN), ('side_category', SIDE_FN), ('popup_shows_tree', POPUP_FN),
                ('skill_name', NAME_FN)]


def row(index, group, type_=0, sibling=None, skill=None, children=(), shown=None, cost=1, max_level=20, opens=10,
        req=(-1, -1), pre1=(-1, -1), pre2=(-1, -1)):
    """A file row: 8 columns, five (child, shown) pairs, 9 columns."""
    links = list(children) + [-1] * (5 - len(children))
    shown = shown or [1] * 5
    cols = [index, group, type_, index if sibling is None else sibling, skill or 1000 + index, -1, 1, 7]
    for c, s in zip(links, shown):
        cols += [c, s]
    return cols + [cost, max_level, opens, req[0], req[1], pre1[0], pre1[1], pre2[0], pre2[1]]


class Tree4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(HERE)], check=True)
        cls.L = L = ctypes.CDLL(str(LIB))
        L.mu_t4_table_init.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        L.mu_t4_table_class.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        L.mu_t4_table_row.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32), ctypes.c_int]
        L.mu_t4_table_get.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32]
        L.mu_t4_table_get.restype = ctypes.POINTER(ctypes.c_int32 * 28)
        L.mu_t4_window_init.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        for name in ('mu_t4_build', 'mu_t4_refresh_all'):
            getattr(L, name).argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        for name in ('mu_t4_show_page', 'mu_t4_change_tab', 'mu_t4_click'):
            getattr(L, name).argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]
        L.mu_t4_set_class.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        L.mu_t4_receive.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
        L.mu_t4_confirm.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_uint8),
                                    ctypes.POINTER(ctypes.c_uint16), ctypes.POINTER(ctypes.c_uint16)]
        L.mu_t4_request.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_uint8, ctypes.c_uint16, ctypes.c_uint16]
        L.mu_t4_request.restype = ctypes.c_size_t
        L.mu_t4_dump.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
        L.mu_t4_dump.restype = ctypes.c_size_t

    def setUp(self):
        self.table = ctypes.create_string_buffer(64)
        self.window = ctypes.create_string_buffer(8192)
        self.log, self.has, self.master, self.use = [], set(), {}, {}

    def load(self, rows, classes=(0,), min_columns=22):
        L = self.L
        L.mu_t4_table_init(self.table, min_columns)
        for c in classes:
            L.mu_t4_table_class(self.table, c)
        out = []
        for cls, cols in rows:
            arr = (ctypes.c_int32 * len(cols))(*cols)
            out.append(L.mu_t4_table_row(self.table, cls, arr, len(cols)))
        return out

    def env(self):
        def skill(u, s, b0, use):
            b0[0], use[0] = (0, self.use[s]) if s in self.use else (1, 0)
            return 1

        def invoke(u, name, args):
            self.log.append(('invoke', name.decode(), json.loads(args.decode('latin1'))))
        texts = {k: ctypes.create_string_buffer(v) for k, v in (
            (0x144d, b'Skill Point: %d'), (0xcff, b'requirements'), (0xcfe, b'max'), (0x912, b'points'),
            (0x6eb, b'Strengthen?'), (0x143f, b'Cost: %d'), (-1, b''))}
        self._texts = texts
        self._keep = [SKILL_FN(skill), HAS_FN(lambda u, s: int(s in self.has)),
                      HAS_FN(lambda u, s: self.master.get(s, 0)), TEXT_FN(lambda u, i: ctypes.addressof(texts.get(i, texts[-1]))),
                      INVOKE_FN(invoke), BOX_FN(lambda u, t: self.log.append(('msgbox', t.decode()))),
                      CONFIRM_FN(lambda u, i, t: self.log.append(('confirm', i, t.decode()))),
                      EVENT_FN(lambda u, w, a: None), SIDE_FN(lambda u, i, g: -1), POPUP_FN(lambda u: 0),
                      NAME_FN(lambda u, k: ctypes.addressof(texts[-1]))]
        return EnvC(None, *self._keep)

    def state(self):
        n = self.L.mu_t4_dump(self.window, None, 0)
        buf = ctypes.create_string_buffer(n + 1)
        self.L.mu_t4_dump(self.window, buf, n + 1)
        return json.loads(buf.value.decode())

    def build(self, cls=0):
        self.e = self.env()
        self.L.mu_t4_window_init(self.window, self.table)
        self.L.mu_t4_set_class(self.window, cls)
        self.L.mu_t4_build(self.window, ctypes.byref(self.e))
        return self.state()

    def test_rows(self):
        r = self.load([(0, row(0, 0)), (0, row(0, 0, cost=9)), (1, row(1, 0)), (0, row(12, 0)[:26]),
                       (0, row(13, 0)[:21])], classes=(0,))
        self.assertEqual(r, [1, 1, 0, 0, 0])            # repeated index kept, unknown class / short rows refused
        rec = list(self.L.mu_t4_table_get(self.table, 0, 0, 0).contents)
        self.assertEqual(rec[18], 1)                    # the first record of the index stays
        self.load([(0, row(37, 2, children=(40, 41), shown=[1, 0, 1, 1, 1]))])
        rec = list(self.L.mu_t4_table_get(self.table, 0, 2, 37).contents)
        self.assertEqual(rec[8:13], [40, 41, -1, -1, -1])   # the link pairs as two arrays
        self.assertEqual(rec[13:18], [1, 0, 1, 1, 1])
        self.assertFalse(self.L.mu_t4_table_get(self.table, 0, 2, 38))
        g = self.build()['groups'][0]
        self.assertEqual(g['rows'], 4)                  # max(index / 10 + 1)

    def test_roots_links_and_availability(self):
        self.load([(0, row(0, 0, children=(1, 20), req=(500, 1))), (0, row(1, 0, children=(2,))),
                   (0, row(2, 0)), (0, row(20, 0, type_=3, children=(21, 22))), (0, row(21, 0, type_=2)),
                   (0, row(22, 0)), (0, row(30, 0, req=(501, 10)))])
        self.use = {500: 0, 501: 4}
        self.has = {500}
        self.master = {501: 9}
        g = self.build()['groups'][0]
        nodes = {n[0]: n for n in g['nodes']}
        self.assertEqual(g['roots'], [0, 30])           # index % 10 == 0, not a branch (type 3)
        self.assertEqual(g['kind'], 2)                  # a type-2 record
        self.assertEqual(nodes[0][6], 1)                # requirement learned
        self.assertEqual(nodes[30][6], 0)               # master level 9 < 10
        self.assertEqual(nodes[0][9], [1, 20])
        self.assertEqual(nodes[21][8], [20])
        self.assertEqual(nodes[2][1], 1)                # a leaf
        self.assertEqual(nodes[0][1], 0)

    def test_level_propagation(self):
        self.load([(0, row(0, 0, children=(1, 2), opens=2)), (0, row(1, 0, sibling=7)), (0, row(2, 0, sibling=7)),
                   (0, row(3, 0, pre1=(1000, 5)))])
        self.build()
        pkt = bytes([0xc1, 0, 0x7e, 2, 0]) + struct.pack('<HI', 3, 2)
        pkt += struct.pack('<BHBff', 0, 0, 2, 1.5, 2.5) + struct.pack('<BHBff', 0, 1, 1, 0, 0)
        self.L.mu_t4_receive(self.window, ctypes.byref(self.e), pkt, len(pkt))
        nodes = {n[0]: n for n in self.state()['groups'][0]['nodes']}
        self.assertEqual(nodes[0][3:6], [2, 1.5, 2.5])
        self.assertEqual(nodes[1][6], 1)                # opened by the parent's level 2, learnable
        self.assertEqual(nodes[2][6], 0)                # its sibling learned level 1 >= cost: closed
        self.assertEqual(nodes[3][6], 0)                # the prerequisite (skill 1000, level 5) is not met

    def test_window_and_click(self):
        self.load([(0, row(0, 0, children=(1,), opens=1, cost=2, max_level=3)), (0, row(1, 0)), (0, row(10, 5, type_=2))])
        self.build()
        tabs = [e for e in self.log if e[1] == 'SetTabInfo'][0][2]
        self.assertEqual(tabs, [[{'TabIndex': 0, 'GroupIndexList': [0]}, {'TabIndex': 2, 'GroupIndexList': [5]}]])
        self.log.clear()
        self.L.mu_t4_show_page(self.window, ctypes.byref(self.e), 0)
        names = [e[1] for e in self.log]
        self.assertEqual(names[:3], ['SetCurrentPage', 'SetSkillSlots', 'SetSkillSlotLinkInfo'])
        slots = self.log[1][2][0]
        self.assertEqual(slots['SlotInfo'][0], {'Index': 0, 'CurrentPoint': 0, 'MaxPoint': 3, 'Type': 0, 'SlotBG': 1})
        self.assertEqual(slots['LinkInfo'][:1], [{'From': 0, 'To': 1, 'LinkState': 2}])
        self.assertEqual(len(slots['LinkInfo']), 10)    # sized nodes x 5, the rest undefined
        self.log.clear()
        self.L.mu_t4_click(self.window, ctypes.byref(self.e), 0)
        self.assertEqual(self.log, [('msgbox', 'points')])  # 0 points < cost 2
        ctypes.c_int32.from_buffer(self.window, ctypes.sizeof(ctypes.c_void_p) + 4).value = 2
        self.log.clear()
        self.assertEqual(self.L.mu_t4_click(self.window, ctypes.byref(self.e), 0), 1)
        self.assertEqual(self.log, [('confirm', 0x73, 'Strengthen?\nCost: 2')])
        g, s, i = ctypes.c_uint8(), ctypes.c_uint16(), ctypes.c_uint16()
        self.assertEqual(self.L.mu_t4_confirm(self.window, 0, ctypes.byref(g), ctypes.byref(s), ctypes.byref(i)), 1)
        out = ctypes.create_string_buffer(16)
        n = self.L.mu_t4_request(out, 16, g.value, s.value, i.value)
        self.assertEqual(out.raw[:n], bytes([0xc1, 9, 0x7e, 1, 0, 0xe8, 0x03, 0, 0]))
        self.assertEqual(self.state()['pend'], [-1, -1])
        self.log.clear()
        ans = bytes([0xc1, 0x13, 0x7e, 1, 1]) + struct.pack('<HBBHff', 0, 0, 3, 0, 3, 4)
        self.L.mu_t4_receive(self.window, ctypes.byref(self.e), ans, len(ans))
        self.assertIn(('invoke', 'SetSkillPoint', [0, 3]), self.log)
        self.log.clear()
        self.L.mu_t4_click(self.window, ctypes.byref(self.e), 0)
        self.assertEqual(self.log, [('msgbox', 'max')])     # level 3 of 3
        for result, text in ((4, 'requirements'), (7, 'points')):
            self.log.clear()
            ans = bytes([0xc1, 5, 0x7e, 1, result])
            self.L.mu_t4_receive(self.window, ctypes.byref(self.e), ans, len(ans))
            self.assertEqual(self.log, [('msgbox', text)])


if __name__ == '__main__':
    unittest.main()
