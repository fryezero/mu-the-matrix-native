# World captures 2: populated original captures of the uncaptured world classes (DATA-ACQ-002)

DATA-ACQ-002, 2026-10-28. Guided live captures on the owner's original client, under the shared game lock,
taken with the method of [world fidelity §1](client-world-fidelity.md#1-method) and compared with the native world
by the same readers and `scripts/fidelity_tour.py`. Labels as in the other notes: **live** = read from (or seen in)
the running client this lane started; **static** = read from files or decoded instructions; **inference** = not
checked by a read or by execution.

Target `main.exe` SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` (the installed
client's file hashes to the evidence-index target). The full per-file SHA-256 list of every capture, the object,
camera, light and image numbers and the music-read hashes are in the companion
[JSON](client-world-captures-2.json). The captured bytes, plaintexts, screenshots and renders stay local.

## 1. Live side

**Client.** The CrossOver application and the `MuMatrix32` bottle named by the older notes and by
`mu-autologin.sh` no longer exist on this Mac. The owner's play install is the free-runtime prefix of
`Mu The Matrix.app` (`~/Library/Application Support/MuTheMatrix`, runtime `archive-c50cb6145767`). The lane ran
the same steps as `mu-autologin.sh` from local copies of the helper programs (`clickstart.exe`,
`muinput-fid.exe` run by Unix path; nothing was copied into the prefix), with the password read from the Keychain
item `mu-the-matrix-dev` into the input helper only. The window was set to the 10-22 size, 1722 × 1048 client area
(launcher option `DevModeIndex` 4 = 1728 × 1080, through the app's own `mu-launch.sh`), with a rollback copy of
`LauncherOption.if`; the owner's file (index 2) was restored byte for byte after each session. The fast x87 loader
refused to patch on this macOS ("unsupported or inconsistent Rosetta runtime"), so the client ran on plain Rosetta;
the first start took 4.5 minutes to reach the world, later ones 1.5 minutes.

**Sessions.** Four sessions, lock held 17:21–17:26, 17:27–17:36, 17:37–17:48 and 17:49–17:53, each ≤ 15 minutes;
client and launcher closed and the lock removed after each. Nighty (MTM-1) entered the world where the owner had
left it, Tormenta Island 134,66, under attack; the client was closed at once (session 1, no capture). On the next
login the server had moved the character to the Tormenta arrival circle (129,119), which was quiet. From then on
travel was only by the Warps window (M): one click on a list row, capture at the arrival tile, next warp. No walk,
fight, NPC, shop, trade or item action; only warp costs were spent; every session ended in Lorencia. One stray
click (the Warps window had been closed by the M key) moved the character a few tiles inside Loren Market's town
area. Reads were `mach_vm_read_overwrite` only; no memory write, packet or traffic capture.

**Per arrival tile** (as on 10-22): a window-only shot (`winshot.swift`), `objread` (sector lists and scene
globals), `lightread` (model container, characters, primary and frame light grids), the wall-clock time; and a
12-byte `memread` of world `0x01cf15fc`/`0x01cf1600`, weather `0x01cf15ec` and WorldTime `0x06fce370`. The readers
are the `live-readers` sources of this branch (the maintained versions of the `fidelity2/bin` helpers).

**What the Warps window offers** (live): 69 rows. Duel Arena (64), world 82, Uruk Mountain (100), Santa Village
(62), the Imperial Guardian (69–72), Arca (92/96/101/111), Debenter-class (95) and worlds 110, 114, 115, 121, 139
are not in it; Aquila's Temple (145) needs total level 1650 (Nighty: 400 + 1200 master, shown red). "Loren Deep"
refused the warp (castle owners and union members only). Event Square warps into world 79, Loren Market's world.
These were recorded and skipped; no other entry was tried.

## 2. Captures and comparison

Native side: `native/build/mu-world --headless --backend gl --fidelity-dump` at the captured world, tile and
1722 × 1048, 25 logic steps, `--objects-dir` with the new local plaintexts
(`scripts/live_objects_to_plain.py --installed`), through `scripts/fidelity_tour.py run`; the manifest's
title bar is 32 (the window is 1080 points tall, 1076 on 10-22). Image error is the masked mean |Δ| in 8-bit
units over the client area (HUD and hero masked); the live shots include the hero's wings and pet, other players
and NPCs, which the native world does not draw.

| Capture | World | Tile | Linked = count, version | Matched / missing / extra | Field diffs map (near hero) | Far live / native | Primary light | Frame light near hero | Image mean \|Δ\| / > 24 | Object snapshot SHA-256 |
|---|---:|---|---|---|---|---|---:|---:|---|---|
| Arena | 6 | 72,174 | 1,417 = count, v0 | 1,416 / 1 / 0 | 0 (0) | 3257.8 / 3257.8 | 0 | 0.0039 | 3.761 / 0.0118 | `54916a158aedbce6…` |
| Kanturu Relics (Move: Kanturu Remain) | 38 | 71,104 | 2,121 = count, v3 | 2,121 / 0 / 0 | 42 (42) | 3257.8 / 3257.8 | 0 | 0.0000 | 6.121 / 0.0562 | `d3fc9450e3d80121…` |
| BattleGrounds | 40 | 230,151 | 2,016 for 2,014 in file, v3 | 2,014 / 2 / 0 | 6 (4) | 3257.8 / 3257.8 | 0 | 0.0060 | 3.985 / 0.0426 | `888fd18ed8c2d483…` |
| Swamp of Calmness | 56 | 136,108 | 4,236 = count, v3 | 4,236 / 0 / 0 | 0 (0) | 3257.8 / 3257.8 | 0 | 0.0295 | 7.310 / 0.0117 | `8dd34e3b61efa53c…` |
| Vulcanus | 63 | 124,129 | 2,319 = count, v3 | 2,319 / 0 / 0 | 0 (0) | 3700 / 3257.8 | 0 | 0.0087 | 2.665 / 0.0158 | `e9046fe266aaa771…` |
| Loren Market | 79 | 56,74 | 1,486 = count, v3 | 1,486 / 0 / 0 | 1 (1) | 3257.8 / 3257.8 | 0 | 0.0122 | 4.361 / 0.0389 | `004f4f833622ca03…` |
| Event Square | 79 | 204,57 | 1,486 = count, v3 | 1,486 / 0 / 0 | 6 (4) | 3257.8 / 3257.8 | 0 | 0.0053 | 3.604 / 0.0171 | `3fccd7eb5f4d3f88…` |
| Acheron (Move: Akeron) | 91 | 58,191 | 5,834 = count, v0 | 5,833 / 1 / 1 | 85 (39) | 3000 / 3000 | 0 | 0.0147 | 7.706 / 0.0424 | `612b11f1132a78ba…` |
| Ferea | 112 | 236,152 | 4,029 = count, v3 | 4,029 / 0 / 0 | 944 (18) | 3257.8 / 3257.8 | 0 | 0.0150 | 2.370 / 0.0043 | `b9fd56bc295fcbc9…` |
| Nixies Lake | 113 | 25,119 | 6,915 = count, v1 | 6,915 / 0 / 0 | 3,838 (169) | 3257.8 / 3257.8 | 0 | 0.0155 | 7.001 / 0.0632 | `c8905fea28d41a75…` |
| Deep Dungeon 1 | 116 | 120,126 | 3,035 = count, v0 | 3,035 / 0 / 0 | 149 (0) | 3257.8 / 3257.8 | 0 | 0.0205 | 5.745 / 0.0626 | `24ca9582bbded52c…` |
| Deep Dungeon 2 | 117 | 131,128 | 3,079 = count, v0 | 3,079 / 0 / 0 | 1,421 (57) | 3257.8 / 3257.8 | 0 | 0.0198 | 4.453 / 0.0297 | `60a67b27af78a925…` |
| Deep Dungeon 3 | 118 | 123,123 | 3,718 = count, v0 | 3,718 / 0 / 0 | 1,716 (69) | 3257.8 / 3257.8 | 0 | 0.0238 | 14.168 / 0.2082 | `5cdb48d43766211b…` |
| Deep Dungeon 4 | 119 | 125,119 | 3,446 = count, v0 | 3,446 / 0 / 0 | 1,105 (27) | 3257.8 / 3257.8 | 0 | 0.0277 | 10.017 / 0.1372 | `6d2a753b1739eb2e…` |
| Deep Dungeon 5 | 120 | 126,119 | 8,494 = count, v0 | 8,494 / 0 / 0 | 5,897 (178) | 3257.8 / 3257.8 | 0 | 0.0371 | 6.353 / 0.0532 | `08783b536e58d30b…` |
| Swamp of Darkness | 122 | 129,122 | 4,985 = count, v2 | 4,985 / 0 / 0 | 2,508 (47) | 3257.8 / 3257.8 | 0 | 0.0000 | 1.709 / 0.0113 | `44b0da5248a0ad66…` |
| Kubera Mine | 123 | 237,88 | 1,730 = count, v2 | 1,730 / 0 / 0 | 572 (16) | 3257.8 / 3257.8 | 0.03515 | 0.1054 | 12.609 / 0.0743 | `a26630df0594cb6f…` |
| Abyss of Atlans 1 | 128 | 130,127 | 3,908 = count, v3 | 3,908 / 0 / 0 | 276 (124) | 3257.8 / 3257.8 | 0 | 0.0943 | 7.946 / 0.0482 | `c410647ea96a5fdb…` |
| Abyss of Atlans 2 | 129 | 128,124 | 5,899 = count, v3 | 5,899 / 0 / 0 | 512 (125) | 3257.8 / 3257.8 | 0 | 0.0447 | 82.170 / 0.9278 | `ece3e755580441d0…` |
| Abyss of Atlans 3 | 130 | 128,124 | 5,238 = count, v3 | 5,238 / 0 / 0 | 455 (153) | 3257.8 / 3257.8 | 0 | 0.0535 | 47.984 / 0.8807 | `0fdf60876ca4cabd…` |
| Scorched Canyon | 131 | 236,14 | 7,111 = count, v3 | 7,111 / 0 / 0 | 4,374 (84) | 3257.8 / 3257.8 | 0 | 0.0115 | 7.624 / 0.0280 | `a2508dfb627c2c93…` |
| Red Smoke Icarus | 132 | 130,116 | 2,093 = count, v3 | 2,092 / 1 / 1 | 1,812 (45) | 6916 / 6916 | 0 | 0.0000 | 26.344 / 0.3854 | `31489aa2bd5b886c…` |
| Temple of Arnil (Move: Arenil Temple) | 133 | 125,57 | 9,402 = count, v3 | 9,402 / 0 / 0 | 6,475 (166) | 3603.6 / 3603.6 | 0 | 0.0000 | 1.028 / 0.0019 | `2d3791974e821b78…` |
| Gray Aida (Move: Ashen Aida) | 134 | 124,30 | 3,889 = count, v3 | 3,889 / 0 / 0 | 2,926 (135) | 3257.8 / 3257.8 | 0 | 0.0106 | 13.153 / 0.2030 | `08efbb5c673e7d08…` |
| Old Kethotum | 135 | 128,17 | 4,940 = count, v3 | 4,940 / 0 / 0 | 399 (23) | 3257.8 / 3257.8 | 0 | 0.0100 | 2.388 / 0.0136 | `91feee91bf254fef…` |
| Burning Kethotum (Move: Blaze Kethotum) | 136 | 127,17 | 3,784 = count, v3 | 3,784 / 0 / 0 | 303 (25) | 3257.8 / 3257.8 | 0 | 0.0000 | 8.661 / 0.1163 | `40a8c5b8febbde45…` |
| Kanturu Underground | 137 | 129,124 | 12,679 = count, v3 | 12,679 / 0 / 0 | 6,094 (141) | 3257.8 / 3257.8 | 0 | 0.0000 | 5.899 / 0.0458 | `bd3fdc2d1defd41c…` |
| Ignis Volcano | 138 | 124,119 | 4,959 = count, v3 | 4,959 / 0 / 0 | 1,037 (39) | 3257.8 / 3257.8 | 0 | 0.0216 | 4.139 / 0.0368 | `3cacdb4a36c065ad…` |
| Bloody Tarkan | 140 | 128,38 | 3,055 = count, v3 | 3,055 / 0 / 0 | 30 (7) | 3257.8 / 3257.8 | 0 | 0.0052 | 5.225 / 0.0020 | `ba7b4b3acf405855…` |
| Twisted Karutan | 142 | 121,120 | 7,061 = count, v3 | 7,061 / 0 / 0 | 6,515 (318) | 3257.8 / 3257.8 | 0 | 0.0058 | 13.480 / 0.1712 | `aaa05d100d6d2b84…` |
| Kardamahal Underground Temple | 143 | 125,22 | 6,383 = count, v3 | 6,383 / 0 / 0 | 550 (22) | 4686.4 / 4686.4 | 0 | 0.0012 | 10.912 / 0.0917 | `1e83ce6a841a577b…` |
| Swamp of Destruction | 144 | 107,130 | 8,988 = count, v4 | 8,988 / 0 / 0 | 8,232 (139) | 3257.8 / 3257.8 | 0 | 0.0316 | 12.755 / 0.0237 | `a547dafde80bbcd5…` |

"Linked = count": the number of objects in the 256 sector lists equals the count global. "v*n*": the only record
version for which 4 + count × record size equals the installed `EncTerrain<n>.obj` length (exactly one fits in
every capture). Field differences are object-by-object differences of the static OBJECT fields the tour compares.

**Findings (live, compared).**

- **Camera**: the eye is within 0.007 world units of the live camera, pitch −48.5 and FOV 39, in all 32 captures.
  The far plane agrees in 31, including the non-default worlds 91 (3000), 133 (3603.6), 132 (6916) and 143
  (4686.4). **Vulcanus differs: live 3700, native 3257.8**: the per-world far-plane choice for world 63 is missing.
- **Primary terrain light equals the live grid exactly (mean |Δ| 0) in 31 of 32 captures**. Kubera Mine (123)
  differs, mean 0.035 over the 65,536 cells; it is also the only capture with a large near-hero frame-light
  difference (0.105). The cause was not investigated.
- **Objects**: every live object is matched by type and start position except Arena's one object of type −515
  (code-made; the plaintext export drops types outside 0..299), BattleGrounds' two type-2606 objects (world 40
  links 2,016 objects for the file's 2,014; code-created), and one moved object each in Acheron and Red Smoke
  Icarus (missing and extra of the same type). The static-field differences are dominated by **range**
  (48,992 objects over all captures, e.g. Acheron types 60/61 live −428.57 against native −30), then the
  after-character flag (7,068), velocity (1,804), BlendMeshLight (190), BlendMesh (182) and HiddenMesh (44): the
  values the still-missing create/move/visual methods of these classes write. Vulcanus and Loren Market, whose
  methods are verified (G/I), have 0 and 1 differences.
- **Image**: the native world is close in Temple of Arnil (1.0), Swamp of Darkness (1.7), Ferea and Old Kethotum
  (2.4), Vulcanus (2.7). The largest errors: **Abyss of Atlans 2 (82.2) and 3 (48.0)**, where the native world draws
  no terrain tiles at all. Their folders `World130`/`World131` hold the height, light, map, attribute and object files
  but no tile textures, which only `World129` (Abyss 1) has (static: folder listings); the client draws the terrain,
  so it takes the textures from elsewhere (inference: Abyss 1's folder). Red Smoke Icarus (26.3) has the
  world-0x84 "no terrain" pass in both and differs in its clouds and particles. Deep Dungeon 3 (14.2),
  Twisted Karutan (13.5), Gray Aida (13.2), Swamp of Destruction (12.8) and Kubera Mine (12.6) follow. In
  Vulcanus the native world draws its bone piles untextured white and lacks the brazier fires (visual inspection).
- **Native models**: 0–4 object types per world have no loaded model in the native world (9 in Kanturu Relics);
  the per-capture count is `native_object_models_missing` in the JSON.

World indices are **live** (objread's world global): Kanturu Relics is world 38, BattleGrounds 40, Swamp of
Calmness 56 and Arena 6 (built-in worlds, outside the 48 classes); Event Square is world 79.

## 3. Music 43/44 (AUDIO follow-up)

Read once, at the server-select screen of the second session (static data is initialised before login), with
`memread`: `0x01cf1680` for `0x130` bytes, `0x06fba808` for 4 bytes, then each nonnull pointer's string with a
512-byte bound. **Live result**: all 76 entries are nonnull and point to 72 distinct strings, the first at
`0x01af63ec`; their order equals the static literal order exactly as [client-audio](client-audio.md) inferred
(0..39 in order, 40..42 repeat ImperialGuardianFort, 45.. from Karutan_A). **Index 43 (`0x01cf172c`) and index 44
(`0x01cf1730`) both hold `0x01af6848` = `data\music\iDoppelganger.mp3`**: the unresolved index 44 is a second
iDoppelganger entry. `0x06fba808` held `0x6973754d` (ASCII "Musi"; inference: the start of a text buffer in this
scene, not a music index). The bytes and the local name table stay local; their SHA-256 are in the JSON.

## 4. Limits

Each capture is one arrival frame: no particle/sprite/joint/effect pools, no RNG phase, no capture across an
emitter window or weather transition (the G/H/I notes ask for those for worlds 62/63/64/79/82/100). The live
shots came from the Wine-track renderer (mugl), whose shading differences are described in world fidelity §4.
WorldTime differs between the two sides; time-dependent fields (pulses, alpha, flicker) are not compared. The
16 classes marked N in [world-handler coverage](world-handler-coverage.md) still have no original populated capture;
reaching them needs event entries, a duel, a castle/union membership or level 1650, which this lane did not attempt.
