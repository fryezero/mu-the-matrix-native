/* SESSION-COMBAT-001. Synthetic server policy only. All results leave as frames. */
#include "../behavior.h"
#include "../combat_demo.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define ACTORS 400
#define QUEUE 64
typedef struct fighter { uint16_t key, cls; int32_t hp; uint8_t x,y,dead,used; uint32_t counter_due,respawn_due,kills; } fighter;
typedef struct pending { uint32_t due; uint16_t key; int32_t amount,type; uint8_t flag8; } pending;
typedef struct combat_fixture {
    fighter actors[ACTORS];pending queue[QUEUE];int count;
    int32_t hp,lo,hi,latency,respawn,counter,hero_hp,hero_max,hero_respawn;
    uint32_t rng,hero_due;uint16_t hero_key;uint8_t hero_dead,hero_ready,hero_joined;int32_t hero_x,hero_y,home_x,home_y,world;
} combat_fixture;
static int arg(const char *args,const char *name,int value)
{
    char key[64];snprintf(key,sizeof key,"%s=",name);const char *p=strstr(args,key);return p?(int)strtol(p+strlen(key),NULL,0):value;
}
static uint32_t random_roll(combat_fixture *s)
{
    uint32_t x=s->rng?s->rng:0x9e3779b9u;x^=x<<13;x^=x>>17;x^=x<<5;s->rng=x;return x;
}
static fighter *find(combat_fixture *s,uint16_t key)
{
    for(int i=0;i<ACTORS;++i) if(s->actors[i].used && s->actors[i].key==key) return &s->actors[i];
    return NULL;
}
static void send_frame(mu_fixture_ctx *ctx,uint8_t *b,size_t size)
{
    mu_packet p;mu_packet_begin(&p,b[0],b[b[0]==0xc2?3:2]);size_t h=b[0]==0xc2?4u:3u;
    mu_packet_add(&p,b+h,size-h,0);mu_fx_send(ctx,MU_CONN_GAME,&p,0);
}
static void put32(uint8_t *p,int32_t v) { memcpy(p,&v,4); }
static void rewards(combat_fixture *s,mu_fixture_ctx *ctx,fighter *f)
{
    ++f->kills;uint32_t kills=0;
    for(int i=0;i<ACTORS;++i)if(s->actors[i].used && s->actors[i].cls==f->cls)kills+=s->actors[i].kills;
    int l=1+f->cls%40,gain=(l+25)*l/3;
    uint8_t exp[10]={0xc1,10,0x16,(uint8_t)(f->key>>8),(uint8_t)f->key,(uint8_t)(gain>>8),(uint8_t)gain};send_frame(ctx,exp,sizeof exp);
    /* Synthetic Short Sword, one viewport row. SESSION-ITEMS will own the full ground domain. */
    uint8_t drop[24]={0xc2,0,24,0x20,1,0x80,1,f->x,f->y};drop[9]=1;drop[10]=0;drop[11]=255;
    send_frame(ctx,drop,sizeof drop);
    uint8_t quest[48]={0xc1,48,0xa4};for(int i=0;i<5;++i) {put32(quest+8+i*8,-1);put32(quest+12+i*8,-1);}
    put32(quest+8,f->cls);put32(quest+12,(int32_t)kills);send_frame(ctx,quest,sizeof quest);
}
static void schedule(combat_fixture *s,mu_fixture_ctx *ctx,uint16_t key,int amount,int type,int flag8,uint32_t delay)
{
    if(s->count==QUEUE) return;
    s->queue[s->count++]=(pending){mu_fx_step(ctx)+delay,key,amount,type,(uint8_t)flag8};
}
static void attack(combat_fixture *s,mu_fixture_ctx *ctx,uint16_t key)
{
    fighter *f=find(s,key);if(!f || f->dead) return;
    uint32_t r=random_roll(s)%100u;int span=s->hi-s->lo+1;
    int damage=s->lo+(int)(random_roll(s)%(uint32_t)(span>0?span:1)),type=0,flag=0;
    if(r<10)damage=0;else if(r<20) {type=3;damage=damage*3/2;}else if(r<30) {type=2;damage=damage*6/5;}else if(r<35) {flag=1;damage*=2;}
    schedule(s,ctx,key,damage,type,flag,(uint32_t)s->latency);
    if(s->counter && !f->counter_due) f->counter_due=mu_fx_step(ctx)+15;
}
static void *open_combat(mu_fixture_ctx *ctx,const char *args,char *error,size_t cap)
{
    (void)ctx;combat_fixture *s=calloc(1,sizeof *s);if(!s)return NULL;
    s->hp=arg(args,"hp",260);s->lo=arg(args,"lo",30);s->hi=arg(args,"hi",95);s->latency=arg(args,"latency",3);
    s->rng=(uint32_t)arg(args,"seed",20261018);s->counter=arg(args,"counter",1);s->respawn=arg(args,"respawn",125);
    s->hero_max=s->hero_hp=arg(args,"hero_hp",400);s->hero_respawn=arg(args,"hero_respawn",100);s->hero_key=1;
    if(s->hp<=0 || s->lo<0 || s->hi<s->lo || s->hi>1000000 || s->latency<0 || s->respawn<0) {
        snprintf(error,cap,"invalid combat fixture parameters");free(s);return NULL;
    }
    return s;
}
void mu_combat_demo_observe(void *state,const mu_world_actors *a,int32_t hero_x,int32_t hero_y)
{
    combat_fixture *s=state;if(!s)return;
    s->world=a->map?a->map->world:0;
    if(!s->hero_ready) {s->home_x=hero_x;s->home_y=hero_y;}
    s->hero_x=hero_x;s->hero_y=hero_y;s->hero_ready=1;
    for(int i=0;i<a->count;++i) {
        const mu_world_actor *actor=&a->list[i];if(actor->actor.spec.monster_type<0)continue;
        fighter *f=find(s,(uint16_t)actor->session_key);
        if(!f) {for(int j=0;j<ACTORS;++j)if(!s->actors[j].used) {f=&s->actors[j];*f=(fighter){.key=(uint16_t)actor->session_key,.cls=(uint16_t)actor->server_class,.hp=s->hp,.used=1};break;}}
        if(f) {f->x=(uint8_t)actor->tile[0];f->y=(uint8_t)actor->tile[1];}
    }
}
static int request(void *self,mu_fixture_ctx *ctx,const mu_fixture_request *rq)
{
    combat_fixture *s=self;
    if(rq->opcode==0x43 && rq->length==7) {attack(s,ctx,(uint16_t)((rq->bytes[3]<<8)|rq->bytes[4]));return 1;}
    if(rq->opcode==0xa2)return 1;
    return 0;
}
static int command(void *self,mu_fixture_ctx *ctx,const char *line,char *error,size_t cap)
{
    combat_fixture *s=self;unsigned key=0,cls=0,x=0,y=0;int damage=0;
    if(sscanf(line,"actor %u %u %u %u",&key,&cls,&x,&y)==4) {
        for(int i=0;i<ACTORS;++i)if(!s->actors[i].used) {s->actors[i]=(fighter){.key=(uint16_t)key,.cls=(uint16_t)cls,.hp=s->hp,.x=(uint8_t)x,.y=(uint8_t)y,.used=1};return 0;}
    }
    if(sscanf(line,"damage %u %d",&key,&damage)==2) {schedule(s,ctx,(uint16_t)key,damage,0,0,0);return 0;}
    if(sscanf(line,"cast %u",&key)==1) {attack(s,ctx,(uint16_t)key);return 0;}
    snprintf(error,cap,"unknown combat command or full actor table");return -1;
}
static void hero_place(combat_fixture *s,mu_fixture_ctx *ctx)
{
    uint8_t b[32]={0xc1,32,0xa0,0x30,(uint8_t)s->home_x,(uint8_t)s->home_y,(uint8_t)s->world,(uint8_t)(s->world>>8),1};
    b[10]=(uint8_t)s->hero_max;b[11]=(uint8_t)(s->hero_max>>8);send_frame(ctx,b,sizeof b);
}
static void respawn_actor(combat_fixture *s,mu_fixture_ctx *ctx,fighter *f)
{
    uint8_t b[33]={0xc2,0,33,0x13,1,(uint8_t)((f->key>>8)|0x80),(uint8_t)f->key,(uint8_t)(f->cls>>8),(uint8_t)f->cls,
        f->x,f->y,f->x,f->y,0x10};
    send_frame(ctx,b,sizeof b);f->dead=0;f->hp=s->hp;f->respawn_due=0;
}
static void step(void *self,mu_fixture_ctx *ctx,uint32_t now)
{
    (void)now;combat_fixture *s=self;uint32_t tick=mu_fx_step(ctx);int kept=0;
    if(s->hero_ready && !s->hero_joined) {hero_place(s,ctx);s->hero_joined=1;}
    if(s->hero_due && s->hero_due<=tick) {hero_place(s,ctx);s->hero_due=0;s->hero_dead=0;s->hero_hp=s->hero_max;}
    for(int k=0;k<s->count;++k) {
        pending e=s->queue[k];if(e.due>tick) {s->queue[kept++]=e;continue;}
        fighter *f=find(s,e.key);int hero=e.key==s->hero_key;
        if((hero && s->hero_dead) || (!hero && (!f || f->dead)))continue;
        uint8_t p[24]={0xc1,24,0xf3,(uint8_t)((e.key>>8)|0x80),(uint8_t)e.key};
        put32(p+8,e.amount);p[13]=(uint8_t)(e.type|(e.flag8?0x80:0));send_frame(ctx,p,sizeof p);
        if(hero) {
            s->hero_hp-=e.amount;
            if(s->hero_max>0 && s->hero_hp<=0) {
                s->hero_dead=1;s->hero_due=tick+14u+(uint32_t)s->hero_respawn;
                for(int j=0;j<ACTORS;++j)s->actors[j].counter_due=0;
                uint8_t die[9]={0xc1,9,0x17,(uint8_t)(s->hero_key>>8),(uint8_t)s->hero_key};send_frame(ctx,die,sizeof die);
            }
            continue;
        }
        f->hp-=e.amount;
        if(f->hp<=0) {
            f->dead=1;f->counter_due=0;f->respawn_due=tick+100u+(uint32_t)s->respawn;
            uint8_t die[9]={0xc1,9,0x17,(uint8_t)(f->key>>8),(uint8_t)f->key};send_frame(ctx,die,sizeof die);
            rewards(s,ctx,f);
        }
    }
    s->count=kept;
    for(int k=0;k<ACTORS;++k) {
        fighter *f=&s->actors[k];if(!f->used)continue;
        if(f->dead && f->respawn_due && f->respawn_due<=tick)respawn_actor(s,ctx,f);
        if(f->dead || s->hero_dead || !f->counter_due || f->counter_due>tick)continue;
        int dx=(int)f->x-s->hero_x,dy=(int)f->y-s->hero_y;
        if(dx*dx+dy*dy>3)continue;
        uint8_t action[9]={0xc1,9,0xc5,(uint8_t)(f->key>>8),(uint8_t)f->key,1,0x78,(uint8_t)(s->hero_key>>8),(uint8_t)s->hero_key};
        send_frame(ctx,action,sizeof action);f->counter_due=tick+50;
        int span=s->hi-s->lo+1;int amount=s->lo+(int)(random_roll(s)%(uint32_t)(span>0?span:1));
        schedule(s,ctx,s->hero_key,amount/3,0,0,14);
    }
}
const mu_fixture_behavior mu_fx_combat={.name="combat",.open=open_combat,.on_plain_request=request,.on_step=step,.on_command=command,.close=free};
