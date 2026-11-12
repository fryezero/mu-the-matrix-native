# APP-POLISH-009

## WIP checkpoint, 2026-11-11 21:40 Chicago

Done: read the complete lane/common briefs, APP-POLISH-007/008 and owning UI sources.
Built baseline root and `mu-world`; baseline binary SHA-256
`4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.
Original collection resize `0x00ac09b2` calls `0x00aae4ae` for every non-null
handler. Unicorn: 60 cases pass. Native fit: 200 cases pass, no mutants yet.
The initial real-movie 640x480 probe confirmed the original fixed scales overflow.
An initial bounded fit keeps inventory, CharacterInfo, quest, Warps and trees above
the HUD. CharacterInfo now reads the same session records as the HUD; this is
presentation only. No fixture stat formula, combat rule or installed app changed.

Left: merge latest main including UI-WINDOWS-001 #372, finish original/static
layout evidence and compiled mutants, automate all-window/size and demo ownership
checks, inspect proof captures, run affected tests/validators plus reduced private
checks and the default identity sweep, finish research/status/PR documentation.

Next: merge `origin/main`, then include Command, Gens, PetInventory, Gremory and
MatchingSelect in the real-movie layout sweep. This checkpoint is not PR-ready.

Local inputs to resume: `~/Documents/MTM/mu-mac-tools/native/scratch/app-polish-009/`
contains the rebuilt baseline binary, preliminary logs and real-movie geometry.
The worktree is `~/Documents/MTM/worktrees/app-polish-009`.

## WIP checkpoint, 2026-11-11 22:00 Chicago

Merged main `710ac816`, including UI-WINDOWS-001 #372, as `66b4357c`.
The shared sizing conflict retained both creation sizing for presentation windows
and the universal resize dispatch. Root and client/world builds passed.
First focused private run: 5 tests pass in 72.042 s, including the five demo
characters and preliminary geometry for 272 window/size/backing-scale combinations.
The latter did not yet assert actual visibility. The strengthened test adds that
assertion, open-window resizing, original map mask/centering and pointer close
activation. QuestSummary's generic show route now uses its actual open/close
methods. The recording host distinguishes quest/tree close delivery from owning
controller behavior.

The strengthened layout run is waiting in the foreground for load <=14 with free
memory >=25%; no result claimed. Research and the validator manifest row are now
written. Compiled mutants, final affected/private checks, identity sweep, captures
and PR-ready documentation remain. Resume with the pending strengthened-test log
under this lane's scratch, then the selective checks. No ready-prs entry yet.

## WIP checkpoint, 2026-11-11 22:20 Chicago

Final production source is `6c62c838`. Latest fetched main remains `710ac816`.
Final root build: 1.333 s; explicit client/world rebuild: 12.862 s; repository
audit: 2,193 staged files, 0 rejected, 25.590 s. Rebuilt final mu-world SHA-256
`e90d3754d2e90cd6b9d1d6484861f6c53d30c08f5ebb11df2a185415a072a4d8`, distinct
from the baseline above. HUD width/bottom arithmetic is now covered by the
compiled-negative-control definitions as well as panel fitting, ten mutants total.

Strengthened layout run: pointer close delivery for all sixteen panels and
open-window resizing pass. One 1024x699 subprocess refused startup without stderr;
its isolated rerun, at both backing scales with map checks, passed in 5.542 s.
The first strengthened matrix had all other sizes pass. A full final private
run is still required; no completion claim from the initial refusal.

Post-build selection: 11 validators, 133 portable work items, including 129 native
modules. Thus private checks use **8d reduced**. The pending private-selection log,
then affected no-mutant validators, ten changed-target mutants once, affected
portable tests, focused private fixture/UI checks, identity sweep and endpoint
captures are next. No PR or ready-prs line yet. All logs remain in the lane's
scratch directory named above. Runtime code and docs are checkpointed remotely.
