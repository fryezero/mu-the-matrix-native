/* Other players: the client side of the player viewport (NATIVE-PLAYERS-001). See remote_players.h. */
#include "remote_players.h"

#include <stdio.h>
#include <string.h>

void mu_rp_calls_push(mu_rp_calls *calls, int32_t kind, int32_t a, int32_t b, int32_t c, int32_t d)
{
    if (!calls || calls->count >= MU_RP_CALLS)
        return;
    mu_rp_call *k = &calls->list[calls->count++];
    k->kind = kind;
    k->a = a;
    k->b = b;
    k->c = c;
    k->d = d;
}

/* ---- verified helpers ---- */

uint8_t mu_rp_class_byte(uint8_t p)
{
    /* 0x0139ca62: bit 3 -> bit 4, the high nibble -> bits 0..3, bit 2 -> bit 5, bit 1 -> bit 6, bit 0 -> bit 7 */
    uint8_t out = (uint8_t)((((p >> 3) & 1) << 4) | (p >> 4) | (((p >> 2) & 1) << 5) | (((p >> 1) & 1) << 6));
    out = (uint8_t)(out | ((p & 1) << 7));
    return out;
}

int32_t mu_rp_item_level(uint32_t code)
{
    static const int32_t table[8] = {0, 3, 5, 7, 9, 11, 13, 15};   /* the jump table 0x01395795 */
    return code <= 7 ? table[code] : 0;
}

uint8_t mu_rp_class_index(uint8_t class_byte)
{
    uint8_t hi = (uint8_t)((class_byte >> 4) & 0xf);
    if (hi == 0)
        return 1;
    uint8_t out = 1;
    for (int32_t b = 3; b >= 0; --b)
        if ((hi >> b) & 1) {
            out = (uint8_t)(b + 2);
            break;
        }
    return out;
}

uint8_t mu_rp_class_skin(uint8_t class_byte)
{
    uint8_t low = (uint8_t)(class_byte & 0xf);                     /* 0x0095f5cc */
    uint8_t tier = (uint8_t)(mu_rp_class_index(class_byte) - 1);   /* 0x0139cb8a - 1 */
    return (uint8_t)(low + (tier << 4));
}

/* The wing switch 0x0137c7df: index -> item type; the second column marks the cases that read e[0x11] & 0xf
 * into the wing level c + 0x21a6 (extracted from the jump table 0x0137d3f3). */
static const struct { int16_t type; uint8_t level; } wing_table[0x67] = {
    {-1, 0},      {0x22e6, 0}, {0x22e7, 0}, {0x22e8, 0}, {0x22e9, 0}, {0x22ea, 0}, {0x22eb, 0}, {0x22ec, 0},
    {0x230a, 0},  {0x230b, 0}, {0x230c, 0}, {0x230d, 0}, {0x230e, 0}, {0x230f, 0}, {0x2310, 0}, {0x2311, 0},
    {0x2317, 0},  {0x2318, 0}, {0x2368, 0}, {0x2369, 0}, {0x236a, 0}, {0x236b, 0}, {0x236c, 0}, {0x236d, 0},
    {0x23ec, 0},  {0x23ed, 0}, {0x23ee, 0}, {0x23ef, 0}, {0x23f0, 0}, {0x23f1, 0}, {0x2504, 0}, {0x23f3, 0},
    {0x23f4, 1},  {0x23fc, 0}, {0x23f4, 1}, {0x23f0, 0}, {0x23fd, 0}, {0x23fe, 0}, {0x23ff, 0}, {0x2400, 0},
    {0x2484, 1},  {0x2485, 1}, {0x2486, 1}, {0x2487, 1}, {0x2488, 1}, {0x2489, 1}, {0x248a, 1}, {0x248b, 1},
    {0x2484, 1},  {0x2485, 1}, {0x2486, 1}, {0x2487, 1}, {0x2488, 1}, {0x2489, 1}, {0x248a, 1}, {0x248b, 1},
    {0x24b9, 1},  {0x24bb, 1}, {0x24bb, 1}, {0x24c6, 0}, {0x24be, 1}, {0x24c0, 1}, {0x24c0, 1}, {0x24cf, 1},
    {0x24d0, 1},  {0x24d0, 1}, {0x2380, 1}, {0x2381, 1}, {0x2382, 1}, {0x2384, 1}, {0x2386, 1}, {0x2386, 1},
    {0x2301, 1},  {0x237e, 1}, {0x237e, 1}, {0x2392, 1}, {0x2393, 1}, {0x2394, 1}, {0x2396, 1}, {0x2398, 1},
    {0x2398, 1},  {0x239a, 1}, {0x239b, 1}, {0x239c, 1}, {0x239d, 1}, {0x239e, 1}, {0x239f, 1}, {0x23a0, 1},
    {0x23a1, 1},  {0x23a2, 1}, {0x23a3, 1}, {0x23a4, 1}, {0x23a5, 1}, {0x23a6, 1}, {0x23a7, 1}, {0x23a8, 1},
    {0x23aa, 1},  {0x23aa, 1}, {0x23ac, 1}, {0x34e6, 1}, {0x34e7, 1}, {0x34e9, 1}, {0x34eb, 1}};

