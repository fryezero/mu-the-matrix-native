/* Portable integration checks for arrow arguments and the model draw callback.
 * Include the implementation to exercise its private emission route without adding a production API. */
#include "../core/mu_combat.c"
#include <assert.h>
#include <stdlib.h>

static int draws;
static void inspect_draw(void *context, const mu_model *model, const mu_textures *textures,
                         int32_t slot, const mu_draw_options *options)
{
    (void)textures; (void)slot; (void)options;
    const int white = *(const int *)context;
    for (int k = 0; k < 3; ++k)
        assert(model->params.color[k] == (white ? 1.0f : 0.25f));
    ++draws;
}

int main(int argc, char **argv)
{
    assert(argc == 2);
    mu_combat *c = calloc(1, sizeof *c);
    assert(c);
    init_env(c);
    c->hero_key = 123;
    mu_sfx_effect *e = &c->effects[0];
    e->type = 0x47f; e->live = 1;
    mu_sfx_call call = {0};
    call.routine = MU_SFX_CALL_JOINT;
    call.type = 0x7f79; call.subtype = 12; call.owner = -2; call.scale = 40;
    call.arg7 = 80;
    env_call(c, &call, e);
    assert(c->stats.joints_created == 1);
    assert(c->joints[0].lifetime == 80 && c->joints[0].key == 0);
    call.type = 0x8182; call.subtype = 10; call.arg7 = -1;
    call.light[0] = 0.1f; call.light[1] = 0.7f; call.light[2] = 0.92f;
    env_call(c, &call, e);
    assert(c->stats.joints_created == 2);
    for (int k = 0; k < 3; ++k) assert(c->joints[1].light[k] == call.light[k]);
    assert(c->jenv.has_creation_light == 0);
    call.routine = MU_SFX_CALL_EFFECT; call.type = 0x38b5; call.subtype = 1;
    call.owner = -1; call.scale = 0.2f; call.range = 0xffff;
    env_call(c, &call, e);
    assert(c->effects[1].type == 0x38b5 && c->effects[1].scale == 0.2f);
    assert(c->effects[1].key == 0xffff && c->stats.arrows == 0);
    for (int white = 0; white <= 1; ++white) {
        mu_combat_config config;
        mu_combat_default_config(&config);
        config.weapon = MU_COMBAT_WEAPON_BOW;
        config.bow_item = white ? 0x1304 : 0x130e;
        char error[128];
        assert(!mu_combat_init(c, argv[1], NULL, NULL, NULL, &config, error, sizeof error));
        e = &c->effects[0];
        e->type = white ? 0x45e : 0x38b5;
        e->subtype = white ? 0 : 1;
        e->live = 1; e->scale = e->alpha = 1;
        e->light[0] = e->light[1] = e->light[2] = 0.25f;
        draws = 0;
        assert(mu_combat_draw_models(c, inspect_draw, &white) == 1);
        assert(draws == (white ? 2 : 1));
        mu_combat_free(c);
    }
    free(c);
    puts("arrow key and colour; multishot above bitmap threshold; gunbow white double draw: OK");
    return 0;
}
