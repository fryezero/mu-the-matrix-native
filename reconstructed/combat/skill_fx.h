#ifndef MU_SKILL_FX_H
#define MU_SKILL_FX_H

/* The client's older effect system for skills and projectiles
 * (NATIVE-COMBAT-002, docs/research/client-combat.md section 8).
 *
 * Three pools carry what a skill shows:
 *   - effects: CreateEffect 0x013c0f19 into 200 records of 0x3d8 bytes at
 *     0x0a4ca430, moved once per logic step by MoveEffect 0x0142fd09 (from
 *     MoveEffects 0x0150ddb1) and drawn by RenderEffects 0x015181fa (model
 *     types through RenderObject 0x016d4fe4; bitmap types draw nothing
 *     themselves, they emit particles and joints while they move);
 *   - particles: CreateParticle 0x0168fafd / 0x015ae7b0 (a list of shared
 *     records at 0x0a3a9adc), MoveParticles 0x01616c80, RenderParticles
 *     0x0159123f (camera-facing sprites);
 *   - joints: CreateJoint 0x0153b02c (500 records of 0xa64 bytes at
 *     0x0a4fa4f0), ribbons that chase a target.
 *
 * Authored C ports; addresses are the routines in the pinned restored text
 * (capture09). Every client operation is binary32 SSE: build with
 * -ffp-contract=off. Functions marked verified equal the client's
 * instructions under Unicorn (scripts/validate_skill_fx.py); the rest are
 * static readings and say so.
 *
 * Calls the client makes into other subsystems (AddTerrainLight,
 * CreateParticle, CreateJoint, nested CreateEffect, the animation player,
 * the projectile hit checks, DeleteEffect) are reported through the
 * environment's call hook in client order, so that a caller can run them and
 * a validator can compare them with the client's. */

#include <stddef.h>
#include <stdint.h>

/* ------------------------------------------------------------------------
 * Client indices. Models are AccessModel indices (Data\Skill\...), bitmaps
 * LoadBitmap indices (Data\Effect\...), both static readings of the loaders
 * 0x018202b4 and 0x0185baac. */
enum {
    MU_SFX_MODEL_STONE1 = 0x419,      /* Skill\Stone01.bmd */
    MU_SFX_MODEL_STONE2 = 0x41a,      /* Skill\Stone02.bmd */
    MU_SFX_MODEL_CIRCLE = 0x41c,      /* Skill\Circle01.bmd (Hellfire) */
    MU_SFX_MODEL_CIRCLE_LIGHT = 0x41d,/* Skill\Circle02.bmd */
    MU_SFX_MODEL_FIRE = 0x413,        /* Skill\Fire01.bmd */
    MU_SFX_MODEL_ARROW = 0x43b,       /* Skill\Arrow01.bmd */
    MU_SFX_MODEL_INFERNO = 0x457,     /* Skill\Inferno01.bmd */
    MU_SFX_BITMAP_THUNDER = 0x7f2b,   /* Effect\Thunder01.jpg (Energy Ball) */
    MU_SFX_BITMAP_SPARK3 = 0x7f26,    /* Effect\Spark03.jpg */
    MU_SFX_BITMAP_FIRE = 0x7f3c,      /* Effect\Fire01.jpg */
    MU_SFX_BITMAP_MAGIC_GROUND2 = 0x7f84, /* Effect\Magic_Ground2.jpg (Heal) */
    MU_SFX_BITMAP_JOINT_SPIRIT = 0x7fd3,  /* Effect\JointSpirit01.jpg (Evil Spirit) */
    MU_SFX_BITMAP_JOINT_ENERGY = 0x7fd8   /* Effect\JointEnergy01.jpg (Heal) */
};

