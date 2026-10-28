#!/usr/bin/env python3
"""WORLD-ORDER-001. Compare compiled call-order C with original x86 control flow.

The scene-manager host carries order-only records: routine/import identity,
virtual slot, and the draw result. Callee bodies, argument/ECX values, general
writes, exception unwinding, and the first-tick packet interval are outside
this contract. The packet interval is one opaque NET_SEND event, as in the
scene-manager family. No native renderer links this reconstruction.
"""
import argparse
import ctypes as C
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pins
import client_ui_machine as cm
from validate_scene import Host, CALLFN, PEEKFN, POKEFN

SOURCE = ROOT / 'reconstructed/world-order/world_order.c'
ROUTINES = {'tick': (0x0185613e, 0x01856e6c), 'draw': (0x0185916b, 0x01859d8a)}
BODIES = {
    'tick': '7d3c2026725a7475ad8421a22ade918117a811c8c7642ae0931e999e78a764aa',
    'draw': '0aeff15d740944d4447d0b0c52d72ce4c280a52e391e4f1022d1b93f3f2d2c99',
    'stack_probe': '0f8ce31cd9b1ce0c271e496c2447217aee128105e3fb255669f8cb2607ef4519',
}
RECT_CONSTANTS = (0x1af7098, 0x1aae3f0, 0x1af70a0, 0x1af70a4)
NET_SEND, VCALL = 0x4e455453, 0x56434c4c
HEAP = cm.HEAP_BASE
CHARACTER = HEAP + 0x400
VECTOR = HEAP + 0x500
# Callee stack cleanup, verified from terminal RETs; this family never executes
# callees. Nonlisted direct calls are cdecl or zero-word thiscalls.
POPS = {0x94997e:4, 0x95c5da:4, 0x9a13f4:4, 0x99b4c0:4, 0x9d3e63:4,
        0xa75708:12, 0xac9613:4, 0xacbb85:4, 0xc0bd87:4, 0xc8dbdd:4,
        0xcfc8f2:4, 0xcfc922:4, 0xd03ee9:8, 0xec3394:4, 0x106bcc5:4,
        0x106be65:4, 0x1206aac:4, 0x129debb:4, 0x150e599:4, 0x15181fa:4,
        0x159123f:4, 0x169159e:4, 0x169270e:4,
        0x1a7c7d8:4, 0x1a7c758:4, 0x1a7c6cc:16}
POINTERS = {0x95f6db, 0x9a13f4, 0xac3bf7, 0xf2bb92, 0xf2bf8b, 0x98647b,
            0x95c5da, 0xacbb85, 0x95f7df, 0xcfc922, 0xcfc94a, 0x9a6ef3,
            0xf2c012, 0xf2c05d, 0xaee554, 0xcd4ea8, 0xcd5d29}
PREDICATES = [0x9dad09, 0x9d3e63, 0x9dacb8, 0xdfbbbb, 0xd61f81, 0xdabe97,
              0xea233c, 0xe42f6d, 0xe94004, 0xe3068f, 0xdd38c5, 0xdd897d,
              0xdde62f, 0xde5519, 0xe6eccc, 0xe1e4b6, 0x16a8325, 0xe45d40,
              0xe0558b, 0xea2761, 0xdeeaff, 0x9a645f, 0x99b3b1, 0x185498e,
              0x129debb, 0xaae6f9, 0xda9d49, 0xf2b602, VCALL + 0x18]
WORLDS = [-1, 0, 1, 2, 3, 6, 7, 10, 24, 29, 30, 36, 39, 42, 44, 45, 50, 51,
          63, 82, 90, 95, 96, 100, 101, 110, 111, 113, 114, 121, 122, 132, 133, 134]
