/* The server's skill packets and the managers they update (NATIVE-SKILL-002); see skill_list.h. */
#include "skill_list.h"

#include <string.h>

#ifndef MU_SKILL_MUTATION
#define MU_SKILL_MUTATION 0
#endif

static void emit(mu_skill_events *ev, int kind, int32_t arg)
{
    if (ev && ev->count < MU_SKILL_EVENTS) {
        ev->kind[ev->count] = kind;
        ev->arg[ev->count] = arg;
        ev->count++;
    }
}

/* ---- the master manager's table walks (GfxMgr +0x1f4) ------------------------------------------------- */

int32_t mu_skill_brand_of(const mu_skill_env *env, int32_t skill)
{
    return mu_skill_record_of(env, skill)->brand;
}

int32_t mu_skill_master_base(const mu_skill_env *env, int32_t skill)
{
    const mu_skill_record *r = mu_skill_record_of(env, skill);
    if (r->index == 0)
        return skill;
    int32_t last = skill;
    for (int32_t b = r->brand; b != 0 && b != 0x4b;) {
        const mu_skill_record *n = mu_skill_record_of(env, b);
        last = n->index;
        b = n->brand;
    }
    return last;
}

/* ---- the stamp manager -------------------------------------------------------------------------------- */

void mu_skill_stamp_init(mu_skill_stamp_mgr *s)
{
    memset(s, 0, sizeof *s);
    s->class_byte = -1;
    s->special_slot = -1;
}

mu_skill_stamp_entry *mu_skill_stamp_push(mu_skill_stamp_mgr *s, int special, int32_t base, int32_t learned)
{
    mu_skill_stamp_tab *t = special ? &s->special : &s->basic;
    if (t->count >= MU_SKILL_STAMP_MAX)
        return NULL;
    mu_skill_stamp_entry *e = &t->pool[t->count];
    e->base = base;
    e->learned = learned;
    e->imprint = 0;
    t->items[t->count++] = e;
    return e;
}

/* 0x01098644: the record's class map (+0x6c) holds the class index with a value above 0. */
static int class_allowed(const mu_skill_record *r, int32_t class_index)
{
    return class_index >= 0 && class_index < 16 && r->classes[class_index] > 0;
}

static void drop_tab(mu_skill_stamp_tab *t)
{
    t->count = 0;
}

/* 0x01095d30 / 0x0109630b: the class's skills of brand 0 by use type, in the table's key order. */
static void fill_basic(const mu_skill_env *env, mu_skill_stamp_mgr *s)
{
    int32_t ci = s->class_byte & 0xf;          /* 0x0095f5cc */
    const mu_skill_table *t = env ? env->table : NULL;
    if (!t)
        return;
    if (ci < 10) {
        for (size_t i = 0; i < t->count; i++) {
            const mu_skill_record *r = &t->records[i];
            if (r->index == 0 || r->index == 0x42 || r->index == 0x12a)
                continue;
            if (class_allowed(r, ci) && r->brand == 0 &&
                (r->use_type == 0 || r->use_type == 4 || r->use_type == 8 || r->use_type == 14))
                mu_skill_stamp_push(s, 0, r->index, 0);
        }
        return;
    }
    for (size_t i = 0; i < t->count; i++) {
        const mu_skill_record *r = &t->records[i];
        if (r->index == 0 || r->index == 0x42 || r->index == 0x12a)
            continue;
        if (class_allowed(r, ci) && r->brand == 0 && (r->use_type == 0 || r->use_type == 4))
            mu_skill_stamp_push(s, 0, r->index, 0);
    }
    for (size_t i = 0; i < t->count; i++) {
        const mu_skill_record *r = &t->records[i];
        if (r->index == 0 || r->index == 0x42)
            continue;
        if (class_allowed(r, ci) && r->brand == 0 && (r->use_type == 8 || r->use_type == 14))
            mu_skill_stamp_push(s, 0, r->index, 0);
    }
}

/* 0x01096710 = 0x01096840 (drop the special tab) + 0x0109672a (the class's skills of brand 0x4b). */
static void fill_special(const mu_skill_env *env, mu_skill_stamp_mgr *s)
{
    drop_tab(&s->special);
    int32_t ci = s->class_byte & 0xf;
    const mu_skill_table *t = env ? env->table : NULL;
    for (size_t i = 0; t && i < t->count; i++) {
        const mu_skill_record *r = &t->records[i];
        if (r->index != 0 && class_allowed(r, ci) && r->brand == 0x4b)
            mu_skill_stamp_push(s, 1, r->index, 0);
    }
}

