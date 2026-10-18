# "Hash Protection" code 0xA4 dialog at launcher start (MAC-APP-005, paused)

Owner report: sometimes the launcher (`MuTheMatrix.exe`, IGCN 1.12.1.3) opens a dialog titled "Hash Protection",
"code: 0xa4", "unable to read beyond the end of the stream." OK closes it and the next start works. The owner
wants players never to see it. On 2026-10-18 the owner paused the work because the dialog had become very rare
to reproduce. This note records what was found so far. **No fix is in place yet.**

The protection (IGC.dll, RGS.dll, the launcher's hash component) was treated strictly as a black box. Nothing was
disassembled, traced, hooked or patched, and its checks were not suppressed. The evidence comes from three sources:
the launcher's own log (`Data/Launcher/Log.txt`, decoded with `mac-play/decode_launcher_log_exact.py`), file
snapshots (size, mtime and SHA-256 of the game folder, `drive_c/users`, `ProgramData`, `C:\mutools` and the
prefix `.reg` files), and OS-level observation of which files the Wine processes had open (`lsof`, polled every
~60 ms) plus a 1 ms poll of `Data/Launcher/Temp`. Snapshots and captures stayed local.

## What the log says

Every occurrence logs the same entry:

```
Code: 0xA4  Unable to read beyond the end of the stream.
System.IO.EndOfStreamException
   at System.IO.File.InternalReadAllBytes(String path, Boolean checkHost)
   at (ck, String, String) / ck.g(String, String) / (ck, Object)     <- worker thread of the launcher
```

So `File.ReadAllBytes` threw. In .NET Framework 4.8 it takes the file length first and then calls `ReadFile`
until it has that many bytes. It throws EndOfStream only when a `ReadFile` returns 0 bytes before that length is
reached. A file that is empty, missing or locked gives a different error. In other words, the file looked longer
than the bytes a read returned.

Occurrences per launcher log:

| Prefix | 0xA4 entries | Notes |
|---|---|---|
| CrossOver bottle MuMatrix32 | 34 (Oct 15-18) | many while the skin was still disabled (Oct 16-17) |
| free install (`~/Library/Application Support/MuTheMatrix/prefix`) | 4 | 07:57:34: first start right after a fresh install by the app (start 07:57:23, cx24.0.7 runtime, plain Rosetta); 10:16:54 (another agent); 11:55:05 and 12:35:53 (this investigation) |

The error is logged 4.5-11 s after the launcher process starts. That is the window in which the launcher opens
its hash-checked files (see below).

## Reproduction attempts (2026-10-18)

| Scenario | Runtime | Starts | Dialogs |
|---|---|---|---|
| `mu-launch.sh`, then `wineserver -k` 4/8 s after start | free | 9 | 0 |
| `mu-launch.sh`, then `kill -9` of the launcher 5-12 s after start | free | 38 | 1 (11:55:05) |
| as above with 12 CPU burners running | free | 5 | 0 |
| launcher, GAME START, game running, `wineserver -k`, restart | free | 2 | 0 |
| direct `wine MuTheMatrix.exe`, `kill -9` after 8 s | free | 18 | 0 |
| same with `COMPlus_GCgen0size=0x10000` (more GCs) | free | 18 | 1 (12:35:53) |
| launcher left idle for 60 s and 170 s | free | 2 | 0 |
| `mu-launch.sh` / direct start, `kill -9` or `wineserver -k` | CrossOver MuMatrix32 | 18 | 0 |
| owner's `play-mu.sh` (fast x87), `taskkill` + `kill`, or `wineserver -k` | CrossOver MuMatrix32 | 18 | 0 |
| launcher, GAME START, `wineserver -k` | CrossOver MuMatrix32 | 7 | 0 |

That makes 2 dialogs in about 135 starts (about 1.5 %). Both were in the free runtime, one after a kill and one in
a run that had a kill before it, like every other run. The MAC-APP-006 (skin) agent saw it in MuMatrix32 after
force-kills, once right after GAME START, and once on a start that followed a close with the launcher's own X.
It never saw it on free-runtime starts. It found the skin was not involved. The MAC-APP-004 agent saw it twice,
each time on the first start after a force-stop, with both the v1 and the v2 mscoree proxy.

## Snapshot diffs (file names and sizes only)

- **Launcher start.** `Data/Launcher/Temp/OPEN.dmm` is created (0 B). `Data/Launcher/Temp/RESTORE.dmm` is touched
  (0 B). `IGCLauncherOption.ini` is rewritten with identical content (117 B). `C:\mutools\winfix.log` and
  `modehook.log` grow (our mscoree proxy). The `.reg` files are saved.
- **Running, about 3.5 s after start.** The launcher downloads `Data/Launcher/Temp/L_Version.wvd` (0 → 10 B) and/or
  `version.wvd` (0 → 174 B). Each file is created, filled and deleted within about 10-50 ms.
- **Forced kill** (`kill -9` or `wineserver -k`). `OPEN.dmm` disappears (it is a delete-on-close file).
  **Nothing is left truncated or half-written.** The next start's snapshot is the same as after a clean start.
- **Game killed.** Only `MuError.log` grows.
- **Fresh install** (free prefix, 07:57). Besides the files above, `Data/Interface/GFx/Notice/Eventnotice.ozp`
  (673,263 B) was rewritten at 07:57:59, 25 s after that start's dialog. In MuMatrix32 it was last rewritten on
  Oct 16 16:42. Because it happened only once, it cannot explain the repeated occurrences.
- On macOS every file in the game folder (36,103 files) reads back exactly its `st_size`. No file has
  compression or other special flags.

Ruled out:
- a half-written cache, state or config file left behind by a forced kill. Kills leave no such file, and the
  dialog also followed a clean X close;
- the restored launcher skin (MAC-APP-006);
- our mscoree proxy. It has no file hooks, and the dialog appeared with v1 and v2;
- CPU load at start (0 in 5 starts with 12 burners).

## Which files the launcher reads at the time

About 5.5 s after start the launcher process opens `main.exe`, `IGC.dll`, `RGS.dll`, `freetype.dll` and
`opengl32es.dll`, and keeps them open. Within about 0.3 s it also opens one or two client data files that differ
on every start. Examples: `Data/Local/{item,mix,mixold,itemtooltip,itemtooltiptext,itemsetoption,itemaddoption,
masterskilltooltip,skilltooltiptext,questprogress,attributevariation,jewelofharmonysmelt,muunmeshinfo,
ItemOptionSystem_Exc}.bmd`, `Data/Player/player.bmd`, `Data/Lang.mpr`, `Data/Interface/GFx/Notice/Eventnotice.ozp`,
`Data/Interface/GFx/AlarmFrame_I1.ozd`, `Data/Interface/GFx/fonts/fonts_all.swf`. Nobody writes these files while
the launcher starts, and the same happens at GAME START. After that, an idle launcher reads no more data files.

## Leading hypothesis (unconfirmed): a Wine read path on macOS

The data does not point to a file. It points to a rare race in a read of a file that does not change:
- XNU behaves differently from Linux here. Suppose `read()` copies into a buffer and hits a page that is not
  writable part-way through. macOS then returns -1/EFAULT *and still advances the file offset* by the bytes it
  copied. Linux returns the partial count. This was checked with a small native test, both arm64 and x86_64 under
  Rosetta: a 15-page read into a buffer whose 10th 4 KB page was read-only returned -1 EFAULT with the offset at
  32,768.
- Wine 11's `NtReadFile` (the base of both the free runtime and CrossOver 26.3) reads synchronous file handles
  with `virtual_locked_read()`. When `read()` returns EFAULT, that function re-enables write access on
  write-watched pages and calls `read()` again *at the current offset*. On macOS that offset has already moved,
  so the retry reads the wrong part of the file and comes up short. The next `ReadFile` then returns 0, which is
  exactly the EndOfStream above.
- Which pages could be read-only in a fresh `byte[]`: the .NET concurrent (background) GC allocates its heap with
  `MEM_WRITE_WATCH` and re-protects pages (`ResetWriteWatch`) while it marks. A background GC that runs while the
  launcher reads a few MB into a new large-object array would trigger this.

This would explain why the dialog is rare and random, why it does not depend on a file left on disk, and why it
appears near start and GAME START. It could not be confirmed. A Win32 test in a scratch prefix read `main.exe`,
`RGS.dll` and `freetype.dll` about 340 times into a `MEM_WRITE_WATCH` buffer while another thread called
`ResetWriteWatch`. It got 0 short reads and 0 wrong bytes, so the race did not show up in that form.
`COMPlus_GCgen0size=0x10000` (more GCs) gave 1 dialog in 18 starts against 1 in about 117 without it, which is
not significant.

## Next steps (not done)

1. **Test the GC hypothesis with enough starts.** The candidate fix is environmental: turn off the launcher's
   concurrent GC with `<runtime><gcConcurrent enabled="false"/></runtime>` in the `MuTheMatrix.exe.config` the kit
   already writes (`LAUNCHER_CONFIG` in `setup-mu-mac.sh`), or `COMPlus_gcConcurrent=0` in `mu-launch.sh` and
   `play-mu.sh`. Without concurrent GC the heap gets no write watches. To show an effect against a 1-2 % base
   rate you need a few hundred automated starts per arm (e.g. the direct start / `kill -9` loop, 9 s per start,
   in 3-minute runs). Checking that the launcher's WPF UI still behaves normally is part of that test.
2. **If the fix is confirmed, think about Wine itself.** A runtime-side patch would make
   `virtual_locked_read()` on macOS restore the offset with `lseek` before retrying, or use `pread`. It belongs in
   our runtime build (`mac-play/installer/packaging/build-wine.sh`) and upstream, and it would also cover the
   CrossOver bottle only if CrossOver takes it.
3. **Graceful close in our helpers** (useful anyway, but not shown to matter for 0xA4). The owner's
   `mu-to-server.sh` and the agents' `perf10/stop.sh` already send `taskkill` without `/f` (WM_CLOSE) before
   `kill`. `runbottle.sh` uses `wineserver -k` after its timeout. The app and `mu-launch.sh` never stop a running
   launcher: `mu-launch.sh` refuses with code 14, and its `wineserver -k` reset only runs when no Mu process is
   left. `setup-mu-mac.sh` stops the prefix's wineserver after its steps (`wineserver_wait`, `--stop`, cancel). A
   `--install` repair while the player has the game open would kill it. A preflight "close the game first" check
   there is a small, safe improvement.
4. Keep the passive observers ready (lsof poll of the launcher process plus a 1 ms poll of `Data/Launcher/Temp`).
   They would show which file was open at the moment of a future occurrence.
