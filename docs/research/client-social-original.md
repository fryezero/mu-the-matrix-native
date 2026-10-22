# Original party, messenger, mail and item-instance reconstruction

NATIVE-SOCIAL-001, round 2. This note continues [the social milestone](client-social.md).
The implementation remains transport neutral: original request schemas and receive
handlers feed an explicitly authored offline server adapter. No real game request
or inventory transaction is sent.

## Evidence identity and method

Target executable SHA-256: `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
The private compatibility-environment captures are the same pinned inputs as the
first milestone: restored text at VA `0x00401000`, SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`, and image data at
VA `0x01a7c000`, SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
Text file offsets are VA minus `0x00401000`. These are restored Linux/Wine inputs,
not native Windows or live-play proof.

Static instruction readings identify the interfaces. The private-input validator
executes the named instructions against production C using synthetic packets,
records and external-state models. C++ manager/container/string operations,
transport, allocation, UI and specified formula inputs are separate boundaries.
Execution outside each allowlist or from undefined tracked memory fails. Neither
protection code nor network encryption/login is entered.

## Party actions

The invite button reaches `0x016a6775`, then `0x016b6771`: logical opcode `0x3a`,
requester key in high/low byte order. The permission method distinguishes blocked
worlds, party leadership and PK state. Incoming request `0x40` stores the requester
key before the `0x0095bd05` autoaccept decision. A current friend lookup is required;
removing a friend must also remove their friends-only autoaccept privilege.

Popup 13 result 0 accepts, result 1 declines; `0x009602cc` builds opcode `0x86`.
Answering retains the requester key. The HUD leave/kick popup is `0x37`; confirming
calls `0x00c79b05`, which serializes the member's number, ten-byte name and NUL in
an ordinary C1 packet whose **opcode** is `0xc3`. This opcode is distinct from a
C3 encryption envelope. The alternate popup `0x39`/BF56 path is a separate action.

`0x0127373e` maps party result `0x41` to notices without changing membership.
Clear `0x43` removes the list before interpreting its status; the stored requester
key is retained. `mu_social_receive` is the session entry point for those normalized
receives. Offline membership changes and leader authorization remain server policy.

## Messenger and mail

UI IDs are shared monotonically allocated u32s. Room numbers are u16s, participant
serials u8s, letter IDs u16s. None is interchangeable with a list position. Room
open answers use dispatcher key `0x83`; mode 1 reconnects an existing peer room
while retaining its movie identity. The native adapter retains loaded/transcript
state and changes connection information through `ChangeChatRoomInfo`.

Room receive boundaries cover membership `0x0122aa7e`, roster loop
`0x00b76a01..0x00b76b62`, and text `0x00b772af`. Rosters are not clamped to the
outgoing invite limit of 30. Text receives reject more than 100 bytes. The send
builder itself appends the full string with its low-byte length; the native editor
applies a separate 100-byte policy. Text transformation is the bounded three-byte
helper, supplied with an explicit adapter key, not the excluded network cipher.
Minimizing retains the room and undelivered messages. Closing is idempotent.
Arrival-time sender names accompany native history so replay cannot relabel an old
message after the server reuses a serial. This retained native history is an
adapter extension to the original movie's current-roster lookup.

Mail header/body boundaries are `0x012506cd` and `0x012509e3`. Header status 2 is new
unread mail; bodies are bounded at 1,000 bytes and may be cached before their header.
Read uses opcode `0x30` only on a cache miss. Compose allocates a UI without sending.
Write uses the original logical A7 schema; success closes that compose UI, while
failure retains the draft. The offline server delivers only self-addressed mail
to this inbox; an ordinary outgoing acknowledgment does not create an incoming row.
Reply uses a read UI ID. Next/previous follow insertion-list neighbors without wrap.
Delete sends opcode `0x40` only after confirmation and removes state only on success.
Read-state updates call `SetMailReaded` without rebuilding mailbox checkboxes.

String conversion remains a boundary: the original GFx conversion uses UTF-8 to
the process ANSI code page, while this offline adapter retains UTF-8. Original
compose limits of 255/10/32 converted bytes are distinct from its 1,000-byte paste
and receive paths. These are not encrypted-wire or original code-page guarantees.

