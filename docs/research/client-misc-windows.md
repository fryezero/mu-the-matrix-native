# SYS-MISC-001a investigation

Work in progress. No live client, protected module, dispatch generator, jump-table walk,
wire encryption or keyed transform was used.

## Inputs and evidence boundary

Pinned restored text SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`;
pinned image data `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
These are the existing compatibility-environment captures, not native Windows observations.

Static observations from bounded window registration, constructors and their direct callers:

- HelpWindow: manager +0x120, registration 0x00ac678a, constructor 0x00b89588,
  vtable 0x01a8f180. Loader 0x00b89977 invokes InitText, SetPosCenter,
  ClearDataProvider and help-row loaders. The helpdata.bmd reader is separate from the movie.
- CommandWindow: manager +0x134, registration 0x00ac699b, constructor 0x00b4c867,
  vtable 0x01a8b718. Command actions include trade, purchase, party, whisper, guild,
  union, rival, friend, follow and duel. These actions depend on social/item domains.
- QuickCommand: manager +0xd8, registration 0x00ac569e, constructor 0x00c0a0f4,
  vtable 0x01a97604. Its contextual target checks and command actions are distinct
  from the list window.
- BossHPUI: manager +0x27c, registration 0x00ac9425, constructor 0x00b35935,
  vtable 0x01a8a16c. Two bar states, each five signed integers at +0x78 with stride
  0x14. Initial state is 0,10,10,0,1 at 0x00b360b1. SetBossInfo 0x00b35af9;
  UpdateHpHud 0x00b35dff. Layer count/colour is not a simple HP percentage.
- DivideWindow is excluded from this slice: its visibility participates in item/NPC
  transaction guards, and the requested item-independent condition is not established.

Local ActionScript inspection of the existing converted movies establishes static interfaces:

- MonsterInfo.AddInfoUI takes key, name, HP frame, attribute, visibility, x, y and mark.
  It has no level argument. InitScene cycles identifiers through 0..100. Its retained
  per-key clips need explicit removal. This differs from hudPlayerName.MonsterInfoMC,
  which the port already renders.
- DamageCount is a resizable text/caution dialog with InitText, SetText and Stop/OK/Cancel
  callbacks. It is not a floating damage-number movie or an automatic damage accumulator.
- BossHpUI.swf exports BossHPUI and uses SetBossInfo and UpdateHpHud.

The pinned image strings contain the BossHPUI/HelpWindow/CommandWindow/QuickCommand
registrations. The exact MonsterInfo and DamageCount class registrations and receive/request
paths have not yet been identified. Movie interfaces alone are not instruction validation.
No arbitrary packet route or invented request is justified by these observations.

## Verified arithmetic checkpoint

`reconstructed/misc/misc.c` implements BossHPUI's initialization, zero-to-three
palette mapping, segment-unit write, gauge remainder and layered palette update.
`validate_misc.py --cases 500 --mutants` executes **2,500 comparisons in five families,
zero mismatches, six of six compiled mistakes caught**. Both bar offsets are covered.
The CRT ceil and float-to-int return are modeled boundary services; the segment-unit
comparison is a bounded interior slice with a synthetic caller frame. These counts
are window arithmetic evidence only, not packet, movie or session acceptance.

Four portable tests cover palette/layer boundaries, gauge full-health and remainder
semantics, atomic host refusal of invalid divisors, and independent bars/reset.
The private test additionally runs 200 instruction comparisons and the six mutants.
The registered validator is `validate_misc` in `scripts/validators.toml`.

## Blocked acceptance and exact next work

SYS-MISC-001a is **not implemented**. No window/domain/fixture migration is claimed.
The current seed route table and existing findings do not identify a remote monster
HP/level answer, a BossHPUI answer, or MonsterInfo/DamageCount receive/request bodies.
The combat domain's F3 events contain damage amounts, not authoritative remote
current/max HP. Subtracting them from invented health would create a second feed.
The viewport migration explicitly lists remote HP-update routing as remaining work.

The supplied movie contracts also do not match the proposed self-contained HUD
scope: MonsterInfo has no level argument; DamageCount is a text/caution dialog;
CommandWindow/QuickCommand initiate social/item operations with target/world guards.
No request builder or packet format can be inferred from a movie callback name.

To resume without crossing the current limits, supply an existing offline finding or
captured scoped native caller for the missing remote-HP and MonsterInfo/DamageCount
bodies and its route provenance. Then validate those bodies, add only evidenced seed
rows, and implement the misc domain/ops/intents, fixture behaviour/scenario and GFx
views. Resolve whether DamageCount should reproduce its actual dialog or the task
requires a different damage-display movie. Commands need a reviewed delegation seam
to their owning social/item domains. HelpWindow additionally needs its helpdata.bmd
row-input contract, not an invented shortcut list.

No dispatcher/jump-table walk, crypto/decode work, new live capture, or speculative
route was performed to bridge these gaps. No full-window render is claimed.

## Static movie provenance

The inspected inputs are existing locally converted bridge movies under
`mu-mac-tools/native/scratch/gfx/all-bridge/`, exported with the existing local
JPEXS tool. These digests identify those derived files, not unconverted original
movie bytes. No native-handler equivalence follows from this inspection.

| Movie | Inspected SWF SHA-256 |
|---|---|
| MonsterInfo.swf | `2f02da2e76885d599bbf5b42afafd5c282d7eb0046c7243bf4cbe11ca3cd95a7` |
| BossHpUI.swf | `e091669041e0f282f5ea4ad8f712e9bfe937c94796838a234791eaebd244ca02` |
| DamageCount.swf | `b14f1e0c6e06a0aae6b43fe2518f6e859dd024c4862a8e811e26c35a38e13427` |
| HelpWindow.swf | `c12ab7e6f778677b7a7e9ac646cdc8c12eb2200bcd49556585380491c3e75c49` |
| CommandWindow.swf | `d0116554f0948d2dc7131b3064fe2d893dc86c577c10e80c48964f0377ac65d6` |
| QuickCommand.swf | `53ac35aaab833ca5b1a3fc679b770688ca057fee9ab020775b47dda57d84ebf6` |
