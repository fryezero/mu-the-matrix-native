/* UI-WINDOWS-003. Empty presentation providers; item/card/list mutations refuse. */
static int presentation_available3(mu_gfx_layer *L, int m)
{
    return L->mv[m].g && L->mv[m].path[0] &&
        (L->presentation_ready & (1u << (m - MU_GFX_COMMAND)));
}

static void presentation_fixture3(mu_gfx_layer *L, int m)
{
    movie *w=&L->mv[m];
    if (m==MU_GFX_BAG) {
        invokef(L,m,w->path,"InitText","[\"Expanded inventory\"]");
        /* Authored eligibility, never the character's purchased/period state. */
        invokef(L,m,w->path,"SetExtensionBagNumber","[2]");
    } else if (m==MU_GFX_TREE5_VIEWER) {
        invokef(L,m,w->path,"SetText","[{\"title\":\"Skill cards - empty preview\",\"btnSetting\":\"Filters\",\"cbSetView0\":\"Skill\",\"cbSetView1\":\"Ability 1\",\"cbSetView2\":\"Ability 2\",\"cbSetView3\":\"Ability 3\",\"cbSetView4\":\"Ability 4\",\"cbSetView5\":\"Ability 5\",\"cbSetView6\":\"Ability 6\",\"cbSetView7\":\"Ability 7\",\"cbSetView8\":\"Ability 8\",\"cbMyItemView\":\"Owned cards\",\"CanLevelUpView\":\"Level-up unavailable\"}]");
        invokef(L,m,w->path,"InitAbilityTypeTitleInfo","[]");
        invokef(L,m,w->path,"InitButtonState","[]");
        invokef(L,m,w->path,"SetViewTypeButtonText","[\"List view\"]");
        invokef(L,m,w->path,"SetViewTypeToggleButtonSelected","[false]");
        invokef(L,m,w->path,"SetMaxPage","[1]");
        invokef(L,m,w->path,"SetCurrentPage","[1]");
        invokef(L,m,w->path,"SetPageSelectText","[\"1 / 1\"]");
        for (int i=0;i<20;i++) {
            invokef(L,m,w->path,"InitSlotDatas","[%d]",i);
            invokef(L,m,w->path,"InitSlotDatas_ListView","[%d]",i);
            invokef(L,m,w->path,"SetVisibleCardView_ListView","[%d,false]",i);
        }
        presentation_set(L,m,"mcSetting.cbMyItemView.disabled","true");
        presentation_set(L,m,"mcSetting.cbCanLevelUpView.disabled","true");
        for (int i=0;i<9;i++) {
            char field[96];snprintf(field,sizeof field,"mcSetting.cbView%d.disabled",i);
            presentation_set(L,m,field,"true");
        }
    } else if (m==MU_GFX_AUTOMATIC) {
        invokef(L,m,w->path,"SetAutomaticMacroFixedText","[{\"tfLeaderMacroTitle\":\"Automatic helper - preview\",\"tfRole\":\"Role\",\"tfState\":\"State\",\"tfName\":\"Demo name\",\"bmMainPosition1\":\"Any\",\"bmMainPosition2\":\"Any\",\"strInputCharacterName\":\"Unavailable\",\"strPartyMatchingAutoJoin\":\"Unavailable\",\"tfPartyRunning\":\"Unavailable\",\"tfPartyRecruit\":\"Unavailable\",\"tfPartyMember\":\"Slot \",\"tfUnregister\":\"Empty\",\"tfImmediatelyRegister\":\"Unavailable\",\"tfPartyMatching\":\"Unavailable\",\"btnCharacterJoin\":\"Unavailable\",\"tfHuntingSettingTitle\":\"Empty offline fixture\",\"tfHuntingMap\":\"Map\",\"tfPosition\":\"Position\",\"tfAttribute\":\"Attribute\",\"tfPlaySettingTitle\":\"Activation unavailable\",\"tfPlayMent1\":\"No helper execution\",\"tfPlayMent2\":\"No saved configuration\",\"tfPlayMent3\":\"No matching requests\",\"rbLeaderWaitSafetyZone\":\"Unavailable\",\"rbLeaderAutoMatching\":\"Unavailable\",\"rbLeaderIntactlyPlay\":\"Unavailable\",\"btnAutoStart\":\"Unavailable\",\"btnImmediatelyStart\":\"Unavailable\",\"btnCancel\":\"Unavailable\",\"btnExit\":\"Close\",\"bmAttribute1\":\"Any\",\"bmAttribute2\":\"Any\",\"bmAttribute3\":\"Any\",\"bmAttribute4\":\"Any\",\"bmAttribute5\":\"Any\",\"bmAttribute6\":\"Any\"}]");
        invokef(L,m,w->path,"OpeningAutomaticMacro","[[]]");
        invokef(L,m,w->path,"VisibleLeaderMacro","[true]");
        static const char *const controls[]={"btnAutoStart","btnImmediatelyStart","btnCancel",
            "dmLeaderHuntingMap","dmLeaderPosition","dmLeaderAttribute","tiLeaderDieCount",
            "rbLeaderWaitSafetyZone","rbLeaderAutoMatching","rbLeaderIntactlyPlay"};
        for (size_t i=0;i<sizeof controls/sizeof *controls;i++) {
            char field[128];snprintf(field,sizeof field,"%s.disabled",controls[i]);
            presentation_set(L,m,field,"true");
        }
        presentation_set(L,m,"tiLeaderDieCount.text", "\"\"");
        for (int i=1;i<=4;i++) {
            char field[128];
            snprintf(field,sizeof field,"mcLeaderMacro.mcPartyMember%d.dmPartyState.disabled",i);
            presentation_set(L,m,field,"true");
            snprintf(field,sizeof field,"mcLeaderMacro.mcPartyMember%d.tiCharacterName.disabled",i);
            presentation_set(L,m,field,"true");
            snprintf(field,sizeof field,"mcLeaderMacro.mcPartyMember%d.btnCharacterJoin.disabled",i);
            presentation_set(L,m,field,"true");
        }
    } else if (m==MU_GFX_BLOCKED_CHAT) {
        invokef(L,m,w->path,"InitBlockedChatText","[\"Blocked chat - empty preview\",\"No saved users\",\"Locked\",\"Locked\"]");
        invokef(L,m,w->path,"ClearScrollListData","[]");
        presentation_set(L,m,"btnRegistUser.disabled","true");
        presentation_set(L,m,"btnUnRegistUser.disabled","true");
        presentation_set(L,m,"tiBlockID.disabled","true");
    }
}