## Full item-instance fields and options

`0x00f08dca` forwards all fifteen wire bytes into category conversion
`0x00f08fb2..0x00f09c51`. The native wire codec round-trips every field. Inventory
escrow, exchange and vault transfer preserve that complete instance, dimensions
and durability. Incoming trade validates the whole Item.bmd rectangle before
insertion. Outgoing permission separately follows `0x016bed45`, including period,
category, special-code and record-flag branches.

The category converter distinguishes ordinary harmony, grade-2 sockets, elemental
ranks, guardian selectors, artifact pairs and extra-word/advanced fields. Socket
extension masks are unnormalized 0/64/128/192 values; extended FE/FF bytes can be
populated sockets. Rank constructor defaults are four `-1` fields, and advanced
slot defaults to `-1`; an absent rank is not a populated zero rank.

The whole `0x00ccc993..0x00cce06c` finalizer includes ordinary option IDs/values,
special-code bit consumption, formula calls, nine excellent slots and A(0x13)
auxiliary reconstruction. Row absence remains distinct from a resolved zero value.
Excellent classification uses the original Common/Wing category keys. Raw excellent
bits are distinct from the finalized excellent flag.

Fixed option BMDs use the existing decoder. The private Lang exporter preserves
composite guardian/advanced keys and all artifact record tails; truncated snapshots
are rejected. No rows or text are compiled into the program. Existing set-prefix
logic is reused. The formula parser preserves the captured client's same-precedence,
left-associative multiply/divide/power operators and ten-significant-digit decimal
round trip after each operation. Missing formula keys mean numeric zero; empty or
malformed input is a separate native error. Host printf/strtod/pow/decimal formatting
remain explicit CRT compatibility boundaries.

## Option presentation and native integration

The trade hover uses the complete instance, with the same option presenter available
in inventory, shop and vault tooltips. Contextual prices remain after packet-option
assembly. Item models use the resolved excellent flag, semantic ancient bits and
element instead of interpreting packed socket/rank bytes as rendering flags.
Mutable native durability, level and additional-option fields overlay their known
wire bits on export; all other instance bytes survive reservation, cancellation,
exchange and vault round trips. Reserved items cannot leave through NPC script
sell/put actions, including a covered cell of a multi-cell item.

Ordinary/additional, excellent, socket and ordinary-harmony consumers are compared
at `0x016bc789`, `0x00cd0dfe`, `0x010a9fdf` and `0x00cd241f`. The socket comparison
checks both the calculated float and the actual narrowed formatter argument.
Normalized slots EC/ED/EE map to 12/13/14. Maximum HP/MP inputs come from native
character state when known. Unknown inputs produce an unavailable-details line.

Guardian construction `0x00f097e1..0x00f0999e` uses `(selector, base level)` keys,
including selector FF and repeated selectors. Names use the selector, rather than
the copied row ID. Presentation `0x00f0d812..0x00f0dc23` calls formula family 8 with
upgrade level. IDs 2/3 supply an unscaled auxiliary integer and a binary32-rounded
result promoted to double. Bonus fields are formula indices too. Special texts,
bonus ordering, footer and low-durability notice follow the observed branches;
blank-line layout is native policy.

Artifact construction `0x009627be..0x00962888` uses the first exact ordered pair
match, signed threshold/percentage arithmetic and formula family 11 with four
arguments `(raw, level, raw, level)`. Zero divisors return an explicit native error
instead of entering the original fault. Formatting `0x00962e2f..0x00962f9b` selects
by text ID, includes the literal plus sign and wraps nonzero ranks even for unknown
format modes. Missing text and present-empty text remain distinct. The original
outer printf copy of preformatted text is modeled as a safe native literal copy.

Earring formatter `0x010ee390..0x010ee6a9` narrows option/selector/tag to bytes and
uses positional values, not stored row IDs. IDs 28..31 call family 9 for each
supplied item and truncate each result before wrapped integer addition. The
self-only trade preview does not invent an equipped partner. The intermediate
format-2 suffix contains two percent characters, as observed in the original.

