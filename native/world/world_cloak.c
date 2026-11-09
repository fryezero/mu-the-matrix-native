/* RENDER-ITEMS-CLOAK / CLOAK-002: the wings' physics capes in the world. See world_cloak.h. */
#include "world_cloak.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/cloth/cloth.h"
#include "../core/mu_meshdraw.h"
#include "../core/mu_lang.h"
#include "../core/mu_raster.h"
#include "../core/mu_textures.h"
#ifndef MU_WORLD_NO_GL
#include "../viewer/gl_backend.h"
#endif
#include "world_rt_internal.h"

#define CLOAK_SLOTS (1 + MU_WORLD_PLAYERS_MAX)

/* The cloth and glow bitmaps of CreateCloth's cases as the client's LoadBitmap calls (0x0185baac) load them: the
 * directory under Data, the file, the filter and the wrap. They are loaded the first time a cloth binds them. */
static const struct {
    int32_t bitmap;
    const char *directory, *name;
    uint32_t filter, wrap;
} cloth_bitmaps[] = {
    {0x790b, "Player", "Robe01.jpg", 0x2600, 0x2900},
    {0x790c, "Player", "Robe02.jpg", 0x2600, 0x2900},
    {0x7912, "Player", "DarklordRobe.tga", 0x2600, 0x2900},
    {0x7914, "Item/Texture", "dl_redwings02.tga", 0x2600, 0x2900},
    {0x7915, "Item/Texture", "dl_redwings03.tga", 0x2600, 0x2900},
    {0x7916, "Item/Texture", "deathha.tga", 0x2600, 0x2900},
    {0x7917, "Item/Texture", "deathjung.tga", 0x2600, 0x2900},
    {0x7918, "Item/Texture", "admangto.tga", 0x2600, 0x2900},
    {0x794c, "Item/Texture", "darklordwing4de.TGA", 0x2601, 0x2901},
    {0x794d, "Item/Texture", "darklordwing4dd.tga", 0x2601, 0x2901},
    {0x794e, "Item/Texture", "darklordwing4de_render.jpg", 0x2601, 0x2901},
    {0x794f, "Item/Texture", "darklordwing4dd_render.JPG", 0x2601, 0x2901},
    {0x7950, "Item/Texture", "ragefighterwing4db.TGA", 0x2601, 0x2901},
    {0x7952, "Item/Texture", "ragefighterwing4db_render.JPG", 0x2601, 0x2901},
    {0x7953, "Item/Texture", "growlancerwing4dc.tga", 0x2601, 0x2901},
    {0x7954, "Item/Texture", "growlancerwing4dc_render.JPG", 0x2601, 0x2901},
    {0x80ed, "Item/Texture", "NCcape.tga", 0x2601, 0x2901},
    {0x80ee, "Item/Texture", "monk_manto01.TGA", 0x2601, 0x2901},
    {0x80ef, "Item/Texture", "monke_manto.TGA", 0x2601, 0x2901},
    {0x81e8, "Item/Texture", "Item801_2_wing.tga", 0x2601, 0x2900},
    {0x81e9, "Item/Texture", "Item802_2_wing.tga", 0x2601, 0x2900},
    {0x830c, "Item/Texture", "season_wing_periodc.tga", 0x2601, 0x2901},
    {0x830d, "Item/Texture", "season_wing_periodc2.tga", 0x2601, 0x2901},
    {0x83f3, "Item/Texture", "kundun_purewhite2.tga", 0x2601, 0x2901},
    {0x83f5, "Item/Texture", "kundun_purewhite2_render.jpg", 0x2601, 0x2901},
    {0x83f6, "Item/Texture", "kundun_innocence2.tga", 0x2601, 0x2901},
    {0x83f7, "Item/Texture", "kundun_sparkle3.tga", 0x2601, 0x2900},
    {0x83f8, "Item/Texture", "kundun_sparkle3_1.tga", 0x2601, 0x2900},
    {0x83fa, "Item/Texture", "kundun_resplendent_6.tga", 0x2601, 0x2900},
    {0x83fb, "Item/Texture", "kundun_resplendent_5.tga", 0x2601, 0x2900},
    {0x842d, "Item/Texture", "kundun_resplendent_6_render.jpg", 0x2601, 0x2900},
    {0x842e, "Item/Texture", "kundun_resplendent_5_render.jpg", 0x2601, 0x2900},
    {0x8469, "Item/Texture", "Ironcloak2.tga", 0x2601, 0x2901},
    {0x846b, "Item/Texture", "BlackCloak_3.tga", 0x2601, 0x2901},
    {0x846c, "Item/Texture", "Desperatecloak3.tga", 0x2601, 0x2900},
    {0x846d, "Item/Texture", "Desperatecloak3_glow.jpg", 0x2601, 0x2900},
    {0x846e, "Item/Texture", "Hatredcloak_3.tga", 0x2601, 0x2900},
    {0x846f, "Item/Texture", "Hatredcloak3_glow.jpg", 0x2601, 0x2900},
    {0x84ec, "Item/Texture", "Fifth_Kundun_cape_03.tga", 0x2601, 0x2900},
    {0x84ed, "Item/Texture", "Fifth_Kundun_cape_04.tga", 0x2601, 0x2900},
    {0x84ee, "Item/Texture", "Fifth_Kundun_cape_04_r.jpg", 0x2601, 0x2900},
    {0x84ef, "Item/Texture", "Fifth_Kundun_cape_05_r.jpg", 0x2601, 0x2900},
    {0x84f1, "Item/Texture", "Fifth_DarkLord_cape_05.tga", 0x2601, 0x2900},
    {0x84f2, "Item/Texture", "Fifth_DarkLord_cape_04.tga", 0x2601, 0x2900},
    {0x84f3, "Item/Texture", "Fifth_DarkLord_cape_03.tga", 0x2601, 0x2900},
    {0x84f4, "Item/Texture", "Fifth_Illusion_cape_03.tga", 0x2601, 0x2900},
    {0x84f5, "Item/Texture", "Fifth_Grow_cape_04.tga", 0x2601, 0x2900},
    {0x84f6, "Item/Texture", "Fifth_Grow_cape_04_r.jpg", 0x2601, 0x2900},
    {0x84f9, "Item/Texture", "Fifth_Rage_Cape_02.tga", 0x2601, 0x2900},
    {0x84fa, "Item/Texture", "Fifth_Rage_Cape_02_Render.JPG", 0x2601, 0x2900},
    {0x8502, "Item/Texture", "Fifth_Darklord_cape_Glow1.jpg", 0x2601, 0x2900},
    {0x8503, "Item/Texture", "Fifth_Darklord_cape_04_r.jpg", 0x2601, 0x2900},
    {0x8504, "Item/Texture", "Fifth_Darklord_cape_05_r.jpg", 0x2601, 0x2900},
    {0x8505, "Item/Texture", "Fifth_Illusion_cape_03_r.jpg", 0x2601, 0x2900},
    {0x8605, "Item/Texture", "blessing_cape_02.tga", 0x2601, 0x2901},
    {0x8607, "Item/Texture", "hope_cape_02.tga", 0x2601, 0x2901},
    {0x8609, "Item/Texture", "sanctuary_cape_02.tga", 0x2601, 0x2901},
    {0x860b, "Item/Texture", "light_cape_02.tga", 0x2601, 0x2901},

    /* CLOAK-003: armour cloths and the mesh level passes, startup registrations. */
    {0x7911, "Monster", "iui06.jpg", 0x2600, 0x2900},
    {0x791d, "Player", "HQskin_Class305_2.tga", 0x2601, 0x2900},
    {0x791e, "Player", "skin_Class405_2.tga", 0x2601, 0x2900},
    {0x791f, "Player", "HQSkinClass110_1.tga", 0x2601, 0x2900},
    {0x7920, "Player", "HQSkinClass310_1.tga", 0x2601, 0x2900},
    {0x7921, "Player", "HQSkinClass410_1.tga", 0x2601, 0x2900},
    {0x7922, "Item/texture", "cotton_Item1125.tga", 0x2601, 0x2900},
    {0x7923, "Item/texture", "cotton_Item1126.tga", 0x2601, 0x2900},
    {0x7924, "Item/texture", "cotton_Item1127.tga", 0x2601, 0x2900},
    {0x7925, "Item/texture", "cotton_Item1132.tga", 0x2601, 0x2900},
    {0x7926, "Item/texture", "cotton_Item1133.tga", 0x2601, 0x2900},
    {0x7927, "Item/texture", "cotton_Item1134.tga", 0x2601, 0x2900},
    {0x7928, "Item/texture", "cotton_Item3100.tga", 0x2601, 0x2900},
    {0x7929, "Item/texture", "cotton_Item3102.tga", 0x2601, 0x2900},
    {0x792a, "Item/texture", "cotton_Item3109.tga", 0x2601, 0x2900},
    {0x792b, "Item/texture", "cotton_Item3113.tga", 0x2601, 0x2900},
    {0x792c, "Item/texture", "cotton_Item1117.tga", 0x2601, 0x2900},
    {0x792d, "Item/texture", "cotton_Item3128.tga", 0x2601, 0x2900},
    {0x792e, "Item/texture", "cotton_Item3138.tga", 0x2601, 0x2900},
    {0x792f, "Item/texture", "Item1151_cotton.tga", 0x2601, 0x2900},
    {0x7930, "Item/texture", "Item1159_cotton.tga", 0x2601, 0x2900},
    {0x7931, "Item/texture", "Item1161_cotton.tga", 0x2601, 0x2900},
    {0x7932, "Item/texture", "Item1174_cotton.tga", 0x2601, 0x2900},
    {0x7933, "Item/texture", "Item1181_slayer_01.tga", 0x2601, 0x2900},
    {0x7948, "Player", "HQlevel_man022_2.tga", 0x2601, 0x2900},
    {0x7949, "Player", "HQSkin_special_02.jpg", 0x2601, 0x2900},
    {0x794a, "Player", "HQSkin_special_03.jpg", 0x2601, 0x2900},
    {0x794b, "Player", "SkinClass404_1.tga", 0x2601, 0x2900},
    {0x7956, "Player", "HQSkinClass109_1.tga", 0x2601, 0x2900},
    {0x7957, "Player", "HQSkinClass309_1.tga", 0x2601, 0x2900},
    {0x7958, "Player", "HQSkinClass409_1.tga", 0x2601, 0x2900},
    {0x7959, "Effect", "cotton_Item1117_render.jpg", 0x2601, 0x2900},
    {0x795a, "Effect", "cotton_Item3102_render.jpg", 0x2601, 0x2900},
    {0x795b, "Player", "HQSkinClass116_1.tga", 0x2601, 0x2900},
    {0x795c, "Player", "HQSkinClass316_1.tga", 0x2601, 0x2900},
    {0x795d, "Player", "HQSkinClass416_1.tga", 0x2601, 0x2900},
    {0x7f1f, "Effect", "Chrome01.jpg", 0x2601, 0x2901},
    {0x7f66, "Effect", "Shiny01.jpg", 0x2601, 0x2900},
    {0x7fcf, "Effect", "Chrome02.jpg", 0x2600, 0x2900},
    {0x8011, "Player", "HQlevel_man021.tga", 0x2601, 0x2900},
    {0x83ef, "Item/texture", "Item1141_Wing1.tga", 0x2601, 0x2900},
    {0x83f0, "Item/texture", "Item1141_Wing2.tga", 0x2601, 0x2900},
    {0x83f1, "Item/texture", "Item1146_1.tga", 0x2601, 0x2900},
    {0x83f2, "Item/texture", "Item1146_2.tga", 0x2601, 0x2900},
};
enum { CLOTH_BITMAPS = (int)(sizeof cloth_bitmaps / sizeof cloth_bitmaps[0]) };

