"""HERO-ITEMS-001: the hero's part slots from its equipment records (reconstructed/hero-equipment).

Portable: worked examples of SetCharacterClass 0x01394870 (mu_he_set_character_class) and 0x00cd0995
(mu_he_item_flag) through ctypes, and the class parts it writes for an empty slot equal the parts the native
character loads (model-codec mu_character_part_type) for every class byte. APP-POLISH-008: an offline session's
equipment record as ITEM fields (mu_he_item_of_record) reaches the slots (family record of the validator).

Private, original instructions (MU_RECOVERY_INTEGRATION=1, pinned text/data): scripts/validate_hero_items.py with
its mutants (validator row validate_hero_items).

Private, installed data (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): Lorencia through `mu-walk --hero-item` (the
front end's equipment, as mu-client passes the demo characters'): files with non-standard names now take their
Item.bmd record's type, so the pre-draw programs of RENDER-ITEMS-002R run on the hero (blade01.bmd 0x0b4b,
CR_shield01.bmd 0x1748 in the left hand, InnocenceCape.bmd 0x2382); standard-named items keep the report.

HERO-ITEMS-002: the end of SetCharacterClass. Portable: worked examples of the castle worlds' weapon override
0x009dadf1 (mu_he_castle_override), SetCharacterScale 0x01394f6f's branches (mu_he_character_scale) and the order
of RenderCharacter's body-part loop (mu_he_part_draws). Private scenes: each listed helm the installed Item.bmd has
loads the class head into the hero's slot 0 (and another helm does not), a Chaos Castle world replaces the hero's
weapons and wing with the class weapon, and the class scale and part float reach the character.
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
sys.path.insert(0, str(ROOT/'scripts'))
from validate_hero_items import HEAD_HELMS, Item, PartDraw, Scale, ScaleIn  # noqa: E402  (ctypes views; no Unicorn)
from validate_players import Character  # noqa: E402

WALK = NATIVE/'build/mu-walk'
DATA = NATIVE/'build/mu-data'
GAME = os.environ.get('MU_GAME_ROOT')
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
EMPTY = (-1, 0, 0, 0, 0)


class Library(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        lib = Path(cls.tmp.name)/'libhero.so'
        subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wconversion', '-fPIC',
                        '-ffp-contract=off', '-shared',
                        str(ROOT/'reconstructed/hero-equipment/hero_equipment.c'),
                        str(ROOT/'reconstructed/players/remote_players.c'),
                        str(ROOT/'reconstructed/model-codec/character.c'),
                        str(ROOT/'reconstructed/record-math/record_math.c'), '-lm', '-o', str(lib)], check=True)
        cls.lib = ctypes.CDLL(str(lib))
        cls.lib.mu_he_set_character_class.argtypes = [ctypes.POINTER(Character), ctypes.POINTER(Item)]
        cls.lib.mu_he_item_flag.argtypes = [ctypes.POINTER(Item), ctypes.c_int32]
        cls.lib.mu_he_item_flag.restype = ctypes.c_uint8
        cls.lib.mu_he_equipment_of_slot.argtypes = [ctypes.c_int32]
        cls.lib.mu_he_equipment_of_slot.restype = ctypes.c_int32
        cls.lib.mu_character_part_type.argtypes = [ctypes.c_int, ctypes.c_uint8]
        cls.lib.mu_character_part_type.restype = ctypes.c_uint32
        cls.lib.mu_he_item_of_record.argtypes = [ctypes.c_int32, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8]
        cls.lib.mu_he_item_of_record.restype = Item
        # HERO-ITEMS-002
        cls.lib.mu_he_castle_override.argtypes = [ctypes.POINTER(Character), ctypes.c_int32]
        cls.lib.mu_he_character_scale.argtypes = [ctypes.POINTER(Character), ctypes.POINTER(ScaleIn),
                                                  ctypes.POINTER(Scale)]
        cls.lib.mu_he_set_character_class_world.argtypes = [ctypes.POINTER(Character), ctypes.POINTER(Item),
                                                            ctypes.POINTER(ScaleIn), ctypes.POINTER(Scale)]
        cls.lib.mu_he_part_draws.argtypes = [ctypes.POINTER(Character), ctypes.POINTER(PartDraw)]
        cls.lib.mu_he_part_draw_type.argtypes = [ctypes.c_uint8, ctypes.c_int32, ctypes.c_int16]
        cls.lib.mu_he_class_scale.argtypes = [ctypes.c_uint8, ctypes.c_int]
        cls.lib.mu_he_class_scale.restype = ctypes.c_float

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_class(self, equipment, class_byte=0x01, model=0xa91, byte_0e=0, prior=(0x1234, 0x55, 0x66, 0x77)):
        c = Character()
        c.model, c.class_byte, c.byte_0e = model, class_byte, byte_0e
        for k in range(11):
            c.slots[k].type, c.slots[k].level, c.slots[k].option, c.slots[k].ext = prior
        items = [EMPTY] * 9
        for s, item in equipment.items():
            items[s] = item
        self.lib.mu_he_set_character_class(ctypes.byref(c), (Item * 9)(*[Item(*i) for i in items]))
        return [(c.slots[k].type, c.slots[k].level, c.slots[k].option, c.slots[k].ext) for k in range(11)]

    def test_weapons_wing_and_helper(self):
        # right hand Katana (code 3, +7, the 0x98 flag), left Small Shield (6*512), wing Wings of Heaven (12*512+1, +9)
        slots = self.run_class({0: (3, 7 << 3, 5, 0, 1), 1: (6 * 512, 0, 0, 0, 0), 7: (12 * 512 + 1, 9 << 3, 9, 0, 1),
                                8: (13 * 512 + 2, 1 << 3, 3, 0, 1)})
        self.assertEqual(slots[6], (0xae9, 7, 1, 5))
        self.assertEqual(slots[7], (0x16e6, 0, 0, 0))
        self.assertEqual(slots[8], (0x22e7, 9, 0x66, 0x77))     # the wing keeps its option and ext bytes
        self.assertEqual(slots[10], (0xae6 + 13 * 512 + 2, 1, 0x66, 0x77))   # the helper: type and level too
        self.assertEqual(slots[9], (0x1234, 0x55, 0x66, 0x77))  # the muun slot is not written

    def test_empty_parts_take_the_class_parts_the_native_character_loads(self):
        for class_byte in range(256):
            slots = self.run_class({}, class_byte=class_byte)
            for k in range(1, 6):
                self.assertEqual(slots[k][0] & 0xffff, self.lib.mu_character_part_type(k, class_byte), (class_byte, k))
                self.assertEqual(slots[k][1:], (0, 0, 0))
            self.assertEqual(slots[6][0], -1)

    def test_level_word_and_codes(self):
        slots = self.run_class({0: (-2, -8, 0, 0, 1), 2: (7 * 512 + 9, 0x7f, 0xab, 0, 1)})
        self.assertEqual(slots[6], (0xae4, 15, 0, 0))   # only -1 is empty; sar keeps the sign; option needs code >= 0
        self.assertEqual(slots[1], (0xae6 + 7 * 512 + 9, 15, 1, 0xab))   # a worn helm: level, option, ext

    def test_head_follows_the_helm(self):
        self.assertEqual(self.run_class({2: (0x18e6 - 0xae6, 0, 0, 0, 0)}, class_byte=0x11)[0][0], 0x3700 + 0x11)
        self.assertEqual(self.run_class({2: (0x18e7 - 0xae6, 0, 0, 0, 0)})[0][0], -1)
        self.assertEqual(self.run_class({}, class_byte=0x02)[0][0], -1)   # the class helm hides the head
        self.assertEqual(self.run_class({2: (0x18e6 - 0xae6, 0, 0, 0, 0)}, byte_0e=1)[0][0], 0x1234)

    def test_other_models_are_left_alone(self):
        self.assertEqual(self.run_class({0: (3, 0, 0, 0, 0)}, model=0x7d9), [(0x1234, 0x55, 0x66, 0x77)] * 11)

    def test_item_flag_modes(self):
        flag = lambda item, mode: self.lib.mu_he_item_flag(ctypes.byref(Item(*item)), mode)  # noqa: E731
        self.assertEqual([flag((5, 0, 0x10, 1, 1), m) for m in (0, 1, 2, 3)], [1, 1, 1, 0])
        self.assertEqual([flag((5, 0, 0x0c, 2, 2), m) for m in (0, 1, 2)], [0, 0, 0])
        self.assertEqual(flag((0x2c00, 0, 0, 0, 1), 1), 1)
        self.assertEqual(flag((0x2c01, 0, 0, 0, 1), 1), 0)

    def test_session_record_items(self):
        # APP-POLISH-008: Cookery Short Sword 0:68 +9 excellent, a +7 shield and a wing as the offline session gives them
        def item(*record):
            i = self.lib.mu_he_item_of_record(*record)
            return (i.type, i.level, i.ancient, i.flag_92, i.flag_98)
        self.assertEqual(item(68, 9, 1, 0), (68, 9 << 3, 0, 0, 1))
        self.assertEqual(item(6 * 512, 7, 0, 0x22), (6 * 512, 7 << 3, 0x22, 0, 0))
        slots = self.run_class({0: item(68, 9, 1, 0), 1: item(6 * 512, 7, 0, 0x22), 7: item(12 * 512 + 1, 4, 1, 5)})
        self.assertEqual(slots[6], (0x0b2a, 9, 1, 0))
        self.assertEqual(slots[7], (0x16e6, 7, 0, 0x22))
        self.assertEqual(slots[8], (0x22e7, 4, 0x66, 0x77))   # the wing: type and level only

    def test_equipment_slot_of_each_character_slot(self):
        self.assertEqual([self.lib.mu_he_equipment_of_slot(k) for k in range(11)], [-1, 2, 3, 4, 5, 6, 0, 1, 7, -1, 8])

    # ---- HERO-ITEMS-002 ----

    def run_world(self, equipment, world, class_byte=0x01, scene=6, buffs=(0, 0), byte_0e=0, model=0xa91,
                  prior=(0x1234, 0x55, 0x66, 0x77)):
        c = Character()
        c.model, c.class_byte, c.byte_0e, c.byte_16 = model, class_byte, byte_0e, 3
        for k in range(11):
            c.slots[k].type, c.slots[k].level, c.slots[k].option, c.slots[k].ext = prior
        items = [EMPTY] * 9
        for s, item in equipment.items():
            items[s] = item
        scale = Scale((7.0,) * 6, 7.0, 0xff, 0xff)
        self.lib.mu_he_set_character_class_world(ctypes.byref(c), (Item * 9)(*[Item(*i) for i in items]),
                                                 ctypes.byref(ScaleIn(world, scene, *buffs)), ctypes.byref(scale))
        slots = [(c.slots[k].type, c.slots[k].level, c.slots[k].option, c.slots[k].ext) for k in range(11)]
        return slots, scale, c

    def test_castle_worlds_replace_the_weapons_wing_and_helper(self):
        worn = {0: (3, 7 << 3, 5, 0, 1), 1: (6 * 512, 2 << 3, 9, 0, 1), 7: (12 * 512 + 1, 9 << 3, 0, 0, 0),
                8: (13 * 512 + 2, 1 << 3, 0, 0, 0)}
        for world in (0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x35, 0x61):
            slots, _, c = self.run_world(worn, world)
            # Dark Knight: the sword 0x0af6 in both hands at level 0, the option cleared, the worn ext kept
            self.assertEqual(slots[6], (0x0af6, 0, 0, 5), world)
            self.assertEqual(slots[7], (0x0af6, 0, 0, 9), world)
            self.assertEqual(slots[8], (-1, 0, 0x66, 0x77), world)    # the wing: type and level
            self.assertEqual(slots[10], (-1, 0, 0x66, 0x77), world)   # the helper too
            self.assertEqual(c.byte_16, 0)
            self.assertEqual(slots[2][0], 0x3750 + 1)                 # the parts are not touched
        for world in (0, 2, 0x11, 0x18, 0x34, 0x36, 0x60, 0x62):
            slots, _, c = self.run_world(worn, world)
            self.assertEqual((slots[6], slots[7], slots[8][0], c.byte_16), ((0xae9, 7, 1, 5), (0x16e6, 2, 1, 9), 0x22e7, 3))

    def test_castle_weapon_of_each_class(self):
        sword, bow, staff = (0x0af6, 0x0af6), (0x12f9, -1), (0x14eb, -1)
        want = [staff, sword, bow, sword, sword, staff, sword, sword, staff, sword, sword, staff, staff, sword, staff,
                sword]
        for nibble in range(16):
            slots, _, _ = self.run_world({0: (3, 0, 0, 0, 0), 1: (6 * 512, 0, 0, 0, 0)}, 0x12, class_byte=nibble | 0x30)
            self.assertEqual((slots[6][0], slots[7][0]), want[nibble], nibble)

    def test_castle_override_alone_returns_whether_it_ran(self):
        c = Character()
        c.class_byte = 2
        for k in range(11):
            c.slots[k].type = 0x1000 + k
        self.assertEqual(self.lib.mu_he_castle_override(ctypes.byref(c), 0x11), 0)
        self.assertEqual(c.slots[6].type, 0x1006)
        self.assertEqual(self.lib.mu_he_castle_override(ctypes.byref(c), 0x61), 1)
        self.assertEqual([c.slots[k].type for k in (6, 7, 8, 9, 10)], [0x12f9, -1, -1, 0x1009, -1])

    def test_scale_branches(self):
        table = [0.9, 0.9, 0.88, 0.95, 0.92, 0.9, 1.03, 0.9, 0.9, 0.9, 0.9, 0.99, 0.9, 0.9, 0.8, 1.1]
        f32 = lambda v: ctypes.c_float(v).value  # noqa: E731
        for nibble in range(16):
            _, scale, _ = self.run_world({}, 0, class_byte=nibble | 0x10)
            self.assertEqual((scale.object, scale.branch, scale.buff_queries), (f32(table[nibble]), 3, 2), nibble)
            self.assertEqual(list(scale.part), [0.0, f32(0.95) if nibble == 11 else 0.0, 0.0, 0.0, 0.0, 0.0])
            _, scale, _ = self.run_world({}, 0x35, class_byte=nibble)   # a castle world: no scene or buff test
            self.assertEqual((scale.object, scale.branch, scale.buff_queries),
                             (f32(0.88 if nibble == 2 else 0.9), 1, 0), nibble)
            self.assertEqual(list(scale.part), [0.0] * 6)
            self.assertEqual(self.lib.mu_he_class_scale(nibble, 0), f32(table[nibble]))
        _, scale, _ = self.run_world({}, 0, class_byte=6, scene=5)      # the character select
        self.assertEqual((scale.object, scale.branch, scale.buff_queries), (f32(1.7), 2, 0))
        _, scale, _ = self.run_world({}, 0, class_byte=6, buffs=(1, 0))
        self.assertEqual((scale.object, scale.branch, scale.buff_queries), (f32(1.1), 4, 1))
        _, scale, _ = self.run_world({}, 0, class_byte=6, buffs=(0, 1))
        self.assertEqual((scale.object, scale.branch, scale.buff_queries), (f32(1.1), 4, 2))
        slots, scale, _ = self.run_world({2: (0x18e6 - 0xae6, 0, 0, 0, 0)}, 0, byte_0e=1)   # c + 0xe: nothing written
        self.assertEqual((slots[0][0], scale.object, list(scale.part), scale.branch), (0x1234, 7.0, [7.0] * 6, 0))
        slots, scale, _ = self.run_world({0: (3, 0, 0, 0, 0)}, 0x12, model=0x7d9)           # not a Player model
        self.assertEqual((slots, scale.object, scale.branch), ([(0x1234, 0x55, 0x66, 0x77)] * 11, 7.0, 0xff))

    def draws(self, c):
        out = (PartDraw * 6)()
        return [(out[i].slot, out[i].type) for i in range(self.lib.mu_he_part_draws(ctypes.byref(c), out))]

    def test_body_part_loop_draws_the_head_last(self):
        for helm in HEAD_HELMS:
            slots, _, c = self.run_world({2: (helm - 0xae6, 0, 0, 0, 0)}, 0, class_byte=0x01)
            self.assertEqual(slots[0][0], 0x3701, hex(helm))
            self.assertEqual(self.draws(c), [(5, 0x3841), (4, 0x37f1), (3, 0x37a1), (2, 0x3751), (1, helm), (0, 0x3701)])
        for helm in (0x18e7, 0x18ef, 0x1926, 0x1a36):   # another helm hides the head: slot 0 is -1 and not drawn
            slots, _, c = self.run_world({2: (helm - 0xae6, 0, 0, 0, 0)}, 0, class_byte=0x01)
            self.assertEqual(slots[0][0], -1)
            self.assertEqual(self.draws(c), [(5, 0x3841), (4, 0x37f1), (3, 0x37a1), (2, 0x3751), (1, helm)])
        _, _, c = self.run_world({}, 0, class_byte=0x01)   # no helm: the class helm part is the head model in slot 1
        self.assertEqual(self.draws(c), [(5, 0x3841), (4, 0x37f1), (3, 0x37a1), (2, 0x3751), (1, 0x3701)])

    def test_class_part_models(self):
        t = self.lib.mu_he_part_draw_type
        self.assertEqual(t(5, 1, 0x18e6 + 10), 0x36ce + 10 + 14)        # class nibble 5: index 10/11 of groups 7..11
        self.assertEqual(t(5, 5, 0xae6 + 11 * 512 + 11), 0x36ce + 11 + 22)
        self.assertEqual(t(5, 1, 0x18e6 + 12), 0x18e6 + 12)
        self.assertEqual(t(6, 2, 0xae6 + 8 * 512 + 5), 0x36d4 + 0 + 32)  # class nibble 6: index 5, 6, 8, 9
        self.assertEqual(t(6, 5, 0xae6 + 11 * 512 + 9), 0x36d4 + 3 + 40)  # group 11 counts as 10
        self.assertEqual(t(6, 1, 0x18e6 + 7), 0x18e6 + 7)
        self.assertEqual(t(4, 1, 0x18e6 + 5), 0x38f6 + 5)               # class nibble 4: the helm slot only
        self.assertEqual(t(4, 2, 0x18e6 + 5), 0x18e6 + 5)
        self.assertEqual(t(4, 1, 0x18e6 + 7), 0x18e6 + 7)
        for nibble in range(16):                                        # a class head is drawn as it is
            self.assertEqual(t(nibble, 0, 0x3700 + nibble), 0x3700 + nibble)


@unittest.skipUnless(PRIVATE, 'original captures are opt-in (MU_RECOVERY_INTEGRATION=1)')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        """validate_hero_items: SetCharacterClass and 0x00cd0995 against the pinned client, with mutants."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'hero.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_hero_items.py'), '--mutations',
                            '--output', str(path)], check=True, capture_output=True)
            report = json.loads(path.read_text())
        self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
        self.assertEqual(report['families']['set_class']['cases'], 3000)
        self.assertEqual(report['families']['defaults']['cases'], 256)
        self.assertEqual(report['families']['record']['cases'], 3000)   # APP-POLISH-008
        # HERO-ITEMS-002: the 17 helms x 256 class bytes, 23 control rows x 16; 320 worlds x 16 + 3,000 direct
        self.assertEqual(report['families']['head_rows']['cases'], 17 * 256 + 23 * 16)
        table = report['families']['head_rows']['table']
        self.assertEqual(sum(1 for row in table.values() if row['listed']), 17)
        self.assertTrue(all(row['mismatches'] == 0 and row['head_draws'] == (256 if row['listed'] else 0)
                            for row in table.values()))
        self.assertEqual(report['families']['castle']['cases'], 320 * 16 + 3000)
        self.assertEqual(report['families']['scale']['cases'], 256 * 2 * 4 * 4)
        self.assertEqual(report['families']['part_loop']['cases'], 3000 + 1376)
        self.assertEqual(report['families']['part_type']['cases'], 0x4400)
        self.assertEqual(len(report['mutants']), 51)
        self.assertTrue(all(report['mutants'].values()))


