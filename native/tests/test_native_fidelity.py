"""NATIVE-FIDELITY-001 checks (docs/research/client-fidelity.md).

Portable (synthetic data only):
  * RenderCharacter's light block (reconstructed/renderchar mu_rc_character_light): the hero's (1, 1, 1) and its
    state tints, scene 5, type 0x7dc, the glow classes;
  * the ambient creatures' body light (reconstructed/environment mu_env_body_light): lighting flag = +5, colour =
    frame light + object light;
  * RenderObjectScreen (reconstructed/hud mu_hud_object_screen): the Player pose for armour parts, the model
    heights, the 0x26f2 remap, kind A 0xc, the held scale, InvenItemAnimation;
  * the item-model loader's special models (mu_gi_special_model_file);
  * the set-item prefix (reconstructed/items item_sets) on synthetic tables: map order by name, set bits, kind B
    0x79, the legendary pair slots, the cash sets;
  * mu_lang's new tables (pentagram, invenanim, legendary, cashsets);
  * mu-walk labels on a synthetic world with synthetic ItemSetType/ItemSetOption: "<prefix><name> +L" and the
    "+Skill" suffix with no leading space.
Private (MU_RECOVERY_INTEGRATION=1 with the pinned captures; MU_LANG_SNAPSHOT and MU_GAME_ROOT for the
Lang.mpr families): scripts/validate_fidelity.py and the light section of scripts/validate_renderchar.py.
"""
import ctypes
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
ROOT = NATIVE.parent
sys.path.insert(0, str(HERE))
from test_native_data import checksum, xor3  # noqa: E402
from test_native_items import run, write_items_world, WALK  # noqa: E402

SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
EVIDENCE = ROOT / 'evidence' if (ROOT / 'evidence').exists() else Path.home() / 'Documents/main-exe-study/evidence'
PYTHON = sys.executable
try:
    import unicorn  # noqa: F401
    HAVE_UNICORN = True
except ImportError:
    HAVE_UNICORN = False


def library(directory, name):
    subprocess.run(['make', '-s', '-C', str(ROOT / directory)], check=True, capture_output=True)
    return ctypes.CDLL(str(ROOT / directory / name))


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


class LightIn(ctypes.Structure):
    _fields_ = [('scene_state', ctypes.c_int32), ('terrain_light', ctypes.c_float * 3),
                ('object_light', ctypes.c_float * 3), ('model_type', ctypes.c_int32), ('class_index', ctypes.c_int32),
                ('is_hero', ctypes.c_int32), ('ability', ctypes.c_uint8)]


class CharacterLight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = library('reconstructed/renderchar', f'librenderchar.{SUFFIX}')
        cls.lib.mu_rc_character_light.argtypes = [ctypes.POINTER(LightIn), ctypes.POINTER(ctypes.c_float)]

    def light(self, **kw):
        c = LightIn(scene_state=kw.get('scene', 6), model_type=kw.get('type', 0xa91), class_index=kw.get('cls', 1),
                    is_hero=kw.get('hero', 0), ability=kw.get('ability', 0))
        for k in range(3):
            c.terrain_light[k] = kw.get('terrain', (0.3, 0.5, 0.7))[k]
            c.object_light[k] = kw.get('object', 0.2)
        out = (ctypes.c_float * 3)()
        status = self.lib.mu_rc_character_light(ctypes.byref(c), out)
        return status, [round(v, 6) for v in out]

    def test_paths(self):
        self.assertEqual(self.light(), (0, [round(f32(0.3) + f32(0.2), 6), round(f32(0.5) + f32(0.2), 6),
                                            round(f32(0.7) + f32(0.2), 6)]))
        self.assertEqual(self.light(scene=5)[1], [round(f32(0.4) + f32(0.2), 6)] * 3)
        self.assertEqual(self.light(type=0x7dc)[1], [0.6] * 3)
        self.assertEqual(self.light(hero=1), (0, [1.0, 1.0, 1.0]))          # the live read: (1, 1, 1)
        self.assertEqual(self.light(hero=1, ability=1)[1], [0.9, 0.5, 0.5])
        self.assertEqual(self.light(hero=1, ability=2)[1], [0.5, 0.9, 0.5])
        self.assertEqual(self.light(hero=1, ability=3)[1], [round(f32(0.9 * 0.5), 6), round(f32(0.5 * 0.9), 6), 0.25])
        self.assertEqual(self.light(hero=1, scene=5)[1], [0.7, 0.7, 0.7])
        self.assertEqual(self.light(cls=0x211)[0], 2)                       # the glow branch: unsupported
        self.assertEqual(self.light(cls=0x3d5)[0], 2)


