# HelpWindow, SYS-MISC-001b

WIP, 2026-10-28. Reader evidence is complete for the bounded cases below.
The movie is not hosted yet. No original client, network or live game ran.

## Inputs and method

Pinned restored text SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`,
base `0x00401000`; second-section SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`,
base `0x01a7c000`. CPU feature word pin
`bce941d196c26696f1f5d701d21a8a9e414e81d6e15a48f3663313e3cd7cc4b9`.
These are existing compatibility-environment captures, not native Windows evidence.

Background: stopped SYS-MISC-001a finding at `60cd0dd`, read with `git show`.
HelpWindow manager field is `+0x120`, registration `0x00ac678a`, constructor
`0x00b89588`, vtable `0x01a8f180`, loader `0x00b89977`.
The converted HelpWindow.swf pin recorded there is
`c12ab7e6f778677b7a7e9ac646cdc8c12eb2200bcd49556585380491c3e75c49`.
No decoded game rows, movie bytes or captures belong in this repository.

## Reader contract

Verified reader `0x00b8968b..0x00b89866`:

- Clears exactly `0x11000` bytes at handler `+0x78` before opening the file.
- Reads `Data/Local/helpdata.bmd`: 512 records of 136 bytes, then a little-endian
  checksum word. Required bytes total 69,636. There is no count prefix.
- Checks the encoded payload with `0x00976895`, key `0xc4f7`, before decoding.
- On checksum equality, calls `0x00976855` separately for each 136-byte row.
  The XOR key phase restarts for every record, using `fc cf ab`.
- Copies each decoded row to `handler + 0x78 + index * 136`.
- Missing/corrupt input leaves the cleared table and reaches the original
  message-box import at return `0x00b89851` / `0x00b89791`. The native wrapper
  returns an explicit status instead of issuing the client's shutdown message.
- The original ignores both fread return values. Native short-read rejection
  is a deliberate safe policy, not an original-instruction equivalence claim.
  Both ignore bytes beyond the required checksum.

The existing `reconstructed/data/data_tables.c` already records this schedule.
`reconstructed/help/help.c` reuses that decoder and provides a file reader with
clear-on-failure behavior. It is independent of any game/session feed.

## Row/controller observations

Static reading, pending controller comparison:

| Offset | Observed use |
|---|---|
| `0x00` | Signed 32-bit row ID; zero terminates provider construction |
| `0x04` | Category byte: 0 or 13 enters the hotkey list; 1 enters the chat list |
| `0x05` | Auxiliary category byte: 1 or 2 also enters a third list |
| `0x06` | Key string, 64-byte field |
| `0x46` | Description string, remaining 66 bytes in the record |

The generic table-layout inventory calls `0x04` a 16-bit group; the controller
actually branches on its two bytes independently. `0x00b89866` stops at the
first zero ID, clears the first two lists and appends to the third list without
clearing it. List fields are `+0x11078`, `+0x11084`, `+0x11090`.

Loader `0x00b89977` checks base load success, reads the file and builds lists,
then invokes InitText with GlobalText IDs `0xd57..0xd5b`, SetPosCenter,
ClearDataProvider, and both row emitters. `0x00b89cc0` sends SetHotKeyData
for ID 1, ID 2 when `0x01072aa9` is false, or ID 3 when it is true.
`0x00b89e69` sends every chat-list row with SetChatHotKeyData. Both pass key
and description after the client's ANSI-to-UTF-8 conversion boundary.
`0x00b89c17` clears the movie provider and replays both lists.

The current input finding records F1 only as a close path for absent legacy
windows 24/25. It does not establish an F1-open HelpWindow binding. No native
binding or menu route is claimed yet.

## Checks at first checkpoint

`scripts/validate_help.py --cases 48 --mutants --game-root <installed-root>`:
56 comparisons, zero mismatches. Families: valid synthetic 48, corrupted 6,
missing 1, installed 1. Valid files execute 25,088 original per-row decode calls
and compare all 69,632 output bytes per file, including inactive trailing rows.
Installed encoded-file SHA-256
`4e585735f248799d6836da1f13767f5a0ff60094a43dc9f4d1b40d3a3336b700`.

Six compiled source mutants are caught: checksum key, row stride, row count,
XOR key, omitted final copied byte, and stale data after failure. These mutate
the compiled production reader/decoder sources in temporary directories.
The runner compares actual original output, not a second Python decoder.

The existing data-table machine supplies CRT file/allocator boundaries. The
reader, checksum, XOR, memset and memcpy execute original instructions. Path
formatting `0x009619dd` and error logging `0x01206598` are skipped services;
the error import terminates the modeled original path. Short-read values are
not presented as original behavior.

Portable `tests/test_help.py`: five tests pass, one private-input test skips
by default. Seven truncation lengths, six corruption offsets, valid/trailing
files, missing/reload and invalid pointers are covered. Private mode invokes
the original comparison and mutants. No full Mac gate has run for this WIP.
