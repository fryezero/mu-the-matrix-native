/* RENDER-WORLDS-SLOTS2: RenderObjectVisual's outer flicker draw for the class worlds, and the custom render
 * (slot 0x38) / after render (slot 0x3c) of the classes RENDER-WORLDS-SLOTS left. Addresses in
 * docs/research/client-worlds-slots2.md. */
#include "world_visual_slots.h"
#include "world_visual_slots2.h"
#include "worlds_s2.h"
#include "charsel_world.h"   /* MU_OBJ_CALL_EFFECT */

int mu_obj_visual_flicker(int32_t world, int has_model)
{
    if (!has_model)
        return 0;   /* 0x017f9790: no model, RenderObjectVisual returns before the draw */
    return world != 4 && world != 7 && world != 8;   /* those: mu_builtin_visual's own first draw */
}

static float f32b(uint32_t u)
{
    float f;
    memcpy(&f, &u, 4);
    return f;
}
/* the model colour (+0x54) scaled component by component (no glColor: the field only) */
static void color_scale(const slot *s, float w)
{
    color(s, w * mu_obj_f32(s->b, MU_MDL_COLOR), w * mu_obj_f32(s->b, MU_MDL_COLOR + 4),
          w * mu_obj_f32(s->b, MU_MDL_COLOR + 8));
}
/* (float)(-((int)WorldTime % n)) * k: idiv first, the remainder negated (Debenter) */
static float tmod_neg_rem(const slot *s, int32_t n, float k)
{
    const int32_t r = cvtt(s->time) % n;
    return (float)(int32_t)(0u - (uint32_t)r) * k;
}
static float clamp1(float x) { return x > 1.0f ? 1.0f : x; }   /* comiss/jbe: NaN stays */

/* ---- Santa Village 62: custom 0x00e426cf, world test 0x00e42f6d (62); after 0x00e428af empty ---- */
static int santa_custom(const slot *s)
{
    if (mu_obj_i32(s->o, MU_OBJF_TYPE) != 0x10)
        return 0;
    mesh_std(s, 0, 2, -1);
    mesh_std(s, 1, 2, -1);
    mesh_std(s, 2, 2, -1);
    color(s, 0.0f, 0.5f, 0.5f);
    mesh_std(s, 2, 0x44, -1);
    return 1;
}

/* ---- Imperial Guardian 69..72: custom 0x00dc8b33 (69; world tests 0x00dd38c5 69, 0x00dd897d 70, 0x00dde62f 71,
 * 0x00de5519 72..74), 70 0x00dd57fa and 71 0x00dda8f5 forward to it (the world-69 handler 0x00dd8a3c(0x45)
 * slot 0x38; 70's own types are above 300), 72 0x00de08df forwards, then its own types; after 0x00dc9f33 /
 * 0x00dd5888 / 0x00dda93e / 0x00de0ff6, one body behind each class's world test ---- */
static int ig_world(int32_t world) { return world >= 69 && world <= 74; }
/* 0x73/0x75: CreateEffect(0x52d) at bone 9 while the frame is in (0, 0.4) and the state +0x60 is 0x64 (then
 * 0x65); back to 0x64 in (7, 7.5) */
