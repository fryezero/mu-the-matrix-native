/* The legacy particle list: CreateParticle, MoveParticles, RenderParticles
 * (NATIVE-PARTICLE-001). See particles.h. */
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "particles.h"
#include "world_flames.h"
#include "particles_internal.h"
#include "../record-math/record_math.h"

int32_t mu_pt_rand(const mu_pt_host *h)
{
    return h && h->rand ? h->rand(h->context) : 0;
}

static void copy3(float d[3], const float s[3])
{
    d[0] = s[0];
    d[1] = s[1];
    d[2] = s[2];
}

int mu_pt_kind_supported(int32_t type, int32_t subtype)
{
    switch (type) {
    case MU_PT_BITMAP_FIRE:
        return (subtype >= 0 && subtype <= 6) || subtype == 17;
    case MU_PT_BITMAP_SMOKE:
        return subtype == 0 || subtype == 1 || subtype == 2 || (subtype >= 3 && subtype <= 8 && subtype != 5) || subtype == 0x75 || subtype == 0x7f || subtype == 21;
    case MU_PT_BITMAP_SPARK2:
        return subtype == 0 || subtype == 1 || subtype == 2;   /* 2: Inferno; 1: NATIVE-HELPERS-002 (the angel's sparkles) */
    case 0x7f54: return subtype == 0;          /* Explosion01, Meteorite and Inferno */
    case MU_PT_BITMAP_SMOKE5:
    case MU_PT_BITMAP_SMOKE2:
    case MU_PT_BITMAP_DROP:
        return subtype == 0;                   /* NATIVE-HELPERS-002 (the mounts' dust) */
    case MU_PT_BITMAP_RAIN_SPLASH:
    case MU_PT_BITMAP_RAIN_RING:
        return subtype == 0;
    case MU_PT_BITMAP_THUNDER:
        return subtype == 0;
    case MU_PT_BITMAP_FLARE:
        return subtype == 0 || subtype == 1;   /* 0: Icarus; NATIVE-FIDELITY-002: Icarus's cloud puffs */
    case MU_PT_BITMAP_SPARK3:
        return subtype == 0 || subtype == 1 || subtype == 11 || subtype == 0xf || subtype == 0x2a;   /* 0xf: NATIVE-HELPERS-002 (Fenrir) */
    case 0x831d: case 0x83b3: return subtype == 6;
    case 0x8086: return subtype == 0x13 || subtype == 0x18;
    case MU_PT_BITMAP_CLOUDS:
        return (subtype >= 0 && subtype <= 5) || subtype == 0x14 || subtype == 18;
    case MU_PT_BITMAP_WATERFALL1:
        return subtype == 2;
    case MU_PT_BITMAP_SHINY1:
        return subtype == 0 || subtype == 1;
    case MU_PT_BITMAP_WATERFALL2:
        return subtype == 2;
    case MU_PT_BITMAP_WATERFALL3:
        return subtype == 0xe;
    case 0x8016:
    case MU_PT_BITMAP_FANTA_B:
        return subtype == 0;
    case MU_PT_BITMAP_CHASELLIGHT:
        return subtype == 5;
    default:
        return mu_pt_world_flame_kind(type, subtype);
    }
}

/* 0x011ff622: the client's quantised random range, with each SSE intermediate rounded to float. */
static float rand_range(const mu_pt_host *h, float lo, float hi, int32_t steps)
{
    const int32_t a = mu_pt_cvttss2si((float)steps * lo), b = mu_pt_cvttss2si((float)steps * hi);
    float r = (float)(mu_pt_rand(h) % (b - a + 1) + a) / (float)steps;
    if (lo > r) r = lo;
    else if (r > hi) r = hi;
    return r;
}

/* ---------------------------------------------------------------- wrapper */

/* 0x010954d4: the kinds world 0x8b never drops. */
static int drop_exempt(int32_t type)
{
    switch (type) {
    case 0x7f26: case 0x7f3c: case 0x7f3d: case 0x7f5a: case 0x7f5b: case 0x7f5d: case 0x7ffd:
    case 0x801c: case 0x801d: case 0x801e: case 0x8067: case 0x807e: case 0x807f: case 0x8080:
    case 0x8086: case 0x8087: case 0x8089:
        return 1;
    default:
        return 0;
    }
}

int mu_pt_wrapper_keeps(const mu_pt_host *h, int32_t type, int32_t subtype)
{
    (void)subtype;
    if (!h || h->world != 0x8b)   /* 0x00da9d49 */
        return 1;
    int32_t divisor = h->drop_divisor > 0 ? h->drop_divisor : 1;
    int32_t r = mu_pt_rand(h) % divisor;
    if (drop_exempt(type))
        r = 0;
    return r == 0;
}

/* ---------------------------------------------------------------- create */

static void owner_position(mu_pt_particle *p, const mu_pt_host *h)
{
    if (p->owner == MU_PT_NO_OWNER) {
        p->owner_position[0] = p->owner_position[1] = p->owner_position[2] = 0.0f;   /* 0x00cfcf7b */
        return;
    }
    float o[3] = {0.0f, 0.0f, 0.0f};
    if (h && h->owner_position)
        h->owner_position(h->context, p->owner, o);
    p->owner_position[0] = o[0];
    p->owner_position[1] = o[1];
    p->owner_position[2] = o[2];
    p->owner_position[2] = h && h->terrain_height ? h->terrain_height(h->context, p->owner_position[0],
                                                                       p->owner_position[1])
                                                  : 0.0f;
}

#include "icarus_clouds.inc"

