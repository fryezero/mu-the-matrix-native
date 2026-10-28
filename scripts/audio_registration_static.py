#!/usr/bin/env python3
"""Lift ordered audio registration calls, never filenames, from pinned instructions.

The actor lifter executes the two constant per-type switches. The earlier model
switch and NPC model switch have straight-line audio calls in each case interval.
The separate Unicorn validator checks this claim over every type, including the
preloaded/no-model exits. Output is authored C with ids and call-site provenance.
"""
from pathlib import Path
import argparse
import pins
import actor_static as a

def registrations(image):
    class Audio(a.Lifter):
        def call(self, target, nxt):
            if target == 0xa6ab76:
                args = list(reversed(self.stack))
                self.audio.append((self.pc, args[0][1], args[2][1], args[3][1]))
            return super().call(target, nxt)
    monsters = {}
    for t in range(a.MONSTER_TYPES):
        lift = Audio(image,t); lift.audio = []; lift.run()
        monsters[t] = lift.audio
    def waves(lo,hi):
        out=[]; pc=lo; instructions=[]
        while pc<hi:
            i=image.instruction(pc); instructions.append(i);pc+=i.size
            if i.mnemonic=='call' and i.op_str=='0xa6ab76':
                out.append((i.address,int(instructions[-2].op_str,0),
                            int(instructions[-5].op_str,0),int(instructions[-6].op_str,0)))
        return out
    starts = {t:image.u32(0x181f25c+4*image.read(0x181f27c+t-0x114,1)[0]) for t in range(0x114,0x124)}
    starts.update({0x124:0x180b4e9,0x125:0x180b603})
    ordered=sorted(set(starts.values())|{0x180cc00})
    for t,start in starts.items():
        if start<0x180cc00:
            monsters[t] = waves(start,ordered[ordered.index(start)+1]) + monsters[t]
    starts={t:image.u32(0x180ae20+4*(t-0x9fe)) for t in range(0x9fe,0xa90)}
    ordered=sorted(set(starts.values())|{0x180a9de})
    npcs={t:waves(start,ordered[ordered.index(start)+1]) if start<0x180a9de else [] for t,start in starts.items()}
    return monsters,npcs

def emit(image):
    monsters,npcs=registrations(image)
    out=['/* AUDIO-002: ordered SND_Load calls, ids + source sites only. No client paths. */']
    for name,rows in [('monster',monsters),('npc',npcs)]:
        out += [f'void mu_audio_register_{name}(int32_t type, int preloaded,',
                '    void (*load)(void *, uint32_t, int32_t, int32_t, int32_t), void *ctx)',
                '{', '    if (preloaded || !load) return;', '    switch (type) {']
        for t, calls in rows.items():
            if not calls: continue
            out += [f'    case {t}:']
            for site,id,ch,flag in calls:
                out += [f'        load(ctx, 0x{site:08x}u, {id}, {ch}, {flag});']
            out += ['        break;']
        out += ['    default: break;', '    }', '}', '']
    return '\n'.join(out)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);args=p.parse_args()
    Path(args.out).write_text(emit(a.Image(pins.TEXT.read(),pins.DATA.read())))