void mu_rp_wing(const uint8_t e[MU_RP_EQUIP_BYTES], mu_rp_character *c)
{
    uint32_t index = (uint32_t)(((e[4] & 0xc) << 4) | ((e[8] & 7) << 3) | ((e[0xf] & 0x1c) >> 2)) & 0xff;
    mu_rp_slot *wing = &c->slots[MU_RP_SLOT_WING];
    wing->level = 0;
    if (index > 0x66 || index == 0) {
        wing->type = -1;
        wing->option = 0;
        wing->ext = 0;
        return;
    }
    wing->type = wing_table[index].type;
    if (wing_table[index].level)
        wing->level = (uint8_t)(e[0x11] & 0xf);
}

void mu_rp_helper_state(const uint8_t e[MU_RP_EQUIP_BYTES], mu_rp_character *c)
{
    c->ride_state = (uint8_t)((e[0x10] & 1) ? 4 : (e[0xf] & 3));
}

static void set_part(mu_rp_character *c, int slot, int32_t code, int32_t group_base, int32_t class_base)
{
    mu_rp_slot *s = &c->slots[slot];
    if (code == 0x1ff)
        s->type = (int16_t)(class_base + mu_rp_class_skin(c->class_byte));
    else
        s->type = (int16_t)(group_base + code);
}

