/* Other players in the walk-around world (NATIVE-PLAYERS-001); see mu_world_players.h. */
#define _POSIX_C_SOURCE 200809L
#include "mu_world_players.h"

#include <ctype.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/actors/actors.h"
#include "../../reconstructed/movement/client_movement.h"
#include "../../reconstructed/model-codec/character.h"
#include "../../reconstructed/objects/object_render.h"
#include "mu_combat.h"
#include "mu_lang.h"
#include "mu_names.h"
#include "mu_world_names.h"

#define PLAYER_OBJECT_LIGHT 0.2f   /* the object light of a character object (NATIVE-LIGHT-001 live read) */

static void log_line(mu_world_players *p, const char *text)
{
    if (p->log_count < (int32_t)(sizeof p->log / sizeof p->log[0]))
        snprintf(p->log[p->log_count++], sizeof p->log[0], "%s", text);
}

static uint32_t demo_rand(mu_world_players *p)
{
    p->rng = p->rng * 1103515245u + 12345u;
    return (p->rng >> 8) & 0xffffffu;
}

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

static int parse_player(mu_world_player_spec *s, char *line, int number, char *error, size_t error_size)
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

/* ---------------------------------------------------------------- models */

static int is_armour(int32_t type)
{
    return type >= 0x18e6 && type < 0x22e6;
}

static int item_file(mu_world_players *p, int32_t type, char *path, size_t cap)
{
    if (type >= 0x3700 && type < 0x3700 + 5 * 0x50) {   /* a class part */
        char name[64];
        if (!mu_character_part_file((uint32_t)type, name, sizeof name))
            return 1;
        snprintf(path, cap, "%s/Data/Player/%s", p->root, name);
        return 0;
    }
    if (!p->has_table)
        return 1;
    mu_item item;
    if (mu_item_model(&p->item_table, type, &item) != 1)
        return 1;
    snprintf(path, cap, "%s/%s%s", p->root, item.folder, item.file);
    for (char *c = path; *c; ++c)
        if (*c == '\\')
            *c = '/';
    return 0;
}

static int32_t weapon_kind(mu_world_players *p, int32_t type)
{
    if (type < 0xae6)
        return MU_WEAPON_NONE;
    int32_t group = (type - 0xae6) / 512, index = (type - 0xae6) % 512;
    int two_handed = 0, kind = 0;
    if (p->has_table) {
        mu_item item;
        if (mu_item_find(&p->item_table, (uint32_t)(type - 0xae6), &item) == 0) {
            two_handed = item.attributes.two_handed != 0;
            kind = item.attributes.kind_b;
        }
    }
    switch (group) {
    case 0: case 1: case 2: return two_handed ? MU_WEAPON_TWO_HAND : MU_WEAPON_ONE_HAND;
    case 3: return MU_WEAPON_SPEAR;
    case 4: return (kind == 9 || (!p->has_table && index >= 8 && index <= 14)) ? MU_WEAPON_CROSSBOW : MU_WEAPON_BOW;
    case 5: return two_handed ? MU_WEAPON_TWO_HAND_STAFF : MU_WEAPON_STAFF;
    default: return MU_WEAPON_NONE;
    }
}

/* Loads the part / weapon / wing models that ChangeCharacterExt's slots name. */
static void load_parts(mu_world_players *p, mu_world_player *q)
{
    char path[2048], error[512];
    static const int item_of[9] = {-1, 1, 2, 3, 4, 5, MU_CHARACTER_WEAPON_ITEM(0), MU_CHARACTER_WEAPON_ITEM(1),
                                   MU_CHARACTER_WING_ITEM};
    char missing[112] = "";
    for (int k = 1; k < 9; ++k) {
        int32_t type = q->c.slots[k].type;
        int item = item_of[k];
        if (type < 0 || item_file(p, type, path, sizeof path)) {
            mu_character_set_item(&q->model, item, NULL, 1, error, sizeof error);
            continue;
        }
        FILE *f = fopen(path, "rb");
        if (!f) {
            size_t n = strlen(missing);
            snprintf(missing + n, sizeof missing - n, "%s%s", n ? " " : "", strrchr(path, '/') + 1);
            mu_character_set_item(&q->model, item, NULL, 1, error, sizeof error);
            continue;
        }
        fclose(f);
        if (mu_character_set_item(&q->model, item, path, p->no_textures, error, sizeof error)) {
            log_line(p, error);
            continue;
        }
        mu_character_item *it = &q->model.items[item];
        if (!p->no_textures && is_armour(type) && it->textures.missing) {
            /* viewer choice (as NATIVE-ITEMS-001): armour bitmaps live in Data/Player */
            char player[2048], directory[2048];
            snprintf(player, sizeof player, "%s/Data/Player", p->root);
            mu_path_directory(path, directory, sizeof directory);
            mu_textures_free(&it->textures);
            mu_textures_load_with_effects(&it->textures, &it->bmd, player, directory);
        }
    }
    q->weapon_kind = weapon_kind(p, q->c.slots[MU_RP_SLOT_WEAPON0].type);
    if (missing[0]) {
        char text[112];
        snprintf(text, sizeof text, "%s: missing %.90s", q->spec.name, missing);
        log_line(p, text);
    }
}

