#include "raklion_event.h"
#include "worlds_b_internal.h"

void mu_raklion_event_arm(uint8_t *s)
{
    if (s[0x20] == 1 || s[0x20] == 2) {
        mu_obj_set_i32(s, 0x18, s[0x20] == 1 ? 500 : 1000);
        mu_obj_set_i32(s, 0x14, 0);
        s[0x23] = 1;
    }
}

static void position(float p[3], const float hero[3], int span, int offset, int height_span, int height,
                     mu_obj_rand_fn random, void *ctx)
{
    p[0] = ((float)(random(ctx) % span) - (float)offset) + hero[0];
    p[1] = ((float)(random(ctx) % span) - (float)offset) + hero[1];
    p[2] = (float)(random(ctx) % height_span) + (float)height;
}
static void emit(mu_obj_log *log, uint32_t call, uint32_t kind, const float p[3], const float a[3],
                 const float l[3], uint32_t sub, float scale)
{
    mu_obj_event *e = wb_event(log, call, -1);
    wb_arg(e, kind); wb_vec(e, p); wb_vec(e, a); wb_vec(e, l); wb_arg(e, sub); wb_float(e, scale);
}
void mu_raklion_event_emit(const uint8_t *s, const float hero[3], const float angle[3], float *quake,
                           mu_obj_rand_fn random, void *ctx, mu_obj_log *log)
{
    float p[3], l[3], scale;
    if (s[0x20] <= 1) {
        for (int i = 0; i < 5; ++i) {
            l[0] = l[1] = l[2] = 1.0f;
            position(p, hero, 1600, 800, 100, 600, random, ctx);
            scale = (float)(random(ctx) % 20) / 5.0f + 2.0f;
            emit(log, MU_OBJ_CALL_CREATE_EFFECT, 0x512, p, angle, l, 2, scale);
            position(p, hero, 1600, 800, 100, 600, random, ctx);
            scale = (float)(random(ctx) % 10) / 5.0f + 0.5f;
            emit(log, MU_OBJ_CALL_CREATE_EFFECT, 0x514, p, angle, l, 2, scale);
            position(p, hero, 1600, 800, 100, 600, random, ctx);
            l[1] = l[2] = 0.8f;
            scale = (float)(random(ctx) % 10) / 200.0f + 0.005f;
            emit(log, MU_OBJ_CALL_CREATE_EFFECT, 0x4cc, p, angle, l, 2, scale);
            l[0] = l[1] = 0.4f; l[2] = 0.5f;
            scale = (float)(random(ctx) % 10) / 20.0f + 0.5f; /* overwritten before each particle, as in client */
            for (int j = 0; j < 3; ++j) {
                position(p, hero, 1000, 500, 150, 760, random, ctx);
                scale = (float)(random(ctx) % 20) / 40.0f + 0.2f;
                uint32_t kind = (uint32_t)(random(ctx) % 2) + 0x801cu;
                emit(log, MU_OBJ_CALL_PARTICLE, kind, p, angle, l, 13, scale);
            }
        }
    } else if (s[0x20] == 2) {
        l[0] = 0.3f; l[1] = 0.5f; l[2] = 1.0f;
        *quake = (float)(random(ctx) % 2 - 2) * 0.5f;
        position(p, hero, 2000, 1000, 100, 500, random, ctx);
        scale = (float)(random(ctx) % 20) / 5.0f + 2.0f;
        emit(log, MU_OBJ_CALL_CREATE_EFFECT, 0x513, p, angle, l, 2, scale);
        position(p, hero, 2000, 1000, 100, 500, random, ctx);
        scale = (float)(random(ctx) % 10) / 5.0f + 0.5f;
        emit(log, MU_OBJ_CALL_CREATE_EFFECT, 0x515, p, angle, l, 2, scale);
        position(p, hero, 2000, 1000, 100, 500, random, ctx);
        l[0] = 1.0f; l[1] = l[2] = 0.8f;
        scale = (float)(random(ctx) % 10) / 20.0f + 0.05f;
        emit(log, MU_OBJ_CALL_CREATE_EFFECT, 0x4cc, p, angle, l, 2, scale);
    }
}

void mu_raklion_event_step(uint8_t *s, uint32_t now, const float hero[3], const float angle[3], float *quake,
                           mu_obj_rand_fn random, void *ctx, mu_obj_log *log)
{
    if (!s[0x23]) return;
    if (s[0x20] <= 2) {
        uint32_t start = (uint32_t)mu_obj_i32(s, 0x14), duration = (uint32_t)mu_obj_i32(s, 0x18);
        /* Timer 0x00c9b4ac: unsigned subtraction, strict greater-than, zero sentinel. */
        s[0x1c] = 0;
        if (!duration) s[0x1c] = 1;
        else if (!start) mu_obj_set_i32(s, 0x14, (int32_t)now);
        else if (now - start > duration) {
            mu_obj_set_i32(s, 0x14, (int32_t)now);
            s[0x1c] = 1;
        }
        if (s[0x1c] == 1) {
            mu_obj_set_i32(s, 0x14, 0);
            s[0x23] = 0;
            if (s[0x20] == 2) *quake = 0.0f;
        } else if (random(ctx) % 2 == 0) {
            mu_raklion_event_emit(s, hero, angle, quake, random, ctx, log);
        }
    } else {
        mu_obj_set_i32(s, 0x14, 0);
        s[0x23] = 0;
        *quake = 0.0f;
    }
}
