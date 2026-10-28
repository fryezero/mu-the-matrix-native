# Main world call order, WORLD-ORDER-001

## Result and contract

**Verified:** compiled authored C records the same ordered calls as the original MoveMainScene
`0x0185613e..0x01856e6c` and RenderMainScene `0x0185916b..0x01859d8a` control flow in Unicorn.
Each family passes 1,200 synthetic cases, zero mismatches and zero stopped cases. The cases reach both edges
of every decoded conditional jump: tick 136/136, draw 158/158. Ten separately compiled planted mistakes
are detected by differing call streams, with no stopped mutant cases.

`reconstructed/world-order/world_order.c` uses the existing `mu_scenemgr_host` / `mu_scenemgr_call` shape.
A record identifies a direct callee or import slot; a virtual record carries its slot in `args[0]`.
This family intentionally projects **order only**. Other arguments, ECX and text are zero/absent, rather than
claimed reconstructed. The draw success result is compared too. The native runtime does not link this C.

## Identity and method

The target is `main.exe` SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Whole-input identities and sizes come from `scripts/pins.py`: restored capture09 text at `0x00401000` and
run10 image data at `0x01a7c000`. The [scene-manager identity table](client-scene-manager.md#identity)
lists their digests. The validator checks both whole pins before any emulation and asserts these body pins:

| Body | Start | Exclusive end | SHA-256 |
|---|---|---|---|
| MoveMainScene | `0x0185613e` | `0x01856e6c` | `7d3c2026725a7475ad8421a22ade918117a811c8c7642ae0931e999e78a764aa` |
| RenderMainScene | `0x0185916b` | `0x01859d8a` | `0aeff15d740944d4447d0b0c52d72ce4c280a52e391e4f1022d1b93f3f2d2c99` |
| Stack probe | `0x0191c5a0` | `0x0191c5e0` | `0f8ce31cd9b1ce0c271e496c2447217aee128105e3fb255669f8cb2607ef4519` |

The original branches, loads and arithmetic execute unpatched from those inputs. A call-site observer
records calls and returns scripted opaque results with the callee's stack cleanup. The first-tick packet
interval `0x0185627f..0x0185636c` is skipped as one `MU_SCENE_NET_SEND` event, following the scene-manager
family's boundary. Its contents and wire behavior are not reconstructed or executed. The external module
call in the UI tail is an opaque identity, without entering that module.

Both sides receive the same explicit global seeds, fake opaque objects and per-callee result sequences.
The original machine rejects unseeded global/heap reads and execution outside the two bodies and stack
probe. The C host also rejects unseeded reads. Shared-pointer output stubs populate synthetic locals; they
model caller-visible reference/null conditions, not the underlying ownership implementation. The report
includes whole-input/body pins, C/validator source digests, case counts, call counts and branch coverage.

Directed cases cover first/later ticks, selected/missing characters, reference release, protocol/ready
combinations, loading counts 29/30/31, UI refusal combinations, pick success/absence/class, focus conditions,
all leaf-gate predicates, relevant world and HeroTile boundaries, camera results, short-circuit name tests,
Kanturu visibility, optional terrain, top-view second passes and GFx refusal. Castle coordinates cover both
bounds and NaNs. Random cases fill the remainder using seed `0x20261028`. A case is a synthetic caller state,
not a claim that every combination occurs during live gameplay.

## From client calls to native columns

`test_world_parts.py` compiles the C into an isolated temporary library, records an ordinary world-1 tick
and draw, and passes those streams to `reconstructed/world-order/parts_order.py`. It has no literal expected
tick or draw list. `ANCHORS` names client calls; `MOVES` and `ADDITIONS` each state a native adapter and why it
exists. Missing recorded anchors fail, and a client-call reordering propagates into the expected columns.
All 42 adjacent swaps across the native tick/GL/software columns fail the order comparison.

The adapters are deliberate preservation of the current native runtime:

- The sound hook uses MoveHero's position in the stream. The shared MoveCharacters call maps to the character
  tick; its renderer maps to hero, player and actor draws, which the native runtime splits into three hooks.
- Native fixture placement, NPC answers, quest steps, progression settlement, social ticking, name state
  and gate travel have no separate matching MoveMainScene call. Each addition is named beside its placement.
- Native combat settlement/points run before helpers. Items combine pick-up/despawn/sparkles after helpers;
  object and weather updates consume the current character positions later in the tick. The original has
  MoveObjects, MoveItems and ambient calls before MoveHero. These differences remain explicit, unchanged.
- Native environmental and particle hooks combine original calls from several positions. EffectManager
  actor instances draw after native particles; the original manager update/render calls precede the sprite
  and particle section. GL helpers separate players and actors; software helpers follow the environment.
- The clicked-point marker is a native viewer aid. Item labels and names are separate native overlay hooks;
  the original handles them inside character/UI/GFx callees. Their placement is recorded as an adapter.
- Haze anchors to the original interface-weather call after BeginBitmap. Its native hook still runs before
  item/name overlays.

The ordinary stream defines the static column projection. The original's objects-first worlds, omitted
terrain, second sprite/particle pass, loading/ready skips and UI branches are separately compared under
Unicorn. A static column cannot represent every such conditional pass; this milestone does not claim that
it does, or change the runtime to reproduce those branches. Open/pre-tick/frame/report retain their separate
WORLD-RT-001 native regression pins. All 23 parts.def rows and all six numeric columns are unchanged.

## Planted mistakes and review

Each mutant changes C source, compiles a fresh library and compares 400 cases with original instructions.

| Mistake | Differing cases |
|---|---:|
| Swap MoveHero / MoveCharacters | 377 |
| Drop MoveObjects | 377 |
| Drop the ready guard | 23 |
| Drop first-tick selected-character calls | 17 |
| Broaden the Lorencia leaf guard | 2 |
| Drop the top-view second pass | 4 |
| Swap objects / terrain in objects-first worlds | 10 |
| Draw terrain in Icarus | 5 |
| Reverse the castle upper-Y bound | 9 |
| Invert the final GFx refusal branch | 362 |

An early synthetic fixture overlapped a class byte with an opaque manager pointer and stopped on an invalid
read. Separate handles fixed the fixture. The initial checkpoint's ordinary-coordinate comparison missed
a reversed upper-Y test in the C model. The expanded boundary sweep exposed it; the corrected comparison
passes and the matching mutant fails nine cases. Earlier reports remain local and are not acceptance proof.
The manifest's first run also rejected a per-family count recorded as a total; the final row expects 2,400.

Self-review checked the diff against the owner brief, AGENTS.md and CONTRIBUTING.md, plus the milestone row.
No independent review is claimed. All executable changes are confined to the validation family/tests.
Runtime source and parts order values remain unchanged, so there is no intended render or hash change.
The final local gate and delivery details are in [the handoff](../handoffs/WORLD-ORDER-001.md).

## Limits

This establishes caller call order and draw success under the scripted host. It does not establish callee
semantics, call arguments, ECX, general memory writes, exception unwinding, side effects from real callees,
wall-clock behavior, full scene initialization effects, image equality or live-game behavior. The static
native adapters remain differences to assess in later fidelity work. No live game, launcher, installed game
folder or protected module was used. Captures, reports and disassembly remain local ignored inputs/artifacts.
