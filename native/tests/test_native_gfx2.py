"""GFx extensions, input, fonts, zero-copy and the GFx layer (NATIVE-GFX-002).

Portable (synthetic data authored here, no client bytes):
  * the Ruffle patch series (native/gfx/ruffle-patches) is a well-formed
    `git am` series (five NATIVE-GFX-002 patches, two more since
    NATIVE-GFX-003) that only touches Ruffle's core crate; when a
    pristine pinned Ruffle checkout is present ($MU_GFX_DEPS), it applies;
  * gfxconvert.py replaces a GFx DefineCompactedFont by the same-named
    DefineFont3 of another movie (under the compacted font's id), and falls
    back to the fontconfig font when no such movie exists;
  * native/gfx/mu_gfx_layer.c, compiled without GL and driven by a test host
    against a stand-in libmugfx (tests/gfx_stub_mugfx.c), plays the game side:
    hotkeys open windows, inventory pick/drop/right click on the reconstructed
    grid, item tooltips in InfoPopup, chat input with local echo, character
    rows, close buttons, clicks outside the interface reach the world, the
    players are sized to their windows.
  * When native/gfx/mugfx is built (Rust + patched Ruffle; CI has neither):
    a synthetic AS2 movie checks every patched extension under Ruffle
    (onReleaseAux/onDragOutAux, hitTestDisable, topmostLevel drawing and
    picking, noAdvance, Selection/Mouse/System.capabilities extensions,
    getTopMostEntity, setCursorType, appendHtml, textAutoSize, verticalAlign,
    disableFocusKeys), keyboard/text input, the GFx hit test, window-sized
    views and the IOSurface path against the read-back path; and the layer
    runs on the real library.
Private (MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT): the six client movies
with DefineCompactedFont convert with no unconverted tag.
"""
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
ROOT = NATIVE.parent
sys.path.insert(0, str(NATIVE/'gfx'))
sys.path.insert(0, str(HERE))

import gfxswf as g  # noqa: E402
import gfxconvert as conv  # noqa: E402
from test_native_gfx import Bits, rect, matrix_bits, tag, cstr, place, font3, swf, build_root  # noqa: E402

PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')
PATCHES = sorted((NATIVE/'gfx/ruffle-patches').glob('*.patch'))
RUFFLE_REV = '061b39b0c3ecdd88214ba1750a035a678bf73559'
SHOT = NATIVE/'gfx/mugfx/target/release/mugfx-shot'
LIBMUGFX = NATIVE/'gfx/mugfx/target/release'/('libmugfx.dylib' if sys.platform == 'darwin' else 'libmugfx.so')
CC = os.environ.get('CC') or shutil.which('cc') or shutil.which('clang') or shutil.which('gcc')

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


# --------------------------------------------------------------------------- SWF / AVM1 helpers

P = conv._push
GV, GM, SM, SV, CM, CF, POP, ADD2, RET = b'\x1c', b'\x4e', b'\x4f', b'\x1d', b'\x52', b'\x3d', b'\x17', b'\x47', b'\x3e'
EI = P('flash') + GV + P('external') + GM + P('ExternalInterface') + GM


def shape_solid(shape_id, w_px, h_px, rgb):
    """DefineShape: a w x h rectangle with one solid fill."""
    tw, th = w_px * 20, h_px * 20
    head = bytes([1, 0x00]) + bytes(rgb)        # one solid fill style
    r = Bits()
    r.ub(8, 0)                                  # no line styles
    r.ub(4, 1); r.ub(4, 0)
    r.ub(1, 0); r.ub(1, 0); r.ub(1, 0); r.ub(1, 1); r.ub(1, 0); r.ub(1, 1)
    r.ub(5, 2); r.sb(2, 0); r.sb(2, 0)
    r.ub(1, 1)
    for dx, dy in ((tw, 0), (0, th), (-tw, 0), (0, -th)):
        n = max(abs(dx).bit_length(), abs(dy).bit_length()) + 1
        r.ub(1, 1); r.ub(1, 1); r.ub(4, n - 2)
        if dx:
            r.ub(1, 0); r.ub(1, 0); r.sb(n, dx)
        else:
            r.ub(1, 0); r.ub(1, 1); r.sb(n, dy)
    r.ub(6, 0)
    return tag(2, struct.pack('<H', shape_id) + rect(0, tw, 0, th) + head + r.bytes())


