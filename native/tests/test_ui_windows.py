"""Presentation controllers cannot reach requests, item state or legacy UI audio."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PresentationWindows(unittest.TestCase):
    def run_host(self, real=False):
        with tempfile.TemporaryDirectory(prefix='mu-ui-windows-') as folder:
            tmp = Path(folder)
            cc = os.environ.get('CC', 'cc')
            lib = tmp / ('libmugfx.dylib' if sys.platform == 'darwin' else 'libmugfx.so')
            subprocess.run([cc, '-std=c11', '-O1', '-shared', '-fPIC',
                            str(ROOT/'native/tests/gfx_stub_mugfx.c'), '-o', str(lib)], check=True, capture_output=True)
            sources = ['native/tests/ui_windows_host.c', 'reconstructed/hud/tooltip_html.c',
                       'reconstructed/hud/inv_grid.c', 'reconstructed/hud/item_slots.c']
            host = tmp/'host'
            build = subprocess.run([cc, '-std=c11', '-O1', '-I', str(ROOT/'reconstructed/hud'),
                                    *[str(ROOT/p) for p in sources], '-lm',
                                    *([] if sys.platform == 'darwin' else ['-ldl']), '-o', str(host)],
                                   capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            movies = tmp/'movies'
            movies.mkdir()
            for name in ('main', 'InventoryFrame', 'InfoPopup', 'CharacterInfoFrame', 'chat',
                         'CommandWindow', 'MatchingSelect', 'GensRanking', 'PetInventoryFrame', 'GremoryCase'):
                (movies/(name+'.swf')).write_bytes(b'authored stub fixture')
            if real:
                movies = Path(os.environ['MU_NATIVE_DATA_DIR'])/'gfx'
                lib = Path(os.environ['MU_GFX_LIB'])
            run = subprocess.run([str(host), str(movies), str(lib)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
            self.assertIn('113 inert callbacks', run.stdout)

    def test_production_firewall_navigation_focus_and_sound_owner(self):
        self.run_host()

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and
                         os.environ.get('MU_NATIVE_DATA_DIR') and os.environ.get('MU_GFX_LIB'),
                         'private original movies and Ruffle')
    def test_original_movies_use_the_same_firewall(self):
        self.run_host(real=True)


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private pinned instructions')
class OriginalRoutes(unittest.TestCase):
    def test_original_key_blocks_and_menu_sound_epilogue(self):
        sys.path.insert(0, str(ROOT/'scripts'))
        import pins
        import validate_input as original
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP
        import struct
        text = pins.TEXT.read()
        client = original.Original(text)
        for key, menu, entry, fall in original.BINDINGS:
            if key in ('N', 'B', 'Y', 'K'):
                self.assertEqual(client.menu(ord(key), entry, fall, 1), menu)
                self.assertEqual(client.menu(ord(key), entry, fall, 0), -1)
        u = Uc(UC_ARCH_X86, UC_MODE_32)
        u.mem_map(0x401000, (len(text)+4095) & ~4095)
        u.mem_write(0x401000, text)
        u.mem_map(0x10000000, 0x10000)
        u.reg_write(UC_X86_REG_ESP, 0x10008000)
        calls = []
        def hook(uc, address, size, data):
            if address == 0xa6ac96:
                sp = uc.reg_read(UC_X86_REG_ESP)
                ret, *args = struct.unpack('<4I', uc.mem_read(sp, 16))
                calls.append(args)
                uc.reg_write(UC_X86_REG_ESP, sp+4)
                uc.reg_write(UC_X86_REG_EIP, ret)
        u.hook_add(UC_HOOK_CODE, hook)
        u.emu_start(0xc716f0, 0xc716fe, count=30)
        self.assertEqual(calls, [[25, 0, 0]])
