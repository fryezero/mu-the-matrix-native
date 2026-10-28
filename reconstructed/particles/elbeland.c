/* Elbeland typhoon's clouds 0x7f89/18. Create 0x015ec345, move 0x01660890. */
#include "particles_internal.h"
#include <math.h>
void mu_pt_elbeland_create(mu_pt_particle *p, const mu_pt_host *h)
{
    p->tex_type = 0x7f21;
    p->lifetime = 160;
    p->light[0] = p->light[1] = p->light[2] = 0.0f;
    p->gravity = (float)(mu_pt_rand(h) % 1000);
    p->position[2] = (float)(mu_pt_rand(h) % 80) + p->position[2];
    p->rotation = (float)(mu_pt_rand(h) % 360);
    p->start[0] = (float)(mu_pt_rand(h) % 200 - 10) / 10.0f;
    p->start[1] = (float)(mu_pt_rand(h) % 200 - 10) / 10.0f;
    p->scale = (float)(mu_pt_rand(h) % 70 + 5) * 0.02f;
    float sign = mu_pt_rand(h) % 2 ? 1.0f : -1.0f;
    p->field_7c = sign * ((float)(mu_pt_rand(h) % 40 + 10) / 10000.0f);
    p->field_80 = (float)(mu_pt_rand(h) % 120 + 80);
    p->velocity[0] = p->velocity[1] = p->velocity[2] = 0.0f;
}
void mu_pt_elbeland_move(mu_pt_particle *p, const mu_pt_host *h)
{
    if (p->lifetime > 90) {
        p->light[0] += 0.002f; p->light[1] += 0.002f; p->light[2] += 0.0017f;
    } else if (p->lifetime < 30) {
        p->light[0] -= 0.004f; p->light[1] -= 0.004f; p->light[2] -= 0.0033f;
    }
    if (p->scale > 0.0f) p->scale -= 0.001f;
    if (p->field_80 > 0.0f) p->field_80 -= 0.5f;
    float owner[3] = {0};
    if (h && h->owner_position) h->owner_position(h->context, p->owner, owner);
    float phase = ((h ? h->world_time : 0.0f) + p->rotation) * p->field_7c;
    p->position[0] = (owner[0] + p->start[0]) + (float)cos((double)phase) * p->field_80;
    p->position[1] = (owner[1] + p->start[1]) + (float)sin((double)phase) * p->field_80;
    p->position[2] = (float)(mu_pt_rand(h) % 10) / 10.0f + p->position[2];
}
/* RenderParticles 0x015995aa, before RenderSprite. */
void mu_pt_elbeland_render(mu_pt_particle *p, float time)
{
    if (p->type == MU_PT_BITMAP_CLOUDS && p->subtype == 18)
        p->rotation = (time * 0.02f) * p->field_7c + p->start[1];
}
