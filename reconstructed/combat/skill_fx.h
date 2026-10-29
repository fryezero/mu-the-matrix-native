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

#include "../joints/joints.h"

/* ------------------------------------------------------------------------
 * Client indices. Models are AccessModel indices (Data\Skill\...), bitmaps
 * LoadBitmap indices (Data\Effect\...), both static readings of the loaders
 * 0x018202b4 and 0x0185baac. */
enum {
    MU_SFX_MODEL_ICE = 0x412,        /* Skill\Ice01.bmd */
    MU_SFX_MODEL_POISON = 0x414,     /* Skill\Poison01.bmd, monster-only caller */
    MU_SFX_MODEL_ICE_DEBRIS = 0x41b, /* Skill\Ice02.bmd */
    MU_SFX_MODEL_WAVE = 0x41f,       /* Skill\Magic02.bmd */
    MU_SFX_MODEL_STONE1 = 0x419,      /* Skill\Stone01.bmd */
    MU_SFX_MODEL_STONE2 = 0x41a,      /* Skill\Stone02.bmd */
    MU_SFX_MODEL_DUNGEON_STONE = 0x43a, /* Object2\DungeonStone01.bmd (worlds 116..120, Deep Dungeon type 52) */
    MU_SFX_MODEL_CIRCLE = 0x41c,      /* Skill\Circle01.bmd (Hellfire) */
    MU_SFX_MODEL_CIRCLE_LIGHT = 0x41d,/* Skill\Circle02.bmd */
    MU_SFX_MODEL_FIRE = 0x413,        /* Skill\Fire01.bmd */
    MU_SFX_MODEL_ARROW = 0x43b,       /* Skill\Arrow01.bmd */
    MU_SFX_MODEL_INFERNO = 0x457,     /* Skill\Inferno01.bmd */
    MU_SFX_MODEL_LASER = 0x421,       /* Skill\Laser01.bmd (Evil Spirit's wide spirits leave one per step) */
    MU_SFX_TWISTING_SLASH = 0x453,    /* no model: spawns one swirl piece per step */
    MU_SFX_TWISTING_SWIRL = 0x454,    /* draws the caster's weapon (RenderEffects 0x015332ac) */
    MU_SFX_MODEL_TORNADO = 0x40e,     /* Object142\hs_fieldtornado.bmd (Tormenta Island, NATIVE-JOINT-001) */
    MU_SFX_MODEL_CLOUD = 0x1a1,       /* Data\\Object11\\cloud.bmd: Icarus's cloud layer around the hero (NATIVE-FIDELITY-002) */
    MU_SFX_MODEL_STAR_DRAGON = 0x5ac, /* Effect\stardr01.bmd: the character-select sky dragon (NATIVE-CHARSEL-003) */
    MU_SFX_MODEL_STAR_GLINT = 0x5ad,  /* Effect\stardr02.bmd: the glint the dragon spawns at its bone 1 */
    /* NATIVE-HELPERS-002: Fenrir's effects (its registry functor) */
    MU_SFX_MODEL_FENRIR_LIGHTNING = 0x4ac, /* Effect\lightning_type01.bmd: flashes on its owner's bones */
    MU_SFX_FENRIR_STEP = 0x4ad,       /* no model: the paws' lightning marks (decals 0x7ff4..0x7ff8) */
    MU_SFX_BITMAP_LIGHTING_A = 0x7ff4,/* Effect\eff_lightinga01..05.jpg (0x7ff4 + frame % 5) */
    MU_SFX_BITMAP_THUNDER = 0x7f2b,   /* Effect\Thunder01.jpg (Energy Ball) */
    MU_SFX_BITMAP_FLARE = 0x7ef7,     /* Effect\\flare01.jpg: Icarus's cloud puffs (sub 0, NATIVE-FIDELITY-002) */
    MU_SFX_BITMAP_SPARK3 = 0x7f26,    /* Effect\Spark03.jpg */
    MU_SFX_BITMAP_FIRE = 0x7f3c,      /* Effect\Fire01.jpg */
    MU_SFX_BITMAP_MAGIC_GROUND2 = 0x7f84, /* Effect\Magic_Ground2.jpg (Heal) */
    MU_SFX_BITMAP_JOINT_SPIRIT = 0x7fd3,  /* Effect\JointSpirit01.jpg (Evil Spirit) */
    MU_SFX_BITMAP_JOINT_ENERGY = 0x7fd8,  /* Effect\JointEnergy01.jpg (Heal) */
    MU_SFX_BITMAP_SHOCKWAVE = 0x8012,     /* Effect\ShockWave.jpg: the mounts' flying step (NATIVE-HELPERS-002) */
    /* RENDER-EFFECTS-004: Rageful Blow (loader 0x0183451b..0x018345fc) */
    MU_SFX_MODEL_GUARDIAN_WING = 0x460, /* Skill\darkwing_hetachi.bmd: Spirit of Guardian's drifting wing (pets, subtype 4) */
    MU_SFX_RAGEFUL_BLOW = 0x461,      /* no model: draws its owner's weapon (RenderEffects 0x01532bd2) */
    MU_SFX_MODEL_QUAKE1 = 0x462,      /* Skill\EarthQuake01.bmd .. 0x469 EarthQuake08.bmd */
    MU_SFX_MODEL_QUAKE2 = 0x463,
    MU_SFX_MODEL_QUAKE3 = 0x464,
    MU_SFX_MODEL_QUAKE4 = 0x465,
    MU_SFX_MODEL_QUAKE5 = 0x466,
    MU_SFX_MODEL_QUAKE7 = 0x468,
    MU_SFX_MODEL_QUAKE8 = 0x469,
    MU_SFX_MODEL_FLASHING = 0x46a,    /* Skill\flashing.bmd */
    MU_SFX_MODEL_TAIL = 0x46b,        /* Skill\tail.bmd */
    /* RENDER-EFFECTS-006: effects the world objects create with themselves as owner (info word4 from scale) */
    MU_SFX_MODEL_FLYBAT = 0x195,      /* Object124\hs_flybatA.bmd (Kubera, AccessModel 0x00e196c8) and Object144\
                                         (Kardamahal, 0x00e0e603; not installed: the client's empty model) */
    MU_SFX_MODEL_SHOAL = 0x199,       /* Object8\Fish02.bmd, loaded only in Atlans and the abyss (0x018399bf,
                                         0x01841a7a): elsewhere an empty model that only leaves its flare trail */
    MU_SFX_MODEL_SEALEAF = 0x59a      /* Object92\zu_sealeaf04.bmd (worlds 91, 92: 0x01840f53) and Object123\
                                         (122: 0x01841845, 0x00e3a40f) */
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
    MU_SFX_CALL_DELETE = 0x0142eea4,          /* DeleteEffect(o) */
    MU_SFX_CALL_SERIAL = 0x01d1df18,          /* ++[[0x01d1df18] + 0x2dec], the hero's skill serial */
    MU_SFX_CALL_QUAKE = 0x0bdb588c,           /* the earthquake offset global (Hellfire), value in scale */
    MU_SFX_CALL_AREA = 0x013bc25e,            /* the hero's area attack request(skill, range, pos, serial, key, 0, 5, 0) */
    MU_SFX_CALL_SOUND = 0x00a6ac96,           /* PlayBuffer(sound, object, 0): type = sound, owner -2 */
    MU_SFX_CALL_ATTRIBUTE = 0x016d34db,       /* TerrainWall[TERRAIN_INDEX(subtype, range)]: returns the attribute word */
    MU_SFX_CALL_POSE = 0x012b5064,            /* model Animation(bones 0x06fce398, frame, prior frame, prior action, angle,
                                                 head angle, 0, 0): poses the effect's model (type) */
    MU_SFX_CALL_BONE = 0x012b678d,            /* model TransformByObjectBone(out, o, bone (range), 0): env->bone answers */
    MU_SFX_CALL_KILL = 0x009b0451,            /* NATIVE-HELPERS-002: SetLive(o, 0)'s cleanup of the record (o = -2) */
    MU_SFX_CALL_ITEM_LINKS = 0x01295f18,      /* RENDER-EFFECTS-004: the item initialiser's +0x358 list reset (o = -2) */
    MU_SFX_CALL_WALL = 0x016d34cd             /* RENDER-EFFECTS-004: TerrainWall[(y << 8) + x], unmasked index:
                                                 subtype = x, range = y; returns the attribute word */
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
    /* NATIVE-JOINT-001 */
    uint8_t field_6;         /* +0x06 */
    int32_t field_70;        /* +0x70 the lifetime at creation (the tornado) */
    float heading;           /* +0x170 the tornado's heading (radians) */
    /* NATIVE-HELPERS-002 */
    int32_t field_64;        /* +0x64 Fenrir's lightning: fade stage; the paws' marks: the sheet frame */
    uint32_t time_mark;      /* +0x9c the paws' marks: timeGetTime() of the last frame step */
    /* RENDER-EFFECTS-004: Rageful Blow 0x461 and the item-object initialiser its renderer runs */
    float impact[3];         /* +0x110 the blow's ground point (the hop's origin) */
    float heading_yz[2];     /* +0x174, +0x178: with heading (+0x170) the weapon's second angle vector */
    uint8_t field_4;         /* +0x04 */
    float field_c0;          /* +0xc0 */
    float spin[3];           /* +0x194 per-step angle change (0x460 subtype 4) */
    /* RENDER-EFFECTS-006: the world objects' owned effects 0x195/0x199/0x59a */
    float field_cc;          /* +0xcc the shoal's pitch swing (0x199; +0xc8 gravity is its yaw swing) */
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

/* What the routines read of another object (the owner or target): the
 * joint module's object view (live +0x00, visible +0x0b, weapon +0x56,
 * position +0x158, light +0xec). */
typedef mu_jt_object mu_sfx_object;

/* One call into another subsystem, in client order (the joint module's call
 * record; vectors are the values at the moment of the call). */
typedef mu_jt_call mu_sfx_call;

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
    /* Object index of the hero ([0x0a39d754] + 0x3254), -1 none. */
    int32_t hero_object;
    /* NATIVE-CHARSEL-003: the world position of the effect model's bone (after MU_SFX_CALL_POSE); NULL: the
     * effect's position. */
    void (*bone)(void *context, const mu_sfx_effect *effect, int32_t bone, float out[3]);
    /* NATIVE-HELPERS-002: timeGetTime() (ms; NULL: 0) and TransformPosition(owner model, BoneTransform + 0x30 *
     * bone, in, out, 0) on the owner's posed model (NULL: out is left alone) */
    uint32_t (*time_ms)(void *context);
    void (*owner_bone)(void *context, int32_t owner, int32_t bone, const float in[3], float out[3]);
    float world_time;        /* 0x06fce370, warp pulse clock */
} mu_sfx_env;

