#ifndef MU_LANG_H
#define MU_LANG_H

#include <stddef.h>
#include <stdint.h>

/* Game text and script tables of Data\Lang.mpr (NATIVE-LANG-001).
 *
 * The package itself stays encrypted (its password sits behind the
 * protection boundary).  live-readers/langread reads the tables
 * main.exe built from it out of the running client, read-only, and
 * scripts/live_lang_to_plain.py writes them as local plaintext files.  This
 * module loads those files when present; every consumer keeps its
 * placeholder when a table is absent.  The files are the server's game text
 * and are never committed (docs/research/client-lang-tables.md).
 *
 * Directory (mu_lang_load): globaltext.txt, skills.tsv, gates.tsv,
 * moves.tsv, npcnames.tsv, dialog.tsv, enchant.tsv (each optional).
 * mu_lang_load_default() reads the directory named by MU_LANG_DIR.
 *
 * Strings are the client's bytes (ANSI; a few CP949), NUL-terminated. */

typedef struct mu_lang mu_lang;

typedef struct mu_lang_skill {        /* Skill(Kor) record (0xd0 bytes), lookup 0x00961620 */
    int32_t index;                    /* +0x04 (the map key) */
    const char *name;                 /* +0x08 std::string */
    int32_t level, damage, mana, ag;  /* +0x20, +0x24 (0x016969c2), +0x28 and +0x2c (0x01696458) */
    int32_t distance, delay;          /* +0x34 (GetSkillDistance 0x01696630), +0x38 (SkillInfo Delay) */
    int32_t req[5];                   /* +0x3c..+0x4c (compared with character values by 0x010922..) */
    int32_t mastery, use_type, brand; /* +0x50 MasteryType, +0x58 SkillUseType, +0x5c */
    uint8_t master_bonus;             /* +0x7c byte (GetSkillInformation's master-skill factor) */
    uint8_t skip;                     /* +0x00 byte (SkillInfo skips the record when set) */
    int32_t icon, type;               /* +0x8c Magic_Icon, +0x90 */
} mu_lang_skill;

typedef struct mu_lang_gate {         /* Gate record (0x34 bytes), lookup 0x0110cbaf */
    int32_t index, flag, world;       /* world +0x0c (read by the move window 0x00c6922a) */
    int32_t x1, y1, x2, y2, target, dir, min_level, max_level;
} mu_lang_gate;

typedef struct mu_lang_move {         /* movereq(kor) record (0x54 bytes), lookup 0x0113c3f5 */
    int32_t index;
    const char *name, *server_name;   /* +0x04, +0x1c std::string */
    int32_t id, zen, min_level, max_level, gate, x44, x48, x4c;   /* +0x00, +0x34.., gate +0x40 (0x00c6922a) */
} mu_lang_move;

typedef struct mu_lang_npc {          /* Npcname(kor) record (0x28 bytes), getters 0x011427c7.. */
    int32_t index;
    const char *name;                 /* +0x04 std::string (0x011427c7) */
    int32_t x1c, x20;                 /* 0x011427e0, 0x011427f9 */
    uint8_t x24;                      /* 0x01142812 */
} mu_lang_npc;

/* Loading.  NULL when the directory holds none of the files. */
mu_lang *mu_lang_load(const char *dir);
mu_lang *mu_lang_load_default(void);
void mu_lang_free(mu_lang *lang);
/* The process-wide tables from MU_LANG_DIR, loaded on first use (NULL when
 * the variable is unset or the directory holds no table).  Consumers that
 * have no configuration path of their own use it. */
const mu_lang *mu_lang_shared(void);

typedef struct mu_lang_counts {
    size_t text, skills, gates, moves, npcs, dialog, enchant_codes, enchant_entries;
    size_t buffs, charinfo, skillreq, soulconv, questtext;   /* NATIVE-LANG-002 */
    int enchant_default;              /* the default colour line was present */
} mu_lang_counts;
void mu_lang_get_counts(const mu_lang *lang, mu_lang_counts *out);

/* GlobalText[index] (0x0095f027); NULL when the table or the entry is absent. */
const char *mu_lang_text(const mu_lang *lang, int32_t index);
/* GlobalText[index] or the fallback when absent (lang may be NULL). */
const char *mu_lang_text_or(const mu_lang *lang, int32_t index, const char *fallback);

const mu_lang_skill *mu_lang_skill_get(const mu_lang *lang, int32_t index);
size_t mu_lang_skill_count(const mu_lang *lang);
const mu_lang_skill *mu_lang_skill_at(const mu_lang *lang, size_t i);
/* GetSkillInformation 0x01696458: mana and AG with the master-skill factor
 * (master_level: the value 0x00bb1d9d returns for skills 300..929) and the
 * base distance (GetSkillDistance 0x01696630 without the character's
 * bonuses).  Returns the name, or NULL when the skill is absent. */
const char *mu_lang_skill_info(const mu_lang *lang, int32_t skill, int32_t master_level, int32_t *mana,
                               int32_t *distance, int32_t *ag);

