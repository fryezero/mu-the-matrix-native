#include "../session/mu_session.h"
#include "../session/mu_session_seed.h"
#include "../fixture/mu_fixture.h"
#include <assert.h>
#include <stdio.h>
typedef struct view { mu_session *s; int calls; } view;
static void present(void *ctx,int32_t slot,const uint8_t e[19])
{
    view *v=ctx; ++v->calls;
    /* Synthetic projection services, distinct from original CreateItem comparison. */
    mu_gi_item *p=(mu_gi_item *)mu_session_items(v->s).pool;
    p[slot].data.code=mu_gi_item_code(e+4);p[slot].object.live=1;
}
int main(int argc,char **argv)
{
    if(argc!=2)return 2;
    char error[512];mu_fixture_options opt={argv[1],NULL,7};
    mu_fixture *f=mu_fixture_open(&opt,error,sizeof error);assert(f);
    mu_transport *t=mu_fixture_transport(f);mu_session_config cfg={0};cfg.transport=t;
    mu_fixture_endpoint(f,"game",&cfg.connect_server);
    mu_session_seed seed={0};mu_session *s=mu_session_open_seeded(&cfg,&seed,error,sizeof error);assert(s);
    view a={s,0},b={s,0};mu_session_items_bind(s,present,&a);
    for(unsigned tick=1;tick<=2;++tick){mu_transport_poll(t,tick*40);mu_session_pump(s,tick*40);}
    assert(a.calls==1);mu_items_view v=mu_session_items(s);assert(v.used[999] && v.pool[999].data.code==1);
    mu_session_items_bind(s,NULL,NULL);mu_session_detach_world(s);
    mu_sim sim=mu_session_sim_begin(s);assert(sim.ground==v.pool && sim.ground_count==1000);
    sim.ground[999].object.position[2]=180;mu_session_sim_end(s,&sim);
    mu_session_items_bind(s,present,&b);assert(b.calls==0 && mu_session_items(s).creates==1 && mu_session_items(s).pool[999].object.position[2]==180);
    for(unsigned tick=3;tick<=4;++tick){mu_transport_poll(t,tick*40);mu_session_pump(s,tick*40);}
    v=mu_session_items(s);assert(!v.used[999] && !v.pool[999].object.live && v.deletes==1);
    mu_session_items_bind(s,NULL,NULL);mu_session_items_bind(s,present,&b);assert(b.calls==0);
    mu_session_close(s);mu_transport_free(t);mu_fixture_close(f);puts("items detach/rebind/delete passed");return 0;
}
