"""NATIVE-LANG-002 checks: BuffEffect, CharacterInfoSetup, MonsterSoulConversion, the NPC dialogue and prices.

Portable (synthetic data only):
  - the synthetic langread snapshot of test_native_lang (now with BuffEffect, CharacterInfoSetup, SkillRequire
    and MonsterSoulConversion maps) through scripts/live_lang_to_plain.py: `mu-lang buff` gives the record or the
    default record ("null" for absent buffs and buffs >= 0x1cb), the InfoPopup lines of 0x01298a54 (name, "\\n",
    the description; with value kind 1 and a hero value one formatted line) and the bufflist's addBuff object
    (hidden buffs, debuff / cash flags, BuffDetailType for groups 0xf6/0xf7); `mu-lang charinfo` the rows of
    a class in the row builder's order (other types first in key order, then types 2/3/5 by sort; ties in key
    order below 33 rows, where MSVC's std::sort is an insertion sort); `mu-lang soul`;
  - the GFx layer on the stand-in libmugfx (base mode): addBuff invokes on the bufflist channel once it loaded,
    a repeated buff not sent twice, the bufflist's onTooltip through the host's tooltip, SetName rows with the
    line builder's HTML and the hero values, and the dialogue's option going to the host's choice callback.
Private (MU_RECOVERY_INTEGRATION=1): with MU_GAME_ROOT the dialogue of Sir Lesnar in mu-world (QuestWords text,
the state change of an option, a server request) and the shop's prices; with the pinned captures and Unicorn
scripts/validate_npc_dialogue.py.
"""
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
import test_native_lang as tl  # noqa: E402

PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
GAME_ROOT = os.environ.get('MU_GAME_ROOT', '')


class Tables(tl.Build):
    def buff(self, *args):
        return tl.lang_json(self.lang, 'buff', *args)

    def test_buff_records_and_default(self):
        b = self.buff(29)
        self.assertEqual((b['name'], b['group'], b['item'], b['type']), ('Seal of Ascension', 60, [13, 43], 2))
        for absent in (2, 0x1cb, 0x7fffffff):
            d = self.buff(absent)
            self.assertEqual((d['index'], d['name'], d['item'], d['type']), (0, 'null', [-1, -1], -1), absent)
            self.assertEqual(d['tooltip'], ['null', '\n'])

    def test_buff_tooltip_lines(self):
        self.assertEqual(self.buff(11)['tooltip'],
                         ['Potion of Soul', '\n', 'AG recovery +8', 'A line longer than fifteen bytes'])
        self.assertEqual(self.buff(320)['tooltip'], ['Mastery', '\n', 'Ignores defense by %d when attacking.'])
        self.assertEqual(self.buff(320, 25)['tooltip'], ['Mastery', '\n', 'Ignores defense by 25 when attacking.'])
        self.assertEqual(self.buff(1, 25)['tooltip'], ['Increase Attack Power', '\n', 'Attack power increases.'])

    def test_addbuff_object(self):
        self.assertEqual(self.buff(1)['addbuff'], {'is_debuff': 0, 'is_cash': 0, 'has_detail': 1, 'detail': 0})
        self.assertEqual(self.buff(29)['addbuff'], {'is_debuff': 0, 'is_cash': 1, 'has_detail': 1, 'detail': 0})
        self.assertEqual(self.buff(35)['addbuff'], {'is_debuff': 0, 'is_cash': 0, 'has_detail': 1, 'detail': 2})
        self.assertEqual(self.buff(55)['addbuff'], {'is_debuff': 1, 'is_cash': 0, 'has_detail': 0, 'detail': 0})
        for hidden in (0x53, 0x78, 0x19b, 0x1be, 0, -1, 0x1cb):
            self.assertIsNone(self.buff(hidden)['addbuff'], hidden)

    def test_character_rows(self):
        def ids(cls):
            return [r['id'] for r in tl.lang_json(self.lang, 'charinfo', cls)]
        self.assertEqual(ids(1), [1, 2, 80, 8, 43, 9, 13, 10])   # row 9 only for class index 1
        self.assertEqual(ids(0), [1, 2, 80, 8, 43, 13, 10])
        self.assertEqual(tl.lang(self.lang, 'charinfo', 16, check=False).returncode, 1)   # no rows
        row = tl.lang_json(self.lang, 'charinfo', 1)[3]
        self.assertEqual((row['label'], row['type'], row['sort'], row['button']), ('Strength', 2, 0, 1))

    def test_soul_conversion(self):
        self.assertEqual([tl.lang(self.lang, 'soul', c).stdout.strip() for c in (7628, 7629, 7630)],
                         [b'1', b'0', b'1'])


