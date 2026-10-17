#include "table_layouts.h"

#include <ctype.h>
#include <string.h>

/* Record layouts (NATIVE-DATA-002). Evidence per field:
 *   C = consumer traced (client code that reads the field)
 *   L = layout only (constructor / comparator / loader widths)
 *   D = decoded installed contents only
 * Addresses and the reasoning are in docs/research/client-item-attributes.md.
 */
#define F(off, type, ev, count, stride, flags, name) {off, MU_FIELD_##type, MU_EVIDENCE_##ev, count, stride, flags, name}
#define S(off, type, ev, name) F(off, type, ev, 1, 0, 0, name)
#define T(off, len, ev, name) F(off, TEXT, ev, len, 0, 0, name)
#define C MU_FIELD_CTOR
#define K MU_FIELD_COMPARED
#define I(off, type, flags, name) F(off, type, CONSUMER, 1, 0, flags, name)

/* Item.bmd, 708 bytes: constructor 0x01184277, comparator 0x011844d9. */
static const mu_record_field ITEM[] = {
    I(0x000, U32, C, "code"), I(0x004, U16, C, "section"), I(0x006, U16, C, "index"),
    F(0x008, TEXT, CONSUMER, 260, 0, C|K, "folder"), F(0x10c, TEXT, CONSUMER, 260, 0, C|K, "file"),
    F(0x210, TEXT, CONSUMER, 64, 0, C|K, "name"),
    I(0x250, U8, C|K, "kind_a"), I(0x251, U8, C|K, "kind_b"), I(0x252, U8, K, "type"),
    I(0x253, U8, C|K, "two_handed"), I(0x254, U16, C|K, "level"), I(0x256, U8, C|K, "slot"),
    I(0x258, U16, C|K, "skill"), I(0x25a, U8, C|K, "width"), I(0x25b, U8, C|K, "height"),
    I(0x25c, U16, C|K, "damage_min"), I(0x25e, U16, C|K, "damage_max"), I(0x260, U8, C|K, "defense_rate"),
    I(0x262, U16, C|K, "defense"), I(0x264, U16, C|K, "magic_defense"), I(0x266, U8, C|K, "attack_speed"),
    I(0x267, U8, C|K, "walk_speed"), I(0x268, U8, C|K, "durability"), I(0x26a, U16, C|K, "set_defense_tier"),
    I(0x26c, U8, C|K, "magic_durability"), I(0x270, U32, C|K, "magic_power"), I(0x274, U32, C|K, "combat_power"),
    I(0x278, U32, C|K, "attack_success_rate"), I(0x27c, U16, C|K, "require_strength"),
    I(0x27e, U16, C|K, "require_dexterity"), I(0x280, U16, C|K, "require_energy"),
    I(0x282, U16, C|K, "require_vitality"), I(0x284, U16, C|K, "require_command"),
    I(0x286, U16, C|K, "require_level"), I(0x288, U8, C|K, "value"), I(0x28c, U32, C|K, "zen"),
    I(0x290, U8, C|K, "set_attribute"),
    F(0x291, U8, CONSUMER, 16, 0, K, "require_class"), F(0x2a1, U8, LAYOUT, 7, 0, K, "resistance"),
    I(0x2a8, U8, 0, "can_drop"), I(0x2a9, U8, C|K, "can_trade"), I(0x2aa, U8, K, "can_personal_store"),
    I(0x2ab, U8, C|K, "can_warehouse"), I(0x2ac, U8, C|K, "can_sell"), I(0x2ad, U8, C|K, "high_value"),
    I(0x2ae, U8, C|K, "can_repair"), I(0x2af, U8, C|K, "max_stack"), I(0x2b0, U8, 0, "pc_room"),
    I(0x2b1, U8, 0, "evolved_pet"), I(0x2b2, U16, C|K, "stat_option_melee"),
    I(0x2b4, U16, C|K, "stat_option_ranged"), I(0x2b6, U16, C|K, "stat_option_magic"),
    I(0x2b8, U8, C|K, "pentagram_grade"), F(0x2b9, U8, LAYOUT, 1, 0, C|K, "field_2b9"),
    F(0x2ba, U8, LAYOUT, 1, 0, C|K, "field_2ba"), I(0x2bc, U16, C|K, "elemental_attack"),
    I(0x2be, U16, C|K, "elemental_defense_bonus"), I(0x2c0, U16, C|K, "elemental_defense"),
};

