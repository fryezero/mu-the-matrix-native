# VIEWPORT-MONSTER-001 handoff

Owned branch `codex/viewport-monster-001`, worktree `~/Documents/MTM/worktrees/viewport-monster-001`.
Started at merged SESSION-VIEWPORT-001 PR #183, `54ae63f`.

The same CharactersClient now accepts C2 `0x13`, backed by the one static seed row at `0x0122c426`.
The `monsters` fixture owns placement/wander policy and emits real plaintext frames. Actors and NPCs
render session records and share the single tick-21 leased character loop. The old renderer placement
parser and wander decisions are gone. Cache identity changes rebuild models/effects and GL textures.

Evidence: **1,000 handler + 963 bounded creation cases, zero mismatches; 8/8 compiled mistakes caught**,
plus 3,000 authored parser-boundary checks. The exact original-code/host boundary, unavailable classes,
32-actor cache limit, and temporary unmigrated combat motion bridge are in
[the finding](../research/client-viewport-monsters.md).

NATIVE-WORLD-002 synthetic world: all **120 frame hashes unchanged** from `54ae63f`, with all 120
repeating exactly. Spider movement, Smith model/light and Maple effect stay unchanged.
The monster fixture scenario contributes **4 inbound frames, zero unbound/undecodable**.

Final gate and unchanged-family counts will be recorded after merging the latest origin/main.
Artifacts are retained outside the disposable worktree under the scratch/renders directories named
in the finding. No original client or live service was used; no wire crypto or dispatch generator.
