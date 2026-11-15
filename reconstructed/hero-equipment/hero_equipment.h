#ifndef MU_HERO_EQUIPMENT_H
#define MU_HERO_EQUIPMENT_H
/* HERO-ITEMS-001: the hero's part slots from the hero's equipment (docs/research/client-render-items.md part 21).
 *
 * Other players' CHARACTER part slots come from the viewport's 18 equipment bytes (ChangeCharacterExt 0x0137b68c,
 * reconstructed/players). The hero's come from its own inventory: CharacterMachine [0x01d1df18] keeps the equipped
 * ITEM records at +0x1b58 + s * 0x12c (s: 0 right hand, 1 left hand, 2..6 helm, armour, pants, gloves, boots,
 * 7 wing, 8 helper), and 0x01394870 (SetCharacterClass; verified under Unicorn, scripts/validate_hero_items.py)
 * writes them into the same slot records c + 0x1c4 + k * 0x3fc that RenderCharacter / RenderLinkItem read:
 *
 *   only for a Player-model character (o + 0x5c == 0xa91, c + 0x32b0);
 *   weapons  slot 6/7 <- s 0/1: type = code + 0xae6 (-1 when code == -1), level = (level word >> 3) & 15,
 *            option = 0x00cd0995(item, 1), ext = item +0x3b;
 *   wing     slot 8 <- s 7: type and level only (option and ext keep their values);
 *   helper   slot 10 <- s 8: type and level only;
 *   parts    slot 1..5 <- s 2..6: an empty slot takes the class part 0x3700 + 0x50 * (k - 1) + skin
 *            (0x0139d6a2), otherwise as the weapons (type, level, option, ext);
 *   head     slot 0 <- 0x01394f6f (unless c + 0xe): the class head 0x3700 + skin for the helm types that leave the
 *            head visible, otherwise -1.
 * Slot 9 (muun) is not written. The rest of 0x01394870 is not reproduced here: 0x009dadf1 (the castle worlds'
 * weapon override, worlds of 0x009dacb8 only), the rest of 0x01394f6f (body scale +0x32f4, part floats +0x288),
 * the hero-only 0x0137ad93 and the stat machine's 0x00a00fb7. An unused flag ([ebp-1], from 0x009dacb8 and
 * c + 0x327e) is computed and never read. */
#include <stdint.h>

#include "../players/remote_players.h"

#define MU_HE_EQUIPMENT 9          /* equipment slots 0x01394870 reads */
#define MU_HE_ITEM_STRIDE 0x12c
#define MU_HE_MODEL_BASE 0xae6     /* MODEL_ITEM: model index = item code + 0xae6 */
#define MU_HE_PART_BASE 0x3700     /* the class parts: helm; + 0x50 per part */
#define MU_HE_PART_STRIDE 0x50

enum { MU_HE_RIGHT = 0, MU_HE_LEFT = 1, MU_HE_HELM = 2, MU_HE_BOOTS = 6, MU_HE_WING = 7, MU_HE_HELPER = 8 };

/* The ITEM fields read (CharacterMachine +0x1b58 + s * 0x12c). */
typedef struct mu_he_item {
    int32_t type;      /* +0x10 item code (group * 512 + index), -1 empty */
    int32_t level;     /* +0x14 level word: the item level is (word >> 3) & 15 */
    uint8_t ancient;   /* +0x3b (the ext byte of the slot) */
    uint8_t flag_92;   /* +0x92 */
    uint8_t flag_98;   /* +0x98 */
} mu_he_item;

/* APP-POLISH-008: the ITEM fields an equipment record of the offline session carries (the hero's own items; the
 * server writes them in the client): code -> +0x10, level 0..15 -> the level word +0x14 = level << 3 (the bits
 * SetCharacterClass reads back as (word >> 3) & 15; the word's other bits 0), option 0/1 -> +0x98 (the flag
 * 0x00cd0995(item, 1) tests == 1), ext -> +0x3b; +0x92 0. Not client code: the inverse of the reads below,
 * checked against the client's own reads by scripts/validate_hero_items.py (family record). */
mu_he_item mu_he_item_of_record(int32_t code, uint8_t level, uint8_t option, uint8_t ext);
/* 0x00cd0995 (thiscall on the ITEM, one argument): 0 for a code outside 0..0x2c00; mode 0: +0x3b & 0x33 != 0,
 * mode 1: +0x98 == 1, mode 2: +0x92 == 1, other modes 0. */
uint8_t mu_he_item_flag(const mu_he_item *item, int32_t mode);
/* 0x01394f6f's head slot from the helm slot's type (class head or -1). */
int16_t mu_he_head_type(int16_t helm_type, uint8_t class_byte);
/* The client's equipment slot behind CHARACTER slot k (6/7 hands, 8 wing, 10 helper, 1..5 parts), -1 none. */
int32_t mu_he_equipment_of_slot(int32_t k);
/* 0x01394870's slot writes (and 0x01394f6f's head slot) on c from the equipment. */
void mu_he_set_character_class(mu_rp_character *c, const mu_he_item equipment[MU_HE_EQUIPMENT]);

/* ---- HERO-ITEMS-002 (docs/research/client-render-items.md, the hero's head slot, castle weapons and scales) ----
 *
 * 0x01394870 ends with 0x009dadf1(c) and 0x01394f6f(c); both are reproduced here (scripts/validate_hero_items.py,
 * families castle, scale, head_rows and part_loop). */