class EnvBodyLight(unittest.TestCase):
    def test_flag_and_colour(self):
        lib = library('reconstructed/environment', f'libclient_env.{SUFFIX}')
        lib.mu_env_test_new.restype = ctypes.c_void_p
        lib.mu_env_test_new.argtypes = [ctypes.c_uint32]
        lib.mu_env_test_load.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        lib.mu_env_test_body_light.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32,
                                               ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                                               ctypes.POINTER(ctypes.c_uint8)]
        lib.mu_env_test_free.argtypes = [ctypes.c_void_p]
        boids = bytearray(40 * 0x3d8)
        for i, (flag, light) in enumerate(((1, 0.5), (0, 1.0))):
            o = i * 0x3d8
            boids[o] = 1
            boids[o + 5] = flag
            struct.pack_into('<3f', boids, o + 0xec, light, light, light)
        h = lib.mu_env_test_new(1)
        lib.mu_env_test_load(h, bytes(boids), bytes(10 * 0x3d8), bytes(200 * 0xb4))
        frame = (ctypes.c_float * 3)(0.25, 0.5, 0.75)
        for i, (flag, light) in enumerate(((1, 0.5), (0, 1.0))):
            color, lighting = (ctypes.c_float * 3)(), ctypes.c_uint8()
            lib.mu_env_test_body_light(h, 0, i, frame, color, ctypes.byref(lighting))
            self.assertEqual(lighting.value, flag)
            self.assertEqual(list(color), [0.25 + light, 0.5 + light, 0.75 + light])
        lib.mu_env_test_free(h)


sys.path.insert(0, str(ROOT / 'scripts'))


class ObjectScreen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import validate_fidelity as vf
        cls.vf = vf
        cls.lib = library('reconstructed/hud', f'libmu_hud.{SUFFIX}')
        cls.lib.mu_hud_object_screen.argtypes = [ctypes.POINTER(vf.RosIn), ctypes.POINTER(vf.RosOut)]

    def ros(self, type_, **kw):
        c = self.vf.RosIn(type=type_, level_word=kw.get('level', 0) << 3, scale=1.0, select=kw.get('select', 0),
                          held=kw.get('held', 0), has_state=1, tick=1, time=1000.0, has_record=kw.get('record', 1),
                          kind_a=kw.get('kind_a', 0), item_kind=kw.get('kind', 0), anim_present=kw.get('anim', 0),
                          anim_action=3, anim_speed=0.3, pose_model_exists=1, object_alpha=1.0, state_frame=2.5)
        out = self.vf.RosOut()
        self.lib.mu_hud_object_screen(ctypes.byref(c), ctypes.byref(out))
        return out

    def test_armour_heights_and_pose(self):
        self.assertEqual((self.ros(0x18e6).pose_model, self.ros(0x18e6).height), (0xa91, -160.0))
        self.assertEqual(self.ros(0x18e6, kind=4).height, -170.0)
        self.assertEqual(self.ros(0x193c).height, -150.0)
        self.assertAlmostEqual(self.ros(0x1927).position[0], 0.04, places=6)
        self.assertEqual(self.ros(0x1ae6).height, -100.0)
        self.assertEqual(self.ros(0x1b40).height, -132.0)
        self.assertEqual(self.ros(0x1ce6).height, -50.0)     # pants
        self.assertEqual(self.ros(0x1ee6).height, -70.0)     # gloves
        self.assertEqual((self.ros(0x20e6).height, self.ros(0x20e6).pose_model), (0.0, 0xa91))   # boots
        self.assertEqual((self.ros(0xae6).height, self.ros(0xae6).pose_model), (0.0, 0xae6))     # a sword
        self.assertEqual(self.ros(0xace).height, -100.0)

    def test_state_and_remaps(self):
        self.assertEqual((self.ros(0x26f2, level=0).render_type, self.ros(0x26f2, level=2).render_type,
                          self.ros(0x26f2, level=1).render_type), (0x3890, 0x3891, 0x26f2))
        self.assertEqual(self.ros(0xae6, level=5, kind_a=0xc).level_word, 0)
        self.assertEqual(self.ros(0xae6, level=5).level_word, 5 << 3)
        self.assertAlmostEqual(self.ros(0xae6, held=1).scale, f32(1.4), places=6)
        self.assertEqual((self.ros(0xae6, select=1).spin, self.ros(0xae6, select=1).spin_angle), (1, 200.0))
        out = self.ros(0xae6, anim=1)
        self.assertEqual((out.action, out.anim_frame, out.ticked), (3, 2.5, 1))
        self.assertEqual((self.ros(0xae6).action, self.ros(0xae6).anim_frame, self.ros(0xae6).ticked), (0, 0.0, 0))
        out = self.ros(0xae6)
        self.assertEqual((out.lighting, list(out.light)), (0, [1.0, 1.0, 1.0]))


