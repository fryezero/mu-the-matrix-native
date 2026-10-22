#ifndef MU_HUD_TIP_H
#define MU_HUD_TIP_H

/* Item tooltip text (NATIVE-HUD-001; shared by mu-render and the GFx layer
 * since NATIVE-GFX-002).
 *
 * The table-driven part of the client's tooltip builder 0x00f0eb44: the name
 * line from itemtooltip, then up to 15 configured lines through the
 * reconstructed formatter cases (reconstructed/hud/tooltip_format.c), and the
 * InfoPopup HTML assembly 0x00b8d94b (reconstructed/hud/tooltip_html.c).  Not
 * reconstructed (and not produced): the runtime-patched header (0x00f0edf1)
 * and GlobalText lines, price, set/socket/excellent/harmony blocks and the
 * full name-colour rules.  Tables are read from the game root and never
 * written out. */

#include <stddef.h>
#include <stdint.h>

#include "mu_data.h"
#include "mu_hud.h"

enum { MU_HUD_TIP_LINES = 40 };

typedef struct mu_hud_tip {
    char text[MU_HUD_TIP_LINES][256];
    int32_t color[MU_HUD_TIP_LINES];
    int32_t count, unsupported, from_tables;
} mu_hud_tip;

typedef struct mu_hud_tip_tables {
    mu_data_table items, tooltip, text;
    int have_items, have_tooltip, have_text;
} mu_hud_tip_tables;

/* Loads Data/Local/item.bmd, itemtooltip.bmd and itemtooltiptext.bmd (each
 * optional; root NULL leaves all absent). */
void mu_hud_tip_tables_load(const char *root, mu_hud_tip_tables *t);
/* Borrow a bounded, NUL-terminated ItemTooltipText template by its original u16 ID. */
const char *mu_hud_tip_text(const mu_hud_tip_tables *, uint16_t);
void mu_hud_tip_tables_free(mu_hud_tip_tables *t);
/* hero = strength, agility, energy, level (the formatter's hero inputs). */
void mu_hud_tip_build(const mu_hud_tip_tables *t, const mu_hud_item *it, const int hero[4], mu_hud_tip *tp);
/* The InfoPopup HTML of the lines, converted to UTF-8 (0x00a99d93 under a
 * Latin-1 code page).  Returns the full length (writes at most cap-1). */
size_t mu_hud_tip_html(const mu_hud_tip *tp, char *utf8, size_t cap);

/* A current inventory snapshot can differ from the constructor's full
 * durability. maximum is the reconstructed maximum-durability result. */
void mu_hud_tip_build_durability(const mu_hud_tip_tables *tables,const mu_hud_item *item,
                                const int hero[4],uint8_t maximum,mu_hud_tip *tip);
#endif
