/* RENDER-WORLDS-A: Karutan flame bitmaps' create/move branches.
 * Core addresses: 015b8daa,015d3fe3,015d8ecf; 01625b4d,01646370,0164b4f6. */
#include "world_flames.h"
#include "particles_internal.h"
int mu_pt_world_flame_kind(int32_t type, int32_t sub)
{
    return (type == 0x806e && sub == 4) || ((type == 0x8084 || type == 0x8085) && sub == 0);
}
void mu_pt_world_flame_create(mu_pt_particle *p, const mu_pt_host *h, float scale)
{
    p->lifetime = mu_pt_rand(h) % 5 + (p->type == 0x8084 ? 27 : p->type == 0x8085 ? 17 : 12);
    p->scale = (float)(mu_pt_rand(h) % 72 + 72) * 0.01f * scale;
    p->rotation = (float)(mu_pt_rand(h) % 360);
    p->gravity = (float)(mu_pt_rand(h) % 24 + 64) * 0.1f;
    p->alpha = 0;
    p->field_7c = p->light[0];
    p->field_80 = p->light[1];
    p->field_84 = p->light[2];
    p->light[0] = p->light[1] = p->light[2] = 0;
}
void mu_pt_world_flame_move(mu_pt_particle *p, const mu_pt_host *h)
{
    if (p->lifetime < (p->type == 0x8084 ? 15 : 10))
        p->alpha -= 0.2f;
    else if (1.0f > p->alpha)
        p->alpha += (float)(mu_pt_rand(h) % 2 + 2) * 0.1f;
    else
        p->alpha = 1.0f;
    if (0.1f > p->alpha)
        p->live = 0;
    p->light[0] = p->field_7c * p->alpha;
    p->light[1] = p->field_80 * p->alpha;
    p->light[2] = p->field_84 * p->alpha;
    if (p->scale > 0)
        p->scale -= (float)(mu_pt_rand(h) % 3 + (p->type == 0x8084 ? 5 : p->type == 0x8085 ? 7 : 6)) * 0.01f;
    else
        p->live = 0;
    p->position[2] += p->gravity;
    p->rotation += 3.0f;
}
