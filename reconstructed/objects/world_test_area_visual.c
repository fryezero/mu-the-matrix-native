/* RENDER-WORLDS-121: Test Area 121's custom render (slot 0x38, 0x00d58bd8) and after render (slot 0x3c,
 * 0x00d5a6cc), class world-121 (vtable 0x01aa51fc), and Devias 0x67's action choice in RenderObjectVisual
 * (0x017f9d79), which shares SetAction 0x012affa4. Addresses in docs/research/client-worlds-121.md.
 *
 * RENDER-WORLDS-RAKLION: Raklion's slots (class world-57, vtable 0x01aad9d0: custom 0x00e949f8, after 0x00e96536)
 * are the same code (docs/research/client-worlds-raklion.md). The after slots are instruction for instruction the
 * same; the custom slots differ only where the row of ta_class below says, so both classes run this one routine.
 *
 * Neither 121 slot tests the world. The world manager passes types 0..300 only, so the custom slot's cases
 * 0x1a8..0x1ad and the base's 0x836..0x83e/0x872..0x875 (121: 0x00d5c79c, which answers 0; Raklion: 0x00e9ef04,
 * which draws only those types) are left out. */
#include "world_visual_slots.h"
#include "world_visual_slots2.h"

int16_t mu_obj_frame_whole(float frame)
{
    return (int16_t)(uint16_t)((uint32_t)cvtt(frame) & 0xffffu);
}

int mu_devias_action_pick(uint8_t *o, int16_t frame_whole, int16_t keys, int32_t action_count, int32_t (*rnd)(void *),
                          void *context)
{
    if (mu_obj_i32(o, MU_OBJF_TYPE) != 0x67 || (int32_t)frame_whole != (int32_t)keys - 1)
        return 0;
    mu_obj_set_action(o, action_count, rnd(context) % 32 == 0 ? 1 : 0);
    return 1;
}

/* What separates the two custom slots (every other instruction, constant and data address is the same) */
typedef struct ta_class {
    int32_t world_first, world_last;   /* 0x00ea233c at Raklion's entry 0x00e94a04: 57 <= world <= 58, else 0;
                                        * 121 has no test (0, -1) */
    int frame_gate;                    /* Raklion 0x00e96242: type 0x52 restarts its frame (+0xd0, +0xd4 = 0) while
                                        * the handler byte +0x22 (mu_slot_model.handler_state) is 0 */
} ta_class;
static const ta_class TEST_AREA = {0, -1, 0}, RAKLION = {57, 58, 1};

static uint16_t action_of(const slot *s) { return mu_obj_u16(s->o, MU_OBJF_ACTION); }   /* o + 0x2a */
static int32_t ta_rand(const slot *s) { return s->model->rand_fn(s->model->rand_context); }
static void ta_set_action(const slot *s, int32_t action) { mu_obj_set_action(s->o, s->model->action_count, action); }
static void ta_object_light(const slot *s, float r, float g, float b)   /* o + 0xec through 0x00cfc922 */
{
    mu_obj_set_f32(s->o, MU_OBJF_LIGHT, r);
    mu_obj_set_f32(s->o, MU_OBJF_LIGHT + 4, g);
    mu_obj_set_f32(s->o, MU_OBJF_LIGHT + 8, b);
}
/* TransformPosition 0x012b6ef1 of the zero point on bone k (NULL without posed bones: no point, no particle) */
static int ta_bone(const slot *s, int32_t k, float p[3])
{
    const float zero[3] = {0.0f, 0.0f, 0.0f};
    if (!s->model->bone)
        return 0;
    s->model->bone(s->model->bone_context, k, zero, p);
    return 1;
}
/* CreateParticle 0x0168fafd(type, point, the object's angle (o + 0x164), light (1, 1, 1), sub, scale, 0, 0) */
static void ta_particle(const slot *s, uint32_t type, const float p[3], int32_t sub, float scale)
{
    const float light[3] = {1.0f, 1.0f, 1.0f};
    uint32_t a[13] = {type};
    memcpy(a + 1, p, 12);
    memcpy(a + 4, s->o + MU_OBJF_ANGLE, 12);
    memcpy(a + 7, light, 12);
    a[10] = (uint32_t)sub;
    a[11] = wv_bits(scale);
    a[12] = 0;
    wv_emit(s->l, MU_OBJ_CALL_PARTICLE, s->i, a, 13);
}
static void ta_bone_particle(const slot *s, int32_t k, uint32_t type, int32_t sub, float scale)
{
    float p[3];
    if (ta_bone(s, k, p))
        ta_particle(s, type, p, sub, scale);
}
static void ta_body(const slot *s) { body(s, 2, BM(s), BL(s), U(s), V(s), -1); }

