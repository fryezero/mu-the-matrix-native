# Companion file findings

Inspection date: 2026-10-15. Scope: recursive inventory of the supplied `Mu The Matrix` installation directory only. Read-only filesystem inspection; no game, launcher, updater, or library was executed. Configuration contents, account data, and credentials were not inspected. These are supplemental static findings, not REA Evidence records.

## Observations

- 36,093 files, totaling 3,138,767,611 bytes (about 2.92 GiB).
- `Data/`: 36,072 files and 3,032,992,247 bytes. The installation also has 20 root files and one file under `Font/`.
- Largest Data groups by bytes: Item (8,910 files, 615,702,526 bytes), Sound (1,378 files, 483,761,058 bytes), Interface (2,255 files, 323,130,598 bytes), Monster (2,136 files, 234,384,631 bytes), Music (68 files, 185,211,761 bytes).
- A recursive extension/name inventory found no `.c`, `.cpp`, `.cc`, `.cxx`, `.h`, `.hpp`, `.cs`, `.sln`, `.vcxproj`, `.vcproj`, `.csproj`, `.vbproj`, `.pas`, `.dfm`, `.lua`, `.py`, `.js`, `.ts`, `.go`, `.rs`, `.java`, `.sql`, `.pdb`, `CMakeLists.txt`, `Makefile`, `package.json`, or `Cargo.toml` files. There are 84 `.map` files, all named `EncTerrain*.map` under world directories; sampled bytes begin with `MAP`, rather than textual linker-map content.
- The executable inventory contains `main.exe`, `MuTheMatrix.exe`, `muplayer.exe`, `awesomium_process.exe`, `Popup.exe`, `Uninstall.exe`, `Data/Launcher/updater.exe`, and two Facebook helpers. No executable filename identifies a separate GameServer, ConnectServer, JoinServer, or DataServer. This is a filename-bounded negative result, not proof that no server behavior exists inside another binary.

## Native and managed code

PE headers were parsed with Python's standard library. All parseable EXE/DLL files use machine 0x14c and PE32. A CLR directory indicates managed metadata; its absence does not establish the original programming language.

| File | Bytes | CLR directory | Observed classification |
|---|---:|---|---|
| main.exe | 32,229,376 | absent | Native PE; sections include `.themida`, `.boot`, `.Silvana`, `.newimp` |
| IGC.dll | 10,185,744 | absent | Native PE; sections include `.vm_sec`, `.winlice`, `.boot` |
| RGS.dll | 3,747,232 | absent | Native PE; sections include `.themida`, `.boot` |
| freetype.dll | 564,736 | absent | Native PE |
| DSETUP.dll | 89,944 | absent | Native PE |
| awesomium_process.exe | 39,704 | absent | Native PE |
| Popup.exe | 169,984 | absent | Native PE |
| muplayer.exe | 36,864 | absent | Native PE |
| Uninstall.exe | 2,306,560 | absent | Native PE |
| MuTheMatrix.exe | 6,154,752 | present, 72 bytes | Managed PE |
| Data/Launcher/updater.exe | 9,728 | present, 72 bytes | Managed PE |
| Data/Facebook/FacebookAPI.dll | 10,240 | present, 72 bytes | Managed PE |
| Data/Facebook/FB_Sender.exe | 5,632 | present, 72 bytes | Managed PE |
| Data/Facebook/FB_Browser.exe | 18,432 | present, 72 bytes | Managed PE |
| opengl32es.dll | 1,572 | not parsed | Does not begin with an ordinary MZ/PE header; `file` classifies it as data |

The section names in the main executable and IGC/RGS libraries are consistent with protection/packing. This is an inference from names only: the inspection did not determine the exact protector version, recover unpacked code, or demonstrate any runtime protection behavior.

## Asset inventory

| Extension | Count |
|---|---:|
| .ozj | 16,429 |
| .bmd | 12,754 |
| .ozt | 3,025 |
| .wav | 1,358 |
| .ozd | 1,264 |
| .ein | 370 |
| .ozg | 179 |
| .ozb | 169 |
| .att | 90 |
| .obj | 84 |
| .map | 84 |
| .ozp | 84 |
| .mp3 | 77 |
| .jpg | 28 |
| .psd | 13 |
| .tga | 12 |
| .ogg | 10 |
| .swf | 8 |

Format-aware representative checks, not whole-extension claims:

- `Data/Effect/!Chrome01.OZJ`: recognized JPEG/JFIF bytes.
- `Data/Effect/01spa_skill.bmd`: starts with `BMD` followed by 0x0f; structure not decoded.
- `Data/World1/EncTerrain1.att`: starts with `ATT`; structure not decoded.
- `Data/World1/EncTerrain1.map`: starts with `MAP`; structure not decoded.
- `Data/World1/TerrainHeight.OZB`: has a repeated BMP-like prefix; not validated as an ordinary BMP.
- `Data/Interface/GFx/NaviMap/Navimap01.OZP`: repeated PNG signature prefix; not validated as an ordinary PNG.
- `Data/Sound/Akeron/Amb_Acheron.wav`: RIFF PCM WAVE, 16-bit stereo, 44.1 kHz.
- `Data/Music/Acheron.mp3`: ID3v2.3/MPEG layer III, 128 kbps, stereo, 44.1 kHz.
- `Data/Interface/GFx/IME.swf`: compressed Flash, version 8.
- `Data/Object7/au_02.psd`: Photoshop image, 256 by 256, RGB.
- All 370 `.ein` files successfully parsed as JSON with the standard library. This confirms editable structured data exists, but not that these files implement game logic or can rebuild the game.

## Bounded conclusion and unresolved requirements

The supplied directory is an installed distribution with substantial game data and compiled programs. This inspection did not find a buildable source project or a separately identifiable server package. The managed companion programs are more directly inspectable than the native main executable, but recovering their source would not itself reconstruct the gameplay client.

A working editable game still requires establishing and implementing the client behavior, file formats, companion-library roles, networking protocol, and any required server behavior. These are unresolved by the inventory. The presence of 3 GB of assets does not establish that a new client can load them correctly. No executable behavior, gameplay, offline operation, server compatibility, build reproducibility, or redistribution/license permission was verified.

Machine-readable counts, PE metadata, section names, and SHA-256 digests are saved in `companion-inventory.json` beside this report.

## Follow-up content inspection

The later investigation in `docs/asset-recovery.md` found one image-extension file that contains wrapped editable mesh text: `Data/Object38/hs_Lifeshin01.OZJ`. It was validated and exported as an eight-triangle `.smd`. This qualifies the earlier extension-only negative source search; it does not supply client/gameplay source or a build project. The image recovery component now fully decodes 19,703 installed assets.