static void ig_gate_effect(const slot *s)
{
    const float zero[3] = {0.0f, 0.0f, 0.0f}, one[3] = {1.0f, 1.0f, 1.0f};
    float p[3] = {0.0f, 0.0f, 0.0f};
    const int bone = s->model->bone != NULL;
    if (bone)
        s->model->bone(s->model->bone_context, 9, zero, p);
    const float f = mu_obj_f32(s->o, MU_OBJF_FRAME);
    if (f > 0.0f && 0.4f > f) {
        if (mu_obj_i32(s->o, 0x60) == 0x64) {
            if (bone) {
                uint32_t a[13] = {0x52d};
                memcpy(a + 1, p, 12);
                memcpy(a + 4, zero, 12);
                memcpy(a + 7, one, 12);
                a[10] = 0;   /* subtype */
                a[11] = 1;   /* the object as owner */
                a[12] = 0;   /* scale 0 */
                wv_emit(s->l, MU_OBJ_CALL_EFFECT, s->i, a, 13);
            }
            mu_obj_set_i32(s->o, 0x60, 0x65);
        }
    } else if (f > 7.0f && 7.5f > f && mu_obj_i32(s->o, 0x60) == 0x65) {
        mu_obj_set_i32(s->o, 0x60, 0x64);
    }
}
static int ig69_custom(const slot *s, int32_t world)
{
    if (!ig_world(world))
        return 0;
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0: case 1: case 3: case 0x2c: case 0x51:
        set_after(s);
        return 1;
    case 0x25:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 0x42, -1);
        return 1;
    case 0x29: {
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 2, 2, -1);
        const float w = csin(s->time * 0.002f) * 0.5f + 0.6f;
        color_scale(s, w);
        mesh_std(s, 1, 0x42, -1);
        return 1;
    }
    case 0x2f:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 2, 2, -1);
        grey(s, 1.2f);
        mesh_std(s, 3, 2, -1);
        return 1;
    case 0x30:
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 2, 2, -1);
        grey(s, 1.1f);
        mesh_std(s, 0, 2, -1);
        return 1;
    case 0x31: case 0x46:
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 2, 2, -1);
        mesh_std(s, 0, 0x42, -1);
        return 1;
    case 0x37:
        body_std(s, H(s));
        return 1;
    case 0x40:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 3, 2, -1);
        mesh_std(s, 2, 2, -1);
        color(s, 1.0f, 0.0f, 0.0f);
        mesh_std(s, 1, 0x44, -1);
        mesh_std(s, 1, 0x44, -1);
        return 1;
    case 0x73: case 0x75: {
        const int big = mu_obj_i32(s->o, MU_OBJF_TYPE) == 0x75;
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 2, 2, -1);
        if (big)
            mesh_std(s, 3, 2, -1);
        mu_obj_set_f32(s->o, MU_OBJF_BLEND_V, (float)(cvtt(s->time) % 25000) * 0.0004f);
        stream(s, 1);
        mesh_std(s, 1, 2, -1);
        mu_obj_set_f32(s->o, MU_OBJF_BLEND_V, (float)(cvtt(s->time) % 25000) * -0.0004f);
        stream(s, big ? 4 : 3);
        mesh_std(s, big ? 4 : 3, 2, -1);
        stream(s, 0xff);
        ig_gate_effect(s);
        return 1;
    }
    default:
        return 0;
    }
}
static int ig_custom(int32_t cls, const slot *s, int32_t world)
{
    switch (cls) {
    case 69:
        return ig69_custom(s, world);
    case 70: case 71:
        return world == cls && ig69_custom(s, world);
    default: {   /* 72 */
        if (!(world >= 72 && world <= 74))
            return 0;
        if (ig69_custom(s, world))
            return 1;
        const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
        if (t != 0x60 && t != 0x61 && t != 0x64)
            return 0;
        grey(s, f32b(0x3e2e789eu));
        body_std(s, H(s));
        return 1;
    }
    }
}
static void ig_after(int32_t cls, const slot *s, int32_t world)
{
    if (cls == 72 ? !(world >= 72 && world <= 74) : world != cls)
        return;
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0: case 1: case 3: case 0x2c: {
        const float w = (csin(s->time * 0.0015f) + 1.0f) * 0.4f + 0.2f;
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh(s, 2, 0x42, A(s), 2, w, U(s), V(s), -1);
        break;
    }
    case 0x51:
        body_std(s, H(s));
        break;
    default:
        break;
    }
}

/* ---- World 82: custom 0x00e2caaf, after 0x00e2d4a8, world test 0x00e3068f (82..90) ---- */
static int w82_world(int32_t world) { return world >= 82 && world <= 90; }
static int w82_custom(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0xa: case 0x13: case 0x14: case 0x1f: case 0x21:
        set_after(s);
        return 1;
    case 0xf:
        stream(s, 0);
        body(s, 2, BM(s), BL(s), U(s), tmod(s, 10000, 0.0001f, 1), -1);
        stream(s, 0xff);
        return 1;
    case 0x10:
        body(s, 2, 0, (csin(s->time * 0.002f) + 1.0f) * 0.3f + 0.4f, U(s), V(s), H(s));
        return 1;
    case 0x46:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 3, 2, -1);
        mesh_std(s, 2, 2, -1);
        color(s, 1.0f, 0.0f, 0.0f);
        mesh_std(s, 1, 0x44, -1);
        mesh_std(s, 1, 0x44, -1);
        return 1;
    case 0x48: {   /* sin(T * 0.003) is evaluated twice; the first pulse is overwritten */
        const float w = (csin(s->time * 0.003f) + 1.0f) * 0.3f + 0.4f;
        mesh_std(s, 0, 2, -1);
        mesh(s, 0, 0x42, A(s) * 0.1f, 0, w, U(s), V(s), 0x8144);
        return 1;
    }
    default:
        return 0;
    }
}
static void w82_after(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0x10:
        body(s, 2, 0, (csin(s->time * 0.002f) + 1.0f) * 0.3f + 0.4f, U(s), V(s), H(s));
        break;
    case 0xa: case 0x13: case 0x14: case 0x1f:
        body_std(s, H(s));
        break;
    case 0x21:
        stream(s, 0);
        mesh(s, 0, 0x42, A(s), BM(s), BL(s), U(s), tmod(s, 10000, 0.0001f, 0), -1);
        stream(s, 0xff);
        break;
    default:
        break;
    }
}