def sprite(sprite_id, shape_id):
    w = Bits()
    matrix_bits(w)
    inner = tag(26, bytes([0x06]) + struct.pack('<HH', 1, shape_id) + w.bytes()) + tag(1, b'') + b'\0\0'
    return tag(39, struct.pack('<HH', sprite_id, 1) + inner)


def arg(a):
    return P(a[1:]) + GV if isinstance(a, str) and a.startswith('$') else P(a)


def ei_call(name, *args):
    """flash.external.ExternalInterface.call(name, args...); '$x' args are variables."""
    code = b''.join(arg(a) for a in reversed(args))
    return code + P(name, len(args) + 1) + EI + P('call') + CM + POP


def target(path):
    parts = path.split('.')
    code = P(parts[0]) + GV
    for p in parts[1:]:
        code += P(p) + GM
    return code


def assign_fn(path, member, params, body):
    return target(path) + P(member) + conv._function(params, body) + SM


def assign(path, member, value):
    return target(path) + P(member, value) + SM


def extension_movie():
    """200 x 100 stage: `bottom` (red) under `top` (green, hitTestDisable) at
    (0,0) 100 x 100; `pop` (blue, topmostLevel) under `cover` (yellow) at
    (100,0) 50 x 50; `ticker` counts frames.  Handlers report through
    ExternalInterface."""
    tags = [tag(69, b'\0\0\0\0')]
    shapes = [(1, (100, 100), (255, 0, 0)), (2, (100, 100), (0, 255, 0)), (3, (50, 50), (0, 0, 255)),
              (4, (50, 50), (255, 255, 0)), (5, (10, 10), (128, 128, 128))]
    for sid, (w, h), rgb in shapes:
        tags.append(shape_solid(sid, w, h, rgb))
        tags.append(sprite(10 + sid, sid))
    tags += [place(11, 1, 0, 0, 'bottom'), place(12, 2, 0, 0, 'top'), place(13, 3, 2000, 0, 'pop'),
             place(14, 4, 2000, 0, 'cover'), place(15, 5, 3600, 1800, 'ticker')]
    code = b''
    code += assign_fn('_root.bottom', 'onRelease', [], ei_call('hit', 'bottom'))
    code += assign_fn('_root.top', 'onRelease', [], ei_call('hit', 'top'))
    code += assign('_root.top', 'hitTestDisable', True)
    code += assign_fn('_root.bottom', 'onReleaseAux', ['a', 'b', 'c'], ei_call('aux', '$a', '$b', '$c'))
    code += assign_fn('_root.bottom', 'onDragOutAux', ['a', 'b'], ei_call('dragout', '$a', '$b'))
    code += assign_fn('_root.pop', 'onRelease', [], ei_call('hit', 'pop'))
    code += assign_fn('_root.cover', 'onRelease', [], ei_call('hit', 'cover'))
    code += assign('_root.pop', 'topmostLevel', True)
    code += P('_root') + GV + P('ticks', 0) + SM
    tick = P('_root') + GV + P('ticks') + P('_root') + GV + P('ticks') + GM + P(1) + ADD2 + SM
    code += assign_fn('_root.ticker', 'onEnterFrame', [], tick)
    tme = P('y') + GV + P('x') + GV + P(2) + P('Mouse') + GV + P('getTopMostEntity') + CM + P(1, 'String') + CF + RET
    code += assign_fn('_root', 'tme', ['x', 'y'], tme)
    tags += [tag(12, code + b'\0'), tag(12, conv.bridge_actions()), tag(1, b'')]
    return swf(tags, version=9, size=(200, 100))