class SpecialModels(unittest.TestCase):
    def test_files(self):
        lib = library('reconstructed/items', f'libclient_items.{SUFFIX}')
        lib.mu_gi_special_model_file.argtypes = [ctypes.c_int32, ctypes.c_char_p, ctypes.c_size_t]
        buf = ctypes.create_string_buffer(128)
        self.assertEqual(lib.mu_gi_special_model_file(0x3894, buf, 128), 1)
        self.assertEqual(buf.value, b'Data\\Item\\MagicBox02.bmd')
        lib.mu_gi_special_model_file(0x38a2, buf, 128)
        self.assertEqual(buf.value, b'Data\\Item\\LifeStoneItem.bmd')
        lib.mu_gi_special_model_file(0x3890, buf, 128)
        self.assertEqual(buf.value, b'Data\\Item\\Event02.bmd')
        self.assertEqual(lib.mu_gi_special_model_file(0x1234, buf, 128), 0)


def set_tables(sets, codes):
    """sets: {index: (name, name2)}; codes: {code: [w0, w1, w2, w3]} -> decoded ItemSetType, ItemSetOption bytes."""
    st = bytearray(0x2c00 * 10)
    for code, words in codes.items():
        struct.pack_into('<4H', st, code * 10, *words)
    so = bytearray(1000 * 0x1d4)
    for index, (n1, n2) in sets.items():
        so[index * 0x1d4:index * 0x1d4 + len(n1)] = n1
        so[index * 0x1d4 + 0x40:index * 0x1d4 + 0x40 + len(n2)] = n2
    return bytes(st), bytes(so)