GLOBALS = {0xbdc5ca3:(1,1), 0x6fca2c4:(4,0x3d), 0xbdc5eb8:(1,1),
           0xbdc58b7:(1,0), 0xb437c14:(4,0), 0x1cf15fc:(4,1), 0xb437c10:(4,4),
           0xbdc5adc:(4,480), 0xbdc5ad8:(4,640), 0xbdc5eb4:(4,0),
           0xbdc5981:(1,0), 0x6fbcd8c:(4,0), 0x1d22c6c:(4,HEAP),
           0x6fc9c94:(4,0), 0x1d1df18:(4,HEAP), 0x1d1df70:(4,6),
           0xbdb588c:(4,0), 0x1cf103c:(4,0x3dcccccd), 0x6fc9eb0:(4,HEAP),
           0xa39d754:(4,HEAP), 0xb437bfc:(4,0), 0x1cf1864:(4,0),
           0xbdc58f0:(4,0), 0xbdc58f4:(4,0)}


def build(directory, source=SOURCE):
    lib = Path(directory) / ('order.dylib' if sys.platform == 'darwin' else 'order.so')
    subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wconversion',
                    '-fPIC', '-fno-fast-math', '-shared', '-I', str(SOURCE.parent), str(source), '-o', str(lib)], check=True)
    out = C.CDLL(str(lib))
    out.mu_world_order_tick.argtypes = [C.POINTER(Host)]
    out.mu_world_order_tick.restype = None
    out.mu_world_order_draw.argtypes = [C.POINTER(Host)]
    out.mu_world_order_draw.restype = C.c_int
    return out


def put(memory, address, value, size=4):
    for i in range(size): memory[address+i] = (value >> (8*i)) & 255


def case(**kwargs):
    memory = dict.fromkeys(range(HEAP, HEAP+0x800), 0)
    for a,(s,v) in GLOBALS.items(): put(memory,a,v,s)
    for offset in (0, 8, 0xc, 0x10, 0x88, 0x128, 0x220, 0x240, 0x254, 0x2ac): put(memory, HEAP+offset, HEAP)
    for a,v in kwargs.get('memory', {}).items(): put(memory,a,v, GLOBALS.get(a,(4,0))[0])
    return {'memory':memory, 'returns':kwargs.get('returns', {}), 'label':kwargs.get('label','baseline')}


class RecordingHost:
    def __init__(self, spec):
        self.memory = dict(spec['memory'])
        self.returns = spec['returns']
        self.counts = Counter()
        self.trace = []
        self.host = Host(None, CALLFN(self.call), PEEKFN(self.peek), POKEFN(self.poke))
        self.errors = []

    def result(self, routine, slot=0):
        key = routine + slot if routine == VCALL else routine
        k = self.counts[key]; self.counts[key] += 1
        default = CHARACTER if routine == 0x9a13f4 else VECTOR if routine == 0xcfc94a else HEAP if routine in POINTERS else 0
        value = self.returns.get(key, default)
        return value[min(k,len(value)-1)] if isinstance(value,list) else value

    def call(self, user, pointer):
        c = pointer.contents
        slot = c.args[0] if c.routine == VCALL else 0
        self.trace.append((c.routine, slot))
        return self.result(c.routine, slot)

    def peek(self, user, address, size):
        try: return int.from_bytes(bytes(self.memory[address+i] for i in range(size)), 'little')
        except KeyError:
            self.errors.append(f'undefined native read {address:#x}/{size}')
            return 0

    def poke(self, user, address, value, size): put(self.memory,address,value,size)

    def run(self, lib, family):
        result = getattr(lib, 'mu_world_order_'+family)(C.byref(self.host))
        if self.errors: raise RuntimeError(self.errors[0])
        return result if family == 'draw' else None


