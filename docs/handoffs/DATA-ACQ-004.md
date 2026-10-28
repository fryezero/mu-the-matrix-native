# DATA-ACQ-004, Native Data manifest slice

Implemented on `codex/data-acq-004` in its assigned isolated worktree.
[Finding](../research/native-data-manifest.md), [re-acquisition procedure](../native-data.md).

- One portable C++17/Crypto++ manifest engine serves the native command-line
  consumers and the app's bundled, signed `mu-native-data` helper. No Python
  runtime dependency returns to the app.
- Manifests record the pinned executable hash, producer version/options, exact
  source input hashes and output inventory. Root manifests cover the component
  manifests, and component checks recurse. Incremental exports retain earlier
  input provenance. Publication uses an atomic manifest rename.
- Setup verifies imports and existing sets before changing them, records first
  conversion inputs, and refuses legacy, mismatched or incomplete data. `--force`
  cannot relabel a bad set. Optional components can be absent at acquisition;
  missing files from a recorded component fail verification.
- Portable manifest tests: 12 pass, including the language export and native
  consumer boundaries; 3/3 planted mistakes caught. App tests: 14, 13 pass and
  one explicit private smoke skip. Temporary-HOME tests create manifests without
  Python and refuse mismatches through setup/plan/smoke without starting a client.
- Production-pin signed app, temporary HOME/CFFIXED_USER_HOME, empty environment
  and PATH without Python: 179 movies and 82 NaviMaps converted, root/component
  manifests verified. All 261 output hashes equal DATA-ACQ-003's app-option
  corpus. A changed build field is refused before any native client starts.
  Optional captured data was absent in this run; the installed owner data was
  read-only and was not retroactively stamped.
- Initial full local macOS gate: 1,310 tests, 1,155 pass and 155 explicit skips;
  viewer and read-only-reader builds pass; publication audit rejects zero files.
  Final integrated gate on `07637bc`, including layout, session verification,
  item rendering and terrain milestones: 1,349 tests, 1,192 pass / 157 explicit
  skips; 2/2 fixture scenarios; viewer/readers builds and audit of 1,172 staged
  files pass, zero rejected. Fixture proof is archived in external scratch
  under `final-fixture-report/`.
- Standalone GFx window and audio-live consumer builds also pass. No reconstructed
  client algorithm or converter output was intentionally changed.

Logs, production first-run data and per-file comparisons remain local under
`~/Documents/MTM/mu-mac-tools/native/scratch/data-acq-004/`.
No original client or launcher was started, stopped or driven. No network,
protection, account or live-service work was performed.

Remaining: the jump-table diff tool depends on paused NET-DISPATCH-001 and is
explicitly outside this manifest slice. Guided capture packaging and second-user
reproduction remain DATA-ACQ-002/CAPTURE-KIT-001. A new build needs validated
re-pinning and a supporting native release before acquisition. Manifests detect
integrity drift; they do not independently attest a historical snapshot's
origin or claim full gate-5/cross-user deployment completion.
