/* Production callback firewall, optional-movie lifecycle and sound ownership. */
#define MU_GFX_NO_GL
#include "../gfx/mu_gfx_layer.c"
#include <assert.h>

static int sounds, foreign;
static void sound(void *u, int32_t id, uint32_t site)
{ (void)u; assert(id==25 && site==0xc716f6u); ++sounds; }
static void progress(void *u,int m,const char *name,const char *args)
{ (void)u;(void)m;(void)name;(void)args;++foreign; }

int main(int argc, char **argv)
{
    assert(argc==3);
    mu_gfx_layer_config cfg={.movie_dir=argv[1],.lib_path=argv[2],.width=1024,.height=768,
        .standalone=1,.window_sound=sound,.progress_call=progress};
    char error[512];
    mu_gfx_layer *L=mu_gfx_layer_open(&cfg,error,sizeof error);
    if(!L){fprintf(stderr,"%s\n",error);return 1;}
    const int keys[]={'D','N','B','Y','K'};
    const char *blocked[]={"onClickbtnTrade","onClickbtnPurchase","onClickbtnParty","onClickbtnGuild",
        "onClickbtnWhisper","onClickbtnGuildUnion","onClickbtnRivalOn","onClickbtnRivalOff",
        "onClickbtnAddFriend","onClickbtnFollow","onClickbtnDuel","onClickList","onClickbtnSorting",
        "onClickbtnPetBook","OnChangedAppearType","requestItemSlotClick","requestItemSlotClickR",
        "EQUIPrequestItemSlotClick","onSave","onStart","onClaim","onHotKey","unknown"};
    int refused=0;
    const mu_gfx_hero before=*mu_gfx_layer_hero(L);
    int held=mu_gfx_layer_held(L), potion=L->potions;
    for(int i=0;i<5;i++) {
        int m=MU_GFX_COMMAND+i;
        assert(*mu_gfx_layer_path(L,m));
        assert(!mu_gfx_layer_is_open(L,m));
        assert(mu_gfx_layer_key(L,1,keys[i],0,0));
        assert(mu_gfx_layer_is_open(L,m));
        mu_gfx_layer_key(L,0,keys[i],0,0);
        assert(mu_gfx_layer_is_open(L,m));
        for(size_t j=0;j<sizeof blocked/sizeof *blocked;j++) {
            assert(!presentation_call(&L->mv[m],blocked[j],"[0]",(double[]){0},1));
            refused++;
            /* Exercise the real callback entry as well, to catch routing fallthrough. */
            on_call(&L->mv[m],blocked[j],"[0]");
        }
        assert(mu_gfx_layer_is_open(L,m));
        assert(mu_gfx_layer_key(L,1,27,0,0));
        assert(!mu_gfx_layer_is_open(L,m));
    }
    assert(sounds==4);
    for(int id=11;id<=15;id++) if(id!=14) assert(presentation_menu(L,id));
    assert(sounds==8);
    assert(!presentation_menu(L,3)); /* original menu 3 is not D */
    assert(!presentation_menu(L,8)); /* SystemMenu is not Help */
    assert(!presentation_menu(L,999));
    for(int p=2;p<=5;p++) assert(presentation_call(&L->mv[MU_GFX_PET_INVENTORY],"onClicknextBtn","[]",NULL,0));
    assert(!presentation_call(&L->mv[MU_GFX_PET_INVENTORY],"onClicknextBtn","[]",NULL,0));
    assert(L->pet_page==5);
    for(int p=1;p<=4;p++) assert(presentation_call(&L->mv[MU_GFX_GREMORY],"OnTabSelected","[]",(double[]){p},1));
    assert(!presentation_call(&L->mv[MU_GFX_GREMORY],"OnTabSelected","[]",(double[]){0},1));
    assert(!presentation_call(&L->mv[MU_GFX_GREMORY],"OnTabSelected","[]",(double[]){2.5},1));
    assert(!memcmp(&before,mu_gfx_layer_hero(L),sizeof before));
    assert(held==mu_gfx_layer_held(L) && potion==L->potions);
    assert(foreign==0 && sounds==8);
    mu_gfx_layer_key(L,1,13,0,0);
    mu_gfx_layer_show(L,MU_GFX_COMMAND,0);
    assert(mu_gfx_layer_key(L,1,'D',0,0)); /* chat focus consumes it */
    assert(!mu_gfx_layer_is_open(L,MU_GFX_COMMAND));
    mu_gfx_layer_key(L,1,27,0,0);
    /* Detached sound has no backlog, optional missing movies refuse. */
    L->cfg.window_sound=NULL;
    presentation_menu(L,11);
    L->cfg.window_sound=sound;
    assert(sounds==8);
    L->presentation_ready=0;
    assert(!presentation_menu(L,11));
    mu_gfx_layer_close(L);
    printf("five windows, %d inert callbacks, eight immediate menu sounds ok\n",refused);
    return 0;
}
