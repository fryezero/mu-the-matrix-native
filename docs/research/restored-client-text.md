# Restored client code through an emulated Linux runtime

Observed 2026-10-15 for the pinned main.exe SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. This is compatibility-environment evidence from the owner's isolated game copy. No account login or gameplay was demonstrated.

## Runtime and capture

The host used QEMU 11.1.2 full x86-64 TCG on Apple Silicon, Debian 12 amd64, Wine 8.0 with both architecture loaders, Xvfb and Mesa LLVMpipe 22.3.6. The guest provided software OpenGL 4.5. An authored 32-bit Windows console probe ran; the x64 helper passed its own-process memory and SHA-256 self-test. Outbound networking was blocked with QEMU `restrict=on` before client launch; a guest outbound TCP probe failed. SSH forwarding remained restricted to host loopback.

The original installation stayed unchanged. The guest copy's main.exe digest matched the target before launch. Two-to-five-minute bounded runs remained in initialization with no demonstrated login window. Logs repeatedly reported an unavailable localhost port 55232. The caller/purpose of that connection is unresolved; it is not evidence of a game-server protocol or a license requirement.

The x64 helper's module enumeration returned Windows error 998. A same-bitness build captured seven executable regions across main.exe and IGC.dll, but reported two failures and an exited target at completion. That wider capture is explicitly incomplete. Its successfully saved region hashes were recomputed locally.

The Linux alternative selects only the first executable image section. The authored [capture tool](../../runtime-linux/capture_text.py) pins the source file hash and checks the process directory/name/start identity, mapped PE32 header and its file device/inode before and after reading, complete readable/executable coverage, post-read identity/mappings and unchanged source. It writes a manifest even after acquisition errors and flushes its files. It does not suspend the process, so successful checks still do not imply an atomic snapshot.

## Before and after bytes

| Observation | Region | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Early Linux capture, about ten seconds after launch | `0x00401000` | 23,572,480 | `89829ebab3b376be3bb61d6bbc8fda7bce08aacb8a9007bbfcdb82473a93bc1d` |
| Later same-bitness helper capture | `0x00401000` | 23,572,480 | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Later Linux text capture while target remained alive | `0x00401000` | 23,572,480 | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |

The early bytes exactly equal the original first section's raw bytes padded with zeros to its mapped size. The later region differs in 22,180,554 byte positions from that mapped baseline. It contains ordinary instruction sequences and recognizable arithmetic operations. The matching late digests establish a repeatable restored region in these runs, not that every function was executed or fully understood.

The declared first-section virtual size is 23,571,611 bytes; the captured page-aligned mapping includes 869 extra bytes. Keep that distinction when importing addresses. The original raw file offset is `0x600`, but restored bytes do not exist at that on-disk offset. Import the capture as raw x86 at `0x00401000`.

## Bounded native analysis

A 4,096-byte prefix was extracted from the verified later region. Prefix SHA-256 is `12862e9cdd93ac2586988694fc4c08066361de7bf31048442bb8cf7ea57a096d`. REA 6.5.0 with Ghidra 12.1.4 successfully decompiled the routine at `0x00401030`; evidence ID `ev_84d38c1948c96dc7db9894b05f5ef71ec9cfe82d91eda3193c70e390a6ff0f36`.

Raw import used x86 at `0x00401000`, two explicit function seeds, a 2 GiB heap and disabled `x86 Constant Reference Analyzer` / `Scalar Operand References`. Seed names are investigator assertions. REA's admitted raw importer uses its generic compiler profile; the pseudocode leaves the ECX input implicit and does not establish a complete Windows calling convention. Attempts to override the raw compiler profile were explicitly rejected. Full 23 MiB analysis was interrupted and is not reported as a completed decompilation.

| Address | Observation | Interpretation limit |
| --- | --- | --- |
| `0x00401000..0x00401015` | Forward copy of sixteen 32-bit words, destination received in ECX, destination returned | A 64-byte object copy; original class/type and overlap contract are unknown |
| `0x00401030..0x0040105b` | Squares and adds three adjacent components, stores a float intermediate, calls `0x01999870`, returns a float-rounded result | Candidate three-component Euclidean length, not a validated portable replacement |
| `0x00401060..0x0040108c` | Similar computation using components at offsets `0x10..0x18` | Candidate adjacent vector/row operation; object layout is inferred |
| `0x00401090..0x004010bc` | Similar computation using components at offsets `0x20..0x28` | Same object-layout uncertainty |
| `0x004010c0` | Computes a related scalar and scales the first three components | Candidate normalization/scaling; zero, nonfinite and rounding behavior remain unverified |
| `0x019998a3` | x87 square-root operation inside the observed callee | The callee's surrounding control-word/error paths must be understood before substitution |

The square-root callee lies outside the 4 KiB REA prefix. It was separately inspected in the full captured region with Capstone 5.0.9. Do not infer that the bounded REA import contains its body. x87 intermediate precision, float stores, control-word state and error handling matter for equivalence. No decompiler text or original instruction bytes are committed here.

## Private artifacts and continuation

- `evidence/x86-capture-01/`: incomplete wider capture, verified first-section payload, byte-comparison summary and prefix-analysis provenance.
- `evidence/x86-linux-capture-02/`: early still-packed mapping evidence.
- `evidence/x86-capture-text-08/`: final successful scoped capture, including the checked PE32 layout and mapped file identity, durable manifest, locally verified payload and matching tested tool-source digest.
- `evidence/x86-capture-text-05-run.txt`: earlier successful scoped capture before the additional PE-layout check.
- `evidence/rea-restored-client-prefix.json`: complete successful REA record and generated pseudocode.
- `runtime/x86/`: verified base, working guest disk, local SSH key, setup and run logs. These files stay ignored.

The final tool source SHA-256 is `f6e50e0aa69dc734eee0c30feab263a2e6da6dba65a7ca9831db3c64f64ed88e`. It matches the version run inside the guest. The complete final capture was transferred and its 23,572,480-byte payload digest recomputed locally.

Next, map selected restored functions and imports, and reconstruct one bounded behavior with independent equivalence checks. Establish the unavailable localhost dependency before assuming that the current Wine initialization state matches a normal Windows session. A readable client region is progress toward source recovery; no complete client source build or native macOS game exists yet.