int mu_pt_create_record(mu_pt_particle *p, const mu_pt_host *h, int32_t type, const float position[3],
                        const float angle[3], const float light[3], int32_t subtype, float scale, int32_t owner,
                        int32_t arg8)
{
    /* common initialisation 0x015ae7e4..0x015aebed */
    p->live = 1;
    p->type = type;
    p->tex_type = type;
    p->subtype = subtype;
    copy3(p->position, position);
    copy3(p->start, position);
    copy3(p->light, light);
    p->scale = scale;
    p->gravity = 0.0f;
    p->lifetime = 2;
    p->frame = 0;
    p->owner = owner;
    p->rotation = 0.0f;
    p->moving = 1;
    p->time = 0.0f;
    p->arg8 = arg8;
    copy3(p->angle, angle);
    copy3(p->start_angle, angle);
    p->velocity[0] = p->velocity[1] = p->velocity[2] = 0.0f;
    owner_position(p, h);
    if (!mu_pt_kind_supported(type, subtype))
        return 0;

    if (mu_pt_world_flame_kind(type, subtype)) {
        mu_pt_world_flame_create(p, h, scale);
        return 1;
    }
    switch (type) {
    case MU_PT_BITMAP_FIRE:
        /* 0x015ba585, subtype table 0x01616318 */
        if (subtype == 0) {                         /* 0x015ba5b3 */
            p->lifetime = 24;
            p->velocity[0] = 0.0f;
            p->velocity[1] = -(float)(mu_pt_rand(h) % 16 + 32) * 0.1f;
            p->velocity[2] = 0.0f;
            p->scale = (float)(mu_pt_rand(h) % 64 + 128) * 0.01f;
            p->rotation = (float)(mu_pt_rand(h) % 360);
        } else if (subtype == 1) {                  /* 0x015ba6cb */
            p->lifetime = 24;
            p->velocity[0] = 0.0f;
            p->velocity[1] = -(float)(mu_pt_rand(h) % 16 + 32) * 0.1f;
            p->velocity[2] = 0.0f;
            p->scale = (float)(mu_pt_rand(h) % 4 + 10) * 0.01f;
            p->rotation = (float)(mu_pt_rand(h) % 360);
        } else if (subtype == 5 || subtype == 17) { /* 0x015ba7e1 */
            p->lifetime = subtype == 17 ? 10 : 24;
            p->velocity[0] = 0.0f;
            p->velocity[1] = -(float)(mu_pt_rand(h) % 16 + 32) * 0.1f;
            p->velocity[2] = 0.0f;
            p->scale = (float)(mu_pt_rand(h) % 64 + 128) * scale * 0.01f;
            p->rotation = (float)(mu_pt_rand(h) % 360);
        } else {                                    /* default 0x015bb3c0 (2, 3, 4, 6) */
            p->lifetime = 24;
            p->velocity[0] = 0.0f;
            p->velocity[1] = -(float)(mu_pt_rand(h) % 32 - 16) * 0.1f;
            p->velocity[2] = 0.0f;
            p->rotation = (float)(mu_pt_rand(h) % 360);
        }
        break;
    case MU_PT_BITMAP_SMOKE:
        /* 0x015c4c55, subtype table 0x016163a0 */
        if (subtype == 21) { /* 0x015c6a19 */
            p->lifetime = 80;
            p->scale = (float)(mu_pt_rand(h) % 64 + 64) * p->scale * 0.005f;
            p->rotation = (float)(mu_pt_rand(h) % 360);
            p->gravity = (float)(mu_pt_rand(h) % 32 + 60) * 0.1f;
        } else if (subtype == 0x7f) {                      /* 0x015cbdb4 */
            p->lifetime = p->initial_lifetime = 100;
            p->scale = rand_range(h, 50.0f, 100.0f, 1) * 0.01f * scale;
            p->alpha = 1.0f;
            p->rotation = rand_range(h, 0.0f, 360.0f, 1);
        } else if (subtype == 0x75) {                     /* Ghost Horse breath, 0x015cb3da */
            p->lifetime = 16;
            p->scale = (float)(mu_pt_rand(h) % 32 + 48) * scale * 0.01f;
            p->angle[0] = (float)(mu_pt_rand(h) % 360);
            p->rotation = (float)(mu_pt_cvttss2si(h ? h->world_time : 0.0f) % 360);
        } else if (subtype == 0 || subtype == 4) {         /* 0x015c4c7b */
            p->lifetime = 16;
            p->scale = (float)(mu_pt_rand(h) % 32 + 48) * 0.01f;   /* (type 0x844 would take rand % 3 + 28) */
            p->angle[0] = (float)(mu_pt_rand(h) % 360);
            p->rotation = (float)(mu_pt_cvttss2si(h ? h->world_time : 0.0f) % 360);
        } else if (subtype == 6) {                  /* 0x015c639e */
            p->lifetime = 30;
            p->gravity = (float)(mu_pt_rand(h) % 1000);
            p->scale = (float)(mu_pt_rand(h) % 20 + 180) * 0.01f;
            p->position[0] = (float)(mu_pt_rand(h) % 200 - 100) * scale + p->position[0];
            p->position[1] = (float)(mu_pt_rand(h) % 200 - 100) * scale + p->position[1];
            p->position[2] = (float)(mu_pt_rand(h) % 20 + 20) + p->position[2];
            p->rotation = p->position[2];
        } else if (subtype == 7) {                  /* 0x015c657d */
            p->lifetime = 30;
            p->velocity[1] = (float)(mu_pt_rand(h) % 4 + 6) * p->scale;
            p->gravity = (float)(mu_pt_rand(h) % 200) / 200.0f;
            p->scale = ((float)(mu_pt_rand(h) % 20 + 120) * 0.01f) * p->scale;
            p->rotation = (float)(mu_pt_rand(h) % 360);
        } else if (subtype == 8) {                  /* 0x015c66df */
            p->lifetime = 24;
            p->velocity[1] = -(float)(mu_pt_rand(h) % 8 + 32) * 0.3f;
            p->scale *= 0.8f;
            p->rotation = (float)(mu_pt_rand(h) % 360);
        } else if (subtype == 1) {                  /* 0x015c5f15: Poison burst */
            p->lifetime = 50;
            p->scale = (float)(mu_pt_rand(h) % 32 + 80) * 0.01f;
            p->position[0] += (float)(mu_pt_rand(h) % 64 - 32);
            p->position[1] += (float)(mu_pt_rand(h) % 64 - 32);
            p->position[2] += (float)(mu_pt_rand(h) % 64 + 32);
            p->angle[0] = (float)(mu_pt_rand(h) % 90 - 45);
            p->angle[2] = (float)(mu_pt_rand(h) % 360);
            p->velocity[1] = -(float)(mu_pt_rand(h) % 8 + 40);
        } else if (subtype == 3) {                  /* 0x015c5a12 */
            p->lifetime = 10;
            p->scale = (float)(mu_pt_rand(h) % 32 + 80) * 0.01f;
            p->angle[0] = (float)(mu_pt_rand(h) % 90 - 45);
            p->angle[2] = (float)(mu_pt_rand(h) % 360);
            p->velocity[0] = 0.0f;
            p->velocity[1] = -(float)(mu_pt_rand(h) % 8 + 40);
            p->velocity[2] = 0.0f;
        } else {                                    /* 2: 0x015c6146 */
            p->lifetime = 50;
            p->scale = (float)(mu_pt_rand(h) % 64 + 64) * 0.01f;
            p->rotation = (float)(mu_pt_rand(h) % 360);
            p->gravity = (float)(mu_pt_rand(h) % 32 + 60) * 0.1f;
        }
        break;
    case MU_PT_BITMAP_RAIN_SPLASH:
    case MU_PT_BITMAP_RAIN_RING:
        /* 0x015bd5eb, the default branch 0x015bd943 */
        p->lifetime = 20;
        p->scale = (float)(mu_pt_rand(h) % 6 + 8) * 0.1f;
        for (int k = 0; k < 3; ++k)
            p->position[k] = (float)(mu_pt_rand(h) % 10 - 5) * 1.0f + p->position[k];
        break;
    case MU_PT_BITMAP_SPARK2: {
        /* 0x015dc098, subtype 0 */
        float m[12], v[3];
        p->scale = (float)(mu_pt_rand(h) % 4 + 4) * 0.1f;
        if (subtype == 1) {
            /* NATIVE-HELPERS-002: subtype 1 skips every listed subtype's block (0x015dc0e3..0x015dd30f) and
             * takes the shared LifeTime 0x015dd424 */
            p->lifetime = mu_pt_rand(h) % 8 + 8;
            break;
        }
        p->lifetime = mu_pt_rand(h) % 16 + 24;
        p->angle[2] = (float)(mu_pt_rand(h) % 360);
        mu_angle_matrix(p->angle, m);
        p->gravity = (float)(mu_pt_rand(h) % 16 + 6);
        v[0] = 0.0f;
        v[1] = (float)(mu_pt_rand(h) % 20 + 20) * 0.1f;
        v[2] = 0.0f;
        if (subtype == 2) {                        /* 0x015dc299 */
            p->scale *= 2.0f;
            for (int k = 0; k < 3; ++k) v[k] = 3.0f * v[k];
        }
        mu_vector_rotate(v, m, p->velocity);
        break;
    }
    case 0x7f54:                                   /* 0x015e42eb */
        p->lifetime = 20;
        if (h && h->scene_state != 3 && h->sound) h->sound(h->context, 0x40);
        break;
    case MU_PT_BITMAP_FLARE:
        if (subtype == 0) {                        /* 0x015eec34 */
            p->lifetime = mu_pt_rand(h) % 10 + 10;
            p->gravity = (float)(mu_pt_rand(h) % 10) + 10.0f;
            p->scale = (((float)(mu_pt_rand(h) % 50) + 50.0f) / 100.0f) * scale;
        } else {
            /* 0x015eee83, subtype 1 */
            p->lifetime = 50;
        }
        break;
    case MU_PT_BITMAP_THUNDER:
        /* 0x015bda75 */
        p->scale = (float)(mu_pt_rand(h) % 8 + 6) * scale * 0.1f;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->gravity = 20.0f;
        break;
    case MU_PT_BITMAP_SPARK3:
        if (subtype == 0x2a) {                      /* 0x015e14bf */
            p->lifetime = p->initial_lifetime = 30;
            p->scale = rand_range(h, 0.5f, 1.0f, 100) * scale;
            p->initial_scale = p->scale;
            p->alpha = 1.0f;
            p->rotation = rand_range(h, 0.0f, 360.0f, 1);
            p->position[0] += rand_range(h, -10.0f, 10.0f, 1);
            p->position[1] += rand_range(h, -10.0f, 10.0f, 1);
            p->position[2] += rand_range(h, -10.0f, 10.0f, 1);
            break;
        }
        if (subtype == 11) { /* 0x015de226..0x015de357, weapon sparks */
            p->alpha = 1.0f;
            p->velocity[0] = (float)(mu_pt_rand(h) % 8) - 4.0f;
            p->velocity[1] = (float)(mu_pt_rand(h) % 4);
            p->velocity[2] = (float)(mu_pt_rand(h) % 4);
            p->lifetime = 30; /* Spark03/11 */
            p->scale = (float)(mu_pt_rand(h) % 5) / 10.0f + 1.0f;
            break;
        }
        /* 0x015dd48c; subtype 1: 0x015dd4c7 */
        if (subtype == 0xf) {
            /* NATIVE-HELPERS-002, 0x015de866: one in three lives 35 steps and falls; the others keep the common
             * LifeTime 2 (and the record's former alpha +0x44) */
            if (mu_pt_rand(h) % 3 == 0) {
                p->alpha = 1.0f;
                p->lifetime = 0x23;
                p->velocity[2] = -((float)(mu_pt_rand(h) % 5) + 5.0f) * 0.5f;
            }
        } else if (subtype == 1) {
            float m[12];
            static const float burst[3] = {0.0f, -50.0f, 0.0f};
            p->angle[0] = (float)(mu_pt_rand(h) % 360);
            p->angle[1] = (float)(mu_pt_rand(h) % 360);
            p->angle[2] = (float)(mu_pt_rand(h) % 360);
            mu_angle_matrix(p->angle, m);
            mu_vector_rotate(burst, m, p->velocity);
        }
        break;
    case MU_PT_BITMAP_SMOKE5:
    case MU_PT_BITMAP_SMOKE2: {
        /* NATIVE-HELPERS-002, 0x015ccbd4 (shared with 0x7f5e), subtype 0: a puff pushed along the angle */
        float m[12];
        static const float push[3] = {0.0f, 3.0f, 0.0f};
        p->lifetime = 0x20;
        p->position[0] = (float)(mu_pt_rand(h) % 16 - 8) + p->position[0];
        p->position[1] = (float)(mu_pt_rand(h) % 16 - 8) + p->position[1];
        p->scale = (float)(mu_pt_rand(h) % 32 + 32) * 0.01f * scale;
        mu_angle_matrix(angle, m);                  /* 0x015ccd50: the argument's angle */
        mu_vector_rotate(push, m, p->velocity);
        p->angle[0] = (float)(mu_pt_rand(h) % 360);
        break;
    }
    case MU_PT_BITMAP_DROP:
        /* NATIVE-HELPERS-002, 0x015b7799 (Atlans' drop01), subtype 0 */
        p->lifetime = mu_pt_rand(h) % 10 + 0x1e;
        p->scale = (float)(mu_pt_rand(h) % 6 + 4) * 0.03f;
        p->light[0] = p->light[1] = p->light[2] = 1.0f;
        break;
    case MU_PT_BITMAP_SHINY1:
        /* 0x015e5c73: subtypes 0 and 1 */
        p->lifetime = 18;
        p->angle[0] = 45.0f;
        break;
    case 0x831d:                                   /* 0x0160702e */
        p->lifetime = p->initial_lifetime = 30;
        p->scale = rand_range(h, 0.5f, 1.0f, 100) * scale;
        p->alpha = 1.0f;
        p->rotation = rand_range(h, 0.0f, 360.0f, 1);
        p->velocity[1] = rand_range(h, 0.0f, 100.0f, 1);
        {
            float len = (float)sqrt((double)(p->velocity[1] * p->velocity[1]));
            p->velocity[1] = 1e-6f > len ? 0.0f : p->velocity[1] / len;
        }
        for (int k = 0; k < 3; ++k)
            p->velocity[k] = rand_range(h, 2.5f, 5.0f, 10) * p->velocity[k];
        break;
    case 0x83b3:                                   /* 0x015d0491 */
        p->lifetime = p->initial_lifetime = 40;
        p->alpha = 1.0f;
        p->rotation = rand_range(h, 0.0f, 360.0f, 1);
        break;
    case 0x8086:
        if (subtype == 0x18) {                     /* 0x015d61fa */
            p->lifetime = p->initial_lifetime = 30;
            p->scale = rand_range(h, 0.5f, 1.0f, 100) * scale;
            p->initial_scale = p->scale;
            p->alpha = 1.0f;
            p->rotation = rand_range(h, 0.0f, 360.0f, 1);
            p->position[0] += rand_range(h, -5.0f, 5.0f, 1);
            p->position[1] += rand_range(h, -5.0f, 5.0f, 1);
            p->position[2] += rand_range(h, 0.0f, 5.0f, 1);
            p->velocity[2] = rand_range(h, 1.0f, 5.0f, 10);
            break;
        }
        /* 0x015d5863 */
        p->lifetime = mu_pt_rand(h) % 5 + 27;
        p->scale = (float)(mu_pt_rand(h) % 72 + 52) * scale * 0.01f;
        p->rotation = (float)(mu_pt_rand(h) % 180);
        p->gravity = (float)(mu_pt_rand(h) % 14 + 44) * 0.05f;
        p->alpha = 0.0f;
        p->field_7c = light[0]; p->field_80 = light[1]; p->field_84 = light[2];
        p->light[0] = p->light[1] = p->light[2] = 0.0f;
        break;
    case MU_PT_BITMAP_CLOUDS:
        if (subtype == 18) { mu_pt_elbeland_create(p, h); break; }
        if (subtype <= 5) { mu_pt_icarus_cloud_create(p, h, scale); break; }
        /* 0x015ea60e, subtype 0x14 0x015ec9de: a slow mist sheet around the position */
        p->lifetime = 300;
        p->gravity = (float)(mu_pt_rand(h) % 1000);
        p->alpha = 0.1f;
        p->position[0] = (float)(mu_pt_rand(h) % 500 - 250) + p->position[0];
        p->position[1] = (float)(mu_pt_rand(h) % 500 - 250) + p->position[1];
        p->position[2] = (float)(mu_pt_rand(h) % 20 - 20) + p->position[2];
        p->start[1] = (float)(mu_pt_rand(h) % 100) / 100.0f;
        p->start[2] = p->position[2];
        p->scale = (float)(mu_pt_rand(h) % 20 + 180) * 0.01f * p->scale;
        p->field_7c = (float)(mu_pt_rand(h) % 10) / 100.0f;
        p->velocity[0] = p->velocity[1] = p->velocity[2] = 0.0f;
        break;
    case MU_PT_BITMAP_WATERFALL1:
        /* 0x015f1a27, subtype 2 0x015f1bb0: falling spray */
        p->lifetime = 30;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->velocity[2] = (float)(-(mu_pt_rand(h) % 5 + 7));
        p->light[0] = p->light[1] = p->light[2] = 0.2f;
        p->scale = 1.6f + scale;
        break;
    case MU_PT_BITMAP_WATERFALL2:
        /* NATIVE-CHARSEL-002. 0x015f27cb: every subtype; subtype 2 0x015f281f; the tail 0x015f2b24 */
        p->lifetime = 30;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->lifetime = 40;
        p->scale = (float)(mu_pt_rand(h) % 6 + 6) * 0.1f + scale;
        p->velocity[2] = (float)(-(mu_pt_rand(h) % 3 + 3));
        if (h && h->scene_state == 5) {             /* 0x009b0bc1(SceneFlag) == 5: the character select */
            p->light[0] = p->light[1] = p->light[2] = 0.25f;
        } else {                                    /* (subtype 7 keeps the argument light) */
            p->light[0] = p->light[1] = p->light[2] = 0.4f;
        }
        p->position[0] = ((float)(mu_pt_rand(h) % 20) - 10.0f) + p->position[0];
        p->position[1] = ((float)(mu_pt_rand(h) % 20) - 10.0f) + p->position[1];
        p->position[2] = ((float)(mu_pt_rand(h) % 40) - 20.0f) + p->position[2];
        break;
    case MU_PT_BITMAP_WATERFALL3:
        /* 0x015f34b8: no case among 0..3, 0xc, 0x10..0x19; the second chain 0x015f4466, subtype 0xe
         * 0x015f4e42, then the position jitter 0x015f5079 */
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->scale = (float)(mu_pt_rand(h) % 10 + 10) * 0.02f;
        p->lifetime = 30;
        p->velocity[2] = (float)(mu_pt_rand(h) % 5 + 5);
        p->scale = (float)(mu_pt_rand(h) % 10 + 10) * 0.05f * scale;
        p->position[0] = ((float)(mu_pt_rand(h) % 40) - 20.0f) + p->position[0];
        p->position[1] = ((float)(mu_pt_rand(h) % 40) - 20.0f) + p->position[1];
        p->position[2] = ((float)(mu_pt_rand(h) % 20) - 10.0f) + p->position[2];
        break;
    case 0x8016:
    case MU_PT_BITMAP_FANTA_B:
        /* 0x015f1549, subtype 0 (none of 5..9): 0x015f1743, 0x015f1827 */
        p->lifetime = 24;
        p->velocity[0] = (float)(mu_pt_rand(h) % 10 - 5) * 0.4f;
        p->velocity[1] = 0.0f;
        p->velocity[2] = (float)(mu_pt_rand(h) % 10 + 5) * 0.2f;
        copy3(p->start, p->position);
        break;
    case MU_PT_BITMAP_CHASELLIGHT:
        /* 0x015b53a8: not 0..3 -> 0x015b55a6; subtype 5 0x015b57d1 draws Impack03 */
        p->lifetime = mu_pt_rand(h) % 3 + 20;
        p->position[0] = (float)(mu_pt_rand(h) % 50 - 25) + p->position[0];
        p->position[1] = (float)(mu_pt_rand(h) % 50 - 25) + p->position[1];
        p->position[2] = ((float)(mu_pt_rand(h) % 200 - 100) + 250.0f) + p->position[2];
        p->tex_type = MU_PT_BITMAP_IMPACK03;
        p->scale = (float)(mu_pt_rand(h) % 10 + 20) * 0.01f * 1.3f;
        p->gravity = (float)(mu_pt_rand(h) % 10 + 20) * 0.05f * 1.3f;
        p->position[1] = (float)(mu_pt_rand(h) % 130 - 65) + p->position[1];
        p->position[2] = (float)(mu_pt_rand(h) % 130) + position[2];   /* the argument's z */
        break;
    default:
        break;
    }
    return 1;
}

