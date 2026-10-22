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

## Checkpoint verification and remaining work

The packet/lifecycle-builder/finalizer checkpoint completed **18,795 C-to-client
comparisons, zero mismatches, 16/16 production-C planted mistakes detected**.
A separate installed-formula check completed **1,011 comparisons, zero mismatches**.
The broader category, receive-state and display comparison suites are being joined
before publication; these research counts do not establish unimplemented UI behavior.

At this checkpoint, item option presentation and the additional receive-transition
comparisons are still in progress. Original active `0x00cd1534` excellent eligibility
is an opaque runtime-patched boundary. External item-state maps, later base-stat
finalizers, full advanced durability, CRT corner cases and original GFx rendering
must not be claimed equivalent merely because option fields are preserved.
