#ifndef MU_ITEMS_STATE_H
#define MU_ITEMS_STATE_H
#include "items.h"
typedef struct mu_dom_items {
    mu_gi_item pool[MU_GI_ITEMS];
    uint8_t used[MU_GI_ITEMS], entries[MU_GI_ITEMS][19];
    uint32_t creates, deletes;
    int32_t pending;
    mu_items_present_fn present;
    void *context;
} mu_dom_items;
#endif
