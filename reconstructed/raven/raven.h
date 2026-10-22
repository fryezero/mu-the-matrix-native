/* The Dark Raven (Dark Spirit) of a Dark Lord (NATIVE-HELPERS-002, docs/research/client-dark-spirit.md).
 *
 * Client routines (restored text, main.exe SHA-256 3cf91f3c...b5527a); names are investigator choices:
 *
 *   pet type from a byte  0x00c92bea  0 none, 1 / 2 / 3 Dark Raven (c + 0x31f8 = 0x1a05, level word c + 0x3204 =
 *                                     1 / 20 / 40), 10..13 the later raven items (0x28f8, 0x28f9, 0x28fa, 0x2900)
 *   create                0x00c92a29  delete 0x00c9321b, then a 0x3688-byte pet object for c + 0x31f8 (c + 0x31f0)
 *   Dark Raven ctor       0x009ecbdf  the start position at the owner's bone 0x23, CreatePetPointer 0x009ec0b0
 *                                     (the pet's own CHARACTER at +0xc, its OBJECT at +0x3260)
 *   per character move   0x00c930df  MovePet (vtable +4, 0x009ecfe9), re-create when faded out, model check
 *                                     0x00c92e04 (safe zone: the soul models 0x748 / 0x750..0x752, else the raven
 *                                     models 0x411 / 0x74d..0x74f)
 *   per character render 0x00c9314f  RenderPet (vtable +0x10, 0x009ef6d5) with 0 or 10 (buff 0x12)
 *   render functors       0x00a2eea5 (model 0x411 DarkSpirit), 0x00a55f03 (model 0x748 Dark_Soul), from the
 *                                     render registry 0x01d1e010 that RenderObject's draw 0x017edf43 asks
 *
 * MovePet's AI byte (object +0x29): 0 / 1 fly around the owner (Spark03 sparkles, turn, climb and sink within a
 * band above the owner), 3 sit: the raven flies to the owner's bone 0x23 (MoveHumming), the soul model follows it
 * with a bob from the owner's animation; 2 / 4 / 5 attack a target (only through the server's pet commands:
 * static, not ported). The safe zone (c + 4) switches the AI to 3 and the model to the soul.
 *
 * Every entry point takes the client state it reads as plain inputs and calls the host for the engine services
 * (rand(), the model container, the animation tick, SetAction, the bone matrices with TransformPosition,
 * CreateParticle, the frustum, RenderObject, the pet packet). Float arithmetic follows the client's binary32 order;
 * comparisons follow its comiss/jcc pairs.
 */
#ifndef MU_RAVEN_H
#define MU_RAVEN_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum {
    MU_RV_ITEM_DARK_RAVEN = 0x1a05,   /* item 13,5 */
    MU_RV_MODEL_RAVEN = 0x411,        /* Data/Skill/DarkSpirit.bmd */
    MU_RV_MODEL_SOUL = 0x748,         /* Data/Item/Dark_Soul.bmd (the raven in a safe zone) */
    MU_RV_MODEL_PLAYER = 0xa91,
    MU_RV_BITMAP_SPARK3 = 0x7f26,     /* Effect\Spark03 (the sparkles, subtype 5) */
    MU_RV_BITMAP_FLARE = 0x7ef7,      /* Effect\flare01 */
    MU_RV_BITMAP_SOUL = 0x83b3,       /* the soul's particle (subtype 0xb) */
    MU_RV_TEXTURE_RAVEN = 0x7fa5,     /* the level-40 raven's overlay texture */
    MU_RV_TEXTURE_SOUL = 0x7f1f,      /* the soul's overlay texture */
    MU_RV_OWNERS = 16
};

