/* domains/inventory.h (sketch, PUBLIC): the hero's items as views see them (SESSION-ITEMS-001).
 * Replaces mu_gfx_layer.c's `item items[MAX_ITEMS=48]` (GL only, per visit). The item record is
 * reconstructed/items' mu_gi_item_data (the ITEM subset the client's 15-byte decode fills,
 * 0x00f09ddc), so a dropped item picked up and an item from the inventory list are the same type. */
#ifndef MU_DOM_INVENTORY_H
#define MU_DOM_INVENTORY_H
#include <stdint.h>
#include "../../../reconstructed/items/ground_items.h"
#include "../mu_intent.h"
typedef struct mu_session mu_session;

typedef struct mu_inventory_cell {
    mu_store store;
    int32_t cell;                  /* the client's slot index in that store */
    int32_t x, y, w, h;            /* grid position and size from Item.bmd (the verified grid pass) */
    mu_gi_item_data item;
} mu_inventory_cell;

#define MU_INVENTORY_CELLS 512     /* TODO(SESSION-ITEMS-001): the client's store sizes (inventory, expanded, warehouse, equipment) */
typedef struct mu_inventory {
    mu_inventory_cell cells[MU_INVENTORY_CELLS];
    int32_t count;
} mu_inventory;

const mu_inventory *mu_session_inventory(const mu_session *s);
#endif
