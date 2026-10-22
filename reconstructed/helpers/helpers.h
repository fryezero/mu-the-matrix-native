/* Helpers: the pets and mounts that follow or carry a character (NATIVE-HELPERS-001).
 *
 * Client routines (restored text, main.exe SHA-256 3cf91f3c...b5527a); names are investigator choices, see
 * docs/research/client-helpers.md:
 *
 *   Bugs (the Guardian Angel 0x24e6; the code also knows the Imp 0x24e7, but no caller creates one):
 *   CreateBug        0x00c9d8df  first free slot of the 10 bugs at 0x0bdc3220 (0x3d8-byte objects)
 *   CreateBugSub     0x00c9d42a  object setup, the angel's / imp's spawn offsets
 *   MoveBugs         0x00c9e24a  -> MoveBug 0x00c9d95a: follow the owner, sparkles, wander
 *   RenderBugs       0x00c9e4e3  -> RenderBug 0x00c9e28a: frustum, RenderObject, the angel's flare
 *   DeleteBug        0x00c9ea70  the owner's bugs of the types 0x00ca211e lists
 *
 *   Mounts (the mount manager 0x01d1dce0, getter 0x009c104e; one C++ object per riding character, a
 *   std::map keyed by the character key c + 0x3e):
 *   kind             0x0106cc24  (ride item, ride state) -> 0 / 1 (item kind B 0x4f) / 2 (no item, state > 0)
 *   factory          0x0106cde5  -> mount class (21 vtables, table below)
 *   set / reset      0x0106b85d / 0x0106ba49
 *   init             0x0103cf7a  mount OBJECT, model (vtable +0x38), play speeds (+8), rider offset (+0x10)
 *   base move        0x0103d45a  copy the owner's position and angle, fade, tick, offset, the riding flag
 *   class moves      vtable +0xc: Uniria 0x01064b6d (dust 0x01064cc2), Dinorant 0x0104009b (0x01040302),
 *                    Dark Horse 0x0103f2a4 (0x0103f457, 0x0103f5e0, 0x0103fc2e), Fenrir 0x010438c1 (0x01043a1c)
 *   move loop        0x0106bbb2  move (+0xc), then the action map (+0x24 0x0103d931, category 0x0106c4b6)
 *   mount action     vtable +0x28: 0x0103d9eb, Dinorant 0x010401c6
 *   rider lift       0x0106bcc5 -> 0x0103da5c with the ride-action test 0x0103dc68
 *   render loop      0x0106bc2b  body 0x0103d6d5, shadow 0x0103d281, after-pass 0x0103d830
 *   rider action     0x0106c382 -> 0x0103dd6b (unarmed) / 0x0103ddde (armed); SetPlayerStop passes 0,
 *                    SetPlayerWalk 1 (run counter < 20) or 2, the attack path 6
 *
 * Every entry point takes the client state it reads as plain inputs and calls the host for the engine
 * services: rand() (MSVC LCG, kept here), RequestTerrainHeight, SetAction, the model's animation tick,
 * CreateParticle, CreateEffect / CreateJoint, the bone lookup by name with TransformPosition, the buff list
 * and item-table predicates, and the render primitives. Float arithmetic follows the client's binary32
 * order; comparisons follow its comiss/jcc pairs.
 */
#ifndef MU_HELPERS_H
#define MU_HELPERS_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum {
    MU_HP_BUGS = 10,                 /* 0x0bdc3220 */
    MU_HP_OBJECT_BYTES = 0x3d8,
    MU_HP_MOUNTS = 32,               /* native capacity of the manager's map */
    MU_HP_SPEEDS = 16                /* play-speed keys a mount class sets (0..11 used) */
};

#define MU_HP_BUG_ARRAY 0x0bdc3220u

/* Model indices (object +0x5c). */
enum {
    MU_HP_MODEL_PLAYER = 0xa91,
    MU_HP_MODEL_ANGEL = 0x24e6,      /* item 13,0 Guardian Angel: Data/Item/helper01.bmd */
    MU_HP_MODEL_IMP = 0x24e7,        /* item 13,1 Imp: Data/Item/helper02.bmd */
    MU_HP_MODEL_DARK_SPIRIT = 0x24eb,/* item 13,5 (DeleteBug's list only) */
    MU_HP_MODEL_BUTTERFLY = 0x193,   /* MoveBug's 0x193 branch */
    MU_HP_MODEL_GHOST_HORSE = 0x671  /* CreateBugSub's scale-1 branch */
};

