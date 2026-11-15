/* Original presentation boundaries with production callback and NPC owners. */
#define MU_GFX_NO_GL
#include "../gfx/mu_gfx_layer.c"
#include "../core/mu_npc.c"
#include <assert.h>
static mu_gfx_layer *L;
static char trace[256];
static int foreign,sounds;
static void other(void *u,int m,const char *n,const char *a)
{(void)u;(void)m;(void)a;if(strcmp(n,"WindowShown") && strcmp(n,"WindowHidden") && strcmp(n,"UIInit")) ++foreign;}
static void sound(void *u,int32_t id,uint32_t site)
{(void)u;assert(id==25 && site==0xc716f6u);++sounds;}
static void close_all(void *u){(void)u;strcat(trace,"close,");mu_gfx_layer_presentation_close(L);}
static void opened(void *u,const mu_npc_open *o)
{(void)u;assert(o->window.slot==0x164 || o->window.slot==0xe0);assert(mu_gfx_layer_presentation_slot(L,o->window.slot));strcat(trace,o->window.slot==0x164?"164:toggle,":"e0:open,");}
static void tail(void *u,int32_t id){(void)u;char b[24];snprintf(b,sizeof b,"sound%d,",id);strcat(trace,b);}
static void field(int m,const char *suffix,const char *expected)
{char p[256];snprintf(p,sizeof p,"%s.%s",L->mv[m].path,suffix);const char *v=L->api.get_variable(L->mv[m].g,p);if(!v || strcmp(v,expected)){fprintf(stderr,"%s expected %s got %s\n",p,expected,v?v:"NULL");abort();}}
int main(int argc,char **argv)
{
 assert(argc==3);mu_gfx_layer_config cfg={.movie_dir=argv[1],.lib_path=argv[2],.width=1024,.height=768,.standalone=1,.window_sound=sound,.progress_call=other,.quest_call=other};
 char error[512];L=mu_gfx_layer_open(&cfg,error,sizeof error);assert(L);
 for(int i=0;i<10;i++)mu_gfx_layer_advance(L,40);
 int real=getenv("MU_WINDOWS4_REAL") && !strcmp(getenv("MU_WINDOWS4_REAL"),"1");
 if(real){
  field(MU_GFX_DUEL_WATCH,"tfTitle.text","\"Duel watch\"");
  for(int i=0;i<4;i++){char f[80];snprintf(f,sizeof f,"m_aDuelWatch.%d.disabled",i);field(MU_GFX_DUEL_WATCH,f,"true");}
  field(MU_GFX_PERSONAL_CATALOG,"mcPersonalShop.taTitle.text","\"Personal shops - empty preview\"");
  field(MU_GFX_PERSONAL_CATALOG,"btnAllShopList.disabled","true");
  field(MU_GFX_PERSONAL_CATALOG,"mcSearchItem.tiSearchItem.disabled","true");
  field(MU_GFX_PERSONAL_CATALOG,"mcShopList.slShopTitle.dataProvider.length","0.0");
  field(MU_GFX_PERSONAL_CATALOG,"mcItemList.slItemList.dataProvider.length","0.0");
  field(MU_GFX_ARTIFACT,"mcBG.tfTitle.text","\"Artifacts - empty preview\"");
  field(MU_GFX_ARTIFACT,"btnPrevPage.disabled","true");
  field(MU_GFX_ARTIFACT,"btnNextPage.disabled","true");
  field(MU_GFX_ARTIFACT,"HexSlotList.0._visible","false");
 }
 mu_gfx_hero hero=*mu_gfx_layer_hero(L);int held=L->held,potions=L->potions;foreign=sounds=0;
 const char *blocked[]={"OnClickAllShopList","OnClickSearchItem","OnClickItemList","OnClickWhisper","OnClickLetter","OnClickPrevPage","OnClickNextPage","OnClickSlotBoard","OnClickRSlotBoard","OnClickExpand","OnClickContract","OnExpandContractNode","onClickLevelup","requestItemSlotClick","onClickbtnBuy","onDepositBtnClick","onClickbtnDuelWatch0","onClickbtnDuelWatch1","onClickbtnDuelWatch2","onClickbtnDuelWatch3","unknown"};
 int refused=0;
 for(int m=MU_GFX_PERSONAL_CATALOG;m<=MU_GFX_DUEL_WATCH;m++){
  assert(presentation_available3(L,m));mu_gfx_layer_show(L,m,1);
  for(size_t i=0;i<sizeof blocked/sizeof *blocked;i++){
   assert(!presentation_call(&L->mv[m],blocked[i],"[0]",(double[]){0},1));on_call(&L->mv[m],blocked[i],"[0]");++refused;
  }
  assert(L->mv[m].open);on_call(&L->mv[m],"CloseWindow","[]");assert(!L->mv[m].open);
  mu_gfx_layer_show(L,m,1);assert(mu_gfx_layer_key(L,1,27,0,0));assert(!L->mv[m].open);
 }
 assert(!presentation_call(&L->mv[MU_GFX_PERSONAL_CATALOG],"OnClickSearchTab","[]",NULL,0));
 assert(!presentation_call(&L->mv[MU_GFX_PERSONAL_CATALOG],"OnClickSearchTab","[9,1]",(double[]){9,1},2));
 for(int tab=0;tab<2;tab++){
  invokef(L,MU_GFX_PERSONAL_CATALOG,L->mv[MU_GFX_PERSONAL_CATALOG].path,"SelectTab","[%d,true]",tab);
  assert(presentation_call(&L->mv[MU_GFX_PERSONAL_CATALOG],"OnClickSearchTab","[]",(double[]){tab,1},2));
  if(real)field(MU_GFX_PERSONAL_CATALOG,"mcItemList._visible",tab?"true":"false");
 }
 /* The inventory callback owns the artifact toggle, never a new shortcut. */
 on_call(&L->mv[MU_GFX_INVENTORY],"onClickArtifact","[]");assert(!L->mv[MU_GFX_ARTIFACT].open);
 mu_gfx_layer_show(L,MU_GFX_INVENTORY,1);
 on_call(&L->mv[MU_GFX_INVENTORY],"onClickArtifact","[]");assert(L->mv[MU_GFX_ARTIFACT].open);
 printf("route 280 280:toggle,\n");
 on_call(&L->mv[MU_GFX_INVENTORY],"onClickArtifact","[]");assert(!L->mv[MU_GFX_ARTIFACT].open);
 unsigned ready=L->presentation_ready;L->presentation_ready=0;
 assert(!mu_gfx_layer_presentation_slot(L,0x280));assert(!mu_gfx_layer_presentation_slot(L,0x164));L->presentation_ready=ready;
 mu_walk walk={0};mu_world_actor actor={0};mu_world_actors actors={.list=&actor,.count=1};actor.server_class=251;actor.actor.spec.npc_index=0;
 mu_npc_demo demo={0};demo.count=1;demo.rows[0].server_class=251;demo.rows[0].result=0x30;
 mu_npc npc;mu_npc_init(&npc,&walk,&actors,&demo);npc.open=opened;npc.close_all=close_all;npc.sound=tail;npc.ordered_window_sounds=1;npc.pending_actor=0;answer(&npc);
 assert(L->mv[MU_GFX_PERSONAL_CATALOG].open);printf("route 30 %s\n",trace);
 trace[0]=0;demo.rows[0].result=0x21;npc.pending_actor=0;answer(&npc);
 assert(L->mv[MU_GFX_DUEL_WATCH].open);printf("route 21 %s\n",trace);
 assert(mu_gfx_layer_presentation_slot(L,0xe0) && L->mv[MU_GFX_DUEL_WATCH].open);
 mu_gfx_layer_presentation_close(L);
 assert(presentation_menu(L,7) && L->mv[MU_GFX_PERSONAL_CATALOG].open);assert(sounds==1);
 assert(presentation_menu(L,7) && !L->mv[MU_GFX_PERSONAL_CATALOG].open);assert(sounds==2);
 assert(!memcmp(&hero,mu_gfx_layer_hero(L),sizeof hero));assert(L->held==held && L->potions==potions && foreign==0 && sounds==2);
 printf("three fixture windows, %d inert callbacks, original routes ok\n",refused);mu_gfx_layer_close(L);
}
