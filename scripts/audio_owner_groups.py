#!/usr/bin/env python3
"""AUDIO-006: semantic ownership evidence and disjoint admission blockers.

A controller vtable or an exact character-timeline caller identifies ownership,
never gates or native delivery. Prologue and sound-id guesses are excluded.
"""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re
import struct
import pins
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
ROOT=Path(__file__).resolve().parents[1]
# Exact character/OBJECT/model argument calls from the shared timeline owner.
TIMELINES={0x13a9051:0x13a09d7,0x13a0b13:0xdf264e,0x13a0bc7:0xe8cc72,0x13a0be5:0xdb30cb}
EXTENDED={0xe9e3d5,0xe92b75,0xe30389,0xdd2776,0xe1829b,0xe21d13,0xd8aba2,0xe4b1c3}
DELEGATED={0xdd852c,0xdde1fb,0xde51cf,0xd7ec63}
MARKERS={0xdee2d1,0xe0dac7,0xda9350}
STOP={0xd5b688}


def semantic_owners(text,data):
    import survey_ui_routes as ui
    md=Cs(CS_ARCH_X86,CS_MODE_32)
    def decode(entry,size):return list(md.disasm(text[entry-ui.TEXT_BASE:entry-ui.TEXT_BASE+size],entry))
    owners={};evidence=[]
    for site,target in TIMELINES.items():
        ins=decode(site,5)
        assert len(ins)==1 and ins[0].mnemonic=='call' and int(ins[0].op_str,0)==target
        owners[target]=('skills','docs/research/client-audio.md:AUDIO-006-timeline-owner')
        evidence.append(dict(owner=hex(target),caller=hex(site),kind='shared character timeline'))
    # Same registered ctor/name pairing as survey_ui_routes, but only the two
    # documented lifecycle slots. No table-size guess or callback substitution.
    ins=decode(0xac4a79,0x4b00)
    for k,i in enumerate(ins):
        if i.mnemonic!='call' or ui.number(i.op_str) not in ui.REGISTRARS:continue
        prev=ins[max(0,k-30):k]
        names=[]
        for j in prev:
            if j.mnemonic!='push':continue
            address=ui.number(j.op_str)
            if address is None or not ui.DATA_BASE<=address<ui.DATA_BASE+len(data):continue
            name=data[address-ui.DATA_BASE:address-ui.DATA_BASE+120].split(b'\0')[0].decode('ascii',errors='replace')
            if re.fullmatch(r'[A-Za-z_0-9]+',name):names.append((j.address,name))
        if not names:continue
        name_site,name=names[-1]
        ctors=[j for j in prev if j.mnemonic=='call' and j.address<name_site and ui.number(j.op_str) not in (0x40c8d0,0x191ba7b) and ui.number(j.op_str) not in ui.REGISTRARS]
        if not ctors:continue
        ctor=ui.number(ctors[-1].op_str)
        if ctor is None:continue
        tables=[ui.number(j.op_str.split(', ')[-1]) for j in decode(ctor,0x100) if j.mnemonic=='mov' and re.fullmatch(r'dword ptr \[eax\], 0x[0-9a-f]+',j.op_str)]
        if not tables:continue
        vt=tables[0]
        if not ui.DATA_BASE<=vt or vt+0x48>ui.DATA_BASE+len(data):continue
        for slot in (0x40,0x44):
            entry=struct.unpack_from('<I',data,vt-ui.DATA_BASE+slot)[0]
            owners.setdefault(entry,('ui','docs/research/client-audio.md:AUDIO-006-registered-lifecycle'))
            evidence.append(dict(owner=hex(entry),movie=name,constructor=hex(ctor),vtable=hex(vt),slot=hex(slot),kind='registered UI lifecycle'))
    return owners,evidence


def classify(before,after,text,data):
    import monster_audio_static as scalar
    slots=scalar.owners(data)
    # Historical 279 candidates are distinct sites in the 19 refused methods.
    refused=EXTENDED|DELEGATED|MARKERS|STOP
    assert refused<=set(slots)
    rows=[]
    for r in before['sites']:
        anchor=int(r['anchor'],16)
        if r['owner']=='unresolved':group='owner unknown'
        elif anchor in refused:
            group=('scalar world/distance/audio RNG' if anchor in EXTENDED else
                   'delegated owner/context absent' if anchor in DELEGATED else
                   'marker field or service absent' if anchor in MARKERS else
                   'prior action and stop ordering' if anchor in STOP else 'silent method')
        elif r['source'].endswith('AUDIO-005-use-controller'):group='use owner target/buff/request/timing context absent'
        else:continue
        new=next(n for n in after['sites'] if n['site']==r['site'])
        rows.append(dict(site=r['site'],anchor=r['anchor'],group=group,owner_after=new['owner'],
                         sound_id_status=r['sound_id_status'],wired=bool(new.get('audio_006_adapter'))))
    return dict(groups=dict(Counter(r['group'] for r in rows)),
                unknown_ids_by_group=dict(Counter(r['group'] for r in rows if r['sound_id_status']=='unresolved')),
                actor_missing_only=0,sites=rows)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--before',type=Path,default=ROOT/'docs/research/audio-006-entry-groups.csv');ap.add_argument('--report',type=Path,required=True);a=ap.parse_args()
    import audio_caller_census as census
    text,data=pins.TEXT.read(),pins.DATA.read();after=census.inventory(text,data)
    if a.before.suffix=='.csv':
        with a.before.open(newline='') as f:
            entry=list(csv.DictReader(f))
        before={'sites':[dict(site=r['site'],anchor=r['anchor'],owner=r['entry_owner'],source=r['entry_source'],sound_id_status=r['entry_sound_id_status']) for r in entry]}
    else:before=json.loads(a.before.read_text())
    report=classify(before,after,text,data)
    _,report['semantic_evidence']=semantic_owners(text,data)
    a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('sites','semantic_evidence')},indent=2))
if __name__=='__main__':main()
