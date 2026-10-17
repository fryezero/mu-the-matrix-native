# meshdraw: native per-corner loop of the mesh draw routine 0x012b8d1d (mugl v7.1)

Source: `meshdraw.c` (included by `mugl.c`), published from Claude's local `meshdraw_v71.c` / `mugl_v71.c` (hashes in
`source-provenance.json`). Decoded by Claude from the pristine in-memory dump described in `README.md` (SHA-256
`6e7957c9...160bfd4`; routine `0x012b8d1d..0x012bb35a`, `ret 0x2c`). Everything below that is not a count of runtime
events is a decoded reading of that routine, not a recovered original source; the statements about verification are
Claude's supplied reports, not rerun in the publication task (see `docs/research/mac-performance.md`, MAC-PERF-005).

## Routine frame (thiscall, ecx = model)
| slot | meaning |
|---|---|
| `[ebp+0x08]` | mesh index i (routine returns early unless 0 <= i < (int16)model[0x24]) |
| `[ebp+0x0c]` | render flags |
| `[ebp+0x10]` | transformed vertex base (per mesh stride 0x2bf20, 12 B per vertex) |
| `[ebp+0x14]` | transformed normal base (same strides) |
| `[ebp+0x18]` | per-normal light intensity base (per mesh stride 0xea60, 4 B per normal) |
| `[ebp+0x1c]` | alpha (float); written only by the mode 0x8000 path |
| `[ebp+0x20]` | mesh selector for UV offset; `[ebp+0x24]` colour scale; `[ebp+0x28]`/`[ebp+0x2c]` u/v offset; `[ebp+0x30]` texture override |
| `[ebp-0x10]` | model; `[ebp-0x20]` mesh = model[0x28] + 32*i |
| `[ebp-0x38]` | draw mode chosen before glBegin: 1 (flag 1), 2, 0x40, 4/0x1000/0x80000/0x8000 (environment group) |
| `[ebp-0x31]` | byte: apply UV offset; `[ebp-0x21]` byte: per-normal light colours (model[0x50], cleared when i == model[0x94]) |

Mesh (`0x20` B): `+0x02` int16 texture slot, `+0x06` int16 normal count, `+0x0a` int16 triangle count,
`+0x14` texcoord array (2 floats), `+0x18` triangle array (stride 0x24), `+0x1c` sub-object.
Triangle (`0x24` B): `+0x00` int8 corner count, `+0x02` int16 v[4], `+0x0a` int16 n[4], `+0x12` int16 t[4].
Tables: light colours `0x089c2120 + i*0x2bf20 + n*12` (3 floats), normal-indexed texcoords `0x072acfd8 + n*8`,
object colour `model+0x54` (3 floats), origin `model+0x78`, secondary light `0x075a9ee8 + i*0xea60`.

## Loop 0x012ba8a0..0x012bb229 (entered after glBegin(GL_TRIANGLES) at 0x012ba893, exits at glEnd 0x012bb22e)
K = 0.99f (`0x01a82fe0`). colour(c) = `alpha >= K ? glColor3fv(c) : glColor4f(c[0], c[1], c[2], alpha)`
(comiss/jb: NaN alpha takes glColor4f, as does C `>=`).

Per corner j of each triangle, by mode:
- **2**: `glTexCoord2f(tc.u + uoff, tc.v + voff)` if byte -0x31 else `glTexCoord2f(tc.u, tc.v)`;
  then, if byte -0x21, colour(light colour of n[j]).
- **4**: colour(model+0x54); `glTexCoord2f(nt.u, nt.v)` (nt = normal-indexed table entry of n[j]).
- **0x1000, 0x80000, 0x100000**: colour(model+0x54); `glTexCoord2f(nt.u + uoff, nt.v + voff)`.
- **0x8000**: calls 0xc97c2d (texture object), 0x9f4218 (x87 return), writes alpha `[ebp+0x1c]`, and calls
  0xcfcd74 / 0x9fa1cb / 0xcfc8f2 / 0x95eda9 which write model+0x54 -> **original loop** (never seen in game).
- anything else (1, 0x40): no attributes.

Then the vertex (first match):
- flag **0x20**: `L = V - origin; L.x = ((L.x + 2000) * L.z) / (L.z - 4000) + L.x; L.z = 5; L += origin;
  glVertex3fv(L)` (constants 0x01a802d8, 0x01a9ff0c, 0x01a7e4cc). Implemented, never seen in game -> falls back
  unless hotpatch bit 8192.
- flag **0x400**: time-based wobble through client sin 0x9681bd -> **original loop**.
- flag **0x200000**: vertex skipped (attributes already sent) if `voff > z` for corners v[0], v[1], v[2]
  (comiss/jbe: NaN does not cull). Implemented, never seen -> falls back unless bit 8192.