static void clear_imprint(mu_skill_stamp_mgr *s)        /* 0x0109658a */
{
    for (int i = 0; i < s->basic.count; i++)
        s->basic.items[i]->imprint = 0;
    for (int i = 0; i < s->special.count; i++)
        s->special.items[i]->imprint = 0;
}

void mu_skill_stamp_reset(const mu_skill_env *env, mu_skill_stamp_mgr *s, int32_t class_byte)
{
    memset(s->edit, 0, sizeof s->edit);                  /* 0x01096d98 */
    memset(s->slots, 0, sizeof s->slots);                /* 0x01096db4 */
    if (s->class_byte != class_byte) {                   /* 0x01095ee9 */
        s->class_byte = class_byte;
        drop_tab(&s->basic);                             /* 0x01095ca2 (also the window's slots) */
        memset(s->edit, 0, sizeof s->edit);
        fill_basic(env, s);
    } else {
        for (int i = 0; i < s->basic.count; i++)         /* 0x0109664d */
            s->basic.items[i]->learned = 0;
        for (int i = 0; i < s->special.count; i++)
            s->special.items[i]->learned = 0;
        clear_imprint(s);
    }
    fill_special(env, s);
}

void mu_skill_stamp_add(const mu_skill_env *env, mu_skill_stamp_mgr *s, int32_t skill)
{
    int32_t base = mu_skill_master_base(env, skill);
    for (int i = 0; i < s->basic.count; i++) {
        mu_skill_stamp_entry *e = s->basic.items[i];
        if (e->base != base)
            continue;
        int below = 0;                                   /* the skill is already behind the learned one */
        if (skill != e->learned)
            for (int32_t c = e->learned; c != 0;) {
                c = mu_skill_brand_of(env, c);
                if (c == skill) {
                    below = 1;
                    break;
                }
            }
#if MU_SKILL_MUTATION == 12
        (void)below;
        e->learned = skill;
#else
        if (!below)
            e->learned = skill;
#endif
        return;
    }
    for (int i = 0; i < s->special.count; i++) {
        mu_skill_stamp_entry *e = s->special.items[i];
        if (e->base == base) {
            e->learned = skill;
            return;
        }
    }
}

void mu_skill_stamp_remove(const mu_skill_env *env, mu_skill_stamp_mgr *s, int32_t skill)
{
    int32_t base = mu_skill_master_base(env, skill);
    for (int i = 0; i < s->basic.count; i++) {
        mu_skill_stamp_entry *e = s->basic.items[i];
        if (e->base == base && e->learned == skill) {
            e->learned = 0;
            return;
        }
    }
    for (int i = 0; i < s->special.count; i++) {
        mu_skill_stamp_entry *e = s->special.items[i];
        if (e->base == base && e->learned == skill) {
            e->learned = 0;
            return;
        }
    }
}

static void imprint_tab(const mu_skill_env *env, mu_skill_stamp_mgr *s, mu_skill_stamp_tab *t)
{
    for (int i = 0; i < t->count; i++) {
        mu_skill_stamp_entry *e = t->items[i];
        if (!e)
            continue;
        int32_t m = mu_skill_record_of(env, e->learned)->mastery;
#if MU_SKILL_MUTATION == 13
        e->imprint = (uint8_t)(m == s->elemental || m == 6);
#else
        e->imprint = (uint8_t)((m == s->elemental && s->elemental != 0) || m == 6);
#endif
    }
}

void mu_skill_stamp_refresh(const mu_skill_env *env, mu_skill_stamp_mgr *s, int32_t elemental)
{
    s->elemental = elemental;
    clear_imprint(s);
    imprint_tab(env, s, &s->basic);
    imprint_tab(env, s, &s->special);
}

static mu_skill_stamp_entry *find_in(const mu_skill_stamp_tab *t, int32_t skill)    /* 0x01096b18 */
{
    for (int i = 0; i < t->count; i++)
        if (t->items[i]->base == skill || t->items[i]->learned == skill)
            return t->items[i];
    return NULL;
}

mu_skill_stamp_entry *mu_skill_stamp_find(const mu_skill_stamp_mgr *s, int32_t skill)
{
    mu_skill_stamp_entry *e = find_in(&s->basic, skill);
    return e ? e : find_in(&s->special, skill);
}

