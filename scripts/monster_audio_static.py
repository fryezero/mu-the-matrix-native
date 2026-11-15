#!/usr/bin/env python3
"""Recover complete scalar slot +0x70 owners, refusing unsupported services.

This restricted interpreter accepts only stack temporaries, null/model/action
reads, constant frame comparisons, branches and SND_Play. The complete body is
checked before any row is emitted. Models/actions are partitioned by every
integer compare and switch entry; frames by every comparison constant, including
unordered. No inferred prologue owner, sampled fit or dynamic service is admitted.
The independent Unicorn verifier executes each emitted partition and its edges.
"""
import argparse
import json
from pathlib import Path
import re
import struct
import sys
import pins
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
ROOT = Path(__file__).resolve().parents[1]
BASE, DATA, PLAY = 0x401000, 0x1a7c000, 0xa6ac96
# These predicates read only the world dword. In the admitted registry group
# their true branch short-circuits the alternate class lookup. The whole
# dispatcher verifier executes the predicates rather than stubbing them.
PREDICATES = {0xd6a614: {91,92}, 0xdbd14d: {95,96}, 0xe2602d: {110,111}}
EXT_PREDICATES = {0xea233c:{57,58},0xe42f6d:{62},0xe94004:{63},0xdc6bfa:{64},
                  0xe3068f:set(range(82,91)),0xdd38c5:{69},0xdd897d:{70},
                  0xdde62f:{71},0xde5519:{72,73,74},0xe6eccc:{79},0xe18ae9:{80,81}}
EXT_OWNERS = {0xe9e3d5,0xe42a9e,0xe92b75,0xdc6b34,0xe30389,0xdd2776,
              0xe6dc49,0xe1829b,0xe21d13,0xd8aba2,0xe4b1c3}
class NeedRandom(Exception): pass

FIELDS = {0x2a: 'action', 0x5c: 'model', 0xd0: 'frame'}
class Unsupported(Exception): pass


def owners(data):
    groups = {}
    for row in json.loads((ROOT/'docs/research/world-handler-coverage.json').read_text())['classes']:
        entry = struct.unpack_from('<I', data, int(row['vtable'], 16)+0x70-DATA)[0]
        group = groups.setdefault(entry, {'worlds': [], 'labels': []})
        group['worlds'] += row['worlds']; group['labels'].append(row['label'])
    return groups


