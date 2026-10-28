/* Synthetic integration of the production Icarus event consumer and real pools. */
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "../core/mu_objects_icarus.h"
#include "../core/mu_particles.h"
#include "../core/mu_env.h"
#include "../../reconstructed/objects/icarus.h"
static int effects,sprites,joints;
static void effect(void *ctx,int32_t type,int32_t sub,const float p[3],const float a[3],const float l[3],int32_t owner)
{ (void)ctx;(void)p;(void)a;(void)l;assert((type==0x1a1 || type==0x7ef7) && sub==0 && owner==-1);++effects; }
static void sprite(void *ctx,int32_t type,const float p[3],float scale,const float l[3],int32_t owner,float rot,int32_t blend,int32_t axes)
{ (void)ctx;(void)p;(void)l;assert(type==0x7f8a && scale==0.5f && owner==MU_WORLD_FX_HERO_OBJECT && rot==0 && blend==0 && axes==4);++sprites; }
static void joint(void *ctx,int32_t type,const float p[3],const float t[3],const float a[3],int32_t sub,int32_t owner,float scale)
{ (void)ctx;(void)p;(void)t;(void)a; assert((type==0x7f7d && sub==0 && owner==-1 && scale>=40) || (type==0x7f7c && sub==6 && owner==0 && scale>=10));++joints; }
static int32_t reference_rand(void *p) { return mu_obj_msvc_rand(p); }
int main(void)
{
    char path[128];
    assert(mu_env_model_file(10,0x7c4,path,sizeof path) && strcmp(path,"Data/Monster/Monster32.bmd")==0);
    mu_objects *o=calloc(1,sizeof *o);assert(o);
    o->world=10;o->rt.ready=1;o->rt.icarus_count=40;o->rt.effect=effect;o->rt.sprite=sprite;o->rt.joint=joint;
    o->count=1; o->rt.images=calloc(1,MU_OBJ_SIZE);assert(o->rt.images);
    float hero[3]={1550,1350,285};
    for(int i=0;i<500;++i) {o->rt.light_count=0;mu_objects_icarus_sky(o,hero);}
    assert(effects>0 && joints>0 && o->rt.effect_events==effects);
    int32_t ordinal=0;
    for(int i=0;i<500;++i) mu_objects_icarus_object(o,0,1,&ordinal);
    assert(sprites>0 && joints>2*sprites && ordinal==sprites);
    int32_t saved=ordinal;
    for(int i=0;i<50;++i) mu_objects_icarus_object(o,0,0,&ordinal);
    assert(ordinal==saved+50);
    /* Production MoveObjects must run sky before the puff RNG, then pass counters forward. */
    uint32_t seed=0, expected;
    mu_obj_event events[8];
    for(;;++seed) {
        expected=seed;mu_obj_log log={0,8,0,events};
        mu_icarus_sky(hero,40,reference_rand,&expected,&log);
        if(log.count<2) continue;
        int before=log.count;
        mu_obj_move_pre_sky(10,hero,reference_rand,&expected,&log);
        if(log.count>before+1) break;
    }
    o->rt.seed=seed;o->rt.icarus_count=40;o->rt.ready=1;
    o->rt.events=events;o->rt.event_capacity=8;
    for(int i=0;i<MU_OBJ_SECTORS;++i) o->rt.world.head[i]=-1;
    mu_objects_step_inputs input={0};memcpy(input.hero,hero,sizeof hero);
    mu_objects_step(o,&input);
    assert(o->rt.seed==expected && o->rt.icarus_count==0 && o->rt.steps==1);
    free(o->rt.images);free(o);
    /* Captured hidden markers must emit before becoming hidden in a fresh native world. */
    mu_objects *sources = calloc(1, sizeof *sources); assert(sources);
    mu_objects_init(sources, 10); sources->count = 1;
    sources->records = calloc(1, sizeof *sources->records); assert(sources->records);
    sources->records[0].scale = 1.0f; sources->hidden_type[0] = 1;
    assert(!mu_objects_start(sources, ""));
    uint8_t *source = mu_objects_object_image(sources, 0);
    assert(mu_obj_i32(source, MU_OBJF_HIDDEN_MESH) != -2);
    source[MU_OBJF_VISIBLE] = 1;
    mu_world_particles *particles = calloc(1, sizeof *particles); assert(particles);
    char error[128];
    assert(!mu_world_particles_open(particles, "", NULL, 10, 1, 1, error, sizeof error));
    mu_world_particles_attach(particles, sources, NULL);
    sources->rt.visual(particles, sources, 0, 1, NULL);
    assert(particles->list.count == 20 && mu_obj_i32(source, MU_OBJF_HIDDEN_MESH) == -2);
    sources->rt.visual(particles, sources, 0, 1, NULL); assert(particles->list.count == 20);
    for (int i = 0; i < 80; ++i) mu_world_particles_step(particles, (float)i * 40);
    assert(particles->list.count == 20 && particles->list.records[0].lifetime == 49);
    source[MU_OBJF_VISIBLE] = 0;
    for (int i = 0; i < 51; ++i) mu_world_particles_step(particles, (float)i * 40);
    assert(particles->list.count == 0 && mu_obj_i32(source, MU_OBJF_HIDDEN_MESH) == 0);
    sources->rt.visual(particles, sources, 0, 1, NULL); assert(particles->list.count == 20);
    /* The actual boid creator reaches the joint pool with a distinct owner handle. */
    mu_world *map = calloc(1, sizeof *map); assert(map);
    mu_world_env *env = calloc(1, sizeof *env); assert(env);
    assert(!mu_world_env_open(env, "", map, 10, 1, 1, 0, error, sizeof error));
    mu_world_particles_attach(particles, sources, env);
    mu_world_env_hero eh = {0}; float camera[3] = {0};
    mu_world_env_step(env, &eh, camera, 1000000);
    assert(env->inputs.ambient_clock == 0 && particles->stats.joints_created == 10);
    mu_world_particles_step(particles, 1000000);
    assert(mu_world_particles_live_joints(particles) == 10);
    for (int i = 0; i < 10; ++i) assert(particles->joints[i].target == MU_WORLD_FX_BOID_BASE + i + 3);
    env->env.boids[3].live = 0;
    mu_world_particles_step(particles, 1000040);
    assert(mu_world_particles_live_joints(particles) == 9);
    mu_world_env_step(env, &eh, camera, 1000040);
    assert(env->inputs.ambient_clock == 1);
    mu_world_particles_close(particles); mu_world_env_close(env); mu_objects_free(sources);
    free(particles); free(env); free(map); free(sources);
    return 0;
}
