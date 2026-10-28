# Validation loader follow-up, VERIFY-HARNESS-002

The bounded question is whether `map_client_window.py` and `model_hierarchy_common.py` can use
`scripts/pins.py` without changing their metadata, reconstruction checks or failure contracts.
This is an offline maintenance change. It adds no reconstructed client behavior.

## Inputs and method

The installed restored text is 23,572,480 bytes at `0x00401000`, SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
The second image section is 2,557,764 bytes at `0x01a7c000`, SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
Both belong to target main.exe SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
The executable itself is not needed or read.

Baseline `origin/main` is `5d35f5d`. Before editing either tool, run its installed-capture callers
and retain their reports locally. Repeat the same commands after migration, using the same Python,
Capstone and input files. Compare complete report bytes and all published metadata constants. Six reports are byte-identical;
the widget and character-select reports differ only in their elapsed `seconds` fields. All eight
results, eleven metadata constants and five recorded failure outcomes agree.
The [handoff](../handoffs/VERIFY-HARNESS-002.md) records both sets of report hashes and check counts.

## Compatibility boundary

The old public constant names and helper signatures remain available. Their values come from the
existing pins. The shared loader checks successful reads. Small local adapters preserve native
missing-file errors, the hierarchy helper's separate size and digest messages, and the mapper's
argparse mismatch exit. A rejected hierarchy input is read again only to construct its existing
detailed error message. Successful inputs are read and checked once.

The reconstruction logic, heuristic confidence labels, region bounds, output refusal and all caller
assertions remain unchanged. No shared machine, manifest row, loader/protection script, item/combat
extractor or audio table is changed. Installed Wine DLLs support the unchanged static frame/render
checks; no game process or original installation is accessed.

## Remaining work

Eight entries remain in `tests/test_pins.py:UNMIGRATED`: the combat/item/audio extractors and five
protector-loader scripts. They are outside this milestone. Shared Unicorn machine consolidation
also remains separate implementation work. Historical missing-input failures in VERIFY-HARNESS-001
were addressed by INTEGRATION-GREEN-001 and are not reopened here.