typedef struct cloak_slot {
    int16_t wing;
    uint32_t generation;
    uint32_t stepped;              /* the rendered frame of the last MoveCloth */
    int active;                    /* drawn since its OBJECT was made: stepped by world_cloak_frame every frame */
    int count;
    const mu_character *ch;        /* the character drawn (the hero's, or player list[key - 1]'s model) */
    mu_cloth cloths[MU_CLOTH_WINGS_MAX];
    mu_cloth_armour_in armour_in;
    int armour_count;
    mu_cloth armour[MU_CLOTH_WINGS_MAX];
} cloak_slot;

typedef struct world_cloak {
    mu_cloth_globals g;
    uint32_t wind_at;              /* logic-step counter the wind walk has reached */
    int wind_started;
    cloak_slot *slots[CLOAK_SLOTS];
    mu_textures textures;
    int textures_state;            /* 0 not tried, 1 the specials loaded, -1 failed */
    int32_t slot_of[CLOTH_BITMAPS];   /* -1 not loaded yet, -2 failed */
#ifndef MU_WORLD_NO_GL
    mu_gl_backend gl;
    int gl_ready;                  /* 0 = (re)upload before the next GL draw */
#endif
    world_cloak_stats stats;
} world_cloak;

static world_cloak *cloak_state(mu_world_rt *a)
{
    if (!a->cloak) {
        world_cloak *w = calloc(1, sizeof *w);
        if (!w)
            return NULL;
        mu_cloth_default_globals(&w->g);
        a->cloak = w;
    }
    return a->cloak;
}

