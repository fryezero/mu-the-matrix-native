"""MapName arrival banner: production controller, original open/update/owner comparisons, mutants."""
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from native.tests import test_ui_windows4 as harness

ROOT=harness.ROOT
NATIVE_OPEN='InitText,timer,SetMapName:Demotown,open,'


class Windows6(unittest.TestCase):
    HOST='native/tests/ui_windows6_host.c'
    MOVIES=('MapName','CommandWindow')
    EXPECTED='13 inert callbacks'
    setUpClass=classmethod(harness.PresentationWindows.setUpClass.__func__)

    def run_host(self,real=False,build_root=ROOT,failing=False):
        import subprocess
        with tempfile.TemporaryDirectory(prefix='mu-ui-windows6-') as folder:
            tmp=Path(folder);cc=os.environ.get('CC','cc')
            lib=tmp/('libmugfx.dylib' if sys.platform=='darwin' else 'libmugfx.so')
            subprocess.run([cc,'-std=c11','-O1','-shared','-fPIC',str(ROOT/'native/tests/gfx_stub_mugfx.c'),'-o',str(lib)],
                           check=True,capture_output=True)
            host=tmp/'host'
            sources=[self.HOST,'reconstructed/hud/tooltip_html.c','reconstructed/hud/inv_grid.c','reconstructed/hud/item_slots.c']
            subprocess.run([cc,'-std=c11','-O1','-I',str(build_root/'reconstructed/hud'),
                            *[str(build_root/p) for p in sources],str(ROOT/'native/build/libmunative.a'),
                            '-lm',*([] if sys.platform=='darwin' else ['-ldl']),'-o',str(host)],check=True,capture_output=True)
            movies=tmp/'movies';movies.mkdir()
            for name in ('main','InventoryFrame','InfoPopup','CharacterInfoFrame','chat',*self.MOVIES):
                (movies/(name+'.swf')).write_bytes(b'authored stub fixture')
            if real:
                movies=Path(os.environ['MU_NATIVE_DATA_DIR'])/'gfx';lib=Path(os.environ['MU_GFX_LIB'])
            run=subprocess.run([str(host),str(movies),str(lib)],capture_output=True,text=True,
                               env={**os.environ,'MU_WINDOWS4_REAL':'1' if real else '0'})
            routes={l.split()[1]:l.split()[2] for l in run.stdout.splitlines() if l.startswith('route ')}
            expected={'1':NATIVE_OPEN,'close':'close,','teleport0':'none,','teleport':NATIVE_OPEN,
                      'respawn':NATIVE_OPEN.replace(',open,',','),'close2':'close,','refused':'none,',
                      'held':NATIVE_OPEN.replace('Demotown','Newtown'),'overlay':'close,'+NATIVE_OPEN,'inert':'none,'}
            if failing:
                # A mutant is caught by a host assertion or by a differing invoke trace.
                survived=run.returncode==0 and routes==expected and 'lifetime 5000\n' in run.stdout
                self.assertFalse(survived,'compiled mutant survived');return None
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn(self.EXPECTED,run.stdout)
            self.assertIn('lifetime 5000\n',run.stdout)
            self.assertEqual(routes,expected)
            if not real:self.assertIn('pointer checked\n',run.stdout)
            return routes

    def test_production_controller(self):self.run_host()

    @unittest.skipUnless(harness.PRIVATE and os.environ.get('MU_NATIVE_DATA_DIR') and os.environ.get('MU_GFX_LIB'),
                         'private original movie and Ruffle')
    def test_original_movie(self):self.run_host(real=True)


