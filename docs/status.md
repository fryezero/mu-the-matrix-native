# Current status

Updated 2026-10-17. The target is the exact installed Mu The Matrix client.
The later destination is native macOS gameplay. A playable source build does
not exist yet.

## Working components

- The startup decompressor is reconstructed in C. Four original compressed
  blocks match independent decoding, but the result is still protector code.
- The isolated QEMU x86 Linux/Wine guest restores a repeatable 23,572,480-byte
  code section. The selected second image section is also captured twice with
  matching digests. No Windows PC is required for this analysis route.
- Authored 64-byte copy/clear source matches captured instructions in 393/768
  synthetic cases. Controlled cofactor/inverse source matches 1,680/1,050 cases.
- The BMD filename call path reaches a version-dispatching model-read routine.
  Its v12 decoder now has authored C matching 4,048 synthetic cases and all 180
  installed v12 payloads, covering 3,176,971 encrypted bytes. Exact overlap and
  signed-length behavior are preserved. [Evidence](research/client-model-loader.md).
- The observed v15 key-setup target has authored C matching 1,320 synthetic
  instruction cases across 16/24/32-byte keys, alignments and no-op gates.
  [Key evidence](research/client-lea-key.md). The ECB decoder now matches 12,960
  actual-code guest cases and 1,152 scalar instruction cases. All 11,583 installed
  payloads match the independent reader, separately from original-code testing.
  [Decoder evidence](research/client-lea-decode.md).
- Images: 19,703 of 19,707 wrapper candidates decode. One remaining candidate is
  editable mesh text; three are inconsistent terrain images.
- Models: 12,663 of 12,754 unique BMD-extension files parse. Versions 10/12/14 pass
  all 701/180/216 files; v15 passes 11,566 of 11,583. Seventeen v15 inputs remain
  rejected and 74 other/table envelopes unsupported. Rejections have precise
  field diagnostics; original handling remains unknown.
- Selected bone/pose instructions show that dummy records leave output slots
  unwritten, while children compose from prior caller-buffer contents. Those
  contents are unknown. Raw call-search totals remain candidates.
- The hierarchy pose-composition source matches 5,176 controlled binary32
  instruction cases; 24 out-of-domain attempts are recorded separately.
  [Evidence](research/pose-concat.md). Actual prior pose state remains unknown.
- The rotation helper `0x00d00724` (ZYX Euler angles to x,y,z,w quaternion)
  has authored C matching 8,012 controlled cases bitwise. Its actual body and client
  SSE2 sine/cosine run with captured flag 1 and no stubs. The C substitutes host
  libm trig; binary32 trig results agree in all 48,072 calls, including
  host-midpoint candidates. [Evidence](research/client-rotation.md).
- The BMD bone-track loop `0x012b4225..0x012b4441` has authored C
  (`mu_bone_tracks_read`). The actual loop, memcpy, operator new/malloc and
  rotation/trig code run without client stubs; only the HeapAlloc import and
  two uncaptured globals are modelled. 342 synthetic comparisons and all 11,962
  installed v12/v14/v15 models accepted by the readers match, including
  4,759,146 per-key rotations. Output layouts and allocation behavior are recorded.
  [Evidence](research/client-bone-tracks.md).
- The pose builder `0x012b5064` has authored C (`mu_pose_build`) plus its
  quaternion compare, slerp, quaternion-to-matrix and angle-to-matrix helpers.
  It slerps q(prior action, prior frame) toward q(current action, integer frame)
  by the frame fraction, lerps positions, resets out-of-range frames to key 0
  and composes each bone with the root global or its parent's output slot.
  Seeded by the actual bone-track loop and run with no client stubs, it matches
  483 synthetic calls, 1,822 direct helper calls and 47,833 calls on all 11,962
  installed models the readers accept. Lerp and modulo-wrap controls fail.
  [Evidence](research/client-pose-builder.md).
- CPU skinning. The model transform `0x012b5bde` (`mu_model_transform`)
  multiplies each vertex by one bone matrix from the pose builder, applies
  body scale/origin, rotates normals and computes clamped per-normal light.
  The animation tick `0x012b4dd3` (`mu_animation_tick`) sets the prior
  frame/action when the integer frame changes. Against the actual
  instructions, with no client stubs, they match:
  * 226 synthetic transforms, 24 synthetic models chained through the actual
    builder and 481 synthetic ticks;
  * all 11,962 installed models the readers accept, run after the actual
    bone-track loop and builder (3,814,006 vertices), plus 35,871 installed
    ticks.

  Four negative controls fail. All 314 builder call candidates are classified.
  Keep-root calls follow a root setter used for attachments. The mesh draw
  `0x012b8d1d` emits one `glBegin(GL_TRIANGLES)` per mesh with per-corner
  glTexCoord2f, glColor and glVertex3fv straight from the transform output;
  this is a static reading against import slots named from the guest's Wine
  opengl32. [Evidence](research/client-skinning.md).