/* Item codes (group * 512 + index; type = code + 0xae6). */
enum {
    MU_HP_ITEM_ANGEL = 0x1a00, MU_HP_ITEM_IMP = 0x1a01, MU_HP_ITEM_UNIRIA = 0x1a02, MU_HP_ITEM_DINORANT = 0x1a03,
    MU_HP_ITEM_DARK_HORSE = 0x1a04, MU_HP_ITEM_DARK_SPIRIT = 0x1a05, MU_HP_ITEM_FENRIR = 0x1a25
};

/* Bitmaps the routines name. */
enum {
    MU_HP_BITMAP_FLARE = 0x7ef7,     /* Effect\flare01.jpg (the angel's and the imp's glow sprite) */
    MU_HP_BITMAP_SPARK2 = 0x7f25,    /* Effect\Spark02.jpg (the angel's sparkles, subtype 1) */
    MU_HP_BITMAP_SMOKE = 0x7f5a,     /* Effect\smoke01.jpg (mount dust in world 2, butterfly) */
    MU_HP_BITMAP_SMOKE_B = 0x7f5b,   /* mount dust elsewhere */
    MU_HP_BITMAP_SMOKE_C = 0x7fcd,   /* Dark Horse dust in the 0x016a88ae worlds */
    MU_HP_EFFECT_STEP = 0x8012,      /* CreateEffect: the Fenrir / Dark Horse flying step */
    MU_HP_JOINT_DARK_HORSE = 0x7f78  /* CreateJoint: the Dark Horse's ring (c + 0x328d) */
};

/* The fields of the client's 0x3d8-byte OBJECT these routines read or write, named by offset. */
typedef struct mu_hp_object {
    uint8_t live;            /* +0x00 (0x0095f977 / SetLive 0x0129f4a5) */
    uint8_t lighting;        /* +0x05 */
    uint8_t visible;         /* +0x0b */
    uint8_t alpha_enable;    /* +0x0c FadeAlpha mode */
    uint8_t flag_0d;         /* +0x0d */
    uint8_t flag_0e;         /* +0x0e */
    uint8_t flag_41;         /* +0x41 */
    uint16_t action;         /* +0x2a */
    uint16_t prior_action;   /* +0x2c */
    int32_t type;            /* +0x5c */
    int32_t subtype;         /* +0x60 */
    int32_t field_68;        /* +0x68 */
    int32_t lifetime;        /* +0x6c */
    int32_t blend_mesh;      /* +0x74 */
    float scale;             /* +0xa0 */
    float blend_light;       /* +0xa8 */
    float velocity;          /* +0xbc (also the bugs' animation speed) */
    float frame;             /* +0xd0 */
    float prior_frame;       /* +0xd4 */
    float alpha_target;      /* +0xd8 */
    float alpha;             /* +0xdc */
    float alpha_speed;       /* +0xe0 */
    float light[3];          /* +0xec */
    float direction[3];      /* +0xf8 */
    float position[3];       /* +0x158 */
    float angle[3];          /* +0x164 */
    float head_angle[3];     /* +0x170 */
    float matrix[3][4];      /* +0x2e8 */
    int32_t owner;           /* +0x34c: index into the host's owner table, -1 for NULL */
    uint8_t custom_shadow;   /* +0x3c8 (0x0103ec05) */
    float shadow_alpha;      /* +0x3cc (0x0103ebf3) */
} mu_hp_object;

/* A character as these routines see it: its OBJECT (c + 0x3254) and the CHARACTER fields they read. */
typedef struct mu_hp_owner {
    uint8_t live;            /* object +0x00 */
    uint8_t fade;            /* object +0x3a (1, 2: fading out) */
    uint8_t kind;            /* object +0x3b */
    uint16_t action;         /* object +0x2a */
    int32_t type;            /* object +0x5c */
    float position[3];       /* object +0x158 */
    float angle[3];          /* object +0x164 */
    uint8_t buff_12;         /* 0x01295ade(buffs, 0x12): the object's (+0x358) and the character's (+0x35ac) list */
    uint8_t class_byte;      /* c + 0x12 */
    uint8_t safe_zone;       /* c + 0x04 (0x0095fb27) */
    uint8_t hidden;          /* c + 0x31e8 */
    uint8_t ring;            /* c + 0x328d (the Dark Horse's ring; cleared by its move) */
    int16_t weapon[2];       /* c + 0x19ac, c + 0x1da8 (slot types, -1 none) */
    uint8_t weapon_kind[2];  /* 0x0129dd4a(c, slot): the weapon's Item.bmd kind B (0 without a record) */
    uint8_t weapon_54;       /* 0x0139d9ed(c, 0): either weapon has kind B 0x54 (0x0139da90) */
} mu_hp_owner;

