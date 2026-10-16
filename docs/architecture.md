# Architecture and recovery boundaries

The repository currently builds recovery tools and source components. It has no recovered game loop or native-client executable target yet.

| Module | Interface | Responsibility |
|---|---|---|
| `reconstructed/boot` | `mu_decode_block` in `decoder.h` | Bounded byte decoding with explicit consumed/written lengths; portable C |
| `reconstructed/client-memory` | `mu_copy64_forward_words` in `copy64.h` | Observed sixteen-word copy for valid spans and DF clear; portable C |
| `reconstructed/record-math` | `mu_record_cofactor`, `mu_record_inverse` | Experimental ordered arithmetic with explicit FP/aliasing limits |
| `reconstructed/model-codec` | `mu_bmd12_decode`, `mu_client_lea_setup`, `mu_client_lea_decode` | Client-linked rolling decoder, LEA context setup and batch ECB; portable C |
| `asset-recovery/recover_images.py` | `decode(path)` | Recognized wrapper removal, image validation, pixel-preserving exports |
| `asset-recovery/recover_smd.py` | `unwrap_smd`, `validate_payload` | Observed text-mesh subset with original payload preservation |
| `model-recovery/bmd10.py` | `parse_bytes`, `pose_matrices`, `obj_text` | Checked mesh, index, bone and animation records; recorded-pose geometry |
| `model-recovery/bmd_encrypted.py` | `parse_model`, `parse_model_file` | Version-specific envelope decoding into the validated model layout |
| `model-recovery/lea256.c` | `mu_lea256_decrypt` | Optional native accelerator, compared with Python and public vectors |
| `windows-capture` | Console helper + JSON manifest | Windows process-region acquisition for later analysis |
| `scripts` | Local CLIs | PE inspection, REA collection, loader provenance and bounded emulation |

Source bytes and provenance belong at acquisition boundaries. Readers validate counts, ranges and references before producing reusable data. The C routines use caller-owned buffers. Decoders report bounds failures; the observed fixed-size copy has explicit accessible-span preconditions. Python-only fallback keeps model decoding usable without a native library.

## Future engine work

Only recovered and behavior-checked functions should graduate into runtime modules. Establish which code owns assets, simulation, network messages, UI, input, rendering and audio before choosing new interfaces. Keep original Windows behavior as the reference during reconstruction.

A macOS implementation will need explicit replacements for confirmed Windows dependencies. Graphics, window/input handling, audio, filesystem conventions and networking are likely areas to inspect, but their final interfaces and technologies are undecided. Do not select a complete engine or claim a port merely because an asset viewer runs on macOS.
