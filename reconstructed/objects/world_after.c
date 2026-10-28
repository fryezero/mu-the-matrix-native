/* RenderObjects_AfterCharacter 0x016d6949. Bounded to the four A worlds;
 * login/character select retain their existing handlers. */
#include "../terrain/terrain.h"
#include "world_visual_internal.h"
int mu_noria_defer(uint8_t *);
int mu_elbeland_defer(uint8_t *);
int mu_raklion_defer(uint8_t *);
int mu_karutan_defer(uint8_t *);
int mu_elbeland_after(uint8_t *, int32_t, float, mu_obj_log *);
void mu_elbeland_after_sprites(const uint8_t *, int32_t, mu_world_bone_fn, void *, mu_obj_log *);
int mu_raklion_after(uint8_t *, int32_t, float, mu_obj_log *);
int mu_karutan_after(uint8_t *, int32_t, float, mu_obj_log *);
int mu_world_after_enabled(int32_t w)
{
    return w == 3 || w == 0x33 || w == 0x39 || w == 0x3a || w == 0x50 || w == 0x51;
}
int mu_world_defer(uint8_t *o, int32_t w)
{
    if (w == 3)
        return mu_noria_defer(o);
    if (w == 0x33)
        return mu_elbeland_defer(o);
    if (w == 0x39 || w == 0x3a)
        return mu_raklion_defer(o);
    if (w == 0x50 || w == 0x51)
        return mu_karutan_defer(o);
    return 0;
}
/* The four worlds' branches of 0x017fe909. This predicate is tested BEFORE
 * sector visibility/live/+0xa by the original second pass. */
int mu_world_after_special(const uint8_t *o, int32_t w)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    return (w == 3 && t == 0x13) || (w == 0x33 && t == 0x59) || ((w == 0x39 || w == 0x3a) && t == 0x4c);
}
int mu_world_after_pass(mu_obj_world *w, const mu_obj_render_inputs *in, int32_t *counter, mu_obj_log *log)
{
    if (!mu_world_after_enabled(in->world))
        return MU_OBJ_UNSUPPORTED;
    if (counter) {
        if (*counter > 40)
            *counter = 0;
        ++*counter;
    }
    for (int32_t i = 0; i < 16; ++i)
        for (int32_t j = 0; j < 16; ++j) {
            const int32_t s = i * 16 + j;
            w->block_visible[s] = (uint8_t)mu_terrain_test_frustum_2d(
                in->x2d, in->y2d, in->scene_state, (float)(i * 16 + 8), (float)(j * 16 + 8), -180.0f);
            for (int32_t k = w->head[s]; k >= 0; k = w->next[k]) {
                uint8_t *o = w->objects[k];
                const float x = mu_obj_f32(o, MU_OBJF_POSITION) * 0.01f,
                            y = mu_obj_f32(o, MU_OBJF_POSITION + 4) * 0.01f;
                /* The special predicate has its own, wider per-world frustum test. */
                const int special = mu_world_after_special(o, in->world) &&
                                    mu_terrain_test_frustum_2d(in->x2d, in->y2d, in->scene_state, x, y,
                                                               in->world == 0x33 ? -400.0f : -600.0f);
                if (!special && ((!w->block_visible[s] && !in->top_view) || !o[MU_OBJF_LIVE] ||
                                 o[MU_OBJF_AFTER_CHARACTER] != 1))
                    continue;
                o[MU_OBJF_VISIBLE] = (uint8_t)mu_terrain_test_frustum_2d(in->x2d, in->y2d, in->scene_state, x,
                                                                         y, mu_obj_f32(o, MU_OBJF_RANGE));
                if (special || o[MU_OBJF_VISIBLE] || in->top_view) {
                    const uint32_t a[3] = {0, 0, 0};
                    wv_emit(log, MU_OBJ_CALL_AFTER_DRAW, k, a, 3);
                }
            }
        }
    return MU_OBJ_OK;
}
int mu_world_after_render(uint8_t *o, int32_t i, int32_t w, float time, mu_obj_log *l, mu_world_bone_fn bone,
                          void *c)
{
    if (w == 3 && mu_obj_i32(o, MU_OBJF_TYPE) == 0x13) {
        wv_body(o, i, l);
        return MU_OBJ_OK;
    }
    if (w == 0x33) {
        int status = mu_elbeland_after(o, i, time, l);
        mu_elbeland_after_sprites(o, i, bone, c, l);
        return status;
    }
    if (w == 0x39 || w == 0x3a)
        return mu_raklion_after(o, i, time, l);
    if (w == 0x50 || w == 0x51)
        return mu_karutan_after(o, i, time, l);
    return MU_OBJ_UNSUPPORTED;
}
