#!/usr/bin/env python3
"""Inventory capture09's direct SND_Play candidates without exporting client bytes.

The historical 1,980 denominator is an E8 rel32-target scan, not a CFG proof.
Known owners use reviewed function anchors, native source references and world
vtable entries. Unassigned owners remain explicit; address proximity never
admits a caller. The nearest MSVC prologue is a grouping aid, not a recovered
symbol. Native source references establish a bounded body, not sound delivery.
"""
import argparse
import bisect
from collections import Counter
import json
from pathlib import Path
import re
import struct
import pins

ROOT = Path(__file__).resolve().parents[1]
BASE, PLAY = 0x401000, 0xa6ac96
OPAQUE = (0x1854279, 0x18542c2)
# Reviewed anchors, independently named in the cited reconstruction/validator.
OWNERS = {
    0xbb22e1: ('ui', 'native/session/domains/skills_audio.h'),
    0xc9eb04: ('world', 'native/core/mu_session_audio.h'),
    0x1851d39: ('world', 'reconstructed/audio/audio_world.c'),
    0x13b1f61: ('hero', 'reconstructed/audio/hero_sound.c'),
    0x138f92f: ('hero', 'reconstructed/combat/combat.h'),
    0x1392bde: ('hero', 'reconstructed/combat/combat.h'),
    0x1393a61: ('hero', 'reconstructed/combat/combat.h'),
    0x13a85a9: ('skills', 'reconstructed/combat/combat.h'),
    0x13966ea: ('skills', 'reconstructed/combat/skill_fx.h'),
    0x1253a92: ('skills', 'reconstructed/combat/combat.h'),
    0x125c7b0: ('skills', 'reconstructed/combat/combat.h'),
    0x13c0f19: ('skills', 'reconstructed/combat/skill_fx.h'),
    0x142fd09: ('skills', 'reconstructed/combat/skill_fx.h'),
    0x13b23f8: ('monsters', 'reconstructed/audio/hero_sound.h'),
    0x16daa27: ('items', 'reconstructed/items/ground_items.h'),
    0xe34169: ('world', 'reconstructed/objects/elbeland.c'),
    0x1250b05: ('events', 'reconstructed/progress/progress.h'),
    0x1857236: ('ui', 'docs/research/client-audio.md:AUDIO-002G'),
    0xb49b97: ('ui', 'docs/research/client-audio.md:AUDIO-002G'),
    0x9a3214: ('ui', 'docs/research/client-audio.md:AUDIO-002G'),
    0xdb3e26: ('events', 'reconstructed/audio/audio_world.c'),
}
# Whole original classless branches whose generic MoveObject prologue precedes
# several worlds. These intervals avoid attributing the entire owner to Devias.
RANGES = [(0x17fffda, 0x18006e2, 'world', 'scripts/validate_worlds_b.py'),
          (0x1800bf8, 0x18013a5, 'world', 'scripts/validate_worlds_b.py')]
# Direct predecessors of the same monster-sound dispatch and the monster
# render hook chain; source call sites are listed in the AUDIO-003 finding.
for _anchor in (0x13a04d6, 0xe33c95, 0xe669c9, 0xdfe9a6, 0xdb16a3,
                0xd6654b, 0xe7bb9f, 0xe81b53, 0xd579e6):
    OWNERS[_anchor] = ('monsters', 'docs/research/client-audio.md:AUDIO-003-dispatch')

DOMAINS = {'ui': 'ui', 'quest': 'ui', 'npc': 'ui', 'items': 'items',
           'environment': 'world', 'objects': 'world', 'combat': 'skills',
           'charsel': 'ui', 'scene': 'ui', 'gfx': 'ui', 'progress': 'events'}


def call_sites(text):
    return [BASE + m.start() for m in re.finditer(b'\xe8', text)
            if m.start() + 5 <= len(text)
            and BASE + m.start() + 5 + struct.unpack_from('<i', text, m.start() + 1)[0] == PLAY
            and not OPAQUE[0] <= BASE + m.start() < OPAQUE[1]]


