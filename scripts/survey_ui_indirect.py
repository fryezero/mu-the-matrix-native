#!/usr/bin/env python3
"""Second, bounded UI route pass: branches, preserved receivers and register calls.

Tracks identities from the manager getter, not nearest offsets. Both virtual
receiver and vtable must belong to the same window. Unknown writes kill facts;
unknown calls clobber volatile registers. Each path has a 512-byte/160-step cap.
No candidate is an upstream user binding or permission to execute its owner.
"""
import argparse
import csv
import json
import re
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_REG
import pins
from survey_ui_routes import census, number, TEXT_BASE, MANAGER


def indirect_routes(text, data, registry, direct, getters):
    md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
    windows={r['slot']:r for r in registry}
    found={}
    explored_helpers=set()
    def memory(src, state):
        m=re.fullmatch(r'dword ptr \[(e[a-z]{2})(?: \+ (0x[0-9a-f]+))?\]',src)
        if not m:return None
        base=state.get(m[1]);off=int(m[2] or '0',16)
        if base==('manager',0) and off in windows:return ('window',off)
        if base and base[0]=='window' and off==0:return ('vtable',base[1])
        if base and base[0]=='vtable' and off in (0x40,0x44):return ('method',base[1],off)
        return None
    for start in direct.get(MANAGER,[]):
        # Path-local facts avoid merging an identity from one arm into another.
        work=[(start+5,{'eax':('manager',0)},0,start,0)]
        seen=set()
        while work:
            pc,state,steps,scope,depth=work.pop()
            key=(pc,tuple(sorted(state.items())),scope,depth)
            if len(seen)>=2048 or key in seen or steps>=240 or not scope<=pc<scope+1024:continue
            seen.add(key)
            seq=list(md.disasm(text[pc-TEXT_BASE:pc-TEXT_BASE+15],pc,count=1))
            if not seq:continue
            i=seq[0];nextpc=pc+i.size;state=state.copy();parts=i.op_str.split(', ')
            if i.mnemonic in ('ret','retf','leave','int3'):continue
            if i.mnemonic.startswith('j'):
                target=number(i.op_str)
                if target is not None:work.append((target,state,steps+1,scope,depth))
                if i.mnemonic!='jmp':work.append((nextpc,state,steps+1,scope,depth))
                continue
            if i.mnemonic=='call':
                target=number(i.op_str);receiver=state.get('ecx')
                method=state.get(i.op_str) or memory(i.op_str,state)
                action=None;slot=None
                if receiver and receiver[0]=='window' and receiver[1] in windows:
                    slot=receiver[1]
                    if target==0xaae767:action='toggle'
                    elif method and method[:2]==('method',slot):action='open' if method[2]==0x40 else 'close'
                    elif target in windows[slot]['lifecycle']:
                        action='open' if target==windows[slot]['lifecycle'][0] else 'close'
                if action:
                    found[(pc,slot,action)]=dict(site=f'0x{pc:08x}',manager_slot=f'0x{slot:x}',movie=windows[slot]['movie'],action=action,manager_site=f'0x{start:08x}',encoding='register' if i.op_str in state else 'memory/direct')
                if depth==0 and receiver and receiver[0]=='window' and target and 0xaad000<=target<0xc90000 and not action and target not in (0xaae6f9,) and (target,receiver[1]) not in explored_helpers:
                    explored_helpers.add((target,receiver[1]))
                    work.append((target,{'ecx':receiver},0,target,1))
                for r in ('eax','ecx','edx'):state.pop(r,None)
                if target==MANAGER:state['eax']=('manager',0)
                elif target in getters and receiver==('manager',0):state['eax']=('window',getters[target])
            elif i.mnemonic=='mov' and len(parts)==2:
                dst,src=parts;value=state.get(src) or memory(src,state)
                state.pop(dst,None)
                if value:state[dst]=value
            else:
                # Capstone's written register list also kills subregister aliases.
                _,written=i.regs_access()
                for reg in written:
                    name=i.reg_name(reg)
                    for full in ('eax','ebx','ecx','edx','esi','edi'):
                        if name==full or name in {'eax':('al','ah','ax'),'ebx':('bl','bh','bx'),'ecx':('cl','ch','cx'),'edx':('dl','dh','dx'),'esi':('si',),'edi':('di',)}[full]:state.pop(full,None)
                # An unmodelled local write cannot leave a stale saved receiver.
                if parts and parts[0].startswith('dword ptr [ebp') and i.mnemonic not in ('cmp','test','push'):state.pop(parts[0],None)
            work.append((nextpc,state,steps+1,scope,depth))
    return sorted(found.values(),key=lambda r:(r['site'],r['manager_slot'],r['action']))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    text=pins.TEXT.read();data=pins.DATA.read();registry,old,direct,getters=census(text,data)
    rows=indirect_routes(text,data,registry,direct,getters)
    args.out.mkdir(parents=True,exist_ok=True)
    with (args.out/'indirect.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=['site','manager_slot','movie','action','manager_site','encoding']);w.writeheader();w.writerows(rows)
    oldsites={(r['site'],r['manager_slot']) for r in old if r['manager_slot']}
    new=[r for r in rows if (r['site'],r['manager_slot']) not in oldsites]
    summary={'paths_from_manager':len(direct[MANAGER]),'joined_sites':len(rows),'additional_sites':len(new),'additional_open_movies':sorted({r['movie'] for r in new if r['action'] in ('open','toggle')})}
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