static void place_model(mu_world_players *p, mu_world_player *q)
{
    mu_character *m = &q->model;
    float light[3] = {1.0f, 1.0f, 1.0f};
    if (p->map) {
        mu_obj_terrain_light(p->map->light, 6, 1, q->c.position[0], q->c.position[1], light);
        for (int k = 0; k < 3; ++k)
            light[k] += PLAYER_OBJECT_LIGHT;
    }
    for (int k = 0; k < 3; ++k) {
        m->params.position[k] = q->c.position[k] + q->place_offset[k];   /* the rider lift 0x0103da5c */
        m->params.angles[k] = q->c.angle[k];
        m->params.light[k] = light[k];
    }
}

/* ---------------------------------------------------------------- the name plates */

static mu_hn_character *plate_character(mu_world_players *p, mu_world_player *q)
{
    if (!p->names)
        return NULL;
    mu_hn_character *c = mu_names_character(&p->names->names, q->key);
    if (!c)
        return NULL;
    c->kind = MU_HN_PLAYER;
    c->class_byte = q->c.class_byte;
    c->pk = q->c.pk;
    c->level = q->c.level;
    c->guild = q->c.guild;
    c->guild_relation = (uint8_t)(q->c.guild >= 0 && q->c.guild == p->hero_guild ? 1 : 0);   /* DEMO */
    c->wing = q->c.slots[MU_RP_SLOT_WING].type;
    c->ride = q->c.helper;
    c->monster_class = -1;
    c->live = q->c.live;
    c->max_hp = 100;
    c->hp = q->c.dead ? 0 : 100;   /* DEMO */
    snprintf(c->name, sizeof c->name, "%s", q->c.name);
    memcpy(c->position, q->c.position, sizeof c->position);
    return c;
}

static void guild_lookup(void *context, int32_t index, const char **name, const char **second)
{
    mu_names *n = context;
    const mu_world_players *p = n->user;
    *name = (p && index >= 0 && index < MU_WORLD_PLAYER_GUILDS) ? p->guild_names[index] : "";
    *second = "";
}

static int party_lookup(void *context, const char *name, int32_t *hp)
{
    mu_names *n = context;
    const mu_world_players *p = n->user;
    if (!p)
        return 0;
    for (int32_t i = 0; i < p->count; ++i)
        if (p->list[i].spec.party && !strcmp(p->list[i].spec.name, name)) {
            *hp = p->list[i].c.dead ? 0 : 100;   /* DEMO: the party window's HP percentage */
            return 1;
        }
    return 0;
}

void mu_world_players_attach(mu_world_players *p, struct mu_world_names *names, const struct mu_combat *combat)
{
    p->names = names;
    p->combat = combat;
    if (names) {
        names->names.user = p;
        names->names.env.guild = guild_lookup;
        names->names.env.party_hp = party_lookup;
    }
}

/* ---------------------------------------------------------------- loading */

static int load_player(mu_world_players *p, mu_world_player *q, const mu_world_player_spec *s, char *error,
                       size_t error_size)
{
    memset(q, 0, sizeof *q);
    q->spec = *s;
    q->key = p->key0 + (int32_t)(q - p->list);
    char player[2048];
    snprintf(player, sizeof player, "%s/Data/Player/Player.bmd", p->root);
    mu_model_params params;
    mu_model_scene_params(&params);
    params.world = p->map->world;
    if (mu_character_init(&q->model, player, &params, error, error_size))
        return 1;
    q->has_model = 1;
    mu_character_apply_player_speeds(&q->model);
    q->model.params.world_items = 1;
    q->model.params.scale = 0.9f;    /* the character create 0x0137d9dd */
    /* the record before the viewport: not live, nothing to draw */
    mu_rp_character_create(&q->c, (int16_t)q->key, MU_RP_PLAYER_MODEL, (uint8_t)s->start[0], (uint8_t)s->start[1], 0.0f);
    q->c.live = 0;
    q->c.direction = s->direction;
    q->c.level = s->level;
    q->c.guild = s->guild;
    q->c.helper = s->ride;
    q->c.position[2] = mu_request_terrain_height(p->map->height, p->map->attributes, p->map->water_height, 6,
                                                 q->c.position[0], q->c.position[1]);
    q->wait = 10 + (int32_t)(demo_rand(p) % 30u);
    q->loaded = 1;
    return 0;
}