/* Client state the routines read. */
typedef struct mu_hp_inputs {
    int32_t world;           /* 0x01cf15fc */
    int32_t scene;           /* SceneFlag 0x01d1df70 (0x009b0bc1) */
    int32_t event_state;     /* +4 of the event object 0x009a6ef3() + 0x78 (0x009a645f; world 0x27 only) */
    uint8_t has_pet_item;    /* 0x0129de01(hero) != -1 (callers of CreateBug in scene 6) */
} mu_hp_inputs;

typedef struct mu_hp_host {
    void *context;
    /* RequestTerrainHeight 0x016cc9e2 */
    float (*terrain_height)(void *context, float x, float y);
    /* the model getter 0x00966cc4 -> 0x00eaa8cf (NULL = always present) */
    int (*has_model)(void *context, int32_t model);
    /* the model's current action = object action, then the tick 0x012b4dd3(frame, prior frame, prior action,
     * speed, position, angle) of model `model` */
    void (*animate)(void *context, mu_hp_object *object, int32_t model, float speed);
    /* SetAction 0x012affa4 on a helper object / on an owner's object (the rider) */
    void (*set_action)(void *context, mu_hp_object *object, int32_t action);
    void (*set_owner_action)(void *context, int32_t owner, int32_t action);
    /* CreateParticle 0x0168fafd(bitmap, position, angle, light, subtype, scale, 0, 0) */
    void (*particle)(void *context, int32_t bitmap, const float position[3], const float angle[3],
                     const float light[3], int32_t subtype, float scale);
    /* CreateEffect 0x013c0eaa(type, position, angle, light, subtype, owner object, -1, 0, ...) as the mounts
     * call it (owner -1: NULL) */
    void (*effect)(void *context, int32_t type, const float position[3], const float angle[3], const float light[3],
                   int32_t subtype, int32_t owner);
    /* CreateJoint 0x0153b02c(type, position, position, angle, 0, object, 40, 2, ...) (the Dark Horse ring) */
    void (*joint)(void *context, int32_t type, const float position[3], const float angle[3],
                  const mu_hp_object *object, float scale);
    /* the bone matrix lookup 0x0129f18a(object, name, 1) and TransformPosition 0x012b6ef1(model, matrix,
     * vector, out, 0); returns 0 when the bone is missing (the client then leaves out unchanged) */
    int (*bone_position)(void *context, const mu_hp_object *object, int32_t model, const char *bone,
                         const float vector[3], float out[3]);
    /* the Dark Horse dust position 0x012b6a2b(model, out, object, name, vector) */
    void (*bone_vector)(void *context, const mu_hp_object *object, int32_t model, const char *bone,
                        const float vector[3], float out[3]);
    /* the item predicate 0x00b96c35(item table, 8) on the hero's inventory (the Dark Horse dust) */
    int (*dark_horse_flag)(void *context);
    /* the cleanup of SetLive(object, 0): 0x009b0451 (optional) */
    void (*kill)(void *context, mu_hp_object *object);
    /* the character animation reset 0x013a763e(c, object, model) the mount set/reset/init calls (optional) */
    void (*rider_reset)(void *context, int32_t owner);
} mu_hp_host;

/* ---- bugs ---- */

typedef struct mu_helpers {
    uint32_t rand_state;     /* the CRT rand() state, shared with the rest of the client */
    uint64_t rand_calls;
    mu_hp_object bugs[MU_HP_BUGS];
    mu_hp_owner *owners;     /* the characters (owner indices) */
    int32_t owner_count;
    mu_hp_host host;
} mu_helpers;

void mu_hp_init(mu_helpers *h, uint32_t rand_seed, mu_hp_owner *owners, int32_t owner_count,
                const mu_hp_host *host);
/* rand() 0x01989721: MSVC LCG. */
int32_t mu_hp_rand(mu_helpers *h);
/* FadeAlpha 0x012af883 (the same routine as reconstructed/environment's). */
void mu_hp_fade_alpha(mu_hp_object *o);

/* CreateBug 0x00c9d8df(type, position, owner, subtype, link): nothing in the worlds of 0x009dacb8 or for an
 * owner that is not a Player model unless the type is the angel; else CreateBugSub on the first free slot.
 * Returns the slot used or -1. */
