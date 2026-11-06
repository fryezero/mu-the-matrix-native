/* RENDER-WORLDS-SLOTS: the custom render (slot 0x38) and after render (slot 0x3c) of the world classes the
 * RENDER-WORLDS-AFTER lanes left: thiscall(handler, object, model, index). Each slot runs its own world test on
 * the current world [0x01cf15fc] (Ferea 112 has none) and tests the object and model pointers where the client
 * does. Logged as in world_slots_visual.c. Addresses in docs/research/client-worlds-slots.md. */
#include "world_visual_slots.h"

/* ---- Loren Market 79 (custom 0x00e6ce2d, after 0x00e6d062, world test 0x00e6eccc) and Event square 114
 * (0x00e1f6ca, 0x00e1f8ff, 0x00e20416): one body behind two world tests ---- */
static int market_custom(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 8: case 0x1e:
        set_after(s);
        return 1;
    case 0x32: {   /* glColor3fv(model +0x54) before each block changes no value */
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 3, 2, -1);
        float x = wave(s, -1.2f) + 0.4f;
        if (x > 1.0f)
            x = 1.0f;
        mesh(s, 2, 2, A(s), -2, BL(s) * x, U(s), V(s), -1);
        return 1;
    }
    default:
        return 0;
    }
}
static void market_after(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 8: {
        for (int32_t m = 2; m <= 4; ++m)
            mesh(s, m, 2, A(s), BM(s), BL(s), 0.0f, 0.0f, -1);
        const float u = csin(s->time * 0.0007f) * 0.05f, v = csin(s->time * 0.001f) * 0.05f;
        mesh(s, 1, 0x42, A(s), 1, 0.3f, U(s), tmod(s, 10000, 0.001f, 1), -1);
        mesh(s, 0, 0x42, A(s), 0, 0.3f, u, v, -1);
        break;
    }
    case 0x1e:
        body_std(s, H(s));
        break;
    case 0x44:
        mesh(s, 0, 0x42, A(s), 0, BL(s), U(s), V(s), -1);
        break;
    default:
        break;
    }
}
static int market_world(int32_t cls, int32_t world) { return world == (cls == 114 ? 0x72 : 0x4f); }

/* ---- dispatch ---- */
static int more_class(int32_t world)
{
    switch (world) {
    case 79: case 114:
        return world;
    default:
        return -1;
    }
}
int mu_slots_more_class(int32_t world) { return more_class(world); }
int mu_slots_more_custom(int32_t cls, const slot *s, int32_t world)
{
    switch (more_class(cls)) {
    case 79: case 114:
        return s->b && market_world(cls, world) ? market_custom(s) : 0;
    default:
        return 0;
    }
}
void mu_slots_more_after(int32_t cls, const slot *s, int32_t world)
{
    switch (more_class(cls)) {
    case 79: case 114:
        if (market_world(cls, world))
            market_after(s);
        break;
    default:
        break;
    }
}
