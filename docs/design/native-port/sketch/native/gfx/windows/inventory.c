/* windows/inventory.c (sketch): InventoryFrame as a session view. */
#include "../mu_window_view.h"

typedef struct inventory_view { int32_t drag_from; } inventory_view;

static void inventory_sync(void *self, struct mu_gfx_movie *m, const mu_session *s)
{
    /* TODO: const mu_inventory *inv = mu_session_inventory(s);  // domains/inventory.h (SESSION-ITEMS-001)
     * for each cell: push item code/level/durability/options (the verified grid and slot pass);
     * the Zen line from mu_session_money(s)  - one source for shop, mix, trade, warp and quest rewards */
    (void)self; (void)m; (void)s;
}

static int inventory_callback(void *self, struct mu_gfx_movie *m, mu_session *s, const char *name, const char *args)
{
    /* TODO: "drop" from,to -> mu_intent move_item {INVENTORY, from, INVENTORY, to};
     *   SENT: keep the item under the cursor until the server's answer changes MU_DOMAIN_INVENTORY;
     *   REFUSED: show the client's notice; UNRECOVERED: development banner, item snaps back */
    (void)self; (void)m; (void)s; (void)name; (void)args;
    return 0;
}

const mu_window_view_ops mu_wv_inventory = {
    .movie = "InventoryFrame",
    .watch = {MU_DOMAIN_INVENTORY, MU_DOMAIN_HERO}, .watch_count = 2,
    .state_size = sizeof(inventory_view),
    .sync = inventory_sync, .callback = inventory_callback,
};
