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
#endif
