/* The later mounts' class visuals and steps (NATIVE-HELPERS-002, docs/research/client-helpers.md).
 *
 * After the after-pass, the mount render loop 0x0106bc2b calls the class's visuals (vtable +0x1c; the classic four
 * share the empty 0x0103d8be); the class move (+0xc) adds the class's steps to the base move. Reconstructed here:
 * the Shining Tail's visuals 0x01057fb0 (flares and glints on its bones, the mist and sparks of its tails, the
 * rune circles under its paws that fade in while it stands, the claws' step effects 0x0105a0bb while it walks),
 * with the random helpers they draw from: 0x011ff622 (a random value of a range in steps), 0x00d01fc6 (a random
 * direction) and 0x00d0221e (a random flat direction). Compared with the client by
 * scripts/validate_mount_visuals.py (section class). */
#ifndef MU_HELPERS_MOUNT_CLASS_H
#define MU_HELPERS_MOUNT_CLASS_H

#include <stdint.h>

#include "helpers.h"
#include "mount_render.h"

#ifdef __cplusplus
extern "C" {
#endif

/* On particle/effect calls, flags bit 0 means the mount OBJECT is the owner. */
enum { MU_HP_AC_OWNED = 1 };

/* call kinds beyond mount_render.h's */
enum {
    MU_HP_AC_OBJECT_BONE = 20, /* TransformByObjectBone 0x012b678d(model, out, object, bone = mesh, 0) */
    MU_HP_AC_JOINT,            /* CreateJoint(type, position, position, angle, subtype, object, scale, -1, ..., light) */
    MU_HP_AC_DECAL,            /* RenderTerrainAlphaBitmap 0x016cdd5f(type, x, y, scale, scale, light, angle x, alpha,
                                  5, 1, 0) */
    MU_HP_AC_BLEND,            /* a blend wrapper (flags = its address) */
    MU_HP_AC_EYES,             /* 0x0137a948(object, model, 0x27, 0x26, -1 ...): eye positions into object +0x194 / +0x188 */
    MU_HP_AC_NAMED_BONE        /* 0x012b6a2b(model, out, object, name, 0): mesh = the name's index in the class's list */
};

/* The state the visuals keep between frames. */
typedef struct mu_hp_class_state {
    float a4;                 /* object +0xa4: the rune circles' fade (the model load writes 0) */
    uint8_t flag_48;          /* mount +0x48: the eye joints were created */
} mu_hp_class_state;

typedef struct mu_hp_class_inputs {
    float world_time;         /* 0x06fce370 */
    uint16_t action;          /* object +0x2a (the visuals); the step: the mount's action +0x30 */
    float frame;              /* object +0xd0 */
    float alpha;              /* object +0xdc */
    float position[3];        /* object +0x158 */
    float angle[3];           /* object +0x164 */
    int32_t subtype;           /* object +0x60: equipment level */
} mu_hp_class_inputs;

typedef struct mu_hp_class_host {
    void *context;
    void (*object_bone)(void *context, int32_t bone, float out[3]);
    void (*named_bone)(void *context, const char *name, float out[3]);
    void (*object_bone_offset)(void *context, int32_t bone, const float offset[3], float out[3]);
} mu_hp_class_host;

float mu_hp_rand_range(mu_helpers *h, float lo, float hi, uint32_t steps);
float mu_hp_rand_direction(mu_helpers *h, float out[3], float r_max, float r_min, float t_max, float t_min,
                           float p_max, float p_min);
float mu_hp_rand_flat(mu_helpers *h, float out[3], float r_max, float r_min, int32_t mode);

/* vtable +0x1c of class cls (once per drawn frame): the calls go to out. Returns 1 when reconstructed for cls. */
int mu_hp_mount_class_visuals(mu_helpers *h, int32_t cls, mu_hp_class_state *state, const mu_hp_class_inputs *in,
                              const mu_hp_class_host *host, mu_hp_after_call *out, int32_t capacity, int32_t *count);
/* The class's own part of the move (+0xc after the base move, once per step). Returns 1 when it ran. */
int mu_hp_mount_class_step(mu_helpers *h, int32_t cls, const mu_hp_class_inputs *in, const mu_hp_class_host *host,
                           mu_hp_after_call *out, int32_t capacity, int32_t *count);

#ifdef __cplusplus
}
#endif

#endif