Standalone Errtel display `0x00fc7317..0x00fc74ec` matches code, physical rank and
option, then indexes one of eleven display values. Holes do not renumber physical
keys. `0x00fc9714..0x00fc99d6` inspects all five bytes independently of its count,
with separate ordinal headings and missing-option fallbacks. Mastery dispatch is
an explicit unavailable boundary. Pentagram rank `0x00fcaa9a..0x00fcabd9` uses
ItemTooltipText 4AE/4AF and formula family 1 with the record's required level and
rank level. Equipment-dependent embedded Errtels and set activation are labeled.

Advanced harmony `0x00cbc777..0x00cbc8fc` uses signed group/option keys and literal
names with ` +value` or ` +value%`. Unsupported formats stay empty. Threshold
`0x00cbc6f2..0x00cbc741` returns the first stored signed threshold that contains
the value, retaining missing-row presence separately. It does not sort thresholds.

Option BMDs load read-only from the installed game. Recreate the private typed
Lang export locally, never commit it:

```sh
python scripts/live_social_options_to_plain.py /LOCAL/lang4.bin \
  --artifact-snapshot /LOCAL/lang1.bin --out-dir /LOCAL/lang
```

Set `MU_LANG_DIR` to that directory. The new `social-options.tsv` must also be in
the Preview app's local Native Data/lang directory. Existing Lang copies are not
replaced by the installer merely because a new export file exists.

## Verification

`scripts/validate_social2.py --cases 500 --mutations --game-root /LOCAL/GAME`
completed **29,700 compiled-C comparison cases, zero mismatches, 36/36 planted
production-C mistakes detected**. Counts sum the reported comparison families;
one guest invocation can check more than one family. The total comprises 9,000
packet/request comparisons, 9,795 finalizer/excellent-value comparisons, 3,000
category/prefix/trade-permission comparisons, 1,763 formula comparisons, 2,000
ordinary/excellent/socket/harmony display comparisons, 3,554 further option
constructor/selection/presenter comparisons and 588 receive-state comparisons.

The receive-state comparisons execute original room-open modes, mail send/delete
answers, read/cache/body transitions and pending-map operations against the native
session model. The final presenter join compiles the actual typed-row loader and
compares Guardian, Artifact, earring, Errtel, pentagram and advanced-harmony
selection/presence, formula operands and formatter arguments. Research-only oracle
counts are not included. Missing typed tables have availability separate from
loaded-empty tables and absent keys; populated Guardian, earring and Errtel
instances visibly report unavailable details. Backward-compatible valid rows and
explicit exporter availability headers supply that distinction.

Portable regressions cover original logical packet builders, receive transitions,
party invitation identity, room reconnect/load/delivery, serial reuse, hidden
message queues, draft restoration, active-window selection, read-state checkbox
preservation, mailbox/window capacity, raw item escrow/vault round trips, packet
price context and unavailable excellent tables. Offline GL renders use the actual
FriendWindow and Trade movies; no original game session or real item transaction
was needed. Renders remain under
`~/Documents/mu-mac-tools/native/renders/social/round2-{mail,compose,messenger,trade-options}-final/`.

## Remaining boundaries

Transport transformations, original ANSI-code-page behavior, native Windows and
live original GFx behavior are not established. Manager/container/string/UI and
specified CRT calls are external models, not reconstructed client bodies. The
receive corpus excludes two peer-map sentinel states and eight invalid cached
packets that cannot be represented by this bounded native model; these are not
counted as comparisons. The model's native capacity and allocation recovery are
separate from original unbounded-container assumptions.

Active `0x00cd1534` excellent eligibility is runtime-patched and opaque. The tooltip
labels its table-resolved excellent candidates as a preview, preserves every raw
requested ID, and reports unavailable tables instead of silently erasing options.
External item-state maps, equipped ancient/earring activation, embedded Errtel
handles and uncaptured mastery/prerequisite patch bodies remain unavailable.
Later full base-stat finalizers, exact original tooltip layout/colors and every
CRT/locale corner case are not claimed equivalent. These boundaries do not remove
or rewrite the original fifteen-byte trade instance.
