/* Current-object bones and callbacks, with an authored fifteen-bone model. */
#include "../core/mu_objects.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
static int particles, sprites, generic, typ;
static float first_x;
static void particle(void *c,int32_t kind,const float p[3],const float a[3],const float l[3],int32_t sub,float scale,int32_t owner)
{
    (void)c;(void)a;(void)l;
    assert(p[0]==99 && p[1]==200 && p[2]==300);
    if(typ==70 || typ==80) assert((kind==0x8086 && sub==2)||(kind==0x8087 && sub==6)||(kind==0x8089 && sub==2));
    if(typ==114) assert(kind==0x801c && sub==16 && owner==-1);
    if(typ==115 || typ==118) assert(kind==0x7f89 && sub==0 && owner==0);
    if(typ==116) assert(kind==0x7f5a && ((sub==69 && scale==2 && owner==-1)||(sub==13 && scale==4 && owner==0)));
    ++particles;
}
static void sprite(void *c,int32_t kind,const float p[3],float scale,const float l[3],int32_t owner,float rotation,int32_t blend,int32_t axes)
{
    (void)c;(void)l;
    assert(owner==0 && rotation==0 && blend==0 && axes==4);
    if(typ==66) assert(kind==0x7f6b && scale==1.2f);
    if(typ==72) assert((kind==0x7ef7 && scale==2)||(kind==0x7f26 && (scale==4 || scale==1.5f)));
    if(typ==113) assert(kind==0x7ef7 && scale==4);
    if(!sprites)first_x=p[0];
    ++sprites;
}
static void visual(void *c,mu_objects *o,int32_t i,int has,mu_object_model *m)
{(void)c;(void)o;(void)i;(void)has;(void)m;++generic;}
int main(int argc,char **argv)
{
    assert(argc==2);char error[256];
    mu_objects *o=calloc(1,sizeof *o);mu_object_model *m=calloc(1,sizeof *m);assert(o&&m);
    assert(mu_bmd_load_file(argv[1],&m->bmd,error,sizeof error)==0);
    assert(mu_model_init(&m->model,&m->bmd,NULL,error,sizeof error)==0);m->loaded=1;
    o->count=1;o->rt.ready=1;o->rt.images=calloc(1,MU_OBJ_SIZE);assert(o->rt.images);
    o->rt.particle=particle;o->rt.sprite=sprite;o->rt.visual=visual;
    uint8_t *img=o->rt.images;img[MU_OBJF_LIVE]=img[MU_OBJF_VISIBLE]=1;
    mu_obj_set_f32(img,MU_OBJF_SCALE,2);mu_obj_set_f32(img,MU_OBJF_ALPHA,1);mu_obj_set_f32(img,MU_OBJF_ALPHA_TARGET,1);
    mu_obj_set_f32(img,MU_OBJF_POSITION,99);mu_obj_set_f32(img,MU_OBJF_POSITION+4,200);mu_obj_set_f32(img,MU_OBJF_POSITION+8,300);
    const int types[]={70,80,70,80,66,72,113,114,115,116,118,66,72,113,114,115,116,118};
    mu_draw_options options;
    for(unsigned n=0;n<sizeof types/sizeof *types;++n) {
        typ=types[n];o->world=n<2?57:n<4?58:n<11?80:81;
        o->models[typ]=m;mu_obj_set_i32(img,MU_OBJF_TYPE,typ);
        mu_obj_set_i32(img,MU_OBJF_HIDDEN_MESH,typ==115||typ==118?-1:-2);
        particles=sprites=0;
        for(int k=0;k<200;++k)(void)mu_objects_prepare_index(o,0,NULL,6,&options);
        if(typ==70 || typ==80)assert(particles==400 && sprites==0);
        else if(typ==66)assert(sprites==400 && first_x==379);
        else if(typ==72)assert(sprites==800 && first_x==359);
        else if(typ==113)assert(particles==200 && sprites==200);
        else if(typ==115)assert(particles==4000);
        else if(typ==118)assert(particles==800);
        else assert(particles>0);
        uint32_t seed=o->rt.seed;int oldp=particles,olds=sprites;
        m->loaded=0;(void)mu_objects_prepare_index(o,0,NULL,6,&options);m->loaded=1;
        o->models[typ]=NULL;(void)mu_objects_prepare_index(o,0,NULL,6,&options);
        assert(o->rt.seed==seed && particles==oldp && sprites==olds);
    }
    assert(generic==0);
    typ=66;o->world=80;o->models[typ]=m;mu_obj_set_i32(img,MU_OBJF_TYPE,typ);mu_obj_set_i32(img,MU_OBJF_HIDDEN_MESH,-2);
    mu_obj_set_f32(img,MU_OBJF_POSITION,999);sprites=0;(void)mu_objects_prepare_index(o,0,NULL,6,&options);
    assert(sprites==2 && first_x==1279);
    m->bmd.bone_count=1;long bad=o->rt.draw_unsupported;sprites=0;
    (void)mu_objects_prepare_index(o,0,NULL,6,&options);assert(sprites==0 && o->rt.draw_unsupported==bad+1);
    m->bmd.bone_count=15;o->world=83;(void)mu_objects_prepare_index(o,0,NULL,6,&options);assert(generic==1);
    free(o->rt.images);mu_model_free(&m->model);mu_bmd_free(&m->bmd);free(m);free(o);return 0;
}
