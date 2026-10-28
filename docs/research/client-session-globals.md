# Session and runtime globals, SESSION-GLOBALS-001

This is native lifetime plumbing. Reconstructed client routines, routes, record layouts, fixture policy and
hash pins are unchanged. No original client, launcher, live service or installed data was used.

## Ownership inventory

| Former process state | Owner now |
|---|---|
| `mu_lang_shared`, including its cached failed load | Explicit `mu_lang_load` / `mu_lang_free` lifetime in the world, shell, GFx/options/item views and standalone render tools. Render-character environments borrow their owner's language pointer. Names already had an owning slot. |
| Helper `imps[]` and attachment/model/host pointers | `mu_world_helpers.imps`, released only by that helper instance |
| Pet `step_context current` | The pet process's own helper binding, accessed through the existing callback context |
| Skill demo class lists, keys and lazy-ready flag | `mu_skill_demo` in each skills fixture; standalone demo callers explicitly own a model |
| Profiling file, phases, frame/GPU counters, GPU wait callback and pacing start | Zero-initialized `mu_perf` in each front end; the world and GFx borrow it |
| World GL elapsed-query ring | The front end's profiling context; world GL teardown deletes its queries. Closing the log clears measurement state while preserving the query ring until that teardown. |
| World part dispatch sequence and lazy initialization flag | Sequence built and checked for each world runtime |
| Item/map fallback text rings, particle object scratch ring and GFx quest-item name | Their item/map/particle/view owner |
| Other core/world temporary draw, tooltip, pick, label, dialogue and packet buffers | Automatic call-local storage; consumers copy or finish consuming it before return |
| PNG CRC lazy table | Compile-time constant table with the same polynomial and values |
| Fixture behavior-name lazy registry | Compile-time constant generated registry |
| Audio log's process-wide host-number counter | The append log owns stream identity: opening-file offset plus one, serialized across opens with the file lock. Sequence/tick/cue state remains in each audio host. New files start at host 1. |

Remaining process-wide data in `native/core`, `native/session`, `native/world` and `native/fixture` are read-only
lookup/default/format tables, part/transport/behavior operation tables, route/layout descriptors, names, model
paths, schema constants and literal strings. The portable and GL builds have separate immutable part lists.
The world CLI no longer keeps its tool object or previous GFx tick in static storage. Environment variables
remain caller configuration read when an owner opens; changing them does not mutate an already-open owner.
The OS clock, GL context and front-end audio/window services are external resources, not replicated session data.

The cleanup also releases the runtime's existing map session and detaches/closes its map view before its GFx
layer disappears. Travel still retains the map session until the runtime closes.

## Verified lifecycle evidence

`native/tests/test_session_globals.py` builds real production sources with renamed tool entry symbols, rather
than textually including a C implementation. It executes each of the eight committed fixture scenarios with
seeds 17 and 29, sixteen sessions consecutively in one process, and compares each run with its own fresh process.
Both the complete JSON output and binary journal, including scalar-zone state snapshots, must be byte-identical.
The host supplies 100 ticks so send-only scenario tails run as they do in the existing fixture suite runner.

A second test invokes the real world tool twice in one process with different language directories and skill
lists, then repeats each in a fresh process. State output and software image hashes agree, including the Imp
attachment. The second world has two learned skills rather than the first world's one.

A third test overlaps two world runtimes, each with different language tables and a rendered Imp. It destroys
the second, verifies the first's text and unchanged image, and exercises two independent skill demo models and
profiling contexts. Closing one profiling context preserves the other's phases and frame counter.
These tests use authored synthetic worlds/tables and loopback fixtures only.

## Evidence boundary

These tests establish native ownership and deterministic offline re-entry. They do not reconstruct new x86
behavior, prove threaded world simulation, or establish live login/account lifetime. Existing instruction
families and hash pins remain authoritative; this milestone does not replace their evidence with a new oracle.
World-session lifetime across account/character replacement still belongs to SESSION-ACCOUNT-001. Wire,
crypto/decode and the existing domain limitations remain separate. GFx transient serialization buffers outside
the audited directories and the underlying Ruffle process are outside this milestone's concurrency claim.

Final locked gate and differential counts are recorded in [the handoff](../handoffs/SESSION-GLOBALS-001.md).
All lane scratch, binaries, renders and the worktree are removed after merge; no new private input is retained.
