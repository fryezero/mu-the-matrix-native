#!/usr/bin/env python3
"""Second, bounded UI route pass: branches, preserved receivers and register calls.

Tracks identities from the manager getter, not nearest offsets. Both virtual
receiver and vtable must belong to the same window. Unknown writes kill facts;
unknown calls clobber volatile registers. Each path has a 1,024-byte/240-step cap, with at most 2,048 states per root.
No candidate is an upstream user binding or permission to execute its owner.
"""
import argparse
import csv
import json
import re
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_AC_WRITE
from capstone.x86 import X86_OP_MEM
import pins
from survey_ui_routes import census, number, TEXT_BASE, DATA_BASE, MANAGER


def indirect_routes(text, data, registry, direct, getters, extra=None):
    # extra: {slot: {vtable offset}} of proved self-opening virtual methods (third pass); default: +0x40/+0x44 only.
    extra=extra or {}
    md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
    windows={r['slot']:r for r in registry}
    found={}
    explored_helpers=set()
    def kill_written(i, state):
        _,written=i.regs_access()
        for reg in written:
            name=i.reg_name(reg)
            if name=='ebp':
                for key in list(state):
                    if key.startswith('dword ptr [ebp'):state.pop(key,None)
            for full,aliases in {'eax':('al','ah','ax'),'ebx':('bl','bh','bx'),'ecx':('cl','ch','cx'),'edx':('dl','dh','dx'),'esi':('si',),'edi':('di',)}.items():
                if name==full or name in aliases:state.pop(full,None)
    def kill_local_write(dst, state):
        object_store=re.fullmatch(r'(?:byte|word|dword|qword) ptr \[(e[a-z]{2}) \+ (0x[0-9a-f]+|[0-9]+)\]',dst)
        if object_store and int(object_store[2],0)>0 and state.get(object_store[1],('',))[0] in ('window','manager'):
            return  # A proved object field does not alias the caller's frame.
        store=re.fullmatch(r'(byte|word|dword|qword) ptr \[ebp(?: ([+-]) (0x[0-9a-f]+|[0-9]+))?\]',dst)
        if not store:
            # Non-frame memory aliases cannot preserve a saved local identity.
            for key in list(state):
                if key.startswith('dword ptr [ebp'):state.pop(key,None)
            return
        width={'byte':1,'word':2,'dword':4,'qword':8}[store[1]]
        offset=int(store[3] or '0',0)*(-1 if store[2]=='-' else 1)
        for key in list(state):
            saved=re.fullmatch(r'dword ptr \[ebp(?: ([+-]) (0x[0-9a-f]+|[0-9]+))?\]',key)
            if not saved:continue
            other=int(saved[2] or '0',0)*(-1 if saved[1]=='-' else 1)
            if offset<other+4 and other<offset+width:state.pop(key,None)
    def memory(src, state):
        absolute=re.fullmatch(r'dword ptr \[(0x[0-9a-f]+)\]',src)
        if absolute:
            a=int(absolute[1],16)-DATA_BASE
            if 0<=a<=len(data)-4:return ('code',struct.unpack_from('<I',data,a)[0])
        m=re.fullmatch(r'dword ptr \[(e[a-z]{2})(?: \+ (0x[0-9a-f]+))?\]',src)
        if not m:return None
        base=state.get(m[1]);off=int(m[2] or '0',16)
        if base==('manager',0) and off in windows:return ('window',off)
        if base and base[0]=='window' and off==0:return ('vtable',base[1])
        if base and base[0]=='vtable' and (off in (0x40,0x44) or off in extra.get(base[1],())):return ('method',base[1],off)
        return None
    for start in direct.get(MANAGER,[]):
        # Path-local facts avoid merging an identity from one arm into another.
        first=list(md.disasm(text[start-TEXT_BASE:start-TEXT_BASE+15],start,count=1))
        if not first:continue
        work=[(start+first[0].size,{'eax':('manager',0)},0,start,0)]
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
                if target is None and method and method[0]=='code':target=method[1]
                action=None;slot=None
                if receiver and receiver[0]=='window' and receiver[1] in windows:
                    slot=receiver[1]
                    if target==0xaae767:action='toggle'
                    elif method and method[:2]==('method',slot):action='close' if method[2]==0x44 else 'open'
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
                if value is None and number(src) is not None:value=('code',number(src))
                kill_written(i,state)
                if 'ptr [' in dst:kill_local_write(dst,state)
                state.pop(dst,None)
                if value and (dst in ('eax','ebx','ecx','edx','esi','edi') or re.fullmatch(r'dword ptr \[ebp(?: [+-] (?:0x[0-9a-f]+|[0-9]+))?\]',dst)):
                    state[dst]=value
            else:
                kill_written(i,state)
                # Include exchanged and implicit memory destinations, not only operand zero.
                for index,operand in enumerate(i.operands):
                    if operand.type==X86_OP_MEM and operand.access & CS_AC_WRITE:
                        kill_local_write(parts[index] if index<len(parts) else '',state)
            work.append((nextpc,state,steps+1,scope,depth))
    return sorted(found.values(),key=lambda r:(r['site'],r['manager_slot'],r['action']))


