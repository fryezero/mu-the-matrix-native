"""The HUD as the client's base movie, icons, item models, placement (NATIVE-GFX-003).

Portable (synthetic data authored here, no client bytes):
  * the Ruffle patch series has the two NATIVE-GFX-003 patches (movie load
    order; host-supplied images) on top of the NATIVE-GFX-002 five;
  * native/gfx/mu_gfx_layer.c against the stand-in libmugfx
    (tests/gfx_stub_mugfx.c) with a base.swf in the movie directory plays the
    client's base movie flow: the UIFrame onLoad answer LoadFrameFiles with
    the client's list limited to the converted movies, changeScene(6) after
    the loader finished, skill.setSkillAll to ASData, InitMenuInfo with menu
    ids and GlobalText placeholders, image0 drawn bottom-up before
    setItemHotKeyAll with the client's render rectangles; the window
    registry placement (InventoryFrame SetAlign 11 + SetWindowSize with the
    window size, none for CharacterInfoFrame) and SetScale(83) below 700
    pixels; menu ids (1 character, 4 inventory); IME composition; the item
    draws the host's item pass receives;
  * the installed skill.bmd decoder (world_gfx_game.c) on a synthetic file;
  * when native/gfx/mugfx is built (CI has no Rust): synthetic movies check
    the patched load order (a movie root's frame-1 onLoad, onLoadComplete
    after the loaded movie's first frame), loadClip with a backslash path,
    loadBitmapFromLib in a loaded icon movie, host images shared with the
    movie, IME preedit and double-buffered shared surfaces.
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT and a built mugfx): the
client's base movie set converts and the layer runs it on the real library.
"""
import json
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
sys.path.insert(0, str(NATIVE/'gfx'))
sys.path.insert(0, str(HERE))

import gfxconvert as conv  # noqa: E402
from test_native_gfx import tag, swf  # noqa: E402
from test_native_gfx2 import (P, GV, GM, SM, SV, CM, POP, RET, ei_call, assign, build_layer_host, states,  # noqa: E402
                              shot, PATCHES, LIBMUGFX, SHOT, CC, Image, PRIVATE)

NEW = b'\x40'


def getv(name):
    return P(name) + GV


def member(code, name):
    return code + P(name) + GM


def callm(obj, method, *args):
    """obj.method(args...) with code fragments as arguments."""
    return b''.join(reversed(args)) + P(len(args)) + obj + P(method) + CM


def ei_code(name, *args):
    """ExternalInterface.call(name, args...) with code fragments as arguments."""
    ei = member(member(getv('flash'), 'external'), 'ExternalInterface')
    return callm(ei, 'call', P(name), *args) + POP


def set_member(obj, name, code):
    return obj + P(name) + code + SM


def bitmap_data():
    return member(member(getv('flash'), 'display'), 'BitmapData')


def lossless_square(cid, size, rgba):
    from PIL import Image as PILImage
    return tag(36, conv.lossless2(cid, PILImage.new('RGBA', (size, size), rgba)))


def icon_movie():
    """An icon library as the client's Icons.swf: a red 4 x 4 bitmap exported
    as icon_7 and a timeline function loadBitmapFromLib(name) that calls
    BitmapData.loadBitmap in this movie; its frame sets `marker` and its
    root onLoad reports `childload`."""
    code = set_member(getv('this'), 'marker', P('ready'))
    body = callm(bitmap_data(), 'loadBitmap', getv('n')) + RET
    code += set_member(getv('this'), 'loadBitmapFromLib', conv._function(['n'], body))
    code += set_member(getv('this'), 'onLoad', conv._function([], ei_code('childload', member(getv('this'), 'marker'))))
    tags = [tag(69, b'\0\0\0\0'), lossless_square(1, 4, (255, 0, 0, 255)),
            tag(56, struct.pack('<H', 1) + struct.pack('<H', 1) + b'icon_7\0'), tag(12, code + b'\0'), tag(1, b'')]
    return swf(tags, version=9, size=(64, 64))


