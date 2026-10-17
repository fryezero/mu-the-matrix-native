# Claude v7.0 CPU hotpatch publication

This is an opt-in snapshot of Claude's existing local v7.0 work. The normal
`make mugl` and setup installer still use PR #52's reviewed `../mugl` proxy.
No target is installed, no bottle is changed and no process is started by these
build commands. The later `meshdraw.c` experiment is outside this snapshot.

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
from wglSwapBuffers after 100 frames. Missing configuration defaults to mask 15.
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

Mask 0 restores these patches, 7 omits skinning, 15 enables all replacements,
and 31 enables verification too. The source's verify path bypasses comparison
when its first stack argument is zero. Reported calls and checked calls are
different counters. Checked output ranges are vertices, normals, light values,
scratch scalars and bounds. Allocator failures and arbitrary state are unverified.

`C:\mutools\mugl-mode.txt` supports `full`, `nomerge`, `nofilter`, `off`,
`nodraw`, the `+vbo` switch and `+time` GL timing. `full+vbo+time` is valid.
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
v7.0 files do not contain an identifiable cap patch installer. We publish that
measurement condition, not an invented implementation. The independently merged
[frame-loop finding](https://github.com/fryezero/mu-the-matrix-recovery/blob/2e8d89e578204c80b6bcf6ce295193ad959bf2ea/docs/research/client-frame-loop.md) records the cap
locations on main, after PR #52 is integrated.

See [the performance finding](../../docs/research/mac-performance.md) for source
identities, reported measurements, failures and the next mesh-draw question.
