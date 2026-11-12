/* Real production allowlist, with synthetic and private original movies. */
#define MU_GFX_NO_GL
#include "../gfx/mu_gfx_layer.c"
#include <assert.h>

static int foreign, sounds, zsounds, hsounds;
static void sound(void *u,int32_t id,uint32_t site)
{
    (void)u; assert(id==25);
    if(site==0xefd43a) ++zsounds;
    else if(site==0xefc772) ++hsounds;
    else {assert(site==0xc716f6);++sounds;}
}
static void other(void *u,int m,const char *n,const char *a)
{(void)u;(void)m;(void)n;(void)a;++foreign;}

int main(int argc,char **argv)
{
    assert(argc==3);
    mu_gfx_layer_config cfg={.movie_dir=argv[1],.lib_path=argv[2],.width=1024,.height=768,
        .standalone=1,.window_sound=sound,.progress_call=other};
    char error[512];mu_gfx_layer *L=mu_gfx_layer_open(&cfg,error,sizeof error);
    if(!L){fprintf(stderr,"%s\n",error);return 1;}
    foreign=0;
    mu_gfx_hero before=*mu_gfx_layer_hero(L);
    int held=L->held, potions=L->potions;
    const char *blocked[]={"SaveMacroOption","btnInit","btnConnect","onClickbtnSave","onClickbtnReset",
        "onClickHealingSkillSave","onClickHealingSkillReset","OpenExecuteHealingSkill","SetBuffRange",
        "OnChangePartyBuffRange","onSelectedcbCombo","btnHuntArea","onClickAutoStart","SaveAutomaticConfig",
        "onClickImmediatelyStart","onDepositBtnClick","onWithDrawBtnClick","onLiftBtnClick","onExtendBtnClick",
        "requestItemSlotClick","requestItemSlotClickR","onClickbtnSearch","onClickbtnRefresh",
        "onChangeosPageSelect","onClickbtnRecruitOK","onClickbtnRecruitCancel","onClickbtnAgree",
        "onClickbtnDisagree","onClickbtnMail","onClickbtnJoinCancel","onClickJoin","onClickPartyRecruitSave",
        "onClickbtnOKRequestWait","onClickbtnCancelRequestWait","onClickbtnDeleteRequestWait",
        "onClickbtnHighLight","setCheckBox","changeMap","unknown"};
    int refused=0;
    for(int m=MU_GFX_MACRO;m<MU_GFX_MOVIES;m++) {
        if(!L->mv[m].g || !*L->mv[m].path) fprintf(stderr,"missing %d %s path=%s\n",m,FILES[m],L->mv[m].path);
        assert(L->mv[m].g && *L->mv[m].path);
        assert(presentation_open(L,m,0));
        for(size_t i=0;i<sizeof blocked/sizeof *blocked;i++) {
            assert(!presentation_call(&L->mv[m],blocked[i],"[0]",(double[]){0},1));
            on_call(&L->mv[m],blocked[i],"[0]");++refused;
        }
        assert(L->mv[m].open);
        assert(mu_gfx_layer_key(L,1,27,0,0));
        assert(!L->mv[m].open);
    }
    assert(!mu_gfx_layer_key(L,1,'H',0,0)); /* H cannot acquire a warehouse. */
    assert(!L->mv[MU_GFX_STORAGE_EXT].open && hsounds==0);
    mu_gfx_layer_show(L,MU_GFX_STORAGE,1);
    assert(mu_gfx_layer_key(L,1,'H',0,0) && L->mv[MU_GFX_STORAGE_EXT].open);
    assert(hsounds==1);
    mu_gfx_layer_show(L,MU_GFX_STORAGE,0);
    assert(!L->mv[MU_GFX_STORAGE_EXT].open);
    assert(mu_gfx_layer_key(L,1,'Z',0,0) && zsounds==1);
    mu_gfx_layer_key(L,0,'Z',0,0);assert(zsounds==1);
    assert(presentation_call(&L->mv[MU_GFX_MACRO],"btnMenu","[0]",(double[]){0},1));
    assert(L->macro_sub_type==1 && L->mv[MU_GFX_MACRO_SUB].open);
    assert(!presentation_call(&L->mv[MU_GFX_MACRO],"btnMenu","[1]",(double[]){1},1));
    assert(!presentation_call(&L->mv[MU_GFX_MACRO],"btnMenu","[2.5]",(double[]){2.5},1));
    assert(!presentation_call(&L->mv[MU_GFX_MACRO],"btnMenu","[-1]",(double[]){-1},1));
    mu_gfx_layer_show(L,MU_GFX_MACRO,0);assert(!L->mv[MU_GFX_MACRO_SUB].open);
    assert(mu_gfx_layer_key(L,1,35,0,0) && L->mv[MU_GFX_HUNT_RECORD].open);
    on_call(&L->mv[MU_GFX_HUNT_RECORD],"closeWindow","[]");assert(!L->mv[MU_GFX_HUNT_RECORD].open);
    assert(mu_gfx_layer_key(L,1,'T',0,2) && L->mv[MU_GFX_PLAY_GUIDE].open);
    mu_gfx_layer_show(L,MU_GFX_PLAY_GUIDE,0);
    assert(presentation_menu(L,12));
    on_call(&L->mv[MU_GFX_MATCHING],"onClickbtnParty","[]");
    assert(!L->mv[MU_GFX_MATCHING].open && L->mv[MU_GFX_MATCH_PARTY].open);
    mu_gfx_layer_show(L,MU_GFX_MATCH_PARTY,0);
    assert(presentation_menu(L,12));
    on_call(&L->mv[MU_GFX_MATCHING],"onClickbtnGuild","[]");
    assert(!L->mv[MU_GFX_MATCHING].open && L->mv[MU_GFX_MATCH_GUILD].open);
    mu_gfx_layer_show(L,MU_GFX_MATCH_GUILD,0);
    assert(presentation_menu(L,10) && L->mv[MU_GFX_GUILD_MATCH].open);
    for(int tab=0;tab<3;tab++) assert(presentation_call(&L->mv[MU_GFX_GUILD_MATCH],"onTabChange","[]",(double[]){tab},1));
    assert(!presentation_call(&L->mv[MU_GFX_GUILD_MATCH],"onTabChange","[3]",(double[]){3},1));
    assert(!memcmp(&before,mu_gfx_layer_hero(L),sizeof before));
    assert(L->held==held && L->potions==potions && foreign==0 && sounds==3);
    L->presentation_ready=0;
    assert(!presentation_open(L,MU_GFX_MACRO,0xefd43a) && zsounds==1);
    mu_gfx_layer_close(L);
    printf("eight fixture windows, %d inert callbacks, lifecycle and sound gates ok\n",refused);
}