int mu_skill_stamp_set_key(mu_skill_stamp_mgr *s, int key, int32_t skill)
{
    if (key >= MU_SKILL_SLOTS)
        return 0;
    if (key == 0)
        key = 10;
    mu_skill_stamp_entry *e = mu_skill_stamp_find(s, skill);
    if (!e)
        return 0;
    s->edit[key - 1] = e;
    return 1;
}

void mu_skill_stamp_save(mu_skill_stamp_mgr *s)
{
    memcpy(s->slots, s->edit, sizeof s->slots);
    for (int i = 0; i < MU_SKILL_SLOTS; i++)
        s->saved[i] = s->slots[i] ? s->slots[i]->learned : 0;
}

void mu_skill_stamp_cancel(mu_skill_stamp_mgr *s)
{
    memcpy(s->edit, s->slots, sizeof s->edit);
}

int32_t mu_skill_stamp_slot_skill(const mu_skill_stamp_mgr *s, int window, int slot)
{
    if (slot >= MU_SKILL_SLOTS)
        return -1;
    const mu_skill_stamp_entry *e = window ? s->edit[slot] : s->slots[slot];
    if (!e)
        return -1;
    return e->learned ? e->learned : e->base;
}

int mu_skill_stamp_learned_index(const mu_skill_hero *hero, const mu_skill_stamp_entry *e)
{
    if (!e || e->learned == 0)
        return -1;
    for (int i = 0; i < hero->count; i++)
        if (hero->skills[i] == e->learned)
            return i;
    return -1;
}

/* ---- the hotkey manager ------------------------------------------------------------------------------- */

static int key_at(const mu_skill_keys *k, int32_t key, int *at)
{
    int lo = 0, hi = k->nlearned;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (k->learned[mid] < key)
            lo = mid + 1;
        else
            hi = mid;
    }
    *at = lo;
    return lo < k->nlearned && k->learned[lo] == key;
}

static void key_insert(mu_skill_keys *k, int32_t key)   /* std::map::insert: an existing key stays */
{
    int at;
    if (key_at(k, key, &at) || k->nlearned >= MU_SKILL_KEYS_MAX)
        return;
    memmove(k->learned + at + 1, k->learned + at, (size_t)(k->nlearned - at) * sizeof *k->learned);
    k->learned[at] = key;
    k->nlearned++;
}

static void key_erase(mu_skill_keys *k, int32_t key)
{
    int at;
    if (!key_at(k, key, &at))
        return;
    memmove(k->learned + at, k->learned + at + 1, (size_t)(k->nlearned - at - 1) * sizeof *k->learned);
    k->nlearned--;
}

int mu_skill_keys_has(const mu_skill_keys *k, int32_t skill)
{
    int at;
    return key_at(k, skill, &at);
}

void mu_skill_keys_select(const mu_skill_env *env, mu_skill_keys *k, int32_t skill, mu_skill_events *ev)
{
    if (skill == k->selected || skill == 0)
        return;
    if (!mu_skill_keys_has(k, skill)) {
        k->selected = 0;
        return;
    }
#if MU_SKILL_MUTATION == 14
    (void)env;
#else
    if (mu_skill_record_of(env, skill)->use_type == 3) {
        k->selected = 0;
        return;
    }
#endif
    k->selected = skill;
    emit(ev, MU_SKILL_EV_SELECT, skill);
}

void mu_skill_keys_follow(const mu_skill_env *env, mu_skill_keys *k, const mu_skill_hero *hero, mu_skill_events *ev)
{
    int32_t s = hero->skills[hero->current];
    if (k->selected != s)
        mu_skill_keys_select(env, k, s, ev);
}

void mu_skill_keys_rebuild(mu_skill_keys *k, const mu_skill_stamp_mgr *s)
{
    memset(k->has_slot, 0, sizeof k->has_slot);          /* 0x00a0826a */
    memset(k->slot, 0, sizeof k->slot);
    for (int i = 0; i < MU_SKILL_SLOTS; i++)
        if (s->slots[i]) {                                /* 0x01096927, 0x00a0827f */
            k->has_slot[i] = 1;
            k->slot[i] = s->slots[i]->learned;
        }
}

void mu_skill_keys_set(const mu_skill_env *env, mu_skill_keys *k, const mu_skill_stamp_mgr *s, const int32_t *skills,
                       int n, mu_skill_events *ev)
{
    k->nlearned = 0;                                      /* 0x00a0addf */
    for (int i = 0; i < n; i++)
        key_insert(k, mu_skill_record_of(env, skills[i])->index);
    emit(ev, MU_SKILL_EV_KEYS_ALL, n);
    mu_skill_keys_rebuild(k, s);
}