static int load_bitmap(mu_world_rt *a, world_cloak *w, int32_t bitmap)
{
    for (int i = 0; i < CLOTH_BITMAPS; ++i) {
        if (cloth_bitmaps[i].bitmap != bitmap)
            continue;
        if (w->slot_of[i] != -1)
            return w->slot_of[i] >= 0;
        w->slot_of[i] = -2;
        char directory[4096];
        snprintf(directory, sizeof directory, "%s/Data/%s", a->root ? a->root : ".", cloth_bitmaps[i].directory);
        const char *dirs[1] = {directory}, *names[1] = {cloth_bitmaps[i].name};
        const int32_t slot = w->textures.count;
        if (mu_textures_add_extras(&w->textures, &bitmap, dirs, names, 1, cloth_bitmaps[i].filter,
                                   cloth_bitmaps[i].wrap))
            return 0;
        w->slot_of[i] = slot;
#ifndef MU_WORLD_NO_GL
        if (w->gl_ready) {   /* a new bitmap: the GL set is uploaded again before the next GL draw */
            mu_gl_release(&w->gl);
            w->gl_ready = 0;
        }
#endif
        return 1;
    }
    return 0;
}

/* The bitmaps a wearer's cloths bind (front, back, glow). 0 when one cannot be loaded. */
static int load_textures(mu_world_rt *a, world_cloak *w, const mu_cloth *cloths, int count)
{
    if (!w->textures_state) {
        w->textures_state = -1;
        for (int i = 0; i < CLOTH_BITMAPS; ++i)
            w->slot_of[i] = -1;
        mu_bmd none;
        memset(&none, 0, sizeof none);
        if (mu_textures_load_specials(&w->textures, &none, NULL))
            return 0;
        w->textures_state = 1;
    }
    if (w->textures_state < 0)
        return 0;
    for (int i = 0; i < count; ++i) {
        if (!cloths[i].owner)
            continue;
        const int32_t bitmaps[4] = {cloths[i].texture_front, cloths[i].texture_back, cloths[i].glow_texture,
                                     cloths[i].glow2_texture};
        for (int k = 0; k < 4; ++k)
            if ((k < 2 || bitmaps[k] != -1) && !load_bitmap(a, w, bitmaps[k]))
                return 0;
        if (cloths[i].mesh != -1)
            for (int k = 0; k < MU_TEXTURE_SPECIAL_COUNT; ++k) {
                const int32_t b = mu_texture_specials[k].index;
                if ((b == 0x7fcf || b == 0x7f66 || b == 0x7f1f) && !load_bitmap(a, w, b))
                    return 0;
            }
    }
    return 1;
}