int32_t mu_hp_create_bug(mu_helpers *h, const mu_hp_inputs *in, int32_t type, const float position[3],
                         int32_t owner, int32_t subtype);
/* MoveBugs 0x00c9e24a: MoveBug on every slot until one returns 0 (a missing model). */
void mu_hp_move_bugs(mu_helpers *h, const mu_hp_inputs *in);
/* DeleteBug 0x00c9ea70(owner object): SetLive 0 for the owner's live bugs of the types 0x00ca211e lists. */
void mu_hp_delete_bug(mu_helpers *h, int32_t owner);
/* 0x00ca211e: the angel, the imp and the dark spirit. */
int mu_hp_bug_type(int32_t type);

typedef struct mu_hp_render_host {
    void *context;
    /* TestFrustrum2D 0x016ccce7(x * 0.01, y * 0.01, -20) */
    int (*frustum)(void *context, float x, float y, float range);
    /* RenderObject 0x016d4fe4(object, a1, a2, a3, a4, a5) */
    void (*draw_object)(void *context, const mu_hp_object *object, int32_t a1, int32_t a2, int32_t a3, int32_t a4,
                        int32_t a5);
    /* its two halves as the mounts call them: setup + body 0x017ec896(object, a1, a2, a3) (returns 0 when nothing
     * is drawn) and the after-pass 0x017edf43(object, a1, a2, a3, a4, a5) */
    int (*draw_body)(void *context, const mu_hp_object *object, int32_t a1, int32_t a2, int32_t a3);
    void (*draw_after)(void *context, const mu_hp_object *object, int32_t a1, int32_t a2, int32_t a3, int32_t a4,
                       int32_t a5);
    /* CreateSprite 0x01692eb7(bitmap, position, scale, light, owner, rotation, 0, 4, ...) */
    void (*sprite)(void *context, int32_t bitmap, const float position[3], float scale, const float light[3],
                   const mu_hp_object *owner);
    /* EnableAlphaTest 0x0184a990(arg), glColor4f, RenderBodyShadow 0x012bc07a(model, -1, -1, -1, -1, a) */
    void (*alpha_test)(void *context, int32_t arg);
    void (*color4)(void *context, float r, float g, float b, float a);
    void (*shadow)(void *context, const mu_hp_object *object, int32_t model, int32_t arg);
} mu_hp_render_host;

/* RenderBugs 0x00c9e4e3 (RenderBug(o, 0) for each slot). */
void mu_hp_render_bugs(mu_helpers *h, const mu_hp_inputs *in, const mu_hp_render_host *r);

/* ---- mounts ---- */

enum {
    MU_HP_MOUNT_NONE = 0,
    MU_HP_MOUNT_UNIRIA, MU_HP_MOUNT_DINORANT, MU_HP_MOUNT_DARK_HORSE, MU_HP_MOUNT_FENRIR,
    MU_HP_MOUNT_GHOST_HORSE, MU_HP_MOUNT_ICE_DRAGON, MU_HP_MOUNT_ICE_DRAGON_RARE,
    MU_HP_MOUNT_PIERCE_LION, MU_HP_MOUNT_PIERCE_LION_RARE, MU_HP_MOUNT_SHINING_TAIL, MU_HP_MOUNT_SHINING_TAIL_RARE,
    MU_HP_MOUNT_UR, MU_HP_MOUNT_UR_RARE, MU_HP_MOUNT_LEVIATHAN, MU_HP_MOUNT_LEVIATHAN_RARE,
    MU_HP_MOUNT_TAUROS, MU_HP_MOUNT_TAUROS_RARE, MU_HP_MOUNT_DIVINE_HORSE,
    MU_HP_MOUNT_GIANT_1, MU_HP_MOUNT_GIANT_2, MU_HP_MOUNT_GIANT_3,
    MU_HP_MOUNT_CLASSES
};

/* One mount class: the factory's choice, the vtable, the model the class loads (vtable +0x38: Fenrir picks by
 * the ride state), the play speeds (+8) and the rider bone (+0x10). Extracted from the client's methods and
 * compared by execution (scripts/validate_helpers.py --sections mount_class). */