/* Client routines reported through the call hook. */
enum {
    MU_SFX_CALL_TERRAIN_LIGHT = 0x016cacfc,   /* AddTerrainLight(x, y, light, range, frame light 0x0b9f5430) */
    MU_SFX_CALL_PARTICLE = 0x0168fafd,        /* CreateParticle(bitmap, pos, angle, light, sub, scale, owner, 0) */
    MU_SFX_CALL_JOINT = 0x0153b02c,           /* CreateJoint(bitmap, pos, target pos, angle, sub, target, scale, ...) */
    MU_SFX_CALL_EFFECT = 0x013c0eaa,          /* CreateEffect(type, pos, angle, light, sub, owner, ...) */
    MU_SFX_CALL_ANIMATION = 0x012b4dd3,       /* model PlayAnimation(&frame, &prior, &prior action, speed, pos, angle) */
    MU_SFX_CALL_CHECK_ARROW = 0x013bd374,     /* the arrow hit check (CheckClientArrow) */
    MU_SFX_CALL_CHECK_MAGIC = 0x013be199,     /* the spell hit check (CheckClientMagic) */
    MU_SFX_CALL_DELETE = 0x0142eea4           /* DeleteEffect(o) */
};

#define MU_SFX_EFFECTS 200
#define MU_SFX_EFFECT_BYTES 0x3d8
#define MU_SFX_NO_OWNER (-1)

/* One effect record: the OBJECT fields the effect routines here read or
 * write, client offsets in the comments. owner is an index into the
 * environment's object table (the client stores an OBJECT pointer at
 * +0x34c; -1 = none). */
typedef struct mu_sfx_effect {
    uint8_t live;            /* +0x00 */
    uint8_t flag5;           /* +0x05 (CreateEffect stores 1) */
    uint8_t visible;         /* +0x0b (RenderEffects' frustum test) */
    uint8_t flag_c;          /* +0x0c */
    uint16_t action;         /* +0x2a current action (0xff: animation done) */
    uint16_t prior_action;   /* +0x2c */
    uint8_t client_hit;      /* +0x3b the client tests the hit itself (CreateEffect info byte 4) */
    uint16_t skill;          /* +0x3c (info word 2) */
    uint8_t info6;           /* +0x45 (info byte 6) */
    uint16_t key;            /* +0x54 owner key (info word 0) */
    uint16_t serial;         /* +0x56 arrows: the hero's skill serial byte */
    int32_t type;            /* +0x5c */
    int32_t subtype;         /* +0x60 */
    int32_t field_68;        /* +0x68 (CreateEffect stores -1) */
    int32_t lifetime;        /* +0x6c */
    int32_t blend_mesh;      /* +0x74 the mesh drawn bright (-1 none) */
    int32_t field_78;        /* +0x78 */
    int32_t field_80;        /* +0x80 */
    float scale;             /* +0xa0 */
    float scale_arg;         /* +0xa4 */
    float blend_light;       /* +0xa8 brightness of the blend mesh */
    float blend_u, blend_v;  /* +0xac, +0xb0 texture scroll of the blend mesh */
    float velocity;          /* +0xbc animation speed */
    float gravity;           /* +0xc8 */
    float frame;             /* +0xd0 animation frame */
    float prior_frame;       /* +0xd4 */
    float alpha;             /* +0xdc */
    float light[3];          /* +0xec */
    float direction[3];      /* +0xf8 motion per step, in the effect's frame */
    float position[3];       /* +0x158 */
    float angle[3];          /* +0x164 degrees */
    float start[3];          /* +0x1d0 the owner's position on the ground */
    int32_t owner;           /* +0x34c */
    uint16_t field_364;      /* +0x364 (info word 8) */
    int32_t field_58;        /* +0x58 (info dword 0x18) */
    int32_t field_2e4;       /* +0x2e4 (info dword 0x1c) */
} mu_sfx_effect;

/* CreateEffect's info block (argument 8, 0x20 bytes). */
typedef struct mu_sfx_info {
    uint16_t key;            /* +0x00 -> +0x54 */
    uint16_t skill;          /* +0x02 -> +0x3c */
    uint16_t word4;          /* +0x04: low byte -> +0x3b; arrows of 0x7e7, 0x7fc, 0x7fd, 0x7fe, 0x2d7 skip the bow offset */
    uint16_t word6;          /* +0x06: low byte -> +0x45 */
    uint16_t field8;         /* +0x08 -> +0x364 */
    int32_t field18;         /* +0x18 -> +0x58 */
    int32_t field1c;         /* +0x1c -> +0x2e4 */
} mu_sfx_info;

