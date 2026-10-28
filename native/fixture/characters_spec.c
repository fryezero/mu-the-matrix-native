/* Synthetic --players specification parser and encodings. No state feed. */
#define _POSIX_C_SOURCE 200809L
#include "characters_demo.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* ---------------------------------------------------------------- the demo server's encodings */

static uint32_t level_code(uint8_t level)   /* the inverse of 0x01395741 */
{
    static const uint8_t table[8] = {0, 3, 5, 7, 9, 11, 13, 15};
    for (uint32_t i = 0; i < 8; ++i)
        if (table[i] == level)
            return i;
    return level >= 15 ? 7 : (uint32_t)((level + 1) / 2);
}

static int32_t wing_index(int32_t type)   /* the inverse of the wing switch's table */
{
    static const int16_t table[0x67] = {
        -1, 0x22e6, 0x22e7, 0x22e8, 0x22e9, 0x22ea, 0x22eb, 0x22ec, 0x230a, 0x230b, 0x230c, 0x230d, 0x230e, 0x230f,
        0x2310, 0x2311, 0x2317, 0x2318, 0x2368, 0x2369, 0x236a, 0x236b, 0x236c, 0x236d, 0x23ec, 0x23ed, 0x23ee, 0x23ef,
        0x23f0, 0x23f1, 0x2504, 0x23f3, 0x23f4, 0x23fc, 0x23f4, 0x23f0, 0x23fd, 0x23fe, 0x23ff, 0x2400, 0x2484, 0x2485,
        0x2486, 0x2487, 0x2488, 0x2489, 0x248a, 0x248b, 0x2484, 0x2485, 0x2486, 0x2487, 0x2488, 0x2489, 0x248a, 0x248b,
        0x24b9, 0x24bb, 0x24bb, 0x24c6, 0x24be, 0x24c0, 0x24c0, 0x24cf, 0x24d0, 0x24d0, 0x2380, 0x2381, 0x2382, 0x2384,
        0x2386, 0x2386, 0x2301, 0x237e, 0x237e, 0x2392, 0x2393, 0x2394, 0x2396, 0x2398, 0x2398, 0x239a, 0x239b, 0x239c,
        0x239d, 0x239e, 0x239f, 0x23a0, 0x23a1, 0x23a2, 0x23a3, 0x23a4, 0x23a5, 0x23a6, 0x23a7, 0x23a8, 0x23aa, 0x23aa,
        0x23ac, 0x34e6, 0x34e7, 0x34e9, 0x34eb};
    for (int32_t i = 1; i < 0x67; ++i)
        if (table[i] == type)
            return i;
    return 0;
}

void mu_world_players_encode_equipment(const mu_world_player_spec *s, uint8_t e[MU_RP_EQUIP_BYTES])
{
    memset(e, 0, MU_RP_EQUIP_BYTES);
    uint32_t codes[2];
    for (int k = 0; k < 2; ++k) {
        int32_t t = s->item_type[MU_RP_SLOT_WEAPON0 + k];
        codes[k] = t < 0 ? 0xfff : (uint32_t)(t - 0xae6) & 0xfff;
    }
    e[0] = (uint8_t)(codes[0] & 0xff);
    e[1] = (uint8_t)(codes[1] & 0xff);
    e[0xb] = (uint8_t)((codes[0] >> 8) << 4);
    e[0xc] = (uint8_t)((codes[1] >> 8) << 4);
    static const int32_t bases[5] = {0x18e6, 0x1ae6, 0x1ce6, 0x1ee6, 0x20e6};
    uint32_t part[5];
    for (int k = 0; k < 5; ++k) {
        int32_t t = s->item_type[MU_RP_SLOT_HELM + k];
        part[k] = (t < bases[k] || t >= bases[k] + 0x1ff) ? 0x1ff : (uint32_t)(t - bases[k]);
    }
    e[2] = (uint8_t)(((part[0] & 0xf) << 4) | (part[1] & 0xf));
    e[3] = (uint8_t)(((part[2] & 0xf) << 4) | (part[3] & 0xf));
    e[4] = (uint8_t)(((part[4] & 0xf) << 4) | (s->pet & 3));   /* e[4] & 3: the group-13 pet (3 none) */
    e[8] = (uint8_t)(((part[0] >> 4 & 1) << 7) | ((part[1] >> 4 & 1) << 6) | ((part[2] >> 4 & 1) << 5) |
                     ((part[3] >> 4 & 1) << 4) | ((part[4] >> 4 & 1) << 3));
    e[0xc] |= (uint8_t)(part[0] >> 5 & 0xf);
    e[0xd] = (uint8_t)(((part[1] >> 5 & 0xf) << 4) | (part[2] >> 5 & 0xf));
    e[0xe] = (uint8_t)(((part[3] >> 5 & 0xf) << 4) | (part[4] >> 5 & 0xf));
    uint32_t L = level_code(s->item_level[MU_RP_SLOT_WEAPON0]) | (level_code(s->item_level[MU_RP_SLOT_WEAPON1]) << 3);
    for (int k = 0; k < 5; ++k)
        L |= level_code(s->item_level[MU_RP_SLOT_HELM + k]) << (6 + 3 * k);
    e[5] = (uint8_t)(L >> 16);
    e[6] = (uint8_t)(L >> 8);
    e[7] = (uint8_t)L;
    for (int k = 0; k < 5; ++k) {
        e[9] |= (uint8_t)((s->excellent[MU_RP_SLOT_HELM + k] & 1) << (7 - k));
        e[0xa] |= (uint8_t)((s->ancient[MU_RP_SLOT_HELM + k] & 1) << (7 - k));
    }
    e[9] |= (uint8_t)(((s->excellent[MU_RP_SLOT_WEAPON0] & 1) << 2) | ((s->excellent[MU_RP_SLOT_WEAPON1] & 1) << 1));
    e[0xa] |= (uint8_t)(((s->ancient[MU_RP_SLOT_WEAPON0] & 1) << 2) | ((s->ancient[MU_RP_SLOT_WEAPON1] & 1) << 1));
    int32_t w = s->item_type[MU_RP_SLOT_WING] < 0 ? 0 : wing_index(s->item_type[MU_RP_SLOT_WING]);
    e[4] |= (uint8_t)(((w >> 6) & 3) << 2);   /* index bits 6..7 (the decode shifts e[4] & 0xc by 4) */
    e[8] |= (uint8_t)((w >> 3) & 7);
    e[0xf] = (uint8_t)(((w & 7) << 2) | (s->ride_state & 3));   /* the ride state 0x0129dc91 (NATIVE-HELPERS-001) */
    e[0xf] |= (uint8_t)(s->pet_ext & 0xe0);   /* the pet process's pet (NATIVE-HELPERS-002) */
    if (s->ride_state == 4)
        e[0x10] |= 1;
    e[0x11] = (uint8_t)(s->item_level[MU_RP_SLOT_WING] & 0xf);
}

