#!/usr/bin/env python3
"""AUDIO-002G: original CButton and credits gates, order and native cue provenance.

Runs complete CButton::Update and CCreditWin bodies with the existing UI machine.
CInput, GDI, file/texture and presentation-service boundaries are the existing
explicit hosts. No event/answer route is followed. Credits HideWin is a marker,
so repeated end records remain visible in this instruction comparison.
"""
import argparse
import ctypes as C
import hashlib
import itertools
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile

import pins
import validate_ui_widgets as v

ROOT = Path(__file__).resolve().parents[1]
BODIES = {
    0x009867e3: 'cddc2a97692c4736778b840d39a85a0ee97530d5dc900910c550258a97392c08',
    0x009d9eb2: '955f4aeec472815ba402066a3b3140d8c746609a7a480d60675c4ae0d8089eb4',
}
WRAPPER = r'''
#include "core/mu_ui_audio.h"
#include "ui_widget.h"
static void decoded(void *ctx, const mu_cue *cue, uint32_t tick) {
    uint32_t *out = ctx; (void)tick;
    out[0]=cue->handler; out[1]=cue->u.sound.site; out[2]=(uint32_t)cue->u.sound.id;
    out[3]=(uint32_t)(int32_t)cue->u.sound.at_key; out[4]=cue->u.sound.loop;
}
int decode(int op, const uint32_t *words, int count, const void *data, size_t size, uint32_t *out) {
    mu_ui_audio audio={0}; mu_ui_audio_set_sound(&audio, decoded, out);
    return mu_ui_audio_event(&audio,op,words,count,data,size,1);
}
void configure(mu_ui_button *b, int show, int enable, int active, int check) {
    b->sprite.show=(uint8_t)show; b->enable=(uint8_t)enable;
    b->active=(uint8_t)active; b->check=(uint8_t)check;
}
uint32_t observe(const mu_ui_ctx *ctx, const mu_ui_button *b) {
    return b->click | (uint32_t)b->check<<8 | (uint32_t)(ctx->held_button==b)<<16;
}
'''


def build(folder, name, changes=None):
    target=folder/name
    target.mkdir()
    # Only authored source/header copies, never client inputs.
    for path in (ROOT/'reconstructed/ui').iterdir():
        if path.suffix in ('.c','.h'):
            (target/path.name).write_text((changes or {}).get(path.name,path.read_text()))
    (target/'core').mkdir()
    header=(changes or {}).get('mu_ui_audio.h',(ROOT/'native/core/mu_ui_audio.h').read_text())
    header=header.replace('"../../reconstructed/ui/ui_sound.h"','"ui_sound.h"').replace(
        '"../session/mu_cue.h"', '"'+str(ROOT/'native/session/mu_cue.h')+'"')
    (target/'core/mu_ui_audio.h').write_text(header)
    (target/'wrapper.c').write_text(WRAPPER)
    sources=['ui2d.c','ui_text.c','ui_texture.c','ui_login.c','ui_widget.c','ui_server.c',
             'ui_credit.c','ui_charsel.c','ui_loading.c','ui_probe.c','wrapper.c']
    out=target/'ui.dylib'
    subprocess.run(['clang','-std=c11','-O2','-shared','-ffp-contract=off','-fno-fast-math',
                    '-I',str(target),*[str(target/s) for s in sources],'-o',str(out)],check=True)
    lib=v.library(out)
    lib.decode.argtypes=[C.c_int,C.c_void_p,C.c_int,C.c_void_p,C.c_size_t,C.c_void_p]
    lib.decode.restype=C.c_int
    lib.configure.argtypes=[C.c_void_p]+[C.c_int]*4
    lib.observe.argtypes=[C.c_void_p,C.c_void_p];lib.observe.restype=C.c_uint32
    lib.mu_ui_button_init.argtypes=[C.c_void_p]
    lib.mu_ui_button_create.argtypes=[C.c_void_p,C.c_void_p]+[C.c_int32]*11
    lib.mu_ui_button_update.argtypes=[C.c_void_p,C.c_void_p,C.c_double]
    lib.mu_ui_sprite_set_position.argtypes=[C.c_void_p]+[C.c_int32]*3
    return lib


