#ifndef MU_RENDERCHAR_H
#define MU_RENDERCHAR_H

#include <stdint.h>

/* NATIVE-RENDERCHAR-001: the client's in-world character/object render
 * decisions (docs/research/client-renderchar.md).
 *
 * This library does not draw. It reproduces the sequence of mesh-draw calls
 * the client issues for one item and the model fields it writes before each
 * call, so that a caller can feed them to the mesh-draw port
 * (native/core/mu_meshdraw). Every rule cites the client address it comes from
 * and is compared with the client's actual instructions executed under
 * Unicorn (scripts/validate_renderchar.py).
 *
 * Coverage ("generic" items): the paths of RenderObjDraw 0x0176ce74,
 * RenderPartObjectBody 0x016e036c, RenderPartObjectBodyColor 0x016dec15,
 * RenderPartObjectBodyColor2 0x016dc148 and the colour helpers 0x016db5eb,
 * 0x016dba54, 0x01806042 that an item type takes when none of their
 * type-specific branches matches. Types with their own branches are listed by
 * mu_rc_item_special (generated from the executed sweep); the library refuses
 * them. */

enum {
    MU_RC_OK = 0,
    MU_RC_SPECIAL = 1,      /* type takes a type-specific branch (not reconstructed) */
    MU_RC_UNSUPPORTED = 2,  /* outside the reconstructed domain (select, shadow, record type 4) */
    MU_RC_FULL = 3          /* output array too small */
};

enum { MU_RC_ENTRY_BODY = 1,   /* RenderBody default-buffer wrapper 0x00966def */
       MU_RC_ENTRY_MESH = 2 }; /* RenderMesh default-buffer wrapper 0x00966e4a */

/* One call into the mesh draw with the model fields current at the call. */
typedef struct mu_rc_draw {
    int32_t entry;
    int32_t mesh;           /* MESH only: mesh index */
    uint32_t flags;         /* render flags (mesh-draw mode word) */
    float alpha;
    int32_t blend_mesh;     /* object +0x74 */
    float blend_light;      /* object +0xa8 */
    float u, v;             /* object +0xac, +0xb0 */
    int32_t hidden;         /* BODY only: hidden mesh */
    int32_t texture;        /* bitmap override, -1 none */
    float body_light[3];    /* model +0x54 */
    int32_t level_field;    /* model +0x40 */
    float shade[3];         /* model +0x44 */
    uint8_t flag_ca;        /* model +0xca */
} mu_rc_draw;

/* Model fields the routines read and write (caller keeps them across calls). */
typedef struct mu_rc_model {
    float body_light[3];    /* +0x54 */
    int32_t level_field;    /* +0x40 */
    float shade[3];         /* +0x44 */
    uint8_t flag_ca;        /* +0xca */
    uint8_t hide_skin;      /* +0xa5 */
} mu_rc_model;

/* Arguments of RenderObjDraw 0x0176ce74 plus the state it reads. */
typedef struct mu_rc_item {
    int32_t type;           /* model index; items are 0xae6 + group*512 + index */
    int32_t item_level;     /* arg 5: level << 3 (bits 3..6 used) */
    int32_t option1;        /* arg 6: excellent flag byte (only == 1 counts) */
    int32_t ext_option;     /* arg 7: ancient bits */
    int32_t select;         /* arg 8 (0 only) */
    uint32_t render_type;   /* arg 9 */
    int32_t a10, a11, a12;  /* args 10..12 (hidden mesh, override texture, body arg) */
    int32_t a13;            /* arg 13 byte */
    float alpha;            /* arg 4 */
    float light[3];         /* arg 3 (character light) */
    /* object */
    float object_alpha;     /* +0xdc */
    int32_t blend_mesh;     /* +0x74 */
    float blend_light, u, v;/* +0xa8, +0xac, +0xb0 */
    uint8_t buff_39, buff_12, buff_41; /* object buffs that suppress the excellent/ancient tail */
    uint8_t object_shadow;  /* +4 (1 = shadow pass, not reconstructed) */
    /* engine state */
    float time;             /* 0x06fce370 */
    int32_t quality;        /* [[0x01d22c7c]+0x2c] graphics option */
    int32_t has_record;     /* item-table record for type-0xae6 exists */
    uint8_t kind_a, kind_b, item_kind; /* record +0x250, +0x251, +0x252 */
    float enchant[3];       /* EnchantEffect colour for the type (table 0x06fbb754 lookup) */
} mu_rc_item;

/* Effective glow level (0x0176cf4a..0x0176dce9). */
int32_t mu_rc_item_glow_level(const mu_rc_item *item);
/* Draw calls for one item; count receives the number written. */
int mu_rc_item_draws(const mu_rc_item *item, mu_rc_model *model, mu_rc_draw *out, int32_t capacity,
                     int32_t *count);
/* The same without the type check (the classification sweep uses it). */
int mu_rc_item_draws_generic(const mu_rc_item *item, mu_rc_model *model, mu_rc_draw *out, int32_t capacity,
                             int32_t *count);
/* 1 when the type takes a type-specific branch the library does not reproduce. */
int mu_rc_item_special(int32_t type);

/* PartObjectColor 0x016db5eb for a type without a hardcoded colour:
 * out = alpha*bright*enchant, then the kind-B overrides 0x26 / 0x5b. */
void mu_rc_part_object_color(const mu_rc_item *item, float alpha, float bright, float out[3]);

#endif