/* What the routines read of another object (the owner or target). */
typedef struct mu_sfx_object {
    uint8_t live;            /* +0x00 */
    uint8_t visible;         /* +0x0b */
    float position[3];       /* +0x158 */
} mu_sfx_object;

/* One call into another subsystem, in client order. Vectors are the values
 * at the moment of the call (the client passes pointers). */
typedef struct mu_sfx_call {
    int32_t routine;         /* MU_SFX_CALL_* */
    int32_t type;            /* bitmap / model / effect type */
    int32_t subtype;
    int32_t owner;           /* object index, -1 none, -2 the calling effect itself */
    int32_t range;           /* AddTerrainLight range */
    float scale;
    float position[3];
    float target[3];         /* CreateJoint's second position */
    float angle[3];
    float light[3];
} mu_sfx_call;

typedef struct mu_sfx_env {
    void *context;
    /* rand() 0x01989721 in call order (non-negative 15-bit values in the client). */
    int32_t (*rand)(void *context);
    /* RequestTerrainHeight 0x016cc9e2. */
    float (*height)(void *context, float x, float y);
    /* The object behind an owner index (NULL: no object). */
    const mu_sfx_object *(*object)(void *context, int32_t index);
    /* Reports one call; for MU_SFX_CALL_ANIMATION returns the player's
     * result (1 while the animation runs), otherwise ignored. NULL: calls are
     * not reported (animations report 1). */
    int (*call)(void *context, const mu_sfx_call *call, mu_sfx_effect *effect);
    /* The model of an effect type: 0 when the client has no model for it
     * (MoveEffect then returns at once), else 1 and *keys = number of keys of
     * action `action` (+8 of the 16-byte action record). NULL: every type has
     * a model with 1 key. */
    int (*model)(void *context, int32_t type, uint16_t action, int16_t *keys);
    /* The hero's skill serial byte [[0x01d1df18] + 0x2dec] (arrows). */
    uint8_t serial;
    /* When set, the two hit checks are reported as calls instead of run. */
    uint8_t report_checks;
} mu_sfx_env;

/* CreateEffect 0x013c0f19 for the supported types and subtypes, from a
 * zeroed record (the object initialiser 0x0129eb81 is taken as clearing
 * every field, a static reading). Returns 1 when the type and subtype are
 * reconstructed, 0 otherwise (the record is then left zeroed).
 * Supported (verified): MODEL_ARROW 0x43b subtypes 0 and 2, MODEL_FIRE 0x413
 * subtype 1 (Fire Ball), Thunder01 0x7f2b subtype 0 (Energy Ball),
 * Magic_Ground2 0x7f84 subtype 1 (Heal). */
int mu_sfx_effect_create(mu_sfx_effect *e, int32_t type, int32_t subtype, const float position[3],
                         const float angle[3], const float light[3], int32_t owner, float scale,
                         const mu_sfx_info *info, const mu_sfx_env *env);

/* MoveEffect 0x0142fd09, one logic step of one live effect, for the types
 * mu_sfx_effect_create supports. Returns 1 when the type is reconstructed. */
int mu_sfx_effect_move(mu_sfx_effect *e, const mu_sfx_env *env);

/* The spell hit check 0x013be199 (static reading, its effect on MoveEffect
 * verified as a recorded call): when the target object (+0x34c) is live and
 * visible and within 100 units of the effect in x/y, LifeTime becomes 1 and
 * the impact is created (Fire Ball: two Stone01/Stone02 effects, Energy Ball:
 * a Spark03 particle of subtype 1, scale 6). */
void mu_sfx_check_magic(mu_sfx_effect *e, const mu_sfx_env *env);

/* The generic effect motion 0x0150df8e(o, rotate): position +=
 * VectorRotate(direction, AngleMatrix(angle)) (rotate) or += direction. */
void mu_sfx_effect_advance(mu_sfx_effect *e, int rotate);

#endif