/* ---------------------------------------------------------------- move */

int mu_pt_move_record(mu_pt_particle *p, const mu_pt_host *h)
{
    /* loop head 0x01616f12: records without life are erased */
    if (p->lifetime <= 0 || !p->live)
        return 0;
    if (p->moving) {
        /* MovePosition 0x012af52d(position, angle, velocity) */
        float m[12], d[3];
        mu_angle_matrix(p->angle, m);
        mu_vector_rotate(p->velocity, m, d);
        p->position[0] = p->position[0] + d[0];
        p->position[1] = p->position[1] + d[1];
        p->position[2] = p->position[2] + d[2];
    }
    if (p->owner != MU_PT_NO_OWNER)
        owner_position(p, h);   /* 0x01616fee..0x01617071 */
    int supported = mu_pt_kind_supported(p->type, p->subtype);
    if (supported) {
        if (mu_pt_world_flame_kind(p->type, p->subtype))
            mu_pt_world_flame_move(p, h);
        else switch (p->type) {
        case MU_PT_BITMAP_FIRE:
            /* 0x016282c9, subtype table 0x0168f278 */
            p->gravity = p->gravity + 0.004f;
            if (p->subtype == 0 || p->subtype == 5 || p->subtype == 6 || p->subtype == 17) {
                p->scale = p->scale - 0.04f;                 /* 0x016282f7 / 0x016283eb */
                if (p->subtype != 0)
                    p->rotation = p->rotation + 5.0f;
            } else {                                         /* 1..4: 0x016296f0 */
                p->scale = p->scale + p->gravity;
                for (int k = 0; k < 3; ++k)
                    p->velocity[k] = 0.98f * p->velocity[k];
            }
            p->frame = (23 - p->lifetime) / 6;
            p->position[2] = p->gravity * 10.0f + p->position[2];
            break;
        case MU_PT_BITMAP_SMOKE:
            /* 0x016333e0, subtype table 0x0168f2fc */
            if (p->subtype == 21) { /* 0x016366eb */
                p->light[0] = p->light[1] = p->light[2] = (float)p->lifetime / 50.0f;
                p->gravity -= 0.1f;
                p->position[0] -= p->gravity * 0.2f;
                p->position[2] += p->gravity;
                p->scale -= 0.01f;
            } else if (p->subtype == 0x7f) {                        /* 0x0163e8e0 */
                if (p->lifetime < p->initial_lifetime / 2)
                    p->alpha -= 1.0f / (float)(p->initial_lifetime / 2);
                p->scale += 0.03f;
            } else if (p->subtype == 0x75) {                     /* 0x0163dddb -> AngleToVector 0x00d015d5 */
                float matrix[12], direction[3];
                const float forward[3] = {0.0f, -1.0f, 0.0f};
                mu_angle_matrix(p->angle, matrix);
                mu_vector_rotate(forward, matrix, direction);
                float length = (float)sqrt((double)(direction[0] * direction[0] + direction[1] * direction[1] + direction[2] * direction[2]));
                if (length != 0.0f) {
                    const float inverse = 1.0f / length;
                    for (int k = 0; k < 3; ++k) direction[k] *= inverse;
                }
                for (int k = 0; k < 3; ++k) p->position[k] += direction[k];
                p->scale += 0.01f;
            } else if (p->subtype == 0) {                           /* 0x01633411 */
                float l = (float)p->lifetime / 8.0f;
                p->light[0] = p->light[1] = p->light[2] = l;
                p->gravity = p->gravity + 0.2f;
                p->position[2] = p->position[2] + p->gravity;
                p->scale = p->scale + 0.05f;
            } else if (p->subtype == 4) {                    /* 0x01635535 */
                float l = (float)p->lifetime / 8.0f;
                p->light[0] = (l * 120.0f) / 255.0f;
                p->light[1] = (l * 100.7f) / 255.0f;
                p->light[2] = (l * 80.0f) / 255.0f;
                p->gravity += 0.2f;
                p->position[2] += p->gravity;
                p->scale += 0.05f;
            } else if (p->subtype == 6) {                    /* 0x0163583a */
                p->lifetime = 10;
                float t = (h ? h->world_time : 0.0f) + p->gravity;
                float angle = t / 5000.0f;
                p->position[2] = (float)sin((double)angle) * 20.0f + p->rotation;
                t = p->gravity + (h ? h->world_time : 0.0f);
                angle = ((float)(mu_pt_cvttss2si(t) % 1800) * 0.1f) * 0.01745329238474369f;
                p->scale = (float)sin((double)angle) * 0.5f + 1.8f;
                p->light[0] = 0.6f * 0.6f; p->light[1] = 0.6f * 0.5f; p->light[2] = 0.6f * 0.4f;
            } else if (p->subtype == 7) {                    /* 0x01635a07 */
                float l = 1.0f;
                p->scale += 0.03f; p->gravity += 1.0f; p->velocity[1] -= 0.1f;
                p->position[2] -= p->gravity;
                if (p->lifetime < 5) { l = (float)p->lifetime / 8.0f; p->scale -= 0.1f; }
                p->light[0] = l * 0.725f; p->light[1] = l * 0.572f; p->light[2] = l * 0.333f;
            } else if (p->subtype == 8) {                    /* 0x01635bf9 */
                p->gravity += 0.02f;
                if (p->lifetime > 5) {
                    p->scale += p->gravity;
                    p->position[2] = p->gravity * 20.0f + p->position[2];
                    for (int k = 0; k < 3; ++k) p->velocity[k] = 1.05f * p->velocity[k];
                    float l = (float)p->lifetime / 24.0f;
                    p->light[0] = p->light[1] = p->light[2] = l;
                    for (int k = 0; k < 3; ++k) p->velocity[k] = 0.4f * p->velocity[k];
                } else {
                    for (int k = 0; k < 3; ++k) { p->light[k] /= 2.0f; p->velocity[k] = 0.0f; }
                }
            } else if (p->subtype == 1) {                    /* 0x01634dc5 */
                float l = (float)p->lifetime / 50.0f;
                p->light[0] = l * 0.5f;
                p->light[1] = l;
                p->light[2] = l * 0.8f;
                for (int k = 0; k < 3; ++k)
                    p->velocity[k] = 0.4f * p->velocity[k];
                p->scale += 0.05f;
            } else if (p->subtype == 3) {                    /* 0x0163402e */
                float l = (float)p->lifetime / 8.0f;
                p->light[0] = l * 0.8f;
                p->light[1] = l * 0.8f;
                p->light[2] = l;
                for (int k = 0; k < 3; ++k)
                    p->velocity[k] = 0.4f * p->velocity[k];
                p->scale = p->scale + 0.1f;
            } else {                                         /* 2: 0x01634fa9 */
                float l = (float)p->lifetime / 50.0f;
                p->light[0] = p->light[1] = p->light[2] = l;
                p->gravity = p->gravity - 0.1f;
                p->position[0] = p->position[0] - p->gravity * 0.2f;
                p->position[2] = p->position[2] + p->gravity;
                p->scale = p->scale - 0.01f;
            }
            break;
        case MU_PT_BITMAP_RAIN_SPLASH:
        case MU_PT_BITMAP_RAIN_RING:
            /* 0x0162b9ee; world 0x22 (0x00dabe97) sets the light first and does not fade it */
            if (h && h->world == 0x22) {
                p->light[0] = 1.0f;
                p->light[1] = 1.0f;
                p->light[2] = 0.7f;
                if (p->lifetime <= 0)
                    p->live = 0;
                p->scale = p->scale + 0.03f;
            } else {
                if (p->lifetime <= 0)
                    p->live = 0;
                p->scale = p->scale + 0.03f;
                for (int k = 0; k < 3; ++k)
                    p->light[k] = p->light[k] - 0.05f;
            }
            break;
        case MU_PT_BITMAP_SPARK2: {
            /* 0x0165006b, subtype 0: fade, fall, bounce off the terrain, and the velocity once more */
            float l = (float)p->lifetime / 16.0f;
            p->light[0] = p->light[1] = p->light[2] = l;
            p->position[2] = p->position[2] + p->gravity;
            p->gravity = p->gravity - 2.0f;
            float ground = h && h->terrain_height ? h->terrain_height(h->context, p->position[0], p->position[1])
                                                  : 0.0f;
            if (ground > p->position[2]) {
                p->position[2] = ground;
                p->gravity = -p->gravity * 0.6f;
                p->lifetime = p->lifetime - 4;
            }
            for (int k = 0; k < 3; ++k)
                p->position[k] = p->position[k] + p->velocity[k];
            break;
        }
        case 0x7f54: {                            /* 0x01622ea1..0x01623c2e */
            p->frame = (20 - p->lifetime) / 2;
            float l = (float)p->lifetime / 20.0f;
            const float light[3] = {l * 0.5f, l * 0.3f, l * 0.1f};
            if (h && h->light) h->light(h->context, p->position[0], p->position[1], light, 4);
            break;
        }
        case MU_PT_BITMAP_FLARE:
            if (p->subtype == 0) {                 /* 0x01662886..0x016635a8 */
                float drift[3];
                drift[0] = (float)(mu_pt_rand(h) % 2001 - 1000) * 0.0004000000189989805f;   /* client 0x39d1b718, one ULP above 0.0004f */
                drift[1] = (float)(mu_pt_rand(h) % 2001 - 1000) * 0.0004000000189989805f;   /* client 0x39d1b718, one ULP above 0.0004f */
                drift[2] = 0.0f;
                for (int k = 0; k < 3; ++k) {
                    drift[k] = (drift[k] + (h ? h->wind_sum[k] : 0.0f)) * 0.5f;
                    p->position[k] += drift[k];
                }
                p->position[2] = 5.0f * 0.5f + p->position[2];
                p->scale -= 0.05f;
                p->light[0] = p->light[1] = p->light[2] = p->scale;
                if (0.1f >= p->scale) { p->live = 0; p->lifetime = -1; }
                break;
            }
            /* 0x016635ad, subtype 1: dims and shrinks */
            for (int k = 0; k < 3; ++k)
                p->light[k] = 0.9f * p->light[k];
            p->scale = p->scale * 0.95f;
            break;
        case MU_PT_BITMAP_THUNDER:
            /* 0x0162bedc */
            p->rotation = p->rotation + p->gravity;
            break;
        case MU_PT_BITMAP_SPARK3:
            if (p->subtype == 0x2a) {                        /* 0x01655100 */
                p->scale -= p->initial_scale / (float)p->initial_lifetime;
                p->alpha -= 1.0f / (float)p->initial_lifetime;
                p->velocity[0] += rand_range(h, -0.6f, 0.6f, 10);
                p->velocity[1] += rand_range(h, 0.3f, 0.8f, 10);
                p->velocity[2] += rand_range(h, -0.2f, 0.8f, 10);
                break;
            }
            if (p->subtype == 11) { /* 0x01651b78..0x01651ca6 */
                for (int k = 0; k < 3; ++k)
                    p->light[k] /= 1.05f;
                p->scale -= 0.04f;
                p->alpha -= 0.001f;
                if (!(0.0f < p->alpha))
                    p->live = 0;
                break;
            }
            if (p->subtype == 0xf) {
                /* NATIVE-HELPERS-002, 0x01651f36: dims, and dies when its alpha runs out */
                for (int k = 0; k < 3; ++k)
                    p->light[k] = p->light[k] / 1.05f;
                p->alpha = p->alpha - 0.001f;
                if (!(0.0f < p->alpha))
                    p->live = 0;
                break;
            }
            /* 0x01650bde: 0x01650c17 / 0x01650c74 */
            p->scale = p->scale - (p->subtype == 1 ? 2.0f : 0.5f);
            if (0.2f > p->scale)
                p->live = 0;
            break;
        case MU_PT_BITMAP_SMOKE5:
    case MU_PT_BITMAP_SMOKE2: {
            /* NATIVE-HELPERS-002, 0x01658099, subtype 0: fades over 32 steps, grows, drifts and slows, and sits
             * on the terrain by half its height */
            float l = (float)p->lifetime / 32.0f;
            p->light[0] = p->light[1] = p->light[2] = l;
            p->scale = p->scale + 0.08f;
            for (int k = 0; k < 3; ++k)
                p->position[k] = p->position[k] + p->velocity[k];
            for (int k = 0; k < 3; ++k)
                p->velocity[k] = 0.9f * p->velocity[k];
            float ground = h && h->terrain_height ? h->terrain_height(h->context, p->position[0], p->position[1])
                                                  : 0.0f;
            float bh = h && h->bitmap_height ? h->bitmap_height(h->context, p->type) : 0.0f;
            p->position[2] = ground + bh * p->scale * 0.5f;
            break;
        }
        case MU_PT_BITMAP_DROP:
            /* NATIVE-HELPERS-002, 0x0162267d, subtype 0: the next sheet cell and a jitter, rising */
            p->frame = p->frame + 1;
            p->position[0] = (float)(mu_pt_rand(h) % 20 - 10) * 2.5f * p->scale + p->position[0];
            p->position[1] = (float)(mu_pt_rand(h) % 20 - 10) * 2.5f * p->scale + p->position[1];
            p->position[2] = (float)(mu_pt_rand(h) % 20 + 10) * 2.5f * p->scale + p->position[2];
            break;
        case MU_PT_BITMAP_SHINY1:
            /* 0x016599cd: the size follows a sine of the lifetime; subtype 1 smaller and spinning */
            p->scale = (float)sin((double)((float)p->lifetime * 10.0f * 0.017453292f));
            if (p->subtype == 1) {
                p->scale = p->scale * 0.75f;
                p->rotation = p->rotation - 12.0f;
            }
            break;
        case 0x831d: case 0x83b3:                   /* 0x01680db5 / 0x016434ed */
            if (p->lifetime < p->initial_lifetime / 2)
                p->alpha -= 1.0f / (float)(p->initial_lifetime / 2);
            p->scale += 0.02f;
            break;
        case 0x8086:
            if (p->subtype == 0x18) {              /* 0x016496de */
                p->position[0] += rand_range(h, -1.0f, 1.0f, 10);
                p->position[1] += rand_range(h, -1.0f, 1.0f, 10);
                p->position[2] += rand_range(h, 0.0f, 1.0f, 10);
                p->alpha = (float)p->lifetime / (float)p->initial_lifetime;
                p->scale -= p->initial_scale / (float)p->initial_lifetime;
                break;
            }
            /* 0x01648a22 */
            if (p->lifetime >= 15) {
                if (1.0f > p->alpha)
                    p->alpha += (float)(mu_pt_rand(h) % 2 + 2) * 0.1f;
                else p->alpha = 1.0f;
            } else {
                p->alpha -= 0.2f;
            }
            if (0.1f > p->alpha) p->live = 0;
            p->light[0] = p->field_7c * p->alpha;
            p->light[1] = p->field_80 * p->alpha;
            p->light[2] = p->field_84 * p->alpha;
            if (p->scale > 0.0f)
                p->scale -= (float)(mu_pt_rand(h) % 3 + 2) * 0.01f;
            else
                p->live = 0;
            p->position[2] += p->gravity;
            break;
        case MU_PT_BITMAP_CLOUDS:
            if (p->subtype == 18) { mu_pt_elbeland_move(p, h); break; }
            if (p->subtype <= 5) { mu_pt_icarus_cloud_move(p, h); break; }
            /* 0x01660fb1, subtype 0x14: rises and brightens for its first 150 steps, then sinks and fades */
            if (!(p->lifetime > 0)) {
                p->live = 0;
            } else if (p->lifetime > 150) {
                if (1.0f > p->alpha)
                    p->alpha = (float)((double)p->alpha + 0.04);
                p->position[2] = p->position[2] + 1.0f;
            } else {
                if (p->alpha > 0.1f)
                    p->alpha = p->alpha - 0.025f;
                p->position[2] = p->position[2] - 0.5f;
            }
            break;
        case MU_PT_BITMAP_WATERFALL1:
            /* 0x01667c6f, subtype 2: shrinks, flares up and fades, falls slower */
            p->scale = p->scale - 0.005f;
            if (p->lifetime < 5) {
                for (int k = 0; k < 3; ++k)
                    p->light[k] = p->light[k] / 1.2f;
            } else if (p->lifetime > 20) {
                for (int k = 0; k < 3; ++k)
                    p->light[k] = p->light[k] * 1.1f;
            }
            p->velocity[2] = p->velocity[2] + 0.1f;
            break;
        case MU_PT_BITMAP_WATERFALL2:
            /* NATIVE-CHARSEL-002. 0x01668bbd (not subtype 5) 0x01668de1: grows, drifts, fades below 10 */
            p->scale = p->scale + 0.03f;
            p->velocity[0] = (float)(mu_pt_rand(h) % 20 - 10) * 0.1f;
            p->velocity[1] = (float)(mu_pt_rand(h) % 20 - 10) * 0.1f;
            p->velocity[2] = p->velocity[2] + 0.1f;
            if (p->lifetime < 10)
                for (int k = 0; k < 3; ++k)
                    p->light[k] = p->light[k] / 1.1f;
            break;
        case MU_PT_BITMAP_WATERFALL3:
            /* 0x016696f4, subtype 0xe 0x0166a631, then the common tail 0x0166b810 (not subtype 0x11) */
            p->scale = p->scale + 0.05f;
            p->velocity[2] = p->velocity[2] - 0.6f;
            for (int k = 0; k < 3; ++k)
                p->light[k] = p->light[k] / 1.1f;
            p->scale = p->scale + 0.005f;
            p->velocity[2] = p->velocity[2] - 2.5f;
            for (int k = 0; k < 3; ++k)
                p->light[k] = p->light[k] / 1.1f;
            break;
        case 0x8016:
        case MU_PT_BITMAP_FANTA_B:
            /* 0x016672be, subtype 0 0x01667872: shrinks, slows, rises, fades over 25 steps */
            p->scale = p->scale - 0.02f;
            if (0.0f > p->scale)
                p->scale = 0.0f;
            p->velocity[0] = p->velocity[0] * 0.95f;
            p->velocity[1] = p->velocity[1] * 0.95f;
            p->position[2] = p->position[2] + 1.0f;
            p->light[0] = (float)p->lifetime / 25.0f;
            p->light[1] = p->light[0];
            p->light[2] = p->light[0];
            break;
        case MU_PT_BITMAP_CHASELLIGHT:
            /* 0x0161d91f, subtype 5: brightens from 10 steps up, fades below; rises by its gravity */
            if (p->lifetime >= 10) {
                for (int k = 0; k < 3; ++k)
                    p->light[k] = p->light[k] * 1.05f;
            } else {
                for (int k = 0; k < 3; ++k)
                    p->light[k] = p->light[k] / 1.16f;
            }
            p->position[2] = p->position[2] + p->gravity;
            break;
        default:
            break;
        }
    }
    /* tail 0x0168ee31 */
    p->lifetime = p->lifetime - 1;
    p->time = p->time + (h ? h->frame_time : 0.0f);
    return supported ? 1 : 2;
}

