# Claude v7.5 CPU hotpatch publication

This is an opt-in snapshot of Claude's existing local v7.2 work: the v7.0 helper,
inline, peephole and skinning patches plus the native mesh-draw loop in
`meshdraw.c` (MAC-PERF-005, see `meshdraw-notes.md`), frame pacing with precise
waits (v7.2, MAC-PERF-006), the zero-copy/strided batch arrays, v7.3 (MAC-PERF-007): terrain face
sorting (`terrain.c`), a raised render-thread priority and long-frame diagnostics (`stall.c`), and v7.4
(MAC-PERF-008): effect-sprite and grass quad batching (`quads.c`), deferred client-array enables, off-screen batch
culling (`cull.c`) and draw/GPU diagnostics (`gpudiag.c`), and v7.5 (MAC-PERF-009): native body shadows
(`shadow.c`), native terrain decals (`decal.c`) and a specialised mesh-draw append. The normal `make mugl` and setup installer still
use PR #52's reviewed `../mugl` proxy. No target is installed, no bottle is
changed and no process is started by these build commands.

## Build without private client inputs

```sh
make mac-hotpatch
```

MinGW cross-builds the proxy, display-mode launcher proxy, mesh/call benchmarks
and muinput. `build/synthetic/opengl32.dll` has empty tables and disables all
main.exe hotpatch and Sleep-IAT installation. It is a compilation check, not the
measured v7.0 game build. CI never downloads a game, runs Wine, or uploads DLLs.
The shared EnumDisplaySettings hook remains present. Do not deploy the CI DLL.

## Generate the measured tables locally

Supply your own pristine runtime dump. The generator derives the offline
linear-sweep call and instruction listings with MinGW binutils objdump 2.47.
The dump maps file offset zero to VA `0x00400000`, is
46,137,344 bytes and has SHA-256
`6e7957c9af8685f5a5fb14008131eab50470d40d2e6128397d5795a88160bfd4`.
It is unpacked process memory, not the protected on-disk main.exe. The pinned
listing digests and original helper digests are in `targets.json`.

```sh
python3 mac-play/hotpatch/generate.py \
  --dump /private/pristine.bin \
  --out mac-play/hotpatch/build/private
make -C mac-play/hotpatch private
```

The v7.1 mesh-draw code needs the original bytes of three small patch sites
(`0x012ba899`, `0x012b968c` and the routine entry `0x012b8d1d`, 7/6/10 bytes). Like
the xform prologue they are not in source: `targets.json` (`meshdraw_sites`) pins
address, length and SHA-256, `generate.py` checks the dump against those digests and writes
`meshdraw-orig.h` under the ignored build directory, and `meshdraw.c` refuses to
patch any site whose live bytes are neither those originals nor its replacement.
The compile-only build gets a zero-filled header and never installs a patch.

Generation refuses different inputs. It compares every generated original-body
span to the recorded digest, assembles the authored `hp.S` replacements, and
requires the final 18,583/50,977 site tables to match Claude v7.0's canonical
record digests exactly. Original byte patterns in the inliner are represented by
length and SHA-256. The generated headers, `orig.h`, saved prologue, binaries and
generation report remain under ignored `build/`. Never upload these headers,
private listings or resulting DLLs as source/CI artifacts. No `make install`
target is provided. An independent dump generally has different runtime data;
this exact-capture recipe deliberately refuses it rather than expanding coverage.

`calls.txt` is one `call-site-hex target-hex` pair per line. `ptext.dis` is the
AT&T instruction-only output of a linear i386 objdump sweep over
`0x00401000..0x01a7c000`, one `address:<TAB>mnemonic operands` line per instruction.
Optional `--calls` and `--disassembly` accept Claude's cached listings instead.
The regenerated call list has one additional direct-call candidate that matches
no inline template; its separate digest is pinned, and the final table is identical.
The private originals used here are documented in the performance finding.
The exact listing identity is required because the sweep can interpret data as
instructions. It does not prove that every candidate is reachable code.

