# README comparison media

These six existing captures were selected for the main README on 2026-10-20 at the owner's request.
They were copied unchanged from the local native render collection. No new screenshots, GIFs,
composites or resized images were made. The original sources remain local and unchanged.

| File | Source relative to the local native `renders/` directory | Contents |
|---|---|---|
| [login-live-vs-native.png](login-live-vs-native.png) | `light/after/compare-client-gl.png` | Live client above, native OpenGL scene below. |
| [character-select-live-vs-native.png](character-select-live-vs-native.png) | `charsel2/compare-live-gl.png` | Live character-select above, native scene below; different character and gear. |
| [lorencia-live-before-after.png](lorencia-live-before-after.png) | `light/lorencia/compare-live-before-after.png` | Live above, native lighting before in the middle, native lighting after below. |
| [native-inventory.png](native-inventory.png) | `gfx3/world/world-inventory-models.png` | Native GFx HUD and inventory with demo data. |
| [native-login.gif](native-login.gif) | `login/client-gl-anim.gif` | Existing native login animation, earlier lighting revision. |
| [native-character-select.gif](native-character-select.gif) | `charsel2/after-anim/anim.gif` | Existing native character-select animation. |

The live captures are the original Windows client running through Wine on the Mac, not native
Windows captures. The native captures are offline reconstruction demos, not live-server sessions.
These are milestone snapshots with different characters, UI data and effect phases, not matched-frame
pixel-equivalence tests. See the linked research reports in the main README for controlled comparisons.

The publication audit pins each file's path and SHA-256 in `scripts/audit_repository.py`.
Replacing a capture requires another explicit review. This narrow documentation-media exception
ships no executable, game asset pack, decoded model, texture source or process dump.
The game imagery retains its owners' rights and is not covered by this repository's MIT license.