/* ---------------------------------------------------------------- render */

static void state(mu_pt_render_call *c, int32_t wrapper, int32_t argument)
{
    if (c->state_count < 4) {
        c->state[c->state_count] = wrapper;
        c->state_arg[c->state_count] = argument;
        c->state_count++;
    }
}

int mu_pt_render_record(mu_pt_particle *p, const mu_pt_bitmap *b, uint8_t mode, float world_time, int32_t ordinal, mu_pt_render_call *out)
{
    memset(out, 0, sizeof *out);
    /* 0x015912e9: the height filters of the two split passes */
    if (mode == 1 && p->position[2] > 350.0f)
        return 0;
    if (mode == 2 && 300.0f >= p->position[2])
        return 0;
    if (!mu_pt_kind_supported(p->type, p->subtype))
        return 2;
    /* 0x01591363 */
    const float width = b->width * p->scale, height = b->height * p->scale;
    if (b->components == 3)
        state(out, MU_PT_STATE_ADD, 0);
    else
        state(out, MU_PT_STATE_ALPHA, 0);
    mu_pt_sprite_call *s = &out->sprite;
    s->bitmap = p->tex_type;
    copy3(s->position, p->position);
    copy3(s->light, p->light);
    s->width = width;
    s->height = height;
    s->rotation = p->rotation;
    s->u = 0.0f;
    s->v = 0.0f;
    s->uw = 1.0f;
    s->vh = 1.0f;
    s->axes = 4;
    switch (p->type) {
    case MU_PT_BITMAP_FIRE:
        /* 0x015978bb (subtypes 5, 17: the record's rotation) / 0x01597adf (the angle's x) */
        s->width = width * 0.25f;
        s->rotation = (p->subtype == 5 || p->subtype == 17) ? p->rotation : p->angle[0];
        s->u = (float)(p->frame % 4) * 0.25f;
        s->uw = 0.25f;
        break;
    case MU_PT_BITMAP_SMOKE:
        if (p->subtype == 6) s->rotation = 0.0f;
        if (p->subtype == 0x7f)
            for (int k = 0; k < 3; ++k) s->light[k] = p->light[k] * p->alpha;
        if (p->subtype == 2 || p->subtype == 21)
            state(out, MU_PT_STATE_SUBTRACT, 0);     /* 0x01596e05 */
        break;
    case MU_PT_BITMAP_SMOKE5:
    case MU_PT_BITMAP_SMOKE2:
        state(out, MU_PT_STATE_BLEND, 0);            /* NATIVE-HELPERS-002, 0x01596f41 */
        break;
    case 0x7f54:                                   /* 0x015925e6, 4x4 explosion sheet */
        s->rotation = 0.0f;
        s->u = (float)(p->frame % 4) * 0.25f + 0.005f;
        s->v = (float)(p->frame / 4) * 0.25f + 0.005f;
        s->uw = s->vh = 0.24f;
        break;
    case MU_PT_BITMAP_DROP: {
        /* NATIVE-HELPERS-002, 0x01592374: cell frame % 9 of a 3x3 sheet (0.24 wide, 0.005 inset), upright */
        int32_t cell = p->frame % 9;
        s->rotation = 0.0f;
        s->u = (float)(cell % 3) * 0.25f + 0.005f;
        s->v = (float)(cell / 3) * 0.25f + 0.005f;
        s->uw = 0.24f;
        s->vh = 0.24f;
        break;
    }
    case 0x8086:
        if (p->subtype == 0x18)
            for (int k = 0; k < 3; ++k) s->light[k] = p->light[k] * p->alpha;
        break;
    case 0x831d: case 0x83b3:
        for (int k = 0; k < 3; ++k) s->light[k] = p->light[k] * p->alpha;
        break;
    case MU_PT_BITMAP_SPARK3:
        if (p->subtype == 0x2a)
            for (int k = 0; k < 3; ++k) s->light[k] = p->light[k] * p->alpha;
        break;
    case MU_PT_BITMAP_CLOUDS:
        if (p->subtype == 18) { mu_pt_elbeland_render(p, world_time); s->rotation = p->rotation; break; }
        /* 0x01599675 (subtypes 8, 9, 0x14): the light times the record's alpha */
        if (p->subtype == 0 || p->subtype == 3) {
            float rate = p->subtype == 3 || ordinal % 2 == 0 ? 0.02f : -0.02f;
            s->rotation = (world_time * rate) * p->field_7c + p->start[1];
        }
        if (p->subtype == 0x14)
            for (int k = 0; k < 3; ++k)
                s->light[k] = p->light[k] * p->alpha;
        break;
    default:
        break;
    }
    out->sprites = 1;
    return 1;
}

