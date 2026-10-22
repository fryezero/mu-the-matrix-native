# NATIVE-SOCIAL-001 WIP handoff

Branch: `claude/native-social`, worktree `~/Documents/mu-worktrees/native-social`.
Issue: https://github.com/fryezero/mu-the-matrix-native/issues/143.
Do not open a PR or merge this WIP as a finished milestone. The original task authorizes publishing only after
the implementation is complete, rebased, reviewed and local macOS CI passes. The owner explicitly authorizes
the fallback used here: commit WIP, write this note, push the branch without a PR when budget runs out.

Read `~/Documents/mu-mac-tools/native/BRIEF-wave4.md`, its common brief and repo AGENTS/CONTRIBUTING.
Do not touch protection/encryption/login, `mtmOriginal`, owner client processes or parallel agents' modules.
The Preview launcher/client PIDs 2818/2826 were already running and were left untouched. No live game was used.
No Preview rebuild/install has been performed for this WIP. Do not claim one.

## Implemented and tested

- `reconstructed/social`: party request key/block branch, party record fields/state/HP-MP clamping, marker
  builder, trade item/zen/lock/result receives, friend rows, whisper receive/block behavior.
- `scripts/validate_social.py`: **7,000 actual-instruction comparisons, zero mismatches, 10/10 planted mistakes**.
  See `docs/research/client-social.md` for whole-routine versus slice boundaries. Do not call the party HP/MP
  count/name loop Unicorn-verified; only its clamp slice executes. Five reconstructed portable tests pass.
- `native/core/mu_social`: OFFLINE demo policy and session, requests/accept/decline/leave/kick, friend edits,
  trade timing/zen, scripted health. Party membership survives world travel; missing players become out of view.
- `native/world/world_gfx_social`: actual winParty HUD, Tab markers after map clearing, Trade's two grids,
  inventory reservation/cancel/atomic commit, friends/local room/whispers. Quoted/backslash/control/Unicode
  messages decode correctly. The trade draw decoder now includes all item-code bits.
- Three native regression tests pass. They exercise party policy, two-world persistence, stationary map
  refresh, actual inventory offers/cancel/result, multi-cell removal, reopens, late capacity changes, local
  messenger callbacks including quoted text and whispers. Native strict client/world builds passed before rebase.

The capacity-race fix commits an atomic GFx inventory exchange through `mu_social_session.trade_commit`
before changing zen/results. The layer saves/restores inventory/grid/reservations if an insertion fails.
The callback is cleared when its host closes. It is demo inventory plumbing, not original server policy.

## Required work before a completion PR

Round 2 specification review still has these unresolved findings:

1. **P1 original party actions are missing.** Current request/accept/leave/kick actions are authored demo
   policy. Reconstruct and validate the client's outbound serialization and relevant dialog callbacks, feed
   those requests into the offline server, and keep server answers labelled demo. The incoming `40` receive
   alone does not establish the actions. Static leads from the pinned text:
   - Callback dispatcher around `0x00c774cf` matches `onLeave`, extracts `name`, calls `0x00c7ad4e`.
   - `0x00c7ad4e` chooses the leave/kick confirmation text and popup. Its popup result path needs tracing.
   - `0x00c7a9..0x00c7ab22` and `0x00c7ab25..0x00c7ac4a` deal with named party members, permissions and dialogs.
   - Party request receiver `0x01270d06` stores key at window +0x3c, tests block, invokes popup `0x00c0a9c8`.
   - Do not confuse opcode `c3` in the packet builder near `0x00c79c58` with network C3 encryption; it is an
     opcode argument to a C1 envelope, and may be another party operation. Trace intent before using it.
2. **P2 original messenger handlers are missing.** Current local echo is only the movie API exercised.
   Reconstruct original room/message receive and callback logic, then connect it to the offline transport.
   Leads: callback dispatch `0x00b79108..0x00b791bf` matches AddChatText, converts the text, reads UI ID and
   calls `0x00b7630c`; that routine calls room manager `0x009c4a58`, then refresh `0x00af0ce9`.
   AddChatText GFx wrappers are `0x00b724b6` and near `0x00b766d7/0x00b7676f/0x00b767c2`.
   RequestChatUser dispatch starts `0x00b791c4`. Actual `FriendWindow` callback is `[text, uiID]`.
3. Mail/invite/minimize/persistent lists, full item options/dimensions/tradeability and original zen input
   dialog remain open. Incoming demo items are 1 x 1; headless no-GFx offers are a separate two-item fixture.

Round 1 bugs (UAF/reset on travel, static-marker refresh, inventoryless trade, unused room, missing result
notice, overclaimed clamp coverage) were fixed. Round 2 correctness bugs (capacity race, item code bits,
missing-player visibility, quoted text) were fixed after that staged review and regression-tested. A fresh
review must include those later changes and the remaining reconstruction, with a new delegated round ID.
Review round IDs use `native-social-{standards,spec}-r1/r2`; each new review must be a new delegate task.

## Local tools and evidence

- Client data root, read-only:
  `~/Library/Application Support/CrossOver/Bottles/MuMatrixKit/drive_c/MuTheMatrix`.
- Captures: main checkout `evidence/x86-text-capture-09/client-text.bin` and
  `evidence/image-data-run10/data-capture-10/client-image-data.bin`; hashes are pinned in validator/note.
- Scratch: `~/Documents/mu-mac-tools/native/scratch/social/`. `inspect_social.py` offers bounded
  disassembly and string xrefs. `party*.txt`, `leave.txt`, `trade*.txt`, `f_*.txt` preserve exploratory reads.
  These are private and must not be committed. `as/` has the four movies' ActionScript.
- Python with Unicorn, Capstone, black and clang-format:
  `~/Documents/mu-mac-tools/native/scratch/social/venv/bin/python`.
  Shared `tools/.venv` is Python 3.9 without Unicorn; use it for portable tests/local CI.
- Validator result: `scratch/social/validate-final.json` and `.log`, 7,000/0/10. It has not changed since that
  run; later fixes are in the native integration only.
- Movies: `scratch/social/movies`, all locally converted, none committed. Use `MU_GFX_SINGLE_BUFFER=1` for
  sparse headless captures. Libmugfx borrowed read-only from
  `~/Documents/mu-worktrees/native-gfx3/native/gfx/mugfx/target/release/libmugfx.dylib`.
- Lang directory: `~/Documents/mu-mac-tools/native/scratch/lang`.
- Renders: `~/Documents/mu-mac-tools/native/renders/social/checked-trade/frame-0030.png` shows
  both offers/zen, `checked-map/frame-0030.png` shows stationary Shopkeep marker after Tab,
  `checked-messenger/frame-0030.png` shows friends/room/whisper, `checked-travel/` shows the two warps.
  Renders predate the final atomic-capacity and escaped-text fixes; those have synthetic regression evidence.

Useful commands:

```sh
tools/.venv/bin/python -m unittest discover -s native/tests -p test_native_social.py -v
~/Documents/mu-mac-tools/native/scratch/social/venv/bin/python scripts/validate_social.py --cases 500 --mutations --output /LOCAL/result.json
make -C native -j4 client world
bash scripts/local-macos-ci.sh
```

Local CI/rebase/push results are recorded below by the finishing run. Preserve both sides of shared docs and
the NATIVE-POLISH-001 world travel work from PR #144. No hosted workflow dispatches.

Rebased onto `ac82b33` including PRs #144/#145. The first local CI run passed tests and native/live-reader
builds, then failed its audit because this note used absolute home paths. Those paths now use `~/`.
