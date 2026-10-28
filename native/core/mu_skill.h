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
 * NATIVE-SKILL-002: the learned list, the Skill Imprint (stamp) manager and the hotkey manager come from the
 * server's packets through the client's handlers (reconstructed/skill/skill_list.c: opcode 0xA0 sub 0x20 the
 * skill list / one skill added / removed, sub 0x03 the saved hotkeys); the bar shows the stamp manager's slots.
 * OFFLINE DEMO (core/mu_skill_demo.c, the server in the real game): those packets from a demo table, the
 * hero's mana/AG spending and regeneration, and the save of the Skill Imprint slots. The bar's isUse runs
 * 0x010918c7 and the class cases. World/equipment/buff answers remain explicit host inputs. The Master tree
 * uses the decoded BMD tables, A0 10/A0 14 answers, and 0x00a01692 supplies tooltip damage. */

#include <stddef.h>
#include <stdint.h>

#include "../../reconstructed/skill/skill_list.h"
#include "../../reconstructed/skill/skill_table.h"
#include "../../reconstructed/skill/skill_tooltip.h"
#include "../../reconstructed/skill/skill_use.h"
#include "../../reconstructed/skill/skill_canuse.h"
#include "../../reconstructed/skill/master_tree.h"

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
/* World/equipment/buff answers for 0x010918c7. The book supplies its Skill(Kor) environment. NULL resets to an
 * untransformed, unequipped hero in world 0; callbacks remain explicit host boundaries. */
void mu_skill_book_set_use_state(mu_skill_book *book, const mu_skill_use_env *state);
void mu_skill_book_set_elemental(mu_skill_book *book, int32_t elemental);
const mu_skill_env *mu_skill_book_env(const mu_skill_book *book);
mu_master_tree *mu_skill_book_master(mu_skill_book *book);
mu_master_env *mu_skill_book_master_env(mu_skill_book *book);
int mu_skill_book_requirement(mu_skill_book *book, int32_t base, int32_t *skill, int32_t *master,
                               int32_t *level);
/* Build the class tree and emit its current ranks/text after the movie's Init. Tables remain book-owned. */
void mu_skill_book_master_build(mu_skill_book *book);
int mu_skill_book_master_tooltip(mu_skill_book *book, int slot, char *title, size_t title_cap, char *body,
                                 size_t body_cap);
/* NATIVE-SKILL-003: the tooltip environment the book's tooltips use (Skill(Kor), GlobalText, the measure,
 * FormulaData, the screen rate), for the fourth tree's tooltips. */
void mu_skill_book_tip_env(mu_skill_book *book, mu_skill_tip_env *out);
/* FormulaData is a host boundary, as in the Unicorn comparison. Absent callback answers 0. */
void mu_skill_book_set_formula(mu_skill_book *book, mu_master_formula_fn formula, void *user);
double mu_skill_book_formula(mu_skill_book *book, int group, int id, int argument);
/* OFFLINE DEMO: A0 10 at login, A0 14 in answer to a decoded C1 08 01 16 request. No network I/O. */
int mu_skill_book_demo_master_login(mu_skill_book *book);
int mu_skill_book_demo_master_request(mu_skill_book *book, const uint8_t *packet, size_t size);

/* The hero enters the world with class byte (attributes +0x187; class index = byte & 0xf): empty learned list and
 * hotkeys, the stamp manager built for the class (0x01095c77; a layer choice: the client does it in the window's
 * 0x00c2008b). */
void mu_skill_book_enter(mu_skill_book *book, int32_t class_byte);
/* A server packet (C1/C2 head): opcode 0xA0 sub 0x20 (0x0126176e) or sub 0x03 (0x0126f225); 1 when handled. */
int mu_skill_book_receive(mu_skill_book *book, const uint8_t *packet, size_t size);
const mu_skill_stamp_mgr *mu_skill_book_stamp_mgr(const mu_skill_book *book);
/* 1 when skills_class.tsv gave the records' class maps (+0x6c); else the demo's lists stand in for them. */
int mu_skill_book_has_classes(const mu_skill_book *book);
/* DEMO class map: let class index `class_index` have `skill` (record +0x6c). */
void mu_skill_book_allow(mu_skill_book *book, int32_t skill, int32_t class_index);

