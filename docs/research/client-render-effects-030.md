# Demo-class skill visual audit and callers

RENDER-EFFECTS-030 starts from EFFECTS-028 `32e36706`, with main `d4af71dd`.
The first deliverable is the complete selectable demo inventory below. This is
an offline presentation audit. No original client, service or installed app is used.

## Evidence and denominator

The pinned executable SHA-256 is
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Capture09 text is
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
Run10 image data is
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
All bytes and decoded tables remain private. Addresses below are static
instruction readings until a comparison family explicitly verifies them.

`native/fixture/skills_model.c` supplies fourteen DK learned entries.
`native/client/demo-skills.txt` supplies fourteen Elf entries, including 2044.
These are the complete learned sets that the demo can select and assign to
its hotbar, regardless of whether usability checks permit a cast. A visible
unlearned tree icon is not a selectable learned cast. Skill 0 is separately
included because ordinary attacks are always available.

The shipped `demo-characters.txt` uses DK byte `0x01` and Elf byte `0x02`.
It contains no evolved byte. The fixture list selector uses `class_byte & 15`,
so synthetic promoted bytes `0x11/0x21/0x31/0x41` and
`0x12/0x22/0x32/0x42` inherit those lists. This does not establish their visual
selectors. Death Stab currently explicitly refuses every byte except `0x01`.
Master/fourth/fifth trees do not automatically add a learned skill or a cast
route. Skill 47 is a stale fixture entry absent from the pinned language table.

P means the bounded primary cast visual is present. L means a specific visual
or context remains missing. M means the native cast adapter refuses the skill.
These labels concern presentation only. Authoritative buffs, power, target
state and service eligibility are excluded. They do not change the historical
23-route denominator in the earlier coverage table.

D = attack-step default `0x0139b454`; A = area-end default `0x013aea7a`;
E = targeted-end default `0x013b1911`. The corresponding dispatchers are
`0x013966ea`, `0x013a90c0` and `0x013af035`. Addresses name the entry of the
selected body, including leading field reads. Buffs have a separate persistent
RenderCharacter consumer. Priorities estimate repeated use, not telemetry.

| Class | Skill | Priority | Before | Original step / end body | Native result or missing part |
|---|---|---:|---|---|---|
| Both | 0 ordinary attack | 5 | P | SetPlayerAttack `0x01392bde`; A | Weapon action or the demo bow's verified arrow |
| DK | 19 Falling Slash | 2 | P | D / A, E; receive `0x01253a92` | Action `0x89` |
| DK | 20 Lunge | 2 | P | D / A, E; receive `0x01253a92` | Action `0x8a` |
| DK | 21 Uppercut | 2 | P | D / A, E; receive `0x01253a92` | Action `0x8b` |
| DK | 22 Cyclone | 2 | P | D / A, E; receive `0x01253a92` | Action `0x8c` |
| DK | 23 Slash | 2 | P | D / A, E; receive `0x01253a92` | Action `0x8d` |
| DK | 41 Twisting Slash | 5 | P | D / `0x013aba81` | Swirl, smoke, sparks and joints |
| DK | 42 Anger Strike, previously labelled Rageful Blow | 4 | P | D / `0x013a94a4` | Flying weapon and quake family, ordinary worlds |
| DK | 43 Death Stab | 4 | L | `0x0139959c` / A, E | Base-DK bone-33 fixture draws 189 requests; general link selector missing |
| DK | 44 Crescent Moon Slash | 2 | M | `0x0139a76f` / `0x013ad798` | Missing action/caller and selected effect consumers |
| DK | 18 Defense | 3 | M | D / A, E; action path separate | Missing shield action admission; absence of an end effect is not proof of a complete cast |
| DK | 47 stale fixture entry | 1 | M | D / A, E | Absent skill record; no invented name, selector or cast |
| DK | 48 Swell Life | 4 | M | `0x0139a51f` / `0x013aa0e1` | Missing 36 joint requests and presence consumer; no real buff values admitted |
| DK | 49 Fire Breath | 1 | M | `0x0139a6f8` / `0x013aba0c` | Missing mount-context caller |
| DK | 344 Blood Storm | 5 | M | `0x0139b2fd` / `0x013a9f25` | Missing `0x583/0` emitter, children and adapter |
| Elf | 24 Triple Shot | 5 | L | D / `0x013af9db` | Existing arrow fan; audit found the caller falls through into `0x013af9fe`, requiring a second request and actual skill/learned-index argument order |
| Elf | 26 Heal | 4 | P | D / `0x013afaab` | Ground effect and energy ribbons |
| Elf | 27 Greater Defense | 4 | L | D / `0x013afb06`; persistent `0x01370ccc` | EFFECTS-028 authored aura; general links/presence input absent |
| Elf | 28 Greater Damage | 4 | L | D / `0x013afcea`; persistent `0x01370ccc` | EFFECTS-028 authored aura; general links/presence input absent |
| Elf | 30 Summon Goblin | 1 | M | D / `0x013a9449` | Actor construction/lifetime outside this lane's owned files |
| Elf | 31 Summon Stone Golem | 1 | M | D / `0x013a9449` | Same summon owner gap |
| Elf | 32 Summon Assassin | 1 | M | D / `0x013a9449` | Same summon owner gap |
| Elf | 33 Summon Elite Yeti | 1 | M | D / `0x013a9449` | Same summon owner gap |
| Elf | 34 Summon Dark Knight | 1 | M | D / `0x013a9449` | Same summon owner gap |
| Elf | 35 Summon Bali | 1 | M | D / `0x013a9449` | Same summon owner gap |
| Elf | 36 Summon Soldier | 1 | M | D / `0x013a9449` | Same summon owner gap |
| Elf | 51 Ice Arrow | 4 | M | D / `0x013afa2c` | Missing target-key write and single-arrow caller |
| Elf | 52 Penetration | 4 | M | `0x01399ca2` / `0x013af9fe` | Missing step-3 charge `0x7fd0/0`, five-step cutoff and subtype-2 arrow caller |
| Elf | 2044 Raining Arrow of Saturation | 5 | P | Receive visual slice `0x0125f5d1`; `0x014d1a18` | Authored ground-volley route, rings, rain, landings and decals |

The before inventory is 10 P, 4 L, 15 M across 29 class/skill rows, counting
ordinary attack once. The DK list has fourteen entries, Elf fourteen, plus zero.
The historical P label for Triple Shot covered the fan component but missed its
caller fallthrough. This wider audit records that limitation rather than treating
component verification as proof of the whole caller.

## Work order and limits

Research Blood Storm first, then the repeated Elf arrow callers and Swell Life.
If a required item/particle consumer is absent, record its exact counted refusal
for EFFECTS-026. Do not add that lane's consumer. Actor summons remain an actor
follow-up. Later-class aliases require individually compared synthetic selector
inputs; a masked class nibble alone is not admission evidence.
