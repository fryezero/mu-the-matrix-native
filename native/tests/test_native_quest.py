"""Quests in the native client (NATIVE-QUEST-001) checks.

Portable (synthetic data only):
  * the quest session (core/mu_quest over reconstructed/quest, build/libmuquest)
    on synthetic quest tables: the NPC's quest list request and the demo
    server's F6 71 answer filling npcdialogue's list ("1. [Q]title"), the
    choice opening NpcQuestProgress with its pages, the accept request after
    the last page, the server's acceptance (state 1, the conditions and
    rewards), monster kills counting to state 2, the complete request and its
    answer closing the window and removing the quest, the give-up request and
    MyQuestInfo's list; every effect reaches the host in order;
  * mu-walk on the synthetic world: a demo row `dialog` answers the talk with
    the NPC dialogue packet F9 01 (npcdialogue for the dialogue NPC, no
    ReceiveTalk: no close-all, no sounds); malformed rows are refused.
Private (MU_RECOVERY_INTEGRATION=1): with MU_QUEST_SNAPSHOT (a langread
snapshot taken with the quest options) scripts/validate_quest.py with its
planted mistakes; with MU_GAME_ROOT, MU_LANG_DIR, MU_GFX_LIB and
MU_QUEST_MOVIES the Lorencia quest demo in mu-world (accept, kills, complete).
"""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
ROOT = NATIVE.parent
sys.path.insert(0, str(HERE))
from test_native_npc import write_npc_world, run  # noqa: E402

LIB = NATIVE/('build/libmuquest.dylib' if sys.platform == 'darwin' else 'build/libmuquest.so')
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'

EVENT_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p)
TEXT_FN = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)
KIND_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32)


class Host(ctypes.Structure):
    _fields_ = [('user', ctypes.c_void_p), ('data', ctypes.c_void_p), ('text', TEXT_FN), ('npc_name', TEXT_FN),
                ('map_name', TEXT_FN), ('item_name', TEXT_FN), ('item_kind', KIND_FN), ('item_byte', KIND_FN),
                ('to_utf8', ctypes.c_void_p)]


def ints(values, n):
    return ' '.join(str(v) for v in (list(values) + [0] * n)[:n])


ACCEPT = [0, 1, 2, 1, 2, 257, 5, 1700, 0, -1, -1, -1, -1, 0] + [1] * 16
HUNT = [1, 2, 2, -1, 3, -1, -1, 0, 0, 0, 0, 250, 1000, 0] + [-1] * 12
TALK = [1, 6, -1, -1, -1, -1, -1, 0, 0, 0, 0, 50, 50, 0] + [-1] * 12
QUESTS = (f'7\tHunt dragons\t0\t0\t{ints(ACCEPT, 30)}\t{ints(HUNT, 26)}\n'
          f'3\tPress C\t0\t0\t{ints(ACCEPT, 30)}\t{ints(TALK, 26)}\n')
STRINGS = ('100\t1\t7\tHunt Budge Dragons\n101\t2\t7\tFirst page\n102\t2\t7\tSecond page\n'
           '103\t3\t7\tNot yet.\n104\t4\t7\tWell done.\n110\t1\t3\tTutorial C\n')
GT = {0x40d: b'Yes', 0x1521: b'Accept', 0x40e: b'No', 0xaf9: b'Requirements', 0xafa: b'Reward', 0xd84: b'NPC Quest',
      0x3ea: b'Close', 0x119f: b'Complete', 0x1077: b'Elimination', 0x551: b'None', 0xb09: b'No quests.'}
DEMO = 'quest 257 7 3\n'


