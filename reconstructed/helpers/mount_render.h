/* The mounts' model passes and visuals (NATIVE-HELPERS-002, docs/research/client-helpers.md).
 *
 * The mount render loop 0x0106bc2b calls, per mount, the body (vtable +0x14 0x0103d6d5: RenderObject's setup), the
 * shadow 0x0103d281, the after-pass (+0x18 0x0103d830 -> RenderObject's draw 0x017edf43) and the class visuals
 * (+0x1c). In the draw, the render registry 0x01d1e010 (std::map from the object type to a functor, filled by
 * 0x00a16273 calls) hands the mount models to their own functors, which draw the body and its glow passes through
 * RenderBodyDefault 0x00966def and RenderMeshDefault 0x00966e4a with the model colour +0x54 set per pass:
 *
 *   0x410 Dark Horse 0x00a2eaa2, 0x417 Uniria 0x00a2f501 (none: the default body), 0x473 Dinorant 0x00a318b8,
 *   0x4a8..0x4ab Fenrir 0x00a335e9 / 0x00a34652 / 0x00a356bb / 0x00a36724 (four copies of one body),
 *   0x671 Ghost Horse 0x00a477ec, 0x69a / 0x69b Ice Dragon 0x00a480f9 / 0x00a48462,
 *   0x6cb / 0x6cc Pierce Lion 0x00a4cd20 / 0x00a4cfed, 0x6f4 / 0x6f5 Shining Tail 0x00a4f699 / 0x00a4fa6d,
 *   0x736 / 0x737 Ur 0x00a527d1 / 0x00a52da0, 0x749 / 0x74a Leviathan 0x00a54b97 / 0x00a54e60,
 *   0x77c / 0x77d Tauros 0x00a551fe / 0x00a55883, 0x753 Divine Horse 0x00a5aee8,
 *   0x73f / 0x740 / 0x741 the ride-state transformations 0x00a53c44 / 0x00a540ba / 0x00a54490.
 *
 * mu_hp_mount_after reproduces a functor as the ordered list of the calls it makes. Every float follows the
 * client's binary32 order; sine and cosine are the host libm's (the client's wrappers 0x009681bd / 0x009fa223 call
 * the CRT). Compared with the client's instructions by scripts/validate_mount_visuals.py. */
#ifndef MU_HELPERS_MOUNT_RENDER_H
#define MU_HELPERS_MOUNT_RENDER_H

#include <stdint.h>

#include "helpers.h"

#ifdef __cplusplus
extern "C" {
#endif

enum {
    MU_HP_AC_BODY = 1,        /* RenderBodyDefault 0x00966def(flags, alpha, blend mesh, blend light, u, v, hidden, texture) */
    MU_HP_AC_MESH,            /* RenderMeshDefault 0x00966e4a(mesh, flags, alpha, blend mesh, blend light, u, v, texture) */
    MU_HP_AC_PUSH,            /* 0x012b7e53(model, 1.0): the model's pose push (Fenrir) */
    MU_HP_AC_POP,             /* 0x012b7e65(model) */
    MU_HP_AC_ALPHA_TEST,      /* EnableAlphaTest 0x0184a990(arg) */
    MU_HP_AC_COLOR4,          /* glColor4f(light[0..2], scale) */
    MU_HP_AC_SHADOW,          /* RenderBodyShadow 0x012bc07a(model, -1, -1, first = mesh, end = texture, 0) */
    MU_HP_AC_BONE,            /* TransformPosition 0x012b6ef1(model, BoneTransform + 0x30 * mesh, position, out, 0) */
    MU_HP_AC_SPRITE,          /* CreateSprite 0x01692eb7(type, position, scale, light, object, 0, 0, 4, {1, 1, 1}) */
    MU_HP_AC_PARTICLE,        /* CreateParticle 0x0168fafd(type, position, angle, light, subtype, scale, 0, 0) */
    MU_HP_AC_EFFECT           /* CreateEffect 0x013c0eaa(type, position, angle, light, subtype, object, -1, 0, ...) */
};

/* One call, the fields its kind uses (model fields as they are at the call). */
typedef struct mu_hp_after_call {
    int32_t kind;
    int32_t mesh;
    uint32_t flags;
    float alpha;
    int32_t blend_mesh;
    float blend_light;
    float u, v;
    int32_t hidden;
    int32_t texture;
    float color[3];           /* model +0x54 */
    uint8_t model_94;         /* model +0x94 (Fenrir clears it around its passes) */
    int32_t type, subtype;
    float position[3];
    float angle[3];
    float light[3];
    float scale;
} mu_hp_after_call;

/* What a functor reads besides the object. */
typedef struct mu_hp_after_inputs {
    int32_t world;            /* 0x01cf15fc */
    float world_time;         /* 0x06fce370 */
    uint8_t world_9b0418;     /* 0x009b0418(world) */
    uint8_t event_block;      /* 0x009a645f(0x009a6ef3() + 0x78) */
    float color[3];           /* model +0x54 on entry (the setup's body light) */
    uint8_t model_94;         /* model +0x94 on entry */
    float object_a4;          /* object +0xa4 (ObjectInit 1.0; the ride-state transformations' glow) */
    float object_u, object_v; /* object +0xac, +0xb0 (the blend mesh's uv scroll) */
} mu_hp_after_inputs;

typedef struct mu_hp_after_host {
    void *context;
    /* TransformPosition(model, BoneTransform + 0x30 * bone, in, out, 0) on the posed model */
    void (*bone)(void *context, int32_t bone, const float in[3], float out[3]);
} mu_hp_after_host;

/* 0x0185bdc4(period, phase): (cos-like wave of the world time + 1) / 2, the glow pulse of the mounts. */
float mu_hp_wave(float period, float phase, float world_time);
/* The registry functor of an object type: 1 when a mount functor exists for it (handled is then its return). */
int mu_hp_mount_after_known(int32_t type);
/* Runs the functor of object o's type (rand() through h when the functor draws one): the calls in client order go
 * to out (capacity calls), *count receives their number. Returns the functor's AL (0: the caller draws the default
 * body RenderBody(2, alpha, blend mesh, blend light, u, v, hidden, -1)), or -1 when the type has no functor. */
int mu_hp_mount_after(mu_helpers *h, const mu_hp_object *o, const mu_hp_after_inputs *in,
                      const mu_hp_after_host *host, mu_hp_after_call *out, int32_t capacity, int32_t *count);

#ifdef __cplusplus
}
#endif

#endif
