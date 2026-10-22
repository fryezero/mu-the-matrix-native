#ifndef MU_SKILL_H
#define MU_SKILL_H

/* The hero's skills in the native client (NATIVE-SKILL-001, docs/research/client-skills.md).
 *
 * The game side of the skill bar, the skill tooltip and the Skill Imprint window (SkillStampFrame) over
 * the reconstructed client routines (reconstructed/skill):
 *   - the skill table: the client's Skill(Kor) records from the Lang tables read out of a running client
 *     (core/mu_lang, MU_LANG_DIR: skills.tsv + skills_ext.tsv), as the row parser 0x01170ca5 builds them;
 *   - SkillTooltipText.bmd (Data/Local, decoded by core/mu_data) for the tooltip builder 0x0117da56;
 *   - the learned list, delay timers, CurrentSkill and the bar's ten hotkeys as the client keeps them
 *     (attributes +0x1e4/+0x1e6/+0xccc, hero +0x32, the hotkey manager 0x01d1df5c);
 *   - the bar feed 0x00c58797 (SetSkillSlot), onSelectSkill, StartSkillDelay / IsSkillReady / the tick,
 *     the stat check 0x0109228f, the class special cases 0x01096e55 and the mana / AG check 0x01091692.
 *
 * OFFLINE DEMO (the server's data in the real game): the learned list (the skill list packet), the
 * hero's mana/AG spending and regeneration, the save of the Skill Imprint slots.  The bar's isUse is the
 * reconstructed part of the usability check 0x010918c7: the stat requirements and the class special cases
 * (the weapon, buff, world and item branches are not reconstructed and count as met). */

#include <stddef.h>
#include <stdint.h>

#include "../../reconstructed/skill/skill_table.h"
#include "../../reconstructed/skill/skill_tooltip.h"
#include "../../reconstructed/skill/skill_use.h"

