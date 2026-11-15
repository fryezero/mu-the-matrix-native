/* Bounded inline producers, authored from pinned instructions. See client-worlds-inner.md. */
#include "world_inner4_visual.h"
#include "world_visual_slots.h"
#include "worlds_r2.h"
#include "icarus.h"

static void particle(const uint8_t *o, int32_t i, int id, int sub, const float light[3], float scale,
                       int owner, const float *angle, mu_obj_log *l)
{
    uint32_t a[13] = {(uint32_t)id};
    memcpy(a + 1, o + MU_OBJF_POSITION, 12);
    memcpy(a + 4, angle ? angle : (const void *)(o + MU_OBJF_ANGLE), 12);
    memcpy(a + 7, light, 12); a[10] = (uint32_t)sub; a[11] = wv_bits(scale); a[12] = (uint32_t)owner;
    wv_emit(l, MU_OBJ_CALL_PARTICLE, i, a, 13);
}
/* 0x00d8e640..0x00d8ea2c. The event getter reads one byte, not a boolean. */
int mu_crywolf_inner(uint8_t *o, int32_t i, int32_t world, int model, float time, uint8_t event,
                      mu_obj_rand_fn rnd, void *c, mu_obj_log *l)
{
    if (!model || world != 30) return 0;
    const int t = mu_obj_i32(o, MU_OBJF_TYPE);
    const float white[3] = {1,1,1}, scale = mu_obj_f32(o, MU_OBJF_SCALE);
    switch (t) {
    case 0: case 0x35:
        if ((t == 0 ? event == 0 : event != 0) && rnd(c) % 3 == 0)
            particle(o,i,0x8016,0,white,scale,0,NULL,l);
        break;
    case 0x29: mu_obj_set_f32(o,MU_OBJF_BLEND_LIGHT,csin(time * 0.002f) * 0.3f + 0.7f); break;
    case 0x2a:
        if (event != 0 && rnd(c) % 3 == 0) particle(o,i,0x7f5a,21,white,scale,0,NULL,l);
        break;
    case 0x34:
        if (event == 0) particle(o,i,0x801e,6,white,scale,0,NULL,l);
        break;
    case 0x36:
        if (event == 0) particle(o,i,0x801c + rnd(c) % 2,0,white,1,0,NULL,l);
        break;
    default: break;
    }
    return 1;
}
static int counter(uint8_t *o, int offset)
{
    const float prior = mu_obj_f32(o,0xb4);
    const int test = cvtt(prior + (float)offset) % 4;
    mu_obj_set_f32(o,0xb4,prior + 1.0f);
    return test == 0;
}
/* Thiscall 0x00d5404b..0x00d54e48. The world tests do not read instance fields. */
int mu_barracks_inner(uint8_t *o, int32_t i, int32_t world, int model, float time,
                       mu_obj_rand_fn rnd, void *c, mu_obj_log *l)
{
    if (!model || (world != 41 && world != 42)) return 0;
    const int t = mu_obj_i32(o,MU_OBJF_TYPE);
    const float white[3] = {1,1,1}, red[3] = {1,0.4f,0.4f}, scale = mu_obj_f32(o,MU_OBJF_SCALE);
    switch (t) {
    case 2: case 3:
        if (rnd(c) % 3 == 0) particle(o,i,t == 2 ? 0x7f5a : 0x8016,t == 2 ? 13 : 0,white,scale,0,NULL,l);
        break;
    case 5:
        if (rnd(c) % 2 == 0 && counter(o,2)) {
            particle(o,i,0x8001,0,white,1,0,NULL,l);
            particle(o,i,0x8000,0,white,1,0,NULL,l);
        }
        if (rnd(c) % 2 == 0 && counter(o,0)) {
            particle(o,i,0x7f89,6,white,1,0,NULL,l);
            particle(o,i,0x8000,1,white,1,0,NULL,l);
        }
        break;
    case 6:
        if (mu_obj_i32(o,MU_OBJF_HIDDEN_MESH) != -2) {
            const float grey[3] = {0.2f,0.2f,0.2f};
            for (int sub=1; sub<=4; ++sub) particle(o,i,0x7f89,sub,grey,scale,1,NULL,l);
        }
        mu_obj_set_i32(o,MU_OBJF_HIDDEN_MESH,-2);
        break;
    case 0x3a:
        if (rnd(c) % 2 == 0) particle(o,i,0x801a,2,white,scale,0,NULL,l);
        break;
    case 0x3b:
        if (rnd(c) % 3 == 0) particle(o,i,0x801b,1,white,scale,0,NULL,l);
        break;
    case 0x3c: particle(o,i,0x801c,3,white,scale,0,NULL,l); break;
    case 0x55:
        if (rnd(c) % 2 == 0 && counter(o,2)) {
            if (rnd(c) % 2 == 0) {
                const float black[3] = {0,0,0};
                particle(o,i,0x8001,1,black,scale,0,NULL,l);
            }
            particle(o,i,0x8000,2,red,scale,0,NULL,l);
        }
        if (rnd(c) % 2 == 0 && counter(o,0)) {
            particle(o,i,0x7f89,14,red,scale,0,NULL,l);
            particle(o,i,0x8000,2,red,scale * 2,0,NULL,l);
        }
        break;
    case 0x58:
        if (rnd(c) % 4 == 0) particle(o,i,0x7f89,10,white,scale,1,NULL,l);
        break;
    case 0x59:
        if (rnd(c) % 4 == 0) {
            const float light[3] = {(float)(rnd(c) % 3) * 0.01f + 0.015f,0,0};
            particle(o,i,0x7f89,11,light,scale,1,NULL,l);
        }
        break;
    case 0x5a:
        if (rnd(c) % 3 == 0) {
            float angle[3] = {(float)(rnd(c) % 40 + 120),0,0};
            angle[2] = (float)(rnd(c) % 30);
            for (unsigned k=0; k<3; ++k) angle[k] += mu_obj_f32(o,MU_OBJF_ANGLE + 4*k);
            uint32_t a[13] = {0x7fd5};
            memcpy(a+1,o+MU_OBJF_POSITION,12); memcpy(a+4,o+MU_OBJF_POSITION,12); memcpy(a+7,angle,12);
            a[10]=4; a[11]=1; a[12]=wv_bits(scale);
            wv_emit(l,MU_ICARUS_JOINT,i,a,13);
            particle(o,i,0x7f25,9,red,scale,0,angle,l);
        }
        break;
    case 0x5c:
        if ((csin(time * 0.0005f) + 1.0f) * 0.5f > 0.9f) {
            uint32_t a[13] = {0x806d};
            memcpy(a+1,o+MU_OBJF_POSITION,12); memcpy(a+4,o+MU_OBJF_ANGLE,12); memcpy(a+7,red,12);
            a[12] = (uint16_t)(uint32_t)cvtt(scale);
            for (int k=0; k<2; ++k) wv_emit(l,MU_R2_EFFECT,i,a,13);
        }
        break;
    default: break;
    }
    return 1;
}

