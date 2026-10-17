#include "item_attributes.h"

#include <string.h>

const mu_record_field *mu_item_layout(size_t *count) {
    const mu_record_layout *layout = mu_record_layout_find("item.bmd");
    if (count) *count = layout->field_count;
    return layout->fields;
}

static uint32_t le(const uint8_t *p, unsigned width) {
    uint32_t value = 0;
    for (unsigned i = 0; i < width; ++i) value |= (uint32_t)p[i] << (8 * i);
    return value;
}

void mu_item_attributes_read(const uint8_t *r, mu_item_attributes *a) {
    memset(a, 0, sizeof *a);
    a->code = le(r, 4);
    a->section = (uint16_t)le(r + 4, 2);
    a->index = (uint16_t)le(r + 6, 2);
    a->kind_a = r[0x250];
    a->kind_b = r[0x251];
    a->type = r[0x252];
    a->two_handed = r[0x253];
    a->level = (uint16_t)le(r + 0x254, 2);
    a->slot = r[0x256];
    a->skill = (uint16_t)le(r + 0x258, 2);
    a->width = r[0x25a];
    a->height = r[0x25b];
    a->damage_min = (uint16_t)le(r + 0x25c, 2);
    a->damage_max = (uint16_t)le(r + 0x25e, 2);
    a->defense_rate = r[0x260];
    a->defense = (uint16_t)le(r + 0x262, 2);
    a->magic_defense = (uint16_t)le(r + 0x264, 2);
    a->attack_speed = r[0x266];
    a->walk_speed = r[0x267];
    a->durability = r[0x268];
    a->set_defense_tier = (uint16_t)le(r + 0x26a, 2);
    a->magic_durability = r[0x26c];
    a->magic_power = le(r + 0x270, 4);
    a->combat_power = le(r + 0x274, 4);
    a->attack_success_rate = le(r + 0x278, 4);
    a->require_strength = (uint16_t)le(r + 0x27c, 2);
    a->require_dexterity = (uint16_t)le(r + 0x27e, 2);
    a->require_energy = (uint16_t)le(r + 0x280, 2);
    a->require_vitality = (uint16_t)le(r + 0x282, 2);
    a->require_command = (uint16_t)le(r + 0x284, 2);
    a->require_level = (uint16_t)le(r + 0x286, 2);
    a->value = r[0x288];
    a->zen = le(r + 0x28c, 4);
    a->set_attribute = r[0x290];
    memcpy(a->require_class, r + 0x291, MU_ITEM_CLASS_SLOTS);
    memcpy(a->resistance, r + 0x2a1, MU_ITEM_RESISTANCES);
    a->can_drop = r[0x2a8];
    a->can_trade = r[0x2a9];
    a->can_personal_store = r[0x2aa];
    a->can_warehouse = r[0x2ab];
    a->can_sell = r[0x2ac];
    a->high_value = r[0x2ad];
    a->can_repair = r[0x2ae];
    a->max_stack = r[0x2af];
    a->pc_room = r[0x2b0];
    a->evolved_pet = r[0x2b1];
    a->stat_option_melee = (uint16_t)le(r + 0x2b2, 2);
    a->stat_option_ranged = (uint16_t)le(r + 0x2b4, 2);
    a->stat_option_magic = (uint16_t)le(r + 0x2b6, 2);
    a->pentagram_grade = r[0x2b8];
    a->field_2b9 = r[0x2b9];
    a->field_2ba = r[0x2ba];
    a->elemental_attack = (uint16_t)le(r + 0x2bc, 2);
    a->elemental_defense_bonus = (uint16_t)le(r + 0x2be, 2);
    a->elemental_defense = (uint16_t)le(r + 0x2c0, 2);
}

/* The item predicates 0x0095fc2e, 0x00987982, 0x0095fbeb and 0x00cd0995
 * first require 0 <= code <= 0x2c00 (signed). */
static int code_ok(const mu_item_state *s) {
    return s->code >= 0 && s->code <= MU_ITEM_CODE_LIMIT;
}

static int is_kind_b(const mu_item_attributes *a, const mu_item_state *s, unsigned kind) {
    return code_ok(s) && a->kind_b == kind; /* 0x00987982 */
}

static int item_level(const mu_item_state *s) {
    return (int)((uint32_t)s->level & 15u); /* the client reads (object +0x14 >> 3) & 15 */
}

uint8_t mu_item_max_durability(const mu_item_attributes *a, const mu_item_state *s) {
    if (is_kind_b(a, s, 0x2b)) return a->durability; /* copied unchanged */
    int level = item_level(s);
    int d = a->durability;
    static const unsigned staff_kinds[] = {0x0c, 0x0d, 0x0e, 0x4e, 0x54, 0x59, 0x5a, 0x72, 0x73};
    for (size_t i = 0; i < sizeof staff_kinds / sizeof staff_kinds[0]; ++i)
        if (is_kind_b(a, s, staff_kinds[i])) {
            d = a->magic_durability;
            break;
        }
    if (level >= 1 && level <= 4)
        d += level;
    else if (level >= 5 && level <= 9)
        d += level * 2 - 4;
    else if (level >= 10 && level <= 15)
        d += level * 2 - 4 + (level - 9) * (level - 8) / 2;
    /* 0x00cd2326 returns 1 for 0x1a04/0x28f7, 0 for 0x1a05/0x28f8/0x28f9/0x28fa/0x2900, else -1;
     * both 0 and 1 set the maximum to 255. */
    switch (s->code) {
    case 0x1a04: case 0x28f7: case 0x1a05: case 0x28f8: case 0x28f9: case 0x28fa: case 0x2900:
        d = 255;
        break;
    default:
        break;
    }
    int ancient = code_ok(s) && (s->ancient & 0x33) != 0;   /* 0x00cd0995(0) */
    int excellent = code_ok(s) && s->excellent == 1;          /* 0x00cd0995(1) */
    if (ancient || is_kind_b(a, s, 0x79))
        d += 20;
    else if (excellent)
        d += 15;
    if (code_ok(s) && a->type == 4) d = 255;                  /* 0x0095fbeb(4) */
    return (unsigned)d > 255u ? 255 : (uint8_t)d;
}

int mu_item_store_ban(const mu_item_attributes *a, const mu_item_state *s) {
    if (s->period == 1) return 1;
    int level = item_level(s);
    if ((s->code == 0x1a14 && level != 0) || (s->code == 0x1c0b && level == 13)) return 1;
    if (s->code == 0x1c15 && level == 3) return 0;
    return a->can_warehouse == 0;
}

int mu_item_repair_ban(const mu_item_attributes *a, const mu_item_state *s) {
    if (is_kind_b(a, s, 0x2b)) return 1;
    if (s->period == 1 && s->expired == 1) return 1;
    return a->can_repair == 0;
}
