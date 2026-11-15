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
    def __init__(self, text, data, entry):
        self.text, self.data, self.entry = text, data, entry
        self.code = {}
        for ins in Cs(CS_ARCH_X86, CS_MODE_32).disasm(text[entry-BASE:entry-BASE+30000],entry):
            self.code[ins.address] = ins
            if ins.mnemonic == 'ret': break
        if not self.code or ins.mnemonic != 'ret': raise Unsupported('no bounded return')
        self.end = ins.address+ins.size
        self.constants = set(); self.float_constants = set(); self.sites = set()
        allowed = {'push','pop','mov','movzx','movss','sub','add','cmp','test','xor','comiss',
                   'je','jne','ja','jb','jae','jbe','jmp','leave','ret','call'}
        for ins in self.code.values():
            m,o=ins.mnemonic,ins.op_str
            if m not in allowed: raise Unsupported(f'{ins.address:#x}: unsupported {m}')
            if m=='call':
                if o!=hex(PLAY): raise Unsupported(f'{ins.address:#x}: service {o}')
                self.sites.add(ins.address)
            # Every non-stack memory operand must be a reviewed input or a
            # constant comparison. Writes to OBJECT or image memory are refused.
            for mem in re.findall(r'\[([^]]+)\]',o):
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
        if match:return struct.unpack_from('<f',self.data,int(match[1],16)-DATA)[0]
        raise Unsupported('operand '+operand)

    def run(self,model,action,frame):
        regs={'eax':0,'ecx':0,'edx':0,'esp':0,'ebp':0,'xmm0':0.0,'xmm1':0.0}
        local={};stack=[];values=dict(model=model,action=action,frame=frame);pc=self.entry;flags=None;sounds=[]
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
                if dst=='al':regs['eax']=int(val)&255
                elif dst in regs:regs[dst]=val
                else:
                    match=re.fullmatch(r'dword ptr \[ebp - (0x[0-9a-f]+|\d+)\]',dst)
                    if not match:raise Unsupported('store '+dst)
                    local[-int(match[1],0)]=val
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
                if kind=='test':a,b=a&b,0
                if kind=='comiss' and (a!=a or b!=b):eq,lt=True,True
                else:eq,lt=a==b,a<b
                take={'je':eq,'jne':not eq,'jb':lt,'jbe':lt or eq,'ja':not lt and not eq,'jae':not lt}[m]
                if take:pc=int(o,0)
            elif m=='call':
                loop,obj,sound=stack[-3:]
                if obj not in (0,0x20000000):raise Unsupported('sound object')
                sounds.append((ins.address,sound,int(bool(obj)),loop))
                regs['eax']=0
            elif m=='leave':pass
            elif m=='ret':return int(regs['eax'])&255,sounds
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
            body=Body(text,data,entry);rows,default,returns,models=body.partitions()
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
