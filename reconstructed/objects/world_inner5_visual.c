/* INNER-005: authored helpers and tower type 0, compared with pinned instructions. */
#include "world_inner5_visual.h"
#include "world_visual_slots.h"
#include "worlds_r2.h"
#include "charsel_world.h"

/* 0x00dfa988..0x00dfae3f. Every operation here rounds to binary32. */
static void kalima_motion(uint8_t *o, const mu_kalima_fixture *f)
{
    if (f->hero_action < 0x32 || f->hero_action >= 0x6f) return;
    const float dx=f->hero[0]-mu_obj_f32(o,MU_OBJF_POSITION);
    const float dy=f->hero[1]-mu_obj_f32(o,MU_OBJF_POSITION+4);
    if (mu_obj_f32(o,MU_OBJF_DIRECTION)<0.1f && sqrtf(dx*dx+dy*dy)<50.0f) {
        mu_obj_set_f32(o,MU_OBJF_DIRECTION,-dx*0.6f);
        mu_obj_set_f32(o,MU_OBJF_DIRECTION+4,-dy*0.6f);
        mu_obj_set_f32(o,MU_OBJF_DIRECTION+8,0);
    }
    for(uint32_t q=0;q<3;++q) {
        const uint32_t d=MU_OBJF_DIRECTION+q*4,h=MU_OBJF_HEAD_ANGLE+q*4;
        mu_obj_set_f32(o,d,mu_obj_f32(o,d)*0.6f);
        mu_obj_set_f32(o,h,mu_obj_f32(o,h)*0.6f);
    }
    for(uint32_t q=0;q<3;++q) {
        const uint32_t p=MU_OBJF_POSITION+q*4,a=MU_OBJF_ANGLE+q*4;
        mu_obj_set_f32(o,p,mu_obj_f32(o,p)+mu_obj_f32(o,MU_OBJF_DIRECTION+q*4));
        mu_obj_set_f32(o,a,mu_obj_f32(o,a)+mu_obj_f32(o,MU_OBJF_HEAD_ANGLE+q*4));
    }
}
int mu_kalima_helpers(uint8_t *o,int32_t i,int32_t world,float time,const mu_kalima_fixture *f,
                       mu_world_named_bone_fn bone,void *c,mu_obj_log *l)
{
    const int t=mu_obj_i32(o,MU_OBJF_TYPE);
    if (!((world>=24 && world<=29)||world==36) || (t!=15 && t!=29 && t!=32)) return 0;
    if (!f) {wv_emit(l,MU_INNER4_CONTEXT_REFUSED,i,NULL,0);return 1;}
    kalima_motion(o,f);
    if (t==32 && bone) {
        const float zero[3]={0,0,0},light[3]={0.6f,0.6f,1};float p[3];
        bone(c,"Bone02",zero,p);
        uint32_t a[12]={0x7ef7};memcpy(a+1,p,12);
        a[4]=wv_bits(csin(time*0.001f)*0.3f+0.7f+0.2f);memcpy(a+5,light,12);
        a[9]=1;a[11]=4;wv_emit(l,MU_OBJ_CALL_SPRITE,i,a,12);
    }
    float x=mu_obj_f32(o,MU_OBJF_POSITION),y=mu_obj_f32(o,MU_OBJF_POSITION+4);
    if (x<0) x=0;
    if (y<0) y=0;
    const float water=f->water?f->water(c,x,y):0;
    mu_obj_set_f32(o,MU_OBJF_POSITION+8,water+180.0f);
    return 1;
}