- All 370 effect JSON files parse and their 92 distinct texture references exist.
- Frame loop (static). The frame driver `0x01851d39` runs game logic in fixed
  40 ms steps from an accumulator. It caps rendering at 25 FPS with
  `Sleep(40 - elapsed)` after SwapBuffers, timed by GetTickCount. The 40 is a
  compiled-in immediate at `0x0185266b`, `0x0185266f` and `0x01852690`; no
  config, data or server value feeds it. Themida packs the code, so the bytes are
  not in `main.exe` and changing the cap needs an in-memory write after unpacking.
  The four-vertex fans come from the terrain tile renderer (one per tile per layer),
  terrain decals and 2D UI helpers. The only per-frame VBO streaming is the JSON
  effect system: a 144-byte sprite buffer rewritten whole, and a 144,000-byte
  particle buffer written as `n*144`-byte prefixes, each drawn as `GL_QUADS`.
  [Evidence](research/client-frame-loop.md).

## Verification

The suite discovers 236 tests. Portable checks pass 218 and explicitly skip
eighteen private-input checks. In the frameloop worktree, the new frame-map check
passes with `MU_RECOVERY_INTEGRATION=1` and `MU_GAME_ROOT`; the full opt-in suite
was not rerun there. In the skinning worktree, opt-in integration passed all 209
earlier tests. The mugl and hotpatch source checks need no private inputs.
In the bone-tracks worktree it passed all 155 tests from before the seven launcher-guard tests.
The rotation worktree's opt-in integration passed 142 of the earlier 147.

The v14 reader matches its pinned independent oracle on 216 installed files and
91 synthetic vectors. A complete model rescan preserves every one of 12,754
statuses and all 12,663 previously pinned parsed-input hashes. The exact-client
v12 comparison runs actual captured leaf instructions without helper stubs.
Its deliberately wrong feedback order fails 312 overlap cases.

Detailed identities, counts and CI references are in `evidence-index.json`.
Original-file scan manifests and binary evidence remain ignored local inputs;
CI runs authored fixtures and reports the private skips explicitly.

## Runtime boundary

The original client works on Windows. Earlier isolated CrossOver `win10_64`
starts fail with a Rosetta selector error. A new `win10`/win32 compatibility path
uses .NET 4.8, builtin WIC/GDI+, WPF software rendering and the default IGCN skin
in a cloned installation. The authored setup and local validation are recorded
in [the CrossOver finding](research/mac-crossover-32bit.md), issue #39.
The fresh test bottle passed all eight synthetic image-pipeline steps, kept
the launcher alive for 65.8 seconds, and was deleted after validation.
The owner now reports GAME START, login and gameplay in MuMatrix32. This is
original-client compatibility gameplay, not a recovered native build. Issue #42
adds an idle-bottle startup reset and monitor validation. An injected stale
source-to-monitor link reproduces the exact Settings exception; the guarded
reset rebuilds the link and Settings opens again in MuSettings-test. Both fresh
win32 and win10_64 bottles have valid monitor registrations. Natural sleep/display
change recovery during an active game remains unverified. MuMatrix32 is reserved
for Claude's frame-rate work and was not modified by this task. No Windows PC is currently available. The separate Mac-only Linux
guest still has outbound networking blocked and reaches an unresolved localhost
connection. Native Windows capture/equivalence
remains unverified, although the optional Windows helper builds and its own
memory/hash smoke checks pass under Wine.

MAC-PERF-001, issue #45 / PR #47, adds an opt-in pinned Rosetta Timewalker
cache build, matching-checksum x87 self-check, authored PE32 transform/GL probes
and launcher selection with plain CrossOver fallback. MAC-PERF-002, issue #48,
adds an authored MIT wrapper that defaults fast translation to arguments
containing `main.exe`. MuTheMatrix.exe and .NET dependencies use the real loader;
the unfiltered fast runtime hangs on .NET. The installer builds/signs and
fingerprints our wrapper in the cache without editing pinned upstream source.
Caller substring overrides and an empty apply-to-all override are supported.
The idle-process guard, prefix-scoped reset and plain monitor check remain.
The real launcher produced its normal window in setup-owned MuX87Filter-test
under required-fast selection with the default filter. The matching-filter
benchmark measured 279.1 Mverts/s fast versus 2.7 plain with matching checksum
3.904312. The test bottle was removed. All 163 portable tests pass, with fourteen
private-input skips; both review axes and the publication audit pass.

