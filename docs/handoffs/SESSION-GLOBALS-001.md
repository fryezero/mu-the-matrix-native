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

## Final locked checks

Lock acquired 2026-10-28 09:46 CDT. Latest main `7d813a9`, including RENDER-WORLDS-H and AUDIO-002C, is integrated.
Clean native build followed by `bash scripts/local-macos-ci.sh` passes: **1,519 tests in 38 suites,
188 explicit private/optional skips, zero failures**. The native suite has 704 tests. All eight fixture
scenarios pass, **67 inbound frames, zero unbound/undecodable**, with the existing two unrecovered intents
and six unsent frames still reported. Viewer and read-only reader builds pass; readers were never run.
Repository audit: **1,438 files, zero rejected**. No hosted workflow was dispatched.

Four baseline/main-versus-milestone synthetic drives agree in stdout, stderr, exit status and **16/16 PNGs**.
The before/after source IDs, configurations and manifest digest are in the finding. Separate focused shell
checks pass, 23 tests with one expected skip. The first development gate exposed an unbound character-select
language callback; setting `gc.text_user = s` fixes it, and the complete final gate includes that regression.
The earlier interrupted/mixed-build attempt and failing development gate are not acceptance evidence.

Instruction reruns use the existing restored Wine captures and unchanged family boundaries. No new target
addresses, live evidence or native-Windows comparison is inferred.

| Registered check | Cases | Controls caught |
|---|---:|---:|
| Helpers | 8,667 | 11/11 |
| Session-skill serialization and points | 120 | 5/5 |
| Pets | 1,062 | 9/9 |
| Base skills | 9,696 | 11/11 |
| Skill-server packets | 548 | 6/6 |
| Master tree | 7,876 | 3/3 |

All have zero mismatches. The first optional run skipped four rows before input paths were supplied;
those four were rerun successfully using existing offline snapshot/installation paths, without copying inputs.
Fourth-tree registered check is finishing.
Reconstructed sources, manifest families, layouts, fixtures and golden hash pins are unchanged from main.
Self-review covered owner release order, callback contexts, remaining mutable statics and the milestone spec;
no independent agent review or live-game comparison is claimed.

The final documentation follow-up changes evidence only. The gate's tracked runtime source was committed at
`0e2ae05`; the two untracked evidence/Python input symlinks and evidence-only documentation edits account for the
fixture runner's dirty flag.

Remaining: account-owned lifetime and the already-recorded wire/live/domain work. This milestone adds no live,
account, threaded-simulation or Ruffle concurrency claim. No new retained input is needed. After merge release
the lock, delete the entire lane scratch/render/build outputs, remove the worktree and local branch, and only
fast-forward the main checkout if it is clean and on main.