static int32_t texture_slot(const world_cloak *w, int32_t bitmap)
{
    for (int i = 0; i < CLOTH_BITMAPS; ++i)
        if (cloth_bitmaps[i].bitmap == bitmap)
            return w->slot_of[i] >= 0 ? w->slot_of[i] : -1;
    return -1;
}

/* ---- the GL calls of Render 0x00fd8bc2 onto a render backend: GL_QUADS as two triangles each ---- */

typedef struct cloak_sink {
    const world_cloak *w;
    mu_world_rt *runtime;
    const mu_render_backend *backend;
    mu_meshdraw_state state;
    int32_t texture;
    float rgba[4];
    float uv[4][2], xyz[4][3];
    int corner;
} cloak_sink;

static void s_state(void *context, int32_t wrapper)
{
    cloak_sink *s = context;
    mu_meshdraw_state_defaults(&s->state);
    s->state.texture = 1;
    switch (wrapper) {
    case MU_CLOTH_STATE_ALPHA_TEST:   /* EnableAlphaTest(1) 0x0184a990 (mu_meshdraw.c w_alpha) */
        s->state.blend = 1;
        s->state.src = MU_GL_SRC_ALPHA;
        s->state.dst = MU_GL_ONE_MINUS_SRC_ALPHA;
        s->state.cull = 0;
        s->state.depth_mask = 1;
        s->state.alpha_test = 1;
        break;
    case MU_CLOTH_STATE_BLEND_ONE:    /* EnableAlphaBlend 0x0184aa2b */
        s->state.blend = 1;
        s->state.src = MU_GL_ONE;
        s->state.dst = MU_GL_ONE;
        s->state.cull = 0;
        s->state.depth_mask = 0;
        s->state.alpha_test = 0;
        break;
    default:                          /* DisableAlphaBlend 0x0184a7f3 */
        s->state.blend = 0;
        s->state.cull = 1;
        s->state.depth_mask = 1;
        s->state.alpha_test = 0;
        break;
    }
}