#ifdef __cplusplus
extern "C" {
#endif

struct mu_lang;
typedef struct mu_skill_book mu_skill_book;

/* lang: the loaded Lang tables (NULL: no skill table, every query answers "none"); lang_dir: the same
 * directory, for skills_ext.tsv (optional); game_root: for Data/Local/skilltooltiptext.bmd (optional). */
mu_skill_book *mu_skill_book_open(const struct mu_lang *lang, const char *lang_dir, const char *game_root);
void mu_skill_book_close(mu_skill_book *book);
size_t mu_skill_book_count(const mu_skill_book *book);          /* skill records */
size_t mu_skill_book_tooltips(const mu_skill_book *book);       /* SkillTooltipText records */
const mu_skill_record *mu_skill_book_record(const mu_skill_book *book, int32_t skill);

typedef struct mu_skill_stats {
    int32_t class_byte;                /* hero + 0x12 (class index = byte & 0xf, 0x0095f5cc) */
    uint16_t strength, agility, vitality, energy, command;
    int32_t mana, ag;
} mu_skill_stats;
void mu_skill_book_set_stats(mu_skill_book *book, const mu_skill_stats *stats);

/* DEMO: the learned list of a class index (a fixed demo list filtered by the table) and the first ten on
 * the bar; returns the learned count. */
int mu_skill_book_demo(mu_skill_book *book, int32_t class_index);
int mu_skill_book_learn(mu_skill_book *book, int32_t skill);
const mu_skill_hero *mu_skill_book_hero(const mu_skill_book *book);
const mu_skill_hotkeys *mu_skill_book_hotkeys(const mu_skill_book *book);

/* The bar's usability of a skill (isUse): stats (0x0109228f) and the class special cases (0x01096e55). */
int mu_skill_book_usable(const mu_skill_book *book, int32_t skill);
/* 0x00c58797: the SetSkillSlot argument when the bar changed (1), else 0. */
int mu_skill_book_feed(mu_skill_book *book, char *json, size_t cap);
/* onSelectSkill of bar slot 0..9; returns 1 when the selection changed. */
int mu_skill_book_select_slot(mu_skill_book *book, int slot);
int32_t mu_skill_book_selected(const mu_skill_book *book);       /* the hotkeys' selected skill (0 none) */

enum { MU_SKILL_CAST_OK = 0, MU_SKILL_CAST_NONE, MU_SKILL_CAST_UNUSABLE, MU_SKILL_CAST_DELAY, MU_SKILL_CAST_MANA,
       MU_SKILL_CAST_AG };
/* The client checks of a cast of `skill` in the use controller's order (0x0107e99a: the stat check,
 * the usability, IsSkillReady, the mana / AG check), then StartSkillDelay.  events: the onUseSkillDelay
 * (skill, delay) pairs; *potion: mana was short (the client drinks a potion then).  DEMO: a cast spends
 * the mana and AG of GetSkillInformation (the server's job). */
int mu_skill_book_cast(mu_skill_book *book, int32_t skill, int32_t events[2][2], int *nevents, int *potion);
const char *mu_skill_cast_name(int result);
void mu_skill_book_tick(mu_skill_book *book, int32_t dt_ms);
/* The delay left on `skill` (the first learned entry), as remaining / total (0 none). */
float mu_skill_book_delay_left(const mu_skill_book *book, int32_t skill);

/* The wrap width factor of the tooltip ([0x06fbcd94], the client's screen rate: window width / 640; the text is
 * measured with the unscaled interface font, so a wider window wraps later).  Default 1. */
void mu_skill_book_set_screen(mu_skill_book *book, int32_t width);
/* The tooltip of a skill as SkillInfoPopup gets it (UTF-8 title and body HTML); 0 when there is none. */
int mu_skill_book_tooltip(mu_skill_book *book, int32_t skill, char *title, size_t title_cap, char *body,
                          size_t body_cap);
/* The tooltip's text lines (tests, reports). */
int mu_skill_book_tooltip_lines(mu_skill_book *book, int32_t skill, mu_skill_tip *out);

/* Skill icons (0x01097130): the bitmap and texture cell of a skill; mu_skill_icon_file gives the bitmap's
 * file (Data/...); cell size 20 x 28 texels is the bar's legacy cell (layer choice for the windows). */
int mu_skill_book_icon(const mu_skill_book *book, int32_t skill, mu_skill_icon *out);
const char *mu_skill_icon_file(int32_t bitmap);

/* ---- the Skill Imprint window (SkillStampFrame, handler 0x00c1f99c) ----
 * slots 0..4: the five bar slots of the shown select page (page 0: bar slots 0..4, 1: 5..9);
 * slots 5..19: the learned list's page (15 per page, learned index = (page - 1) * 15 + slot - 5);
 * a drag from a learned slot to a bar slot assigns the skill (0x00c2226c; a skill already on the bar
 * leaves its old slot), from a bar slot to another swaps them; Save keeps the bar, Cancel restores it. */
typedef struct mu_skill_stamp {
    int page, pages;                  /* learned list page (1-based) and count */
    int select_page;                  /* 0: bar slots 1..5, 1: 6..10 */
    int drag_from, drag_to;           /* +0x1fc / +0x200 */
    int32_t saved[MU_SKILL_SLOTS];    /* the bar when the window opened (Cancel) */
} mu_skill_stamp;
void mu_skill_book_stamp_open(mu_skill_book *book, mu_skill_stamp *stamp);
/* The skill a window slot shows: learned (0 none) and the base the icon falls back on. */
int32_t mu_skill_book_stamp_skill(const mu_skill_book *book, const mu_skill_stamp *stamp, int slot);
/* Apply a drag (0x00c2226c mode 0); returns 1 when the bar changed, -1 for "not learned" (GlobalText
 * 0x12bb), 0 otherwise. */
int mu_skill_book_stamp_drop(mu_skill_book *book, mu_skill_stamp *stamp, int from, int to);
void mu_skill_book_stamp_cancel(mu_skill_book *book, const mu_skill_stamp *stamp);

#ifdef __cplusplus
}
#endif

#endif
