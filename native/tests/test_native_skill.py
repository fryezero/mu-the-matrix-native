"""Skills in the native client's interface (NATIVE-SKILL-001, NATIVE-SKILL-002) checks.

Portable (synthetic data only):
  * the skill book (core/mu_skill through native/build/skill-book-host) over a synthetic Lang plaintext
    (globaltext.txt, skills.tsv, skills_ext.tsv) and a synthetic SkillTooltipText.bmd (count, records XORed
    with FC CF AB, checksum key 0xe2f1): the demo learned list and bar, the bar feed (SetSkillSlot JSON, sent
    again only after a change), onSelectSkill's CurrentSkill, casts through the client's checks (ok, delay,
    requirements, mana with the potion flag) with StartSkillDelay's events and the tick, the tooltip's HTML,
    the icon bitmaps and the Skill Imprint window's slots, drag and cancel; NATIVE-SKILL-002: the learned list,
    the stamp manager and the bar come from the demo server's packets (opcode 0xA0 sub 0x20 list / 0xFE / 0xFF,
    sub 0x03 the saved bar) through the client's handlers, Save commits the window's slots, a master upgrade
    (brand) takes its base skill's entry and CurrentSkill;
  * the GFx layer on the stand-in libmugfx: the skill host's bar feed (SetSkillSlot), onSelectSkill to the
    host, onSkillTooltip -> SkillInfoPopup.SetInfoPopupSkillStamp at x + w/2, onUseSkillDelay, the U key
    toggling SkillStampFrame with its creation and open invokes, the window's slot rectangles for the host's
    icons, hover tooltips, the drag through CheckOverSlot / DragEndSlotIndex_Mouse, "not learned" and Save.
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_LANG_DIR): the book over the installed tables; with the
pinned captures, Unicorn and the langread snapshot ($SNAP), scripts/validate_skill.py with its planted
mistakes.
"""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
ROOT = NATIVE.parent
sys.path.insert(0, str(HERE))
from test_native_gfx2 import build_layer_host, states, CC  # noqa: E402

BOOK = NATIVE/'build/skill-book-host'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')
KEY3 = bytes((0xfc, 0xcf, 0xab))


def checksum(data, key):
    result = (key << 9) & 0xffffffff
    for offset in range(0, len(data) - 3, 4):
        word = struct.unpack_from('<I', data, offset)[0]
        result = result ^ word if ((offset >> 2) + key) % 2 == 0 else (result + word) & 0xffffffff
        if offset % 16 == 0:
            result = (((key + result) & 0xffffffff) >> (((offset >> 2) % 8) + 1)) ^ result
    return result


# index, name, level, damage, mana, ag, distance, delay, str, dex, energy, command, vitality, mastery, use_type,
# icon, type (skills.tsv: req_3c = strength, req_40 = agility, req_44 = energy, req_48 = command, req_4c = vitality)
SKILLS = [
    (19, 'Falling Slash', 0, 0, 9, 0, 3, 0, 0, 0, 0, 0, 0, 6, 0, 19, 0),
    (41, 'Twisting Slash', 0, 0, 10, 10, 2, 0, 0, 0, 0, 0, 0, 6, 0, 41, 0),
    (22, 'Cyclone', 0, 0, 9, 0, 2, 0, 0, 0, 0, 0, 0, 6, 0, 22, 0),
    (344, 'Blood Storm', 0, 25, 87, 29, 3, 5000, 0, 0, 0, 0, 0, 6, 4, 44, 0),
    (9, 'Evil Spirit', 50, 45, 90, 0, 6, 0, 0, 0, 220, 0, 0, 6, 0, 9, 0),
    (14, 'Inferno', 88, 100, 200, 0, 4, 0, 0, 0, 724, 0, 0, 6, 0, 14, 0),
    (330, 'Twisting Upgrade', 0, 0, 12, 10, 2, 0, 0, 0, 0, 0, 0, 6, 4, 330, 0),
]
BRAND = {330: 41}     # record +0x5c: 330 improves on Twisting Slash
DEMO = 'list 1 19 22 41 344 9 14\nkeys 1 19 41 22 344 -1 -1 9 14 -1 -1\n'   # the demo server's login data


