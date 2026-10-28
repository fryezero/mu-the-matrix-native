# HelpWindow, SYS-MISC-001b

WIP, 2026-10-28. The reader and bounded controller comparisons pass; the real
movie is hosted in an isolated viewer and the native offline client. The
locked full Mac gate and merge remain open. No original client, network or
live game ran.

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

The controller comparison below verifies these field uses:

| Offset | Observed use |
|---|---|
| `0x00` | Signed 32-bit row ID; zero terminates provider construction |
| `0x04` | Category byte: 0 or 13 enters the hotkey list; 1 enters the chat list |
| `0x05` | Auxiliary category byte: 1 or 2 also enters a third list |
| `0x06` | Key string starts here, 64 bytes before the description |
| `0x46` | Description string starts here, 66 bytes remain in the record |

The generic table-layout inventory calls `0x04` a 16-bit group; the controller
actually branches on its two bytes independently. `0x00b89866` stops at the
first zero ID, clears the first two lists and appends to the third list without
clearing it. List fields are `+0x11078`, `+0x11084`, `+0x11090`.
The original string constructors read to NUL. They do not establish whether
the final two record bytes are part of a declared text array or padding.
The native 66-byte description bound uses the remaining record extent.

Loader `0x00b89977` checks base load success, reads the file and builds lists,
then invokes InitText with GlobalText IDs `0xd57..0xd5b`, SetPosCenter,
ClearDataProvider, and both row emitters. `0x00b89cc0` sends SetHotKeyData
for ID 1, ID 2 when `0x01072aa9` is false, or ID 3 when it is true.
`0x00b89e69` sends every chat-list row with SetChatHotKeyData. Both pass key
and description after the client's ANSI-to-UTF-8 conversion boundary.
`0x00b89c17` clears the movie provider and replays both lists.

The current input finding records F1 only as a close path for absent legacy
windows 24/25. It does not establish an F1-open HelpWindow binding or a
HelpWindow menu route.

The host now uses Ctrl+H, explicitly logged and documented as a native binding.
It does not replace F1. Bare H remains the expanded-storage route. HelpWindow
is optional and Ctrl+H is enabled only after valid installed rows are loaded.

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

## Controller and constructor checks

`validate_help_controller.py --cases 64 --mutants`: 832 comparisons, zero
mismatches, 11 compiled source mutants caught. Cases by family:

| Family | Cases | Comparison |
|---|---:|---|
| Constructor provider projection | 64 | Three empty providers; original base/vector/callback boundary trace checked separately |
| Provider rebuild | 64 | Ordered copies of all selected 136-byte records in all three lists |
| Hotkeys | 192 | Ordered SetHotKeyData strings, modes 0, 1 and 2 |
| Chat keys | 64 | Ordered SetChatHotKeyData strings |
| Reload | 192 | ClearDataProvider followed by the two ordered row streams |
| Loader | 192 | InitText arguments, SetPosCenter, clear, row streams, success return |
| Base-load refusal | 64 | No invokes or provider mutation; false return |

Corpus includes empty, 511-row and full 512-row tables, negative/nonstandard
IDs, both category bytes, retained auxiliary rows, and strings reaching both
field boundaries. The original constructor executes `0x00b89588` and its
callback constructor `0x00b89fbc`: base construction, vector offsets, allocation
of 20 bytes, callback vtable `0x01a8f1d0`, owner pointer and registration at
handler `+0x30` are checked. Compiled C reproduces the provider projection.
The native GFx layer supplies its own base window/callback lifetime; C++
allocation/refcount/exception internals are modeled services, not ported code.

The controller machine allowlists the original bodies and supplies explicit
STL vector, iterator, std::string, ASCII identity conversion, GlobalText,
base-load and GFx Invoke services. It executes the actual window selection,
iteration, filtering, argument offsets and invoke order. The loader's reader
is a stub supplying its input table; the separate reader families validate
the file instructions. This is not an original code-page or whole-C++-runtime
comparison. The callback/GFx allocation failure path remains outside it.

Native capacity is 512 copied records per provider. A rebuild that would
overflow retained auxiliary rows refuses atomically. Unterminated key/text
fields refuse before row invokes. These are native bounds absent from the
original's unbounded STL/string behavior.

## Native hosting and checks

