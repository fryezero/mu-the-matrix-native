"""Part 18 bodies (RENDER-ITEMS-002R): pre-draw effect programs (RenderObjDraw's own type case, item bones)."""
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
import validate_item_predraw as predraw

F32 = lambda x: ctypes.c_float(x).value


class ItemPreDraw(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = base.lib()
        cls.lib.mu_rc_item_pre_fx.restype = ctypes.c_int
        cls.lib.mu_rc_item_owner_fx.restype = ctypes.c_int
        cls.v = ownerfx.v
    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def run_item(self, t, names, count, values=(5,), visible=1, time=0.0, host=True):
        """Draws, requests and refusals of one item with identity item bones (bone k translated by
        (k, 2k, 3k)), model scale 1 and origin (100, 200, 300)."""
        effects, drawn = [], []

        @ownerfx.RANDOM
        def rand(_):
            drawn.append(values[len(drawn) % len(values)])
            return drawn[-1]

        @predraw.NAMED
        def named(_, name):
            return names.index(name.decode()) if name.decode() in names else -1

        @predraw.ITEM_TRANSFORM
        def item_transform(_, bone, local, translate, out):
            for k in range(3):
                moved = F32(local[k] + F32(bone * (k + 1)))
                out[k] = F32(moved + F32((100.0, 200.0, 300.0)[k])) if translate else moved

        @ownerfx.EMIT
        def emit(_, fx):
            f = fx.contents
            effects.append((f.kind, f.bitmap, tuple(f.position), tuple(f.light), f.scale, f.rotation, f.blend))

        @ownerfx.EMIT
        def refuse(_, fx):
            effects.append(('refused', fx.contents.kind, fx.contents.bitmap))
        hosted = ownerfx.Host(0, -1, ownerfx.TRANSFORM(), rand, emit, None, count, (ctypes.c_float * 3)(),
                              named, item_transform if host else predraw.ITEM_TRANSFORM(), refuse, visible)
        context = self.v.CContext(0, -1, self.v.RANDOM_FN(lambda _: rand(None)), None)
        it, model = self.item(type=t, time=time), self.v.CModel()
        out, n = (self.v.CDraw * 32)(), ctypes.c_int32()
        status = self.lib.mu_rc_item_draws_owner(ctypes.byref(it), ctypes.byref(model), out, 32, ctypes.byref(n),
                                                 ctypes.byref(context), ctypes.byref(hosted))
        return status, list(out[:n.value]), effects, len(drawn)

    def test_admissions_and_existing_domain(self):
        self.assertEqual(len(fxgen.PRE_FX_TYPES), 26)
        earlier = set(gen.ALL_TYPES) - set(fxgen.PRE_FX_TYPES)
        self.assertFalse(set(fxgen.PRE_FX_TYPES) & earlier)
        for t in fxgen.PRE_FX_TYPES:
            self.assertEqual(self.draws(self.item(type=t))[0], 0, hex(t))
            self.assertEqual(self.lib.mu_rc_item_pre_fx(t), 1, hex(t))
            self.assertEqual(self.lib.mu_rc_item_owner_fx(t), 0, hex(t))
            for args in ({'a10': 0}, {'select': 1}, {'object_shadow': 1}):
                self.assertEqual(self.draws(self.item(type=t, **args))[0], 2, (hex(t), args))
        for t in (0x0ae6, 0x1bc3, 0x0f1e, 0x23a8, -1):
            self.assertEqual(self.lib.mu_rc_item_pre_fx(t), 0, hex(t))

    def test_staff_sine_light_at_named_bone(self):
        """0x1311: s = sin(time * 0.001) * 0.5 + 0.5, l = s * 0.9 + 0.1; one bone sprite 0x7f7a at bone "a02",
        scale 0.3, light (0.35, 0.75, 1.5) * l; no rand. The draws equal the host-free stream."""
        names = ['x', 'y', 'z', 'a02', 'a02']
        status, draws, effects, used = self.run_item(0x1311, names, 8)
        self.assertEqual((status, used), (0, 0))
        self.assertEqual([bytes(d) for d in draws], [bytes(d) for d in self.draws(self.item(type=0x1311))[1]])
        l = F32(F32(F32(F32(0.0 * F32(0.5)) + F32(0.5)) * F32(0.9)) + F32(0.1))
        light = tuple(F32(F32(k) * l) for k in (0.35, 0.75, 1.5))
        self.assertEqual(effects, [(2, 0x7f7a, (103.0, 206.0, 309.0), light, F32(0.3), 0.0, 0)])
        for names, count in ((['x'], 8), (names, 3)):
            status, _, effects, used = self.run_item(0x1311, names, count)
            self.assertEqual((status, effects, used), (0, [('refused', 2, 0x7f7a)], 0), (names, count))

    def test_visibility_flag_skips_the_case(self):
        """0xb27: behind TestFrustrum2D's flag, (float)(rand() % 20) scales the light of four bone sprites."""
        status, _, shown, used = self.run_item(0x0b27, [], 64, values=(7,))
        self.assertEqual((status, used), (0, 1))
        self.assertTrue(shown and all(e[0] == 2 for e in shown))
        status, _, hidden, used = self.run_item(0x0b27, [], 64, values=(7,), visible=0)
        self.assertEqual((status, hidden, used), (0, [], 0))

    def test_no_item_host_creates_nothing(self):
        status, draws, effects, used = self.run_item(0x1311, ['a02'], 8, host=False)
        self.assertEqual((status, effects, used), (0, [], 0))
        status, plain = self.draws(self.item(type=0x1311))
        self.assertEqual([bytes(d) for d in draws], [bytes(d) for d in plain])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'predraw.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_predraw.py'),
                            '--mutations', '--output', str(path)], check=True, capture_output=True)
            report = json.loads(path.read_text())
            types = len(predraw.TYPES)
            self.assertEqual(report['families']['bodies']['cases'], 292*types)
            self.assertEqual(report['families']['predraw']['cases'], 64*types)
            self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
            self.assertEqual(len(report['mutants']), len(predraw.MUTANTS))
            self.assertTrue(all(report['mutants'].values()))


if __name__ == '__main__':
    unittest.main()