def write_lang(directory):
    directory.mkdir(parents=True, exist_ok=True)
    texts = {0x18c4: 'Energy %d', 0x18c6: ' / ', 0x12b0: 'Mana %d', 0x12b1: 'AG %d', 0x12b2: 'Range %d',
             0x12b3: 'Cooldown: %.1f sec.', 0x12b4: 'Damage %d', 0x12b6: '(Imprint Bonus %d%%)', 0x12b7: 'Neutral',
             0x1709: 'All Elements', 0: 'Arial'}
    (directory/'globaltext.txt').write_text('# synthetic\n' + ''.join(f'{k}\t{v}\n' for k, v in sorted(texts.items())))
    rows = []
    for s in SKILLS:
        idx, name, level, damage, mana, ag, dist, delay, st, dx, en, cm, vt, mastery, use, icon, typ = s
        rows.append('\t'.join(str(v) for v in (idx, name, level, damage, mana, ag, dist, delay, st, dx, en, cm, vt,
                                               mastery, use, BRAND.get(idx, 0), 0, icon, typ, 0)))
    (directory/'skills.tsv').write_text('# synthetic\n' + '\n'.join(rows) + '\n')
    ext = ['\t'.join(str(v) for v in (s[0],) + (0,) * 17 + (110, 0, 0)) for s in SKILLS]
    (directory/'skills_ext.tsv').write_text('# synthetic\n' + '\n'.join(ext) + '\n')


def tip_record(skill, name, text1, text2=b'', cond2=-1):
    rec = bytearray(808)
    struct.pack_into('<H', rec, 0, skill)
    rec[2:2 + len(name)] = name
    struct.pack_into('<ii', rec, 0x104, 3, 0)
    rec[0x10c:0x10c + len(text1)] = text1
    struct.pack_into('<ii', rec, 0x20c, 0, cond2)
    rec[0x214:0x214 + len(text2)] = text2
    struct.pack_into('<iiiii', rec, 0x314, 2, -1, -1, 0, -1)
    return bytes(rec)


def write_root(root, extra=()):
    local = root/'Data/Local'
    local.mkdir(parents=True, exist_ok=True)
    records = [tip_record(9, b'Evil Spirit', b'Spirits strike#all around.', b'Learn it.', 2),
               tip_record(344, b'Blood Storm', b'A storm.'), tip_record(9, b'Duplicate', b'not used'), *extra]
    payload = b''.join(bytes(b ^ KEY3[i % 3] for i, b in enumerate(r)) for r in records)
    (local/'skilltooltiptext.bmd').write_bytes(struct.pack('<I', len(records)) + payload +
                                              struct.pack('<I', checksum(payload, 0xe2f1)))


def write_master(root):
    local = root/'Data/Local'
    local.mkdir(parents=True, exist_ok=True)
    nodes = bytearray(24 * 2048)
    struct.pack_into('<BBHBBBBiiii', nodes, 0, 1, 0, 1, 0, 1, 20, 4, 0, 0, 330, 0)
    tips = bytearray(808 * 2048)
    struct.pack_into('<ih', tips, 0, 330, 1)
    for offset, value in ((6, b'Rank %d, Skill Level: %d/%d'), (0x46, b'Synthetic master skill'),
                          (0x146, b'Required Points: %d')):
        tips[offset:offset + len(value)] = value
    for name, raw in (('masterskilltreedata.bmd', nodes), ('masterskilltooltip.bmd', tips)):
        stride = 24 if 'data' in name else 808
        payload = b''.join(bytes(b ^ KEY3[i % 3] for i, b in enumerate(raw[start:start + stride]))
                           for start in range(0, len(raw), stride))
        (local/name).write_bytes(payload + struct.pack('<I', checksum(payload, 0x2bc1)))


def book(lang, root, *ops):
    r = subprocess.run([str(BOOK), str(lang), str(root)] + [str(o) for o in ops], capture_output=True, text=True,
                       timeout=60)
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    return [json.loads(line) for line in r.stdout.splitlines() if line.startswith('{')]


