#include "map_overlay_wire.h"
#include <string.h>
#ifndef MU_MAP_OVERLAY_MUTATION
#define MU_MAP_OVERLAY_MUTATION 0
#endif
int mu_map_overlay_marker_parse(const uint8_t *p, size_t n, mu_map_unit *out)
{
    if (n < 10 || p[0] != 0xc1 || p[1] != n || p[2] != 0xe7 || (p[3] != 3 && p[3] != 4))
        return -1;
    if (p[7] == 0 && p[3] == 3 && !memchr(p + 10, 0, n - 10))
        return -1;
    int r = mu_map_unit_packet(p, n, p[3] == 3, out);
    if (MU_MAP_OVERLAY_MUTATION == 1 && r == MU_MAP_UNIT_ADD)
        out->key = p[5];
    return r;
}
int mu_map_overlay_detect_parse(const uint8_t *p, size_t n, mu_map_unit out[MU_MAP_DETECTED_MAX])
{
    if (n < 9 || p[0] != 0xc2 || ((size_t)p[1] * 256 + p[2]) != n || p[3] != 0xe7 || p[4] != 5)
        return -1;
    unsigned count = (unsigned)p[7] | ((unsigned)p[8] << 8);
    if (n != 9 + (size_t)count * 5)
        return -1;
    unsigned used = 0;
    for (unsigned i = 0; i < count; ++i) {
        const uint8_t *e = p + 9 + i * 5;
        if (!e[0] && MU_MAP_OVERLAY_MUTATION != 2)
            continue;
        if (used == MU_MAP_DETECTED_MAX)
            return -1;
        int x = e[1] | (e[2] << 8), y = e[3] | (e[4] << 8);
        if (MU_MAP_OVERLAY_MUTATION == 3)
            x = e[1];
        mu_map_detected_unit((int)used, e[0], x, y, &out[used]);
        if (MU_MAP_OVERLAY_MUTATION == 4)
            out[used].key = (int)i;
        ++used;
    }
    return (int)used;
}
