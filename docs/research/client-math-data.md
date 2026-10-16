# Selected image-data capture for record arithmetic

Observed 2026-10-15 for the pinned main.exe SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
The existing isolated QEMU x86 Debian/Wine guest resumed without a source share,
with outbound networking blocked. Its outbound probe failed before client launch.
Original installation files stayed unchanged; the guest copy's source identity,
file-backed mapped header device/inode, PE layout and PID/start time were checked.

## Fixed scope and readiness

`capture_text.py --scope math-data` saves only the three reviewed image-data
ranges below. Their combined length is 76 bytes. Arbitrary addresses are not
accepted. Mapping plans require complete readable coverage inside the pinned
image; text confirmation separately requires readable/executable coverage.

| Region | VA | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Scalar added during the selected record operation | `0x01a7dd40` | 8 | `af5570f5a1810b7af78caf4bc70a660f0df51e42baf91d4de5b2328de0e83dfc` |
| Template copied by its fallback branch | `0x01cf3b00` | 64 | `5998e9d1dd9bf48af6af87a1ef8c7783b818ac8329637ada08cc5fb329042376` |
| Clear helper feature word | `0x01cf6618` | 4 | `bce941d196c26696f1f5d701d21a8a9e414e81d6e15a48f3663313e3cd7cc4b9` |

Before and after data reads, the tool hashes the complete 23,572,480-byte text
section and requires the known restored digest
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
It rechecks mappings, process start identity, mapped file identity and source
hash afterward. Files and manifest are flushed before returning. These checks
still do not make unsuspended sequential reads an atomic snapshot.

An early attempt was refused before any data payload was written. Its text hash
was the earlier packed mapping digest `89829ebab3b376be3bb61d6bbc8fda7bce08aacb8a9007bbfcdb82473a93bc1d`.
A later attempt passed all checks and saved all three ranges. Each transferred
file's size/hash was recomputed locally. The same final tool then repeated the
legacy text scope, preserving its manifest format and reproducing the restored
23,572,480-byte payload. The guest shut down cleanly after verification.

Tested capture-tool SHA-256
`11bcd31f1e502ad11c281fd048e4a6bb18fa922584edff33174c667bf4bf34d8`.
This matches the version run inside the guest and recorded in both successful
manifests. The old text scope remains the default; its file/address/bytes/hash
fields and format are retained, with additive scope/tool identity metadata.

## Observations and limits

The scalar equals positive double zero. The template equals an independently
authored standard 4-by-4 float identity matrix. Feature bit 1 is set in this
Wine run, selecting the SSE helper path; the earlier clear comparison already
validated both possible bit states. These observations resolve the selected
runtime data for this captured environment. They do not recover an original
class/symbol or prove native Windows initialization or game invocation.

The values are ready for captured-instruction comparisons of the routine at
`0x004013d0`. x87 control/rounding, exception cases, output aliasing, branch-dependent
register results and the zero-scalar fallback still need validation. Keep the
constants private. An authored implementation may use public mathematical
constructions only after comparison establishes their relationship to these inputs.

Ignored local artifacts:

- `evidence/x86-math-capture-09/`: complete scoped manifest and three payloads.
- `evidence/x86-math-early-09/`: refused early manifest, no data payloads.
- `evidence/x86-text-capture-09/`: final-tool legacy text regression capture.
- `evidence/x86-math-capture-09-run.txt`: guest run, readiness, network and source-hash log.

The portable tests cover fixed scope boundaries, readable versus executable plans,
range hashing/short reads and all earlier file/process identity safeguards. The
actual capture supplies the end-to-end Linux check; no original bytes or raw
records are published with this finding.
