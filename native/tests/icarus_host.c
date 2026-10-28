/* Synthetic integration of the production Icarus event consumer and real pools. */
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "../core/mu_objects_icarus.h"
#include "../core/mu_particles.h"
static int effects,sprites,joints;
static void effect(void *ctx,int32_t type,int32_t sub,const float p[3],const float a[3],const float l[3],int32_t owner)
{ (void)ctx;(void)p;(void)a;(void)l;assert(type==0x1a1 && sub==0 && owner==-1);++effects; }
static void sprite(void *ctx,int32_t type,const float p[3],float scale,const float l[3],int32_t owner,float rot,int32_t blend,int32_t axes)
{ (void)ctx;(void)p;(void)l;assert(type==0x7f8a && scale==0.5f && owner==-1 && rot==0 && blend==0 && axes==4);++sprites; }
static void joint(void *ctx,int32_t type,const float p[3],const float t[3],const float a[3],int32_t sub,int32_t owner,float scale)
{ (void)ctx;(void)p;(void)t;(void)a; assert((type==0x7f7d && sub==0 && owner==-1 && scale>=40) || (type==0x7f7c && sub==6 && owner==0 && scale>=10));++joints; }
int main(void)
{
    mu_objects *o=calloc(1,sizeof *o);assert(o);
    o->world=10;o->rt.icarus_count=40;o->rt.effect=effect;o->rt.sprite=sprite;o->rt.joint=joint;
    o->count=1; o->rt.images=calloc(1,MU_OBJ_SIZE);assert(o->rt.images);
    float hero[3]={1550,1350,285};
    for(int i=0;i<500;++i) {o->rt.light_count=0;mu_objects_icarus_sky(o,hero);}
    assert(effects>0 && joints>0 && o->rt.effect_events==effects);
    int32_t ordinal=0;
    for(int i=0;i<500;++i) mu_objects_icarus_object(o,0,1,&ordinal);
    assert(sprites>0 && joints>2*sprites && ordinal==sprites);
    int32_t saved=ordinal;
    for(int i=0;i<50;++i) mu_objects_icarus_object(o,0,0,&ordinal);
    assert(ordinal==saved+50);
    free(o->rt.images);free(o);
    return 0;
}