const mu_lang_gate *mu_lang_gate_get(const mu_lang *lang, int32_t index);
const mu_lang_move *mu_lang_move_get(const mu_lang *lang, int32_t index);
size_t mu_lang_move_count(const mu_lang *lang);
const mu_lang_move *mu_lang_move_at(const mu_lang *lang, size_t i);
const mu_lang_npc *mu_lang_npc_get(const mu_lang *lang, int32_t index);
const char *mu_lang_npc_name(const mu_lang *lang, int32_t index);
const char *mu_lang_dialog(const mu_lang *lang, int32_t index);

/* Map name of a world (the map-name function 0x016baaa6 with the current
 * world equal to the argument and no event running): the GlobalText index
 * from mu_lang_maps.h, or 30 + world past the table.  -1 for worlds whose
 * name comes from runtime state. */
int32_t mu_lang_map_text_index(int32_t world);
/* The name, or NULL (no table, runtime-named world, or absent entry). */
const char *mu_lang_map_name(const mu_lang *lang, int32_t world);

/* EnchantEffect (table 0x06fbb754, key item code = model index - 0xae6).
 * Both write the colour and return 1 when the table is loaded (the table's
 * default colour when nothing matches), 0 otherwise (out untouched).
 *   first: 0x010ffd7a, the first entry of the code;
 *   mesh:  0x010ffddb, the first entry whose mesh is the argument or -1. */
int mu_lang_enchant_first(const mu_lang *lang, int32_t code, float out[3]);
int mu_lang_enchant_mesh(const mu_lang *lang, int32_t code, int32_t mesh, float out[3]);
/* Number of entries of a code (0x010ffd25's vector size; 0 when absent). */
size_t mu_lang_enchant_entries(const mu_lang *lang, int32_t code);

/* Copies src into dst for renderers that need plain ASCII (JSON, the
 * glyph atlas): printable ASCII is kept, other bytes become '?'.  Returns dst. */
char *mu_lang_ascii(char *dst, size_t cap, const char *src);


/* ---- NATIVE-FIDELITY-001 tables (pentagram.tsv, invenanim.tsv, legendary.tsv, cashsets.tsv) ---- */

/* PentagramOption 0x011447ac: record +0x24 of the code, or the default record's; 0 without the table. */
int mu_lang_pentagram_tier(const mu_lang *lang, int32_t code, int32_t *tier);
/* InvenItemAnimation 0x0111d824: 1 with the record's action (+8) and speed (+0xc), 0 when absent. */
int mu_lang_inven_anim(const mu_lang *lang, int32_t code, uint16_t *action, float *speed);
/* LegendaryItemSetType 0x011288c7: the four codes at record +4 of the set type, or the default record's;
 * 0 without the table. */
int mu_lang_legendary(const mu_lang *lang, int32_t type, int32_t codes[4]);
typedef struct mu_lang_cash_set { const char *name, *name2; } mu_lang_cash_set;
typedef struct mu_lang_cash_item { int32_t group, index, set; } mu_lang_cash_item;
/* CashItemSetOption's set and item vectors (read by 0x009debe4), in vector order. */
size_t mu_lang_cash_sets(const mu_lang *lang, const mu_lang_cash_set **sets);
size_t mu_lang_cash_items(const mu_lang *lang, const mu_lang_cash_item **items);


/* ---- NATIVE-LANG-002 tables (buffs.tsv, charinfo.tsv, skillreq.tsv) ---- */

#define MU_LANG_BUFF_LINES 8
typedef struct mu_lang_buff {         /* BuffEffect record (0x06fbb2a4, map +0x38) */
    int32_t index;                    /* +0x00 (the key) */
    int32_t group;                    /* +0x04: buffs of one group replace each other (0x009584dc); the bufflist's
                                         BuffDetailType is 1 for group 0xf7, 2 for 0xf6 (0x00c5f36e) */
    int32_t item_group, item_index;   /* +0x08, +0x0c: the item that gives the buff (0x010de6d3), 255 = none */
    int32_t type;                     /* +0x28: 1 debuff, 2 cash buff (addBuff isDebuff / isCashBuff) */
    int32_t x2c, x30;                 /* +0x2c (0x00c78d6b skips 0), +0x30 */
    int32_t value_kind;               /* +0x40: 1/2 = the first description line formats the hero's buff value */
    const char *name;                 /* +0x10 std::string */
    const char *lines[MU_LANG_BUFF_LINES];   /* +0x34 std::vector<std::string>: the description */
    int32_t nlines;
} mu_lang_buff;

/* 0x010de66f: the record of a buff, or the default record (index 0, name "null") for buff >= 0x1cb or an
 * absent buff; NULL without the table. */
const mu_lang_buff *mu_lang_buff_get(const mu_lang *lang, int32_t buff);
/* 0x010de6d3: the first record (key order) whose item is code (group * 512 + index), else the default record. */
const mu_lang_buff *mu_lang_buff_by_item(const mu_lang *lang, int32_t code);
size_t mu_lang_buff_count(const mu_lang *lang);
const mu_lang_buff *mu_lang_buff_at(const mu_lang *lang, size_t i);

