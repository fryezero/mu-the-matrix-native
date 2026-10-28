/* Uruk Mountain, world 100. Slots 0x00e6f0a2 and 0x00e6f1ca. */
#include "worlds_i.h"
#include "worlds_b_internal.h"
int mu_uruk_create(uint8_t *o, int32_t world)
{
    if (world != 100 && world != 101) return 0;
    mu_obj_set_i32(o, 0x64, 0);
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 20: case 29: case 33: case 34: case 35: case 39: case 54: case 55: case 56: case 96: case 97:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -400.0f); break;
    case 27: case 87: case 88: case 89: case 90: case 91: case 92: case 93: case 94:
    case 99: case 100: case 105: case 106: case 108: case 109:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2); break;
    default: break;
    }
    return 1;
}
int mu_uruk_move(uint8_t *o, int32_t index, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    if (in->world != 100 && in->world != 101) return 0;
    float delta;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 16: delta = -0.015f; break;
    case 44: delta = -0.0035f; break;
    case 72: delta = 0.007f; break;
    case 73: delta = -0.02f; break;
    case 84: case 85: case 86: delta = -0.017f; break;
    case 27: {
        const float s = (float)(in->rand_fn(in->context) % 4 + 3) * 0.1f;
        wb_light(log, index, o, s, s * 0.6f, s * 0.2f, 3);
        return 1;
    }
    default: return 1;
    }
    mu_obj_set_f32(o, MU_OBJF_BLEND_V, mu_obj_f32(o, MU_OBJF_BLEND_V) + delta);
    return 1;
}

#include "worlds_g_internal.h"
#include "world_visual_internal.h"
#include "../record-math/record_math.h"
static void uruk_particle(const uint8_t *o, int32_t i, int32_t id, int32_t sub,
                           const float p[3], const float a[3], const float l[3], float scale,
                           uint32_t owner, mu_obj_log *log)
{
    (void)o;
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_PARTICLE, i);
    wb_arg(e, (uint32_t)id); wb_vec(e, p); wb_vec(e, a); wb_vec(e, l);
    wb_arg(e, (uint32_t)sub); wb_float(e, scale); wb_arg(e, owner);
}
int mu_uruk_visual(uint8_t *o, int32_t i, int32_t world, int32_t weather, float time,
                   mu_obj_rand_fn random, void *ctx, mu_obj_log *log)
{
    if (world != 100 && world != 101) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE);
    float p[3], a[3], l[3] = {1, 1, 1};
    wb_get(o, MU_OBJF_POSITION, p); wb_get(o, MU_OBJF_ANGLE, a);
    switch (t) {
    case 20: wb_sound(log, i, 0x442, 0, 0); break;
    case 27: {
        const float orange[3] = {1, 0.2f, 0};
        wg_sprite(log, i, o, 2.0f * scale, orange);
        const int32_t choice = random(ctx) % 3;
        uruk_particle(o, i, choice == 0 ? 0x8084 : choice == 1 ? 0x806e : 0x8085,
                       choice == 1 ? 4 : 0, p, a, l, scale, 0, log);
        break;
    }
    case 87:
        if (random(ctx) % 2 == 0) uruk_particle(o,i,0x801a,2,p,a,l,scale,0,log);
        break;
    case 88: uruk_particle(o,i,0x801c,14,p,a,l,scale*2.0f,0,log); break;
    case 89:
        if (random(ctx) % 8 == 0) {
            l[0]=0.5f; l[1]=0.9f; l[2]=0.5f;
            uruk_particle(o,i,0x7f5a,69,p,a,l,scale,0,log);
            wb_get(o,MU_OBJF_LIGHT,l);
            uruk_particle(o,i,0x7f5a,21,p,a,l,scale*2.0f,1,log);
        }
        break;
    case 90: case 91:
        if (random(ctx) % 6 == 0) {
            l[0]=t==90 ? 0.05f : 0.01f; l[1]=0.02f; l[2]=t==90 ? 0.01f : 0.05f;
            uruk_particle(o,i,0x7f89,25,p,a,l,scale,1,log);
        }
        break;
    case 92: {
        const float phase = (((float)sin((double)(time*0.001f)) + 1.0f)*0.5f)*100.0f;
        const int32_t start = (wb_int(p[0]) % 3 + 1)*30;
        const int32_t width = start == 90 ? 10 : 40;
        if (phase >= (float)start && phase <= (float)(start+width)) {
            l[0]=0.9f; l[1]=l[2]=0.2f;
            for (int k=0;k<20;++k) uruk_particle(o,i,0x801b,7,p,a,l,scale,1,log);
        }
        break;
    }
    case 93:
        if (random(ctx) % 3 == 0) {
            l[0]=0.9f; l[1]=l[2]=0.2f;
            uruk_particle(o,i,0x7f5a,69,p,a,l,scale,1,log);
        }
        break;
    case 94:
        if (random(ctx) % 3 == 0) uruk_particle(o,i,0x801b,2,p,a,l,scale,0,log);
        break;
    case 105: case 106:
        if (random(ctx) % 5 == 0) {
            float local[3]={0,(float)(random(ctx)%100),0};
            const float angle[3]={0,0,(float)(random(ctx)%100)};
            float matrix[3][4], offset[3];
            mu_angle_matrix(angle,&matrix[0][0]); mu_vector_rotate(local,matrix,offset);
            for (int k=0;k<3;++k) p[k]=offset[k]+p[k];
            wb_get(o,MU_OBJF_LIGHT,l);
            if (t==106) {
                l[0]=1; l[1]=0.5f; l[2]=0.1f;
                memcpy(o+MU_OBJF_LIGHT,l,12);
            }
            uruk_particle(o,i,t==105?0x7fdd:0x8184,t==105?3:2,p,a,l,1,0,log);
        }
        break;
    case 108:
        if (weather==1 && random(ctx)%2 != 0) {
            l[0]=1; l[1]=l[2]=0;
            uruk_particle(o,i,0x7f5a,22,p,a,l,3.5f,0,log);
            l[1]=l[2]=1;
            float angle[3];
            angle[0]=(float)(30-random(ctx)%61); angle[1]=(float)(30-random(ctx)%61);
            angle[2]=(float)random(ctx);
            uruk_particle(o,i,0x7fd5,0,p,angle,l,45,0,log);
            if (random(ctx)%3 != 0) {
                const float key=(float)cos((double)(float)random(ctx))+0.5f;
                mu_obj_event *e=wb_event(log,MU_URUK_KEYED_EFFECT,i);
                wb_arg(e,0x806e); wb_vec(e,p); wb_vec(e,a); wb_vec(e,l);
                wb_arg(e,12); wb_arg(e,1); wb_arg(e,(uint32_t)(uint16_t)wb_int(key));
            }
        }
        break;
    case 109:
        if (weather==1) {
            const float color[3]={0.7f,0.05f,0};
            mu_obj_event *e=wb_event(log,MU_URUK_COLORED_JOINT,i);
            wb_arg(e,0x7f7d); wb_vec(e,p); wb_vec(e,p); wb_vec(e,a);
            wb_arg(e,13); wb_arg(e,0); wb_float(e,scale*225.0f); wb_vec(e,color);
        }
        break;
    default: return 0;
    }
    return 1;
}