static void tower_request(const uint8_t *o,int32_t i,int effect,int id,int sub,const float p[3],
                            const float light[3],float scale,mu_obj_log *l)
{
    uint32_t a[13]={(uint32_t)id};memcpy(a+1,p,12);memcpy(a+4,o+MU_OBJF_ANGLE,12);memcpy(a+7,light,12);
    a[10]=(uint32_t)sub;
    if(effect) {a[12]=wv_bits(scale);wv_emit(l,MU_OBJ_CALL_EFFECT,i,a,13);}
    else {a[11]=wv_bits(scale);wv_emit(l,MU_OBJ_CALL_PARTICLE,i,a,13);}
}
static void tower_bone(mu_world_bone_fn bone,void *c,int k,const float local[3],float p[3])
{
    if(bone) bone(c,k,local,p);
    else p[0]=p[1]=p[2]=NAN;
}
/* 0x00e8d888..0x00e8e4e7. State is supplied by an authored fixture only. */
static void tower_sequence(const uint8_t *o,int32_t i,mu_tower_fixture *f,mu_obj_rand_fn rnd,
                             mu_world_bone_fn bone,void *c,mu_obj_log *l)
{
    const float white[3]={1,1,1};float p[3],local[3];
    if(f->active) f->phase=2;
    if(f->phase==0) {
        const float light[3]={0.2f,0.2f,0.4f};
        local[0]=(float)(rnd(c)%60)+50.0f-200.0f;local[1]=local[2]=0;
        /* AngleMatrix(0) / VectorRotate is identity, including the original RNG draw. */
        tower_bone(bone,c,34,local,p);
        tower_request(o,i,1,0x4be,0,p,light,0,l);
        for(int k=0;k<100;++k) {
            p[0]=(float)(rnd(c)%20-10)*90.0f+f->hero[0];
            p[1]=(float)(rnd(c)%20-10)*90.0f+f->hero[1];
            p[2]=f->hero[2]-(float)(rnd(c)%5)*100.0f-500.0f;
            const int id=0x419+rnd(c)%2;
            tower_request(o,i,1,id,2,p,white,0,l);
        }
        f->phase=-1;
    } else if(f->phase==1) {
        if(!f->emit) return;
        if(f->burst==0 || f->timer0) {
            for(int k=0;k<10;++k) {
                p[0]=(float)(rnd(c)%20-10)*80.0f+f->hero[0]+500.0f;
                p[1]=(float)(rnd(c)%20-10)*80.0f+f->hero[1];
                p[2]=f->hero[2]+300.0f+(float)(rnd(c)%10)*100.0f;
                const float scale=(float)(rnd(c)%10)/3.0f+5.0f;
                const int id=rnd(c)%3+0x4c0;
                tower_request(o,i,1,id,0,p,white,scale,l);
                tower_request(o,i,1,0x4c5,id,p,white,scale,l);
            }
            f->burst=(int32_t)((uint32_t)f->burst+1u);
        }
        if(f->burst>3) {f->phase=-1;f->emit=0;f->burst=0;}
    } else if(f->phase==2 && f->active) {
        static const int bones[11]={3,5,18,19,23,25,26,27,28,29,30};
        if(f->sequence==0) {
            if(rnd(c)%5==0) for(int k=0;k<3;++k) {
                /* Three overwritten offsets still consume RNG in the original. */
                (void)rnd(c);(void)rnd(c);(void)rnd(c);
                const float zero[3]={0,0,0};const int b=rnd(c)%42+33;
                tower_bone(bone,c,b,zero,p);
                const float scale=(float)(rnd(c)%10)/20.0f+1.5f;
                tower_request(o,i,0,0x7f54,1,p,white,scale,l);
            }
            if(f->timer1) f->sequence=(int32_t)((uint32_t)f->sequence+1u);
        } else if(f->sequence==1 || f->sequence==3) {
            for(int k=0;k<3;++k) {
                const float offsets[3]={-100,-0.0f,-0.0f};const int indices[3]={11,21,24};
                local[0]=0;local[1]=offsets[k];local[2]=0;
                tower_bone(bone,c,indices[k],local,p);
                tower_request(o,i,1,0x4bf,0,p,white,0,l);
            }
            f->sequence=(int32_t)((uint32_t)f->sequence+1u);
        } else if(f->sequence>=5) {f->phase=-1;f->active=0;f->sequence=0;}
        else {
            for(int k=0;k<3;++k) {
                for(uint32_t q=0;q<3;++q) local[q]=(float)(rnd(c)%100)-50.0f;
                int b=bones[rnd(c)%11];tower_bone(bone,c,b,local,p);
                float scale=(float)k*1.5f+1.0f;scale+=(float)(rnd(c)%10)/10.0f;
                tower_request(o,i,0,0x7f54,1,p,white,scale,l);
                for(uint32_t q=0;q<3;++q) local[q]=(float)(rnd(c)%200)-100.0f;
                b=bones[rnd(c)%11];tower_bone(bone,c,b,local,p);
                scale=(float)(rnd(c)%4)+1.5f;
                const float light[3]={1,0.5f,0.3f};
                tower_request(o,i,0,0x7f5a,47,p,light,scale,l);
            }
            if(f->timer2) f->sequence=(int32_t)((uint32_t)f->sequence+1u);
        }
    }
}
int mu_tower_zero(uint8_t *o,int32_t i,int32_t world,mu_tower_fixture *f,mu_obj_rand_fn rnd,
                   mu_world_bone_fn bone,void *c,mu_obj_log *l)
{
    if(world!=39 || mu_obj_i32(o,MU_OBJF_TYPE)!=0) return 0;
    if(!f) {wv_emit(l,MU_INNER4_CONTEXT_REFUSED,i,NULL,0);return 1;}
    if(!f->active) mu_obj_set_i32(o,MU_OBJF_HIDDEN_MESH,0);
    if(f->stage>=3 && f->stage<=18) mu_obj_set_f32(o,MU_OBJF_POSITION+8,-749.5f);
    if(f->rising) {
        if(mu_obj_f32(o,MU_OBJF_POSITION+8)>=-749.5f) {
            f->rising=0;mu_obj_set_f32(o,MU_OBJF_POSITION+8,-749.5f);
        }
        f->shake=(float)(rnd(c)%6-3)*2.0f;
        mu_obj_set_f32(o,MU_OBJF_POSITION+8,mu_obj_f32(o,MU_OBJF_POSITION+8)+13.0f);
    } else {
        float local[3],p[3];local[0]=(float)(rnd(c)%20)-30.0f;local[1]=(float)(rnd(c)%20)-30.0f;local[2]=0;
        tower_bone(bone,c,34,local,p);
        const float frame=mu_obj_f32(o,MU_OBJF_FRAME);
        if(frame>=5.0f && frame<12.5f) {
            const float light[3]={0.08f,0.08f,0.08f};
            tower_request(o,i,0,0x7f5a,43,p,light,1.5f,l);
        }
    }
    if(f->stage==18 || f->mode==1) mu_obj_set_f32(o,MU_OBJF_POSITION+8,-2749.5f);
    tower_sequence(o,i,f,rnd,bone,c,l);
    return 1;
}