static void presentation_shown3(mu_gfx_layer *L, int m, int open)
{
    /* 0x00b91950 auto-opens eligible bags; 0x00b919d5 closes them with inventory. */
    if (m==MU_GFX_INVENTORY && presentation_available3(L,MU_GFX_BAG))
        mu_gfx_layer_show(L,MU_GFX_BAG,open);
    if (m==MU_GFX_AUTOMATIC) {
        const char *top=channel(L,"topmenu");
        if (*top) invokef(L,MU_GFX_MAIN,top,"setPlayAutomaticMacro","[false]");
    }
    if (m==MU_GFX_BLOCKED_CHAT) {
        const char *path=channel(L,"chat");
        if (!*path) path=L->mv[MU_GFX_CHAT].path;
        invokef(L,MU_GFX_CHAT,path,"setBlocked","[%s]",open ? "true" : "false");
    }
}

static int presentation_requested3(const char *args)
{
    const char *p=strstr(args,"\"open\"");
    if (!p) return -1;
    p+=6;
    while (*p==' ' || *p=='\t' || *p=='\n') ++p;
    if (*p++!=':') return -1;
    while (*p==' ' || *p=='\t' || *p=='\n') ++p;
    int result;
    if (!strncmp(p,"true",4)) {result=1;p+=4;}
    else if (!strncmp(p,"false",5)) {result=0;p+=5;}
    else return -1;
    while (*p==' ' || *p=='\t' || *p=='\n') ++p;
    return *p=='}' || *p==',' ? result : -1;
}