/* The pet's OBJECT (pet + 0x3260): the fields these routines read or write, named by offset. */
typedef struct mu_rv_object {
    uint8_t live;            /* +0x00 */
    uint8_t flag_04;         /* +0x04 */
    uint8_t lighting;        /* +0x05 */
    uint8_t target;          /* +0x08 (attack target set) */
    uint8_t visible;         /* +0x0b */
    uint8_t alpha_enable;    /* +0x0c */
    uint8_t flag_0d;         /* +0x0d */
    uint8_t flag_0e;         /* +0x0e */
    uint8_t ai;              /* +0x29 */
    uint16_t action;         /* +0x2a */
    uint16_t prior_action;   /* +0x2c */
    uint8_t flag_40;         /* +0x40 */
    uint8_t level;           /* +0x41 (the raven's mesh choice) */
    uint8_t flag_44;         /* +0x44 */
    int32_t type;            /* +0x5c */
    int32_t subtype;         /* +0x60 */
    int32_t hidden_mesh;     /* +0x68 */
    int32_t lifetime;        /* +0x6c (the "lost" counter) */
    int32_t blend_mesh;      /* +0x74 */
    uint32_t time;           /* +0x84 */
    float scale;             /* +0xa0 */
    float blend_light;       /* +0xa8 */
    float uv[2];             /* +0xac, +0xb0 */
    float field_b4;          /* +0xb4 */
    float velocity;          /* +0xbc */
    float field_c0;          /* +0xc0 */
    float field_c4;          /* +0xc4 */
    float field_c8;          /* +0xc8 */
    float frame;             /* +0xd0 */
    float prior_frame;       /* +0xd4 */
    float alpha_target;      /* +0xd8 */
    float alpha;             /* +0xdc */
    float light[3];          /* +0xec */
    float direction[3];      /* +0xf8 */
    float box_min[3];        /* +0x128 */
    float box_max[3];        /* +0x134 */
    float position[3];       /* +0x158 */
    float angle[3];          /* +0x164 */
    float matrix[3][4];      /* +0x2e8 */
} mu_rv_object;

/* The 0x3688-byte pet (CSPetSystem): its own fields and the modelled CHARACTER fields at +0xc. */
typedef struct mu_rv_pet {
    uint8_t live;            /* c + 0x31f0 != NULL */
    int32_t cls;             /* 1: the Dark Raven (vtable 0x01a7fac8); 0: a class not ported */
    int32_t owner;           /* +0x04 (the owner index) */
    int32_t target;          /* +0x08 (a target character; always NULL offline) */
    uint8_t safe;            /* +0x10 (= character +0x04) */
    uint8_t counter;         /* +0x2d (character +0x21) */
    uint8_t byte_29;         /* +0x35 (character +0x29) */
    uint8_t tile_byte[2];    /* +0x39, +0x3a */
    int16_t target_key;      /* +0x4c (character +0x40) */
    uint16_t level;          /* +0x150 (character +0x144) */
    int32_t tile[2];         /* +0x18c, +0x190 */
    uint8_t command;         /* +0x3684 */
    uint8_t fade_in;         /* +0x3685 */
    uint8_t fade_out;        /* +0x3686 */
    int32_t slot;            /* +0x367c */
    int32_t info_level;      /* +0x3680: the hero's pet record +0x10 byte (-1: no record) */
    mu_rv_object object;     /* +0x3260 */
} mu_rv_pet;

/* The owner character, as these routines see it. */
typedef struct mu_rv_owner {
    uint8_t live;            /* the character exists */
    uint8_t hero;            /* the hero (0x0a39d754) */
    uint8_t safe;            /* c + 0x04 */
    int32_t tile[2];         /* c + 0x180, c + 0x184 */
    int32_t pet_item;        /* c + 0x31f8 */
    uint16_t pet_level;      /* c + 0x3204 */
    uint16_t ride;           /* c + 0x322e */
    /* the object c + 0x3254 */
    uint16_t action;         /* +0x2a */
    int32_t type;            /* +0x5c */
    float scale;             /* +0xa0 */
    float frame;             /* +0xd0 */
    float position[3];       /* +0x158 */
    uint8_t buff_12, buff_3d, buff_b2, buff_118;   /* the object's buff list (+0x358 = c + 0x35ac) */
    /* the mount manager's answers for the character: 0x0106b93a (a mount; its rider offset z) and
     * 0x0106b9f7(c, 2, 1) (a ride-state mount) */
    uint8_t has_mount;
    float mount_offset_z;
    uint8_t mount_state2;
    /* the hero's pet record 0x0129dabe(c, 0): present, its type word and level byte (+0x10) */
    uint8_t has_info;
    int16_t info_type;
    uint8_t info_level;
} mu_rv_owner;

typedef struct mu_rv_inputs {
    int32_t world;           /* 0x01cf15fc */
    uint32_t tick;           /* 0x0bdc5eb0 */
} mu_rv_inputs;

enum {   /* which object a bone call names */
    MU_RV_OWNER_OBJECT = 0,
    MU_RV_PET_OBJECT = 1
};

