# Observed v15 decoder dispatch

CLIENT-DISPATCH-001 / issue #24 resolves two selected runtime jump slots used
by the model-loading path. Both point inside the pinned restored client text.
The six-byte entries are indirect jumps, not complete decoder implementations.
This result enables bounded algorithm recovery without acquiring another DLL.
It does not establish that the live game invoked either target.

## Exact inputs and method

The original executable SHA-256 is
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Its restored text at `0x00401000`, length 23,572,480, is pinned by
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
Capstone 5.0.9 decodes the model-path call targets as indirect memory jumps:

| Entry | Referenced four-byte slot | Observed target | Slot payload SHA-256 |
|---|---|---|---|
| `0x0091a6c0` | `0x01d04e14` | `0x0092a430` | `aba07ebb7084c95fd575a3f30955e6ab9bc52b89612482ecde4cd25442899d5d` |
| `0x0091a730` | `0x01d04df4` | `0x0092be30` | `ec514d730caf387dda906bfa17ac4d9c7dbc2ec7efc5ca1a89cd21a4cabc76de` |

`capture_text.py --scope model-dispatch` reads exactly these eight bytes. Its
new format is `mu-linux-wine-model-dispatch-capture-v1`. It reuses the readable
mapping, mapped-header device/inode, process start, source-file hash and
post-read identity/mapping checks. Pinned restored text is required before and
after slot reads. Payloads and manifest are flushed to disk. The tool SHA-256
for this acquisition is
`9dde7db64e754ee3945585728b4ed29a86c3ca187eb94ad3d4fca22377154ae0`.

The isolated QEMU x86 Linux/Wine run used blocked outbound networking. Both
late capture11 and a repeated read pass every identity/completeness flag and
produce identical slot hashes. After transfer, all payload lengths and digests
were recomputed. Both decoded values lie inside the verified executable text
range, so their instruction bytes are already available in that capture.
No arbitrary target memory was acquired by the new scope.

## Early refusal and compatibility checks

The first early attempt reached the reader before process identity was ready
and was refused before creating an output directory. Its failed attempt stays
in the local run log. A second controlled startup waited for the exact process
name/directory, then immediately attempted the same scope. It was refused on
the known packed text digest
`89829ebab3b376be3bb61d6bbc8fda7bce08aacb8a9007bbfcdb82473a93bc1d`.
Its only output is an incomplete manifest with an empty region list. No slot
payload was saved before the restored-state guard passed.

The same tool also reproduced the old text, math-data and second-image-data
formats and all previous payload hashes. One new synthetic test checks the
two exact addresses and eight-byte total. All 103 local integration tests
pass; portable checks pass 95 with eight explicit private-input skips. A fresh
101-file source-only checkout also passes 95 with eight explicit skips. The guest shut down
cleanly after the transferred evidence was verified.

## Interpretation and next step

The model-loading caller supplies key/context setup and decode parameters to
these entries. The captured values identify where to inspect next; they do not
establish original symbols, complete function boundaries, CPU-selection rules,
all possible bindings, algorithm equivalence or native Windows behavior.
Two matching reads do not make unsuspended sequential acquisition atomic.

A bounded REA/Ghidra follow-up for the decode target observes a 198-byte body
through `0x0092bef5` that dispatches groups of eight, four and one block to
other code targets. Evidence ID
`ev_6d66b208948d94526d1010311f5088eec5490d1a692540833c2dfe25bac123d5`
is analysis output, not a verified source implementation. Trace its argument
passing and helpers before choosing an editable replacement.

Raw data/manifests are ignored under `evidence/model-dispatch-run11/`, including
`dispatch-early-12-1/`, the late/repeat slots and three legacy capture modes.
Logs are `evidence/client-lea/dispatch-capture-11-run.txt` and
`dispatch-early-12-run.txt`; bounded dossiers/windows are in
`evidence/client-lea/` and `evidence/client-lea-resolved/`. Guest drivers remain
under ignored `runtime/x86/`. A fresh GitHub clone contains none of these
private inputs. Use `runtime-linux/README.md` to reproduce with the matching
installation, then validate each complete manifest and hash before analysis.
