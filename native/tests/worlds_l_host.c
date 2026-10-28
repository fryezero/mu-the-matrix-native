/* Production dispatch, native fixed-pool and missing-asset/model boundaries. */
#include "../core/mu_particles.h"
#include "../core/mu_objects.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static mu_world_particles p;
static int vertices;
static void vertex(void *c, const float v[3]) { (void)c; (void)v; ++vertices; }
static void prepare(void *c, const mu_meshdraw_state *s, int32_t t) { (void)c; (void)s; assert(t >= 0); }
static void noop(void *c) { (void)c; }
static void uv(void *c, float u, float v) { (void)c; (void)u; (void)v; }
static void color(void *c, float r, float g, float b, float a) { (void)c; (void)r; (void)g; (void)b; (void)a; }
static int backend(void *c, const mu_world_particles *ps, mu_render_backend *out)
{
    (void)c; (void)ps; memset(out, 0, sizeof *out);
    out->prepare=prepare; out->begin=noop; out->end=noop;
    out->sink.vertex=vertex; out->sink.texcoord=uv; out->sink.color4=color;
    return 0;
}
static const int kinds[][2]={{0x801c,16},{0x8086,2},{0x8087,6},{0x8089,2},{0x801e,0},{0x801c,8},{0x801b,4}};
static const float pos[3]={100,100,100}, zero[3]={0}, light[3]={1,0.5f,0.25f};
static const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
static const mu_world_particles_target target={NULL,backend};
static void create_kinds(void)
{
    for(unsigned i=0;i<sizeof kinds/sizeof *kinds;++i)
        assert(mu_world_particles_create(&p,kinds[i][0],pos,zero,light,kinds[i][1],1));
}
static void producers(const char *model_path)
{
    mu_objects *o=calloc(1,sizeof *o); mu_object_model *m=calloc(1,sizeof *m); assert(o&&m);
    char error[256]; assert(mu_bmd_load_file(model_path,&m->bmd,error,sizeof error)==0);
    assert(mu_model_init(&m->model,&m->bmd,NULL,error,sizeof error)==0); m->loaded=1;
    o->count=1; o->rt.ready=1; o->rt.images=calloc(1,MU_OBJ_SIZE); assert(o->rt.images);
    uint8_t *img=o->rt.images; img[MU_OBJF_LIVE]=img[MU_OBJF_VISIBLE]=1;
    mu_obj_set_f32(img,MU_OBJF_SCALE,1); mu_obj_set_f32(img,MU_OBJF_ALPHA,1);
    mu_obj_set_f32(img,MU_OBJF_ALPHA_TARGET,1); memcpy(img+MU_OBJF_POSITION,pos,sizeof pos);
    mu_obj_set_i32(img,MU_OBJF_HIDDEN_MESH,-2);
    mu_world_particles_attach(&p,o,NULL); mu_draw_options options;
    const int types[]={66,114,70,80};
    for(unsigned i=0;i<sizeof types/sizeof *types;++i) {
        int type=types[i]; o->world=p.world=i<2?80:57;
        o->models[type]=m; mu_obj_set_i32(img,MU_OBJF_TYPE,type);
        mu_pt_system_clear(&p.list); memset(p.sprites,0,sizeof *p.sprites);
        for(int k=0;k<100;++k) (void)mu_objects_prepare_index(o,0,NULL,6,&options);
        assert(type==66?p.sprites->created==200:p.list.count>0);
        uint32_t seed=o->rt.seed; uint64_t calls=p.rand_calls; int count=p.list.count;
        uint64_t sprites=p.sprites->created;
        m->loaded=0; (void)mu_objects_prepare_index(o,0,NULL,6,&options);
        m->loaded=1; o->models[type]=NULL; (void)mu_objects_prepare_index(o,0,NULL,6,&options);
        assert(o->rt.seed==seed&&p.rand_calls==calls&&p.list.count==count&&p.sprites->created==sprites);
    }
    p.objects=NULL; free(o->rt.images); mu_model_free(&m->model); mu_bmd_free(&m->bmd); free(m); free(o);
}
int main(int argc,char **argv)
{
    assert(argc==3); char error[256];
    assert(mu_world_particles_open(&p,argv[1],NULL,80,1,0,error,sizeof error)==0);
    create_kinds(); mu_world_particles_step(&p,123456);
    assert(p.list.count==7&&p.stats.unsupported==0);
    assert(mu_world_particles_sprite(&p,0x7f6b,pos,1.2f,light,-1,0,0,4)>=0);
    assert(mu_world_particles_draw(&p,identity,&target)==8);
    assert(p.stats.drawn_particles==7&&p.stats.drawn_sprites==1&&vertices==48);
    /* Old slots remain stable; the four new load-time registrations precede rain. */
    const int sizes[][2]={{16,16},{32,32},{64,32},{128,128}};
    for(int i=MU_WORLD_PT_BITMAPS-6;i<MU_WORLD_PT_BITMAPS-2;++i) {
        assert(p.bitmaps.slots[i]&&p.bitmaps.filter[i]==0x2601&&p.bitmaps.wrap[i]==0x2900);
        int n=i-(MU_WORLD_PT_BITMAPS-6);
        assert(p.bitmaps.images[i].width==sizes[n][0]&&p.bitmaps.images[i].height==sizes[n][1]);
    }
    producers(argv[2]);
    for(unsigned i=0;i<sizeof kinds/sizeof *kinds;++i) {
        mu_pt_system_clear(&p.list); int capacity=p.list.capacity; p.list.capacity=0;
        uint64_t overflow=p.stats.overflow, unsupported=p.stats.unsupported, calls=p.rand_calls;
        assert(!mu_world_particles_create(&p,kinds[i][0],pos,zero,light,kinds[i][1],1));
        assert(p.list.count==0&&p.stats.overflow==overflow+1&&p.stats.unsupported==unsupported&&p.rand_calls>calls);
        p.list.capacity=capacity;
    }
    memset(p.sprites,0,sizeof *p.sprites);
    for(int i=0;i<MU_PT_SPRITES;++i) assert(mu_world_particles_sprite(&p,0x7f6b,pos,1,light,-1,0,0,4)>=0);
    uint64_t full=p.stats.sprites_full;
    (void)mu_world_particles_sprite(&p,0x7f6b,pos,1,light,-1,0,0,4); assert(p.stats.sprites_full==full+1);
    const int absent[][2]={{0x801c,17},{0x8086,3},{0x8087,5},{0x8089,3},{0x801e,1},{0x801b,3}};
    for(unsigned i=0;i<sizeof absent/sizeof *absent;++i)
        assert(!mu_pt_kind_supported(absent[i][0],absent[i][1]));
    mu_world_particles_close(&p);
    assert(mu_world_particles_open(&p,argv[1],NULL,80,1,1,error,sizeof error)==0);
    create_kinds(); assert(mu_world_particles_sprite(&p,0x7f6b,pos,1,light,-1,0,0,4)>=0);
    assert(mu_world_particles_draw(&p,identity,&target)==0&&p.stats.unsupported==0);
    mu_world_particles_close(&p);
    puts("7 consumers, 4 registrations, 8 quads, 400 producer preparations, 8 missing-model checks, 8 full-pool checks, absent assets: OK");
    return 0;
}