The generator excludes the helper bodies from inline sites. Claude had already
patched those helpers when scanning. It excludes the replaced skinning body
`0x012b5bde..0x012b678d` from peephole sites. This reproduces the final headers,
rather than intermediate `sites.json`/`peep_sites.json` counts. The local peep
slice is the fixed `mem[a-base:end-base]` version. The flags-dead scan is Claude's
existing heuristic, including calls/returns as kills. It is not whole-program
liveness proof. General flags equivalence remains unverified.

All float builds require `-O2 -msse2 -mfpmath=sse -ffp-contract=off`. The
private harness compiles but is not executed by make. Its existing final
register/memory checks do not establish complete EFLAGS or access-trace
identity. Crash testing belongs only in a disposable bottle with AeDebug
disabled first. A prior crashing probe spawned winedbg and killed a live game
thread. Never use MuMatrix32 for these tests.

## Runtime controls from the original snapshot

The private build checks `C:\mutools\mugl-hotpatch.txt` about once per second
from wglSwapBuffers after 100 frames. Missing configuration defaults to mask 44916143 (v7.5; v7.4 used 875951, v7.3 23983,
v7.1 and v7.2 7599, v7.0 15). The file is read as a 26-bit mask; v7.4 reads 21 bits, v7.3 16 bits and v7.1/v7.2 14 bits
of the same value, so 44916143 gives each older build its own default. Only in `main.exe` are the code patches (bits
1-512, 8192, 2097152-33554432) and the
frame pacing (1024) applied; any other process that loads the private build (a test program) gets the GL-level bits only.
Each site is checked against its original or replacement bytes before a write;
unexpected bytes are skipped. This is process-local patching with instruction
cache flushes. It does not write the on-disk executable. Changing a mask is not
an all-or-nothing transaction, and other game threads are not suspended.

| Bit | Effect |
|---|---|
| 1 | Handwritten hot helper bodies |
| 2 | Trivial inline call sites |
| 4 | Constant idiom peepholes |
| 8 | Skinning C replacement via entry jump and original trampoline |
| 16 | Compare skinning outputs against original, when bit 8 is also set |
| 32 | Native replacement of the mesh-draw per-corner loop (`0x012ba899`), calling GL through the client's import slots |
| 64 | Verify the mesh-draw loop and, with 256, the light table against the original (diagnostic) |
| 128 | With 32/64: append directly into mugl's open batch instead of calling its entry points, when the import slots point at mugl |
| 256 | With 32/64: native port of the per-normal light table precompute (`0x012b968c`) |
| 512 | Time the whole mesh routine and its pre/loop/post segments (diagnostic, off by default) |
| 1024 | Frame pacing fix: skip the frame driver's own Sleep after in-world frames and pace swaps to 40 ms; v7.2 waits on a waitable timer, and routes other render-thread `Sleep(ms>0)` through it |
| 2048 | Draw T2F_C4F_N3F_V3F batches straight from the vertex buffer (zero-copy) |
| 4096 | All batch formats read the vertex buffer in place with stride 48 (no packing) |
| 8192 | Also run the mesh-draw vertex paths for flags `0x20` and `0x200000` (never seen in game, unverified; off by default) |
| 16384 | Terrain face sorting: record a run of terrain tile faces and draw opaque faces, then alpha faces, grouped by texture (`terrain.c`) |
| 32768 | With 16384: on every 8th sorted run, draw the run in both orders into an offscreen framebuffer and count differing pixels (diagnostic) |
| 65536 | Effect-sprite and grass quad batching: record a run of those quads and draw faces with identical state together, moving a face only past faces it commutes with (`quads.c`) |
| 131072 | With 65536: on every 16th run, draw the run in both orders offscreen, from a copy of the window, and count differing pixels (diagnostic) |
| 262144 | Deferred client-array enables: send glEnable/DisableClientState of the six fixed arrays only before something can observe them |
| 524288 | Off-screen batch culling: do not submit a batch whose vertices all lie outside one clip plane (x, y or w) (`cull.c`) |
| 1048576 | With 524288: rasterize every 16th culled batch inside a samples-passed query with all tests off and count non-zero results (diagnostic) |
| 2097152 | Native body shadows: the per-triangle loop of the shadow routine `0x012bc07a`, including the terrain height lookup per corner (`shadow.c`); with 128 the vertices go straight into mugl's open batch |
| 4194304 | With 2097152: verify every shadow mesh against the original loop (vertex stream or, with 128, the appended vertices) (diagnostic) |
| 8388608 | Native terrain decals: the ground-effect routine `0x016cdd5f` and its per-tile fan `0x016d197d` (`decal.c`); with 128 the fans go straight into mugl |
| 16777216 | With 8388608: run every decal natively record-only, then the original with recorders, and compare the GL call streams and the client globals it writes (diagnostic) |
| 33554432 | With 128: the mesh-draw direct append specialised per attribute kind (`md_run_vtx` in `meshdraw.c`); bit 64 verifies it |