class AudioAuthored(v.Authored):
    def _record(self,user,op,words,count,data,size):
        super()._record(user,op,words,count,data,size)
        if v.OPS[op]=='Sound':
            row=(C.c_uint32*5)()
            if self.lib.decode(op,words,count,data,size,row)!=1:
                self.audio.append(('native cue refused',))
                return
            observed=self.lib.observe(C.byref(self.ctx),self.button) if self.button else 0
            self.audio.append(tuple(row)+(observed,))


# Side resolves Authored dynamically. Keep the existing normalised stream checks.
v.Authored=AudioAuthored


def side(lib,client):
    bitmaps={7:{'width':16.,'height':64.,'texture':7,'components':4}}
    # Tiny framebuffer keeps this boundary test small.
    result=v.Side(lib,(64,48),bitmaps,(1.,1.),{}, {'groups':[],'notice':b''},bytes(640*480*3))
    result.authored.lib=lib;result.authored.ctx=result.ctx
    result.authored.audio=[];result.authored.button=None
    client.setup(result.authored.state,bitmaps,(64,48),{}, {'groups':[],'notice':b''})
    return result


def button_cases():
    for flags in itertools.product([1,0],repeat=3):
        for held,down,up,delta,point,check,check_frame in itertools.product(
                [1,0,2],[0,1],[1,0],[40.,0.,-1.],
                [(5,5),(-1,1),(0,0),(10,5),(5,10)],[0,1],[-1,3]):
            yield (*flags,held,down,up,delta,*point,check,check_frame)
    # Noncanonical true bytes and unordered delta are actual x86 branches.
    for delta in [float('nan'),float('-inf'),float('inf')]:
        yield (2,2,2,1,0,2,delta,5,5,2,3)


def buttons(client,lib,limit=None):
    s=side(lib,client);m=client.machine
    b=m.alloc(0xe0,define=True);other=m.alloc(0xe0,define=True)
    mine=C.create_string_buffer(lib.mu_ui_probe_sizeof(1))
    s.authored.button=mine
    original=[]
    def sound(mm):
        ret=mm.u32(mm.uc.reg_read(v.cm.UC_X86_REG_ESP))
        id,obj,loop=mm.args(3)
        observed=mm.read(b+0xaa,1)[0] | mm.read(b+0xab,1)[0]<<8 | (mm.u32(v.HELD_BUTTON)==b)<<16
        original.append((0x9867e3,ret-5,id,0xfffffffe if not obj else obj,loop,observed))
        mm.calls.append(('Sound',(id,)))
        return 0
    client.stub(0xa6ac96,sound,0)
    out=(C.c_uint32*512)();count=0;sounds=0
    for case in itertools.islice(button_cases(),limit):
        show,enable,active,held,down,up,delta,x,y,check,check_frame=case
        m.call(0x986569,ecx=b)
        args=[10,10,7,4,2,1,-1,check_frame,-1,-1,-1]
        m.call(0x9865f4,[a&0xffffffff for a in args],ecx=b)
        m.call(0x10add3c,[0,0,3],ecx=b)
        lib.mu_ui_button_init(mine);lib.mu_ui_button_create(C.byref(s.ctx),mine,*args)
        lib.mu_ui_sprite_set_position(mine,0,0,3)
        lib.configure(mine,show,enable,active,check)
        for off,value in [(0xa0,show),(0xa8,enable),(0xa9,active),(0xab,check)]:m.write(b+off,bytes([value]))
        m.put32(v.HELD_BUTTON,[0,b,other][held]);s.ctx.held_button=[None,C.addressof(mine),1][held]
        client.set_input(x,y,down,up,(64,48));s.set_input(x,y,down,up)
        original.clear();s.authored.audio.clear();m.calls.clear();s.calls.clear()
        lo,hi=struct.unpack('<II',struct.pack('<d',delta))
        m.call(0x9867e3,[lo,hi],ecx=b)
        lib.mu_ui_button_update(C.byref(s.ctx),mine,delta)
        assert original==s.authored.audio,(case,original,s.authored.audio)
        assert v.normalize(m.calls)==v.normalize_authored(s.calls),(case,m.calls,s.calls)
        got=list(out[:lib.mu_ui_probe_button(mine,out)])
        assert client.snap_button(b)==got,('state',case)
        original_held=m.u32(v.HELD_BUTTON)
        expected=0 if not original_held else 1 if original_held==b else 2
        actual=0 if not s.ctx.held_button else 1 if s.ctx.held_button==C.addressof(mine) else 2
        assert actual==expected,('held',case)
        count+=1;sounds+=len(original)
    return {'cases':count,'sounds':sounds,'mismatches':0}


