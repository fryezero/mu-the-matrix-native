/* RENDER-WORLDS-C. Client 0x018016b0 and world-10 slice 0x0180249e..0x01802692.
 * Calls are expanded into values, never guest pointers. */
#include "icarus.h"
#include "../record-math/record_math.h"
#include <string.h>
static uint32_t bits(float f) { uint32_t b; memcpy(&b, &f, 4); return b; }
static void emit(mu_obj_log *l, const mu_obj_event *e)
{
    if (!l) return;
    if (l->count < l->capacity) l->events[l->count++] = *e;
    else ++l->overflow;
}
static void joint(mu_obj_log *log, int index, int type, const float p[3], const float t[3], const float a[3],
                  int sub, float scale)
{
    mu_obj_event e = {MU_ICARUS_JOINT, index, 13, {0}};
    e.args[0] = (uint32_t)type;
    for (int q=0;q<3;++q) { e.args[1+q]=bits(p[q]); e.args[4+q]=bits(t[q]); e.args[7+q]=bits(a[q]); }
    e.args[10]=(uint32_t)sub; e.args[11]=(uint32_t)(index >= 0); e.args[12]=bits(scale);
    emit(log, &e);
}
int32_t mu_icarus_sky(const float hero[3], int32_t count, mu_obj_rand_fn random, void *context, mu_obj_log *log)
{
    if (random(context) % 50 != 0) return 0;
    float x = ((float)(random(context)%300) + hero[0]) - 150.0f;
    float z = ((float)(random(context)%300) + hero[2]) - 150.0f;
    float lum = (float)(random(context)%4+4)*0.05f;
    float light[3] = {lum*0.3f, lum*0.3f, lum*0.081f};
    mu_obj_event e = {MU_OBJ_CALL_ADD_LIGHT, -1, 6, {0}};
    e.args[0]=bits(x); e.args[1]=bits(hero[1]);
    for (int q=0;q<3;++q) e.args[2+q]=bits(light[q]);
    e.args[5]=2; emit(log,&e);
    (void)z; /* The client computes z but AddTerrainLight only reads x/y. */
    e=(mu_obj_event){MU_OBJ_CALL_CREATE_EFFECT,-1,12,{0}};
    e.args[0]=0x1a1;
    for(int q=0;q<3;++q) { e.args[1+q]=bits(hero[q]); e.args[7+q]=bits(light[q]); }
    emit(log,&e);
    int32_t selected = count ? random(context)%count : 0;
    if (random(context)%5 != 0) return selected;
    static const float first[4][3]={{-400,-1000,0},{-300,-400,0},{-200,-400,0},{-200,400,0}};
    static const float second[4][3]={{-200,-1000,0},{-500,-1000,0},{-1000,-1500,0},{-600,-1200,0}};
    static const float yaw[4]={240,210,235,200};
    int side=random(context)%4;
    float a[3]={0,0,-45}, m[3][4], v[3], center[3], p[3], t[3];
    mu_angle_matrix(a,&m[0][0]); mu_vector_rotate(first[side],m,v);
    for(int q=0;q<3;++q) center[q]=side==1 ? hero[q]-v[q] : hero[q]+v[q];
    a[2]=yaw[side]; mu_angle_matrix(a,&m[0][0]); mu_vector_rotate(second[side],m,v);
    for(int q=0;q<3;++q) { t[q]=center[q]-v[q]; p[q]=center[q]+v[q]; }
    p[2]-=300; t[2]-=300; a[2]=0;
    for(int k=0;k<2;++k) joint(log,-1,0x7f7d,p,t,a,0,(float)(random(context)%10)+40.0f);
    return selected;
}
void mu_icarus_object(const uint8_t *o,int32_t index,int32_t selected,int32_t *ordinal,
                      mu_obj_rand_fn random,void *context,mu_obj_log *log)
{
    ++*ordinal;
    if (!selected) return;
    int r=random(context)%10;
    int type=mu_obj_i32(o,MU_OBJF_TYPE);
    if(r || type<0 || type>5) { --*ordinal; return; }
    float light[3], p[3], a[3];
    for(int q=0;q<3;++q) light[q]=(float)(random(context)%10)/50.0f;
    for(int q=0;q<3;++q) { p[q]=mu_obj_f32(o,MU_OBJF_POSITION+4u*(unsigned)q); a[q]=mu_obj_f32(o,MU_OBJF_ANGLE+4u*(unsigned)q); }
    mu_obj_event e={MU_ICARUS_SPRITE,index,12,{0}};
    e.args[0]=0x7f8a; e.args[4]=bits(0.5f);
    for(int q=0;q<3;++q) { e.args[1+q]=bits(p[q]); e.args[5+q]=bits(light[q]); }
    e.args[9]=MU_ICARUS_SPRITE_HERO; e.args[10]=0; e.args[11]=4; emit(log,&e);
    for(int k=0;k<2;++k) joint(log,index,0x7f7c,p,p,a,6,(float)(random(context)%20)+10.0f);
}

/* RenderObjectVisual world 10, types 0..5, 0x017fba5e..0x017fbf34.
 * Model lookup and the common random brightness call precede this slice. */
void mu_icarus_cover(uint8_t *o, int32_t index, mu_obj_log *log)
{
    int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    if (type < 0 || type > 5) return;
    if (mu_obj_i32(o, MU_OBJF_HIDDEN_MESH) != -2) {
        for (int i = 0; i < (type < 3 ? 20 : 10); ++i) {
            mu_obj_event e = {MU_OBJ_CALL_PARTICLE, index, 12, {0}};
            e.args[0] = 0x7f89;
            for (int k = 0; k < 3; ++k) {
                e.args[1+k] = bits(mu_obj_f32(o, MU_OBJF_POSITION + 4u*(unsigned)k));
                e.args[4+k] = bits(mu_obj_f32(o, MU_OBJF_ANGLE + 4u*(unsigned)k));
                e.args[7+k] = bits(0.1f);
            }
            e.args[10] = (uint32_t)type;
            e.args[11] = bits(mu_obj_f32(o, MU_OBJF_SCALE));
            emit(log, &e);
        }
    }
    mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
}
