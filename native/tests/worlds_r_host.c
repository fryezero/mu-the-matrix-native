/* RENDER-WORLDS-R production host: create/move dispatch of worlds 131..134, the deferred Scorched Canyon create,
 * visual bones and callbacks, refused extra meshes and keyed effects. Authored twenty-bone, four-action model. */
#include "../core/mu_objects.h"
#include "../../reconstructed/objects/worlds_r.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
static int particles, sprites, effects, generic, typ;
static void particle(void *c,int32_t kind,const float p[3],const float a[3],const float l[3],int32_t sub,float scale,int32_t owner)
{
    (void)c;(void)a;(void)l;(void)p;(void)owner;(void)scale;
    if(typ<=4) assert(kind==0x7f89 && sub==typ);
    if(typ==0xa) assert(kind==0x7ef7 && sub==0 && scale==1 && p[0]==3*10*2+99);   /* bone 3 */
    if(typ==0x3b) assert(kind==0x7f89 && sub==0x1a);
    if(typ==0x49) assert(kind==0x7f26 && sub==2 && scale==1.3f);
    ++particles;
}
static void sprite(void *c,int32_t kind,const float p[3],float scale,const float l[3],int32_t owner,float rotation,int32_t blend,int32_t axes)
{
    (void)c;(void)l;(void)p;
    assert(kind==0x7f26 && owner==0 && rotation==0 && blend==0 && axes==4 && scale>=3 && scale<=6);
    ++sprites;
}
static void effect(void *c,int32_t kind,int32_t sub,const float p[3],const float a[3],const float l[3],int32_t owner,float scale)
{(void)c;(void)p;(void)a;(void)l;assert(kind==0x193 && sub==3 && owner==0 && scale==0);++effects;}
static void visual(void *c,mu_objects *o,int32_t i,int has,mu_object_model *m){(void)c;(void)o;(void)i;(void)has;(void)m;++generic;}
static mu_objects *world(int32_t w,int32_t t,mu_object_model *m)
{
    mu_objects *o=calloc(1,sizeof *o);assert(o);
    o->world=w;o->count=1;o->records=calloc(1,sizeof *o->records);assert(o->records);
    o->records[0].type=(int16_t)t;o->records[0].position[0]=99;o->records[0].position[1]=200;o->records[0].position[2]=300;
    o->records[0].scale=2;o->models[t]=m;
    assert(mu_objects_start(o,NULL)==0);
    memset(o->rt.world.block_visible,1,sizeof o->rt.world.block_visible);
    return o;
}
static void release(mu_objects *o){mu_objects_runtime_free(o);free(o->records);free(o);}
static void step(mu_objects *o)
{
    mu_objects_step_inputs in;memset(&in,0,sizeof in);
    in.scene_state=6;in.time=1000;in.hero[0]=5000;in.hero[1]=200;
    o->rt.images[MU_OBJF_VISIBLE]=1;
    mu_objects_step(o,&in);
}
int main(int argc,char **argv)
{
    assert(argc==2);char error[256];
    mu_object_model *m=calloc(1,sizeof *m);assert(m);
    assert(mu_bmd_load_file(argv[1],&m->bmd,error,sizeof error)==0);
    assert(mu_model_init(&m->model,&m->bmd,NULL,error,sizeof error)==0);m->loaded=1;
    mu_draw_options options;

    /* 131: the deferred create draws the phase from the shared RNG; 0xaa divides the velocity; 0xa0 flickers. */
    mu_objects *o=world(0x83,0x6a,m);
    const int32_t phase=mu_obj_i32(o->rt.images,0x60);
    assert(o->rt.images[MU_OBJF_AFTER_CHARACTER]==1 && phase>=10 && phase<=180 && phase%10==0);
    assert(mu_obj_f32(o->rt.images,MU_OBJF_RANGE)==-400.0f);
    release(o);
    o=world(0x83,0xaa,m);assert(mu_obj_f32(o->rt.images,MU_OBJF_VELOCITY)==0.16f/3.0f);release(o);
    o=world(0x83,0xa0,m);assert(mu_obj_i32(o->rt.images,MU_OBJF_HIDDEN_MESH)==-2);
    step(o);assert(o->rt.light_count==1 && o->rt.lights[0].range==3 && o->rt.lights[0].rgb[2]>0);release(o);
    /* 132: the sky plate; 133: type 6 drops its light flags; 134: alpha, turning and the hidden light. */
    o=world(0x84,0x1e,m);
    assert(mu_obj_f32(o->rt.images,MU_OBJF_SCALE)==3.25f && mu_obj_f32(o->rt.images,MU_OBJF_POSITION+8)==-1600.0f);
    assert(mu_obj_f32(o->rt.images,MU_OBJF_RANGE)==-30000.0f && o->rt.images[MU_OBJF_AFTER_CHARACTER]==0);
    release(o);
    o=world(0x84,0x6,m);assert(o->rt.images[MU_OBJF_AFTER_CHARACTER]==1);step(o);assert(o->rt.move_unsupported==0);
    release(o);
    o=world(0x85,6,m);
    assert(o->rt.images[MU_OBJF_AFTER_CHARACTER]==1 && o->rt.images[MU_OBJF_LIGHT_ENABLE]==0 &&
           o->rt.images[MU_OBJF_LIGHT_FULL]==0);
    release(o);
    o=world(0x85,0xa5,m);assert(mu_obj_i32(o->rt.images,MU_OBJF_HIDDEN_MESH)==-2);release(o);
    o=world(0x86,0x29,m);assert(o->rt.images[MU_OBJF_AFTER_CHARACTER]==1);
    step(o);assert(mu_obj_f32(o->rt.images,MU_OBJF_ALPHA)==0.5f);step(o);
    assert(mu_obj_f32(o->rt.images,MU_OBJF_ALPHA)==0.5f);release(o);
    o=world(0x86,0x48,m);const float y=mu_obj_f32(o->rt.images,MU_OBJF_ANGLE+4);
    step(o);step(o);assert(mu_obj_f32(o->rt.images,MU_OBJF_ANGLE+4)==y+10.0f+10.0f);release(o);
    o=world(0x86,0x3f,m);step(o);
    assert(o->rt.light_count==1 && o->rt.lights[0].range==2 && o->rt.lights[0].rgb[1]>=0.6f &&
           mu_obj_i32(o->rt.images,MU_OBJF_HIDDEN_MESH)==-2);
    release(o);

    /* Visual through the production prepare path. */
    o=calloc(1,sizeof *o);assert(o);o->count=1;o->rt.ready=1;o->rt.images=calloc(1,MU_OBJ_SIZE);assert(o->rt.images);
    o->rt.particle=particle;o->rt.sprite=sprite;o->rt.effect_scaled=effect;o->rt.visual=visual;
    uint8_t *img=o->rt.images;img[MU_OBJF_LIVE]=img[MU_OBJF_VISIBLE]=1;
    mu_obj_set_f32(img,MU_OBJF_SCALE,2);mu_obj_set_f32(img,MU_OBJF_ALPHA,1);mu_obj_set_f32(img,MU_OBJF_ALPHA_TARGET,1);
    mu_obj_set_f32(img,MU_OBJF_POSITION,99);mu_obj_set_f32(img,MU_OBJF_POSITION+4,200);mu_obj_set_f32(img,MU_OBJF_POSITION+8,300);
    const int types[]={0,3,0xa,0x1e,0x47,0x3b,0x3c,0x49,0x41,0x4d,0x46,0,0};
    const int worlds[]={0x84,0x84,0x84,0x86,0x86,0x86,0x86,0x86,0x86,0x86,0x86,0x83,0x85};
    for(unsigned n=0;n<sizeof types/sizeof *types;++n){
        typ=types[n];o->world=worlds[n];o->models[typ]=m;mu_obj_set_i32(img,MU_OBJF_TYPE,typ);
        mu_obj_set_i32(img,MU_OBJF_HIDDEN_MESH,-1);
        particles=sprites=effects=0;uint32_t before=o->rt.seed;long refused=o->rt.draw_unsupported;
        for(int k=0;k<200;++k)(void)mu_objects_prepare_index(o,0,NULL,6,&options);
        assert(o->rt.seed!=before);   /* outer flicker draw at least */
        const long counted=o->rt.draw_unsupported-refused;
        if(o->world==0x84 && typ<3)assert(particles==20 && mu_obj_i32(img,MU_OBJF_HIDDEN_MESH)==-2);
        else if(o->world==0x84 && typ<=4)assert(particles==10);
        else if(typ==0xa)assert(particles==200 && sprites==0);
        else if(typ==0x1e||typ==0x47)assert(sprites==2400 && particles==0 && counted==0);
        else if(typ==0x3b)assert(particles==10 && mu_obj_i32(img,MU_OBJF_HIDDEN_MESH)==-2);
        else if(typ==0x3c)assert(effects==200 && mu_obj_i32(img,MU_OBJF_HIDDEN_MESH)==-2);   /* WorldTime 0 */
        else if(typ==0x49)assert(particles==200 && mu_obj_f32(img,MU_OBJF_LIGHT)==0.2f);
        else if(typ==0x41||typ==0x4d)assert(counted==200 && particles==0 && sprites==0);   /* extra mesh refused */
        else if(typ==0x46)assert(counted>0 && counted<200 && effects==0);   /* keyed effect refused */
        else assert(particles==0 && sprites==0 && effects==0 && counted==0);
        uint32_t seed=o->rt.seed;int oldp=particles,olds=sprites;
        m->loaded=0;(void)mu_objects_prepare_index(o,0,NULL,6,&options);m->loaded=1;
        o->models[typ]=NULL;(void)mu_objects_prepare_index(o,0,NULL,6,&options);
        assert(o->rt.seed==seed && particles==oldp && sprites==olds);
    }
    /* Missing bones: refused and counted, never an origin or stale position. */
    typ=0x1e;o->world=0x86;o->models[typ]=m;mu_obj_set_i32(img,MU_OBJF_TYPE,typ);
    const int32_t bones=m->bmd.bone_count;m->bmd.bone_count=17;long bad=o->rt.draw_unsupported;sprites=0;
    (void)mu_objects_prepare_index(o,0,NULL,6,&options);assert(sprites==0 && o->rt.draw_unsupported==bad+1);
    m->bmd.bone_count=bones;assert(generic==0);
    o->world=0x87+0x10;(void)mu_objects_prepare_index(o,0,NULL,6,&options);assert(generic==1);
    free(o->rt.images);free(o);
    mu_model_free(&m->model);mu_bmd_free(&m->bmd);free(m);return 0;
}
