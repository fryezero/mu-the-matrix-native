# Item mixing and jewels, NATIVE-MIX-001

## Current boundary

This is a verified rule-library slice, not a completed native mix feature.
`reconstructed/mix` has authored C for scalar mix-item summaries, ingredient
conditions, quantities, rate expressions, A/B/C zen-cost modes,
Bless/Soul/Life eligibility and the unencrypted jewel request body.
Native inventory/GFx integration, recipe ranking, demo replies, personal
store and repair flows are still open. No live client was used.

## Inputs and method

The installed main.exe SHA-256 was verified again on 2026-10-22:
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
The validator pins the complete existing private captures:

- Text capture09, VA `0x00401000`, SHA-256
  `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
- Second image section run10, VA `0x01a7c000`, SHA-256
  `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.

`scripts/validate_mix.py` uses `client_ui_machine.Machine`, Unicorn 2.1.4
and Capstone 5.0.9, with code allowlists and undefined-read checks. The
actual routines and scalar helpers execute. Modelled boundaries are GFx
manager/window getters and visibility, memset, empty-vector clears,
readiness in the quote wrapper tests after its independent comparison,
and the jewel sender's environment-eligibility input, packet-builder,
transport and inventory lookup. That lookup returns no item, excluding
the potion-sound tail. No socket call executes. The rate expression and
CRT conversion execute, using the non-FISTTP path with `[0x0bdcb280]=0`.
An authored caller stores the formula's x87 return. Captures are absent
from a fresh clone; no bytes, decoded tables or exports are committed.

## Recovered rules

| Client routine | Authored entry point | Bounded result |
|---|---|---|
| `0x00ad50b4` | `mu_jewel_allowed` | Bless/Soul/Life eligibility |
| `0x00960420` | `mu_jewel_request` | C1 length 6, opcode 31, source/destination/mode; source index adds 12 before byte conversion; positive throttle suppresses the send, otherwise it becomes 10 |
| `0x00d07528` | `mu_mix_source_make` | First 76 scalar bytes of the 100-byte summary, without harmony vectors; ItemValue is supplied |
| `0x00d06e3c` | `mu_mix_matches` | Summary against one 72-byte condition |
| `0x00d05394` | `mu_mix_repeats` | Repeat count from quantities/minima |
| `0x00d04fc3` | `mu_mix_ready` | Ordered quantity consumption and leftover rule |
| `0x00d051b8` | `mu_mix_extra` | Optional ingredient selectors 1 through 11 |
| `0x00d09bbb`, `0x00d09c9b`, `0x00d09d8c` | `mu_mix_formula` | Binary32 expression, precedence, grouping, truncation, state variables |
| `0x00d098da` | `mu_mix_rate` | Cap, additive ingredients, charm subtraction, unsigned clamp |
| `0x00d099f2` | `mu_mix_cost` | A/C: base times repeats; B: rate times base times repeats, 32-bit wrap |

Bless accepts levels 0..5, Soul 0..8. Their shared path checks the mix window
and several exclusions. Life checks option below 4 and period zero, with
direct kind branches that bypass some Bless/Soul exclusions. The port
preserves this asymmetry. Most ingredient flags are required subsets;
bit `0x40` requires equality. Readiness mutates summary `+0x24` even on
rejection, so hosts must use scratch summaries before a server answer.

The native formula API rejects missing operands, unmatched groups, stray
closing tokens, trailing operands and unsupported tokens. This is native
hardening: the client assumes well-formed table expressions. Finite token-7
conversion has defined CVTTSS2SI overflow behavior, INT_MIN. Non-finite
expressions, zero divisors and more than 32 tokens are outside the adapter's
accepted domain. Harmony summaries are rejected. Cost D is unimplemented;
unsupported cost modes return zero and must not be treated as free quotes.

## Verification

Private run, 2026-10-22: **52,533 comparisons, zero mismatches**.

