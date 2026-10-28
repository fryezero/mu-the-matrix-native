/* SESSION-ITEMS-001a: synthetic server ground policy; results use recorded routes.
 * Pick-up answer routing is unknown. "pickup" explicitly schedules a 0x21 removal,
 * not a reconstructed pickup answer or an encrypted request round trip. */
#include "../behavior.h"
#include "../items_demo.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
void *mu_items_demo_state(mu_fixture *fixture) { return mu_fixture_behavior_state(fixture,"items"); }
typedef struct item_slot { uint8_t bytes[19], used, sent, remove; uint32_t due; } item_slot;
typedef struct items_fixture { item_slot slots[1000]; uint32_t tick; int latency, despawn; } items_fixture;
static int arg(const char *args,const char *name,int fallback)
{
    char key[40]; snprintf(key,sizeof key,"%s=",name); const char *p=strstr(args,key);
    return p?(int)strtol(p+strlen(key),NULL,0):fallback;
}
static void *open_items(mu_fixture_ctx *ctx,const char *args,char *error,size_t cap)
{
    (void)ctx; items_fixture *s=calloc(1,sizeof *s); if(!s)return NULL;
    s->latency=arg(args,"latency",4); s->despawn=arg(args,"despawn",1500);
    if(s->latency<0 || s->despawn<0) {snprintf(error,cap,"negative items timer");free(s);return NULL;}
    return s;
}
int32_t mu_items_demo_drop(void *state,int32_t code,int32_t level,uint8_t excellent,uint8_t ancient,
                           int32_t zen,float x,float y,int drop)
{
    items_fixture *s=state; if(!s)return -1;
    int slot=0; while(slot<1000 && s->slots[slot].used)++slot; if(slot==1000)return -1;
    item_slot *e=&s->slots[slot]; memset(e,0,sizeof *e); e->used=1;
    unsigned key=(unsigned)slot|(drop?0x8000u:0);
    e->bytes[0]=(uint8_t)(key>>8); e->bytes[1]=(uint8_t)key;
    e->bytes[2]=(uint8_t)(x/100); e->bytes[3]=(uint8_t)(y/100);
    uint8_t *b=e->bytes+4; memset(b,255,15); b[0]=(uint8_t)code; b[1]=(uint8_t)level; b[2]=255;
    b[3]=(uint8_t)((excellent&127)|(((code>>8)&1)<<7)); b[4]=ancient;
    b[5]=(uint8_t)((((code>>9)&15)<<4)|((code>>13)&1)); b[6]=0;
    if(code==0x1c0f) {b[6]=(uint8_t)(zen>>24);b[1]=(uint8_t)(zen>>16);b[2]=(uint8_t)(zen>>8);b[4]=(uint8_t)zen;}
    return slot;
}
int mu_items_demo_remove(void *state,int32_t slot)
{
    items_fixture *s=state; if(!s || slot<0 || slot>=1000 || !s->slots[slot].used)return 0;
    s->slots[slot].remove=1; s->slots[slot].due=s->tick+(uint32_t)s->latency; return 1;
}
static int command(void *self,mu_fixture_ctx *ctx,const char *line,char *error,size_t cap)
{
    (void)ctx; int code,level=0,slot; float x,y;
    if(sscanf(line,"drop %i %f %f %i",&code,&x,&y,&level)>=3)
        return mu_items_demo_drop(self,code,level,0,0,100,x*100+50,y*100+50,1)<0?-1:0;
    if(sscanf(line,"pickup %d",&slot)==1 && mu_items_demo_remove(self,slot))return 0;
    snprintf(error,cap,"invalid items command or full table");return -1;
}
static void step(void *self,mu_fixture_ctx *ctx,uint32_t now)
{
    (void)now; items_fixture *s=self; s->tick=mu_fx_step(ctx);
    for(int i=0;i<1000;++i) {
        item_slot *e=&s->slots[i]; if(!e->used)continue;
        mu_packet p;
        if(!e->sent) {
            mu_packet_begin(&p,0xc2,0x20);uint8_t count=1;mu_packet_add(&p,&count,1,0);mu_packet_add(&p,e->bytes,19,0);
            if(mu_fx_send(ctx,MU_CONN_GAME,&p,0)==0) {e->sent=1;e->due=s->tick+(uint32_t)s->despawn;}
        } else if((e->remove || s->despawn>0) && e->due<=s->tick) {
            uint8_t b[3]={1,(uint8_t)(i>>8),(uint8_t)i}; mu_packet_begin(&p,0xc2,0x21);mu_packet_add(&p,b,3,0);
            if(mu_fx_send(ctx,MU_CONN_GAME,&p,0)==0)memset(e,0,sizeof *e);
        }
    }
}
const mu_fixture_behavior mu_fx_items={.name="items",.open=open_items,.on_command=command,.on_step=step,.close=free};