class SetPrefix(unittest.TestCase):
    def build(self, sets, codes, legendary=None, cash=(), cash_items=(), records=None):
        import validate_fidelity as vf  # noqa: F401
        lib = library('reconstructed/items', f'libclient_items.{SUFFIX}')
        st, so = set_tables(sets, codes)
        HAS = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32)
        LEG = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32))

        class Inputs(ctypes.Structure):
            _fields_ = [('set_type', ctypes.c_char_p), ('set_option', ctypes.c_char_p), ('context', ctypes.c_void_p),
                        ('has_record', HAS), ('legendary', LEG), ('cash_set_count', ctypes.c_size_t),
                        ('cash_names', ctypes.POINTER(ctypes.c_char_p)),
                        ('cash_names2', ctypes.POINTER(ctypes.c_char_p)), ('cash_item_count', ctypes.c_size_t),
                        ('cash_items', ctypes.POINTER(ctypes.c_int32))]

        def leg(ctx, t, out):
            for k, v in enumerate((legendary or {}).get(t, (-1, -1, -1, -1))):
                out[k] = v
            return 1
        self.keep = [HAS(lambda ctx, c: int(records is None or c in records)), LEG(leg)]
        n1 = (ctypes.c_char_p * max(1, len(cash)))(*[c[0] for c in cash])
        n2 = (ctypes.c_char_p * max(1, len(cash)))(*[c[1] for c in cash])
        items = (ctypes.c_int32 * max(1, 3 * len(cash_items)))(*[v for t in cash_items for v in t])
        self.keep += [n1, n2, items, st, so]
        inputs = Inputs(st, so, None, self.keep[0], self.keep[1] if legendary is not None else LEG(),
                        len(cash), n1, n2, len(cash_items), items)
        lib.mu_gi_sets_build.restype = ctypes.c_void_p
        lib.mu_gi_sets_build.argtypes = [ctypes.POINTER(Inputs)]
        lib.mu_gi_set_prefix.restype = ctypes.c_char_p
        lib.mu_gi_set_prefix.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_uint8, ctypes.c_uint8]
        self.lib = lib
        return lib.mu_gi_sets_build(ctypes.byref(inputs))

    def test_entries_bits_and_order(self):
        s = self.build({1: (b"Bbb's", b'Bbb'), 2: (b"Aaa's", b'Aaa'), 3: (b"Aaa's", b'Dup')},
                       {0x10: [1, 2, 0, 0], 0x11: [0, 0, 3, 0], 0x12: [2, 0, 0, 1]}, records={0x10, 0x12})
        p = self.lib.mu_gi_set_prefix
        self.assertEqual(p(s, 0x10, 1, 0), b'Bbb')
        self.assertEqual(p(s, 0x10, 2, 0), b'Aaa')
        self.assertEqual(p(s, 0x10, 0x41, 0), b'Bbb')       # bits & 0x33
        self.assertEqual(p(s, 0x10, 0, 0), b'')
        self.assertEqual(p(s, 0x11, 0x10, 0), b'')         # set 3 dropped (duplicate name), no record anyway
        # map order by name: "Aaa's" before "Bbb's"; kind B 0x79 takes any bits
        self.assertEqual(p(s, 0x12, 0x20, 0), b'Bbb')
        self.assertEqual(p(s, 0x12, 0, 0x79), b'Aaa')

    def test_legendary_pairs_and_cash(self):
        s = self.build({5: (b'Leg', b'Legend')}, {0x20: [5, 0, 0, 0]}, legendary={5: (0x20, 0x21, -1, -1)},
                       cash=[(b'Growth', b'Growth')], cash_items=[(0, 0x30, 1)])
        p = self.lib.mu_gi_set_prefix
        self.assertEqual(p(s, 0x20, 1, 0), b'Legend')
        self.assertEqual(p(s, 0x21, 0, 0), b'Legend')     # an unfilled pair slot keeps set bits 0
        self.assertEqual(p(s, 0x21, 1, 0), b'')
        self.assertEqual(p(s, 0x30, 1, 0), b'Growth')     # cash set index base + 1 (base = 5 + 1)


class LangTables(unittest.TestCase):
    def test_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / 'pentagram.tsv').write_text('#c\ndefault\t0\n6344\t1\n6352\t2\n')
            (d / 'invenanim.tsv').write_text(f'#c\n10354\t20\t114\t3\t{struct.unpack("<I", struct.pack("<f", 0.3))[0]}\n')
            (d / 'legendary.tsv').write_text('#t\ndefault\t-1\t-1\t-1\t-1\n326\t128\t128\t-1\t-1\n')
            (d / 'cashsets.tsv').write_text('#s\nset\t0\tGrowth\tGrowth\nitem\t7\t372\t1\n')
            lib_path = d / f'libmulang.{SUFFIX}'
            subprocess.run([shutil.which('cc') or 'clang', '-std=c11', '-O2', '-fPIC', '-shared',
                            str(NATIVE / 'core/mu_lang.c'), '-o', str(lib_path)], check=True)
            L = ctypes.CDLL(str(lib_path))
            L.mu_lang_load.restype = ctypes.c_void_p
            L.mu_lang_load.argtypes = [ctypes.c_char_p]
            L.mu_lang_pentagram_tier.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)]
            L.mu_lang_inven_anim.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_uint16),
                                             ctypes.POINTER(ctypes.c_float)]
            L.mu_lang_legendary.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)]
            L.mu_lang_cash_sets.restype = ctypes.c_size_t
            L.mu_lang_cash_sets.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            h = L.mu_lang_load(str(d).encode())
            t = ctypes.c_int32()
            L.mu_lang_pentagram_tier(h, 6352, ctypes.byref(t))
            self.assertEqual(t.value, 2)
            L.mu_lang_pentagram_tier(h, 1, ctypes.byref(t))
            self.assertEqual(t.value, 0)
            a, sp = ctypes.c_uint16(), ctypes.c_float()
            self.assertEqual(L.mu_lang_inven_anim(h, 10354, ctypes.byref(a), ctypes.byref(sp)), 1)
            self.assertEqual((a.value, round(sp.value, 6)), (3, 0.3))
            self.assertEqual(L.mu_lang_inven_anim(h, 1, ctypes.byref(a), ctypes.byref(sp)), 0)
            codes = (ctypes.c_int32 * 4)()
            L.mu_lang_legendary(h, 326, codes)
            self.assertEqual(list(codes), [128, 128, -1, -1])
            L.mu_lang_legendary(h, 1, codes)
            self.assertEqual(list(codes), [-1] * 4)
            ptr = ctypes.c_void_p()
            self.assertEqual(L.mu_lang_cash_sets(h, ctypes.byref(ptr)), 1)


