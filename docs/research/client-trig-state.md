# Rotation helper dispatch state

CLIENT-TRIG-STATE-001 / issue #35 captures one four-byte main-image flag at
`0x0bdd1cc8`. Two late reads match value 1. The flag is a branch input for the
trigonometric dependencies of the selected hierarchy rotation helper. It does
not by itself establish the path invoked by the live client.

## Identity and source link

Original executable SHA-256 is
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Restored text starts at `0x00401000`, length 23,572,480 and digest
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
All static addresses below refer to that pinned text. Capture offsets are VA
minus that base, not offsets into the packed executable.

REA 6.5.0/Ghidra 12.1.4 analyzes rotation candidate
`0x00d00724..0x00d008be`, inclusive, 411 bytes in an 8,192-byte raw x86 window
at `0x00d00000`. Evidence ID is
`ev_ab1d111d96e988e1db29bd7973e3c4018cb25b075d45fea18250bb52da7eb593`.
Capstone decodes 113 instructions. The candidate reads three input floats,
scales each through double `0x01a7de98`, rounds back to float, makes six calls
and writes four output floats. The verified second-section capture contains
0.5 at that scale address. The resulting arithmetic is consistent with an
Euler-to-quaternion operation, an inference pending actual-code comparison.
Original names, angle units and live invocation remain unverified.

Three calls target `0x009681bd`, whose 31-byte wrapper widens float to double,
calls `0x01985700`, and rounds its x87 return back to float. Three target
`0x009fa223`, which similarly calls `0x0198c4d0`. Both latter entries read
`[0x0bdd1cc8]`. Zero selects fallback paths; nonzero also checks MXCSR and x87
control state before choosing the other path. Fallbacks at `0x019997cf` and
`0x019996df` contain FSIN and FCOS respectively. Other paths start at
`0x019a72f8` and `0x019acd58` and reference captured second-section tables.
These are bounded instruction observations, not complete recovered CRT symbols
or validated trigonometric implementations.

## Acquisition and checks

`capture_text.py --scope trig-state` saves only `math-dispatch-flag.bin`, four
bytes at `0x0bdd1cc8`. Its format is `mu-linux-wine-trig-state-capture-v1`.
The fixed range lies inside the pinned main image. It reuses exact-file digest,
mapped-header device/inode, process-start, readable mapping and post-read
identity checks. Text must match the restored digest before and after reading.
File/manifest flushing and all existing scope formats remain unchanged.

The acquisition tool SHA-256 is
`4402746b070716d0253e207a0811ae347fc6fd9feb5c1d4972ae0363d58a37a4`.
The isolated QEMU x86 Linux/Wine run verified outbound networking blocked.
Late/repeat reads pass every completeness/identity check and agree on the
four-byte digest
`67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450`.
The decoded little-endian value is 1.

An identity-ready early attempt refused the known packed text digest
`89829ebab3b376be3bb61d6bbc8fda7bce08aacb8a9007bbfcdb82473a93bc1d`.
Its directory contains only an incomplete manifest with an empty region list,
no flag payload. The same tool repeated text, math-data, image-data and
model-dispatch captures. All four formats and every payload length/hash match
the prior run11 results. Transfer verification recomputed each digest and
checked exact addresses, source identity and completion flags. The guest shut
down cleanly afterward. Sequential reads are not an atomic process snapshot.

The new synthetic test pins the address, filename and four-byte limit. All
141 local integration tests pass; portable/source-only checks pass 129 with
twelve explicit private skips. No extra private integration check or automatic
guest execution was added.

## Reproduce and continue

Follow [the runtime setup](../../runtime-linux/README.md), select the matching
main.exe and write outside the installation. The acquisition uses the existing
command with `--scope trig-state`; repeat in a new output directory, then verify
every manifest/payload after transfer. Raw evidence is ignored under
`evidence/trig-state-15/captures/`, with `early-1`, `late`, `repeat` and four
legacy scopes. The local verifier/report are `verify-transfers.py`/`verified.json`;
REA is `rea-rotation.json`, and the driver/run log stay local. Source-only clones
contain none of those inputs or outputs.

Next emulate the actual rotation candidate with pinned text, second-section
data and this flag, under explicit x87/MXCSR state. Follow the real sine/cosine
helpers and stop on unknown dependencies. Do not replace them with host math
and claim whole-helper equivalence without comparison. Native Windows state,
actual caller FP settings, live animation inputs, exceptional-angle handling
and complete renderer behavior remain open.

A later private three-input smoke probe executes the full candidate and actual
trig helpers with captured flag 1 and explicit PC53/RNE/MXCSR `0x1f80`. All
return, with zero input producing `(0,0,0,1)`. It refuses uncaptured reads in the
flag page. This establishes a usable controlled execution lead, not authored
source equivalence, complete memory/ABI coverage or live client FP settings.
The probe and report remain ignored as `probe-rotation.py`/`rotation-probe.json`.
