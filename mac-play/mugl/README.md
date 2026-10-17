# mugl immediate-mode proxy

Authored MIT code for the original client's 32-bit CrossOver renderer. It buffers
legacy vertices in the 32-bit process, then submits arrays through Wine's OpenGL.
It reduces WoW64 calls; it does not replace Wine's renderer or the game.

```sh
brew install mingw-w64
make mugl
```

The result is `build/opengl32.dll`. `gen.py` reads the checked-in 361-name export
manifest and generates assembly stubs, pointer declarations and a DEF file into
`build/`. Generated sources and binaries are ignored. The manifest lists names
from CrossOver 26.3's i386 `opengl32.dll`, SHA-256
`0965d21be959f804d0dedaa4a52da952befbc9b73df573229c0074390823ec56`.
It contains API names, not extracted implementation code. All real exports must resolve
at load time. Ordinal-only imports and other runtime export sets are unverified.

`MINGW_CC` and `PYTHON` select the build tools. SSE flags are mandatory and remain
in the Makefile: `-O2 -msse2 -mfpmath=sse`. Default MinGW x87 arithmetic is extremely
slow under Rosetta. `make test` tests generation and compiles `triangles.c` with
host clang without needing Wine, Windows headers or a game installation. Linux CI
also cross-builds the proxy and diagnostics.

## Deployment and diagnostics

Run the parent setup script for a new bottle. It installs mugl by default beside
`main.exe` in the cloned game directory and sets only the `main.exe` AppDefaults
`opengl32=native,builtin` override. It verifies the Wine builtin marker at offset
64 in `C:\windows\system32\opengl32.dll`, leaves that file untouched and records
its hash. The proxy loads that absolute system32 path. Copying the proxy into
system32 would prevent it from finding the real implementation.

Rerun setup while the game/launcher are closed to refresh the proxy. The state
folder records `mugl.sha256`, `mugl-builtin.sha256`, `mugl.mode` and `mugl.log`.
Setup refuses symlink deployment paths, an unmanaged game DLL and a non-builtin
system DLL. It does not repair a foreign system DLL. Recreate the test bottle.
To remove the managed proxy and its AppDefaults value, rerun setup with:

```sh
MU_GL_BATCHING=0 ./mac-play/setup-crossover-32bit.sh --bottle MyMuBottle
```

Optional environment variables inside Wine:

- `MUGL_STATS=C:\MuMatrixTools\mugl.log` appends the real-module load path and
  two-second interval counters. `blocks`, `verts`, `draws` and `fallbacks` are
  interval totals; `fps` is frames divided by interval duration.
- `MUGL_MODE=nomerge` submits each block separately through arrays.
- `MUGL_MODE=off` disables buffering, but intercepted integer/double entry points
  still use float wrappers. Use CrossOver's `--dll opengl32=b` for a true builtin
  baseline. Its wrapper overwrites inherited `WINEDLLOVERRIDES`. The benchmark
  helper sets this override when `MU_GL_BATCHING=0`.

For launcher children, persist optional values with the bottle-scoped `cxwine`
adapter and `reg add HKCU\Environment`, then use `Play.command` for its idle reset.
Remove diagnostic values with `reg delete` when finished. Logs stay private.

The [performance finding](../../docs/research/mac-performance.md) describes
conversion order, synchronization, measured coverage and unsupported GL behavior.
The proxy assumes a single rendering thread and one current context at a time.
It is intended for the observed float32, fixed-function MU path, not arbitrary
OpenGL applications.
