/* Exercise production callbacks against synthetic and private original movies. */
#define MU_GFX_NO_GL
#include "../gfx/mu_gfx_layer.c"
#include <assert.h>
static int foreign,sounds;
static void other(void *u,int m,const char *n,const char *a)
{ (void)u;(void)m;(void)a;
  if(strcmp(n,"WindowShown") && strcmp(n,"WindowHidden") && strcmp(n,"UIInit")) ++foreign; }
static void sound(void *u,int32_t id,uint32_t site)
{ (void)u;(void)id;(void)site;++sounds; }
static void field(mu_gfx_layer *L,int m,const char *suffix,const char *expected)
{
    char path[256];snprintf(path,sizeof path,"%s.%s",L->mv[m].path,suffix);
    const char *v=L->api.get_variable(L->mv[m].g,path);
    if (!v || strcmp(v,expected)) {fprintf(stderr,"field %s expected %s got %s\n",path,expected,v?v:"NULL");abort();}
}
int main(int argc,char **argv)
{
    assert(argc==3);
    mu_gfx_layer_config cfg={.movie_dir=argv[1],.lib_path=argv[2],.width=1024,.height=768,
        .standalone=1,.window_sound=sound,.progress_call=other,.quest_call=other};
    char error[512];mu_gfx_layer *L=mu_gfx_layer_open(&cfg,error,sizeof error);
    if (!L) {fprintf(stderr,"%s\n",error);return 1;}
    for(int i=0;i<10;i++) mu_gfx_layer_advance(L,40);
    for(int m=MU_GFX_BAG;m<MU_GFX_MOVIES;m++) assert(presentation_available3(L,m));
    int real=getenv("MU_WINDOWS3_REAL") && !strcmp(getenv("MU_WINDOWS3_REAL"),"1");
    if(real) {
        field(L,MU_GFX_BLOCKED_CHAT,"btnRegistUser.disabled","true");
        field(L,MU_GFX_BLOCKED_CHAT,"slUserList.dataProvider.length","0.0");
        field(L,MU_GFX_TREE5_VIEWER,"mcSetting.cbCanLevelUpView.disabled","true");
        field(L,MU_GFX_TREE5_VIEWER,"mc5thTreeItemViewer.mcViewTypeBook._visible","true");
        field(L,MU_GFX_TREE5_VIEWER,"mc5thTreeItemViewer.mcViewTypeList._visible","false");
    }
    if(real) {
        field(L,MU_GFX_AUTOMATIC,"btnAutoStart.disabled","true");
        field(L,MU_GFX_AUTOMATIC,"dmLeaderHuntingMap.dataProvider.length","0.0");
    }
    foreign=sounds=0;
    mu_gfx_hero hero=*mu_gfx_layer_hero(L);int held=L->held,potions=L->potions;
    on_call(&L->mv[MU_GFX_INVENTORY],"onClickbtnExtensionBag","[]");assert(!L->mv[MU_GFX_BAG].open);
    mu_gfx_layer_show(L,MU_GFX_INVENTORY,1);assert(L->mv[MU_GFX_BAG].open);
    on_call(&L->mv[MU_GFX_INVENTORY],"onClickbtnExtensionBag","[]");assert(!L->mv[MU_GFX_BAG].open);
    on_call(&L->mv[MU_GFX_INVENTORY],"onClickbtnExtensionBag","[]");assert(L->mv[MU_GFX_BAG].open);
    mu_gfx_layer_show(L,MU_GFX_INVENTORY,0);assert(!L->mv[MU_GFX_BAG].open);
    /* Ctrl+J repairs each mismatched state by opening both. Ctrl+I is independent. */
    for(int tree=0;tree<2;tree++) for(int viewer=0;viewer<2;viewer++) {
        mu_gfx_layer_show(L,MU_GFX_TREE5,tree);mu_gfx_layer_show(L,MU_GFX_TREE5_VIEWER,viewer);
        assert(mu_gfx_layer_key(L,1,'J',0,2));
        assert(L->mv[MU_GFX_TREE5].open==!(tree&&viewer));
        assert(L->mv[MU_GFX_TREE5_VIEWER].open==!(tree&&viewer));
    }
    mu_gfx_layer_show(L,MU_GFX_TREE5,0);mu_gfx_layer_show(L,MU_GFX_TREE5_VIEWER,0);
    assert(mu_gfx_layer_key(L,1,'I',0,2) && L->mv[MU_GFX_TREE5_VIEWER].open);
    assert(!L->mv[MU_GFX_TREE5].open);
    (void)mu_gfx_layer_key(L,0,'I',0,2);assert(L->mv[MU_GFX_TREE5_VIEWER].open);
    assert(presentation_call(&L->mv[MU_GFX_TREE5_VIEWER],"onClickViewTypeToggle","[false]",NULL,0));
    if(real) {
        field(L,MU_GFX_TREE5_VIEWER,"mc5thTreeItemViewer.mcViewTypeBook._visible","false");
        field(L,MU_GFX_TREE5_VIEWER,"mc5thTreeItemViewer.mcViewTypeList._visible","true");
        field(L,MU_GFX_TREE5_VIEWER,"osPageSelect2.textField.text","\"1 / 1\"");
        field(L,MU_GFX_TREE5_VIEWER,"btnNextPage2.disabled","true");
        for(int i=0;i<20;i++) {char p[160];snprintf(p,sizeof p,"m_arrCardList.%d.CardInfo._visible",i);field(L,MU_GFX_TREE5_VIEWER,p,"false");}
    }
    assert(!presentation_call(&L->mv[MU_GFX_TREE5_VIEWER],"onClickViewTypeToggle","[2]",NULL,0));
    assert(presentation_call(&L->mv[MU_GFX_TREE5_VIEWER],"onClickViewTypeToggle","[true]",NULL,0));
    mu_gfx_layer_show(L,MU_GFX_TREE5_VIEWER,0);
    on_call(&L->mv[MU_GFX_CHAT],"chat","[\"BlockedUser\",{\"open\":true}]");assert(L->mv[MU_GFX_BLOCKED_CHAT].open);
    on_call(&L->mv[MU_GFX_CHAT],"chat","[\"BlockedUser\",{\"open\":true}]");assert(L->mv[MU_GFX_BLOCKED_CHAT].open);
    on_call(&L->mv[MU_GFX_CHAT],"chat","[\"BlockedUser\",{}]");assert(L->mv[MU_GFX_BLOCKED_CHAT].open);
    on_call(&L->mv[MU_GFX_CHAT],"chat","[\"BlockedUser\",{\"open\":trueish}]");assert(L->mv[MU_GFX_BLOCKED_CHAT].open);
    on_call(&L->mv[MU_GFX_CHAT],"chat","[\"BlockedUser\",{\"open\":false}]");assert(!L->mv[MU_GFX_BLOCKED_CHAT].open);
    assert(mu_gfx_layer_key(L,1,113,0,0) && L->mv[MU_GFX_BLOCKED_CHAT].open);
    assert(mu_gfx_layer_key(L,1,27,0,0) && !L->mv[MU_GFX_BLOCKED_CHAT].open);
    on_call(&L->mv[MU_GFX_MAIN],"topmenu","[\"MacroMenu\",\"AutomaticMacroStart\"]");
    assert(L->mv[MU_GFX_AUTOMATIC].open);
    on_call(&L->mv[MU_GFX_MAIN],"topmenu","[\"MacroMenu\",\"AutomaticMacroStart\"]");
    assert(!L->mv[MU_GFX_AUTOMATIC].open);
    if(real) {
        on_call(&L->mv[MU_GFX_MAIN],"topmenu","[\"MacroMenu\",\"AutomaticMacroStart\"]");
        assert(L->mv[MU_GFX_AUTOMATIC].open);
        for(int i=0;i<10;i++) mu_gfx_layer_advance(L,40);
        L->api.invoke(L->mv[MU_GFX_AUTOMATIC].g,L->mv[MU_GFX_AUTOMATIC].path,"onClickExit","[]");
        for(int i=0;i<10;i++) mu_gfx_layer_advance(L,40);
        assert(!L->mv[MU_GFX_AUTOMATIC].open);
    }
    assert(!presentation_key3(L,36,0)); /* Home activation is still unavailable. */
    /* Cross-window forged actions must never reach session/NPC/item/social owners. */
    const char *blocked[]={"requestItemSlotClick","requestItemSlotClickR","requestItemSlotDoubleClick",
        "requestItemSlotDragBegin","requestItemSlotDragEnd","SetViewType","SetVisibleOnlyMyItem",
        "SetVisibleItemCanLevelUp","onClickLevelUpAll","onClickRegistUser","onClicDeleteUser",
        "onClickBlockIDInputText","onOverSandGlass","OnSandglassRelease","SaveAutomaticConfig",
        "onClickImmediatelyStart","onClickbtnJoin","onDepositBtnClick","unknown",
        "onClickAutoStart","onClickAutoPlayCancel","CancelAutoStart","VisibleLeaderMacro",
        "SelectedLeaderHuntingMap","onClickDirectRegistUserValid","UpdateCharacterInput",
        "InputReadyRelease","onClickLeaderDieCount","onClickCharacterNameInput","setCheckBox",
        "onClickprevBtn","onClicknextBtn","onClickLevelup"};
    assert(sounds==0); /* These original direct routes have no guessed click sound. */
    foreign=0;
    int refused=0;
    for(int m=MU_GFX_BAG;m<MU_GFX_MOVIES;m++) {
        mu_gfx_layer_show(L,m,1);
        for(size_t i=0;i<sizeof blocked/sizeof *blocked;i++) {
            assert(!presentation_call(&L->mv[m],blocked[i],"[0]",(double[]){0},1));
            on_call(&L->mv[m],blocked[i],"[0]");++refused;
        }
        assert(L->mv[m].open);on_call(&L->mv[m],"CloseWindow","[]");assert(!L->mv[m].open);
        mu_gfx_layer_show(L,m,1);assert(mu_gfx_layer_key(L,1,27,0,0));assert(!L->mv[m].open);
    }
    /* Missing viewer refuses atomically, including an already open tree. */
    unsigned ready=L->presentation_ready;
    L->presentation_ready &= ~(1u<<(MU_GFX_TREE5_VIEWER-MU_GFX_COMMAND));
    assert(!presentation_key3(L,'J',2) && !L->mv[MU_GFX_TREE5].open);
    L->presentation_ready=ready;
    assert(!memcmp(&hero,mu_gfx_layer_hero(L),sizeof hero) && L->held==held && L->potions==potions);
    assert(foreign==0 && sounds==0);
    mu_gfx_layer_close(L);
    printf("four empty windows, %d inert callbacks, routes and sound silence ok\n",refused);
}
