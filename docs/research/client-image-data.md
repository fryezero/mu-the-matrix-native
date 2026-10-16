# Fixed second image section

Issue #19 adds a read-only acquisition scope for the exact client's second PE section. The offline QEMU/Linux Wine run captured 2,557,764 bytes twice with the same digest. Selected data contains readable asset paths and format strings, which provide candidate references for finding the original model loader. This is compatibility-environment evidence, not complete source or gameplay validation.

## Provenance and bounded acquisition

The original file is pinned by SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Its second section has RVA `0x0167c000`, VA `0x01a7c000`, declared virtual size 2,557,764 and raw file offset 7,492,096 with 885,248 raw bytes. The scope ends at `0x01cec744`, excluding page padding before the next section at `0x01ced000`. The section name is blank; no original `.rdata` name is recovered.

`capture_text.py --scope image-data` accepts no arbitrary address or size. It uses complete readable mappings, mapped-header device/inode checks, target file identity, process start identity, unchanged mapping plans and the source hash. It requires the pinned restored text hash before and after reading, then durably writes the payload and manifest. This tool version has SHA-256 `ea29b59b3e1755671917bedf1de02f06a399345738efe4cca147e924124e3e05`.

Capture10 and its repeat both pass every identity/completeness flag and transfer digest check:

| Item | Value |
|---|---|
| Scope/format | `image-data` / `mu-linux-wine-image-data-capture-v1` |
| Region | `client-image-data.bin`, VA `0x01a7c000`, 2,557,764 bytes |
| SHA-256, both reads | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |
| Text before/after | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |

An early packed-state attempt was refused with empty regions and only a manifest, after text hash `89829ebab3b376be3bb61d6bbc8fda7bce08aacb8a9007bbfcdb82473a93bc1d`. Legacy text and math-data modes then succeeded with their existing formats and previous payload hashes. The outbound network probe failed as required, no game account was used, and the guest shut down cleanly after transfer.

## What is observed

A local scan of maximal printable ASCII runs of at least four bytes finds 40,825 runs. Of those, 72 contain the case-sensitive substring `.bmd`. These are candidate strings, not function counts, parsed assets or proof that every run is meaningful. The original raw section prefix differs from captured memory. Byte entropy falls from the static raw section's approximately 7.98 bits to 5.64 over the larger captured virtual span; different lengths and zero-filled memory also affect that comparison.

The readable paths and format strings support partial restoration of useful data. They do not prove every byte is restored, typed or immutable. Representative model-loader search seeds are data addresses `0x01aef904`, `0x01aefab4` and `0x01aefc6c`, including generic BMD filename formatting and a player-model error message. No caller or original symbol has yet been validated for these addresses. Follow references in pinned text and check instruction boundaries before naming a function.

## Verification and local artifacts

All 94 local integration tests pass. The portable run passes 87 with seven explicit private-input skips. A new synthetic test checks the exact virtual span and excludes page padding and the following section. A fresh 93-file source-only checkout also passes 87 tests with seven explicit skips.

The ignored `evidence/image-data-run10/` directory retains the early, late, repeat, math and text capture directories, `strings.json` and `summary.json`. The bounded startup log is `evidence/image-data-capture-10-run.txt`; the guest driver is `runtime/x86/run-data-capture.sh`. A fresh source-only clone cannot read these private artifacts. Supply the matching installation and reproduce the procedure in `runtime-linux/README.md` before importing any bytes.

Unsuspended sequential reads remain non-atomic. Matching two data digests does not establish all runtime states or native Windows equivalence. No login/gameplay is demonstrated. Next inspect bounded code references to the selected BMD strings and validate the model loader's actual field handling before changing the strict reader.
