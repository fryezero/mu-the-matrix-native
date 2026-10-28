#include "viewport_monsters.h"
#include "actors.h"
#include "effect_class_table.h"
#include <string.h>

int mu_monster_viewport_record(const uint8_t *p, int32_t length, mu_monster_viewport *v)
{
    if (!p || !v || length < 0x1c || p[0x1a] > 56 || length < 0x1c + 8 * p[0x1a]) return 0;
    memset(v, 0, sizeof *v);
    uint16_t key = (uint16_t)((p[0] << 8) | p[1]);
    v->size = 0x1c + 8 * p[0x1a];
    v->key = key & 0x7fff;
    v->created = (uint8_t)(key >> 15);
    v->special = (p[0] >> 6) & 1;
    v->server_class = (uint16_t)(((p[2] & 3) << 8) | p[3]);
    v->flag_34 = p[2] & 0x80;
    v->object_43 = (p[2] >> 4) & 7;
    v->x = p[4]; v->y = p[5];
    v->target[0] = p[6]; v->target[1] = p[7];
    v->direction = p[8] >> 4; v->elemental = p[9];
    v->words[0] = p[0xa]; v->words[1] = p[0xb];
    v->words[2] = (uint16_t)((p[0xc] << 8) | p[0xd]); v->words[3] = p[0xe];
    v->effect = p[0xf];
    v->level = (uint16_t)((p[0x10] << 8) | p[0x11]);
    v->max_hp = ((uint32_t)p[0x12] << 24) | ((uint32_t)p[0x14] << 16) | ((uint32_t)p[0x13] << 8) | p[0x15];
    v->hp = ((uint32_t)p[0x16] << 24) | ((uint32_t)p[0x18] << 16) | ((uint32_t)p[0x17] << 8) | p[0x19];
    v->buff_count = p[0x1a];
    for (int i = 0; i < v->buff_count; ++i) {
        const uint8_t *b = p + 0x1c + 8 * i;
        v->buff_type[i] = (uint16_t)(b[0] | (b[1] << 8));
        v->buff_value[i] = (uint32_t)b[4] | ((uint32_t)b[5] << 8) | ((uint32_t)b[6] << 16) | ((uint32_t)b[7] << 24);
    }
    return v->size;
}

int mu_monster_character_create(mu_rp_character *c, const mu_monster_viewport *v)
{
    const mu_monster_class *r = mu_monster_class_find(v->server_class);
    int32_t model = r ? r->model : -1;
    for (unsigned i = 0; i < MU_EFFECT_CLASS_ROWS; ++i)
        if (mu_effect_classes[i].server_class == v->server_class) model = mu_effect_classes[i].npc_index;
    if (model < 0) return 0; /* unavailable engine-dependent classes stay explicit */
    mu_rp_character_create(c, (int16_t)v->key, model, v->x, v->y, 0);
    c->class_word = (int16_t)v->server_class;
    c->kind = 2; /* native actor discriminator; table's NPC classification is kept by the presenter */
    if (r) {
        c->class_byte = r->class_byte;
        for (unsigned k = 0; k < 9; ++k)
            if (r->slots[k].type) {
                c->slots[k].type = (int16_t)r->slots[k].type;
                c->slots[k].level = r->slots[k].level;
            }
    }
    return 1;
}

void mu_monster_viewport_apply(mu_rp_character *c, const mu_monster_viewport *v, const mu_rp_env *env)
{
    c->level = v->level; c->max_hp = v->max_hp; c->hp = v->hp;
    c->tile[0] = v->x; c->tile[1] = v->y;
    memcpy(c->target, v->target, sizeof c->target);
    c->direction = v->direction;
    c->byte_43 = v->object_43;
    c->elemental = v->elemental;
    float factor = 45.0f;
    if (c->model == 0x808) {
        if (c->tile[1] == 90) factor = 0;
        if (c->tile[0] == 62) factor = -135;
        if (c->tile[0] == 183) factor = 90;
    } else if (c->model == 0xa3e) factor = 90;
    c->angle[2] = ((float)v->direction - 1.0f) * factor;
    if ((c->model >= 0xa57 && c->model <= 0xa5a) || (c->model >= 0xa5c && c->model <= 0xa5d)) c->angle[2] = 90;
    if (c->model == 0xa62) c->angle[2] = 20;
    if (c->model == 0xa6c) c->angle[2] = 49;
    if (c->model == 0xa4d) c->angle[2] = 30;
    /* The 0x5c/model table's angle override is unavailable; bounded host answer is false. */
    int mode = (env->world >= 0x52 && env->world <= 0x5a) ? 4 : 2;
    int ok = env->path_finding2 && env->path_finding2(env->context, v->x, v->y, v->target[0], v->target[1], &c->path, mode);
    if (!ok && env->path_finding2)
        ok = env->path_finding2(env->context, v->x, v->y, v->target[0], v->target[1], &c->path, 4);
    if (ok) c->movement = 1;
    else {
        c->tile[0] = v->target[0]; c->tile[1] = v->target[1];
        c->position[0] = (float)c->tile[0] * 100.0f + 50.0f;
        c->position[1] = (float)c->tile[1] * 100.0f + 50.0f;
    }
}
