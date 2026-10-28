#ifndef MU_MAP_OVERLAY_STATE_H
#define MU_MAP_OVERLAY_STATE_H
#include "map_overlay.h"
typedef struct mu_dom_map_overlay {
    mu_map_unit markers[MU_MAP_MARKERS_MAX], detected[MU_MAP_DETECTED_MAX];
    int count, detected_count;
    uint32_t detector_seq;
} mu_dom_map_overlay;
#endif
