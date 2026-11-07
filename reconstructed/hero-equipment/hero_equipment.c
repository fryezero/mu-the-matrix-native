/* HERO-ITEMS-001: SetCharacterClass 0x01394870 (see hero_equipment.h). */
#include "hero_equipment.h"

uint8_t mu_he_item_flag(const mu_he_item *item, int32_t mode)
{
    if (item->type < 0 || item->type > 0x2c00)   /* 0x00cd09a0..0x00cd09b0 */
        return 0;
    switch (mode) {
    case 0: return (item->ancient & 0x33) != 0;
    case 1: return item->flag_98 == 1;
    case 2: return item->flag_92 == 1;
    default: return 0;
    }
}

int16_t mu_he_head_type(int16_t helm_type, uint8_t class_byte)
{
    switch (helm_type) {   /* the compare tree 0x01394fa3..0x01395075 */
    case 0x18e6: case 0x18e8: case 0x18f0: case 0x18f1: case 0x18f2: case 0x18f3: case 0x1925: case 0x1927:
    case 0x192a: case 0x192c: case 0x193d: case 0x193e: case 0x193f: case 0x19a0: case 0x19a1: case 0x1a35:
    case 0x1a5f:
        return (int16_t)(MU_HE_PART_BASE + mu_rp_class_skin(class_byte));
    default:
        return -1;
    }
}

int32_t mu_he_equipment_of_slot(int32_t k)
{
    if (k >= MU_RP_SLOT_HELM && k <= MU_RP_SLOT_BOOTS)
        return MU_HE_HELM + (k - MU_RP_SLOT_HELM);
    switch (k) {
    case MU_RP_SLOT_WEAPON0: return MU_HE_RIGHT;
    case MU_RP_SLOT_WEAPON1: return MU_HE_LEFT;
    case MU_RP_SLOT_WING: return MU_HE_WING;
    case MU_RP_SLOT_HELPER: return MU_HE_HELPER;
    default: return -1;
    }
}

static int16_t item_type(const mu_he_item *item)
{
    return (int16_t)(item->type == -1 ? -1 : item->type + MU_HE_MODEL_BASE);   /* cmp [+0x10], -1 / add 0xae6 */
}

static uint8_t item_level(const mu_he_item *item)
{
    return (uint8_t)((item->level >> 3) & 0xf);   /* sar 3, and 0xf */
}

void mu_he_set_character_class(mu_rp_character *c, const mu_he_item e[MU_HE_EQUIPMENT])
{
    if (c->model != MU_RP_PLAYER_MODEL)   /* 0x01394879 */
        return;
    c->slots[MU_RP_SLOT_WEAPON0].type = item_type(&e[MU_HE_RIGHT]);
    c->slots[MU_RP_SLOT_WEAPON1].type = item_type(&e[MU_HE_LEFT]);
    c->slots[MU_RP_SLOT_WING].type = item_type(&e[MU_HE_WING]);
    c->slots[MU_RP_SLOT_HELPER].type = item_type(&e[MU_HE_HELPER]);
    for (int h = 0; h < 2; ++h) {
        mu_rp_slot *s = &c->slots[MU_RP_SLOT_WEAPON0 + h];
        s->level = item_level(&e[h]);
        s->option = mu_he_item_flag(&e[h], 1);
        s->ext = e[h].ancient;
    }
    c->slots[MU_RP_SLOT_WING].level = item_level(&e[MU_HE_WING]);
    c->slots[MU_RP_SLOT_HELPER].level = item_level(&e[MU_HE_HELPER]);
    const uint8_t skin = mu_rp_class_skin(c->class_byte);
    for (int k = MU_RP_SLOT_HELM; k <= MU_RP_SLOT_BOOTS; ++k) {
        const mu_he_item *item = &e[MU_HE_HELM + (k - MU_RP_SLOT_HELM)];
        mu_rp_slot *s = &c->slots[k];
        s->type = item->type == -1 ? (int16_t)(MU_HE_PART_BASE + MU_HE_PART_STRIDE * (k - MU_RP_SLOT_HELM) + skin)
                                   : item_type(item);
        s->level = item_level(item);
        s->option = mu_he_item_flag(item, 1);
        s->ext = item->ancient;
    }
    if (!c->byte_0e)   /* 0x01394f6f: the head */
        c->slots[MU_RP_SLOT_HEAD].type = mu_he_head_type(c->slots[MU_RP_SLOT_HELM].type, c->class_byte);
}
