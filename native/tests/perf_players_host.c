/* Compare every mapped output, shared bone side effect and saved attachment
 * bone after serial/parallel frames. Authored inputs only. */
#include "../core/mu_world_players.h"
#include "../core/mu_png.h"
#include <stdlib.h>
#include <string.h>

static void model_hash(const mu_model *m)
{
    for (uint32_t i = 0; i < m->memory.count; ++i) {
        char hash[65];
        mu_sha256_hex(m->memory.regions[i].bytes, m->memory.regions[i].size, hash);
        puts(hash);
    }
}

int main(int argc, char **argv)
{
    if (argc < 2 || argc > 4) return 2;
    int players = argc > 2 ? atoi(argv[2]) : 9;
    int frames = argc > 3 ? atoi(argv[3]) : 32;
    if (players < 0 || players > MU_WORLD_PLAYERS_MAX || frames < 1) return 2;
    mu_world_players *p = calloc(1, sizeof *p);
    if (!p) return 3;
    p->count = players;
    for (int i = 0; i < p->count; ++i) {
        mu_world_player *q = &p->list[i];
        char error[256];
        if (mu_character_init(&q->model, argv[1], NULL, error, sizeof error)) return 4;
        q->has_model = q->in_view = 1;
        for (int j = 1; j < MU_CHARACTER_ITEMS; ++j) {
            if (mu_character_set_item(&q->model, j, argv[1], 1, error, sizeof error)) return 5;
            q->model.items[j].link_bone = 1;
        }
    }
    for (int frame = 0; frame < frames; ++frame) {
        for (int i = 0; i < p->count; ++i) {
            mu_world_player *q = &p->list[i];
            q->in_view = (frame + i) % 7 != 0;
            q->has_model = (frame + i) % 11 != 0;
            for (int k = 0; k < 3; ++k) {
                q->c.position[k] = (float)(frame * 17 + i * 3 + k);
                q->c.angle[k] = (float)(i * 15 + frame * 2 + k);
                q->model.params.head[k % 2] = (float)(frame + i);
            }
            q->model.params.scale = 0.7f + (float)i * 0.04f;
            mu_character_set_state(&q->model, (uint16_t)(frame % 2), (float)(frame % 3) * 0.6f,
                                   (float)((frame + 1) % 3) * 0.4f, (uint16_t)((frame + i) % 2));
            q->model.items[MU_CHARACTER_WEAPON_ITEM(0)].carry = frame % 3;
            q->model.items[MU_CHARACTER_WEAPON_ITEM(0)].carry_bone = 1;
            q->model.items[MU_CHARACTER_WEAPON_ITEM(0)].carry_frame = (float)(frame % 3) * 0.25f;
        }
        mu_world_players_frame(p);
        for (int i = 0; i < p->count; ++i) {
            mu_character *c = &p->list[i].model;
            model_hash(&c->player);
            char hash[65];
            mu_sha256_hex((const uint8_t *)c->player_bones, MU_MODEL_SHARED_BONE_BYTES, hash);
            puts(hash);
            for (int j = 1; j < MU_CHARACTER_ITEMS; ++j) {
                model_hash(&c->items[j].model);
                if (c->items[j].bones) {
                    mu_sha256_hex((const uint8_t *)c->items[j].bones, (size_t)c->items[j].bmd.bone_count * 48, hash);
                    puts(hash);
                }
            }
        }
    }
    for (int i = 0; i < p->count; ++i) mu_character_free(&p->list[i].model);
    free(p);
    return 0;
}
