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
            sources = ['native/tests/ui_windows2_host.c', 'reconstructed/hud/tooltip_html.c',
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
                         'CommandWindow', 'MatchingSelect', 'GensRanking', 'PetInventoryFrame', 'GremoryCase', 'MacroMain', 'MacroSub', 'HuntRecord', 'StorageInven',
                         'MatchingParty', 'MatchingGuild', 'Guildmatching_2024', 'PlayGuide'):
                (movies/(name+'.swf')).write_bytes(b'authored stub fixture')
            if real:
                movies = Path(os.environ['MU_NATIVE_DATA_DIR'])/'gfx'
                lib = Path(os.environ['MU_GFX_LIB'])
            run = subprocess.run([str(host), str(movies), str(lib)], capture_output=True, text=True,
                                 env={**os.environ, "MU_WINDOWS2_REAL": "1" if real else "0"})
            self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
            self.assertIn('416 inert callbacks', run.stdout)

    def test_production_firewall_navigation_focus_and_sound_owner(self):
        self.run_host()

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and
                         os.environ.get('MU_NATIVE_DATA_DIR') and os.environ.get('MU_GFX_LIB'),
                         'private original movies and Ruffle')
    def test_original_movies_use_the_same_firewall(self):
        self.run_host(real=True)


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private pinned instructions')
class OriginalWindowRoutes(unittest.TestCase):
    def test_z_h_and_end_key_blocks(self):
        """Execute bounded key blocks; unavailable world/class eligibility is a fixture input."""
        sys.path.insert(0, str(ROOT/'scripts'))
        import pins
        import struct
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EBP, UC_X86_REG_EAX, UC_X86_REG_EIP
        text = pins.TEXT.read()
        decisions = 0
        for route, entry, stops, key in (
            ('macro', 0xefd3a4, (0xefd442,), 90),
            ('storage', 0xefc715, (0xefc77a, 0xefc792), 72),
            ('hunt', 0xefc39a, (0xefc426,), 35),
        ):
            for pressed in (0, 1):
                for opened in (0, 1):
                    for mini in (0, 1):
                        u = Uc(UC_ARCH_X86, UC_MODE_32)
                        u.mem_map(0x401000, (len(text)+4095) & ~4095)
                        u.mem_write(0x401000, text)
                        u.mem_map(0x10000000, 0x10000)
                        u.mem_map(0xa39d000, 0x1000)
                        u.reg_write(UC_X86_REG_ESP, 0x10008000)
                        u.reg_write(UC_X86_REG_EBP, 0x1000f000)
                        observed = []
                        def hook(uc, addr, size, data):
                            if addr in stops:
                                uc.emu_stop(); return
                            result = None
                            if addr == 0xec53a7:
                                sp = uc.reg_read(UC_X86_REG_ESP)
                                self.assertEqual(struct.unpack('<I',uc.mem_read(sp+4,4))[0], key)
                                result = pressed
                            elif addr in (0xac3bf7,0x95f986,0x95f647,0xabed9f,0xc08ba8,0x95f75d):
                                result = 0x10000100
                            elif addr == 0xaae6f9: result = opened
                            elif addr == 0xefdc58: result = 1
                            elif addr == 0x95fb99: result = 0
                            elif addr == 0x9616aa: result = mini
                            elif addr in (0xaae767,0xb8a5e2,0xb8a8cf,0xb8a8fc):
                                observed.append(addr)
                                if route == 'hunt': uc.emu_stop(); return
                                result = 0
                            elif addr == 0xa6ac96:
                                sp = uc.reg_read(UC_X86_REG_ESP)
                                self.assertEqual(struct.unpack('<3I',uc.mem_read(sp+4,12)), (25,0,0))
                                observed.append(addr); result = 0
                            if result is not None:
                                sp = uc.reg_read(UC_X86_REG_ESP)
                                ret = struct.unpack('<I',uc.mem_read(sp,4))[0]
                                uc.reg_write(UC_X86_REG_ESP,sp+4)
                                uc.reg_write(UC_X86_REG_EAX,result)
                                uc.reg_write(UC_X86_REG_EIP,ret)
                        u.hook_add(UC_HOOK_CODE,hook)
                        u.emu_start(entry,0,count=300)
                        expected = []
                        if pressed:
                            if route == 'macro' or route == 'storage' and opened:
                                expected = [0xaae767,0xa6ac96]
                            elif route == 'hunt':
                                expected = [0xb8a5e2 if not opened else 0xb8a8fc if mini else 0xb8a8cf]
                        self.assertEqual(observed,expected, (route,pressed,opened,mini))
                        decisions += 1
        self.assertEqual(decisions,24)

    def test_original_playguide_menu_22_block_and_sound(self):
        sys.path.insert(0, str(ROOT/'scripts'))
        import pins
        import struct
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EBP, UC_X86_REG_EAX, UC_X86_REG_EIP
        text=pins.TEXT.read()
        self.assertEqual(struct.unpack_from('<I',text,0xc7170d-0x401000+22*4)[0],0xc71576)
        u=Uc(UC_ARCH_X86,UC_MODE_32)
        u.mem_map(0x401000,(len(text)+4095)&~4095);u.mem_write(0x401000,text)
        u.mem_map(0x10000000,0x10000)
        u.reg_write(UC_X86_REG_ESP,0x10008000);u.reg_write(UC_X86_REG_EBP,0x1000f000)
        calls=[]
        def hook(uc,addr,size,data):
            if addr in (0xac3bf7,0xb3b39e,0xaae767,0xa6ac96):
                calls.append(addr);sp=uc.reg_read(UC_X86_REG_ESP)
                if addr==0xa6ac96:self.assertEqual(struct.unpack('<3I',uc.mem_read(sp+4,12)),(25,0,0))
                ret=struct.unpack('<I',uc.mem_read(sp,4))[0]
                uc.reg_write(UC_X86_REG_ESP,sp+4);uc.reg_write(UC_X86_REG_EAX,0x10000100)
                uc.reg_write(UC_X86_REG_EIP,ret)
        u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0xc71576,0xc716fe,count=80)
        self.assertEqual(calls,[0xac3bf7,0xb3b39e,0xaae767,0xa6ac96])
