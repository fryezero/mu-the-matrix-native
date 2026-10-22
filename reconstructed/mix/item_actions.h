#ifndef MU_ITEM_ACTIONS_H
#define MU_ITEM_ACTIONS_H
#include <stdint.h>

/* Inventory's jewel predicate 0x00ad50b4. This is the predicate, not the
 * earlier, opaque item-action extension or a prediction of server success. */
typedef struct mu_jewel_target {
    int32_t code, level, option;
    uint8_t kind_a, kind_b, type, durability, period;
} mu_jewel_target;
int mu_jewel_allowed(int32_t jewel, const mu_jewel_target *item, int mix_visible);

/* The unencrypted body built by 0x00960420 after its busy/throttle gates.
 * source_slot includes the equipment offset 12; target_slot is the
 * original destination index. No encryption or socket I/O. */
void mu_jewel_request(uint8_t out[6], uint8_t source_slot, uint8_t target_slot, uint8_t mode);
#endif