/* Back-carry root matrix (RenderLinkItem 0x012bd910 in link mode, generic
 * path 0x012c29e4): the root matrix 0x078965ac = concat(owner bone, local)
 * through the reconstructed pose concat 0x00cff83e, where local is the
 * per-(type, kind B, right hand) matrix of back_matrices.h (extracted by
 * execution). bone/out are twelve binary32 bit patterns, row-major 3x4.
 * Returns 1, or 0 when the type takes another path (no plain table entry). */
int mu_rc_back_root(const uint32_t bone[12], int32_t type, int32_t kind_b, int32_t right_hand, uint32_t out[12]);
/* The table entry alone (local matrix): 1 composed under the bone, 2 absolute, 0 none. */
int mu_rc_back_local(int32_t type, int32_t kind_b, int32_t right_hand, uint32_t out[12]);

/* ---- RenderCharacter 0x01363260 call plan (Player characters) ----
 * The calls the client's character render makes into RenderPartObject
 * 0x017e63f4 (shadow and body parts) and RenderLinkItem 0x012bd910 (weapons,
 * back-carried weapons, wing), with the part animation fields it writes
 * first. Domain: Player model 0xa91, kind 1, generic world (0), class nibbles
 * other than 4, 5, 6 and 13, no buffs, character byte +0xe clear. */

typedef struct mu_rc_slot {
    int32_t type;           /* -1 empty */
    int8_t level;           /* +2 */
    uint8_t option;         /* +3 */
    uint8_t ext;            /* +4 */
    int32_t has_record;     /* item record present */
    uint8_t kind_b;         /* record +0x251 */
    uint8_t action;         /* +6 part action (input; may be rewritten) */
    float frame, prior_frame, speed; /* +0xc, +0x10, +0x14 */
} mu_rc_slot;

typedef struct mu_rc_character {
    uint8_t class_byte;     /* +0x12 */
    uint8_t safe_zone;      /* +4 */
    uint16_t action;        /* object +0x2a */
    float frame;            /* object +0xd0 */
    float alpha;            /* object +0xdc */
    int32_t translate, select;
    mu_rc_slot parts[6];    /* +0x1c4 */
    mu_rc_slot weapons[2];  /* +0x19ac */
    mu_rc_slot wing;        /* +0x21a4 */
    float player_speed[0x186]; /* Player model action play speeds (record +4) */
} mu_rc_character;

enum { MU_RC_CALL_SHADOW = 1, MU_RC_CALL_PART = 2, MU_RC_CALL_LINK = 3 };

typedef struct mu_rc_call {
    int32_t kind;
    int32_t slot;           /* part slot, weapon slot, or 8 for the wing; -1 for the shadow */
    int32_t type;
    int32_t item_level;     /* PART: level << 3; LINK: level */
    int32_t option;         /* PART: option != 0; LINK: option byte */
    int32_t ext;
    int32_t render_type;
    int32_t translate, select;
    float xyz[3];           /* LINK vector */
    int32_t link, right_hand;
    /* part fields at a LINK call */
    int32_t link_bone, part_action;
    float part_speed, part_frame, part_prior_frame;
} mu_rc_call;

int mu_rc_character_plan(const mu_rc_character *c, mu_rc_call *out, int32_t capacity, int32_t *count);

/* ---- the character light (NATIVE-FIDELITY-001) ----
 * RenderCharacter 0x01363260 writes the light its body parts are drawn with
 * (character +0x1b8, passed to every part's RenderPartObject) in the block
 * 0x01367530..0x01367d85:
 *   base = scene state 5 ? (0.4, 0.4, 0.4) : RequestTerrainLight 0x016cb08d at the
 *          object position (the frame light, no 0.1 factor)
 *   light = base + object light (+0xec)
 *   object type (+0x5c) 0x7dc: light = (0.6, 0.6, 0.6)
 *   else when 0x0139bcdc(character +0x146) holds (monster indices 0x211..0x21b, 0x349..0x34c,
 *        0x371..0x373, 0x3c1, 0x3d5): a red fading glow with particles (MU_RC_UNSUPPORTED here)
 *   the hero (character == [0x0a39d754]):
 *     L = (1, 1, 1); for each bit of Hero +0x1a6 ([0x01d1df1c], set by the
 *     state packet handler 0x012474bc): bit 0 L *= (0.9, 0.5, 0.5), bit 1 (0.5, 0.9, 0.5),
 *     bit 2 (0.9, 0.5, 0.5), bit 3 (0.9, 0.5, 0.5) (in that order, binary32)
 *     scene state 5: light = (0.5, 0.5, 0.5) + object light; otherwise light = L.
 * Later branches of RenderCharacter (the class-1 world rule 0x0136a06b, the PK colour
 * 0x0136ac25, the slot loop) rewrite the light for their cases; they are outside this
 * function. */
typedef struct mu_rc_light_in {
    int32_t scene_state;        /* [0x01d1df70] */
    float terrain_light[3];     /* RequestTerrainLight 0x016cb08d(x, y) (used when scene state != 5) */
    float object_light[3];      /* object +0xec */
    int32_t model_type;         /* object +0x5c */
    int32_t class_index;        /* character +0x146 (word, sign-extended) */
    int32_t is_hero;            /* character == [0x0a39d754] */
    uint8_t ability;            /* Hero +0x1a6 */
} mu_rc_light_in;

/* 1 when 0x0139bcdc(index) holds (the glow branch of the block). */
int mu_rc_light_glow_class(int32_t index);
/* MU_RC_OK with out = character +0x1b8 after the block, or MU_RC_UNSUPPORTED (glow branch). */
int mu_rc_character_light(const mu_rc_light_in *in, float out[3]);