void mu_rp_change_equipment(mu_rp_character *c, const uint8_t e[MU_RP_EQUIP_BYTES], int32_t a14,
                            const mu_rp_env *env, mu_rp_calls *calls)
{
    if (c->model != MU_RP_PLAYER_MODEL)
        return;
    mu_rp_slot *w0 = &c->slots[MU_RP_SLOT_WEAPON0], *w1 = &c->slots[MU_RP_SLOT_WEAPON1];
    /* weapons: the low byte and the high nibble of e[0xb] / e[0xc] */
    int32_t code = (int32_t)(int16_t)(((e[0xb] & 0xf0) << 4) | e[0]);
    if (code == 0xfff) {
        w0->type = -1;
        w0->option = 0;
        w0->ext = 0;
    } else
        w0->type = (int16_t)(code + 0xae6);
    code = (int32_t)(int16_t)(((e[0xc] & 0xf0) << 4) | e[1]);
    if (code == 0xfff) {
        w1->type = -1;
        w1->option = 0;
        w1->ext = 0;
    } else
        w1->type = (int16_t)(code + 0xae6);
    mu_rp_wing(e, c);
    mu_rp_slot *helper = &c->slots[MU_RP_SLOT_HELPER];
    if (a14 == 0) {
        mu_rp_calls_push(calls, MU_RP_CALL_C9EA70, 0, 0, 0, 0);
        mu_rp_calls_push(calls, MU_RP_CALL_HELPER_EFFECT_OFF, helper->type, 0, 0, 0);
    } else
        mu_rp_calls_push(calls, MU_RP_CALL_SET_LIVE, a14, 0, 0, 0);
    /* the pet / helper of group 12 (0x24e6): e[4] & 3, 3 = none; the extended codes in e[0xf] & 0xe0 */
    uint32_t v = e[4] & 3;
    if (v != 3) {
        uint32_t s = e[0xf] & 0xe0;
        int32_t w = -1;
        switch (s) {   /* 0x0137b8dd..0x0137b934 */
        case 0x20: w = 0x40; break;
        case 0x40: w = 0x41; break;
        case 0x60: w = 0x7b; break;
        case 0x80: w = 0x43; break;
        case 0xa0: w = 0x50; break;   /* inferred: the compare at 0x0137b8c9 and the switch default at 0x0137b901 are
                                       * protection-patched (5 bytes each); the surviving bytes 74 1d / eb 2b / 6a 40
                                       * fit "cmp eax, 0xa0; je" and "je 0x0137b924 (push 0x50)"; not executed */
        default: break;
        }
        if (w >= 0) {
            helper->type = (int16_t)(0x24e6 + w);
            mu_rp_calls_push(calls, MU_RP_CALL_HELPER_MODEL, 0x1a00 + w, helper->type, 0, 0);
        } else {
            helper->type = (int16_t)(0x24e6 + (int32_t)v);
            int32_t effect_type = 0, create = 1;
            if (v == 0) {
                if (env->scene_state == 6) {
                    int32_t pet = (c->pet_index >= 0 && c->pet_index < 3) ? c->pets[c->pet_index] : -1;   /* 0x0129de01 */
                    if (pet != -1)
                        create = 0;
                }
                effect_type = 0x24e6;
            } else
                create = 0;
            if (create) {
                if (a14 == 0)
                    mu_rp_calls_push(calls, MU_RP_CALL_EFFECT_24E6, effect_type, 0, 0, 0);
                else
                    mu_rp_calls_push(calls, MU_RP_CALL_EFFECT_24E6_A14, effect_type, a14, 0, 0);
            }
        }
    }
    /* the mount manager */
    if (c->transformed) {
        mu_rp_calls_push(calls, MU_RP_CALL_MOUNT_RESET, 0, 0, 0, 0);
        mu_rp_calls_push(calls, MU_RP_CALL_MOUNT_SET, -1, -2, 0, 0);   /* second argument: 0x00b9b476(c), opaque */
    } else if (c->helper != 0xffff) {
        mu_rp_calls_push(calls, MU_RP_CALL_MOUNT_RESET, 0, 0, 0, 0);
        mu_rp_calls_push(calls, MU_RP_CALL_MOUNT_SET, (int32_t)c->helper, (int32_t)c->ride_state, 0, 0);
    }
    if (env->is_hero)
        mu_rp_calls_push(calls, MU_RP_CALL_HERO_OPTIONS, 0, 0, 0, 0);
    mu_rp_calls_push(calls, MU_RP_CALL_9EBF04, 0, 0, 0, 0);
    /* c + 0x16 from e[0xb] bit 1 */
    if (((e[0xb] >> 1) & 1) == 1) {
        if (!(c->byte_16 > 0 && c->byte_16 <= 3))
            c->byte_16 = 4;
    } else if (!(c->byte_16 > 0 && c->byte_16 <= 3))
        c->byte_16 = 0;
    c->byte_31dc = (uint8_t)((e[0xb] & 8) ? 0x10 : 0xf);
    /* levels: 3-bit codes in e[5..7] */
    uint32_t L = ((uint32_t)e[5] << 16) | ((uint32_t)e[6] << 8) | e[7];
    w0->level = (uint8_t)mu_rp_item_level(L & 7);
    w1->level = (uint8_t)mu_rp_item_level((L >> 3) & 7);
    helper->level = 0;
    set_part(c, MU_RP_SLOT_HELM, (int32_t)(int16_t)((e[2] >> 4) | (((e[8] >> 7) & 1) << 4) | ((e[0xc] & 0xf) << 5)),
             0x18e6, 0x3700);
    set_part(c, MU_RP_SLOT_ARMOR, (int32_t)(int16_t)((e[2] & 0xf) | (((e[8] >> 6) & 1) << 4) | (((e[0xd] >> 4) & 0xf) << 5)),
             0x1ae6, 0x3750);
    set_part(c, MU_RP_SLOT_PANTS, (int32_t)(int16_t)((e[3] >> 4) | (((e[8] >> 5) & 1) << 4) | ((e[0xd] & 0xf) << 5)),
             0x1ce6, 0x37a0);
    set_part(c, MU_RP_SLOT_GLOVES, (int32_t)(int16_t)((e[3] & 0xf) | (((e[8] >> 4) & 1) << 4) | (((e[0xe] >> 4) & 0xf) << 5)),
             0x1ee6, 0x37f0);
    set_part(c, MU_RP_SLOT_BOOTS, (int32_t)(int16_t)((e[4] >> 4) | (((e[8] >> 3) & 1) << 4) | ((e[0xe] & 0xf) << 5)),
             0x20e6, 0x3840);
    c->slots[MU_RP_SLOT_HELM].level = (uint8_t)mu_rp_item_level((L >> 6) & 7);
    c->slots[MU_RP_SLOT_ARMOR].level = (uint8_t)mu_rp_item_level((L >> 9) & 7);
    c->slots[MU_RP_SLOT_PANTS].level = (uint8_t)mu_rp_item_level((L >> 12) & 7);
    c->slots[MU_RP_SLOT_GLOVES].level = (uint8_t)mu_rp_item_level((L >> 15) & 7);
    c->slots[MU_RP_SLOT_BOOTS].level = (uint8_t)mu_rp_item_level((L >> 18) & 7);
    /* the option (excellent) bytes from e[9], the ext (ancient) bytes from e[0xa] */
    for (int k = 0; k < 5; ++k) {
        c->slots[MU_RP_SLOT_HELM + k].option = (uint8_t)((e[9] >> (7 - k)) & 1);
        c->slots[MU_RP_SLOT_HELM + k].ext = (uint8_t)((e[0xa] >> (7 - k)) & 1);
    }
    w0->option = (uint8_t)((e[9] >> 2) & 1);
    w1->option = (uint8_t)((e[9] >> 1) & 1);
    w0->ext = (uint8_t)((e[0xa] >> 2) & 1);
    w1->ext = (uint8_t)((e[0xa] >> 1) & 1);
    c->byte_15 = (uint8_t)(e[0xa] & 1);
    if (c->byte_0e == 0)
        mu_rp_calls_push(calls, MU_RP_CALL_9DADF1, 0, 0, 0, 0);
    mu_rp_calls_push(calls, MU_RP_CALL_1394F6F, 0, 0, 0, 0);
    if (env->scene_state != 5 && env->is_hero)
        mu_rp_calls_push(calls, MU_RP_CALL_1394870, 0, 0, 0, 0);
}

