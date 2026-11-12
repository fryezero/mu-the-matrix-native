# UI-WINDOWS-001

## Delivered scope

Five more original movies open in the offline native client. All are
presentation-only. Help's original open/menu route remains unproved; native
Ctrl+H keeps its existing explicit native-policy label. No F1 route was added.

Base `d4af71dd`. Production source is `ec855c57`; validators ran with HEAD
`e5474394`. Later changes are docs only. The final head is in the PR metadata.
The [research and full inventory](../research/client-ui-windows.md) records
134 movies absent from the baseline 31-entry world registry, 5 added here and
129 remaining survey rows. Another 21 names are font/library/HUD entries or
movies already owned by the front-end host. This is not a whole-client window
completion denominator. Untraced original routes remain explicitly untraced.

| Priority | Movie | Original route | Presentation / inert actions |
|---|---|---|---|
| 1 | CommandWindow | D, `0x00efcee8`, manager `+0x134` | Labels and close; all eleven commands disabled and refused |
| 2 | MatchingSelect | N/menu 12, `0x00efcbf0` -> `0x00c73aeb` | Original selector and close; party/guild catalogue buttons inert |
| 3 | PetInventoryFrame | Y/menu 13, `0x00efc559` -> `0x00c739e3` | Five empty pages; equip/move/sort/book/appearance actions inert |
| 4 | GensRanking | B/menu 11, `0x00efcbb6` -> `0x00aae767` | Empty family/rank fixture, no default badge or replicated record |
| 5 | GremoryCase | K/menu 15, `0x00efcc2a` -> `0x00c73abc` | Four empty local tabs; claims and reward actions inert |
| Next | Guildmatching_2024, MatchingParty/Guild | G and MatchingSelect children | Catalogue/search/application providers and exact child lifecycle absent |
| Next | MacroMain/Sub, AutomaticMacro | Z / Home branches | Persistent helper configuration, skill/item inputs and activation owner absent |
| Next | HuntRecord | End branch | Custom root lifecycle, timing and historical provider absent |
| Next | Expanded warehouse | H while warehouse open, manager `+0x104` | Additional StorageInven grid owner absent; H must not open remote storage |
| Unproved | Help | Getter `0x00b6cba2`, manager `+0x120` | Sole direct getter call `0x00b6b744` reads auxiliary rows for EventMapHelper, not an open route |

Menu ID 3 is not the D route: it goes directly to the original dispatcher
sound epilogue. Menu 8 opens SystemMenu, not Help. The main movie has no Help
menu entry. No indirect or other-scene Help route is claimed recovered.

## Controller and sound checks

The new callbacks return before existing NPC, item, social or command
handlers. Unknown actions refuse by default. The production C test covers
115 action/window combinations in both the synthetic host and real Ruffle
movies, unchanged hero/item/potion state, valid and invalid tab values,
page limits, focus, key release, close, readiness and detached sound.

Eight original key-block press/release decisions and the actual menu sound
epilogue are executed under Unicorn. This is bounded key-block evidence,
not recovery of every original world/class/window eligibility predicate.
The offline demo supplies eligibility. Original menu dispatcher sound 25
at `0x00c716f6` fires once per accepted dispatch; D's direct toggle does not
invent a menu sound. Each test host observes eight immediate deliveries,
with no replay after reattachment. AUDIO-002G's legacy CButton owner stays
separate, and its existing release/hold/refusal/mute/decoder regressions pass.
The unowned GFx query `0x00b49b97` remains unwired. Full GFx sound parity is
not claimed; tabs, pages and close get no guessed sound.

## Native journeys and captures

Actual `native/build/mu-client`, offline fixtures, `--no-store --no-audio`,
`MU_GFX_SINGLE_BUFFER=1 MU_GFX_TEST_CLOCK=1`, 1024x768 points / 2048x1536
pixels, canonical read-only Native Data and GFx library. The installed app
was not replaced. These are window/framebuffer-only captures with demo
names. All nine retained proof frames were inspected and checked opaque.
They are local evidence, never committed, and are removed during cleanup.

- Key journey: D, N, B, Y and K each open their movie; Esc closes each.
  Captures at frames 68/78/88/98/108, all closed at 115; quit at 118.
  Actual completed run: 12.89 s. The initial Gens badge capture was superseded
  by the corrected empty fixture in the second journey.
- Mouse journey: Gens close X, MatchingSelect Close, Pet next page to 2/5,
  Pet close X, Gremory Account tab and close X. Final frame shows no window.
  113 frames, 11.02 s runtime / 12.45 s command wall. No casts, pickups,
  item requests or travel occurred in either run.
- Script VKs are numeric. The first argument-parser refusal used letter VKs;
  no client journey ran in that attempt. The portable mu-shell trial reaches
  scene 6 but is a software front end and is not counted as window proof.

| Inspected capture | SHA-256 |
|---|---|
| `command.png` | `a5cc7dd8e2af1ec72a9bb19e560134f75d370de450ae7edee3e736b8a0f0ab66` |
| `matching.png` | `4bb8716ef4efeedfe8911857a2c015491ec88f9014b68089d6762422dc1b3c75` |
| `gens-fixed.png` | `dffd410afb8f18fd3fafb031f157038d866221bb68c25b46ed58b0b2301ef908` |
| `pet.png` | `abcac4aeb26870b31cd632fba8c256bf54a675c9b8d67b60e55365dfdac81ef6` |
| `gremory.png` | `08588fc6a1828531ead1e1fc0eebbf78198070abc4673c01e79519a3cafbe419` |
| `closed.png` | `d03ceb62644ce763590fd31f3ff65f9d754a05ebda8a439a218872cfad226e03` |
| `pet-page2.png` | `230acfc4ed0d3d69bc58f5c1a9c5f76f472b9e0649462aba7b160eb61e4e78ad` |
| `gremory-account.png` | `1a419dfce60251804cc79909b80b4a7a5abab66c365ceb91e11668975d5d6a33` |
| `mouse-closed.png` | `422d7a7482db8935d66e7bbf65561c8db8a6fcb29c75a23f0739ac781a346b43` |

