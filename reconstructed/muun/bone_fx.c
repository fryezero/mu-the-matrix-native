#include "bone_fx.h"
#include <math.h>
#include <string.h>
int mu_mv_bone_row(int32_t model, int32_t mesh)
{
    return (model == 0x2b8d && mesh == 1) || (model == 0x2b8e && mesh == 2) ||
           (model == 0x2b90 && mesh == 4);
}
int mu_mv_bone_mesh(int32_t model, int32_t mesh, float time, float alpha, float light,
                    mu_mv_pass *pass, float uv[2])
{
    if (model == 0x2b90 && mesh == 4) return 0; /* This branch emits only effects. */
    if (model == 0x2b8d && mesh == 1) {
        int32_t clock = !isfinite(time) || time >= 2147483648.0f || time < -2147483648.0f ? INT32_MIN : (int32_t)time;
        int32_t frame = (clock % 260) / 20;
        uv[0] = (float)(frame % 4) * 0.25f;
        uv[1] = (float)(frame / 4) * 0.25f;
        pass->mesh = pass->blend = 1;
        pass->flags = 0x42; pass->alpha = alpha; pass->light = light; pass->texture = -1;
        pass->color[0] = 1.0f; pass->color[1] = 0.2f; pass->color[2] = 0.15f;
    }
    return 1;
}
static void op(mu_mv_bone_op *o, int particle, int type, int subtype, const float p[3],
                float r, float g, float b, float scale, float rotation)
{
    o->particle = particle; o->type = type; o->subtype = subtype;
    memcpy(o->position, p, sizeof o->position);
    o->light[0] = r; o->light[1] = g; o->light[2] = b;
    o->scale = scale; o->rotation = rotation;
}
int mu_mv_bone_effects(int32_t model, int32_t mesh, float time, float scale,
                      const float points[7][3], const float fractions[12], int32_t random0,
                      int32_t random1, mu_mv_bone_op out[MU_MV_BONE_OPS])
{
    if (model == 0x2b8d && mesh == 1) {
        float d[3], length;
        for (int k=0;k<3;++k) d[k] = points[1][k] - points[0][k];
        length = (float)sqrt((double)(d[0]*d[0] + d[1]*d[1] + d[2]*d[2]));
        float unit[3];
        for (int k=0;k<3;++k) unit[k] = length >= 0.000001f ? d[k] * (1.0f / length) : 0.0f;
        for (int i=0;i<3;++i) {
            float p[3];
            float distance = fractions[4*i] * length;
            float jitter[3];
            for (int k=0;k<3;++k) jitter[k] = fractions[4*i+k+1] * 10.0f;
            float jl = (float)sqrt((double)(jitter[0]*jitter[0] + jitter[1]*jitter[1] + jitter[2]*jitter[2]));
            for (int k=0;k<3;++k) {
                float j = jl >= 0.000001f ? jitter[k] * (1.0f / jl) : 0.0f;
                p[k] = (unit[k] * distance) * 0.7f + points[0][k] + j * 0.9f;
            }
            op(out+i,1,0x8084,28,p,1,1,1,scale,0);
        }
        return 3;
    }
    if (model == 0x2b8e && mesh == 2) {
        float angle = time * 0.001f * 2.0f;
        float pulse = (float)sin((double)angle) * 0.07f;
        for (int i=0;i<4;++i) {
            op(out+2*i,0,0x80ba,0,points[2+i],1,1,1,0.15f+pulse,0);
            op(out+2*i+1,0,0x810d,0,points[2+i],1,1,1,0.15f-pulse,0);
        }
        return 8;
    }
    if (model == 0x2b90 && mesh == 4) {
        float rotation = time * 0.0006f * 360.0f;
        float s = ((float)(random0 % 15) / 37.5f + 0.8f) * 0.6f;
        op(out,0,0x8003,0,points[6],1,1,1,0.3f,-rotation);
        op(out+1,0,0x7ef7,0,points[6],0,0.8f,1,s,rotation);
        /* Reuse the independently verified pulse consumer for wave(1.5, 0). */
        uint8_t row[300] = {0}; float a = -1.5f, one = 1.0f;
        memcpy(row+0x118,&a,4); memcpy(row+0x120,&one,4); row[0x128]=row[0x129]=1;
        const float white[3] = {1,1,1}; mu_mv_pass pass;
        mu_mv_mesh_pass(row,white,1,-1,1,-1,time,&pass);
        float inv = 1.0f-pass.light;
        op(out+2,0,0x7ef7,0,points[6],0.3f*inv,0.3f*inv,inv,pass.light*7.0f,0);
        if (random1 % 6 == 0) {
            op(out+3,1,0x7efa,3,points[6],0.26f,0.65f,1,0.13f,0);
            return 4;
        }
        return 3;
    }
    return 0;
}

int mu_mv_remote_buff_visible(int remote_found, uint8_t predicate, uint8_t buff18,
                              uint8_t local_byte16, uint8_t remote_byte16)
{
    static const uint8_t groups[4][2] = {{6,9},{7,10},{8,11},{12,13}};
    if (!remote_found || predicate != 1 || !buff18) return 1;
    for (int i=0;i<4;++i)
        if (local_byte16 == groups[i][0] || local_byte16 == groups[i][1])
            return remote_byte16 == groups[i][0] || remote_byte16 == groups[i][1];
    return 1; /* Unclassified local bytes do not hide the original pass. */
}