def inventory(text, data, root=ROOT):
    starts = [BASE + m.start() for m in re.finditer(b'\x55\x8b\xec', text)]
    owners = dict(OWNERS)
    # Slot 0x70 is the class monster-sound selector. Static only: these
    # selectors have no corresponding migrated generic native consumer.
    coverage = json.loads((root/'docs/research/world-handler-coverage.json').read_text())
    for row in coverage['classes']:
        table = int(row['vtable'], 16)
        sound = struct.unpack_from('<I', data, table + 0x70 - 0x1a7c000)[0]
        owners.setdefault(sound, ('monsters', 'docs/research/world-handler-coverage.json:slot+0x70'))
        for handler in row['handlers'].values():
            owners.setdefault(int(handler['entry'], 16), ('world', handler['source']))
    # Exact anchor references only. This inventory deliberately leaves unknown
    # classes, request owners and helper lifetimes unclassified.
    references = {}
    for folder, category in DOMAINS.items():
        for path in sorted((root/'reconstructed'/folder).rglob('*')):
            if path.suffix not in ('.h', '.c'):
                continue
            for match in re.finditer(r'0x([0-9a-fA-F]{6,8})\b', path.read_text()):
                address = int(match[1], 16)
                references.setdefault(address, []).append((category, str(path.relative_to(root))))
    delivered = set()
    adapter_paths = ['native/core/mu_session_audio.h', 'native/core/mu_combat_audio.h',
                     'native/core/mu_charsel_audio.h', 'native/core/mu_ui_audio.h',
                     'native/session/domains/items_audio.h', 'native/session/domains/skills_audio.h',
                     'reconstructed/audio/hero_sound.c']
    for path in adapter_paths:
        delivered.update(int(m[1], 16) for m in re.finditer(
            r'0x([0-9a-fA-F]{6,8})[uU]?\b', (root/path).read_text()))
    delivered.add(0x125104c)  # existing hero level-up boundary; no new answer route
    added = {int(m[1], 16) for m in re.finditer(r'0x([0-9a-fA-F]{6,8})[uU]?\b',
             (root/'native/core/mu_object_audio.h').read_text())}
    rows = []
    for site in call_sites(text):
        index = bisect.bisect_right(starts, site)
        anchor = starts[index - 1] if index else 0
        domain, source = owners.get(anchor, ('unresolved', 'unrecovered owner'))
        refs = references.get(anchor, [])
        if domain == 'unresolved' and len({r[0] for r in refs}) == 1:
            domain, source = refs[0]
        for lo, hi, category, cited in RANGES:
            if lo <= site < hi:
                domain, source = category, cited
        rows.append({'site': f'0x{site:08x}', 'anchor': f'0x{anchor:08x}',
                     'owner': domain, 'source': source,
                     'native_reference': bool(refs) or source.startswith(('reconstructed/', 'native/')),
                     'audio_adapter': site in delivered or anchor == 0x1851d39 or anchor == 0xdb3e26,
                     'audio_003_adapter': site in added})
    counts = Counter((r['owner'], r['native_reference']) for r in rows)
    return {'method': 'direct E8 candidates; exact anchors with explicit unresolved remainder',
            'text_sha256': pins.TEXT.sha256, 'data_sha256': pins.DATA.sha256, 'total': len(rows),
            'mapped_audio_sites': sum(r['audio_adapter'] for r in rows),
            'added_audio_sites': sum(r['audio_003_adapter'] for r in rows),
            'summary': [{'owner': owner, 'native_reference': native, 'sites': n}
                        for (owner, native), n in sorted(counts.items())], 'sites': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = inventory(pins.TEXT.read(), pins.DATA.read())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('total', 'summary')}))


if __name__ == '__main__':
    main()