def window_movie():
    """A window movie: its root onLoad reports `rootload`; it loads
    datas\\icons.swf into mcIcon with a MovieClipLoader whose onLoadComplete
    reports the loaded movie's `marker`; show() returns the width of
    mcIcon.loadBitmapFromLib("icon_7"); pix() the pixel (1,1) of the game
    image image0; attach() draws image0 at (0,0)."""
    code = set_member(getv('this'), 'onLoad', conv._function([], ei_code('rootload')))
    code += P('mcIcon') + callm(getv('_root'), 'createEmptyMovieClip', P('mcIcon'), P(1)) + SV
    code += P('l') + P(0, 'Object') + NEW + SV
    code += set_member(getv('l'), 'onLoadComplete',
                       conv._function(['t'], ei_code('complete', member(getv('t'), 'marker'))))
    code += P('mcl') + P(0, 'MovieClipLoader') + NEW + SV
    code += callm(getv('mcl'), 'addListener', getv('l')) + POP
    code += callm(getv('mcl'), 'loadClip', P('datas\\icons.swf'), getv('mcIcon')) + POP
    show = member(callm(member(getv('_root'), 'mcIcon'), 'loadBitmapFromLib', P('icon_7')), 'width') + RET
    code += set_member(getv('_root'), 'show', conv._function([], show))
    pix = callm(callm(bitmap_data(), 'loadBitmap', P('image0')), 'getPixel32', P(1), P(1)) + RET
    code += set_member(getv('_root'), 'pix', conv._function([], pix))
    attach = callm(callm(getv('_root'), 'createEmptyMovieClip', P('pic'), P(5)), 'attachBitmap',
                   callm(bitmap_data(), 'loadBitmap', P('image0')), P(1)) + POP
    code += set_member(getv('_root'), 'attach', conv._function([], attach))
    tags = [tag(69, b'\0\0\0\0'), tag(12, code + b'\0'), tag(12, conv.bridge_actions()), tag(1, b'')]
    return swf(tags, version=9, size=(64, 64))


# --------------------------------------------------------------------------- patch series

class PatchSeries(unittest.TestCase):
    def test_gfx3_patches_follow_the_gfx2_series(self):
        names = [p.name for p in PATCHES]
        self.assertEqual(len(names), 7)
        self.assertTrue(names[5].startswith('0006-mu-GFx-movie-load-order'))
        self.assertTrue(names[6].startswith('0007-mu-host-supplied-images'))
        files6 = {l.split()[2][2:] for l in PATCHES[5].read_text().splitlines() if l.startswith('diff --git')}
        files7 = {l.split()[2][2:] for l in PATCHES[6].read_text().splitlines() if l.startswith('diff --git')}
        self.assertEqual(files6, {'core/src/display_object/movie_clip.rs', 'core/src/loader.rs'})
        self.assertEqual(files7, {'core/src/avm1/runtime.rs', 'core/src/avm1/globals/bitmap_data.rs',
                                  'core/src/player.rs'})
        for p in PATCHES[5:]:
            text = p.read_text()
            self.assertIn('Co-Authored-By: Claude Opus 5.5', text)
            self.assertIn('mu patch', text)


# --------------------------------------------------------------------------- the layer in base mode (stub library)

BASE_MOVIES = ('base', 'ExternalBase', 'ImageData', 'main', 'Chat', 'InventoryFrame', 'InfoPopup',
               'CharacterInfoFrame')