typedef struct mu_hp_mount_info {
    int32_t cls;
    uint32_t vtable;
    int32_t item;              /* the ride item (factory key), -1 for the ride-state classes */
    int32_t model;             /* AccessModel index (Fenrir: by state, see mu_hp_mount_model) */
    const char *file;          /* Data\Skill\<file>.bmd */
    const char *bone;          /* rider bone name (vtable +0x10) */
    float lift;                /* added to offset z when has_lift */
    uint8_t has_lift;
    uint8_t scale_offset;      /* the offset is multiplied by the object scale (the ride-state classes) */
    uint8_t ported;            /* 1: the class move (+0xc) is reconstructed; else only the base move runs */
    float scale;               /* object scale (+0xa0) the model load writes */
    float speed[MU_HP_SPEEDS]; /* play speeds by mount action (0x0103dbf4: 0.4 for keys the class does not set) */
} mu_hp_mount_info;

const mu_hp_mount_info *mu_hp_mount_class_info(int32_t cls);
/* 0x0106cc24: -1 / 0 / 1 / 2. item_kind_4f: the Item.bmd kind B of the item is 0x4f (0x00cd6017). */
int32_t mu_hp_mount_kind(int32_t item, int32_t state, int item_kind_4f);
/* 0x0106cde5 with the descriptor of 0x0106cc74: the class, MU_HP_MOUNT_NONE when the factory makes nothing. */
int32_t mu_hp_mount_class(int32_t kind, int32_t item, int32_t state);
/* vtable +0x38: the model index (Fenrir 0x4a9 red, 0x4a8 black, 0x4aa blue, 0x4ab gold by state). */
int32_t mu_hp_mount_model(int32_t cls, int32_t state);
/* 0x0103dbf4: the play speed of a mount action (0.4 when the class map has no entry). */
float mu_hp_mount_speed(int32_t cls, int32_t action);

typedef struct mu_hp_mount {
    int32_t live;              /* present in the manager's map */
    int32_t key;               /* the map key (character key c + 0x3e) */
    int32_t cls;               /* vtable */
    int32_t kind, item, state; /* +0x04 descriptor */
    int32_t model;             /* +0x10 */
    int32_t owner;             /* +0x14 / +0x18 (character / its object) */
    mu_hp_object object;       /* *(+0x1c) */
    uint8_t has_model;         /* +0x20 != NULL */
    float offset[3];           /* +0x24 */
    int32_t action;            /* +0x30 */
    uint8_t riding;            /* +0x34 */
    int32_t counter;           /* +0x38 */
    uint8_t shadow;            /* +0x3c */
    uint8_t flag_48;           /* +0x48 */
    int32_t shadow_arg;        /* +0x4c */
    uint8_t fly;               /* +0x50 (Dinorant) */
} mu_hp_mount;

typedef struct mu_hp_mounts {
    mu_hp_mount list[MU_HP_MOUNTS];   /* sorted by key (std::map order) */
    int32_t count;
} mu_hp_mounts;

/* The manager's set 0x0106b85d(helper, state, c) for owner `owner` with map key `key`: returns the mount (the
 * existing one when the key is present; NULL when the factory makes nothing or the class has no model).
 * item_kind_4f as mu_hp_mount_kind. The init 0x0103cf7a runs inside (the world-0xe136f3 shadow argument from
 * shadow_world). */
mu_hp_mount *mu_hp_mount_set(mu_helpers *h, mu_hp_mounts *m, const mu_hp_inputs *in, int32_t key, int32_t owner,
                             int32_t item, int32_t state, int item_kind_4f, int shadow_world);
/* The reset 0x0106ba49(c): removes the key's mount, then the rider reset 0x013a763e. */
void mu_hp_mount_reset(mu_helpers *h, mu_hp_mounts *m, int32_t key, int32_t owner);
mu_hp_mount *mu_hp_mount_find(mu_hp_mounts *m, int32_t key);

/* The init 0x0103cf7a on a fresh mount (class, descriptor and key set). Returns 1, or 0 when the model is
 * missing (the mount is then destroyed by the caller). */
int mu_hp_mount_init(mu_helpers *h, mu_hp_mount *mount, const mu_hp_inputs *in, int32_t owner, int shadow_world);
/* The base move 0x0103d45a. Returns its AL (the riding flag). */
int mu_hp_mount_move_base(mu_helpers *h, mu_hp_mount *mount, const mu_hp_inputs *in);
/* vtable +0xc (class move: the base move plus the class's dust / steps). Returns its AL. */
int mu_hp_mount_move(mu_helpers *h, mu_hp_mount *mount, const mu_hp_inputs *in);
/* vtable +0x10: the rider offset (bone + lift). */
void mu_hp_mount_offset(mu_helpers *h, mu_hp_mount *mount);
/* 0x016a88ae: world 7 or 0x80..0x82 (the mounts' dim shadow and the Dark Horse's dust kind). */
int mu_hp_world_16a88ae(int32_t world);
/* 0x0106c4b6: the owner action's category. */
int32_t mu_hp_action_category(uint16_t action);
/* vtable +0x24 (0x0103d931): the mount action for the owner's category, through vtable +0x28. */
void mu_hp_mount_follow_action(mu_helpers *h, mu_hp_mount *mount);
/* vtable +0x28: 0x0103d9eb (SetAction when it changes), Dinorant 0x010401c6 (flying actions). */
void mu_hp_mount_set_action(mu_helpers *h, mu_hp_mount *mount, int32_t action);
/* The move loop 0x0106bbb2. */
void mu_hp_mounts_move(mu_helpers *h, mu_hp_mounts *m, const mu_hp_inputs *in);