/* CreateEffect 0x013c0f19 for the supported types and subtypes, from a
 * zeroed record (the object initialiser 0x0129eb81 is taken as clearing
 * every field, a static reading). Returns 1 when the type and subtype are
 * reconstructed, 0 otherwise (the record is then left zeroed).
 * Supported (verified): MODEL_ARROW 0x43b subtypes 0 and 2, MODEL_FIRE 0x413
 * subtype 1 (Fire Ball), Thunder01 0x7f2b subtype 0 (Energy Ball),
 * Magic_Ground2 0x7f84 subtype 1 (Heal); the area skills' Circle01 / Circle02
 * 0x41c / 0x41d (Hellfire), Inferno01 0x457, Laser01 0x421 (Evil Spirit),
 * 0x453 / 0x454 (Twisting Slash), all subtype 0; Stone01 / Stone02 0x419 /
 * 0x41a subtypes 0 and 1 (impact and area debris); the Tormenta tornado 0x40e
 * subtype 0 (NATIVE-JOINT-001: the hero's object through hero_object, the
 * PlayBuffer call through MU_SFX_CALL_SOUND). */
/* RenderEffects' helper decals and the shock ring in RenderTerrainEffects. flat is the alternate
 * 0x00deec1f path in worlds 0x18..0x1d / 0x24: a separate signed height grid plus 400, 50-unit cells.
 * Only its call selection is reconstructed here; native rendering awaits that grid's loader. */
