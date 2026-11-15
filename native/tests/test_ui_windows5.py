"""Table-driven provider/firewall and original instruction comparisons."""
import os
from pathlib import Path
import random
import sys
import unittest
from native.tests import test_ui_windows4 as harness

ROOT=harness.ROOT

class Windows5(unittest.TestCase):
    HOST='native/tests/ui_windows5_host.c'
    MOVIES=('PersonalShop','ArtifactFrame','DuelWatch','MUMix','MixGoblinSel','MixInventoryFrame')
    EXPECTED='88 inert callbacks'
    run_host=harness.PresentationWindows.run_host
    setUpClass=classmethod(harness.PresentationWindows.setUpClass.__func__)

    def test_production_controllers(self):self.run_host()

    @unittest.skipUnless(harness.PRIVATE,'private original movies')
    def test_original_movies(self):self.run_host(real=True)

    @unittest.skipUnless(harness.PRIVATE,'private original instructions')
    def test_original_routes(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        import pins
        import validate_npc as original
        from native.tests.test_ui_windows3 import OriginalRoutes
        native=self.run_host()
        machine=original.TalkMachine(pins.TEXT.read(),pins.DATA.read())
        for result in (0x30,0x21):
            case=next(c for c in original.talk_cases(random.Random(4),1) if c['packet'][3]==result)
            events=machine.run(case)['events'];trace=''
            for callee,owner,args in events:
                if callee==0xac9c74:trace+='close,'
                elif callee==0xaae767:trace+=f'{owner:x}:toggle,'
                elif callee==0xb54793:trace+=f'{owner:x}:open,'
                elif callee==0xa6ac96:trace+=f'sound{args[0]},'
            self.assertEqual(native[result],trace)
        # Execute the exact artifact callback arm with a manager and getter stub.
        oracle=OriginalRoutes();oracle.text=pins.TEXT.read()
        calls=oracle.machine(0xb97ed1,0xb97ee4,{
            0xac3bf7:lambda u,c:(0x10000700,0),
            0x981423:lambda u,c:(0x10000100,0),
            0xaae767:lambda u,c:(c.append('280:toggle,') or 0,0)})
        self.assertEqual(native[0x280],''.join(calls))

        tail=oracle.machine(0xb548ef,0xb548f7,{
            0xaae420:lambda u,c:(c.append('e0:open,') or 0,0)},
            [(0x1000efe4,0x10000100)])
        self.assertEqual(tail,['e0:open,'])
        mix=oracle.machine(0xbd07e8,0xbd080f,{
            0xac3bf7:lambda u,c:(0x10000700,0),0xa98c22:lambda u,c:(0x10000100,0),
            0x10002000:lambda u,c:(c.append('290:open,') or 0,0),
            0x10002010:lambda u,c:(c.append('selector:close,') or 0,0)},
            [(0x1000efe4,0x10000100)])
        self.assertEqual(native[0x290],''.join(mix))

@unittest.skipUnless(os.environ.get('MU_UI_WINDOWS5_MUTANTS')=='1','changed-controller mutants once at finish')
class MutationSensitivity(unittest.TestCase):
    def test_compiled_mutants(self):
        import tempfile
        source=ROOT/'native/gfx/mu_gfx_windows5.inc';normal=source.read_text()
        mutants=[
            ('wrong-slot','{0x164,MU_GFX_PERSONAL_CATALOG,1}','{0x184,MU_GFX_PERSONAL_CATALOG,1}',False),
            ('wrong-movie','{0x164,MU_GFX_PERSONAL_CATALOG,1}','{0x164,MU_GFX_ARTIFACT,1}',False),
            ('wrong-open-kind','if(r->toggle) mu_gfx_layer_toggle(L,r->movie);','if(0) mu_gfx_layer_toggle(L,r->movie);',False),
            ('unready','if(!presentation_available3(L,r->movie)) return 0;','if(0) return 0;',False),
            ('lost-close','mu_gfx_layer_show(w->L,w->id,0);','mu_gfx_layer_show(w->L,w->id,1);',False),
            ('forged-action','return !strcmp(name,"TweenTimeSet")','return 1 || !strcmp(name,"TweenTimeSet")',False),
            ('hidden-parent','if(w->open) (void)presentation_slot5','if(1) (void)presentation_slot5',False),
            ('invented-sound','        if(r->toggle) mu_gfx_layer_toggle','        if(L->cfg.window_sound) L->cfg.window_sound(L->cfg.tooltip_user,25,0xc716f6);\n        if(r->toggle) mu_gfx_layer_toggle',False),
            ('disabled-tabs','presentation_set(L,m,"btnItemList.enabled","true");','presentation_set(L,m,"btnItemList.enabled","false");',True),
            ('mix-branch','v[0]==1 && !w->L->mv[MU_GFX_MIX].open','v[0]==0 && !w->L->mv[MU_GFX_MIX].open',False),
            ('enabled-watch','[%d,\\"No match\\",true]','[%d,\\"No match\\",false]',True),
        ]
        with tempfile.TemporaryDirectory(prefix='mu-windows5-mutants-') as folder:
            mirror=Path(folder)/'repo';mirror.mkdir()
            for item in ROOT.iterdir():
                if item.name!='native':(mirror/item.name).symlink_to(item,target_is_directory=item.is_dir())
            (mirror/'native').mkdir();(mirror/'native/gfx').mkdir()
            for item in (ROOT/'native').iterdir():
                if item.name not in ('gfx','tests'):(mirror/'native'/item.name).symlink_to(item,target_is_directory=item.is_dir())
            (mirror/'native/tests').mkdir()
            (mirror/'native/tests/ui_windows5_host.c').write_text((ROOT/'native/tests/ui_windows5_host.c').read_text())
            for item in (ROOT/'native/gfx').iterdir():
                if item.name!=source.name:
                    target=mirror/'native/gfx'/item.name
                    if item.is_dir():target.symlink_to(item,target_is_directory=True)
                    else:target.write_bytes(item.read_bytes())
            for name,old,new,real in mutants:
                if os.environ.get('MU_UI_WINDOWS5_MUTANT_ONLY') and name!=os.environ['MU_UI_WINDOWS5_MUTANT_ONLY']:continue
                with self.subTest(mutant=name):
                    self.assertEqual(normal.count(old),1)
                    (mirror/'native/gfx'/source.name).write_text(normal.replace(old,new))
                    Windows5().run_host(real=real,build_root=mirror,failing=True)
