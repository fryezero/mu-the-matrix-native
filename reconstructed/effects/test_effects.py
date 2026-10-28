"""Portable checks of the reconstructed effect system (NATIVE-FX-001).

Synthetic effect descriptions only (no client data). The instruction comparison
against the client's own effect code is scripts/validate_effects.py; its
private run is gated by MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT.
"""
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LIBRARY = HERE / ('libeffects.dylib' if sys.platform == 'darwin' else 'libeffects.so')
sys.path.insert(0, str(ROOT / 'scripts'))
import pins
spec = importlib.util.spec_from_file_location('validate_effects', ROOT / 'scripts/validate_effects.py')
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)

CAMERA = V.DEFAULT_CAMERA
GL_ONE, GL_SRC_COLOR, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_DST_COLOR = 1, 0x300, 0x302, 0x303, 0x306


class Rng(ctypes.Structure):
    _fields_ = [('state', ctypes.c_uint32), ('calls', ctypes.c_uint64)]


def particle_system(**overrides):
    d = {'Type': 0, 'Name': 'synthetic', 'Texture': 'Data\\Effect\\none.ozj', 'Scale': 1.0, 'Duration': 2.0,
         'Looping': True, 'SpaceIsLocal': False, 'MaxParticle': 16, 'Blending': 1, 'Billboarding': 0,
         'LengthScale': 1.0, 'SpeedScale': 0.3,
         'Components': [{'Type': 0, 'Frequency': 1, 'Delay': 0.0, 'MinEmissionCount': 1, 'MaxEmissionCount': 3,
                         'Components': [{'Type': 0, 'Shape': 1, 'Radius': 0.5, 'EmitFromShell': False,
                                         'RandomDirection': False},
                                        {'Type': 2, 'Min': 0.5, 'Max': 1.0, 'Curve': None},
                                        {'Type': 4, 'Min': 0.2, 'Max': 0.4, 'Curve': None},
                                        {'Type': 5, 'Min': 1.0, 'Max': 2.0, 'Curve': None}]}]}
    d.update(overrides)
    return d


def billboard(**overrides):
    d = {'Type': 1, 'Name': 'synthetic', 'Texture': 'Data\\Effect\\none.ozj', 'Scale': 1.0, 'Duration': 1.0,
         'Looping': True, 'Width': 2.0, 'Height': 1.0, 'RotationAngle': 0.0, 'Blending': 0, 'Billboarding': 0,
         'Brightness': 1.0, 'Components': []}
    d.update(overrides)
    return d


def run(library, document, frames=10, seed=1, texture=1, dt=0.1):
    """Client order per rendered frame: update, then draw (the update needs the previous draw)."""
    effect = V.NativeEffect(library, json.dumps(document), seed)
    rows = []
    try:
        for _ in range(frames):
            effect.update(dt)
            vertices, state, count = effect.draw(CAMERA, texture)
            rows.append({'particles': effect.particles(), 'vertices': vertices, 'state': state, 'count': count,
                         'faulted': library.lib.mu_fx_faulted(effect.h),
                         'rand_calls': library.lib.mu_fx_rand_calls(effect.h)})
    finally:
        effect.close()
    return rows


class EffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        cls.library = V.NativeLibrary(LIBRARY)
        lib = cls.library.lib
        lib.mu_fx_rng_seed.argtypes = [ctypes.POINTER(Rng), ctypes.c_uint32]
        lib.mu_fx_rand.argtypes = [ctypes.POINTER(Rng)]
        lib.mu_fx_rand.restype = ctypes.c_int32
        lib.mu_fx_curve_eval.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.c_float]
        lib.mu_fx_curve_eval.restype = ctypes.c_int

    def test_msvc_rand_sequence(self):
        rng = Rng()
        self.library.lib.mu_fx_rng_seed(ctypes.byref(rng), 1)
        values = [self.library.lib.mu_fx_rand(ctypes.byref(rng)) for _ in range(5)]
        self.assertEqual(values, [41, 18467, 6334, 26500, 19169])   # MSVC CRT rand() after srand(1)
        self.assertEqual(rng.calls, 5)

    def test_curve_hermite_endpoints_and_empty(self):
        class Key(ctypes.Structure):
            _fields_ = [('time', ctypes.c_float), ('value', ctypes.c_float), ('tangent', ctypes.c_float)]

        class Curve(ctypes.Structure):
            _fields_ = [('keys', ctypes.POINTER(Key)), ('count', ctypes.c_uint32)]

        keys = (Key * 2)(Key(0.0, 1.0, 0.0), Key(1.0, 3.0, 0.0))
        out = ctypes.c_float(-7.0)
        lib = self.library.lib
        self.assertEqual(lib.mu_fx_curve_eval(ctypes.byref(Curve(None, 0)), ctypes.byref(out), 0.5), 0)
        self.assertEqual(out.value, -7.0)   # untouched without keys
        for t, expected in ((0.0, 1.0), (1.0, 3.0), (0.5, 2.0)):
            self.assertEqual(lib.mu_fx_curve_eval(ctypes.byref(Curve(keys, 2)), ctypes.byref(out), t), 1)
            self.assertAlmostEqual(out.value, expected, places=6)

    def test_particle_system_emits_up_to_capacity(self):
        rows = run(self.library, particle_system(), frames=12)
        counts = [len(r['particles']) // 0x88 for r in rows]
        self.assertEqual(counts[0], 0)            # the first update runs before any draw: nothing emitted
        self.assertTrue(all(b >= a for a, b in zip(counts, counts[1:9])))
        self.assertEqual(max(counts), 16)         # MaxParticle
        for r, n in zip(rows, counts):
            self.assertEqual(r['count'], 4 * n)   # one GL_QUADS quad per particle
            self.assertEqual(len(r['vertices']), 36 * r['count'])
            self.assertFalse(r['faulted'])

    def test_deterministic_per_seed(self):
        a = run(self.library, particle_system(), seed=7)
        b = run(self.library, particle_system(), seed=7)
        c = run(self.library, particle_system(), seed=8)
        self.assertEqual([r['particles'] for r in a], [r['particles'] for r in b])
        self.assertEqual([r['vertices'] for r in a], [r['vertices'] for r in b])
        self.assertNotEqual([r['particles'] for r in a], [r['particles'] for r in c])

    def test_particle_blend_states(self):
        expected = {0: [0, 0, 0], 1: [1, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA], 2: [1, GL_ONE, GL_ONE],
                    3: [1, GL_DST_COLOR, 0]}
        for blending, state in expected.items():
            row = run(self.library, particle_system(Blending=blending), frames=3)[-1]
            self.assertEqual(row['state'][1:4], state, blending)
            self.assertEqual(row['state'][4], 1)   # texture enabled when loaded
            self.assertEqual(row['state'][6], 0)   # particle draw leaves culling alone

    def test_billboard_quad_and_blend_states(self):
        expected = {0: [0, 0, 0], 1: [1, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA], 2: [1, GL_SRC_COLOR, GL_ONE],
                    3: [1, GL_DST_COLOR, 0]}
        for blending, state in expected.items():
            row = run(self.library, billboard(Blending=blending), frames=2, texture=0)[-1]
            self.assertEqual(row['count'], 4)
            self.assertEqual(row['state'][1:4], state, blending)
            self.assertEqual(row['state'][4], 0)   # no texture: GL_TEXTURE_2D disabled
            self.assertEqual(row['state'][6], 1)   # billboards disable culling
            corners = [struct.unpack_from('<3f', row['vertices'], 36 * i) for i in range(4)]
            xs = sorted({round(c[0], 4) for c in corners})
            self.assertEqual(len(corners), 4)
            self.assertGreater(len(xs), 1)

    def test_expired_billboard_makes_no_gl_calls(self):
        rows = run(self.library, billboard(Looping=False, Duration=0.25, Blending=2), frames=5, texture=1)
        self.assertEqual(rows[0]['count'], 4)
        self.assertEqual(rows[0]['state'][4], 1)
        # past its duration the client draw returns before any GL call: no texture, blend or cull state
        self.assertEqual(rows[-1]['count'], 0)
        self.assertEqual(rows[-1]['state'], [0] * 7)

    def test_missing_frequency_is_the_client_divide_fault(self):
        document = particle_system()
        del document['Components'][0]['Frequency']
        rows = run(self.library, document, frames=4)
        # update 1 returns before the emitter (no draw yet); update 2 reaches rand() % 0 (client #DE at 0x00a80790)
        self.assertEqual([r['faulted'] for r in rows], [0, 1, 1, 1])
        self.assertEqual(rows[1]['rand_calls'], 1)
        self.assertEqual(rows[3]['rand_calls'], 1)   # a faulted effect no longer updates

    def test_validator_nan_canonicalization(self):
        x86 = struct.pack('<3I', 0xffc00000, 0x3f800000, 0x7f800000)   # x86 indefinite, 1.0, +inf
        arm = struct.pack('<3I', 0x7fc00000, 0x3f800000, 0x7f800000)
        self.assertEqual(V.canonical_nan(x86), (arm, 1))
        self.assertEqual(V.canonical_nan(arm), (arm, 1))
        finite = struct.pack('<2f', 0.5, -2.0)
        self.assertEqual(V.canonical_nan(finite), (finite, 0))

    def test_bad_json_is_rejected(self):
        error = ctypes.create_string_buffer(256)
        raw = b'{"Type": 0, "Components": ['
        self.assertIsNone(self.library.lib.mu_fx_open(raw, len(raw), 1, error, 256))


GAME_ROOT = os.environ.get('MU_GAME_ROOT')



@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and GAME_ROOT,
                     'private client captures and installed effects (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT)')
class PrivateEffectValidation(unittest.TestCase):
    def test_instruction_comparison(self):
        try:
            import unicorn  # noqa: F401
        except ImportError:
            self.skipTest('unicorn not installed')
        text = pins.TEXT.default_str()
        data = pins.DATA.default_str()
        section3 = pins.EFFECTS_INIT.default_str()
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'effects.json'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_effects.py'), '--text', text,
                                     '--data', data, '--section3', section3, '--game-root', GAME_ROOT,
                                     '--limit', '40', '--mutations', '40', '--frames', '30',
                                     '--output', str(report)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
            parsed = json.loads(report.read_text())
        self.assertEqual(parsed['mismatches'], 0)
        self.assertEqual(parsed['cases'], 80)
        self.assertGreater(parsed['vertices_compared'], 10000)


if __name__ == '__main__':
    unittest.main()