| Family | Cases |
|---|---:|
| Scalar source | 3,024 |
| Jewel eligibility | 8,048 |
| Jewel request/throttle | 2,000 |
| Ingredient condition | 2,000 |
| Repeat | 2,000 |
| Readiness and mutated quantities | 2,000 |
| Extra selectors | 2,378 |
| Expressions | 2,000 |
| Rate/cost wrappers | 2,000 |
| Installed conditions over synthetic summaries | 15,047 |
| Installed readiness, complete/one-removed summaries | 6,018 |
| Installed repeats | 6,018 |

The installed pass covers all 3,009 rows in 22 Mix.bmd groups, SHA-256
`44e2e3451e526dcaac72e28f15f00cc06573030997d0316e0156e381a338b498`,
using NATIVE-DATA-001's verified decode-unit schedule. These are synthetic
summaries built from installed conditions, not player inventories or a test
of recipe ranking. All **11 planted mistakes** are caught: jewel level,
missing flag, readiness, cap 99, cost-B multiplier, special classification,
division, truncation, missing extra kinds 6..11, jewel opcode, and treating
kind `0x37` as compound equipment. Twelve portable worked examples include
malformed expressions, non-finite intermediates and numeric boundaries.

Review found that the first 22,048-case corpus missed division, token 7 and
accepting extra kinds 6..11, and that malformed formulas passed. Shape
validation, added cases and three additional mutation families address
those findings. The earlier count alone did not cover those branches.
The second review found that kind `0x37` wrongly set summary `+0x44` and
that token 7 concealed a non-finite intermediate. The compound predicate
now uses helper `0x00cd1dfc`'s explicit kind set. The corpus includes all 256 kind
and sub-kind values under two states each, and mutant 11 reproduces the
`0x37` defect. The formula adapter rejects non-finite intermediates before
conversion while retaining INT_MIN for finite out-of-range values.

```sh
python3 -m unittest discover -s reconstructed/mix -p 'test_*.py' -v
python3 scripts/validate_mix.py --text "$MU_CLIENT_TEXT" --data "$MU_IMAGE_DATA" \
  --game-root "$MU_GAME_ROOT" --cases 2000 --mutations --output /tmp/mix-validation.json
```

Use the repo's pinned Python requirements. Report, private disassembly and
AS exports are local under `~/Documents/mu-mac-tools/native/scratch/mix/`.
The full local macOS gate exited 0 on the resolved tree rebased onto
`bb27f8a`; its log is `scratch/mix/local-macos-ci.log` under mu-mac-tools/native.
The requested `~/Documents/mu-mac-tools/native/renders/mix/` exists but
has no native mix renders yet.

## Next work and static readings

- Port candidate filtering/ranking `0x00d0b2c6`, tie score `0x00d0b5d7`,
  grouping `0x00d08e38` and aggregation `0x00d09366`/`0x00d096f0`. Selecting
  the first ready row would be an unverified replacement for that manager.
- Wire MixGoblinSel and MixInventoryFrame through GFx. NPC result 3 opens
  MixGoblinSel. MixInventoryFrame is 8 by 4, page type 4 at manager `+0xa8`,
  type 5 at `+0xb8`. Its AS calls `onClickbtnMix` and exposes InitText,
  SetText, SetMixType, SetVisibleMixButton and shared slot callbacks.
  These are static readings, not native UI verification.
- Trace mix/jewel answers and apply demo-server snapshots only after an
  answer. Item glow already exists through RenderItem3D/RenderObjDraw in
  `world_gfx_game.c`; no renderer change made here.
- Personal-store movies exist: PersonalShop, PersonalShopProductList,
  PersonalShopRegister, PersonalShopPurchase. Registration gate
  `0x00c00b38` calls `0x016be0dc` with item-specific refusals. These remain
  static readings; registration/open/close/replies are unimplemented.
- Repair cost and ban already exist in reconstructed/price and
  reconstructed/data. NpcShop repair-button requests/results remain unwired.
- Harmony vectors and the harmony table are needed for cost mode D.

The inventory click path's earlier call outside the restored image remains
opaque. No protection module, encryption/login packet, real item or zen
mutation was investigated or performed.
