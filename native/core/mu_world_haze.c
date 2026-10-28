#include "mu_world_haze.h"
#include "mu_textures.h"
#include "mu_terrain.h"
#include <stdio.h>
#include <string.h>

void mu_world_haze_open(mu_world_haze *h, const char *root, int32_t world)
{
    memset(h,0,sizeof *h);
    h->world=world;
    for (int i=0;i<2;++i) {
        const char *name=mu_world_haze_texture(world,i);
        if (!name) continue;
        char directory[4096],path[4096],error[512];
        char relative[256];snprintf(relative,sizeof relative,"%s",name);
        char *slash=strrchr(relative,'/');
        if (!slash) continue;
        *slash=0;
        snprintf(directory,sizeof directory,"%s/Data/%s",root,relative);
        int8_t components=0;
        if (mu_image_resolve(directory,slash+1,path,sizeof path)) {
            if (mu_texture_upload_file(path,'j',&h->images[i],&components,error,sizeof error))
                fprintf(stderr,"world haze: %s\n",error);
        } else fprintf(stderr,"world haze: missing %s\n",name);
    }
}

void mu_world_haze_close(mu_world_haze *h)
{
    for (int i=0;i<2;++i) mu_image_free(&h->images[i]);
    memset(h,0,sizeof *h);
}

typedef struct haze_raster {
    const mu_world_haze *h;
    mu_raster *r;
    mu_render_backend backend;
    mu_meshdraw_state state;
} haze_raster;
static void state(void *c,int32_t s,int32_t a)
{
    haze_raster *h=c;
    mu_world_state(s,a,&h->state);
    h->state.depth_test=0;
}
static void bind(void *c,int32_t id)
{
    haze_raster *h=c;
    mu_raster_set(h->r,&h->state,&h->h->images[id-0x7f21],1);
}
static void begin(void *c,int32_t mode) {mu_raster_begin_mode(((haze_raster *)c)->r,mode);}
static void end(void *c) {mu_raster_end_mode(((haze_raster *)c)->r);}
static void tex(void *c,float u,float v) {haze_raster *h=c;h->backend.sink.texcoord(h->r,u,v);}
static void c3(void *c,const float *rgb) {haze_raster *h=c;h->backend.sink.color3(h->r,rgb);}
static void c4(void *c,float r,float g,float b,float a) {haze_raster *h=c;h->backend.sink.color4(h->r,r,g,b,a);}
static void vertex(void *c,const float *v)
{
    haze_raster *h=c;
    /* A failed lookup must not draw an untextured white screen. */
    if (!h->r->texture || !h->r->texture->rgba) return;
    h->backend.sink.vertex(h->r,v);
}
void mu_world_haze_draw_raster(const mu_world_haze *h,float time,mu_raster *r)
{
    if (!mu_world_haze_texture(h->world,0)) return;
    float view[16],projection[16];
    memcpy(view,r->view,sizeof view);memcpy(projection,r->projection,sizeof projection);
    memset(r->view,0,sizeof r->view);memset(r->projection,0,sizeof r->projection);
    for (int k=0;k<16;k+=5) r->view[k]=r->projection[k]=1;
    r->projection[0]=2.0f/(float)r->width;r->projection[5]=2.0f/(float)r->height;
    r->projection[10]=-1;r->projection[12]=-1;r->projection[13]=-1;
    haze_raster adapter={.h=h,.r=r};mu_raster_backend(r,&adapter.backend);
    mu_terrain_sink sink={&adapter,state,bind,begin,tex,c3,c4,vertex,end};
    mu_world_haze_draw(h->world,time,(uint32_t)r->width,(uint32_t)r->height,&sink);
    memcpy(r->view,view,sizeof view);memcpy(r->projection,projection,sizeof projection);
}
