# First-run GFx conversion in C, DATA-ACQ-003

Verified on macOS arm64, 2026-10-27. This replaces an authored preprocessing tool,
not a recovered client routine. The oracle is `native/gfx/gfxconvert.py`; no new
original-instruction or Unicorn claim is made.

## Implementation

`make -C native/gfx converter` builds `native/build/gfxconvert/gfxconvert`.
The C sources beside `gfxconvert.py` implement the movie/tag reader, DDS DXT1/3/5
and 24/32-bit RGB(A) top mip decoder, atlas crop/resampling, SWF lossless bitmap
encoding, font imports, Latin font subsets, compacted-font replacement and the
AVM1 host bridge. The existing `model-recovery/modulus.cpp` envelope reader is
linked as an object. Runtime dependencies are Crypto++ and system zlib.

The resize arithmetic follows the Python oracle: premultiply RGBA with rounded
8-bit multiplication, separable bilinear weights rounded to 22 fractional bits,
unpremultiply, then floor-premultiply into SWF ARGB. Atlas coordinates use Python's
ties-to-even rounding. Reference for the resampling behavior is Pillow 11.3.0's
[Resample.c](https://github.com/python-pillow/Pillow/blob/11.3.0/src/libImaging/Resample.c).
The C implementation is authored here; Pillow remains a test dependency.

The CLI accepts the app's existing options and selected `--movie` conversions.
Its JSON report records bytes and numeric image, sub-image, atlas, missing-file
and unconverted-tag counts, or an error. It is a compact diagnostic report, not a
schema-identical copy of Python's detailed report. Unsupported DDS modes fail
explicitly. Input buffers are checked before reads, individual buffers are limited
to 256 MiB, and images to 16,384 per side and 16,777,216 pixels. Per-movie scratch
allocations are reclaimed after success or failure.

`native/app` now bundles and ad-hoc signs `Contents/MacOS/gfxconvert`, and bundles
its dylibs through the existing dependency collector. No Python sources or
interpreter go into the app. The launcher invokes that binary directly and ignores
old `python` settings. A complete successful conversion is installed only after
both base/main movies exist; failed conversion leaves the previous set intact.
Existing scratch-movie fallback is retained.

## Evidence

The configured game root was read from the installed Native Data setup record.
Both it and `~/Library/Application Support/MuTheMatrixNative/Native Data` were
read-only inputs. Outputs, hashes and logs are external local scratch artifacts:
`~/Documents/MTM/mu-mac-tools/native/scratch/data-acq-003/`.
No client payloads, converted assets, font data or per-file hash lists are committed.

`gfxconvert_compare.py` reruns both tools over the full installed set with default
options and again with the app's options:

- Each mode: 179/179 movies and 82/82 NaviMap files, 261/261 SHA-256 hashes equal.
- Each mode: 9,166/9,166 embedded DefineBitsLossless2 assets hash-equal, covering
  1,416 direct images and 7,750 atlas sub-images. There are 159 atlas definitions.
- Zero missing, extra or differing generated files/assets in either mode.
- Existing Native Data: 260/261 file hashes equal to the fresh Python and C runs.
  `winQuestSummary.swf` differs from both fresh runs. Its provenance was not
  investigated; the installed copy was left untouched. This is not a converter
  mismatch. `corpus/summary.json` records that boundary.

The signed bundle's `--setup` ran under `env -i`, a new temporary HOME and
CFFIXED_USER_HOME, and `PATH=/nonexistent`. MU_NATIVE_SUPPORT_DIR and log/scratch
paths also pointed to external scratch. The reader inputs were read-only symlinks
to the existing Native Data's lang, object and sound directories, with no converted
movie fallback available. Result: 179 movies converted, all 261 generated file
hashes equal to the oracle, 31 text files, 33 object files and one sound table copied.
The log and setup record are under `clean-user/`.

Portable tests in `test_gfxconvert_c.py`: 11 tests, including 16 randomized DDS
format/resize cases, scaled/padded atlas crops, four container signatures, font
subset/layout/kerning, compacted fonts, bridge variable types and repeated keys,
long unresolved imports, NaviMaps, truncation, bad font offsets and invalid paths.
The same tests pass under AddressSanitizer and UndefinedBehaviorSanitizer.
`gfxconvert_mutations.py` catches 3/3 planted mistakes: wrong premultiplication,
wrong font subset range and wrong bridge callback name.

`test_native_app.py`: 12 tests, 11 pass and one private installed-game smoke skips.
Checks include bundle layout/signing/self-containment, no Python files, synthetic
first run with no Python/Pillow on PATH, retained legacy settings compatibility,
repeat/forced conversion, preservation on conversion failure, the existing launch
plan and synthetic offline smoke. The local macOS gate result is recorded in the
milestone handoff.

## Repeat

```sh
make -C native/gfx converter
tools/python/bin/python -m unittest discover -s native/tests -p test_gfxconvert_c.py -v
tools/python/bin/python native/gfx/gfxconvert_compare.py \
  --root "$MU_GAME_ROOT" --native-data "$MU_NATIVE_DATA" --scratch "$NEW_EXTERNAL_SCRATCH"
tools/python/bin/python native/gfx/gfxconvert_mutations.py --scratch "$NEW_MUTATION_SCRATCH"
bash scripts/local-macos-ci.sh tools/python/bin/python
```

The compare and mutation scripts require a new scratch directory and reject paths
inside the repository. All Python usage above belongs to development verification.

## Limits

A real second macOS account was unavailable. A temporary HOME and empty tool PATH
exercise setup and runtime dependencies, but do not reproduce that user's login,
Finder Documents consent, Keychain, or filesystem permissions. No original game
or launcher was started, stopped or driven. No live service, network, protection,
account, wire or acquisition work was performed. Guided acquisition of data for
other users remains DATA-ACQ-002. Signing/notarization and cross-machine deployment
remain deferred APP-DIST-001 work; the existing locally signed bundle is retained.
