# Pose-builder callers, animation tick, CPU skinning and mesh draw

CLIENT-SKIN-001 / issue #53 follows the pose builder `0x012b5064`
([finding](client-pose-builder.md)) outward in both directions:

* Callers. All 314 raw call candidates are read and classified. The animation
  tick `0x012b4dd3` sets the prior frame and action. A root setter `0x012b7019`
  explains how the keep-root flag is used. This part is static only.
* Consumers. The builder's bone matrices feed the model transform
  `0x012b5bde`, the client's CPU skinning. Its outputs are submitted by the
  mesh draw routine `0x012b8d1d`.

Authored C for the transform and the tick runs against the actual client
instructions under Unicorn. It matches 226 synthetic transform calls, 24
synthetic models chained through the actual pose builder, 481 synthetic tick
calls and 903 direct vector-helper calls. Every installed model the readers
accept also matches: 11,962 transform calls, run after the actual bone-track
loop and the actual builder, covering 3,814,006 vertices and 3,988,165 normals,
plus 35,871 tick calls. All four negative controls fail.

The draw routine was not executed. Its GL call order is documented statically,
against import slots named from the guest's Wine `opengl32.dll`. Live game state,
the action-change code and native Windows behavior remain unverified.

## Identity

| Input | Bytes | SHA-256 |
|---|---:|---|
| `main.exe` (target identity) | | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09) | 23,572,480 | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | 2,557,764 | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |
| Trig dispatch flag `0x0bdd1cc8` (value 1) | 4 | `67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450` |
| Debian `libwine_8.0~repack-4_i386.deb` (matches the bookworm i386 `Packages` index) | 95,293,888 | `c992aad6a47d81b719514f5d06c5df10267f1e40a6f4f3b4e3f655cbbf308d57` |
| its `i386-windows/opengl32.dll` (preferred base `0x7a800000`) | | `6e10ea17cd63f1fec97f37b1c00a902028c82674231cd477d7a857f72cd7b394` |
| its `i386-windows/glu32.dll` | | `d75036023e994eaecf6b9cb7ba74ae4a9dfcb7ee84597db1b5f32d1f2e0499b1` |

The guest that captured the text and data ran Wine `8.0~repack-4` (`wine32:i386`,
`evidence/x86-guest-setup.txt`). The package's own signature chain (Release file)
was not checked; only the `Packages` hash was. The DLLs are untrusted third-party
data. They live only under ignored `evidence/client-skinning/`. They are parsed for
export tables and never executed.

Pinned bodies. Capstone 5.0.9 linear decodes land exactly on the end and on the
stated `ret`:

| Body | Range | Instr. | SHA-256 |
|---|---|---:|---|
| Model transform, `ret 0x30` | `0x012b5bde..0x012b678d` | 908 | `a546b109d885d267c1269b62cf2cdf694ee0d8faf3440979ffe7fa03f38bd2e9` |
| Animation tick, `ret 0x18` | `0x012b4dd3..0x012b5064` | 180 | `047f50df9bf736daaef507c39d40f76b5673583bb2b831453ed61b39d3ae2d20` |
| Vector inverse rotate | `0x00cfff3c..0x00d000ad` | 144 | `6a3b8bb624c91270b9addd94ea2eb205cb69eb76d51c4c902737ee78fb187102` |
| Vector rotate | `0x00d000ad..0x00d0021e` | 144 | `250728dccd9ba7c60811122d82c62c8c8fc75f6290e408746f4fde439603c457` |
| Vector transform | `0x00d002b2..0x00d0045e` | 168 | `697638c67f6e7da903ef069c8051ad5ecdecc7c044945b4765311712066205ca` |
| World test (`== 30`) | `0x0095fb7c..0x0095fb99` | 11 | `5efade7b9656bcf9c3e241d01671c49cd7bd236b4f33cbf1d000918426609a0c` |
| Scene-state getter (`return [ecx]`) | `0x009b0bc1..0x009b0bcf` | 8 | `60e1dbe0e4e756e1dcd216bd8343b4442a04af8747bb16c427db7e71fe4af490` |
| Mesh draw, `ret 0x2c` (static only) | `0x012b8d1d..0x012bb35a` | 2,713 | not executed |

