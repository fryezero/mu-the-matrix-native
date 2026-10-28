/* Production Raklion dispatch and native event consumption with authored records. */
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "../core/mu_objects.h"
#include "../core/mu_env.h"
#include "../core/mu_particles.h"
static int effects, particles;
static void effect(void *c, int32_t type, int32_t sub, const float p[3], const float a[3], const float l[3], int32_t owner, float scale)
{ (void)c;(void)p;(void)a;(void)l;assert(type==0x513 || type==0x515 || type==0x4cc);assert(sub==2 && owner==-1 && scale>0);++effects; }
static void particle(void *c,int32_t type,const float p[3],const float a[3],const float l[3],int32_t sub,float scale,int32_t owner)
{ (void)c;(void)type;(void)p;(void)a;(void)l;(void)sub;(void)scale;(void)owner;++particles; }
int main(int argc, char **argv)
{
    mu_objects *o=calloc(1,sizeof *o);assert(o);o->world=57;o->rt.ready=1;
    o->rt.effect_scaled=effect;o->rt.particle=particle;
    o->count=1;o->rt.images=calloc(1,MU_OBJ_SIZE);assert(o->rt.images);o->rt.images[0]=1;o->rt.images[MU_OBJF_VISIBLE]=1;
    mu_obj_set_f32(o->rt.images,MU_OBJF_ALPHA,1);mu_obj_set_f32(o->rt.images,MU_OBJF_ALPHA_TARGET,1);
    o->rt.events=calloc(8,sizeof(mu_obj_event));o->rt.event_capacity=8;
    for(int k=0;k<MU_OBJ_SECTORS;++k)o->rt.world.head[k]=-1;
    o->rt.world.head[0]=0;o->rt.world.count=1;o->rt.world.block_visible[0]=1;
    o->rt.world.objects=calloc(1,sizeof(uint8_t *));o->rt.world.objects[0]=o->rt.images;
    o->rt.world.next=calloc(1,sizeof(int32_t));o->rt.world.next[0]=-1;
    o->models[0]=calloc(1,sizeof(mu_object_model));o->models[0]->loaded=1;
    mu_objects_step_inputs in={0};in.scene_state=6;
    mu_objects_raklion_set_event(o,2);o->rt.now_ms=100;
    mu_objects_step(o,&in);assert(mu_obj_i32(o->rt.raklion_state,0x14)==100);
    o->rt.now_ms=1100;mu_objects_step(o,&in);assert(o->rt.raklion_state[0x23]);
    for(int k=0;k<20;++k)mu_objects_step(o,&in);
    assert(effects>0 && !particles && o->rt.raklion_quake<0);
    mu_world *map=calloc(1,sizeof *map);assert(map);mu_objects_apply_lights(o,map);assert(map->camera_shake==o->rt.raklion_quake);
    o->rt.now_ms=1101;mu_objects_step(o,&in);assert(!o->rt.raklion_state[0x23] && o->rt.raklion_quake==0);
    mu_objects_raklion_set_event(o,1);o->models[0]->loaded=0;o->rt.now_ms=2000;
    mu_objects_step(o,&in);assert(mu_obj_i32(o->rt.raklion_state,0x14)==0); /* missing models skip the handler */
    o->models[0]->loaded=1;mu_obj_set_i32(o->rt.images,MU_OBJF_TYPE,0x16);
    mu_objects_step(o,&in);assert(mu_obj_i32(o->rt.raklion_state,0x14)==0); /* special branch skips inherited timer */
    free(o->rt.world.objects);free(o->models[0]);free(o->rt.world.next);free(o->rt.images);free(o->rt.events);free(o);
    if(argc>1) {
        mu_world_env *e=calloc(1,sizeof *e);assert(e);
        char error[512];
        assert(mu_world_env_open(e,argv[1],map,51,1,0,0,error,sizeof error)==0);
        assert(e->model_count==2 && e->models[0].loaded && e->models[1].loaded);
        mu_world_particles *p=calloc(1,sizeof *p);assert(p);
        assert(mu_world_particles_open(p,argv[1],map,51,1,0,error,sizeof error)==0);
        mu_world_particles_attach(p,NULL,e);
        mu_env_object *b=&e->env.boids[0];mu_env_object_init(NULL,b);
        b->live=1;b->type=0x1a4;b->pass=1;b->velocity=1;b->alpha=1;
        b->light[0]=b->light[1]=b->light[2]=0.5f;
        mu_raster raster;assert(mu_raster_init(&raster,128,128)==0);
        float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
        memcpy(raster.view,identity,sizeof identity);memcpy(raster.projection,identity,sizeof identity);
        raster.projection[0]=raster.projection[5]=0.02f;raster.projection[10]=0.002f;
        mu_world_env_draw_raster(e,&raster,identity,NULL);
        assert(e->stats.drawn_objects==1 && p->list.count==1 && p->list.unsupported==0);
        assert(p->list.records[0].owner==MU_WORLD_FX_BOID_BASE);
        assert(e->models[1].model.params.body_scale==1.0f); /* +a0, +bc is zero */
        b->position[0]=200;b->position[1]=300;
        mu_world_particles_step(p,1000);
        assert(p->list.records[0].owner_position[0]==200 && p->list.records[0].owner_position[1]==300);
        assert(p->list.records[0].light[0]>0);
        assert(mu_world_particles_draw_raster(p,&raster,identity)>0);
        assert(p->list.records[0].rotation == (1000.0f * 0.02f) * p->list.records[0].field_7c + p->list.records[0].start[1]);
        mu_raster_free(&raster);mu_world_particles_close(p);free(p);
        mu_world_env_close(e);free(e);
    }
    free(map);return 0;
}
