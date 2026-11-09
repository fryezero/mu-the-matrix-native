# RENDER-EFFECTS-024

Implementation in progress on `codex/render-effects-024`, base main `6736cb57`.
Offline/static only. No installed app, live client, launcher, network, server-state, protection-module work or memory writes.

## Scope and addresses

- Two world sprite slots, original LINEAR/CLAMP loader mappings: `0x81ec`, `Effect\lightmarks_red.jpg`, call
  `0x01823365`; `0x854a`, `Effect\light_blue.jpg`, call `0x0182ec0d`. Native files use the OZJ envelope.
- Ferea's one-step `0x413/10` fire emitter: CreateEffect `0x013d2f05` and `0x013d3b33..0x013d3b58`;
  MoveEffect `0x0146d6b9..0x0146d7f5`, shared advance and immediate lifetime retirement.
- Its rand-selected children are `0x8084/3`, `0x806e/4`, `0x8085/0`. The latter two already have consumers.
  New `0x8084/3`: create `0x015d45a8..0x015d4748`, move `0x01646f7f..0x0164723a`, existing sprite render.
- Hammer14's exact `up01 ` versus requested `up01` refusal remains. No guessed name normalization or model swap.
- RENDER-ITEMS-002W owns `0x0f2a` blend light and item draw fits; those are unchanged here.

## Routed versus refused census

Initial instrumented baseline is main `6736cb57`. Diagnostic logging is lane-local and removed from production.
The 14 October 22 views plus 32 DATA-ACQ-002 views, default draw, report six `0x413/10` refusals and one
`0x7f89/28` particle refusal, all in Ferea. The 61-consecutive-draw Lorencia demo and eight-mace fixture add
no unsupported particle kinds. This is a bounded scene census, not a whole-client census.
Ferea's 61-draw baseline at tile 236,152 has 183 refused fire emitters and 11 refused clouds/28.

## Checks, renders and byte identity

Pending final checks. No full lane gate. Heavy jobs use nice 10, make at most four jobs, validator runners two.
Private native tests source `~/Documents/MTM/mu-mac-tools/native/private-env.sh` from the repository root.

## Limits and next

`0x7f89/28` cloud motion, exact-name and unavailable-bone refusals, native/original pose and process-random/counter
phase differences remain. Native before/after visibility does not establish original-client pixel equivalence.
The merge steward owns the full gate and merge.
