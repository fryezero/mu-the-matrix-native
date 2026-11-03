"""RENDER-EFFECTS-009: the named-bone service, arrows 0x615/0x617, bow 0x12f9's sparks in the session, the arrows'
0x7fd5/3 and 0x7fd6/5 joints and 0x7f5a/0xd particle, and the arrow models' texture retries."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from test_native_combat import write_combat_world
from test_native_particles import ozj_jpeg
import native_fixtures as nf

SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'


def named_layout(seed, names):
    """A synthetic model whose bones 0, 1, 2, 4, 5, 6 carry the given names (bone 3 is the fixture's dummy)."""
    layout = nf.synthetic_layout(seed, actions=1, keys=(8,))
    for bone, name in zip((0, 1, 2, 4, 5, 6), names):
        old = nf.name32(f'bone{bone}')
        assert layout.count(old) == 1
        layout = layout.replace(old, nf.name32(name))
    return layout


class NamedBones(unittest.TestCase):
    """mu_named_bones.c: worked examples of 0x012bd35a, 0x0129f18a and 0x0129f12c."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        out = Path(cls.tmp.name)/f'named_bones.{SUFFIX}'
        subprocess.run(['clang', '-std=c11', '-O2', '-fPIC', '-shared', str(ROOT/'native/core/mu_named_bones.c'),
                        '-o', str(out)], check=True, capture_output=True)
        cls.lib = ctypes.CDLL(str(out))
        cls.lib.mu_named_bone_index.argtypes = [ctypes.POINTER(ctypes.c_char_p), ctypes.c_int32, ctypes.c_int,
                                                ctypes.c_char_p, ctypes.c_int32]
        cls.lib.mu_named_bone_index.restype = ctypes.c_int32
        cls.lib.mu_named_bone_matrix.argtypes = [ctypes.POINTER(ctypes.c_char_p), ctypes.c_int32, ctypes.c_int,
                                                 ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                                                 ctypes.POINTER(ctypes.c_int32)]
        cls.lib.mu_owner_bone_valid.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int32, ctypes.c_int32]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def names(self, *names):
        return (ctypes.c_char_p * len(names))(*[n.encode() for n in names])

    def test_index_first_equal_name_or_fallback(self):
        n = self.names('center', 'red_01', 'red_011', 'red_01')
        self.assertEqual(self.lib.mu_named_bone_index(n, 4, 1, b'red_01', -1), 1)       # the first one
        self.assertEqual(self.lib.mu_named_bone_index(n, 4, 1, b'Red_01', -1), -1)      # case matters
        self.assertEqual(self.lib.mu_named_bone_index(n, 4, 1, b'red_0', 7), 7)         # no prefix match
        self.assertEqual(self.lib.mu_named_bone_index(n, 1, 1, b'red_01', -1), -1)      # past the count
        self.assertEqual(self.lib.mu_named_bone_index(n, 4, 0, b'red_01', 5), 5)        # no bone records

    def test_matrix_global_or_own_buffer(self):
        n = self.names('Group001', 'Line003')
        i = ctypes.c_int32(-9)
        self.assertEqual(self.lib.mu_named_bone_matrix(n, 2, 1, 1, 0, b'Line003', 1, ctypes.byref(i)), 1)
        self.assertEqual(i.value, 1)
        self.assertEqual(self.lib.mu_named_bone_matrix(n, 2, 1, 1, 1, b'Line003', 1, ctypes.byref(i)), 2)
        self.assertEqual(self.lib.mu_named_bone_matrix(n, 2, 1, 1, 1, b'Line003', 0, ctypes.byref(i)), 1)
        self.assertEqual(self.lib.mu_named_bone_matrix(n, 2, 1, 0, 0, b'Line003', 1, ctypes.byref(i)), 0)
        self.assertEqual(self.lib.mu_named_bone_matrix(n, 2, 1, 1, 0, b'Line004', 1, ctypes.byref(i)), 0)

    def test_owner_bone_needs_model_own_bones_and_range(self):
        self.assertEqual(self.lib.mu_owner_bone_valid(1, 1, 50, 0), 1)
        self.assertEqual(self.lib.mu_owner_bone_valid(1, 1, 50, 49), 1)
        self.assertEqual(self.lib.mu_owner_bone_valid(1, 1, 50, 50), 0)
        self.assertEqual(self.lib.mu_owner_bone_valid(1, 1, 50, -1), 0)
        self.assertEqual(self.lib.mu_owner_bone_valid(1, 0, 50, 3), 0)
        self.assertEqual(self.lib.mu_owner_bone_valid(0, 1, 50, 3), 0)


class BowSession(unittest.TestCase):
    """Triple Shot with the bows of this lane in a synthetic world."""

    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(ROOT/'native'), 'build/mu-walk'], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.tmp.name)
        cls.root = write_combat_world(cls.directory/'game')
        skill = cls.root/'Data/Skill'; skill.mkdir(exist_ok=True)
        effect = cls.root/'Data/Effect'; effect.mkdir(exist_ok=True)
        for name in ('smoke01', 'Spark01', 'Spark02', 'JointLaser01'):
            (effect/f'{name}.OZJ').write_bytes(ozj_jpeg(32, 32))
        (skill/'Carow.bmd').write_bytes(nf.synthetic_layout(410, actions=1, keys=(8,)))
        (skill/'Imperial_arrow.bmd').write_bytes(named_layout(411, ['red_01', 'red_02', 't1', 't2', 't3', 't4']))
        (skill/'devilcrossbow_arrow.bmd').write_bytes(
            nf.synthetic_layout(412, meshes=1, actions=1, keys=(8,), texture_names=['devil_arrow.jpg']))
        (effect/'devil_arrow.OZJ').write_bytes(ozj_jpeg(16, 16))   # only in Data/Effect (LoadBitmap 0x01833b47)
        cls.placement = cls.directory/'actors.txt'
        cls.placement.write_text('actor 3 122 120 0 label spider\n')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def shoot(self, bow, frames=30):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = [str(ROOT/'native/build/mu-walk'), '--game-root', str(self.root), '--headless', '--backend', 'soft',
                   '--no-audio', '--no-items', '--no-players', '--tile', '120,120', '--placement', str(self.placement),
                   '--combat', '--combat-weapon', 'bow', '--combat-bow', bow, '--class', '2',
                   '--combat-script', '2:skill:24:spider;3:stop', '--frames', str(frames), '--every', '1',
                   '--width', '160', '--height', '100', '--out-dir', tmp]
            p = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            rows = [json.loads(x) for x in p.stdout.splitlines() if x.startswith('{')]
            images = [hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(Path(tmp).glob('*.png'))]
        summary = next(r for r in rows if r.get('combat') is True)
        kinds = next(r['combat_unsupported'] for r in rows if 'combat_unsupported' in r)
        return summary, kinds, rows, images

    def test_bow_12f9_sparks_trails_and_smoke(self):
        """Bow 0x12f9: four Carow arrows, fifteen Spark02 sparks with their 0x7fd5/3 joints at the hero's bone,
        the arrows' 0x7fd6/5 trails and Carow's 0x7f5a/0xd smoke; nothing unsupported (it was 130 kinds' requests)."""
        summary, kinds, rows, images = self.shoot('0x12f9')
        self.assertEqual(summary['arrows'], 4)
        self.assertEqual(summary['bow_sparks'], 15)
        self.assertEqual((summary['unsupported'], kinds), (0, []))
        self.assertGreaterEqual(summary['joints_created'], 4 + 1)   # four trails, at least one spark joint
        self.assertGreater(summary['particles_created'], 15)        # the sparks and the smoke
        frames = [r for r in rows if 'combat_frame' in r]
        self.assertTrue(any(f['joints'] >= 4 for f in frames))

    def test_imperial_arrow_named_bone_sprites(self):
        """0x617: four Imperial arrows; each step nine sprites at the named bones (red_01, red_02, t1..t5). A name
        the model lacks (t5 here, every name in the second run) still requests its sprite: 0x012bd35a answers -1 and
        0x0150e746 places it with that (unset) matrix, so the count does not depend on the names."""
        summary, kinds, _, _ = self.shoot('0x132f')
        self.assertEqual(summary['arrows'], 4)
        self.assertGreater(summary['sprites'], 0)
        self.assertEqual(summary['sprites'] % 9, 0)
        self.assertEqual(sorted([k[0], k[1], k[2]] for k in kinds), [['p', 0x8450, 4], ['p', 0x85fb, 2]])
        model = self.root/'Data/Skill/Imperial_arrow.bmd'
        saved = model.read_bytes()
        try:
            model.write_bytes(named_layout(411, ['a', 'b', 'c', 'd', 'e', 'f']))
            other, _, _, _ = self.shoot('0x132f')
        finally:
            model.write_bytes(saved)
        self.assertEqual(other['sprites'], summary['sprites'])

    def test_devil_crossbow_arrow_texture_from_the_name_map(self):
        """0x5b0: devil_arrow.jpg is not in Data/Skill; the startup LoadBitmap's name-map entry gives it (the arrow
        drew white without it)."""
        summary, _, _, images = self.shoot('0x1300')
        self.assertEqual(summary['arrow_textures_retried'], 1)
        tex = self.root/'Data/Effect/devil_arrow.OZJ'
        tex.rename(tex.with_suffix('.off'))
        try:
            again, _, _, white = self.shoot('0x1300')
        finally:
            tex.with_suffix('.off').rename(tex)
        self.assertEqual(again['arrow_textures_retried'], 0)
        self.assertNotEqual(images, white)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
    def test_original_instructions_and_compiled_mutants(self):
        """validate_render_effects9: CreateEffect/MoveEffect 0x615/0x617, the named-bone service, joints 0x7fd5/3
        and 0x7fd6/5, particle 0x7f5a/0xd."""
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects9.py'), '--cases', '2',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            r = json.loads(report.read_text())
            self.assertTrue(r['all_equal'])
            self.assertTrue(r['all_mutants_caught'])
            self.assertEqual(len(r['mutants']), 25)
            self.assertEqual(r['instruction_cases'], 304)


if __name__ == '__main__':
    unittest.main()