class Original:
    def __init__(self, text, data):
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        self.m = cm.Machine(text,data)
        self.instructions = {}
        md = Cs(CS_ARCH_X86, CS_MODE_32)
        for start,end in ROUTINES.values():
            for i in md.disasm(text[start-cm.TEXT_BASE:end-cm.TEXT_BASE], start):
                self.instructions[i.address] = (i.size, i.mnemonic, i.op_str)
        self.m.uc.hook_add(cm.UC_HOOK_CODE, self.hook)
        self.edges = Counter()
        self.visited = set()
        self.pending = None

    def hook(self, uc, address, size, user):
        if address not in self.instructions: return
        if self.pending is not None:
            self.edges[(self.pending,address)] += 1
            self.pending = None
        self.visited.add(address)
        size, op, arg = self.instructions[address]
        if op.startswith('j') and op != 'jmp': self.pending = address
        if address == 0x0185627f:
            self.host.trace.append((NET_SEND,0))
            uc.reg_write(cm.UC_X86_REG_EIP, 0x0185636c)
            return
        if op != 'call': return
        # __chkstk executes as original instructions. Every external call is
        # observed at the call site and returns from an opaque recording host.
        if arg == '0x191c5a0': return
        slot = 0
        if arg.startswith('0x'): target = int(arg,16)
        elif arg.startswith('dword ptr [0x'): target = int(arg[11:-1],16)
        elif arg in ('dword ptr [eax + 4]', 'dword ptr [eax + 0x18]', 'dword ptr [eax]'):
            target = VCALL
            slot = {'dword ptr [eax + 4]':4, 'dword ptr [eax + 0x18]':0x18, 'dword ptr [eax]':0}[arg]
        else: raise RuntimeError(f'unhandled call {address:#x}: {arg}')
        self.host.trace.append((target,slot))
        value = self.host.result(target,slot)
        esp = uc.reg_read(cm.UC_X86_REG_ESP)
        if target in (0x95c5da, 0xacbb85):
            out = self.m.u32(esp)
            ref = self.host.peek(None,HEAP+4,4)
            object_value = self.host.peek(None,HEAP+8,4) if target == 0xacbb85 else HEAP
            self.m.write(out,struct.pack('<II',object_value,ref))
        if target == 0xec3394: self.m.write(self.m.u32(esp),bytes(12))
        if target == 0x99b4c0: self.m.write(self.m.u32(esp),bytes(12))
        cleanup = POPS.get(target,4 if target == VCALL and slot == 4 else 0)
        uc.reg_write(cm.UC_X86_REG_EAX,value & 0xffffffff)
        uc.reg_write(cm.UC_X86_REG_ESP,esp+cleanup)
        uc.reg_write(cm.UC_X86_REG_EIP,address+size)

    def run(self, spec, family):
        self.host = RecordingHost(spec)
        m = self.m; m.reset()
        m.allowed = [ROUTINES[family],(0x191c5a0,0x191c5e0)]
        self.pending = None
        # Only explicit seeded bytes are defined. cm rejects all other global
        # and heap reads, including reads not anticipated by this model.
        for a,v in spec['memory'].items(): m.write(a,bytes([v]))
        # Captured floats used by the rectangle conditions also feed C.
        result = m.call(ROUTINES[family][0], [])
        if self.host.errors:
            raise RuntimeError(self.host.errors[0])
        return self.host.trace, (result & 255 if family == 'draw' else None)


