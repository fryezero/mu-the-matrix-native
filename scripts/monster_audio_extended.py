#!/usr/bin/env python3
"""AUDIO-006 semantic partitions for whole world/distance/random sound owners.

The restricted Body checks every instruction before lifting. Random nodes use
signed remainder classes of the LCM of literal divisors, including the signed
remainder-by-two idiom. Nodes preserve conditional RNG consumption and ordered
sound requests. Original execution independently verifies every emitted leaf.
Only authored semantic partitions are emitted, never instruction bytes.
"""
import argparse
import json
import math
from pathlib import Path
import monster_audio_static as lift
import pins
ROOT=Path(__file__).resolve().parents[1]


def recover(text,data):
    nodes=[];intern={};groups={}
    def node(value):
        if value not in intern:intern[value]=len(nodes);nodes.append(value)
        return intern[value]
    for entry,g in lift.owners(data).items():
        if entry not in lift.EXT_OWNERS:continue
        body=lift.Body(text,data,entry,g['worlds'],extended=True)
        period=body.period
        def tree(model,action,frame,tape=()):
            try:
                handled,sounds,used=body.run(model,action,frame,tape)
                assert used==len(tape)
                assert len(sounds)<=4
                return node(('leaf',handled,tuple(sounds)))
            except lift.NeedRandom:
                assert len(tape)<2,'unreviewed RNG depth'
                children=tuple(tree(model,action,frame,tape+(n,)) for n in range(1-period,period))
                # Even an identical outcome consumes the original RNG call.
                return node(('random',period,children))
        default=tree(-1,65535,math.nan);rows=[];reached=set()
        models={-1,0,0x7fffffff}
        for n in body.constants:
            if 0x7a5<=n<0x9fe:models.update(range(n,n+65))
        actions=range(32)
        bounds=[-math.inf]+sorted(body.float_constants)+[math.inf]
        spans=[]
        for lo,hi in zip(bounds,bounds[1:]):
            if lo<hi:spans.append((lo,hi,False,False,hi-1 if lo==-math.inf else lo+1 if hi==math.inf else (lo+hi)/2))
        spans += [(f,f,True,True,f) for f in sorted(body.float_constants)]
        def add(model,action,lo,hi,lc,hc,nan,root):
            rows.append(dict(model=model,action=action,lo=lo,hi=hi,lc=lc,hc=hc,nan=nan,node=root))
        for model in sorted(models):
            md=tree(model,65535,math.nan)
            if md!=default:add(model,-1,-math.inf,math.inf,True,True,2,md)
            for action in actions:
                ad=tree(model,action,math.nan)
                if ad!=md:add(model,action,-math.inf,math.inf,True,True,2,ad)
                for lo,hi,lc,hc,f in spans:
                    root=tree(model,action,f)
                    if root!=ad:add(model,action,lo,hi,lc,hc,0,root)
        def visit(n):
            v=nodes[n]
            if v[0]=='leaf':reached.update(s[0] for s in v[2])
            else:
                for child in set(v[2]):visit(child)
        visit(default)
        for r in rows:visit(r['node'])
        assert reached==body.sites,(hex(entry),body.sites-reached)
        groups[entry]=dict(g,rows=rows,default=default,end=body.end,sites=sorted(reached),period=period,
                           models=sorted(models),frames=sorted(body.float_constants),
                           distance=600.0 if entry==0xe1829b else 500.0 if any(i.op_str=='0x961a07' for i in body.code.values()) else math.inf)
    return groups,nodes


def production_sounds(groups,nodes):
    """Nonnegative CRT-rand outcomes. Negative tapes are arithmetic controls."""
    seen=set();sounds=set()
    def visit(n):
        if n in seen:return
        seen.add(n);value=nodes[n]
        if value[0]=='leaf':sounds.update(value[2])
        else:
            for child in set(value[2][value[1]-1:]):visit(child)
    for group in groups.values():
        visit(group['default'])
        for row in group['rows']:visit(row['node'])
    return sounds


def emit(groups,nodes):
    out=['/* AUDIO-006: whole-owner semantic plans; monster_audio_extended.py. */']
    def f(x):return ('-INFINITY' if x<0 else 'INFINITY') if math.isinf(x) else float(x).hex()+'f'
    # Each node is a leaf or an RNG decision with remainder-indexed edges.
    edges=[];sounds=[]
    for n,v in enumerate(nodes):
        if v[0]=='leaf':
            start=len(sounds);sounds.extend((n,*s) for s in v[2])
            out.append(f'MU_AUDIO_EXT_NODE({n}, 0, {v[1]}, {start}, {len(v[2])})')
        else:
            start=len(edges);edges.extend(v[2]);out.append(f'MU_AUDIO_EXT_NODE({n}, {v[1]}, 0, {start}, {len(v[2])})')
    for n,child in enumerate(edges):out.append(f'MU_AUDIO_EXT_EDGE({n}, {child})')
    for n,(site,sound,obj,loop) in enumerate(s[1:] for s in sounds):
        # The owning routine is resolved by the selected world group.
        out.append(f'MU_AUDIO_EXT_SOUND({n}, 0x{site:08x}u, {sound}, {obj}, {loop})')
    # Sound sites retain their independent original return address.
    for entry,g in sorted(groups.items()):
        for world in g['worlds']:out.append(f'MU_AUDIO_EXT_WORLD({world}, 0x{entry:08x}u, {g["default"]}, {f(g["distance"])})')
        for r in g['rows']:
            out.append(f'MU_AUDIO_EXT_ROW(0x{entry:08x}u, {r["model"]}, {r["action"]}, {f(r["lo"])}, {f(r["hi"])}, {int(r["lc"])}, {int(r["hc"])}, {r["nan"]}, {r["node"]})')
    for site,sound,obj,loop in sorted(production_sounds(groups,nodes)):
        out.append(f'MU_AUDIO_EXT_PRODUCTION_ID(0x{site:08x}u, {sound})')
    return '\n'.join(out)+'\n'


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--emit-c',type=Path);ap.add_argument('--report',type=Path);a=ap.parse_args()
    groups,nodes=recover(pins.TEXT.read(),pins.DATA.read())
    if a.emit_c:a.emit_c.write_text(emit(groups,nodes))
    report={hex(e):dict(worlds=g['worlds'],sites=len(g['sites']),rows=len(g['rows']),period=g['period']) for e,g in groups.items()}
    if a.report:a.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
