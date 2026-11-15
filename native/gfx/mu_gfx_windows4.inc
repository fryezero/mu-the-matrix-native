/* UI-WINDOWS-004. Original NPC window routes over empty local providers.
 * No inventory, recipe, currency or request owner is attached to these movies. */
static int presentation_slot5(mu_gfx_layer *, unsigned);
typedef struct { unsigned slot; int movie, toggle; } presentation_route4;
static const presentation_route4 PRESENTATION_ROUTES4[] = {
    {0x204,MU_GFX_ELEMENTAL_MIX,0}, {0x208,MU_GFX_SOCKET_MIX,0},
    {0x20c,MU_GFX_GUARDIAN_MIX,0}, {0x260,MU_GFX_HARMONY_MIX,0},
    {0x264,MU_GFX_HARMONY_MIX,0}, {0x270,MU_GFX_LUCK_COIN,0},
    {0x1ac,MU_GFX_MUUN_EXCHANGE,1}, {0x1fc,MU_GFX_RUUD_SHOP,0},
    {0x0ac,MU_GFX_MIX_SELECTOR,0}, {0x0b4,MU_GFX_ATTRIBUTE_SELECTOR,0}
};

static void presentation_fixture4(mu_gfx_layer *L, int m)
{
    movie *w=&L->mv[m];
    switch(m) {
    case MU_GFX_ELEMENTAL_MIX:
        invokef(L,m,w->path,"InitFixedText","[\"Elemental mix - preview\",\"Recipes\",\"Materials\",\"Charms\",\"Unavailable\",\"Result\",\"No recipes or items\",\"Empty offline fixture\",\"\",\"\",\"\"]");
        invokef(L,m,w->path,"ClearSlotFrame","[]");
        invokef(L,m,w->path,"ClearNumTextAll","[]");
        invokef(L,m,w->path,"SetDefaultPageText","[\"Empty offline fixture. Item operations are unavailable.\"]");
        presentation_set(L,m,"btnMixStart.disabled","true");
        presentation_set(L,m,"MixScrollingList.disabled","true");
        presentation_set(L,m,"MixScrollingList.dataProvider","[]");
        presentation_set(L,m,"btnSocketInfo.disabled","true");
        break;
    case MU_GFX_SOCKET_MIX:
        invokef(L,m,w->path,"initFixedTextObj","[{\"WindowTitle\":\"Socket mix - preview\",\"DefaultPageText\":\"Empty offline fixture. No recipes or items.\",\"MixListTitle\":\"Recipes\",\"ExpectedResultTitle\":\"Result\",\"MixStartBtn\":\"Unavailable\",\"SocketInfoTitle\":\"Unavailable\",\"ConfirmBtn\":\"Close\",\"SocketInfoBtn\":\"Unavailable\"}]");
        presentation_set(L,m,"mcSocketMix.btnMixStart.disabled","true");
        presentation_set(L,m,"mixScrollingList.disabled","true");
        presentation_set(L,m,"mixScrollingList.dataProvider","[]");
        break;
    case MU_GFX_GUARDIAN_MIX:
        invokef(L,m,w->path,"SetText","[{\"Title\":\"Guardian mix - preview\",\"MixListTitle\":\"Recipes\",\"ResultTitle\":\"Result\",\"MixButtonLabel\":\"Unavailable\",\"Description\":\"Empty offline fixture. No recipes or items.\"}]");
        invokef(L,m,w->path,"CreateTab","[[]]");
        invokef(L,m,w->path,"InitSlot","[{\"MainSlotTitle\":\"Materials\",\"SubSlotTitle\":\"Materials\",\"MainSlotQuantity\":\"\",\"SubSlotCount\":0,\"SubSlotQuantity\":\"\"}]");
        presentation_set(L,m,"btnMixStart.disabled","true");
        presentation_set(L,m,"slMixTab.disabled","true");
        break;
    case MU_GFX_HARMONY_MIX:
        invokef(L,m,w->path,"SetText","[{\"Title\":\"Harmony mix - preview\",\"MixListTitle\":\"Recipes\",\"ChangeOptionTitle\":\"Empty offline fixture\",\"ChangeOptionDesc\":\"No recipes or items\",\"RemoveOptionTitle\":\"\",\"RemoveOptionDesc\":\"\",\"RefiningStoneTitle\":\"\",\"RefiningStoneDesc\":\"\",\"ChanceInfo\":\"Unavailable\"}]");
        invokef(L,m,w->path,"CreateTab","[[]]");
        presentation_set(L,m,"slMixTab.disabled","true");
        break;
    case MU_GFX_MUUN_EXCHANGE:
        invokef(L,m,w->path,"Init","[\"Muun exchange - preview\",\"Empty offline fixture. No exchanges.\",1,\"Input\",\"Output\",\"Unavailable\"]");
        invokef(L,m,w->path,"SetCurrentPage","[1,0,\"\"]");
        break;
    case MU_GFX_RUUD_SHOP:
        invokef(L,m,w->path,"Initialize","[\"Ruud shop - preview\",\"Unavailable\",\"Empty offline fixture. No catalogue or purchases.\",\"1 / 1\"]");
        invokef(L,m,w->path,"SetMaxPage","[1]");
        invokef(L,m,w->path,"SetCurrentPage","[0]");
        for(int i=0;i<4;i++) invokef(L,m,w->path,"SetSaleList","[%d,\"\",\"\",\"\",false]",i);
        break;
    case MU_GFX_LUCK_COIN:
        invokef(L,m,w->path,"SetTextInfo","[\"Luck coin exchange - preview\",\"Unavailable\",\"Close\",\"Empty offline fixture. No exchanges.\"]");
        presentation_set(L,m,"btnExchange.disabled","true");
        break;
    case MU_GFX_MIX_SELECTOR:
        invokef(L,m,w->path,"SetMixSelType","[0]");
        invokef(L,m,w->path,"InitTitle","[\"Mix selection - preview\"]");
        invokef(L,m,w->path,"InitBtnTitle","[\"Unavailable\",\"Close\"]");
        invokef(L,m,w->path,"InitBtn2Title","[\"Unavailable\"]");
        invokef(L,m,w->path,"InitBtn3Title","[\"Unavailable\"]");
        invokef(L,m,w->path,"InitMentTitle","[\"Empty offline fixture. No recipe selection.\"]");
        presentation_set(L,m,"btnType1.disabled","true");
        presentation_set(L,m,"btnType2.disabled","true");
        presentation_set(L,m,"btnType3.disabled","true");
        break;
    case MU_GFX_ATTRIBUTE_SELECTOR:
        invokef(L,m,w->path,"InitText","[{\"Title\":\"Attribute mix - preview\",\"SelectMent\":\"Empty offline fixture. No item operations.\",\"MixAttScalpButton\":\"Unavailable\",\"CloseButton\":\"Close\"}]");
        invokef(L,m,w->path,"SetEnableMixAttScalpButton","[false]");
        break;
    }
}