/* ---- the move packet and the remote step ---- */

static int world_mode4(int32_t world)
{
    return world >= 0x52 && world <= 0x5a;   /* 0x00e3068f */
}

static void teleport(mu_rp_character *c)
{
    c->tile[0] = c->target[0];
    c->tile[1] = c->target[1];
    c->position[0] = (float)c->tile[0] * 100.0f + 50.0f;
    c->position[1] = (float)c->tile[1] * 100.0f + 50.0f;
}

static int find_path(mu_rp_character *c, const mu_rp_env *env, mu_rp_calls *calls, int32_t mode)
{
    mu_rp_calls_push(calls, MU_RP_CALL_PATH, c->tile[0] | (c->tile[1] << 8), c->target[0] | (c->target[1] << 8), mode, 0);
    int found = env->path_finding2 ? env->path_finding2(env->context, c->tile[0], c->tile[1], c->target[0], c->target[1],
                                                        &c->path, mode)
                                   : 0;
    if (found) {
        c->movement = 1;
        return 1;
    }
    return 0;
}

int mu_rp_move_packet(const uint8_t *p, mu_rp_character *c, const mu_rp_env *env, mu_rp_calls *calls)
{
    if (!c)
        return 0;
    if (c->dead)
        return 1;
    c->direction = (uint8_t)(p[7] >> 4);
    if (!env->hero_moving && env->hero_key_match) {   /* the hero's own echo */
        if ((int8_t)c->movement == 0) {
            c->tile[0] = p[5];
            c->tile[1] = p[6];
            /* with the auto-move flag c + 0x31c8 == 2 the hero's list continues (0x0129cc44 / SendMove /
             * 0x0129c51d, NATIVE-PATH-002); that state is not modelled here (static) */
        }
        return 1;
    }
    c->target[0] = p[5];
    c->target[1] = p[6];
    if ((int32_t)c->target[0] == c->tile[0] && (int32_t)c->target[1] == c->tile[1])
        return 1;
    if (c->model == 0x7d9) {
        c->tile[0] = c->target[0];
        c->tile[1] = c->target[1];
        mu_rp_calls_push(calls, MU_RP_CALL_CREATE_ANGLE, c->tile[0], c->tile[1], 0, 0);   /* angle z = CreateAngle(...) */
        mu_rp_calls_push(calls, MU_RP_CALL_SET_WALK, 0, 0, 0, 0);
        if (env->set_player_walk)
            env->set_player_walk(env->context, c);
        c->byte_2c = 1;
        return 1;
    }
    if (c->byte_31 != 0)
        return 1;
    int32_t mode = (world_mode4(env->world) && !env->hero_key_match) ? 4 : 2;
    if (find_path(c, env, calls, mode))
        return 1;
    if (find_path(c, env, calls, 4))
        return 1;
    teleport(c);
    return 1;
}