@unittest.skipUnless(WALK.exists(), 'native/build/mu-walk not built')
class WalkLabels(unittest.TestCase):
    def test_prefix_and_suffix_spacing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = write_items_world(tmp)
            st, so = set_tables({1: (b"Warrior's", b'Warrior')}, {0x0e05: [1, 0, 0, 0]})
            local = Path(root) / 'Data' / 'Local'
            for name, raw, size, key in (('itemsettype.bmd', st, 10, 0xe5f1), ('itemsetoption.bmd', so, 0x1d4, 0xa2f1)):
                payload = b''.join(xor3(raw[i:i + size]) for i in range(0, len(raw), size))
                (local / name).write_bytes(payload + struct.pack('<I', checksum(payload, key)))
            out = run(root, '--items', '--frames', '12', '--item-script',
                      '2:drop:0x0e05:40:122,120:1;2:drop:1:0xcf:120,122;2:drop:0x0e05:40:121,121:0')
            names = sorted({i['name'] for f in out['frames'] for i in f['list']})
            self.assertIn('WarriorLeather Helm +5', names)
            self.assertIn('Leather Helm +5', names)
            self.assertIn('Short Sword +9+Skill+Option+Luck', names)


@unittest.skipUnless(PRIVATE and HAVE_UNICORN and (EVIDENCE / 'x86-text-capture-09/client-text.bin').exists(),
                     'private captures and Unicorn')
class PrivateValidators(unittest.TestCase):
    def test_fidelity_sections(self):
        args = [PYTHON, str(ROOT / 'scripts/validate_fidelity.py'), '--sections', 'env_light,object_screen,special_models',
                '--env-runs', '1', '--env-steps', '120', '--cases', '200']
        if os.environ.get('MU_GAME_ROOT'):
            args += ['--game-root', os.environ['MU_GAME_ROOT']]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])

    @unittest.skipUnless(os.environ.get('MU_LANG_SNAPSHOT') and os.environ.get('MU_GAME_ROOT'), 'snapshot and game root')
    def test_lang_families(self):
        result = subprocess.run([PYTHON, str(ROOT / 'scripts/validate_fidelity.py'), '--sections',
                                 'lang_tables,set_prefix', '--snapshot', os.environ['MU_LANG_SNAPSHOT'],
                                 '--game-root', os.environ['MU_GAME_ROOT'], '--set-bits', '1', '--set-limit', '300'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])

    def test_hero_light_section(self):
        e = EVIDENCE
        result = subprocess.run([PYTHON, str(ROOT / 'scripts/validate_renderchar.py'), '--text',
                                 str(e / 'x86-text-capture-09/client-text.bin'), '--data',
                                 str(e / 'image-data-run10/data-capture-10/client-image-data.bin'), '--flag',
                                 str(e / 'trig-state-15/captures/late/math-dispatch-flag.bin'), '--feature',
                                 str(e / 'x86-math-capture-09/cpu-features.bin'), '--sections', 'light',
                                 '--light-cases', '60'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])


if __name__ == '__main__':
    unittest.main()