static void s_bind(void *context, int32_t bitmap)
{
    cloak_sink *s = context;
    s->texture = texture_slot(s->w, bitmap);
}

static void s_color4(void *context, float r, float g, float b, float a)
{
    cloak_sink *s = context;
    s->rgba[0] = r;
    s->rgba[1] = g;
    s->rgba[2] = b;
    s->rgba[3] = a;
}

static void s_begin(void *context, uint32_t mode)
{
    (void)mode;   /* GL_QUADS */
    cloak_sink *s = context;
    s->corner = 0;
    s->backend->prepare(s->backend->context, &s->state, s->texture);
    s->backend->begin(s->backend->context);
}

static void s_texcoord(void *context, float u, float v)
{
    cloak_sink *s = context;
    s->uv[s->corner][0] = u;
    s->uv[s->corner][1] = v;
}

static void s_vertex(void *context, float x, float y, float z)
{
    cloak_sink *s = context;
    s->xyz[s->corner][0] = x;
    s->xyz[s->corner][1] = y;
    s->xyz[s->corner][2] = z;
    if (++s->corner < 4)
        return;
    static const int order[6] = {0, 1, 2, 0, 2, 3};
    const mu_meshdraw_sink *k = &s->backend->sink;
    for (int i = 0; i < 6; ++i) {
        k->texcoord(k->context, s->uv[order[i]][0], s->uv[order[i]][1]);
        k->color4(k->context, s->rgba[0], s->rgba[1], s->rgba[2], s->rgba[3]);
        k->vertex(k->context, s->xyz[order[i]]);
    }
    s->corner = 0;
}

static void s_end(void *context)
{
    cloak_sink *s = context;
    s->backend->end(s->backend->context);
}

static void s_sprite(void *context, int32_t bitmap, const float position[3], float scale, const float light[3])
{
    cloak_sink *s = context;
    if (s->runtime->has_particles)
        mu_world_particles_sprite(&s->runtime->particles, bitmap, position, scale, light, MU_PT_NO_OWNER, 0.0f, 0, 4);
}

/* ---- the character's calls ---- */

