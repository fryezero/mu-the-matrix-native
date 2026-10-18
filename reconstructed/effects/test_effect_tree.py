"""Portable checks of the effect tree and EffectManager layer (NATIVE-FX-002).

Synthetic effect descriptions only (no client data). The instruction comparison
against the client's own code is scripts/validate_effect_tree.py; its private
run is gated by MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT.
"""
import ctypes
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
LIBRARY = HERE / ('libeffects.dylib' if sys.platform == 'darwin' else 'libeffects.so')
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('validate_effect_tree', ROOT / 'scripts/validate_effect_tree.py')
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)

CAMERA = [3.0, -12.0, 4.0, -0.24, 0.94, -0.24, 0.0, 0.0, 1.0]


def emitter(**overrides):
    d = {'Type': 0, 'Frequency': 1, 'Delay': 0.0, 'MinEmissionCount': 1, 'MaxEmissionCount': 2,
         'Components': [{'Type': 0, 'Shape': 3}, {'Type': 2, 'Min': 1.0, 'Max': 1.0, 'Curve': None},
                        {'Type': 4, 'Min': 0.3, 'Max': 0.3, 'Curve': None},
                        {'Type': 5, 'Min': 0.0, 'Max': 0.0, 'Curve': None}]}
    d.update(overrides)
    return d


def particle_system(**overrides):
    d = {'Type': 0, 'Name': 'ps', 'Texture': '', 'Scale': 1.0, 'Duration': 2.0, 'Looping': True,
         'SpaceIsLocal': False, 'MaxParticle': 8, 'Blending': 1, 'Billboarding': 0, 'LengthScale': 0.0,
         'SpeedScale': 0.0, 'Components': [emitter()]}
    d.update(overrides)
    return d


def billboard(**overrides):
    d = {'Type': 1, 'Name': 'bb', 'Texture': '', 'Scale': 1.0, 'Duration': 1.0, 'Looping': True, 'Width': 2.0,
         'Height': 1.0, 'RotationAngle': 0.0, 'Blending': 1, 'Billboarding': 0, 'Brightness': 0.5,
         'Color': [1, 1, 1, 1], 'Components': []}
    d.update(overrides)
    return d


def floats(values):
    return (ctypes.c_float * len(values))(*values)


class Scene:
    def __init__(self, library, documents, managed=False, seed=1):
        self.native = T.NativeScene(library, seed, managed)
        self.lib = self.native.lib
        for d in documents:
            self.native.add(json.dumps(d))
        self.owner(visible=1)

    def owner(self, flag5=0, flag6=0, action=0, visible=1, frame=0.0, tint=(1.0, 1.0, 1.0)):
        self.lib.mu_fxt_set_owner(self.native.h, flag5, flag6, action, visible, frame, floats(tint))

    def count(self):
        return self.lib.mu_fxt_node_count(self.native.h)

    def state(self, k):
        raw, flags = self.native.state(k)
        return struct.unpack('<28f', raw), flags

    def frame(self, dt=0.1, external=None, roots=1):
        ok = True
        for r in range(roots):
            ok = ok and bool(self.lib.mu_fxt_update(self.native.h, r, dt, floats(external) if external else None))
        draws = [self.native.draw(k, CAMERA, 0) for k in range(self.count())]
        return ok, draws

    def close(self):
        self.native.close()


class EffectTreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        cls.library = T.NativeLibrary(LIBRARY)

    def scene(self, documents, **kwargs):
        s = Scene(self.library, documents, **kwargs)
        self.addCleanup(s.close)
        return s

    def test_children_are_loaded_and_unknown_types_skipped(self):
        root = billboard(Children=[particle_system(), {'Type': 5, 'Name': 'unknown'},
                                   billboard(Children=[billboard()])])
        s = self.scene([root])
        self.assertEqual(s.count(), 4)
        self.assertEqual([s.lib.mu_fxt_node_type(s.native.h, k) for k in range(4)], [1, 0, 1, 1])

    def test_child_world_transform_follows_the_parent(self):
        root = billboard(Position=[1.0, 2.0, 3.0], Rotation=[0.0, 0.0, math.pi / 2], Scale=2.0,
                         Children=[billboard(Position=[1.0, 0.0, 0.0], Scale=3.0)])
        s = self.scene([root])
        s.frame()
        child, _ = s.state(1)
        world = child[16:19]
        self.assertAlmostEqual(world[0], 1.0, places=5)   # R(z = 90 deg) * 2 * (1, 0, 0) = (0, 2, 0), plus (1, 2, 3)
        self.assertAlmostEqual(world[1], 4.0, places=5)
        self.assertAlmostEqual(world[2], 3.0, places=5)
        self.assertEqual(child[19], 6.0)                 # world scale: parent's times the child's

    def test_external_matrix_replaces_the_identity_and_keeps_the_scale(self):
        root = billboard(Children=[billboard(Position=[0.0, 0.0, 1.0])])
        s = self.scene([root])
        external = [5.0, 0, 0, 0, 0, 5.0, 0, 0, 0, 0, 5.0, 0, 100.0, 200.0, 0.0, 1.0]
        s.frame(external=external)
        top, _ = s.state(0)
        child, _ = s.state(1)
        self.assertEqual(top[16:19], (100.0, 200.0, 0.0))
        self.assertEqual(child[16:19], (100.0, 200.0, 5.0))
        self.assertEqual(top[19], 1.0)                   # the external path does not multiply the world scale
        self.assertEqual(child[19], 1.0)
        s.frame(external=[1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0])
        self.assertEqual(s.state(0)[0][16:19], (0.0, 0.0, 0.0))   # identity external: no-parent path

    def test_parentduration_billboard_takes_the_parent_duration(self):
        root = particle_system(Duration=3.0, Children=[billboard(Duration=0.5, parentduration=True, Looping=False)])
        s = self.scene([root])
        for _ in range(6):
            s.frame()
        child, flags = s.state(1)
        self.assertGreater(child[21], 2.8)   # expired once, reloaded from the parent's duration (3.0)
        self.assertEqual(flags[2], 1)        # and the parent's looping

    def test_parentduration_particles_take_the_parent_time_left(self):
        root = particle_system(Duration=3.0, Children=[particle_system(Duration=0.5, parentduration=True)])
        s = self.scene([root])
        for _ in range(7):
            s.frame()
        top, _ = s.state(0)
        child, _ = s.state(1)
        self.assertEqual(child[21], top[21])   # reloaded from the parent's remaining time, then the same steps

    def test_clones_never_reach_the_missing_frequency_fault(self):
        document = particle_system(Components=[emitter(Frequency=None)])
        del document['Components'][0]['Frequency']
        loaded = self.scene([document])
        self.assertFalse(all(loaded.frame()[0] for _ in range(3)))   # a loaded tree divides by zero
        clone = self.scene([document])
        self.assertTrue(clone.lib.mu_fxt_clone(clone.native.h, 0, floats([1, 2, 3]), floats([0, 0, 0]), 2.0, 0,
                                               None, 0, 0.0))
        for _ in range(5):
            ok, draws = clone.frame()
            self.assertTrue(ok)
        self.assertGreater(draws[0][2], 0)
        top, _ = clone.state(0)
        self.assertEqual(top[16:19], (1.0, 2.0, 3.0))
        self.assertEqual(top[19], 2.0)

    def test_owner_action_gate_and_tint(self):
        s = self.scene([billboard()])
        actions = (ctypes.c_int32 * 1)(2)
        s.lib.mu_fxt_set_gate(s.native.h, 0, 1, actions, 1, 1.0)
        s.owner(action=1)
        self.assertEqual(s.frame()[1][0][2], 0)          # action not listed: playing cleared, nothing drawn
        s.owner(action=2, frame=0.5)
        self.assertEqual(s.frame()[1][0][2], 0)          # listed, before the start frame
        s.owner(action=2, frame=1.5, flag5=1, flag6=1, tint=(0.25, 0.5, 1.0))
        vertices, state, n = s.frame()[1][0]
        self.assertEqual(n, 4)
        color = struct.unpack_from('<4f', vertices, 20)
        self.assertEqual(color, (0.125, 0.25, 0.5, 1.0))   # owner tint times brightness 0.5, alpha kept
        s.owner(action=2, frame=1.5, visible=0)
        self.assertEqual(s.frame()[1][0][2], 0)          # invisible owner: no draw

    def test_frustum_octree_and_render_order(self):
        near = billboard(Scale=20.0)
        s = self.scene([near, near, near], managed=True)
        for r, x in enumerate((12000.0, 12000.0, 90000.0)):
            m = [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, x, 13000.0 + 400.0 * r, 0.0, 1.0]
            self.assertTrue(s.lib.mu_fxt_update(s.native.h, r, 0.1, floats(m)))
        record = (ctypes.c_float * 36)()
        s.lib.mu_fxt_set_frustum(s.native.h, floats([12000.0, 11000.0, 600.0]), floats([0.0, 0.98058, -0.19612]),
                                 floats([0.0, 0.19612, 0.98058]), 0.8, 4 / 3, 10.0, 3000.0, record)
        for p in range(6):
            n = record[12 + 4 * p:15 + 4 * p]
            self.assertAlmostEqual(sum(v * v for v in n), 1.0, places=5)   # every plane normalised
        depths = []
        for k in range(3):
            box = (ctypes.c_float * 6)()
            depths.append(s.lib.mu_fxt_cell(s.native.h, k, box))
        self.assertEqual(depths[2], -1)                  # outside the EffectManager's world box: not in the tree
        self.assertTrue(depths[0] > 0 and depths[1] > 0)
        indices = (ctypes.c_uint32 * 8)()
        n = s.lib.mu_fxt_query(s.native.h, indices, 8)
        self.assertEqual(sorted(indices[:n]), [0, 1])
        s.lib.mu_fxt_set_frustum(s.native.h, floats([12000.0, 11000.0, 600.0]), floats([0.0, -0.98058, -0.19612]),
                                 floats([0.0, -0.19612, 0.98058]), 0.8, 4 / 3, 10.0, 3000.0, None)
        self.assertEqual(s.lib.mu_fxt_query(s.native.h, indices, 8), 0)   # looking away

    def test_render_pass_gl_calls(self):
        calls = (ctypes.c_uint32 * 72)()
        lib = self.library.lib
        self.assertEqual(lib.mu_fxt_render_calls((ctypes.c_uint32 * 6)(1, 1, 1, 1, 0x302, 0x303), 0, calls), 0)
        n = lib.mu_fxt_render_calls((ctypes.c_uint32 * 6)(1, 0, 1, 1, 0x302, 0x303), 3, calls)
        sequence = [tuple(calls[3 * i:3 * i + 3]) for i in range(n)]
        self.assertEqual(sequence, [(1, 0xbc0, 0), (1, 0xde1, 0), (1, 0xbe2, 0), (2, 0xbe1, 0), (2, 0xbe0, 0),
                                    (1, 0xb72, 0), (3, 0, 0), (5, 0xbc0, 0), (8, 3, 0), (6, 0xde1, 0),
                                    (5, 0xde1, 0), (7, 0x302, 0x303), (4, 0xbe2, 0), (3, 1, 0), (4, 0xbc0, 0)])


