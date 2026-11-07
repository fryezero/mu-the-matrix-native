"""HERO-ITEMS-001: the hero's part slots from its equipment records (reconstructed/hero-equipment).

Portable: worked examples of SetCharacterClass 0x01394870 (mu_he_set_character_class) and 0x00cd0995
(mu_he_item_flag) through ctypes, and the class parts it writes for an empty slot equal the parts the native
character loads (model-codec mu_character_part_type) for every class byte.

Private, original instructions (MU_RECOVERY_INTEGRATION=1, pinned text/data): scripts/validate_hero_items.py with
its mutants (validator row validate_hero_items).

Private, installed data (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): Lorencia through `mu-walk --hero-item` (the
front end's equipment, as mu-client passes the demo characters'): files with non-standard names now take their
Item.bmd record's type, so the pre-draw programs of RENDER-ITEMS-002R run on the hero (blade01.bmd 0x0b4b,
CR_shield01.bmd 0x1748 in the left hand, InnocenceCape.bmd 0x2382); standard-named items keep the report.
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
from validate_hero_items import Item  # noqa: E402  (ctypes view only; Unicorn is not needed)
from validate_players import Character  # noqa: E402

WALK = NATIVE/'build/mu-walk'
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

    def test_equipment_slot_of_each_character_slot(self):
        self.assertEqual([self.lib.mu_he_equipment_of_slot(k) for k in range(11)], [-1, 2, 3, 4, 5, 6, 0, 1, 7, -1, 8])


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
        self.assertEqual(len(report['mutants']), 14)
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
    return pre, particles


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


if __name__ == '__main__':
    unittest.main()