static uint8_t packet_class(uint8_t class_byte)   /* the inverse of 0x0139ca62 */
{
    for (uint32_t v = 0; v < 256; ++v)
        if (mu_rp_class_byte((uint8_t)v) == class_byte)
            return (uint8_t)v;
    return 0;
}

int32_t mu_world_players_encode_viewport(const mu_world_players *p, const mu_world_player *q, int created,
                                         uint8_t *out, int32_t cap)
{
    (void)p;
    if (cap < 0x44)
        return 0;
    memset(out, 0, 0x44);
    const mu_world_player_spec *s = &q->spec;
    uint16_t key = (uint16_t)(q->key | (created ? 0x8000 : 0));
    out[0] = (uint8_t)(key >> 8);
    out[1] = (uint8_t)key;
    out[2] = (uint8_t)q->c.tile[0];
    out[3] = (uint8_t)q->c.tile[1];
    out[4] = packet_class(s->class_byte);
    mu_world_players_encode_equipment(s, out + 5);
    memcpy(out + 0x18, s->name, 10);
    out[0x22] = (uint8_t)q->c.target[0];
    out[0x23] = (uint8_t)q->c.target[1];
    out[0x24] = (uint8_t)((q->c.direction << 4) | (s->pk & 0xf));
    for (int i = 0; i < 3; ++i) {
        out[0x26 + 3 * i] = 0xff;
        out[0x27 + 3 * i] = 0xff;
    }
    out[0x30] = (uint8_t)(s->ride >> 8);
    out[0x31] = (uint8_t)s->ride;
    out[0x41] = 0xff;
    return 0x44;
}

/* ---------------------------------------------------------------- the players file */

static int parse_item(const char *v, int32_t *type, uint8_t *level, uint8_t *exc, uint8_t *anc)
{
    int g, i, l = 0, e = 0, a = 0;
    int n = sscanf(v, "%d:%d:%d:%d:%d", &g, &i, &l, &e, &a);
    if (n < 2 || g < 0 || g > 15 || i < 0 || i > 511)
        return 1;
    *type = 0xae6 + g * 512 + i;
    *level = (uint8_t)(l < 0 ? 0 : l > 15 ? 15 : l);
    *exc = (uint8_t)(e != 0);
    *anc = (uint8_t)(a != 0);
    return 0;
}

