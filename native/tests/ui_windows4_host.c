/* Production UI and offline NPC callback-order host. No live service. */
#define MU_GFX_NO_GL
#include "../gfx/mu_gfx_layer.c"
#include "../core/mu_npc.c"
#include <assert.h>
static int foreign,sounds;
static mu_gfx_layer *layer;
static char trace[256];
static void other(void *u,int m,const char *n,const char *a)
{ (void)u;(void)m;(void)a;
  if(strcmp(n,"WindowShown") && strcmp(n,"WindowHidden") && strcmp(n,"UIInit")) ++foreign; }
static void sound(void *u,int32_t id,uint32_t site)
{ (void)u;(void)id;(void)site;++sounds; }
static void field(mu_gfx_layer *L,int m,const char *suffix,const char *expected)
{
    char p[256];snprintf(p,sizeof p,"%s.%s",L->mv[m].path,suffix);
    const char *v=L->api.get_variable(L->mv[m].g,p);
    if(!v || strcmp(v,expected)) {fprintf(stderr,"%s expected %s got %s\n",p,expected,v?v:"NULL");abort();}
}
static void close_all(void *unused)
{ (void)unused;strcat(trace,"close,");mu_gfx_layer_presentation_close(layer); }
static void open_window(void *unused,const mu_npc_open *o)
{
    (void)unused;char s[64];
    assert(mu_gfx_layer_presentation_slot(layer,o->window.slot));
    int found=0;
    for(int m=MU_GFX_ELEMENTAL_MIX;m<=MU_GFX_ATTRIBUTE_SELECTOR;m++)
        if(!strcmp(FILES[m],o->window.movie)) {assert(layer->mv[m].open);++found;}
    assert(found==1);
    snprintf(s,sizeof s,"%x:%s,",o->window.slot,o->window.method==MU_TALK_TOGGLE?"toggle":"open");strcat(trace,s);
}
static void npc_tail_sound(void *unused,int32_t id)
{ (void)unused;char s[32];snprintf(s,sizeof s,"sound%d,",id);strcat(trace,s); }
int main(int argc,char **argv)
{
    assert(argc==3);
    mu_gfx_layer_config cfg={.movie_dir=argv[1],.lib_path=argv[2],.width=1024,.height=768,
        .standalone=1,.window_sound=sound,.progress_call=other,.quest_call=other};
    char error[512];layer=mu_gfx_layer_open(&cfg,error,sizeof error);assert(layer);
    for(int i=0;i<10;i++) mu_gfx_layer_advance(layer,40);
    int real=getenv("MU_WINDOWS4_REAL") && !strcmp(getenv("MU_WINDOWS4_REAL"),"1");
    if(real) {
        field(layer,MU_GFX_ELEMENTAL_MIX,"tfTitle.text","\"Elemental mix - preview\"");
        field(layer,MU_GFX_ELEMENTAL_MIX,"btnMixStart.disabled","true");
        field(layer,MU_GFX_SOCKET_MIX,"mcSocketMix.tfTitle.text","\"Socket mix - preview\"");
        field(layer,MU_GFX_SOCKET_MIX,"mcSocketMix.btnMixStart.disabled","true");
        field(layer,MU_GFX_GUARDIAN_MIX,"slMixTab.dataProvider.length","0.0");
        field(layer,MU_GFX_HARMONY_MIX,"slMixTab.dataProvider.length","0.0");
        field(layer,MU_GFX_RUUD_SHOP,"mcRuudShopFrame.mcShopList0._visible","false");
        field(layer,MU_GFX_LUCK_COIN,"btnExchange.disabled","true");
        field(layer,MU_GFX_ATTRIBUTE_SELECTOR,"btnMixAttScalp.disabled","true");
    }
    mu_gfx_hero hero=*mu_gfx_layer_hero(layer);int held=layer->held,potions=layer->potions;
    foreign=sounds=0;
    assert(!mu_gfx_layer_presentation_slot(NULL,0x204));
    assert(!mu_gfx_layer_presentation_slot(layer,0x184)); /* event inventory remains refused */
    assert(!mu_gfx_layer_presentation_slot(layer,0x29c)); /* separate fifth inventory */
    const char *blocked[]={"onClickExchangeBtn","OnClickMixStart","OnSelectedTab","onClickbtnBuy",
        "onClickType1","onClickbtnType1","onClickbtnMixAttScalp","onClickprevBtn","onClicknextBtn",
        "requestItemSlotClick","requestItemSlotClickR","requestItemSlotDragBegin","requestItemSlotDragEnd",
        "onDepositBtnClick","onClickLevelup","SaveAutomaticConfig","unknown"};
    int refused=0;
    for(int m=MU_GFX_ELEMENTAL_MIX;m<=MU_GFX_ATTRIBUTE_SELECTOR;m++) {
        assert(presentation_available3(layer,m));
        mu_gfx_layer_show(layer,m,1);
        for(size_t i=0;i<sizeof blocked/sizeof *blocked;i++) {
            assert(!presentation_call(&layer->mv[m],blocked[i],"[0]",(double[]){0},1));
            on_call(&layer->mv[m],blocked[i],"[0]");++refused;
        }
        assert(layer->mv[m].open);
        on_call(&layer->mv[m],m==MU_GFX_LUCK_COIN?"onClickExitBtn":"CloseWindow","[]");
        assert(!layer->mv[m].open);
        mu_gfx_layer_show(layer,m,1);assert(mu_gfx_layer_key(layer,1,27,0,0));assert(!layer->mv[m].open);
        unsigned ready=layer->presentation_ready;layer->presentation_ready=0;
        for(size_t i=0;i<sizeof PRESENTATION_ROUTES4/sizeof *PRESENTATION_ROUTES4;i++)
            if(PRESENTATION_ROUTES4[i].movie==m) assert(!mu_gfx_layer_presentation_slot(layer,PRESENTATION_ROUTES4[i].slot));
        assert(!layer->mv[m].open);layer->presentation_ready=ready;
    }
    /* ReceiveTalk preserves original show versus toggle, and the UI opt-in
     * delivers close -> controller open -> 25 -> 28. No extra UI sound. */
    int results[]={7,8,9,0x11,0x13,0x17,0x18,0x20,0x26,0x27,0x29,0x33,0x35};
    mu_walk walk={0};mu_world_actor actor={0};mu_world_actors actors={.list=&actor,.count=1};
    actor.server_class=251;actor.actor.spec.npc_index=0;
    mu_npc_demo demo={0};demo.count=1;demo.rows[0].server_class=251;
    mu_npc n;mu_npc_init(&n,&walk,&actors,&demo);
    n.open=open_window;n.close_all=close_all;n.sound=npc_tail_sound;n.ordered_window_sounds=1;
    for(size_t i=0;i<sizeof results/sizeof *results;i++) {
        demo.rows[0].result=results[i];n.pending_actor=0;trace[0]=0;answer(&n);
        printf("route %02x %s\n",results[i],trace);
        assert(strstr(trace,"close,")==trace);
        assert(strstr(trace,"sound25,sound28,"));
    }
    /* A direct repeated Muun route must toggle, not force visibility. */
    mu_gfx_layer_presentation_close(layer);
    assert(mu_gfx_layer_presentation_slot(layer,0x1ac) && layer->mv[MU_GFX_MUUN_EXCHANGE].open);
    assert(mu_gfx_layer_presentation_slot(layer,0x1ac) && !layer->mv[MU_GFX_MUUN_EXCHANGE].open);
    assert(mu_gfx_layer_presentation_slot(layer,0x204) && layer->mv[MU_GFX_ELEMENTAL_MIX].open);
    assert(mu_gfx_layer_presentation_slot(layer,0x204) && layer->mv[MU_GFX_ELEMENTAL_MIX].open);
    mu_gfx_layer_presentation_close(layer);
    for(int m=MU_GFX_ELEMENTAL_MIX;m<=MU_GFX_ATTRIBUTE_SELECTOR;m++) assert(!layer->mv[m].open);
    assert(!memcmp(&hero,mu_gfx_layer_hero(layer),sizeof hero));
    assert(layer->held==held && layer->potions==potions && foreign==0 && sounds==0);
    printf("nine fixture windows, %d inert callbacks, ordered controller and sound tail ok\n",refused);
    mu_gfx_layer_close(layer);
}
