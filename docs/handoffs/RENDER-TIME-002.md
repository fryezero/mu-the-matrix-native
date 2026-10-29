# RENDER-TIME-002 live half, 2026-10-28

## Scope and result

This milestone runs RENDER-TIME-001's live half on the owner's client under the shared game lock: Lorencia,
mugl patches off, the plan's physical inputs. **The original-vs-native temporal comparison fails.** The live
series is honestly `phase: unaligned`: no pool, animation or RNG history was restored. Beyond the phase gate,
`compare --mode live` reports 477 (run 3) and 433 (run 4) component failures under the declared `LIVE_LIMITS`.

The hero path, walk distance, static-object placement and primary light agree. The failures come from:

- the refused live zoom;
- unaligned animation, pool and RNG phase;
- other characters in the live scene;
- live WorldTime jitter below 25 fps;
- one real discrepancy: the visible-object count.

The [finding section](../research/client-render-time.md#live-half-render-time-002-2026-10-28) gives every number
and the threshold review. [client-render-time-live.json](../research/client-render-time-live.json) holds the
reviewed summaries and provenance hashes. No limit was changed in code.

New source:

- `live-readers/rtsample.c`: a read-only post-draw sampler that emits only sums and counts.
- `live-readers/rtinput/rtinput.c`: a Wine-side input replay, `SetCursorPos`/`SendInput` only, built with mingw
  outside the default build.
- `scripts/render_time_live.py`: `schedule`, `export`, `pair` and `summarize`.
- `scripts/render_time.py`: live mode reports declared-unavailable components as `not_compared` instead of scoring
  them. Native mode ignores the declaration.
- `native/tests/test_render_time_live.py`: 15 synthetic tests (no client, no captured bytes).

## Live sessions (shared game lock)

Before each session `pgrep` was empty, both `.game-lock` paths were absent and the disk had 100 GB free.

- **Session 1, 18:25:34–18:35:02.** The client and launcher were started by this lane through DATA-ACQ-002's
  route: its `login.sh` steps, with `clickstart.exe` and `muinput-fid.exe`, the password from the Keychain into
  the helper only, and the server and MTM-1 positions adjusted to the 960×600 layout.
  - The Events window was closed with its Close button.
  - A player shop's banner sat at the east click target, so that spot was not armed. Two `/move` chat attempts
    did not register.
  - One Lorencia warp by the Warps window (2,000 zen) moved the hero to 146,132.
  - Runs 1 and 2 used the first, target-only sampler. Some of their reads saw WorldTime move, so they can't be
    exported.
- **Session 2, 18:38:35–18:42:26.**
  - The Events window was closed.
  - Run 3 (start 137,129) and run 4 (start 138,129) used the every-edge sampler.
  - The next spot had a figure near a click target, so no third run was armed.
- **Both sessions.**
  - Runs took about 10 s; each lock hold was under 10 minutes.
  - The hero ended in Lorencia 139,130. The client and launcher were quit and the lock removed.
  - `mugl-hotpatch.txt`, `mu-modes.txt` and `LauncherOption.if` were restored byte for byte from rollback copies;
    `cmp` reports them the same.
  - Reads only; no packet or traffic capture. No fight, NPC, item or trade action.
  - Other lanes' native renders (`mu-world` with prefix paths) match `pgrep -fl 'main.exe|MuTheMatrix'`. They are
    not clients.

Capture setup: plain Rosetta (fast x87 off). `mugl-hotpatch.txt` = 0, and mugl logged
`=== hotpatch mask 0: funcs 9/9 sites 18583 peep 50977`; with mask 0 those are sites verified in their original
bytes. Buffering mode stayed `full+vbo`. main.exe SHA-256 = the evidence target `3cf91f3c…`. **The client has no
640×480 mode, so the live client area is 960×600.** The plan's positions were replayed at the same client-area
fractions, and each native twin ran at 960×600 with that scaled script.

## Verification

- Synthetic: `test_render_time*.py` runs 31 tests, 30 passed and 1 explicit private skip. RENDER-TIME-001's 16 are
  among them and unchanged in behaviour.
- Live exports: run 3 gives 21 samples (5 reads rejected for WorldTime moving after the swap); run 4 gives 21 (1
  rejected). There were 0 torn reads, every read took ≤ 4 ms, and inputs were ≤ 4.4 ms late. The client drew
  19.1–20.9 fps.
- Native twins: `render_time.py capture` on the private plans gives 201 samples each, then `pair` on the recorded
  logic ordinals. Walk distance is 223.606798 in all four series.
- An unscored diagnostic native twin of run 3 without the wheel events matches live hero and eye positions
  exactly at 20/21 samples; the remaining sample is 13 units off mid-walk.
- Gate: `bash scripts/local-macos-ci.sh` under the merge lock, on main `3735625` merged in and `native/build` rebuilt
  from clean (RENDER-EFFECTS-004 changed shared struct layouts): **1,669 tests across 38 suites, 212 explicit
  skips, 0 failures**; 11/11 fixture scenarios; repository audit 1,625 files, 0 rejected. No hosted workflow.

## Next steps

1. Find why this client refuses the wheel zoom here. MouseWheel reached ±1 while the zoom index stayed 2 and
   zoom-settled was 1. Candidates are window `0x3e`, the world list `0x00da9d49` and the UI taking the wheel. Then
   port the guard natively, since native zooms where the original does not.
2. Find the cause of the visible-object gap: live 176–198, native 249–290 at the same camera, 960×600.
3. Split live pool sums by owner and score only world-owned entries. Alternatively, capture with no other
   characters present.
4. Phase alignment (procedure step 6): animation starts, pool ages, boid spawn RNG. Until these are aligned no
   live comparison can pass.
5. Adopt the reviewed WorldTime and mid-walk policy (finding, items 1–2) before the next scored run, then capture
   the other thirteen views.

## Inputs kept for a later lane

Under `~/Documents/MTM/mu-mac-tools/native/scratch/render-time-002/`, about 0.5 MB in total, numeric summaries
only:

- `live/run3/` and `live/run4/`: `samples.jsonl` (every post-draw edge), `inputs.log` and `export/` (`series.json`,
  `native-plan.json` and the 960×600 script);
- `bin/`: the session scripts (`login.sh`, `run.sh`, `settings.sh`, `quit.sh`, `env.sh`) and `rtinput.exe`.

Screenshots, native captures and session logs were deleted.