The transform makes eleven listed direct calls plus 33 element-accessor calls,
all to `0x00cfc922`. The tick makes one call, to `0x009b0bc1`. The validator
requires exactly these calls, the fifteen binary32 constants it uses (1.3, 2.0,
0.5, -1, 1, -45, -1.5, -0.5, 1.8, ±999999, 0, 0.8, 0.2 and 0.01) and the earlier
builder, bone-track and helper pins.

## 1. Pose-builder callers

`scripts/client_render_static.py` reads every raw `E8` candidate of the builder.
For each one it takes the nearest preceding `PUSH EBP; MOV EBP,ESP` whose linear
decode lands exactly on the call with no `RET` in between. It then reads the eight
pushed arguments and ECX symbolically, inside the call's basic block.

All 314 candidates sync, in 105 functions. None needs a wider window. The code
is unoptimized MSVC-style: every argument is reloaded from memory just before its
push, so the reading is direct. It is still a straight-line reading inside one
block, not a whole-function data-flow proof.

Names below are investigator labels. Offsets on the "object" are the caller's
per-instance record. The model (ECX) is a separate per-model record.

| Argument | Dominant source | Count |
|---|---|---:|
| output | shared bone buffer `0x06fce398` (otherwise: 8 from `0x0129f11a`'s return, 5 locals, 1 `0x075a6b58`) | 300 |
| frame | object `+0xd0`, or a local | — |
| prior frame | object `+0xd4` | 186+ |
| prior action | u16 object `+0x2c` | 202+ |
| angles | object `+0x164` | 208+ |
| head angles | object `+0x170` (or the angles vector) | 284 |
| keep root | `0`: 289, `1`: 24, byte from a struct: 1 | |
| translate | `1`: 201, `0`: 108, other: 5 | |

The "+" counts are the most common exact expression. Variants through other base
expressions, such as `[[arg+0x54]+…]` or `[[arg+0x34c]+…]`, add more.

Coarse classes, in `pose_callers.classes.state`:

| Class | Calls | Reading |
|---|---:|---|
| object fields | 117 | frame, prior frame, prior action, angles and head all from one object |
| object prior, computed frame | 140 | prior/action/angles from the object, frame from a local; 108 of these store `object+0xd0 - local` just before |
| prior = (int)frame - 1 | 19 | caller-chosen frame with the previous integer key as prior |
| bind pose | 12 | frame 0, prior 0, action 0 |
| other | 26 | other records (e.g. `[x+0xc]`, `[x+0x10]`, `u16 [x+8]` small records, `0x0129f11a` buffers) |

The 108 "object minus local" frames look like poses sampled behind the live frame.
That suggests trail or after-image effects, but it is an inference; the effects
themselves were not traced.

### Animation tick `0x012b4dd3`

There are 91 raw candidates in 42 functions, and all of them sync. 68 pass
`&object+0xd0`, `&object+0xd4`, `&object+0x2c`, a speed, `&object+0x158` and
`&object+0x164` from the object argument. Most of the rest pass the same fields
of a local or nested object. The tick is thiscall on the model and pops six
arguments. It never reads the last two.

```
loop = 1
if !frame_ptr || !prior_ptr || !action_ptr: return 1
if actions(+0x26) > 0 and current(+0xa8) >= actions: return 1
if actions == 0 or keys[current] <= 1: return 1
old = cvttss2si(*frame);  *frame += speed            # binary32
if old != cvttss2si(*frame):
    *prior_action = current                          # u16
    *prior_frame  = (float)old
if 0 >= *frame (ordered): *frame = (keys - 1.0) + *frame
if action.stop(+0):
    if *frame >= keys: *frame = keys - 0.01; loop = 0
else:
    limit = action.lock(+0xa) ? keys-1 : keys
    test = *frame + 2.0 if scene_state([0x01d1df70]) == 5
           else *frame + 1.0 if world([0x01cf15fc]) == 39 and current == 7
           else *frame
    if test >= limit: i = cvttss2si(*frame); *frame = (float)(i % limit) + (*frame - i); loop = 0
model+0xac = *frame;  model+0xb4 = (int16)cvttss2si(model+0xac)
return loop                                          # AL
```

**How a tick picks the prior frame and action.** The tick writes the prior pair
only when the frame's integer part changes. It stores the model's current action
and the old integer part. The builder then slerps from key `floor(prior)` of the
prior action to key `floor(frame)` of the current action, by the current frame's
fraction.

For speeds below one key per tick, consecutive keys are therefore blended
continuously, with the displayed pose one key behind the frame counter. Frame
4.2 shows key 3 blended 0.2 toward key 4. Frame 5.1 shows key 4 blended 0.1
toward key 5. At a wrap, the last key blends into key 0. This is inferred from
the two compared routines; the composition across ticks was not run as a live
loop.

Faster speeds skip keys: the prior is the old integer part, wherever it lies.
The code that changes an object's action, writing `+0x2a`, `+0x2c` and `+0xd4`
directly, was not traced. It sets the model's current action `+0xa8` from object
`+0x2a`, but only 58 of the 314 builder windows contain such a store. Elsewhere
the field is persistent model state.

**Keep root.** 25 builder calls pass a nonzero keep-root value: 24 immediate 1s
and one struct byte. Of these, 9 have a call to `0x012b7019` in the same block and
2 a call to `0x012b6ef1`. `0x012b7019` (thiscall, `ret 0xc`, args
`matrix, vector, out`) does two things when `matrix` is nonzero:

* it writes `out = model[+0x74] * rotate(vector, matrix)`;
* it copies the 3x4 `matrix` into the root global `0x078965ac`.

Callers pass a bone slot of another object's bone buffer
(`0x06fce398 + bone*0x30`). The builder then composes the attached model's root
bones under that matrix instead of rebuilding the root from its own angles. This
is the attachment path, for weapons and similar items on a parent bone; the item
names are an inference. Sixteen of the keep-root calls also pass the angles
vector as head angles, and 23 pass translate 1. The root-matrix writers for the
other 14 calls lie outside the call block and were not traced.

## 2. From bone matrices to submitted vertices

Raw immediate references show this data flow. Default-buffer wrappers pass fixed
globals:

| Stage | Routine | Callers (raw) | Buffers |
|---|---|---|---|
| Pose | builder `0x012b5064` | 314 / 105 functions | writes bones `0x06fce398` (`+i*0x30`), quaternions `0x075a90d8` |
| Skinning | transform `0x012b5bde` via `0x00966ea5` | 7 direct; wrapper 34 / 16 functions | vertices `0x078978a0`, normals `0x0812cce0`, light `0x06fd0918`; secondary light `0x075a9ee8` |
| Per-normal colour | inside mesh draw | — | colour `0x089c2120` = light x model `+0x54` |
| Submission | mesh draw `0x012b8d1d` via `0x00966e4a` | 23 direct; wrapper 6,361 / 485 functions | reads vertices, normals, light, texcoords |
| Body | `0x012bb35a` via `0x00966def` | 4 direct; wrapper 1,256 / 443 functions | glPushMatrix, mesh draws, glPopMatrix |

Per-mesh strides are fixed at `0x2bf20` bytes (15,000 x 12) for vertices and
normals and `0xea60` (15,000 x 4) for light values. The vertex and normal globals
are exactly 9,000,000 bytes apart, which suggests 50 meshes of 15,000 entries
(inference). Nothing in the transform bounds an index. No installed model has
more than 30 meshes.

The quaternion table has eleven raw immediate references, all in the two builders
`0x012b5064` and `0x012bcffb`. No other direct reader was found, so the table
looks like builder scratch (inference; a pointer-based reader is not excluded).
The secondary light table `0x075a9ee8` starts 0xe10 bytes after it.

### Transform `0x012b5bde` (CPU skinning)

The transform is thiscall on the model and takes twelve stack arguments (pops
0x30): `bones, vertices, normals, lights, bounds_min, bounds_max, box, translate,
vertex_scale, light_ambient, light_scale, light_minimum`. The `0x00966ea5`
wrapper fixes the three buffers. `0x012b5a0a` passes 0, 0.4, 0.4, 0.4 for the
last four.

```
if bones == 0: return
if model.lighting(+0x50):
    L = (1.3, 0, 2) if [0x01cf1048] else
        (0.5, -1, 1) and model+0x98.. = (0, 0, -45) if world([0x01cf15fc]) == 30 else (0, -1.5, 0)
    M = angle_matrix(model+0x98)                     # 0x00cff32a
    L1 = irotate(L, M);  L2 = irotate((1.3, -0.5, 1.8), M)    # transpose rotation 0x00cfff3c
if [0x0b437bfc] == 2: lo = (999999,)*3, hi = (-999999,)*3
for i < (int16)model+0x24:                           # mesh stride 0x20
  for j < (int16)mesh+4:                             # vertex: int16 bone, 3 floats
    v = out_vertices + i*0x2bf20 + j*12
    if [0x01cf104c] == 1.0:                          # bone scale, exact compare
        v = transform(vertex_scale != 0 ? vertex_scale*p : p, B[bone])   # 0x00d002b2
    else:
        v = rotate(p, B[bone]);  v[k] = v[k]*bone_scale + B[bone][k][3]
    if translate: v *= model+0x74                    # body scale
    if bounds mode 2: lo = min(lo, v), hi = max(hi, v)   # strict COMISS tests
    if translate: v += model+0x78                    # body origin
  for j < (int16)mesh+6:                             # normal: int16 bone, 3 floats, bind vertex
    n = out_normals + i*0x2bf20 + j*12 = rotate(normal, B[bone])         # 0x00d000ad
    if model.lighting:
        lights[i*0xea60 + j*4]     = max(light_minimum, dot(n, L1)*light_scale + ambient)
        [0x075a9ee8 + i*0xea60+j*4] = max(0.2, dot(n, L2)*0.8 + ambient)  # NaN kept
box origin = (mode 2 ? lo : bounds_min) + model+0x78
box axes   = diag(hi - lo or bounds_max - bounds_min); other axis entries = +0
```

Each vertex uses one bone, with no weights or blending. Normals are rotated by the
bone's 3x3 and are not renormalized. Translation, bone scale and body scale never
touch them. Light is a per-normal Lambert term against a fixed direction rotated
into model space by the transposed light-angle matrix, then scaled, offset and
clamped. All arithmetic is scalar binary32, in this order:

* rotate: `out[r] = (in0*m[r][0] + in1*m[r][1]) + in2*m[r][2]`;
* transform: adds `m[r][3]`;
* inverse rotate: uses column `r` instead of row `r`.

Each output component is stored before the next is computed, and the inputs are
reread each time. Aliasing is therefore sequential.

## 3. Authored source and comparison

`mu_model_transform` and `mu_animation_tick` are in
`reconstructed/model-codec/skinning.{c,h}`, built as `libskinning` together with
the bone-track loop, the pose builder and record-math. Record-math gains
`mu_vector_rotate`, `mu_vector_transform` and `mu_vector_irotate`. The light-angle
matrix uses `mu_angle_matrix` with host sin/cos. That is the same substitution as
in the pose builder, and binary32 results agree in every observed call.

`scripts/validate_skinning.py` runs the actual transform, tick and vector helpers
in Unicorn over the full text, the full second section, the four flag bytes, a
stack and per-case regions. The case regions are the window, one region per
mesh output span at its fixed stride, the secondary light table spans at their
client address, and the declared global bytes. ECX is the model. Execution
starts at a sentinel return with x87 `0x027f`, MXCSR `0x1f80` and poisoned XMM.

Modelled, stated explicitly:

* The uncaptured globals: bone scale `0x01cf104c`, light override `0x01cf1048`,
  world `0x01cf15fc`, bounds mode `0x0b437bfc`, scene state `0x01d1df70` (all
  declared read-only bytes), and the secondary light table (undefined until
  written).
* Caller memory: the output arrays (undefined poison), box, bounds, the light
  arguments, the mesh record array and model fields `+0x24`, `+0x28`, `+0x50`,
  `+0x74..+0x83` and `+0x98..+0xa3`. The mesh records follow model reader
  `0x012b3812`, which memcpys 16-byte vertex and 20-byte normal records and
  stores counts at `+4`/`+6` and pointers at `+0xc`/`+0x10`. Installed records
  point at the decoded file bytes themselves.
* Tick state: action records (stop `+0`, keys `+8`, lock `+0xa`), the frame, and
  undeclared prior slots. The unused origin/angles arguments are unmapped
  addresses, so any read would stop the case.

No client instruction is stubbed and neither routine reaches an import. A case
stops on any read of an undefined or undeclared byte, a write to a read-only
global, an unmapped access, or caller-stack access outside the arguments. A pass
requires:

* return to the sentinel with ESP + 4 + 0x30 (transform) or + 0x18 (tick);
* EBX, ESI, EDI and EBP preserved, DF clear, FPCW/MXCSR control unchanged, x87
  TOP balanced;
* byte-identical regions against the authored C and against an independent
  Python model;
* for the tick, the same AL.

**Installed chain.** For every installed model the existing readers decode and
parse, the actual bone-track loop runs first, and the authored loop must agree
with it. Then the actual pose builder runs, using the "blend" sample of the
builder harness, and the authored builder must give the same window and
quaternions. The transform then runs on the builder's own output window, with
deterministic per-file flags: lighting, override, world, bounds mode, bone
scale, vertex scale, translate and light arguments. The body scale and origin are
the builder's fields. Three ticks per model use the real key counts and lock flags,
preferring actions with more than one key.

Results:

| Comparison | Calls | Matches | Coverage |
|---|---:|---:|---|
| Vector rotate / transform / inverse rotate (direct, 20% aliased) | 301 each | 301 each | |
| Synthetic transform | 226 | 226 | 9,118 vertices, 9,141 normals |
| Synthetic models through the actual builder | 24 | 24 | 503 vertices, 476 normals |
| Synthetic tick | 481 | 481 | |
| Installed transform v12 / v14 / v15 | 180 / 216 / 11,566 | all | 3,814,006 vertices, 3,988,165 normals |
| Installed tick | 35,871 | 35,871 | real key counts and lock flags |

The 17 reader-rejected v15 files were not run. The corpus digest
`de62cb0f…edba4` equals the pose-builder run's. Every transform branch was
reached in the synthetic set and all but the null-bones return on installed
models, including:

* plain 2,183,070, prescaled 696,402 and bone-scale 934,534 vertices;
* bounds updates 165,544 / 166,764;
* lit normals 2,366,527, primary clamps 1,064,540 and secondary floors 1,057,585;
* each of the three light setups.

Every tick branch was reached synthetically. Installed ticks are mostly early
returns: 27,900 single-key actions. They also include 5,315 cycles, 3,397 prior
updates, 577 wraps, 108 clamps, 268 lock limits, 1,797 scene-5 tests and 4
world-39/action-7 tests. Client sin/cos for the light matrix: 21,417 calls of each
on installed models, with 569/645 binary64 differences from host libm and none
after binary32 rounding.

Negative controls (Python variants that must differ from the client):

* transposed bone rotation for vertices differs in 210 of 226 synthetic transforms;
* adding the bone translation to normals differs in 223;
* updating the prior pair on every tick differs in 259 of 481 ticks;
* ignoring the lock flag's `keys - 1` limit differs in 35.

The full run took 5 min 23 s on four niced workers. Report
`comparison-v12-v14-v15.json`, SHA-256
`4b225477edaaff717b8ba648cf5e19ea812bf143572c619ddac232404b4fc036`, authored library
`da2d0c5e…969c`. A first run is kept as `run-01-v14-unbuilt/`: its worktree had
not built `libmodulus`, so all 216 v14 files were reader-rejected there. That was
a harness setup failure, not a client result.

## 4. Mesh draw GL sequence (static)

**Import names.** The OPENGL32 block at `0x01a7c64c..0x01a7c78c` holds 81 slots.
Every slot value minus Wine opengl32's preferred base `0x7a800000` is an export
RVA of the pinned DLL. The first slot is `wglDeleteContext`, which is exactly the
one OPENGL32 name left in the protected file's static import table. The GLU32
block at `0x01a7c170` holds four slots: `gluBuild2DMipmaps` (the static name),
`gluPerspective`, `gluLookAt` and `gluOrtho2D`. These match glu32 at its observed
guest mapping `0x00360000` (`evidence/x86-first-game-maps.txt`). The render-path
slots are:

| Slot | Import | Slot | Import |
|---|---|---|---|
| `0x01a7c750` | glBegin | `0x01a7c760` | glEnd |
| `0x01a7c774` | glTexCoord2f | `0x01a7c778` | glVertex3fv |
| `0x01a7c770` | glColor3fv | `0x01a7c754` | glColor4f |
| `0x01a7c76c` | glColor3f | `0x01a7c77c` | glBindTexture |
| `0x01a7c75c` / `0x01a7c758` | glEnable / glDisable | `0x01a7c748` | glBlendFunc |
| `0x01a7c740` | glDepthMask | `0x01a7c718` / `0x01a7c72c` | glPushMatrix / glPopMatrix |

**Body `0x012bb35a`.** It calls `0x012b7e53` (glPushMatrix), the mesh draw for
each mesh, with glColor3f/glColor4f between draws, then `0x012b7e65`
(glPopMatrix). There is no matrix call between the push and the pop. Positions
arrive already in world space from the CPU transform, so the pair does not change
the matrix here (inference from the absence of calls).

**Mesh draw `0x012b8d1d`.** It takes eleven arguments: `mesh, flags, vertices,
normals, lights, alpha, …, u offset, v offset, texture`. The order per mesh is:

1. If the model's lighting flag `+0x50` is clear: glColor3fv(model `+0x54`)
   when alpha is at least 0.99 (binary32 at `0x01a82fe0`), else
   glColor4f(r, g, b, alpha) (`0x012b8d7b`, `0x012b8dd4`).
2. A per-normal colour pass into `0x089c2120`. Each colour is the light value
   times the model `+0x54` RGB. When model byte `+0xcb` is 1 it uses the
   secondary light plus 0.2. The branch conditions around this pass were not
   decoded in full.
3. State from the flag bits, through cached wrappers (below). The readings are
   selective:
   * flag `0x1` takes a short path: blend ONE,ONE for `0x40`,
     ZERO,ONE_MINUS_SRC_COLOR for `0x80`, otherwise off; depth test off for
     `0x2000`; alpha test off; then colour from model `+0x54` (glColor3fv at
     alpha >= 0.99, otherwise SRC_ALPHA,ONE_MINUS_SRC_ALPHA blend and glColor4f);
   * on the long path, `0x40`, `0x80`, `0x10` and `0x400000` select the ONE,ONE,
     ZERO,ONE_MINUS_SRC_COLOR, ZERO,SRC_COLOR and ZERO,SRC_ALPHA wrappers;
     otherwise the alpha-blend or blend-off wrapper is used, and `0x2000`
     disables the depth test;
   * `0x40000` enables culling and the depth mask just before glBegin;
   * the texture comes from the cached bind wrapper, either the mesh texture or
     a flag-selected special index (`0x7fcf`, `0x800b`, `0x800c`, `0x8005`,
     `0x7f1f`, `0x7f66`).
4. `glBegin(GL_TRIANGLES)` once per mesh (`push 4` at `0x012ba891`).
5. For each triangle record (stride 0x24: corner count byte `+0`, vertex indices
   `+2`, normal indices `+0xa`, UV indices `+0x12`) and each corner:
   * `glTexCoord2f(u [+ u offset], v [+ v offset])` from mesh `+0x14`;
   * then `glColor3fv(colour[normal])`, or `glColor4f(r, g, b, alpha)` by mode;
   * then `glVertex3fv(&vertices[mesh*0x2bf20 + vertex*12])`, read straight from
     the transform output.

   The flags `0x20` (origin-relative distortion), `0x400` (normal-driven wave
   using the global float at `0x06fce370`) and `0x200000` (skip corners) select
   modified vertex variants.
6. `glEnd()` once.

A record's corner count drives the corner loop, so a 4-corner record would emit
four vertices inside `GL_TRIANGLES`. The readers accept 3 or 4 corners; the
effect on GL is an inference.

**State wrappers.** Each wrapper keeps a byte or word cache and calls GL only on
a change:

| Wrapper | GL when the cache changes |
|---|---|
| `0x0184a6b7` / `0x0184a6da` | glEnable / glDisable(GL_DEPTH_TEST) |
| `0x0184a6fd` / `0x0184a720` | glEnable / glDisable(GL_CULL_FACE) |
| `0x0184a743` / `0x0184a763` | glDepthMask(1 / 0) |
| `0x0184a783` | depth mask on, alpha test on/off by its byte argument, GL_TEXTURE_2D off |
| `0x0184a7f3` | blend off, cull/depth-mask on, alpha test off, texture on, fog on when the fog setting byte `0x0bdc597c` is set |
| `0x0184a872`, `0x0184a901`, `0x0184a990`, `0x0184aa2b`, `0x0184aab7`, `0x0184ab46`, `0x0184abd5`, `0x0184ac67` | glEnable(GL_BLEND) + glBlendFunc (ZERO,SRC_COLOR), (ZERO,SRC_ALPHA), (SRC_ALPHA,1-SRC_ALPHA), (ONE,ONE), (ZERO,1-SRC_COLOR), (1-SRC_COLOR,ONE), (SRC_ALPHA,1-SRC_ALPHA), (ONE,1-SRC_COLOR), each with its own cull/depth-mask/alpha-test/fog choices |
| `0x0184acf6` | glBindTexture(GL_TEXTURE_2D, id) when the index differs from `[0x01cf1620]`; id from the bitmap record `+0x215`, or `-index` for negative indices |
| `0x0184a699` / `0x0184a6ab` | glPushMatrix + glLoadIdentity / glPopMatrix |

**Primitive census.** The text has 68 raw `glBegin` call sites. Each has an
immediate argument pushed in the same straight-line run:

| Mode | Sites |
|---|---:|
| GL_QUADS | 27 |
| GL_TRIANGLE_FAN | 24, in 19 functions; 10 in the cluster `0x016cf46c..0x016d197d` and 8 in `0x0184d9bb..0x0184f4ba` |
| GL_TRIANGLES | 10, including the mesh draw |
| GL_LINES | 6 |
| GL_LINE_STRIP | 1 |

The profiled four-vertex fans therefore come from routines other than the mesh
draw, which emits only GL_TRIANGLES. Which routine produces them (terrain or 2D
sprites, for example) is not established. Raw call-site counts for every named
import are in the static report. glColor4f has 354, glVertex3fv 138 and
glDrawArrays 28.

For a batching layer this means:

* each skinned mesh is exactly one GL_TRIANGLES begin/end;
* every vertex carries a texcoord and a colour call;
* texture binds and state are already deduplicated by the client's caches;
* the vertex data is CPU-skinned every frame.

## Unresolved

* Live state: object speeds, the action-change code, real model light/scale
  fields, the global values (bone scale, bounds mode, world, scene) and live
  FP state. The across-tick pose lag is inferred, not run.
* The mesh draw, body and colour pass were not executed. Their order and flag
  semantics are static readings. The modified vertex variants and special
  textures are not interpreted.
* Root-matrix writers for 14 keep-root calls, and readers of the quaternion
  table beyond raw immediates.
* Buffer capacities: the 50-mesh/15,000-entry figures are inferences, and no
  bounds check exists. The 17 reader-rejected v15 files; NaN/infinity behavior
  (all compared values are finite in practice, not by restriction). Five models
  without actions feed the transform declared prior matrices, not builder output.
* The frame cap and main loop that drive these routines are not traced.
* The second builder `0x012bcffb` and native Windows behavior.

## Reproduce

```sh
make -C model-recovery && make -C reconstructed/model-codec
./tools/python/bin/python scripts/validate_skinning.py \
  --text evidence/x86-text-capture-09/client-text.bin \
  --data evidence/image-data-run10/data-capture-10/client-image-data.bin \
  --flag evidence/trig-state-15/captures/late/math-dispatch-flag.bin \
  --feature evidence/x86-math-capture-09/cpu-features.bin \
  --game-root "$MU_GAME_ROOT" --versions 12,14,15 --workers 4 \
  --output /new/local/skinning.json
./tools/python/bin/python scripts/client_render_static.py \
  --text evidence/x86-text-capture-09/client-text.bin \
  --data evidence/image-data-run10/data-capture-10/client-image-data.bin \
  --opengl32 /extracted/libwine/i386-windows/opengl32.dll \
  --glu32 /extracted/libwine/i386-windows/glu32.dll --output /new/local/static.json
```

The static report (`static-05.json`, SHA-256 `924b0b0b…1b30`) takes about 40 s.

Portable tests:

* `reconstructed/model-codec/test_skinning.py`: eleven portable checks. They cover
  worked transform examples (bone matrix, body scale/origin, bone and vertex
  scale, light clamp/floor, the world-30 angle rewrite, both box sources, null
  bones and outside memory); tick prior update, wrap, lock, clamp, shift and
  scene; C/Python agreement with all four negative controls; the vector helpers;
  and refusal of unpinned text. A twelfth, private check runs the validator on
  the synthetic sets and installed v12/v14 models.
* `tests/test_client_render_static.py`: six portable checks on hand-assembled code
  and an authored PE export table, plus a private check of the counts above. The
  private check reads the Wine DLLs from `MU_WINE_DLLS` (default: the ignored
  extraction under `evidence/client-skinning/`).

Reports, logs, the downloaded package, the extracted DLLs and scratch scripts are
ignored under `evidence/client-skinning/` in the skinning worktree.