static void sprite(int32_t i, int id, const float p[3], float size, const float light[3], float angle, mu_obj_log *l)
{
    uint32_t a[12] = {(uint32_t)id};
    memcpy(a+1,p,12); a[4]=wv_bits(size); memcpy(a+5,light,12); a[8]=wv_bits(angle); a[9]=1; a[11]=4;
    wv_emit(l,MU_OBJ_CALL_SPRITE,i,a,12);
}
/* 0x00def747..0x00deff29. Types 15/29/32 need the hero/water helper context and remain refused. */
int mu_kalima_inner(uint8_t *o, int32_t i, int32_t world, float time, mu_obj_rand_fn rnd,
                     mu_world_named_bone_fn bone, void *c, mu_obj_log *l)
{
    if (!((world>=24 && world<=29) || world==36)) return 0;
    const int t=mu_obj_i32(o,MU_OBJF_TYPE);
    const float white[3]={1,1,1};
    switch (t) {
    case 12:
        if (bone) {
            const float local[3]={0,0,0},light[3]={0.6f,0.6f,1};float p[3];
            bone(c,"Bone02",local,p);
            sprite(i,0x7ef7,p,csin(time*0.001f)*0.3f+0.7f+0.2f,light,0,l);
        }
        break;
    case 15: case 29: case 32:
        wv_emit(l,MU_INNER4_CONTEXT_REFUSED,i,NULL,0);
        break;
    case 35: {
        const float light[3]={0.3f,0.6f,1};
        particle(o,i,0x7ef7,6,light,1,1,NULL,l);
        mu_obj_set_i32(o,MU_OBJF_HIDDEN_MESH,-2);
        break;
    }
    case 36: case 37:
        particle(o,i,t==36?0x8017:0x801e,0,white,1,0,NULL,l);
        mu_obj_set_f32(o,MU_OBJF_SCALE,0.5f);
        if (t==36) mu_obj_set_i32(o,MU_OBJF_HIDDEN_MESH,-2);
        break;
    case 38:
        if (rnd(c)%2==0) particle(o,i,0x801a,0,white,1,0,NULL,l);
        mu_obj_set_f32(o,MU_OBJF_SCALE,0.5f);
        break;
    case 39:
        particle(o,i,0x801c+rnd(c)%2,0,white,1,0,NULL,l);
        mu_obj_set_f32(o,MU_OBJF_SCALE,0.5f);
        break;
    case 40:
        if (rnd(c)%4==0) particle(o,i,0x801b,0,white,1,0,NULL,l);
        mu_obj_set_f32(o,MU_OBJF_SCALE,0.5f);
        break;
    default: break;
    }
    return 1;
}
static void tower_joint(const uint8_t *o,int32_t i,int id,int sub,float scale,mu_obj_log *l)
{
    uint32_t a[13]={(uint32_t)id};
    memcpy(a+1,o+MU_OBJF_POSITION,12);memcpy(a+4,o+MU_OBJF_POSITION,12);memcpy(a+7,o+MU_OBJF_ANGLE,12);
    a[10]=(uint32_t)sub;a[12]=wv_bits(scale);
    wv_emit(l,MU_ICARUS_JOINT,i,a,13);
}
/* 0x00e84941..0x00e855f1. Type 0's nested sequence 0x00e8d888 remains a counted refusal. */
int mu_tower_inner(uint8_t *o,int32_t i,int32_t world,float time,uint8_t hidden,mu_obj_rand_fn rnd,
                    mu_world_bone_fn bone,void *c,mu_obj_log *l)
{
    if (world!=39) return 0;
    const int t=mu_obj_i32(o,MU_OBJF_TYPE);
    const float scale=mu_obj_f32(o,MU_OBJF_SCALE);
    switch (t) {
    case 0: wv_emit(l,MU_INNER4_CONTEXT_REFUSED,i,NULL,0); break;
    case 5:
        if (bone) {
            const float pulse=(csin(time*0.002f)+2.0f)*0.5f,light[3]={pulse*0.3f,pulse*0.5f,pulse};
            const float local[3]={-1,0,0};float p[3];bone(c,1,local,p);
            const float size=(float)((double)pulse/2.4);
            sprite(i,0x7ef7,p,size,light,0,l);
            sprite(i,0x7f67,p,size,light,(float)(cvtt(time/2.0f)%360),l);
            sprite(i,0x7f67,p,size,light,(float)(cvtt(time/4.0f)%360),l);
        }
        break;
    case 1: case 11: case 0x2e: case 0x31: case 0x32: {
        const int sub=t==1||t==0x31?1:t==11?3:t==0x2e?7:4;
        const float v=t==0x2e?0.25f:0.1f;
        const float light[3]={t==1||t==0x31?0:v,t==1?0.03f:t==0x31?0.06f:v,t==1?0.04f:v};
        if (mu_obj_i32(o,MU_OBJF_HIDDEN_MESH)!=-2)
            for(int k=0;k<(t==0x2e?20:10);++k) particle(o,i,0x7f89,sub,light,scale,1,NULL,l);
        mu_obj_set_i32(o,MU_OBJF_HIDDEN_MESH,-2);
        break;
    }
    case 0x20:
        if (rnd(c)%3==0) {
            const float light[3]={0.4f,0.6f,0.7f};
            particle(o,i,0x802a,1,light,1,0,NULL,l);
        }
        break;
    case 0x4a:
        if (hidden) {mu_obj_set_i32(o,MU_OBJF_HIDDEN_MESH,-2);break;}
        /* fall through */
    case 0x2f:
        if (rnd(c)%5==0) tower_joint(o,i,0x7f7d,11,scale*15,l);
        break;
    case 0x30:
        if (rnd(c)%3==0) {float light[3];memcpy(light,o+MU_OBJF_LIGHT,12);particle(o,i,0x7f89,10,light,scale,1,NULL,l);}
        break;
    case 0x34: case 0x35:
        if (rnd(c)%3==0) {
            const float light[3]={t==0x34?0.5f:0.3f,t==0x34?1:0.3f,t==0x34?0.7f:0.3f};
            memcpy(o+MU_OBJF_LIGHT,light,12);
            particle(o,i,t==0x34?0x8017:0x7f5a,t==0x34?1:46,light,scale,0,NULL,l);
        }
        break;
    case 0x36:
        if (rnd(c)%3==0) {mu_obj_set_i32(o,MU_OBJF_HIDDEN_MESH,-1);tower_joint(o,i,0x7f7c,19,scale*10,l);}
        break;
    default: break;
    }
    return 1;
}
