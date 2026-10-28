/* 0x00ca2154: Icarus boid creator. Shared flight/steering stays in env_boids.c. */
#include "env_internal.h"
int env_icarus_create(mu_env *env,const mu_env_inputs *in,mu_env_object *o,int32_t index)
{
    if(in->world!=10) return 0;
    if(index<3) {
        env_set_live(env,o,1);
        if(env->host.open_monster) env->host.open_monster(env->host.context,31);
        o->type=0x7c4;
        o->velocity=(float)(mu_env_rand(env)%3+(MU_ENV_MUTATION == 12 ? 5 : 6))*0.05f;
        o->alpha=o->alpha_target=1;
        o->scale=(float)(mu_env_rand(env)%10+10)*0.02f;
        o->gravity=(float)(mu_env_rand(env)%10+10)*0.05f;
        o->flag_05=1; o->alpha_enable=0; o->subtype=0;
        o->field_68=o->field_74=-1;
        o->action=7; env_set_action(env,o,7);
        o->angle[0]=o->angle[1]=0; o->angle[2]=(float)(mu_env_rand(env)%360);
        for(int k=0;k<2;++k) o->position[k]=(float)(mu_env_rand(env)%4000-2000)+in->hero_position[k];
        o->position[2]=in->hero_position[2]-(MU_ENV_MUTATION == 11 ? 500.0f : 600.0f);
    } else {
        o->type=0x472; o->scale=2.2f; o->flag_05=0; o->timer=9600; o->ai=2;
        o->light[0]=o->light[1]=o->light[2]=1; o->alpha_enable=1;
        o->velocity=0.8f; o->field_c4=10; o->field_68=o->field_74=-1;
        o->phase=(float)(mu_env_rand(env)%314)*0.01f;
        for(int k=0;k<2;++k) o->position[k]=(float)(mu_env_rand(env)%1024-512)+in->hero_position[k];
        o->position[2]=in->hero_position[2];
        if(env->host.create_effect) env->host.create_effect(env->host.context,0x472,o,25,1);
        o->angle[0]=o->angle[1]=0; o->angle[2]=(float)(mu_env_rand(env)%360);
    }
    return 1;
}
/* 0x00ca3189: the ten accompanying 0x472 emitters, angle in radians. */
void env_icarus_emitter_move(mu_env *env,const mu_env_inputs *in,mu_env_object *o,int32_t index)
{
    o->position[0]=env_sin(o->angle[2])*o->scale+o->position[0];
    o->position[1]=o->position[1]-env_cos(o->angle[2])*o->scale;
    int32_t a=(int32_t)((uint32_t)in->ambient_clock+(uint32_t)index*0xa139u+0x870bu);
    int32_t b=(int32_t)((uint32_t)in->ambient_clock+(uint32_t)index*0x1429u+0x4544u);
    float c=env_cos((float)a*0.0003f)*0.01f;
    o->angle[2]=c*env_sin((float)b*0.0003f)+o->angle[2];
    float dx=o->position[0]-in->hero_position[0],dy=o->position[1]-in->hero_position[1];
    if(env_sqrt(dx*dx+dy*dy)>=1500) env_set_live(env,o,0);
    if(mu_env_rand(env)%5120==0) env_set_live(env,o,0);
}