Registration statically pushes alignment 9 at `0x00ac677d`. The shared layer
opens HelpWindow.swf as an optional MUComponent movie, retains its UIInit path,
and sizes it through SetWindowSize. The one-time `world_gfx_help_load` reads the
installed file, sends the recovered controller calls and enables Ctrl+H.
There is no help frame hook or per-frame allocation. Invalid/missing data clears
the movie providers and leaves the binding unavailable. The existing native
Latin-1 conversion is used, as in quest windows. Standard mode 0 is explicit
native policy; the original mode getter's platform preference is not recovered.
GlobalText `0xd57..0xd5b` supplies headings when available; compact English
fallback headings are native labels. Installed row text is not rewritten to
claim that its listed legacy shortcuts are working native bindings.

- Isolated real-movie viewer: mode 0 sends/displays 32 hotkeys and 14 chat
  rows; mode 1 sends/displays 28 and 14. Movie provider lengths are read back
  and checked against the emitted counts. Hotkey and chat renders inspected.
- Isolated SDL window: 120 frames, count parity and visible rows checked.
- Native client build passes. Headless GL journey reaches offline scene 6,
  95 frames, HelpWindow rendered over the world and inspected.
- Actual native client window: Ctrl+H opens, Esc closes, Ctrl+H reopens, mouse
  selects the chat tab, Esc closes. Both tab screenshots inspected. Finite
  scripted run exits at frame 140 in 9.26 seconds, no store or audio enabled.
- `tests/test_help*.py` with private inputs: 13 tests pass. Two synthetic
  file-to-layer tests pass, covering valid, missing, truncated, corrupted,
  toggle, release, focus and close/unbind behavior.
- Existing GFx2: 16 tests, 8 pass / 8 optional private-renderer skips. GFx3:
  12 tests, 6 pass / 6 optional skips. Input router: 13 tests, 12 pass / 1
  optional private skip. No old renderer hash is intentionally changed.

Still required before merge: full current-main Mac gate under the queue/lock,
review of shared hooks against the active lanes, and any resulting repairs.
This WIP has no PR and makes no merge or installed-app refresh claim.

Final checks extend the reader to seven compiled mutants: decoding the whole
payload in one XOR unit is caught, directly testing the per-record phase reset.
Both registered validators pass with 887 synthetic cases and 18 total mutants.
The separate installed reader case brings the total to 888 comparisons.
The registry consistency suite passes 17/17 tests.

A final real client window run also supplies the installed GlobalText export,
resizes from 1280 by 800 to 1024 by 768, and switches tabs with the mouse.
Both resized renders were inspected; center placement and row content remain
visible. The run exits at frame 145 after 8.98 seconds. Some installed heading
strings and long descriptions clip in the converted movie's fixed text fields.
This is observed, not an original-image comparison. Review the HelpWindow text
layout before calling the visual result final; no shared font/movie rewrite
was made to hide the clipping.

## Text layout and scrolling review (resume, 2026-10-28)

Static, from the converted movie's ActionScript and tags: HelpWindow sets
plain `.text`; every heading and row field is a single-line DefineEditText
(`multiline=false`, `wordWrap=false`) using the 12 px `$NormalFont` import.
The list renderer (MUComplexListItemRenderer) writes Data1/Data2 into fixed
fields with no truncation or ellipsis. The validated controller passes row
and GlobalText strings unchanged, so overlong text clips at the field edge in
the original movie as well. The native converter inlines the font that the
English `fontconfig.txt` maps `$NormalFont` to (Arial Unicode MS, see
native-gfx.md), so equal clipping is an inference; GFx versus Ruffle text
layout can still differ by a few pixels. No host wrapping, truncation or
movie edit is added: any of these would diverge from the original.

Measured with `native/help` `--scroll-check` on the installed file (lengths
only, no row text recorded): 133 rows, keys at most 13 bytes, descriptions at
most 25, all ASCII, no newlines, so the host's conversion buffers and the
Latin-1 policy are not involved. Each list has 20 renderers. Hotkeys reach
their last position (mode 0: 32 rows, position 12; mode 1: 28 rows,
position 8); the 14 chat rows fit without scrolling. One chat description
field is 2.8 px wider than its 154.2 px field; no hotkey field clips. With
the installed GlobalText headings, the chat tab label measures 130 px in a
99 px button field; the 60 px column headings do not report textWidth in this
runtime. MUScrollingList overrides only the scrollPosition setter, so its
getter is undefined; the check reads `_scrollPosition`. Mouse wheel input
already reaches the movie under the cursor through the shared router
(WM_MOUSEWHEEL to layer mouse kind 3); no new hook was needed.

Hook review: Ctrl+H collides with no recovered menu key (only Ctrl+Z/Ctrl+X
are menu keys), is enabled only after a valid load, and is consumed before the
main movie. The Esc close follows the layer's existing fixed-priority chain.
