"""Translate recorded client calls into the existing native part columns.

Anchors are client identities, not a second hand-written part order. The
native adapters below are explicit exceptions to those anchors. Removing an
anchor from the reconstruction raises; changing client order propagates into
these expectations. Private comparison validates the C source of the stream.
"""
# One client call can cover several native part hooks. The character renderer
# owns all three character groups; the native runtime draws them separately.
ANCHORS = {
    'tick': {0x016d82c7: ('objects',), 0x017ea1aa: ('items',),
             0x00c9eb04: ('env',), 0x016a9150: ('sound',),
             0x0137a7ce: ('characters',), 0x0106bbb2: ('helpers',),
             0x016914a0: ('combat',), 0x0150ddb1: ('particles',)},
    'draw': {0x016cd468: ('terrain',), 0x016d5020: ('objects',),
             0x0137a3c2: ('hero', 'players', 'actors'), 0x017e9495: ('items',),
             0x00c9e4e3: ('helpers',), 0x01538145: ('env',),
             0x00a75708: ('actor_effects',), 0x0159123f: ('particles',),
             0x0169159e: ('combat',), 0x00def268: ('haze',)},
}

# (part, predecessor, why). These preserve existing renderer hashes. They do
# not assert that native order equals every original pass or every branch.
MOVES = {
    'tick': (
        ('combat', 'characters', 'demo combat settlement runs before helper animation; original MovePoints is later'),
        ('items', 'helpers', 'native pick-up/despawn and sparkle share one hook after helpers; original MoveItems precedes MoveHero'),
        ('objects', 'items', 'native objects consume current hero/character positions; original MoveObjects precedes MoveHero'),
        ('env', 'objects', 'native weather/boids/fish share one hook after objects; original ambient calls precede MoveHero'),
    ),
    'draw_gl': (
        ('helpers', 'players', 'native mount GL rendering separates players and demo actors; original helpers follow all characters/items'),
        ('actor_effects', 'particles', 'native actor EffectManager instances draw after particle pool; original manager update precedes sprites/particles'),
    ),
    'draw_soft': (
        ('helpers', 'env', 'software helper raster follows the environment; original helpers precede leaves'),
        ('actor_effects', 'particles', 'native actor EffectManager instances draw after particle pool; original manager update precedes sprites/particles'),
    ),
}
ADDITIONS = {
    'tick': (
        ('actors', 'sound', 'native fixture placement/sync before the shared MoveCharacters loop; no separate client mover'),
        ('npc', 'characters', 'demo NPC talk/answer step, no standalone MoveMainScene call'),
        ('quest_step', 'npc', 'native session quest step, no standalone MoveMainScene call'),
        ('progress', 'combat', 'demo progression settlement, no standalone MoveMainScene call'),
        ('social', 'progress', 'native social demo tick, no standalone MoveMainScene call'),
        ('names', 'items', 'native overhead-name state tick; original updates live in character/UI callees'),
        ('map', 'particles', 'native gate/travel check, no standalone MoveMainScene call'),
    ),
    'draw_gl': (
        ('marker', 'env', 'native clicked-point viewer aid; no client counterpart'),
        ('item_labels', 'haze', 'native item-label overlay; original labels are inside GFx/UI callees'),
        ('names', 'item_labels', 'native name overlay; original names are inside character/GFx callees'),
    ),
    'draw_soft': (
        ('marker', 'particles', 'native clicked-point viewer aid; software raster placement differs from GL'),
        ('item_labels', 'haze', 'native item-label overlay; original labels are inside GFx/UI callees'),
        ('names', 'item_labels', 'native name overlay; original names are inside character/GFx callees'),
    ),
}


def projected_order(trace, column):
    anchors = ANCHORS['tick' if column == 'tick' else 'draw']
    found = set()
    result = []
    for routine, slot in trace:
        if routine in anchors and routine not in found:
            found.add(routine)
            result.extend(anchors[routine])
    missing = set(anchors) - found
    if missing:
        raise ValueError('recorded order lacks client anchors: ' + ', '.join(hex(a) for a in sorted(missing)))
    for part, after, reason in MOVES[column]:
        assert reason
        result.remove(part)
        result.insert(result.index(after) + 1, part)
    for part, after, reason in ADDITIONS[column]:
        assert reason
        if part in result:
            raise ValueError(f'duplicate native adapter: {part}')
        result.insert(result.index(after) + 1, part)
    return result