/* 0x13: the action-0 particles by frame window, then one 0x801c per bone; action 1 returns to 0 on 30 of 40 */
static void ta_0x13(const slot *s)
{
    const uint16_t a = action_of(s);
    if (a == 0) {
        const float f = mu_obj_f32(s->o, MU_OBJF_FRAME);
        if (f >= 2.0f && 5.0f >= f) {
            for (int32_t k = 0; k < s->model->bone_count; ++k)
                ta_bone_particle(s, k, 0x801e, 7, 1.0f);
        } else if (f >= 11.0f && 12.0f >= f) {
            for (int32_t k = 6; k <= 8; ++k)
                ta_bone_particle(s, k, 0x801e, 7, 1.0f);
        } else if (f >= 13.0f && 14.0f >= f) {
            for (int32_t k = 9; k <= 11; ++k)
                ta_bone_particle(s, k, 0x801e, 7, 1.0f);
        } else if (f >= 15.0f && 17.0f >= f) {
            for (int32_t k = 12; k < 20; ++k)
                ta_bone_particle(s, k, 0x801e, 7, 1.0f);
        } else if (f >= 19.5f) {
            mu_obj_set_u16(s->o, MU_OBJF_ACTION, 1);   /* a direct write, not SetAction */
        }
        for (int32_t k = 0; k < s->model->bone_count; ++k)
            ta_bone_particle(s, k, 0x801c, 8, 1.5f);
    } else if (a == 1 && ta_rand(s) % 40 == 30) {
        mu_obj_set_u16(s->o, MU_OBJF_ACTION, 0);
    }
    ta_body(s);
}
/* 0x14: four meshes (two with Effect\Chrome08.jpg 0x800a), then the action-0 particles; no RenderBody */
static void ta_0x14(const slot *s)
{
    mesh_std(s, 0, 2, -1);
    mesh_std(s, 1, 2, -1);
    mesh_std(s, 1, 0x280, 0x800a);
    mesh_std(s, 1, 0x44, 0x800a);
    const uint16_t a = action_of(s);
    if (a == 0) {
        float p[3];
        ta_bone_particle(s, 5, 0x801c, 8, 2.0f);
        if (8.0f >= mu_obj_f32(s->o, MU_OBJF_FRAME) && ta_bone(s, 6, p)) {
            ta_particle(s, 0x801c, p, 8, 1.5f);
            ta_particle(s, 0x801e, p, 7, 0.1f);
        }
        if (mu_obj_f32(s->o, MU_OBJF_FRAME) >= 12.0f && ta_bone(s, 6, p)) {
            ta_particle(s, 0x801c, p, 8, 2.0f);
            ta_particle(s, 0x801e, p, 7, 0.1f);
        }
        if (15.0f >= mu_obj_f32(s->o, MU_OBJF_FRAME)) {
            static const int32_t bones[2] = {8, 11};
            for (int q = 0; q < 2; ++q)
                if (ta_bone(s, bones[q], p)) {
                    ta_particle(s, 0x801c, p, 9, 2.0f);
                    ta_particle(s, 0x801e, p, 7, 0.1f);
                }
        }
        if (mu_obj_f32(s->o, MU_OBJF_FRAME) >= 19.0f)
            mu_obj_set_u16(s->o, MU_OBJF_ACTION, 1);
    } else if (a == 1 && ta_rand(s) % 40 == 25) {
        mu_obj_set_u16(s->o, MU_OBJF_ACTION, 0);
    }
}
/* 0x15: in frames [4, 8] of action 0, ten particles from bones 7, 16, 17, 20..24 */
static void ta_0x15(const slot *s)
{
    const uint16_t a = action_of(s);
    if (a == 0) {
        const float f = mu_obj_f32(s->o, MU_OBJF_FRAME);
        if (f >= 4.0f && 8.0f >= f) {
            float p[3];
            if (ta_bone(s, 7, p)) {
                ta_particle(s, 0x801c, p, 9, 0.5f);
                ta_particle(s, 0x801e, p, 7, 1.0f);
            }
            static const struct {
                int32_t bone;
                float scale;
            } sparks[8] = {{7, 1.0f}, {16, 0.5f}, {17, 0.7f}, {20, 0.3f}, {21, 0.3f}, {22, 0.5f}, {23, 0.3f},
                           {24, 0.3f}};
            for (int q = 0; q < 8; ++q)
                ta_bone_particle(s, sparks[q].bone, 0x801b, 5, sparks[q].scale);
        }
        if (mu_obj_f32(s->o, MU_OBJF_FRAME) >= 19.0f)
            mu_obj_set_u16(s->o, MU_OBJF_ACTION, 1);
    } else if (a == 1 && ta_rand(s) % 40 == 19) {
        mu_obj_set_u16(s->o, MU_OBJF_ACTION, 0);
    }
    ta_body(s);
}
/* 0x11: actions 0/1 past frame 19 draw one rand() % 100 (below 90: action 0 or 1 by its parity, else 2 or 3);
 * action 2 past 97 and action 3 past 98 return to rand() % 2 */
static void ta_0x11(const slot *s)
{
    const uint16_t a = action_of(s);
    const float f = mu_obj_f32(s->o, MU_OBJF_FRAME);
    if (a <= 1 && f >= 19.0f) {
        const int32_t r = ta_rand(s) % 100;
        if (r < 90)
            ta_set_action(s, r % 2 == 0 ? 0 : 1);
        else
            ta_set_action(s, r % 2 == 0 ? 2 : 3);
    } else if (a == 2 && f >= 97.0f) {
        ta_set_action(s, ta_rand(s) % 2);
    } else if (a == 3 && f >= 98.0f) {
        ta_set_action(s, ta_rand(s) % 2);
    }
    ta_body(s);
}

