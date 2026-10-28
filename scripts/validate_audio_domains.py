#!/usr/bin/env python3
"""AUDIO-002D: compiled audio adapters versus original NPC/Master callers.

NPC: synthetic viewport buff keys populate the original MSVC map. Its lookup and
voice fragment run as instructions, including empty/absent/present keys. Buff
packet parsing has its unchanged viewport family. This is the latest viewport
snapshot, not a reconstruction of later buff add/remove handlers.
Master: reuse the complete click/confirmation instruction comparison, record the
original SND_Play return address, and compare the production event adapter.
Quest: a bounded static CFG audit of migrated handler/callback roots, not a claim
about every transitive service. No quest sound is invented.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import pins
from validate_audio import Machine, ARENA, STACK, STACK_SIZE
import validate_skill_tree as tree

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = r'''
#include "core/mu_session_audio.h"
#include "session/domains/skills_audio.h"
typedef struct decision { unsigned routine,site; int id,key,loop,missing; } decision;
static decision rows[8]; static int count;
void mu_session_sound_emit(mu_session *s,unsigned routine,unsigned site,int id,int16_t key,int loop)
{ (void)s;rows[count++]=(decision){routine,site,id,key,loop,0}; }
void mu_session_sound_missing(mu_session *s,unsigned routine,unsigned site,unsigned input)
{ (void)s;rows[count++]=(decision){routine,site,(int)input,-2,0,1}; }
int npc(int world,int model,int action,float frame,int known,int n,const uint16_t *keys,decision *out)
{
    mu_monster_viewport v={0};v.size=28+8*n;v.buff_count=(uint8_t)n;
    for(int i=0;i<n;++i)v.buff_type[i]=keys[i];
    count=0;mu_session_npc_viewport_voice(NULL,model,0,(uint16_t)action,frame,world,known?&v:NULL);
    for(int i=0;i<count;++i)out[i]=rows[i];return count;
}
int master(const char *what,int id,decision *out)
{
    count=0;mu_session_master_audio_event(NULL,what,id);
    for(int i=0;i<count;++i)out[i]=rows[i];return count;
}
'''
class Decision(C.Structure):
    _fields_=[('routine',C.c_uint),('site',C.c_uint),('id',C.c_int),('key',C.c_int),('loop',C.c_int),('missing',C.c_int)]
def rows(lib,name,args):
    out=(Decision*8)();n=getattr(lib,name)(*args,out)
    return [tuple(getattr(out[i],k) for k,_ in Decision._fields_) for i in range(n)]
def build(tmp,name,audio=None,skills=None):
    folder=tmp/name;(folder/'core').mkdir(parents=True);(folder/'session/domains').mkdir(parents=True)
    (folder/'core/mu_session_audio.h').write_text(audio or (ROOT/'native/core/mu_session_audio.h').read_text())
    (folder/'session/domains/skills_audio.h').write_text(skills or (ROOT/'native/session/domains/skills_audio.h').read_text())
    for src in (ROOT/'native/core').glob('*.h'):
        if src.name!='mu_session_audio.h':(folder/'core'/src.name).symlink_to(src)
    for src in (ROOT/'native/session').iterdir():
        if src.name!='domains':(folder/'session'/src.name).symlink_to(src)
    for src in (ROOT/'native/session/domains').iterdir():
        if src.name!='skills_audio.h':(folder/'session/domains'/src.name).symlink_to(src)
    for src in (ROOT/'native').iterdir():
        if src.is_dir() and src.name not in ('core','session'):(folder/src.name).symlink_to(src)
    if not (tmp/'reconstructed').exists():(tmp/'reconstructed').symlink_to(ROOT/'reconstructed')
    (folder/'wrapper.c').write_text(WRAPPER);out=folder/'adapter.dylib'
    subprocess.run(['clang','-std=c11','-O2','-shared','-I',str(folder),'-I',str(folder/'session'),'-I',str(ROOT/'native/build/gen'),
                    str(folder/'wrapper.c'),str(ROOT/'reconstructed/audio/audio_world.c'),
                    str(ROOT/'native/build/libmunative.a'),'-lm','-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation','-framework','AudioToolbox','-o',str(out)],check=True)
    lib=C.CDLL(str(out));lib.npc.argtypes=[C.c_int,C.c_int,C.c_int,C.c_float,C.c_int,C.c_int,C.POINTER(C.c_uint16),C.POINTER(Decision)]
    lib.master.argtypes=[C.c_char_p,C.c_int,C.POINTER(Decision)];return lib

def buff_map(m,keys):
    keys=sorted(set(keys));head=ARENA+0x100;obj=ARENA
    m.write(obj,bytes(16));m.write32(obj+4,head);m.write32(obj+8,len(keys))
    m.write(head,struct.pack('<III',head,head,head)+b'\1\1\0\0'+bytes(8))
    def branch(lo,hi,parent):
        if lo==hi:return head
        mid=(lo+hi)//2;node=ARENA+0x200+32*mid
        left=branch(lo,mid,node);right=branch(mid+1,hi,node)
        m.write(node,struct.pack('<III',left,parent,right)+b'\1\0\0\0'+struct.pack('<II',keys[mid],0))
        return node
    root=branch(0,len(keys),head)
    if keys:m.write(head,struct.pack('<III',ARENA+0x200,root,ARENA+0x200+32*(len(keys)-1)))
    return obj

def npc_corpus(text,data,buff_index):
    m=Machine(text,data,strict_stack=False);ebp=STACK+STACK_SIZE-0x8000;obj=ARENA+0x4000;sounds=[]
    def sound(m):
        assert m.arg(1)==0 and m.arg(2)==0
        sounds.append((0x13b23f8,m.read32(m.reg('esp'))-5,m.arg(0),-2,0,0));return 1,0
    m.hook(0xa6ac96,sound)
    # Execute AddBuff's world and key-27 eligibility gates. Table existence,
    # unrelated effects and map insertion are explicit hosts. Lookup below runs
    # the original instructions on a synthetic map, not a Python membership stub.
    added=[]
    m.hook(0x10de759,lambda m:(buff_index,4))
    m.hook(0x95f6db,lambda m:(0,0));m.hook(0x9a1510,lambda m:(0,0))
    m.hook(0x121ea20,lambda m:(0,0));m.hook(0x121e006,lambda m:(0,0))
    def insert(m):
        added.append(m.arg(0));return 0,8
    m.hook(0x129588d,insert)
    m.model_page(0x1cf1000);m.model_page(0xa39d000)
    m.write32(0xa39d754,ARENA+0x9000)
    m.write(obj,bytes(0x500));corpus=[]
    keysets=[[],[26],[27],[28],[0,26,28,65535],[27,27],list(range(56)),list(range(28,84))]
    for world in [0,17,18,23,24,53,54,97,98]:
      m.write32(0x1cf15fc,world)
      for keys in keysets:
        added.clear()
        if 27 in keys:
            m.call(0x128723b,[27,obj,0,0])
        active=[k for k in keys if k!=27]+added
        # OBJECT +0x358 is the buff container. Repoint its map to the same synthetic tree.
        container=buff_map(m,active);m.write(obj+0x358,m.read(container,12))
        for action in [0,1,65535]:
          for frame in [float('nan'),-float('inf'),0.,4.9999995,5.,7.,10.,10.000001,float('inf')]:
            sounds.clear();m.write32(ebp+12,obj);m.write(obj+0x2a,struct.pack('<H',action));m.write(obj+0xd0,struct.pack('<f',frame))
            m.run(0x13b543c,0x13b549c,stops=(0x13b8058,),ebp=ebp,esp=ebp-0x1000)
            assert m.reg('eip') in (0x13b549c,0x13b8058)
            corpus.append(((world,0xa01,action,frame,1,keys),sounds[:]))
    return corpus

def master_corpus(text,data,snapshot,cases,tmp):
    snap=tree.plain.Snapshot.load(snapshot);m=tree.vl.LangMachine(text,data,snap)
    native=tree.TreeNative(tmp);corpus=[];original=tree.Recorder
    class Recorder(original):
        def __init__(self,m,h,case):
            super().__init__(m,h,case);self.sounds=[];Recorder.current=self
            def sound(mm):
                self.log.append(('sound',tree.s32(mm.args(3)[0])))
                self.sounds.append((tree.CLICK,mm.u32(mm.uc.reg_read(tree.cm.UC_X86_REG_ESP))-5,
                                    tree.s32(mm.args(3)[0]),-2,0,0))
                assert mm.args(3)[1]==0 and mm.args(3)[2]==0
                return 0
            m.stub(0xa6ac96,sound,0)
    class Family(tree.vs.Family):
        def check(self,label,client,nat):
            assert client==nat,(label,client,nat)
            events=[(b'sound',e[1]) for e in nat['log'] if e[0]=='sound']
            corpus.append((events,Recorder.current.sounds[:]))
            super().check(label,client,nat)
    tree.Recorder=Recorder
    try:
        records=tree.vs.snapshot_records(snap);keys=[r.index for r in records];table=native.table(records);native.table_c=table
        tree.run_click(m,native,random.Random(20024),Family('click'),keys,table,records,tree.snapshot_text(snap),cases)
    finally:tree.Recorder=original
    return corpus

def check(lib,name,corpus):
    for args,want in corpus:
        if name=='npc':
            world,model,action,frame,known,keys=args
            got=rows(lib,'npc',(world,model,action,frame,known,len(keys),(C.c_uint16*len(keys))(*keys)))
        else:got=[row for event in args for row in rows(lib,'master',event)]
        if got!=want:return (args,want,got)
    return None

def quest_audit(text):
    from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_OP_IMM
    cs=Cs(CS_ARCH_X86,CS_MODE_32);cs.detail=True
    roots=[0x122adf5,0x1222933,0x122287a,0x12510fe,0x1253577,0x12533c9,
           0x1278f3a,0x127a1db,0x1278f6c,0x124cbb0,0x128a52d,0x12534ae,
           0xbe436d,0xbe45c7,0xbe4b89,0xbe906d,0xbe8565,
           0xd4bed6,0xd4b942,0xd4ffea,0xd5029b,0xd5060e,0xc89dfb,0xc8ae30]
    result={}
    for root in roots:
        todo=[root];seen=set();sounds=[]
        while todo:
            a=todo.pop()
            if a in seen:continue
            seen.add(a);ins=next(cs.disasm(text[a-0x401000:a-0x401000+15],a),None)
            assert ins and len(seen)<10000
            if ins.mnemonic=='call' and ins.op_str=='0xa6ac96':sounds.append(hex(a))
            if ins.mnemonic.startswith('ret') or ins.mnemonic in ('int3','ud2'):continue
            if ins.mnemonic.startswith('j'):
                if ins.operands[0].type==CS_OP_IMM:todo.append(ins.operands[0].imm)
                if ins.mnemonic=='jmp':continue
            todo.append(a+ins.size)
        assert not sounds,(hex(root),sounds)
        result[hex(root)]={'instructions':len(seen),'direct_sound_sites':sounds}
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=int,default=600)
    p.add_argument('--snapshot');p.add_argument('--mutations',action='store_true');p.add_argument('--report');a=p.parse_args()
    text,data=pins.TEXT.read(),pins.DATA.read();snapshot=pins.SKILL_LANG5.path(a.snapshot);pins.SKILL_LANG5.read(snapshot)
    # Settle the one static table-existence answer with the original getter on
    # the pinned snapshot. Do not substitute guessed BuffInfo validity.
    snap=tree.plain.Snapshot.load(snapshot);bm=tree.vl.LangMachine(text,data,snap);bm.prepare(force=True)
    bm.call(0x10de759,[27],ecx=tree.plain.BUFF)
    buff_index=bm.uc.reg_read(tree.cm.UC_X86_REG_EAX);assert buff_index!=0xffffffff
    report={'buff_table_key_verified':True,'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,'families':{},'mutants':{},'mismatches':0,'quest_static':quest_audit(text)}
    with tempfile.TemporaryDirectory(prefix='audio-domains-') as folder:
        tmp=Path(folder);corpora={'npc':npc_corpus(text,data,buff_index),'master':master_corpus(text,data,snapshot,a.cases,tmp)};lib=build(tmp,'plain')
        for name,corpus in corpora.items():
            error=check(lib,name,corpus);assert error is None,(name,error)
            report['families'][name]={'cases':len(corpus),'mismatches':0}
        # Unsupported event names/ids must not acquire invented original provenance.
        for event in [(b'stats',25),(b'sound',26),(b'',25)]:assert rows(lib,'master',event)==[]
        if a.mutations:
            audio=(ROOT/'native/core/mu_session_audio.h').read_text();skills=(ROOT/'native/session/domains/skills_audio.h').read_text()
            variants=[('buff-key','npc','buff_type[i] == 0x1b','buff_type[i] == 0x1c'),
                      ('buff-world','npc','mu_rp_world_rule(world)','mu_rp_world_rule(world + 1)'),
                      ('buff-count','npc','i < viewport->buff_count','i + 1 < viewport->buff_count'),
                      ('voice-frame','npc','action, frame, buff','action, frame + 1.0f, buff'),
                      ('click-site','master','0x00bb23d1u','0x00bb23d2u'),
                      ('click-id','master','0x19, -2, 0','0x1a, -2, 0'),
                      ('click-loop','master','0x19, -2, 0','0x19, -2, 1')]
            for name,family,old,new in variants:
                source=audio if family=='npc' else skills;assert old in source,old
                bad=build(tmp,name,audio=source.replace(old,new,1) if family=='npc' else None,
                          skills=source.replace(old,new,1) if family=='master' else None)
                assert check(bad,family,corpora[family]) is not None,name;report['mutants'][name]='caught'
    report['cases']=sum(f['cases'] for f in report['families'].values())
    if a.report:Path(a.report).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
