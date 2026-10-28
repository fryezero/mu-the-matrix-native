/* Uruk nested consumers: production dispatch, fixed pools, weather input and asset boundaries. */
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
static const int kinds[][2]={{0x7f5a,69},{0x7f89,25},{0x801b,7},{0x8184,2},{0x7f5a,22},{0x7fd5,0}};
static const float pos[3]={99,100,100}, zero[3]={0}, light[3]={1,0.5f,0.25f};
static const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
static const mu_world_particles_target target={NULL,backend};
static int producers_checked, refusals;
static void create_kinds(void)
{
    for(unsigned i=0;i<sizeof kinds/sizeof *kinds;++i)
        assert(mu_world_particles_create(&p,kinds[i][0],pos,zero,light,kinds[i][1],1));
}
/* Real Uruk visual 0x00e6f3d5 through the attached particle module. Type 105's 0x7fdd/3 is
 * RENDER-EFFECTS-004's, so it is not exercised here. */
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
    o->world=p.world=100;
    const int types[]={89,90,91,92,93,106,108,108};
    for(unsigned i=0;i<sizeof types/sizeof *types;++i) {
        int type=types[i], weather=i==6;  /* 108 twice: explicit weather 1, then the default 0 */
        o->rt.uruk_weather=weather; o->models[type]=m; mu_obj_set_i32(img,MU_OBJF_TYPE,type);
        mu_pt_system_clear(&p.list); uint64_t unsupported=p.stats.unsupported;
        long refused=o->rt.draw_unsupported;
        for(int k=0;k<100;++k) (void)mu_objects_prepare_index(o,0,NULL,6,&options);
        assert(p.stats.unsupported==unsupported);
        if(type==108&&!weather) assert(p.list.count==0&&o->rt.draw_unsupported==refused);
        else assert(p.list.count>0);
        if(type==108&&weather) { assert(o->rt.draw_unsupported>refused); refusals+=(int)(o->rt.draw_unsupported-refused); }
        uint32_t seed=o->rt.seed; uint64_t calls=p.rand_calls; int count=p.list.count;
        m->loaded=0; (void)mu_objects_prepare_index(o,0,NULL,6,&options);
        m->loaded=1; o->models[type]=NULL; (void)mu_objects_prepare_index(o,0,NULL,6,&options);
        assert(o->rt.seed==seed&&p.rand_calls==calls&&p.list.count==count);
        producers_checked+=100;
    }
    p.objects=NULL; free(o->rt.images); mu_model_free(&m->model); mu_bmd_free(&m->bmd); free(m); free(o);
}
int main(int argc,char **argv)
{
    assert(argc==3); char error[256];
    assert(mu_world_particles_open(&p,argv[1],NULL,100,1,0,error,sizeof error)==0);
    create_kinds(); mu_world_particles_step(&p,123456);
    assert(p.list.count==6&&p.stats.unsupported==0);
    assert(mu_world_particles_draw(&p,identity,&target)==6);
    assert(p.stats.drawn_particles==6&&vertices==36);
    /* flare_mono is the last effect slot, before rain02/rain03, with the loader's sampling. */
    const int slot=MU_WORLD_PT_BITMAPS-3;
    assert(p.bitmaps.slots[slot]&&p.bitmaps.filter[slot]==0x2601&&p.bitmaps.wrap[slot]==0x2900);
    assert(p.bitmaps.images[slot].width==64&&p.bitmaps.images[slot].height==16);
    producers(argv[2]);
    for(unsigned i=0;i<sizeof kinds/sizeof *kinds;++i) {
        mu_pt_system_clear(&p.list); int capacity=p.list.capacity; p.list.capacity=0;
        uint64_t overflow=p.stats.overflow, unsupported=p.stats.unsupported, calls=p.rand_calls;
        assert(!mu_world_particles_create(&p,kinds[i][0],pos,zero,light,kinds[i][1],1));
        assert(p.list.count==0&&p.stats.overflow==overflow+1&&p.stats.unsupported==unsupported&&p.rand_calls>calls);
        p.list.capacity=capacity;
    }
    const int absent[][2]={{0x7f5a,70},{0x7f5a,23},{0x7f89,26},{0x801b,8},{0x8184,1},{0x7fd5,1}};
    for(unsigned i=0;i<sizeof absent/sizeof *absent;++i)
        assert(!mu_pt_kind_supported(absent[i][0],absent[i][1]));
    mu_world_particles_close(&p);
    assert(mu_world_particles_open(&p,argv[1],NULL,100,1,1,error,sizeof error)==0);
    create_kinds(); assert(mu_world_particles_draw(&p,identity,&target)==0&&p.stats.unsupported==0);
    mu_world_particles_close(&p);
    printf("6 consumers, 1 registration, 6 quads, %d producer preparations, %d keyed refusals kept, "
           "16 missing-model checks, 6 full-pool checks, weather-off silence, absent assets: OK\n",
           producers_checked, refusals);
    return 0;
}