@unittest.skipUnless(harness.PRIVATE,'private pinned original instructions')
class OriginalBanner(unittest.TestCase):
    """The original open, update and three owner tails, executed with every service stubbed."""
    THIS=0x10000100;NAME=0x10003000;STRIFE=0x10003100;GUILD=0x10003200;WORLD=0x1cf15fc

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,str(ROOT/'scripts'))
        import pins
        cls.text=pins.TEXT.read();cls.data=pins.DATA.read()

    def machine(self,entry,stop,services,writes=(),inside=()):
        from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EIP
        u=Uc(UC_ARCH_X86,UC_MODE_32)
        u.mem_map(0,0x1000)                                    # fs:[0] of the frame prologue
        u.mem_map(0x401000,(len(self.text)+4095)&~4095);u.mem_write(0x401000,self.text)
        u.mem_map(0x1a7c000,0x284000);u.mem_write(0x1a7c000,self.data)   # image data and its zero-filled tail
        u.mem_map(0x10000000,0x10000)
        u.reg_write(UC_X86_REG_ESP,0x10008000);u.reg_write(UC_X86_REG_EBP,0x1000f000)
        u.reg_write(UC_X86_REG_ECX,self.THIS)
        u.mem_write(0x10008000,struct.pack('<I',0xdead0000))   # return address of a whole-method run
        for a,v in [(self.THIS,0x10001000),(0x10001040,0x10002000),(0x10001044,0x10002010),*writes]:
            try:u.mem_write(a,v if isinstance(v,bytes) else struct.pack('<I',v))
            except Exception:                                  # a global outside the mapped image
                u.mem_map(a&~0xfff,0x1000);u.mem_write(a,v if isinstance(v,bytes) else struct.pack('<I',v))
        calls=[]
        def hook(uc,a,size,data):
            if a==stop or a==0xdead0000:
                uc.emu_stop();return
            if a in services:
                value,pop=services[a](uc,calls)
                sp=uc.reg_read(UC_X86_REG_ESP);ret=struct.unpack('<I',uc.mem_read(sp,4))[0]
                uc.reg_write(UC_X86_REG_EAX,value);uc.reg_write(UC_X86_REG_ESP,sp+4+pop)
                uc.reg_write(UC_X86_REG_EIP,ret)
            elif not (entry<=a<stop or any(lo<=a<hi for lo,hi in inside)):
                self.fail(f'unmodeled banner service {a:#x}')
        u.mem_map(0xdead0000,0x1000)
        u.hook_add(UC_HOOK_CODE,hook);u.emu_start(entry,0,count=20000)
        return calls,u

    @staticmethod
    def cstring(u,a):
        return bytes(u.mem_read(a,96)).split(b'\0')[0].decode('ascii')

    def open_method(self,world,strife,guild):
        from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX
        cstring=self.cstring
        def arg(u,i):return struct.unpack('<I',u.mem_read(u.reg_read(UC_X86_REG_ESP)+4+4*i,4))[0]
        def const(v,pop=0):return lambda u,c:(v,pop)
        def this(u,c):return (u.reg_read(UC_X86_REG_ECX),0)
        def invoke(u,c):
            self.assertEqual(arg(u,0),self.THIS)
            method=cstring(u,arg(u,1));fmt=cstring(u,arg(u,2))
            self.assertIn(fmt,('','%s'))
            c.append(method+(':'+cstring(u,arg(u,3)) if fmt else ''));return (0,0)
        def timer(u,c):
            self.assertEqual(u.reg_read(UC_X86_REG_ECX),self.THIS+0x78);c.append('timer');return (0,0)
        def memset(u,c):u.mem_write(arg(u,0),bytes([arg(u,1)&255])*arg(u,2));return (arg(u,0),0)
        def name(u,c):
            self.assertEqual(arg(u,0),world);return (self.NAME,0)
        def strcat(u,c):
            dst=arg(u,0);u.mem_write(dst+len(cstring(u,dst)),cstring(u,arg(u,1)).encode()+b'\0');return (dst,0)
        def strlen(u,c):return (len(cstring(u,arg(u,0))),0)
        def rand(u,c):c.append('rand');return (0x20,0)
        def from_chars(u,c):
            ecx=u.reg_read(UC_X86_REG_ECX);u.mem_write(ecx,struct.pack('<I',arg(u,0)));return (ecx,4)
        def assign(u,c):
            u.mem_write(arg(u,0),bytes(u.mem_read(arg(u,1),4)));return (arg(u,0),0)
        def chars(u,c):
            return (struct.unpack('<I',u.mem_read(u.reg_read(UC_X86_REG_ECX),4))[0],0)
        def is_strife(u,c):
            self.assertEqual(arg(u,0),world);return (strife,0)
        def text(u,c):
            self.assertEqual((u.reg_read(UC_X86_REG_ECX),arg(u,0)),(0x6fbab48,0xbac));return (self.STRIFE,4)
        def empty(u,c):
            self.assertEqual(u.reg_read(UC_X86_REG_ECX),self.THIS+0xac);return (0 if guild else 1,0)
        def base_open(u,c):
            self.assertEqual(u.reg_read(UC_X86_REG_ECX),self.THIS);c.append('open');return (0,0)
        calls,u=self.machine(0xbaee4a,0xbaf100,{
            0xaae7e0:invoke,0x11865d8:timer,0x8e6d00:this,0x194cd00:memset,0x16baaa6:name,0x1983a90:strcat,
            0x195a4b0:strlen,0x1989721:rand,0x94997e:from_chars,0xa99d93:assign,0x8e83a0:const(0),0x8e7940:chars,
            0x16bec9f:is_strife,0x95f027:text,0x8e53e0:empty,0xaae420:base_open},
            [(self.WORLD,world),(self.THIS+0xa8,0xffff),(self.THIS+0xac,self.GUILD),
             (self.NAME,b'Demotown\0'),(self.STRIFE,b'Strife\0'),(self.GUILD,b'Demoguild\0')])
        saved=struct.unpack('<H',u.mem_read(self.THIS+0xa8,2))[0]
        return calls,saved

    def test_open_method_against_the_native_provider(self):
        native=Windows6().run_host()
        cases=0
        for world in (0,3,0x27,0x29,0x70):
            calls,saved=self.open_method(world,0,False)
            # The letter loop calls rand() once per letter; its store was removed, so the name is unchanged.
            self.assertEqual(calls.count('rand'),8)
            self.assertEqual(','.join(c for c in calls if c!='rand')+',',native['teleport'])
            self.assertEqual(saved,world);cases+=1
        # What the offline provider leaves out: the strife line and the occupying guild.
        for strife in (0,1):
            for guild in (False,True):
                calls,_=self.open_method(3,strife,guild)
                expected=['InitText','timer','SetMapName:Demotown']+(['SetStrife:Strife'] if strife else [])+\
                         (['SetOccupyGuild:Demoguild'] if guild else [])+['open']
                self.assertEqual([c for c in calls if c!='rand'],expected);cases+=1
        calls,saved=self.open_method(0x28,1,True)
        self.assertEqual((calls,saved),([],0xffff));cases+=1
        self.assertEqual(cases,10)

    def test_update_closes_at_five_seconds(self):
        from unicorn.x86_const import UC_X86_REG_ECX
        cases=0
        for loaded in (0,1):
            for opened in (0,1):
                for elapsed in (0,4960,4999,5000,5001,60000):
                    now=[100000+elapsed]
                    def ticks(u,c):return (now[0],0)
                    def is_open(u,c):return (opened,0)
                    def is_loaded(u,c):
                        self.assertEqual(u.reg_read(UC_X86_REG_ECX),self.THIS+8);return (loaded,0)
                    def close(u,c):c.append('close');return (0,0)
                    calls,u=self.machine(0xbaf120,0xbaf183,{
                        0x10004000:ticks,0xab03cf:is_loaded,0xaae6f9:is_open,0x10002010:close},
                        [(0x1a7c9a4,0x10004000),(0x1cf6610,0x20),(self.THIS+0x78+8,0),(self.THIS+0x78+0xc,100000)],
                        inside=((0x11865d8,0x1186683),(0x191c350,0x191c3a0)))
                    restarted=struct.unpack('<I',u.mem_read(self.THIS+0x78+0xc,4))[0]
                    due=loaded and opened and elapsed>=5000
                    self.assertEqual(calls,['close'] if due else [])
                    self.assertEqual(restarted,100000+elapsed if due else 100000);cases+=1
        self.assertEqual(cases,24)

    def test_three_owner_tails(self):
        from unicorn.x86_const import UC_X86_REG_ECX
        native=Windows6().run_host()
        def const(v,pop=0):return lambda u,c:(v,pop)
        def manager(u,c):return (0x10000700,0)
        def opened(u,c):
            self.assertEqual(u.reg_read(UC_X86_REG_ECX),self.THIS);c.append('128:open');return (0,0)
        window=[(0x10000700+0x128,self.THIS)]
        # Teleport answer 0x0128136d: manager close-all, legacy close-all, then the banner for a numbered answer.
        for number in (0,1,17,0xffff):
            def close_all(u,c):c.append('close-all');return (0,0)
            def legacy(u,c):c.append('legacy-close');return (0,0)
            calls,_=self.machine(0x1281d8b,0x1281eab,{
                0xac3bf7:manager,0xac9c74:close_all,0xf2bb92:const(0x10000800),0xf2b53d:legacy,
                0xf2c102:const(0x10000900),0xef00ff:const(0,4),0xc92a29:const(0),0xcfc94a:const(0x10000a00,4),
                0x13c0eaa:const(0),0x138fe69:const(0),0x10002000:opened},
                window+[(0x1000f000-0x14,0x10000b00),(0x1000f000-0x10,0x10000c00),(0x10000b04,number),(0xa39d754,0x10000d00),
                        (0x1ec3254,1),(0xb478014,1)])   # two globals the tail clears
            self.assertEqual(calls,['close-all','legacy-close']+(['128:open'] if number else []))
            self.assertEqual('none,' if not number else NATIVE_OPEN,native['teleport' if number else 'teleport0'])
        # Respawn answer 0x0127bd9e and join answer 0x0124cc64: the open is unconditional on the tail.
        calls,_=self.machine(0x127c539,0x127c56a,{0xac3bf7:manager,0x10002000:opened},window)
        self.assertEqual(calls,['128:open'])
        for flag in (0,1):
            calls,_=self.machine(0x124e07a,0x124e161,{0xac3bf7:manager,0x10002000:opened},
                                 window+[(0x1000f000-0x44,flag)])
            self.assertEqual(calls,['128:open'])