- else `glVertex3fv(&V)` with V = vbase + i*0x2bf20 + v[j]*12 (pointer into the client's buffer).

All float work is single binary32 SSE ops in the original order (`-msse2 -mfpmath=sse -ffp-contract=off`).
Side effects besides GL calls: frame locals only (-0x74, -0x30, -0x2c, -0x8c, -0x4c, -0x78.. -0xb0, -0x88,
-0x68, -0x50, -0x144, -0xec..-0xf8); the post-glEnd code reads only -0x10, -0x20, -0x44, -0x12c, -0xfc.
Called helpers 0xcfc94a (self) and 0xcfc922 (index) are pure.

## Per-normal light precompute 0x012b968c..0x012b996c (bit 256)
For n < (int16)mesh[6], C = model+0x54: model[0xcb] == 1: `T[n][k] = S[n]*C[k] + 0.2f` (0x01a7df08), else
`T[n][k] = L[n]*C[k]`. Temporaries -0x28, -0x114, -0x120, -0xc0..-0xc8, -0xe4, -0x104, -0x108 are loop-local.
Native version writes the table and sets -0x28 = count, then jumps to the exit 0x012b9971.

## Patches (all verify original bytes before writing, revert on mask change)
Original bytes are not published: each site's address, length and SHA-256 are in `targets.json` (`meshdraw_sites`) and
the bytes are generated locally into the ignored `meshdraw-orig.h` (README). A site is patched only when its live bytes
equal that original, or already equal the replacement.

| site | original | replacement |
|---|---|---|
| 0x012ba899 | 7 bytes (`md_orig`): `nop; and [ebp-0x74],0; jmp 0x012ba8a7` | `jmp md_entry; nop; nop` -> md_hook(ebp): 1 = jump to glEnd call 0x012bb22e, 0 = `and [ebp-0x74],0; jmp 0x012ba8a7` |
| 0x012b968c | 6 bytes (`md_lorig`): `and [ebp-0x28],0; jmp 0x012b9699` | `jmp md_light_entry; nop` -> 1 = jump 0x012b9971, 0 = `and [ebp-0x28],0; jmp 0x012b9699` |
| 0x012b8d1d (bit 512 only) | 10 bytes (`md_prologue`): `push ebp; mov ebp,esp; push -1; push 0x1a1cef7` | `jmp md_time_wrap` (timer; trampoline runs the first 10 bytes) |

## Hotpatch mask bits (C:\mutools\mugl-hotpatch.txt; v7.1 default 7599)
1/2/4/8/16 as v7.0; 32 meshdraw native loop (calls through the import slots); 64 verify; 128 direct append into
mugl's batch (what mugl's glTexCoord2f/glColor3fv/glColor4f/glVertex3fv do inside a batched block; used only when
the import slots point at mugl and a batched block is open); 256 light precompute; 512 routine timer + segment
timing; 1024 frame pacing fix; 2048 zero-copy T2F_C4F_N3F_V3F batches; 4096 strided batch arrays (no pack);
8192 enable the unverified 0x20/0x200000 vertex paths.

Verify (64): with 128, our loop appends into a scratch Vtx array from a snapshot of mugl's current values, the
original loop runs, and at its glEnd (import slot swapped to a recorder) the scratch must equal
vb[block_start..vcount) byte for byte plus identical cur_t/cur_c/set flags. Without 128, the loop's 5 import
slots are pointed at recorders while the original runs, and the (op, float bits) streams are compared. The light
table is computed into a scratch copy at precompute time and compared with the real table at the next mesh-loop
hook of the same model/mesh.

## Reported results (2026-10-17, Claude's MuMatrix32 sessions; supplied, not rerun in the publication task)
Verification, 0 mismatches everywhere:
- call stream (64): 7.52M meshes / 3.99G corners (spawn + hunting spot, session 1), 2.03M meshes (hunting spot, session 5)
- direct append (64|128): 1.55M (session 2) + 1.13M (session 3, spawn) + 1.15M (session 5, spawn) + 3.78M
  (session 5, hunting spot) + 0.58M (v7.1 build, login/character select) meshes
- light precompute: 265k (session 3) + 270k + 1.46M (session 5) + 0.48M (v7.1) meshes, 0 unverified
- fbhash (glstride, all six batch formats): builtin GL == proxy at masks 0/15/2063/4111/6159
Coverage: modes seen 2 (~96%), 4 (~2.3%), 0x1000 (~1.1%), 0x40 (<0.1%); vertex path always plain; no fallbacks.
Mode 0x80000 was seen once (50 meshes); it shares the 0x1000 code path and was not directly verified. Mode 0x100000 (not in the reported coverage) and 0x8000,
flag 0x400, and the 0x20/0x200000 vertex paths were never observed (0x8000/0x400 fall back to the original loop; the others
only run with bit 8192).