static int presentation_call4(movie *w, const char *name)
{
    if(w->id<MU_GFX_ELEMENTAL_MIX) return -1;
    if(!strcmp(name,"CloseWindow") || (w->id==MU_GFX_LUCK_COIN && !strcmp(name,"onClickExitBtn"))) {
        mu_gfx_layer_show(w->L,w->id,0);
        return 1;
    }
    /* Layout metadata is consumed locally. Unknown callbacks cannot fall
     * through to the existing NPC, item, social or command handlers. */
    return !strcmp(name,"TweenTimeSet") || !strcmp(name,"requestWindowPos") ||
           !strcmp(name,"requestSlotInfo") || !strcmp(name,"SetItem2DImagePos") ||
           !strcmp(name,"SetSlotSize") || !strcmp(name,"SetCashCharmPos") ||
           !strcmp(name,"SetChaosCharmPos") || !strcmp(name,"SetResultPos") ||
           !strcmp(name,"SetSubSlotPos") || !strcmp(name,"SetSrcSlotPos") ||
           !strcmp(name,"SetMainSlotUIInfo") || !strcmp(name,"SetResultSlotUIInfo");
}

int mu_gfx_layer_presentation_slot(mu_gfx_layer *L, unsigned slot)
{
    if (presentation_slot5(L,slot)) return 1;
    if(!L) return 0;
    for(size_t i=0;i<sizeof PRESENTATION_ROUTES4/sizeof *PRESENTATION_ROUTES4;i++) {
        const presentation_route4 *r=&PRESENTATION_ROUTES4[i];
        if(r->slot!=slot) continue;
        if(!presentation_available3(L,r->movie)) return 0;
        if(r->toggle) mu_gfx_layer_toggle(L,r->movie);
        else mu_gfx_layer_show(L,r->movie,1);
        /* ReceiveTalk's already-owned sound tail delivers 25 then 28.
         * This controller must not add another sound or request. */
        return 1;
    }
    return 0;
}

void mu_gfx_layer_presentation_close(mu_gfx_layer *L)
{
    if(!L) return;
    for(int m=MU_GFX_ELEMENTAL_MIX;m<MU_GFX_MOVIES;m++)
        mu_gfx_layer_show(L,m,0);
}
