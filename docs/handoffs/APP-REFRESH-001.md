# APP-REFRESH-001

Implementation checkpoint, 2026-10-28. Worktree `worktrees/app-refresh-001`, branch
`codex/app-refresh-001`, initial main `7d813a9`. Offline only; no original client,
launcher, live read, account, network or protection work.

## Findings and fixes

- The expected `~/Applications/Mu The Matrix Native Preview.app` was absent at
  inspection. A clean current-main native/viewer/app build succeeds with the
  existing real ABI-3 Ruffle library from `scratch/polish/libmugfx.dylib`.
- The launcher default scratch path predates the Documents/MTM move. Prefer the
  current path when present, preserving the legacy fallback and environment
  override. The new temporary-HOME regression fails before the change and passes
  afterward.
- INPUT-001 selected-skill smoke exposed zero mana in all three seeded world
  session paths. The skill migration reads hero context from the session, whose
  seed deliberately supplies only class/place. World fixtures now compose the
  existing progress behaviour's baseline stats/resource replies. Combat's A0/30
  initial join and respawn retain its HP policy and obtain MP/SD/AG from that
  independent progress server model, instead of overwriting them with zeros.
  No client checks or encrypted-send refusals are bypassed. These are synthetic
  offline fixture policies, not reconstructed account/join semantics.
- The new three-path regression covers skills-only, players and actor/combat
  sessions and checks nonzero MP/AG without moving the hero from its spawn.

## First run and smoke checkpoint

- Signed production-pin app, `env -i`, temporary HOME/CFFIXED_USER_HOME and
  `PATH=/nonexistent`: C conversion and root/component manifests pass. Base
  first run converts 179 movies and 82 NaviMaps with optional captures absent.
- A second clean HOME imports freshly re-exported, manifest-bearing existing
  snapshots through the app setup: 27 language files, 32 object/sidecar files
  covering 16 worlds and one sound table. No new live acquisition.
- Existing owner Native Data has legacy setup.json and no manifest. Verification
  refuses it. Owner data remains unchanged at this checkpoint.
- Synthetic doctor passes on Apple M5; scene flow and 90-frame walking recipe
  pass, one arrival, zero path refusals, 12 units per position step.
- Real app window: 516 frames, 27.79 seconds, twelve panel views plus chat,
  screenshots inspected. Inventory, character, imprint, master/fourth/fifth
  trees, quests, move, friends, options, store and system menu open/close.
  Twelve unavailable keys report their names and J reports its empty handler.
  Tree data gaps remain explicit. Terrain, hero, NPCs, remote armour and
  effects are textured; no crash or unexpected console error in that run.
- Three real-data travel operations, Lorencia to Devias to Noria to Lorencia,
  pass in mu-world, zero travel failures. Windowed click travel remains next.
- Full gate, final smoke repetition, installation and merge are still pending.