void mu_rp_move_step(mu_rp_character *c, const mu_rp_env *env, mu_rp_calls *calls)
{
    if (env->is_hero)
        return;
    if (c->dead != 0) {
        if (c->model == 0x7a7)
            mu_rp_calls_push(calls, MU_RP_CALL_TERRAIN_HEIGHT, 0, 0, 0, 0);   /* position z = RequestTerrainHeight(x, y) */
        return;
    }
    if (c->class_word == 0x180 || c->class_word == 0x17f)
        c->movement = 0;
    if ((int8_t)c->movement == 0) {
        if (c->byte_31 == 0 && c->model != 0x7ac && c->model != 0x93f &&
            !((int32_t)c->target[0] == c->tile[0] && (int32_t)c->target[1] == c->tile[1])) {
            int32_t mode = world_mode4(env->world) ? 4 : 2;
            if (!find_path(c, env, calls, mode) && !find_path(c, env, calls, 4))
                teleport(c);
        }
        return;
    }
    int keep = 0;
    if (c->model == 0x81e)
        keep = c->action == 3 || c->action == 4 || c->action == 8 || c->action == 9 || c->action == 0xb;
    else if (c->model == 0x93f)
        keep = c->action == 3 || c->action == 4;
    if (keep) {
        c->movement = 1;
        mu_rp_calls_push(calls, MU_RP_CALL_SET_ACTION, c->action, 0, 0, 0);
        if (env->set_action)
            env->set_action(env->context, c, c->action);
    } else if (!env->skill_group_7) {
        mu_rp_calls_push(calls, MU_RP_CALL_SET_WALK, 0, 0, 0, 0);
        if (env->set_player_walk)
            env->set_player_walk(env->context, c);
    }
    mu_rp_calls_push(calls, MU_RP_CALL_MOVE_PATH, 1, 0, 0, 0);
    int arrived = env->move_path ? env->move_path(env->context, c) : 0;
    if (arrived) {
        c->movement = 0;
        mu_rp_calls_push(calls, MU_RP_CALL_SET_STOP, 0, 0, 0, 0);
        if (env->set_player_stop)
            env->set_player_stop(env->context, c);
        c->angle[2] = ((float)(int32_t)c->direction - 1.0f) * 45.0f;
    }
    mu_rp_calls_push(calls, MU_RP_CALL_MOVE_POSITION, 0, 0, 0, 0);
    if (env->move_character_position)
        env->move_character_position(env->context, c);
}

