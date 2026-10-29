#!/usr/bin/env python3
"""Classify every special body type by executed helper/draw sites, offline.

The eleven original classification states vary level, quality, options, flags
and time. This is a branch-shape survey in the unselected/no-buff domain, not
an exhaustive control-flow proof. Type IDs and code addresses are summaries;
no client bytes or item records are exported.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import struct
import pins
import validate_renderchar as v
ROOT = Path(__file__).resolve().parents[1]

def special_types():
    source = (ROOT/'reconstructed/renderchar/special_types.h').read_text()
    return [t for a,b in re.findall(r'\{(0x[0-9a-f]+), (0x[0-9a-f]+)\}',source)
            for t in range(int(a,16),int(b,16)+1)]

def visibility(t):
    if t>=0x3700:return 'class skin'
    group=(t-0xae6)//512
    return 'weapon' if group<=6 else 'armour' if group<=11 else 'wing' if group==12 else 'pet/item'

def survey(wa):
    from unicorn import UC_HOOK_CODE
    from item_body_machine import ResetWorld

    class Traced(v.World):
        def __init__(self,*args):
            super().__init__(*args)
            self.trace=[]
            def helper(uc,address,size,context):
                m=self.m
                self.trace.append((hex(address),hex(m.r32(m.uc.reg_read(m.x86.UC_X86_REG_ESP)))))
            for address in (0x016e036c,0x016dc148,0x016dec15):
                self.m.uc.hook_add(UC_HOOK_CODE,helper,begin=address,end=address)
            # Record draw caller addresses inside the service handler, before the
            # machine simulates its return. A second hook would see the saved ABI words.
            for address in (0x00966def,0x00966e4a,0x01692eb7,0x0168fafd,0x0150e746):
                old,cleanup=self.m.stubs[address]
                def draw(m,old=old,address=address):
                    self.trace.append((hex(address),'leaf@'+hex(m.r32(m.uc.reg_read(m.x86.UC_X86_REG_ESP)))))
                    return old(m)
                self.m.stub(address,draw,cleanup)

    reset=ResetWorld(wa,Traced)
    def factory(*args):
        world=reset(*args)
        world.trace.clear()
        return world
    rows=[]
    for t in special_types():
        states=[]
        for config in v.CLASSIFY:
            result,stream,other,m=v.client_stream(wa,v.classify_case(t,config),factory)
            trace=list(reset.world.trace)
            if not result['ok']:
                trace.append(('unavailable',result['pc']))
            states.append(trace)
        shape=hashlib.sha256(json.dumps(states).encode()).hexdigest()[:16]
        rows.append({'type':t,'visibility':visibility(t),'shape':shape,'states':states})
        if len(rows)%100==0:print(f'classified {len(rows)}',flush=True)
    return rows


def export_tables(rows, covered, directory):
    groups = collections.defaultdict(list)
    for row in rows:
        groups[row['shape']].append(row)
    def visibility_score(members):
        scores=[]
        for row in members:
            t=row['type']
            if row['visibility']=='class skin':scores.append(0)
            elif row['visibility']=='wing':scores.append(1)
            elif row['visibility'] in ('weapon','armour'):scores.append(1 if (t-0xae6)%512<64 else 2)
            else:scores.append(3)
        return min(scores)
    ordered = sorted(groups.items(), key=lambda item: (-len(item[1]),visibility_score(item[1]),item[0]))
    visible = sorted(groups.items(),key=lambda item: (visibility_score(item[1]),-len(item[1]),item[0]))
    visible_rank={shape:rank for rank,(shape,_) in enumerate(visible,1)}
    membership = ['type\tvisibility\tshape\tbody_implemented\tstopped_states']
    for row in rows:
        stops = sum(any(call[0]=='unavailable' for call in state) for state in row['states'])
        membership.append(f"0x{row['type']:04x}\t{row['visibility']}\t{row['shape']}\t{int(row['type'] in covered)}\t{stops}")
    shapes = ['size_rank\tvisibility_rank\tshape\ttypes\timplemented\tvisibility_counts\thelpers_and_return_sites\tdraw_targets\tstopped_pcs']
    for rank,(shape,members) in enumerate(ordered,1):
        calls = [call for state in members[0]['states'] for call in state]
        helpers = sorted({a+'@'+b for a,b in calls if not b.startswith('leaf@') and a!='unavailable'})
        draws = sorted({a+'@'+b[5:] for a,b in calls if b.startswith('leaf@')})
        stops = sorted({b for a,b in calls if a=='unavailable'})
        counts = collections.Counter(row['visibility'] for row in members)
        shapes.append('\t'.join((str(rank),str(visible_rank[shape]),shape,str(len(members)),
                    str(sum(r['type'] in covered for r in members)),
                    ','.join(f'{key}:{value}' for key,value in sorted(counts.items())),
                    ','.join(helpers) or '-',','.join(draws) or '-',','.join(stops) or '-')))
    (directory/'item-body-types.tsv').write_text('\n'.join(membership)+'\n')
    (directory/'item-body-shapes.tsv').write_text('\n'.join(shapes)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--tables-dir',type=Path,help='write reviewed type and ranked shape summaries')
    a=p.parse_args()
    rows=survey(tuple(pin.read() for pin in (pins.TEXT,pins.DATA,pins.FLAG,pins.FEATURE)))
    a.output.write_text(json.dumps({'text_sha256':pins.TEXT.sha256,'data_sha256':pins.DATA.sha256,
                                   'states':v.CLASSIFY,'rows':rows},indent=2)+'\n')
    if a.tables_dir:
        import gen_item_bodies as gen
        import validate_item_types as old
        import item_pose_machine as pose
        export_tables(rows,set(gen.REVIEWED_TYPES)|set(gen.ADDITIONAL_TYPES)|set(gen.CONTINUATION_TYPES)|set(gen.RANKED_TYPES)|set(gen.EXPANDED_TYPES)|set(gen.NEXT_TYPES)|set(gen.CLOCK_TYPES)|set(gen.CLUSTER_TYPES)|set(gen.WING_TYPES)|set(gen.VISIBLE_TYPES)|set(gen.SCALAR_TYPES)|set(gen.CHAIN_TYPES)|set(gen.LEVEL_TYPES)|set(gen.CARRY_TYPES)|set(gen.COLOUR_TYPES)|set(pose.TYPES)|set(old.BODY)|{0x3895,0x3896,0x389b,0x389c,0x389d,0x389e},a.tables_dir)
    print(f'{len(rows)} types, {len({r["shape"] for r in rows})} shapes')
if __name__=='__main__':main()
