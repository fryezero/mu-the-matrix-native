"""Talking to NPCs (NATIVE-NPC-001) checks.

Portable (synthetic data only):
  * mu-walk --npc on the synthetic open world of test_native_world.py with
    synthetic NPC models (Smith01, Storage01, MixNpc01, Wizard01 under
    Data/Npc): a scripted click goes through the client's character pick,
    the hero walks with the path finder and stops beside the NPC (the
    character bit of MoveCharacters keeps the NPC's tile out of the path),
    the talk request leaves at the end of the walk, the demo answer arrives
    `latency` steps later and the reconstructed dispatch names the window:
    NpcShop with the smith's repair flag, StorageInven, MixGoblinSel (not
    played natively), none for an NPC without a demo row; SND_Play 25 and 28
    per answer; clicks are ignored while a shop or the vault is open;
  * malformed scripts and demo tables are refused; the committed Lorencia
    demo table names only results the dispatch knows;
  * the GFx layer on the stand-in libmugfx: npcdialogue's invoke sequence
    (SetTitle, VisibleContribute(0), SetDialogueMentDivide(text, ";"), the
    pages from NPCDialogTextWidth, SetSelectBtnContent, SetPosLeftCenter),
    NpcShop and StorageInven as 8 x 15 slot windows (page types 8 and 9 in
    the slot pass, item draws), the inventory opening with them, demo buy /
    sell / take / put, options and close.
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): the Lorencia demo (dialogue,
shop, vault, Chaos Goblin) on the installed data; with the pinned captures and
Unicorn, scripts/validate_npc.py with its planted mistakes.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
ROOT = NATIVE.parent
sys.path.insert(0, str(HERE))
import native_fixtures as nf  # noqa: E402
from test_native_world import write_open_world  # noqa: E402
from test_native_gfx2 import build_layer_host, states, CC  # noqa: E402

WALK = NATIVE/'build/mu-walk'
DEMO = NATIVE/'world/lorencia-demo-npc.txt'
PLACEMENT = NATIVE/'world/lorencia-demo-placement.txt'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')


def write_npc_world(root):
    write_open_world(root)
    npc = Path(root)/'Data'/'Npc'
    npc.mkdir(parents=True, exist_ok=True)
    for k, name in enumerate(('Smith01', 'Storage01', 'MixNpc01', 'Wizard01')):
        (npc/f'{name}.bmd').write_bytes(nf.synthetic_layout(20 + k, actions=8, keys=(4,)))
    return root


PLACE = """# synthetic demo
actor 251 123 120 6 label smith
actor 240 120 123 4 label vault
actor 238 117 120 2 label goblin
actor 254 120 117 0 label wizard
"""
TABLE = """talk 251 0x00
shop 251 0 3584 7171
talk 240 2
storage 0 7171
talk 238 0x03
"""


def run(root, placement, demo, *args, check=True):
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run([str(WALK), '--game-root', str(root), '--headless', '--backend', 'soft',
                                 '--no-audio', '--placement', str(placement), '--npc-demo', str(demo), '--width', '160',
                                 '--height', '120', '--every', '1', '--out-dir', tmp, '--tile', '120,120',
                                 *[str(a) for a in args]], capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    return {'frames': [r for r in rows if 'npc_frame' in r], 'opens': [r for r in rows if 'npc_open' in r],
            'walk': [r for r in rows if 'frame' in r and 'tick' in r],
            'summary': next((r for r in rows if r.get('npc') is True), None),
            'logs': [r['npc_log'] for r in rows if 'npc_log' in r], 'result': result}


def log_step(logs, pattern):
    m = next((re.match(r'step (\d+)', l) for l in logs if pattern in l), None)
    return int(m.group(1)) if m else None


class Session(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        cls.root = write_npc_world(d/'game')
        cls.placement = d/'placement.txt'
        cls.placement.write_text(PLACE)
        cls.demo = d/'demo.txt'
        cls.demo.write_text(TABLE)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_click_walk_talk_answer(self):
        out = run(self.root, self.placement, self.demo, '--frames', '90', '--npc-script', '3:click:smith')
        s = out['summary']
        self.assertEqual((s['picks'], s['pick_hits'], s['walks'], s['talks'], s['answers']), (1, 1, 1, 1, 1))
        self.assertEqual(s['sounds'], 2)                                   # SND_Play 25, 28
        walk, talk, answer = (log_step(out['logs'], p) for p in ('walk to smith', 'talk request', 'answer'))
        self.assertLess(walk, talk)
        self.assertEqual(answer - talk, 4)                                 # demo latency
        o = out['opens'][0]
        self.assertEqual((o['npc_open'], o['movie'], o['slot'], o['result'], o['repair'], o['close_all']),
                         ('shop', 'NpcShop', 0xf4, 0, 1, 1))
        tile = out['frames'][-1]['hero_tile']
        self.assertNotEqual(tile, [123, 120])                              # the NPC's tile carries bit 2
        self.assertLessEqual(max(abs(tile[0] - 123), abs(tile[1] - 120)), 1)
        moving_at_talk = [f for f in out['frames'] if f['step'] == talk + 1]
        self.assertTrue(moving_at_talk and moving_at_talk[0]['moving'] == 0)

    def test_windows_by_result_and_the_window_gate(self):
        out = run(self.root, self.placement, self.demo, '--frames', '120', '--npc-script',
                  '2:talk:vault 30:talk:smith 40:close 50:talk:goblin 80:talk:wizard')
        kinds = [(o['npc_open'], o['movie'], o['result']) for o in out['opens']]
        self.assertEqual(kinds, [('storage', 'StorageInven', 2), ('other', 'MixGoblinSel', 3), ('none', '', 255)])
        s = out['summary']
        self.assertEqual(s['clicks_ignored'], 1)                           # the smith while the vault was open
        self.assertEqual((s['answers'], s['windows'], s['not_played']), (3, 1, 1))
        self.assertEqual(s['sounds'], 6)

    def test_click_off_the_npcs_walks(self):
        out = run(self.root, self.placement, self.demo, '--frames', '30', '--walk', '125,125')
        self.assertEqual(out['summary']['pick_hits'], 0)
        self.assertEqual(out['opens'], [])

    def test_bad_scripts_and_tables_are_refused(self):
        for text in ('5:hug:smith', '5:click', 'click:smith', '5:talk'):
            r = subprocess.run([str(WALK), '--game-root', str(self.root), '--headless', '--npc-script', text],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0, text)
        bad = Path(self.tmp.name)/'bad.txt'
        for text in ('talk 251\n', 'shop 251 0x1ffff\n', 'talk 251 300\n', 'frob 1\n', 'storage 7+20\n'):
            bad.write_text(text)
            r = run(self.root, self.placement, bad, '--frames', '2', check=False)
            self.assertNotEqual(r['result'].returncode, 0, text)
            self.assertIn('npc demo', r['result'].stderr)

    def test_lorencia_demo_table_names_known_results(self):
        named = {0x00, 0x02, 0x03, 0x28}
        talks = []
        for line in DEMO.read_text().splitlines():
            line = line.split('#')[0].split()
            if line and line[0] == 'talk':
                talks.append((int(line[1]), int(line[2], 0)))
            if line:
                self.assertIn(line[0], ('talk', 'shop', 'storage', 'actor'))
        self.assertEqual({r for _, r in talks}, named)
        self.assertIn((584, 0x28), talks)                                  # the dialogue NPC 0x248 itself


@unittest.skipUnless(CC, 'no C compiler')
class Windows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.exe, cls.lib = build_layer_host(cls.dir)
        movies = cls.dir/'movies'
        movies.mkdir()
        for name in ('main', 'InventoryFrame', 'InfoPopup', 'CharacterInfoFrame', 'chat', 'NpcDialogue', 'NpcShop',
                     'StorageInven'):
            (movies/f'{name}.swf').write_bytes(b'stub')
        (cls.dir/'plain').mkdir()
        for name in ('main', 'InventoryFrame', 'InfoPopup', 'CharacterInfoFrame', 'chat'):
            (cls.dir/'plain'/f'{name}.swf').write_bytes(b'stub')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def host(self, *ops, movies='movies'):
        log = self.dir/'stub.log'
        if log.exists():
            log.unlink()
        r = subprocess.run([str(self.exe), str(self.dir/movies), str(self.lib)] + [str(o) for o in ops],
                           capture_output=True, text=True, timeout=60, env={**os.environ, 'MUGFX_STUB_LOG': str(log)})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout, log.read_text().splitlines() if log.exists() else []

    @staticmethod
    def npc(out):
        return [s for s in states(out) if 'npc_window' in s]

    def test_dialogue_invokes_pages_and_options(self):
        out, log = self.host('npcdialog', 'npcprint', 'npcact', 'option', '0', 'npcprint', 'npcact', 'option', '1',
                             'npcprint')
        calls = [l.split(' ', 2)[1].split('.')[-1] for l in log if l.startswith('NpcDialogue') and 'SetVisible' not in l]
        self.assertEqual(calls, ['SetTitle', 'VisibleContribute', 'SetDialogueMentDivide', 'SetDialogueMent',
                                 'VisibleArrowBtn', 'SetSelectBtnContent', 'SetPosLeftCenter'])
        self.assertIn('NpcDialogue _level0.g_mcNpcDialogue.SetDialogueMentDivide ["First line of the talk;Second line",";"]',
                      log)
        self.assertIn('NpcDialogue _level0.g_mcNpcDialogue.SetSelectBtnContent ["1. Tell me more;2. Goodbye;"]', log)
        self.assertIn('NpcDialogue _level0.g_mcNpcDialogue.SetDialogueMent ["First line of the talk\\nSecond line",0]',
                      log)
        n = self.npc(out)
        self.assertEqual(n[0]['npc_window'], 5)
        self.assertIn('option 1: Tell me more', n[1]['last'])
        self.assertEqual(n[2]['npc_window'], -1)                           # the last option closes (demo)

    def test_shop_slots_buy_and_sell(self):
        out, log = self.host('npcshop', 'npcprint', 'slotdraws', '6', 'slot', '6', '0', 'npcprint', 'npcact', 'sell',
                             '0', 'npcprint', 'npcact', 'close', '0', 'npcprint')
        n = self.npc(out)
        self.assertEqual((n[0]['npc_window'], n[0]['shop_items'], n[0]['inventory_open']), (6, 3, 1))
        draws = [s for s in states(out) if 'slot_draw' in s]
        self.assertEqual([d['code'] for d in draws], [0, 3584, 7171])
        self.assertEqual({(d['page_type'], d['type8']) for d in draws}, {(8, 1)})    # NpcShop page type 8
        self.assertEqual(draws[1]['rect'][2:], [52.0, 52.0])                         # 2 x 2 cells of 26
        self.assertEqual(n[1]['zen'], n[0]['zen'] - 1000)                            # the Kris, demo price
        self.assertEqual(n[1]['inventory_items'], n[0]['inventory_items'] + 1)
        self.assertIn('sold', n[2]['last'])
        self.assertEqual(n[2]['inventory_items'], n[1]['inventory_items'] - 1)
        self.assertEqual(n[3]['npc_window'], -1)
        self.assertIn('NpcShop _level0.g_mcNpcShop.SetVisibleRepair [true]', log)
        self.assertIn('NpcShop _level0.g_mcNpcShop.SetAvailableTabs [2]', log)

    def test_vault_take_and_put(self):
        out, _ = self.host('storage', 'npcprint', 'slotdraws', '7', 'npcact', 'take', '0', 'npcprint', 'npcact',
                           'put', '0', 'npcprint')
        n = self.npc(out)
        self.assertEqual((n[0]['npc_window'], n[0]['storage_items']), (7, 2))
        self.assertEqual({s['page_type'] for s in states(out) if 'slot_draw' in s}, {9})
        self.assertEqual((n[1]['storage_items'], n[1]['inventory_items']), (1, n[0]['inventory_items'] + 1))
        self.assertEqual((n[2]['storage_items'], n[2]['inventory_items']), (2, n[1]['inventory_items'] - 1))

    def test_without_npc_movies(self):
        out, _ = self.host('npcdialog', 'npcshop', 'storage', 'npcprint', movies='plain')
        self.assertIn('npcdialog 0', out)
        self.assertIn('npcshop 0', out)
        self.assertEqual(self.npc(out)[0]['npc_window'], -1)


@unittest.skipUnless(PRIVATE, 'set MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class Installed(unittest.TestCase):
    def test_lorencia_demo(self):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        root = os.environ['MU_GAME_ROOT']
        expect = {'sir lesnar': ('dialog', 'npcdialogue', 40), 'smith': ('shop', 'NpcShop', 0),
                  'storage': ('storage', 'StorageInven', 2), 'goblin (pub)': ('other', 'MixGoblinSel', 3)}
        for label, want in expect.items():
            out = run(root, PLACEMENT, DEMO, '--frames', '160', '--every', '200', '--npc-script', f'2:talk:{label}')
            o = out['opens'][0]
            self.assertEqual((o['npc_open'], o['movie'], o['result']), want, label)
        out = run(root, PLACEMENT, DEMO, '--tile', '133,127', '--frames', '80', '--every', '200', '--npc-script',
                  '5:click:sir lesnar')
        self.assertEqual(out['summary']['pick_hits'], 1)
        self.assertEqual(out['opens'][0]['dialogue'], 0x248)

    @unittest.skipUnless((ROOT/'evidence/x86-text-capture-09/client-text.bin').exists() or
                         os.environ.get('MU_CLIENT_TEXT'), 'pinned captures absent')
    def test_validator(self):
        python = ROOT/'tools/python/bin/python'
        python = str(python) if python.exists() else sys.executable
        try:
            subprocess.run([python, '-c', 'import unicorn, capstone'], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            self.skipTest('unicorn/capstone not installed')
        r = subprocess.run([python, str(ROOT/'scripts/validate_npc.py'), '--cases', '200', '--talk-cases', '2',
                            '--pick-cases', '120', '--mutations'], capture_output=True, text=True, timeout=1800)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])


if __name__ == '__main__':
    unittest.main()
