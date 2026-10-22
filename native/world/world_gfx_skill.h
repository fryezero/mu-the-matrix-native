/* The skill host of mu-world / mu-client's GFx layer (NATIVE-SKILL-001, docs/research/client-skills.md).
 *
 * Binds core/mu_skill (the reconstructed skill routines over the client's Skill(Kor) table and
 * SkillTooltipText.bmd) to the GFx layer: the bar feed, onSelectSkill, the skill tooltip in SkillInfoPopup,
 * the Skill Imprint window (SkillStampFrame) with its pages and drags, and the skill icons the game draws
 * over that window: RenderBitmap of the client's skill sheets (Data/Interface newui_skill00 /
 * newui_non_skill00 / new_Master_Icon / 4th_Skill_Icon, bitmap and cell as 0x01097130 picks them) and the
 * delay overlay of 0x00f18574 (colour 1, .5, .5, alpha .5, the remaining part from the bottom).
 * OFFLINE DEMO: the server's skill packets (core/mu_skill_demo.c: the login's skill list and saved bar, a
 * skill learned or forgotten; the client's handlers take them, NATIVE-SKILL-002) and the save. */
#ifndef MU_WORLD_GFX_SKILL_H
#define MU_WORLD_GFX_SKILL_H

#include <stdint.h>

struct mu_gfx_layer;
struct mu_lang;
struct mu_skill_book;
typedef struct wg_skill wg_skill;

wg_skill *wg_skill_open(const char *game_root, const struct mu_lang *lang, const char *lang_dir, int32_t class_byte);
void wg_skill_close(wg_skill *s);
/* Becomes the layer's skill host (mu_gfx_layer_set_skill_host). */
void wg_skill_attach(wg_skill *s, struct mu_gfx_layer *layer);
struct mu_skill_book *wg_skill_book(wg_skill *s);
/* A cast of the selected skill through the client's checks; on success the layer gets onUseSkillDelay and
 * the demo hero spends the mana/AG.  Returns MU_SKILL_CAST_*; *skill = the skill (0 none). */
int wg_skill_cast(wg_skill *s, int32_t *skill);
void wg_skill_tick(wg_skill *s, double dt_ms);
/* DEMO server: verb "learn" / "forget" sends the 0xFE / 0xFF skill packet for `skill`; 1 when handled. */
int wg_skill_server(wg_skill *s, const char *verb, int32_t skill);
/* The interface's width in points (the tooltip wrap's screen rate). */
void wg_skill_set_screen(wg_skill *s, int32_t width);
/* Counters for the run report. */
void wg_skill_counts(const wg_skill *s, long *casts, long *refused, long *icons_drawn, long *tooltips);

#endif
