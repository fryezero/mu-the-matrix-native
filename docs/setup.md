# Setup and reproduction

## Portable source checks

Use Python 3.9+ and Clang. The native libraries build on macOS and Linux. The
Windows-only capture utility has a separate cross-build.

```sh
python3 -m venv tools/python
./tools/python/bin/python -m pip install -r asset-recovery/requirements.txt
make test PYTHON=./tools/python/bin/python
```

CI runs the same portable checks on macOS and Linux with Python 3.11. Unit tests
use authored geometry/image/decoder fixtures and public LEA vectors. Three
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
the original executable. Two model integration checks need the installed model
files. The reference-comparison test also needs
`evidence/model-v15-sample.bin`: the original investigator's independently
decoded 01spa_skill payload, prefixed with the four-byte `BMD`/10 layout marker.
It is private derived evidence, not a tracked fixture. Acquire/reproduce it from
the pinned TypeScript oracle in `model-recovery/SOURCES.md`. Requested integration
checks fail when inputs are missing rather than silently reporting full success.

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