def cases(count, seed, rectangle=None):
    out = []
    def add(label, memory=None, returns=None): out.append(case(label=label,memory=memory or {},returns=returns or {}))
    add('ordinary')
    add('not-ready', {0xbdc5eb8:0,0x6fca2c4:0})
    for world in WORLDS:
        for tile in (2,3,4,9,10): add(f'world-{world}-tile-{tile}', {0x1cf15fc:world,0xb437c10:tile})
    for p in PREDICATES:
        for value in (1,2,0x100): add(f'callee-{p:x}-{value}',returns={p:value})
    for a,values in {0xbdc5ca3:[0],0x6fca2c4:[0,0x3c,0x3d],0xbdc5eb8:[0],
                     0xbdc58b7:[1],0xb437c14:[29,30,31],0xbdc5eb4:[110],
                     0xb437bfc:[1],0xbdc5981:[1],0xbdc5adc:[479],HEAP+8:[0],CHARACTER+0x12:[1],HEAP+0x71:[1]}.items():
        for v in values: add(f'global-{a:x}-{v}',{a:v})
    for ready in (0,1):
        for selected in (0,HEAP):
            for ref in (0,1):
                add('first-tick', {0xbdc5ca3:0,0xbdc5eb8:ready,HEAP+4:ref}, {0x9a13f4:[selected,CHARACTER]})
    add('first-tick-null-output', {0xbdc5ca3:0,HEAP+8:0})
    for aa in ([0,0],[1,0],[1,1],[2,2]): add('ui-refusal', returns={0xaae6f9:aa})
    for pick in (0xffffffff,0,42): add('pick',returns={0x16b47bf:pick})
    for world in (6,30):
        for camera in (0,1,2):
            for name in ([0,0,0],[1,0,1],[0,1,0]):
                add('camera', {0x1cf15fc:world},{0x185498e:camera,0x129debb:name})
    for tile in (3,10):
        add('devias-second-pass', {0x1cf15fc:2,0xb437c10:tile}, {0xdeeaff:1})
    for flag in (0,1):
        for active in (0,1):
            add('focus',{0xbdc5981:1,0x6fbcd8c:flag},{0x1a7c840:active})
    if rectangle:
        low_x, high_x, low_y, other_y = rectangle
        def bits(f): return struct.unpack('<I', struct.pack('<f', f))[0]
        for x in (low_x-1, low_x, (low_x+high_x)/2, high_x, high_x+1, float('nan')):
            for y in (low_y-1, low_y, other_y-1, other_y, max(low_y,other_y)+1, float('nan')):
                add('castle-rectangle', {0x1cf15fc:30,VECTOR:bits(x),VECTOR+4:bits(y)})
    g=random.Random(seed)
    while len(out)<count:
        mem={0x1cf15fc:g.choice(WORLDS),0xb437c10:g.choice([2,3,4,9,10]),
             0xbdc58b7:g.randrange(2),0xb437c14:g.choice([0,29,30,31]),
             0xbdc5981:g.randrange(2),0xbdc5ca3:g.choice([0,1,1,1]),
             0xbdc5eb8:g.randrange(2),0x6fca2c4:g.choice([0,0x3c,0x3d]),HEAP+4:g.randrange(2),
             HEAP+0x66:g.randrange(2),HEAP+0x71:g.randrange(2),CHARACTER+0x12:g.randrange(2)}
        ret={p:g.choice([0,0,0,1,2,0x100]) for p in PREDICATES}
        ret[0x16b47bf]=g.choice([0xffffffff,0,7])
        add('random',mem,ret)
    return out


def compare(original, lib, specs, family):
    result = {'cases':len(specs),'equal':0,'mismatches':0,'stopped':0,'calls':0,'examples':[]}
    for spec in specs:
        try:
            trace, ret = original.run(spec,family)
            host=RecordingHost(spec)
            # Captured constants remain local inputs, never authored fixtures.
            for a in RECT_CONSTANTS:
                put(host.memory,a,original.m.u32(a))
            native_ret=host.run(lib,family)
            result['calls']+=len(trace)
            if trace == host.trace and ret == native_ret: result['equal']+=1
            else:
                result['mismatches']+=1
                if len(result['examples'])<3:
                    k=next((i for i,(a,b) in enumerate(zip(trace,host.trace)) if a!=b),min(len(trace),len(host.trace)))
                    result['examples'].append({'label':spec['label'],'index':k,'client':trace[max(0,k-2):k+3],
                                               'native':host.trace[max(0,k-2):k+3],'return':[ret,native_ret]})
        except (cm.CaseError,RuntimeError) as e:
            result['stopped']+=1
            if len(result['examples'])<3: result['examples'].append({'label':spec['label'],'error':str(e)})
    return result

