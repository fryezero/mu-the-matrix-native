/* CHARSEL-ITEMS-001: authored appearance records, not character-list decoding. */
#ifndef MU_CHARSEL_ITEMS_H
#define MU_CHARSEL_ITEMS_H
#include "../core/mu_charsel.h"
#include "../core/mu_renderchar.h"

/* RenderCharacter's part caller 0x0136a6d7 forwards ext; RenderLinkItem's
 * RenderObjDraw caller 0x012c6a83 forces ext to zero. Both forward level and
 * the boolean excellent flag. The renderer converts level back to level<<3.
 * Unset records deliberately retain the old selection mesh path. */
static inline int mu_charsel_record_glow(const mu_charsel_item_record *record, int slot,
                                        mu_renderchar_glow *glow)
{
    if (slot < 1 || slot >= MU_CHARACTER_ITEMS || !record->set)
        return 0;
    *glow = (mu_renderchar_glow){0};
    glow->type = 0xae6 + record->code;
    glow->level = record->level;
    glow->option1 = record->option != 0;
    glow->ext = slot < MU_CHARACTER_PART_SLOTS ? record->ext : 0;
    return 1;
}
#endif
