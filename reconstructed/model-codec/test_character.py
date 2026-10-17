"""Checks for the authored character helpers (NATIVE-CHAR-001).

Portable: worked examples of rotation position 0x012b7019 and transform
position 0x012b6ef1 against the validator's independent Python model, the
class tier/skin-index/tier-2 tables, the body-part file names of the loader
0x01830aa6, and refusal of unpinned text. Private (MU_RECOVERY_INTEGRATION=1):
scripts/validate_character.py against the actual client instructions, with
installed Player.bmd chains when MU_GAME_ROOT is set.
"""
import importlib.util
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'


def load_validator():
    spec = importlib.util.spec_from_file_location('validate_character', ROOT/'scripts/validate_character.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CharacterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        cls.v = load_validator()
        cls.authored = cls.v.Authored(HERE/f'libcharacter.{SUFFIX}')

    def run_case(self, setup):
        native = self.authored.run_position(setup)
        self.assertEqual(native['status'], 0)
        self.assertEqual(native['regions'], self.v.python_position(setup), setup['label'])
        return native['regions']

    def test_rotation_position_scales_and_copies_the_bone_matrix(self):
        v = self.v
        generator = random.Random(1)
        matrix = [0.0, -1.0, 0.0, 10.0, 1.0, 0.0, 0.0, 20.0, 0.0, 0.0, 1.0, 30.0]
        setup = v.position_setup('worked', 'rotation', generator, matrix=matrix, vector=[2.0, 3.0, 4.0], scale=0.5)
        regions = self.run_case(setup)
        out = struct.unpack_from('<3f', regions['window'], 0x300)
        self.assertEqual(out, (-1.5, 1.0, 2.0))   # 0.5 * R * v; the translation column is not used
        root = struct.unpack_from('<12f', regions['root'], v.ROOT_MATRIX-v.ROOT_REGION[0])
        self.assertEqual(list(root), matrix)
        null = v.position_setup('null', 'rotation', generator, null=True)
        self.assertEqual(self.run_case(null), {r.name: bytes(r.data) for r in null['regions']})
        for alias in ('out-vector', 'out-matrix', 'root-matrix'):
            self.run_case(v.position_setup(alias, 'rotation', generator, alias=alias))

    def test_transform_position_world_and_local(self):
        v = self.v
        generator = random.Random(2)
        matrix = [1.0, 0.0, 0.0, 10.0, 0.0, 1.0, 0.0, 20.0, 0.0, 0.0, 1.0, 30.0]
        world = v.position_setup('world', 'transform', generator, matrix=matrix, vector=[1.0, 2.0, 3.0], scale=2.0,
                                 origin=[100.0, 200.0, 300.0], world=0x101)
        out = struct.unpack_from('<3f', self.run_case(world)['window'], 0x300)
        self.assertEqual(out, (122.0, 244.0, 366.0))   # (M v) * scale + origin
        local = v.position_setup('local', 'transform', generator, matrix=matrix, vector=[1.0, 2.0, 3.0], scale=2.0,
                                 origin=[100.0, 200.0, 300.0], world=0x100)
        out = struct.unpack_from('<3f', self.run_case(local)['window'], 0x300)
        self.assertEqual(out, (11.0, 22.0, 33.0))       # low byte clear: M v only
        for case in v.position_cases():
            self.run_case(case)

    def test_class_tables_and_part_files(self):
        a, v = self.authored, self.v
        for value in range(256):
            self.assertEqual(a.class_tier(value), v.py_tier(value))
            self.assertEqual(a.skin_index(value), v.py_skin(value))
            self.assertEqual(a.skips_tier2(value), v.py_skips(value))
        self.assertEqual([a.class_tier(c) for c in (0x01, 0x11, 0x21, 0x41, 0x81, 0x31)], [1, 2, 3, 4, 5, 3])
        self.assertEqual(a.skin_index(0x11), 17)
        self.assertEqual(a.file_for(0x3700), 'HelmClass01.bmd')
        self.assertEqual(a.file_for(0x3750+0x10+1), 'ArmorClass202.bmd')
        self.assertEqual(a.file_for(0x37a0+0x20+15), 'PantClass316.bmd')
        self.assertEqual(a.file_for(0x37f0+0x40+9), 'GloveClass410.bmd')   # tier 5 loads the tier-4 names
        self.assertIsNone(a.file_for(0x3840+0x10+3))                      # tier 2 skipped for base class 3
        self.assertIsNone(a.file_for(0x3700-1))
        self.assertIsNone(a.file_for(0x3700+5*0x50))

    def test_refuses_unpinned_text(self):
        with tempfile.TemporaryDirectory() as directory:
            text = Path(directory)/'text.bin'
            text.write_bytes(b'\0'*64)
            result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_character.py'),
                                     '--text', str(text), '--data', str(text), '--flag', str(text),
                                     '--feature', str(text)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('pinned restored text', result.stderr)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'Private character instruction comparison is opt-in')
    def test_private_original_character_instructions(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA', ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        flag = Path(os.environ.get('MU_TRIG_FLAG', ROOT/'evidence/trig-state-15/captures/late/math-dispatch-flag.bin'))
        feature = Path(os.environ.get('MU_MATH_DATA', ROOT/'evidence/x86-math-capture-09'))/'cpu-features.bin'
        game_root = os.environ.get('MU_GAME_ROOT')
        command = [sys.executable, str(ROOT/'scripts/validate_character.py'), '--text', str(text), '--data', str(data),
                   '--flag', str(flag), '--feature', str(feature)]
        if game_root:
            command += ['--game-root', game_root, '--limit', os.environ.get('MU_CHARACTER_LIMIT', '12')]
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory)/'report.json'
            subprocess.run(command+['--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
        self.assertEqual(result['positions']['matches'], result['positions']['cases'])
        self.assertGreaterEqual(result['positions']['cases'], 380)
        for name, entry in result['class_helpers'].items():
            self.assertEqual(entry, {'cases': 256, 'matches': 256}, name)
        self.assertTrue(result['loader']['match'])
        self.assertEqual(result['loader']['calls'], 380)
        self.assertGreater(result['negative_controls']['unscaled_rotation_position'], 0)
        if game_root:
            installed = result['installed']
            self.assertTrue(all(s['ok'] for s in installed['player_states']))
            for key in ('parts', 'items', 'roots'):
                summary = installed[f'{key}_summary']
                self.assertEqual(summary['matches'], summary['cases'], key)
                self.assertGreater(summary['cases'], 0, key)


if __name__ == '__main__':
    unittest.main()