/* ---- static readings ---- */

int mu_rp_viewport_record(const uint8_t *p, int32_t avail, mu_rp_viewport *v)
{
    if (avail < 0x44)
        return 0;
    memset(v, 0, sizeof *v);
    uint16_t key = (uint16_t)((p[0] << 8) | p[1]);
    v->created = (uint8_t)(key >> 15);
    v->key = (uint16_t)(key & 0x7fff);
    v->x = p[2];
    v->y = p[3];
    v->packet_class = p[4];
    memcpy(v->equipment, p + 5, MU_RP_EQUIP_BYTES);
    memcpy(v->name, p + 0x18, 10);
    v->name[10] = 0;
    v->target[0] = p[0x22];
    v->target[1] = p[0x23];
    v->direction = (uint8_t)(p[0x24] >> 4);
    v->pk = (uint8_t)(p[0x24] & 0xf);
    v->elemental = p[0x25];
    for (int i = 0; i < 3; ++i) {
        v->pet_code[i] = (uint16_t)((p[0x26 + 3 * i] << 8) | p[0x27 + 3 * i]);
        v->pet_level[i] = p[0x28 + 3 * i];
    }
    v->pet_index = p[0x2f];
    v->helper = (uint16_t)((p[0x30] << 8) | p[0x31]);
    v->byte_32 = p[0x32];
    v->server = (uint16_t)(p[0x3e] | (p[0x3f] << 8));
    v->flags = p[0x40];
    v->muun = p[0x41];
    v->muun_level = p[0x42];
    v->buff_count = p[0x43];
    int32_t n = v->buff_count > 56 ? 56 : v->buff_count;
    v->size = 0x44 + 8 * v->buff_count;   /* 0x204 - (0x38 - n) * 8 */
    if (v->size > avail)
        return 0;
    for (int32_t i = 0; i < n; ++i) {
        v->buff_type[i] = (uint16_t)(p[0x44 + 8 * i] | (p[0x45 + 8 * i] << 8));
        v->buff_value[i] = (uint32_t)p[0x48 + 8 * i] | ((uint32_t)p[0x49 + 8 * i] << 8) |
                           ((uint32_t)p[0x4a + 8 * i] << 16) | ((uint32_t)p[0x4b + 8 * i] << 24);
    }
    v->pose_state = (uint8_t)((v->equipment[0x10] >> 5) & 7);
    return v->size;
}

void mu_rp_character_create(mu_rp_character *c, int16_t key, int32_t model, uint8_t x, uint8_t y, float angle)
{
    memset(c, 0, sizeof *c);
    c->key = key;
    c->tile[0] = x;
    c->tile[1] = y;
    c->target[0] = x;
    c->target[1] = y;
    c->guild = -1;
    c->pk = 3;
    c->model = model;
    c->live = 1;
    c->kind = 1;
    c->class_word = -1;
    c->move_speed = 10;
    c->guild_bytes[0] = 0xff;   /* +0x17 */
    c->guild_bytes[3] = 0x43;   /* +0x1a */
    c->helper = 0xffff;
    c->pet_index = 0;
    for (int i = 0; i < 3; ++i)
        c->pets[i] = -1;
    for (int k = 0; k < MU_RP_SLOTS; ++k)
        c->slots[k].type = -1;
    c->action = c->prior_action = (uint16_t)(model == MU_RP_PLAYER_MODEL ? 1 : 0);
    c->position[0] = (float)c->tile[0] * 100.0f + 50.0f;
    c->position[1] = (float)c->tile[1] * 100.0f + 50.0f;
    c->angle[2] = angle;
}

int32_t mu_rp_viewport_pose_action(int32_t state, int class_check, int ride_59, int ride_5a, int ride_72)
{
    switch (state) {
    case 2:
        if (!class_check)
            return ride_59 ? 0x174 : 0x172;
        return ride_5a ? 0x175 : ride_72 ? 0x176 : 0x177;
    case 3:
        if (!class_check)
            return ride_59 ? 0x17c : 0x17b;
        return ride_5a ? 0x17d : ride_72 ? 0x17e : 0x17f;
    case 4:
        return class_check ? 0x17a : 0x179;
    default:
        return -1;
    }
}