/* Parent callbacks are consumed even when unavailable, before legacy item/social handlers. */
static int presentation_parent3(movie *w, const char *name, const char *args)
{
    mu_gfx_layer *L=w->L;
    if (w->id==MU_GFX_INVENTORY && !strcmp(name,"onClickbtnExtensionBag")) {
        if (w->open) (void)presentation_open(L,MU_GFX_BAG,0);
        return 1;
    }
    if (w->id==MU_GFX_MAIN && !strcmp(name,"topmenu")) {
        char event[64],action[64];
        if (json_string(args,0,event,sizeof event) && !strcmp(event,"MacroMenu") &&
            json_string(args,1,action,sizeof action) && !strcmp(action,"AutomaticMacroStart")) {
            (void)presentation_open(L,MU_GFX_AUTOMATIC,0);
            return 1;
        }
    }
    if ((w->id==MU_GFX_CHAT || (L->base_mode && w->id==MU_GFX_MAIN)) && !strcmp(name,"chat")) {
        char event[64];
        if (json_string(args,0,event,sizeof event) && !strcmp(event,"BlockedUser")) {
            /* 0x00c5fd7d: requested visibility, not an unconditional toggle. */
            int open=presentation_requested3(args);
            if ((open==0 || open==1) && presentation_available3(L,MU_GFX_BLOCKED_CHAT))
                mu_gfx_layer_show(L,MU_GFX_BLOCKED_CHAT,(int)open);
            return 1;
        }
    }
    return 0;
}

static int presentation_call3(movie *w, const char *name, const char *args)
{
    if (w->id<MU_GFX_BAG) return -1;
    mu_gfx_layer *L=w->L;
    if (w->id==MU_GFX_AUTOMATIC && !strcmp(name,"LeaveComplete")) {
        /* Readback cannot run reentrantly inside the player's callback. */
        L->automatic_leave_pending=1;
        return 1;
    }
    if (!strcmp(name,"CloseWindow")) {
        mu_gfx_layer_show(L,w->id,0);
        return 1;
    }
    if (!strcmp(name,"TweenTimeSet") || !strcmp(name,"requestWindowPos") || !strcmp(name,"requestSlotInfo"))
        return 1;
    if (w->open && w->id==MU_GFX_TREE5_VIEWER && !strcmp(name,"onClickViewTypeToggle") &&
        (!strcmp(args,"[true]") || !strcmp(args,"[false]"))) {
        /* 0x00b1602a inverts the movie-reported selection before applying it. */
        int list=!strcmp(args,"[false]");
        invokef(L,w->id,w->path,"SetViewTypeButtonText","[\"%s\"]",list ? "Book view" : "List view");
        invokef(L,w->id,w->path,"SetViewTypeToggleButtonSelected","[%s]",list ? "true" : "false");
        return 1;
    }
    return 0;
}

static int presentation_key3(mu_gfx_layer *L, int vk, int mods)
{
    if (!mods && vk==113) return presentation_open(L,MU_GFX_BLOCKED_CHAT,0);
    if (mods!=2 || (vk!='J' && vk!='I')) return 0;
    if (!presentation_available3(L,MU_GFX_TREE5_VIEWER)) return 0;
    if (vk=='I') return presentation_open(L,MU_GFX_TREE5_VIEWER,0);
    /* 0x00efc118: equal -> toggle both; unequal -> open both. Preflight atomically. */
    if (!L->mv[MU_GFX_TREE5].g || !L->mv[MU_GFX_TREE5].path[0]) return 0;
    int open=!(L->mv[MU_GFX_TREE5].open && L->mv[MU_GFX_TREE5_VIEWER].open);
    mu_gfx_layer_show(L,MU_GFX_TREE5,open);
    mu_gfx_layer_show(L,MU_GFX_TREE5_VIEWER,open);
    return 1;
}

/* Drain the local Exit notification after pump; a stale animation cannot close a reopened view. */
static void presentation_sync3(mu_gfx_layer *L)
{
    if (!L->automatic_leave_pending) return;
    L->automatic_leave_pending=0;
    movie *w=&L->mv[MU_GFX_AUTOMATIC];
    char path[192];snprintf(path,sizeof path,"%s.m_bVisibleState",w->path);
    const char *visible=L->api.get_variable(w->g,path);
    if (visible && !strcmp(visible,"false")) mu_gfx_layer_show(L,w->id,0);
}