void mu_skill_keys_add(const mu_skill_env *env, mu_skill_keys *k, const mu_skill_stamp_mgr *s, int32_t skill,
                       mu_skill_events *ev)
{
    key_erase(k, skill);
    int32_t index = mu_skill_record_of(env, skill)->index;
    key_insert(k, index);
    emit(ev, MU_SKILL_EV_KEYS_ADD, index);
    mu_skill_keys_rebuild(k, s);
    emit(ev, MU_SKILL_EV_MASTER_ADD, skill);
}

void mu_skill_keys_remove(const mu_skill_env *env, mu_skill_keys *k, const mu_skill_stamp_mgr *s, int32_t skill,
                          mu_skill_events *ev)
{
    if (!mu_skill_keys_has(k, skill))
        return;
    key_erase(k, skill);
    if (k->selected == skill)
        mu_skill_keys_select(env, k, 0, ev);              /* select(0) does nothing: the selection stays */
    mu_skill_keys_rebuild(k, s);
}

void mu_skill_keys_hotkeys(const mu_skill_keys *k, mu_skill_hotkeys *out)
{
    out->selected = k->selected;
    for (int i = 0; i < MU_SKILL_SLOTS; i++)
        out->slots[i] = k->has_slot[i] ? k->slot[i] : 0;
}

/* ---- the packets -------------------------------------------------------------------------------------- */

static int32_t u16le(const uint8_t *p)
{
    return (int32_t)p[0] | (int32_t)p[1] << 8;
}

static void current_tail(mu_skill_hero *hero)       /* 0x01261ad3.. */
{
    uint8_t cur = hero->current;
    if (cur >= hero->count)
        cur = 0;
    if (hero->count == 1)
        cur = 0;
    if (hero->skills[cur] == 0)
        cur = 0;
    for (int k = 0; k < MU_SKILL_LIST; k++) {
        int32_t s = hero->skills[cur];
        if ((s >= 0x43 && s <= 0x48) || s == 0)
            cur = (uint8_t)(cur + 1);
        else
            break;
    }
    hero->current = cur;
}

int mu_skill_list_receive(mu_skill_world *w, const uint8_t *p, size_t size, mu_skill_events *ev)
{
    const mu_skill_env *env = w->env;
    mu_skill_hero *hero = w->hero;
    if (size < 6)
        return 0;
    int kind = p[5];
    if (kind == 0xff) {
        if (size < 7 + 3)
            return 0;
        int32_t skill = u16le(p + 8);
        int i = 0;
        for (; i < hero->count; i++)
            if (hero->skills[i] == skill) {
                hero->skills[i] = 0;
                break;
            }
        mu_skill_stamp_remove(env, w->stamp, skill);
        mu_skill_keys_remove(env, w->keys, w->stamp, skill, ev);
        if (hero->count == i + 1)
            for (int j = i - 1; j >= 0; j--)
                if (hero->skills[j] != 0) {
                    hero->count = (uint8_t)(j + 1);
                    break;
                }
    } else if (kind == 0xfe) {
        if (size < 7 + 3)
            return 0;
        int32_t skill = u16le(p + 8);
        int j = 0;
        int present = 0;
        for (; j < 0x96; j++)
            if (hero->skills[j] == skill) {
                present = 1;
                break;
            }
        if (!present)
            for (j = 0; j < 0x96; j++)
                if (hero->skills[j] == 0) {
                    hero->skills[j] = (uint16_t)skill;
                    break;
                }
        mu_skill_stamp_add(env, w->stamp, skill);
        mu_skill_keys_add(env, w->keys, w->stamp, skill, ev);
        if (hero->count == j)
            hero->count = (uint8_t)(j + 1);
        emit(ev, MU_SKILL_EV_TREE_ADD, skill);
        /* 0x00a002d4: the learned index of the skill's brand (-1 without one) */
        int32_t brand = mu_skill_record_of(env, skill)->brand;
        int at = -1;
        if (brand != 0)
            for (int i = 0; i < hero->count; i++)
                if (hero->skills[i] == brand) {
                    at = i;
                    break;
                }
        if ((int)hero->current == at)
            hero->current = (uint8_t)j;
    } else {
        if (size < 7 + 4 * (size_t)kind)
            return 0;
        memset(hero->skills, 0, sizeof hero->skills);
        int32_t vec[256];
        int k = 0;
        for (int i = 0; i < kind; i++) {
            int32_t skill = u16le(p + 7 + 4 * i + 1);
            vec[i] = skill;
#if MU_SKILL_MUTATION == 15
            hero->skills[k++] = (uint16_t)skill;
#else
            if (mu_skill_record_of(env, skill)->use_type != 3)
                hero->skills[k++] = (uint16_t)skill;
#endif
            mu_skill_stamp_add(env, w->stamp, skill);
        }
        mu_skill_keys_set(env, w->keys, w->stamp, vec, kind, ev);
        hero->count = (uint8_t)k;
    }
    mu_skill_stamp_refresh(env, w->stamp, hero->elemental);
    current_tail(hero);
    mu_skill_keys_follow(env, w->keys, hero, ev);
    return 1;
}

