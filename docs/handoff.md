# Continue from here

Read `status.md`, then choose a task from `roadmap.md`. The current blocker for gameplay code recovery is actual Windows runtime evidence. The user has a Windows system where this exact game normally runs.

## First useful Windows task

Review and validate `windows-capture/capture-client.c` on Windows x64 against the pinned client. The helper identifies `main.exe` by SHA-256, opens the process for query/read access, and saves executable image regions from main.exe, IGC.dll and RGS.dll. It leaves the process running and writes a manifest with region digests and limitations. Build/smoke success under Wine does not prove native game capture.

Keep the capture local. Validate every file against `capture.json` before importing bytes into analysis. Live reads are not an atomic snapshot. Private executable allocations outside the selected image regions are not captured. Establish actual code restoration and build identity before declaring an unpacked program.

## Existing local artifacts

On the original workstation the lab directory is `main-exe-study`. Its ignored paths retain:

- `input/main.exe`: exact original analysis copy.
- `evidence/loader-recovery/recovery.json`: compression chunk mappings and identities.
- `evidence/loader-recovery/themida-decoded.bin`: 41,984,000-byte protector layer.
- `evidence/loader-recovery/emulation-04/`: corrected STOP-at-import trace and overlays.
- `evidence/rea-*.json`: full REA outputs, including failures and limitations.
- `asset-recovery/verified-v2/`: image scan manifest and selected exports.
- `model-recovery/verified-encrypted-v2/`: corrected complete model scan and selected exports.
- `runtime/`: isolated client copy and startup logs.

A GitHub clone contains source and reviewed summaries, not these artifacts. Reacquire private inputs or work on independent format/tests tasks when the lab data is unavailable.

## Traps already investigated

- The first unpacked layer is still the protector. Its matching size/hash does not establish gameplay recovery.
- Default Ghidra whole-region analysis exhausted a 2 GiB heap. A 4 GiB profile with two analyzers disabled completed, but returned short obfuscated call wrappers.
- An early emulator run treated unresolved IAT values as callable addresses and fell into zero data. Emulation-04 corrected this with STOP-only traps. The earlier run is not decryption evidence.
- V15 model payloads can leave a full sixteen-byte alignment trailer. Preserve it, retain block alignment, and validate the complete model structure.
- The original Mac filesystem is case-insensitive. Use file identity to deduplicate selected aliases such as Player.bmd/player.bmd.
- GitHub counts are not game-recovery percentages. Track proof for functions and behaviors, not a speculative overall completion number.

## End a work session

Record the branch/issue, change, input digest, decisive addresses/offsets, checks run, ignored artifact locations and next action. Update only the relevant findings, `status.md` and this handoff. Keep credentials, proprietary payloads and process dumps out of the repository.

## Original lab versus GitHub checkout

The original lab retains an archival local `lab/bootstrap` branch. The published
GitHub `main` branch is the collaboration baseline. For new development, clone
that repo or fetch and switch to `origin/main` once local Git authentication is
configured; preserve ignored lab artifacts separately.
