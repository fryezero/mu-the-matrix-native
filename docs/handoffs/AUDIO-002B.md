# AUDIO-002 part 2

Owned branch `codex/audio-002b`, worktree `~/Documents/MTM/worktrees/audio-002b`, base `a278d93`.
No original client, launcher or live service is used.

Claimed scope: native audio cue routing and log provenance; minimal character/actor/NPC call-site adapters;
audio validators/tests; this handoff, the audio finding and AUDIO-002 status rows. Combat files, music
43/44 and the virtualised frame gap are excluded.

Work in progress: wire the verified NPC voice fragments and model registration into the migrated character
loop, route NPC talk sounds through its session ring, then inspect already identified non-combat ambience
sites. The third NPC voice requires buff 0x1b state, absent from the current viewport records; unknown
inputs must stay explicit. Preserve the visual RNG, rendering and existing comparison assertions.

Acceptance remains pending. The local baseline gate and new bounded checks will be recorded here before
publication. Local artifacts stay in `~/Documents/MTM/mu-mac-tools/native/scratch/audio-002b/` and
`~/Documents/MTM/mu-mac-tools/native/renders/audio-002b/`.
