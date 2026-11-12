# Native window layout, APP-POLISH-009

Offline/static work on the pinned restored client. Text SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`,
data SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
No original client or launcher ran. The installed applications were not changed.

## Original rules

| Evidence | Address or movie method | Rule |
|---|---|---|
| Static; creation compared by existing `validate_gfx3` | registry `0x00ac4a79`, creator `0x00ac9edc` | Inventory and PetInventory align right, 11; Warps aligns left, 10; master/fourth tree center, 0; fifth tree left-center, 3; CharacterInfo and the other standard panels use no fixed alignment, 9 |
| Verified, Unicorn | collection resize `0x00ac09b2..0x00ac0a38` | Store width/height at collection +0x10/+0x14; visit every entry, skip null handlers, call `0x00aae4ae` on every remaining handler regardless of alignment |
| Verified, Unicorn | handler `0x00aae4ae..0x00aae506` | Set the movie viewport and invoke `SetWindowSize(width,height)` |
| Static | manager `0x00acb333..0x00acb426` | Resize the three handler collections at +0x74/+0x78/+0x7c; set 640/width and 480/height conversion rates |
| Static; existing creator comparison | `0x00ac9edc`, scale setter `0x00aaebca` | Below height 700, standard windows use 83%, master tree 90%; popups do not get this scale. The scale setter also stores the item-pass factor at handler +0x58 |
| Static ActionScript, exercised by real-movie sweep | `Common.Base.MUComponent.SetWindowSize` | Preserve the previous center's screen fraction for free alignment; right/left alignment pins the horizontal edge; center variants recenter. Negative free/right/left positions clamp to zero. `SetPos` reports the resulting window position |
| Static ActionScript | `MUComponent.onDragStart` | Drag range is 0..viewport width minus GetWidth and 0..viewport height minus GetHeight |
| Static ActionScript, exercised by real-movie sweep | `Frame.Main.onResize` | HUD scale 95% below 700, otherwise 100%; floor the horizontal centering and the bottom anchor using the background height |
| Static ActionScript, exercised by real-movie sweep | `HUD.hudMap.onResize` | Map scale 83% below 700, otherwise 100%; below the boundary convert stage dimensions by floor(size*100/83), then center the map/mask at floor(width/2), floor(height/2)-30. The existing movie owns clipping and Tab visibility |

These rules depend on viewport dimensions, not an aspect-ratio category. The
native app supports continuously resizable windows with a 640x480 minimum.
The sweep samples 4:3, 5:4, 16:9, 16:10 and the 699/700 threshold, through
2560x1440, with Retina checks at both endpoints. This is a native supported-size
sweep, not a claim to have recovered an exhaustive original display-mode list.

## Where the original fixed scales overflow

Measured with the converted original movies and the frame-zero library at
640x480: inventory has y=40 and height=530.35; master tree is at
(-96.6,-80.35), size 833.3x640.7; HUD x=-118 and width=874.95.
The original arithmetic does not promise that all controls fit such a viewport.

The native adaptation runs after the movie's original layout. It shrinks only
when the measured window exceeds the available viewport, caps scale at the
original value and clamps position. Standard panels fit above the measured HUD
background; the HUD shrinks horizontally when needed and keeps its bottom
anchor. The movie still performs alignment and reports positions. After a resize,
the original scale is restored before applying the fit for the new size.
This bounded fit is native policy, not claimed original-client equivalence.
Its compiled arithmetic has containment, maximal-fit and no-enlargement checks
with ten compiled mutants. Tooltips retain their owning movie's placement.

## CharacterInfo ownership

Previously `world_gfx` copied only vitals from the session. CharacterInfo retained
the layer's canned name, stats and other display fields, or values from the
independent `mu_progress` demo. The latter could disagree with the session's
selected fixture. Missing derived data also triggered a local damage estimate.

The session's `mu_hero_stats` now feeds the name, class, level, points, experience,
base/added stats and existing derived fields as well as HP/MP/SD/AG. Session
money, speed text and the existing experience-bar record feed their display
fields. The selected demo name is supplied to the session seed. Missing derived
data displays a dash. No new class formula, authoritative state, combat rule,
stat feature or power feature is added. The standalone progression demonstration
still works when no session is bound.

The demo character-list levels are decorative authored selection data. Existing
join fixtures remain level 1 for four characters and level 320 for Windleaf.
This lane preserves their join values and does not reinterpret those labels as
new stat inputs. HUD and CharacterInfo display the same joined record.

Checks, timings, captures and limits are recorded in the
[handoff](../handoffs/APP-POLISH-009.md).