int mu_world_players_load_text(mu_world_players *p, const char *root, mu_walk *walk, const mu_world *map,
                               const char *text, int no_textures, char *error, size_t error_size)
{
    memset(p, 0, sizeof *p);
    snprintf(p->root, sizeof p->root, "%s", root);
    p->walk = walk;
    p->map = map;
    p->no_textures = no_textures;
    p->view_range = 12;
    p->key0 = 0x200;
    p->hero_guild = 0;
    p->rng = 0x9a7e2026u;
    snprintf(p->guild_names[0], sizeof p->guild_names[0], "Matrix");
    snprintf(p->guild_names[1], sizeof p->guild_names[1], "Lions");
    snprintf(p->guild_names[2], sizeof p->guild_names[2], "Spiders");
    snprintf(p->guild_names[3], sizeof p->guild_names[3], "Unicorn");
    char path[2048];
    snprintf(path, sizeof path, "%s/Data/Local/item.bmd", root);
    if (mu_data_load(path, NULL, &p->item_table) == 0 && p->item_table.result.status == 0)
        p->has_table = 1;
    else {
        snprintf(path, sizeof path, "%s/Data/Local/Item.bmd", root);
        if (mu_data_load(path, NULL, &p->item_table) == 0 && p->item_table.result.status == 0)
            p->has_table = 1;
    }
    int number = 0;
    const char *q = text;
    while (*q) {
        const char *end = strchr(q, '\n');
        size_t n = end ? (size_t)(end - q) : strlen(q);
        char line[1024];
        if (n >= sizeof line)
            n = sizeof line - 1;
        memcpy(line, q, n);
        line[n] = 0;
        q += n + (end ? 1 : 0);
        ++number;
        char *hash = strchr(line, '#');
        if (hash)
            *hash = 0;
        char *s = line;
        while (isspace((unsigned char)*s))
            ++s;
        if (!*s)
            continue;
        if (p->count == MU_WORLD_PLAYERS_MAX) {
            snprintf(error, error_size, "players: more than %d players", MU_WORLD_PLAYERS_MAX);
            mu_world_players_free(p);
            return 1;
        }
        mu_world_player_spec spec;
        if (parse_player(&spec, s, number, error, error_size) ||
            load_player(p, &p->list[p->count], &spec, error, error_size)) {
            mu_world_players_free(p);
            return 1;
        }
        ++p->count;
        char t[112];
        snprintf(t, sizeof t, "player %s class %#x pk %d at %d,%d route %d", spec.name, spec.class_byte, spec.pk,
                 spec.start[0], spec.start[1], spec.route_count);
        log_line(p, t);
    }
    return 0;
}

int mu_world_players_load(mu_world_players *p, const char *root, mu_walk *walk, const mu_world *map, const char *file,
                          int no_textures, char *error, size_t error_size)
{
    FILE *f = fopen(file, "rb");
    if (!f) {
        memset(p, 0, sizeof *p);
        snprintf(error, error_size, "cannot open players file %s", file);
        return 1;
    }
    char *text = calloc(1, 1 << 16);
    size_t n = text ? fread(text, 1, (1 << 16) - 1, f) : 0;
    fclose(f);
    if (!text) {
        memset(p, 0, sizeof *p);
        snprintf(error, error_size, "out of memory");
        return 1;
    }
    text[n] = 0;
    int status = mu_world_players_load_text(p, root, walk, map, text, no_textures, error, error_size);
    free(text);
    return status;
}

void mu_world_players_free(mu_world_players *p)
{
    for (int32_t i = 0; i < p->count; ++i)
        if (p->list[i].has_model)
            mu_character_free(&p->list[i].model);
    if (p->has_table)
        mu_data_free(&p->item_table);
    memset(p, 0, sizeof *p);
}

/* ---------------------------------------------------------------- the client's movement services */

typedef struct step_context {
    mu_world_players *p;
    mu_world_player *q;
} step_context;

