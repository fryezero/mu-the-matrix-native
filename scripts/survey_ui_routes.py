#!/usr/bin/env python3
"""Static UI lifecycle census over pinned text/data, never a runtime route oracle.

Direct relative calls are exhaustively searched for registered lifecycle targets.
Virtual +0x40/+0x44 encodings are candidates, since those slots have other owners.
Receiver joins require the manager getter in the same straight instruction span.
Unresolved indirect calls and computed IDs remain explicit, never guessed.
Outputs contain addresses and reviewed classifications only, no captured bytes.
"""
import argparse
import csv
import json
import re
import struct
from pathlib import Path

import pins
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

TEXT_BASE = 0x401000
DATA_BASE = 0x1a7c000
MANAGER = 0xac3bf7
REGISTRARS = {0xac9d74, 0xac9e28}


def number(s):
    try:
        return int(s, 0)
    except ValueError:
        return None


def census(text, data):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    def decode(a, n):
        return list(md.disasm(text[a-TEXT_BASE:a-TEXT_BASE+n], a))
    def string(a):
        if not DATA_BASE <= a < DATA_BASE+len(data):
            return ''
        return data[a-DATA_BASE:a-DATA_BASE+120].split(b'\0')[0].decode('ascii', errors='replace')
    registry = []
    # A single straight constructor registers the world controllers. Front-end,
    # dynamically registered and old NewUI windows are separate inventories.
    ins = decode(0xac4a79, 0x4b00)
    for k, i in enumerate(ins):
        if i.mnemonic != 'call' or number(i.op_str) not in REGISTRARS:
            continue
        prev = ins[max(0, k-30):k]
        fields = [j for j in prev[-4:] if j.mnemonic == 'push' and
                  re.fullmatch(r'dword ptr \[eax \+ 0x[0-9a-f]+\]', j.op_str)]
        if not fields:
            continue
        off = int(re.search(r'0x[0-9a-f]+', fields[-1].op_str)[0], 16)
        names = [(j, string(number(j.op_str))) for j in prev if j.mnemonic == 'push' and number(j.op_str) is not None]
        names = [(j, s) for j, s in names if s and re.fullmatch(r'[A-Za-z_0-9]+', s)]
        if not names:
            continue
        j, name = names[-1]
        # Last constructor call before storing the new controller in the manager.
        ctors = [t for t in prev if t.mnemonic == 'call' and t.address < j.address and
                 number(t.op_str) not in (0x40c8d0, 0x191ba7b) and number(t.op_str) not in REGISTRARS]
        ctor = number(ctors[-1].op_str) if ctors else None
        vtables = [number(t.op_str.split(', ')[-1]) for t in decode(ctor, 0x100) if
                   t.mnemonic == 'mov' and re.fullmatch(r'dword ptr \[eax\], 0x[0-9a-f]+', t.op_str)] if ctor else []
        vt = vtables[0] if vtables else None
        lifecycle = []
        if vt and DATA_BASE <= vt and vt+0x48 <= DATA_BASE+len(data):
            lifecycle = list(struct.unpack_from('<2I', data, vt-DATA_BASE+0x40))
        registry.append(dict(movie=name+'.swf', slot=off, registration=i.address,
                             name_reference=j.address, constructor=ctor, lifecycle=lifecycle))
    # Exact tiny thiscall getters, qualified at use by an immediately preceding
    # manager call. Identical field offsets in unrelated classes do not join.
    getters = {}
    for match in re.finditer(b'\x55\x8b\xec\x51\x89\x4d\xfc\x8b\x45\xfc', text):
        a = TEXT_BASE+match.start()
        got = decode(a, 24)
        if len(got) < 8 or got[5].mnemonic != 'mov':
            continue
        m = re.fullmatch(r'eax, dword ptr \[eax \+ (0x[0-9a-f]+)\]', got[5].op_str)
        if m and got[6].mnemonic == 'leave' and got[7].mnemonic == 'ret':
            getters[a] = int(m[1], 16)
    direct = {}
    for match in re.finditer(b'\xe8', text):
        p = match.start()
        if p+5 <= len(text):
            target = TEXT_BASE+p+5+struct.unpack_from('<i', text, p+1)[0]
            direct.setdefault(target, []).append(TEXT_BASE+p)
    targets = {0xaae767: 'toggle', 0xac9c74: 'close-all'}
    for r in registry:
        for target, action in zip(r['lifecycle'], ('open', 'close')):
            if TEXT_BASE <= target < TEXT_BASE+len(text):
                targets.setdefault(target, action)
    candidates = {}
    for target, action in targets.items():
        for a in direct.get(target, []):
            candidates[a] = (action, target)
    # All register-base virtual encodings at +40/+44, including disp32 forms.
    # The receiver can belong to another class; candidate status is retained.
    for match in re.finditer(rb'\xff[\x50-\x57\x90-\x97]', text):
        a = TEXT_BASE+match.start()
        got = decode(a, 7)
        if got and got[0].mnemonic == 'call' and re.fullmatch(r'dword ptr \[e[a-z]{2} \+ 0x(40|44)\]', got[0].op_str):
            candidates.setdefault(a, ('virtual-open-candidate' if '0x40' in got[0].op_str else 'virtual-close-candidate', None))
    managers = direct.get(MANAGER, [])
    import bisect
    sites = []
    for a, (action, target) in sorted(candidates.items()):
        # Only walk forward from an actual manager-getter call. No nearest
        # constant heuristic, and no state carried across a branch or call.
        slot = None
        p = bisect.bisect_left(managers, a)
        for start in reversed(managers[max(0, p-4):p]):
            if a-start > 160:
                break
            seq = decode(start, a-start+7)
            regs, locals_ = {}, {}
            valid = False
            for i in seq:
                if i.address == a:
                    valid = True
                    slot = regs.get('ecx', ('unknown', None))[1] if regs.get('ecx', ('',))[0] == 'window' else None
                    break
                if i.mnemonic.startswith('j') or i.mnemonic in ('ret', 'leave'):
                    break
                if i.mnemonic == 'call':
                    t = number(i.op_str)
                    receiver = regs.get('ecx')
                    regs = {k:v for k,v in regs.items() if k not in ('eax','ecx','edx')}
                    if t == MANAGER:
                        regs['eax'] = ('manager', None)
                    elif t in getters and receiver == ('manager', None):
                        regs['eax'] = ('window', getters[t])
                    else:
                        break
                elif i.mnemonic == 'mov':
                    parts = i.op_str.split(', ')
                    if len(parts) != 2:
                        continue
                    dest, src = parts
                    value = regs.get(src, locals_.get(src, ('unknown', None)))
                    m = re.fullmatch(r'dword ptr \[(e[a-z]{2}) \+ (0x[0-9a-f]+)\]', src)
                    if m and regs.get(m[1]) == ('manager', None):
                        value = ('window', int(m[2],16))
                    if dest.startswith('dword ptr [ebp'):
                        locals_[dest] = value
                    else:
                        regs[dest] = value
            if valid and slot is not None:
                break
        sites.append(dict(site=f'0x{a:08x}', action=action, target=f'0x{target:08x}' if target else '',
                          manager_slot=f'0x{slot:x}' if slot is not None else '',
                          receiver='manager-window' if slot is not None else 'unresolved'))
    return registry, sites, direct, getters


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True, help='private report directory')
    args = ap.parse_args()
    registry, sites, direct, getters = census(pins.TEXT.read(), pins.DATA.read())
    args.out.mkdir(parents=True, exist_ok=True)
    for name, rows in [('registry',registry), ('services',sites)]:
        with (args.out/(name+'.csv')).open('w') as f:
            w = csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    summary = dict(registrations=len(registry), services=len(sites),
                   manager_receivers=sum(s['receiver']=='manager-window' for s in sites),
                   direct_toggle_calls=len(direct.get(0xaae767, [])),
                   unresolved_receivers=sum(s['receiver']=='unresolved' for s in sites),
                   text_sha256=pins.TEXT.sha256,data_sha256=pins.DATA.sha256)
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
