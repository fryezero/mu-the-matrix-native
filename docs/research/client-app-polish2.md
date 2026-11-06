# Session vitals and the main HUD viewport

APP-POLISH-002. Display changes only. The existing combat and progression state, formulas, regeneration,
fixture rules and placement are unchanged. No original client was launched and no network work was done.

## Vitals

The previous world host enabled `mu_gfx_layer_config.demo`. Its 40 ms `demo_step` replaced HP, MP and SD
with sine/cosine values, incremented AG and advanced experience without a session event. The main movie
received those values through `setHPMP`. A visible falling orb was therefore not evidence of combat.

The world now borrows the same session used by the skills/combat view and calls `mu_session_hero` before
advancing the movie. Its eight vitality fields feed the existing `setHPMP` adapter. A world unload clears
the borrowed session and progression pointer before either owner is destroyed; the next world rebinds it.
This occurs even when the optional skill UI is disabled. `progress_sync` no longer clamps displayed HP/MP.

The offline join fixture leaves maximum-vital fields zero. When a session maximum is nonpositive, the HUD
uses the existing native progression view's corresponding maximum. Positive session maxima always win.
This is an explicit native display fallback, not a reconstruction of the original. No state is written
back. A standalone world without progression and without session maxima still has unavailable maxima;
completing the fixture/session join is outside this display-only lane.

### Original instructions

Inputs are `pins.TEXT`, `pins.DATA` and the requested `pins.SECTION3`, the latter supplied by `MU_SECTION3`.
The comparison verifies all three hashes. Third-section dynamic hero pointers/records are synthetic case
inputs, not values inferred from the snapshot. No protection module is read or analysed.

- `0x00c71772` jumps to `0x10b14930`, outside the restored image. That entry hook stays opaque. The validator
  enters the intact body at `0x00c717d4` with an authored stack frame and `isToxic=false`; it stops before
  exception cleanup. Toxic/buff selection at `0x00c71798..0x00c717ce` is outside this comparison.
- `0x00c717d4` reads the hero pointer `0x0a39d754`, class byte `+0x12`. `0x0139d8ea` → `0x0139cb15` tests
  class bit 5. The third-class branch calls `0x00a0020f/232/255/278` and reads maxima `+0x40/44/48/4c` of
  CharacterAttribute, whose pointer is `0x01d1df1c`.
- The ordinary branch at `0x00c71826` calls `0x0096168c`, `0x00c745c1`, `0x00c745df`, `0x00c745ee` for
  maxima `+0x70/74/7c/84`. Current values always use `+0x68/6c/78/80`, through `0x0096167d`, `0x0096169b`,
  `0x00c745d0`, `0x009616ba`, called at `0x00c71864/72/80/8e`.
- `0x00c718a3` calls cache equality `0x00c73fb6` against handler `+0x22c`; unchanged values skip the invoke.
  `0x00c718c1` copies the new cache through `0x00c73eae`.
- `0x00c718d9` creates the GFx object through `0x00c8f5f4`. `0x00c718f5` sets `isToxic` through
  `0x00aecd73`; `0x00c7190f/29/43/5d/77/91/ab/c5` use `0x00ae957f` to set `hp`, `maxHp`, `mp`, `maxMp`,
  `Shield`, `ShieldMax`, `SkillMana`, `SkillManaMax`. `0x00c719d6` invokes `setHPMP` through `0x00c8fac2`.
  The GFx value operations are recording boundaries; the selection, getters and cache instructions execute.
- The movie's `Frame.Main.setHPMP` sends the four pairs to `_HPbar`, `_MPbar`, `_SDbar`, `_AGbar.setValue`.
  This path passes an object to Invoke, not eight independent SetVariable calls.

`validate_app_polish2` compiles the production `mu_session_hero` getter and `vitals_sync` function verbatim,
with the real layout headers, and links the real GFx layer. A small synthetic session container holds the
same `mu_dom_hero` record. The fallback view is a test double. Original comparisons cover supplied positive
maxima, while portable tests separately cover missing maxima and precedence. Each original case invokes
the intact body twice and checks that the second invocation is suppressed. The portable movie log checks
the full outgoing object and 100 idle logic steps without an extra vitality invoke. Ten compiled mistakes
cover the eight field assignments, a disconnected session, and re-enabling world demo animation.

## Main HUD scaling

No scaling change is needed for 1504×936. This conclusion concerns the main HUD at the requested size,
not every independent GFx window or every low-resolution layout.

- Static creation: the base filename at `0x01a85fe4` is loaded by `0x00aef02d..0x00aef04d`. The movie view
  is stored at manager `+0x88`. `0x00aef135` sets `_root.isClient`; `0x00aef1b4` calls the base viewport setup.
- **Instruction verified:** `0x00aef36d` reads actual screen width/height from `0x01cf1624/28`. Its call at
  `0x00aef3b6` to `0x00ab0d72` passes `[W,H,0,0,W,H,0]`. Comparisons cover 800×600, 1280×800, 1504×936 and
  1722×1048 and compare the native layer's stage dimensions. This is the base HUD path; the fixed 800×600
  independent-window arguments from APP-POLISH-001 were not reused as evidence.
- **Static ActionScript:** `base` frame 1 assigns `Stage.align="TL"`, `Stage.scaleMode="noScale"`.
  The strings occur at decompressed GFx offsets `0x864` and `0x86e`. `Frame.Main.onResize` sets both scales
  to 95 below `gStandard.ResizeStageHeight=700`, otherwise 100; then centers horizontally and anchors the
  background to the stage bottom. `main`'s `ResizeStageHeight` string is at decompressed offset `0x3a7da`.
  At both 1280×800 and 1504×936 this is 1:1, not proportional expansion of an 800×600 canvas.
- Native `mugfx` already forces `StageScaleMode::NoScale` and passes the point-sized stage to the original
  converted movies. Retina backing scale changes raster resolution, not these layout coordinates.

Movie provenance, read-only installed inputs under `Data/Interface/GFx`:

| Input | SHA-256 |
|---|---|
| base.ozg | `2487c880e7fedd37d972abb2a39bf999e32c03693b2b2f9f6c287789b73fb1ca` |
| decoded base movie | `632a88ae5034de482eff9968645b14c2f8a25f9dd23c9c1783ca321db01faf28` |
| main.ozg | `d4bedaed51a28babee2d044645c2dfbd153a0203c902553a79ceb8e00a27868d` |
| decoded main movie | `e7052be16a3b0adcb37d811ef51cad21ccde5b8f89def95fc1cf35da56435df2` |

JPEXS decompiled the locally converted base movie; the settings were cross-checked in the original
unwrapped movie. The existing main-movie decompilation supplies the layout reading. No movie bytes or
ActionScript source are committed. Live comparison, toxic colour changes and exhaustive low-resolution
layout checks remain open. See [the handoff](../handoffs/APP-POLISH-002.md) for measured checks and screenshots.
