/* Production host checks with a synthetic posed model, no client assets. */
#include "../core/mu_objects.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
static int sprites,particles,sounds,other;
static float first_x,last_x;
static void sprite(void *c,int32_t type,const float p[3],float size,const float l[3],int32_t owner,float rotation,int32_t blend,int32_t axes)
{
    (void)c;(void)l;(void)rotation;
    assert(type==0x7f84 || type==0x7f37 || type==0x8021);assert(size>0 && owner==0 && blend==0 && axes==4);
    if(!sprites)first_x=p[0];last_x=p[0];++sprites;
}
static void particle(void *c,int32_t type,const float p[3],const float a[3],const float l[3],int32_t sub,float size,int32_t owner)
{
    (void)c;(void)a;assert(owner==-1);
    if(type==0x7ef7) {assert(sub==0 && size==1 && l[0]==1);assert(p[0]==119 && p[1]==204 && p[2]==306);}
    else assert(type==0x7f5a && sub==6 && size==2);
    ++particles;
}
static void visual(void *c,mu_objects *o,int32_t i,int has,mu_object_model *m)
{(void)c;(void)o;(void)i;(void)has;(void)m;++other;}
static void sound(void *c,int32_t id){(void)c;assert(id==0x7c);++sounds;}
int main(int argc,char **argv)
{
    assert(argc==2);mu_objects *o=calloc(1,sizeof *o);mu_object_model *m=calloc(1,sizeof *m);assert(o&&m);char error[256];
    assert(!mu_bmd_load_file(argv[1],&m->bmd,error,sizeof error));assert(!mu_model_init(&m->model,&m->bmd,NULL,error,sizeof error));m->loaded=1;
    /* A captured hidden sidecar must not pre-hide the one-shot type-60 producer. */
    mu_objects *started=calloc(1,sizeof *started);assert(started);
    started->world=8;started->count=1;started->records=calloc(1,sizeof *started->records);assert(started->records);
    mu_objects_record_init(started->records);started->records[0].type=60;started->hidden_type[60]=1;
    assert(!mu_objects_start(started,NULL));assert(mu_obj_i32(mu_objects_object_image(started,0),MU_OBJF_HIDDEN_MESH)!=-2);
    mu_objects_runtime_free(started);free(started->records);free(started);
    o->count=1;o->rt.ready=1;o->rt.images=calloc(1,MU_OBJ_SIZE);assert(o->rt.images);
    o->rt.sprite=sprite;o->rt.particle=particle;o->rt.visual=visual;o->sound=sound;
    uint8_t *img=o->rt.images;img[MU_OBJF_LIVE]=img[MU_OBJF_VISIBLE]=1;
    mu_obj_set_f32(img,MU_OBJF_SCALE,2);mu_obj_set_f32(img,MU_OBJF_ALPHA,1);mu_obj_set_f32(img,MU_OBJF_ALPHA_TARGET,1);
    mu_obj_set_f32(img,MU_OBJF_POSITION,99);mu_obj_set_f32(img,MU_OBJF_POSITION+4,200);mu_obj_set_f32(img,MU_OBJF_POSITION+8,300);
    mu_draw_options options;
    o->world=4;o->models[19]=m;mu_obj_set_i32(img,MU_OBJF_TYPE,19);
    assert(mu_objects_prepare_index(o,0,NULL,6,&options));assert(sprites==6 && first_x==99 && last_x==119 && other==0);
    mu_obj_set_f32(img,MU_OBJF_POSITION,199);assert(mu_objects_prepare_index(o,0,NULL,6,&options));assert(sprites==12 && last_x==219);
    uint32_t seed=o->rt.seed;m->loaded=0;assert(!mu_objects_prepare_index(o,0,NULL,6,&options));assert(sprites==12 && seed==o->rt.seed);m->loaded=1;
    o->world=8;o->models[60]=m;mu_obj_set_i32(img,MU_OBJF_TYPE,60);mu_obj_set_i32(img,MU_OBJF_HIDDEN_MESH,-1);
    mu_objects_prepare_index(o,0,NULL,6,&options);assert(particles==20 && mu_obj_i32(img,MU_OBJF_HIDDEN_MESH)==-2);
    mu_objects_prepare_index(o,0,NULL,6,&options);assert(particles==20);
    /* MoveObject hides type 63; its visual still needs this object's current pose. */
    o->models[63]=m;mu_obj_set_i32(img,MU_OBJF_TYPE,63);
    assert(!mu_objects_prepare_index(o,0,NULL,6,&options));assert(sprites==13 && last_x==229 && other==0);
    o->world=10;o->models[10]=m;mu_obj_set_i32(img,MU_OBJF_TYPE,10);mu_obj_set_i32(img,MU_OBJF_HIDDEN_MESH,-1);mu_obj_set_f32(img,MU_OBJF_POSITION,99);
    assert(mu_objects_prepare_index(o,0,NULL,6,&options));assert(particles==21 && other==1);
    m->loaded=0;mu_objects_prepare_index(o,0,NULL,6,&options);assert(particles==21);m->loaded=1;
    /* MoveObject's logged helper is consumed with this hero's action. */
    o->world=4;o->models[38]=m;mu_obj_set_i32(img,MU_OBJF_TYPE,38);mu_obj_set_f32(img,0xf8,0);mu_obj_set_f32(img,0xfc,0);
    mu_obj_set_f32(img,MU_OBJF_POSITION,10);mu_obj_set_f32(img,MU_OBJF_POSITION+4,10);o->rt.hero_action=50;
    uint8_t *images[]={img};int32_t next[]={-1};o->rt.world.objects=images;o->rt.world.count=1;o->rt.world.next=next;
    for(int k=0;k<256;++k)o->rt.world.head[k]=-1;o->rt.world.head[0]=0;o->rt.world.block_visible[0]=1;
    o->rt.event_capacity=16;o->rt.events=calloc(16,sizeof *o->rt.events);assert(o->rt.events);
    mu_objects_step_inputs in={0};in.scene_state=6;mu_objects_step(o,&in);assert(sounds==1 && mu_obj_f32(img,0xf8)>0);
    mu_model_free(&m->model);mu_bmd_free(&m->bmd);free(m);free(o->rt.images);free(o->rt.events);free(o);return 0;
}