/* ---- Debenter 95: custom 0x00dbee19, world test 0x00dbd14d (95, 96); after the base 0x00d5cc60 ---- */
static int debenter_custom(const slot *s)
{
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    if (t >= 0x38 && t <= 0x43)
        return 1;
    switch (t) {
    case 0xb: {
        body(s, 2, BM(s), BL(s), U(s), V(s), 2);
        stream(s, 2);
        mesh(s, 2, 2, A(s), -1, BL(s), U(s), tmod_neg_rem(s, 10000, 0.0001f), -1);
        mesh(s, 2, 2, A(s), -2, BL(s), U(s), tmod_neg_rem(s, 10000, 0.0001f), -1);
        mesh(s, 2, 2, A(s), -2, BL(s), U(s), tmod_neg_rem(s, 10000, 0.0001f), -1);
        stream(s, 0xff);
        return 1;
    }
    case 0x25:
        stream(s, 0);
        body(s, 2, -1, BL(s), U(s), (float)(cvtt(s->time) % 25000) * 4e-05f, H(s));
        stream(s, 0xff);
        return 1;
    case 0x32: {
        const float w = (float)fabs((double)csin((float)((double)s->time * 0.001))) * 0.4f + 0.3f;
        mesh(s, 0, 2, A(s), BM(s), A(s), U(s), V(s), -1);
        mesh(s, 0, 2, A(s), -2, w, U(s), V(s), 0x81a7);
        return 1;
    }
    default:
        return 0;
    }
}

/* ---- Uruk Mountain 100: custom 0x00e702eb, world test 0x00e6efb9 (100, 101); after the base ---- */
static int uruk_custom(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0x10:
        stream(s, 0);
        mesh_std(s, 0, 2, -1);
        stream(s, 1);
        mu_obj_set_f32(s->o, MU_OBJF_BLEND_V, V(s) - 0.005f);
        mesh_std(s, 1, 2, -1);
        mu_obj_set_f32(s->o, MU_OBJF_BLEND_V, V(s) + 0.005f);
        stream(s, 0xff);
        return 1;
    case 0x2c:
        set_hidden(s, 2);
        mesh(s, 0, 2, A(s), BM(s), BL(s), 0.0f, 0.0f, -1);
        stream(s, 1);
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 1, 0x42, -1);
        set_hidden(s, -1);
        stream(s, 0xff);
        return 1;
    case 0x31: {
        const float w = clamp1((csin(s->time * 0.001f) + 1.0f) * 0.6f + 0.2f);
        set_hidden(s, 1);
        body_std(s, H(s));
        set_hidden(s, 0);
        body(s, 2, 0, w, U(s), V(s), H(s));
        return 1;
    }
    case 0x39: case 0x3a:
        body(s, 2, 0, clamp1((csin(s->time * 0.001f) + 1.0f) * 0.2f + 0.2f), U(s), V(s), H(s));
        return 1;
    case 0x46: case 0x47: {
        const float w = clamp1((csin(s->time * 0.005f) + 1.0f) * 0.2f + 0.6f);
        set_hidden(s, 4);
        body_std(s, H(s));
        set_hidden(s, 0);
        body(s, 2, 4, w, U(s), V(s), H(s));
        return 1;
    }
    case 0x48:
        set_hidden(s, 4);
        mesh(s, 0, 2, A(s), BM(s), BL(s), 0.0f, 0.0f, -1);
        mesh(s, 1, 2, A(s), BM(s), BL(s), 0.0f, 0.0f, -1);
        stream(s, 2);
        mesh_std(s, 2, 2, -1);
        mesh_std(s, 2, 0x42, -1);
        mesh(s, 3, 2, A(s), BM(s), BL(s), 0.0f, 0.0f, -1);
        stream(s, 0xff);
        set_hidden(s, -1);
        return 1;
    case 0x49: {
        set_hidden(s, 1);
        mesh(s, 0, 2, A(s), BM(s), BL(s), 0.0f, 0.0f, -1);
        mesh(s, 1, 2, A(s), BM(s), BL(s), 0.0f, 0.0f, -1);
        stream(s, 2);
        mesh(s, 2, 2, A(s), BM(s), BL(s), U(s), tmod(s, 2000, 0.0005f, 1), -1);
        for (int k = 0; k < 3; ++k)
            mesh(s, 2, 0x42, A(s), BM(s), BL(s), U(s), tmod(s, 2000, 0.0005f, 1), -1);
        stream(s, 0xff);
        set_hidden(s, -1);
        return 1;
    }
    case 0x54: case 0x55: case 0x56:
        body_std(s, -1);
        return 1;
    default:
        return 0;
    }
}

