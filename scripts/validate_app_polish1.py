#!/usr/bin/env python3
"""APP-POLISH-001: character shadow policy and Warps window size against pinned x86.

The production character-shadow function is compiled verbatim with a recording
shadow_with boundary. No copy of its world/alpha rules lives in this harness.
The original caller is entered with a synthetic frame at 0x0176cfab. Model draw,
actor predicates and GL state helpers are recorded boundaries; world predicates
execute. Covers ordinary visible, unbuffed parts, not every RenderPartObject gate.
Warps uses the existing GFx native host and original window creator. A separate
SetWindowSize call records all seven viewport words before the GFx SDK boundary.
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


def source_function(signature):
    text = (ROOT/'native/core/mu_particles.c').read_text()
    start = text.index(signature)
    end = text.index('\n}', start) + 2
    return text[start:end]


def shadow_source():
    return source_function('int32_t mu_world_particles_character_shadow(')


def native_shadow(work, mutation=None):
    body = shadow_source()
    if mutation:
        old, new = mutation
        assert old in body
        body = body.replace(old, new)
    source = '''#include <stdint.h>
#include "mu_particles.h"
static float result[7];
static int32_t shadow_with(mu_world_particles *p, const mu_model *m, const mu_bmd *b,
 const float rgba[4], int32_t state, int32_t z, const mu_render_backend *backend) {
 (void)p; (void)m; (void)b; (void)backend;
 result[0]=1; result[1]=(state==MU_PT_STATE_ALPHA); result[2]=z;
 for(int i=0;i<4;i++) result[3+i]=rgba[i];
 return 1;
}
''' + body + '\n' + source_function('static void apply_state(') + '''
int *probe_state(int alpha, int bits) {
 static int out[4]; mu_meshdraw_state s={0};
 s.blend=bits&1; s.depth_mask=(bits>>1)&1; s.alpha_test=(bits>>2)&1; s.texture=(bits>>3)&1;
 apply_state(&s, alpha ? MU_PT_STATE_ALPHA : MU_PT_STATE_OPAQUE, 1);
 apply_state(&s, MU_PT_STATE_UNTEXTURED, 0); apply_state(&s, MU_PT_STATE_DEPTH_OFF, 0);
 out[0]=s.blend; out[1]=s.depth_mask; out[2]=s.alpha_test; out[3]=s.texture;
 return out;
}
float *probe(int world) {
 for(int i=0;i<7;i++) result[i]=0;
 mu_world_particles p={0}; p.world=world;
 mu_world_particles_character_shadow(&p, 0, 0, 0);
 return result;
}
'''
    c = work/'shadow.c'; c.write_text(source)
    lib = work/('shadow.dylib' if sys.platform == 'darwin' else 'shadow.so')
    subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-O1', '-shared', '-fPIC',
                    '-I', str(ROOT/'native/core'), str(c), '-o', str(lib)], check=True, capture_output=True)
    dll = ctypes.CDLL(str(lib)); dll.probe.argtypes = [ctypes.c_int]; dll.probe.restype = ctypes.POINTER(ctypes.c_float)
    def probe(world): return list(dll.probe(world)[:7])
    dll.probe_state.argtypes = [ctypes.c_int, ctypes.c_int]
    dll.probe_state.restype = ctypes.POINTER(ctypes.c_int)
    probe.state = lambda alpha,bits: list(dll.probe_state(alpha,bits)[:4])
    return probe


def shadow_machine(text, data):
    import client_ui_machine as cm
    import validate_gfx3 as gfx
    m = cm.Machine(text, data)
    m.allow((0x0176cfab, 0x0176d160))
    gfx.allow_functions(m, text, 0x016a88ae, 0x016a8325, 0x009b0418, 0x00e136f3)
    # Ordinary visible character part: no event suppression, buff 0x12 or special model.
    m.stub(0x009a6ef3, lambda _: 0x30001000)
    m.stub(0x009a645f, lambda _: 0)
    m.stub(0x01295ade, lambda _: 0, 4)
    m.stub(0x01807c1f, lambda _: 0)
    return m


def original_shadow(m, world):
    import client_ui_machine as cm
    m.reset()
    m.put32(0x01cf15fc, world)
    obj = m.alloc(0x400, define=True)
    m.write(obj+3, bytes([1, 1])); m.put32(obj+0x68, -1); m.put32(obj+0x74, -1)
    result = [0.0]*7
    state = [0]
    m.stub(0x0184a7f3, lambda _: state.__setitem__(0, 0x0184a7f3))
    m.stub(0x0184a990, lambda _: state.__setitem__(0, 0x0184a990))
    def draw(mm):
        args = mm.args(5)
        assert args[:4] == [0xffffffff]*4, args
        color = [x for x in mm.calls if x[0] in ('glColor3f', 'glColor4f')][-1]
        rgba = [cm.bits_f(v) for v in color[1]]
        if len(rgba) == 3: rgba.append(1.0)
        result[:] = [1, int(state[0] == 0x0184a990), args[4], *rgba]
    m.stub(0x012bc07a, draw, 20)
    def stop(mm):
        mm.uc.reg_write(cm.UC_X86_REG_EIP, cm.RETURN_SENTINEL)
        return cm.REDIRECT
    m.stub(0x0176d15b, stop)
    def enter(mm):
        ebp = cm.STACK_BASE + 0x10000
        mm.put32(ebp+8, obj); mm.put32(ebp-0xb0, 0)
        mm.uc.reg_write(cm.UC_X86_REG_EBP, ebp)
        mm.uc.reg_write(cm.UC_X86_REG_ESP, ebp-0x200)
        mm.uc.reg_write(cm.UC_X86_REG_EIP, 0x0176cfab)
        return cm.REDIRECT
    m.stub(0x008e0480, enter)
    m.call(0x008e0480)
    return result


def original_state(text, data, alpha, bits):
    import client_ui_machine as cm
    import validate_gfx3 as gfx
    m = cm.Machine(text,data)
    gfx.allow_functions(m,text,0x0184a7f3,0x0184a990,0x0184a743,0x0184a763,0x0184a783,0x0184a6fd,0x0184a720)
    m.put32(0x0bdc58c4,bits&1)
    m.write(0x0bdc5980,bytes([(bits>>1)&1]))
    m.write(0x0bdc58b5,bytes([(bits>>2)&1]))
    m.write(0x0bdc597d,bytes([(bits>>3)&1]))
    m.write(0x0bdc597f,b'\0'); m.write(0x0bdc597c,b'\0')
    m.call(0x0184a990 if alpha else 0x0184a7f3,args=(1,) if alpha else ())
    m.call(0x0184a783,args=(0,)); m.call(0x0184a763)
    # Depth testing is inherited; depth writes, texturing and alpha testing are off.
    assert not any('Stencil' in name for name,_ in m.calls)
    return [int(m.u32(0x0bdc58c4)!=0),m.read(0x0bdc5980,1)[0],m.read(0x0bdc58b5,1)[0],m.read(0x0bdc597d,1)[0]]


def original_viewport(text, data, width, height):
    import validate_gfx3 as gfx
    import client_ui_machine as cm
    m = gfx.machine(text, data)
    gfx.allow_functions(m, text, gfx.SET_WINDOW_SIZE)
    m.stub(0x00ab03cf, lambda _: 1, cm.stdcall_cleanup(text, 0x00ab03cf))
    m.stub(0x00ab041b, lambda _: 0x30000100, cm.stdcall_cleanup(text, 0x00ab041b))
    result = []
    m.stub(0x00ab0d72, lambda mm: result.extend(mm.args(7)), cm.stdcall_cleanup(text, 0x00ab0d72))
    m.stub(gfx.WINDOW_INVOKE, lambda _: 0)
    m.call(gfx.SET_WINDOW_SIZE, args=(width, height), ecx=m.alloc(0x100, define=True))
    return result


def layer_window(log):
    result = []
    for line in log:
        movie, _, tail = line.partition(' ')
        path, _, args = tail.partition(' ')
        method = path.rsplit('.', 1)[-1]
        if movie == 'MoveCommand' and method in ('SetScale', 'SetAlign', 'SetWindowSize'):
            result.append([method, *json.loads(args)])
    return result


MUTANTS = {
    'translucent_land': ('translucent ? 0.2f : 1.0f', '0.2f'),
    'blend_on_land': ('translucent ? MU_PT_STATE_ALPHA : MU_PT_STATE_OPAQUE', 'MU_PT_STATE_ALPHA'),
    'underwater_world': ('w == 7', 'w == 3'),
    'icarus_shadow': ('w == 0xa', 'w == 0xb'),
    'offset': ('w == 0x8f ? 5 : 0', 'w == 0x8f ? 0 : 5'),
}


def run(args):
    import validate_gfx3 as gfx
    text, data = pins.TEXT.read(args.text), pins.DATA.read(args.data)
    # Verify the supplied third-section identity. Dynamic scene globals are synthetic,
    # deliberately not taken from a logged-in snapshot.
    pins.SECTION3.read(args.section3)
    report = {'pins': {p.name: p.sha256 for p in (pins.TEXT, pins.DATA, pins.SECTION3)}, 'families': {}}
    rng = random.Random(1001)
    worlds = list(range(150)) if args.cases >= 150 else [0, 2, 3, 7, 10, 24, 29, 36, 128, 130, 132, 143]
    worlds += [rng.randrange(-3, 170) for _ in range(max(0, args.cases-len(worlds)))]
    with tempfile.TemporaryDirectory(prefix='app-polish-') as tmp:
        work = Path(tmp); native = native_shadow(work); m = shadow_machine(text, data)
        expected = [(w, original_shadow(m, w)) for w in worlds]
        assert all(native(w) == out for w, out in expected), [(w, native(w), out) for w, out in expected if native(w) != out][:3]
        report['families']['shadow_policy'] = {'cases': len(expected), 'mismatches': 0}
        for alpha in (0,1):
            for bits in range(16):
                assert native.state(alpha,bits) == original_state(text,data,alpha,bits)
        report['families']['shadow_state'] = {'cases':32,'mismatches':0}
        import validate_particles as pt
        subprocess.run(['make','-j4','-C',str(ROOT/'reconstructed/particles')],check=True,capture_output=True)
        library=pt.load_library(str(ROOT/f'reconstructed/particles/libclient_particles.{pt.SUFFIX}'))
        projection=pt.Report(); negatives={key:0 for key in pt.NEGATIVES}
        pt.family_shadow(pt.PtMachine(text,data),library,random.Random(1001),args.cases,projection,negatives)
        family=projection.families['shadow']
        assert family['equal']==family['cases'],family
        report['families']['shadow_projection']={'cases':family['cases'],'mismatches':0}
        sizes = [(800,600), (1024,699), (1024,700), (1280,800), (1504,936), (1920,1080)]
        sizes += [(rng.randrange(640,2600), rng.randrange(480,1500)) for _ in range(max(0,args.cases//5-len(sizes)))]
        windows = []
        for w,h in sizes:
            original = gfx.window_case(text,data,w,h,10)
            layer = layer_window(gfx.layer_log(work,(w,h)))
            assert original == layer, (w,h,original,layer)
            viewport = original_viewport(text,data,w,h)
            assert viewport == [w,h,0,0,w,h,0], viewport
            windows.append((w,h,original))
        report['families']['warps_window'] = {'cases': len(sizes), 'mismatches': 0}
        report['families']['viewport'] = {'cases': len(sizes), 'mismatches': 0}
        report['examples'] = [x for x in windows if x[:2] in [(1280,800),(1504,936)]]
        if args.mutants:
            caught = {}
            for name, mutation in MUTANTS.items():
                folder=work/name; folder.mkdir()
                mutant=native_shadow(folder, mutation)
                caught[name]=any(mutant(w)!=out for w,out in expected)
            # Mutate the native invokes, not the oracle. No display-scale change above 700.
            caught['scale_large_window'] = any(h>=700 and [*out,['SetScale',h/600*100]] != out for w,h,out in windows)
            caught['viewport_800x600'] = any(original_viewport(text,data,w,h) != [800,600,0,0,800,600,0] for w,h,_ in windows)
            caught['shadow_origin_height'] = negatives['shadow_origin_height'] > 0
            assert all(caught.values()), caught
            report['mutants']=caught
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--text'); p.add_argument('--data'); p.add_argument('--section3')
    p.add_argument('--cases',type=int,default=300); p.add_argument('--mutants',action='store_true')
    p.add_argument('--output',required=True)
    args=p.parse_args(); start=time.monotonic(); report=run(args)
    report['wall_seconds']=round(time.monotonic()-start,3)
    Path(args.output).write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report))

if __name__ == '__main__': main()