Mask 0 restores these patches, 7 omits skinning, 15 enables all v7.0 replacements,
and 31 enables skinning verification too. The v7.1 default 7599 is 15 plus 32, 128,
256, 1024, 2048 and 4096. 6575 is the same without the pacing fix. The v7.3 default 23983 is
7599 plus 16384; 56751 adds the terrain verification. The v7.4 default 875951 is 23983 plus 65536, 262144 and
524288; 2056111 adds all three verifications (32768, 131072, 1048576). The v7.5 default 44916143 is 875951 plus
2097152, 8388608 and 33554432; 65887727 adds the mesh-draw, shadow and decal verifications (64, 4194304, 16777216). Mesh-draw
modes `0x8000` and flag `0x400` call client code with side effects and always run
the original loop. `meshdraw-notes.md` has the decoded routine and verification
method. The source's verify path bypasses comparison
when its first stack argument is zero. Reported calls and checked calls are
different counters. Checked output ranges are vertices, normals, light values,
scratch scalars and bounds. Allocator failures and arbitrary state are unverified.

`C:\mutools\mugl-mode.txt` supports `full`, `nomerge`, `nofilter`, `off`,
`nodraw`, and `+` tokens in any order: `+vbo` (VBO emulation), `+time` (GL timing, with v7.4 per draw class),
`+finish`, `+samples` and `+cull` (v7.4 diagnostics, below). `full+vbo+time` is valid.
QPC measures selected downstream GL calls. `MUGL_STATS` enables a private log;
`work=` is wall interval time minus render-thread Sleep time per frame,
and includes other waits/host scheduling. It is not pure sampled CPU time.

`../mumodes/modehook.c` uses `C:\mutools\mu-modes.txt` for an exact curated
32-bpp/60-Hz enumeration, shared with the mscoree launcher proxy. The older
`mugl-modes.txt` extra-mode implementation remains unused in this snapshot.
No launcher-proxy installation is performed. Loader-lock behavior, general
OpenGL state equivalence, mode-hook compatibility and Windows-native behavior
have not been revalidated for this published build.