static void host_of(mu_cloth_host *h, const mu_character *ch, float alpha)
{
    memset(h, 0, sizeof *h);
    h->bones = ch->player_bones;   /* OBJECT +0x318: the Player pose (RenderCharacter poses into the OBJECT's bones) */
    h->bone_count = ch->player_bone_count;
    h->has_model = ch->player_loaded;
    h->body_scale = ch->params.scale;   /* the Player model's BodyScale / BodyOrigin are the OBJECT's at its pose */
    memcpy(h->body_origin, ch->params.position, sizeof h->body_origin);
    memcpy(h->angles, ch->params.angles, sizeof h->angles);
    h->alpha = alpha;
}

static void move_cloth(world_cloak *w, cloak_slot *s, const mu_cloth_host *h)   /* MoveCloth 0x01362f24 */
{
    for (int i = 0; i < s->count + s->armour_count; ++i) {
        mu_cloth *c = i < s->count ? &s->cloths[i] : &s->armour[i - s->count];
        if (!c->owner)
            continue;
        w->stats.steps++;
        if (!mu_cloth_move2(c, h, &w->g, 0.005f, 5)) {
            s->count = s->armour_count = 0;   /* DeleteCloth 0x0137aafe */
            return;
        }
    }
}

static void set_globals(const mu_world_rt *a, world_cloak *w)
{
    w->g.time = a->map ? a->map->time : 0.0f;   /* 0x06fce370 */
    w->g.logic_steps = (int32_t)a->walk.frame.clock.logic_steps;   /* 0x0bdc5eb0 */
    w->g.world = a->world;
}

/* The client's frame driver walks the wind five times in every logic step of every scene from start-up, on the
 * process rand() that WinMain seeds with srand(time) and 18 other srand sites re-seed; no native stream can match it.
 * The stand-in walks from the frame driver's logic step 0 (the runtime's start), so the wind at a frame depends on the
 * steps since start and not on when the first cloth wing came into view. A first catch-up beyond 2^20 logic steps
 * (about 11.6 hours) walks only the last 2^20; later gaps (a stalled frame) walk at most 1000. */
static void wind_catch_up(mu_world_rt *a, world_cloak *w)
{
    const uint32_t steps = a->walk.frame.clock.logic_steps;
    uint32_t cap = 1000;
    if (!w->wind_started) {
        w->wind_at = 0;
        w->wind_started = 1;
        cap = 1u << 20;
    }
    uint32_t n = steps - w->wind_at;
    if (n > cap)
        n = cap;
    for (uint32_t k = 0; k < n; ++k)
        for (int j = 0; j < 5; ++j)   /* the frame driver's five manager steps 0x01851eee..0x01851f07 */
            mu_cloth_wind_step(&w->g);
    w->stats.wind_steps += n;
    w->wind_at = steps;
}

static void armour_inputs(const mu_world_rt *a, int32_t key, const mu_character *ch,
                          const mu_cloth_gate_in *gate, mu_cloth_armour_in *in)
{
    memset(in, 0, sizeof *in);
    in->class_byte = gate->class_byte;
    in->enabled = 1;   /* CreateCharacter 0x0137dbd7 */
    in->class_index = gate->class_index;
    in->wing_type = gate->wing_type;
    in->armour_type = in->pants_type = -1;
    for (int part = 2; part <= 3; ++part) {
        int32_t type = -1;
        int8_t level = 0;
        if (key == WORLD_CLOAK_HERO) {
            if (a->hero_glow_set[part]) {
                type = a->hero_glow[part].type;
                level = (int8_t)a->hero_glow[part].level;
            } else if (ch->items[part].loaded)
                type = mu_renderchar_type_from_path(ch->items[part].path);
        } else if (a->players && key - 1 < a->players->count) {
            const mu_rp_slot *slot = &a->players->list[key - 1].c.slots[part];
            type = slot->type;
            level = (int8_t)slot->level;
        }
        if (part == 2)
            in->armour_type = (int16_t)type;
        else {
            in->pants_type = (int16_t)type;
            in->pants_level = level;
        }
    }
    for (int k = 0; k < 3; ++k)
        in->mesh_color[k] = a->ground ? a->ground->config.glow_color[k] : (k == 0 ? 0.4f : k == 1 ? 0.6f : 1.0f);
    mu_lang_enchant_mesh(a->lang, in->pants_type - 0xae6, mu_cloth_armour_color_mesh(in->pants_type), in->mesh_color);
}

