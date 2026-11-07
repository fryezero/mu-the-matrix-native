# The Muun effect table's consumers and Uruk's weather-driven effect

Target: Mu The Matrix `main.exe`, SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`; pinned text
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` (base `0x00401000`), image data
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`, third section `0x01ced000` (capture 04,
`0571c519…1c6f`). This closes the two consumers [016](client-render-effects-016.md) and
[017](client-render-effects-017.md) left open because "their inputs are missing": the Muun table's `0x0114203d`
(RENDER-EFFECTS-008 exported its 16 records) and Uruk Mountain's keyed effect 0x806e/12 (RENDER-EFFECTS-011). The
validators compare native code with the pinned client on the same input, so synthetic owner and weather fixtures
decide the domain; no live client session was needed or taken.

Evidence labels: **verified** = equal to the client's instructions under Unicorn
(`scripts/validate_render_effects18.py`); **static** = read from the disassembly; **live** = from existing
read-only captures.

## 1. The Muun table and the OBJECT fields its consumers read (verified)

**Table.** MuunEffectInfo (`0x06fbb46c`, loaded from `Data/Lang.mpr` by `0x00aed7c3`) keeps at `+0x38` a
`std::multimap<int, entry>`: node `+0x10` the key (a Muun's render-info id), `+0x14` the path `std::string`, then
position, rotation, scale, bone and the follow byte at the same offsets as the map-object entries of 008 (value
`+0x1c`, `+0x28`, `+0x34`, `+0x38`, `+0x3c`). The local export holds 16 records under 15 codes (363 twice, in file
order); their bones are 3, 5, 26 and 50, follow 1 except 183/184.

**Who attaches.** The table's only reader is `0x0114203d`, called only by the Muun slot method `0x009af699`.
That method runs from the slot's setup (`0x009a9992`, after `0x009ab41e`/`0x009a9c88`) and from the manager's
refresh (`0x009ba824`, right after the clear `0x009af6f6` at `0x009ba80a`, for each of a character's three slots
MainMuun/SubMuun/HeroMuun). The slot fields it reads:

| Field | Read by | Meaning |
|---|---|---|
| slot `+0x08` | `0x009af6a3`, `0x009af6e6` | the Muun OBJECT (null: nothing) |
| slot `+0x04` | `0x009af6ac`, `0x009af6cb` | the owning CHARACTER (null: nothing) |
| slot `+0x0c` | `0x009af6b5`, `0x009af6de` | the render-info record; its first int32 is the table key |
| slot `+0x10` | `0x009af6c0` | a byte that must be set |
| slot `+0x1c` vs owner `+0x3244` | `0x009af6d6` (owner key `0x009a1b49`) | ownership: only the owner's own Muun attaches |

`0x009af6f6` clears the OBJECT's effect list `+0x3d0` (`0x009b0451`) when OBJECT and owner are set.

**The consumer `0x0114203d(object, code)`** (this = MuunEffectInfo): `equal_range(code)` (`0x00aed702`, signed
`std::less<int>`), and for every entry in order the factory `0x00a797a0(path, position, rotation, scale, template
transform 0, &type word 0, tint 0, an empty action vector (0x0095e433), start frame 0.0)`; a valid effect
(`0x00a78918`) is attached with `0x0129f9c6(effect, bone, follow, timed 0, lifetime 0.0)`; the factory's pointer is
released (`0x00965b01`) either way. Unlike 008's table walk there is no first update at attach and no type word.

**The OBJECT update `0x0129f671(dt)`** moves the attached records with the OBJECT every frame (RenderObjects'
calls `0x016d51f5`/`0x016d536b`; for a Muun the slot method `0x009a9ae2` calls it at `0x009a9c35` with the slot's
OBJECT `+0x08`). For each record of the `+0x3d0` std::list (node `+8`: effect
pointer, `+8` template scale, `+0xc` bone, `+0x10` follow, `+0x11` timed, `+0x14` lifetime):

- **Lifetime:** a timed record loses `dt` and leaves the list (`0x012a1417`) when `0 >= lifetime` (NaN stays).
- **Scale:** the effect's `+0x50` (`0x012a0d5c`) = template scale × OBJECT scale `+0xa0`.
- **Matrix**, then the node update `0x00a75708(dt, matrix, OBJECT)`:
  - follow, bone −1: the OBJECT's world matrix `0x0129faee` (angle `+0x164`, position `+0x158`, scale; 007);
  - follow, bone ≥ 0: `0x0129fd4f(bone)`: the bone's 3x4 transposed to a column-major 4x4; outside a sector list
    (`0x012a0d29`: `+0x350` and `+0x354` both 0, as for a Muun) it is placed by `0x00cf2679(position, (0, 0, 0),
    scale) × bone` (`0x00cf0db8`);
  - follow, bone below −1: the matrix is never initialised (`0x00a7497a` constructs nothing); undefined, refused
    natively;
  - no follow: the scale's diagonal (`0x00cef956`) with the translation `+0x158` for bone −1, `0x012a0030(bone)` =
    the bone's translation (+ the position outside a sector list, without the scale) for bone ≥ 0, none below −1.
- **Posed bone transforms** (`0x0129f12c`): the OBJECT's own transforms `+0x318 + 0x30·bone` when its model
  (GetModel of the type `+0x5c`) exists, `+0x318` is set and `bone` is below the model's count (int16 `+0x22`);
  otherwise the shared pose buffer `0x06fce398 + 0x30·bone`.

So the OBJECT fields the Muun path reads are: `+0x5c` type (model and bone count), `+0xa0` scale, `+0x158`
position, `+0x164` angle, `+0x318` bone transforms, `+0x350`/`+0x354` sector links and the `+0x3d0` list; the
owner's `+0x3244` and the slot's `+0x04..+0x1c`.

**Native.** `reconstructed/objects/muun_effects.c` ports `0x0114203d`, `0x009af699`, `0x009af6f6` and `0x0129f671`
with its bone helpers through ops. `native/core/mu_muun_effects` loads `MU_LANG_DIR/muuneffects.tsv` and keeps an
owner's list: the slot refresh creates the effects through an EffectManager scene (`mu_effect_scene_create`, the
template scale is the instance's scale), the update hands each instance its scale and external matrix and runs its
node update. With the installed data all 16 records load their `.ein` templates, attach, and follow a fixture
pose for 30 frames (480 node updates), every external matrix equal to the reconstruction.

**Validation.** `muun_attach` (random multimaps: duplicates, negative and extreme codes, empty tables, inline and
heap paths, invalid templates), `muun_gate` (owner/OBJECT/record present or null, the byte, matching and other keys),
`muun_update` (one to eight records per OBJECT: bones −7..63 including the model's count and the four the table
uses, follow 0/1/2/0xff, timed lifetimes around `dt`, own and shared bones, in and outside a sector list, model
present or absent) and the private `muun_records` (the 16 decoded records, every code and absent neighbours, valid and
invalid templates). The client's list helpers, erase, matrix routines and sector predicate run as client code.

**Found, not changed (static + verified client side):** the native map-object update (`o_ein_update`,
RENDER-EFFECTS-008) places an unfollowed record at the OBJECT position, while the client, for a map object in a
sector list, uses `0x012a0030`: the shared pose buffer's bone translation without the position. 19 of the 758
map-object table entries are unfollowed. Changing it would change world captures, so it stays a named gap (the
client side of this path is covered by `muun_update`'s in-sector cases).

## 2. Uruk's weather word `0x01cf15ec` (static + live)

`0x01cf15ec` is the first int32 of a four-word event state in the data section: `0x01cf15ec` a type/state value,
`0x01cf15f0` a world, `0x01cf15f4` a counter, `0x01cf15f8` a float step.

| Role | Address | What |
|---|---|---|
| initial value | data image | `-1, -1, -1, -1.0f` (third-section capture 04, taken before login) |
| reset | `0x017ebfd2` | all three words -1, the float from `0x01a7e4ec`; called when an event object's action ends (`0x009db4d0`, `0x009db672`, `0x009db814`) and by `0x017ec3bc` |
| set | `0x017ebffc(world, value, counter, step)` | from server handlers: `0x00d52517` (36, 20, 1), `0x00d53216` (1, 40, 1), `0x0127edb4` (36, 0, 1), and `0x0127edf3` in worlds 100/101: value = (packet byte +5 == 0) ? 1 : 0, counter 0, step −1 |
| read | `0x00e70014`, `0x00e7023c` | Uruk's RenderObjectVisual, types 108 and 109: acts on `== 1` only |
| read | `0x017ec03b`, `0x017ec0d5`, `0x017ec149` | the event objects' update `0x017ec026` (returns at once in worlds 100/101) |

**The default without a server event is −1** (static: the data image at `0x01cf15ec`; live: DATA-ACQ-002's 32
`-mem-01cf15ec.bin` reads are all `ffffffff`). In Uruk, the handler `0x0127edf3` is the writer that can make
it 1 there besides `0x00d53216` (which writes 1 for whatever world is current); both are server handlers, ported
here only as fixture values, not as handlers. The native field (`mu_objects_runtime.uruk_weather`)
now starts at −1 instead of 0; both are off for the reader, so no world changes.

**The reader** (`uruk.c`, RENDER-WORLDS-I) is compared over every value it distinguishes: −1, 0, 1, 2, 36 and the
int32 extremes (`uruk_reader`). Two planted mutants show why the domain matters: `weather > 0` is caught only by 2
and 36, `weather != 0` only by the −1 default.

## 3. The keyed effect 0x806e/12 and its flames (verified)

Type 108 with the word at 1 (and `rand % 2 != 0`, after its two particles, then `rand % 3 != 0`) asks for CreateEffect `0x013c0eaa(0x806e, position,
angle, (1, 1, 1), 12, the object, −1, 0, (u16)(int)(cos(rand) + 0.5), 0, 0.0, −1, 0, 0)` (`0x00e7022f`).

| Part | Address | Behaviour |
|---|---|---|
| create | `0x013c4a45` (0x806e's case `0x013c47b3`) | LifeTime 20, then the common code |
| move | `0x01439417` (case `0x014388c6`) | each step one particle at position + ((rand % 50 − 25), (rand % 50 − 25), (rand % 10 + 5)), scale (rand % 5 + 13) × 0.05 × the effect's scale, the effect's angle and light, no owner: rand % 3 → 0x8084/1, 0x806e/5, 0x8085/1 |
| render | RenderEffects `0x0151898f` → `0x01519939` | nothing drawn (0x806e is a bitmap index, no model) |

The particles are separate branches of their bitmaps' subtype chains, shaped like the Karutan flames:

| Kind | Create | Move | Render |
|---|---|---|---|
| 0x8084/1 | `0x015d41ab`: LifeTime rand % 5 + 20, scale (rand % 72 + 72) × 0.01 × scale, rotation rand % 360, rise (rand % 24 + 74) × 0.1, alpha 0, colour kept, light 0 | `0x0164669e`: below LifeTime 20 alpha − 0.2, else up by (rand % 2 + 2) × 0.1 to 1; dead below 0.1 or at scale ≤ 0; light = colour × alpha; scale − (rand % 2 + 4) × 0.01; rises; turns 3 | 0x8084's sprite `0x015a439f` |
| 0x806e/5 | `0x015b8f64`: as above with LifeTime rand % 5 + 24 | `0x01625e90`: dims below 15, shrinks (rand % 2 + 5) × 0.01 | 0x806e's sprite `0x01597633` |
| 0x8085/1 | `0x015d9089` (rand % 5 + 34) | `0x0164b839` (below 15, (rand % 2 + 6) × 0.01) | RENDER-EFFECTS-010's Demon flame (`pet_kinds.inc`) |

`reconstructed/combat/uruk_fx.inc` ports the effect, `reconstructed/particles/uruk_flames.inc` the two new kinds.
The native objects runtime now hands the keyed event to the owned-effect hook (owner = the object, word4 = the
key) instead of counting it refused.

## Still open

- **A native Muun OBJECT:** created only by the server's Muun packets (`0x01219294`, out of scope); its model
  (`Data/Item/*pet*.bmd`), follow logic and pose are not ported, so no native scene draws the 16 effects yet. The
  consumer, the update and the requests are native and verified; a later Muun port only has to call them.
- **The Muun OBJECT's owner fields** (visibility and the other owner bytes the effects read, 006's `ein_owner`) are
  not modelled for Muun owners.
- **The map-object update's unfollowed records** use the position instead of the shared pose's bone translation
  (§1).
- **Uruk's server value:** the native world keeps −1 unless a caller sets the field; no packet handler is ported.
- Uruk (100) still has no capture, so the effect is checked by the instruction comparison and the native hosts only.

The exact counts and wall times are in the [handoff](../handoffs/RENDER-EFFECTS-018.md).
