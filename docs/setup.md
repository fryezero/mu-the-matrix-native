# Setup and reproduction

## Portable source checks

Use Python 3.9+, Clang/Clang++, and Crypto++. The native libraries build on macOS and Linux. Capstone supports bounded static code-map checks. The
Windows-only capture utility has a separate cross-build.

```sh
# macOS
brew install cryptopp
# Debian/Ubuntu alternative: sudo apt-get install libcrypto++-dev
python3 -m venv tools/python
./tools/python/bin/python -m pip install -r tools/requirements-portable.txt
make test PYTHON=./tools/python/bin/python
```

CI runs the same portable checks on macOS and Linux with Python 3.11. Unit tests
use authored geometry/image/decoder fixtures and public LEA vectors. Ten
private-input checks explicitly skip by default. A source-only checkout should
pass without downloading or shipping the original game.

For the full optional local analysis environment, install the pinned Python
dependencies in `tools/requirements-lock.txt`. REA requires a supported Node.js
runtime; Node 22.22.3 was used in the recorded investigation.

```sh
./tools/python/bin/python -m pip install -r tools/requirements-lock.txt
npm ci --ignore-scripts --prefix tools
./tools/node_modules/.bin/rea --version
```

REA is pinned to 6.5.0. Its repository checkout is optional and ignored. When
needed for source inspection, use commit
`93c620c3e7c401be40b71c480518147c76ade4dc` from `morluto/rea`.

## Private integration checks

Supply the exact `main.exe` locally at `input/main.exe`. Its SHA-256 must be
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Set `MU_GAME_ROOT` to your own matching installation directory. It is an
environment value, not a file to commit.

```sh
export MU_GAME_ROOT='/absolute/path/to/your/Mu The Matrix'
python3 scripts/loader_recover.py
# Also restore the local independent reference payload described below.
MU_RECOVERY_INTEGRATION=1 make test PYTHON=./tools/python/bin/python
```

The decoder integration check needs `evidence/loader-recovery/recovery.json` and
the original executable. Three model integration checks need the installed model
files. The v14 check pins three source digests and compares decoded digests
from the independent upstream oracle. The reference-comparison test also needs
`evidence/model-v15-sample.bin`: the original investigator's independently
decoded 01spa_skill payload, prefixed with the four-byte `BMD`/10 layout marker.
It is private derived evidence, not a tracked fixture. Acquire/reproduce it from
the pinned TypeScript oracle in `model-recovery/SOURCES.md`. Requested integration
checks fail when inputs are missing rather than silently reporting full success.

The client-memory integration checks also need Unicorn and the pinned restored
first section at `evidence/x86-capture-text-08/client-text.bin`, or an explicit
`MU_CLIENT_TEXT` path. It validates the full section digest before running the
393 copy and 768 clear instruction comparisons. See [client-memory setup](../reconstructed/client-memory/README.md).

The record-math private check also needs the verified scoped math-data capture09
manifest and three files. Set `MU_MATH_DATA` to that directory if needed. See
[record-math setup and FP limits](../reconstructed/record-math/README.md).

For complete corpus scans, use the reader CLIs, supply the installation root,
and write to a new directory outside the installation:

```sh
./tools/python/bin/python asset-recovery/recover_images.py --root "$MU_GAME_ROOT" --output asset-recovery/verified-local --validate-all
./tools/python/bin/python model-recovery/recover_models.py --root "$MU_GAME_ROOT" --output model-recovery/verified-local --validate-all
```

These commands retain manifests and return nonzero when inputs are rejected or
unsupported. Inspect those results; a nonzero full-scan result is not the same
as a failing portable unit test. Keep the generated outputs ignored.

## Native analysis with REA

The reference setup used Ghidra 12.1.4, a full OpenJDK 21, and GNU binutils 2.47.
Install/configure them separately from REA. Set `GHIDRA_INSTALL_DIR` and
`JAVA_HOME` for your system, then run the REA doctor for that provider.

`scripts/collect_evidence.py NEW_DIRECTORY` repeats the initial static inventory.
Its `--objdump` option accepts your GNU objdump path. `docs/code-recovery.md`
records raw mappings, seed addresses and the changed Ghidra analyzer profile.
Preserve these profiles and derived-byte hashes when comparing results.

## Bounded restored-code map

Supply the pinned first-section capture and follow [the map finding](research/client-window-map.md).
`map_client_window.py` limits window size and traversal budgets, labels heuristic
origins and unresolved references, and refuses unpinned input. Its synthetic tests
run in the portable suite with Capstone; no game data or Unicorn is needed.

## Windows helper

With MinGW-w64 installed:

```sh
make windows
```

See `windows-capture/README.md`. The output executable is generated and ignored.
Native Windows validation remains open; the existing Wine smoke result only
covers the helper's own memory read and hash implementation.

## Before publishing

```sh
git add README.md AGENTS.md CONTRIBUTING.md LICENSE LICENSE-analysis THIRD_PARTY_NOTICES.md Makefile .gitignore .gitattributes docs scripts tests asset-recovery model-recovery reconstructed windows-capture tools .github companion-findings.md
git diff --cached --stat
python3 scripts/audit_repository.py
```

The ignore rules exclude original inputs, raw ledgers, downloaded tool trees,
exports, memory captures, builds and local environments. The staged-tree audit
adds a format/path/content check. Review the actual staged diff as well.

## Client-linked model decoder comparison

The default suite adds seven authored model-codec tests and skips its private
check unless integration is requested. That check requires the full pinned
restored text at `evidence/x86-text-capture-09/client-text.bin`, or
`MU_CLIENT_TEXT`, plus `MU_GAME_ROOT` and the exact ignored
`model-recovery/verified-v14/manifest.json`. It compares all 180 pinned v12
payloads against captured x86, authored C and the Python reader. A requested
integration run errors if evidence is absent or any input hash differs.
The module README documents synthetic-only comparison without installed assets.

## Hierarchy instruction checks

The ninth private check validates selected hierarchy instructions against pinned
text and second-image-data captures. Set `MU_CLIENT_IMAGE_DATA` when the data
file is outside `evidence/image-data-run10/data-capture-10/`; `MU_CLIENT_TEXT`
also applies. The v2 report labels raw call/PUSH matches as heuristic candidates.
A passing report does not establish all caller boundaries, argument provenance,
prior output-buffer values or actual rendering. Strict model rejection remains.

## Client-linked LEA setup

Five additional portable tests cover the recovered LEA context setup. The tenth
private check requires the same full pinned restored text and Unicorn, without
installed model assets. Use `MU_CLIENT_TEXT` to override its default capture09
path. The [finding](research/client-lea-key.md) includes the standalone command
and excludes key/context aliasing and payload decoding from the contract.