/* itemtooltip.bmd, 136 bytes: loader 0x00f0ada4 (key section<<9 + index), builder 0x00f0eb44. */
static const mu_record_field ITEM_TOOLTIP[] = {
    S(0x00, U8, CONSUMER, "section"), S(0x02, I16, CONSUMER, "index"), T(0x04, 64, CONSUMER, "name"),
    S(0x44, U8, CONSUMER, "name_color"), S(0x45, U8, CONSUMER, "name_style"), S(0x46, U16, DATA, "field_46"),
    S(0x48, U8, CONSUMER, "show_level"), S(0x4a, I16, CONSUMER, "name_text"),
    F(0x4c, I16, CONSUMER, 15, 4, 0, "line_text"), F(0x4e, U8, CONSUMER, 15, 4, 0, "line_color"),
    F(0x4f, U8, CONSUMER, 15, 4, 0, "line_style"),
};

/* itemtooltiptext.bmd, 260 bytes: type selects the formatter case in 0x00f1098a. */
static const mu_record_field ITEM_TOOLTIP_TEXT[] = {
    S(0x000, U16, CONSUMER, "id"), T(0x002, 256, CONSUMER, "text"), S(0x102, I16, CONSUMER, "type"),
};

/* ItemSetType.bmd, 10 bytes per item code: 0x009de132 reads four set indexes. */
static const mu_record_field ITEM_SET_TYPE[] = {
    F(0x0, U16, CONSUMER, 4, 0, 0, "set_index"), S(0x8, U16, DATA, "field_8"),
};

/* ItemSetOption.bmd, 468 bytes. */
static const mu_record_field ITEM_SET_OPTION[] = {
    T(0x000, 64, DATA, "name"), T(0x040, 64, DATA, "name_2"),
    F(0x080, I32, DATA, 12, 0, 0, "option"), F(0x0b0, I32, DATA, 12, 0, 0, "option_value"),
    F(0x0e0, I32, DATA, 43, 0, 0, "extra"),
};

/* ItemSetOptionText.bmd, 102 bytes: constructor 0x01184b4b, comparator 0x01184b7e. */
static const mu_record_field ITEM_SET_OPTION_TEXT[] = {
    S(0x00, U8, LAYOUT, "option"), T(0x01, 100, DATA, "text"), S(0x65, U8, LAYOUT, "field_65"),
};

/* ExcellentCommonOption / ExcellentWingOption.bmd, 120 bytes: constructor 0x011838bf,
 * key category<<8 | index (loader 0x00cd51fe), consumers 0x00cd061e, 0x00cd0743, 0x00cd0d49. */
static const mu_record_field EXCELLENT_OPTION[] = {
    S(0x00, U8, CONSUMER, "category"), S(0x01, U8, CONSUMER, "index"), T(0x02, 100, CONSUMER, "text"),
    S(0x66, U8, CONSUMER, "value_type"), S(0x68, I32, CONSUMER, "value"), S(0x6c, I32, CONSUMER, "format"),
    F(0x70, U8, LAYOUT, 7, 0, 0, "flags"),
};

/* SocketItem.bmd, 168 bytes in 3 groups of 50 (loader 0x010a9926). */
static const mu_record_field SOCKET_ITEM[] = {
    S(0x00, I32, DATA, "index"), S(0x04, I32, DATA, "element"), S(0x08, I32, DATA, "option"),
    T(0x0c, 64, DATA, "name"), S(0x4c, I32, DATA, "value_type"), F(0x50, I32, DATA, 20, 0, 0, "value"),
    F(0xa0, U8, CONSUMER, 6, 0, 0, "combination"),
};

/* JewelOfHarmonyOption.bmd, one 135000-byte unit of 750 x 180-byte records. */
static const mu_record_field HARMONY_OPTION[] = {
    S(0x00, I32, DATA, "option"), T(0x04, 60, DATA, "name"), S(0x40, I32, DATA, "min_level"),
    F(0x44, I32, DATA, 14, 0, 0, "level_value"), F(0x7c, I32, DATA, 14, 0, 0, "zen"),
};