GAME_ROOT = os.environ.get('MU_GAME_ROOT')
EVIDENCE = Path(os.environ.get('MU_EVIDENCE', str(ROOT / 'evidence')))


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and GAME_ROOT,
                     'private client captures and installed effects (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT)')
class PrivateEffectTreeValidation(unittest.TestCase):
    def test_instruction_comparison(self):
        try:
            import unicorn  # noqa: F401
        except ImportError:
            self.skipTest('unicorn not installed')
        text = os.environ.get('MU_CLIENT_TEXT', str(EVIDENCE / 'x86-text-capture-09/client-text.bin'))
        data = os.environ.get('MU_IMAGE_DATA', str(EVIDENCE / 'image-data-run10/data-capture-10/client-image-data.bin'))
        section3 = os.environ.get('MU_SECTION3', str(EVIDENCE / 'x86-linux-capture-04/main-01ced000.bin'))
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'tree.json'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_effect_tree.py'), '--text', text,
                                     '--data', data, '--section3', section3, '--game-root', GAME_ROOT,
                                     '--limit', '60', '--mutations', '20', '--clones', '20', '--scenes', '10',
                                     '--frames', '20', '--output', str(report)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
            parsed = json.loads(report.read_text())
        self.assertEqual(parsed['mismatches'], 0)
        self.assertEqual(parsed['cases'], 110)
        self.assertGreater(parsed['render_passes_compared'], 0)


if __name__ == '__main__':
    unittest.main()