class Body:
    def __init__(self, text, data, entry, worlds=(), extended=False):
        self.text, self.data, self.entry = text, data, entry
        self.worlds=set(worlds)
        self.extended=extended
        if extended and entry not in EXT_OWNERS: raise Unsupported('owner not in extended review')
        self.period=1
        self.code = {}
        for ins in Cs(CS_ARCH_X86, CS_MODE_32).disasm(text[entry-BASE:entry-BASE+30000],entry):
            self.code[ins.address] = ins
            if ins.mnemonic == 'ret': break
        if not self.code or ins.mnemonic != 'ret': raise Unsupported('no bounded return')
        self.end = ins.address+ins.size
        self.constants = set(); self.float_constants = set(); self.sites = set()
        allowed = {'push','pop','mov','movzx','movss','sub','add','cmp','test','xor','comiss',
                   'je','jne','ja','jb','jae','jbe','jmp','leave','ret','call'}
        if extended: allowed |= {'subss','mulss','addss','fstp','cdq','idiv','and','or','inc','dec','jns','jg'}
        for ins in self.code.values():
            m,o=ins.mnemonic,ins.op_str
            if m not in allowed: raise Unsupported(f'{ins.address:#x}: unsupported {m}')
            if m=='call':
                if o==hex(PLAY):self.sites.add(ins.address)
                elif extended and (int(o,0) in EXT_PREDICATES or int(o,0) in (0xcfc922,0x961a07,0x1989721,0x9dad2c,0xc7dfcc,0x9d3e63)):pass
                elif int(o,0) in PREDICATES and self.worlds <= PREDICATES[int(o,0)]:pass
                elif entry in (0xd733e1,0xdc4773) and int(o,0) in (0x95c652,0xd7b3ce):pass
                else:raise Unsupported(f'{ins.address:#x}: service {o}')
            # Every non-stack memory operand must be a reviewed input or a
            # constant comparison. Writes to OBJECT or image memory are refused.
            if extended and m=='idiv':
                # Only literal push/pop divisors are accepted by the executor.
                before=list(self.code.values());index=before.index(ins)
                divisor=before[index-2];pop=before[index-1]
                if divisor.mnemonic!='push' or pop.mnemonic!='pop' or pop.op_str!=o:raise Unsupported('nonliteral divisor')
                import math
                self.period=math.lcm(self.period,int(divisor.op_str,0))
            if extended and m=='and' and o.endswith('0x80000001'):
                import math
                self.period=math.lcm(self.period,2)
            for mem in re.findall(r'\[([^]]+)\]',o):
                if extended and (mem in ('esi','eax') or mem in ('0xa39d754','0x1cf15fc')):
                    if m in ('mov','movss','and','or','add','sub') and o.split(', ')[0] in (f'dword ptr [{mem}]',f'word ptr [{mem}]',f'byte ptr [{mem}]'):raise Unsupported('non-stack write')
                    continue
                if mem.startswith('ebp ') or mem=='esp': continue
                if re.fullmatch(r'(eax|ecx) \+ 0x[0-9a-f]+',mem):
                    off=int(mem.split(' + ')[1],16)
                    if off not in FIELDS: raise Unsupported(f'{ins.address:#x}: object field {off:#x}')
                    if o.startswith(('dword ptr [','word ptr [','byte ptr [')):
                        raise Unsupported(f'{ins.address:#x}: object write')
                elif re.fullmatch('0x[0-9a-f]+',mem) and m in ('movss','comiss'):
                    self.float_constants.add(struct.unpack_from('<f',data,int(mem,16)-DATA)[0])
                elif m=='jmp' and re.fullmatch(r'eax\*4 \+ 0x[0-9a-f]+',mem): pass
                else: raise Unsupported(f'{ins.address:#x}: memory {mem}')
            if m in ('cmp','sub') and not o.startswith('esp, '):
                try:self.constants.add(int(o.rsplit(', ',1)[1],0))
                except ValueError:pass
        # Validate both paths, all actions and all explicit model/switch values
        # below. The interpreter rejects pointer-dependent compares/addresses.

    def read(self, operand, regs, local, stack, values):
        if operand in regs:return regs[operand]
        if operand=='al':return regs['eax'] & 255
        if re.fullmatch(r'-?(0x[0-9a-f]+|\d+)',operand):return int(operand,0)&0xffffffff
        match=re.fullmatch(r'(?:dword|word) ptr \[ebp ([+-]) (0x[0-9a-f]+|\d+)\]',operand)
        if match:
            k=int(match[2],0)*(1 if match[1]=='+' else -1)
            if k==8:return 0x20000000
            return local[k]
        match=re.fullmatch(r'(?:dword|word) ptr \[(eax|ecx) \+ (0x[0-9a-f]+)\]',operand)
        if match:
            if regs[match[1]]!=0x20000000:raise Unsupported('non-object field base')
            return values[FIELDS[int(match[2],16)]]
        match=re.fullmatch(r'dword ptr \[(0x[0-9a-f]+)\]',operand)
        if match:
            address=int(match[1],16)
            if self.extended and address==0xa39d754:return 0x21000000
            return struct.unpack_from('<f',self.data,address-DATA)[0]
        if self.extended and operand in ('dword ptr [esi]','dword ptr [eax]'):
            address=regs[operand[11:-1]]
            if address in (0x20000158,0x2000015c):return values['distance'] if address==0x20000158 else 0.0
            if address in (0x210033ac,0x210033b0):return 0.0
            raise Unsupported('non-vector dereference')
        raise Unsupported('operand '+operand)

    def run(self,model,action,frame,random_tape=(),distance=0.0,world=None):
        regs={'eax':0,'ecx':0,'edx':0,'esp':0,'ebp':0,'xmm0':0.0,'xmm1':0.0,'esi':0,'st0':0.0}
        local={};stack=[];values=dict(model=model,action=action,frame=frame,distance=distance);pc=self.entry;flags=None;sounds=[];random_count=0
        world=next(iter(self.worlds)) if world is None else world
        def f32(v):
            try:return struct.unpack('<f',struct.pack('<f',v))[0]
            except OverflowError:return float('inf')
        for _ in range(3000):
            ins=self.code.get(pc)
            if ins is None:raise Unsupported(f'branch outside body {pc:#x}')
            pc+=ins.size;m,o=ins.mnemonic,ins.op_str
            read=lambda v:self.read(v,regs,local,stack,values)
            if m=='push':stack.append(read(o))
            elif m=='pop':regs[o]=stack.pop()
            elif m in ('mov','movzx','movss'):
                dst,src=o.split(', ',1)
                if dst=='ebp' and src=='esp':continue
                val=read(src)
                if self.extended and dst=='dword ptr [esp]':
                    stack[-1]=val;continue
                if dst=='al':regs['eax']=int(val)&255
                elif dst in regs:regs[dst]=val
                else:
                    match=re.fullmatch(r'dword ptr \[ebp - (0x[0-9a-f]+|\d+)\]',dst)
                    if not match:raise Unsupported('store '+dst)
                    local[-int(match[1],0)]=val
            elif self.extended and m=='fstp':
                match=re.fullmatch(r'dword ptr \[ebp - (0x[0-9a-f]+|\d+)\]',o)
                if not match:raise Unsupported('fstp destination')
                local[-int(match[1],0)]=f32(regs['st0'])
            elif self.extended and m in ('subss','mulss','addss'):
                dst,src=o.split(', ',1);a,b=read(dst),read(src)
                regs[dst]=f32(a-b if m=='subss' else a*b if m=='mulss' else a+b)
            elif self.extended and m in ('and','or','inc','dec','cdq','idiv'):
                signed=lambda v:v-0x100000000 if v&0x80000000 else v
                if m=='cdq':regs['edx']=0xffffffff if signed(regs['eax'])<0 else 0
                elif m=='idiv':
                    a,b=signed(regs['eax']),signed(read(o));q=abs(a)//abs(b)*(1 if a*b>=0 else -1)
                    regs['eax']=q&0xffffffff;regs['edx']=(a-q*b)&0xffffffff
                else:
                    dst,src=o.split(', ',1) if ', ' in o else (o,'1')
                    a,b=read(dst),read(src)
                    val=(a&b if m=='and' else a|b if m=='or' else a+1 if m=='inc' else a-1)&0xffffffff
                    regs[dst]=val;flags=(val,0,'logic')
            elif m in ('sub','add'):
                dst,src=o.split(', ',1);val=read(src)
                if dst=='esp':
                    if m=='add' and val:del stack[-val//4:]
                else:regs[dst]=(read(dst)+(val if m=='add' else -val))&0xffffffff
            elif m=='xor':
                dst,src=o.split(', ',1)
                if dst!=src:raise Unsupported('nonzero xor')
                regs['eax' if dst=='al' else dst]=0
            elif m in ('cmp','test','comiss'):
                a,b=map(read,o.split(', ',1))
                flags=(a,b,m)
            elif m=='jmp':
                match=re.fullmatch(r'dword ptr \[eax\*4 \+ (0x[0-9a-f]+)\]',o)
                if match:
                    addr=int(match[1],16)+regs['eax']*4
                    if not self.entry<=addr<self.end+4096:raise Unsupported('unbounded switch')
                    pc=struct.unpack_from('<I',self.text,addr-BASE)[0]
                else:pc=int(o,0)
            elif m.startswith('j'):
                a,b,kind=flags
                if m=='jns':
                    if not int(a)&0x80000000:pc=int(o,0)
                    continue
                if m=='jg':
                    signed=lambda v:v-0x100000000 if v&0x80000000 else v
                    if signed(a)>signed(b):pc=int(o,0)
                    continue
                if kind=='test':a,b=a&b,0
                if kind=='comiss' and (a!=a or b!=b):eq,lt=True,True
                else:eq,lt=a==b,a<b
                take={'je':eq,'jne':not eq,'jb':lt,'jbe':lt or eq,'ja':not lt and not eq,'jae':not lt}[m]
                if take:pc=int(o,0)
            elif m=='call':
                target=int(o,0)
                if self.extended and target in EXT_PREDICATES:
                    regs['eax']=int(world in EXT_PREDICATES[target]);continue
                if self.extended and target==0x1989721:
                    if random_count==len(random_tape):raise NeedRandom()
                    regs['eax']=random_tape[random_count]&0xffffffff;random_count+=1;continue
                if self.extended and target==0xcfc922:
                    index=stack.pop()
                    if index not in (0,1):raise Unsupported('vector index')
                    regs['eax']=regs['ecx']+index*4;continue
                if self.extended and target==0x961a07:
                    import math
                    regs['st0']=math.sqrt(stack[-1]);continue
                if target in PREDICATES and self.worlds <= PREDICATES[target]:
                    regs['eax']=1
                    continue
                if target!=PLAY:raise Unsupported(f'reachable service {target:#x}')
                loop,obj,sound=stack[-3:]
                if obj not in (0,0x20000000):raise Unsupported('sound object')
                sounds.append((ins.address,sound,int(bool(obj)),loop))
                regs['eax']=0
            elif m=='leave':pass
            elif m=='ret':
                result=int(regs['eax'])&255,sounds
                return (*result,random_count) if self.extended else result
            else:raise Unsupported(m)
        raise Unsupported('step limit')

    def partitions(self):
        # Model selectors are literal compares, or model-base + table indices.
        models=set()
        for n in self.constants:
            if 32<=n<0x3000:
                models.add(n)
                models.update(n+k for k in range(65))
        actions=set(range(32))|{65535}
        actions.update(n+k for n in self.constants for k in (-1,0,1) if 0<=n+k<=65535)
        floats=sorted(self.float_constants)
        spans=[]
        import math
        bounds=[-math.inf]+floats+[math.inf]
        for lo,hi in zip(bounds,bounds[1:]):
            if lo<hi:spans.append((lo,hi,lo==-math.inf,hi==math.inf,lo+1 if hi==math.inf else hi-1 if lo==-math.inf else (lo+hi)/2))
        spans += [(v,v,True,True,v) for v in floats]
        spans += [(0.,0.,False,False,math.nan)]
        rows=[]
        default=self.run(-1,65535,math.nan)[0]
        returns=[]
        for model in sorted(models):
            model_default=self.run(model,65535,math.nan)[0]
            if model_default!=default:returns.append((model,-1,model_default))
            for action in sorted(actions):
                action_return=self.run(model,action,math.nan)[0]
                if action_return!=model_default:returns.append((model,action,action_return))
                for lo,hi,lc,hc,probe in spans:
                    handled,sounds=self.run(model,action,probe)
                    if handled!=action_return:raise Unsupported('frame-dependent handled result')
                    if sounds:rows.append(dict(model=model,action=action,lo=lo,hi=hi,lc=lc,hc=hc,nan=probe!=probe,
                                               handled=handled,sounds=sounds))
        # Only emit sound rows. Suppression is separately derived for complete
        # model/action partitions; controls verify silent returns too.
        return rows,default,returns,sorted(models)


def recover(text,data):
    accepted,refused={},{}
    for entry,group in owners(data).items():
        try:
            body=Body(text,data,entry,group['worlds']);rows,default,returns,models=body.partitions()
            reached={s[0] for row in rows for s in row['sounds']}
            if reached!=body.sites:raise Unsupported(f'unreached sites {sorted(body.sites-reached)}')
            accepted[entry]=dict(group,rows=rows,end=body.end,default=default,returns=returns,models=models)
        except (Unsupported,KeyError,IndexError,TypeError) as error:
            refused[entry]=dict(group,reason=str(error))
    return accepted,refused


def emit(accepted):
    out=['/* AUDIO-005: reviewed complete scalar owners. Generated by monster_audio_static.py. */']
    def f(x):return ('-INFINITY' if x<0 else 'INFINITY') if abs(x)==float('inf') else float(x).hex()+'f'
    for entry,group in sorted(accepted.items()):
        out.append(f"MU_AUDIO_MONSTER_OWNER(0x{entry:08x}u, {group['default']})")
        for model,action,handled in group['returns']:
            out.append(f'MU_AUDIO_MONSTER_RETURN(0x{entry:08x}u, {model}, {action}, {handled})')
        for world in sorted(set(group['worlds'])):
            out.append(f'MU_AUDIO_MONSTER_WORLD({world}, 0x{entry:08x}u)')
        for row in group['rows']:
            for order,(site,sound,obj,loop) in enumerate(row['sounds']):
                out.append(f"MU_AUDIO_MONSTER_SOUND(0x{entry:08x}u, {row['model']}, {row['action']}, {f(row['lo'])}, {f(row['hi'])}, {int(row['lc'])}, {int(row['hc'])}, {int(row['nan'])}, {order}, 0x{site:08x}u, {sound}, {obj}, {loop})")
    return '\n'.join(out)+'\n'


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--emit-c',type=Path);ap.add_argument('--report',type=Path);a=ap.parse_args()
    accepted,refused=recover(pins.TEXT.read(),pins.DATA.read())
    if a.emit_c:a.emit_c.write_text(emit(accepted))
    summary={'accepted':{hex(k):dict(worlds=v['worlds'],rows=len(v['rows']),sites=len({s[0] for r in v['rows'] for s in r['sounds']})) for k,v in accepted.items()},'refused':{hex(k):v for k,v in refused.items()}}
    if a.report:a.report.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
