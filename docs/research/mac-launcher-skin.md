# The server's official launcher skin under Wine (MAC-APP-006)

Since the first Mac setups the installers renamed the server team's launcher skin
`Data\Launcher\Design\Template.design` to `Template.design.disabled`. The launcher then fell back to its built-in IGCN
skin (794x584, "MU Continent of Legend" art). The recorded reason was that "the custom animated-GIF `Template.design`
fails Wine's design loader, so the launcher constructor aborts" (`docs/research/mac-crossover-32bit.md`,
`docs/code-recovery.md`, both READMEs). That reason was wrong. The skin fails because of a Wine 11 JPEG decoder
change, and the mscoree proxy v3 (`mac-play/mumodes/wicfix.c`) now works around it. With v3 the official skin
(900x620) works in both runtimes, and the installer restores it.

Launcher: `MuTheMatrix.exe` IGCN 1.12.1.3 (`c32e99ee…`). Skin tested: `Template.design` SHA-256
`c405354d97c73020c4bd2868100ac6658bc8b1a90c67b8fa43881b2eeba5c6b4` (the same file in the CrossOver bottle MuMatrix32 and
in the free install). Runtimes: CrossOver 26.3.0 (bottle MuMatrix32) and the free runtime `archive-c50cb6145767`
(Wine CX 26.3). Both have the same Wine 11 code.

## Method

The launcher, the skin and the client were treated as black boxes. Nothing was decompiled, nothing about the
launcher's protection was looked at, and neither the skin nor any client file was modified. Tools:
- the launcher's own log `Data\Launcher\Log.txt`, decoded with `mac-play/decode_launcher_log_exact.py`
  (decoded logs stayed local);
- `--debugmsg +wincodecs` (CrossOver) traces of one start, kept local;
- the upstream `dlls/windowscodecs` sources (`gitlab.winehq.org/wine/wine`, tags `wine-10.0`, `wine-11.0` and master);
- window-only captures, `CGWindowListCopyWindowInfo` and System Events for the Dock, as in
  `docs/research/mac-launcher-windows.md`.

## Observations

With the skin restored (a copy; the `.disabled` file kept) and the v2 proxy, the launcher draws the official skin. It
then shows "Critical Error Occured. Object reference not set to an instance of an object" twice, and Wine reports an
unhandled page fault at address 0. The launcher log has the same three entries for every skin start. The bottle's log
shows them for the October 15 and 16 attempts made before the skin was disabled, and again on 2026-10-18:

1. `DispatcherUnhandledException` `System.NullReferenceException` in
   `System.Windows.Media.StreamAsIStream.Read(Byte[] buffer, UInt32 cb, UInt32& cbRead)`, called from
   `WICBitmapDecoder.GetFrame`. That call comes from `BitmapFrameDecode` and a `JpegBitmapDecoder` created by
   `BitmapDecoder.Create(Stream, …)` in an `Image` `Loaded` handler of the launcher.
2. `UnhandledException` `System.AccessViolationException` in `MILUnknown.Release`, run by a WIC `SafeMILHandle`
   finalizer.
3. Usually followed by the Hash Protection `0xA4` dialog (see below).

So the decoder that fails is the JPEG decoder, not GIF, and nothing aborts in a constructor. The old logs also
have a handled `NullReferenceException at di..ctor()` entry, which is probably where the "constructor aborts" reading
came from. None of the 2026-10-18 starts, with or without the skin, logs it.

The `+wincodecs` trace shows decoders created with `ImagingFactory_CreateDecoderFromStream` on a WPF stream. A JPEG
decoder (`CommonDecoder_CreateInstance({9456a480-…}` = `CLSID_WICJpegDecoder`) created with metadata option 0 returns
from `CommonDecoder_GetFrame` normally (`-> 78x36, 24-bit`). The ones created with option 1
(`WICDecodeMetadataCacheOnLoad`) never get past `CommonDecoder_GetFrame`.

## Cause

- `CommonDecoder_GetFrame` reads the frame's metadata blocks right away when the decoder was created with
  `WICDecodeMetadataCacheOnLoad`.
- In Wine 11, `jpeg_decoder_get_metadata_blocks` (`dlls/windowscodecs/libjpeg.c`) walks the JPEG markers with
  `stream_read(This->stream, header, 4, NULL)`, and `stream_read` passed the NULL straight to `IStream_Read`. In
  Wine 10.0 that function was a `FIXME` stub that read nothing, which is why older runtimes did not crash.
- `IStream::Read` accepts a NULL `pcbRead` by contract. The stream WPF hands to WIC calls back into managed code,
  though, and `StreamAsIStream.Read` writes `cbRead` through its `out` parameter. With NULL that write throws the
  `NullReferenceException`, which then unwinds through the native decoder. WIC's objects are left inconsistent, so a
  finalizer crashes later.
