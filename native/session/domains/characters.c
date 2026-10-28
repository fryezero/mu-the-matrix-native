/* SESSION-VIEWPORT-001. Only apply functions create/delete replicated records.
 * The world services are borrowed synchronously during a pump or simulation lease. */
#include "../session_internal.h"
#include "layout_CHARACTER.h"
#include <string.h>
#include <stddef.h>
#ifdef MU_SESSION_SEED
#include "../mu_session_seed.h"
#endif

mu_characters_view mu_session_characters(const mu_session *s)
{
    mu_characters_view v = {s->characters.records, s->characters.used, s->characters.generation,
        s->characters.equipment_revision, s->characters.equipment_calls, s->characters.equipment,
        s->characters.store_open, s->characters.store_title, MU_CHARACTERS_MAX, s->characters.monsters};
    return v;
}

int32_t mu_session_character_index(const mu_session *s, uint16_t key)
{
    for (int32_t i = 0; i < MU_CHARACTERS_MAX; ++i)
        if (s->characters.used[i] && (uint16_t)s->characters.records[i].key == key)
            return i;
    return -1;
}

static mu_rp_env environment(mu_session *s)
{
    mu_rp_env e;
    memset(&e, 0, sizeof e);
    e.world = s->place.world;
    e.scene_state = 6;
    if (s->has_port) {
        e.context = s->port.context;
        e.path_finding2 = s->port.path_finding2;
        e.move_path = s->port.move_path;
        e.move_character_position = s->port.move_character_position;
        e.set_player_walk = s->port.set_player_walk;
        e.set_player_stop = s->port.set_player_stop;
        e.set_action = s->port.set_action;
    }
    return e;
}

mu_apply characters_players(mu_session *s, const mu_frame *f)
{
    if (f->length < 5) return MU_APPLY_IGNORED;
    unsigned count = f->bytes[4] < 75 ? f->bytes[4] : 75;
    /* Validate the entire variable-length packet before changing any slot. */
    mu_rp_viewport v;
    size_t at = 5;
    for (unsigned k = 0; k < count; ++k) {
        int n = mu_rp_viewport_record(f->bytes + at, (int32_t)(f->length - at), &v);
        if (!n) return MU_APPLY_IGNORED;
        at += (size_t)n;
    }
    at = 5;
    mu_rp_env e = environment(s);
    int changed = 0;
    for (unsigned k = 0; k < count; ++k) {
        int n = mu_rp_viewport_record(f->bytes + at, (int32_t)(f->length - at), &v);
        at += (size_t)n;
        if (!strcmp(v.name, "webzen")) continue;
        int32_t i = mu_session_character_index(s, v.key);
        int allocating = i < 0;
        if (i < 0) {
            for (i = 0; i < MU_CHARACTERS_MAX && s->characters.used[i] && s->characters.records[i].live; ++i) {}
            if (i == MU_CHARACTERS_MAX) continue;
        }
        mu_dom_characters *d = &s->characters;
        mu_rp_character *c = &d->records[i];
        mu_rp_character prior = *c;
        mu_rp_character_create(c, (int16_t)v.key, MU_RP_PLAYER_MODEL, v.x, v.y, 0);
        if (allocating) {
            c->guild_bytes[0] = c->guild_bytes[1] = c->guild_bytes[2] = c->guild_bytes[4] = 0;
        } else {
            c->guild = prior.guild;
            memcpy(c->guild_bytes, prior.guild_bytes, sizeof c->guild_bytes);
        }
        mu_rp_calls calls = {0};
        mu_rp_viewport_apply(&v, c, &e, &calls);
        if (!allocating && (v.packet_class & 7) == 1) c->byte_16 = prior.byte_16;
        if (s->has_port && s->port.terrain_height)
            c->position[2] = s->port.terrain_height(s->port.context, c->position[0], c->position[1]);
        memset(&d->monsters[i], 0, sizeof d->monsters[i]);
        d->used[i] = 1;
        if (allocating) ++d->generation[i];
        ++d->equipment_revision[i];
        d->equipment_calls[i] = calls;
        memcpy(d->equipment[i], v.equipment, MU_RP_EQUIP_BYTES);
        d->store_open[i] = 0;
        changed = 1;
    }
    if (changed) mu_session_touch(s, MU_DOMAIN_CHARACTERS);
    return changed ? MU_APPLY_DONE : MU_APPLY_IGNORED;
}

