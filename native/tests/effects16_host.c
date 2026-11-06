/* RENDER-EFFECTS-016: the production combat routes of 016. No argument: portable self-checks (Fire06 0x7f40/1..3
 * admitted and in the world particle table, every combat bitmap's LoadBitmap filter and wrap, 0x70c's crater decal
 * under EnableAlphaTest(1): alpha test and depth writes). "table": the combat bitmap rows and the world particle
 * table's Fire06 slot as JSON. "decals": the wrapper ops and decal quad states of 0x70a, 0x70c and 0x45e/3..7 as
 * JSON (scripts/validate_render_effects16.py compares both with the client). */
#include "../core/mu_combat.c"
#include <assert.h>
#include <stdlib.h>

static void bitmaps_without_files(mu_combat *c)
{
    for (size_t k = 0; k < sizeof bitmap_files / sizeof bitmap_files[0]; ++k) {
        mu_combat_bitmap *b = &c->bitmaps[c->bitmap_count++];
        b->id = bitmap_files[k].id;
        b->wrap = bitmap_files[k].wrap;
        b->filter = bitmap_files[k].filter;
        if (bitmap_files[k].decal) {
            b->loaded = 1;
            b->image.width = b->image.height = 4;
        }
    }
}

static int table(void)
{
    printf("{\"bitmaps\": [");
    for (size_t k = 0; k < sizeof bitmap_files / sizeof bitmap_files[0]; ++k)
        printf("%s[%d, \"%s\", \"%s\", %u, %u, %d]", k ? ", " : "", bitmap_files[k].id, bitmap_files[k].dir,
               bitmap_files[k].name, bitmap_files[k].filter, bitmap_files[k].wrap, bitmap_files[k].decal);
    mu_world_particles *p = calloc(1, sizeof *p);
    char error[128];
    if (!p || mu_world_particles_open(p, "", NULL, 0, 1, 1, error, sizeof error))
        return 1;
    const int32_t slot = mu_world_particles_bitmap_slot(0x7f40);
    printf("], \"fire06\": [%d, %u, %u], \"fire06_kinds\": [%d, %d, %d, %d, %d]}\n", slot,
           slot >= 0 ? p->bitmaps.filter[slot] : 0u, slot >= 0 ? p->bitmaps.wrap[slot] : 0u,
           mu_pt_kind_supported(0x7f40, 0), mu_pt_kind_supported(0x7f40, 1), mu_pt_kind_supported(0x7f40, 2),
           mu_pt_kind_supported(0x7f40, 3), mu_pt_kind_supported(0x7f40, 4));
    mu_world_particles_close(p);
    free(p);
    return 0;
}

/* one effect alone: its ops, then its decal quads (consecutive equal states merged) */
static void decals_of(mu_combat *c, mu_terrain_scene *scene, const mu_sfx_effect *e, int first)
{
    static mu_combat_quad quads[MU_COMBAT_DECAL_QUADS];
    for (int i = 0; i < MU_SFX_EFFECTS; ++i)
        c->effects[i].live = 0;
    c->effects[0] = *e;
    mu_sfx_render_op ops[MU_SFX_RENDER_OPS];
    const int count = mu_sfx_effect_render_ops(e, 0.0f, ops);
    printf("%s{\"type\": %d, \"subtype\": %d, \"lifetime\": %d, \"ops\": [", first ? "" : ", ", e->type, e->subtype,
           e->lifetime);
    for (int k = 0; k < count; ++k)
        printf("%s[%d, %d, %d]", k ? ", " : "", ops[k].routine, ops[k].argument, ops[k].texture);
    const int32_t n = decal_quads_scene(c, scene, 0.0f, quads, MU_COMBAT_DECAL_QUADS);
    printf("], \"quads\": [");
    int printed = 0;
    for (int32_t k = 0; k < n; ++k) {
        const mu_combat_quad *q = &quads[k];
        if (k && q->bitmap == quads[k - 1].bitmap && q->additive == quads[k - 1].additive &&
            q->src == quads[k - 1].src && q->dst == quads[k - 1].dst && q->alpha_test == quads[k - 1].alpha_test &&
            q->depth_mask == quads[k - 1].depth_mask)
            continue;
        printf("%s[%d, %d, %u, %u, %d, %d]", printed++ ? ", " : "", c->bitmaps[q->bitmap].id, q->additive, q->src,
               q->dst, q->alpha_test, q->depth_mask);
    }
    printf("]}");
}

static int decals(mu_combat *c)
{
    static uint16_t attributes[MU_TERRAIN_CELLS];
    static float height[MU_TERRAIN_CELLS];
    mu_terrain_scene scene;
    memset(&scene, 0, sizeof scene);
    scene.attributes = attributes;
    scene.height = height;
    mu_sfx_effect e;
    memset(&e, 0, sizeof e);
    e.live = 1;
    e.position[0] = 18200.0f;
    e.position[1] = 12800.0f;
    e.light[0] = e.light[1] = e.light[2] = 0.9f;
    e.alpha = 0.8f;
    e.scale = 1.0f;
    e.field_d8 = 0.5f;
    printf("{\"effects\": [");
    static const int32_t kinds[][3] = {{0x70a, 0, 15}, {0x70a, 1, 5}, {0x70c, 0, 40}, {0x70c, 0, 20}, {0x45e, 3, 30},
                                       {0x45e, 7, 30}};
    for (size_t k = 0; k < sizeof kinds / sizeof kinds[0]; ++k) {
        e.type = kinds[k][0];
        e.subtype = kinds[k][1];
        e.lifetime = kinds[k][2];
        decals_of(c, &scene, &e, k == 0);
    }
    printf("]}\n");
    return 0;
}

