/* SESSION-MAP-001a: packet-owned overlay records; travel remains in mu_map. */
#ifndef MU_SESSION_MAP_OVERLAY_H
#define MU_SESSION_MAP_OVERLAY_H
#include "../../../reconstructed/map/map.h"
#define MU_MAP_MARKERS_MAX 128
#define MU_MAP_DETECTED_MAX 256
struct mu_session;
typedef struct mu_map_overlay_view {
    const mu_map_unit *markers, *detected;
    int count, detected_count;
    uint32_t revision, detector_seq;
} mu_map_overlay_view;
mu_map_overlay_view mu_session_map_overlay(const struct mu_session *s);
#endif
