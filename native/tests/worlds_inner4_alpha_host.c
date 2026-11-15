/* INNER-004: actual scene draws preserve GREATER 0 / 0.25 in software, immediate GL and captured batches. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../core/mu_raster.h"
#include "../viewer/gl_backend.h"
#include "../viewer/gl_batch.h"
#include "../viewer/gl_headless.h"
#ifdef __APPLE__
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif

enum { W=32,H=32 };
static const uint8_t black[4]={0,0,0,255};
static const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
static int lit(const uint8_t *p)
{
    int n=0;for(int i=0;i<W*H;++i)n+=p[4*i]>8;return n;
}
static int draw(mu_model *m,mu_draw_options *o,mu_render_backend *b)
{
    mu_draw_stats stats={0};assert(mu_scene_draw_model(m,o,b,&stats)==0);
    assert(stats.corners==3 && stats.refused==0 && stats.faulted==0);return 0;
}
int main(int argc,char **argv)
{
    assert(argc==2);char error[256];mu_bmd bmd;mu_model model;
    assert(mu_bmd_load_file(argv[1],&bmd,error,sizeof error)==0);
    mu_model_params p;mu_model_default_params(&p);p.lighting=0;
    assert(mu_model_init(&model,&bmd,&p,error,sizeof error)==0);assert(mu_model_update(&model)==0);
    /* Synthetic host-owned geometry, one triangle in clip space. */
    const float triangle[9]={-0.8f,-0.8f,0,0.8f,-0.8f,0,-0.8f,0.8f,0};
    memcpy((void *)mu_model_vertices(&model,0),triangle,sizeof triangle);
    uint8_t pixel[4]={255,255,255,0};mu_image im={1,1,4,pixel};
    const mu_image *slots[4]={&im,NULL,NULL,NULL};int8_t components[4]={4,3,3,3};
    uint32_t filter[4]={GL_NEAREST,GL_NEAREST,GL_NEAREST,GL_NEAREST};
    uint32_t wrap[4]={GL_REPEAT,GL_REPEAT,GL_REPEAT,GL_REPEAT};
    mu_textures textures={0};textures.count=textures.model_count=4;textures.slots=slots;
    textures.components=components;textures.filter=filter;textures.wrap=wrap;
    mu_draw_options options;mu_draw_default_options(&options);options.mesh_plus_one=1;options.textures=&textures;
    options.cull=0;
    mu_raster r;assert(mu_raster_init(&r,W,H)==0);r.textures=slots;r.texture_count=4;
    memcpy(r.view,identity,sizeof identity);memcpy(r.projection,identity,sizeof identity);
    mu_render_backend raster;mu_raster_backend(&r,&raster);
    int have_gl=mu_gl_headless_begin(W,H,error,sizeof error)==0;
    if(!have_gl){fprintf(stderr,"no GL: %s\n",error);return 3;}
    int cases=0;
    const uint8_t alphas[]={0,32,63,64,255};
    for(unsigned a=0;a<sizeof alphas;++a) {
        pixel[3]=alphas[a];
        mu_gl_backend gl={0};mu_gl_upload(&gl,&textures,0);
        for(int pass=0;pass<3;++pass) {
            options.alpha_reference_set=(uint8_t)(pass==1);options.alpha_reference=0;
            const int want=pass==1 ? alphas[a]>0 : alphas[a]>63;
            mu_raster_clear(&r,black);draw(&model,&options,&raster);
            assert((lit(r.color)>0)==want && r.alpha_reference==0.25f);
            uint8_t immediate[W*H*4],batch[W*H*4];
            for(int mode=0;mode<2;++mode) {
                mu_gl_frame(W,H,black,identity,identity);
                gl.batch=mode?mu_gl_batch_new():NULL;
                if(gl.batch)mu_gl_batch_session_begin(gl.batch);
                mu_render_backend backend;mu_gl_backend_bind(&gl,&backend);draw(&model,&options,&backend);
                if(gl.batch)mu_gl_batch_session_end(gl.batch);
                GLfloat reference=-1;glGetFloatv(GL_ALPHA_TEST_REF,&reference);assert(reference==0.25f);
                mu_gl_read(W,H,mode?batch:immediate);
                assert((lit(mode?batch:immediate)>0)==want);
                if(gl.batch){mu_gl_batch_free(gl.batch);gl.batch=NULL;}
            }
            assert(memcmp(immediate,batch,sizeof immediate)==0);++cases;
        }
        mu_gl_release(&gl);
    }
    mu_gl_headless_end();mu_raster_free(&r);mu_model_free(&model);mu_bmd_free(&bmd);
    printf("alpha reference: %d scene cases, software/immediate/batched GL and restoration OK\n",cases);
    return 0;
}