def credits(client,lib,cases):
    # Reuse the complete credits/state/stream comparison, instrumenting its
    # independent original SND_Play stub and authored native cue decoder.
    setup=client.setup
    original=[];authored=[]
    def wrapped_setup(*args,**kwargs):
        setup(*args,**kwargs)
        def sound(mm):
            ret=mm.u32(mm.uc.reg_read(v.cm.UC_X86_REG_ESP));id,obj,loop=mm.args(3)
            original.append((0x9d9eb2,ret-5,id,0xfffffffe if not obj else obj,loop,0))
            mm.calls.append(('Sound',(id,)))
            return 0
        client.stub(0xa6ac96,sound,0)
    client.setup=wrapped_setup
    record=AudioAuthored._record
    def collect(self,*args):
        if not hasattr(self,'audio'):
            self.lib=lib;self.audio=[];self.button=None
        before=len(self.audio);record(self,*args)
        authored.extend(self.audio[before:])
    AudioAuthored._record=collect
    report={}
    try:v.validate_credits(client,lib,random.Random(2007),report,cases)
    finally:client.setup=setup;AudioAuthored._record=record
    assert original==authored,('credits audio',original,authored)
    assert original,'credits corpus must reach an end record'
    return {**report['credits'],'sounds':len(original),'mismatches':0}


def compare(text,data,lib,cases=None,credit_cases=40):
    client=v.WidgetClient(text,data)
    return {'button':buttons(client,lib,cases),'credits':credits(client,lib,credit_cases)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases',type=int);p.add_argument('--mutations',action='store_true');p.add_argument('--report')
    a=p.parse_args();text,data=pins.TEXT.read(),pins.DATA.read()
    pins_bodies={}
    for start in [0x9867e3,0x9d9eb2]:
        end=v.cm.function_extent(text,start)
        digest=hashlib.sha256(text[start-v.cm.TEXT_BASE:end-v.cm.TEXT_BASE]).hexdigest()
        assert digest==BODIES[start],hex(start)
        pins_bodies[hex(start)]=digest
    with tempfile.TemporaryDirectory(prefix='audio-ui-') as tmp:
        folder=Path(tmp);families=compare(text,data,build(folder,'base'),a.cases)
        mutants={}
        if a.mutations:
            plants=[
                ('button-site','ui_widget.c','0x0098689eu','0x0098689fu'),
                ('button-enabled','ui_widget.c','if (button->enable) {','if (!button->enable) {'),
                ('button-release','ui_widget.c','if (in->lbutton_up) {','if (in->lbutton_down) {'),
                ('button-held','ui_widget.c',
                 'if (in->lbutton_up) {\n            if (mu_ui_button_cursor_in(ctx, button) && ctx->held_button == button)',
                 'if (in->lbutton_up) {\n            if (mu_ui_button_cursor_in(ctx, button) && ctx->held_button != button)'),
                ('button-order','ui_widget.c','button->click = 1;','button->click = 0;'),
                ('credit-site','ui_credit.c','0x009d9eedu','0x009d9eeeu'),
                ('credit-gate','ui_credit.c','if (type == MU_UI_CREDIT_END) {','if (type == MU_UI_CREDIT_TITLE) {'),
                ('cue-id','mu_ui_audio.h','cue.u.sound.id = (int32_t)words[0];','cue.u.sound.id = 26;'),
                ('cue-object','mu_ui_audio.h','cue.u.sound.at_key = -2;','cue.u.sound.at_key = -1;'),
                ('cue-loop','mu_ui_audio.h','cue.u.sound.site = source.site;','cue.u.sound.site = source.site; cue.u.sound.loop = 1;')]
            for name,file,old,new in plants:
                path=ROOT/('native/core' if file=='mu_ui_audio.h' else 'reconstructed/ui')/file
                source=path.read_text();assert source.count(old)==1,(name,source.count(old))
                lib=build(folder,name,{file:source.replace(old,new,1)})
                try:compare(text,data,lib,2000,4)
                except AssertionError:mutants[name]='caught'
                else:raise AssertionError(('survived',name))
    report={'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,'bodies':pins_bodies,
            'families':families,'cases':sum(f['cases'] for f in families.values()),'mismatches':0,'mutants':mutants}
    if a.report:Path(a.report).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
