# Item mixing and jewels, NATIVE-MIX-001

## Current boundary

The native client now plays MixGoblinSel and MixInventoryFrame, identifies
bounded Mix.bmd recipes, shows rate and zen, and applies delayed offline
mix and Bless/Soul/Life answers to inventory snapshots. `mu-world` and
`mu-client` share this GFx path. The demo server's result is authored: it
never predicts the real server's random outcome. Personal store and repair
are the next slice. No live client or real items were used.

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
Round 1 had no native renders; round 2 renders are listed below.

## Native integration and round 2

`reconstructed/mix/mix_manager.c` adds the following instruction comparisons:

| Client routine | Authored entry point | Scope |
|---|---|---|
| `0x00d07e3f` | `mu_mix_value` | Mix-specific jewel values, ItemValue fallback supplied by the host |
| `0x00d0b2c6`, `0x00d0c374` | `mu_mix_select` | Single-row shortcut, candidate intersection, required-condition count and J/L filters |
| `0x00d0b5d7` | `mu_mix_score` | Ordered quantity consumption, weights, flags, optional leftovers; equal scores retain the earlier row |
| `0x00d0a318`, `0x00d08e38` | `mu_mix_same`, `mu_mix_group_add` | Scalar equality and grouping, class filter -1, no harmony vectors |
| `0x00d096f0`, `0x00d09811` | `mu_mix_values_make` | Value totals and bonus |
| `0x00d0960d` | `mu_mix_first_values` | Last source matching condition 0 supplies summary +0x10 and +0x38 to formula fields |
| `0x00d09366` | `mu_mix_additions_make` | Rate-affecting optional quantities; Item.bmd +0x254 supplied at the lookup boundary |

`scripts/validate_mix_manager.py` executes these instructions against the
same pinned captures. STL allocation, copying and iteration are modelled;
selection, candidate filtering and tie scoring execute. Empty harmony
vector lifecycle is modelled. Grouping supplies a mix-value boundary,
checked separately by executing the actual valuation helper with a
modelled ItemValue fallback. Item.bmd lookups for optional values are
modelled. The native quote adapter composes these helpers; its whole
file-loading/GFx/demo transaction is covered by portable tests and native
renders, not a claim of a complete original-client quote execution.

Round 2 private run: **16,021 comparisons, zero mismatches**. Eight
synthetic families have 2,000 cases each: selection, score plus mutated
quantities, scalar totals, equality, first fields, optional additions,
grouping and mix valuation. Another 21 selection cases traverse every
nonempty installed group, including all 3,009 candidate rows. This is one
synthetic inventory per group, not exhaustive recipe-ranking coverage.
All six new planted mistakes are caught: last-wins ties, first-wins formula
fields, omitted extra kinds 9/10, wrong score weight, wrong duplicate value,
and using shop prices instead of mix values. Together with the repeated
round-1 run: **68,554 comparisons, zero mismatches, 17/17 mutants caught**.
Fifteen portable reconstructed tests and sixteen native mix tests pass.

Review exposed three native transaction bugs: a pending jewel could be
returned by a world click, repeated put/take cycles exhausted the backing
array, and Escape left the mix movie open. Pending requests now own their
jewel, vacant slots are reused, and paired windows close only after the
items can return. The second review also required checked jewel restoration and preserving the
grid vector order when reusing slots; both have regression coverage. Later
checks cover scripted sell/vault mutations while pending, option preservation
through the vault, and reclaiming consumed inventory entries. Review
also exposed the shop-price/mix-value confusion; the valuation helper and
a value-dependent native quote regression correct it.

`native/core/mu_mix.*` loads local Item.bmd/Mix.bmd without exports and
builds scratch summaries. The bounded snapshot adapter refuses nonzero
additional options, L recipes requiring an authoritative class mask,
harmony, unsupported formulas and cost D. Unsupported quotes never enable
the Mix button. Numeric overflow/non-finite expressions are rejected by
the native adapter. The regular Goblin button follows the movie's
MixSystem 1 path; its separate Chaos-weapon system is visibly unavailable.
Other NPC talk results opening manager +0xa8 use the same mix movie.
The invokes and menu lifecycle are static readings of the handler and
local AS2, verified in native renders, not guest-executed window handlers.

The movie uses the reconstructed 8 by 4 grid, page type 4, shared slot
callbacks and the existing item pass. Right click moves an ingredient;
left drag can place a held ingredient; clicking a mix item returns it.
Pending requests lock both inventories. A 160ms offline reply applies
success, failure or rejection once. Success returns an authored snapshot
of the first ingredient at its next level; failure consumes ingredients;
rejection preserves both items and zen. These are explicitly demo-server
policies, not reconstructed server recipes. The mix request is a semantic
offline request, not a recovered wire packet or a live connection.

Bless/Soul/Life eligibility runs the reconstructed predicate. Their C1 31
body is logged locally, with source slot +12. The pending jewel leaves
the cursor until the answer. Demo success increments level or option;
Soul failure resets level, Life failure resets the option, rejection
restores the jewel. The existing renderer receives the new level for glow;
tooltip titles use that level and an authored additional-option line uses
the answer's option. Full option-stat conversion and server reply packets
remain outside this snapshot adapter.

Reproduction with converted movies and libmugfx:

```sh
mu-world --game-root "$MU_GAME_ROOT" --gfx "$MOVIES" --npc \
  --headless --backend gl --frames 62 --every 2 --out-dir "$LOCAL_RENDERS" \
  --npc-script '0:goblin 5:mixopen:0 6:mixadd:7171 7:mixadd:7171 8:mixput:7 9:mixput:23 10:mixput:24 20:mix 32:mixtake:0 33:close 35:mixadd:7182 36:jewel:23:1 44:tipinv:1 50:mixadd:7184 51:jewel:23:1 59:tipinv:1'
```

These numeric items/cells are a local demo example, not embedded inventory
data. `mixadd:CODE:LEVEL` grants an offline item, `mixresult:0|1|2` chooses
rejection/success/failure before a request, and `mixput`/`mixtake` use cells.
`--gfx-open mix` opens the regular machine directly. Missing tables disable
quotes; absent movies keep the optional feature unavailable.

Native world renders, standalone movie checks, reports and gate logs stay
under `~/Documents/mu-mac-tools/native/{renders,scratch}/mix/`. The native
demo shows a recognized recipe, 50 percent rate and 100,000 zen, a pending
request, result, then Soul/Life tooltips. No game data, movies, plaintext,
screenshots or renders are committed.

## Follow-up

PersonalShop, PersonalShopProductList, PersonalShopRegister and
PersonalShopPurchase exist. Registration gate `0x00c00b38` calls
`0x016be0dc`; NPC repair has ConvertRepairGold and the Item.bmd ban.
Their UI requests/results are the next PR. Harmony vectors, cost D,
authoritative class/option feeds, the separate Chaos-weapon system and
real-server packet handling remain bounded gaps. The inventory extension
outside the restored image remains opaque. Protection and encryption/login
packets were not investigated.