static int cb_path(void *context, int32_t sx, int32_t sy, int32_t tx, int32_t ty, mu_rp_path *path, int32_t mode)
{
    step_context *s = context;
    ++s->p->path_calls;
    mu_client_path cp;
    memcpy(&cp, path, sizeof cp);
    int found = mu_path_finding2(&s->p->walk->finder, sx, sy, tx, ty, &cp, 0.0f, mode, 0) == 1;
    if (found)
        memcpy(path, &cp, sizeof *path);
    return found;
}

static int cb_move_path(void *context, mu_rp_character *c)
{
    (void)context;
    return mu_move_path((mu_path *)&c->path, c->tile, c->position, c->angle, 1);
}

static void set_action(mu_world_player *q, int32_t action, float speed)
{
    if (mu_move_set_action(&q->c.action, &q->c.prior_action, &q->frame, &q->prior_frame,
                           q->model.player_bmd.action_count, action))
        q->action_changed = 1;
    q->play_speed = speed;
}

static void cb_set_action(void *context, mu_rp_character *c, int32_t action)
{
    step_context *s = context;
    (void)c;
    set_action(s->q, action, mu_character_action_speed(&s->q->model, (uint16_t)action));
}

static void run_input(mu_world_players *p, mu_world_player *q, mu_run_input *in)
{
    memset(in, 0, sizeof *in);
    in->stunned = q->c.stunned;
    in->safe_zone = q->safe_zone;
    in->class_byte = q->c.class_byte;
    in->class_value = q->c.class_word;
    in->world = p->map->world;
    in->gloves_type = q->c.slots[MU_RP_SLOT_GLOVES].type;
    in->boots_type = q->c.slots[MU_RP_SLOT_BOOTS].type;
    in->gloves_level = (int8_t)q->c.slots[MU_RP_SLOT_GLOVES].level;
    in->boots_level = (int8_t)q->c.slots[MU_RP_SLOT_BOOTS].level;
    in->mounted_item = 0;
    in->safe_zone_keeps_run = q->riding;   /* 0x0106bdb7 (NATIVE-HELPERS-001) */
}

void mu_world_players_set_action(mu_world_players *p, int32_t i, int32_t action)
{
    if (i < 0 || i >= p->count)
        return;
    mu_world_player *q = &p->list[i];
    set_action(q, action, mu_character_action_speed(&q->model, (uint16_t)action));
}

static void cb_set_walk(void *context, mu_rp_character *c)
{
    step_context *s = context;
    mu_world_player *q = s->q;
    mu_run_input in;
    run_input(s->p, q, &in);
    q->run = mu_player_run_counter(&in, q->run);
    float speed;
    int32_t action;
    /* riding (0x0106bdb7): the rider action 0x0106c382(c, run < 20 ? 1 : 2) (NATIVE-HELPERS-001) */
    if (q->riding && s->p->ride_hook && s->p->ride_hook(s->p->ride_context, (int32_t)(q - s->p->list), q->run < 0x14 ? 1 : 2))
        return;
    if (q->weapon_kind == MU_WEAPON_NONE)
        action = mu_player_walk_action(c->class_byte, q->run, &speed);
    else {   /* static table of the armed walk actions (NATIVE-ACTOR-001); the run threshold as unarmed */
        action = q->run >= 40 ? mu_player_walk_action(c->class_byte, q->run, &speed)
                              : mu_player_pose_action(MU_POSE_WALK, q->weapon_kind, c->class_byte, s->p->map->world);
        speed = mu_character_action_speed(&q->model, (uint16_t)action);
    }
    set_action(q, action, speed);
}

static void cb_set_stop(void *context, mu_rp_character *c)
{
    step_context *s = context;
    mu_world_player *q = s->q;
    q->run = mu_player_stop_run_counter(q->keeps_run, q->run);
    if (q->riding && s->p->ride_hook && s->p->ride_hook(s->p->ride_context, (int32_t)(q - s->p->list), 0)) {
        ++q->arrivals;   /* the rider action 0x0106c382(c, 0) (NATIVE-HELPERS-001) */
        return;
    }
    int32_t action;
    float speed;
    if (q->weapon_kind == MU_WEAPON_NONE) {
        action = mu_player_stop_action(c->class_byte);
        speed = mu_player_stop_speed(action);
    } else {
        action = mu_player_pose_action(MU_POSE_STAND, q->weapon_kind, c->class_byte, s->p->map->world);
        speed = mu_character_action_speed(&q->model, (uint16_t)action);
    }
    set_action(q, action, speed);
    ++q->arrivals;
}

