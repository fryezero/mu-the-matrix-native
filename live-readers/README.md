# Live-state readers

Small macOS command-line tools that copy, read-only, selected state out of a running `main.exe` (the original
Windows client, running in Wine on the same Mac). The native reconstruction uses these snapshots to check its
results against the real client: object lists, scene globals, lighting inputs, static tables and the text tables
the client decrypts from `Data\Lang.mpr`.

| Tool | Reads | Used by |
|---|---|---|
| `objread` | the static-object sector lists, plus a fixed list of scene globals | [client-objects](../docs/research/client-objects.md), [client-login-scene](../docs/research/client-login-scene.md), `scripts/live_objects_to_plain.py`, `scripts/live_object_state.py` |
| `memread` | fixed address ranges named on the command line | [client-path](../docs/research/client-path.md) |
| `lightread` | the lighting inputs of the model draws | [client-model-light](../docs/research/client-model-light.md), `scripts/validate_model_light.py` |
| `langread` | the tables built from `Data\Lang.mpr` (optional extra nodes/maps; `graph:` pointer closures from a root or a pointer path, NATIVE-SKILL-003) | [client-lang-tables](../docs/research/client-lang-tables.md), [client-quests](../docs/research/client-quests.md), `scripts/live_lang_to_plain.py` |
| `rtsample` | post-draw temporal summaries (sums/counts only) of camera, objects, pools, lights, bracketed by WorldTime and the logic/frame counters; `rtinput/` is its Wine-side input replay (mingw, `SetCursorPos`/`SendInput` only) | [client-render-time](../docs/research/client-render-time.md), `scripts/render_time_live.py` |

```sh
make live-readers                 # or: make -C live-readers objread
live-readers/build/objread <main.exe pid> snap.bin
```

`langread PID out.bin graph:0x06fbb8ec=0x44,10,0 graph:0x01d22c0c/0x1f8/0=0xfc,3,0x100` copies 4ThTreeData's nested
maps and the SkillTree4th handler (a path `A/B/C` is `[[A]+B]+C`). It follows only maps, vectors and strings, or with
the third number any pointer (that many bytes), and only into read+write memory or main.exe's uninitialised data
([client-skills section 12](../docs/research/client-skills.md#12-the-fourth-tree-native-skill-003)).

Rules:

- Point them only at a client you started yourself, under the shared game lock. They use
  `mach_vm_read_overwrite`: they never write, suspend or inject.
- Each binary is ad-hoc signed with `debugger-entitlement.plist` so `task_for_pid` works on the Wine process.
- Snapshots contain decoded game data. They stay local (ignored paths) and are never committed.

Running the client on the Mac is covered by the separate Wine-track repository,
[mu-the-matrix-mac](https://github.com/fryezero/mu-the-matrix-mac). These readers moved here from its
`mac-play/diagnostics/` directory when the two tracks were split (history is preserved: `git log --follow`).
