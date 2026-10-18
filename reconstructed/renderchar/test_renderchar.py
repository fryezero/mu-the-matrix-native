"""Worked examples for the reconstructed world render decisions (NATIVE-RENDERCHAR-001).

Portable: builds librenderchar and checks the rules against independent
binary32 arithmetic in Python (no client data). The comparison with the
client's instructions is scripts/validate_renderchar.py; the private test here
runs a small configuration of it when MU_RECOVERY_INTEGRATION=1.
"""
import ctypes
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
sys.path.insert(0, str(ROOT/'scripts'))
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def fsin(x):
    return f32(math.sin(f32(x)))


def lib():
    subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
    return ctypes.CDLL(str(HERE/f'librenderchar.{SUFFIX}'))


class RenderCharLibrary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import validate_renderchar as v
        cls.v = v
        cls.lib = lib()
        cls.lib.mu_rc_item_special.restype = ctypes.c_int
        cls.lib.mu_rc_item_glow_level.restype = ctypes.c_int32

    def item(self, **kw):
        v = self.v
        it = v.CItem(type=0xae6, item_level=0, option1=0, ext_option=0, select=0, render_type=2, a10=-1, a11=-1, a12=3,
                     alpha=1.0, light=v.F3(0.8, 0.7, 0.6), object_alpha=1.0, blend_mesh=-1, time=0.0, quality=5,
                     enchant=v.F3(0.25, 0.5, 0.75))
        for k, value in kw.items():
            if k in ('light', 'enchant'):
                value = v.F3(*value)
            setattr(it, k, value)
        return it

    def draws(self, it, model=None):
        v = self.v
        model = model or v.CModel()
        out = (v.CDraw * 32)()
        count = ctypes.c_int32()
        status = self.lib.mu_rc_item_draws(ctypes.byref(it), ctypes.byref(model), out, 32, ctypes.byref(count))
        return status, list(out[:count.value])

    def test_glow_level_rules(self):
        level = lambda **kw: self.lib.mu_rc_item_glow_level(ctypes.byref(self.item(**kw)))
        self.assertEqual(level(item_level=13 << 3), 13)
        self.assertEqual(level(item_level=(13 << 3) | 7), 13)
        self.assertEqual(level(item_level=13 << 3, render_type=0x402), 0)
        self.assertEqual([level(item_level=15 << 3, quality=q) for q in range(6)], [5, 7, 9, 11, 13, 15])
        self.assertEqual(level(item_level=0, has_record=1, kind_b=0x26), 9)
        self.assertEqual(level(item_level=0, has_record=1, kind_b=0x5b), 9)

    def test_plain_and_pulse_levels(self):
        status, d = self.draws(self.item())
        self.assertEqual(status, 0)
        self.assertEqual([(x.entry, x.flags, x.hidden, x.texture) for x in d], [(1, 2, -1, -1)])
        self.assertEqual(list(d[0].body_light), [f32(0.8), f32(0.7), f32(0.6)])
        t = 1234.0
        p = f32(f32(fsin(f32(t)*f32(0.004))*f32(0.15)) + f32(0.6))
        for lv, factors in ((3, (p, f32(p*f32(0.6)), f32(p*f32(0.6)))), (5, (f32(p*f32(0.5)), f32(p*f32(0.7)), p))):
            status, d = self.draws(self.item(item_level=lv << 3, time=t))
            light = (f32(0.8), f32(0.7), f32(0.6))
            self.assertEqual(list(d[0].body_light), [f32(a*b) for a, b in zip(factors, light)])
            self.assertEqual(d[0].flag_ca, 1)

    def test_high_level_pass_sequence(self):
        flags = lambda lv, q=5: [x.flags for x in self.draws(self.item(item_level=lv << 3, quality=q))[1]]
        self.assertEqual(flags(7), [2, 0x44])
        self.assertEqual(flags(9), [2, 0x44, 0x48])
        self.assertEqual(flags(11), [2, 0x240, 0x48, 0x44])
        self.assertEqual(flags(13), [2, 0x240, 0x1040, 0x48, 0x44])
        self.assertEqual(flags(13, q=2), [2, 0x44, 0x48])          # capped at 9
        status, d = self.draws(self.item(item_level=13 << 3, alpha=0.5))
        glow = d[-1]
        self.assertEqual(list(glow.body_light), [f32(f32(0.5)*x) for x in (f32(0.25), f32(0.5), f32(0.75))])
        self.assertEqual(glow.level_field, 13)

    def test_excellent_and_ancient(self):
        t = 777.0
        status, d = self.draws(self.item(option1=1, time=t))
        p = f32(f32(fsin(f32(t)*f32(0.002))*f32(0.5)) + f32(0.5))
        self.assertEqual((d[-1].flags, d[-1].alpha), (0x42, 1.0))
        self.assertEqual(list(d[-1].body_light), [p, f32(p*f32(0.3)), f32(1.0-p)])
        status, d = self.draws(self.item(ext_option=2, time=t, has_record=1))
        a = f32(f32(fsin(f32(t)*f32(0.001))*f32(0.5)) + f32(0.4))
        self.assertEqual((d[-1].flags, d[-1].alpha), (0x840, a))
        status, d = self.draws(self.item(ext_option=2, time=t, has_record=0))
        self.assertEqual(len(d), 1)                                  # ancient needs the item record
        status, d = self.draws(self.item(option1=1, quality=0))
        self.assertEqual(len(d), 1)                                  # quality 0 suppresses the tail

    def test_refusals(self):
        self.assertEqual(self.draws(self.item(has_record=1, item_kind=4))[0], 2)
        self.assertEqual(self.draws(self.item(select=1))[0], 2)
        special = next(t for t in range(0xae6, 0x2ae6) if self.lib.mu_rc_item_special(t))
        self.assertEqual(self.draws(self.item(type=special))[0], 1)
        self.assertEqual(self.lib.mu_rc_item_special(0x100), 1)     # outside the classified ranges

    def test_plus15_attachment_passes(self):
        t = 2500.0
        status, d = self.draws(self.item(type=0xa9b, time=t, blend_light=0.3, u=0.1, v=0.2))
        k = f32(f32(0.8) - abs(f32(fsin(f32(t)*f32(0.0018))*f32(0.5))))
        g = abs(fsin(f32(t)*f32(0.0005)))
        self.assertEqual([(x.entry, x.mesh, x.flags, x.texture) for x in d],
                         [(2, 0, 0x42, -1), (2, 0, 0x42, 0x80d4), (2, 0, 0x1002, -1)])
        self.assertEqual([d[0].blend_light, d[1].blend_light, d[1].u], [f32(k-f32(0.1)), f32(k-f32(0.3)), g])
        self.assertEqual(self.draws(self.item(type=0xa9b, item_level=8))[0], 2)

    def test_back_root_composition(self):
        local = (ctypes.c_uint32 * 12)()
        mode = self.lib.mu_rc_back_local(0xae6, 0, 1, local)
        self.assertIn(mode, (1, 2))
        identity = (ctypes.c_uint32 * 12)(*[struct.unpack('<I', struct.pack('<f', x))[0]
                                           for x in (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0)])
        out = (ctypes.c_uint32 * 12)()
        self.assertEqual(self.lib.mu_rc_back_root(identity, 0xae6, 0, 1, out), 1)
        if mode == 1:
            self.assertEqual(list(out), list(local))
        # composition with a general bone follows the binary32 concat order
        bone = [0.36, -0.48, 0.8, 11.0, 0.8, 0.6, 0.0, -7.0, -0.48, 0.64, 0.6, 3.0]
        bits = (ctypes.c_uint32 * 12)(*[struct.unpack('<I', struct.pack('<f', x))[0] for x in bone])
        self.lib.mu_rc_back_root(bits, 0xae6, 0, 1, out)
        L = [struct.unpack('<f', struct.pack('<I', x))[0] for x in local]
        B = [f32(x) for x in bone]
        expect = []
        for r in range(3):
            for c in range(4):
                s = f32(f32(f32(B[4*r]*L[c]) + f32(B[4*r+1]*L[4+c])) + f32(B[4*r+2]*L[8+c]))
                expect.append(f32(s + B[4*r+3]) if c == 3 else s)
        if mode == 1:
            self.assertEqual([struct.unpack('<f', struct.pack('<I', x))[0] for x in out], expect)
        self.assertEqual(self.lib.mu_rc_back_local(0x12, 0, 1, local), 0)

    def character(self, **kw):
        v = self.v
        ch = v.CCharacter(class_byte=1, safe_zone=0, action=1, frame=0.0, alpha=1.0, translate=1, select=0)
        for k in range(0x186):
            ch.player_speed[k] = f32(0.25 + k / 1000.0)
        for s in list(ch.parts) + list(ch.weapons) + [ch.wing]:
            s.type = -1
        for k, value in kw.items():
            setattr(ch, k, value)
        return ch

    def plan(self, ch):
        v = self.v
        out = (v.CCall * 32)()
        count = ctypes.c_int32()
        status = self.lib.mu_rc_character_plan(ctypes.byref(ch), out, 32, ctypes.byref(count))
        return status, list(out[:count.value])

    def test_character_plan(self):
        ch = self.character()
        ch.parts[2].type, ch.parts[2].level = 0x1ae6, 7
        ch.weapons[0].type = 0xae6
        status, calls = self.plan(ch)
        self.assertEqual(status, 0)
        self.assertEqual([(c.kind, c.slot, c.type) for c in calls], [(1, -1, 0xa92), (2, 2, 0x1ae6), (3, 0, 0xae6)])
        self.assertEqual((calls[1].item_level, calls[1].render_type), (56, 2))
        hand = calls[2]
        self.assertEqual((list(hand.xyz), hand.link, hand.link_bone, hand.part_action), ([0, 0, 0], 0, 33, 0))
        self.assertEqual(hand.part_speed, f32(0.251))                 # swords: Player action 1 speed
        ch.safe_zone = 1
        status, calls = self.plan(ch)
        back = calls[-1]
        self.assertEqual((list(back.xyz), back.link, back.link_bone, back.right_hand), ([0, 0, 15], 1, 47, 1))
        ch.alpha = 0.4
        self.assertNotIn(1, [c.kind for c in self.plan(ch)[1]])        # no shadow below alpha 0.5
        ch = self.character()
        ch.parts[2].type, ch.parts[2].level = 0x1ae6, 15
        models = [c.type for c in self.plan(ch)[1] if c.kind == 3]
        self.assertEqual(models, [0xa9b, 0xa9c])                      # +15 armour attachments
        self.assertEqual(self.plan(self.character(class_byte=4))[0], 2)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'Private render-decision instruction comparison is opt-in')
    def test_private_original_render_instructions(self):
        e = ROOT/'evidence'
        text = Path(os.environ.get('MU_CLIENT_TEXT', e/'x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA', e/'image-data-run10/data-capture-10/client-image-data.bin'))
        flag = Path(os.environ.get('MU_TRIG_FLAG', e/'trig-state-15/captures/late/math-dispatch-flag.bin'))
        feature = Path(os.environ.get('MU_MATH_DATA', e/'x86-math-capture-09'))/'cpu-features.bin'
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_renderchar.py'), '--text', str(text),
                            '--data', str(data), '--flag', str(flag), '--feature', str(feature),
                            '--sections', 'back,character', '--back-checks', '100', '--characters', '60',
                            '--output', str(report)], check=True, capture_output=True)
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_renderchar.py'), '--text', str(text),
                            '--data', str(data), '--flag', str(flag), '--feature', str(feature),
                            '--sections', 'items', '--classify', 'none', '--cases', '500',
                            '--output', str(Path(directory)/'items.json')], check=True, capture_output=True)
            back = json.loads(report.read_text())
            items = json.loads((Path(directory)/'items.json').read_text())
        self.assertTrue(back['back']['ok'])
        self.assertTrue(back['character']['ok'])
        self.assertEqual(items['items']['matches'], items['items']['compared'])

    def test_refuses_unpinned_text(self):
        with tempfile.NamedTemporaryFile() as handle:
            handle.write(b'\0' * 64)
            handle.flush()
            result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_renderchar.py'), '--text', handle.name,
                                     '--data', handle.name, '--flag', handle.name, '--feature', handle.name],
                                    capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('text', result.stderr)


if __name__ == '__main__':
    unittest.main()