static void cb_move_position(void *context, mu_rp_character *c)
{
    step_context *s = context;
    mu_world_player *q = s->q;
    mu_speed_fields fields;
    memset(&fields, 0, sizeof fields);
    fields.move_speed = c->move_speed;
    fields.object_type = c->model;
    fields.object_kind = c->kind;
    fields.helper_type = c->helper;
    fields.safe_zone = q->safe_zone;
    fields.wing_type = c->slots[MU_RP_SLOT_WING].type;
    fields.transformed = c->transformed;
    fields.world = s->p->map->world;
    fields.stunned = c->stunned;
    mu_move_speed_input in;
    mu_move_speed_input_from(&fields, &in);
    mu_position_input pos;
    memset(&pos, 0, sizeof pos);
    pos.speed = mu_character_move_speed(&in, &q->run);
    pos.world = s->p->map->world;
    pos.helper_type = c->helper;
    pos.safe_zone = q->safe_zone;
    pos.object_type = c->model;
    pos.height = s->p->map->height;
    pos.wall = s->p->map->attributes;
    pos.special_height = s->p->map->water_height;
    pos.scene_state = 6;
    mu_move_character_position(&pos, c->position, c->angle, &q->timer);
    ++q->position_steps;
}

static void make_env(mu_world_players *p, step_context *s, mu_rp_env *env)
{
    memset(env, 0, sizeof *env);
    env->context = s;
    env->world = p->map->world;
    env->scene_state = 6;
    env->path_finding2 = cb_path;
    env->move_path = cb_move_path;
    env->move_character_position = cb_move_position;
    env->set_player_walk = cb_set_walk;
    env->set_player_stop = cb_set_stop;
    env->set_action = cb_set_action;
}

/* ---------------------------------------------------------------- the demo server's packets */

static void viewport_create(mu_world_players *p, mu_world_player *q, int created)
{
    uint8_t record[0x44];
    mu_world_players_encode_viewport(p, q, created, record, sizeof record);
    mu_rp_viewport v;
    if (!mu_rp_viewport_record(record, sizeof record, &v))
        return;
    ++p->viewport_packets;
    /* CreateCharacter 0x0137f6c2: the slot by key (reused), the character create, then the record's fields */
    int32_t key = q->key;
    float z = q->c.position[2];
    mu_rp_character_create(&q->c, (int16_t)key, MU_RP_PLAYER_MODEL, v.x, v.y, 0.0f);
    q->c.level = q->spec.level;
    q->c.guild = q->spec.guild;
    step_context s = {p, q};
    mu_rp_env env;
    make_env(p, &s, &env);
    p->calls.count = 0;
    mu_rp_viewport_apply(&v, &q->c, &env, &p->calls);
    q->equip_calls = p->calls;   /* NATIVE-HELPERS-001: ChangeCharacterExt's helper calls for the helpers module */
    ++q->equip_events;
    q->c.position[2] = z;
    memcpy(q->equipment, v.equipment, sizeof q->equipment);
    q->run = 0;
    q->frame = q->prior_frame = 0.0f;
    q->action_changed = 1;
    q->play_speed = mu_character_action_speed(&q->model, q->c.action);
    q->fade.timer = 0.0f;
    q->fade.alpha = 1.0f;
    q->fade.removed = 0;
    q->voice_3324 = 0.0f;
    q->store_open = 0;
    q->in_view = 1;
    ++q->creates;
    load_parts(p, q);
    if (q->c.movement)
        ++q->moves;
    mu_hn_character *c = plate_character(p, q);
    if (c && mu_names_add(&p->names->names, key))
        ++p->addinfo;
    char text[112];
    snprintf(text, sizeof text, "viewport: %s key %#x at %d,%d (%s)", q->spec.name, key, v.x, v.y,
             created ? "appears" : "walks in");
    log_line(p, text);
}

static void viewport_destroy(mu_world_players *p, mu_world_player *q)
{
    uint8_t packet[8] = {0xc1, 6, 0x14, 1, (uint8_t)(q->key >> 8), (uint8_t)q->key, 0, 0};
    uint16_t keys[4];
    if (mu_rp_destroy_keys(packet, 6, keys, 4) != 1 || keys[0] != (uint16_t)q->key)
        return;
    ++p->destroy_packets;
    if (p->names && q->store_open)
        mu_names_set_store(&p->names->names, q->key, 0, NULL, NULL);   /* 0x00c848fa before DeleteCharacter */
    q->store_open = 0;
    if (mu_rp_delete_character(&q->c, p->map->world) && p->names) {
        mu_names_remove(&p->names->names, q->key, 0);
        ++p->removeinfo;
    }
    q->in_view = 0;
    ++q->destroys;
    char text[112];
    snprintf(text, sizeof text, "destroy: %s key %#x (out of the demo range)", q->spec.name, q->key);
    log_line(p, text);
}