class Session(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), LIB.relative_to(NATIVE).as_posix()], check=True,
                       capture_output=True)
        cls.L = L = ctypes.CDLL(str(LIB))
        L.mu_quest_session_size.restype = ctypes.c_size_t
        L.mu_quest_session_open.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
                                            ctypes.c_char_p, ctypes.c_size_t]
        L.mu_quest_session_client.argtypes = [ctypes.c_void_p]
        L.mu_quest_session_client.restype = ctypes.c_void_p
        L.mu_quest_session_set_event.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        for name in ('mu_quest_session_step', 'mu_quest_session_close', 'mu_quest_session_toggle_info'):
            getattr(L, name).argtypes = [ctypes.c_void_p]
        L.mu_quest_session_npc_list.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        L.mu_quest_session_kill.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32]
        L.mu_quest_dialog_choice.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int)]
        L.mu_quest_progress_select.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        L.mu_quest_progress_confirm.argtypes = [ctypes.c_void_p]
        L.mu_quest_info_giveup_ok.argtypes = [ctypes.c_void_p]
        L.mu_quest_maps_text.argtypes = [ctypes.c_void_p]
        L.mu_quest_maps_text.restype = ctypes.c_char_p
        L.mu_quest_fields.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)]
        L.mu_quest_client_field.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int32]
        L.mu_quest_client_field.restype = ctypes.c_int32
        L.mu_quest_info_callback.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_double),
                                             ctypes.c_int, ctypes.c_char_p]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        (d/'quests.tsv').write_text(QUESTS)
        (d/'queststrings.tsv').write_text(STRINGS)
        self.events = []
        self.keep = {}
        self.event_fn = EVENT_FN(lambda u, line: self.events.append(line.decode('latin1')))
        self.host = Host()
        self.host.text = TEXT_FN(lambda u, i: self._keep(('t', i), GT.get(i)))
        self.host.npc_name = TEXT_FN(lambda u, i: self._keep(('n', i), b'Soldier' if i == 257 else b'Budge Dragon'))
        self.s = ctypes.create_string_buffer(self.L.mu_quest_session_size())
        err = ctypes.create_string_buffer(256)
        self.assertEqual(self.L.mu_quest_session_open(self.s, str(d).encode(), DEMO.encode(), ctypes.byref(self.host),
                                                      err, 256), 0, err.value)
        self.L.mu_quest_session_set_event(self.s, ctypes.cast(self.event_fn, ctypes.c_void_p), None)
        self.c = self.L.mu_quest_session_client(self.s)

    def tearDown(self):
        self.L.mu_quest_session_close(self.s)
        self.tmp.cleanup()

    def _keep(self, key, value):
        if value is None:
            return None
        if key not in self.keep or self.keep[key].value != value:
            self.keep[key] = ctypes.create_string_buffer(value)
        return ctypes.addressof(self.keep[key])

    def steps(self, n=5):
        for _ in range(n):
            self.L.mu_quest_session_step(self.s)

    def take(self):
        out, self.events = self.events, []
        return out

    def fields(self, q):
        f = (ctypes.c_int32 * 4)()
        self.L.mu_quest_fields(self.c, q, f)
        return list(f)

    def test_accept_progress_complete(self):
        L = self.L
        L.mu_quest_session_npc_list(self.s, 257)
        self.assertEqual(self.take(), [])                       # the answer arrives after the demo latency
        self.steps()
        ev = self.take()
        self.assertIn('invoke npcdialogue SetSelectBtnContent ["1. [Q]Hunt Budge Dragons;2. [Q]Tutorial C;"]', ev)
        L.mu_quest_dialog_choice(self.c, 1, None)
        ev = self.take()
        self.assertIn('invoke NpcQuestProgress SetQuestMentDivide ["First page","#"]', ev)
        self.assertIn('show NpcQuestProgress', ev)
        self.assertIn('invoke NpcQuestProgress SetSelectBtnContent ["1. Yes;2. No;"]', ev)
        L.mu_quest_progress_select(self.c, 0)
        self.assertIn('invoke NpcQuestProgress SetSelectBtnContent ["1. Accept;2. No;"]', self.take())
        L.mu_quest_progress_select(self.c, 0)                  # no page left: the accept request
        self.steps()
        ev = self.take()
        self.assertEqual(self.fields(7)[:2], [1, 0])
        self.assertIn('invoke NpcQuestProgress SetQuestMentDivide ["Not yet.","#"]', ev)
        cond = next(e for e in ev if 'SetConditionRewardText' in e)
        self.assertIn('Budge Dragon Elimination x 0/3', cond)
        self.assertIn("#ff1e1e", cond)
        for _ in range(3):
            L.mu_quest_session_kill(self.s, 2, 0)
            self.steps()
        self.assertEqual(self.fields(7)[:2], [2, 3])
        ev = self.take()
        self.assertIn('invoke NpcQuestProgress InitText ["Complete"]', ev)
        self.assertIn("#dfbf67", [e for e in ev if 'SetConditionRewardText' in e][-1])
        L.mu_quest_progress_confirm(self.c)
        self.steps()
        ev = self.take()
        self.assertIn('hide NpcQuestProgress', ev)
        self.assertTrue(any(e.startswith('demo Quest complete') for e in ev))
        f = (ctypes.c_int32 * 4)()
        self.assertEqual(L.mu_quest_client_field(self.c, b'progress.visible', 0, 0), 0)

    def test_talk_goal_and_give_up(self):
        L = self.L
        L.mu_quest_session_npc_list(self.s, 257)
        self.steps()
        L.mu_quest_dialog_choice(self.c, 2, None)              # quest 3: no pages, the accept goes out at once
        self.steps(10)
        self.assertEqual(self.fields(3)[:1], [2])              # a talk goal: done once accepted (demo)
        self.take()
        L.mu_quest_session_toggle_info(self.s)                 # T: MyQuestInfo opens on its first tab (guide)
        v = (ctypes.c_double * 2)(2, 0)
        L.mu_quest_info_callback(self.c, b'OnSelectTab', v, 1, None)
        ev = self.take()
        listing = [e for e in ev if e.startswith('value MyQuestInfo SetMyQuestList')][-1]
        items = json.loads(listing.split(' ', 3)[3])[0]
        self.assertEqual([(i['QuestIndex'], i['Name']) for i in items], [(3, '1. Tutorial C')])
        v = (ctypes.c_double * 2)(0, 3)
        L.mu_quest_info_callback(self.c, b'OnSelectQuest', v, 2, None)
        L.mu_quest_info_giveup_ok(self.c)
        self.assertTrue(any(e.startswith('invoke MyQuestInfo SetConditionReward') for e in self.take()))
        self.assertIn('active2:3,', L.mu_quest_maps_text(self.c).decode())
        self.steps()                                            # C1 F6 73: the demo server's answer removes it
        self.assertIn('active2: ', L.mu_quest_maps_text(self.c).decode() + ' ')


