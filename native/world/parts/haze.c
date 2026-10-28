/* RENDER-WORLDS-F: RenderMainScene's screen weather pass, before 2D labels.
 * This part owns only Tarkan/Raklion haze. It has no tick or handler state. */
#include "../world_rt_internal.h"
#include "../../core/mu_world_haze.h"

typedef struct haze_part {
    mu_world_haze haze;
#ifndef MU_WORLD_NO_GL
    GLuint texture[2];
    int drawable;
#endif
} haze_part;

static int haze_open(struct mu_world_rt *a,void *self)
{
    haze_part *p=self;
    mu_world_haze_open(&p->haze,a->root,a->world);
    return 0;
}
static void haze_close(struct mu_world_rt *a,void *self)
{
    (void)a;mu_world_haze_close(&((haze_part *)self)->haze);
}
static void haze_draw_soft(struct mu_world_rt *a,void *self,mu_world_draw *d)
{
    haze_part *p=self;
    if (!a->no_env) mu_world_haze_draw_raster(&p->haze,a->map->time,d->raster);
}
#ifndef MU_WORLD_NO_GL
static void haze_gl_setup(struct mu_world_rt *a,void *self)
{
    (void)a;
    haze_part *p=self;
    for (int i=0;i<2;++i) {
        const mu_image *im=&p->haze.images[i];
        if (!im->rgba) continue;
        glGenTextures(1,&p->texture[i]);glBindTexture(GL_TEXTURE_2D,p->texture[i]);
        glPixelStorei(GL_UNPACK_ALIGNMENT,1);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_REPEAT);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_REPEAT);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGB8,im->width,im->height,0,GL_RGBA,GL_UNSIGNED_BYTE,im->rgba);
    }
}
static void haze_gl_teardown(struct mu_world_rt *a,void *self)
{
    (void)a;
    haze_part *p=self;
    for (int i=0;i<2;++i) if (p->texture[i]) {glDeleteTextures(1,&p->texture[i]);p->texture[i]=0;}
}
static void state(void *c,int32_t state_id,int32_t arg)
{
    (void)c;
    mu_meshdraw_state s;mu_world_state(state_id,arg,&s);
    glEnable(GL_BLEND);glBlendFunc((GLenum)s.src,(GLenum)s.dst);
    glDepthMask(s.depth_mask?GL_TRUE:GL_FALSE);
    if(s.alpha_test) glEnable(GL_ALPHA_TEST);else glDisable(GL_ALPHA_TEST);
    glDisable(GL_CULL_FACE);
}
static void bind(void *c,int32_t id)
{
    haze_part *p=c;GLuint texture=p->texture[id-0x7f21];
    p->drawable=texture!=0;glBindTexture(GL_TEXTURE_2D,texture);
}
static void begin(void *c,int32_t mode) {if(((haze_part *)c)->drawable) glBegin((GLenum)mode);}
static void end(void *c) {if(((haze_part *)c)->drawable) glEnd();}
static void tex(void *c,float u,float v) {if(((haze_part *)c)->drawable) glTexCoord2f(u,v);}
static void c3(void *c,const float *rgb) {(void)c;glColor3fv(rgb);}
static void c4(void *c,float r,float g,float b,float al) {(void)c;glColor4f(r,g,b,al);}
static void vertex(void *c,const float *v) {if(((haze_part *)c)->drawable) glVertex3fv(v);}
static void haze_draw_gl(struct mu_world_rt *a,void *self,mu_world_draw *d)
{
    haze_part *p=self;
    if(a->no_env || !mu_world_haze_texture(a->world,0)) return;
    glPushAttrib(GL_ENABLE_BIT|GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT|GL_TEXTURE_BIT|GL_VIEWPORT_BIT|GL_CURRENT_BIT);
    GLint matrix;glGetIntegerv(GL_MATRIX_MODE,&matrix);
    glViewport(0,0,d->width,d->height);glDisable(GL_DEPTH_TEST);glDisable(GL_FOG);
    glEnable(GL_TEXTURE_2D);glTexEnvi(GL_TEXTURE_ENV,GL_TEXTURE_ENV_MODE,GL_MODULATE);
    glMatrixMode(GL_PROJECTION);glPushMatrix();glLoadIdentity();glOrtho(0,d->width,0,d->height,-1,1);
    glMatrixMode(GL_MODELVIEW);glPushMatrix();glLoadIdentity();
    mu_terrain_sink sink={p,state,bind,begin,tex,c3,c4,vertex,end};
    mu_world_haze_draw(a->world,a->map->time,(uint32_t)d->width,(uint32_t)d->height,&sink);
    glPopMatrix();glMatrixMode(GL_PROJECTION);glPopMatrix();glMatrixMode((GLenum)matrix);glPopAttrib();
}
#endif
const mu_world_part_ops mu_part_haze = {
    .name = "haze",
    .state_size = sizeof(haze_part),
    .open = haze_open,
    .close = haze_close,
    .draw_soft = haze_draw_soft,
#ifndef MU_WORLD_NO_GL
    .gl_setup = haze_gl_setup,
    .gl_teardown = haze_gl_teardown,
    .draw_gl = haze_draw_gl,
#endif
};