/* Validate a whole batch before mutating the shared character table. */
mu_apply characters_monsters(mu_session *s, const mu_frame *f)
{
    if (f->head != 0xc2 || f->length < 5) return MU_APPLY_IGNORED;
    unsigned count = f->bytes[4] < 75 ? f->bytes[4] : 75;
    size_t at = 5;
    mu_monster_viewport v;
    for (unsigned n = 0; n < count; ++n) {
        int size = mu_monster_viewport_record(f->bytes + at, (int32_t)(f->length - at), &v);
        if (!size) return MU_APPLY_IGNORED;
        at += (size_t)size;
    }
    at = 5;
    int changed = 0;
    mu_rp_env e = environment(s);
    for (unsigned n = 0; n < count; ++n) {
        int size = mu_monster_viewport_record(f->bytes + at, (int32_t)(f->length - at), &v);
        at += (size_t)size;
        mu_rp_character c;
        if (!mu_monster_character_create(&c, &v)) continue;
        int32_t i = mu_session_character_index(s, v.key);
        int allocating = i < 0;
        if (allocating) {
            for (i = 0; i < MU_CHARACTERS_MAX && s->characters.used[i] && s->characters.records[i].live; ++i) {}
            if (i == MU_CHARACTERS_MAX) continue;
        }
        mu_monster_viewport_apply(&c, &v, &e);
        if (s->has_port && s->port.terrain_height)
            c.position[2] = s->port.terrain_height(s->port.context, c.position[0], c.position[1]);
        s->characters.records[i] = c;
        s->characters.monsters[i] = v;
        memset(s->characters.equipment[i], 0, sizeof s->characters.equipment[i]);
        memset(&s->characters.equipment_calls[i], 0, sizeof s->characters.equipment_calls[i]);
        s->characters.used[i] = 1;
        s->characters.store_open[i] = 0;
        if (allocating) ++s->characters.generation[i];
        ++s->characters.equipment_revision[i];
        changed = 1;
    }
    if (changed) mu_session_touch(s, MU_DOMAIN_CHARACTERS);
    return changed ? MU_APPLY_DONE : MU_APPLY_IGNORED;
}

mu_apply characters_move(mu_session *s, const mu_frame *f)
{
    if (f->length < 8) return MU_APPLY_IGNORED;
    uint16_t key = (uint16_t)((f->bytes[3] << 8) | f->bytes[4]);
    int32_t i = mu_session_character_index(s, key);
    if (i < 0) return MU_APPLY_IGNORED;
    mu_rp_env e = environment(s);
    mu_rp_calls calls = {0};
    if (!mu_rp_move_packet(f->bytes, &s->characters.records[i], &e, &calls)) return MU_APPLY_IGNORED;
    mu_session_touch(s, MU_DOMAIN_CHARACTERS);
    return MU_APPLY_DONE;
}

mu_apply characters_destroy(mu_session *s, const mu_frame *f)
{
    if (f->length < 4 || f->length < 4u + 2u * f->bytes[3]) return MU_APPLY_IGNORED;
    uint16_t keys[256];
    int n = mu_rp_destroy_keys(f->bytes, (int32_t)f->length, keys, 256);
    for (int k = 0; k < n; ++k) {
        int32_t i = mu_session_character_index(s, keys[k]);
        if (i < 0) continue;
        mu_rp_delete_character(&s->characters.records[i], s->place.world);
        s->characters.used[i] = 0;
        s->characters.store_open[i] = 0;
    }
    mu_session_touch(s, MU_DOMAIN_CHARACTERS);
    return MU_APPLY_DONE;
}