static void move_packet(mu_world_players *p, mu_world_player *q, int32_t tx, int32_t ty)
{
    /* opcode 0x3d: key at +3, target at +5, direction (high nibble) at +7 */
    uint8_t packet[8] = {0xc1, 8, 0x3d, (uint8_t)(q->key >> 8), (uint8_t)q->key, (uint8_t)tx, (uint8_t)ty,
                         (uint8_t)((demo_rand(p) % 8u + 1u) << 4)};
    ++p->move_packets;
    step_context s = {p, q};
    mu_rp_env env;
    make_env(p, &s, &env);
    int32_t before = q->c.tile[0] | (q->c.tile[1] << 8);
    uint8_t moving = q->c.movement;
    p->calls.count = 0;
    mu_rp_move_packet(packet, &q->c, &env, &p->calls);
    if (q->c.movement && !moving)
        ++q->moves;
    if (!q->c.movement && (q->c.tile[0] | (q->c.tile[1] << 8)) != before)
        ++p->teleports;
}

static void die_packet(mu_world_players *p, mu_world_player *q)
{
    /* the die packet 0x01234585 (static): Dead = 1, movement 0 */
    ++p->die_packets;
    q->c.dead = 1;
    q->c.movement = 0;
    ++q->deaths;
    if (p->names) {
        mu_hn_character *c = plate_character(p, q);
        if (c)
            mu_names_set_hp(&p->names->names, q->key, 0, 100);
    }
    char text[112];
    snprintf(text, sizeof text, "die packet: %s (demo)", q->spec.name);
    log_line(p, text);
}

static void store_packet(mu_world_players *p, mu_world_player *q)
{
    uint8_t packet[6 + 0x2f];
    memset(packet, 0, sizeof packet);
    packet[0] = 0xc1;
    packet[1] = sizeof packet;
    packet[2] = 0x3f;
    packet[3] = 2;
    packet[5] = 1;
    packet[6] = (uint8_t)(q->key >> 8);
    packet[7] = (uint8_t)q->key;
    memcpy(packet + 8, q->spec.store_title, strlen(q->spec.store_title));
    mu_rp_store store;
    if (mu_rp_store_records(packet, sizeof packet, &store, 1) != 1)
        return;
    ++p->store_packets;
    q->store_open = 1;
    if (p->names) {
        const mu_lang *lang = mu_lang_shared();
        const char *label = lang ? mu_lang_text(lang, 0x450) : NULL;
        mu_names_set_store(&p->names->names, q->key, 1, store.title, label ? label : "Store");
    }
    char text[112];
    snprintf(text, sizeof text, "store: %s opens '%s' (demo)", q->spec.name, store.title);
    log_line(p, text);
}

/* ---------------------------------------------------------------- the step */

static int32_t hero_distance(const mu_world_players *p, const mu_world_player *q)
{
    int32_t dx = abs(q->c.tile[0] - p->walk->hero.tile[0]), dy = abs(q->c.tile[1] - p->walk->hero.tile[1]);
    return dx > dy ? dx : dy;
}

static void animate(mu_world_player *q)
{
    mu_model *player = &q->model.player;
    if (q->action_changed) {   /* SetAction 0x012affa4 on the object: prior = current, frame 0 */
        uint16_t prior = mu_model_action(player);
        float prior_frame = mu_model_frame(player);
        mu_character_set_state(&q->model, q->c.action, 0.0f, prior_frame, prior);
        q->action_changed = 0;
    }
    uint8_t loop = 0;
    mu_character_tick(&q->model, q->play_speed, &loop);
    q->step_result = loop;
    q->frame = mu_model_frame(player);
    q->prior_frame = mu_model_prior_frame(player);
}

