# APP-POLISH-009

The HUD and the sixteen task panels now fit the native 640x480 minimum while
retaining the original alignment. CharacterInfo reads the same joined demo
record as the HUD. Windleaf's existing authored level 320 and 318 free points
now survive the fixture-to-session seed; no new stat formula or allocation
operation is added. Missing derived display data remains a dash.

## Recovered rules and implementation

Pinned text SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`;
data SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
Full evidence and the native policy distinction are in
[client-ui-layout.md](../research/client-ui-layout.md).

- Collection resize `0x00ac09b2..0x00ac0a38` visits every non-null handler;
  `0x00aae4ae..0x00aae506` updates its viewport and calls `SetWindowSize`.
  Unicorn compares 60 empty/null/populated collection cases.
- Manager `0x00acb333..0x00acb426` resizes three collections and stores
  640/width and 480/height rates. Registry `0x00ac4a79`, creator `0x00ac9edc`
  and scale setter `0x00aaebca` provide alignment and fixed low-height scales.
- Original `MUComponent.SetWindowSize` aligns inventory/PetInventory right,
  Warps left, master/fourth trees centrally and fifth tree left-centre.
  The original HUD floors its horizontal centre and bottom anchor. Map scale
  is 83% below 700 and 100% otherwise, with the original centred 800x600 mask.
- Original fixed scales overflow 640x480: inventory y=40, height=530.35;
  master tree (-96.6,-80.35), size 833.3x640.7; HUD x=-118, width=874.95.
  The native adaptation caps scale, fits panels above the measured HUD top,
  clamps positions, and reapplies original alignment after shrinking. Resize
  restores original scales before fitting. This is native policy, not a claim
  of original pixel parity at the native minimum.
- `world_gfx` copies name/class, level/master level, points, experience,
  base/added stats, existing derived fields, money and speed from the bound
  session. HP/MP/SD/AG continue through the existing session-vitals path.
  The independent progression demo feeds CharacterInfo only without a session.
  Authored fixture name/level/points reach the development-only seed.
- The original CharacterInfo table masks HP/MP/SD/AG rows 26/27/34/35 out for
  every current class. Tests check the enabled rows through actual `SetName`
  calls and leave those masks intact. Four joins retain level 1; Windleaf
  retains its existing level 320. Decorative selection-list levels are not
  reinterpreted as new stat inputs.

Merged main through `c35458a011cbb6b74d1fdfb0fbf5a6ce68699069`, including
UI-WINDOWS-001 #372, ITEMS-UI-001 #379, UI-WINDOWS-002 #380 and
RENDER-ACTORS-004 #381. The actor merge required only shared status resolution,
preserving both lanes; no authored UI or fixture source changed.
The #380 show-route conflict preserves HuntRecord's open/close and
QuestSummary/Party's openWindow/closeWindow routes. Both status entries survive. No authored icon/cursor, item-table,
effect, actor, world-renderer, Muun or audio change. Shared manifest changes
add APP-POLISH-009's row and preserve all upstream rows.

## Checks

Checks ran from the repository root, nice 10, at most make -j4 and two runner
workers. Wall times below exclude the brief's resource waits. The full lane
gate was not run. Canonical private environment was sourced from
`~/Documents/MTM/mu-mac-tools/native/private-env.sh`; Native Data stayed read-only.

| Check | Result | Wall seconds |
|---|---|---:|
| Root build before #380 | Pass | 0.799 |
| UI-002 root build, `1f42e17b` | Pass | 4.795 |
| Client/world build before #380 | Pass | 14.180 |
| UI-002 client/world build, `1f42e17b` | Pass | 7.834 |
| Final root / client-world builds, `1d709542` | Pass | 11.457 / 10.322 |
| Upstream control world rebuild | Pass | 6.748 |
| Reduced private checks before #380, `7e97044e` | 19/19 methods pass; no skips | 147.640 |
| Final reduced private checks, `1f42e17b` | 23/23 methods pass; no skips | 141.883 |
| Actor/session private checks, `1d709542` | 7/7 pass; includes five demo profiles; no skips | 110.348 |
| Own and post-merge validator selection | 27 own; 107 since prior tested `6ea82f67`; union 107 | 30.926 + 34.038 |
| Selected private validators, `7e97044e` | 107 pass, zero fail/error/skip; 1,229,800 reported cases plus two rows without a unified case total | 1251.812 |
| #380 affected selection / rerun, `1f42e17b` | All 13 changed-input rows pass, zero fail/error/skip | 33.550 + 112.208 |
| #381 affected selection / rerun, `1d709542` | All 25 changed-input rows pass, zero fail/error/skip | 63.952 + 223.945 |
| Changed-target compiled mutants, `6ea82f67` | 4,668 cases; zero mismatches; 10/10 mutants caught | 6.688 |
| Affected portable tests, `66f4bba7` | 1,532 tests: 1,263 passed, 269 skipped; zero failures/errors | 411.697 |
| Post-#380 affected portable tests, `1f42e17b` | 1,455 tests: 1,184 passed, 271 skipped; zero failures/errors | 392.839 |
| Post-#381 portable tests, `1d709542` | 1,525 tests: 1,264 passed, 261 skipped; zero failures/errors | 448.875 |
| Pre-#380 repository audit | 2,222 staged files, zero rejected | 29.293 |
| Post-#380 repository audit | 2,226 staged files, zero rejected | 17.138 |
| Final post-#381 repository audit | 2,233 staged files, zero rejected | 18.450 |
| Final endpoint captures | 640x480 and 2560x1440, opaque, inspected bytes unchanged | 15.533 |
| Initial default identity, including explicit world rebuild | 92/92 PNGs, 92/92 OBJECT/light dumps, 46/46 normalized reports identical | 137.031 |
| Post-#380 after-only refresh, including explicit world rebuild | Same 92/92 PNGs, 92/92 dumps, 46/46 reports; original before files retained once | 62.759 |
| Post-#381 after-only refresh, including explicit world rebuild | Same 92/92 PNGs, 92/92 dumps, 46/46 reports; original before files retained once | 62.468 |

The new validator separates 60 original resize cases from 4,096 native panel-fit
and 512 native HUD-fit invariant cases. Mutants caught: grow, width, height,
right, bottom, left, top, HUD width, HUD bottom and HUD floor. Each altered C
header compiled successfully. The fit header, validator and original helper are
unchanged since that one mutant run; unchanged mutants were disabled later.

**8d reduced:** canonical private selection exceeded 40 work items (164/164 at
the first selection; the initial portable selection includes 162 native modules).
Final private modules: `test_app_polish9`,
`test_app_polish5.PrivateGroundSkill`, `test_ui_windows`, and the incoming
`test_items_ui`; the UI run also includes `test_ui_windows2`. The actor integration additionally
runs DemoOwnership, `test_actor_composites` and `test_actor_recipes`. New module
coverage includes five demo profiles, 272 visible
panel/size/backing-scale combinations, 48 open-panel resize checks, sixteen real
pointer-close deliveries, seventeen map-layout checks and original resize code.
Quest/tree close probes record controller delivery; their recording host does
not implement the owning controllers. Separate presentation tests cover the five #372 windows'
controller firewall. The fixture test builds and privately copies
its client binary. The 6b seed-consumer closure is selected: session core, combat,
map overlay, characters, party, monsters, skills, items and audio.

The matrix covers 640x480, 800x600, 1024x600/699/700/768, 1280x720/800/1024,
1366x768, 1440x900, 1600x1000, 1680x1050, 1920x1080 and 2560x1440; Retina
backing scale 2 at both endpoints. It covers inventory, CharacterInfo, imprint,
master/fourth/fifth trees, Warps, four quest panels and all five #372 panels.
The native viewport is continuously resizable; this samples its supported range
and common aspects, not an exhaustive original display-mode list.

Development findings: the ownership test exposed and fixed the real missing
Windleaf seed metadata. Earlier log-spelling and masked-vital-row assertions were
corrected against the actual original feed. One early 1024x699 renderer startup
returned 1 without stderr; an isolated two-backing-scale rerun and both final
full matrices passed. Its cause remains unproved.

## Captures and default identity

Final native framebuffer-only captures show demo Ironclad, inventory and
CharacterInfo with the HUD, at a fixed clock. Both are opaque. At the minimum,
all panel controls and the full HUD remain inside the viewport and the panels
clear the HUD. At the largest size the original scale is retained. Inspected
both PNGs; all later refreshes, including #380/#381, have the same hashes.

| Capture | Size | SHA-256 |
|---|---|---|
| `small.png` | 640x480 | `479d107cd7b3c499e732c015b8906395376816386647b4d126b73e658c21112d` |
| `large.png` | 2560x1440 | `2b4aa4da31eea1fb6a6c3e514eb1caea70e598ad7d624240e99b17a40877e1ae` |

Local proof location before required cleanup:
`~/Documents/MTM/mu-mac-tools/native/renders/app-polish-009/`.
Captures use `mu-client --session native/client/demo-session.txt --headless
--backend gl --no-audio --no-store --progress --frames 115 --every 1000`, the
canonical Native Data gfx/objects and lang directories, `MU_GFX_TEST_CLOCK=1`
and `MU_GFX_PUBLIC_DEMO=1`. The authored script selects group 0/server 0,
uses demo text, joins row 1 at frames 42/54, then opens C at 80 and I at 85.
Only the two endpoint width/height arguments differ.

The default sweep, no draw_all/live_time, uses the 14-view October 22 tour and
32-view DATA-ACQ-002 tour. The private October 22 manifest's obsolete tools-path
prefix was normalized before rendering; shared inputs were not changed.
All 92 PNG pairs and 92 OBJECT/light dump pairs are byte-identical. All 46
reports are identical after only binary/output-path normalization. Before
numbers were taken once. Only after files were refreshed for #380/#381's compiled
world/GFx/core changes. This is native repeatability, not live-client parity.

Both trees explicitly built `world` for the 626abce1 baseline. After the latest integration and
its tests, the branch explicitly rebuilt client/world, then another
`make -C native -j2 world` took 0.268 s before refreshing only the after files.
The final hashes are distinct:

- Control, main `626abce1`: `0486f35e813b641f2500df6b0107515c33d3fb37d2cc3683005c8b91b08b10ef`.
- Branch: `0dc7137ef1ecd90ef392ad16efa7ba38bb291f61e39ffd409f90e4ce2f8023bc`.

The initial sweep took 136.658 s; outer command 137.031 s. The final after-only
refresh took 62.142 s; outer command 62.468 s. Portable runner post-selection
walls were 354.7 s initially, 299.5 s after #380 and 393.7 s after #381;
outer commands include selection.

## Steward validators

The combined evidence is 108 passing rows, 1,231,227 reported cases plus two
rows without unified totals. Post-build selectors retain every fallback row.
Latest tested heads: 25 rows at `1d709542`, four UI rows at `1f42e17b`, 79 rows
at `7e97044e`; the latter compiled inputs are unchanged by the later merges.
Use the canonical private environment and validator cache. No row needs new
mutants unless its checks or compiled mutant targets change.

Steward validators: validate_actor_composites,validate_actor_recipes,validate_app_polish1,validate_app_polish2,validate_app_polish4,validate_app_polish7,validate_app_polish9,validate_audio_callers,validate_audio_charsel,validate_audio_combat,validate_audio_domains,validate_audio_items,validate_audio_objects,validate_charsel_items,validate_charsel_world,validate_combat,validate_gfx3,validate_icarus,validate_icarus_c2,validate_inventory_fx,validate_item_callers,validate_item_hiddenmesh,validate_items,validate_items_ui,validate_login_world,validate_map_polish,validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_muun_passes,validate_muun_visual,validate_object_render,validate_path,validate_render_effects,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_render_effects13,validate_render_effects14,validate_render_effects15,validate_render_effects16,validate_render_effects17,validate_render_effects18,validate_render_effects19,validate_render_effects20,validate_render_effects21,validate_render_effects22,validate_render_effects23,validate_render_effects24,validate_render_effects25,validate_render_effects27,validate_render_effects28,validate_render_effects3,validate_render_effects4,validate_render_effects5,validate_render_effects6,validate_render_effects7,validate_render_effects9,validate_render_worlds_a,validate_session_party,validate_skill_fx,validate_terrain,validate_terrain_remaining,validate_viewport_monsters,validate_world_fidelity,validate_world_light_name,validate_world_particle_consumers,validate_world_tile_folder,validate_worlds_121,validate_worlds_after,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_worlds_b,validate_worlds_d,validate_worlds_e,validate_worlds_f,validate_worlds_fog,validate_worlds_g,validate_worlds_g2,validate_worlds_g3,validate_worlds_h,validate_worlds_i,validate_worlds_inner,validate_worlds_inner2,validate_worlds_j,validate_worlds_k,validate_worlds_karutan,validate_worlds_l,validate_worlds_m,validate_worlds_n,validate_worlds_o,validate_worlds_p,validate_worlds_p2,validate_worlds_q,validate_worlds_q2,validate_worlds_r,validate_worlds_r2,validate_worlds_raklion,validate_worlds_s,validate_worlds_s2,validate_worlds_s3,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3

| Validator | Reported cases | Wall seconds | Tested head |
|---|---:|---:|---|
| `validate_actor_composites` | 1427 | 12.5 | `1d709542` |
| `validate_actor_recipes` | 1669 | 148.3 | `1d709542` |
| `validate_app_polish1` | 752 | 17.5 | `1d709542` |
| `validate_app_polish2` | 1028 | 5.2 | `1d709542` |
| `validate_app_polish4` | 10485 | 44.0 | `1d709542` |
| `validate_app_polish7` | 5120 | 1.9 | `1f42e17b` |
| `validate_app_polish9` | 4668 | 4.7 | `1f42e17b` |
| `validate_audio_callers` | 5528 | 4.7 | `1d709542` |
| `validate_audio_charsel` | 5968 | 5.3 | `7e97044e` |
| `validate_audio_combat` | 19548 | 18.9 | `1d709542` |
| `validate_audio_domains` | 2544 | 20.6 | `1d709542` |
| `validate_audio_items` | 3000 | 3.5 | `1d709542` |
| `validate_audio_objects` | 4000 | 3.8 | `1d709542` |
| `validate_charsel_items` | 8817 | 6.6 | `1d709542` |
| `validate_charsel_world` | 1200 | 3.4 | `7e97044e` |
| `validate_combat` | 496 | 1.3 | `7e97044e` |
| `validate_gfx3` | not reported | 6.5 | `1f42e17b` |
| `validate_icarus` | 5240 | 37.2 | `7e97044e` |
| `validate_icarus_c2` | 8400 | 13.9 | `1d709542` |
| `validate_inventory_fx` | 8017 | 8.4 | `1d709542` |
| `validate_item_callers` | 6013 | 1.3 | `1d709542` |
| `validate_item_hiddenmesh` | 116281 | 541.5 | `7e97044e` |
| `validate_items` | 444 | 3.8 | `7e97044e` |
| `validate_items_ui` | 8517 | 9.6 | `1d709542` |
| `validate_login_world` | 1200 | 4.7 | `7e97044e` |
| `validate_map_polish` | 876 | 0.5 | `1f42e17b` |
| `validate_meshdraw` | 14619 | 109.9 | `7e97044e` |
| `validate_model_edge` | 954 | 167.5 | `7e97044e` |
| `validate_model_light` | 1433 | 6.3 | `7e97044e` |
| `validate_movement` | 6614 | 89.8 | `1d709542` |
| `validate_muun_passes` | 1361 | 1.4 | `7e97044e` |
| `validate_muun_visual` | 912 | 1.3 | `7e97044e` |
| `validate_object_render` | 1984 | 4.2 | `7e97044e` |
| `validate_path` | 4719 | 31.7 | `7e97044e` |
| `validate_render_effects` | 660 | 1.6 | `7e97044e` |
| `validate_render_effects10` | 154 | 0.7 | `7e97044e` |
| `validate_render_effects11` | 176 | 0.5 | `7e97044e` |
| `validate_render_effects12` | 64 | 0.5 | `7e97044e` |
| `validate_render_effects13` | 180 | 0.8 | `7e97044e` |
| `validate_render_effects14` | 660 | 1.8 | `7e97044e` |
| `validate_render_effects15` | 509 | 0.6 | `7e97044e` |
| `validate_render_effects16` | 424 | 4.2 | `1d709542` |
| `validate_render_effects17` | 618 | 6.6 | `1d709542` |
| `validate_render_effects18` | 540 | 1.1 | `1d709542` |
| `validate_render_effects19` | 400 | 0.9 | `1d709542` |
| `validate_render_effects20` | 148 | 0.2 | `7e97044e` |
| `validate_render_effects21` | 267 | 0.2 | `7e97044e` |
| `validate_render_effects22` | 202 | 4.7 | `7e97044e` |
| `validate_render_effects23` | 1174 | 5.5 | `7e97044e` |
| `validate_render_effects24` | 226 | 3.4 | `1d709542` |
| `validate_render_effects25` | 202 | 7.9 | `1d709542` |
| `validate_render_effects27` | 424 | 0.9 | `7e97044e` |
| `validate_render_effects28` | 630 | 3.9 | `1d709542` |
| `validate_render_effects3` | 720 | 1.6 | `7e97044e` |
| `validate_render_effects4` | 1920 | 12.1 | `7e97044e` |
| `validate_render_effects5` | 1190 | 6.5 | `7e97044e` |
| `validate_render_effects6` | 1000 | 2.3 | `7e97044e` |
| `validate_render_effects7` | 596 | 2.6 | `7e97044e` |
| `validate_render_effects9` | 304 | 1.5 | `7e97044e` |
| `validate_render_worlds_a` | 9000 | 15.0 | `7e97044e` |
| `validate_session_party` | 200 | 1.2 | `7e97044e` |
| `validate_skill_fx` | 660 | 1.2 | `7e97044e` |
| `validate_terrain` | 583500 | 431.3 | `7e97044e` |
| `validate_terrain_remaining` | 2147 | 4.5 | `7e97044e` |
| `validate_viewport_monsters` | 1963 | 6.8 | `1d709542` |
| `validate_world_fidelity` | 200 | 0.2 | `7e97044e` |
| `validate_world_light_name` | 304 | 0.5 | `7e97044e` |
| `validate_world_particle_consumers` | 900 | 1.5 | `7e97044e` |
| `validate_world_tile_folder` | 5700 | 44.7 | `7e97044e` |
| `validate_worlds_121` | 4000 | 3.1 | `7e97044e` |
| `validate_worlds_after` | 13424 | 16.4 | `7e97044e` |
| `validate_worlds_after2` | 32216 | 32.2 | `7e97044e` |
| `validate_worlds_after3` | 10212 | 12.7 | `7e97044e` |
| `validate_worlds_after4` | 9181 | 20.7 | `7e97044e` |
| `validate_worlds_after5` | 6000 | 20.1 | `7e97044e` |
| `validate_worlds_after6` | 7300 | 84.8 | `7e97044e` |
| `validate_worlds_b` | 4000 | 3.6 | `7e97044e` |
| `validate_worlds_d` | 2400 | 4.3 | `7e97044e` |
| `validate_worlds_e` | 4840 | 18.8 | `7e97044e` |
| `validate_worlds_f` | 1818 | 0.5 | `7e97044e` |
| `validate_worlds_fog` | 4044 | 4.6 | `1d709542` |
| `validate_worlds_g` | 6000 | 7.1 | `7e97044e` |
| `validate_worlds_g2` | 2657 | 6.5 | `7e97044e` |
| `validate_worlds_g3` | 4000 | 6.1 | `7e97044e` |
| `validate_worlds_h` | 6000 | 4.3 | `7e97044e` |
| `validate_worlds_i` | 6000 | 5.7 | `7e97044e` |
| `validate_worlds_inner` | 4000 | 2.1 | `7e97044e` |
| `validate_worlds_inner2` | 5000 | 6.2 | `7e97044e` |
| `validate_worlds_j` | 6000 | 6.1 | `7e97044e` |
| `validate_worlds_k` | 6000 | 7.2 | `7e97044e` |
| `validate_worlds_karutan` | 3000 | 2.1 | `7e97044e` |
| `validate_worlds_l` | 1260 | 1.9 | `7e97044e` |
| `validate_worlds_m` | 1080 | 2.3 | `7e97044e` |
| `validate_worlds_n` | 13000 | 10.3 | `7e97044e` |
| `validate_worlds_o` | not reported | 9.0 | `7e97044e` |
| `validate_worlds_p` | 10000 | 10.1 | `7e97044e` |
| `validate_worlds_p2` | 6000 | 5.5 | `7e97044e` |
| `validate_worlds_q` | 11000 | 12.1 | `7e97044e` |
| `validate_worlds_q2` | 4000 | 9.2 | `7e97044e` |
| `validate_worlds_r` | 12000 | 11.5 | `7e97044e` |
| `validate_worlds_r2` | 9000 | 7.4 | `7e97044e` |
| `validate_worlds_raklion` | 3000 | 2.4 | `7e97044e` |
| `validate_worlds_s` | 11000 | 17.4 | `7e97044e` |
| `validate_worlds_s2` | 10000 | 15.2 | `7e97044e` |
| `validate_worlds_s3` | 22000 | 30.2 | `7e97044e` |
| `validate_worlds_slots` | 18999 | 25.5 | `7e97044e` |
| `validate_worlds_slots2` | 33000 | 20.1 | `7e97044e` |
| `validate_worlds_slots3` | 36000 | 18.7 | `7e97044e` |

Self-review against repository evidence/privacy standards and the task brief is
complete, with no open findings within the stated coverage. External steward
review remains pending.

## Limits and next

Offline/static fixture presentation only. No original client or launcher ran;
no live account, server, packet, protection or power work was added. Converted
original movies and the fixed-clock GFx library are private local inputs.
The sweep covers the sixteen named task panels and map/HUD, not every NPC,
trade, social or tooltip state. The eight new #380 adapters are controller-tested
but outside the requested sixteen-panel size matrix. Inventory item-model protrusions retain the
original icon rules and are outside this lane's ownership.

Next: the steward performs integration checks and merges; a later APP-REFRESH
lane can install and inspect the combined app. The installed Native Preview,
Wine player app and staged Wine app were not changed. Proofs and reports are
summarized here; per the brief, the lane's scratch/renders/build outputs and
both owned worktrees/local branch are removed after the ready entry. No private
artifact from this lane is needed as a later input.
