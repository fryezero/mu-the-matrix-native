#!/usr/bin/env python3
"""RENDER-ACTORS-004: bounded original construction census, never spawn data.

All 1,024 authored fixture class selectors are attempted using the existing
world-0/rand-0 constructor machine and its documented declining processors.
All 601 monster and 147 NPC opener selectors are separately enumerated.
Only reviewed construction metadata and classifications are exported.
"""
import argparse
import collections
import csv
import ctypes as C
import re
from pathlib import Path

import actor_machine as am
import pins
import validate_actor_recipes as recipes
import validate_actors as va

COMPOSITE_NPCS = (230, 248, 250, 253, 255)
MONSTER_EXTRA = (147, 226, 229, 230, 231, 232, 233, 245, 289)
NPC_EXTRA = (0x9fe, 0x9ff, 0xa00, 0xa2c, 0xa2d, 0xa5e, 0xa7d)
_EFFECT_ROWS = (Path(__file__).resolve().parents[1]/'reconstructed/actors/effect_class_table.h').read_text().split(
    'static const mu_effect_class mu_effect_classes')[1]
EFFECT_CLASSES = {int(cl): (int(model, 0), int(npc, 0)) for cl, model, npc in re.findall(
    r'^    \{([0-9]+), (0x[0-9a-f]+), (0x[0-9a-f]+),', _EFFECT_ROWS, re.M)}


def collect():
    text = pins.TEXT.read()
    machine = am.ActorMachine(text, pins.DATA.read())
    classes, static = va.extract_classes(machine, text, 1024)
    for record in classes:
        if record.get('via') == 'generic':
            record['case'] = hex(va.static_generic_target(text, record['class']))
    openers = []
    for selector in range(va.MONSTER_TYPES):
        run = va.run_client_open(machine, va.monster_case(str(selector), selector, actions=16))
        if not run['ok']:
            raise RuntimeError((selector, run['stopped']))
        extra = [c for c in run['calls'] if c[0] == 'access' and c[1] != selector + 0x7a5]
        openers.append(dict(family='monster', selector=selector, extra_models=len(extra),
                            extra_loads=len(run['loaders']), bitmap_loads=sum(c[0] == 'bitmap' for c in run['loaders']),
                            sound_loads=sum(c[0] != 'bitmap' for c in run['loaders']), result='extracted'))
    for selector in range(va.NPC_FIRST, va.NPC_LAST + 1):
        run = va.extract_npc(machine, selector)
        openers.append(dict(family='npc', selector=selector, extra_models=len(run.get('extra', [])),
                            extra_loads='', bitmap_loads='', sound_loads='', result='unresolved mesh state' if 'error' in run else
                            'extracted' if run.get('file') else 'no own file'))
    monster_openers = {r['selector']:r for r in openers if r['family'] == 'monster'}
    for record in classes:
        record['bitmap_loads'] = sum(monster_openers[s]['bitmap_loads'] for k, s in record.get('opens', []) if k == 'monster')
    return classes, openers, static


def classify(record, row, composite_ready=False):
    """Completeness is deliberately bounded to construction and body plans.

    Generic bodies have no whole RenderCharacter special-pass proof. Calling
    those complete would turn an opener census into a false fidelity claim.
    """
    cl = record['class']
    path = 'unresolved'
    if 'error' not in record:
        opens = record['opens']
        path = '+'.join(f'{kind}:{selector}' for kind, selector in opens) or 'no opener'
    tags = []
    if cl in (374, 642):
        tags.append('companion')
    if record.get('model') == 0xa91 or cl in (378, 55, 361, 937, 939, 940, 941) or cl in EFFECT_CLASSES or record.get('joints'):
        tags.append('special appearance hook')
    if cl in (625, 626):
        tags.append('action-dependent transformed-player hook excluded')
    if any(kind == 'monster' and selector in MONSTER_EXTRA or kind == 'npc' and selector in NPC_EXTRA
           for kind, selector in record.get('opens', [])):
        tags.append('sub-model/extra-load')
        if cl not in COMPOSITE_NPCS:
            tags.append('action-dependent or auxiliary hook')
    if record.get('bitmap_loads'):
        tags.append('extra bitmap load')
    if any(t not in (0, 65535) for t, _ in record.get('slots', [])):
        tags.append('constructor equipment/parts')
    if path == 'no opener':
        tags.append('no opener/startup model')
    if not tags:
        tags.append('unresolved construction' if 'error' in record else 'plain body construction')
    if not row or cl in (374, 378, 617, 642):
        status = 'refused'
    elif cl in recipes.FIXED or composite_ready and cl in COMPOSITE_NPCS:
        status = 'correct bounded body plan'
    else:
        status = 'incomplete/unverified special passes'
    return dict(server_class=cl, constructor=record.get('via', record.get('error', ['unknown'])[0]),
                constructor_case=record.get('case', ''), native_override=('effect class table, model '+hex(EFFECT_CLASSES[cl][0])) if cl in EFFECT_CLASSES else '', model=hex(record['model']) if record.get('model') is not None else '', opener=path,
                construction='; '.join(tags), native=status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--classes', type=Path, required=True)
    parser.add_argument('--openers', type=Path, required=True)
    parser.add_argument('--composite-ready', action='store_true')
    args = parser.parse_args()
    records, openers, static = collect()
    lib = recipes.library(recipes.LIBRARY)
    lib.mu_monster_class_find.argtypes = [C.c_uint32]
    lib.mu_monster_class_find.restype = C.POINTER(recipes.Row)
    lib.mu_npc_find.argtypes = [C.c_uint32]
    lib.mu_npc_find.restype = C.c_void_p
    rows = []
    for record in records:
        native = lib.mu_monster_class_find(record['class'])
        if native and 'error' not in record:
            row = native.contents
            if row.model != record['model'] or row.scale_bits != record['scale_bits'] or \
               row.class_byte != record['class_byte'] or row.opened != (record['opens'][0][1] if record['opens'] else 0) or \
               [[s.type, s.level] for s in row.slots] != [list(s) for s in record['slots']]:
                raise ValueError(f"class table differs from original constructor: {record['class']}")
        admitted = bool(native)
        if native:
            row = native.contents
            if row.kind == 4 or row.kind == 2 and not lib.mu_npc_find(row.opened):
                admitted = False
            if row.kind == 3 and not lib.mu_actor_player_recipe(record['class'], None):
                admitted = False
        if record['class'] in EFFECT_CLASSES:
            admitted = True  # mu_world_actors resolves these before the core class table.
        rows.append(classify(record, admitted, args.composite_ready))
    for path, values in ((args.classes, rows), (args.openers, openers)):
        with path.open('w', newline='') as out:
            writer = csv.DictWriter(out, fieldnames=list(values[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(values)
    print(dict(classes=len(rows), native=collections.Counter(r['native'] for r in rows),
               constructors=collections.Counter(r['constructor'] for r in rows), static=static,
               openers=len(openers), submodel_openers=sum(bool(r['extra_models']) for r in openers),
               secondary_loads=sum(r['extra_models'] for r in openers)))


if __name__ == '__main__':
    main()