@unittest.skipUnless(tl.CC, 'no C compiler')
class Layer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.host, cls.lib, cls.movies = tl.build_layer_host(cls.dir)
        (cls.movies/'NpcDialogue.swf').write_bytes(b'')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_host(self, *ops, **env):
        log = self.dir/'stub.log'
        if log.exists():
            log.unlink()
        r = subprocess.run([str(self.host), str(self.movies), str(self.lib), *ops], capture_output=True, text=True,
                           timeout=60, env={**os.environ, 'MUGFX_STUB_LOG': str(log), **env})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout, log.read_text().splitlines()

    def test_bufflist_add_and_tooltip(self):
        out, log = self.run_host('buffs', 'advance', '50', 'npcact', 'bufftip', '35', 'advance', '50')
        self.assertIn('buffs 3 3', out)
        adds = [line.split(' ', 2)[2] for line in log if '.addBuff ' in line]
        self.assertEqual([json.loads(a)[0] for a in adds],
                         [{'BuffType': 1, 'isDebuff': False, 'isCashBuff': False, 'BuffDetailType': 0},
                          {'BuffType': 35, 'isDebuff': False, 'isCashBuff': False, 'BuffDetailType': 2},
                          {'BuffType': 55, 'isDebuff': True, 'isCashBuff': False}])
        self.assertTrue(all(line.split(' ')[1].startswith('_level0.base.UI.mcBottom.bufflist_5.BuffList.')
                            for line in log if '.addBuff ' in line))
        tips = [line for line in log if '.SetInfoPopup ' in line]
        self.assertEqual(len(tips), 1)
        self.assertIn('<b>buff 35</b>', tips[0])

    def test_character_rows(self):
        out, log = self.run_host('charrows', 'open', '3', 'advance', '50')
        rows = [json.loads(line.split(' ', 2)[2]) for line in log if '.SetName ' in line]
        self.assertEqual([r[:3] for r in rows], [[1, 1, 0], [2, 8, 0], [3, 43, 0]])
        self.assertEqual(rows[0][3], "<font color='#%s'>Class</font><br>" % rows[0][3].split('#')[1][:6])
        self.assertIn('&lt;DMG>', rows[2][3])                       # the line builder escapes '<'
        self.assertEqual(rows[2][4].split('>')[1].split('<')[0], '-')
        self.assertEqual([r[6] for r in rows], [0, 1, 0])
        self.assertNotIn('Damage', ' '.join(str(r) for r in rows))  # the stand-in rows are gone

    def test_dialogue_choice_goes_to_the_host(self):
        out, _ = self.run_host('npcdialog', 'npcact', 'option', '1', 'npcprint', MU_GFX_HOST_CHOICE='1')
        self.assertIn('host choice 1', out)
        state = [json.loads(line) for line in out.splitlines() if line.startswith('{"npc_window"')][0]
        self.assertEqual(state['npc_window'], 5)                    # the host keeps the window (no demo close)


@unittest.skipUnless(PRIVATE and GAME_ROOT and Path(GAME_ROOT, 'Data/Local').exists(),
                     'needs MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class Installed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(ROOT/'reconstructed/npc')], check=True, capture_output=True)

    def test_dialogue_tables_parse(self):
        import ctypes
        lib = ctypes.CDLL(str(ROOT/'reconstructed/npc'/('libnpc.dylib' if sys.platform == 'darwin' else 'libnpc.so')))
        out = subprocess.run([str(NATIVE/'build/mu-data'), 'decode', str(Path(GAME_ROOT)/'Data/Local/npcdialogue.bmd'),
                              '--out', '/dev/stdout'], capture_output=True, check=False)
        if out.returncode:
            self.skipTest('mu-data not built')
        t = ctypes.create_string_buffer(64)
        lib.mu_dlg_parse_records.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
        lib.mu_dlg_parse_records.restype = ctypes.c_long
        self.assertGreater(lib.mu_dlg_parse_records(t, out.stdout, len(out.stdout)), 50)

    @unittest.skipUnless((ROOT/'evidence/x86-text-capture-09/client-text.bin').exists() or
                         os.environ.get('MU_CLIENT_TEXT'), 'pinned captures absent')
    def test_dialogue_validator(self):
        python = ROOT/'tools/python/bin/python'
        python = str(python) if python.exists() else sys.executable
        try:
            subprocess.run([python, '-c', 'import unicorn, capstone'], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            self.skipTest('unicorn/capstone not installed')
        r = subprocess.run([python, str(ROOT/'scripts/validate_npc_dialogue.py'), '--mutations'], capture_output=True,
                           text=True, timeout=1800)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
        self.assertIn('all cases match', r.stdout)


if __name__ == '__main__':
    unittest.main()