Timers (spawn, ~1,840 mesh calls and ~0.98M corners per frame): original routine 16.8-17.4 ms/frame -> native
direct 10.7-11.5 ms (loop 4.0 ms with vector stores; the rest is mostly batch submits/draws triggered inside the
routine: pre 6.5 ms, post 0.25 ms). mugl pack 2.4 ms -> 2.0 (zero-copy) -> 1.2 (strided).

Same-session A/B (wkwin, work ms / fps):
- spawn 124,120: 15 -> 38.8 / 23.1; 943 (meshdraw direct+light) -> 34.3 / 19.6; 1967 (+pacing) -> 33.8 / 24.2;
  4015 (+zero-copy) -> 33.6 / 24.2; 8111 (+strided) -> 32.7 / 23.6
- hunting spot 116,101 (MU Helper, 4 interleaved rounds of 20 s): 15 -> 42.4 / 22.6; 431 -> 35.8 / 22.0;
  7599 -> 33.8 / 24.1

## Frame pacing finding (bit 1024)
The frame driver 0x01851d39 sleeps `40 - elapsed`, where elapsed is the previous frame's work (the slept time is
added to the saved tick). With alternating frame costs this loses time; lowering work made fps drop (19.6 fps at
34 ms work). The fix skips the driver's Sleep at 0x0185267a (return address 0x01852680) after a frame that
swapped in the in-game scene ([0x01d1df70] == 6), and mugl paces swaps on a 40 ms schedule. The logic
accumulator still tracks real time (the assumed sleep reappears in the next elapsed). GL streams unchanged.

## Attribution caveat
mugl is built without frame pointers, so EBPWALK attributes time spent in mugl code (including the old
immediate-mode emulation behind the loop's GL calls) to the calling main.exe function: the 44.8% "self" of
0x012b8d1d was mostly mugl. With the frame-pointer build the routine's own self time is ~3%.

## v7.2: precise waits (bit 1024), 2026-10-17
Published from Claude's local `mugl_v72.c` (hash in `source-provenance.json`); the reported results below are Claude's,
supplied, single-host, and were not rerun in the publication task (see `docs/research/mac-performance.md`, MAC-PERF-006).

The 17-22 fps with pacing on was not the client's inactive throttle and not double sleeping. The client's active flag
[0x01cf0fc0] stayed 1 (the inactive branch of the message loop at 0x0120ee34 has no Sleep), and the only render-thread
Sleep is the driver's (return 0x01852680), skipped on every eligible frame, with one logic step per frame. The cause
reported by diagnostic builds is that Wine's Sleep() waits on the client side with select(), and macOS coalesces those
timers whenever main.exe is not the frontmost Mac app (muinput `activate` only activates the window on the Windows
side, so macOS still treats the process as background). In the background Sleep(7..14) took 17-45 ms (170 ms requested
per 2 s became 635 ms). Frontmost, every wait was within 2 ms. A waitable timer, an alertable SleepEx and an event wait
with a timeout stayed under 1 ms late in the background (the wineserver times them). The same ~28 ms of work then gave:
- pacing off (mask 6575): background 19.3-21.1 fps; frontmost 25.0.
- v7.1 pacing (7599): background about 24.5 fps on average but about half the frames late, with 60-80 ms spikes (17-22 fps
  observed); frontmost 25.0.

v7.2 changes only the waiting (still bit 1024; no GL change, no new patch site):
- `pace_wait` waits on a waitable timer to the exact 40 ms deadline (relative 100 ns units, no millisecond rounding) and falls
  back to `Sleep` if the timer cannot be created or set.
- With bit 1024, any other render-thread `Sleep(ms > 0)` also goes through the precise timer (this fixes the driver's own
  cap on the login and character-select screens). `Sleep(0)` and other threads are untouched.
- New stats line: `pace: logic steps=.. waits=.. late=.. restarts=.. overshoot avg=.. | frame ms <30 30-38 38-42 42-50
  50-60 60-80 80+` (swap-to-swap histogram). The logic-step count reads the driver counter at 0x0bdc5eb0.

Result at spawn (about 28-29 ms work): v7.2 mask 7599 in the background held 25.00 fps over 140 s (69 periods, minimum 25.0;
3,468 of 3,482 frames at 38-42 ms; mean overshoot 0.08 ms); frontmost 24.95. The logic stays real-time: 50.4-50.5 steps per
about 2.01 s, which is 25 Hz. Not established: other hosts, macOS versions or power states; behavior on a Windows host (the
cause is specific to Wine on macOS); long-run stability beyond the reported run.