def self_open_slots(text, data, registry):
    """Third pass, step one: window vtable methods that open their own window through `this`.

    Only +0x40/+0x44 were lifecycle slots for the first two passes. A parameterised open is another virtual
    method of the same class which reaches the base open 0x00aae420, the class's own +0x40 method, the
    toggle 0x00aae767 or `call [vtable + 0x40]` with the entry `this` still in ecx. The walk is bounded
    (2,048 bytes, 400 steps and 4,096 states per method, no helper calls); `this` survives only register
    moves and frame saves, any other write kills it and calls clobber eax/ecx/edx. Returns
    {slot: {vtable offset: (method, site, action)}}; a method proves a lifecycle shape, never a caller."""
    md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
    def decode(a,n):return list(md.disasm(text[a-TEXT_BASE:a-TEXT_BASE+n],a))
    frame=r'dword ptr \[ebp - (?:0x[0-9a-f]+|[0-9]+)\]'
    found={}
    for r in registry:
        if not r.get('constructor'):continue
        tables=[number(t.op_str.split(', ')[-1]) for t in decode(r['constructor'],0x100) if
                t.mnemonic=='mov' and re.fullmatch(r'dword ptr \[eax\], 0x[0-9a-f]+',t.op_str)]
        if not tables or not DATA_BASE<=tables[0]<DATA_BASE+len(data):continue
        own=r['lifecycle'][0] if r.get('lifecycle') else None
        for offset in range(0,0x200,4):
            at=tables[0]-DATA_BASE+offset
            if at+4>len(data):break
            method=struct.unpack_from('<I',data,at)[0]
            if not TEXT_BASE<=method<TEXT_BASE+len(text):break
            if offset in (0x40,0x44) or method in (r.get('lifecycle') or ()):continue
            work=[(method,{'ecx':'this'},0)];seen=set()
            while work:
                pc,state,steps=work.pop()
                key=(pc,tuple(sorted(state.items())))
                if key in seen or len(seen)>=4096 or steps>=400 or not method<=pc<method+2048:continue
                seen.add(key)
                seq=decode(pc,15)
                if not seq:continue
                i=seq[0];nextpc=pc+i.size;state=dict(state);parts=i.op_str.split(', ')
                if i.mnemonic in ('ret','retf','int3'):continue
                if i.mnemonic.startswith('j'):
                    target=number(i.op_str)
                    if target is not None:work.append((target,state,steps+1))
                    if i.mnemonic!='jmp':work.append((nextpc,state,steps+1))
                    continue
                if i.mnemonic=='call':
                    target=number(i.op_str);action=None
                    if state.get('ecx')=='this':
                        virtual=re.fullmatch(r'dword ptr \[(e[a-z]{2}) \+ 0x40\]',i.op_str)
                        if target==0xaae767:action='toggle'
                        elif target in (0xaae420,own) and target is not None:action='open'
                        elif virtual and state.get(virtual[1])=='vtable':action='open'
                    if action:found.setdefault(r['slot'],{}).setdefault(offset,(method,pc,action))
                    for reg in ('eax','ecx','edx'):state.pop(reg,None)
                elif i.mnemonic=='mov' and len(parts)==2:
                    dst,src=parts;value=state.get(src)
                    loaded=re.fullmatch(r'dword ptr \[(e[a-z]{2})\]',src)
                    if value is None and loaded and state.get(loaded[1])=='this':value='vtable'
                    if re.fullmatch(r'e[a-z]{2}',dst) or re.fullmatch(frame,dst):
                        state.pop(dst,None)
                        if value:state[dst]=value
                    elif 'ptr [' in dst:
                        # A field of the proved `this` object does not alias the frame; other stores may.
                        field=re.fullmatch(r'(?:byte|word|dword|qword) ptr \[(e[a-z]{2}) \+ (0x[0-9a-f]+|[0-9]+)\]',dst)
                        if not (field and state.get(field[1])=='this' and int(field[2],0)>0):
                            for saved in [k for k in state if k.startswith('dword ptr')]:state.pop(saved)
                    else:
                        for reg in [k for k in state if not k.startswith('dword ptr') and (dst==k or dst==k[1:] or dst in (k[1]+'l',k[1]+'h'))]:state.pop(reg)
                else:
                    _,written=i.regs_access()
                    for reg in written:
                        name=i.reg_name(reg)
                        for full in [k for k in state if not k.startswith('dword ptr')]:
                            if name==full or name==full[1:] or name in (full[1]+'l',full[1]+'h'):state.pop(full)
                    if any(operand.type==X86_OP_MEM and operand.access & CS_AC_WRITE for operand in i.operands):
                        for saved in [k for k in state if k.startswith('dword ptr')]:state.pop(saved)
                work.append((nextpc,state,steps+1))
    return found


