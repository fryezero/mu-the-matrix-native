#ifndef MU_MAP_OVERLAY_WIRE_H
#define MU_MAP_OVERLAY_WIRE_H
#include "map_overlay.h"
int mu_map_overlay_marker_parse(const uint8_t *p, size_t n, mu_map_unit *out);
/* C2 E7/05: LE count at 7, five-byte kind/x16/y16 entries at 9. Zero kinds skipped.
 * Returns compacted count, -1 for malformed or over-capacity. */
int mu_map_overlay_detect_parse(const uint8_t *p, size_t n, mu_map_unit out[MU_MAP_DETECTED_MAX]);
#endif