@unittest.skipUnless(os.environ.get('MU_UI_WINDOWS6_MUTANTS')=='1','changed-controller mutants once at finish')
class MutationSensitivity(unittest.TestCase):
    def test_compiled_mutants(self):
        six='native/gfx/mu_gfx_windows6.inc';layer='native/gfx/mu_gfx_layer.c'
        four='native/gfx/mu_gfx_windows4.inc';base='native/gfx/mu_gfx_windows.inc'
        mutants=[
            ('short-lifetime',six,'#define MAP_BANNER_LIFETIME_MS 5000.0','#define MAP_BANNER_LIFETIME_MS 4960.0',False),
            ('late-close',six,'L->map_banner_start_ms>=MAP_BANNER_LIFETIME_MS','L->map_banner_start_ms>MAP_BANNER_LIFETIME_MS',False),
            ('no-restart',six,'    L->map_banner_start_ms=L->time_ms;            /* 0x00baee94 */','    if(!w->open) L->map_banner_start_ms=L->time_ms;            /* 0x00baee94 */',False),
            ('world-40',six,'    if(world==0x28) return 0;                     /* open method, 0x00baee6b */\n','',False),
            ('unnumbered-teleport',six,'if(kind==MU_GFX_ARRIVAL_TELEPORT && !number) return 0;','if(0) return 0;',False),
            ('lost-init-text',six,'    invokef(L,w->id,w->path,"InitText","[]");\n','',False),
            ('timer-after-name',six,'    json_quote(q,sizeof q,name);\n    invokef(L,w->id,w->path,"SetMapName","[%s]",q);\n','    json_quote(q,sizeof q,name);\n    invokef(L,w->id,w->path,"SetMapName","[%s]",q);\n    logf_(L,"%s lifetime timer start",w->file);\n',False),
            ('invented-strife',six,'    mu_gfx_layer_show(L,w->id,1);                 /* 0x00baf0e2 */','    invokef(L,w->id,w->path,"SetStrife","[\\"Strife\\"]");\n    mu_gfx_layer_show(L,w->id,1);                 /* 0x00baf0e2 */',True),
            ('invented-sound',six,'    mu_gfx_layer_show(L,w->id,1);                 /* 0x00baf0e2 */','    if(L->cfg.window_sound) L->cfg.window_sound(L->cfg.tooltip_user,25,0xc716f6);\n    mu_gfx_layer_show(L,w->id,1);                 /* 0x00baf0e2 */',False),
            ('dropped-hold',six,'        L->map_banner_pending=1;\n','        L->map_banner_pending=0;\n',False),
            ('stale-hold',six,'        snprintf(L->map_banner_name,sizeof L->map_banner_name,"%s",name);\n','        if(!L->map_banner_name[0]) snprintf(L->map_banner_name,sizeof L->map_banner_name,"%s",name);\n',False),
            ('forged-close',six,'    return !strcmp(name,"TweenTimeSet") || !strcmp(name,"requestWindowPos");','    return -1;',False),
            ('forged-action',six,'    return !strcmp(name,"TweenTimeSet") || !strcmp(name,"requestWindowPos");','    return 1;',False),
            ('escape-closes',base,'presentation_movie(L->order[i]) && !presentation_overlay6(L->order[i]) &&','presentation_movie(L->order[i]) &&',False),
            ('npc-close-all',four,'        if(!presentation_overlay6(m)) mu_gfx_layer_show(L,m,0);','        mu_gfx_layer_show(L,m,0);',False),
            ('pointer-press',layer,'        if (presentation_overlay6(stack[i]))\n            continue;\n','',False),
            ('pointer-hover',layer,'if (inside && !over && !presentation_overlay6(stack[i]) && L->api.hit_test','if (inside && !over && L->api.hit_test',False),
        ]
        sources={name:(ROOT/name).read_text() for name in (six,layer,four,base)}
        with tempfile.TemporaryDirectory(prefix='mu-windows6-mutants-') as folder:
            mirror=Path(folder)/'repo';mirror.mkdir()
            for item in ROOT.iterdir():
                if item.name!='native':(mirror/item.name).symlink_to(item,target_is_directory=item.is_dir())
            (mirror/'native').mkdir();(mirror/'native/gfx').mkdir();(mirror/'native/tests').mkdir()
            for item in (ROOT/'native').iterdir():
                if item.name not in ('gfx','tests'):(mirror/'native'/item.name).symlink_to(item,target_is_directory=item.is_dir())
            (mirror/'native/tests/ui_windows6_host.c').write_text((ROOT/'native/tests/ui_windows6_host.c').read_text())
            # Copies, not links: a quoted include resolves beside the including file.
            for item in (ROOT/'native/gfx').iterdir():
                target=mirror/'native/gfx'/item.name
                if item.is_dir():target.symlink_to(item,target_is_directory=True)
                else:target.write_bytes(item.read_bytes())
            only=os.environ.get('MU_UI_WINDOWS6_MUTANT_ONLY')
            for name,file,old,new,real in mutants:
                if only and name not in only.split(','):continue
                with self.subTest(mutant=name):
                    self.assertEqual(sources[file].count(old),1)
                    for path,normal in sources.items():
                        (mirror/path).write_text(normal.replace(old,new) if path==file else normal)
                    Windows6().run_host(real=real,build_root=mirror,failing=True)