@unittest.skipUnless(CC, 'no C compiler')
class BaseMovieWithStub(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.host, cls.lib = build_layer_host(cls.dir)
        (cls.dir/'movies').mkdir()
        for m in BASE_MOVIES:
            (cls.dir/'movies'/f'{m}.swf').write_bytes(b'')   # the stub only needs the names

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_host(self, *ops, size=None):
        log = self.dir/'stub.log'
        if log.exists():
            log.unlink()
        env = {**os.environ, 'MUGFX_STUB_LOG': str(log)}
        if size:
            env['MU_GFX_SIZE'] = size
        r = subprocess.run([str(self.host), str(self.dir/'movies'), str(self.lib)] + [str(o) for o in ops],
                           capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout, log.read_text().splitlines() if log.exists() else []

    def test_base_movie_flow_skills_icons_and_menu(self):
        out, log = self.run_host('print', 'channels')
        s = states(out)
        self.assertEqual(s[0]['base_mode'], 1)
        self.assertEqual(s[0]['main_path'], '_level0.base.UI.mcBottomFrame.main_1.mc')
        self.assertEqual(s[0]['chat_path'], '_level0.base.UI.mcBottom.Chat_2.instance96')
        ch = json.loads(next(l for l in out.splitlines() if l.startswith('{"channels"')))['channels']
        self.assertEqual((ch['UIFrame'], ch['ASData']), ('_level0.base.UI', '_level0.base.DataMan'))
        # The client's list (0x00c8f05d), limited to the converted movies of the directory.
        self.assertIn('base _level0.base.UI.LoadFrameFiles [{"mcData":["ImageData"],"mcTopLevel":[],'
                      '"mcBottomFrame":["main"],"mcBottom":["Chat"],"mcBottomHud":[]}]', log)
        i_load = log.index(next(l for l in log if '.LoadFrameFiles ' in l))
        i_scene = log.index('base _level0.base.UI.changeScene [6]')
        self.assertGreater(i_scene, i_load)
        skills = next(l for l in log if '.skill.setSkillAll ' in l)
        self.assertTrue(skills.startswith('base _level0.base.DataMan.skill.setSkillAll [[{"Index":1,"Magic_Icon":1,'
                                          '"Name":"Skill 1","Delay":0,"SkillUseType":0,"MasteryType":0}'))
        menu = next(l for l in log if '.InitMenuInfo ' in l)
        self.assertIn('"CharacterInfo":{"keyCode":1,"key":"C","label":"Character"}', menu)
        self.assertIn('{"keyCode":5,"key":"","label":"GlobalText 2343"}', menu)      # GT 0x927, placeholder
        self.assertIn('{"keyCode":22,"key":"CTRL+T","label":"GlobalText 6459"}', menu)
        # image0 before the hotkeys, the stand-in square in GL row order (bottom-up rows).
        i_image = log.index('base set_image image0 512x512 opaque 256 rows 494..509 cols 2..17')
        hot = next(l for l in log if '.setItemHotKeyAll ' in l)
        self.assertLess(i_image, log.index(hot))
        self.assertIn('"itemType":7171,"itemLevel":0,"itemCount":25,"InventoryIndex":-1,"renderX":0,"renderY":0,'
                      '"renderW":20,"renderH":20}', hot)

    def test_window_placement_and_scale(self):
        _, log = self.run_host('print')
        self.assertIn('InventoryFrame _level0.g_mcInventory.SetAlign [11]', log)
        self.assertIn('InventoryFrame _level0.g_mcInventory.SetWindowSize [1280,800]', log)
        self.assertFalse(any(l.startswith('CharacterInfoFrame') and ('SetWindowSize' in l or 'SetAlign' in l)
                             for l in log))
        self.assertFalse(any('SetScale' in l for l in log))
        out, log = self.run_host('key', 73, 'items', size='1024x600')
        self.assertIn('InventoryFrame _level0.g_mcInventory.SetScale [83]', log)
        self.assertIn('CharacterInfoFrame _level0.g_CharacterInfoFrame.SetScale [83]', log)
        self.assertIn('InventoryFrame _level0.g_mcInventory.SetWindowSize [1024,600]', log)
        draws = [json.loads(l) for l in out.splitlines() if l.startswith('{"item_draw"')]
        self.assertEqual([d['code'] for d in draws], [0, 3584, 7171])
        self.assertTrue(all(abs(d['frame_scale'] - 0.83) < 1e-6 for d in draws))
        # The helm (2 x 2) at cell 1: 26-point cells scaled by 0.83, 640 x 480 units for 1024 x 600.
        helm = draws[1]
        self.assertAlmostEqual(helm['rect'][2], 2 * 26 * 0.83, places=3)
        self.assertAlmostEqual(helm['slot'][2], helm['rect'][2] * 640 / 1024, delta=0.01)

    def test_menu_ids_and_hotkeys(self):
        out, log = self.run_host('invoke', 0, '_level0', 'testCall', '["main","onHotKey",{"keyCode":1}]', 'print',
                                 'invoke', 0, '_level0', 'testCall', '["main","onHotKey",{"keyCode":4}]', 'print',
                                 'key', 27, 'print', 'key', 67, 'print')
        s = states(out)
        self.assertEqual((s[0]['character_open'], s[0]['inventory_open']), (1, 0))   # id 1: CharacterInfoFrame
        self.assertEqual((s[1]['character_open'], s[1]['inventory_open']), (1, 1))   # id 4: inventory (layer choice)
        self.assertEqual((s[2]['character_open'], s[2]['inventory_open']), (0, 0))   # Esc closes them
        self.assertEqual(s[3]['character_open'], 1)                                  # C: layer key scan
        self.assertFalse(any('.onKeyUp' in l for l in log))   # menu ids are not key codes: no bar key handler

    def test_chat_ime_composition(self):
        out, log = self.run_host('key', 13, 'compose', 'ka', 'text', 'Ka', 'key', 13, 'print')
        self.assertIn('base ime "ka" 2 0', log)
        self.assertIn('base ime "" -1 0', log)            # the commit ends the composition
        self.assertEqual(states(out)[-1]['chat_sent'], 'Ka')


# --------------------------------------------------------------------------- skill table

@unittest.skipUnless(CC, 'no C compiler')
class SkillTable(unittest.TestCase):
    def test_skill_bmd_decode(self):
        key = bytes([0xfc, 0xcf, 0xab])
        records = []
        for i in range(4):
            r = bytearray(120)
            if i in (1, 3):
                r[0:6] = b'Skill' + bytes([0x30 + i])
                struct.pack_into('<H', r, 74, 100 + i)     # Magic_Icon
                r[54] = 2 + i                             # MasteryType
                r[55] = 7 if i == 3 else 0                # SkillUseType
            records.append(bytes(b ^ key[k % 3] for k, b in enumerate(r)))
        data = b''.join(records) + b'\0\0\0\0'
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp/'probe.c'
            src.write_text('#include <stdio.h>\n#include "world_gfx_game.h"\n'
                           'int main(int c, char **v) { FILE *f = fopen(v[1], "rb"); unsigned char b[8192];'
                           ' size_t n = fread(b, 1, sizeof b, f); fclose(f); mu_gfx_skill s[8];'
                           ' int k = wg_skills_decode(b, n, s, 8); printf("%d\\n", k);'
                           ' for (int i = 0; i < k; i++) printf("%d %d %d %d %s\\n", s[i].index, s[i].icon,'
                           ' s[i].mastery, s[i].use_type, s[i].name); return 0; }\n')
            exe = tmp/'probe'
            subprocess.run([CC, '-std=c11', '-DWG_SKILLS_ONLY', '-I', str(NATIVE/'world'), '-I', str(NATIVE/'gfx'),
                            str(src), str(NATIVE/'world/world_gfx_game.c'), '-o', str(exe)], check=True)
            (tmp/'skill.bmd').write_bytes(data)
            out = subprocess.run([str(exe), str(tmp/'skill.bmd')], capture_output=True, text=True, check=True).stdout
            self.assertEqual(out.splitlines(), ['2', '1 101 3 0 Skill 1', '3 103 5 7 Skill 3'])
            (tmp/'bad.bmd').write_bytes(data[:-5])
            out = subprocess.run([str(exe), str(tmp/'bad.bmd')], capture_output=True, text=True, check=True).stdout
            self.assertEqual(out.splitlines(), ['0'])


# --------------------------------------------------------------------------- Ruffle with the patch series

@unittest.skipUnless(SHOT.exists() and Image, 'native/gfx/mugfx not built')
class RuffleLoadingAndImages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.swf = cls.dir/'win.swf'
        cls.swf.write_bytes(window_movie())
        (cls.dir/'icons.swf').write_bytes(icon_movie())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_load_order_loadclip_and_load_bitmap_from_lib(self):
        out = shot(self.swf, '-', '--advance', 3, '--resolve', 'datas\\icons.swf', '--resolve', 'frame\\ICONS.SWF',
                   '--resolve', 'missing.swf', '--invoke', '_root', 'show', '[]', size='64x64')
        self.assertIn('call rootload []', out)                 # the root's frame-1 onLoad (patch 0006)
        self.assertIn('call childload ["ready"]', out)         # the loaded movie's root onLoad
        self.assertIn('call complete ["ready"]', out)          # onLoadComplete after the loaded first frame
        resolved = dict(l[len('resolve '):].split(' -> ') for l in out.splitlines() if l.startswith('resolve '))
        icons = self.dir/'icons.swf'
        self.assertTrue(os.path.samefile(resolved['datas\\icons.swf'], icons))      # backslash directory dropped
        self.assertTrue(os.path.samefile(resolved['frame\\ICONS.SWF'], icons))      # and case-insensitive
        self.assertEqual(resolved['missing.swf'], '-')
        self.assertIn('invoke _root show -> 4.0', out)         # loadBitmapFromLib in the icon movie's library

    def test_host_image_shared_with_the_movie(self):
        out = shot(self.swf, '-', '--advance', 2, '--invoke', '_root', 'pix', '[]', '--image', 'image0', 4, 4,
                   'FF0000FF', '--invoke', '_root', 'pix', '[]', '--invoke', '_root', 'attach', '[]',
                   '--pixel', 1, 1, '--image', 'image0', 4, 4, '00FF00FF', '--pixel', 1, 1, size='64x64')
        pix = [l for l in out.splitlines() if l.startswith('invoke _root pix')]
        self.assertEqual(pix[0], 'invoke _root pix -> null')             # no library image0, no host image yet
        self.assertEqual(pix[1], 'invoke _root pix -> -65536.0')         # 0xFFFF0000 (signed) from the host
        pixels = [l for l in out.splitlines() if l.startswith('pixel 1 1')]
        self.assertEqual(pixels[0], 'pixel 1 1 -> [255, 0, 0, 255]')
        self.assertEqual(pixels[1], 'pixel 1 1 -> [0, 255, 0, 255]')     # same bitmap, new pixels (shared)

    def test_ime_preedit(self):
        out = shot(self.swf, '-', '--invoke', '_root', 'createTextField', '["tf",20,0,0,60,20]',
                   '--set', '_root.tf.type', '"input"', '--invoke', 'Selection', 'setFocus', '["_root.tf"]',
                   '--ime', 'ab', 2, 0, '--get', '_root.tf.text', '--ime', '', -1, 0, '--get', '_root.tf.text',
                   '--text', 'abc', '--get', '_root.tf.text', size='64x64')
        gets = [l for l in out.splitlines() if l.startswith('get ')]
        self.assertEqual(gets, ['get _root.tf.text -> "ab"', 'get _root.tf.text -> ""', 'get _root.tf.text -> "abc"'])

    @unittest.skipUnless(sys.platform == 'darwin', 'IOSurface: macOS only')
    def test_double_buffered_surface(self):
        out = shot(self.swf, self.dir/'double.png', '--advance', 2, '--image', 'image0', 4, 4, 'FF0000FF',
                   '--invoke', '_root', 'attach', '[]', '--double', 1, '--shot', '-', '--seed', '--advance', 1,
                   '--shot', '-', '--seed', size='64x64', shared=True)
        self.assertIn('double 1 -> 0', out)
        seeds = [l.split()[1] for l in out.splitlines() if l.startswith('seed ')]
        self.assertEqual(len(seeds), 2)
        self.assertNotEqual(seeds[0], seeds[1])                  # the shown surface alternates
        im = Image.open(self.dir/'double.png').convert('RGBA')
        self.assertEqual(im.getpixel((1, 1)), (255, 0, 0, 255))


# --------------------------------------------------------------------------- private: the client's movies

@unittest.skipUnless(PRIVATE and LIBMUGFX.exists() and CC and Image, 'needs MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, mugfx')
class InstalledBaseMovie(unittest.TestCase):
    def test_client_base_movie_runs(self):
        movies = ('base', 'ExternalBase', 'ImageData', 'Tooltip', 'Popups', 'main', 'ItemDurability', 'Chat',
                  'AlarmFrame', 'topmenu', 'bufflist', 'hudPlayerName', 'hudMap', 'hudNotice', 'InventoryFrame',
                  'InfoPopup', 'CharacterInfoFrame')
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            out = tmp/'movies'
            args = ['--out', str(out), '--bridge', '--transparent', '--var', '_root.isClient=true',
                    '--fontconfig', 'English', '--font-subset', 'latin']
            for m in movies:
                args += ['--movie', m]
            self.assertEqual(conv.main(args), 0)
            host, _ = build_layer_host(tmp)
            ops = ['print', 'channels', 'key', 73, 'items', 'advance', 500, 'composite', 'print']
            r = subprocess.run([str(host), str(out), str(LIBMUGFX)] + [str(o) for o in ops],
                               capture_output=True, text=True, timeout=300, env={**os.environ, 'MU_GFX_LOG': '1'})
            self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
            s = states(r.stdout)
            self.assertEqual(s[0]['base_mode'], 1)
            self.assertEqual(s[0]['main_path'], '_level0.base.UI.mcBottomFrame.main_1.mc')
            self.assertTrue(s[0]['chat_path'].startswith('_level0.base.UI.mcBottom.Chat_'))
            ch = json.loads(next(l for l in r.stdout.splitlines() if l.startswith('{"channels"')))['channels']
            self.assertEqual(ch['ASData'], '_level0.base.DataMan')
            self.assertTrue(ch['topmenu'] and ch['alarmframe'])
            self.assertIn('"mcBottomHud":["hudPlayerName","hudMap","hudNotice"]', r.stderr)   # the whole list
            self.assertIn('changeScene([6])', r.stderr)
            self.assertIn('game: image0 (1 item icons)', r.stderr)
            self.assertEqual(s[-1]['inventory_open'], 1)
            draws = [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{"item_draw"')]
            self.assertEqual(len(draws), 3)


if __name__ == '__main__':
    unittest.main()