typedef struct mu_rv_host {
    void *context;
    /* the model getter 0x00966cc4 -> 0x00eaa8cf (NULL = always present) */
    int (*has_model)(void *context, int32_t model);
    /* the key count of an action of a model (model +0x30 records, short at +8) */
    int32_t (*action_keys)(void *context, int32_t model, int32_t action);
    /* the animation tick 0x012b4dd3 on the object: returns its AL */
    int (*animate)(void *context, mu_rv_object *object, int32_t model, float speed);
    /* SetAction 0x012affa4 */
    void (*set_action)(void *context, mu_rv_object *object, int32_t action);
    /* the bone matrix getter 0x0129f12c of an object (the owner's or the pet's): 0 for NULL (no model, no bone
     * buffer, index out of range); then TransformPosition 0x012b6ef1(model, that matrix, vector, out, translate) */
    int (*bone)(void *context, int32_t which, int32_t owner, int32_t bone);
    void (*transform)(void *context, int32_t model, int32_t which, int32_t owner, int32_t bone, const float vector[3],
                      float out[3], int translate);
    /* 0x012b6d2a(model, out, matrix of `bone`, base, vector): BodyScale * VectorTransform(vector) + base */
    void (*transform_base)(void *context, int32_t model, int32_t which, int32_t owner, int32_t bone,
                           const float base[3], const float vector[3], float out[3]);
    /* CreateParticle 0x0168fafd(bitmap, position, angle, light, subtype, scale, 0, 0) */
    void (*particle)(void *context, int32_t bitmap, const float position[3], const float angle[3],
                     const float light[3], int32_t subtype, float scale);
    /* PlayBuffer 0x00a6ac96(id, object, 0) */
    void (*sound)(void *context, int32_t id, int32_t owner);
    /* the pet-info request packet (0xc1, 0xc8; network, recorded only) */
    void (*request)(void *context, int32_t owner, int32_t slot);
    /* RequestTerrainHeight 0x016cc9e2 and the TerrainWall word at 0x016d34db(x, y) */
    float (*terrain_height)(void *context, float x, float y);
    uint16_t (*terrain_wall)(void *context, int32_t x, int32_t y);
    /* the soul model's BodyOrigin (+0x78) and the parent matrix 0x078965ac (AngleMatrix of the model's +0x84
     * concatenated with AngleMatrix(0)); body_angle answers the model's +0x84 */
    void (*model_origin)(void *context, int32_t model, const float origin[3]);
    void (*body_angle)(void *context, int32_t model, float angle[3]);
    void (*parent_matrix)(void *context, const float matrix[3][4]);
    /* the character with a key 0x009a13f4 (the attack target; NULL offline) */
    int (*find)(void *context, int16_t key);
    /* the class of a later raven item (0x009f0258, not ported): recorded */
    void (*unsupported)(void *context, int32_t owner, int32_t item);
} mu_rv_host;

typedef struct mu_raven {
    uint32_t rand_state;     /* the CRT rand() state, shared with the rest of the client */
    uint64_t rand_calls;
    uint8_t requested;       /* [0x01d1e028 + 8]: the pet-info request was sent (MovePet sends it once) */
    mu_rv_pet pets[MU_RV_OWNERS];   /* c + 0x31f0 per owner */
    mu_rv_owner *owners;
    int32_t owner_count;
    mu_rv_host host;
} mu_raven;

void mu_rv_init(mu_raven *r, uint32_t rand_seed, mu_rv_owner *owners, int32_t owner_count, const mu_rv_host *host);
int32_t mu_rv_rand(mu_raven *r);

/* 0x00c92bea(c, value): the pet item and level word from a byte, then create (0..3 the Dark Raven, 10..13 the
 * later items). Returns 1 when it changed the owner. */
int mu_rv_set_type(mu_raven *r, const mu_rv_inputs *in, int32_t owner, uint8_t value);
/* 0x00c92a29: delete, then the pet for the owner's pet item. */
void mu_rv_create(mu_raven *r, const mu_rv_inputs *in, int32_t owner);
/* 0x00c9321b */
void mu_rv_delete(mu_raven *r, int32_t owner);
/* 0x009ec0b0 CreatePetPointer(type, x, y, angle z) */
void mu_rv_create_pointer(mu_raven *r, mu_rv_pet *p, int32_t type, int32_t x, int32_t y, float angle);
/* 0x009ec878: AI byte and the lost counter */
void mu_rv_set_ai(mu_rv_pet *p, uint8_t ai);
/* 0x009ecb21: alpha step with the fade flags */
void mu_rv_alpha_step(mu_rv_pet *p, float step);
/* 0x00c92e04: the pet's model fits the owner's safe state */
int mu_rv_model_fits(const mu_raven *r, int32_t owner);