int mu_characters_parse_player(mu_world_player_spec *s, char *line, int number, char *error, size_t error_size)
{
    memset(s, 0, sizeof *s);
    for (int k = 0; k < MU_RP_SLOTS; ++k)
        s->item_type[k] = -1;
    s->guild = -1;
    s->ride = 0xffff;
    s->pet = 3;
    s->idle_steps = 40;
    s->die_step = -1;
    s->store_step = -1;
    s->respawn_steps = 400;
    s->direction = 1;
    char *save = NULL;
    char *tok = strtok_r(line, " \t", &save);
    if (!tok || strcmp(tok, "player")) {
        snprintf(error, error_size, "players line %d: expected \"player NAME ...\"", number);
        return 1;
    }
    tok = strtok_r(NULL, " \t", &save);
    if (!tok) {
        snprintf(error, error_size, "players line %d: missing name", number);
        return 1;
    }
    snprintf(s->name, sizeof s->name, "%s", tok);
    int has_at = 0;
    static const char *const slots[] = {"head", "helm", "armor", "pants", "gloves", "boots", "weapon0", "weapon1", "wing"};
    while ((tok = strtok_r(NULL, " \t", &save))) {
        char *eq = strchr(tok, '=');
        const char *v = eq ? eq + 1 : "";
        if (eq)
            *eq = 0;
        int matched = 0;
        for (int k = 1; k < 9; ++k)
            if (!strcmp(tok, slots[k])) {
                if (parse_item(v, &s->item_type[k], &s->item_level[k], &s->excellent[k], &s->ancient[k])) {
                    snprintf(error, error_size, "players line %d: %s needs GROUP:INDEX[:LEVEL[:EXC[:ANC]]]", number, tok);
                    return 1;
                }
                matched = 1;
            }
        if (matched)
            continue;
        if (!strcmp(tok, "class"))
            s->class_byte = (uint8_t)strtol(v, NULL, 0);
        else if (!strcmp(tok, "pk"))
            s->pk = (uint8_t)(atoi(v) & 0xf);
        else if (!strcmp(tok, "level"))
            s->level = (uint16_t)atoi(v);
        else if (!strcmp(tok, "guild"))
            s->guild = (int16_t)atoi(v);
        else if (!strcmp(tok, "party"))
            s->party = 1;
        else if (!strcmp(tok, "ride"))
            s->ride = (uint16_t)strtol(v, NULL, 0);
        else if (!strcmp(tok, "ride_state"))
            s->ride_state = (uint8_t)atoi(v);
        else if (!strcmp(tok, "raven"))   /* NATIVE-HELPERS-002 */
            s->raven = (uint8_t)atoi(v);
        else if (!strcmp(tok, "pet")) {
            static const struct { const char *name; uint8_t ext; } ext[] = {
                {"demon", 0x20}, {"spirit", 0x40}, {"skeleton", 0x60}, {"rudolph", 0x80}, {"panda", 0xa0}};
            s->pet = (uint8_t)(!strcmp(v, "angel") ? 0 : !strcmp(v, "imp") ? 1 : (atoi(v) & 3));
            for (size_t k = 0; k < sizeof ext / sizeof ext[0]; ++k)
                if (!strcmp(v, ext[k].name)) {   /* NATIVE-HELPERS-002: e[4] & 3 != 3 and the code in e[0xf] */
                    s->pet = 0;
                    s->pet_ext = ext[k].ext;
                }
        }
        else if (!strcmp(tok, "dir"))
            s->direction = (uint8_t)(atoi(v) & 0xf);
        else if (!strcmp(tok, "idle"))
            s->idle_steps = atoi(v);
        else if (!strcmp(tok, "die"))
            s->die_step = atoi(v);
        else if (!strcmp(tok, "respawn"))
            s->respawn_steps = atoi(v);
        else if (!strcmp(tok, "store"))
            s->store_step = atoi(v);
        else if (!strcmp(tok, "title")) {
            snprintf(s->store_title, sizeof s->store_title, "%s", v);
            for (char *c = s->store_title; *c; ++c)
                if (*c == '_')
                    *c = ' ';
        } else if (!strcmp(tok, "at")) {
            if (sscanf(v, "%d,%d", &s->start[0], &s->start[1]) != 2) {
                snprintf(error, error_size, "players line %d: at=X,Y", number);
                return 1;
            }
            has_at = 1;
        } else if (!strcmp(tok, "route")) {
            const char *q = v;
            while (*q && s->route_count < MU_WORLD_PLAYER_ROUTE) {
                int x, y, used = 0;
                if (sscanf(q, "%d,%d%n", &x, &y, &used) != 2) {
                    snprintf(error, error_size, "players line %d: route=X,Y;X,Y;...", number);
                    return 1;
                }
                s->route[s->route_count][0] = x & 0xff;
                s->route[s->route_count][1] = y & 0xff;
                ++s->route_count;
                q += used;
                if (*q == ';')
                    ++q;
            }
        } else {
            snprintf(error, error_size, "players line %d: unknown field \"%s\"", number, tok);
            return 1;
        }
    }
    if (!has_at) {
        snprintf(error, error_size, "players line %d: at=X,Y is required", number);
        return 1;
    }
    if (!s->store_title[0])
        snprintf(s->store_title, sizeof s->store_title, "%s's store", s->name);
    return 0;
}