class Packet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        cls.root = write_npc_world(d/'game')
        cls.placement = d/'placement.txt'
        cls.placement.write_text('actor 251 123 120 6 label smith\nactor 240 120 123 4 label vault\n')
        cls.demo = d/'demo.txt'
        cls.demo.write_text('dialog 251 257 5\nquest 257 7\ntalk 240 2\n')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_dialog_row_answers_f9(self):
        out = run(self.root, self.placement, self.demo, '--frames', '60', '--npc-script', '2:talk:smith 30:talk:vault')
        o = out['opens']
        self.assertEqual((o[0]['npc_open'], o[0]['dialogue'], o[0]['dialog_packet'], o[0]['close_all']),
                         ('dialog', 257, 1, 0))
        self.assertEqual(o[1]['dialog_packet'], 0)
        self.assertEqual(out['summary']['sounds'], 2)           # only the vault's ReceiveTalk plays 25 and 28
        self.assertTrue(any('F9 01' in l for l in out['logs']))

    def test_bad_rows(self):
        bad = Path(self.tmp.name)/'bad.txt'
        bad.write_text('dialog 251\n')
        r = run(self.root, self.placement, bad, '--frames', '2', check=False)
        self.assertNotEqual(r['result'].returncode, 0)


@unittest.skipUnless(PRIVATE and os.environ.get('MU_QUEST_SNAPSHOT'), 'needs MU_RECOVERY_INTEGRATION=1 and '
                     'MU_QUEST_SNAPSHOT (a langread snapshot with the quest options)')
class Validator(unittest.TestCase):
    def test_validator(self):
        py = ROOT/'tools/python/bin/python'
        r = subprocess.run([str(py if py.exists() else sys.executable), str(ROOT/'scripts/validate_quest.py'),
                            '--snapshot', os.environ['MU_QUEST_SNAPSHOT'], '--sequences', '20', '--length', '20',
                            '--text-rounds', '1', '--mutations'], capture_output=True, text=True, timeout=1800)
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-2000:])


@unittest.skipUnless(PRIVATE and all(os.environ.get(k) for k in ('MU_GAME_ROOT', 'MU_LANG_DIR', 'MU_GFX_LIB',
                                                                  'MU_QUEST_MOVIES')),
                     'needs MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_LANG_DIR (with quests.tsv), MU_GFX_LIB and '
                     'MU_QUEST_MOVIES (converted movies)')
class LorenciaDemo(unittest.TestCase):
    def test_accept_kill_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([str(NATIVE/'build/mu-world'), '--game-root', os.environ['MU_GAME_ROOT'], '--headless',
                                '--backend', 'gl', '--no-audio', '--placement',
                                str(NATIVE/'world/lorencia-demo-placement.txt'), '--npc-demo',
                                str(NATIVE/'world/lorencia-demo-npc.txt'), '--gfx', os.environ['MU_QUEST_MOVIES'],
                                '--tile', '133,127', '--npc-script',
                                '5:click:soldier 60:option:1 90:option:0 120:qnext 130:qnext 140:qnext 150:qnext '
                                '170:qclose 180:qwin 200:qtab:2 215:qsel:7 240:qkill:2 245:qkill:2 250:qkill:2 '
                                '270:qwin 280:click:soldier 330:option:1 360:option:0 390:qok',
                                '--frames', '420', '--every', '1000', '--out-dir', tmp],
                               capture_output=True, text=True, timeout=600,
                               env={**os.environ, 'MU_GFX_SINGLE_BUFFER': '1'})
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        quest = next(json.loads(l)['quest'] for l in r.stdout.splitlines() if l.startswith('{"quest"'))
        self.assertEqual((quest['accepted'], quest['completed'], quest['progress']), (1, 1, 3))
        self.assertEqual(quest['active'], [])


if __name__ == '__main__':
    unittest.main()
