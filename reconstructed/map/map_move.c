/* The Move window's game side (NATIVE-MAP-001): the move manager, its sort,
 * the availability pass, the list rows and the click.  See map.h. */
#include "map.h"

#include <stdio.h>
#include <string.h>

/* Planted mistakes for scripts/validate_map.py --mutations (0: none). */
#ifndef MU_MAP_MUTATION
#define MU_MAP_MUTATION 0
#endif

static const mu_move_record *rec_of(mu_move_lookup_fn lookup, void *user, int32_t key)
{
    static const mu_move_record none = {0, 0, "", "", 0, 0, 0, 0, 0, 0, 0};   /* the table's default (+0x4c) */
    const mu_move_record *r = lookup ? lookup(user, key) : NULL;
    return r ? r : &none;
}

int mu_move_build(const int32_t *keys, int n, mu_move_lookup_fn lookup, void *user, mu_move_entry *out, int cap)
{
    int count = 0;
    for (int i = 0; i < n && count < cap; i++) {
        const mu_move_record *r = rec_of(lookup, user, keys[i]);
        mu_move_entry e;
        memset(&e, 0, sizeof e);
        e.key = keys[i];
        e.key2 = keys[i];
        e.order = i;
        e.x44 = MU_MAP_MUTATION == 5 ? r->x48 : r->x44;
        e.x48 = MU_MAP_MUTATION == 5 ? r->x44 : r->x48;
        out[count++] = e;
    }
    return count;
}

/* ---- MSVC std::sort (_Sort 0x00d3c25a; the VS2012-era <algorithm>), on 0x18-byte entries ---------------- */

typedef int (*less_fn)(const mu_move_entry *a, const mu_move_entry *b);

static int less_order(const mu_move_entry *a, const mu_move_entry *b) { return a->order < b->order; }   /* 0x00d3b651 */
static int less_x44(const mu_move_entry *a, const mu_move_entry *b) { return a->x44 < b->x44; }         /* 0x00d3b66a */
static int less_x48(const mu_move_entry *a, const mu_move_entry *b) { return a->x48 < b->x48; }         /* 0x00d3b683 */

static void swap_e(mu_move_entry *a, mu_move_entry *b)
{
    mu_move_entry t = *a;
    *a = *b;
    *b = t;
}

static void insertion_sort(mu_move_entry *first, mu_move_entry *last, less_fn lt)
{
    if (first == last)
        return;
    for (mu_move_entry *next = first; ++next != last;) {
        mu_move_entry *next1 = next;
        mu_move_entry val = *next;
        if (lt(&val, first)) {
            memmove(first + 1, first, (size_t)(next - first) * sizeof *first);
            *first = val;
        } else {
            for (mu_move_entry *first1 = next1; lt(&val, --first1); next1 = first1)
                *next1 = *first1;
            *next1 = val;
        }
    }
}

static void med3(mu_move_entry *first, mu_move_entry *mid, mu_move_entry *last, less_fn lt)
{
    if (lt(mid, first))
        swap_e(mid, first);
    if (lt(last, mid)) {
        swap_e(last, mid);
        if (lt(mid, first))
            swap_e(mid, first);
    }
}

static void median(mu_move_entry *first, mu_move_entry *mid, mu_move_entry *last, less_fn lt)
{
    if (40 < last - first) {
        ptrdiff_t step = (last - first + 1) / 8;
        med3(first, first + step, first + 2 * step, lt);
        med3(mid - step, mid, mid + step, lt);
        med3(last - 2 * step, last - step, last, lt);
        med3(first + step, mid, last - step, lt);
    } else {
        med3(first, mid, last, lt);
    }
}

static void unguarded_partition(mu_move_entry *first, mu_move_entry *last, less_fn lt, mu_move_entry **pf,
                                mu_move_entry **pl)
{
    mu_move_entry *mid = first + (last - first) / 2;
    median(first, mid, last - 1, lt);
    mu_move_entry *pfirst = mid, *plast = pfirst + 1;
    while (first < pfirst && !lt(pfirst - 1, pfirst) && !lt(pfirst, pfirst - 1))
        --pfirst;
    while (plast < last && !lt(plast, pfirst) && !lt(pfirst, plast))
        ++plast;
    mu_move_entry *gfirst = plast, *glast = pfirst;
    for (;;) {
        for (; gfirst < last; ++gfirst) {
            if (lt(pfirst, gfirst))
                ;
            else if (lt(gfirst, pfirst))
                break;
            else if (plast++ != gfirst)
                swap_e(plast - 1, gfirst);
        }
        for (; first < glast; --glast) {
            if (lt(glast - 1, pfirst))
                ;
            else if (lt(pfirst, glast - 1))
                break;
            else if (--pfirst != glast - 1)
                swap_e(pfirst, glast - 1);
        }
        if (glast == first && gfirst == last) {
            *pf = pfirst;
            *pl = plast;
            return;
        }
        if (glast == first) {
            if (plast != gfirst)
                swap_e(pfirst, plast);
            ++plast;
            swap_e(pfirst++, gfirst++);
        } else if (gfirst == last) {
            if (--glast != --pfirst)
                swap_e(glast, pfirst);
            swap_e(pfirst, --plast);
        } else {
            swap_e(gfirst++, --glast);
        }
    }
}