void world_cloak_draw(mu_world_rt *a, int32_t key, uint32_t generation, const mu_character *ch,
                      const mu_cloth_gate_in *gate, int8_t wing_level, uint16_t action, uint16_t prior_action,
                      float alpha, mu_raster *raster, void *batch)
{
    const int16_t wing_type = gate->wing_type;
    if (key < 0 || key >= CLOAK_SLOTS || !ch || !ch->player_loaded)
        return;
    /* CreateCloth's inputs: native characters have no arg 4 (guild war / duel), play in scene 6 and keep sub-type 0. */
    const mu_cloth_wing_in wing_in = {wing_type, wing_level, 0, 6, ch->params.scale};
    mu_cloth_armour_in armour_in;
    armour_inputs(a, key, ch, gate, &armour_in);
    const int eligible = mu_cloth_wing_cloths(&wing_in) || mu_cloth_armour_cloths(&armour_in);
    if (!a->cloak && !eligible)   /* no state (and no report line) before a cloth wing */
        return;
    world_cloak *w = cloak_state(a);
    if (!w)
        return;
    cloak_slot *s = w->slots[key];
    if (!s) {
        if (!eligible)   /* nothing to keep for a wing without a cloth case */
            return;
        s = w->slots[key] = calloc(1, sizeof *s);
        if (!s)
            return;
        s->wing = wing_type;
        s->generation = generation;
    }
    if (s->generation != generation) {
        s->armour_count = 0;
        memset(&s->armour_in, 0, sizeof s->armour_in);
    }
    if (memcmp(&s->armour_in, &armour_in, sizeof armour_in)) {
        s->armour_count = 0;
        s->armour_in = armour_in;
    }
    if (s->wing != wing_type || s->generation != generation) {   /* the OBJECT changed: its cloths go */
        s->count = 0;
        s->active = 0;
        s->wing = wing_type;
        s->generation = generation;
    }
    if (!w->wind_started)
        world_cloak_frame(a);
    set_globals(a, w);
    mu_cloth_host h;
    host_of(&h, ch, alpha);
    s->ch = ch;
    const uint32_t frame = a->walk.frame.clock.frames;
    if (!s->active || s->stepped != frame) {   /* first drawn frame: this frame's MoveCloth has not run */
        move_cloth(w, s, &h);
        s->stepped = frame;
    }
    s->active = 1;
    mu_cloth_gate_in in = *gate;
    in.world = a->world;
    mu_cloth_gate_out out;
    mu_cloth_gate(&in, &out);
    if (!out.render) {
        w->stats.gated++;
        return;
    }
    int created = 0;
    if (s->count == 0) {
        s->count = mu_cloth_wing_create(s->cloths, &wing_in, &h);
        created += s->count;
    }
    if (s->armour_count == 0) {
        s->armour_count = mu_cloth_armour_create(s->armour, &armour_in, &h);
        created += s->armour_count;
    }
    w->stats.created += (uint32_t)created;
    if (created)
        move_cloth(w, s, &h);
    if (!(s->count + s->armour_count) ||
        !mu_cloth_draw_allowed(gate->class_byte, h.subtype, action, prior_action, gate->class_index) ||
        !load_textures(a, w, s->cloths, s->count) || !load_textures(a, w, s->armour, s->armour_count))
        return;
    mu_render_backend backend;
    const mu_image *const *saved = NULL;
    int32_t saved_count = 0;
    const uint32_t *saved_filter = NULL, *saved_wrap = NULL;
    if (raster) {
        saved = raster->textures;
        saved_count = raster->texture_count;
        saved_filter = raster->texture_filter;
        saved_wrap = raster->texture_wrap;
        raster->textures = w->textures.slots;
        raster->texture_count = w->textures.count;
        raster->texture_filter = w->textures.filter;
        raster->texture_wrap = w->textures.wrap;
        mu_raster_backend(raster, &backend);
    } else {
#ifndef MU_WORLD_NO_GL
        if (!w->gl_ready) {
            memset(&w->gl, 0, sizeof w->gl);
            mu_gl_upload(&w->gl, &w->textures, 0);
            w->gl_ready = 1;
        }
        w->gl.batch = batch;
        mu_gl_backend_bind(&w->gl, &backend);
#else
        (void)batch;
        return;
#endif
    }
    cloak_sink sink;
    memset(&sink, 0, sizeof sink);
    sink.w = w;
    sink.runtime = a;
    sink.backend = &backend;
    sink.texture = -1;
    mu_meshdraw_state_defaults(&sink.state);
    mu_cloth_sink cs = {&sink, s_state, s_bind, s_color4, s_begin, s_texcoord, s_vertex, s_end, s_sprite};
    for (int i = 0; i < s->count; ++i)
        if (s->cloths[i].owner && mu_cloth_render(&s->cloths[i], &h, &w->g, out.light, &cs) == MU_CLOTH_OK)
            w->stats.drawn++;
    if (mu_cloth_armour_draw_allowed(gate->class_byte, h.subtype))
        for (int i = 0; i < s->armour_count; ++i)
            if (s->armour[i].owner && mu_cloth_render(&s->armour[i], &h, &w->g, NULL, &cs) == MU_CLOTH_OK)
                w->stats.drawn++;
    if (raster) {
        raster->textures = saved;
        raster->texture_count = saved_count;
        raster->texture_filter = saved_filter;
        raster->texture_wrap = saved_wrap;
    }
}

