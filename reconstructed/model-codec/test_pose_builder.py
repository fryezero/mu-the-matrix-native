"""Checks for the authored pose builder (client 0x012b5064..0x012b58cb)."""
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'


def load_validator():
    spec = importlib.util.spec_from_file_location('validate_pose_builder', ROOT/'scripts/validate_pose_builder.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bone(parent, positions, angles):
    return {'dummy': 0, 'name': b'b', 'parent': parent, 'tracks': [(positions, angles)]}


class PoseBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        cls.v = load_validator()
        cls.authored = cls.v.Authored(HERE/f'libposebuilder.{SUFFIX}')

    def build(self, actions, bones, **params):
        v = self.v
        tcase = v.tracks.build_case('t', actions, bones)
        setup = v.make_setup('t', tcase, v.seed_authored(self.authored, tcase), params)
        result = self.authored.run(setup)
        self.assertEqual(result['status'], 0)
        return setup, result

    def matrices(self, setup, result, count):
        low = setup['output_span'][0]-self.v.WINDOW
        return [struct.unpack_from('<12f', result['window'], low+i*0x30) for i in range(count)]

    def test_spherical_interpolation_between_prior_and_current_keys(self):
        # Root yaw 0 -> 90 degrees about z; t = 0.5 must give 45 degrees.
        quarter = math.pi/2
        setup, result = self.build([2], [bone(-1, [(0.0, 0.0, 0.0), (10.0, 20.0, 30.0)],
                                              [(0.0, 0.0, 0.0), (0.0, 0.0, quarter)])],
                                   frame=1.5, prior_frame=0.0, keep_root=1, root_matrix=[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0])
        m = self.matrices(setup, result, 1)[0]
        c = math.cos(math.pi/4)
        for actual, expected in zip(m, (c, -c, 0, 5.0, c, c, 0, 10.0, 0, 0, 1, 15.0)):
            self.assertAlmostEqual(actual, expected, places=6)
        # A component-wise lerp would leave an unnormalized quaternion: m00 = 0.75.
        self.assertGreater(abs(m[0]-0.75), 0.04)
        q = struct.unpack_from('<4f', result['quaternions'], self.v.QUATERNIONS-self.v.GLOBAL_REGIONS['quaternions'][0])
        self.assertAlmostEqual(q[2], math.sin(math.pi/8), places=6)
        self.assertAlmostEqual(q[3], math.cos(math.pi/8), places=6)

    def test_frame_reset_keeps_fraction_and_stores_frame_fields(self):
        v = self.v
        positions = [(float(k), 0.0, 0.0) for k in range(4)]
        setup, result = self.build([4], [bone(-1, positions, [(0.0, 0.0, 0.0)]*4)],
                                   frame=4.25, prior_frame=7.0, keep_root=1, root_matrix=[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0])
        model = setup['model']-v.WINDOW
        window = result['window']
        self.assertEqual(struct.unpack_from('<f', window, model+0xac)[0], 4.25)
        # Integer frame 4 >= 4 keys resets to key 0 (not modulo, not last key);
        # the fraction 0.25 was taken before the reset. Prior frame 7 -> 0.
        self.assertEqual(struct.unpack_from('<h', window, model+0xb4)[0], 0)
        self.assertEqual(self.matrices(setup, result, 1)[0][3], 0.0)
        setup, result = self.build([4], [bone(-1, positions, [(0.0, 0.0, 0.0)]*4)],
                                   frame=2.25, prior_frame=1.0, keep_root=1, root_matrix=[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0])
        # x = p_prior*(1-t) + p_current*t with prior key 1, current key 2, t 0.25.
        self.assertEqual(self.matrices(setup, result, 1)[0][3], 1.25)

    def test_action_clamps_and_argument_slot(self):
        v = self.v
        setup, result = self.build([1, 1], [bone(-1, [(1.0, 2.0, 3.0)], [(0.0, 0.0, 0.0)])],
                                   prior_action=0x12340007, current=9, frame=0.0)
        self.assertEqual(result['prior_action'], 0x12340000)
        self.assertEqual(struct.unpack_from('<H', result['window'], setup['model']+0xa8-v.WINDOW)[0], 0)

    def test_dummy_slots_untouched_and_child_of_dummy_uses_prior_slot(self):
        v = self.v
        identity = [(0.0, 0.0, 0.0)]
        setup, result = self.build([1], [bone(-1, [(1.0, 2.0, 3.0)], identity), {'dummy': 1},
                                         bone(1, [(0.5, 0.0, 0.0)], identity)], frame=0.0)
        low = setup['output_span'][0]-v.WINDOW
        before, after = setup['image'], result['window']
        self.assertEqual(after[low+0x30:low+0x60], before[low+0x30:low+0x60])
        prior = struct.unpack_from('<12f', before, low+0x30)
        child = struct.unpack_from('<12f', after, low+0x60)
        # Identity rotation and translation (0.5, 0, 0) composed with the prior slot.
        self.assertAlmostEqual(child[3], v.f32(v.f32(prior[0]*0.5)+prior[3]), places=6)
        self.assertEqual(child[0], prior[0])

    def test_locked_root_position_and_height(self):
        v = self.v
        positions = [(1.0, 2.0, 3.0), (5.0, 7.0, 11.0), (13.0, 17.0, 19.0)]
        setup, result = self.build([3], [bone(-1, positions, [(0.0, 0.0, 0.0)]*3)], frame=2.5, prior_frame=1.0,
                                   locks={0: 1}, height=100.0, keep_root=1,
                                   root_matrix=[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0])
        m = self.matrices(setup, result, 1)[0]
        # x, y from the current action's key 0; z interpolated, plus height.
        self.assertEqual((m[3], m[7], m[11]), (1.0, 2.0, 11.0*0.5+19.0*0.5+100.0))

    def test_python_model_agrees_and_negative_controls_fail(self):
        v = self.v
        differences = {'lerp': 0, 'modulo-wrap': 0}
        cases = 0
        for label, tcase, param_list in v.synthetic_groups():
            seeded = v.seed_authored(self.authored, tcase)
            for params in param_list:
                setup = v.make_setup(label, tcase, seeded, params)
                native = self.authored.run(setup)
                model = v.python_model(setup)
                self.assertEqual(native['status'], 0, label)
                observed = (native['window'], native['quaternions'], native['root'], native['prior_action'])
                self.assertEqual(observed, (bytes(model[0]), bytes(model[1]), bytes(model[2]), model[3]), label)
                for variant in differences:
                    wrong = v.python_model(setup, variant)
                    differences[variant] += int(observed != (bytes(wrong[0]), bytes(wrong[1]), bytes(wrong[2]),
                                                             wrong[3]))
                cases += 1
        self.assertGreater(cases, 400)
        self.assertGreater(differences['lerp'], 100)
        self.assertGreater(differences['modulo-wrap'], 20)

    def test_outside_memory_status(self):
        v = self.v
        tcase = v.tracks.build_case('far', [1], [bone(0x7fff, [(0.0, 0.0, 0.0)], [(0.0, 0.0, 0.0)])])
        setup = v.make_setup('far', tcase, v.seed_authored(self.authored, tcase), {'frame': 0.0})
        self.assertEqual(self.authored.run(setup)['status'], 2)

    def test_validator_refuses_unpinned_text_without_optional_emulator(self):
        with tempfile.TemporaryDirectory() as directory:
            text = Path(directory)/'authored.bin'
            text.write_bytes(b'not captured code')
            result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_pose_builder.py'),
                                     '--text', str(text), '--data', str(text), '--flag', str(text),
                                     '--feature', str(text)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('pinned restored text', result.stderr)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'Private pose-builder instruction comparison is opt-in')
    def test_private_original_pose_builder_instructions(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA', ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        flag = Path(os.environ.get('MU_TRIG_FLAG', ROOT/'evidence/trig-state-15/captures/late/math-dispatch-flag.bin'))
        feature = Path(os.environ.get('MU_MATH_DATA', ROOT/'evidence/x86-math-capture-09'))/'cpu-features.bin'
        game_root = os.environ.get('MU_GAME_ROOT')
        self.assertTrue(game_root, 'Requested integration needs MU_GAME_ROOT for installed v12/v14 models')
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_pose_builder.py'), '--text', str(text),
                            '--data', str(data), '--flag', str(flag), '--feature', str(feature),
                            '--game-root', game_root, '--versions', '12,14', '--workers', '4',
                            '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
        synthetic = result['synthetic']
        self.assertEqual(synthetic['matches'], synthetic['cases'])
        self.assertGreater(synthetic['cases'], 450)
        for total, matched in result['helpers']['cases'].values():
            self.assertEqual(total, matched)
        self.assertTrue(all(result['negative_controls'].values()))
        for branch in ('slerp-spherical', 'slerp-linear', 'slerp-negate-q', 'copy-equal', 'locked-root-position',
                       'special-bone-euler', 'root-scale-translate', 'current-frame-reset', 'prior-frame-reset',
                       'dummy-skip', 'child-compose', 'no-actions-return', 'acos-sse2'):
            self.assertIn(branch, synthetic['branches'])
        self.assertIn('slerp-opposite', synthetic['branches'])
        stops = {item['label']: item for item in result['characterization']}
        self.assertFalse(stops['zero-keys-undeclared']['emulator_returned'])
        self.assertFalse(stops['huge-interpolation-factor']['emulator_returned'])
        installed = result['installed']
        self.assertEqual(installed['matches'], installed['cases'])
        self.assertEqual(installed['per_version']['12']['files'], 180)
        self.assertEqual(installed['per_version']['14']['files'], 216)
        self.assertEqual(installed['per_version']['12']['reader_rejected'], 0)
        self.assertEqual(installed['per_version']['14']['reader_rejected'], 0)


if __name__ == '__main__':
    unittest.main()
