/* RENDER-EFFECTS-015: the production combat routes of the ground skills' rain 0x70a: its rings and sound at
 * creation, the caster lookup and the arrows its move fires (owned by the rain, whose +0x64 is their landing flag),
 * and RenderEffects' terrain decals as clamped quads over a flat synthetic terrain. */
#include "../core/mu_combat.c"
#include <assert.h>
#include <stdlib.h>

static int32_t count_type(const mu_combat *c, int32_t type)
{
    int32_t n = 0;
    for (int i = 0; i < MU_SFX_EFFECTS; ++i)
        n += c->effects[i].live && c->effects[i].type == type;
    return n;
}

int main(void)
{
    mu_combat *c = calloc(1, sizeof *c);
    assert(c);
    init_env(c);
    c->hero_key = 0x1234;
    c->weapon_item[0] = 0x12e6;   /* Bow01: Arrow01 0x43b */
    for (size_t k = 0; k < sizeof bitmap_files / sizeof bitmap_files[0]; ++k) {   /* load_bitmaps without files */
        c->bitmaps[c->bitmap_count].id = bitmap_files[k].id;
        c->bitmaps[c->bitmap_count++].wrap = bitmap_files[k].wrap;
    }
    const float at[3] = {18200.0f, 12800.0f, 0.0f}, angle[3] = {0, 0, 90.0f}, white[3] = {1, 1, 1};
    mu_sfx_info info;
    memset(&info, 0, sizeof info);
    info.key = 0x1234;

    /* creation: seven rings (0x700, 0x702 twice, 0x707, 0x701 three times) and sound 0x55d at its site */
    create_effect_scaled(c, 0x70a, 1, at, angle, white, MU_COMBAT_HERO_OBJECT, &info, 1.0f);
    assert(c->stats.unsupported == 0 && c->stats.fx_created == 8);
    assert(count_type(c, 0x70a) == 1 && count_type(c, 0x700) == 1 && count_type(c, 0x701) == 3 &&
           count_type(c, 0x702) == 2 && count_type(c, 0x707) == 1);
    assert(c->sounds_played == 1 && c->last_sound == 0x55d);
    uint32_t routine = 0;
    assert(mu_sfx_sound_site(0x55d, &routine) == 0x0141953eu && routine == 0x013c0f19u);
    assert(mu_sfx_sound_site(0x42, &routine) == 0x01579fa1u && routine == 0x01556c26u);
    mu_sfx_effect *rain = &c->effects[0];
    assert(rain->type == 0x70a && rain->lifetime == 20 && rain->field_64 == 0 && rain->angle[2] == 0.0f);

    /* the move: the hero is the caster; one Arrow01 from the rain's moved position, owned by the rain */
    c->walk = calloc(1, sizeof *c->walk);
    assert(c->walk);
    refresh_objects(c);
    const uint32_t arrows = c->stats.arrows;
    assert(mu_sfx_effect_move(rain, &c->env));
    assert(c->stats.arrows == arrows + 1 && c->stats.unsupported == 0);
    assert(rain->position[0] == at[0] && rain->position[1] == at[1]);   /* restored after the shot */
    mu_sfx_effect *arrow = NULL;
    for (int i = 0; i < MU_SFX_EFFECTS; ++i)
        if (c->effects[i].live && c->effects[i].type == MU_SFX_MODEL_ARROW)
            arrow = &c->effects[i];
    assert(arrow && arrow->owner == MU_COMBAT_EFFECT_OBJECT(0) && arrow->skill == 0x7e7);
    assert(arrow->position[2] == 500.0f);   /* 500 above the (flat, height 0) ground */
    const mu_jt_object *view = mu_combat_object(c, MU_COMBAT_EFFECT_OBJECT(0));
    assert(view && view->live);
    /* the landing flag is the rain's +0x64: the first landing plays, the next does not */
    mu_sfx_call flag = {0};
    flag.routine = MU_SFX_CALL_OWNER_FLAG;
    flag.owner = arrow->owner;
    assert(env_call(c, &flag, arrow) == 0 && rain->field_64 == 1 && env_call(c, &flag, arrow) == 1);
    /* a dead caster fires nothing */
    c->hero_dead = 1;
    assert(mu_sfx_effect_move(rain, &c->env) && c->stats.arrows == arrows + 1);
    c->hero_dead = 0;

    /* the decals: 0x70a's empact01, enemy_ring02, lightmarks as clamped additive quads over a flat terrain */
    static uint16_t attributes[MU_TERRAIN_CELLS];
    static float height[MU_TERRAIN_CELLS];
    mu_terrain_scene scene;
    memset(&scene, 0, sizeof scene);
    scene.attributes = attributes;
    scene.height = height;
    for (int k = 0; k < c->bitmap_count; ++k)
        if (c->bitmaps[k].id == 0x8070 || c->bitmaps[k].id == 0x7f87 || c->bitmaps[k].id == 0x8078) {
            c->bitmaps[k].loaded = 1;
            c->bitmaps[k].image.width = c->bitmaps[k].image.height = 4;
            assert(c->bitmaps[k].wrap == 0x2900u);
        }
    for (int i = 1; i < MU_SFX_EFFECTS; ++i)
        c->effects[i].live = 0;
    rain->lifetime = 15;
    static mu_combat_quad quads[MU_COMBAT_DECAL_QUADS];
    const int32_t n = decal_quads_scene(c, &scene, 0.0f, quads, MU_COMBAT_DECAL_QUADS);
    /* sizes 2, 3 and 4: (2 (int size + 1) + 1)^2 = 49, 81 and 121 tiles */
    assert(n == 49 + 81 + 121 && c->stats.decals == 3 && c->stats.decal_quads == (uint32_t)n);
    for (int32_t k = 0; k < n; ++k)
        assert(quads[k].additive && quads[k].depth_test && quads[k].position[0][2] == 5.0f);
    const int32_t small = decal_quads_scene(c, &scene, 0.0f, quads, 10);
    assert(small == 10 && c->stats.decal_quads_dropped == (uint32_t)(n - 10));

    free(c->walk);
    free(c);
    puts("0x70a rings, sound site, rain arrows, landing flag and terrain decals through native routes: OK");
    return 0;
}
