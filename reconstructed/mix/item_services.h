#ifndef MU_ITEM_SERVICES_H
#define MU_ITEM_SERVICES_H
#include <stdint.h>

/* Stable Item.bmd record and 300-byte item snapshot. Personal-store ban
 * 0x016be0dc and registration gate 0x00c00b38. The helper 0x016b823e
 * returns true for every stable record: its nested kind-A predicates
 * require the same byte to equal 8, 25 and 26. See client-mix.md. */
int mu_personal_store_ban(const uint8_t *record, const uint8_t *item);
int mu_personal_store_register(const uint8_t *record, const uint8_t *item);
/* NpcShop repair-mode toggle 0x00bf1765. */
int mu_repair_toggle(int state);
/* Clear repair request payload, builder boundary of 0x00bf1916 and
 * 0x00ab83e4. Slot 255 means repair-all; mode 0 at an NPC, 1 self repair.
 * Transport/encryption and reply layout are outside this reconstruction. */
void mu_repair_request(uint8_t out[5], uint8_t slot, uint8_t mode);
#endif
