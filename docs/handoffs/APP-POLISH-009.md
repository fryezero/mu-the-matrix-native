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
