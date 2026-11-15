/* UI-WINDOWS-005. Empty catalogue and artifact-board presentation only. */
static const presentation_route4 PRESENTATION_ROUTES5[] = {
    {0x164,MU_GFX_PERSONAL_CATALOG,1}, {0x280,MU_GFX_ARTIFACT,1},
    {0x0e0,MU_GFX_DUEL_WATCH,0}
};

static void presentation_fixture5(mu_gfx_layer *L, int m)
{
    movie *w=&L->mv[m];
    if(m==MU_GFX_PERSONAL_CATALOG) {
        invokef(L,m,w->path,"SetText","[{\"Title\":\"Personal shops - empty preview\",\"TitleList\":\"Shops\",\"ItemList\":\"Items\",\"AllShopList\":\"Locked\"}]");
        invokef(L,m,w->path,"SetShopListText","[{\"Title\":\"Shop\",\"CharacterName\":\"Demo name\",\"Whisper\":\"Locked\",\"Letter\":\"Locked\"}]");
        invokef(L,m,w->path,"SetItemListText","[{\"ItemName\":\"Item\",\"ProductType\":\"Type\",\"ItemCount\":\"Count\",\"Price\":\"Price\",\"Whisper\":\"Locked\",\"Letter\":\"Locked\"}]");
        invokef(L,m,w->path,"SetSearchItemText","[{\"SearchItemLabel\":\"No catalogue\",\"SearchItemButton\":\"Locked\"}]");
        invokef(L,m,w->path,"SetShopList","[[]]");
        invokef(L,m,w->path,"SetItemList","[[]]");
        invokef(L,m,w->path,"SetSearchItemList","[[]]");
        invokef(L,m,w->path,"SetSearchButtonEnabled","[false]");
        presentation_set(L,m,"btnTitleList.enabled","true");
        presentation_set(L,m,"btnItemList.enabled","true");
        presentation_set(L,m,"btnAllShopList.disabled","true");
        presentation_set(L,m,"mcSearchItem.tiSearchItem.disabled","true");
    } else if(m==MU_GFX_DUEL_WATCH) {
        invokef(L,m,w->path,"InitTitle","[\"Duel watch\",\"Empty offline fixture. No matches or entry.\"]");
        for(int i=0;i<4;i++) {
            invokef(L,m,w->path,"InitDuelInfo","[%d,\"\",\"No match\",\"Locked\"]",i);
            invokef(L,m,w->path,"UpdateDuelWatch","[%d,\"No match\",true]",i);
        }
    } else if(m==MU_GFX_ARTIFACT) {
        invokef(L,m,w->path,"InitText","[{\"Title\":\"Artifacts - empty preview\",\"OptionListTitle\":\"No options\"}]");
        invokef(L,m,w->path,"SetName","[\"Empty offline fixture\"]");
        invokef(L,m,w->path,"SetSlotData","[[]]");
        invokef(L,m,w->path,"SetOptionText","[\"No artifact records or bonuses.\"]");
        invokef(L,m,w->path,"SetOptionListData","[{\"label\":\"\",\"nodes\":[]}]");
        invokef(L,m,w->path,"SetCurrentPage","[0,1]");
        presentation_set(L,m,"mcSlots.enabled","false");
        presentation_set(L,m,"btnInfoExpand.disabled","true");
        presentation_set(L,m,"btnInfoContract.disabled","true");
    }
}

static int presentation_slot5(mu_gfx_layer *L, unsigned slot)
{
    if(!L) return 0;
    for(size_t i=0;i<sizeof PRESENTATION_ROUTES5/sizeof *PRESENTATION_ROUTES5;i++) {
        const presentation_route4 *r=&PRESENTATION_ROUTES5[i];
        if(r->slot!=slot) continue;
        if(!presentation_available3(L,r->movie)) return 0;
        if(r->toggle) mu_gfx_layer_toggle(L,r->movie);
        else mu_gfx_layer_show(L,r->movie,1);
        return 1;
    }
    return 0;
}

static int presentation_parent5(movie *w, const char *name)
{
    /* Inventory callback 0x00b97ebe..e4: onClickArtifact -> +0x280 toggle.
     * No item or character predicate is read in this callback arm. */
    if(w->id==MU_GFX_INVENTORY && !strcmp(name,"onClickArtifact")) {
        if(w->open) (void)presentation_slot5(w->L,0x280);
        return 1;
    }
    return 0;
}

static int presentation_call5(movie *w, const char *name, const double *v, int n)
{
    if(w->id<MU_GFX_PERSONAL_CATALOG) return -1;
    if(!strcmp(name,"CloseWindow")) {mu_gfx_layer_show(w->L,w->id,0);return 1;}
    /* The original movie already changed the local tab. Replace its request
     * by the same empty lists; reject malformed/foreign callbacks. */
    if(w->id==MU_GFX_PERSONAL_CATALOG && !strcmp(name,"OnClickSearchTab") &&
       n==2 && (v[0]==0 || v[0]==1) && (v[1]==0 || v[1]==1)) {
        invokef(w->L,w->id,w->path,"SetShopList","[[]]");
        invokef(w->L,w->id,w->path,"SetItemList","[[]]");
        return 1;
    }
    return !strcmp(name,"TweenTimeSet") || !strcmp(name,"requestWindowPos") ||
           (w->id==MU_GFX_ARTIFACT && (!strcmp(name,"SetSlotInfo") ||
            !strcmp(name,"OnInitHexSlotCompleted") || !strcmp(name,"SetSlotBoardInfo")));
}
