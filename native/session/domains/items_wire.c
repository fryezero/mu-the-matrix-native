#include "items_wire.h"
int mu_items_delete_parse(const uint8_t *p, size_t n, uint16_t out[255])
{
    if (n < 5 || n < 5u + 2u * p[4]) return -1;
    for (unsigned i = 0; i < p[4]; ++i) {
        unsigned key = ((unsigned)p[5 + 2*i] << 8) | p[6 + 2*i];
        out[i] = key < 1000 ? (uint16_t)key : 0;
    }
    return p[4];
}
size_t mu_items_pickup_request(uint8_t out[5], uint16_t slot, int32_t pending)
{
    if (pending != -1) return 0;
    /* Both ordinary and zen branches use Begin(C1, 0), keyed adds and Send(1,0).
     * Keep the observed zero opcode; do not substitute a different MU version. */
    out[0] = 0xc1; out[1] = 5; out[2] = 0;
    out[3] = (uint8_t)(slot >> 8); out[4] = (uint8_t)slot;
    return 5;
}
int32_t mu_items_pickup_tail(int32_t code)
{
    if (code == 0x1c0d || code == 0x1c0e || code == 0x1c10 ||
        code == 0x180f || code == 0x1c16 || code == 0x1c1f) return 0x45;
    return code == 0x1c29 ? 0x2d3 : 0x1d;
}
