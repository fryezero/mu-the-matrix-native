/* RENDER-WORLDS-P production host: deferred create/move after the tick, visual bones and callbacks,
 * clamped lights. Authored sixteen-bone, four-action model. */
#include "../core/mu_objects.h"
#include "../../reconstructed/objects/worlds_p.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
static int particles, sprites, effects, sounds, generic, typ, last_sound;
static void particle(void *c,int32_t kind,const float p[3],const float a[3],const float l[3],int32_t sub,float scale,int32_t owner)
{
    (void)c;(void)a;(void)l;(void)p;(void)owner;
    if(typ==15) assert((kind==0x7efa && sub==2 && scale==0.25f)||(kind==0x7f26 && sub==14 && scale==0.06f));
    if(typ==0xa5) assert(((kind==0x8084||kind==0x8085) && sub==0)||(kind==0x806e && sub==4));
    ++particles;
}
static void sprite(void *c,int32_t kind,const float p[3],float scale,const float l[3],int32_t owner,float rotation,int32_t blend,int32_t axes)
{
    (void)c;(void)l;
    assert(owner==0 && rotation==0 && blend==0 && axes==4);
    if(typ==15) assert(kind==0x7ef7 && p[0]==4*10*2+99 && scale>=1.4f && scale<=1.6f);   /* bone 4 */
    if(typ==16) assert(kind==0x7f26 && (scale==2 || scale==1.5f));
    if(typ==0xa5) assert(kind==0x7ef7 && scale==4 && p[0]==99);
    ++sprites;
}
static void effect(void *c,int32_t kind,int32_t sub,const float p[3],const float a[3],const float l[3],int32_t owner,float scale)
{(void)c;(void)p;(void)a;(void)l;assert(kind==0x59a && sub==3 && owner==0 && scale==0);++effects;}
static void visual(void *c,mu_objects *o,int32_t i,int has,mu_object_model *m){(void)c;(void)o;(void)i;(void)has;(void)m;++generic;}
static void sound(void *c,int32_t id){(void)c;last_sound=id;++sounds;}
static mu_objects *world(int32_t w,int32_t t,mu_object_model *m,float x)
{
    mu_objects *o=calloc(1,sizeof *o);assert(o);
    o->world=w;o->count=1;o->records=calloc(1,sizeof *o->records);assert(o->records);
    o->records[0].type=(int16_t)t;o->records[0].position[0]=x;o->records[0].position[1]=200;o->records[0].position[2]=300;
    o->records[0].scale=2;o->models[t]=m;o->sound=sound;
    assert(mu_objects_start(o,NULL)==0);
    memset(o->rt.world.block_visible,1,sizeof o->rt.world.block_visible);
    return o;
}
static void release(mu_objects *o){mu_objects_runtime_free(o);free(o->records);free(o);}
static void step(mu_objects *o,float hx)
{
    mu_objects_step_inputs in;memset(&in,0,sizeof in);
    in.scene_state=6;in.time=1000;in.hero[0]=hx;in.hero[1]=200;
    o->rt.images[MU_OBJF_VISIBLE]=1;   /* as the render pass leaves it */
    mu_objects_step(o,&in);
}
int main(int argc,char **argv)
{
    assert(argc==2);char error[256];
    mu_object_model *m=calloc(1,sizeof *m);assert(m);
    assert(mu_bmd_load_file(argv[1],&m->bmd,error,sizeof error)==0);
    assert(mu_model_init(&m->model,&m->bmd,NULL,error,sizeof error)==0);m->loaded=1;
    mu_draw_options options;

    /* Create: all four actions 0.3, action 1 of the swinging type scaled by 1.03; the phase of type 16. */
    mu_objects *o=world(0x87,0x16,m,99);
    assert(o->rt.wp_speed_set[0x16] && o->rt.wp_speed[0x16][0]==0.3f && o->rt.wp_speed[0x16][3]==0.3f);
    assert(o->rt.wp_speed[0x16][1]==0.3f*1.03f);
    const int32_t limit=mu_obj_i32(o->rt.images,0x34);assert(limit>=15 && limit<=24);
    assert(o->rt.images[MU_OBJF_AFTER_CHARACTER]==1);
    /* Move after the tick: rests `limit` loops of action 0, then swings (action 1) with its sound near the hero. */
    int swung=0;sounds=0;
    for(int k=0;k<4000 && !swung;++k){step(o,99+500);swung=mu_obj_u16(o->rt.images,MU_OBJF_ACTION)==1;}
    assert(swung && mu_obj_i32(o->rt.images,0x30)==limit+1 && o->rt.ticks>0);
    for(int k=0;k<40;++k)step(o,99+500);
    assert(sounds>0 && last_sound==0x549);
    release(o);

    /* Gate 0x77: opens within 300 (sound 0x55b, action 1 then 2), closes beyond (0x55c, 3, then 0). */
    o=world(0x88,0x77,m,99);assert(o->rt.wp_speed[0x77][1]==0.3f*1.01f);
    step(o,99+100);assert(mu_obj_u16(o->rt.images,MU_OBJF_ACTION)==1 && last_sound==0x55b);
    for(int k=0;k<200;++k)step(o,99+100);
    assert(mu_obj_u16(o->rt.images,MU_OBJF_ACTION)==2);
    step(o,99+5000);assert(mu_obj_u16(o->rt.images,MU_OBJF_ACTION)==3 && last_sound==0x55c);
    for(int k=0;k<200;++k)step(o,99+5000);
    assert(mu_obj_u16(o->rt.images,MU_OBJF_ACTION)==0);
    release(o);

    /* 0xb5: refused .ein requests are counted, the cycle still runs; brazier 0xa5 adds range-3 light at scale 2. */
    o=world(0x88,0xb5,m,99);assert(o->rt.wp_speed[0xb5][1]==0.3f*0.9f);
    long refused=o->rt.move_unsupported;step(o,5000);assert(o->rt.move_unsupported==refused+1);
    release(o);
    o=world(0x88,0xa5,m,99);step(o,5000);
    assert(o->rt.light_count==1 && o->rt.lights[0].range==3 && o->rt.lights[0].rgb[1]==o->rt.lights[0].rgb[0]*0.6f);
    release(o);

    /* Bloody Tarkan 0x13: blend mesh 0, clamped light flag; 0x51 hidden and a plain light. */
    o=world(0x8c,0x13,m,99);step(o,5000);
    assert(o->rt.light_count==1 && (o->rt.lights[0].range&MU_OBJECT_LIGHT_CLAMPED) &&
           (o->rt.lights[0].range&~MU_OBJECT_LIGHT_CLAMPED)==3 && mu_obj_i32(o->rt.images,MU_OBJF_BLEND_MESH)==0);
    release(o);
    o=world(0x8c,0x51,m,99);assert(mu_obj_i32(o->rt.images,MU_OBJF_HIDDEN_MESH)==-2);
    step(o,5000);assert(o->rt.light_count==1 && o->rt.lights[0].range==3);
    release(o);
    float *buffer=calloc(256*256*3,sizeof *buffer);assert(buffer);
    for(int k=0;k<256*256*3;++k)buffer[k]=0.9f;
    const float hot[3]={2,-3,0.05f};
    mu_bloody_tarkan_add_light_clamped(12800,12800,hot,3,buffer);
    const float *cell=buffer+3*((128<<8)+128);
    assert(cell[0]==1 && cell[1]==0 && cell[2]==0.9f+0.05f);
    free(buffer);

    /* Visual through the production prepare path: current bones, callbacks, model gates, RNG stability. */
    o=calloc(1,sizeof *o);assert(o);o->count=1;o->rt.ready=1;o->rt.images=calloc(1,MU_OBJ_SIZE);assert(o->rt.images);
    o->rt.particle=particle;o->rt.sprite=sprite;o->rt.effect_scaled=effect;o->rt.visual=visual;
    uint8_t *img=o->rt.images;img[MU_OBJF_LIVE]=img[MU_OBJF_VISIBLE]=1;
    mu_obj_set_f32(img,MU_OBJF_SCALE,2);mu_obj_set_f32(img,MU_OBJF_ALPHA,1);mu_obj_set_f32(img,MU_OBJF_ALPHA_TARGET,1);
    mu_obj_set_f32(img,MU_OBJF_POSITION,99);mu_obj_set_f32(img,MU_OBJF_POSITION+4,200);mu_obj_set_f32(img,MU_OBJF_POSITION+8,300);
    const int types[]={15,16,0xa5,0xa5,0x13};const int worlds[]={0x87,0x87,0x87,0x88,0x8c};
    for(unsigned n=0;n<sizeof types/sizeof *types;++n){
        typ=types[n];o->world=worlds[n];o->models[typ]=m;mu_obj_set_i32(img,MU_OBJF_TYPE,typ);
        mu_obj_set_i32(img,MU_OBJF_HIDDEN_MESH,-2);
        particles=sprites=effects=0;uint32_t before=o->rt.seed;
        for(int k=0;k<200;++k)(void)mu_objects_prepare_index(o,0,NULL,6,&options);
        assert(o->rt.seed!=before);   /* outer flicker draw at least */
        if(typ==15)assert(sprites==200 && particles>0);
        else if(typ==16)assert(sprites==2400 && particles==0);
        else if(typ==0xa5 && o->world==0x88)assert(sprites==200 && particles==200);
        else if(typ==0xa5)assert(sprites==0 && particles==0 && effects<=10);
        else assert(sprites==0 && particles==0);
        uint32_t seed=o->rt.seed;int oldp=particles,olds=sprites;
        m->loaded=0;(void)mu_objects_prepare_index(o,0,NULL,6,&options);m->loaded=1;
        o->models[typ]=NULL;(void)mu_objects_prepare_index(o,0,NULL,6,&options);
        assert(o->rt.seed==seed && particles==oldp && sprites==olds);
    }
    /* Missing bone: refused and counted, never an origin or stale position. */
    typ=16;o->world=0x87;o->models[16]=m;mu_obj_set_i32(img,MU_OBJF_TYPE,16);
    const int32_t bones=m->bmd.bone_count;m->bmd.bone_count=15;long bad=o->rt.draw_unsupported;sprites=0;
    (void)mu_objects_prepare_index(o,0,NULL,6,&options);assert(sprites==0 && o->rt.draw_unsupported==bad+1);
    m->bmd.bone_count=bones;assert(generic==0);
    o->world=83;(void)mu_objects_prepare_index(o,0,NULL,6,&options);assert(generic==1);
    free(o->rt.images);free(o);
    mu_model_free(&m->model);mu_bmd_free(&m->bmd);free(m);return 0;
}
