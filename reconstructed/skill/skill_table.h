#ifndef MU_SKILL_TABLE_H
#define MU_SKILL_TABLE_H

/* The client's skill table loader (NATIVE-SKILL-001, docs/research/client-skills.md).
 *
 * Pinned inputs as in reconstructed/data: restored text capture 09
 * (2bd5f2e9...3724, VA 0x00401000), second image section run 10.
 *
 * Skill(Kor) is a Lang.mpr script table (object 0x06fbb138 = table manager
 * 0x06fbaa60 + 0x6d8, loaded by 0x0115eceb through the generic table loader
 * 0x010d68e1, which is behind the protection boundary: its body jumps into
 * the packed section).  The loader hands each tokenised row to the table's
 * virtual row parser, slot 2 of the vtable 0x01ac1d7c:
 *
 *   bool __thiscall SkillTable::ParseRow(int line, std::vector<std::string> *row)   0x01170ca5
 *
 * which needs at least 52 columns (0x34), converts the columns in a fixed
 * order with boost::lexical_cast (int: 0x00cd80e9 -> try-parse 0x00cd8314;
 * bool: 0x010c2add -> 0x010c2ce2), strips the name's enclosing quotes
 * (0x010bb278), builds the 0xd0-byte record on its stack and inserts
 * pair(index, record) into the map at this+0x108 (std::map::insert: an
 * existing index keeps its first record).  A failed conversion throws; the
 * handler logs the line (0x010d7e03) and the row is dropped (returns 0).
 *
 * The row reads 61 columns although the size check only asks for 52: a row
 * with 52..60 columns makes the client read past the vector (undefined);
 * mu_skill_parse_row rejects it (MU_SKILL_ROW_SHORT).
 *
 * Field names: "verified" offsets come from consumers that ran in Unicorn
 * (scripts/validate_skill.py, scripts/validate_lang.py, scripts/validate_gfx3.py);
 * the requirement names are the client's own tooltip labels (GlobalText
 * 0x18c1..0x18c5 "Strength %d", "Agility %d", "Health %d", "Energy %d",
 * "Command %d", builder 0x0117da56) and the stat check 0x0109228f; fields
 * marked "data" are readings of the values. */

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MU_SKILL_COLUMNS 61          /* columns the parser reads */
#define MU_SKILL_MIN_COLUMNS 52      /* the parser's size check (0x34) */
#define MU_SKILL_NAME 128

enum {
    MU_SKILL_ROW_OK = 1,
    MU_SKILL_ROW_FEW = 0,            /* fewer than 52 columns: the parser returns 0 */
    MU_SKILL_ROW_BAD = -1,           /* a lexical_cast failed: logged and dropped (returns 0) */
    MU_SKILL_ROW_SHORT = -2          /* 52..60 columns: the client reads past the vector */
};

