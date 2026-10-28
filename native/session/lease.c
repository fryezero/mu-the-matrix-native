/* SESSION-CORE-001: the simulation lease and its audit.
 *
 * Between mu_session_sim_begin and _end the world may write the MOTION zones of the leased records
 * (MoveCharacters' remote step, MoveItems' sparkle, the dead fade - once those domains exist; today
 * the hero CHARACTER record's tile). Everything else in a domain's zone list is REPLICATED: only an
 * apply function (inside mu_session_pump) may write it. Audit builds (-DMU_SESSION_AUDIT) copy the
 * replicated zones at begin and compare at end; a difference aborts and names the zone, the offset
 * and the field. The zone list is the same one the journal's SNAPSHOT records dump (and, after
 * LAYOUT-001, the layout manifest's zone column generates). */
#include "session_internal.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void mu_audit_add(mu_audit_zones *zs, const char *name, const uint8_t *base, uint32_t offset, uint32_t size, mu_zone zone,
                  const char *field)
{
    if (!size)
        return;
    if (zs->count >= MU_AUDIT_ZONES_MAX) {
        fprintf(stderr, "lease audit: zone capacity exceeded\n");
        abort();
    }
    mu_audit_zone *z = &zs->z[zs->count++];
    z->name = name;
    z->base = base;
    z->offset = offset;
    z->size = size;
    z->zone = zone;
    z->field = field;
}

/* Bound fields name the audit/dump ranges; unknown gaps stay replicated.
 * The session may own a prefix of a client record, so clip to its actual storage. */
void mu_audit_layout(mu_audit_zones *zs, const char *name, const uint8_t *base, uint32_t size,
                     const mu_layout_record *record)
{
    uint32_t at = 0;
    for (size_t i = 0; i < record->field_count && at < size; ++i) {
        const mu_layout_field *f = &record->fields[i];
        if (f->offset >= size)
            break;
        if (f->offset > at)
            mu_audit_add(zs, name, base, at, f->offset - at, MU_ZONE_REPLICATED, "unknown");
        uint32_t end = f->offset + f->size;
        if (end > size)
            end = size;
        mu_audit_add(zs, name, base, f->offset, end - f->offset,
                     f->zone == MU_LAYOUT_MOTION ? MU_ZONE_MOTION :
                     f->zone == MU_LAYOUT_VIEW ? MU_ZONE_VIEW : MU_ZONE_REPLICATED, f->name);
        at = end;
    }
    if (at < size)
        mu_audit_add(zs, name, base, at, size - at, MU_ZONE_REPLICATED, "unknown");
}

void mu_session_zones(const mu_session *s, mu_audit_zones *zones)
{
    memset(zones, 0, sizeof *zones);
#define MU_DOMAIN(name) mu_dom_##name##_zones(s, zones);
#include "domains_all.def"
#undef MU_DOMAIN
}

size_t mu_session_zone_views(const mu_session *s, mu_session_zone_view *out, size_t cap)
{
    mu_audit_zones zs;
    mu_session_zones(s, &zs);
    size_t n = 0;
    for (int i = 0; i < zs.count && n < cap; ++i, ++n) {
        out[n].name = zs.z[i].name;
        out[n].field = zs.z[i].field;
        out[n].base = zs.z[i].base;
        out[n].offset = zs.z[i].offset;
        out[n].size = zs.z[i].size;
        out[n].motion = zs.z[i].zone == MU_ZONE_MOTION;
        out[n].view = zs.z[i].zone == MU_ZONE_VIEW;
    }
    return n;
}

static void misuse(const char *what)
{
#ifdef MU_SESSION_AUDIT
    fprintf(stderr, "mu_session lease: %s\n", what);
    abort();
#else
    (void)what;
#endif
}

mu_sim mu_session_sim_begin(mu_session *s)
{
    mu_sim sim;
    memset(&sim, 0, sizeof sim);
    sim.hero_index = -1;
    if (!s)
        return sim;
    if (s->sim_open || s->pumping) {
        misuse(s->sim_open ? "sim_begin inside a lease" : "sim_begin inside a pump");
        return sim;
    }
    s->sim_open = 1;
    sim.epoch = ++s->sim_epoch;
    sim.hero_record = s->hero.record;
#ifdef MU_SESSION_AUDIT
    mu_audit_zones zs;
    mu_session_zones(s, &zs);
    size_t total = 0;
    for (int i = 0; i < zs.count; ++i)
        if (zs.z[i].zone == MU_ZONE_REPLICATED)
            total += zs.z[i].size;
    if (total > s->audit_size) {
        free(s->audit_snapshot);
        s->audit_snapshot = malloc(total);
        s->audit_size = s->audit_snapshot ? total : 0;
    }
    size_t at = 0;
    for (int i = 0; i < zs.count && s->audit_snapshot; ++i)
        if (zs.z[i].zone == MU_ZONE_REPLICATED) {
            memcpy(s->audit_snapshot + at, zs.z[i].base + zs.z[i].offset, zs.z[i].size);
            at += zs.z[i].size;
        }
#endif
    return sim;
}

void mu_session_sim_end(mu_session *s, const mu_sim *sim)
{
    if (!s || !sim)
        return;
    if (!s->sim_open || sim->epoch != s->sim_epoch) {
        misuse("sim_end without its sim_begin");
        return;
    }
#ifdef MU_SESSION_AUDIT
    mu_audit_zones zs;
    mu_session_zones(s, &zs);
    size_t at = 0;
    for (int i = 0; i < zs.count && s->audit_snapshot; ++i) {
        const mu_audit_zone *z = &zs.z[i];
        if (z->zone != MU_ZONE_REPLICATED)
            continue;
        const uint8_t *now = z->base + z->offset;
        for (uint32_t k = 0; k < z->size; ++k)
            if (now[k] != s->audit_snapshot[at + k]) {
                char msg[256];
                snprintf(msg, sizeof msg,
                         "lease audit: %s+0x%03x (%s) changed during the lease (replicated zone, 0x%02x -> 0x%02x)",
                         z->name, (unsigned)(z->offset + k), z->field ? z->field : "?",
                         (unsigned)s->audit_snapshot[at + k], (unsigned)now[k]);
                mu_journal_text(s->cfg.journal, MU_JNL_EVENT, s->tick, s->now, msg);
                mu_journal_close(s->cfg.journal);   /* flush the evidence before the abort */
                s->cfg.journal = NULL;
                fprintf(stderr, "%s\n", msg);
                abort();
            }
        at += z->size;
    }
#endif
    s->sim_open = 0;
}

void mu_session_step(mu_session *s, mu_domain d, const mu_sim *sim)
{
    if (!s || !sim || !s->sim_open || sim->epoch != s->sim_epoch) {
        misuse("mu_session_step outside a lease");
        return;
    }
    /* domains_all.def lists the domains in mu_domain order (both generated from one sorted list);
     * the X-macro cannot upper-case a name, so the domain is found by its index */
    int i = 0;
#define MU_DOMAIN(name)                     \
    if (i++ == (int)d)                      \
        mu_dom_##name##_step(s, sim);
#include "domains_all.def"
#undef MU_DOMAIN
}