mu_apply characters_stores(mu_session *s, const mu_frame *f)
{
    if (f->length < 6 || f->length < 6u + 0x2fu * f->bytes[5]) return MU_APPLY_IGNORED;
    mu_rp_store stores[256];
    int n = mu_rp_store_records(f->bytes, (int32_t)f->length, stores, 256);
    for (int k = 0; k < n; ++k) {
        int32_t i = mu_session_character_index(s, stores[k].key);
        if (i < 0) continue;
        s->characters.store_open[i] = 1;
        memcpy(s->characters.store_title[i], stores[k].title, sizeof stores[k].title);
    }
    mu_session_touch(s, MU_DOMAIN_CHARACTERS);
    return MU_APPLY_DONE;
}

void mu_dom_characters_init(mu_session *s) { memset(&s->characters, 0, sizeof s->characters); }
void mu_dom_characters_free(mu_session *s) { (void)s; }
void mu_dom_characters_step(mu_session *s, const mu_sim *sim) { (void)s; (void)sim; }
#ifdef MU_SESSION_SEED
void mu_dom_characters_seed(mu_session *s, const struct mu_session_seed *seed) { (void)s; (void)seed; }
#endif

/* Projection widths are declared once alongside native members; addresses come
 * exclusively from the generated manifest. The skill word is sign-extended on restore. */
typedef struct binding { size_t raw, member, size; } binding;
static const binding bindings[] = {
#define MU_BIND(field, member, size) {MU_LAYOUT_CHARACTER_##field##_OFFSET, offsetof(mu_rp_character, member), size},
#include "characters_projection.def"
#undef MU_BIND
};

int mu_character_project(const mu_rp_character *c, uint8_t *raw, size_t size)
{
    if (!c || !raw || size < MU_LAYOUT_CHARACTER_SIZE) return 0;
    for (size_t i = 0; i < sizeof bindings / sizeof bindings[0]; ++i) {
        const binding *b = &bindings[i];
        memcpy(raw + b->raw, (const uint8_t *)c + b->member, b->size);
    }
    return 1;
}

int mu_character_restore(mu_rp_character *c, const uint8_t *raw, size_t size)
{
    if (!c || !raw || size < MU_LAYOUT_CHARACTER_SIZE) return 0;
    for (size_t i = 0; i < sizeof bindings / sizeof bindings[0]; ++i) {
        const binding *b = &bindings[i];
        memcpy((uint8_t *)c + b->member, raw + b->raw, b->size);
    }
    c->skill = (int16_t)mu_layout_CHARACTER_skill(raw, size, 0);
    return 1;
}

void mu_dom_characters_zones(const mu_session *s, mu_audit_zones *zs)
{
    const mu_dom_characters *d = &s->characters;
    /* Metadata cannot be written through a simulation lease. */
    mu_audit_add(zs, "characters.metadata", (const uint8_t *)d,
        (uint32_t)offsetof(mu_dom_characters, monsters),
        (uint32_t)(sizeof *d - offsetof(mu_dom_characters, monsters)), MU_ZONE_REPLICATED, "metadata");
    uint8_t motion[sizeof(mu_rp_character)] = {0};
    for (size_t i = 0; i < sizeof bindings / sizeof bindings[0]; ++i)
        for (size_t j = 0; j < MU_CHARACTER_LAYOUT.field_count; ++j) {
            const mu_layout_field *f = &MU_CHARACTER_FIELDS[j];
            if (f->offset == bindings[i].raw && f->zone == MU_LAYOUT_MOTION)
                memset(motion + bindings[i].member, 1, bindings[i].size);
        }
    for (int32_t k = 0; k < MU_CHARACTERS_MAX; ++k) {
        if (!d->used[k]) {
            mu_audit_add(zs, "characters.unused", (const uint8_t *)&d->records[k], 0,
                         sizeof d->records[k], MU_ZONE_REPLICATED, "unused");
            continue;
        }
        size_t at = 0;
        while (at < sizeof motion) {
            size_t end = at + 1;
            while (end < sizeof motion && motion[end] == motion[at]) ++end;
            mu_audit_add(zs, "characters.record", (const uint8_t *)&d->records[k], (uint32_t)at,
                (uint32_t)(end - at), motion[at] ? MU_ZONE_MOTION : MU_ZONE_REPLICATED, "projection");
            at = end;
        }
    }
}