MAC-PERF-003, issue #51, adds the authored MIT mugl OpenGL batching proxy,
361-name export generation, host-tested primitive conversion and a default-on
setup step with `MU_GL_BATCHING=0` opt-out. Deployment checks Wine's system32
builtin marker and records the proxy SHA-256. The setup-created MuMugl-test
bottle passed three plain/proxy framebuffer comparisons at 20,000 quads/frame:
38.7 to 118.7 FPS for one quad/block, 65.2 to 118.9 for four, and 76.8 to 119.6
for sixteen. All thirty-six GL regression hashes match, with zero state failures or
GL errors. Setup off/on/rerun checks pass. The launcher started main.exe with
active batching and a 25.0 FPS log; one interval reduced 999,569 blocks to 8,966
draws. The test bottle was removed. Owner in-world testing remains open.
The x87 hypothesis is superseded by Claude's reported in-world EIP profile,
which places 73% of main-thread samples in OpenGL; fast x87 did not improve
in-world FPS. These figures are compatibility evidence, not native recovery.

See [measurements and limits](research/mac-performance.md) for local checks and
Claude's separately supplied launcher-to-main/profile observations. Post-patch
in-world FPS remains owner testing. MuMatrix32 was not touched. This improves
original-client compatibility; native source recovery acceptance gates are
unchanged.