/* 0x009ecfe9 MovePet. Returns 1 when it ran to the end (0: an early return). */
int mu_rv_move_pet(mu_raven *r, const mu_rv_inputs *in, int32_t owner);
/* 0x00c930df: MovePet, re-create when faded out, the model check. */
void mu_rv_move(mu_raven *r, const mu_rv_inputs *in, int32_t owner);

typedef struct mu_rv_render_host {
    void *context;
    /* TestFrustrum2D 0x016ccce7(x * 0.01, y * 0.01, -20) */
    int (*frustum)(void *context, float x, float y, float range);
    /* RenderObject 0x016d4fe4(object, 0, 0, a3, -1, -1) */
    void (*draw_object)(void *context, const mu_rv_object *object, int32_t owner, int32_t a3);
} mu_rv_render_host;

/* 0x00c9314f(c): RenderPet 0x009ef6d5 with 0, or 10 under buff 0x12. world_9dacb8: the run-speed worlds. */
void mu_rv_render(mu_raven *r, const mu_rv_inputs *in, int32_t owner, const mu_rv_render_host *rh);
/* 0x009dacb8: worlds 0x12..0x17, 0x35, 0x61 */
int mu_rv_world_9dacb8(int32_t world);

/* ---- the render functors (what RenderObject draws for the pet's model) ---- */

enum {
    MU_RV_DRAW_COLOR3 = 1,   /* glColor3f(a, b, c) */
    MU_RV_DRAW_PUSH,         /* the model's push 0x012b7e53(alpha) */
    MU_RV_DRAW_POP,          /* 0x012b7e65 */
    MU_RV_DRAW_BODY,         /* RenderBody 0x00966def(flags, alpha, blend mesh, blend light, u, v, hidden, texture) */
    MU_RV_DRAW_MESH,         /* RenderMesh 0x00966e4a(mesh, flags, alpha, blend mesh, blend light, u, v, texture) */
    MU_RV_DRAW_SPRITE,       /* CreateSprite 0x01692eb7(bitmap, position, scale, light, object, 0, 0, 4) */
    MU_RV_DRAW_PARTICLE,     /* CreateParticle 0x0168fafd(bitmap, position, angle, light, subtype, scale, object) */
    MU_RV_DRAW_SHADOW        /* EnableAlphaTest(1), glColor4f(0, 0, 0, a), BodyOrigin, RenderBodyShadow */
};

typedef struct mu_rv_draw {
    int32_t kind;
    int32_t mesh, flags, blend_mesh, hidden, texture, bitmap, subtype;
    float alpha, blend_light, uv[2], scale;
    float color[3];          /* the model's body colour (+0x54) at the call */
    float vector[3];         /* sprite / particle / shadow-origin position, or glColor3f */
    float light[3];
} mu_rv_draw;

typedef struct mu_rv_draw_list {
    mu_rv_draw items[16];
    int32_t count;
} mu_rv_draw_list;

typedef struct mu_rv_draw_inputs {
    int32_t world;
    float time;              /* WorldTime 0x06fce370 */
    uint8_t shadow_world;    /* 0x009b0418(world) */
    uint8_t event_block;     /* 0x009a645f(event + 0x78) */
    uint8_t dim_world;       /* 0x016a88ae(world) */
    float color[3];          /* the model's +0x54 on entry */
} mu_rv_draw_inputs;

typedef struct mu_rv_draw_host {
    void *context;
    float (*sine)(void *context, float x);                 /* 0x009681bd */
    float (*wave)(void *context, float a, int32_t b);      /* 0x0185bdc4 */
    float (*random_float)(void *context, float lo, float hi, int32_t steps);   /* 0x011ff622 */
    float (*terrain_height)(void *context, float x, float y);
} mu_rv_draw_host;

/* 0x00a2eea5 (model 0x411) and 0x00a55f03 (model 0x748). Both return 1 (drawn by the functor). The soul's
 * functor turns the object (angle z + 2). */
int mu_rv_draw_raven(const mu_rv_object *o, const mu_rv_draw_inputs *in, const mu_rv_draw_host *h,
                     mu_rv_draw_list *out);
int mu_rv_draw_soul(mu_rv_object *o, const mu_rv_draw_inputs *in, const mu_rv_draw_host *h, mu_rv_draw_list *out);

#ifdef __cplusplus
}
#endif

#endif