static int slot_shows(const mu_skill_stamp_mgr *s, int32_t skill)    /* 0x01096c83 */
{
    for (int i = 0; i < MU_SKILL_SLOTS; i++)
        if (skill == mu_skill_stamp_slot_skill(s, 0, i))
            return 1;
    return 0;
}

void mu_skill_stamp_after_save(mu_skill_world *w, mu_skill_events *ev)
{
    mu_skill_hero *hero = w->hero;
    mu_skill_stamp_mgr *s = w->stamp;
    int32_t current = hero->skills[hero->current];
    if (slot_shows(s, current))
        return;
    int found = 0;
    for (int i = 0; i < MU_SKILL_SLOTS; i++)
        if (s->edit[i]) {
            hero->current = (uint8_t)mu_skill_stamp_learned_index(hero, s->edit[i]);
            found = 1;
            break;
        }
    if (!found) {
        emit(ev, MU_SKILL_EV_USABLE, current);
        found = w->usable ? w->usable(w->usable_user, current) != 0 : 0;
    }
    if (!found)
        for (int i = 0; i < s->special.count; i++)
            if (mu_skill_record_of(w->env, s->special.items[i]->learned)->brand == 0x4b) {
                hero->current = (uint8_t)mu_skill_stamp_learned_index(hero, s->special.items[i]);
                break;
            }
    mu_skill_keys_follow(w->env, w->keys, hero, ev);
}

int mu_skill_keys_receive(mu_skill_world *w, const uint8_t *p, size_t size, mu_skill_events *ev)
{
    if (size < 4 + 2 * MU_SKILL_SLOTS)
        return 0;
    for (int i = 0; i < MU_SKILL_SLOTS; i++) {
        int32_t id = (int32_t)p[4 + 2 * i] << 8 | p[5 + 2 * i];
        if (id == 0xffff)
            continue;
        if (id == 0x12a)
            w->stamp->special_slot = i;
        else
            mu_skill_stamp_set_key(w->stamp, i, id);
    }
    mu_skill_stamp_save(w->stamp);
    mu_skill_stamp_after_save(w, ev);
    mu_skill_keys_rebuild(w->keys, w->stamp);
    return 1;
}

size_t mu_skill_list_packet(uint8_t *out, size_t cap, int kind, const int32_t *skills, int n)
{
    if (kind == 0xfe || kind == 0xff)
        n = n > 0 ? 1 : 0;
    if (n < 0 || n > 0xfd)
        n = 0xfd;
    size_t size = 7 + 4 * (size_t)n;
    if (size > cap || size > 0xff)
        return 0;
    memset(out, 0, size);
    out[0] = 0xc1;
    out[1] = (uint8_t)size;
    out[2] = 0xa0;
    out[3] = 0x20;
    out[5] = (uint8_t)(kind == 0xfe || kind == 0xff ? kind : n);
    for (int i = 0; i < n; i++) {
        out[7 + 4 * i] = (uint8_t)i;
        out[7 + 4 * i + 1] = (uint8_t)(skills[i] & 0xff);
        out[7 + 4 * i + 2] = (uint8_t)(skills[i] >> 8 & 0xff);
    }
    return size;
}

size_t mu_skill_keys_packet(uint8_t *out, size_t cap, const int32_t keys[MU_SKILL_SLOTS])
{
    size_t size = 4 + 2 * MU_SKILL_SLOTS;
    if (size > cap)
        return 0;
    out[0] = 0xc1;
    out[1] = (uint8_t)size;
    out[2] = 0xa0;
    out[3] = 0x03;
    for (int i = 0; i < MU_SKILL_SLOTS; i++) {
        int32_t id = keys[i] < 0 ? 0xffff : keys[i];
        out[4 + 2 * i] = (uint8_t)(id >> 8 & 0xff);
        out[5 + 2 * i] = (uint8_t)(id & 0xff);
    }
    return size;
}