@unittest.skipUnless(BOOK.exists(), 'native/build/skill-book-host not built (make -C native)')
class Book(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        write_lang(cls.dir/'lang')
        write_root(cls.dir/'root')
        (cls.dir/'demo.txt').write_text(DEMO)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_book(self, *ops):
        out = book(self.dir/'lang', self.dir/'root', 'demofile', self.dir/'demo.txt', *ops)
        return out[:1] + out[2:]                                              # without the demofile line

    def test_demo_bar_feed_and_select(self):
        out = self.run_book('demo', '1', 'print', 'stats', '100', '100', '100', '300', '0', '1000', '100',
                            'feed', 'feed', 'select', '3', 'feed')
        self.assertEqual(out[0], {'records': 7, 'tooltips': 2})               # the duplicate skill 9 is dropped
        bar = out[2]
        self.assertEqual(bar['learned'], [19, 22, 41, 344, 9, 14])           # the server's list, in its order
        self.assertEqual(bar['bar'], [19, 41, 22, 344, 0, 0, 9, 14, 0, 0])   # its saved keys (key 0: slot 10)
        self.assertEqual(bar['basic'], [[9, 9, 1], [14, 14, 1], [19, 19, 1], [22, 22, 1], [41, 41, 1], [344, 344, 1]])
        feed = out[3]['feed']
        self.assertEqual((feed['SelectSlot'], feed['SelectSkill'], feed['SelectUseSkill']), (0, 19, True))
        self.assertEqual([s['isUse'] for s in feed['arrSlots']][6:8], [True, False])    # Inferno: energy 724 > 300
        self.assertIsNone(out[4]['feed'])                                     # nothing changed
        self.assertEqual(out[5], {'select': 1, 'selected': 344})
        self.assertEqual((out[6]['feed']['SelectSlot'], out[6]['feed']['SelectSkill']), (3, 344))

    def test_casts(self):
        out = self.run_book('demo', '1', 'stats', '100', '100', '100', '300', '0', '1000', '100',
                            'cast', '344', 'cast', '344', 'tick', '4000', 'cast', '344', 'tick', '1000', 'cast', '344',
                            'cast', '14', 'cast', '77', 'stats', '100', '100', '100', '300', '0', '50', '100',
                            'cast', '9', 'stats', '100', '100', '100', '300', '0', '1000', '5', 'cast', '41')
        casts = [o for o in out if 'cast' in o]
        self.assertEqual(casts[0], {'cast': 'ok', 'events': [[344, 5000]], 'potion': 0, 'mana': 913, 'ag': 71,
                                    'left': 1.0})
        self.assertEqual([c['cast'] for c in casts], ['ok', 'delay', 'delay', 'ok', 'requirements', 'no skill',
                                                      'mana', 'AG'])
        self.assertAlmostEqual(casts[2]['left'], 0.2)
        self.assertEqual(casts[6]['potion'], 1)

    def test_tooltip_icon_and_window(self):
        out = self.run_book('demo', '1', 'stats', '100', '100', '100', '300', '0', '1000', '100', 'tip', '9',
                            'tip', '22', 'icon', '344', 'icon', '19', 'stamp', 'slot', '5', 'slot', '0',
                            'drop', '6', '4', 'print', 'drop', '1', '4', 'print', 'cancel', 'print')
        tip = out[2]
        self.assertEqual(tip['tip'], 1)
        self.assertEqual(tip['title'], "<font color='#FFCC19'>Evil Spirit</font><br>")
        self.assertIn("<font color='#7FB2FF'>Energy 220</font><br>", tip['body'])
        self.assertIn('Mana 90', tip['body'])
        self.assertIn('Damage 45 (Imprint Bonus 110%)', tip['body'])
        self.assertIn('<BR>', tip['body'])
        self.assertIn('Spirits strike', tip['body'])
        self.assertNotIn('Learn it.', tip['body'])                          # condition 2: shown when not learned
        self.assertEqual(out[3]['tip'], 0)                                    # no SkillTooltipText record
        self.assertEqual((out[4]['bitmap'], out[4]['file']), (0x7e18, 'Interface/new_Master_Icon.jpg'))
        self.assertEqual((out[5]['bitmap'], out[5]['file']), (0x7c40, 'Interface/newui_skill00.jpg'))
        self.assertEqual(out[6], {'stamp_pages': 1})
        self.assertEqual((out[7]['skill'], out[8]['skill']), (9, 19))        # the tab's first entry / slot 0
        self.assertEqual(out[9], {'drop': 1})
        self.assertEqual(out[10]['window'], [19, 41, 22, 344, 14, 0, 9, 0, 0, 0])  # Inferno onto slot 4,
                                                                                    # leaving its old slot
        self.assertEqual(out[10]['bar'], [19, 41, 22, 344, 0, 0, 9, 14, 0, 0])     # the bar waits for Save
        self.assertEqual(out[11], {'drop': 1})
        self.assertEqual(out[12]['window'][:5], [19, 14, 22, 344, 41])             # slots 1 <-> 4 swapped
        self.assertEqual(out[13]['window'], [19, 41, 22, 344, 0, 0, 9, 14, 0, 0])  # Cancel takes the bar back

    def test_save_and_server_packets(self):
        out = self.run_book('demo', '1', 'stamp', 'drop', '6', '4', 'save', 'print', 'select', '1', 'learn', '330',
                            'print', 'forget', '22', 'print', 'packet', 'c2000ba020ff0000130000', 'print')
        self.assertEqual(out[4]['bar'], [19, 41, 22, 344, 14, 0, 9, 0, 0, 0])      # Save: the bar takes the slots
        self.assertEqual(out[5], {'select': 1, 'selected': 41})
        learned = out[7]
        self.assertEqual(learned['learned'], [19, 22, 41, 344, 9, 14, 330])       # 0xFE: appended
        self.assertIn([41, 330, 1], learned['basic'])                              # the upgrade takes 41's entry
        self.assertEqual(learned['bar'][1], 330)                                   # and its bar slot
        self.assertEqual((learned['selected'], learned['current']), (330, 6))     # CurrentSkill follows (0x00a002d4)
        forgot = out[9]
        self.assertEqual(forgot['learned'], [19, 0, 41, 344, 9, 14, 330])          # 0xFF: the entry becomes 0
        self.assertIn([22, 0, 0], forgot['basic'])                                # no skill: no imprint
        self.assertEqual(forgot['bar'][2], 0)
        self.assertEqual(out[10], {'packet': 1})                                   # a C2 head: 0xFF of skill 19
        self.assertEqual(out[11]['learned'][0], 0)

    def test_master_answer_updates_damage_and_saved_bar(self):
        root = self.dir/'master-root'
        write_root(root, [tip_record(330, b'Twisting Upgrade', b'An upgraded skill.')])
        write_master(root)
        out = book(self.dir/'lang', root, 'demofile', self.dir/'demo.txt', 'demo', 129, 'master', 330,
                   'masterlearn', 330, 'master', 330, 'print', 'tip', 330)
        self.assertEqual(out[3], {'tree_nodes': 1, 'tree_tips': 1, 'master_points': 100, 'master_learned': 0,
                                  'level': 0, 'damage': 0})
        self.assertEqual(out[4], {'master_answer': 1})
        self.assertEqual((out[5]['level'], out[5]['master_points'], out[5]['damage']), (1, 99, 25))
        self.assertEqual(out[6]['learned'][2], 330)              # A0 14 replaces brand 41 in the hero list
        self.assertEqual(out[6]['bar'][1], 330)                  # the saved slot follows the upgrade
        self.assertIn('Damage 25', out[7]['body'])               # skill-bar tooltip uses the master damage
        # The login A0 10 restores a learned master value into the same tree, without spending points.
        demo = self.dir/'master-demo.txt'
        demo.write_text('list 1 330\nkeys 1 330\n')
        restored = book(self.dir/'lang', root, 'demofile', demo, 'demo', 129, 'master', 330)[-1]
        self.assertEqual((restored['level'], restored['master_points'], restored['damage']), (1, 100, 25))

    def test_weapon_rule_reaches_the_bar(self):
        lang = self.dir/'weapon-lang'
        write_lang(lang)
        ext = (lang/'skills_ext.tsv').read_text().splitlines()
        for i, line in enumerate(ext):
            if line.startswith('19\t'):
                fields = line.split('\t')
                fields[17] = '3'                              # sword/axe requirement in 0x010918c7
                ext[i] = '\t'.join(fields)
        (lang/'skills_ext.tsv').write_text('\n'.join(ext) + '\n')
        out = book(lang, self.dir/'root', 'demofile', self.dir/'demo.txt', 'demo', 1,
                   'stats', 100, 100, 100, 300, 0, 1000, 100, 'use', 0, 0, 'feed', 'use', 0, 1, 'feed')
        self.assertFalse(out[-2]['feed']['arrSlots'][0]['isUse'])
        self.assertTrue(out[-1]['feed']['arrSlots'][0]['isUse'])


@unittest.skipUnless(CC, 'no C compiler')
class Layer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.exe, cls.lib = build_layer_host(cls.dir)
        movies = cls.dir/'movies'
        movies.mkdir()
        for name in ('base', 'main', 'InventoryFrame', 'InfoPopup', 'CharacterInfoFrame', 'Chat', 'chat',
                     'SkillInfoPopup', 'SkillStampFrame', 'MasterSkillTree', 'SkillTree4th', 'SkillTree5th'):
            (movies/f'{name}.swf').write_bytes(b'stub')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def host(self, *ops):
        log = self.dir/'stub.log'
        if log.exists():
            log.unlink()
        r = subprocess.run([str(self.exe), str(self.dir/'movies'), str(self.lib)] + [str(o) for o in ops],
                           capture_output=True, text=True, timeout=60, env={**os.environ, 'MUGFX_STUB_LOG': str(log)})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout, log.read_text().splitlines() if log.exists() else []

    def test_bar(self):
        out, log = self.host('skillhost', 'advance', '100', 'skilldelay', '22', '1500',
                             'invoke', '0', '-', 'testCall', '["main","onSelectSkill",{"slot":3,"skill":22}]',
                             'invoke', '0', '-', 'testCall',
                             '["main","onSkillTooltip",{"slot":1,"skill":41,"x":600,"y":740,"w":41,"h":40}]',
                             'skillprint', 'invoke', '0', '-', 'testCall', '["main","offSkillTooltip",{}]', 'skillprint')
        feeds = [l for l in log if 'SetSkillSlot' in l]
        self.assertEqual(len([f for f in feeds if '"SelectSkill":22' in f]), 1)   # the host feed, once
        self.assertTrue(any('mcSkillHotKey.onUseSkillDelay [{"skill":22,"delaytime":1500}]' in l for l in log))
        self.assertIn('host select 3 22', out)
        self.assertTrue(any('SetInfoPopupSkillStamp [620,740,0,0,"Title 41","Body 41",0]' in l for l in log))
        st = [s for s in states(out) if 'popup_open' in s]
        self.assertEqual((st[0]['popup_open'], st[1]['popup_open']), (1, 0))

    def test_window(self):
        out, log = self.host('skillhost', 'advance', '100', 'key', '85', 'skillprint', 'skillicons',
                             'skillact', 'over', '5', '0', 'skillact', 'drag', '7', '1',
                             'invoke', '11', '-', 'testDropTarget', '[3]',
                             'invoke', '11', '-', 'testCall', '["requestSkillSlotDragStart",6.0]',
                             'invoke', '11', '-', 'testCall', '["requestSkillSlotDragEnd",6.0]', 'advance', '40',
                             'skillact', 'page', '1', '0', 'skillact', 'save', '0', '0', 'skillprint',
                             'key', '85', 'skillact', 'cancel', '0', '0', 'skillprint')
        self.assertIn('host stamp_open 1', out)
        for invoke in ('InitText', 'InitButton', 'InitStampExplain', 'SetVisible [true]', 'UpdateSkillPage [1]',
                       'SetStampDamage [0,', 'SetSkillSlotSize', 'CheckOverSlot', 'UpdateSkillPage [2]'):
            self.assertTrue(any('g_mcSkillStampFrame' in l and invoke in l for l in log), invoke)
        icons = [s for s in states(out) if 'skill_icon' in s]
        self.assertEqual(len(icons), 20)
        self.assertEqual(icons[5]['rect'], [51.0, 158.0, 26.0, 37.0])              # window 8,0 + slot 43,158
        self.assertEqual(icons[5]['delay'], 0.5)
        self.assertTrue(any('SetInfoPopupSkillStamp [64,158,0,0,"Title 105"' in l for l in log))
        self.assertIn('host drop 7 1', out)
        self.assertTrue(any('You cannot register a skill that you did not learn.' in l for l in log))
        self.assertIn('host drop 6 3', out)                                        # DragEndSlotIndex_Mouse(3)
        self.assertIn('host save', out)
        self.assertTrue(any('Skill Imprint saved.' in l for l in log))
        st = [s for s in states(out) if 'stamp_open' in s]
        self.assertEqual([s['stamp_open'] for s in st], [1, 0, 0])
        self.assertIn('host stamp_open 0', out)                                    # Cancel: the host restores
        self.assertTrue(any('g_mcSkillStampFrame.SetWindowSize [1280,800]' in l for l in log))

    def test_tree_hotkey_and_character_buttons(self):
        out, log = self.host('key', 65, 'treeprint', 'key', 27, 'treeprint',
                             'invoke', 3, '-', 'testCall', '["onClickbtnMasterSkillTree",0]', 'treeprint',
                             'invoke', 3, '-', 'testCall', '["OnClick4thSkillTree",0]', 'treeprint',
                             'invoke', 3, '-', 'testCall', '["OnClick5thSkillTree",0]', 'treeprint')
        trees = [s for s in states(out) if 'master_open' in s]
        self.assertEqual([s['master_open'] for s in trees], [1, 0, 1, 1, 1])
        self.assertEqual((trees[-1]['fourth_open'], trees[-1]['fifth_open']), (1, 1))
        self.assertIn('tree callback 13 UIInit', out)
        self.assertIn('tree callback 13 WindowShown', out)
        self.assertTrue(any('g_MasterSkillTree.SetAlign [0]' in l for l in log))
        self.assertTrue(any('g_SkillTree5th.SetAlign [3]' in l for l in log))


@unittest.skipUnless(PRIVATE and os.environ.get('MU_LANG_DIR') and BOOK.exists(), 'private data absent')
class Installed(unittest.TestCase):
    def test_book_over_the_installed_tables(self):
        out = book(os.environ['MU_LANG_DIR'], os.environ['MU_GAME_ROOT'], 'demo', '0', 'tip', '9', 'icon', '9',
                   'stats', '1250', '800', '650', '300', '0', '9000', '9000', 'icon', '9', 'cast', '9')
        self.assertGreater(out[0]['records'], 500)
        self.assertGreater(out[0]['tooltips'], 500)
        self.assertEqual(out[2]['tip'], 1)
        self.assertEqual(out[3]['bitmap'], 0x7c43)            # energy 0 < Evil Spirit's: the grey sheet
        self.assertEqual(out[4]['bitmap'], 0x7c40)
        self.assertEqual(out[5]['cast'], 'ok')

    @unittest.skipUnless((ROOT/'evidence/x86-text-capture-09/client-text.bin').exists() and os.environ.get('SNAP'),
                         'pinned captures or the langread snapshot absent')
    def test_validator(self):
        python = ROOT/'tools/python/bin/python'
        python = str(python) if python.exists() else sys.executable
        try:
            subprocess.run([python, '-c', 'import unicorn, capstone'], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            self.skipTest('unicorn/capstone not installed')
        for script in ('validate_skill.py', 'validate_skill_server.py'):     # NATIVE-SKILL-001 / -002
            r = subprocess.run([python, str(ROOT/'scripts'/script), '--cases', '60', '--mutations'],
                               capture_output=True, text=True, timeout=3600)
            self.assertEqual(r.returncode, 0, script + r.stdout[-2000:] + r.stderr[-2000:])


if __name__ == '__main__':
    unittest.main()