/* 0x009dacb8(world): the Chaos Castle worlds 0x12..0x17, 0x35 and 0x61. */
uint8_t mu_he_castle_world(int32_t world);
/* The weapon slots 0x009dadf1 writes for a class nibble (0x0095f5cc = class byte & 15) in those worlds:
 * 1, 3, 4, 6, 7, 9, 10, 13, 15: both hands 0x0af6; 2: right hand 0x12f9; 0, 5, 8, 11, 12, 14: right hand 0x14eb.
 * A hand the rule does not write keeps 0x009dad3f's -1. */
void mu_he_castle_weapons(uint8_t class_byte, int16_t type[2]);
/* 0x009dadf1(c): nothing outside the castle worlds (returns 0). In them (returns 1): 0x009dad3f clears the wing and
 * the helper (type -1, level 0), both weapons (type -1, level 0, option 0) and c + 0x16; then the class weapons at
 * level 0. Ext bytes and the weapons' options after the clear are not written again. The three interface calls
 * between the clear and the weapons (0x009dc341, 0x011e042c, 0x011f4019) are the host's and write no slot. */
int mu_he_castle_override(mu_rp_character *c, int32_t world);

/* 0x01394f6f's inputs besides the character: the world [0x01cf15fc], the scene state 0x009b0bc1([0x01d1df70]) and
 * the answers of the buff list (c + 0x35ac).0x01295ade(0x1a8 / 0x1a9). */
typedef struct mu_he_scale_in {
    int32_t world, scene;
    uint8_t buff_1a8, buff_1a9;
} mu_he_scale_in;

/* The branch of 0x01394f6f that wrote the OBJECT scale. */
enum {
    MU_HE_SCALE_SKIPPED = 0,   /* c + 0xe set: nothing is written, the head slot included */
    MU_HE_SCALE_CASTLE = 1,    /* castle world: by class nibble (jump table 0x013953f3), no scene or buff test */
    MU_HE_SCALE_SCENE5 = 2,    /* scene 5 (character select): 1.7 */
    MU_HE_SCALE_CLASS = 3,     /* by class nibble (jump table 0x01395433) */
    MU_HE_SCALE_BUFF = 4       /* the class value replaced by 1.1 under buff 0x1a8 or 0x1a9 */
};

/* The floats 0x01394f6f writes. In/out: a field the routine does not write keeps the caller's value. */
typedef struct mu_he_scale {
    float part[6];        /* c + 0x288 + k * 0x3fc (slot record +0xc4), k 0..5: RenderPartObject's vertex scale */
    float object;         /* c + 0x32f4 = OBJECT +0xa0, the body scale */
    uint8_t branch;       /* MU_HE_SCALE_* */
    uint8_t buff_queries; /* 0x01295ade calls made: 0, 1 (0x1a8 answered) or 2 */
} mu_he_scale;

/* The OBJECT scale of a class nibble in a castle world (0.88 for 2, else 0.9) and elsewhere (0.9, 0.9, 0.88, 0.95,
 * 0.92, 0.9, 1.03, 0.9, 0.9, 0.9, 0.9, 0.99, 0.9, 0.9, 0.8, 1.1). */
float mu_he_class_scale(uint8_t class_byte, int castle);
/* 0x01394f6f(c): the head slot (as mu_he_head_type, from the helm slot), the six part floats and the OBJECT scale.
 * Part floats: 0, except 0.95 for class nibble 11's helm slot (k 1) outside the castle worlds. */
void mu_he_character_scale(mu_rp_character *c, const mu_he_scale_in *in, mu_he_scale *scale);
/* 0x01394870 complete, in the client's order: the slot writes, 0x009dadf1, 0x01394f6f. Not reproduced: the hero-only
 * 0x0137ad93 and the stat machine's 0x00a00fb7. Another model than 0xa91: nothing (scale->branch unchanged). */
void mu_he_set_character_class_world(mu_rp_character *c, const mu_he_item equipment[MU_HE_EQUIPMENT],
                                     const mu_he_scale_in *in, mu_he_scale *scale);

/* RenderCharacter's body-part loop 0x0136a374..0x0136a8ef: slots 5 down to 0, a slot of type -1 is skipped, and every
 * other slot (the head slot 0 like the rest) reaches RenderPartObject 0x017e63f4 with the slot record. */
typedef struct mu_he_part_draw {
    int32_t slot;     /* 5..0 */
    int32_t type;     /* the model the loop asks GetModel 0x00eaa8cf for (mu_he_part_draw_type) */
} mu_he_part_draw;
/* The model type the loop draws for a slot's type (0x0136a3cc..0x0136a57b): class nibble 5 takes 0x36ce + index +
 * 2 * group for groups 7..11, index 10 or 11; class nibble 6 takes 0x36d4 + j + 4 * g for groups 7..11 and index
 * {5, 6, 8, 9}[j] (g = group, 10 for group 11; 0x00d2ae8c); class nibble 4's helm slot (k 1) takes 0x38f6 + d for
 * the helms 0x18e6 + d, d 0, 5, 6, 8 or 9; every other type is drawn as it is. */
int32_t mu_he_part_draw_type(uint8_t class_byte, int32_t slot, int16_t slot_type);
/* The loop's RenderPartObject calls in order; returns their number (0..6). */
int32_t mu_he_part_draws(const mu_rp_character *c, mu_he_part_draw out[6]);
#endif