typedef struct mu_skill_record {
    uint8_t skip;                    /* +0x00 cleared by the parser; SkillInfo 0x00c5ebaa skips set records */
    int32_t index;                   /* +0x04 column 0 (the map key) */
    char name[MU_SKILL_NAME];        /* +0x08 std::string, column 1 without its enclosing quotes (else "null") */
    int32_t level;                   /* +0x20 column 2 (data: required level) */
    int32_t damage;                  /* +0x24 column 3 (getter 0x016969c2) */
    int32_t mana;                    /* +0x28 column 4 (GetSkillInformation 0x01696458) */
    int32_t ag;                      /* +0x2c column 5 (GetSkillInformation) */
    int32_t distance;                /* +0x34 column 6 (GetSkillDistance 0x01696630) */
    int32_t delay;                   /* +0x38 column 7 (StartSkillDelay 0x01696aca, ms) */
    int32_t req_energy;              /* +0x44 column 8 */
    int32_t req_strength;            /* +0x3c column 9 */
    int32_t req_dexterity;           /* +0x40 column 10 (label "Agility") */
    int32_t req_command;             /* +0x48 column 11 */
    int32_t req_vitality;            /* +0x4c column 12 (label "Health") */
    int32_t mastery;                 /* +0x50 column 13 MasteryType: element 0 none, 1..5 (tooltip 0x12a2..0x12a6) */
    int32_t x54;                     /* +0x54 column 14 */
    int32_t use_type;                /* +0x58 column 15 SkillUseType (icon sheet, GetSkillInformation) */
    int32_t brand;                   /* +0x5c column 16 (GetSkillInformation's mana branch) */
    int32_t x60;                     /* +0x60 column 17 */
    int32_t rank[3];                 /* +0x64 std::map<int,int>: keys 0x80, 0x40, 0x20 <- columns 18, 19, 20 */
    int32_t classes[16];             /* +0x6c std::map<int,int>: key i <- column 21 + i (class index i) */
    int32_t x74, x78;                /* +0x74, +0x78 columns 37, 38 */
    int32_t master_factor;           /* +0x7c column 39 (GetSkillInformation reads its low byte) */
    int32_t x80, x84, x88;           /* columns 40..42 */
    int32_t icon;                    /* +0x8c column 43 Magic_Icon */
    int32_t type;                    /* +0x90 column 44 (7: the mounted-skill check of onSelectSkill) */
    uint8_t x94;                     /* +0x94 column 45, lexical_cast<bool> (0x0109260c: 1 = special-item skill) */
    int32_t x98, x9c, xa0, xa4, xa8, xac;   /* columns 46..51 */
    int32_t xb0;                     /* +0xb0 column 52 (usability check 0x010918c7: 1/2 with the hero's state) */
    int32_t weapon;                  /* +0xb4 column 53 (usability check: the required weapon kind, 1..0x12) */
    int32_t pairs[2][2];             /* +0xb8 std::vector<std::pair<int,int>>: (column 54, 55), (56, 57); */
    int32_t npairs;                  /*        a pair is pushed when its first column is not -1 */
    int32_t imprint;                 /* +0xc4 column 58 (tooltip: elemental imprint bonus %, GT 0x12b6) */
    uint8_t xc8;                     /* +0xc8 column 59 != 0 */
    int32_t damage_type;             /* +0xcc column 60 (bar: damageType / SelectSkill_damageType) */
} mu_skill_record;

/* boost::lexical_cast<int>(std::string) as the client's try-parse 0x00cd8314 runs it with the classic
 * locale: an optional '+'/'-', then decimal digits only (no spaces), within int's range.  Returns 1 and
 * the value, or 0. */
int mu_skill_lexical_int(const char *text, size_t length, int32_t *out);
/* boost::lexical_cast<bool> (0x010c2ce2): "...0"/"...1" with an optional '+' (or '-' before a final
 * '0') and leading zeros. */
int mu_skill_lexical_bool(const char *text, size_t length, uint8_t *out);
/* 0x010bb278: the text between a leading '"' and the last '"' (its length); -1 when the column is not
 * quoted that way: the record keeps its constructor's name "null". */
long mu_skill_unquote(const char *text, size_t length, char *out, size_t cap);

/* SkillTable::ParseRow 0x01170ca5 for one row (cols[i] of lengths lens[i], or NUL-terminated when lens
 * is NULL); returns MU_SKILL_ROW_*. */
int mu_skill_parse_row(const char *const *cols, const size_t *lens, size_t ncols, mu_skill_record *out);

/* The table: records in key order (std::map<int, record> at +0x108); add keeps the first record of an
 * index as std::map::insert does.  get is the lookup 0x00961620 (NULL for an absent key: the client
 * returns the default record at this+0x38 then). */
typedef struct mu_skill_table {
    mu_skill_record *records;
    size_t count, capacity;
} mu_skill_table;
int mu_skill_table_add(mu_skill_table *table, const mu_skill_record *record);
const mu_skill_record *mu_skill_table_get(const mu_skill_table *table, int32_t index);
void mu_skill_table_free(mu_skill_table *table);

#ifdef __cplusplus
}
#endif

#endif
