# APP-POLISH-002

Codex GPT-6-Astra, xhigh. PR-ready for the merge steward; no full gate, installation or original-client run.
Started from APP-POLISH-001 `144aa1f8` while #293 was queued, then merged main `9e93e6c9` with
RENDER-EFFECTS-011. Merge #293 first. Both sides of the validator registry and status additions are retained.

## Player-facing result

The world HUD now displays the current session's HP, MP, SD and AG. Hound damage lowers HP visibly; standing
still no longer makes resources oscillate. The old `demo_step` also advanced experience and AG without a
session event; the world no longer enables it. Standalone GFx demonstration tools retain their demo mode.
No hero stats, damage, regeneration, combat rule or monster placement changed in this lane.

The session's eight fields go through the existing `setHPMP` object. Positive session maxima take precedence;
the offline join fixture currently leaves maxima zero, so those missing values use the existing native
progression view. This is a display fallback, not a claim that the fixture supplies the original's complete
vital record. Standalone worlds without that facade still have unavailable maxima. Toxic colour and the
opaque patched entry to the original updater remain outside this slice.

Main HUD scaling stays 1:1 at 1504×936. The original base viewport uses actual W/H, `base` frame 1 sets
`Stage.scaleMode="noScale"`, and `Frame.Main.onResize` uses 100% at stage heights of at least 700. The earlier
Warps viewport is a separate path. No controls moved. Detailed addresses, input hashes and boundaries are
in [client-app-polish2](../research/client-app-polish2.md).

## Fidelity

The baseline was taken once using this worktree's unmodified main-equivalent native C sources at `90e11d71`.
APP-POLISH-001 had changed only placement, Swift and tests. Its new Hound placement was supplied explicitly
for the idle HUD screenshot baseline; the default-draw tour has no placement override or HUD.
The before window ran at Lorencia 203,131 for eight seconds with zero monster attacks/hero hits; a screenshot
nevertheless shows HP 528/1100 and MP 41/200. That is the independent demonstration animation.

After runs use the same Lorencia field, original placement file, real local Ruffle and read-only canonical
Native Data lang/objects. Converted gfx movies come from APP-REFRESH-004's existing read-only Native Data.
No audio, owner settings changes or installed-app use. A scripted attack on `hound` triggers its existing
counterattack rule; the test does not alter its HP or damage. Both headless and windowed runs record one
monster attack and one hero hit. The window records five hero attacks and the Hound's death.

The latest-main travel proof uses x=122, Noria y=257 and Devias y=324 at 1504×936. Session and HUD HP
both change from 400 to 1100 when entering Noria through the existing world/fixture lifecycle, then remain
1100 in Devias. No old-session pointer is used after unload.

Opt-in `MU_HUD_TRACE=1` reports session and HUD current values once per second. Final Hound run:

| Time | Session HP/MP/SD/AG | HUD HP/MP/SD/AG | HUD maxima |
|---|---|---|---|
| 1 s | 400,200,52,25 | 400,200,52,25 | 1100,200,52,25 |
| 2 s | 377,200,52,25 | 377,200,52,25 | 1100,200,52,25 |
| 3–7 s | 377,200,52,25 | 377,200,52,25 | 1100,200,52,25 |

Window-only PNGs were read from this lane's own SDL framebuffer, scaled from Retina pixels to 1504×936,
and inspected. Temporary paths under `native/renders/app-polish-002/` and SHA-256 prefixes:
`after-30.png` `158059cb83ad5a74` shows 400/1100;
`after-90.png` `b64b66905b64e4a3` and `after-150.png` `d317331e6c370b2cb` show 377/1100.
The before image and three after images are appearance checks at different animation times, not pixel-parity
claims. They are deleted with the lane's outputs after queueing, per the brief.

## Checks