static int self_checks(mu_combat *c)
{
    /* Fire06 0x7f40: Fire01's case for subtypes 1..3, in the world particle table LINEAR/CLAMP */
    assert(!mu_pt_kind_supported(0x7f40, 0) && mu_pt_kind_supported(0x7f40, 1) && mu_pt_kind_supported(0x7f40, 3) &&
           !mu_pt_kind_supported(0x7f40, 4));
    mu_world_particles *p = calloc(1, sizeof *p);
    char error[128];
    assert(p && !mu_world_particles_open(p, "", NULL, 0, 1, 1, error, sizeof error));
    const int32_t slot = mu_world_particles_bitmap_slot(0x7f40);
    assert(slot >= 0 && p->bitmaps.filter[slot] == 0x2601u && p->bitmaps.wrap[slot] == 0x2900u);
    assert(mu_world_particles_bitmap_slot(MU_PT_BITMAP_RAIN_RING) == MU_WORLD_PT_BITMAPS - 1);
    mu_world_particles_close(p);
    free(p);
    /* the combat bitmaps: GL_CLAMP but Thunder01, Flare02, force_Pillar, !SwordEff and Swordeff_mono3 (REPEAT);
     * Cratered GL_NEAREST */
    int repeat = 0, nearest = 0;
    for (int k = 0; k < c->bitmap_count; ++k) {
        const mu_combat_bitmap *b = &c->bitmaps[k];
        assert(b->wrap == 0x2900u || b->wrap == 0x2901u);
        repeat += b->wrap == 0x2901u;
        nearest += b->filter == 0x2600u;
        if (b->id == 0x7f2b || b->id == 0x7f79 || b->id == 0x80e3 || b->id == 0x80e4 || b->id == 0x85cc)
            assert(b->wrap == 0x2901u);
        if (b->id == 0x7fe9)
            assert(b->filter == 0x2600u);
    }
    assert(repeat == 5 && nearest == 1);
    /* the wrappers: EnableAlphaTest(1) leaves blending (SRC_ALPHA, ONE_MINUS_SRC_ALPHA), alpha test and depth writes
     * on; EnableAlphaBlend turns both off; EnableAlphaTest(0) keeps the depth mask */
    mu_sfx_gl_state s;
    memset(&s, 0, sizeof s);
    s.fog_flag = 1;
    assert(mu_sfx_render_state(&s, MU_SFX_RENDER_BLEND_ALPHA, 1) && s.gl_blend && s.gl_src == 0x0302u &&
           s.gl_dst == 0x0303u && s.gl_alpha_test && s.gl_depth_mask && s.gl_fog && !s.gl_cull);
    assert(mu_sfx_render_state(&s, MU_SFX_RENDER_BLEND_ADD, 0) && s.gl_src == 1u && s.gl_dst == 1u &&
           !s.gl_alpha_test && !s.gl_depth_mask && !s.gl_fog);
    assert(mu_sfx_render_state(&s, MU_SFX_RENDER_BLEND_ALPHA, 0x100) && !s.gl_depth_mask && s.gl_alpha_test);
    assert(mu_sfx_render_state(&s, MU_SFX_RENDER_BLEND_OFF, 0) && !s.gl_blend && s.gl_depth_mask && s.gl_cull);
    assert(!mu_sfx_render_state(&s, MU_SFX_RENDER_DECAL, 0));
    /* 0x70c's crater: alpha-tested, depth-writing (SRC_ALPHA, ONE_MINUS_SRC_ALPHA) quads; its flash additive */
    static uint16_t attributes[MU_TERRAIN_CELLS];
    static float height[MU_TERRAIN_CELLS];
    mu_terrain_scene scene;
    memset(&scene, 0, sizeof scene);
    scene.attributes = attributes;
    scene.height = height;
    mu_sfx_effect *e = &c->effects[0];
    memset(e, 0, sizeof *e);
    e->live = 1;
    e->type = 0x70c;
    e->lifetime = 40;
    e->position[0] = 18200.0f;
    e->position[1] = 12800.0f;
    e->light[0] = e->light[1] = e->light[2] = 1.0f;
    e->alpha = e->scale = e->field_d8 = 1.0f;
    static mu_combat_quad quads[MU_COMBAT_DECAL_QUADS];
    const int32_t n = decal_quads_scene(c, &scene, 0.0f, quads, MU_COMBAT_DECAL_QUADS);
    assert(n > 49);
    for (int32_t k = 0; k < n; ++k) {
        const int crater = c->bitmaps[quads[k].bitmap].id == 0x7fe9;
        assert(k < 49 ? crater : !crater);   /* size 2.25: 49 tiles first */
        assert(crater ? (quads[k].alpha_test && quads[k].depth_mask && quads[k].src == 0x0302u &&
                         quads[k].dst == 0x0303u && !quads[k].additive)
                      : (!quads[k].alpha_test && !quads[k].depth_mask && quads[k].additive));
    }
    puts("Fire06 0x7f40/1..3, LoadBitmap filter and wrap of the combat bitmaps, the wrappers' GL state and the "
         "crater's alpha test through native routes: OK");
    return 0;
}

int main(int argc, char **argv)
{
    mu_combat *c = calloc(1, sizeof *c);
    assert(c);
    init_env(c);
    bitmaps_without_files(c);
    int code;
    if (argc > 1 && !strcmp(argv[1], "table"))
        code = table();
    else if (argc > 1 && !strcmp(argv[1], "decals"))
        code = decals(c);
    else
        code = self_checks(c);
    free(c);
    return code;
}