def walk(*args, frames=60):
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run([str(WALK), '--game-root', GAME, '--headless', '--backend', 'soft', '--no-audio',
                                 '--width', '320', '--height', '240', '--every', '1000', '--out-dir', tmp,
                                 '--tile', '128,124', '--no-players', '--frames', str(frames), '--quiet', *args],
                                capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr[-2000:]}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    pre = next((r for r in rows if r.get('item_pre_draw') is True), None)
    particles = next(r for r in rows if r.get('particles') is True)
    walk.hero_class = next((r for r in rows if r.get('hero_class') is True), None)   # HERO-ITEMS-002
    return pre, particles


def hero_class(*args, frames=2):
    """HERO-ITEMS-002: the summary's hero_class row (None when the end of SetCharacterClass changed nothing)."""
    walk(*args, frames=frames)
    return walk.hero_class


def item_file(code):
    """The installed Item.bmd's model file of an item code ('Item/NAME.bmd'), or None without a record."""
    p = subprocess.run([str(DATA), 'item', str(Path(GAME, 'Data/Local/Item.bmd')), str(code)], capture_output=True,
                       text=True)
    if p.returncode:
        return None
    record = json.loads(p.stdout.splitlines()[0])
    return record['folder'].replace('\\', '/').split('/', 1)[1] + record['file']