| Check | Result | Wall time |
|---|---|---|
| Main-equivalent baseline native `all world` build | pass | 19.75 s |
| Root build before integration | pass | 17.55 s |
| Latest-main root build / GL world build | pass | 12.73 / 4.42 s |
| New validator, full count once | 1,024 vital cases plus 4 base viewports; 0 mismatches; 10/10 mutants, none equivalent | 18.53 s |
| New test + app + world-parts + registry modules | 51 tests, 0 failures, 0 skips | 123.23 s |
| App module after the effects merge | 18 tests, 0 failures, 0 skips | 70.48 s |
| Idle before window, eight seconds | zero hero hits; independently changing displayed vitals | 12.50 s |
| Final Hound window / headless, 200 frames | 400 → 377 in session and HUD; 1 hero hit each | 11.56 / 4.40 s |
| Rebinding/Warps travel, latest build | 0 → 3 → 2, 2 travels, 0 failures; original row points; HUD equals rebound session | 5.77 s |
| Default-draw DATA-ACQ-002 tours, before / after | 32/32 maps and 128/128 PNG/binary artifacts byte-identical, including after main's effects merge | 38.74 / 41.50 s |
| Staged repository audit | 1,866 staged files, 0 rejected | 22.11 s |

The tour contains no HUD, so it has no HUD-only differences. The changed vitality numbers/orb fills are
intentional only in the separate HUD runs. An early diagnostic run exposed missing session maxima; after
adding the display fallback, the final Hound runs above were repeated. An idle headless diagnostic also
confirmed constant HP before the Hound script was added. Those exploratory runs are not extra tour sweeps.

No full gate. Builds use `nice -n 10 make -j4`; heavy Python checks use `nice -n 10` with one heavy job at a
time. No runner uses more than two jobs. Free memory remained above 25%; heavy work paused after concurrent
load rose above 14. The new validator's full count and mutants ran once; development used 20-case samples.
Budget deviation: the private `test_world_parts` module also invoked the unchanged WORLD-ORDER comparison
and its ten mutants, all caught, within the 51-test run. That helper was not repeated and is not requested
from the steward for this lane.

TEST BUDGET 6b: searched native/tests, reconstructed and tests for `world_gfx_open`, `world_gfx_frame`,
`world_gfx_progress`, `world_gfx_rebind_skills`, `progress_sync` and `vitals_sync`. No public signature or
shared record changed. `world_gfx` is private to its C file. The new test compiles the adapter; world-parts
and app modules cover its host build/lifecycle. The existing registry rows that name `native` compile
specific core/audio/crypto sources, none compiling `world_gfx.c`. No existing validator requires rerun for
this lane's source diff. The new row is the only steward validator. APP-POLISH-001 keeps its separate row.
The RENDER-EFFECTS-011 merge touched no source compiled by the new comparison; its mutants were not repeated.
The root/world build and app module were repeated because their compiled sources changed.

Steward validators: validate_app_polish2

Steward mutants: none. All ten were caught once here; rerun without `--mutants`.
Environment: `MU_RECOVERY_INTEGRATION=1`, `MU_SECTION3` pointing to
`~/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`, and
`MU_GAME_ROOT=~/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix`.
Native Data: canonical `~/Documents/MTM/mu-mac-tools/native/scratch/native-data/export`, read-only.

## APP-REFRESH-005 and remaining scope

Rebuild/reinstall the merged app in the refresh lane. Existing converted movies and Native Data remain usable.
Verify idle vitals, a Hound counterattack, and Lorencia → Noria → Devias in the installed app. This lane does
not install it. No scaling adjustment or new journey coordinates are needed.

The original updater entry `0x00c71772 → 0x10b14930` remains opaque; buff/toxic colour handling and live
original-client comparison remain open. A later session lane should supply authoritative maxima at join
and retire the progression display fallback. Complete HUD/CharacterInfo ownership and all sub-700 layouts
are not claimed. The main bar's viewport and layout at the requested size are accounted for.

## Cleanup

After the ready-prs line, no more pushes. Remove this lane's scratch, renders, build outputs, worktree and
local branch. No new private input must be retained; canonical inputs and installed applications stay intact.
