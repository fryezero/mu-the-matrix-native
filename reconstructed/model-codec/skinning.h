#ifndef MU_SKINNING_H
#define MU_SKINNING_H

#include <stdint.h>

#include "pose_builder.h"

/* Authored reconstructions of the model transform observed at
 * 0x012b5bde..0x012b678d (thiscall on the model object, ret 0x30) and the
 * animation tick at 0x012b4dd3..0x012b5064 (thiscall, ret 0x18). Names are
 * investigator labels, not recovered original symbols. See
 * docs/research/client-skinning.md.
 *
 * Both operate on mu_client_memory views of 32-bit client address ranges.
 *
 * Model fields used by the transform (byte offsets):
 *   +0x24 int16 mesh count (reread per mesh), +0x28 u32 mesh array,
 *   +0x50 u8 lighting flag (reread per normal), +0x74 binary32 body scale,
 *   +0x78..+0x83 three binary32 body origin values, +0x98..+0xa3 three
 *   binary32 light angles in degrees (written to 0, 0, -45 on one path).
 * Mesh records, stride 0x20, as written by model reader 0x012b3812:
 *   +4 int16 vertex count, +6 int16 normal count, +0xc u32 vertices
 *   (stride 16: int16 bone at +0, three binary32 at +4), +0x10 u32 normals
 *   (stride 20: int16 bone at +0, three binary32 at +4).
 * Output arrays use a fixed stride per mesh: 0x2bf20 bytes (15,000 x 12) for
 * vertices and normals, 0xea60 bytes (15,000 x 4) for the two light arrays.
 * Nothing bounds a mesh, vertex or bone index.
 */

/* The twelve 32-bit stack arguments, first = [esp+4]. */
typedef struct mu_transform_arguments {
    uint32_t bones;          /* client address of 0x30-byte 3x4 bone matrices; 0 returns at once */
    uint32_t vertices;       /* output: transformed positions */
    uint32_t normals;        /* output: rotated normals */
    uint32_t lights;         /* output: primary light intensity per normal */
    uint32_t bounds_min;     /* three binary32, read only when bounds mode != 2 */
    uint32_t bounds_max;     /* three binary32, read only when bounds mode != 2 */
    uint32_t box;            /* 0x30-byte box: origin, then three axis vectors */
    uint32_t translate;      /* low byte nonzero: body scale and origin applied */
    uint32_t vertex_scale;   /* binary32 bits; nonzero scales positions before the bone transform */
    uint32_t light_ambient;  /* binary32 bits added to both light terms */
    uint32_t light_scale;    /* binary32 bits multiplying the primary light term */
    uint32_t light_minimum;  /* binary32 bits clamping the primary light term from below */
} mu_transform_arguments;

/* Client addresses of the uncaptured globals the transform uses. */
#define MU_SKIN_BONE_SCALE 0x01cf104cu      /* binary32; exactly 1.0 selects the plain path */
#define MU_SKIN_LIGHT_OVERRIDE 0x01cf1048u  /* u8 */
#define MU_SKIN_WORLD 0x01cf15fcu           /* int32; 30 selects the second light setup */
#define MU_SKIN_BOUNDS_MODE 0x0b437bfcu     /* int32; 2 accumulates vertex bounds */
#define MU_SKIN_SECONDARY_LIGHT 0x075a9ee8u /* binary32 per normal, stride 0xea60 per mesh */
#define MU_TICK_SCENE_STATE 0x01d1df70u     /* int32 read through 0x009b0bc1 */

typedef struct mu_transform_globals {
    uint32_t bone_scale;
    uint32_t light_override;
    uint32_t world;
    uint32_t bounds_mode;
    uint32_t secondary_light;
} mu_transform_globals;

enum {
    MU_SKIN_OK = 0,
    MU_SKIN_OUTSIDE_MEMORY = 2
};

/* Runs the transform. For mesh i, vertex j (bone b, position p):
 *   bone scale == 1.0:  v = M[b] * (vertex_scale != 0 ? vertex_scale*p : p)
 *                       then, when translating, v *= body scale;
 *   otherwise:          v = R[b] p, v[k] = v[k]*bone_scale + M[b][k][3],
 *                       then, when translating, v *= body scale;
 *   bounds mode 2 updates running min/max; translating adds the body origin.
 * Normal j: n = R[b] normal. With the lighting flag, the primary light is
 * max(light_minimum, dot(n, L1)*light_scale + light_ambient) and the secondary
 * light max(0.2, dot(n, L2)*0.8 + light_ambient), where L1 and L2 are fixed
 * vectors rotated by the transpose of the light-angle matrix. Finally the box
 * origin and axes are written. Single bone per vertex; no blending, no
 * normalization. All arithmetic is binary32 in the original order; light
 * angles use host libm sin/cos (the client helpers are a substitute boundary,
 * as in the pose builder). An access outside every region returns
 * MU_SKIN_OUTSIDE_MEMORY after earlier effects. */
int mu_model_transform(const mu_client_memory *memory, uint32_t model, const mu_transform_arguments *arguments,
                       const mu_transform_globals *globals);

/* The six 32-bit stack arguments of the animation tick. origin and angles are
 * never read by the observed body. */
typedef struct mu_tick_arguments {
    uint32_t frame;         /* client address of binary32 current frame (read/write) */
    uint32_t prior_frame;   /* client address of binary32 prior frame (written) */
    uint32_t prior_action;  /* client address of u16 prior action (written) */
    uint32_t speed;         /* binary32 bits added to the frame */
    uint32_t origin;
    uint32_t angles;
} mu_tick_arguments;

typedef struct mu_tick_globals {
    uint32_t scene_state;  /* MU_TICK_SCENE_STATE */
    uint32_t world;        /* MU_SKIN_WORLD */
} mu_tick_globals;

/* Advances *frame by speed for the model's current action (+0xa8, actions at
 * +0x30 stride 16: u8 stop flag at +0, int16 keys at +8, u8 lock flag at +0xa).
 * When the integer part changes, *prior_action = current action and
 * *prior_frame = (float)old integer part. Non-positive frames add keys-1.
 * With the stop flag, frames >= keys clamp to keys-0.01; otherwise frames at
 * or past the limit (keys, or keys-1 with the lock flag; tested with +2 when
 * the scene state is 5, or +1 for action 7 in world 39) wrap by integer
 * modulo keeping the fraction. Model +0xac/+0xb4 receive the frame and its
 * truncation. *loop receives the returned AL: 1 unless a clamp or wrap
 * happened. Null pointers, an invalid action or keys <= 1 return 1 early. */
int mu_animation_tick(const mu_client_memory *memory, uint32_t model, const mu_tick_arguments *arguments,
                      const mu_tick_globals *globals, uint8_t *loop);

#endif