/* ItemAddOption.bmd, one unit of 0x2c00 x 16 bytes indexed by item code. */
static const mu_record_field ITEM_ADD_OPTION[] = {
    S(0x0, U16, DATA, "option_1"), S(0x2, U16, DATA, "value_1"), S(0x4, U16, DATA, "option_2"),
    S(0x6, U16, DATA, "value_2"), S(0x8, U16, DATA, "item_index"), S(0xa, U16, DATA, "field_a"),
    S(0xc, U32, DATA, "time"),
};

/* InfoTooltip.bmd, 42 bytes; InfoTooltipText.bmd, 258 bytes (constructors 0x011840f1 / 0x011841d8). */
static const mu_record_field INFO_TOOLTIP[] = {
    S(0x00, I16, LAYOUT, "id"), F(0x02, I16, DATA, 10, 4, 0, "line_text"), F(0x04, I16, DATA, 10, 4, 0, "line_color"),
};
static const mu_record_field INFO_TOOLTIP_TEXT[] = {
    S(0x00, I16, LAYOUT, "id"), T(0x02, 256, DATA, "text"),
};

/* StatOption.bmd, 52 bytes; StatOptionText.bmd, 260 bytes. */
static const mu_record_field STAT_OPTION[] = {
    S(0x00, I32, DATA, "field_0"), S(0x04, I32, DATA, "field_4"), S(0x08, I32, DATA, "option"),
    F(0x0c, I32, DATA, 5, 0, 0, "require"), F(0x20, I32, DATA, 5, 0, 0, "value"),
};
static const mu_record_field STAT_OPTION_TEXT[] = {
    S(0x00, I32, DATA, "id"), T(0x04, 256, DATA, "text"),
};

/* helpdata.bmd, 136 bytes; PlayGuide.bmd, 260 bytes. */
static const mu_record_field HELP_DATA[] = {
    S(0x00, I32, DATA, "page"), S(0x04, I16, DATA, "group"), T(0x06, 64, DATA, "key"), T(0x46, 66, DATA, "text"),
};
static const mu_record_field PLAY_GUIDE[] = {
    S(0x00, I32, DATA, "index"), T(0x04, 256, DATA, "url"),
};

/* MonsterSkill.bmd, 48 bytes. */
static const mu_record_field MONSTER_SKILL[] = {
    S(0x00, I32, DATA, "monster"), F(0x04, I32, DATA, 10, 0, 0, "skill"), S(0x2c, I32, DATA, "field_2c"),
};

/* MasterSkillTreeData.bmd, 24 bytes; MasterSkillTooltip.bmd, 808 bytes. */
static const mu_record_field MASTER_SKILL_TREE[] = {
    S(0x00, U16, DATA, "slot"), S(0x02, U16, DATA, "field_2"), S(0x04, U8, DATA, "field_4"), S(0x05, U8, DATA, "field_5"),
    S(0x06, U8, DATA, "max_level"), S(0x07, U8, DATA, "field_7"), S(0x08, U32, DATA, "field_8"),
    S(0x0c, U32, DATA, "field_c"), S(0x10, U32, DATA, "skill"), S(0x14, U32, DATA, "field_14"),
};
static const mu_record_field MASTER_SKILL_TOOLTIP[] = {
    S(0x000, I32, DATA, "skill"), S(0x004, I16, DATA, "field_4"), T(0x006, 64, DATA, "rank_text"),
    T(0x046, 256, DATA, "description"), T(0x146, 256, DATA, "text_3"),
};

/* SkillTooltipText.bmd, 808 bytes: constructor 0x0118501e. */
static const mu_record_field SKILL_TOOLTIP_TEXT[] = {
    S(0x000, U16, LAYOUT, "skill"), T(0x002, 256, DATA, "name"), S(0x104, U32, LAYOUT, "field_104"),
    S(0x108, U32, LAYOUT, "field_108"), T(0x10c, 256, DATA, "description"), S(0x20c, U32, LAYOUT, "field_20c"),
    S(0x210, U32, LAYOUT, "field_210"), T(0x214, 256, DATA, "text_3"), S(0x314, U32, LAYOUT, "field_314"),
    F(0x318, I32, DATA, 4, 0, 0, "field_318"),
};

