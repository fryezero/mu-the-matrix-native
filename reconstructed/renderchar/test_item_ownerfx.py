"""Part 17 bodies (RENDER-ITEMS-002Q): owner-effect programs of the armour bodies 0x1bc3..0x1c78 and five helms."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import test_renderchar as base
import gen_item_bodies as gen
import gen_item_owner_fx as fxgen
import validate_item_ownerfx as ownerfx

F32 = lambda x: ctypes.c_float(x).value


class ItemOwnerFx(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = base.lib()
        cls.lib.mu_rc_item_owner_fx.restype = ctypes.c_int
        cls.v = ownerfx.v
    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def owner(self, t, bones, values, item_bones=None, angle=(10.0, 20.0, 30.0)):
        """Draws and effect requests of one item with an identity-rotation owner skeleton (bone k translated
        by (k, 2k, 3k)), model scale 1 and OBJECT position (100, 200, 300)."""
        effects, drawn = [], []

        @ownerfx.RANDOM
        def rand(_):
            drawn.append(values[len(drawn) % len(values)])
            return drawn[-1]

        @ownerfx.TRANSFORM
        def transform(_, bone, local, out):
            for k in range(3):
                out[k] = F32(F32(local[k] + F32(bone * (k + 1))) + F32((100.0, 200.0, 300.0)[k]))

        @ownerfx.EMIT
        def emit(_, fx):
            f = fx.contents
            effects.append((f.kind, f.bitmap, f.subtype, tuple(f.position), tuple(f.light), f.scale, tuple(f.angle)))
        host = ownerfx.Host(bones, -1, transform, rand, emit, None, bones if item_bones is None else item_bones,
                            (ctypes.c_float * 3)(*angle))
        context = self.v.CContext(0, -1, self.v.RANDOM_FN(lambda _: rand(None)), None)
        it, model = self.item(type=t), self.v.CModel()
        out, count = (self.v.CDraw * 32)(), ctypes.c_int32()
        status = self.lib.mu_rc_item_draws_owner(ctypes.byref(it), ctypes.byref(model), out, 32, ctypes.byref(count),
                                                 ctypes.byref(context), ctypes.byref(host))
        return status, list(out[:count.value]), effects, len(drawn)

    def test_admissions_and_existing_domain(self):
        self.assertEqual(len(fxgen.OWNER_FX_TYPES), 43)
        earlier = set(gen.ALL_TYPES) - set(fxgen.OWNER_FX_TYPES)
        self.assertFalse(set(fxgen.OWNER_FX_TYPES) & earlier)
        for t in fxgen.OWNER_FX_TYPES:
            self.assertEqual(self.draws(self.item(type=t))[0], 0, hex(t))
            self.assertGreater(self.lib.mu_rc_item_owner_fx(t), 0, hex(t))
            for args in ({'a10': 0}, {'a11': 0}, {'select': 1}, {'object_shadow': 1}):
                self.assertEqual(self.draws(self.item(type=t, **args))[0], 2, (hex(t), args))
        self.assertEqual(self.lib.mu_rc_item_owner_fx(0x1bc3), 37)   # bones 26, 27, 36, 18, 35
        self.assertEqual(self.lib.mu_rc_item_owner_fx(0x19f4), 21)   # bone 20
        self.assertEqual(self.lib.mu_rc_item_owner_fx(0x0f1e), 0)    # particle before the body helper: refused
        self.assertEqual(self.lib.mu_rc_item_owner_fx(0x1c26), 0)    # rank-5 owner block, not a program

    def test_helm_sprite_at_owner_bone(self):
        """0x19f4: one CreateSprite 0x810a at owner bone 20, scale 0.8, light (0.2, 0.95, 0.8), no rand."""
        status, draws, effects, used = self.owner(0x19f4, 21, [5])
        self.assertEqual((status, used), (0, 0))
        self.assertEqual(draws, self.draws(self.item(type=0x19f4))[1])
        self.assertEqual(effects, [(2, 0x810a, 0, (120.0, 240.0, 360.0), (F32(0.2), F32(0.95), F32(0.8)), F32(0.8),
                                    (0.0, 0.0, 0.0))])
        for bones, item_bones in ((20, 21), (21, 20), (0, 21)):
            status, _, effects, used = self.owner(0x19f4, bones, [5], item_bones)
            self.assertEqual((status, effects, used), (0, [], 0), (bones, item_bones))

    def test_armour_gate_and_object_angle(self):
        """0x1bc3: nine sprites, then rand() % 2 == 0 adds CreateParticle 0x810a subtype 7 with the OBJECT angle
        and a 0x011ff622 scale; an odd rand skips both the range draw and the particle."""
        status, _, even, used = self.owner(0x1bc3, 40, [0, 7])
        self.assertEqual((status, used), (0, 2))
        self.assertEqual([e[0] for e in even], [2] * 9 + [1])
        self.assertEqual(even[-1][1:3], (0x810a, 7))
        self.assertEqual(even[-1][6], (10.0, 20.0, 30.0))
        status, _, odd, used = self.owner(0x1bc3, 40, [1])
        self.assertEqual((status, used), (0, 1))
        self.assertEqual(odd, even[:9])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'ownerfx.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_ownerfx.py'),
                            '--mutations', '--output', str(path)], check=True, capture_output=True)
            report = json.loads(path.read_text())
            types = len(ownerfx.TYPES)
            self.assertEqual(report['families']['bodies']['cases'], 292*types)
            self.assertEqual(report['families']['owner']['cases'], 48*types)
            self.assertEqual(report['families']['refusal']['cases'], 8*types)
            self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
            self.assertEqual(len(report['mutants']), len(ownerfx.MUTANTS))
            self.assertTrue(all(report['mutants'].values()))


if __name__ == '__main__':
    unittest.main()