/* ---- Nars 110: custom 0x00e28bb2, after 0x00e28faf, world test 0x00e2602d (110, 111) ---- */
static int nars_custom(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0: case 0x4d:
        stream(s, 0);
        mesh_std(s, 0, 2, -1);
        stream(s, 0xff);
        return 1;
    case 6:
        mesh_std(s, 1, 2, -1);
        return 1;
    case 0x11:
        body_std(s, -1);
        return 1;
    case 0x17: case 0x18:
        body_std(s, 2);
        return 1;
    case 0x22: case 0x23: case 0x24: case 0x25: case 0x26:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 2, 2, -1);
        return 1;
    default:
        return 0;
    }
}
static void nars_after(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0:
        mesh_std(s, 0, 2, -1);
        break;
    case 6: case 0x10: case 0x11: case 0x15: case 0x16: case 0x1b: case 0x96:
        mesh(s, 0, 2, A(s), 0, BL(s), U(s), V(s), -1);
        break;
    case 0x17: case 0x18:
        mesh(s, 2, 2, A(s), 2, (csin(s->time * 0.005f) + 1.0f) * 0.2f + 0.6f, U(s), V(s), -1);
        break;
    case 0x22: case 0x23: case 0x24: case 0x25: case 0x26:   /* glPushMatrix/glPopMatrix around it: no value */
        stream(s, 4);
        mesh(s, 4, 2, A(s), 4, BL(s), U(s), tmod(s, 2000, 0.0005f, 1), -1);
        stream(s, 0xff);
        mesh_std(s, 3, 2, -1);
        mesh_std(s, 3, 0x42, -1);
        mesh_std(s, 3, 0x42, -1);
        mesh(s, 3, 0x20080, 1.0f, 3, BL(s), U(s), V(s), 0x7f1f);
        mesh(s, 3, 0x20080, 1.0f, 3, BL(s), U(s), V(s), 0x7f1f);
        break;
    case 0x8e:
        mesh(s, 0, 2, A(s), 0, (csin(s->time * 0.003f) + 1.0f) * 0.15f + 0.7f, U(s), V(s), -1);
        break;
    default:
        break;
    }
}

/* ---- dispatch (cls: the world the runtime passes; Arca War 92/96/101/111 forward to their base world's slot,
 * 0x00d7c02e / 0x00d7de81 through the registry 0x00ea594b/0x00ea4679 and the handler's base world +0x1c) ---- */
