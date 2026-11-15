"""Empty NPC presentation routes, original lifecycle ordering and callback refusal."""
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
MOVIES = ('ElementalMix','SocketMix','GuardianMix','HarmonyMix','ExchangeLuckCoin',
          'MuunExchange','RuudShopFrame','MixSel','MixAttributeScalp')
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'


class PresentationWindows(unittest.TestCase):
    def run_host(self, real=False, build_root=ROOT, failing=False):
        with tempfile.TemporaryDirectory(prefix='mu-ui-windows4-') as folder:
            tmp=Path(folder);cc=os.environ.get('CC','cc')
            lib=tmp/('libmugfx.dylib' if sys.platform=='darwin' else 'libmugfx.so')
            subprocess.run([cc,'-std=c11','-O1','-shared','-fPIC',
                            str(ROOT/'native/tests/gfx_stub_mugfx.c'),'-o',str(lib)],check=True,capture_output=True)
            host=tmp/'host'
            sources=[getattr(self,'HOST','native/tests/ui_windows4_host.c'),'reconstructed/hud/tooltip_html.c',
                     'reconstructed/hud/inv_grid.c','reconstructed/hud/item_slots.c']
            subprocess.run([cc,'-std=c11','-O1','-I',str(build_root/'reconstructed/hud'),
                            *[str(build_root/p) for p in sources],str(ROOT/'native/build/libmunative.a'),
                            '-lm',* ([] if sys.platform=='darwin' else ['-ldl']),'-o',str(host)],
                           check=True,capture_output=True)
            movies=tmp/'movies';movies.mkdir()
            for name in ('main','InventoryFrame','InfoPopup','CharacterInfoFrame','chat',*getattr(self,'MOVIES',MOVIES)):
                (movies/(name+'.swf')).write_bytes(b'authored stub fixture')
            if real:
                movies=Path(os.environ['MU_NATIVE_DATA_DIR'])/'gfx';lib=Path(os.environ['MU_GFX_LIB'])
            run=subprocess.run([str(host),str(movies),str(lib)],capture_output=True,text=True,
                               env={**os.environ,'MU_WINDOWS4_REAL':'1' if real else '0'})
            if failing:
                self.assertNotEqual(run.returncode,0,'compiled mutant survived');return
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn(getattr(self,'EXPECTED','153 inert callbacks'),run.stdout)
            return {int(l.split()[1],16):l.split()[2] for l in run.stdout.splitlines() if l.startswith('route ')}

    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-C','native','-j2','build/libmunative.a'],cwd=ROOT,check=True,capture_output=True)

    def test_production_firewall_and_ordered_lifecycle(self):
        self.run_host()

    @unittest.skipUnless(PRIVATE and os.environ.get('MU_NATIVE_DATA_DIR') and os.environ.get('MU_GFX_LIB'),
                         'private original movies and Ruffle')
    def test_original_movies_empty_providers(self):
        self.run_host(real=True)

    @unittest.skipUnless(PRIVATE,'private pinned original instructions')
    def test_original_routes_and_sound_order(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        import pins
        import validate_npc as original
        machine=original.TalkMachine(pins.TEXT.read(),pins.DATA.read())
        native=self.run_host()
        cases={c['packet'][3]:c for c in original.talk_cases(random.Random(4),1)}
        for result,observed in native.items():
            with self.subTest(result=result):
                events=machine.run(cases[result])['events']
                trace=''
                for callee,owner,args in events:
                    if callee==0xac9c74:trace+='close,'
                    elif callee==original.VTABLE|0x40:trace+=f'{owner:x}:open,'
                    elif callee==0xaae767:trace+=f'{owner:x}:toggle,'
                    elif callee==0xa6ac96:trace+=f'sound{args[0]},'
                    # The selector-specific methods are bounded presentation
                    # openers; their non-presentation internals are not executed.
                    elif callee in (0xbd72a3,0xbd7408,0xbd709c):
                        trace+=f'{owner:x}:open,'
                self.assertEqual(observed,trace)


@unittest.skipUnless(os.environ.get('MU_UI_WINDOWS4_MUTANTS')=='1','changed-controller mutants once at lane finish')
class MutationSensitivity(unittest.TestCase):
    def test_compiled_mutants(self):
        import shutil
        windows=(ROOT/'native/gfx/mu_gfx_windows4.inc').read_text()
        npc=(ROOT/'native/core/mu_npc.c').read_text()
        mutants=[
            ('wrong-slot','{0x204,MU_GFX_ELEMENTAL_MIX,0}','{0x184,MU_GFX_ELEMENTAL_MIX,0}',False),
            ('wrong-movie','{0x204,MU_GFX_ELEMENTAL_MIX,0}','{0x204,MU_GFX_SOCKET_MIX,0}',False),
            ('lost-toggle','{0x1ac,MU_GFX_MUUN_EXCHANGE,1}','{0x1ac,MU_GFX_MUUN_EXCHANGE,0}',False),
            ('unready-open','if(!presentation_available3(L,r->movie)) return 0;','if(0) return 0;',False),
            ('forged-action','return !strcmp(name,"TweenTimeSet")','return 1 || !strcmp(name,"TweenTimeSet")',False),
            ('lost-close','mu_gfx_layer_show(w->L,w->id,0);','mu_gfx_layer_show(w->L,w->id,1);',False),
            ('enabled-exchange','presentation_set(L,m,"btnExchange.disabled","true");','presentation_set(L,m,"btnExchange.disabled","false");',True),
            ('sound-before-open','if (!n->ordered_window_sounds)\n            if (n->sound)','if (1)\n            if (n->sound)',False),
        ]
        with tempfile.TemporaryDirectory(prefix='mu-windows4-mutants-') as folder:
            mirror=Path(folder)/'repo';mirror.mkdir()
            for item in ROOT.iterdir():
                if item.name!='native':(mirror/item.name).symlink_to(item,target_is_directory=item.is_dir())
            (mirror/'native').mkdir()
            for dirname in ('gfx','core','tests'):
                (mirror/'native'/dirname).mkdir()
                for item in (ROOT/'native'/dirname).iterdir():
                    if item.name not in ('mu_gfx_windows4.inc','mu_npc.c'):
                        (mirror/'native'/dirname/item.name).symlink_to(item,target_is_directory=item.is_dir())
            for item in (ROOT/'native').iterdir():
                if item.name not in ('gfx','core','tests'):(mirror/'native'/item.name).symlink_to(item,target_is_directory=item.is_dir())
            for name,old,new,real in mutants:
                with self.subTest(mutant=name):
                    target=npc if name=='sound-before-open' else windows
                    self.assertEqual(target.count(old),1)
                    (mirror/'native/gfx/mu_gfx_windows4.inc').write_text(windows if name=='sound-before-open' else windows.replace(old,new))
                    (mirror/'native/core/mu_npc.c').write_text(npc.replace(old,new) if name=='sound-before-open' else npc)
                    PresentationWindows().run_host(real=real,build_root=mirror,failing=True)