/* 1 while the slot's character is still drawn with the OBJECT its cloths were made for. */
static int slot_live(const mu_world_rt *a, int key, const cloak_slot *s)
{
    if (key == WORLD_CLOAK_HERO)
        return a->has_character && s->ch == &a->ch;
    const int32_t i = key - 1;
    if (!a->players || i >= a->players->count)
        return 0;
    const mu_world_player *q = &a->players->list[i];
    return s->ch == &q->model && q->creates == s->generation && mu_world_players_alpha(a->players, i) > 0.0f;
}

void world_cloak_frame(mu_world_rt *a)
{
    world_cloak *w = a->cloak;
    if (!w)
        return;
    wind_catch_up(a, w);
    set_globals(a, w);
    const uint32_t frame = a->walk.frame.clock.frames;
    for (int key = 0; key < CLOAK_SLOTS; ++key) {   /* RenderCharacter's MoveCloth 0x0136ab80 of this frame */
        cloak_slot *s = w->slots[key];
        if (!s || !s->active)
            continue;
        if (!slot_live(a, key, s)) {
            s->active = 0;
            continue;
        }
        if (s->count + s->armour_count == 0 || s->stepped == frame)
            continue;
        mu_cloth_host h;
        host_of(&h, s->ch, 1.0f);
        move_cloth(w, s, &h);
        if (mu_cloth_armour_update(s->armour, s->armour_count, &s->armour_in, &h))
            move_cloth(w, s, &h);
        s->stepped = frame;
    }
}

void world_cloak_reset(mu_world_rt *a)
{
    world_cloak *w = a->cloak;
    if (!w)
        return;
    for (int i = 0; i < CLOAK_SLOTS; ++i) {
        free(w->slots[i]);
        w->slots[i] = NULL;
    }
}

void world_cloak_gl_teardown(mu_world_rt *a)
{
#ifndef MU_WORLD_NO_GL
    world_cloak *w = a->cloak;
    if (w && w->gl_ready) {
        mu_gl_release(&w->gl);
        w->gl_ready = 0;
    }
#else
    (void)a;
#endif
}

void world_cloak_free(mu_world_rt *a)
{
    world_cloak *w = a->cloak;
    if (!w)
        return;
    world_cloak_reset(a);
    mu_textures_free(&w->textures);
    free(w);
    a->cloak = NULL;
}

void world_cloak_stats_get(const mu_world_rt *a, world_cloak_stats *out)
{
    memset(out, 0, sizeof *out);
    const world_cloak *w = a->cloak;
    if (!w)
        return;
    *out = w->stats;
    out->wind = w->g.wind;
}