- Upstream fixed it on 2026-08-24 in commit `111e5197` ("windowscodecs: Always pass a valid pcbRead pointer to
  IStream::Read()", which also mentions SharpDX). CrossOver 26.3 and the CX 26.3 sources of the free runtime do not
  have that commit.

The old environment notes still hold: native `windowscodecs` breaks GDI+ image encoding (the October 16 log has
`Code: 0xD0 … A generic error occurred in GDI+` from `Image.Save` in the skin's design-item converter), so the kit
keeps builtin WIC and GDI+.

## Fix: mscoree proxy v3 (`mac-play/mumodes/wicfix.c`)

The mscoree proxy is loaded only by the .NET launcher (AppDefaults `MuTheMatrix.exe` `mscoree=native`). v3 adds the
upstream fix from outside. WPF P/Invokes `IWICImagingFactory_CreateDecoderFromStream_Proxy`
(PresentationCore imports it by name from `WindowsCodecs.dll`). When `windowscodecs.dll` loads
(`LdrRegisterDllNotification`, or right away if it is already loaded), the proxy points that export-table entry at a
wrapper. The wrapper gives the decoder a forwarding `IStream` whose `Read` always passes a valid byte count and, like
upstream, returns `S_FALSE` for a short read when the caller passed NULL. All other `IStream` methods are forwarded
(NULL out-pointers of `Write`, `Seek` and `CopyTo` also get a local). Nothing in the launcher, the skin or Wine is
modified, and no Microsoft DLL is needed. `C:\mutools\winfix.log` records `WIC stream fix armed`, `on` and
`used (first decoder hr=…)`. `MU_LAUNCHER_WICFIX=0` disables it.

Alternatives not taken: native `windowscodecs` for the launcher (breaks GDI+ encoding, see above, and needs Microsoft
redistributables), native `gdiplus` (does not touch the WPF path), and a patched runtime (would not cover the CrossOver
bottle).

## Installer

- The launcher skin step now runs after the proxy DLL step. If the installed (or, in a dry run, planned) mscoree proxy
  contains the fix, which `mukit_mscoree_has_wicfix` checks by its `WIC stream fix` text so that a proxy built locally
  with MinGW counts too, then:
  - an active `Template.design` is left as it is;
  - otherwise the newest `Template.design.disabled[.N]` left by earlier kits is renamed back (`mukit_skin_pick`: newest
    modification time, a game update writes the current skin; ties go to the highest N, the later rename). Every other
    copy stays.
- Without the fix (an old proxy in `--dll-dir` and no MinGW, or no proxy at all), the step renames the skin away as
  before, so the launcher keeps working with its default skin. Files are only renamed, never deleted.
- Verify reports `launcher skin`:
  - PASS: official skin active, with the kept copies listed;
  - WARN: the official skin is disabled (shown whether or not the proxy has the fix);
  - FAIL: the skin is present but the proxy lacks the fix.
  It also shows the last `WIC stream fix` line of `winfix.log`. The v3 proxy is pinned. v2 is recognised (WARN), and
  setup builds v3 instead of installing a v1 or v2 from `--dll-dir` when MinGW is present.
- `mac-play/setup-crossover-32bit.sh` (legacy) installs no mscoree proxy, so it still disables the skin. Its message now
  gives the real reason.

## Live verification (2026-10-18)

Both runtimes, skin restored from the `.disabled` copy, v3 proxy:
- The launcher initialises with the official skin. There is no Critical Error and no `StreamAsIStream` entry in the
  log, and `winfix.log` has `WIC stream fix used (first decoder hr=0x00000000)`. Server time is shown.
- GAME START (`clickstart.exe` at its usual 0.8753/0.9264, inside the skin's START button) gets to the game's
  server selection, at 25 fps.
- The PR #103 window fix still works with the skin. The skin's main window is the same layered WPF window
  (`WS_EX_LAYERED`, 900x620) with the owned news panel. With the game frontmost, the game window is above both launcher
  windows, all at layer 0. The launcher's **–** button leaves one minimized Dock tile. A click on that tile restores the
  launcher with its content, and a click on the app's Dock icon does too. No tile is left behind.
- The launcher closes with its own **X** button.

Observation for the Hash Protection `0xA4` dialog ("unable to read beyond the end of the stream", handled separately):
- it appeared on the CrossOver bottle's starts after earlier force-kills, once also right after GAME START, and once
  on a start that followed a close with the launcher's own **X** button (default skin);
- it did not appear on the two free-runtime starts, the second after a graceful `WM_CLOSE`;
- the bottle's log has many `0xA4` entries from October 16 and 17, while the skin was disabled, so the skin is not
  involved.

A visible `0xA4` dialog is a visible launcher window, and Wine restores a minimized window on a Dock icon click only
when no other window of the app is visible. Then only the minimized tile restores the launcher.

## Open

- The CX24 fallback runtime (Wine 9-based) was not tested live with the skin. Its JPEG decoder reads no metadata
  blocks, and the v3 proxy is harmless there.
- Once a runtime contains upstream `111e5197`, the wrapper is redundant but still harmless.
