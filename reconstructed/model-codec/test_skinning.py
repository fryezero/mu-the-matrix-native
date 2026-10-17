"""Checks for the authored model transform (0x012b5bde) and animation tick (0x012b4dd3)."""
import importlib.util
import json
import math
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
    spec = importlib.util.spec_from_file_location('validate_skinning', ROOT/'scripts/validate_skinning.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


IDENTITY = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]


class SkinningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        cls.v = load_validator()
        cls.authored = cls.v.Authored(HERE/f'libskinning.{SUFFIX}')

    def setup(self, matrices, vertices, normals, **params):
        """One mesh; vertices [(bone, (x, y, z))], normals [(bone, (x, y, z))]."""
        v = self.v
        window = v.Region('window', v.WINDOW, v.poison(v.PAGE, 0x11), bytes(v.PAGE))
        bones = v.WINDOW+0x200
        for index, matrix in enumerate(matrices):
            window.define(bones+index*0x30, struct.pack('<12f', *matrix))
        vertex_array = v.WINDOW+0x600
        normal_array = v.WINDOW+0xa00
        for index, (bone, position) in enumerate(vertices):
            window.define(vertex_array+index*16, struct.pack('<hh3f', bone, 0, *position))
        for index, (bone, normal) in enumerate(normals):
            window.define(normal_array+index*20, struct.pack('<hh3fhh', bone, 0, *normal, 0, 0))
        meshes = [{'vertices': vertex_array, 'normals': normal_array, 'nv': len(vertices), 'nn': len(normals)}]
        return v.transform_setup('t', window, v.WINDOW, bones, meshes, params)

    def run_transform(self, setup):
        result = self.authored.run_transform(setup)
        self.assertEqual(result['status'], 0)
        self.assertEqual(result['regions'], self.v.python_transform(setup))
        return result['regions']

    def floats(self, regions, name, count, offset=0):
        return list(struct.unpack_from(f'<{count}f', regions[name], offset))

    def test_vertex_is_bone_matrix_times_position_then_body_scale_and_origin(self):
        bone = [0.0, -1.0, 0.0, 10.0, 1.0, 0.0, 0.0, 20.0, 0.0, 0.0, 1.0, 30.0]  # 90 degrees about z
        setup = self.setup([IDENTITY, bone], [(1, (1.0, 2.0, 3.0))], [(1, (1.0, 0.0, 0.0))],
                           translate=1, body_scale=2.0, origin=(100.0, 200.0, 300.0))
        regions = self.run_transform(setup)
        # M*p = (-2+10, 1+20, 3+30); scaled by 2, then origin added.
        self.assertEqual(self.floats(regions, 'vertices:0', 3), [116.0, 242.0, 366.0])
        # Normals are rotated only: no translation, scale or origin.
        self.assertEqual(self.floats(regions, 'normals:0', 3), [0.0, 1.0, 0.0])
        regions = self.run_transform(self.setup([IDENTITY, bone], [(1, (1.0, 2.0, 3.0))], [], translate=0x100))
        self.assertEqual(self.floats(regions, 'vertices:0', 3), [8.0, 21.0, 33.0])  # low byte 0: untranslated

    def test_bone_scale_scales_the_rotated_part_and_vertex_scale_the_position(self):
        bone = [2.0, 0.0, 0.0, 1.0, 0.0, 2.0, 0.0, 2.0, 0.0, 0.0, 2.0, 3.0]
        regions = self.run_transform(self.setup([bone], [(0, (1.0, 1.0, 1.0))], [], bone_scale=0.5))
        self.assertEqual(self.floats(regions, 'vertices:0', 3), [2.0, 3.0, 4.0])  # R p * 0.5 + t
        regions = self.run_transform(self.setup([bone], [(0, (1.0, 1.0, 1.0))], [], vertex_scale=3.0))
        self.assertEqual(self.floats(regions, 'vertices:0', 3), [7.0, 8.0, 9.0])  # M (3p)
        regions = self.run_transform(self.setup([bone], [(0, (1.0, 1.0, 1.0))], [], vertex_scale=-0.0))
        self.assertEqual(self.floats(regions, 'vertices:0', 3), [3.0, 4.0, 5.0])  # -0 == 0: unscaled

    def test_light_terms_clamp_and_floor(self):
        # Override vector (1.3, 0, 2) with zero light angles: L1 = (1.3, 0, 2), L2 = (1.3, -0.5, 1.8).
        normals = [(0, (0.0, 0.0, 1.0)), (0, (0.0, 0.0, -1.0))]
        regions = self.run_transform(self.setup([IDENTITY], [], normals, lighting=1, override=1, ambient=0.5,
                                                light_scale=0.25, light_minimum=0.3))
        primary = self.floats(regions, 'lights:0', 2)
        secondary = self.floats(regions, 'secondary:0', 2)
        self.assertEqual(primary[0], struct.unpack('<f', struct.pack('<f', 2.0*0.25+0.5))[0])
        self.assertAlmostEqual(primary[1], 0.3, places=6)            # 0.5-0.5 = 0 clamped to minimum
        self.assertAlmostEqual(secondary[0], 1.8*0.8+0.5, places=5)
        self.assertAlmostEqual(secondary[1], 0.2, places=6)          # floor
        regions = self.run_transform(self.setup([IDENTITY], [], normals, lighting=0))
        self.assertNotIn(b'\0', regions['lights:0'])                  # untouched poison without the flag

    def test_world_30_rewrites_light_angles(self):
        setup = self.setup([IDENTITY], [], [(0, (0.0, 1.0, 0.0))], lighting=1, world=30,
                           light_angles=(10.0, 20.0, 30.0))
        regions = self.run_transform(setup)
        angles = self.floats(regions, 'window', 3, setup['model']+0x98-self.v.WINDOW)
        self.assertEqual(angles, [0.0, 0.0, -45.0])
        setup = self.setup([IDENTITY], [], [(0, (0.0, 1.0, 0.0))], lighting=1, world=31,
                           light_angles=(10.0, 20.0, 30.0))
        regions = self.run_transform(setup)
        self.assertEqual(self.floats(regions, 'window', 3, setup['model']+0x98-self.v.WINDOW), [10.0, 20.0, 30.0])

    def test_box_from_vertex_bounds_or_arguments(self):
        vertices = [(0, (1.0, -2.0, 3.0)), (0, (-4.0, 5.0, 0.5))]
        setup = self.setup([IDENTITY], vertices, [], bounds_mode=2, translate=1, origin=(10.0, 10.0, 10.0))
        regions = self.run_transform(setup)
        box = setup['arguments'][6]-self.v.WINDOW
        values = self.floats(regions, 'window', 12, box)
        # Bounds use positions before the origin is added; the box origin adds it once.
        self.assertEqual(values, [6.0, 8.0, 10.5, 5.0, 0.0, 0.0, 0.0, 7.0, 0.0, 0.0, 0.0, 2.5])
        setup = self.setup([IDENTITY], vertices, [], bounds_mode=0, bounds_min=(-1.0, -2.0, -3.0),
                           bounds_max=(1.0, 2.0, 3.0), origin=(5.0, 5.0, 5.0))
        values = self.floats(self.run_transform(setup), 'window', 12, setup['arguments'][6]-self.v.WINDOW)
        self.assertEqual(values, [4.0, 3.0, 2.0, 2.0, 0.0, 0.0, 0.0, 4.0, 0.0, 0.0, 0.0, 6.0])

    def test_null_bones_return_and_outside_memory(self):
        setup = self.setup([IDENTITY], [(0, (1.0, 2.0, 3.0))], [], null_bones=True)
        regions = self.run_transform(setup)
        self.assertEqual(regions['vertices:0'], bytes(setup['regions'][1].data))
        setup = self.setup([IDENTITY], [(0x7fff, (1.0, 2.0, 3.0))], [])
        self.assertEqual(self.authored.run_transform(setup)['status'], 2)

    def tick(self, actions, **params):
        setup = self.v.tick_setup('t', actions, params)
        native = self.authored.run_tick(setup)
        self.assertEqual(native['status'], 0)
        self.assertEqual((native['regions'], native['loop']), self.v.python_tick(setup))
        window = native['regions']['window']
        return {'frame': struct.unpack_from('<f', window, 0x100)[0],
                'prior_frame': struct.unpack_from('<f', window, 0x110)[0],
                'prior_action': struct.unpack_from('<H', window, 0x120)[0],
                'model_frame': struct.unpack_from('<f', window, 0xac)[0],
                'integer_frame': struct.unpack_from('<h', window, 0xb4)[0], 'loop': native['loop']}

    def test_tick_sets_prior_only_when_the_integer_frame_changes(self):
        actions = [(0, 8, 0), (0, 8, 0), (0, 8, 0)]
        result = self.tick(actions, current=2, frame=6.75, speed=0.5, declare_prior=True)
        self.assertEqual((result['prior_action'], result['prior_frame']), (2, 6.0))
        self.assertEqual((result['frame'], result['integer_frame'], result['loop']), (7.25, 7, 1))
        result = self.tick(actions, current=2, frame=6.25, speed=0.5, declare_prior=True)
        self.assertEqual((result['prior_action'], result['prior_frame']), (0x5555, 123.0))  # untouched

    def test_tick_wraps_by_integer_modulo_or_clamps_with_stop_flag(self):
        result = self.tick([(0, 8, 0)], frame=7.75, speed=0.5)
        self.assertEqual((result['frame'], result['loop']), (0.25, 0))
        result = self.tick([(0, 8, 1)], frame=6.75, speed=0.5)   # lock: limit keys-1
        self.assertEqual((result['frame'], result['loop']), (0.25, 0))
        result = self.tick([(1, 8, 0)], frame=7.75, speed=0.5)   # stop flag: clamp
        self.assertEqual((result['frame'], result['loop']), (struct.unpack('<f', struct.pack('<f', 8-0.01))[0], 0))
        result = self.tick([(0, 8, 0)], frame=0.25, speed=-0.5)  # non-positive adds keys-1
        self.assertEqual(result['frame'], 6.75)
        result = self.tick([(0, 8, 0)], frame=5.75, speed=0.5, scene=5)  # tested with +2
        self.assertEqual((result['frame'], result['loop']), (6.25, 0))
        result = self.tick([(0, 1, 0)], frame=0.5, speed=0.5)    # one key: early return, nothing written
        self.assertEqual((result['frame'], result['loop']), (0.5, 1))

    def test_python_model_agrees_and_negative_controls_fail(self):
        v = self.v
        differences = {'transpose': 0, 'normal-translate': 0, 'prior-every-tick': 0, 'ignore-lock': 0}
        cases = 0
        for setup in v.synthetic_transform_cases():
            native = self.authored.run_transform(setup)
            self.assertEqual(native['status'], 0, setup['label'])
            self.assertEqual(native['regions'], v.python_transform(setup), setup['label'])
            for variant in ('transpose', 'normal-translate'):
                differences[variant] += int(native['regions'] != v.python_transform(setup, variant))
            cases += 1
        for setup in v.synthetic_tick_cases():
            native = self.authored.run_tick(setup)
            observed = (native['regions'], native['loop'])
            self.assertEqual(observed, v.python_tick(setup), setup['label'])
            for variant in ('prior-every-tick', 'ignore-lock'):
                differences[variant] += int(observed != v.python_tick(setup, variant))
            cases += 1
        self.assertGreater(cases, 700)
        self.assertGreater(differences['transpose'], 150)
        self.assertGreater(differences['normal-translate'], 150)
        self.assertGreater(differences['prior-every-tick'], 150)
        self.assertGreater(differences['ignore-lock'], 20)

    def test_vector_helpers_match_python_rows(self):
        import ctypes
        generator = random.Random(4)
        for _ in range(50):
            vector = [self.v.f32(generator.uniform(-9, 9)) for _ in range(3)]
            matrix = [self.v.f32(generator.uniform(-2, 2)) for _ in range(12)]
            for name in ('rotate', 'transform', 'irotate'):
                a = (ctypes.c_float*3)(*vector)
                m = (ctypes.c_float*12)(*matrix)
                out = (ctypes.c_float*3)()
                self.authored.vectors[name](ctypes.addressof(a), ctypes.addressof(m), ctypes.addressof(out))
                rows = self.v.py_rows(matrix, vector, transpose=name == 'irotate')
                if name == 'transform':
                    rows = [self.v.f32(rows[k]+matrix[k*4+3]) for k in range(3)]
                self.assertEqual(list(out), rows)

    def test_validator_refuses_unpinned_text_without_optional_emulator(self):
        with tempfile.TemporaryDirectory() as directory:
            text = Path(directory)/'authored.bin'
            text.write_bytes(b'not captured code')
            result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_skinning.py'),
                                     '--text', str(text), '--data', str(text), '--flag', str(text),
                                     '--feature', str(text)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('pinned restored text', result.stderr)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'Private transform/tick instruction comparison is opt-in')
    def test_private_original_transform_and_tick_instructions(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA', ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        flag = Path(os.environ.get('MU_TRIG_FLAG', ROOT/'evidence/trig-state-15/captures/late/math-dispatch-flag.bin'))
        feature = Path(os.environ.get('MU_MATH_DATA', ROOT/'evidence/x86-math-capture-09'))/'cpu-features.bin'
        game_root = os.environ.get('MU_GAME_ROOT')
        self.assertTrue(game_root, 'Requested integration needs MU_GAME_ROOT for installed v12/v14 models')
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_skinning.py'), '--text', str(text),
                            '--data', str(data), '--flag', str(flag), '--feature', str(feature),
                            '--game-root', game_root, '--versions', '12,14', '--workers', '4',
                            '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
        for key, minimum in (('synthetic_transform', 200), ('chained_transform', 20), ('synthetic_tick', 450)):
            self.assertEqual(result[key]['matches'], result[key]['cases'], key)
            self.assertGreaterEqual(result[key]['cases'], minimum, key)
        for total, matched in result['helpers'].values():
            self.assertEqual(total, matched)
        self.assertTrue(all(result['negative_controls'].values()))
        for branch in ('null-bones-return', 'light-override', 'light-world-30', 'light-default', 'vertex-prescale',
                       'vertex-plain', 'vertex-bone-scale', 'bounds-min-update', 'bounds-max-update',
                       'light-minimum-clamp', 'secondary-floor', 'box-from-bounds', 'box-from-arguments'):
            self.assertIn(branch, result['synthetic_transform']['branches'])
        for branch in ('tick-early-return', 'tick-no-keys-return', 'tick-prior-update', 'tick-nonpositive-shift',
                       'tick-clamp', 'tick-lock-limit', 'tick-scene-5', 'tick-world-39-action-7', 'tick-wrap'):
            self.assertIn(branch, result['synthetic_tick']['branches'])
        installed = result['installed']
        for key in ('transform', 'tick'):
            self.assertEqual(installed[key]['matches'], installed[key]['cases'], key)
        self.assertEqual(installed['per_version']['12']['files'], 180)
        self.assertEqual(installed['per_version']['14']['files'], 216)
        self.assertEqual(installed['per_version']['12']['reader_rejected'], 0)
        self.assertEqual(installed['per_version']['14']['reader_rejected'], 0)
        self.assertEqual(installed['per_version']['14']['compared'], 216)
        self.assertGreater(installed['transform']['vertices'], 20000)


if __name__ == '__main__':
    unittest.main()
