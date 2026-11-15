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

mu_he_item mu_he_item_of_record(int32_t code, uint8_t level, uint8_t option, uint8_t ext)
{
    mu_he_item item = {.type = code, .level = (int32_t)((level & 0xfu) << 3), .ancient = ext, .flag_92 = 0,
                       .flag_98 = (uint8_t)(option != 0)};
    return item;
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

static void slot_writes(mu_rp_character *c, const mu_he_item e[MU_HE_EQUIPMENT])
{
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
}

void mu_he_set_character_class(mu_rp_character *c, const mu_he_item e[MU_HE_EQUIPMENT])
{
    if (c->model != MU_RP_PLAYER_MODEL)   /* 0x01394879 */
        return;
    slot_writes(c, e);
    if (!c->byte_0e)   /* 0x01394f6f: the head */
        c->slots[MU_RP_SLOT_HEAD].type = mu_he_head_type(c->slots[MU_RP_SLOT_HELM].type, c->class_byte);
}

/* ---- HERO-ITEMS-002 ---- */

uint8_t mu_he_castle_world(int32_t world)
{
    return (world >= 0x12 && world <= 0x17) || world == 0x35 || world == 0x61;   /* 0x009dacbb..0x009dacd1 */
}

void mu_he_castle_weapons(uint8_t class_byte, int16_t type[2])
{
    type[0] = type[1] = -1;
    switch (class_byte & 0xf) {   /* 0x009dae93..0x009daf79 */
    case 1: case 3: case 4: case 6: case 7: case 9: case 10: case 13: case 15:
        type[0] = type[1] = 0x0af6;
        break;
    case 2:
        type[0] = 0x12f9;
        break;
    default:   /* 0, 5, 8, 11, 12, 14 */
        type[0] = 0x14eb;
        break;
    }
}

int mu_he_castle_override(mu_rp_character *c, int32_t world)
{
    if (!mu_he_castle_world(world))   /* 0x009dadf7 */
        return 0;
    /* 0x009dad3f */
    c->slots[MU_RP_SLOT_WING].type = -1;
    c->slots[MU_RP_SLOT_WING].level = 0;
    c->slots[MU_RP_SLOT_HELPER].type = -1;
    c->slots[MU_RP_SLOT_HELPER].level = 0;
    for (int h = 0; h < 2; ++h) {
        mu_rp_slot *s = &c->slots[MU_RP_SLOT_WEAPON0 + h];
        s->type = -1;
        s->level = 0;
        s->option = 0;
    }
    c->byte_16 = 0;
    int16_t type[2];
    mu_he_castle_weapons(c->class_byte, type);
    for (int h = 0; h < 2; ++h)
        if (type[h] != -1) {   /* a written hand: type and level 0 */
            c->slots[MU_RP_SLOT_WEAPON0 + h].type = type[h];
            c->slots[MU_RP_SLOT_WEAPON0 + h].level = 0;
        }
    return 1;
}

float mu_he_class_scale(uint8_t class_byte, int castle)
{
    /* jump table 0x01395433; binary32 0x01a7edac 0.9, 0x01a802b4 0.88, 0x01a7fb08 0.95, 0x01a800dc 0.92,
     * 0x01aa53b0 1.03, 0x01a82fe0 0.99, 0x01a7df18 0.8, 0x01a889d0 1.1 */
    static const float scale[16] = {0.9f, 0.9f, 0.88f, 0.95f, 0.92f, 0.9f, 1.03f, 0.9f,
                                    0.9f, 0.9f, 0.9f,  0.99f, 0.9f,  0.9f, 0.8f,  1.1f};
    const uint8_t nibble = class_byte & 0xf;
    if (castle)   /* jump table 0x013953f3 */
        return nibble == 2 ? 0.88f : 0.9f;
    return scale[nibble];
}

void mu_he_character_scale(mu_rp_character *c, const mu_he_scale_in *in, mu_he_scale *scale)
{
    scale->buff_queries = 0;
    if (c->byte_0e) {   /* 0x01394f78 */
        scale->branch = MU_HE_SCALE_SKIPPED;
        return;
    }
    c->slots[MU_RP_SLOT_HEAD].type = mu_he_head_type(c->slots[MU_RP_SLOT_HELM].type, c->class_byte);
    const uint8_t nibble = c->class_byte & 0xf;
    if (mu_he_castle_world(in->world)) {   /* 0x013950ba */
        for (int k = 0; k < 6; ++k)
            scale->part[k] = 0.0f;
        scale->object = mu_he_class_scale(c->class_byte, 1);
        scale->branch = MU_HE_SCALE_CASTLE;
        return;
    }
    for (int k = 0; k < 6; ++k)   /* 0x01395165 */
        scale->part[k] = nibble == 11 && k == 1 ? 0.95f : 0.0f;
    if (in->scene == 5) {   /* 0x013951ef */
        scale->object = 1.7f;
        scale->branch = MU_HE_SCALE_SCENE5;
        return;
    }
    scale->object = mu_he_class_scale(c->class_byte, 0);
    scale->branch = MU_HE_SCALE_CLASS;
    uint8_t buff = in->buff_1a8;   /* 0x013953aa */
    scale->buff_queries = 1;
    if (!buff) {
        buff = in->buff_1a9;
        scale->buff_queries = 2;
    }
    if (buff) {
        scale->object = 1.1f;
        scale->branch = MU_HE_SCALE_BUFF;
    }
}

void mu_he_set_character_class_world(mu_rp_character *c, const mu_he_item e[MU_HE_EQUIPMENT], const mu_he_scale_in *in,
                                     mu_he_scale *scale)
{
    if (c->model == MU_RP_PLAYER_MODEL) {   /* 0x01394879: only a Player model */
        slot_writes(c, e);
        mu_he_castle_override(c, in->world);   /* 0x01394f3a */
        mu_he_character_scale(c, in, scale);   /* 0x01394f43 */
    }
}

int32_t mu_he_part_draw_type(uint8_t class_byte, int32_t slot, int16_t slot_type)
{
    const int32_t code = (int32_t)slot_type - MU_HE_MODEL_BASE;
    const int32_t group = code / 512, index = code % 512;   /* cdq / and 0x1ff / sar 9: truncating division */
    const uint8_t nibble = class_byte & 0xf;
    if (nibble == 4 && slot == MU_RP_SLOT_HELM) {   /* 0x0136a4d1..0x0136a57b: the helm slot only */
        const int32_t d = (int32_t)slot_type - 0x18e6;
        if (d == 0 || d == 5 || d == 6 || d == 8 || d == 9)
            return 0x38f6 + d;
    }
    if (group < 7 || group > 11)
        return slot_type;
    if (nibble == 5 && (index == 10 || index == 11))   /* 0x0136a41b..0x0136a452 */
        return 0x36ce + index + 2 * group;
    if (nibble == 6) {   /* 0x00d2ae8c */
        static const int32_t list[4] = {5, 6, 8, 9};
        for (int32_t j = 0; j < 4; ++j)
            if (index == list[j])
                return 0x36d4 + j + 4 * (group == 11 ? group - 1 : group);
    }
    return slot_type;
}

int32_t mu_he_part_draws(const mu_rp_character *c, mu_he_part_draw out[6])
{
    int32_t n = 0;
    for (int32_t k = MU_RP_SLOT_BOOTS; k >= MU_RP_SLOT_HEAD; --k) {   /* 0x0136a374: 5 down to 0 */
        if (c->slots[k].type == -1)   /* 0x0136a3b7 */
            continue;
        out[n].slot = k;
        out[n].type = mu_he_part_draw_type(c->class_byte, k, c->slots[k].type);
        ++n;
    }
    return n;
}