/* Quest.bmd, 1000 bytes: header only. */
static const mu_record_field QUEST[] = {
    S(0x00, I16, DATA, "condition_count"), S(0x02, I16, DATA, "request_count"), S(0x04, U16, DATA, "npc"),
    T(0x06, 32, DATA, "name"),
};

/* PentagramMixNeedSource.bmd, 188 bytes: constructor 0x01184d7c. */
static const mu_record_field PENTAGRAM_MIX[] = {
    S(0x00, I32, LAYOUT, "field_0"), S(0x04, I32, LAYOUT, "field_4"), S(0x08, I32, LAYOUT, "field_8"),
    F(0x0c, I32, LAYOUT, 5, 0, 0, "field_c"), F(0x20, I32, LAYOUT, 5, 0, 0, "field_20"),
    F(0x34, I32, LAYOUT, 5, 0, 0, "field_34"), F(0x48, I32, LAYOUT, 5, 0, 0, "field_48"),
    S(0x5c, I32, LAYOUT, "field_5c"), S(0x60, I32, LAYOUT, "field_60"), S(0x64, I32, LAYOUT, "field_64"),
    S(0x68, I32, LAYOUT, "field_68"), F(0x6c, I32, LAYOUT, 5, 0, 0, "field_6c"), F(0x80, I32, LAYOUT, 4, 0, 0, "field_80"),
    S(0x90, I32, LAYOUT, "field_90"), S(0x94, I32, LAYOUT, "field_94"), F(0x98, I32, LAYOUT, 3, 0, 0, "field_98"),
    F(0xa4, I32, LAYOUT, 3, 0, 0, "field_a4"), F(0xb0, I32, LAYOUT, 3, 0, 0, "field_b0"),
};

/* RuudShopViewInfo.bmd, 240 bytes: header only. */
static const mu_record_field RUUD_SHOP[] = {
    S(0x00, I32, DATA, "item_code"), T(0x04, 64, DATA, "category"), T(0x44, 64, DATA, "name"),
    S(0x84, I32, DATA, "field_84"), S(0x88, I32, DATA, "price"),
};

/* petdata.bmd, 48 bytes: header only. */
static const mu_record_field PET_DATA[] = {
    S(0x00, I32, DATA, "index"), S(0x04, I32, DATA, "field_4"),
};

/* MuunTooltipInfo.bmd, 32 bytes; MuunMeshInfo.bmd, 300 bytes: partial. */
static const mu_record_field MUUN_TOOLTIP_INFO[] = {
    S(0x00, I32, DATA, "item_code"), S(0x04, I32, DATA, "field_4"), F(0x08, F32, DATA, 6, 0, 0, "view"),
};
static const mu_record_field MUUN_MESH_INFO[] = {
    S(0x00, I32, DATA, "item_code"), S(0x04, I32, DATA, "field_4"), T(0x08, 256, DATA, "texture"),
};

/* MuunExchange.bmd, 16 bytes. */
static const mu_record_field MUUN_EXCHANGE[] = {
    S(0x0, I32, DATA, "item_code"), S(0x4, I32, DATA, "field_4"), S(0x8, I32, DATA, "field_8"), S(0xc, I32, DATA, "field_c"),
};
#undef F
#undef S
#undef T
#undef C
#undef K
#undef I