static void player_step(mu_world_players *p, mu_world_player *q)
{
    const mu_world_player_spec *s = &q->spec;
    int32_t dist = hero_distance(p, q);
    /* DEMO server: the viewport around the hero */
    if (!q->in_view) {
        if (q->respawn_in > 0) {
            if (--q->respawn_in == 0) {   /* respawn at the start tile */
                q->c.tile[0] = s->start[0];
                q->c.tile[1] = s->start[1];
                q->c.target[0] = (uint8_t)s->start[0];
                q->c.target[1] = (uint8_t)s->start[1];
                q->c.position[0] = (float)s->start[0] * 100.0f + 50.0f;
                q->c.position[1] = (float)s->start[1] * 100.0f + 50.0f;
                q->c.dead = 0;
                q->fade.removed = 0;
                q->next_leg = 0;
                if (hero_distance(p, q) <= p->view_range)
                    viewport_create(p, q, 1);
            }
            return;
        }
        if (q->fade.removed || q->c.dead)
            return;
        if (dist <= p->view_range)
            viewport_create(p, q, q->creates == 0 && p->steps == 0);
        return;
    }
    if (dist > p->view_range + 3 && !q->c.dead) {
        viewport_destroy(p, q);
        return;
    }
    if ((int32_t)p->steps == s->die_step && !q->c.dead)
        die_packet(p, q);
    if ((int32_t)p->steps == s->store_step && !q->store_open && !q->c.dead)
        store_packet(p, q);
    if (!q->c.dead && !q->c.movement && !q->store_open && s->route_count > 0) {
        if (q->wait > 0)
            --q->wait;
        else {
            const int32_t *leg = s->route[q->next_leg % s->route_count];
            q->next_leg = (q->next_leg + 1) % s->route_count;
            q->wait = s->idle_steps + (int32_t)(demo_rand(p) % 20u);
            move_packet(p, q, leg[0], leg[1]);
        }
    }
    /* the client: the safe-zone byte of the render pass, the dead fade, MoveCharacters' remote step, the dead
     * counter with SetPlayerDie, the animation step */
    uint16_t attribute = p->map->attributes[((q->c.tile[1] & 0xff) << 8) + (q->c.tile[0] & 0xff)];
    q->safe_zone = (uint8_t)(attribute & 1);
    if (q->c.dead) {
        q->fade.model = q->c.model;
        q->fade.world = p->map->world;
        q->fade.z = q->c.position[2];
        q->fade.is_hero = 0;
        mu_dead_fade(q->c.dead, &q->fade);
        q->c.position[2] = q->fade.z;
        if (q->fade.removed) {   /* the fade's removal: live 0, the plate goes (0x013a5ea1) */
            q->c.live = 0;
            q->in_view = 0;
            if (p->names) {
                mu_names_remove(&p->names->names, q->key, 0);
                ++p->removeinfo;
            }
            q->respawn_in = s->respawn_steps > 0 ? s->respawn_steps : 0;
            char text[112];
            snprintf(text, sizeof text, "%s removed after the dead fade", s->name);
            log_line(p, text);
            return;
        }
    }
    step_context ctx = {p, q};
    mu_rp_env env;
    make_env(p, &ctx, &env);
    uint8_t moving = q->c.movement;
    p->calls.count = 0;
    mu_rp_move_step(&q->c, &env, &p->calls);
    if (q->c.movement && !moving)
        ++q->moves;
    animate(q);
    if (q->c.dead) {
        int die = 0;
        q->c.dead = mu_dead_step(q->c.dead, &die);
        if (die && q->voice_3324 == 0.0f) {
            mu_player_state st;
            memset(&st, 0, sizeof st);
            st.class_byte = q->c.class_byte;
            st.class_check = (uint8_t)mu_class_check(st.class_byte);
            st.transform = q->c.helper;
            st.world_voice = (uint8_t)mu_rp_world_rule(p->map->world);
            int32_t rands[4], action = -1, sounds[2];
            for (int k = 0; k < 4; ++k)
                rands[k] = (int32_t)(demo_rand(p) & 0x7fff);
            mu_player_die(&st, rands, 4, &action, sounds);
            set_action(q, action, mu_character_action_speed(&q->model, (uint16_t)action));
            q->voice_3324 = 0.001f;
        }
    }
}

void mu_world_players_step(mu_world_players *p)
{
    for (int32_t i = 0; i < p->count; ++i)
        player_step(p, &p->list[i]);
    ++p->steps;
}

void mu_world_players_frame(mu_world_players *p)
{
    for (int32_t i = 0; i < p->count; ++i) {
        mu_world_player *q = &p->list[i];
        if (!q->in_view || !q->has_model)
            continue;
        place_model(p, q);
        mu_character_update(&q->model);
        if (p->names)
            plate_character(p, q);
    }
}

float mu_world_players_alpha(const mu_world_players *p, int32_t i)
{
    const mu_world_player *q = &p->list[i];
    if (!q->in_view || !q->c.live)
        return 0.0f;
    return q->c.dead ? q->fade.alpha : 1.0f;
}

