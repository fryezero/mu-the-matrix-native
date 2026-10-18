/* The legacy particle list: CreateParticle, MoveParticles, RenderParticles
 * (NATIVE-PARTICLE-001). See particles.h. */
#include <stdlib.h>
#include <string.h>

#include "particles.h"
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
        return subtype == 0 || subtype == 2;
    case MU_PT_BITMAP_RAIN_SPLASH:
    case MU_PT_BITMAP_RAIN_RING:
        return subtype == 0;
    case MU_PT_BITMAP_THUNDER:
        return subtype == 0;
    case MU_PT_BITMAP_SPARK3:
        return subtype == 0 || subtype == 1;
    default:
        return 0;
    }
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
        if (subtype == 0) {                         /* 0x015c4c7b */
            p->lifetime = 16;
            p->scale = (float)(mu_pt_rand(h) % 32 + 48) * 0.01f;   /* (type 0x844 would take rand % 3 + 28) */
            p->angle[0] = (float)(mu_pt_rand(h) % 360);
            p->rotation = (float)(mu_pt_cvttss2si(h ? h->world_time : 0.0f) % 360);
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
    case MU_PT_BITMAP_THUNDER:
        /* 0x015bda75 */
        p->scale = (float)(mu_pt_rand(h) % 8 + 6) * scale * 0.1f;
        p->rotation = (float)(mu_pt_rand(h) % 360);
        p->gravity = 20.0f;
        break;
    case MU_PT_BITMAP_SPARK3:
        /* 0x015dd48c; subtype 1: 0x015dd4c7 */
        if (subtype == 1) {
            float m[12];
            static const float burst[3] = {0.0f, -50.0f, 0.0f};
            p->angle[0] = (float)(mu_pt_rand(h) % 360);
            p->angle[1] = (float)(mu_pt_rand(h) % 360);
            p->angle[2] = (float)(mu_pt_rand(h) % 360);
            mu_angle_matrix(p->angle, m);
            mu_vector_rotate(burst, m, p->velocity);
        }
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
        switch (p->type) {
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
            if (p->subtype == 0) {                           /* 0x01633411 */
                float l = (float)p->lifetime / 8.0f;
                p->light[0] = p->light[1] = p->light[2] = l;
                p->gravity = p->gravity + 0.2f;
                p->position[2] = p->position[2] + p->gravity;
                p->scale = p->scale + 0.05f;
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
        case MU_PT_BITMAP_THUNDER:
            /* 0x0162bedc */
            p->rotation = p->rotation + p->gravity;
            break;
        case MU_PT_BITMAP_SPARK3:
            /* 0x01650bde: 0x01650c17 / 0x01650c74 */
            p->scale = p->scale - (p->subtype == 1 ? 2.0f : 0.5f);
            if (0.2f > p->scale)
                p->live = 0;
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

int mu_pt_render_record(const mu_pt_particle *p, const mu_pt_bitmap *b, uint8_t mode, mu_pt_render_call *out)
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
        if (p->subtype == 2)
            state(out, MU_PT_STATE_SUBTRACT, 0);     /* 0x01596e05 */
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
    int32_t kept = 0;
    for (int32_t i = 0; i < s->count; ++i) {
        mu_pt_particle p = s->records[i];
        if (!mu_pt_move_record(&p, h))
            continue;   /* erased (0x01616f36..0x01616f77) */
        s->records[kept++] = p;
    }
    s->count = kept;
}

int32_t mu_pt_render_all(const mu_pt_system *s, uint8_t mode, const float camera[12], mu_pt_bitmap_fn bitmap,
                         void *bitmap_context, const mu_pt_gl *gl)
{
    int32_t drawn = 0;
    for (int32_t i = 0; i < s->count; ++i) {
        const mu_pt_particle *p = &s->records[i];
        if (!p->live)
            continue;
        mu_pt_bitmap b;
        if (!bitmap || !bitmap(bitmap_context, p->tex_type, &b))
            continue;
        mu_pt_render_call c;
        if (mu_pt_render_record(p, &b, mode, &c) != 1)
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