/* ---------------------------------------------------------------- list */

int mu_pt_system_init(mu_pt_system *s, int32_t capacity)
{
    memset(s, 0, sizeof *s);
    if (capacity <= 0)
        return 1;
    s->records = calloc((size_t)capacity, sizeof *s->records);
    if (!s->records)
        return 1;
    s->capacity = capacity;
    return 0;
}

void mu_pt_system_free(mu_pt_system *s)
{
    free(s->records);
    memset(s, 0, sizeof *s);
}

void mu_pt_system_clear(mu_pt_system *s)
{
    s->count = 0;
}

int mu_pt_create(mu_pt_system *s, const mu_pt_host *h, int32_t type, const float position[3], const float angle[3],
                 const float light[3], int32_t subtype, float scale, int32_t owner, int32_t arg8)
{
    if (!mu_pt_wrapper_keeps(h, type, subtype)) {
        s->dropped++;
        return 0;
    }
    mu_pt_particle p;
    memset(&p, 0, sizeof p);
    if (!mu_pt_create_record(&p, h, type, position, angle, light, subtype, scale, owner, arg8)) {
        s->unsupported++;
        return 0;
    }
    if (s->count >= s->capacity) {
        s->overflow++;
        return 0;
    }
    s->records[s->count++] = p;   /* push_back 0x01691232 */
    s->created++;
    return 1;
}

