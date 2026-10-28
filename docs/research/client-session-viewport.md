# Session-owned player viewport

SESSION-VIEWPORT-001, 2026-10-27. Player viewport, move, destroy, death and store-open answers now
cross the loopback fixture and the session dispatcher before changing CharactersClient records.
`--players` keeps its authored specification format. Its scheduler and packet encodings are in
`native/fixture`, and the core player module contains presentation and movement services.
No original client, live service, wire crypto or protection code was used.

## Instruction evidence

The target is the client in `docs/evidence-index.json`, main.exe SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
`scripts/validate_viewport.py` uses the pinned restored text `2bd5f2e9…3724`, base `0x00401000`, and
image data `c985e2e6…a0672f`, base `0x01a7c000`. This is compatibility-environment evidence.

The new family executes `0x0122d413` from entry to return for 1,000 bounded Player-model cases.
It compares the equipment, path, tile, position, angle and movement fields with authored C. Engine
services, character allocation/defaults, effects, string/guild services and table lookups are explicit
host stubs. Full-handler cases vary class/equipment, creation versus walk-in, and failed path answers;
they exclude pose states 1..4, pet-item and muun lookups and nonzero buff lists. This is equality of the
compared record fields under those host answers, not equality of every handler side effect.

Six further sections run 1,000 cases each against original instruction ranges:

- key mask/creation flag, `0x0122d486..0x0122d4b6`;
- field application, `0x0122d660..0x0122d6a9`, `0x0122d8a1..0x0122d996`, `0x0122da8e..0x0122db06`;
- variable record stride, `0x0122e211..0x0122e22d`;
- the represented defaults in the create prefix, `0x0137d8a1..0x0137db3e`;
- walk-in placement, `0x0122dc47..0x0122dd87`;
- name, pet words/levels, buff types/values and server-word reads, `0x0122d4b6..0x0122d4dc`,
  `0x0122d996..0x0122da8e`, `0x0122df8a..0x0122e018`, `0x0122e10e..0x0122e11c`.

Result: **7,000 instruction cases, zero mismatches**, plus 3,000 authored parser-boundary checks.
All **8/8 compiled-C mutants** are caught: key mask, record stride, target, flag shift, guild default,
angle multiplier, name offset and buff value offset. Mutant sources/libraries exist only in a temporary
directory. Original instruction bytes are never changed.

The placement comparison found and corrected one static reconstruction error: viewport walk-in starts
with path mode 2, then tries 4, including world `0x52`. The old C incorrectly borrowed the movement
packet's mode-4-world rule. Verified move/equipment/step code is unchanged. The existing players family
rerun gives **4,768 cases, zero mismatches, 7/7 controls**. Helpers give **8,667 cases, zero mismatches,
11/11 controls**. The manifest already explains the historical 8,639 count: NATIVE-HELPERS-002 added 28
class/state entries; the original 8,639-case set remains covered with the same arguments and code.

## Session and presentation

`domains/characters*` owns 400 records, occupancy, generations, equipment revisions/call lists and store
state. The first free slot is reused. Generation changes on allocation, independently of equipment
refresh. A packet's complete variable-length record list is checked before it changes state; the
original count limit is 75. Unknown/dead move targets are ignored. A full pool preserves existing
records. Tests cover all 400 slots, overflow and first-free reuse through actual fixture frames.

The `characters` part runs one table walk over `mu_sim` records. It follows the actor lane at tick 21,
before NPC/quest/combat logic. The hero still runs through `mu_walk` before `on_step`; the unmigrated
monster/NPC table stays in its actor lane until VIEWPORT-MONSTER-001. Helpers retain tick 90 after the
character movement loop. Their caches read the same records and equipment call revisions. Mount
rendering's first rider-pose write uses a short lease too, so the next tick cannot overwrite it with
an older session action. `test_world_parts.py` pins the revised order against the recorded `on_step`
order and rejects a second player tick.

The fixture observes client motion only to retain the old demo's arrival/range choreography. Every
creation, move, death, store-open and destroy still returns through framed bytes and the one dispatcher.
It never writes session records. Its choices remain synthetic, not a recovered server simulation.
The world tools use the existing loopback-only fixture archive. TCP serving remains in `mu-session`;
the offline app retains its no-network-import check.

## Projection

`layout/viewport.def` and `characters_projection.def` bind the reconstructed numeric/array subset.
The adapters use generated manifest offsets, preserve unknown gaps and keep the two level reads
separate. The native path exposes 33 bytes; the remainder of the older 0x48-byte declaration becomes
unknown, rather than invented padding. The scene level has no matching remote-player member. The
manifest's +0x44 name/label bytes and the C++ string object are not projected from the native name.
There is no claim to reproduce a C++ string representation.

The portable test round-trips every mapped member for 100 byte patterns, including every equipment
slot, signed skill word and path cell. It checks untouched unknown/scene bytes and short-buffer
refusal. Lease auditing protects both occupied records' replicated fields and unused slots; its
capacity includes a full viewport and the quest domain.

## Intended hash change

Against main `5ebc2b6` with #178/#179, the 120-frame synthetic player/helper run changes 35 PNGs,
frames 85..119. The first 85 frames remain byte-identical. The new run repeated with all 120 hashes
identical. Frame 85 changes from
`fd0af2ce34620a25ab5b84a7e84548d0c27661a5aa0df93ba5ff5d732c3e27c5` to
`8ba956c33886f070ff09b504637c2d38398950ebc6d9761f068d32e337369305`.

The old demo shared one RNG between server movement choices and client death-animation draws. Moving
the server into the fixture separates those streams. After the scripted death, Kyra's later move has
a different direction/position; both runs still have 3 viewport creations, 6 move packets, 6 path
calls and 1 death. The single-loop placement is also an intentional order change. No render pass or
quality setting was removed. The compared software images were inspected in the real renderer's PNG
output; they contain the synthetic fixtures' colored meshes and labels, not installed-game fidelity.

## Remaining limits

The five seeded routes are bounded plaintext fixture routes; their dispatch addresses remain STATIC
until NET-DISPATCH. The new family does not upgrade pet-item eligibility, muun index mapping, pose
services, C++ strings, buffs' engine effects, creation effects or the complete create routine. Existing
static/inferred behavior in those branches remains labeled as such. Store close and equipment-change
packets, hero move echoes, dynamic caches beyond the legacy eight-player demo, and monster/NPC viewport
creation remain later work. The session table itself supports 400 entries.

World/account ownership across scene flow is still SESSION-ACCOUNT. The characters fixture is opened
and closed with the world runtime; no persistence across a destroyed session, account login or process
restart is claimed. No live-service, encrypted-frame or replay-oracle completion is claimed.

Checks, artifact locations and the final local gate are in
[the milestone handoff](../handoffs/SESSION-VIEWPORT-001.md).