float mu_rp_viewport_angle(uint8_t direction)
{
    return ((float)(int32_t)direction - 1.0f) * 45.0f;
}

void mu_rp_viewport_apply(const mu_rp_viewport *v, mu_rp_character *c, const mu_rp_env *env, mu_rp_calls *calls)
{
    c->class_byte = mu_rp_class_byte(v->packet_class);
    c->byte_13 = 0;
    c->pk = v->pk;
    c->kind = 1;
    c->tile[0] = v->x;
    c->tile[1] = v->y;
    c->target[0] = v->target[0];
    c->target[1] = v->target[1];
    c->angle[2] = mu_rp_viewport_angle(v->direction);
    c->elemental = v->elemental;
    c->byte_327c = 0;
    c->stunned = (uint8_t)(v->flags & 1);
    c->field_3230 = (v->flags >> 1) & 0x3f;
    c->transformed = (uint8_t)((v->flags & 0x80) ? 1 : 0);
    for (int i = 0; i < 3; ++i)
        c->pets[i] = v->pet_code[i] == 0xffff ? -1 : (int32_t)v->pet_code[i];   /* the item-kind check is static */
    c->pet_index = v->pet_index;
    c->helper = v->helper;
    mu_rp_helper_state(v->equipment, c);
    if (v->created) {
        c->position[0] = ((float)c->tile[0] + 0.5f) * 100.0f;
        c->position[1] = ((float)c->tile[1] + 0.5f) * 100.0f;
        c->field_3330 = 0.0f;
    } else {
        int32_t mode = 2;   /* 0x0122dc47: viewport starts with 2 in every world */
        if (!find_path(c, env, calls, mode) && !find_path(c, env, calls, 4))
            teleport(c);
    }
    mu_rp_change_equipment(c, v->equipment, 0, env, calls);
    memcpy(c->name, v->name, sizeof c->name);
    if (v->muun != 0xff) {   /* the muun table 0x06fbc870 lookup 0x01177e1c: static, the index is taken as is */
        c->slots[MU_RP_SLOT_MUUN].type = (int16_t)(0xae6 + v->muun);
        c->slots[MU_RP_SLOT_MUUN].level = v->muun_level;
    } else
        c->slots[MU_RP_SLOT_MUUN].type = -1;
    c->server = v->server;
}

int32_t mu_rp_destroy_keys(const uint8_t *p, int32_t avail, uint16_t *keys, int32_t max)
{
    if (avail < 4)
        return 0;
    int32_t count = p[3], n = 0;
    for (int32_t i = 0; i < count && n < max; ++i) {
        int32_t at = 4 + 2 * i;
        if (at + 2 > avail)
            break;
        keys[n++] = (uint16_t)(((p[at] << 8) | p[at + 1]) & 0x7fff);
    }
    return n;
}

int mu_rp_world_rule(int32_t world)
{
    return (world >= 0x12 && world <= 0x17) || world == 0x35 || world == 0x61;
}

int mu_rp_delete_character(mu_rp_character *c, int32_t world)
{
    c->live = 0;
    return !mu_rp_world_rule(world);
}

int32_t mu_rp_store_records(const uint8_t *p, int32_t avail, mu_rp_store *out, int32_t max)
{
    if (avail < 6)
        return 0;
    int32_t count = p[5], n = 0;
    for (int32_t i = 0; i < count && n < max; ++i) {
        const uint8_t *r = p + 6 + 0x2f * i;
        if (6 + 0x2f * (i + 1) > avail)
            break;
        out[n].key = (uint16_t)((r[0] << 8) | r[1]);
        memcpy(out[n].title, r + 2, 0x2d);
        out[n].title[0x2d] = 0;
        ++n;
    }
    return n;
}

void mu_rp_store_id_html(const char *pk_color, const char *name, char *out, size_t cap)
{
    snprintf(out, cap, "<font color='%s'>%s</font>", pk_color, name);
}