@unittest.skipUnless(PRIVATE and GAME, 'needs MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class HeroScene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'build/mu-walk'], check=True, capture_output=True)

    def test_record_types_run_the_pre_draw_programs(self):
        pre, particles = walk('--hero-item', 'weapon0=Item/blade01.bmd', '--hero-item', 'weapon1=Item/CR_shield01.bmd',
                              '--hero-item', 'wing=Item/InnocenceCape.bmd')
        self.assertEqual(pre['hero'], {'pre_effects': 30, 'pre_refused': 0, 'hidden': 0})
        self.assertEqual(particles['sprites_created'], 30)
        self.assertEqual(particles['rand_calls'], 120)

    def test_left_hand_is_the_second_weapon_slot(self):
        pre, _ = walk('--hero-item', 'weapon1=Item/CR_shield01.bmd')
        self.assertEqual(pre['hero'], {'pre_effects': 4, 'pre_refused': 0, 'hidden': 0})

    def test_standard_names_keep_the_report(self):
        pre, particles = walk('--hero-item', 'weapon0=Item/Sword04.bmd', '--hero-item', 'wing=Item/Wing02.bmd')
        self.assertIsNone(pre)
        self.assertEqual(particles['sprites_created'], 0)
        self.assertIsNone(walk.hero_class)   # HERO-ITEMS-002: a Dark Knight in class parts outside the castle worlds


@unittest.skipUnless(PRIVATE and GAME, 'needs MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class HeroClassScene(unittest.TestCase):
    """HERO-ITEMS-002: the head slot, the castle worlds' weapons and the scales on the hero (installed data)."""

    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'build/mu-walk', 'build/mu-data'], check=True, capture_output=True)

    def test_each_listed_helm_loads_and_draws_the_class_head(self):
        seen = []
        for helm in HEAD_HELMS:
            code = helm - 0xae6
            file = item_file(code)
            if file is None:   # the installed Item.bmd has no record of this helm (7:87..89 in the pinned install)
                continue
            seen.append(helm)
            row = hero_class('--hero-item', f'helm={file}@7:{code - 7 * 512}')
            self.assertEqual((row['head'], row['head_file'], row['refused']), (0x3701, 'HelmClass02.bmd', 0), hex(helm))
            self.assertGreater(row['head_passes'], 0, hex(helm))
        self.assertGreaterEqual(len(seen), 10)

    def test_the_head_follows_the_class(self):
        file = item_file(0x18f0 - 0xae6)   # Vine Helm
        for class_byte, head in ((0x02, 'HelmClass03.bmd'), (0x12, 'HelmClass203.bmd'), (0x4f, 'HelmClass416.bmd')):
            row = hero_class('--class', str(class_byte), '--hero-item', f'helm={file}@7:10')
            skin = (class_byte & 15) + 16 * (class_byte >> 4).bit_length()
            self.assertEqual((row['head'], row['head_file']), (0x3700 + skin, head))

    def test_another_helm_hides_the_head(self):
        self.assertIsNone(hero_class('--hero-item', f'helm={item_file(7 * 512 + 1)}@7:1'))
        self.assertIsNone(hero_class())

    def test_castle_worlds_give_the_class_weapon(self):
        worn = ('--hero-item', 'weapon0=Item/Sword04.bmd', '--hero-item', 'weapon1=Item/Shield01.bmd',
                '--hero-item', 'wing=Item/Wing02.bmd')
        for world in (18, 19, 20, 21, 22, 23, 53, 97):
            for class_byte, weapons, scale in ((1, [0x0af6, 0x0af6], 0.9), (2, [0x12f9, -1], 0.88),
                                               (0, [0x14eb, -1], 0.9)):
                if world not in (18, 97) and class_byte != 1:
                    continue
                row = hero_class('--world', str(world), '--tile', '30,90', '--class', str(class_byte), *worn)
                self.assertEqual((row['castle'], row['weapons'], row['wing'], row['refused'], row['branch']),
                                 (1, weapons, -1, 0, 1), (world, class_byte))
                self.assertEqual(row['scale'], scale)
        self.assertIsNone(hero_class('--world', '0', *worn))        # Lorencia keeps the worn items
        row = hero_class('--world', '17', '--tile', '30,90', *worn)   # a neighbour of the world list
        self.assertIsNone(row)

    def test_a_world_change_applies_and_drops_the_override(self):
        worn = ('--hero-item', 'weapon0=Item/Sword04.bmd', '--hero-item', 'wing=Item/Wing02.bmd')
        row = hero_class(*worn, '--travel-script', '3:to:18:30:90', frames=12)
        self.assertEqual((row['castle'], row['weapons'], row['wing']), (1, [0x0af6, 0x0af6], -1))
        self.assertIsNone(hero_class(*worn, '--travel-script', '3:to:18:30:90 9:to:0:128:124', frames=16))

    def test_class_scale_and_part_float(self):
        for class_byte, scale in ((2, 0.88), (3, 0.95), (4, 0.92), (6, 1.03), (0x0b, 0.99), (0x0e, 0.8), (0x0f, 1.1),
                                  (0x12, 0.88)):
            row = hero_class('--class', str(class_byte))
            self.assertEqual((row['scale'], row['branch'], row['castle']), (scale, 3, 0), class_byte)
            self.assertEqual(row['part_scale'], [0.0, 0.95 if class_byte & 15 == 0x0b else 0.0, 0.0, 0.0, 0.0, 0.0])
        for class_byte in (0, 1, 5, 7, 8, 9, 10, 12, 13):          # the creation default 0.9: no row
            self.assertIsNone(hero_class('--class', str(class_byte)), class_byte)


if __name__ == '__main__':
    unittest.main()
