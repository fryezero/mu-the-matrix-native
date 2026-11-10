"""Part 18 bodies (RENDER-ITEMS-002R): pre-draw effect programs (RenderObjDraw's own type case, item bones).
Part 19 (RENDER-ITEMS-002S): integer registers, runtime branches, CreateJoint and the OBJECT position.
Part 21 (RENDER-ITEMS-002T): the frame counter, 0x012b678d on item bones, post programs."""
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
        cls.lib.mu_rc_item_post_fx.restype = ctypes.c_int
        cls.v = ownerfx.v
    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def run_item(self, t, names, count, values=(5,), visible=1, time=0.0, host=True, position=(0.0, 0.0, 0.0),
                 frame=None):
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

        self.joints = []

        @ownerfx.EMIT
        def emit(_, fx):
            f = fx.contents
            effects.append((f.kind, f.bitmap, tuple(f.position), tuple(f.light), f.scale, f.rotation, f.blend))
            if f.kind == 3:
                self.joints.append((f.bitmap, f.subtype, f.owner, tuple(f.target), tuple(f.angle), f.scale))

        @ownerfx.EMIT
        def refuse(_, fx):
            effects.append(('refused', fx.contents.kind, fx.contents.bitmap))

        @ownerfx.OBJECT_TRANSFORM
        def object_transform(_, bone, out):
            for k in range(3):
                out[k] = F32(F32(bone * (k + 1)) + F32(position[k]))
        hosted = ownerfx.Host(0, -1, ownerfx.TRANSFORM(), rand, emit, None, count, (ctypes.c_float * 3)(),
                              named, item_transform if host else predraw.ITEM_TRANSFORM(), refuse, visible,
                              (ctypes.c_float * 3)(*position), object_transform, frame or 0, frame is not None)
        context = self.v.CContext(0, -1, self.v.RANDOM_FN(lambda _: rand(None)), None)
        it, model = self.item(type=t, time=time), self.v.CModel()
        out, n = (self.v.CDraw * 32)(), ctypes.c_int32()
        status = self.lib.mu_rc_item_draws_owner(ctypes.byref(it), ctypes.byref(model), out, 32, ctypes.byref(n),
                                                 ctypes.byref(context), ctypes.byref(hosted))
        return status, list(out[:n.value]), effects, len(drawn)

    def test_predraw_callbacks_reject_invalid_bones(self):
        class InvalidNative:
            def mu_rc_item_draws_owner(inner, *args):
                host = args[-1]._obj
                local = (ctypes.c_float * 3)()
                out = (ctypes.c_float * 3)(1, 2, 3)
                host.item_transform(None, 1, local, 1, out)
                self.assertEqual(tuple(out), (0, 0, 0))
                out[:] = (1, 2, 3)
                host.owner_item_transform(None, -1, local, 1, out)
                self.assertEqual(tuple(out), (0, 0, 0))
                out[:] = (1, 2, 3)
                host.object_transform(None, 1, out)
                self.assertEqual(tuple(out), (0, 0, 0))
                return 0
        o = dict(stream=[0], records=True, names=['zero'], count=1, matrices=[0.0]*12,
                 owner_matrices=[0.0]*12, origin=[0.0]*3, scale=1.0, angle=[0.0]*3,
                 position=[0.0]*3, attached=True, frame=0)
        case = self.v.classify_case(0x0f1f, self.v.CLASSIFY[0])
        status, stream, effects, used = predraw.run_c(InvalidNative(), None, case, o, 1)
        self.assertEqual((status, stream, used), (0, [], 0))
        self.assertEqual(effects, [('invalid-transform', 'item', 1),
                                   ('invalid-transform', 'owner-item', -1),
                                   ('invalid-transform', 'object', 1)])

    def test_admissions_and_existing_domain(self):
        self.assertEqual(len(fxgen.PRE_FX_TYPES), 65)   # RENDER-ITEMS-002X: fourteen further programs
        for t in fxgen.POST_FX_TYPES:
            self.assertEqual(self.draws(self.item(type=t))[0], 0, hex(t))
            self.assertEqual((self.lib.mu_rc_item_post_fx(t), self.lib.mu_rc_item_pre_fx(t)), (1, 0), hex(t))
        for t in (0x0f1f, 0x0b27, 0x1bc3, -1):
            self.assertEqual(self.lib.mu_rc_item_post_fx(t), 0, hex(t))
        earlier = set(gen.ALL_TYPES) - set(fxgen.PRE_FX_TYPES)
        self.assertFalse(set(fxgen.PRE_FX_TYPES) & earlier)
        for t in fxgen.PRE_FX_TYPES:
            self.assertEqual(self.draws(self.item(type=t))[0], 0, hex(t))
            self.assertEqual(self.lib.mu_rc_item_pre_fx(t), 1, hex(t))
            self.assertEqual(self.lib.mu_rc_item_owner_fx(t), 0, hex(t))
            for args in ({'a10': 0}, {'select': 1}, {'object_shadow': 1}):
                self.assertEqual(self.draws(self.item(type=t, **args))[0], 2, (hex(t), args))
        for t in (0x0ae6, 0x1bc3, 0x0b51, 0x23f1, -1):
            self.assertEqual(self.lib.mu_rc_item_pre_fx(t), 0, hex(t))

    def test_frame_counter_body_chains(self):
        """RENDER-ITEMS-002U: bodies whose mesh u/v follow the rendered-frame counter (mu_rc_item.frame). Sword 0xb66:
        v = ((counter + 1) % 60) as unsigned * 1/60 on its last mesh; 0x1109: a 4 x 4 atlas, (counter + 1) % 16;
        mace 0x0f2a: f = (counter % 32) / 2, u = (f % 4) * 0.25, v = (f / 4) * 0.25 (unsigned divisions)."""
        def uv(t, frame):
            status, draws = self.draws(self.item(type=t, frame=frame))
            self.assertEqual(status, 0, (hex(t), frame))
            return [(d.u, d.v) for d in draws]
        self.assertIn(0xb66, gen.FRAME_TYPES)
        for frame in (0, 1, 58, 59, 0x7fffffff, 0x80000000, 0xffffffff):
            n = ((frame + 1) & 0xffffffff) % 60
            self.assertEqual(uv(0xb66, frame)[-1], (0.0, F32(float(n) * F32(1 / 60))), frame)
            self.assertEqual(uv(0xb66, frame), uv(0xb66, frame + 60) if frame + 60 < 1 << 32 else uv(0xb66, frame))
        for frame in (0, 1, 2, 3, 4, 14, 15, 59):
            n = (frame + 1) % 16
            self.assertEqual(uv(0x1109, frame)[5], (F32(n % 4 * 0.25), F32(n // 4 * 0.25)), frame)
        for frame in (0, 1, 2, 9, 31, 32, 63, 0xffffffff):
            f = frame % 32 // 2
            self.assertEqual(uv(0x0f2a, frame)[-1], (F32(f % 4 * 0.25), F32(f // 4 * 0.25)), frame)
        # an ordinary body does not read the counter
        self.assertEqual(uv(0x0b27, 0), uv(0x0b27, 12345))

    def test_counter_range_colour_rounding(self):
        """0x0f24's mesh 1 colour is (component * range(0.25, 1, 100)) * 0.4.
        The two multiplications round separately. A host-free draw has rand result zero."""
        status, draws = self.draws(self.item(type=0x0f24, frame=99))
        self.assertEqual(status, 0)
        mesh = next(d for d in draws if d.texture == 0x8467)
        self.assertEqual(list(mesh.body_light), [F32(F32(F32(k) * F32(0.25)) * F32(0.4))
                                                for k in (0.2, 0.4, 0.9)])
        self.assertEqual(fxgen.Program().bound('umod', ('i', 0), ('c', 120)), (0, 119))
        self.assertIn(0x1588, gen.EXIT_TYPES)
        self.assertEqual(self.draws(self.item(type=0x1588, frame=0xffffffff, ext=1))[0], 0)

    def test_staff_sine_light_at_named_bone(self):
        """0x1311: s = sin(time * 0.001) * 0.5 + 0.5, l = s * 0.9 + 0.1; one bone sprite 0x7f7a at bone "a02",
        scale 0.3, light (0.35, 0.75, 1.5) * l; no rand. The draws equal the host-free stream."""
        names = ['x', 'y', 'z', 'a02', 'a02']
        status, draws, effects, used = self.run_item(0x1311, names, 8)
        self.assertEqual((status, used), (0, 0))
        self.assertEqual([base.draw_bytes(d) for d in draws], [base.draw_bytes(d) for d in self.draws(self.item(type=0x1311))[1]])
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
        self.assertEqual([base.draw_bytes(d) for d in draws], [base.draw_bytes(d) for d in plain])

    def test_post_program_on_item_bones(self):
        """0x2713 (RENDER-ITEMS-002T): after its RenderPartObjectBody draws, three CreateSprite 0x7ef7 requests at
        TransformPosition of item bones 8, 10 and 11 (translated); on ten bones the last two are refused."""
        status, draws, effects, used = self.run_item(0x2713, [], 12)
        self.assertEqual((status, used), (0, 0))
        self.assertEqual([e[:3] for e in effects],
                         [(2, 0x7ef7, (100.0 + b, 200.0 + 2 * b, 300.0 + 3 * b)) for b in (8, 10, 11)])
        status, _, effects, _ = self.run_item(0x2713, [], 10)
        self.assertEqual([e[0] for e in effects], [2, 'refused', 'refused'])

    def test_frame_counter_gate(self):
        """0x0f20 (RENDER-ITEMS-002T): particles behind [0x0bdc5ebc] % 3 and % 5 tests (unsigned). Without a
        known counter every request after the first test is refused; with counter 15 (both tests pass) none of
        the particles placed by 0x012b678d at named bones present in the skeleton is."""
        names = ['center001', 'center002', 'center003', 'red001', 'red002', 'red003']
        status, _, unknown, _ = self.run_item(0x0f20, names, 8)
        status2, _, known, _ = self.run_item(0x0f20, names, 8, frame=15)
        self.assertEqual((status, status2), (0, 0))
        particles = lambda effects: [e for e in effects if e[0] == 1]
        self.assertTrue(particles(known))
        self.assertFalse(particles(unknown))
        self.assertTrue(any(e[:2] == ('refused', 1) for e in unknown))
        self.assertEqual(len(known), len(unknown))

    def test_random_bone_count(self):
        """0x23ef: behind rand() % 15 == 0, one particle 0x8180 at bone rand() % bone count (idiv on the model's
        +0x22), never outside the skeleton."""
        a = self.run_item(0x23ef, [], 64, values=(0, 13))
        b = self.run_item(0x23ef, [], 64, values=(0, 14))
        c = self.run_item(0x23ef, [], 64, values=(0, 13 + 64))
        self.assertEqual((a[0], a[3]), (0, 2))
        self.assertEqual(self.run_item(0x23ef, [], 64, values=(1,))[3], 1)   # the gate skips the particle
        self.assertFalse([e for e in a[2] if e[0] == 'refused'])
        self.assertEqual(a[2], c[2])
        moved = [(x, y) for x, y in zip(a[2], b[2]) if x != y]
        self.assertEqual(len(moved), 1)
        self.assertEqual(tuple(F32(q - p) for p, q in zip(moved[0][0][2], moved[0][1][2])), (1.0, 2.0, 3.0))

    def test_joint_loop(self):
        """0x22ec: CreateJoint 0x7f7c/0xe then 0x7fd3/4 in each of ten loop steps, the OBJECT as target object;
        a joint's target position is the other joint's start (the two TransformPosition results swap)."""
        status, _, effects, used = self.run_item(0x22ec, [], 64)
        self.assertEqual((status, used), (0, 0))
        self.assertEqual([j[:3] for j in self.joints], [(0x7f7c, 14, 1), (0x7fd3, 4, 1)] * 10)
        starts = [e[2] for e in effects if e[0] == 3]
        for k in range(0, 20, 2):
            self.assertEqual(self.joints[k][3], starts[k + 1])
            self.assertEqual(self.joints[k + 1][3], starts[k])
        self.run_item(0x22ec, [], 20)
        self.assertLess(len(self.joints), 20)   # bones 20..30 are outside a 20-bone skeleton: refused

    def test_integer_clock(self):
        """0x0b4f: the bone sprites' rotation is (float)((int)time % 4000) / 4000 * 360 (cvttss2si, idiv)."""
        turns = {}
        for time in (0.0, 1.0, 1000.0, 1000.75, 4000.0, 4001.0):
            status, _, effects, _ = self.run_item(0x0b4f, ['a1', 'b1'], 8, time=time)
            self.assertEqual(status, 0)
            turns[time] = {e[5] for e in effects}
        self.assertEqual(turns[0.0], {0.0, 45.0})           # two sprites add 45
        self.assertEqual(turns[1000.0], {90.0, 135.0})
        self.assertEqual(turns[1000.75], turns[1000.0])     # truncated
        self.assertEqual(turns[4001.0], turns[1.0])
        self.assertIn(F32(F32(F32(1.0) / F32(4000.0)) * F32(360.0)), turns[1.0])

    def test_rotated_sprite_branch(self):
        """0x230c: a CreateSprite with rotation 0.5, then rand() % 15 >= 8 adds two particles 0x7f66/5
        (cmp edx, 8; jl skips them)."""
        taken = self.run_item(0x230c, [], 64, values=(8,))
        skipped = self.run_item(0x230c, [], 64, values=(7,))
        for r in (taken, skipped):
            self.assertEqual(len([e for e in r[2] if e[0] == 2 and e[5] == 0.5]), 1)
        self.assertEqual([e[1] for e in taken[2] if e[0] == 1], [0x7f66, 0x7f66])
        self.assertEqual([e for e in skipped[2] if e[0] == 1], [])

    def test_object_position(self):
        """0x26f8: its sprites sit at the OBJECT position (+0x158) plus item-bone offsets."""
        a = self.run_item(0x26f8, [], 8)[2]
        b = self.run_item(0x26f8, [], 8, position=(10.0, 20.0, 30.0))[2]
        self.assertTrue(a and len(a) == len(b))
        self.assertNotEqual([e[2] for e in a], [e[2] for e in b])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'predraw.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_predraw.py'),
                            '--mutations', '--output', str(path)], check=True, capture_output=True)
            report = json.loads(path.read_text())
            types = len(predraw.TYPES)
            self.assertEqual(report['families']['bodies']['cases'], 292*(types + 1))
            self.assertEqual(report['families']['predraw']['cases'], 64*types)
            self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
            self.assertEqual(len(report['mutants']), len(predraw.MUTANTS))
            self.assertTrue(all(report['mutants'].values()))


if __name__ == '__main__':
    unittest.main()