MUTANTS = [
 ('swap hero/characters','0x016a9150, 0x0137a7ce','0x0137a7ce, 0x016a9150','tick'),
 ('drop objects','call(h, 0x016d82c7);','/* dropped objects */','tick'),
 ('drop ready branch','if (!byte(h, 0x0bdc5eb8)) return;','if (0) return;','tick'),
 ('drop first-tick selection branch','if (selected) SEQ(0x0129deaa, 0x008e7f90, 0x01206598);','if (0) SEQ(0x0129deaa, 0x008e7f90, 0x01206598);','tick'),
 ('broaden leaf guard','w == 0 && tile != 4','w == 0','tick'),
 ('drop top second pass','if (low_call(h, 0x00deeaff) == 1) {','if (low_call(h, 0x00deeaff) == 77) {','draw'),
 ('swap objects/terrain','if (first) call(h, 0x016d5020);\n            call(h, 0x016cd468);',
  'call(h, 0x016cd468);\n            if (first) call(h, 0x016d5020);','draw'),
 ('draw Icarus terrain','w != 10 && w != 132','w != 132','draw'),
 ('reverse castle upper bound','real(h, 0x01af70a4) >= y','y >= real(h, 0x01af70a4)','draw'),
 ('drop GFx refusal','if (!low_call(h, 0x00aae6f9)) SEQ','if (low_call(h, 0x00aae6f9)) SEQ','draw'),
]


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--text',default=pins.TEXT.default_str());p.add_argument('--data',default=pins.DATA.default_str())
    p.add_argument('--cases',type=int,default=1200);p.add_argument('--seed',type=int,default=0x20261028)
    p.add_argument('--mutations',action='store_true');p.add_argument('--output')
    args=p.parse_args(argv)
    text=pins.load(args.text,pins.TEXT.size,pins.TEXT.sha256);data=pins.load(args.data,pins.DATA.size,pins.DATA.sha256)
    body_report = {}
    for name, (start, end) in {**ROUTINES, 'stack_probe': (0x191c5a0,0x191c5e0)}.items():
        digest = hashlib.sha256(text[start-cm.TEXT_BASE:end-cm.TEXT_BASE]).hexdigest()
        if digest != BODIES[name]: raise ValueError(f'body pin changed: {name}')
        body_report[name] = {'start':hex(start),'end_exclusive':hex(end),'sha256':digest}
    original=Original(text,data)
    rectangle = [struct.unpack('<f',data[a-cm.DATA_BASE:a-cm.DATA_BASE+4])[0] for a in RECT_CONSTANTS]
    specs=cases(args.cases,args.seed,rectangle)
    report={'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,'seed':args.seed,'bodies':body_report,
            'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'validator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'families':{}}
    with tempfile.TemporaryDirectory(prefix='mu-world-order-') as temp:
        lib=build(temp)
        for name in ROUTINES:
            r=compare(original,lib,specs,name);report['families'][name]=r;print(name,json.dumps(r))
        report['branch_coverage'] = {}
        for family,(start,end) in ROUTINES.items():
            edges = {(a,destination) for a,(size,op,arg) in original.instructions.items()
                     if start <= a < end and op.startswith('j') and op != 'jmp'
                     for destination in (a+size,int(arg,16))}
            covered = edges & set(original.edges)
            report['branch_coverage'][family] = {
                'covered_edges':len(covered),'decoded_edges':len(edges),
                'uncovered':[[hex(a),hex(b)] for a,b in sorted(edges-covered)]}
        if args.mutations:
            report['mutations']=[]
            for index,(label,old,new,family) in enumerate(MUTANTS):
                source=SOURCE.read_text();assert source.count(old)==1,(label,source.count(old))
                directory=Path(temp)/str(index);directory.mkdir();path=directory/'mutant.c';path.write_text(source.replace(old,new))
                r=compare(original,build(directory,path),specs[:400],family)
                row={'name':label,'cases':r['cases'],'detected':r['mismatches'],'stopped':r['stopped']}
                report['mutations'].append(row);print('mutation',json.dumps(row))
    report['ok']=all(r['mismatches']==r['stopped']==0 for r in report['families'].values())
    report['ok'] &= all(not r['uncovered'] for r in report['branch_coverage'].values())
    print('branch coverage',json.dumps(report['branch_coverage']))
    if args.mutations:report['ok'] &= all(r['detected']>0 and r['stopped']==0 for r in report['mutations'])
    if args.output: Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['ok'] else 1

if __name__ == '__main__': sys.exit(main())