## Checks and wall times

All commands run from the repository root. `nice -n 10`; builds initially
`-j4`, then `-j2` after more than 20 minutes of resource-guard waits, per the
common brief's fallback. Validators and suite runner use two jobs. One heavy
job at a time. No full gate or hosted workflow was run by this lane.

| Check | Result | Wall seconds |
|---|---|---:|
| Final `make -j2` | pass, incremental | 0.85 |
| Graphical client and world builds | pass; final explicit checks both incremental | 0.40 / 0.40 |
| Baseline explicit world build | pass; final freshness check 0.28 s | 21.28 |
| Portable `run_test_suites.py --affected origin/main` | 133 work items; 1,421 tests, 1,163 passed, 258 optional skips, zero failures/errors | 358.4 execution / 414.68 including selection |
| Private `native.tests.test_ui_windows` | 3/3 pass; synthetic and real movies; 9 original instruction checks | 3.79 |
| Private `native.tests.test_audio_ui` | 8/8 pass, including 5,803 original comparisons and installed click decode | 33.23 |
| Affected private validator runner | 12/12 pass, no fail/error/skip, no mutants | 153.86 including selection |
| Repository audit | 2,188 files, zero rejected | 34.01 |
| Key / mouse window journeys | pass | 12.89 / 12.45 |
| Default identity before/after | 92 PNG + 92 dump + 46 report identities | 171.85 |

**8d reduced:** selection exceeds 40 native work items; run the newly added
private UI module, plus the focused UI-audio regressions above. The portable
133-item run includes the shared-symbol consumers under brief 6b: GFx2/3,
Help, input/hotkeys, map overlay, social, layout, session and shell hosts.
No validator or original mutant target changed, so no mutants were rerun.

| Steward validator | Cases / contracts, zero mismatches | Seconds |
|---|---:|---:|
| `validate_app_polish1` | 752 | 24.8 |
| `validate_app_polish2` | 1028 | 4.3 |
| `validate_app_polish4` | 10485 | 48.0 |
| `validate_app_polish7` | 5120 | 2.4 |
| `validate_audio_callers` | 5528 | 7.8 |
| `validate_audio_domains` | 2544 | 29.3 |
| `validate_audio_items` | 3000 | 4.6 |
| `validate_gfx3` | 80 window cases; loader/menu/skill contracts | 6.8 |
| `validate_map_polish` | 876 | 0.8 |
| `validate_movement` | 6614 | 72.6 |
| `validate_render_effects16` | 424 | 4.7 |
| `validate_worlds_fog` | 4044 | 10.3 |

Steward validators: validate_app_polish1,validate_app_polish2,validate_app_polish4,validate_app_polish7,validate_audio_callers,validate_audio_domains,validate_audio_items,validate_gfx3,validate_map_polish,validate_movement,validate_render_effects16,validate_worlds_fog.
Ran at `e5474394`, source `ec855c57`; no compiled input changes afterward.
Use canonical `private-env.sh` from the repository root. Keep the symbol-level
fallback `validate_movement`; it was selected and passed rather than dropped.

## Default identity and binary provenance

Both explicit world builds precede the sweep. Before is detached `d4af71dd`;
after has source `ec855c57`. SHA-256:

- Before: `4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.
- After: `b681255a6c1b0718a7885fffb251999b0d5af7cbdd7931cecd8ca0e7cc75d10e`.

October 22: 14 maps, 28 PNG / 28 dump / 14 normalised report identities,
34.06 s before and 22.11 s after. DATA-ACQ-002: 32 maps, 64 PNG / 64 dump /
32 normalised report identities, 49.84 s before and 65.43 s after.
Default draw only, no draw_all, no live_time. Report output/binary paths are
normalised; pixels and dumps are compared byte for byte. An old canonical
manifest had stale input paths and failed before any render; the resolved
existing October 22 and DATA-ACQ-002 manifests were then used. No baseline
render was repeated. No original-image or performance acceptance is claimed.

## Limits, next and cleanup

No original Help route, replicated family/pet/reward data, matching catalogue,
requests, item/character changes, helper configuration or live authority.
English labels are authored presentation fixtures; full localisation, every
window size and original context predicates are unproved. The remaining
129 survey rows, legacy aliases, route gaps and inferred data needs are
listed individually in the research inventory. Next work should recover
one child/controller lifecycle and its fixture provider before binding it.

No original client, protection module, live memory, installed Wine app,
staged Wine app or installed Native Preview was touched. No README work.
No raw assets, screenshots, data rows or input symlinks are committed.

Checkpoint commits `10311bf5` and `e5474394` were pushed with WIP handoffs;
`ec855c57` preserves the source. Finish is PR-ready for the merge steward,
not merged. The owner deadline was stop by 02:30 on 2026-11-12.
Cleanup removes lane renders/scratch, the detached baseline tree, build
outputs, this worktree and its local branch. No new input needs retaining.
