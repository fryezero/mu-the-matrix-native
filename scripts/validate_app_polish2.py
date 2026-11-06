#!/usr/bin/env python3
"""APP-POLISH-002: intact setHPMP body versus the production session getter and HUD adapter.

The entry jump at c71772 is opaque. Enter at c717d4 with the toxic flag false;
stop before the exception epilogue. Execute getters, cache comparison/copy and
property construction. GFx object operations are recording boundaries.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import pins
FIELDS = ('hp','maxHp','mp','maxMp','Shield','ShieldMax','SkillMana','SkillManaMax')

def function(path, signature):
    text = (ROOT/path).read_text()
    start = text.index(signature)
    return text[start:text.index('\n}',start)+2]

def native(work, mutation=None):
    import validate_gfx3 as gfx
    gfx.layer_log(work)  # portable movies and recording libmugfx
    getter = function('native/session/domains/hero.c','void mu_session_hero(')
    sync = function('native/world/world_gfx.c','static void vitals_sync(')
    if mutation and mutation[0] != 'demo':
        old,new=mutation
        assert old in sync
        sync=sync.replace(old,new)
    subprocess.run([sys.executable,str(ROOT/'scripts/gen_layout.py'),'--out',str(work/'gen')],check=True,capture_output=True)
    import re
    demo = re.search(r'\.demo\s*=\s*(\d+)', (ROOT/'native/world/world_gfx.c').read_text()).group(1)
    if mutation and mutation[0]=='demo': demo=mutation[1]
    source = '''#include <stdio.h>
#include <string.h>
#include "native/session/domains/hero.h"
#include "native/session/domains/hero_state.h"
#include "native/gfx/mu_gfx_layer.h"
#include "native/core/mu_progress.h"
struct mu_session { mu_dom_hero hero; };
typedef struct {mu_session *session; mu_gfx_layer *layer; mu_progress *progress;} world_gfx;
static mu_progress_view fallback;
void mu_progress_get_view(const mu_progress *p,mu_progress_view *v){(void)p;*v=fallback;}
'''
    source += function('reconstructed/progress/progress_calc.c','int32_t mu_prg_master_level(')+'\n'
    source += function('reconstructed/progress/progress_bar.c','int32_t mu_prg_class_stage(')+'\n'+getter+'\n'+sync
    source += '''
static mu_session s;
static world_gfx g;
int init(const char *movies,const char *lib) {
 char error[512]; mu_gfx_layer_config cfg={.movie_dir=movies,.lib_path=lib,.width=1504,.height=936};
 g.session=&s; g.layer=mu_gfx_layer_open(&cfg,error,sizeof error); return g.layer!=NULL;
}
int32_t *probe(int cls,const int32_t *words) {
 static int32_t out[8];
 memset(&s,0,sizeof s);s.hero.record[0x12]=(uint8_t)cls;s.hero.attr[0x187]=(uint8_t)cls;
 const int offsets[12]={0x68,0x6c,0x70,0x74,0x78,0x7c,0x80,0x84,0x40,0x44,0x48,0x4c};
 for(int i=0;i<12;i++)memcpy(s.hero.attr+offsets[i],words+i,4);
 vitals_sync(&g); mu_gfx_layer_advance(g.layer,40);
 const mu_gfx_hero *h=mu_gfx_layer_hero(g.layer);
 out[0]=h->hp;out[1]=h->max_hp;out[2]=h->mp;out[3]=h->max_mp;
 out[4]=h->sd;out[5]=h->max_sd;out[6]=h->ag;out[7]=h->max_ag;return out;
}
void set_fallback(int on) { g.progress=on?(mu_progress *)&fallback:NULL;
 fallback.life_max=1100;fallback.mana_max=200;fallback.shield_max=52;fallback.ag_max=25; }
int32_t *stage(int w,int h) {static int32_t out[2];mu_gfx_layer_resize(g.layer,w,h);
 mu_gfx_layer_stage_size(g.layer,out,out+1);return out;}
void finish(void){mu_gfx_layer_close(g.layer);}
'''
    source=source.replace('.width=1504', '.demo='+demo+',.width=1504')
    c=work/'probe.c';c.write_text(source)
    lib=work/'probe.so'
    subprocess.run([os.environ.get('CC','cc'),'-std=c11','-O1','-shared','-fPIC','-DMU_GFX_NO_GL',
        '-I',str(ROOT),'-I',str(ROOT/'reconstructed/hud'),'-I',str(work/'gen'),str(c),str(ROOT/'native/gfx/mu_gfx_layer.c'),
        *[str(ROOT/'reconstructed/hud'/x) for x in ('inv_grid.c','item_slots.c','tooltip_html.c')],'-lm',
        *([] if sys.platform=='darwin' else ['-ldl']),'-o',str(lib)],check=True,capture_output=True)
    dll=ctypes.CDLL(str(lib));dll.init.argtypes=[ctypes.c_char_p]*2
    stub=next(work.glob('libmugfx_stub.*'))
    assert dll.init(os.fsencode(work/'movies'),os.fsencode(stub))
    dll.probe.argtypes=[ctypes.c_int,ctypes.POINTER(ctypes.c_int32)];dll.probe.restype=ctypes.POINTER(ctypes.c_int32)
    def probe(cls,words):return dict(zip(FIELDS,list(dll.probe(cls,(ctypes.c_int32*12)(*words))[:8])))
    dll.stage.argtypes=[ctypes.c_int]*2;dll.stage.restype=ctypes.POINTER(ctypes.c_int32)
    probe.stage=lambda w,h:list(dll.stage(w,h)[:2])
    probe.fallback=dll.set_fallback
    probe.close=dll.finish
    return probe

def original(text,data):
    import client_ui_machine as cm
    import validate_gfx3 as gfx
    m=gfx.machine(text,data);v=gfx.Values(m,text);v.install()
    m.allow((0xc717d4,0xc719db))
    gfx.allow_functions(m,text,0x139d8ea,0x139cb15,0xa0020f,0xa00232,0xa00255,0xa00278,
        0x96168c,0xc745c1,0xc745df,0xc745ee,0x96167d,0x96169b,0xc745d0,0x9616ba,0xc73fb6,0xc73eae)
    m.stub(0xaecd73,lambda mm: v.nodes[mm.args(3)[0]].update({v.cstr(mm.args(3)[1]):bool(mm.args(3)[2])}),12)
    def stop(mm):
        mm.uc.reg_write(cm.UC_X86_REG_EIP,cm.RETURN_SENTINEL);return cm.REDIRECT
    m.stub(0xc719db,stop);m.stub(0xc719e8,stop)
    def probe(cls,words):
        m.reset();v.invokes.clear();v.nodes.clear()
        hero=m.alloc(0x400,define=True);attr=m.alloc(0x1000,define=True);handler=m.alloc(0x400,define=True)
        m.write(hero+0x12,bytes([cls]));m.put32(0xa39d754,hero);m.put32(0x1d1df1c,attr)
        for off,value in zip((0x68,0x6c,0x70,0x74,0x78,0x7c,0x80,0x84,0x40,0x44,0x48,0x4c),words):m.put32(attr+off,value)
        # Make the cache distinct from every generated case, including all zeros.
        m.write(handler+0x22c,bytes([1]))
        def enter(mm):
            ebp=cm.STACK_BASE+0x10000
            mm.write(ebp-0x80,bytes(0x80));mm.put32(ebp-0x10,handler)
            mm.uc.reg_write(cm.UC_X86_REG_EBP,ebp);mm.uc.reg_write(cm.UC_X86_REG_ESP,ebp-0x100)
            mm.uc.reg_write(cm.UC_X86_REG_EIP,0xc717d4);return cm.REDIRECT
        m.stub(0x8e0480,enter);m.call(0x8e0480)
        assert len(v.invokes)==1 and v.invokes[0][0]=='setHPMP',v.invokes
        m.call(0x8e0480)
        assert len(v.invokes)==1, "unchanged cache invoked again"
        result=dict(v.invokes[0][1]);assert result.pop('isToxic') is False
        return result
    return probe

MUTANTS=[(f'h.{a} = v.{a};',f'h.{a} = v.{b};') for a,b in
         [('hp','max_hp'),('max_hp','hp'),('mp','hp'),('max_mp','max_hp'),('sd','ag'),('max_sd','max_ag'),('ag','sd'),('max_ag','max_sd')]] + [('mu_session_hero(g->session, &v);','mu_session_hero(NULL, &v);'),('demo','1')]

def original_viewport(text,data,width,height):
    import validate_gfx3 as gfx
    import client_ui_machine as cm
    m=gfx.machine(text,data)
    gfx.allow_functions(m,text,0xaef36d)
    m.put32(gfx.SCREEN_W,width);m.put32(gfx.SCREEN_H,height)
    m.stub(0xab03cf,lambda _:1,cm.stdcall_cleanup(text,0xab03cf))
    m.stub(0xab041b,lambda _:0x30000100,cm.stdcall_cleanup(text,0xab041b))
    words=[]
    m.stub(0xab0d72,lambda mm: words.extend(mm.args(7)),cm.stdcall_cleanup(text,0xab0d72))
    m.call(0xaef36d,ecx=m.alloc(0x400,define=True))
    return words

def run(args):
    start=time.monotonic();text=pins.TEXT.read(args.text);data=pins.DATA.read(args.data)
    # Pin the requested third-section input even though this routine's dynamic globals are synthetic.
    pins.SECTION3.read(args.section3)
    client=original(text,data);rng=random.Random(20261105)
    cases=[(i%256,[rng.randrange(0,2000000) for _ in range(12)]) for i in range(args.cases)]
    expected=[client(c,w) for c,w in cases]
    viewports=[(800,600),(1280,800),(1504,936),(1722,1048)]
    with tempfile.TemporaryDirectory() as tmp:
        p=native(Path(tmp));assert all(p(c,w)==e for (c,w),e in zip(cases,expected))
        for w,h in viewports:
            assert original_viewport(text,data,w,h)==[w,h,0,0,*p.stage(w,h),0]
        p.close()
    caught=[]
    if args.mutants:
        for i,mutation in enumerate(MUTANTS):
            with tempfile.TemporaryDirectory() as tmp:
                p=native(Path(tmp),mutation)
                assert any(p(c,w)!=e for (c,w),e in zip(cases[:20],expected[:20])),mutation
                p.close();caught.append(i+1)
    return {'cases':len(cases)+len(viewports),'vital_cases':len(cases),'viewport_cases':len(viewports),'mismatches':0,'mutants_caught':caught,'equivalent':0,'wall_seconds':round(time.monotonic()-start,3)}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('text','data','section3'):ap.add_argument('--'+name)
    ap.add_argument('--cases',type=int,default=1024);ap.add_argument('--mutants',action='store_true');ap.add_argument('--out',type=Path)
    args=ap.parse_args();report=run(args);print(json.dumps(report))
    if args.out:args.out.write_text(json.dumps(report,indent=2)+'\n')