The original live experiment also used a 25 FPS / 40 ms frame cap. The pinned
v7.0 files do not contain an identifiable cap patch installer, and neither does
v7.1. Bit 1024 is different: it skips the frame driver's `Sleep` at `0x0185267a`
(identified by its return address) after a frame that swapped in-world (scene
state at `0x01d1df70` equal to 6) and has mugl pace the swaps to a 40 ms schedule
instead. The driver sleeps 40 ms minus the *previous* frame's work, so lowering the
work of alternating frames lowered the frame rate; the report says GL output is
unchanged and the logic accumulator still tracks real time. Login and character
screens keep the driver's sleep. v7.2 makes the waits precise: Wine's `Sleep` is
stretched by macOS timer coalescing while the game is not the frontmost Mac app
(`Sleep(7..14)` reported at 17-45 ms), so the 40 ms schedule and, with the bit
set, every other render-thread `Sleep(ms>0)` wait on a waitable timer instead
(falling back to `Sleep` if none can be created); `Sleep(0)` and other threads are
untouched. The stats line `pace:` prints logic steps, late frames, overshoot and
a swap-interval histogram. This is a reported behavior (`meshdraw-notes.md`, v7.2); the merged
[frame-loop finding](https://github.com/fryezero/mu-the-matrix-recovery/blob/2e8d89e578204c80b6bcf6ce295193ad959bf2ea/docs/research/client-frame-loop.md) records the
driver and cap locations.

`../diagnostics/glstride.c` renders 150 frames using all six batch formats and prints a
framebuffer hash of the last frame. mugl applies the mask after frame 100, so
comparing the builtin OpenGL (`WINEDLLOVERRIDES=opengl32=b`) with the proxy at
different masks checks the batch-submission paths. It is a cross-build only here.

See [the performance finding](../../docs/research/mac-performance.md) for source
identities, reported measurements, failures and the remaining profile.

## v7.3 additions (MAC-PERF-007)

**Terrain face sorting (bit 16384).** The tile loop draws each visible tile as a 4-vertex fan: the layer-1 face
(return address `0x016cfab3`; blending off, culling on, alpha test off), then for tiles with layer-2 alpha the
alpha face (`0x016cfb53`; blending on, culling off, alpha test on). State and texture flip for every alpha tile,
so mugl drew one batch per face: about 1,300 draws per frame in the default view and 3,500 with the zoomed-out F6
camera. `terrain.c` records a run of these faces, with their state calls made virtual, until any other GL call.
When every opaque face shares one blend-off state class and every alpha face one blend-on class, and each alpha
face directly follows its own opaque face with identical corner positions, the run is drawn as opaque faces
grouped by texture in first-use order, then alpha faces likewise. An alpha face that is back-facing or edge-on
(sign of the clip-space determinant) and its opaque face stay in their original place between sorted sub-runs.
Any other run is drawn in the original order. Afterwards the real GL state equals what the original stream
leaves. Argument and limit: an alpha face covers exactly its own opaque face's pixels at equal depth, the depth
test is LEQUAL and both write depth, so with depth-distinct surfaces every pixel ends as (alpha over opaque) of
its nearest tile in either order. Depth ties between different tiles are not excluded analytically. Bit 32768
checks them: it draws the run in both orders into an offscreen framebuffer with the window's depth size, from
the same cleared start, and compares color and depth of every pixel.

**Render-thread priority.** The render thread runs at `THREAD_PRIORITY_HIGHEST`; the wineserver maps this
to Mach precedence on macOS. `C:\mutools\mugl-prio.txt` overrides it (-2..2, 0 = normal; polled every 2 s).
This is not a hotpatch bit and changes no GL output.

**Diagnostics.** With `MUGL_STATS`, every presented frame of 100 ms or more is logged at once as `stall: unix_ms=..
frame=.. ms=.. scene=..`, and each stats interval gets an `io: max_frame=..` line. `C:\mutools\mugl-stall.txt` (opt-in)
also points the client's CreateFileA/W, ReadFile, glTexImage2D, glTexSubImage2D and glGenTextures import slots at
counting wrappers, so stall lines show file opens, reads and texture uploads with the first file names.
`C:\mutools\mugl-shm.txt` receives the address of the presented-frame counter for `../machprof/stallprof`.
Writing a frame count (1-20) to `C:\mutools\mugl-trace.txt` records the GL call stream of the next frames to
`C:\mutools\mugl-trace-<frame>.txt` (glBegin callers, state calls, filtered calls, batch draws); the file format is
in `stall.c`. The `tsort:` stats line counts runs, sorted runs, faces, draws, in-place pairs, fallbacks and
verification results.

## v7.4 additions (MAC-PERF-008)

**Quad batching (bit 65536, `quads.c`).** Zoomed out the client draws about 780 effect sprite quads per frame from
return address `0x0184c914` and about 830 grass quads from `0x016d16bf`, each a 4-vertex `glBegin(GL_QUADS)` block,
changing only the texture and (sprites) the blend function between them: a darkening quad (ZERO,
ONE_MINUS_SRC_COLOR) and an additive one (ONE, ONE) alternate. Such a run is recorded with the terrain machinery
(the same virtual state) and drawn as batches of faces with identical state. A face joins the latest batch with its
state only if it commutes with every later batch: their window-space boxes are disjoint (2 pixels of margin; each
triangle clipped to the near plane, the face unbounded when depth clamping is on or a clipped vertex has w <= 1e-5),
or the face lies entirely outside one clip plane (draws nothing), or both are additive without depth writes (blend
ONE, ONE with FUNC_ADD for color and alpha, logic op off, depth mask off). Order inside a batch is kept. Every
inverted pair of faces has been checked, so the drawn sequence is reachable from the original by swapping
commuting neighbours. Additive commutation relies on exact clamped addition in the 8-bit framebuffer; bit 131072
checks it with the terrain sort's offscreen comparison, starting from a blit of the window's color and depth. Only
smooth-shaded quads are taken (flat shading would change the provoking vertex). The `qsort:` stats line counts
runs, faces, state groups (the draws without the bit), draws, unbounded, off-screen and additive faces.

**Deferred client-array enables (bit 262144).** The effect code draws each sprite from its vertex buffer as
`glEnableClientState` x3, `glDrawArrays`, `glDisableClientState` x3, about 2,800 calls per frame zoomed out. With
the bit, enables of the vertex, normal, color, index, texture-coordinate and edge-flag arrays are recorded and sent
only before something can observe them: generated stubs with the "release" flag (draws, glArrayElement,
interleaved arrays, client attribute push/pop, glGet*, glIsEnabled, wgl*), array-related extensions, display
lists, glBegin, glDrawElements/glDrawRangeElements, client-state queries and full synchronization. A disable
followed by an enable before the next such call cancels out. After a client attribute pop, glInterleavedArrays or
a client texture unit change the state is unknown and the next call passes through.

**Off-screen culling (bit 524288, `cull.c`).** Zoomed out about a third of the mesh batches (575 of 1,704, 377k of
1.17M vertices) are entirely outside the view. mugl does not submit a triangle batch whose bounding box has all 8
corners outside one of x = w, x = -w, y = w, y = -w or w = 0 (relative margin 1e-5 in double precision; batches with
a NaN position are left to GL); such a batch produces no fragment. The first vertex is tested first, so a visible
batch costs one transform. The matrices are re-read only after a change: matrix calls are wrapped (translate,
rotate, scale, multiply, load, ortho, frustum, load identity, pop, display lists) and advance an epoch after the
real call, as does each frame; matrix extensions turn the cache off. Culling pauses outside `GL_RENDER`. Bit 1048576
rasterizes every 16th culled batch with color and depth writes and the depth, alpha, stencil, scissor and
face-culling tests off inside a `GL_SAMPLES_PASSED` query; the count must be 0. That check found the first version's
bug (the epoch advanced before the real matrix call, so a batch flushed inside that call re-cached the old matrix).

**Draw/GPU diagnostics (`gpudiag.c`, mode-file tokens).** `+time` adds a `draw classes:` line (terrain, mesh,
sprite, grass, other glBegin, the client's own array draws: ms, draws and vertices per frame). `+finish` times a
glFinish before the swap (GPU work still queued at the end of the frame). `+samples` wraps each class run in a
`GL_SAMPLES_PASSED` query (fragments passing the depth test per class). `+cull` estimates the culling potential per
class (exact per-vertex test and the box test; slow). The client's `glDrawArrays` is now a custom export with the
generated stub's synchronization.

**Tests.** `../diagnostics/glcstate.c` is a framebuffer-hash test for bits 262144 and 524288 (effect pattern,
observers of array state, perspective batches in and out of view under every kind of matrix call); the private
build in a test bottle must print the builtin OpenGL's hash. A stale-matrix build failed it. `../diagnostics/glvbench.c`
measures submission cost by vertex layout and transport (client arrays were fastest; VBO streaming with
glBufferSubData per draw was about 50 times slower).

## v7.5 additions (MAC-PERF-009)

Profiled in the MTM-1 boss fight at Tormenta Island (many players and effects, MU Helper on) with `../machprof`
(`stackprof` EBP walks; `MOD=` and a `-fno-omit-frame-pointer` build attribute mugl's own time; `incl.py` groups the
samples by function). The body-shadow routine and the terrain height lookup it calls per corner were about 21% of the
main thread's x86 samples, the terrain-decal routine and its tile fan about 14%, and after those the native mesh-draw
loop (`md_run`, 16.7%).

**Native body shadows (bit 2097152, `shadow.c`).** The shadow routine `0x012bc07a` projects each mesh's transformed
vertices onto the ground: per corner a planar projection away from the model origin, then the client's terrain height
lookup `0x016cc9e2` (bilinear over the height map, or a fixed height in world 0x91), then `glVertex3fv`. The 7 bytes
after its `glBegin(GL_TRIANGLES)` (return address `0x012bc181`, so mugl sees the same caller) jump to `sh_entry`,
which emits the mesh's vertices natively and resumes at the `glEnd` call `0x012bc58c`. The height lookup is ported in
the client's operation order (its x87 float return is exact); the world and scene tests are read once per mesh. With
bit 128 the vertices are appended straight into mugl's open batch (what `mugl_glVertex3fv` does). Bit 4194304 runs the
original loop for every mesh with the `glVertex3fv`/`glEnd` slots on recorders and compares the vertex streams (or,
direct, the appended vertices) bit for bit.

**Native terrain decals (bit 8388608, `decal.c`).** Ground effects are drawn by `0x016cdd5f` as one
`GL_TRIANGLE_FAN` per visible terrain tile under the effect (about 30,000 fans per frame in the boss fight), each
through the tile routine `0x016d197d`. The routine entry (pinned `td_prologue`) jumps to `td_wrap`, a C port of both
in the client's operation order: colour call, the client's own AngleMatrix (`0x00cff32a`) and texture bind
(`0x0184acf6`), the tile visibility test (`0x016d2050`), texture coordinates rotated by the client's VectorRotate
(`0x00d000ad`), corner heights, and the client globals the tile routine writes (`0x0b6b4eac`, `0x0b6b52e8..f0`,
`0x0b6b5318`). With bit 128 the fans go to `mugl_glBegin`, a direct append and `mugl_glEnd`. Bit 16777216 runs each
decal natively record-only (no bind), then the original through a trampoline with the colour/begin/texcoord/vertex/end
slots on recorders, and compares the call streams and the globals.

**Specialised mesh-draw append (bit 33554432).** `md_run_vtx` is `md_run`'s direct append split per attribute kind,
with the constant colour/normal parts hoisted, so the corner loop has no per-corner mode or output tests. The 0x20 and
0x200000 vertex paths still use `md_run`. Bit 64 verifies it (the verify path calls the same function).

**forget_state without a 512 KB memset.** Every `glPopAttrib` cleared the whole 8 x 64K enable cache (about 3% of
the samples). Entries now record when they leave 0 (in `mugl_glEnable/Disable`; `terrain.c` writes three fixed
unit-0 caps, which are cleared explicitly), and only those are cleared; overflow of the 2,048-entry list falls back
to the memset. Same cache contents, no mask bit.
