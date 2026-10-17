"""Native character assembly (NATIVE-CHAR-001) checks.

Portable (synthetic data only):
  * golden data: `mu-render chardump` (Player skeleton, body parts, weapons and
    wing) equals the reconstructed libraries and the validators' Python models
    byte for byte, through independently built client memory
    (native/tests/character_reference.py), over several states, envelopes and
    item sets;
  * a negative control: a reference that poses items without keep root differs;
  * character renders are deterministic, and the windowed viewer's headless GL
    output agrees with the software renderer (macOS with SDL2).
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): the installed Player.bmd
with class parts for several classes and installed weapons, shields and a
wing against the same reference; installed character renders succeed with
every texture found. Renders stay in a temporary directory.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
import native_fixtures as nf  # noqa: E402
import character_reference as cr  # noqa: E402

TOOL = NATIVE/'build/mu-render'
VIEWER = NATIVE/'build/mu-viewer'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
SLOT_OPTIONS = {6: ('--weapon', '0'), 7: ('--weapon', '1')}


def run(*args, check=True):
    result = subprocess.run([str(TOOL), *[str(a) for a in args]], capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f'mu-render {args[0]} failed: {result.stderr}')
    return result


def character_arguments(player, paths, actions, state):
    args = [player]
    s = dict(state)
    for name, key in (('--action', 'action'), ('--frame', 'frame'), ('--prior-action', 'prior_action'),
                      ('--prior-frame', 'prior_frame'), ('--ticks', 'ticks'), ('--speed', 'speed'),
                      ('--scale', 'scale'), ('--lighting', 'lighting'), ('--wing-scale', 'wing_scale')):
        if key in s:
            args += [name, repr(s[key]) if isinstance(s[key], float) else str(s[key])]
    for name, key in (('--origin', 'origin'), ('--angles', 'angles'), ('--head', 'head')):
        if key in s:
            args += [name, *[repr(float(x)) for x in s[key]]]
    for index, path in sorted(paths.items()):
        if index < 6:
            args += ['--part', str(index), path]
        elif index == 8:
            args += ['--wing', path]
        else:
            option, slot = SLOT_OPTIONS[index]
            args += [option, slot, path, '--weapon-action', slot, str(actions.get(index, 0))]
    return args + ['--no-textures']


class CharacterBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.directory = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls.directory.name)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def compare(self, reference, player_raw, player_path, items, paths, state):
        """items: {index: (raw, action)}; paths: {index: file}. Returns compared vertices."""
        expected = reference.character(player_raw, items, state)
        actions = {index: action for index, (_, action) in items.items()}
        result = run('chardump', *character_arguments(player_path, paths, actions, state), '--out', self.tmp/'c.bin')
        report = json.loads(result.stdout)
        observed = cr.read_chardump(self.tmp/'c.bin')
        self.assertEqual(report['posed'], 1)
        self.assertEqual(report['prior_action'], expected['state']['prior_action'])
        self.assertEqual(observed['player_bones'], expected['player_bones'])
        vertices = 0
        for index in range(9):
            mine, theirs = observed['items'][index], expected['items'][index]
            self.assertEqual(mine is None, theirs is None, index)
            if theirs is None:
                continue
            self.assertEqual(mine['bones'], theirs['bones'], f'item {index} bones')
            self.assertEqual(len(mine['meshes']), len(theirs['meshes']))
            for a, b in zip(mine['meshes'], theirs['meshes']):
                for key in ('vertices', 'normals', 'lights', 'secondary'):
                    if b[key] is not None:
                        self.assertEqual(a[key], b[key], f'item {index} {key}')
                vertices += len(a['vertices'])//12
        return vertices


def synthetic_set(seed):
    """Player (v15) with link bones 33/42/47, body parts (v10), two items and a wing (v12)."""
    dummies = (9, 21)
    player = nf.envelope_v15(nf.character_layout(seed, bones=50, actions=4, keys=(5, 3, 1, 6), dummies=dummies))
    raws = {slot: nf.character_layout(seed*10+slot, bones=50, meshes=1+slot % 2, dummies=dummies)
            for slot in (0, 1, 2, 3, 4, 5)}
    raws[6] = nf.envelope_v12(nf.character_layout(seed*10+6, bones=3, actions=2, keys=(2, 4), meshes=1))
    raws[7] = nf.envelope_v12(nf.character_layout(seed*10+7, bones=1, meshes=1))
    raws[8] = nf.envelope_v12(nf.character_layout(seed*10+8, bones=5, actions=1, keys=(4,), meshes=2))
    return player, raws


STATES = [
    {'action': 0, 'frame': 1.5, 'prior_action': 0, 'prior_frame': 1.0},
    {'action': 3, 'frame': 2.25, 'prior_action': 1, 'prior_frame': 2.0, 'ticks': 3, 'speed': 0.37,
     'origin': (120.5, -40.0, 7.0), 'angles': (0.0, 0.0, 135.0), 'head': (10.0, -5.0)},
    {'action': 1, 'frame': 0.5, 'scale': 1.2, 'lighting': 0, 'wing_scale': 0.75},
]


class SyntheticCharacterTests(CharacterBuild):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reference = cr.CharacterReference()

    def write(self, player, raws, tag):
        player_path = self.tmp/f'player{tag}.bmd'
        player_path.write_bytes(player)
        paths = {}
        for index, raw in raws.items():
            paths[index] = self.tmp/f'item{tag}-{index}.bmd'
            paths[index].write_bytes(raw)
        return player_path, paths

    def test_chardump_equals_the_reconstructed_functions(self):
        cases = vertices = 0
        for seed in (3, 4):
            player, raws = synthetic_set(seed)
            player_path, paths = self.write(player, raws, seed)
            selections = [dict.fromkeys(raws), {1: 0, 2: 0, 5: 0, 6: 0}, {7: 0, 8: 0, 3: 0}]
            for selection in selections:
                for state in STATES:
                    items = {i: (raws[i], 1 if i == 6 else 0) for i in selection}
                    with self.subTest(seed=seed, items=sorted(selection), state=state):
                        vertices += self.compare(self.reference, player, player_path, items,
                                                 {i: paths[i] for i in selection}, state)
                        cases += 1
        self.assertEqual(cases, 2*3*len(STATES))
        self.assertGreater(vertices, 1000)

    def test_comparison_detects_a_missing_keep_root_attachment(self):
        player, raws = synthetic_set(5)
        player_path, paths = self.write(player, raws, 5)
        expected = self.reference.character(player, {6: (raws[6], 0)}, STATES[1], variant='no-keep-root')
        run('chardump', *character_arguments(player_path, {6: paths[6]}, {6: 0}, STATES[1]), '--out', self.tmp/'n.bin')
        observed = cr.read_chardump(self.tmp/'n.bin')
        self.assertEqual(observed['player_bones'], expected['player_bones'])
        self.assertNotEqual(observed['items'][6]['meshes'][0]['vertices'], expected['items'][6]['meshes'][0]['vertices'])

    def test_render_is_deterministic(self):
        player, raws = synthetic_set(6)
        player_path, paths = self.write(player, raws, 6)
        args = character_arguments(player_path, paths, {6: 1}, STATES[1])
        first = json.loads(run('character', *args, '--size', '120', '160', '--out', self.tmp/'a.png').stdout)
        second = json.loads(run('character', *args, '--size', '120', '160', '--out', self.tmp/'b.png').stdout)
        self.assertEqual(first['sha256'], second['sha256'])
        self.assertEqual(first['items'], 9)
        self.assertGreater(first['triangles'], 50)
        self.assertEqual((self.tmp/'a.png').read_bytes(), (self.tmp/'b.png').read_bytes())

    def test_rejects_bad_slots_and_missing_inputs(self):
        player, raws = synthetic_set(8)
        player_path, paths = self.write(player, raws, 8)
        for bad in (['--weapon', 'nan', paths[6]], ['--weapon', '2', paths[6]], ['--part', '-1', paths[1]],
                    ['--part', '1e300', paths[1]], ['--weapon-action', 'inf', '1'], ['--class', '1e12']):
            with self.subTest(bad=bad):
                result = run('chardump', player_path, *bad, '--out', self.tmp/'r.bin', check=False)
                self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(run('chardump', '--out', self.tmp/'r.bin', check=False).returncode, 1)
        for command in ('image', 'scan', 'info'):
            self.assertEqual(run(command, check=False).returncode, 2, command)

    @unittest.skipUnless(sys.platform == 'darwin' and shutil.which('sdl2-config'), 'needs macOS with SDL2')
    def test_viewer_character_mode_gl_agrees_with_software(self):
        subprocess.run(['make', '-C', str(NATIVE), 'viewer'], check=True, capture_output=True)
        player, raws = synthetic_set(7)
        player_path, paths = self.write(player, raws, 7)
        args = character_arguments(player_path, paths, {}, STATES[0])
        result = subprocess.run([str(VIEWER), *map(str, args), '--headless', '--backend', 'gl', '--compare',
                                 '--size', '160', '120', '--out', str(self.tmp/'v.png')],
                                capture_output=True, text=True, check=True)
        report = json.loads(result.stdout)
        self.assertLess(report['pixels_over_8'], 160*120//100)


@unittest.skipUnless(PRIVATE, 'Installed character checks are opt-in (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT)')
class PrivateCharacterTests(CharacterBuild):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        root = os.environ.get('MU_GAME_ROOT')
        if not root:
            raise AssertionError('Requested integration needs MU_GAME_ROOT')
        cls.root = Path(root)
        cls.data = cls.root/'Data'

    def class_parts(self, class_byte):
        import ctypes
        handle = ctypes.CDLL(str(cr.ROOT/f'reconstructed/model-codec/libcharacter.{cr.SUFFIX}'))
        handle.mu_character_part_type.restype = ctypes.c_uint32
        handle.mu_character_part_file.argtypes = [ctypes.c_uint32, ctypes.c_char_p, ctypes.c_size_t]
        parts = {}
        for slot in range(1, 6):
            buffer = ctypes.create_string_buffer(64)
            if handle.mu_character_part_file(handle.mu_character_part_type(slot, class_byte), buffer, 64):
                parts[slot] = self.data/'Player'/buffer.value.decode()
        return parts

    def test_installed_characters_equal_the_reference(self):
        reference = cr.CharacterReference()
        player_path = self.data/'Player'/'Player.bmd'
        player = player_path.read_bytes()
        weapons = [('Sword01.bmd', 'Shield01.bmd'), ('Staff01.bmd', None), ('Axe03.bmd', 'Shield05.bmd'),
                   ('Spear02.bmd', None), (None, 'Bow01.bmd')]
        vertices = 0
        for number, class_byte in enumerate((0x00, 0x01, 0x02, 0x11, 0x23)):
            parts = self.class_parts(class_byte)
            items = {slot: (path.read_bytes(), 0) for slot, path in parts.items()}
            paths = dict(parts)
            right, left = weapons[number]
            for index, name in ((6, right), (7, left)):
                if name:
                    paths[index] = self.data/'Item'/name
                    items[index] = (paths[index].read_bytes(), 0)
            if number == 3:
                paths[8] = self.data/'Item'/'Wing04.bmd'
                items[8] = (paths[8].read_bytes(), 0)
            state = {'action': 4 + number, 'frame': 1.5, 'prior_action': 4 + number, 'prior_frame': 1.0,
                     'ticks': 2, 'speed': 0.37, 'scale': 0.9, 'origin': (12800.0, 12900.0, 200.0),
                     'angles': (0.0, 0.0, 45.0 * number)}
            with self.subTest(class_byte=hex(class_byte)):
                vertices += self.compare(reference, player, player_path, items, paths, state)
        self.assertGreater(vertices, 4000)

    def test_installed_character_renders_find_every_texture(self):
        result = json.loads(run('character', '--game-root', self.root, '--class', '1', '--action', '4',
                                '--prior-action', '4', '--frame', '1', '--prior-frame', '1', '--weapon', '0',
                                self.data/'Item'/'Sword01.bmd', '--weapon', '1', self.data/'Item'/'Shield01.bmd',
                                '--size', '240', '320', '--out', self.tmp/'dk.png').stdout)
        self.assertEqual(result['items'], 7)
        self.assertEqual(result['textures_missing'], 0)
        self.assertEqual(result['refused'], 0)


if __name__ == '__main__':
    unittest.main()