def shot(swf_path, png, *ops, size='200x100', frames=1, shared=False):
    cmd = [str(SHOT), str(swf_path), str(png), '--size', size, '--frames', str(frames)] + (['--shared'] if shared else [])
    r = subprocess.run(cmd + [str(o) for o in ops], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise AssertionError(r.stdout + r.stderr)
    return r.stdout


def lines_after(out, op):
    """Output lines following the line that starts with `op`."""
    lines = out.splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith(op))
    return lines[i + 1:]


# --------------------------------------------------------------------------- patch series

class PatchSeries(unittest.TestCase):
    def test_series_is_well_formed(self):
        self.assertEqual(len(PATCHES), 7)   # 0001-0005 NATIVE-GFX-002, 0006-0007 NATIVE-GFX-003
        subjects = []
        for i, p in enumerate(PATCHES, 1):
            text = p.read_text()
            m = re.search(r'^Subject: \[PATCH (\d+)/(\d+)\] (mu: .*)$', text, re.M)
            self.assertIsNotNone(m, p.name)
            self.assertEqual((int(m.group(1)), int(m.group(2))), (i, len(PATCHES)))
            subjects.append(m.group(3))
            files = re.findall(r'^diff --git a/(\S+) b/', text, re.M)
            self.assertTrue(files)
            self.assertTrue(all(f.startswith('core/src/') for f in files), files)
            self.assertIn('Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>', text)
        joined = '\n'.join(subjects)
        for word in ('onPressAux', 'hitTestDisable', 'Selection', 'TextField', 'host view', 'load order',
                     'host-supplied images'):
            self.assertIn(word, joined)
        script = (NATIVE/'gfx/apply-ruffle-patches.sh').read_text()
        self.assertIn(RUFFLE_REV, script)
        self.assertIn(RUFFLE_REV, (NATIVE/'gfx/fetch-ruffle.sh').read_text())
        self.assertEqual(subprocess.run(['sh', '-n', str(NATIVE/'gfx/apply-ruffle-patches.sh')]).returncode, 0)

    def test_series_applies_to_the_pinned_checkout(self):
        deps = Path(os.environ.get('MU_GFX_DEPS', Path.home()/'.cache/mu-recovery-gfx'))
        pristine = deps/f'ruffle-{RUFFLE_REV[:12]}'
        if not (pristine/'.git').exists() or not shutil.which('git'):
            self.skipTest('no pinned Ruffle checkout (native/gfx/fetch-ruffle.sh)')
        with tempfile.TemporaryDirectory() as tmp:
            wt = Path(tmp)/'ruffle'
            subprocess.run(['git', '-C', str(pristine), 'worktree', 'add', '--quiet', '--detach', str(wt), RUFFLE_REV],
                           check=True)
            try:
                r = subprocess.run(['git', '-C', str(wt), '-c', 'user.name=t', '-c', 'user.email=t@localhost', 'am',
                                    '--quiet'] + [str(p) for p in PATCHES], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                log = subprocess.run(['git', '-C', str(wt), 'log', '--format=%s', f'{RUFFLE_REV}..HEAD'],
                                     capture_output=True, text=True).stdout.splitlines()
                self.assertEqual(len(log), len(PATCHES))
            finally:
                subprocess.run(['git', '-C', str(pristine), 'worktree', 'remove', '--force', str(wt)])


# --------------------------------------------------------------------------- converter: compacted fonts

@unittest.skipUnless(Image, 'Pillow missing')
class CompactedFont(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.gfx = build_root(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _movie(self, name, tags):
        (self.gfx/f'{name}.ozg').write_bytes(swf([tag(69, b'\0\0\0\0')] + tags + [tag(1, b'')], sig=b'CFX'))

    def test_compacted_font_takes_the_same_named_font(self):
        packed = struct.pack('<H', 7) + b'Slate Mobile\0' + bytes(range(40))   # glyph data not decoded
        self._movie('Packed', [tag(1005, packed)])
        self._movie('Donor', [tag(75, font3(3, 'Slate Mobile', [0x41, 0x42, 0x43, 0x44]))])
        self.assertEqual(g.parse_compacted_font(g.Tag(1005, packed))['name'], 'Slate Mobile')
        out, rep = conv.convert_movie(self.gfx/'Packed.ozg')
        tags = list(g.movie_tags(g.parse_movie(out)))
        self.assertNotIn(1005, {t.code for t in tags})
        font = next(t for t in tags if t.code == 75)
        info = g.parse_font(font)
        self.assertEqual((info['id'], info['name'], info['glyphs']), (7, 'Slate Mobile', 4))
        self.assertEqual(rep.fonts_inlined, ['Slate Mobile(compacted)<-Donor:Slate Mobile (4 glyphs)'])
        self.assertEqual(rep.unconverted, {})

    def test_compacted_font_without_donor_uses_the_library_font(self):
        packed = struct.pack('<H', 8) + b'Unknown Face\0' + b'\0' * 8
        self._movie('Packed', [tag(1005, packed)])
        out, rep = conv.convert_movie(self.gfx/'Packed.ozg')
        font = next(t for t in g.movie_tags(g.parse_movie(out)) if t.code == 75)
        info = g.parse_font(font)
        self.assertEqual((info['id'], info['name']), (8, 'Unknown Face'))
        self.assertTrue(rep.fonts_inlined[0].startswith('Unknown Face(compacted)<-gfxfontlib.swf'))


# --------------------------------------------------------------------------- the GFx layer (stub library)

def build_layer_host(tmp: Path):
    host = tmp/'gfx-layer-host'
    lib = tmp/('libmugfx_stub.dylib' if sys.platform == 'darwin' else 'libmugfx_stub.so')
    hud = ROOT/'reconstructed/hud'
    subprocess.run([CC, '-std=c11', '-O1', '-shared', '-fPIC', '-o', str(lib), str(HERE/'gfx_stub_mugfx.c')],
                   check=True)
    libs = [] if sys.platform == 'darwin' else ['-ldl']
    subprocess.run([CC, '-std=c11', '-O1', '-Wall', '-Wextra', '-DMU_GFX_NO_GL', '-I', str(NATIVE/'gfx'),
                    '-I', str(hud), str(HERE/'gfx_layer_host.c'), str(NATIVE/'gfx/mu_gfx_layer.c'),
                    str(hud/'inv_grid.c'), str(hud/'item_slots.c'), str(hud/'tooltip_html.c'), '-lm'] + libs +
                   ['-o', str(host)], check=True)
    return host, lib


def states(out):
    import json
    return [json.loads(l) for l in out.splitlines() if l.startswith('{')]


@unittest.skipUnless(CC, 'no C compiler')
class LayerWithStub(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.host, cls.lib = build_layer_host(cls.dir)
        (cls.dir/'movies').mkdir()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_host(self, *ops, scale=1, quests=False):
        log = self.dir/'stub.log'
        if log.exists():
            log.unlink()
        env = {**os.environ, 'MUGFX_STUB_LOG': str(log), 'MU_GFX_SCALE': str(scale)}
        if quests:
            env['MU_GFX_HOST_QUEST'] = '1'
        r = subprocess.run([str(self.host), str(self.dir/'movies'), str(self.lib)] + [str(o) for o in ops],
                           capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout, log.read_text() if log.exists() else ''

    def test_quest_window_channels_and_inventory_conditions(self):
        files = [self.dir/'movies'/f'{name}.swf' for name in ('winQuestSummary', 'QuestProgressInfo',
                                                            'NpcJobChangeQuest')]
        for path in files:
            path.touch()
        try:
            out, log = self.run_host('invoke', 16, '-', 'testCall',
                                     '["QuestSummary","OnClickQuest",{"category":2,"index":7}]',
                                     'invoke', 18, '-', 'testCall', '["onClickSelectBtn",1]',
                                     'invoke', 17, '-', 'PlayAnimation', '[]',
                                     'qcount', 'key', 73, 'click', 0, 'qcount', 'click', 24, 'qcount', quests=True)
            self.assertIn('quest callback 16 onLoad [0,0]', out)
            self.assertIn('quest callback 16 OnClickQuest [2,7]', out)
            self.assertIn('quest callback 18 onClickSelectBtn [1]', out)
            self.assertIn('winQuestSummary _level0.win.onFileLoad []', log)
            self.assertIn('.gotoAndPlay [1]', log)
            self.assertEqual([line for line in out.splitlines() if line.startswith('quest inventory')],
                             ['quest inventory 1', 'quest inventory 0', 'quest inventory 1'])
        finally:
            for path in files:
                path.unlink()

    def test_windows_inventory_tooltips_chat_and_routing(self):
        out, log = self.run_host('print', 'key', 73, 'composite', 'print', 'hover', 1, 'click', 1, 'print', 'click', 41,
                                 'print', 'rclick', 41, 'key', 13, 'text', 'hello', 'key', 13, 'print', 'key', 67,
                                 'print', 'at', 640, 300, 'closebtn', 'print', 'key', 27, 'print')
        s = states(out)
        # Paths reported by the movies through UIInit / main onLoad (layer plays the UI loader).
        self.assertEqual((s[0]['main_path'], s[0]['inventory_path']), ('_level0.mc', '_level0.g_mcInventory'))
        self.assertEqual(s[0]['cells'], [0, 1, 3])                   # 0x00ad49fb first-fit of 1x3, 2x2, 1x1
        self.assertEqual(s[0]['inventory_open'], 0)
        # 'I' opens the inventory (the layer's key scan; NATIVE-GFX-003: the bar's menu ids are not key codes).
        self.assertEqual(s[1]['inventory_open'], 1)
        self.assertIn('InventoryFrame _level0.g_mcInventory.SetVisible [true]', log)
        # The player is sized to the window: content 948..1280 x 20..659, padded to 32 px.
        self.assertEqual(s[1]['inventory_view'], [928, 0, 352, 672])
        # Hovering the helm shows its tooltip through InfoPopup.SetInfoPopup (reconstructed HTML).
        self.assertRegex(log, r"InfoPopup _level0\.g_mcInfoPopup\.SetInfoPopup \[\d+,\d+,52,52,\"<font color='#FFCC19'>"
                              r"Bronze Helm \+7</font><br><BR>")
        # Click picks the helm up (reconstructed grid remove), click on cell 41 drops it there.
        self.assertEqual((s[2]['held'], s[2]['cells'][1]), (1, -1))
        self.assertEqual((s[3]['held'], s[3]['cells']), (-1, [0, 41, 3]))
        self.assertIn('rclick 41 took 1', out)
        # Enter opens the chat input, typed text is sent through the movie's own path and echoed.
        self.assertEqual(s[4]['chat_sent'], 'hello')
        self.assertIn('chat _level0.mc.OpenEditText []', log)
        self.assertIn('chat _level0.mc.onPushText [{"pos":0,"str":"hello"}]', log)
        self.assertIn('chat _level0.mc.AddChatInfo [{"type":1,"name":"Nighty","msg":"hello"}]', log)
        # 'C' opens the character window filled from the hero values.
        self.assertEqual(s[5]['character_open'], 1)
        self.assertIn('CharacterInfoFrame _level0.g_CharacterInfoFrame.SetName [2,1,0,"Strength","1,250","",1]', log)
        # A click on empty world space is not taken; the movie's close button closes the inventory.
        self.assertIn('at 640 300 took 0', out)
        self.assertIn('closebtn took 1', out)
        self.assertEqual((s[6]['inventory_open'], s[6]['character_open']), (0, 1))
        # Esc closes the open windows (layer key scan).
        self.assertEqual(s[7]['character_open'], 0)

    def test_retina_scale_keeps_stage_points(self):
        """At 2 pixels per point the movies keep a 1280 x 800 point stage; input
        in window pixels reaches the same cells."""
        out, log = self.run_host('key', 73, 'composite', 'hover', 1, 'click', 1, 'click', 41, 'at', 640, 300,
                                 'closebtn', 'print', scale=2)
        s = states(out)[-1]
        self.assertEqual(s['cells'], [0, 41, 3])
        self.assertEqual(s['inventory_view'], [928, 0, 352, 672])       # points, as at scale 1
        self.assertEqual(s['inventory_open'], 0)
        self.assertIn('at 640 300 took 0', out)
        self.assertIn('InventoryFrame _level0.g_mcInventory.SetWindowSize [1280,800]', log)   # the window size (0x00ac9edc)

    def test_missing_library_fails_cleanly(self):
        r = subprocess.run([str(self.host), str(self.dir/'movies'), str(self.dir/'nope.so')], capture_output=True,
                           text=True, timeout=60, cwd=self.dir, env={**os.environ, 'MU_GFX_LIB': str(self.dir/'nope.so')})
        self.assertEqual(r.returncode, 1)
        self.assertIn('libmugfx not found', r.stdout)


# --------------------------------------------------------------------------- Ruffle with the patch series

@unittest.skipUnless(SHOT.exists() and Image, 'native/gfx/mugfx not built (fetch-ruffle.sh, build-mugfx.sh)')
class RuffleExtensions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.swf = cls.dir/'ext.swf'
        cls.swf.write_bytes(extension_movie())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_mouse_extensions(self):
        out = shot(self.swf, self.dir/'a.png',
                   '--click', 50, 50,                    # top is hitTestDisable: bottom gets the click
                   '--click', 50, 50, 1,                 # right click: onReleaseAux(0, 0, 1)
                   '--mouse', 'down', 50, 50, 1, '--mouse', 'move', 170, 70, '--mouse', 'up', 170, 70, 1,
                   '--click', 125, 25,                   # pop (topmostLevel) is picked above cover
                   '--hit', 50, 50, '--hit', 170, 40, '--invoke', '_root', 'tme', '[125,25]',
                   '--invoke', 'Mouse', 'setCursorType', '[2]', '--cursor')
        self.assertIn('call hit ["bottom"]', out)
        self.assertNotIn('call hit ["top"]', out)
        self.assertIn('call aux [0.0,0.0,1.0]', out)
        self.assertIn('call dragout [0.0,1.0]', out)
        self.assertIn('call hit ["pop"]', out)
        self.assertNotIn('call hit ["cover"]', out)
        self.assertIn('hit 50 50 -> 1', out)
        self.assertIn('hit 170 40 -> 0', out)
        self.assertIn('invoke _root tme -> "_level0.pop"', out)
        self.assertIn('cursor 2', out)
        im = Image.open(self.dir/'a.png').convert('RGBA')
        self.assertEqual(im.getpixel((50, 50)), (0, 255, 0, 255))     # hitTestDisable does not change drawing
        self.assertEqual(im.getpixel((125, 25)), (0, 0, 255, 255))    # topmostLevel drawn above the cover

    def test_selection_capabilities_and_no_advance(self):
        out = shot(self.swf, '-', '--get', 'System.capabilities.numControllers', '--get', 'Selection.numFocusGroups',
                   '--get', 'Mouse.HAND', '--invoke', 'Selection', 'getControllerMaskByFocusGroup', '[0]',
                   '--advance', 5, '--get', '_root.ticks', '--set', '_root.ticker.noAdvance', 'true',
                   '--advance', 5, '--get', '_root.ticks')
        self.assertIn('get System.capabilities.numControllers -> 1.0', out)
        self.assertIn('get Selection.numFocusGroups -> 1.0', out)
        self.assertIn('get Mouse.HAND -> 1.0', out)
        self.assertIn('invoke Selection getControllerMaskByFocusGroup -> 1.0', out)
        ticks = [float(l.split('-> ')[1]) for l in out.splitlines() if l.startswith('get _root.ticks')]
        self.assertGreater(ticks[0], 0)
        self.assertEqual(ticks[0], ticks[1])                          # noAdvance stops onEnterFrame

    def test_text_field_extensions_and_keyboard(self):
        out = shot(self.swf, '-', '--invoke', '_root', 'createTextField', '["tf",20,0,0,120,40]',
                   '--set', '_root.tf.text', '"AB"', '--invoke', '_root.tf', 'appendHtml', '["C"]',
                   '--get', '_root.tf.text', '--set', '_root.tf.textAutoSize', '"fit"', '--get', '_root.tf.textAutoSize',
                   '--set', '_root.tf.verticalAlign', '"center"', '--get', '_root.tf.verticalAlign',
                   '--set', '_root.tf.type', '"input"', '--invoke', 'Selection', 'setFocus', '["_root.tf"]',
                   '--invoke', 'Selection', 'setSelection', '[3,3]',
                   '--focus', '--text', 'xy', '--get', '_root.tf.text', '--key', 8, '--get', '_root.tf.text',
                   '--set', 'Selection.disableFocusKeys', 'true', '--key', 9, '--invoke', 'Selection', 'getFocus', '[]')
        gets = [l for l in out.splitlines() if l.startswith('get ')]
        self.assertEqual(gets[0], 'get _root.tf.text -> "ABC"')
        self.assertEqual(gets[1], 'get _root.tf.textAutoSize -> "fit"')
        self.assertEqual(gets[2], 'get _root.tf.verticalAlign -> "center"')
        self.assertIn('focus 1', out)
        self.assertEqual(gets[3], 'get _root.tf.text -> "ABCxy"')
        self.assertEqual(gets[4], 'get _root.tf.text -> "ABCx"')
        self.assertIn('invoke Selection getFocus -> "_level0.tf"', out)   # Tab did not move the focus

    def _ink_rows(self, png):
        im = Image.open(png).convert('RGBA')
        rows = [y for y in range(im.height) if any(im.getpixel((x, y))[3] for x in range(im.width))]
        return (rows[0], rows[-1]) if rows else (None, None)

    def test_text_auto_size_and_vertical_align_layout(self):
        def text_png(name, *props):
            ops = ['--invoke', '_root', 'createTextField', '["tt",30,0,0,200,100]', '--set', '_root.bottom._visible',
                   'false', '--set', '_root.top._visible', 'false', '--set', '_root.pop._visible', 'false',
                   '--set', '_root.cover._visible', 'false', '--set', '_root.ticker._visible', 'false']
            for k, v in props:
                ops += ['--set', f'_root.tt.{k}', v]
            ops += ['--set', '_root.tt.text', '"' + 'Hello hello hello ' * 6 + '"']
            shot(self.swf, self.dir/name, *ops)
            return self._ink_rows(self.dir/name)
        plain = text_png('plain.png')
        centred = text_png('centre.png', ('verticalAlign', '"center"'))
        shrunk = text_png('shrink.png', ('textAutoSize', '"shrink"'))
        self.assertIsNotNone(plain[0])
        self.assertLess(plain[0], 10)                                   # top-aligned by default
        self.assertGreater(centred[0], 30)                              # one line centred in 100 px
        self.assertLess(shrunk[1] - shrunk[0], plain[1] - plain[0])     # the overflowing line is scaled down

    def test_window_view_and_shared_surface(self):
        out = shot(self.swf, self.dir/'v.png', '--view', 200, 100, 100, 0, 100, 100, '--click', 25, 25)
        self.assertIn('call hit ["pop"]', out)                         # mouse is relative to the view
        im = Image.open(self.dir/'v.png').convert('RGBA')
        self.assertEqual(im.size, (100, 100))
        self.assertEqual(im.getpixel((25, 25)), (0, 0, 255, 255))
        out = shot(self.swf, self.dir/'v2.png', '--view', 200, 100, 100, 0, 100, 100, 2, '--click', 50, 50)
        self.assertIn('call hit ["pop"]', out)                         # Retina: viewport pixels = 2 x points
        im = Image.open(self.dir/'v2.png').convert('RGBA')
        self.assertEqual(im.size, (200, 200))
        self.assertEqual(im.getpixel((50, 50)), (0, 0, 255, 255))
        self.assertEqual(im.getpixel((150, 50))[3], 0)                 # x 75 pt: outside the 50 pt pop
        if sys.platform != 'darwin':
            return
        shot(self.swf, self.dir/'readback.png')
        shot(self.swf, self.dir/'shared.png', shared=True)
        a = Image.open(self.dir/'readback.png').convert('RGBA')
        b = Image.open(self.dir/'shared.png').convert('RGBA')
        diff = max(abs(p - q) for pa, pb in zip(a.getdata(), b.getdata()) for p, q in zip(pa, pb))
        self.assertLessEqual(diff, 2)                                  # IOSurface (BGRA, premultiplied) == read-back


@unittest.skipUnless(LIBMUGFX.exists() and CC, 'native/gfx/mugfx not built')
class LayerWithRuffle(unittest.TestCase):
    def test_layer_opens_synthetic_movies(self):
        """The layer's loader steps on real Ruffle: synthetic movies that report
        the paths the client movies report."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            host, _ = build_layer_host(tmp)
            movies = tmp/'movies'
            movies.mkdir()
            ui_init = {'InventoryFrame': 'g_mcInventory', 'InfoPopup': 'g_mcInfoPopup',
                       'CharacterInfoFrame': 'g_CharacterInfoFrame'}
            for name in ('main', 'InventoryFrame', 'InfoPopup', 'CharacterInfoFrame', 'chat'):
                code = b''
                if name == 'main':
                    code += P('_root') + GV + P('mc') + P(0, 'Object') + b'\x40' + SM     # _root.mc = new Object()
                    code += assign_fn('_root.mc', 'onFileLoad', [], ei_call('main', 'onLoad', '_level0.mc'))
                elif name in ui_init:
                    code += ei_call('UIInit', ui_init[name])
                    code += ei_call('requestSlotInfo', 24, 370, 26, 26, 0) if name == 'InventoryFrame' else b''
                tags = [tag(69, b'\0\0\0\0'), tag(12, code + b'\0'), tag(12, conv.bridge_actions()), tag(1, b'')]
                (movies/f'{name}.swf').write_bytes(swf(tags, size=(200, 100)))
            r = subprocess.run([str(host), str(movies), str(LIBMUGFX), 'print', 'advance', '100', 'composite', 'print'],
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            s = states(r.stdout)
            self.assertEqual((s[0]['main_path'], s[0]['inventory_path']), ('_level0.mc', '_level0.g_mcInventory'))


@unittest.skipUnless(PRIVATE and Image, 'set MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class InstalledCompactedFonts(unittest.TestCase):
    def test_six_compacted_font_movies_convert(self):
        gfx = Path(os.environ['MU_GAME_ROOT'])/'Data/Interface/GFx'
        fonts = conv.FontResolver(gfx, 'English', conv.LATIN_SUBSET)
        for name in ('ExtensionBagFrame', 'GensRanking', 'GuildInfoFrame', 'PrivateStoreFrame', 'RebuyList',
                     'SnsWindow'):
            out, rep = conv.convert_movie(gfx/f'{name}.ozg', fonts)
            self.assertEqual(rep.unconverted, {}, name)
            self.assertTrue(any(f.startswith('Slate Mobile(compacted)<-') for f in rep.fonts_inlined), name)
            self.assertNotIn(1005, {t.code for t in g.movie_tags(g.parse_movie(out))})


if __name__ == '__main__':
    unittest.main()
