#ifndef MU_SESSION_ITEMS_H
#define MU_SESSION_ITEMS_H
#include "../../../reconstructed/items/ground_items.h"
typedef struct mu_session mu_session;
typedef struct mu_items_view {
    const mu_gi_item *pool;
    const uint8_t *used;
    uint32_t creates, deletes;
    int32_t pending;
} mu_items_view;
mu_items_view mu_session_items(const mu_session *s);
/* Bind only presentation services. A NULL callback detaches the view. The session
 * retains packet records and reconstructs the presentation when a view rebinds. */
typedef void (*mu_items_present_fn)(void *, int32_t, const uint8_t[19]);
void mu_session_items_bind(mu_session *s, mu_items_present_fn fn, void *ctx);
#endif
