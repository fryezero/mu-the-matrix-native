# SYS-MISC-001b handoff

## Final state (resume, 2026-10-28 evening, Claude Opus 5.5)

Merged. Resumed at `75a70d9` on the same branch. Added `--scroll-check` to
the isolated viewer and recorded the text-layout, scrolling and hook review in
`docs/research/client-help-window.md`. No shared hook needed changing: rows
are short ASCII (keys at most 13 bytes, descriptions at most 25); every movie
field is single-line with no wrap, the same as the original movie; one chat
description field and the installed chat-tab label clip at the field edge.
Hotkey lists reach their last scroll position (12 for mode 0, 8 for mode 1);
the mouse wheel already reaches the movie through the shared router.

Merged latest main (conflicts only in status/handoff/roadmap lines and
validators.toml; both sides kept). Checks on the merged tree:
`tests/test_help*.py` with private inputs 13/13; `test_help_layer.py` 2/2;
registered validators validate_help and validate_help_controller 2 pass
(887 synthetic cases, 18 mutants); registry suites 38 tests OK (21 optional
skips); full locked `scripts/local-macos-ci.sh`: 38 suites, 1,630 tests,
0 failures, 208 optional private skips, audit 1,585 files 0 rejected, fixture
replay 11/11 scenarios. Not done: an original-client image comparison of the
clipping, the original platform mode-getter preference, and an F1/menu route,
which the recovered input code does not establish.

## Earlier WIP handoff (14:45 deadline)

2026-10-28. Owner hard stop is 14:45 CDT; leave a pushed handoff by 14:40.
Keep this worktree for resumption. No merge lock acquired, queue entry added
or PR opened. Issue #236 owns this slice; #208 remains stopped and untouched.

Branch `codex/sys-misc-001b`, worktree `~/Documents/MTM/worktrees/sys-misc-001b`,
created from origin/main `374777c`. First reader checkpoint `7dfd443` is pushed.
Current branch commits hold subsequent controller/host work. `tools/python`
and `evidence` are untracked symlinks to the main checkout's inputs. Never
stage them. No client-derived rows, movie bytes, captures or images committed.

## Current source state

- `reconstructed/help/help.[ch]`: fixed 512 by 136-byte helpdata reader, reusing
  the existing data decoder. Missing, truncated and corrupt files clear output
  and return statuses. Native truncation rejection is distinct from the
  original's unchecked short fread behavior.
- `help_controller.c`: copied providers, zero-ID stop, independent category
  bytes, retained third list, mode filtering, ordered row calls, InitText,
  SetPosCenter, ClearDataProvider and base-load refusal. Native capacity and
  unterminated-string refusals are explicit.
- `validate_help.py` / `validate_help_controller.py`: pinned instruction
  comparisons and compiled production-source mutants. Manifest rows are added
  for both. Preserve these small shared-registry additions when reconciling
  VERIFY-HARNESS-002.
- `native/help`: isolated real-movie SDL/headless test viewer. It checks movie
  provider lengths, reuses one frame buffer/texture and uses native test
  headings. Build outputs belong in lane scratch.
- `world/world_gfx_help.[ch]`: one-time installed-row load; no frame hook or
  allocations in the frame loop. GlobalText headings with compact English
  fallback; existing native Latin-1 conversion; explicit standard mode 0.
- Minimal shared hooks: optional HelpWindow enum/file/alignment, ready flag,
  native Ctrl+H toggle, Esc close, world startup load, optional `--gfx-open help`,
  input forwarding and build entries. A pre-existing unbounded item-service
  close guard is narrowed to actual store movie IDs so it cannot block Help.
  The legacy F1 and bare-H routes remain unchanged.
- Native synthetic adapter tests cover valid/missing/truncated/corrupt input,
  toggle/release, chat focus, Esc and readiness invalidation. A two-line movie
  UIInit response was added to the existing GFx stub.

Full evidence, addresses, source digests and semantic limits are in
`docs/research/client-help-window.md`.

## Checks actually completed

- Reader: 56 comparisons, zero mismatches. Families: 48 valid synthetic,
  6 corrupt, 1 missing, 1 installed. 25,088 original row decode calls; all seven
  compiled mutants caught. Registry run omits installed data, so expects 55.
