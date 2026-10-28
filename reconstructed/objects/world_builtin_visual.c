/* Built-in visual branches of RenderObjectVisual 0x017f9758. RENDER-WORLDS-K.
 * Engine services are callbacks; output arguments never contain guest pointers. */
#include "world_visual_internal.h"
#include "icarus.h"
#include <math.h>
#include <limits.h>
static int32_t trunc32(float x)
{
    return x >= -2147483648.0f && x < 2147483648.0f ? (int32_t)x : INT32_MIN;
}
static void pair(mu_obj_log *log, int32_t index, int32_t bitmap, const float p[3], float size,
                 const float light[3], float rotation)
{
    for (int k = 0; k < 2; ++k) {
        uint32_t a[12] = {(uint32_t)bitmap};
        memcpy(a+1,p,12); a[4]=wv_bits(size); memcpy(a+5,light,12);
        a[8]=wv_bits(k ? -rotation : rotation); a[9]=1; a[11]=4;
        wv_emit(log,MU_OBJ_CALL_SPRITE,index,a,12);
    }
}
static void particle(const uint8_t *o,int32_t index,int bitmap,int sub,const float p[3],
                     const float light[3],float size,mu_obj_log *log)
{
    uint32_t a[13]={(uint32_t)bitmap};
    memcpy(a+1,p,12);memcpy(a+4,o+MU_OBJF_ANGLE,12);memcpy(a+7,light,12);
    a[10]=(uint32_t)sub;a[11]=wv_bits(size);
    wv_emit(log,MU_OBJ_CALL_PARTICLE,index,a,13);
}
int mu_builtin_visual(uint8_t *o,int32_t index,int32_t world,int has_model,float time,
                      mu_obj_rand_fn random,mu_world_named_bone_fn bone,void *ctx,mu_obj_log *log)
{
    if (world!=4 && world!=7 && world!=8 && world!=10) return 0;
    if (!has_model) return 1;
    const float l=(float)(random(ctx)%30+70)*0.01f;
    const int32_t t=mu_obj_i32(o,MU_OBJF_TYPE);
    float p[3],light[3];memcpy(p,o+MU_OBJF_POSITION,12);memcpy(light,o+MU_OBJF_LIGHT,12);
    const float zero[3]={0,0,0};
    if (world==4) {
        const float rotation=(float)(trunc32(time*0.1f)%360);
        if(t==19 || t==20) {
            light[0]=l*(t==19?1.0f:0.4f);light[1]=l*(t==19?0.2f:0.8f);light[2]=l*(t==19?0.0f:1.0f);
            static const char *const names[]={"light02","light01","Bone01"};
            for(int k=0;k<3 && bone;++k) {
                bone(ctx,names[k],zero,p);
                pair(log,index,t==19?0x7f84:0x7f37,p,k==2?1.5f:0.3f,light,rotation);
            }
        } else if(t==23 && bone) {
            light[0]=l*0.4f;light[1]=l*0.8f;light[2]=l;
            bone(ctx,"Box03",zero,p);
            for(int k=0;k<2;++k) wv_sprite(index,0x7ef7,p,l*1.5f,light,log);
        } else if(t==40 || t==41) {
            light[0]=light[1]=light[2]=l;
            p[2]+=260.0f;pair(log,index,t==40?0x7f37:0x7f38,p,2.5f,light,rotation);
        }
    } else if(world==8) {
        const float size=mu_obj_f32(o,MU_OBJF_SCALE);
        switch(t) {
        case 60:
            if(mu_obj_i32(o,MU_OBJF_HIDDEN_MESH)!=-2)
                for(int k=0;k<20;++k) particle(o,index,0x7f5a,6,p,light,size,log);
            mu_obj_set_i32(o,MU_OBJF_HIDDEN_MESH,-2);break;
        case 63:
            if(bone) {
                const float v=(float)sin((double)((mu_obj_f32(o,MU_OBJF_ANGLE+8)*5.0f+time)*0.002f))*0.3f+0.7f;
                light[0]=v/1.7f;light[1]=light[2]=v;
                bone(ctx,"Bone02",zero,p);wv_sprite(index,0x8021,p,v*1.5f,light,log);
            }
            break;
        case 70:
            mu_obj_set_i32(o,MU_OBJF_HIDDEN_MESH,-2);
            if(random(ctx)%5==0) particle(o,index,0x7f5a,7,p,light,size,log);
            break;
        case 76:
            mu_obj_set_i32(o,MU_OBJF_HIDDEN_MESH,-2);
            if(trunc32(time)%5000>4500) particle(o,index,0x7f5a,4,p,light,size,log);
            break;
        case 83: {
            mu_obj_set_i32(o,MU_OBJF_HIDDEN_MESH,-2);
            int32_t phase=(int32_t)((uint32_t)trunc32(mu_obj_f32(o,MU_OBJF_ANGLE+8))*10u);
            int32_t clock=trunc32(time)%10000;
            if(clock>(int32_t)((uint32_t)phase+3500u) && clock<(int32_t)((uint32_t)phase+4000u)) {
                particle(o,index,0x7f5a,8,p,light,size,log);
                if(random(ctx)%3==0) {
                    p[0]+=(float)(random(ctx)%128-64);p[1]+=(float)(random(ctx)%128-64);
                    particle(o,index,0x7f5a,4,p,light,size*0.5f,log);
                    uint32_t a[12]={0};a[0]=(uint32_t)(random(ctx)%2+0x419);
                    memcpy(a+1,o+MU_OBJF_POSITION,12);memcpy(a+4,o+MU_OBJF_ANGLE,12);memcpy(a+7,light,12);
                    wv_emit(log,MU_OBJ_CALL_CREATE_EFFECT,index,a,12);
                }
            }
            break;
        }
        default:break;
        }
    } else if(world==10) {
        mu_icarus_cover(o,index,log);
        mu_icarus_bone_flare(o,index,bone,ctx,log);
    }
    /* World 7 reaches the common hook chain. No dedicated Atlans visual case. */
    return 1;
}
/* Lost Tower's MoveObject helper 0x017f6ca7, types 38/39. */
void mu_losttower_push(uint8_t *o,int32_t index,const float hero[3],uint16_t action,mu_obj_log *log)
{
    float x=hero[0]-mu_obj_f32(o,MU_OBJF_POSITION),y=hero[1]-mu_obj_f32(o,MU_OBJF_POSITION+4);
    if(action>=50 && action<111 && mu_obj_f32(o,0xf8)<0.1f && sqrtf(x*x+y*y)<50.0f) {
        mu_obj_set_f32(o,0xf8,-x*0.4f);mu_obj_set_f32(o,0xfc,-y*0.4f);mu_obj_set_f32(o,0x100,0);
        mu_obj_set_f32(o,0x174,-x*4.0f);mu_obj_set_f32(o,0x170,-y*4.0f);
        const uint32_t a[]={0x7c};wv_emit(log,MU_OBJ_CALL_SOUND,index,a,1);
    }
    for(unsigned k=0;k<3;++k) {
        mu_obj_set_f32(o,0xf8+4*k,0.6f*mu_obj_f32(o,0xf8+4*k));
        mu_obj_set_f32(o,0x170+4*k,0.6f*mu_obj_f32(o,0x170+4*k));
    }
    for(unsigned k=0;k<3;++k) {
        mu_obj_set_f32(o,MU_OBJF_POSITION+4*k,mu_obj_f32(o,MU_OBJF_POSITION+4*k)+mu_obj_f32(o,0xf8+4*k));
        mu_obj_set_f32(o,MU_OBJF_ANGLE+4*k,mu_obj_f32(o,MU_OBJF_ANGLE+4*k)+mu_obj_f32(o,0x170+4*k));
    }
}

void mu_icarus_bone_flare(const uint8_t *o,int32_t index,mu_world_named_bone_fn bone,void *ctx,mu_obj_log *log)
{
    if(mu_obj_i32(o,MU_OBJF_TYPE)!=10 || !bone) return;
    const float zero[3]={0,0,0},light[3]={1,1,1};float p[3]={0,0,0};
    bone(ctx,"Bone01",zero,p);particle(o,index,0x7ef7,0,p,light,1,log);
}
