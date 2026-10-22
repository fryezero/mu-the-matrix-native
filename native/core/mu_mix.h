#ifndef MU_NATIVE_MIX_H
#define MU_NATIVE_MIX_H
#include <stdint.h>

/* Offline inventory snapshots. Outcomes are demo-server inputs, never a
 * prediction of the real server. No transport or encryption is involved. */
typedef struct mu_mix_item {
    int32_t code, level, option, excellent, durability, period;
} mu_mix_item;
typedef struct mu_mix_quote {
    int32_t recipe, ready, supported;
    uint32_t rate, cost;
    char title[96], detail[256];
} mu_mix_quote;
typedef struct mu_mix_book mu_mix_book;
mu_mix_book *mu_mix_book_open(const char *root);
void mu_mix_book_close(mu_mix_book *book);
int mu_mix_book_quote(mu_mix_book *book, int group, const mu_mix_item *items, int n, mu_mix_quote *out);
int mu_mix_book_jewel(mu_mix_book *book, int jewel, const mu_mix_item *target, int mix_visible);
/* Bounded item-service adapter over the same local Item.bmd. Repair rejects
 * option-bearing snapshots whose special-option price inputs are absent. */
int mu_mix_book_store(mu_mix_book *book, const mu_mix_item *item);
int mu_mix_book_repair(mu_mix_book *book, const mu_mix_item *item, int npc,
                       int32_t *cost, int32_t *max_durability);
#endif
