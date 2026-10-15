# Windows executable-region capture

This helper supports the next recovery step on a Windows x64 system where the original game actually runs. It is an analysis utility, not a game client or a macOS port.

## Status

The C source cross-compiles with MinGW-w64. The `--self-test` SHA-256 known vector and own-process memory read pass under Wine. Capturing the real game on native Windows is still unverified and is CAP-001 in the roadmap.

## Build

```sh
make -C windows-capture
```

This produces `capture-client.exe`, ignored by Git. Use an x64 MinGW-w64 compiler; the source depends on Windows system APIs and BCrypt, not a .NET runtime. The program does not automatically request elevation.

## Use on Windows

1. Build or transfer your locally built helper to a separate working folder.
2. Start the exact original game normally and stay at its login screen before entering account details.
3. Run `capture-client.exe`. It finds one readable running `main.exe` matching the pinned SHA-256. If the game runs elevated, run the helper with the corresponding Windows access level.
4. Retain the new `MuMatrixCapture-...` folder, including `capture.json`, for local analysis. The game is left running and can be closed normally.

For explicit selection, use `capture-client.exe PID NEW_OUTPUT_DIRECTORY`. The target must still match the exact pinned executable; the output directory must be new. Read the reported errors rather than treating an empty/partial folder as a successful capture.

## Scope and limits

The helper opens query/read access and selects executable committed image regions within `main.exe`, `IGC.dll` and `RGS.dll`. It records addresses, region hashes, module-file identities and failures. It does not inject code, patch the process, log in, suspend threads or stop the game.

Reads occur while the process runs, so they are not an atomic snapshot. Private executable allocations outside those module images and data-only pages are not selected. Captured code may still include packed or virtualized material. A manifest marked complete within this selection is not a claim that the whole program was recovered.

Capture files stay local and are ignored. Future analysis must verify their digests, target identity and actual code restoration before using them as a reconstruction reference.