def indirect_manager_roots(text, data):
    """Captured absolute pointer calls and register-immediate call encodings."""
    md=Cs(CS_ARCH_X86,CS_MODE_32)
    roots=set()
    for m in re.finditer(b'\xff\x15',text):
        if m.start()+6>len(text):continue
        pointer=struct.unpack_from('<I',text,m.start()+2)[0]-DATA_BASE
        if 0<=pointer<=len(data)-4 and struct.unpack_from('<I',data,pointer)[0]==MANAGER:
            roots.add(TEXT_BASE+m.start())
    for m in re.finditer(bytes([0xb8])+struct.pack('<I',MANAGER),text):
        # The strict adjacent encoding is useful evidence, not all indirect roots.
        if text[m.start()+5:m.start()+7]==b'\xff\xd0':roots.add(TEXT_BASE+m.start()+5)
    return sorted(roots)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    text=pins.TEXT.read();data=pins.DATA.read();registry,old,direct,getters=census(text,data)
    roots=indirect_manager_roots(text,data)
    direct[MANAGER]=sorted(set(direct[MANAGER]+roots))
    rows=indirect_routes(text,data,registry,direct,getters)
    args.out.mkdir(parents=True,exist_ok=True)
    with (args.out/'indirect.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=['site','manager_slot','movie','action','manager_site','encoding']);w.writeheader();w.writerows(rows)
    oldsites={(r['site'],r['manager_slot']) for r in old if r['manager_slot']}
    new=[r for r in rows if (r['site'],r['manager_slot']) not in oldsites]
    # Third pass: parameterised open methods, then manager-qualified virtual calls through their vtable offsets.
    selfopen=self_open_slots(text,data,registry)
    known={(r['site'],r['manager_slot'],r['action']) for r in rows}
    third=[r for r in indirect_routes(text,data,registry,direct,getters,{slot:set(m) for slot,m in selfopen.items()})
           if (r['site'],r['manager_slot'],r['action']) not in known]
    movies={r['slot']:r['movie'] for r in registry}
    with (args.out/'parameterised.csv').open('w') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['kind','manager_slot','movie','action','site','vtable_offset_or_manager_site','method'])
        for slot in sorted(selfopen):
            for offset,(method,site,action) in sorted(selfopen[slot].items()):
                w.writerow(['self-open method',f'0x{slot:x}',movies[slot],action,f'0x{site:08x}',f'+0x{offset:x}',f'0x{method:08x}'])
        for r in third:
            w.writerow(['virtual caller',r['manager_slot'],r['movie'],r['action'],r['site'],r['manager_site'],''])
    summary={'self_open_methods':sum(len(m) for m in selfopen.values()),'parameterised_sites':len(third),
             'parameterised_open_movies':sorted({r['movie'] for r in third}),
             'indirect_manager_roots':len(roots),'paths_from_manager':len(direct[MANAGER]),'joined_sites':len(rows),'additional_sites':len(new),'additional_open_movies':sorted({r['movie'] for r in new if r['action'] in ('open','toggle')})}
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
