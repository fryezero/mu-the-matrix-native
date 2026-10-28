#include "../session_internal.h"
#include "map_overlay_wire.h"
#include <string.h>
mu_map_overlay_view mu_session_map_overlay(const mu_session *s)
{
    mu_map_overlay_view v = {0};
    if (s) {
        v.markers = s->map_overlay.markers;
        v.detected = s->map_overlay.detected;
        v.count = s->map_overlay.count;
        v.detected_count = s->map_overlay.detected_count;
        v.revision = mu_session_rev(s, MU_DOMAIN_MAP_OVERLAY);
        v.detector_seq = s->map_overlay.detector_seq;
    }
    return v;
}
mu_apply map_overlay_marker(mu_session *s, const mu_frame *f)
{
    mu_map_unit u;
    int r = mu_map_overlay_marker_parse(f->bytes, f->length, &u);
    if (r <= MU_MAP_UNIT_NONE)
        return MU_APPLY_IGNORED;
    mu_dom_map_overlay *d = &s->map_overlay;
    int i = 0;
    while (i < d->count && (d->markers[i].type != u.type || d->markers[i].key != u.key))
        ++i;
    if (r == MU_MAP_UNIT_DEL) {
        if (i == d->count)
            return MU_APPLY_IGNORED;
        memmove(d->markers + i, d->markers + i + 1, (size_t)(d->count - i - 1) * sizeof u);
        memset(&d->markers[--d->count], 0, sizeof u);
    } else {
        if (i == MU_MAP_MARKERS_MAX)
            return MU_APPLY_IGNORED;
        if (i == d->count)
            ++d->count;
        d->markers[i] = u;
    }
    mu_session_touch(s, MU_DOMAIN_MAP_OVERLAY);
    return MU_APPLY_DONE;
}
mu_apply map_overlay_detected(mu_session *s, const mu_frame *f)
{
    mu_map_unit parsed[MU_MAP_DETECTED_MAX];
    int n = mu_map_overlay_detect_parse(f->bytes, f->length, parsed);
    if (n < 0)
        return MU_APPLY_IGNORED;
    mu_dom_map_overlay *d = &s->map_overlay;
    memset(d->detected, 0, sizeof d->detected);
    memcpy(d->detected, parsed, (size_t)n * sizeof parsed[0]);
    d->detected_count = n;
    ++d->detector_seq;
    mu_session_touch(s, MU_DOMAIN_MAP_OVERLAY);
    return MU_APPLY_DONE;
}
void mu_dom_map_overlay_init(mu_session *s) { memset(&s->map_overlay, 0, sizeof s->map_overlay); }
void mu_dom_map_overlay_free(mu_session *s) { (void)s; }
void mu_dom_map_overlay_step(mu_session *s, const mu_sim *sim)
{
    (void)s;
    (void)sim;
}
void mu_dom_map_overlay_zones(const mu_session *s, mu_audit_zones *z)
{
    mu_audit_add(z, "map_overlay.records", (const uint8_t *)&s->map_overlay, 0, sizeof s->map_overlay,
                 MU_ZONE_REPLICATED, "frame-owned markers and detector refresh");
}
#ifdef MU_SESSION_SEED
void mu_dom_map_overlay_seed(mu_session *s, const struct mu_session_seed *seed)
{
    (void)s;
    (void)seed;
}
#endif