/* 0x0103dc68: the owner is in a ride action (offset applies). */
int mu_hp_mount_lifts(const mu_helpers *h, const mu_hp_mount *mount);
/* 0x0103da5c(lift): owner position = mount position (+ offset when lift and 0x0103dc68). */
void mu_hp_mount_place_owner(mu_helpers *h, mu_hp_mount *mount, int lift);
/* The lift loop 0x0106bcc5(lift). */
void mu_hp_mounts_place_owners(mu_helpers *h, mu_hp_mounts *m, int lift);

/* The rider action 0x0106c382(c, how) (how 0 stand, 1 walk, 2 run, 6 attack path): the owner's SetAction, or
 * nothing for other values. Returns the action set, 0 when none. */
int32_t mu_hp_rider_action(mu_helpers *h, int32_t owner, int32_t how);

/* The render loop 0x0106bc2b for one mount (body, shadow, after-pass). */
void mu_hp_mount_render(mu_helpers *h, mu_hp_mount *mount, const mu_hp_inputs *in, const mu_hp_render_host *r);
void mu_hp_mounts_render(mu_helpers *h, mu_hp_mounts *m, const mu_hp_inputs *in, const mu_hp_render_host *r);

/* ---- the Imp on the shoulder (static reading of BackCarry 0x0139db9a's helper block 0x0139ef04..0x0139f2d9) ----
 * With the helper slot type 0x24e7 in scene 5, or in scene 6 without a pet item, RenderCharacter draws the Imp
 * with RenderLinkItem(vector, c, &slot 10, type, level, option, 0, translate, 0, 1) on link bone 0x22 (slot +5),
 * part speed 0.5 (+0x14), then a flare sprite (0x7ef7, scale 1.5, light (0.5k, 0, 0), k = (rand % 30 + 70)
 * * 0.01) at TransformPosition(bone 0x22, sprite vector, world 1). Class nibble 6 with weapon 0 type 0x1b21,
 * 0x1b22, 0x1b23, 0x1b2f or 0x1b39 moves both vectors. */
typedef struct mu_hp_imp_link {
    int32_t bone;              /* 0x22 */
    float speed;               /* 0.5 */
    float vector[3];           /* RenderLinkItem's first three arguments */
    float sprite_vector[3];    /* the flare's bone vector */
} mu_hp_imp_link;
/* Returns 1 when the Imp is drawn. weapon0: slot 6 type (c + 0x1c4 + 2 * 0x3fc... the client reads slot 2 of
 * the part table, i.e. c + 0x1c4 + 0x7f8). */
int mu_hp_imp_link_plan(int32_t helper_type, int32_t scene, int has_pet_item, uint8_t class_byte, int16_t weapon0,
                        mu_hp_imp_link *out);

/* ---- equipment -> helper (what the client builds from a helper item) ---- */
enum { MU_HP_HELPER_NONE = 0, MU_HP_HELPER_BUG = 1, MU_HP_HELPER_LINK = 2, MU_HP_HELPER_MOUNT = 3,
       MU_HP_HELPER_PET = 4 };
/* The route of a helper item code: the angel is a bug (ChangeCharacterExt's effect 0x24e6, verified in
 * NATIVE-PLAYERS-001), the imp a link item (above), the ride items a mount (the manager's set with the ride
 * word c + 0x322e), the data-driven pets of 0x00b990b0 (Demon 0x1a40, Spirit of Guardian 0x1a41, Rudolph 0x1a43,
 * Panda 0x1a50, Skeleton 0x1a7b, ...) MU_HP_HELPER_PET (not reconstructed). kind_b: the item's Item.bmd kind B. */
int32_t mu_hp_helper_route(int32_t item, uint8_t kind_b);

#ifdef __cplusplus
}
#endif

#endif
