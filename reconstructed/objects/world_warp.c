#include "world_warp.h"
#include <math.h>

int mu_world_warp_type(int32_t type) { return type >= 0x1a8 && type <= 0x1ad; }

void mu_world_warp_create(mu_sfx_effect *e, float source_light[3], const mu_sfx_env *env)
{
    e->lifetime = 0xffffff;
    e->blend_mesh = -2;
    if (e->type == 0x1aa || e->type == 0x1ad) {
        e->scale = 0.6f;
        return;
    }
    /* The client clears the caller's light AFTER copying it into the effect. */
    source_light[0] = source_light[1] = source_light[2] = 0.0f;
    e->scale = (float)((env && env->rand ? env->rand(env->context) : 0) % 50) / 100.0f + 1.3f;
    e->gravity = (float)((env && env->rand ? env->rand(env->context) : 0) % 80) / 10.0f;
    e->velocity = (float)((env && env->rand ? env->rand(env->context) : 0) % 100) / 1000.0f + 0.01f;
}

void mu_world_warp_move(mu_sfx_effect *e, float world_time)
{
    if (e->subtype == 0) {
        e->light[0] = (float)sin((double)(world_time * 0.0011f)) * 0.2f + 0.01f;
        e->light[1] = (float)sin((double)(world_time * 0.0017f)) * 0.2f + 0.01f;
        e->light[2] = (float)sin((double)(world_time * 0.0013f)) * 0.2f + 0.01f;
        e->angle[1] = (4.0f + e->gravity) + e->angle[1];
    } else if (e->subtype == 1) {
        const float pulse = (float)sin((double)(world_time * 0.0011f)) * 0.05f;
        e->light[0] = 0.0f + pulse;
        e->light[1] = 0.2f + pulse;
        e->light[2] = 0.1f + pulse;
        e->angle[1] = (2.0f + e->gravity) + e->angle[1];
    }
}

int mu_world_warp_render(mu_sfx_effect *e, const float normal[5][3], const float d[5],
                         int alpha_pass, int model_meshes)
{
    if (!e->live)
        return 0;
    /* TestFrustrum 0x016ccc14 uses five 3D planes, in world units. */
    e->visible = 1;
    for (int k = 0; normal && d && k < 5; ++k) {
        float distance = e->position[0] * normal[k][0];
        distance = distance + e->position[1] * normal[k][1];
        distance = distance + e->position[2] * normal[k][2];
        distance = distance + d[k];
        if (-400.0f > distance) {
            e->visible = 0;
            break;
        }
    }
    if (!e->visible)
        return 0;
    if (alpha_pass && (e->blend_mesh < -2 || e->blend_mesh == -1 || model_meshes < e->blend_mesh))
        return 0;
    return 1; /* RenderObject(o, 0, 0, 0, -1, -1), 0x01518d73 */
}
