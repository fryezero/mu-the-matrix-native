#ifndef MU_LANG_H
#define MU_LANG_H

#include <stddef.h>
#include <stdint.h>

/* Game text and script tables of Data\Lang.mpr (NATIVE-LANG-001).
 *
 * The package itself stays encrypted (its password sits behind the
 * protection boundary).  mac-play/diagnostics/langread reads the tables
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

#endif