/* make_heap / sort_heap of the same header (reached only when the partition depth budget runs out). */
static void adjust_heap(mu_move_entry *first, ptrdiff_t hole, ptrdiff_t bottom, mu_move_entry val, less_fn lt)
{
    ptrdiff_t top = hole, idx = 2 * hole + 2;
    for (; idx < bottom; idx = 2 * idx + 2) {
        if (lt(first + idx, first + (idx - 1)))
            --idx;
        first[hole] = first[idx];
        hole = idx;
    }
    if (idx == bottom) {
        first[hole] = first[bottom - 1];
        hole = bottom - 1;
    }
    for (idx = (hole - 1) / 2; top < hole && lt(first + idx, &val); idx = (hole - 1) / 2) {
        first[hole] = first[idx];
        hole = idx;
    }
    first[hole] = val;
}

static void heap_sort(mu_move_entry *first, mu_move_entry *last, less_fn lt)
{
    ptrdiff_t bottom = last - first;
    for (ptrdiff_t hole = bottom / 2; 0 < hole;) {
        --hole;
        adjust_heap(first, hole, bottom, first[hole], lt);
    }
    for (; 1 < last - first; --last) {
        mu_move_entry val = last[-1];
        last[-1] = *first;
        adjust_heap(first, 0, last - 1 - first, val, lt);
    }
}

static void msvc_sort(mu_move_entry *first, mu_move_entry *last, ptrdiff_t ideal, less_fn lt)
{
    ptrdiff_t count;
    for (; 32 < (count = last - first) && 0 < ideal;) {
        mu_move_entry *mf, *ml;
        unguarded_partition(first, last, lt, &mf, &ml);
        ideal /= 2, ideal += ideal / 2;
        if (mf - first < last - ml) {
            msvc_sort(first, mf, ideal, lt);
            first = ml;
        } else {
            msvc_sort(ml, last, ideal, lt);
            last = mf;
        }
    }
    if (32 < count)
        heap_sort(first, last, lt);
    else if (1 < count)
        insertion_sort(first, last, lt);
}

void mu_move_sort(mu_move_entry *entries, int n, int32_t order)
{
    less_fn lt = order == 0 ? less_order : order == 1 ? less_x44 : order == 2 ? less_x48 : NULL;
    if (!lt || n < 2)
        return;
    if (MU_MAP_MUTATION == 6)
        insertion_sort(entries, entries + n, lt);   /* a stable sort instead of std::sort */
    else
        msvc_sort(entries, entries + n, n, lt);
}

/* ---- strife flags, availability, rows ---------------------------------------------------------------------- */

const int32_t mu_move_strife_keys_5[5] = {0x1c, 0x1d, 0x21, 0x2a, 0x2d};

void mu_move_set_strife(mu_move_entry *entries, int n, const int32_t *keys, int nkeys, mu_move_lookup_fn lookup,
                        void *user)
{
    for (int i = 0; i < n; i++)          /* 0x00d3b290 */
        entries[i].strife = 0;
    for (int k = 0; k < nkeys; k++) {    /* 0x00d3b239(record id, 1): the first entry whose +8 is the id */
        int32_t id = rec_of(lookup, user, keys[k])->id;
        for (int i = 0; i < n; i++)
            if (entries[i].order == id) {
                entries[i].strife = 1;
                break;
            }
    }
}

int32_t mu_move_required_zen(const mu_move_record *r, const mu_move_hero *hero)
{
    return hero->pk_level > (MU_MAP_MUTATION == 7 ? 3 : 4) ? (int32_t)((uint32_t)r->zen * 0x32u) : r->zen;
}

static int has(const char *hay, const char *needle)   /* std::string::find(needle, 0) != npos */
{
    if (!needle)
        needle = "";
    return strstr(hay ? hay : "", needle) != NULL;
}

static const char *gt(mu_move_text_fn text, void *user, int32_t index)
{
    const char *s = text ? text(user, index) : NULL;
    return s ? s : "";
}

