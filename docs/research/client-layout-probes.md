# Client record offset probes

LAYOUT-PROBE-001, 2026-10-27. Read-side research using existing captures only.
No client process was opened, driven, suspended or written.

## Source and method

`scripts/probe_layout.py` checks the whole restored text against `scripts/pins.py`'s TEXT pin,
SHA-256 `2bd5f2e9…3724`, base `0x00401000`. The second-section pin used by the unchanged
validators is DATA, `c985e2e6…a0672f`, base `0x01a7c000`. These are compatibility-environment
captures, not native Windows evidence. The script reports the full text digest.

Each probe executes one original load in Unicorn with explicitly seeded synthetic base/index
registers. A memory hook checks the exact read address and width as well as the returned value.
Four independent byte patterns distinguish nearby fields. For arrays every index 0..928 is
exercised. This is VERIFIED offset/width evidence for the bounded load; it does not prove a
whole routine, caller provenance, allocation size or every semantic interpretation.
The surrounding routines below were read statically with Capstone.

## OBJECT live and the fade flag

| Field | Original read | Result | Evidence |
|---|---|---|---|
| `live` | IsLive `0x0095f977`, load `0x0095f981` | u8 at +0x00 | VERIFIED |
| `fade_flag_08` | death fade `0x013a5ea1`, load `0x013a6086` | u8 at +0x08 | VERIFIED offset; authored neutral name |

These are distinct fields. The fade routine calls SetLive `0x0129f4a5` at `0x013a6019`,
then separately clears +0x08 at `0x013a6028`, and subsequently tests +0x08. Treating that
second byte as the shared IsLive field loses the distinction. Combat's damage-point pool
also uses +0x08 for its own live byte; those are point records, not OBJECT records.
The existing combat comparison seeds/tests the fade byte and stubs SetLive, so its success
never established that OBJECT's shared live getter reads +0x08. No reconstruction is changed.

## CHARACTER levels

| Field | Original read | Result | Evidence |
|---|---|---|---|
| `scene_level` | start loading `0x0185a75a`, load `0x0185a89c` | u16 at +0x144 | VERIFIED |
| `label_level_14e` | name/label routine `0x00b3c4e7`, load `0x00b3c5c7` | u16 at +0x14e | VERIFIED offset; interpretation STATIC |

The scene reads +0x144 and passes it to SetLevel `0x00a00031`. The label branch reads
+0x14e, adds 600 at `0x00b3c5ce`, and formats a name obtained by `0x0129deaa`. Thus the
fields cannot be collapsed into one universal `level` accessor. The players header's
unqualified +0x14e label is insufficient to override the scene evidence. The manifest keeps
two names; the meaning of the label branch's level component remains STATIC. The existing
players validator does not compare this member, so its passing cases do not settle its meaning.

## CharacterAttribute extent

| Field | Original read | Result | Evidence |
|---|---|---|---|
| learned count | `0x00a002a9` in `0x00a00287` | u8 at +0x1e4 | VERIFIED |
| skill ids | `0x016969f8` in IsSkillReady `0x016969e9` | u16 at +0x1e6 + index*2 | VERIFIED load; capacity STATIC |
| timers | `0x01696e6c` in tick `0x01696e06` | i32 at +0xccc + index*4 | VERIFIED load; capacity STATIC |

The skill table capacity used by the existing reconstruction is 0x3a1; the tick explicitly
compares its count with 0x3a1 at `0x01696e1b`. The learned count is a byte, so the current
count-controlled loop cannot reach every synthetic index exercised by the load probe.
Skill storage ends at exclusive +0x928. Timers extend to exclusive +0x1b50 under that
capacity. **0x200 is a progress-only prefix, not a recovered full allocation size.**
LAYOUT-001 must describe at least the known +0x1b50 extent and label the size STATIC/minimum.
No claim that this is the complete allocation is made. Gaps are unknown bytes, not padding
proved by the client. The progress routines may continue using their bounded 0x200 prefix.

## Reproduction and results

```
./tools/python/bin/python scripts/probe_layout.py --mutations --report <private>/probes.json
MU_RECOVERY_INTEGRATION=1 ./tools/python/bin/python -m unittest discover -s tests -p test_layout_probes.py -v
```

7 families, 7,452 bounded load cases, zero mismatches. All 7 competing offset/prefix
hypotheses differ from the observed reads or values. These controls change the comparison
hypothesis, not original instruction bytes. They do not substitute for the unchanged
reconstruction validators' planted C mistakes.

Affected validators were rerun unchanged: charsel, combat, players, progress, scene and
ground items. Counts and the local macOS gate are recorded in
[the milestone handoff](../handoffs/LAYOUT-PROBE-001.md). Local reports live under
`~/Documents/MTM/mu-mac-tools/native/scratch/layout-001/`, never in Git.
