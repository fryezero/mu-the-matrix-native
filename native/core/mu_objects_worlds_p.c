/* RENDER-WORLDS-P: Kethotum create/move through the type's model action table. The move runs after the
 * object's tick, as MoveObject calls the handler slot after its animation step. */
#include "mu_objects_worlds_p.h"
#include "../../reconstructed/objects/worlds_p.h"
#include <string.h>

static int32_t random_value(void *c) { return mu_obj_msvc_rand(&((mu_objects *)c)->rt.seed); }
static float value(uint32_t b) { float f; memcpy(&f, &b, 4); return f; }

/* The view's arrays hold MU_WP_SPEEDS actions; SetAction targets and the read actions are 0..3. */
static int view(mu_objects *o, int32_t t, float *speed, int16_t *keys, mu_wp_model *m)
{
    const mu_object_model *model = t >= 0 && t < MU_OBJECT_TYPES ? o->models[t] : NULL;
    if (!model || !model->loaded)
        return 0;
    int32_t n = model->bmd.action_count;
    if (n > MU_WP_SPEEDS) n = MU_WP_SPEEDS;
    for (int32_t k = 0; k < MU_WP_SPEEDS; ++k) {
        keys[k] = k < n ? (int16_t)model->bmd.actions[k].keys : 0;
        speed[k] = o->rt.wp_speed[t][k];
    }
    m->action_count = n;
    m->speed = speed;
    m->keys = keys;
    return 1;
}

void mu_objects_worlds_p_create(mu_objects *o, int32_t i)
{
    uint8_t *img = mu_objects_object_image(o, i);
    const int32_t t = mu_obj_i32(img, MU_OBJF_TYPE);
    float speed[MU_WP_SPEEDS] = {0};
    int16_t keys[MU_WP_SPEEDS];
    mu_wp_model m = {0, speed, keys};
    /* Without a model the original skips the speed loop; types that scale action 1 would fault there. */
    const int has = view(o, t, speed, keys, &m);
    if (o->world == 0x87) mu_old_kethotum_create(img, o->world, has ? &m : NULL, random_value, o);
    else mu_burning_kethotum_create(img, o->world, has ? &m : &(mu_wp_model){0, speed, keys}, random_value, o);
    if (!has || t < 0 || t >= MU_OBJECT_TYPES)
        return;
    memcpy(o->rt.wp_speed[t], speed, sizeof speed);
    o->rt.wp_speed_set[t] = 1;
}

float mu_objects_worlds_p_speed(const mu_objects *o, int32_t t, int32_t action, int *set)
{
    *set = t >= 0 && t < MU_OBJECT_TYPES && action >= 0 && action < MU_WP_SPEEDS && o->rt.wp_speed_set[t];
    return *set ? o->rt.wp_speed[t][action] : 0.0f;
}

void mu_objects_worlds_p_move(mu_objects *o, int32_t i, const float hero[3])
{
    mu_objects_runtime *rt = &o->rt;
    uint8_t *img = mu_objects_object_image(o, i);
    const int32_t t = mu_obj_i32(img, MU_OBJF_TYPE);
    float speed[MU_WP_SPEEDS];
    int16_t keys[MU_WP_SPEEDS];
    mu_wp_model m;
    const int has = view(o, t, speed, keys, &m);
    if (has && mu_obj_u16(img, MU_OBJF_ACTION) >= MU_WP_SPEEDS) {
        ++rt->move_unsupported;
        return;
    }
    /* No native .ein effect system: the container stays empty and every request is refused. */
    mu_wp_move_inputs in = {o->world, {hero[0], hero[1], hero[2]}, 0.1f /* [0x01cf103c] */, has ? &m : NULL,
                            random_value, o, 0, 0};
    mu_obj_event events[16];
    mu_obj_log log = {0, 16, 0, events};
    if (o->world == 0x87) mu_old_kethotum_move(img, i, &in, &log);
    else mu_burning_kethotum_move(img, i, &in, &log);
    int refused = 0;
    for (int32_t k = 0; k < log.count; ++k) {
        const mu_obj_event *e = &events[k];
        if (e->call == MU_OBJ_CALL_SOUND) {
            ++rt->sound_events;
            if (o->sound) o->sound(o->sound_context, (int32_t)e->args[0]);
        } else if (e->call == MU_OBJ_CALL_ADD_LIGHT && rt->light_count < MU_OBJECT_STEP_LIGHTS) {
            mu_object_light *l = &rt->lights[rt->light_count++];
            l->x = value(e->args[0]);
            l->y = value(e->args[1]);
            for (int q = 0; q < 3; ++q) l->rgb[q] = value(e->args[2 + q]);
            l->range = (int32_t)e->args[5];
            ++rt->light_events;
        } else if (e->call == MU_WP_EIN_EFFECT || e->call == MU_WP_EIN_ATTACH) {
            refused = 1;
        }
    }
    rt->move_unsupported += refused;
}