void mu_move_availability(mu_move_entry *entries, int n, const mu_move_hero *hero, mu_move_lookup_fn lookup,
                          mu_move_text_fn text, void *user)
{
    for (int i = 0; i < n; i++) {
        mu_move_entry *e = &entries[i];
        e->enabled = 0;
        e->clicked = 0;
        const mu_move_record *r = rec_of(lookup, user, e->key2);
        const char *name = r->name ? r->name : "";
        if (hero->level >= r->min_level && hero->zen >= mu_move_required_zen(r, hero)) {
            if (has(name, gt(text, user, 0x37))) {
                int32_t t = hero->helper_type;
                if (hero->wings_slot || t == 0x1a03 || t == 0x1a04 || t == 0x28f7 || t == 0x1a25 ||
                    hero->helper_flies || t == 0x1a02)
                    e->enabled = 1;
                else
                    e->enabled = hero->flying > 0;
            } else {
                const char *atlans = gt(text, user, 0x25);
                if (!strncmp(name, atlans, strlen(atlans)))
                    e->enabled = 1;
                else if (has(name, gt(text, user, 0x29d)))
                    e->enabled = hero->kalima == 1;
                else if (hero->server_flag == 1 && has(name, gt(text, user, 0xa7e)))
                    e->enabled = 0;
                else
                    e->enabled = 1;
            }
            for (int k = 0; k < 8; k++) {
                char buf[0x100];
                snprintf(buf, sizeof buf, "%s%d", gt(text, user, 0x3a), k);
                if (has(name, buf)) {
                    e->enabled = hero->event_a == 1 || hero->event_b == 1;
                    break;
                }
            }
        }
        if (e->enabled == 1 && e->strife == 1 && hero->strife_ok == 0)
            e->enabled = 0;
    }
}

void mu_move_row_make(const mu_move_entry *e, int32_t index, const mu_move_hero *hero, int checked,
                      mu_move_lookup_fn lookup, mu_move_text_fn text, void *user, mu_move_row *out)
{
    memset(out, 0, sizeof *out);
    const mu_move_record *r = rec_of(lookup, user, e->key2);
    out->order_idx = index;
    snprintf(out->strife, sizeof out->strife, "%s", e->strife == 1 ? gt(text, user, MU_MOVE_TEXT_STRIFE + (MU_MAP_MUTATION == 8)) : "");
    snprintf(out->map, sizeof out->map, "%s", r->name ? r->name : "");
    snprintf(out->level, sizeof out->level, "%d", (int)r->min_level);              /* _itoa(v, buf, 10) */
    snprintf(out->zen, sizeof out->zen, "%d", (int)mu_move_required_zen(r, hero));
    out->checked = checked != 0;
    out->disabled = !e->enabled;
    out->map_idx = e->key2;
}

int mu_move_is_favourite(const mu_move_favourite favs[5], int32_t key)
{
    for (int i = 0; i < 5; i++)
        if (favs[i].key == (uint16_t)key)
            return 1;
    return 0;
}

int mu_move_special(int32_t current_world, int32_t key)
{
    return current_world == 0x1e || current_world == 0x22 || current_world == 0x4f || key == 0x18 || key == 0x2c ||
           key == (MU_MAP_MUTATION == 9 ? 0x31 : 0x30);
}

int mu_move_request_packet(uint32_t move_key, uint16_t key, uint8_t tail, uint8_t *out, size_t cap)
{
    const uint8_t p[11] = {0xc1, 11, 0x8e, 2, (uint8_t)move_key, (uint8_t)(move_key >> 8), (uint8_t)(move_key >> 16),
                           (uint8_t)(move_key >> 24), (uint8_t)key, (uint8_t)(key >> 8), tail};
    if (cap < sizeof p)
        return 0;
    memcpy(out, p, sizeof p);
    return (int)sizeof p;
}

void mu_move_click(mu_move_entry *entries, int n, int32_t index, int32_t current_world, int helper_running,
                   uint32_t move_key, mu_move_click_result *out)
{
    memset(out, 0, sizeof *out);
    if (index < 0 || index >= n)   /* 0x00d3aff7: the manager's default entry (+0x10), never enabled */
        return;
    mu_move_entry *e = &entries[index];
    if (!e->enabled)
        return;
    e->clicked = 1;
    if (mu_move_special(current_world, e->key2)) {
        out->helper_stop = 1;
        out->helper_packet = helper_running != 0;
    }
    out->accepted = 1;
    out->packet_length = mu_move_request_packet(move_key, (uint16_t)e->key2, 0xff, out->packet, sizeof out->packet);
}