- Controller: 832 comparisons, zero mismatches; all eleven compiled mutants
  caught. Constructor provider projection 64, build 64, hotkeys 192, chat 64,
  reload 192, loader 192, base-load refusal 64. C++ base/vector/callback/STL,
  string and conversion services are explicit boundaries. Constructor trace
  checks callback ownership/registration, but native C only compares the
  provider projection. Allocation/refcount/exception internals are not ported.
- Private Help tests: 13/13 pass. Native synthetic adapter tests: 2/2 pass.
- Existing GFx2: 16 tests, 8 pass / 8 optional skips. GFx3: 12 tests, 6 pass /
  6 optional skips. Input router: 13 tests, 12 pass / 1 optional skip.
- Validator registry: both help validators pass, no fail/error/skip. Registry
  consistency suite: 17/17 tests pass.
- Native client build passes. Isolated movie modes show 32/14 and 28/14
  hotkey/chat rows with actual movie count parity. Both tabs inspected.
- Isolated SDL window passes. Native client headless GL reaches scene 6 in
  95 frames, HelpWindow over the world inspected. Actual native client window
  opens with Ctrl+H, closes with Esc, reopens, switches to chat by mouse and
  closes. Both tab captures inspected. Finite script exits at frame 140,
  9.26 seconds, with `--no-store --no-audio`. An earlier test window was
  terminated after confirming its PID/command because `--frames` bounds only
  headless mode. Use `--seconds` and/or a scripted `quit` for a window run.

Final registered run: 887 synthetic comparisons and 18 compiled mutants pass;
the installed reader case adds one, total 888. The final window also uses the
installed GlobalText export and resizes to 1024x768. Both tab renders inspected;
center position and rows remain visible, but some long headings/descriptions
clip in fixed movie text fields. It exits at frame 145 in 8.98 seconds. Review
that visual limit before final acceptance; no original-image claim is made.

No full `scripts/local-macos-ci.sh` gate, latest-main merge, PR or installed
Preview app refresh is claimed. No original client or network ran.

## Exact next steps

1. Inspect this branch's final diff and integrate the latest main as part of
   the common brief's final queue/lock sequence. Reconcile the small
   Makefile/GFx/input/validator registry additions with active lane changes.
2. Run the registered validators and relevant tests below. Review the bounded
   constructor projection and original code-page limits before calling the
   entire original C++ constructor recovered. A native callback lifetime is
   tested, but it does not reconstruct C++ refcount internals.
3. Rebuild the native client, repeat Ctrl+H/Esc/tab checks after final integration
   and review the fixed-field heading/description clipping with installed
   GlobalText. A 1280x800 to 1024x768 window run already confirms placement
   and tab content; the shared size hook uses SetWindowSize.
4. Acquire the queue/lock only when a full current-main Mac gate and merge can
   finish. Run the full gate, repair real failures, open/merge the PR, release
   the lock and clean up per the brief. Do not resume other SYS-MISC windows.

```sh
MU_RECOVERY_INTEGRATION=1 ./tools/python/bin/python -m unittest discover \
  -s tests -p 'test_help*.py' -v
./tools/python/bin/python -m unittest discover -s native/tests -p test_help_layer.py -v
MU_RECOVERY_INTEGRATION=1 ./tools/python/bin/python scripts/run_validators.py \
  --private --only validate_help,validate_help_controller --jobs 1 \
  --report '<lane-scratch>/registry'
```

The installed root is `game_root` in Preview Native Data's setup.json. Read
only that field; do not log whole settings. Existing inputs: pinned evidence,
`scratch/gfx/all-bridge/HelpWindow.swf`, and `scratch/polish/libmugfx.dylib`.
The local JRE is `gfx-deps/jdk/Contents/Home/bin/java` if JPEXS is needed again.

## Cleanup and retained inputs

Delete lane `scratch/sys-misc-001b`, `renders/sys-misc-001b`, native/build and
Python caches after summaries are committed, before the deadline. They are
disposable builds, logs, AS exports and screenshots; none is a new input.
Keep the worktree and its two untracked evidence/Python links. Rebuild from
source on resume. Do not remove another lane's scratch or the shared inputs.

Cleanup completed before the owner deadline: lane scratch/renders, native/build
and the task-created Python caches were deleted. The worktree and its two
untracked input links remain. The committed finding and this handoff retain
the counts, commands and limitations; no generated output is needed to resume.