#define LAYOUT(file, size, fields) {file, size, fields, (uint32_t)(sizeof fields / sizeof fields[0])}
static const mu_record_layout LAYOUTS[] = {
    LAYOUT("item.bmd", 708, ITEM),
    LAYOUT("itemtooltip.bmd", 136, ITEM_TOOLTIP),
    LAYOUT("itemtooltiptext.bmd", 260, ITEM_TOOLTIP_TEXT),
    LAYOUT("itemsettype.bmd", 10, ITEM_SET_TYPE),
    LAYOUT("itemsetoption.bmd", 468, ITEM_SET_OPTION),
    LAYOUT("itemsetoptiontext.bmd", 102, ITEM_SET_OPTION_TEXT),
    LAYOUT("excellentcommonoption.bmd", 120, EXCELLENT_OPTION),
    LAYOUT("excellentwingoption.bmd", 120, EXCELLENT_OPTION),
    LAYOUT("socketitem.bmd", 168, SOCKET_ITEM),
    LAYOUT("jewelofharmonyoption.bmd", 180, HARMONY_OPTION),
    LAYOUT("itemaddoption.bmd", 16, ITEM_ADD_OPTION),
    LAYOUT("infotooltip.bmd", 42, INFO_TOOLTIP),
    LAYOUT("infotooltiptext.bmd", 258, INFO_TOOLTIP_TEXT),
    LAYOUT("statoption.bmd", 52, STAT_OPTION),
    LAYOUT("statoptiontext.bmd", 260, STAT_OPTION_TEXT),
    LAYOUT("helpdata.bmd", 136, HELP_DATA),
    LAYOUT("playguide.bmd", 260, PLAY_GUIDE),
    LAYOUT("monsterskill.bmd", 48, MONSTER_SKILL),
    LAYOUT("masterskilltreedata.bmd", 24, MASTER_SKILL_TREE),
    LAYOUT("masterskilltooltip.bmd", 808, MASTER_SKILL_TOOLTIP),
    LAYOUT("skilltooltiptext.bmd", 808, SKILL_TOOLTIP_TEXT),
    LAYOUT("quest.bmd", 1000, QUEST),
    LAYOUT("pentagrammixneedsource.bmd", 188, PENTAGRAM_MIX),
    LAYOUT("ruudshopviewinfo.bmd", 240, RUUD_SHOP),
    LAYOUT("petdata.bmd", 48, PET_DATA),
    LAYOUT("muuntooltipinfo.bmd", 32, MUUN_TOOLTIP_INFO),
    LAYOUT("muunmeshinfo.bmd", 300, MUUN_MESH_INFO),
    LAYOUT("muunexchange.bmd", 16, MUUN_EXCHANGE),
};
#undef LAYOUT

const mu_record_layout *mu_record_layouts(size_t *count) {
    if (count) *count = sizeof LAYOUTS / sizeof LAYOUTS[0];
    return LAYOUTS;
}

static int same_name(const char *a, const char *b) {
    for (; *a && *b; ++a, ++b)
        if (tolower((unsigned char)*a) != tolower((unsigned char)*b)) return 0;
    return *a == *b;
}

const mu_record_layout *mu_record_layout_find(const char *file) {
    if (!file) return NULL;
    for (size_t i = 0; i < sizeof LAYOUTS / sizeof LAYOUTS[0]; ++i)
        if (same_name(LAYOUTS[i].file, file)) return &LAYOUTS[i];
    return NULL;
}

unsigned mu_field_width(const mu_record_field *f) {
    switch (f->type) {
    case MU_FIELD_U16: case MU_FIELD_I16: return 2;
    case MU_FIELD_U32: case MU_FIELD_I32: case MU_FIELD_F32: return 4;
    default: return 1;
    }
}

unsigned mu_field_span(const mu_record_field *f) {
    unsigned width = mu_field_width(f);
    if (f->type == MU_FIELD_TEXT || f->type == MU_FIELD_BYTES || f->count <= 1) return f->count ? f->count * width : width;
    unsigned stride = f->stride ? f->stride : width;
    return stride * (unsigned)(f->count - 1) + width;
}

int64_t mu_field_integer(const mu_record_field *f, const uint8_t *r, unsigned i) {
    unsigned width = mu_field_width(f), stride = f->stride ? f->stride : width;
    const uint8_t *p = r + f->offset + stride * i;
    uint32_t v = 0;
    for (unsigned k = 0; k < width; ++k) v |= (uint32_t)p[k] << (8 * k);
    switch (f->type) {
    case MU_FIELD_I8: return (int8_t)v;
    case MU_FIELD_I16: return (int16_t)v;
    case MU_FIELD_I32: return (int32_t)v;
    default: return v;
    }
}

float mu_field_float(const mu_record_field *f, const uint8_t *r, unsigned i) {
    uint32_t bits = (uint32_t)mu_field_integer(f, r, i);
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

const char *mu_field_evidence_name(mu_field_evidence evidence) {
    switch (evidence) {
    case MU_EVIDENCE_CONSUMER: return "consumer";
    case MU_EVIDENCE_LAYOUT: return "layout";
    case MU_EVIDENCE_DATA: return "data";
    }
    return "unknown";
}
