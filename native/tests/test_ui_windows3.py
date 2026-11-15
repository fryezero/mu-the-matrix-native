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
            sources = ['native/tests/ui_windows3_host.c', 'reconstructed/hud/tooltip_html.c',
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
                         'CommandWindow', 'MatchingSelect', 'GensRanking', 'PetInventoryFrame', 'GremoryCase', 'SkillTree5th', 'ExtensionBagFrame', 'SkillTree5thItemViewer', 'BlockedChat'):
                (movies/(name+'.swf')).write_bytes(b'authored stub fixture')
            if real:
                movies = Path(os.environ['MU_NATIVE_DATA_DIR'])/'gfx'
                lib = Path(os.environ['MU_GFX_LIB'])
            run = subprocess.run([str(host), str(movies), str(lib)], capture_output=True, text=True,
                                 env={**os.environ,"MU_WINDOWS3_REAL":"1" if real else "0"})
            self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
            self.assertIn('57 inert callbacks', run.stdout)

    def test_production_firewall_navigation_focus_and_sound_owner(self):
        self.run_host()

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and
                         os.environ.get('MU_NATIVE_DATA_DIR') and os.environ.get('MU_GFX_LIB'),
                         'private original movies and Ruffle')
    def test_original_movies_use_the_same_firewall(self):
        self.run_host(real=True)


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private pinned instructions')
class OriginalRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,str(ROOT/'scripts'))
        import pins
        cls.text=pins.TEXT.read()

    def machine(self,entry,stop,services,fields=()):
        import struct
        from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EIP
        u=Uc(UC_ARCH_X86,UC_MODE_32)
        u.mem_map(0x401000,(len(self.text)+4095)&~4095);u.mem_write(0x401000,self.text)
        u.mem_map(0x10000000,0x10000)
        u.reg_write(UC_X86_REG_ESP,0x10008000);u.reg_write(UC_X86_REG_EBP,0x1000f000)
        # Synthetic C++ handler, owner, two vtables. Only the bounded caller executes.
        for a,v in [(0x1000eff0,0x10000500),(0x10000514,0x10000600),
                    (0x10000100,0x10001000),(0x10000300,0x10001100),
                    (0x10001040,0x10002000),(0x10001044,0x10002010),
                    (0x10001140,0x10002020),*fields]:
            u.mem_write(a,struct.pack('<I',v))
        calls=[]
        def hook(uc,a,size,data):
            if a==stop or a==0xefd4be:
                uc.emu_stop();return
            if a in services:
                value,pop=services[a](uc,calls)
                sp=uc.reg_read(UC_X86_REG_ESP);ret=struct.unpack('<I',uc.mem_read(sp,4))[0]
                uc.reg_write(UC_X86_REG_EAX,value);uc.reg_write(UC_X86_REG_ESP,sp+4+pop)
                uc.reg_write(UC_X86_REG_EIP,ret)
            elif not entry<=a<stop:
                self.fail(f'unmodeled route service {a:#x}')
        u.hook_add(UC_HOOK_CODE,hook);u.emu_start(entry,0,count=300)
        return calls

    def test_original_bag_button_and_parent_lifecycle(self):
        def const(v):return lambda u,c:(v,0)
        def event(s):return lambda u,c:(c.append(s) or 0,0)
        cases=0
        for present in (0,1):
            for special in (0,1):
                trace=self.machine(0xb977ea,0xb9782f,{
                    0xac3bf7:const(0x10000700),0xabeab8:const(0x10000100 if present else 0),
                    0xb92b14:const(special),0xb92b0b:event('special-noop'),0xaae767:event('toggle')})
                self.assertEqual(trace,[] if not present else ['special-noop' if special else 'toggle']);cases+=1
        for eligible in (0,1):
            trace=self.machine(0xb91950,0xb91986,{
                0xac3bf7:const(0x10000700),0xabeab8:const(0x10000100),
                0xb6eaa2:const(eligible),0x10002000:event('open')})
            self.assertEqual(trace,['open'] if eligible else []);cases+=1
        for opened in (0,1):
            trace=self.machine(0xb919d5,0xb91a0b,{
                0xac3bf7:const(0x10000700),0xabeab8:const(0x10000100),
                0xaae6f9:const(opened),0x10002010:event('close')})
            self.assertEqual(trace,['close'] if opened else []);cases+=1
        self.assertEqual(cases,8)

    def test_original_fifth_tree_pair_and_independent_viewer(self):
        from unicorn.x86_const import UC_X86_REG_ECX
        def const(v):return lambda u,c:(v,0)
        def event(s):return lambda u,c:(c.append(s) or 0,0)
        cases=0
        for pressed in (0,1):
            for tree in (0,1):
                for viewer in (0,1):
                    def opened(u,c):return (tree if u.reg_read(UC_X86_REG_ECX)==0x10000100 else viewer,0)
                    def toggle(u,c):return (c.append('toggle-tree' if u.reg_read(UC_X86_REG_ECX)==0x10000100 else 'toggle-viewer') or 0,0)
                    trace=self.machine(0xefc104,0xefc1ad,{
                        0xec53a7:const(pressed),0xac3bf7:const(0x10000700),
                        0x95fb5b:const(0x10000100),0x95f5ba:const(0x10000300),0xaae6f9:opened,
                        0xaae767:toggle,0x10002000:event('open-tree'),0x10002020:event('open-viewer')})
                    expected=[] if not pressed else ['toggle-tree','toggle-viewer'] if tree==viewer else ['open-tree','open-viewer']
                    self.assertEqual(trace,expected);cases+=1
            trace=self.machine(0xefc1ad,0xefc1d7,{
                0xec53a7:const(pressed),0xac3bf7:const(0x10000700),
                0x95f5ba:const(0x10000300),0xaae767:event('toggle-viewer')})
            self.assertEqual(trace,['toggle-viewer'] if pressed else []);cases+=1
        self.assertEqual(cases,10)

    def test_original_blocked_chat_requested_visibility(self):
        def const(v,pop=0):return lambda u,c:(v,pop)
        def event(s):return lambda u,c:(c.append(s) or 0,0)
        for requested in (0,1):
            for opened in (0,1):
                trace=self.machine(0xc5fd7d,0xc5fdc2,{
                    0xc61e6b:const(requested,8),0xac3bf7:const(0x10000700),
                    0xbbfe04:const(0x10000100),0xaae6f9:const(opened),0xaae767:event('toggle')})
                self.assertEqual(trace,['toggle'] if requested!=opened else [])

    def test_help_direct_getter_caller_is_still_only_event_helper(self):
        import struct
        target=0xb6cba2
        callers=[0x401000+i for i in range(len(self.text)-5) if self.text[i]==0xe8 and
                 0x401000+i+5+struct.unpack_from('<i',self.text,i+1)[0]==target]
        self.assertEqual(callers,[0xb6b744])
