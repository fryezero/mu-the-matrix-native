#ifndef MU_ITEMS_WIRE_H
#define MU_ITEMS_WIRE_H
#include <stddef.h>
#include <stdint.h>
/* Plain bodies only. The 0x012424bd decode prelude is deliberately excluded. */
int mu_items_delete_parse(const uint8_t *p, size_t n, uint16_t out[255]);
size_t mu_items_pickup_request(uint8_t out[5], uint16_t slot, int32_t pending);
/* Sound/label slice 0x01242b3c..0x01242c2b, after successful inventory insertion.
 * Does not insert an inventory item or clear the ground object's live byte. */
int32_t mu_items_pickup_tail(int32_t code);
#endif
