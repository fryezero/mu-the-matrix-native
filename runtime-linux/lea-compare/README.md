# Original AVX helper comparison

This optional 32-bit Windows console tool runs the four selected captured LEA
bodies under the isolated x86 Linux/Wine guest. It compares them with authored
portable C. It contains no captured instructions and does not launch or attach
to the game. It only reads a supplied private restored-text file.

Build with `make -C runtime-linux/lea-compare` and MinGW's
`i686-w64-mingw32-gcc`. Linux CI cross-builds it; normal portable tests do not
require MinGW or a guest. Copy the generated executable into the already
configured guest described in [runtime setup](../README.md). Verify outbound
networking is blocked before running. Inside the guest:

```sh
env WINEPREFIX="$HOME/wineprefix" WINEDEBUG=-all \
  timeout 120 wine /path/to/lea-compare.exe 'Z:\path\to\client-text.bin'
```

The tool refuses anything except the exact text length and SHA-256. A host-side
static check must also pass before treating relocation as established:

```sh
./tools/python/bin/python scripts/validate_client_lea_decode.py \
  --text /path/to/client-text.bin --output /new/local/scalar-report.json
```

The original addresses conflict with the standalone runner's Wine allocations.
The tool copies only the four selected bodies into a shared relocated window.
They use relative calls/branches and no absolute or segmented memory operands.
The host check pins each body and verifies branch boundaries/internal calls.
Pages outside those bodies stay inaccessible; executable pages contain the
selected bodies and zero padding. No algorithm substitutions are used.

Synthetic cases exercise all supported key sizes, context/data word alignments,
overlap and batch boundaries. An assembly bridge checks saved integer registers,
DF and stack cleanup, then restores the runner's own state. A deliberately bad
authored callee must fail that bridge check. The arena has inaccessible guard
pages, context is read-only and the entire arena is compared after each call.
A deliberately scalar batch replacement must differ from original output.

A successful JSON report requires zero output/ABI failures and a nonzero wrong
batch count. Crashes, timeouts, bad input or missing AVX support fail the run.
The report does not provide instruction coverage or an inside-arena read trace.
It does not establish native Windows behavior, game invocation or complete
loader behavior. No installed model bytes are used by this guest test. See
[the finding](../../docs/research/client-lea-decode.md) for recorded results,
identities and separate installed-payload coverage. Keep all private inputs,
compiled executables and machine logs outside Git.