int mu_slots2_class(int32_t world)
{
    switch (world) {
    case 62: case 69: case 70: case 71: case 72: case 82: case 95: case 100: case 110:
        return world;
    case 92: case 96: case 101: case 111:
        return 92;
    case 121:   /* RENDER-WORLDS-121 */
        return 121;
    case 57: case 58:   /* RENDER-WORLDS-RAKLION: class world-57 */
        return 57;
    case 80: case 81:   /* RENDER-WORLDS-KARUTAN: class world-80 */
        return 80;
    default:
        return -1;
    }
}
int mu_slots2_custom(int32_t cls, const slot *s, int32_t world)
{
    switch (mu_slots2_class(cls)) {
    case 62:
        return world == 62 ? santa_custom(s) : 0;
    case 69: case 70: case 71: case 72:
        return ig_custom(cls, s, world);
    case 82:
        return w82_world(world) ? w82_custom(s) : 0;
    case 95:
        return world == 95 || world == 96 ? debenter_custom(s) : 0;
    case 100:
        return world == 100 || world == 101 ? uruk_custom(s) : 0;
    case 110:
        return world == 110 || world == 111 ? nars_custom(s) : 0;
    case 92:
        return mu_arca_world(world) ? mu_class_custom(mu_arca_base_world(cls), s->o, s->b, s->i, world, s->time,
                                                      s->model, s->l) : 0;
    case 121:
        return mu_slots121_custom(s);
    case 57:
        return mu_slots_raklion_custom(s, world);   /* its own world test (57, 58) */
    case 80:
        return mu_slots_karutan_custom(s, world);   /* its own world test (80, 81, 102..106) */
    default:
        return 0;
    }
}
void mu_slots2_after(int32_t cls, const slot *s, int32_t world)
{
    switch (mu_slots2_class(cls)) {
    case 69: case 70: case 71: case 72:
        ig_after(cls, s, world);
        break;
    case 82:
        if (w82_world(world))
            w82_after(s);
        break;
    case 110:
        if (world == 110 || world == 111)
            nars_after(s);
        break;
    case 92:
        if (mu_arca_world(world))
            mu_class_after(mu_arca_base_world(cls), s->o, s->b, s->i, world, s->time, s->model, s->l);
        break;
    case 121:
        mu_slots121_after(s);
        break;
    case 57:   /* no world test, as 121's */
        mu_slots_raklion_after(s);
        break;
    case 80:
        mu_slots_karutan_after(s, world);   /* its own world test (80, 81) */
        break;
    default:   /* 62's after 0x00e428af is empty; 95 and 100 have the base after */
        break;
    }
}
int mu_slots2_bitmap(int32_t world, int32_t index, const char **path, uint32_t *filter, uint32_t *wrap)
{
    static const struct {
        int32_t world, index;
        const char *path;
        uint32_t wrap;
    } shared[] = {   /* the shared object-bitmap sites 0x01842420 / 0x018410ae / 0x018220db */
        {-82, 0x8144, "Effect\\chovolcano_02_R.jpg", 0x2900}, {95, 0x81a7, "Object96\\solight02_R.jpg", 0x2900},
        {96, 0x81a7, "Object96\\solight02_R.jpg", 0x2900}, {110, 0x7f1f, "Effect\\Chrome01.jpg", 0x2901},
        {111, 0x7f1f, "Effect\\Chrome01.jpg", 0x2901},
    };
    for (size_t k = 0; k < sizeof shared / sizeof shared[0]; ++k)
        if ((shared[k].world == world || (shared[k].world == -82 && w82_world(world))) && shared[k].index == index) {
            *path = shared[k].path;
            *filter = 0x2601;
            *wrap = shared[k].wrap;
            return 1;
        }
    if (mu_slots121_bitmap(world, index, path, filter, wrap) || mu_slots_karutan_bitmap(world, index, path, filter, wrap))
        return 1;
    return mu_arca_world(world) && mu_world_slot_bitmap(mu_arca_base_world(world), index, path, filter, wrap);
}
int32_t mu_slots2_bitmaps(int32_t world, int32_t type, int32_t *out, int32_t room)
{
    if (room <= 0)
        return 0;
    if (w82_world(world) && type == 0x48) {   /* the slot's world test: 82..90 */
        out[0] = 0x8144;
        return 1;
    }
    if ((world == 95 || world == 96) && type == 0x32) {
        out[0] = 0x81a7;
        return 1;
    }
    if ((world == 110 || world == 111) && type >= 0x22 && type <= 0x26) {
        out[0] = 0x7f1f;
        return 1;
    }
    if (world == 121 || world == 57 || world == 58)   /* RENDER-WORLDS-RAKLION: 57/58 too */
        return mu_slots121_bitmaps(world, type, out, room);
    if (world == 80 || world == 81)   /* RENDER-WORLDS-KARUTAN */
        return mu_slots_karutan_bitmaps(world, type, out, room);
    if (mu_arca_world(world)) {   /* the base world's slot names them */
        int32_t base[MU_WORLD_SLOT_BITMAPS];
        const int32_t n = mu_world_slot_bitmaps(mu_arca_base_world(world), type, base);
        int32_t k = 0;
        for (; k < n && k < room; ++k)
            out[k] = base[k];
        return k;
    }
    return 0;
}
