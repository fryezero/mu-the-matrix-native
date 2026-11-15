/* MapName arrival banner: production controller, lifetime and overlay limits. */
#define MU_GFX_NO_GL
#include "../gfx/mu_gfx_layer.c"
#include <assert.h>
static mu_gfx_layer *L;
static FILE *journal;
static long mark;
static int foreign,sounds;
static void other(void *u,int m,const char *n,const char *a)
{(void)u;(void)m;(void)a;if(strcmp(n,"WindowShown") && strcmp(n,"WindowHidden") && strcmp(n,"UIInit")) ++foreign;}
static void sound(void *u,int32_t id,uint32_t site){(void)u;(void)id;(void)site;++sounds;}
static void step(int n){for(int i=0;i<n;i++)mu_gfx_layer_advance(L,40);}
/* The layer journal since the last mark: the banner's own invokes, in order. */
static void route(const char *label,int from_open)
{
 char line[1024],out[512]="";
 fflush(journal);fseek(journal,mark,SEEK_SET);
 while(fgets(line,sizeof line,journal)) {
  char *p=strstr(line,"MapName ");
  if(!p) continue;
  /* Load-time sizing and hiding precede the held join's open. */
  if(from_open && !out[0] && !strstr(p,".InitText(")) continue;
  if(strstr(p,".SetWindowSize(") || strstr(p,".SetScale(") || strstr(p,".SetAlign(") ||
     strstr(p,".GetWidth(") || strstr(p,".GetHeight(") || strstr(p,".getBounds(")) continue;   /* layout only */
  assert(strlen(out)+strlen(p)<sizeof out);
  if(strstr(p,"lifetime timer start")) {strcat(out,"timer,");continue;}
  if(strncmp(p,"MapName <- ",11)) continue;
  char *open=strchr(p,'('),*dot=open;
  assert(open);
  while(dot>p && *dot!='.') --dot;
  *open=0;
  char *close=strstr(open+1,") = ");
  assert(close);*close=0;
  if(!strcmp(dot+1,"SetVisible")) strcat(out,!strcmp(open+1,"[true]")?"open,":"close,");
  else if(!strcmp(dot+1,"InitText")) strcat(out,"InitText,");
  else {
   strcat(out,dot+1);strcat(out,":");
   for(const char *c=open+1;*c;c++) if(*c!='[' && *c!=']' && *c!='"') strncat(out,c,1);
   strcat(out,",");
  }
 }
 fseek(journal,0,SEEK_END);mark=ftell(journal);
 printf("route %s %s\n",label,out[0]?out:"none,");
}
static void field(const char *suffix,const char *expected)
{char p[256];snprintf(p,sizeof p,"%s.%s",L->mv[MU_GFX_MAP_NAME].path,suffix);const char *v=L->api.get_variable(L->mv[MU_GFX_MAP_NAME].g,p);if(!v || strcmp(v,expected)){fprintf(stderr,"%s expected %s got %s\n",p,expected,v?v:"NULL");abort();}}
int main(int argc,char **argv)
{
 assert(argc==3);journal=tmpfile();assert(journal);
 mu_gfx_layer_config cfg={.movie_dir=argv[1],.lib_path=argv[2],.width=1024,.height=768,.standalone=1,.window_sound=sound,.progress_call=other,.quest_call=other,.log=journal};
 char error[512];L=mu_gfx_layer_open(&cfg,error,sizeof error);assert(L);
 movie *w=&L->mv[MU_GFX_MAP_NAME];assert(w->g);
 int real=getenv("MU_WINDOWS4_REAL") && !strcmp(getenv("MU_WINDOWS4_REAL"),"1");
 /* Join before the movie is ready: held, then opened on the first ready frame. */
 /* Real movies report UIInit after open; the stub is ready at once, so its
  * readiness is withheld for the same held-join path. */
 unsigned ready0=L->presentation_ready;int natural=!presentation_available3(L,MU_GFX_MAP_NAME);
 if(!natural) L->presentation_ready&=~(1u<<(MU_GFX_MAP_NAME-MU_GFX_COMMAND));
 assert(mu_gfx_layer_map_arrival(L,MU_GFX_ARRIVAL_JOIN,0,0,"Demotown")==1);
 assert(L->map_banner_pending && !w->open);
 fflush(journal);fseek(journal,0,SEEK_END);mark=ftell(journal);
 if(!natural){step(2);assert(!w->open && L->map_banner_pending);L->presentation_ready=ready0;}
 for(int i=0;i<250 && !w->open;i++)step(1);
 assert(w->open && !L->map_banner_pending && presentation_available3(L,MU_GFX_MAP_NAME));
 route("1",1);
 if(real){field("tfMapName.text","\"Demotown\"");field("tfStrife.text","\"\"");field("tfOccupyGuild.text","\"\"");}
 /* 0x00baf120: open below 5000 ms, closed at 5000 ms. */
 double start=L->map_banner_start_ms;
 step(124);assert(w->open && L->time_ms-start==4960);
 step(1);assert(!w->open);printf("lifetime %.0f\n",L->time_ms-start);
 route("close",0);
 mu_gfx_hero hero=*mu_gfx_layer_hero(L);int held=L->held,potions=L->potions;foreign=sounds=0;
 /* The three original owners; the teleport tail needs a non-zero number. */
 assert(!mu_gfx_layer_map_arrival(L,MU_GFX_ARRIVAL_TELEPORT,0,3,"Demotown") && !w->open);route("teleport0",0);
 assert(mu_gfx_layer_map_arrival(L,MU_GFX_ARRIVAL_TELEPORT,17,3,"Demotown") && w->open);route("teleport",0);
 step(100);assert(w->open);
 /* A second open restarts the lifetime (0x00baee94). */
 assert(mu_gfx_layer_map_arrival(L,MU_GFX_ARRIVAL_RESPAWN,0,0,"Demotown") && w->open);route("respawn",0);
 step(100);assert(w->open);step(25);assert(!w->open);route("close2",0);
 /* Open 0x00baee6b does nothing in world 0x28; invalid owners and names refuse. */
 assert(!mu_gfx_layer_map_arrival(L,MU_GFX_ARRIVAL_JOIN,0,0x28,"Demotown"));
 assert(!mu_gfx_layer_map_arrival(L,MU_GFX_ARRIVAL_TELEPORT,17,0x28,"Demotown"));
 assert(!mu_gfx_layer_map_arrival(L,3,17,0,"Demotown") && !mu_gfx_layer_map_arrival(L,-1,17,0,"Demotown"));
 assert(!mu_gfx_layer_map_arrival(L,MU_GFX_ARRIVAL_JOIN,0,0,"") && !mu_gfx_layer_map_arrival(L,MU_GFX_ARRIVAL_JOIN,0,0,NULL));
 assert(!mu_gfx_layer_map_arrival(NULL,MU_GFX_ARRIVAL_JOIN,0,0,"Demotown"));
 assert(!w->open && !L->map_banner_pending);route("refused",0);
 /* A readiness loss holds the latest arrival only; world 0x28 is never held. */
 unsigned ready=L->presentation_ready;L->presentation_ready=0;
 assert(!mu_gfx_layer_map_arrival(L,MU_GFX_ARRIVAL_JOIN,0,0x28,"Demotown") && !L->map_banner_pending);
 assert(mu_gfx_layer_map_arrival(L,MU_GFX_ARRIVAL_JOIN,0,0,"Oldtown") && L->map_banner_pending && !w->open);
 assert(mu_gfx_layer_map_arrival(L,MU_GFX_ARRIVAL_TELEPORT,2,3,"Newtown") && L->map_banner_pending && !w->open);
 step(3);assert(!w->open);L->presentation_ready=ready;step(1);assert(w->open && !L->map_banner_pending);route("held",0);
 if(real)field("tfMapName.text","\"Newtown\"");
 /* Overlay limits: Esc, NPC close-all and the pointer leave the banner alone,
  * even while it is the most recently raised movie. */
 assert(presentation_available3(L,MU_GFX_COMMAND));mu_gfx_layer_show(L,MU_GFX_COMMAND,1);
 mu_gfx_layer_show(L,w->id,0);assert(mu_gfx_layer_map_arrival(L,MU_GFX_ARRIVAL_TELEPORT,5,3,"Demotown") && w->open);
 assert(L->order[L->norder-1]==MU_GFX_MAP_NAME);
 assert(mu_gfx_layer_key(L,1,27,0,0));assert(!L->mv[MU_GFX_COMMAND].open && w->open);
 mu_gfx_layer_npc_close(L);mu_gfx_layer_presentation_close(L);assert(w->open);
 route("overlay",0);
 /* Positive control: a point the movie itself reports as hit. */
 double px=-1,py=-1,lx,ly;
 for(double y=4;y<L->h && px<0;y+=8) for(double x=4;x<L->w;x+=8)
  if(local(L,w,x,y,&lx,&ly) && L->api.hit_test(w->g,lx,ly)){px=x;py=y;break;}
 assert(real || px>=0);
 for(int m=MU_GFX_MAIN;m<MU_GFX_MOVIES;m++) if(m!=MU_GFX_MAP_NAME && m!=MU_GFX_TOOLTIP) L->mv[m].open=0;
 if(px>=0){
  assert(!mu_gfx_layer_mouse(L,0,0,px*L->scale,py*L->scale));
  assert(!mu_gfx_layer_mouse(L,1,0,px*L->scale,py*L->scale) && L->capture!=MU_GFX_MAP_NAME);
  (void)mu_gfx_layer_mouse(L,2,0,px*L->scale,py*L->scale);
 }
 printf("pointer %s\n",px>=0?"checked":"no hit point");
 const char *blocked[]={"CloseWindow","onClickbtnClose","OnClickOk","OnClickCancel","requestItemSlotClick","SetStrife","SetOccupyGuild","SetMapName","onClickbtnEnterTime","PCRoomClick","onClickAlarm","LeaveComplete","unknown"};
 int refused=0;
 for(size_t i=0;i<sizeof blocked/sizeof *blocked;i++){
  assert(!presentation_call(w,blocked[i],"[0]",(double[]){0},1));on_call(w,blocked[i],"[0]");++refused;
  assert(w->open);
 }
 assert(presentation_call(w,"TweenTimeSet","[0.5]",(double[]){0.5},1) && presentation_call(w,"requestWindowPos","[]",NULL,0));
 route("inert",0);
 assert(!memcmp(&hero,mu_gfx_layer_hero(L),sizeof hero));assert(L->held==held && L->potions==potions && foreign==0 && sounds==0);
 printf("map banner, %d inert callbacks, original owners ok\n",refused);mu_gfx_layer_close(L);
}