void mu_pt_wind_step(mu_pt_system *s, const mu_pt_host *h)
{
    /* 0x01616ca7: wind[i] += (rand() % 2001 - 1000) * 0.0006, clamped to +-0.6 */
    for (int i = 0; i < 2; ++i) {
        float w = (float)(mu_pt_rand(h) % 2001 - 1000) * 0.0006f + s->wind[i];
        s->wind[i] = w;
        float c = 0.6f > s->wind[i] ? s->wind[i] : 0.6f;
        s->wind[i] = -0.6f > c ? -0.6f : (0.6f > s->wind[i] ? s->wind[i] : 0.6f);
    }
    /* 0x01616dbf: wind_sum[i] += wind[i], clamped to +-1.7 */
    for (int i = 0; i < 2; ++i) {
        s->wind_sum[i] = s->wind_sum[i] + s->wind[i];
        float c = 1.7f > s->wind_sum[i] ? s->wind_sum[i] : 1.7f;
        s->wind_sum[i] = -1.7f > c ? -1.7f : (1.7f > s->wind_sum[i] ? s->wind_sum[i] : 1.7f);
    }
}

void mu_pt_move_all(mu_pt_system *s, const mu_pt_host *h)
{
    mu_pt_wind_step(s, h);
    mu_pt_host step_host;
    if (h) step_host = *h; else memset(&step_host, 0, sizeof step_host);
    step_host.wind_sum[0] = s->wind_sum[0]; step_host.wind_sum[1] = s->wind_sum[1];
    step_host.wind_sum[2] = 0.0f;
    h = &step_host;
    int32_t kept = 0;
    for (int32_t i = 0; i < s->count; ++i) {
        mu_pt_particle p = s->records[i];
        if (!mu_pt_move_record(&p, h))
            continue;   /* erased (0x01616f36..0x01616f77) */
        s->records[kept++] = p;
    }
    s->count = kept;
}

int32_t mu_pt_render_all(const mu_pt_system *s, uint8_t mode, const float camera[12], float world_time, mu_pt_bitmap_fn bitmap,
                         void *bitmap_context, const mu_pt_gl *gl)
{
    int32_t drawn = 0;
    for (int32_t i = 0; i < s->count; ++i) {
        mu_pt_particle *p = &s->records[i];
        if (!p->live)
            continue;
        mu_pt_bitmap b;
        if (!bitmap || !bitmap(bitmap_context, p->tex_type, &b))
            continue;
        mu_pt_render_call c;
        if (mu_pt_render_record(p, &b, mode, world_time, i, &c) != 1)
            continue;
        for (int32_t k = 0; k < c.state_count; ++k)
            if (gl && gl->state)
                gl->state(gl->context, c.state[k], c.state_arg[k]);
        if (c.sprites) {
            mu_pt_render_sprite(camera, &c.sprite, b.components, gl);
            drawn++;
        }
    }
    return drawn;
}
