/* Icarus event consumer. No world-input or other world handlers live here. */
#include "mu_objects_icarus.h"
#include "mu_particles.h"
#include "../../reconstructed/objects/icarus.h"
#include <string.h>
static float value(uint32_t b) { float f; memcpy(&f,&b,4); return f; }
static int32_t random_value(void *c) { return mu_obj_msvc_rand(&((mu_objects *)c)->rt.seed); }
static void consume(mu_objects *o, const mu_obj_log *log)
{
    mu_objects_runtime *rt=&o->rt;
    for(int k=0;k<log->count;++k) {
        const mu_obj_event *e=&log->events[k];
        float p[3],a[3],l[3];
        if(e->call==MU_OBJ_CALL_ADD_LIGHT && rt->light_count<MU_OBJECT_STEP_LIGHTS) {
            mu_object_light *light=&rt->lights[rt->light_count++];
            light->x=value(e->args[0]); light->y=value(e->args[1]);
            for(int q=0;q<3;++q) light->rgb[q]=value(e->args[2+q]);
            light->range=(int32_t)e->args[5]; ++rt->light_events;
        } else if(e->call==MU_OBJ_CALL_CREATE_EFFECT) {
            for(int q=0;q<3;++q) { p[q]=value(e->args[1+q]); a[q]=value(e->args[4+q]); l[q]=value(e->args[7+q]); }
            if(rt->effect) rt->effect(rt->hook_context,(int32_t)e->args[0],(int32_t)e->args[10],p,a,l,-1);
            ++rt->effect_events;
        } else if(e->call==MU_ICARUS_JOINT) {
            for(int q=0;q<3;++q) { p[q]=value(e->args[1+q]); a[q]=value(e->args[7+q]); l[q]=value(e->args[4+q]); }
            if(rt->joint) rt->joint(rt->hook_context,(int32_t)e->args[0],p,l,a,(int32_t)e->args[10],e->args[11]?e->object:-1,value(e->args[12]));
        } else if(e->call==MU_ICARUS_SPRITE) {
            for(int q=0;q<3;++q) { p[q]=value(e->args[1+q]); l[q]=value(e->args[5+q]); }
            if(rt->sprite) rt->sprite(rt->hook_context,(int32_t)e->args[0],p,value(e->args[4]),l,MU_WORLD_FX_HERO_OBJECT,value(e->args[8]),0,4);
            ++rt->sprite_events;
        }
    }
}
int32_t mu_objects_icarus_sky(mu_objects *o,const float hero[3])
{
    mu_obj_event events[4];mu_obj_log log={0,4,0,events};
    int32_t selected=mu_icarus_sky(hero,o->rt.icarus_count,random_value,o,&log);
    consume(o,&log);return selected;
}
void mu_objects_icarus_object(mu_objects *o,int32_t index,int32_t selected,int32_t *ordinal)
{
    mu_obj_event events[3];mu_obj_log log={0,3,0,events};
    mu_icarus_object(mu_objects_object_image(o,index),index,selected,ordinal,random_value,o,&log);
    consume(o,&log);
}