/* 0x52: RenderBody with the hidden mesh; in Raklion first the frame restart while its event is past state 6 */
static void ta_0x52(const slot *s, const ta_class *c)
{
    if (c->frame_gate && s->model->handler_state == 0) {
        mu_obj_set_f32(s->o, MU_OBJF_FRAME, 0.0f);
        mu_obj_set_f32(s->o, MU_OBJF_PRIOR_FRAME, 0.0f);
    }
    body_std(s, H(s));
}

static int ta_custom(const slot *s, const ta_class *c, int32_t world)
{
    if (c->world_first <= c->world_last && (world < c->world_first || world > c->world_last))
        return 0;
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    if (t >= 6 && t <= 12) {   /* 0x00d58c01..: the per-vertex light 0.5 of every mesh, the object light 1 */
        const uint32_t half[1] = {wv_bits(0.5f)};
        wv_emit(s->l, MU_OBJ_CALL_VERTEX_LIGHT, s->i, half, 1);
        ta_object_light(s, 1.0f, 1.0f, 1.0f);
        ta_body(s);
        return 1;
    }
    switch (t) {
    case 0x10:
        if (mu_obj_f32(s->o, MU_OBJF_FRAME) >= 19.0f)
            ta_set_action(s, ta_rand(s) % 2);
        ta_body(s);
        return 1;
    case 0x11:
        ta_0x11(s);
        return 1;
    case 0x13:
        ta_0x13(s);
        return 1;
    case 0x14:
        ta_0x14(s);
        return 1;
    case 0x15:
        ta_0x15(s);
        return 1;
    case 0x2e: case 0x35: case 0x4c: case 0x59:
        set_after(s);
        return 1;
    case 0x39: {   /* TransformPosition on bone 1, its point unused */
        float p[3];
        ta_bone(s, 1, p);
        body_std(s, H(s));
        return 1;
    }
    case 0x44: case 0x45: case 0x47:
        body(s, 2, 0, (csin(s->time * 0.001f) + 1.0f) * 0.5f + 0.3f, U(s), V(s), -1);
        return 1;
    case 0x52:
        ta_0x52(s, c);
        return 1;
    case 0x53:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_self(s, 2, 0x42, BL(s), U(s), V(s));
        mesh_self(s, 3, 0x42, BL(s), U(s), V(s));
        set_after(s);
        return 1;
    case 0x5c:
        mesh_std(s, 0, 2, -1);
        set_after(s);
        return 1;
    default:
        return 0;
    }
}

/* The after slot 0x00d5a6cc (198 instructions; Raklion's 0x00e96536 is the same). The client's after pass 0x016d6949
 * never runs in world 121 (0x79 is outside its world list and the class leaves the handler byte +5 at 0), so there
 * it draws only through a direct call; it runs in 57/58. Answers 1 for the types it draws. */
static int ta_after(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0x2e: case 0x35:
        body_std(s, H(s));
        break;
    case 0x4c: {   /* the object light pulses on three periods, then the body */
        const float r = csin(s->time * 0.002f) * 0.2f + 0.5f;
        const float g = csin(s->time * 0.0015f) * 0.2f + 0.5f;
        const float b = csin(s->time * 0.0014f) * 0.2f + 0.5f;
        ta_object_light(s, r, g, b);
        body_std(s, H(s));
        break;
    }
    case 0x53:
        mesh_self(s, 4, 0x42, BL(s), U(s), V(s));
        break;
    case 0x59:
        mesh_self(s, 0, 0x42, BL(s), U(s), V(s));
        break;
    case 0x5c:
        mesh_self(s, 1, 0x42, BL(s), U(s), V(s));
        break;
    default:
        return 0;
    }
    return 1;
}

int mu_slots121_custom(const slot *s) { return ta_custom(s, &TEST_AREA, 121); }
void mu_slots121_after(const slot *s) { ta_after(s); }
int mu_slots_raklion_custom(const slot *s, int32_t world) { return ta_custom(s, &RAKLION, world); }
int mu_slots_raklion_after(const slot *s) { return ta_after(s); }
static int ta_world(int32_t world) { return world == 121 || world == 57 || world == 58; }
/* LoadBitmap("Effect\\Chrome08.jpg", 0x800a, 0x2601, 0x2900) in the object loader's cases of world 121 (0x018417cd)
 * and of Raklion 57/58 (0x0183f4e2) */
int mu_slots121_bitmap(int32_t world, int32_t index, const char **path, uint32_t *filter, uint32_t *wrap)
{
    if (!ta_world(world) || index != 0x800a)
        return 0;
    *path = "Effect\\Chrome08.jpg";
    *filter = 0x2601;
    *wrap = 0x2900;
    return 1;
}
int32_t mu_slots121_bitmaps(int32_t world, int32_t type, int32_t *out, int32_t room)
{
    if (!ta_world(world) || type != 0x14 || room <= 0)
        return 0;
    out[0] = 0x800a;
    return 1;
}