/* OFFLINE DEMO server (core/mu_skill_demo.c): the login packets (the class's skill list, then its saved bar) for a
 * class byte; mu_skill_book_demo is the same for a class index.  Returns the learned count. */
enum { MU_DEMO_CLASSES = 16, MU_DEMO_SKILLS = 64 };
typedef struct mu_skill_demo_class {
    int32_t skills[MU_DEMO_SKILLS];
    int count;
    int32_t keys[MU_SKILL_SLOTS];
    int has_keys;
} mu_skill_demo_class;
typedef struct mu_skill_demo {
    mu_skill_demo_class classes[MU_DEMO_CLASSES];
    int ready;
} mu_skill_demo;
void mu_skill_demo_reset(mu_skill_demo *model);
int mu_skill_demo_load(mu_skill_demo *model, const char *path);     /* "list CLASS SKILL..." / "keys CLASS K1..K9 K0" lines; -1 no file */
int mu_skill_book_demo_login(mu_skill_demo *model, mu_skill_book *book, int32_t class_byte);
int mu_skill_book_demo(mu_skill_demo *model, mu_skill_book *book, int32_t class_index);
/* DEMO: the server's 0xFE (learned) or 0xFF (forget != 0) packet for one skill. */
int mu_skill_book_demo_learn(mu_skill_book *book, int32_t skill, int forget);
const mu_skill_hero *mu_skill_book_hero(const mu_skill_book *book);
const mu_skill_hotkeys *mu_skill_book_hotkeys(const mu_skill_book *book);

/* The bar's usability (isUse): 0x010918c7 and the class special cases 0x01096e55. */
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
int mu_skill_book_check_cast(mu_skill_book *, int32_t skill, int *potion);
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

/* ---- the Skill Imprint window (SkillStampFrame, handler 0x00c1f99c) over the stamp manager ----
 * slots 0..4: the window's slots (stamp +0x24) of the shown select page (page 0: bar slots 0..4, 1: 5..9);
 * slots 5..19: the tab's entries (15 per page, entry = (page - 1) * 15 + slot - 5, 0x00c22588 / 0x010968c6);
 * a drag from an entry to a slot assigns it (0x00c2226c; an entry already in a slot leaves it, 0x01096c42; an
 * entry without a learned skill: GlobalText 0x12bb), from a slot to another swaps them (0x01096e15); Save
 * (0x00c20db4) commits the window's slots to the bar, Cancel (0x01096dd0) takes the bar's back. */
typedef struct mu_skill_stamp {
    int tab;                          /* 0 Basic Skill (stamp +0xc), 1 Special Skill (+0x18); handler +0x8c */
    int page, pages;                  /* the tab's page (1-based) and count (15 entries per page) */
    int select_page;                  /* 0: bar slots 1..5, 1: 6..10 */
    int drag_from, drag_to;           /* +0x1fc / +0x200 */
    int32_t saved[MU_SKILL_SLOTS];    /* the bar when the window opened (Cancel) */
} mu_skill_stamp;
void mu_skill_book_stamp_open(mu_skill_book *book, mu_skill_stamp *stamp);
/* The skill a window slot shows (0x01096a60: the entry's learned skill, else its base; 0 none) and its entry. */
int32_t mu_skill_book_stamp_skill(const mu_skill_book *book, const mu_skill_stamp *stamp, int slot);
int mu_skill_book_stamp_entry(const mu_skill_book *book, const mu_skill_stamp *stamp, int slot, int32_t *base,
                              int32_t *learned, int *imprint);
/* The tab buttons (onClickBaseSKill / onClickSpecialSkill): page 1 of tab 0 or 1; returns the page count. */
int mu_skill_book_stamp_tab(mu_skill_book *book, mu_skill_stamp *stamp, int tab);
void mu_skill_book_stamp_save(mu_skill_book *book);
/* Apply a drag (0x00c2226c mode 0); returns 1 when the bar changed, -1 for "not learned" (GlobalText
 * 0x12bb), 0 otherwise. */
int mu_skill_book_stamp_drop(mu_skill_book *book, mu_skill_stamp *stamp, int from, int to);
void mu_skill_book_stamp_cancel(mu_skill_book *book, const mu_skill_stamp *stamp);

#ifdef __cplusplus
}
#endif

#endif