void mu_world_players_glow(const mu_world_players *p, int32_t i, int item, int32_t *type, int32_t *level,
                           int32_t *option, int32_t *ext, int *has_record, uint8_t *kind_a, uint8_t *kind_b,
                           uint8_t *item_kind)
{
    static const int slot_of[MU_CHARACTER_ITEMS] = {0, 1, 2, 3, 4, 5, MU_RP_SLOT_WEAPON0, MU_RP_SLOT_WEAPON1, MU_RP_SLOT_WING};
    const mu_rp_slot *s = &p->list[i].c.slots[slot_of[item]];
    *type = s->type;
    *level = s->level;
    *option = s->option;
    *ext = s->ext;
    *has_record = 0;
    *kind_a = *kind_b = *item_kind = 0;
    if (p->has_table && s->type >= 0xae6) {
        mu_item rec;
        if (mu_item_find(&p->item_table, (uint32_t)(s->type - 0xae6), &rec) == 0) {
            *has_record = 1;
            *kind_a = rec.attributes.kind_a;
            *kind_b = rec.attributes.kind_b;
            *item_kind = rec.attributes.type;
        }
    }
}

/* ---------------------------------------------------------------- reports */

void mu_world_players_report_frame(const mu_world_players *p, FILE *out, int32_t frame)
{
    fprintf(out, "{\"players_frame\": %d, \"players\": [", frame);
    for (int32_t i = 0; i < p->count; ++i) {
        const mu_world_player *q = &p->list[i];
        fprintf(out, "%s[%d, %d, %.2f, %.2f, %.2f, %d, %d, %u, %u, %u, %.3f, %d, %u]", i ? ", " : "", q->key, q->in_view,
                (double)q->c.position[0], (double)q->c.position[1], (double)q->c.position[2], q->c.tile[0],
                q->c.tile[1], q->c.action, q->c.movement, q->c.dead, (double)mu_world_players_alpha(p, i),
                q->store_open, q->run);
    }
    fprintf(out, "]}\n");
}

void mu_world_players_report_summary(const mu_world_players *p, FILE *out, int quiet)
{
    fprintf(out, "{\"players\": {\"count\": %d, \"steps\": %u, \"viewport_packets\": %u, \"move_packets\": %u,"
                 " \"destroy_packets\": %u, \"die_packets\": %u, \"store_packets\": %u, \"path_calls\": %u,"
                 " \"teleports\": %u, \"addinfo\": %u, \"removeinfo\": %u, \"item_table\": %d, \"range\": %d}}\n",
            p->count, p->steps, p->viewport_packets, p->move_packets, p->destroy_packets, p->die_packets,
            p->store_packets, p->path_calls, p->teleports, p->addinfo, p->removeinfo, p->has_table, p->view_range);
    for (int32_t i = 0; i < p->count; ++i) {
        const mu_world_player *q = &p->list[i];
        fprintf(out, "{\"player\": %d, \"key\": %d, \"name\": \"%s\", \"class\": %d, \"pk\": %d, \"in_view\": %d,"
                     " \"tile\": [%d, %d], \"action\": %u, \"weapon_kind\": %d, \"moves\": %u, \"arrivals\": %u,"
                     " \"creates\": %u, \"destroys\": %u, \"deaths\": %u, \"position_steps\": %u, \"parts\": [",
                i, q->key, q->spec.name, q->c.class_byte, q->c.pk, q->in_view, q->c.tile[0], q->c.tile[1],
                q->c.action, q->weapon_kind, q->moves, q->arrivals, q->creates, q->destroys, q->deaths,
                q->position_steps);
        for (int k = 0; k < MU_RP_SLOTS; ++k)
            fprintf(out, "%s[%d, %d, %d, %d]", k ? ", " : "", q->c.slots[k].type, q->c.slots[k].level,
                    q->c.slots[k].option, q->c.slots[k].ext);
        fprintf(out, "], \"loaded\": [");
        for (int k = 0; k < MU_CHARACTER_ITEMS; ++k)
            fprintf(out, "%s%d", k ? ", " : "", q->has_model && q->model.items[k].loaded);
        fprintf(out, "], \"light\": [%.3f, %.3f, %.3f], \"textures_missing\": [", (double)q->model.params.light[0],
                (double)q->model.params.light[1], (double)q->model.params.light[2]);
        for (int k = 0; k < MU_CHARACTER_ITEMS; ++k)
            fprintf(out, "%s%d", k ? ", " : "", q->has_model && q->model.items[k].loaded ? q->model.items[k].textures.missing : -1);
        fprintf(out, "]}\n");
    }
    if (!quiet)
        for (int32_t i = 0; i < p->log_count; ++i)
            fprintf(out, "{\"players_log\": \"%s\"}\n", p->log[i]);
}