typedef struct mu_sfx_decal {
    int32_t texture;
    float size, light[3], rotation;
    int32_t flat;
} mu_sfx_decal;
int mu_sfx_effect_decal(const mu_sfx_effect *effect, int32_t world, mu_sfx_decal *out);

/* Warp types 0x1a8/9/b/c clear the writable caller light after copying it. */
int mu_sfx_effect_create(mu_sfx_effect *e, int32_t type, int32_t subtype, const float position[3],
                         const float angle[3], float light[3], int32_t owner, float scale,
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

/* ------------------------------------------------------------------------
 * Particles (CreateParticle 0x015ae7b0, MoveParticles 0x01616c80,
 * RenderParticles 0x0159123f). The client keeps them in a list of shared
 * records (0x0a3a9adc); the record fields used here: */
typedef struct mu_sfx_particle {
    uint8_t live;            /* +0x08 */
    int32_t type;            /* +0x0c */
    int32_t tex_type;        /* +0x10 the bitmap drawn */
    int32_t subtype;         /* +0x14 */
    float scale;             /* +0x18 */
    float position[3];       /* +0x20 */
    float angle[3];          /* +0x2c */
    float light[3];          /* +0x38 */
    int32_t lifetime;        /* +0x48 */
    int32_t owner;           /* +0x50 object index, -1 none */
    float owner_position[3]; /* +0x54 */
    float rotation;          /* +0x60 degrees */
    int32_t frame;           /* +0x64 sprite-sheet cell */
    uint8_t moving;          /* +0x68 position += VectorRotate(velocity, AngleMatrix(angle)) each step */
    float gravity;           /* +0x6c */
    float velocity[3];       /* +0x70 */
    float start[3];          /* +0x88 */
    float start_angle[3];    /* +0x94 */
    float time;              /* +0xac */
    int32_t arg8;            /* +0xb0 CreateParticle argument 8 */
} mu_sfx_particle;

/* CreateParticle 0x015ae7b0(type, position, angle, light, subtype, scale,
 * owner, arg8) for the supported kinds (verified): Fire01 0x7f3c subtypes 0
 * and 5 (arrow and Fire Ball trails), Thunder01 0x7f2b subtype 0 (Energy
 * Ball), Spark03 0x7f26 subtypes 0 and 1 (Energy Ball glow and impact).
 * Without an owner (owner < 0). Returns 1 when supported. The wrapper
 * 0x0168fafd may drop a particle in some worlds (rand() % [0x0a39d768]); the
 * world-agnostic default keeps every particle. */
int mu_sfx_particle_create(mu_sfx_particle *p, int32_t type, const float position[3], const float angle[3],
                           const float light[3], int32_t subtype, float scale, int32_t owner, int32_t arg8,
                           const mu_sfx_env *env);

/* One logic step of MoveParticles 0x01616c80 for one record (verified):
 * returns 0 when the client removes the record at the head of the step
 * (LifeTime <= 0 or not live), else moves it (the motion flag, the kind's
 * case, LifeTime - 1, time += time_step [0x01cf103c]) and returns 1. */
int mu_sfx_particle_move(mu_sfx_particle *p, float time_step);

/* The bitmap record RenderParticles reads (+0x204 width, +0x208 height,
 * +0x214 component count; the loaders store the uploaded texture size). */
typedef struct mu_sfx_bitmap_info {
    float width, height;
    int8_t components;
} mu_sfx_bitmap_info;

/* Arguments of RenderSprite 0x0184c39c(bitmap, position, width, height,
 * light, rotation, u, v, u width, v height, rotation axes). */
typedef struct mu_sfx_sprite {
    int32_t bitmap;
    float position[3];
    float width, height;
    float light[3];
    float rotation;
    float u, v, uw, vh;
    int32_t axes;            /* bit 0 x, bit 1 y, bit 2 z: the axes the rotation turns about */
    uint8_t additive;        /* blend wrapper 3 (ONE, ONE) for 3-component bitmaps, else 0x0184a990(0) */
} mu_sfx_sprite;

/* RenderParticles' per-record part (verified): skips the record in mode 1
 * when z > 350 and in mode 2 when 300 >= z; otherwise the blend state and
 * one RenderSprite call. Returns the number of sprites (0 or 1). */
int mu_sfx_particle_render(const mu_sfx_particle *p, const mu_sfx_bitmap_info *bitmap, uint8_t mode,
                           mu_sfx_sprite *sprite);

/* RenderSprite's corners (static reading): the position is transformed by
 * the camera matrix 0x0bdc5918 (row-major 3x4), half width / height
 * w = width / 2, h = height / 2; rotation 0 gives (x-w, y-h), (x+w, y-h),
 * (x+w, y+h), (x-w, y+h) at the eye z, otherwise (+-w, +-h, 0) turned by
 * AngleMatrix of the rotation on the axes of `axes` and added to the eye
 * position. uv[i] = (u, v), (u+uw, v), (u+uw, v+vh), (u, v+vh); drawn as
 * GL_QUADS with glColor3fv(light) for 3-component bitmaps. */
void mu_sfx_sprite_corners(const float camera[12], const mu_sfx_sprite *sprite, float corners[4][3],
                           float uv[4][2]);

/* ------------------------------------------------------------------------
 * Joints: one implementation in reconstructed/joints (NATIVE-JOINT-001);
 * these wrappers keep NATIVE-COMBAT-002's entry points. */
#define MU_SFX_JOINTS MU_JT_JOINTS
#define MU_SFX_JOINT_TAILS MU_JT_TAILS

enum {
    MU_SFX_CALL_SPRITE = MU_JT_CALL_SPRITE,           /* CreateSprite(bitmap, pos, scale, light, owner, rotation, blend, axes) */
    MU_SFX_CALL_AREA_ATTACK = MU_JT_CALL_AREA_ATTACK  /* the hero's area attack request (skill, range, pos, ...) */
};

typedef mu_jt_joint mu_sfx_joint;

/* CreateJoint through mu_jt_create (the common part runs for every kind; the
 * record keeps its previous contents). Returns 1 when the kind is
 * reconstructed (mu_jt_kind_supported). */
int mu_sfx_joint_create(mu_sfx_joint *j, int32_t type, const float position[3], const float target_position[3],
                        const float angle[3], int32_t subtype, int32_t target, float scale, uint16_t key,
                        uint16_t skill, uint8_t byte10, uint16_t word13, int32_t arg14, const mu_sfx_env *env);

/* MoveJoint through mu_jt_move. wall: the terrain attribute at the head,
 * wall_scene: [0x01ec8ee7]; is_hero_target: the target is the hero. */
int mu_sfx_joint_move(mu_sfx_joint *j, const mu_sfx_env *env, float time_step, int wall_scene, uint16_t wall,
                      int is_hero_target);

/* One textured quad of RenderJoints (GL_QUADS, uv per corner). */
typedef struct mu_sfx_joint_quad {
    float position[4][3];
    float uv[4][2];
} mu_sfx_joint_quad;

/* RenderJoints through mu_jt_render at WorldTime 0: the quads, the record
 * colour (the first glColor3f) and the render type. */
int mu_sfx_joint_render(const mu_sfx_joint *j, uint8_t mode, float color[3], int32_t *render_type,
                        mu_sfx_joint_quad *quads, int max);

/* RENDER-EFFECTS-003 adds Fire01/0 and Aqua Beam 0x7f4e/0 for ordinary worlds.
 * Aqua creation excludes the hero-only source writeback and area-request services.
 * Original 0x013c07f4, bounded Inferno subtype 0. */
void mu_sfx_inferno_burst(const float position[3], uint8_t visible, const mu_sfx_env *env);

/* RenderEffects primary Aqua Beam sprite/light chain, ordinary worlds. */
void mu_sfx_aqua_render(mu_sfx_effect *effect, const mu_sfx_env *env);

/* RENDER-EFFECTS-004: the item object initialiser 0x016da00b (per-model blend presets; the
 * WorldTime clock is env->world_time) and Rageful Blow's weapon draw, RenderEffects 0x01532bd2:
 * from step 11 of its 20 on, the owner's weapon model (owner +0x56 + 0xae6) at the record
 * position. The record is re-initialised as that item (light 0.3, scale 0.8 or the preset,
 * gravity kept) before RenderPartObject 0x017e63f4. terrain_light: RequestTerrainLight 0x016cb08d
 * at the position; hero_byte: [[0x0a39d754] + 0x12]. Returns 0 when nothing is drawn. */
typedef struct mu_sfx_weapon_draw {
    int32_t model;
    float origin[3];          /* model BodyOrigin +0x78 */
    float angle[3], head_angle[3];
    float frame, prior_frame;
    uint16_t prior_action, action;
    uint8_t hero_class;       /* model +0xa4 */
    float light[3];
    float alpha;
    int32_t level;            /* RenderPartObject argument 5: owner +0x41 << 3 */
} mu_sfx_weapon_draw;

void mu_sfx_item_object_init(mu_sfx_effect *e, const mu_sfx_env *env);
int mu_sfx_rageful_weapon(mu_sfx_effect *e, const float terrain_light[3], uint8_t hero_byte, const mu_sfx_env *env,
                          mu_sfx_weapon_draw *out);

/* RENDER-EFFECTS-004: CreateArrows 0x0158d5bd(character, object, target, skill, flag, skill index) and
 * CreateArrow 0x0158cf57 (verified). The archer's inputs that come from other subsystems: */
typedef struct mu_sfx_archer {
    int16_t weapon;           /* character + 0x19ac: the slot-0 item model type */
    int32_t hero_weapon;      /* [[0x01d1df18] + 0x1b68], the hero's slot-0 item index (-1 none) */
    uint8_t is_hero;          /* character == [0x0a39d754] */
    uint8_t master_1a2;       /* 0x00bb1e55 on skill record 0x1a2 (0x00ac3bf7 / 0x0095f998) */
    int32_t tree_value;       /* 0x01094039(skill index): CreateArrow's last argument in the fan */
    int32_t mastery;          /* 0x00bb1c32 on the current skill's record */
    uint8_t special;          /* 0x00cd6017 on the bow's attribute 0x54: the 0x6a9 shot */
    uint16_t key;             /* object + 0x54 */
    uint16_t field_364;       /* object + 0x364 */
} mu_sfx_archer;

#define MU_SFX_ARROW_SHOTS 8
typedef struct mu_sfx_arrow_shots {
    int count;                /* CreateArrow calls, in order */
    float angle[MU_SFX_ARROW_SHOTS][3];   /* the object's angle at each call */
    int32_t last[MU_SFX_ARROW_SHOTS];
    int serial_steps;         /* ++[[0x01d1df18] + 0x2dec] */
    int bow_sparks;           /* bow 0x12f9's fifteen bone sparks follow (not reconstructed) */
} mu_sfx_arrow_shots;

/* angle: the object's angle, turned for each shot and restored. Returns the number of shots. */
int mu_sfx_create_arrows(const mu_sfx_archer *a, float angle[3], uint16_t skill, uint16_t flag, uint16_t index,
                         mu_sfx_arrow_shots *out);

enum { MU_SFX_CALL_ARROW_EFFECT = 0x013c0e0a };   /* CreateEffect(type, subtype, pos, angle, light, owner, scale, info) */
enum { MU_SFX_ARROW_OWNER_OBJECT = 0, MU_SFX_ARROW_OWNER_CHARACTER = 1, MU_SFX_ARROW_OWNER_TARGET = 2 };
typedef struct mu_sfx_arrow_effect {
    int32_t routine;          /* 0: nothing (no arrow for this bow), MU_SFX_CALL_EFFECT (0x49d), MU_SFX_CALL_ARROW_EFFECT */
    int32_t type, subtype, owner;
    float position[3], angle[3];   /* light: the object's; scale 0 */
    mu_sfx_info info;
    int32_t sounds[3];        /* PlayBuffer(sound, object, 0); negative: 0x00a6ad76(-sound, 1) */
    int sound_count;
} mu_sfx_arrow_effect;

int mu_sfx_create_arrow(const mu_sfx_archer *a, const float position[3], const float angle[3], uint16_t skill,
                        uint16_t flag, uint16_t index, int32_t last, const mu_sfx_env *env, mu_sfx_arrow_effect *out);

#endif
