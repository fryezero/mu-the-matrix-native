/* Authored models and objects through production step/preparation. */
#include "../core/mu_objects.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
static int particles, sprites, sounds, generic, current_type, current_world;
static float lamp_x[3];
static void particle(void *ctx,int32_t type,const float p[3],const float a[3],const float l[3],
                     int32_t sub,float scale,int32_t owner)
{
    (void)ctx;(void)a;(void)l;
    if (current_world==79) {
        assert(p[0]==99 && p[1]==200 && p[2]==300);
        if(current_type==54) assert(type==0x801e && sub==0 && scale==1 && owner==-1);
        if(current_type==55) assert(type==0x801c && sub==8 && scale==2 && owner==-1);
        if(current_type==56) assert(type==0x801b && sub==4 && scale==2 && owner==-1);
        if(current_type==57) assert(type==0x8084 || type==0x806e || type==0x8085);
    }
    ++particles;
}
static void sprite(void *ctx,int32_t type,const float p[3],float scale,const float l[3],
                   int32_t owner,float rotation,int32_t blend,int32_t axes)
{
    (void)ctx;(void)l;
    assert(owner==0 && rotation==0 && blend==0 && axes==4);
    if (current_type==30 || current_type==35) {
        assert(type==0x7f78 && scale==3);
        assert(p[0]!=99); /* Posed bone, not object origin. */
        lamp_x[sprites%3]=p[0];
    } else assert(type==0x7ef7 && p[0]==99 && (scale==4 || scale==40));
    ++sprites;
}
static void sound(void *ctx,int32_t id) { (void)ctx; assert(id==0x442);++sounds; }
static void visual(void *ctx,mu_objects *o,int32_t i,int has,mu_object_model *m)
{(void)ctx;(void)o;(void)i;(void)has;(void)m;++generic;}
int main(int argc,char **argv)
{
    assert(argc==2);
    mu_objects *o=calloc(1,sizeof *o);mu_object_model *m=calloc(1,sizeof *m);
    assert(o&&m);char error[256];
    assert(mu_bmd_load_file(argv[1],&m->bmd,error,sizeof error)==0);
    assert(mu_model_init(&m->model,&m->bmd,NULL,error,sizeof error)==0);m->loaded=1;
    o->count=1;o->rt.ready=1;o->rt.images=calloc(1,MU_OBJ_SIZE);assert(o->rt.images);
    o->rt.particle=particle;o->rt.sprite=sprite;o->rt.visual=visual;o->sound=sound;
    uint8_t *img=o->rt.images;
    img[MU_OBJF_LIVE]=img[MU_OBJF_VISIBLE]=1;
    mu_obj_set_i32(img,MU_OBJF_HIDDEN_MESH,-2);
    mu_obj_set_f32(img,MU_OBJF_SCALE,2);mu_obj_set_f32(img,MU_OBJF_ALPHA,1);
    mu_obj_set_f32(img,MU_OBJF_ALPHA_TARGET,1);
    mu_obj_set_f32(img,MU_OBJF_POSITION,99);mu_obj_set_f32(img,MU_OBJF_POSITION+4,200);mu_obj_set_f32(img,MU_OBJF_POSITION+8,300);
    mu_draw_options options;
    const int types[]={30,35,54,55,56,57,58,20,27,87,88,89,90,91,92,93,94,105,106,108,109};
    for(unsigned n=0;n<sizeof types/sizeof *types;++n) {
        current_type=types[n];current_world=n<7?79:100;o->world=current_world;
        o->models[current_type]=m;mu_obj_set_i32(img,MU_OBJF_TYPE,current_type);
        int oldp=particles,olds=sprites,old_sound=sounds;long refused=o->rt.draw_unsupported;
        o->rt.uruk_weather=1;
        for(int k=0;k<200;++k) assert(!mu_objects_prepare_index(o,0,NULL,6,&options));
        if(current_type==30) assert(sprites-olds==600);
        else if(current_type==35) assert(sprites-olds==200);
        else if(current_type==58) assert(sprites-olds==200);
        else if(current_type==20) assert(sounds-old_sound==200);
        else if(current_type==109) assert(o->rt.draw_unsupported-refused==200);
        else assert(particles>oldp);
        uint32_t seed=o->rt.seed;oldp=particles;olds=sprites;old_sound=sounds;
        m->loaded=0;assert(!mu_objects_prepare_index(o,0,NULL,6,&options));m->loaded=1;
        o->models[current_type]=NULL;assert(!mu_objects_prepare_index(o,0,NULL,6,&options));
        assert(o->rt.seed==seed && particles==oldp && sprites==olds && sounds==old_sound);
    }
    assert(generic==0);
    /* Real step: sector move, tick, then pose-dependent market lamp. */
    current_world=79;current_type=30;o->world=79;o->models[30]=m;
    mu_obj_set_i32(img,MU_OBJF_TYPE,30);mu_obj_set_f32(img,MU_OBJF_VELOCITY,0.25f);
    uint8_t *images[]={img};int32_t next[]={-1};
    o->rt.world.objects=images;o->rt.world.count=1;o->rt.world.next=next;
    for(int k=0;k<256;++k) o->rt.world.head[k]=-1;
    o->rt.world.head[0]=0;o->rt.world.block_visible[0]=1;
    o->rt.event_capacity=16;o->rt.events=calloc(16,sizeof *o->rt.events);assert(o->rt.events);
    mu_objects_step_inputs in={0};in.scene_state=6;
    mu_objects_step(o,&in);
    assert(o->rt.ticks==1 && o->rt.light_count==1 && o->rt.lights[0].range==3);
    sprites=0;assert(!mu_objects_prepare_index(o,0,NULL,6,&options));
    assert(fabsf(o->rt.lights[0].x-lamp_x[0])<0.00001f);
    assert(fabsf(o->rt.lights[0].rgb[0]-0.56f)<0.00001f);
    /* A second object's position must not reuse the shared model's old pose. */
    mu_obj_set_f32(img,MU_OBJF_POSITION,999);
    mu_objects_step(o,&in);assert(o->rt.light_count==1 && o->rt.lights[0].x>900);
    m->bmd.bone_count=1;long bad=o->rt.move_unsupported;
    mu_objects_step(o,&in);assert(o->rt.light_count==0 && o->rt.move_unsupported==bad+1);
    int old_sprites=sprites;
    assert(!mu_objects_prepare_index(o,0,NULL,6,&options));
    assert(sprites==old_sprites);
    m->bmd.bone_count=4;
    o->world=101;uint32_t seed=o->rt.seed;
    assert(!mu_objects_prepare_index(o,0,NULL,6,&options));
    assert(generic==1 && o->rt.seed==seed);
    free(o->rt.events);free(o->rt.images);mu_model_free(&m->model);mu_bmd_free(&m->bmd);free(m);free(o);
    return 0;
}