/* The hero-side inputs of the buff InfoPopup lines (0x01298a54). */
typedef struct mu_lang_buff_values {
    int32_t hero_value;               /* 0x01295d1c(buff) on the hero's buff list (0: none) */
    int value2_hidden;                /* value_kind 2: the predicate 0x010702e1 (1: name only) */
    int32_t value2_kind;              /* value_kind 2: 0x010702bd's +8 (0 int, 1 float, other: no value) */
    int32_t value2_int;               /* its +0 */
    float value2_float;               /* its +4 */
} mu_lang_buff_values;

/* The buff InfoPopup lines of 0x01298a54: the name, a "\n" line, then
 *   value_kind 1 and hero_value != 0: one line, the description lines joined (0x01299f67) used as the printf
 *     format of hero_value;
 *   value_kind 2: nothing more when value2_hidden; else the joined format with value2_int (kind 0) or
 *     (double)value2_float (kind 1), or an empty line for other kinds;
 *   otherwise the description lines.
 * The client's sprintf runs on the table's format; here only one conversion (%d %i %u %x %f %g with flags,
 * width and precision; %% kept) is substituted and anything else is printed as it is.  vals may be NULL
 * (no hero values).  Writes up to max lines; returns the count, 0 without the table. */
int mu_lang_buff_tooltip(const mu_lang *lang, int32_t buff, const mu_lang_buff_values *vals, char (*out)[256],
                         int max);

/* The bufflist's addBuff (handler 0x00c5f278): 0 when the buff is not listed (buff <= 0 or >= 0x1cb, the hidden
 * buffs of 0x00c5f53f: 0x53..0x55, 0x78, 0x19b..0x19f, 0x1be, or no table); else 1 with the object it sends:
 * BuffType = buff, isDebuff = (type == 1), isCashBuff = (type == 2), and for non-debuffs BuffDetailType
 * (group 0xf7 -> 1, 0xf6 -> 2, else 0). */
typedef struct mu_lang_addbuff {
    int32_t buff;
    int is_debuff, is_cash, has_detail;
    int32_t detail;
} mu_lang_addbuff;
int mu_lang_buff_addbuff(const mu_lang *lang, int32_t buff, mu_lang_addbuff *out);

typedef struct mu_lang_charinfo {     /* CharacterInfoSetup record (0x06fbad18, map +0x38), 0xa4 bytes */
    int32_t id;                       /* +0x00 (the key; SetName's second argument) */
    int32_t color;                    /* +0x04 label colour (line builder 0x00ab4dc0) */
    int32_t group;                    /* +0x20 */
    int32_t type;                     /* +0x30 SetName type (1 base info, 2 stats, 3.. other tabs) */
    int32_t sort;                     /* +0x34 SetName sort (types 2, 3, 5 are sorted by it, 0x00b46e30) */
    int32_t value_color;              /* +0x38 value colour */
    int32_t button;                   /* +0xa0 SetName's last argument ("+" button) */
    uint8_t classes[16];              /* +0x24 vector<int>: shown for class index 0x0095f5cc(class) when nonzero */
    int32_t nclasses;
    const char *label, *prefix, *suffix;   /* +0x08, +0x3c, +0x54 std::string */
} mu_lang_charinfo;

/* 0x010e5203: the row or the default record (id 0, label "null"); NULL without the table. */
const mu_lang_charinfo *mu_lang_charinfo_get(const mu_lang *lang, int32_t id);
size_t mu_lang_charinfo_count(const mu_lang *lang);
const mu_lang_charinfo *mu_lang_charinfo_at(const mu_lang *lang, size_t i);   /* key order */
/* The character window's row order of 0x00b3dedc for a class index: rows whose class flag is set, types other
 * than 2/3/5 first in key order (SetName at once), then the rows of types 2/3/5 collected in key order and
 * ordered by sort with MSVC's std::sort (0x00b48089, comparator 0x00b46e30; not stable).  Writes up to max row
 * pointers; returns the count. */
int mu_lang_charinfo_rows(const mu_lang *lang, int32_t class_index, const mu_lang_charinfo **out, int max);

typedef struct mu_lang_skillreq {     /* SkillRequire record (0x06fbb248, map +0x54) */
    int32_t key, x00, skill, item_group, item_index, x10, x14, x18;
} mu_lang_skillreq;
/* 0x00abf829(group, index): the record of a skill scroll, or NULL. */
const mu_lang_skillreq *mu_lang_skillreq_item(const mu_lang *lang, int32_t group, int32_t index);

/* MUQuestString(kor) (questtext.txt): the quest text of an index, or NULL. */
const char *mu_lang_quest_text(const mu_lang *lang, int32_t index);

/* MonsterSoulConversion 0x01135146: 1 when the item code is in the map at +0x44 (soulconv.tsv), else 0. */
int mu_lang_soul_conversion(const mu_lang *lang, int32_t code);

#endif
