# Native Data version drift, DATA-ACQ-004 manifest slice

Implemented against the supported `main.exe` SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
This is authored acquisition/integrity code, not a reconstructed client routine;
no original instruction equivalence claim is made. No client bytes or derived
data are published. [Procedure and schema contract](../native-data.md).

## Verified behavior

One C++17 engine, `native/data/manifest.cpp`, runs in the portable native tools
and in the app's bundled `mu-native-data` helper. SHA-256 uses the existing
Crypto++ dependency. Runtime needs no Python. The helper is bundled, its dylibs
are relocated, and it is signed before the app's outer signature.

The root manifest pins the executable and every installed output, including
component manifests. Each component records exact source input hashes and the
producer version/options. The first-run GFx component records every installed
GFx input, including fonts and NaviMaps. Optional export copies preserve their
own manifests. Setup rejects legacy or mismatched data before modifying it.
Partial failures leave no usable completion record. Native command-line checks
run before loading or rendering and return the same actionable message.

Portable tests cover matching sets, manifest/executable build mismatch, missing
and partial manifests, changed/missing/extra outputs, tampered entries, duplicate
and traversing paths, symlinks, failed writes preserving the previous manifest,
pin alignment with the evidence index, native consumer refusal, and the actual
language exporter writing snapshot provenance and refusing a dirty destination.
Three planted mistakes bypass build, inventory and completion checks separately;
the negative cases detect all three.

App tests use an authored executable and an isolated helper compiled with that
fixture's pin. The production pin is unchanged. A temporary HOME and
CFFIXED_USER_HOME with no Python on PATH exercise first-run conversion and
manifest writing. A corrupted build field is refused by `--print-plan`,
`--smoke`, and `--setup --force`, without creating a client log or relabeling the
manifest. Deleted movies and unversioned scratch exports are refused. The normal
synthetic offline flow still reaches the world under the existing guard.

Checks and final gate counts are recorded in [the handoff](../handoffs/DATA-ACQ-004.md).
Local logs are outside the repo in
`~/Documents/MTM/mu-mac-tools/native/scratch/data-acq-004/`.

## Limits and remaining work

Guided capture packaging and a real second user's reproduction remain
DATA-ACQ-002/CAPTURE-KIT-001. The temporary HOME does not prove Finder consent or
another account's permissions. Existing owner Native Data was not modified or
retroactively attributed. Historical snapshots require known matching provenance;
matching `main.exe` supplied alongside a snapshot cannot prove its origin.

Raw library APIs and unversioned research fixtures retain their prior behavior.
Managed folders are identified at command-line entry by manifest, legacy setup
record or the standard folder name. The app requires manifests even on custom
import paths. The format is an integrity record, not an authenticity signature;
concurrent external modifications after a completed check are not serialized.

No original client or launcher was started, stopped or driven. No network,
protection, account, live-service or dispatch code changed. The jump-table diff
tool remains pending on paused NET-DISPATCH-001, as the user explicitly excluded
it from this slice. No claim of full DATA-ACQ-004 completion is made.
