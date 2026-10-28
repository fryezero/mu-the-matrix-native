# SESSION-GLOBALS-001

Implemented on `codex/session-globals-001` in the requested isolated worktree. Read the 2026-10-27 port brief;
no original client or launcher used. [Ownership inventory and evidence boundary](../research/client-session-globals.md).

Moved language caches, helper attachments, pet callback binding, skill demo tables, profiling/pacing/GL queries,
part sequence caches and return buffers to their owners. Transient core/world buffers are call-local; CRC and
fixture registries are immutable tables. Audio log stream identity belongs to its append file. Runtime map
state/views now release at the correct lifetime boundary.

Three committed lifecycle tests pass: sixteen consecutive fixture sessions versus sixteen fresh processes,
with exact journal/snapshot/JSON equality; two different-input world runs versus fresh processes with matching
state/render hashes; overlapping world/language/helper, demo-table and perf owners, including other-owner close.
The eight fixture scenarios, reconstructed sources and existing hash pins are unchanged.

Final gate and differential evidence pending. The final merge sequence uses the shared merge lock and integrates
latest main before the complete local Mac gate. Checkpoints are pushed, including `dc872c3` and the clean merge
of RENDER-WORLDS-H main `40f34a9`.

Remaining: account-owned lifetime and the already-recorded wire/live/domain work. This milestone adds no live,
account, threaded-simulation or Ruffle concurrency claim. No new retained input is needed. After merge release
the lock, delete the entire lane scratch/render/build outputs, remove the worktree and local branch, and only
fast-forward the main checkout if it is clean and on main.
