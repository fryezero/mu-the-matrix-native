/* AUDIO-006: semantic world/distance/random plans for complete class owners. */
#ifndef MU_MONSTER_AUDIO_EXTENDED_H
#define MU_MONSTER_AUDIO_EXTENDED_H
#include "monster_audio.h"
typedef int32_t (*mu_monster_audio_random_fn)(void *);
typedef struct { int period, handled, start, count; } mu_audio_ext_node;
typedef struct { uint32_t site; int id, object, loop; } mu_audio_ext_sound;
typedef struct { uint32_t owner; int model, action; float lo, hi; int lc, hc, nan, node; } mu_audio_ext_row;
#define MU_AUDIO_EXT_NODE(n,p,h,s,c) {p,h,s,c},
#define MU_AUDIO_EXT_EDGE(n,c)
#define MU_AUDIO_EXT_SOUND(n,s,id,o,l)
#define MU_AUDIO_EXT_WORLD(w,r,n,d)
#define MU_AUDIO_EXT_ROW(r,m,a,lo,hi,lc,hc,nan,n)
static const mu_audio_ext_node mu_audio_ext_nodes[]={
#include "monster_audio_extended.inc"
};
#undef MU_AUDIO_EXT_NODE
#undef MU_AUDIO_EXT_EDGE
#define MU_AUDIO_EXT_NODE(n,p,h,s,c)
#define MU_AUDIO_EXT_EDGE(n,c) c,
static const int mu_audio_ext_edges[]={
#include "monster_audio_extended.inc"
};
#undef MU_AUDIO_EXT_EDGE
#undef MU_AUDIO_EXT_SOUND
#define MU_AUDIO_EXT_EDGE(n,c)
#define MU_AUDIO_EXT_SOUND(n,s,id,o,l) {s,id,o,l},
static const mu_audio_ext_sound mu_audio_ext_sounds[]={
#include "monster_audio_extended.inc"
};
#undef MU_AUDIO_EXT_SOUND
#undef MU_AUDIO_EXT_ROW
#define MU_AUDIO_EXT_SOUND(n,s,id,o,l)
#define MU_AUDIO_EXT_ROW(r,m,a,lo,hi,lc,hc,nan,n) {r,m,a,lo,hi,lc,hc,nan,n},
static const mu_audio_ext_row mu_audio_ext_rows[]={
#include "monster_audio_extended.inc"
};
#undef MU_AUDIO_EXT_ROW
#define MU_AUDIO_EXT_ROW(r,m,a,lo,hi,lc,hc,nan,n)
static inline int mu_monster_audio_extended_known(int world)
{
#undef MU_AUDIO_EXT_WORLD
#define MU_AUDIO_EXT_WORLD(w,r,n,d) if(world==(w))return 1;
#include "monster_audio_extended.inc"
#undef MU_AUDIO_EXT_WORLD
#define MU_AUDIO_EXT_WORLD(w,r,n,d)
    return 0;
}
/* Distance is the original XY scalar. The native dispatch applies its earlier
 * >500 consume too. A missing RNG callback refuses a random decision. */
static inline mu_monster_sound_plan mu_monster_sound_extended(int world,int model,uint16_t action,
    float frame,float distance,mu_monster_audio_random_fn random,void *context)
{
    mu_monster_sound_plan p={0};uint32_t owner=0;int node=0;float limit=INFINITY;
#undef MU_AUDIO_EXT_WORLD
#define MU_AUDIO_EXT_WORLD(w,r,n,d) if(world==(w)){owner=(r);node=(n);limit=(d);}
#include "monster_audio_extended.inc"
#undef MU_AUDIO_EXT_WORLD
    if(!owner)return p;
    p.known=1;
    if(distance > limit){p.handled=1;return p;}
    for(unsigned n=0;n<sizeof mu_audio_ext_rows/sizeof mu_audio_ext_rows[0];++n){
        const mu_audio_ext_row *r=&mu_audio_ext_rows[n];
        if(owner!=r->owner || model!=r->model || (r->action>=0 && action!=r->action))continue;
        if(r->nan==2 || (r->nan ? isnan(frame) : !isnan(frame) &&
            (r->lc ? frame>=r->lo : frame>r->lo) && (r->hc ? frame<=r->hi : frame<r->hi)))node=r->node;
    }
    const mu_audio_ext_node *leaf=&mu_audio_ext_nodes[node];
    while(leaf->period){
        if(!random)return (mu_monster_sound_plan){0};
        int rem=random(context)%leaf->period;
        node=mu_audio_ext_edges[leaf->start+rem+leaf->period-1];
        leaf=&mu_audio_ext_nodes[node];
    }
    p.handled=leaf->handled;
    for(int n=0;n<leaf->count && n<4;++n){
        const mu_audio_ext_sound *s=&mu_audio_ext_sounds[leaf->start+n];
        p.sound[p.count++]=(mu_monster_sound){owner,s->site,s->id,s->object,s->loop};
    }
    return p;
}
#undef MU_AUDIO_EXT_NODE
#undef MU_AUDIO_EXT_EDGE
#undef MU_AUDIO_EXT_SOUND
#undef MU_AUDIO_EXT_ROW
#endif