MAC-PERF-004, issue #57, publishes Claude's opt-in v7.0 CPU hotpatch source
stacked on open PR #52. Local pinned-input generation reproduces nine helper
patches, 18,583 inline sites and 50,977 peepholes. Original byte tables and the
xform prologue stay private; CI uses empty tables with game hooks disabled.
Claude reports 20.5 FPS at mask 0, 24.1 at mask 7 and 24.7 at mask 15 in the
same approximate hunting area, and zero skinning comparison mismatches over
more than one million in-game calls. These are prior single-host reports,
not rerun measurements; the 44.8% mesh-draw attribution it cites was later
corrected (below). Default setup still uses #52. No running game, bottle or registry
was changed. [Evidence and limits](research/mac-performance.md#mac-perf-004-claude-v70-in-process-cpu-hotpatches).

MAC-PERF-005, issue #59, publishes Claude's opt-in v7.1 source: a native
replacement of the per-corner loop of mesh draw routine `0x012b8d1d`, a native
light-table precompute, a frame-pacing fix, direct batch append and zero-copy or
strided batch arrays, plus the `glstride` framebuffer-hash test. The three small
original patch-site byte sequences stay private (SHA-256 in `targets.json`,
generated into an ignored header); CI builds with zero tables and no game hooks.
Local checks: private regeneration matches the pinned digests and a private rebuild
has an instruction stream identical to Claude's DLL; neither was run. Claude reports
zero mismatches over about 9.5M call-stream, 8.2M direct-append and 2.5M light-table
verification meshes, equal framebuffer hashes at five masks, and, in the default
7599 mask, 24.1 fps at the hunting spot (22.6 at mask 15) with 33.8 ms of work. These
are supplied single-host reports, not rerun. The correction: the v7.0 finding that
the routine took 44.8% of main-thread self time came from a profile of a build
without frame pointers and charged mugl's own code to the caller; the routine's true
self time is about 3%. 25 fps remains the fixed 40 ms logic-step cap, with no single
dominant hotspot left. Default setup still uses #52. No running game or bottle was
changed. [Evidence and limits](research/mac-performance.md#mac-perf-005-claude-v71-mesh-draw-loop-frame-pacing-and-zero-copy-batches).

MAC-PERF-006, issue #61, publishes Claude's v7.2 `mugl.c`: the frame-pacing bit now
waits on a waitable timer instead of Wine's `Sleep`. Claude's diagnostic builds traced
the 17-22 fps seen with pacing on (28 ms of work) to macOS stretching Wine `Sleep`
calls (7-14 ms took 17-45 ms) whenever the game is not the frontmost Mac app, not to
the client's inactive throttle or a double sleep. Claude reports 25.00 fps in the
background over 140 s with 99.6% of frames at 38-42 ms, versus about 24.5 fps with half
the frames late for v7.1, and 24.95 fps frontmost; the logic still runs at 25 Hz. No new
patch site or original byte is added. These are supplied single-host reports, not rerun;
the new code was only compiled here. Default setup still uses #52. No running game or
bottle was changed. [Evidence and limits](research/mac-performance.md#mac-perf-006-claude-v72-precise-frame-pacing-waits).

MAC-KIT-001, issue #63, publishes the owner's reproducible Mac setup kit as
`mac-play/installer/`: an idempotent setup, a read-only verify, a launcher script and a
synthetic test suite that reproduce the hand-built MuMatrix32 layout in a new win32
bottle. The owner reports that the local copy built a fresh bottle in 3 min 44 s with
.NET 4.8 and ran in world at parity or better than MuMatrix32, after six live-found bugs
were fixed. This publication replaced machine-specific siblings with repository sources and
parameters, ships no DLL (pinned SHA-256 only; prebuilt v7.x DLLs are user supplied), keeps
account and Keychain names out of the tree, and runs its 180-check suite on macOS and Linux
in CI. The adapted setup has not been run live, only dry-run and tested synthetically. It
sits beside the older `setup-crossover-32bit.sh`. No game or bottle was changed.
[Evidence and limits](research/mac-crossover-32bit.md#reproducible-setup-kit-mac-kit-001).

## Repository and next work

The private [repository](https://github.com/fryezero/mu-the-matrix-recovery)
contains reviewed authored source, synthetic fixtures and evidence summaries.
PRs #4, #6, #8, #10, #13, #14, #16, #18, #20, #23, #25, #26, #28, #30, #32, #34 and #36 are merged after macOS/Linux checks.
No game executable, asset pack or memory capture was uploaded.

The client-linked v12 milestone is merged through PR #23. Two selected v15
dispatch slots now resolve into restored client code. See
[the capture finding](research/model-dispatch.md). Next trace the original v14 helper or bounded model record-loading/matrix code.
Original types, hierarchy semantics, initialization dependencies, simulation,
networking, renderer/input/audio equivalence and a complete client build remain
unfinished. Read `handoff.md` for exact local artifact paths and entry addresses.

The fixed v15 dispatch scope is merged through PR #26 after macOS/Linux CI.
Hierarchy findings are merged through PR #25. Post-merge review corrections
are merged through PR #28 after both platform checks. Strict model acceptance is unchanged.

The v15 key context is merged through PR #30. The ECB source and guest comparator
are merged through PR #32 after macOS/Linux CI. The guest is shut down. Decoder equivalence does not
resolve the model loader's allocation, hierarchy or actual rendering behavior.

Pose arithmetic is merged through PR #34 after macOS/Linux CI. Next validate original rotation/model
record loading, keeping actual FP state and unknown prior output contents open.

Issue #35 adds a fixed four-byte rotation dispatch capture. Two reads match
value 1; early packed code is refused without a payload and every prior scope
repeats. [Finding](research/client-trig-state.md). Actual FP state and full
rotation/trigonometric equivalence remain open. Guest is shut down.

Issue #37 adds rotation source and an actual-instruction comparison with
8,012 matches, 2,816 alias/alignment and 256 FP-state variants. A wrong axis
order fails 7,547. [Finding](research/client-rotation.md). Client SSE2 trig
algorithms are not reconstructed. Out-of-domain angles, non-finite values and live
caller FP state remain open. No guest run was needed.

Issue #40 adds the bone-track loop source and an actual-instruction comparison.
All 342 synthetic comparisons and every installed v12/v14/v15 model the readers
accept match, including dummy records, zero-count allocations and overlapping
layouts. Skipping zero-size allocations fails 57 comparisons.
[Finding](research/client-bone-tracks.md). Client allocation failure, the real
heap/memcpy feature state, rejected v15 files and pose-builder interpolation
remain open. No guest run was needed.

Issue #46 adds the pose-builder source and an actual-instruction comparison
seeded by the actual bone-track loop. All 483 synthetic, 1,822 helper and 47,833
installed calls match; lerp differs in 364 and a modulo frame wrap in 60.
[Finding](research/client-pose-builder.md). The caller's frame/action choice,
prior output and root contents, live FP state and renderer use remain open.
No guest or CrossOver run was needed.

Issue #53 adds the model transform and animation tick sources, a static map of
the pose-builder callers and the mesh draw's GL order. The transform matches on
every installed model the readers accept, chained through the actual loop and
builder, and the tick matches on 35,871 installed calls. Transposed rotation,
translated normals, per-tick prior updates and an ignored lock limit all fail.
[Finding](research/client-skinning.md). The draw routine was not executed, and
live object state, action changes and the frame loop remain open. No guest or
CrossOver run was needed.

Issue #55 (CLIENT-FRAME-001) maps the message loop, scene dispatcher and frame driver,
including the 40 ms Sleep cap and the fixed 40 ms logic step. It also labels all
24 fan and 27 quad glBegin sites with their return addresses and recovers the
effect system's stream-VBO pattern. Everything is static and checked by
`scripts/client_frame_static.py`. [Finding](research/client-frame-loop.md). Runtime
per-routine counts, `IGC.dll` hook behaviour and whether animation runs per frame
remain open. No guest or CrossOver run was needed, and nothing was patched.
