/* AUDIO-006: existing fixture actor contexts, independent audio RNG only. */
#ifndef MU_NATIVE_MONSTER_AUDIO_EXTRA_H
#define MU_NATIVE_MONSTER_AUDIO_EXTRA_H
#include "mu_monster_audio.h"
#include "../../reconstructed/audio/monster_audio_extended.h"
static inline int32_t mu_monster_audio_random(void *context)
{
    uint32_t *state=context;
    *state=*state*214013u+2531011u;
    return (int32_t)((*state>>16)&0x7fffu);
}
static inline mu_monster_sound_plan mu_monster_audio_extra_plan(int world,int model,uint16_t action,
    float frame,const float position[3],const float hero[3],mu_monster_audio_random_fn random,void *context)
{
    if(model<0x7a5 || model>=0x9fe || model==0x840 || model==0x90a || model==0x90b || model==0x90c)
        return (mu_monster_sound_plan){0};
    const float dx=position[0]-hero[0],dy=position[1]-hero[1];
    const float distance=(float)sqrt((double)(dx*dx+dy*dy));
    /* The outer dispatcher consumes distant objects before the class slot. */
    if(distance>500.0f){mu_monster_sound_plan p={0};p.known=mu_monster_audio_extended_known(world);p.handled=p.known;return p;}
    return mu_monster_sound_extended(world,model,action,frame,distance,random,context);
}
static inline void mu_monster_audio_extra_combat(mu_combat *c,int32_t index,float played)
{
    if(!c->actors || !c->walk || !c->map || index<0 || index>=c->actors->count || !(played==0.0f))return;
    const mu_world_actor *a=&c->actors->list[index];
    if(!a->actor.loaded || a->player || !(mu_actor_frame(&a->actor)==0.0f))return;
    mu_monster_sound_plan p=mu_monster_audio_extra_plan(c->map->world,a->actor.spec.model_index,
        mu_actor_action(&a->actor),mu_actor_frame(&a->actor),a->position,c->walk->hero.position,
        mu_monster_audio_random,&c->audio_rng);
    mu_monster_audio_emit(c->session,&p,a->session_key);
    if(!c->session && c->play_sound)
        for(int n=0;n<p.count;++n)c->play_sound(c->sound_context,p.sound[n].id);
}
static inline void mu_monster_audio_extra_motion(mu_session *session,const mu_walk *walk,
    const mu_world_actor *a,const mu_rp_character *record,uint32_t *random)
{
    if(!session || !walk || !walk->map || !a->actor.loaded || a->player || !record->live ||
        !record->movement || mu_actor_action_count(&a->actor)<=2)return;
    mu_monster_sound_plan p=mu_monster_audio_extra_plan(walk->map->world,a->actor.spec.model_index,
        2,mu_actor_action(&a->actor)==2?mu_actor_frame(&a->actor):0.0f,record->position,walk->hero.position,
        mu_monster_audio_random,random);
    mu_monster_audio_emit(session,&p,a->session_key);
}
static inline void mu_monster_audio_extra_tick(mu_session *session,const mu_walk *walk,
    const mu_world_actor *a,uint32_t *random)
{
    if(!session || !walk || !walk->map || !a->actor.loaded || a->player || mu_actor_action(&a->actor)>1)return;
    mu_monster_sound_plan p=mu_monster_audio_extra_plan(walk->map->world,a->actor.spec.model_index,
        mu_actor_action(&a->actor),mu_actor_frame(&a->actor),a->position,walk->hero.position,
        mu_monster_audio_random,random);
    mu_monster_audio_emit(session,&p,a->session_key);
}
#endif
