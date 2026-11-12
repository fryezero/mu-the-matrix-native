/* UI-WINDOWS-001. Original movies, authored empty presentation. No session,
 * item, command or request handler is reachable from these callbacks. */
static int presentation_movie(int m)
{
    return m >= MU_GFX_COMMAND && m <= MU_GFX_GREMORY;
}

static void presentation_init(mu_gfx_layer *L)
{
    for (int m = MU_GFX_COMMAND; m <= MU_GFX_GREMORY; ++m) {
        movie *w = &L->mv[m];
        if (!w->g || !w->path[0]) continue;
        switch (m) {
        case MU_GFX_COMMAND:
            invokef(L,m,w->path,"InitTitle","[\"Command\"]");
            invokef(L,m,w->path,"InitBtnText",
                "[\"Trade\",\"Buy\",\"Party\",\"Whisper\",\"Guild\",\"Alliance\",\"Rival on\",\"Rival off\",\"Add friend\",\"Follow\",\"Duel\"]");
            invokef(L,m,w->path,"SetAllButtonsDisable","[true]");
            break;
        case MU_GFX_MATCHING:
            invokef(L,m,w->path,"InitSelect",
                "[\"Matching\",\"Offline preview: catalogues unavailable\",\"Party\",\"Guild\",\"Close\"]");
            break;
        case MU_GFX_GENS:
            invokef(L,m,w->path,"InitText",
                "[\"Gens\",\"Family\",\"Gens rank\",\"Rank\",\"\",\"Contribution\",\"Information\"]");
            /* Authored empty fixture: the timeline otherwise shows its default family badge. */
            for (int family = 0; family < 2; ++family) {
                char path[192];
                snprintf(path,sizeof path,"%s.mcGensRanking.mcMark_%c._visible",w->path,family ? 'V' : 'D');
                L->api.set_variable(w->g,path,"false");
            }
            invokef(L,m,w->path,"SetGensTeamName","[\"None\"]");
            invokef(L,m,w->path,"SetRanking","[\"-\"]");
            invokef(L,m,w->path,"SetGensRanking","[\"-\"]");
            invokef(L,m,w->path,"SetContribution","[\"0\"]");
            invokef(L,m,w->path,"SetNextContribution","[\"\"]");
            invokef(L,m,w->path,"SetGensInfo","[\"Offline preview. No family or ranking record.\"]");
            break;
        case MU_GFX_PET_INVENTORY:
            invokef(L,m,w->path,"SetText",
                "[{\"Title\":\"Muun inventory\",\"MainMuun\":\"Main Muun\",\"SubMuun\":\"Sub Muun\",\"HeroMuun\":\"Hero Muun\",\"Sorting\":\"Sort\",\"PetBook\":\"Book\"}]");
            invokef(L,m,w->path,"SortingEnabled","[false]");
            invokef(L,m,w->path,"PetBookEnabled","[false]");
            L->pet_page = 1;
            invokef(L,m,w->path,"SetCurrentPage","[1]");
            break;
        case MU_GFX_GREMORY:
            invokef(L,m,w->path,"Initialize",
                "[{\"Title\":\"Gremory case\",\"TabName1\":\"Character\",\"TabName2\":\"Account\",\"TabName3\":\"MUA\",\"TabName4\":\"Store\"}]");
            invokef(L,m,w->path,"SetDescText","[\"Offline preview. No rewards or claims.\"]");
            invokef(L,m,w->path,"SetMaxItemCount","[0]");
            invokef(L,m,w->path,"RefreshList","[[]]");
            invokef(L,m,w->path,"SelectTab","[2]");
            break;
        }
        L->presentation_ready |= 1u << (m - MU_GFX_COMMAND);
    }
}

/* Movie-local layout and navigation only. Unknown callbacks refuse by default,
 * including forged state-changing actions from a disabled button. */
static int presentation_call(movie *w, const char *name, const char *args, const double *v, int n)
{
    mu_gfx_layer *L = w->L;
    (void)args;
    if (!strcmp(name,"CloseWindow") ||
        (w->id == MU_GFX_MATCHING && !strcmp(name,"onClickbtnClose"))) {
        mu_gfx_layer_show(L,w->id,0);
        return 1;
    }
    if (!strcmp(name,"TweenTimeSet") || !strcmp(name,"requestWindowPos") ||
        !strcmp(name,"requestSlotInfo") || !strcmp(name,"EQUIPrequestSlotInfo")) return 1;
    if (w->id == MU_GFX_GREMORY && !strcmp(name,"OnTabSelected") &&
        n == 1 && v[0] >= 1 && v[0] <= 4 && v[0] == (int)v[0]) {
        invokef(L,w->id,w->path,"RefreshList","[[]]");
        return 1;
    }
    if (w->id == MU_GFX_PET_INVENTORY &&
        (!strcmp(name,"onClickprevBtn") || !strcmp(name,"onClicknextBtn"))) {
        /* The movie authors five pages. Every page stays empty. */
        int page = L->pet_page + (!strcmp(name,"onClicknextBtn") ? 1 : -1);
        if (page < 1 || page > 5) return 0;
        L->pet_page = page;
        invokef(L,w->id,w->path,"SetCurrentPage","[%d]",page);
        return 1;
    }
    logf_(L,"presentation: %s refused %s",w->file,name);
    return 0;
}

static int presentation_open(mu_gfx_layer *L, int m, int menu)
{
    if (!L->mv[m].g || !L->mv[m].path[0] ||
        !(L->presentation_ready & (1u << (m - MU_GFX_COMMAND)))) return 0;
    mu_gfx_layer_toggle(L,m);
    /* Menu handler 0x00c714bd emits once after dispatch. Direct D does not. */
    if (menu && L->cfg.window_sound)
        L->cfg.window_sound(L->cfg.tooltip_user,25,0x00c716f6u);
    return 1;
}

static int presentation_menu(mu_gfx_layer *L, int id)
{
    int m = id == 11 ? MU_GFX_GENS : id == 12 ? MU_GFX_MATCHING :
            id == 13 ? MU_GFX_PET_INVENTORY : id == 15 ? MU_GFX_GREMORY : -1;
    return m >= 0 ? presentation_open(L,m,1) : 0;
}

static int presentation_key(mu_gfx_layer *L, int vk)
{
    if (vk == 27) {
        for (int i = L->norder - 1; i >= 0; --i)
            if (presentation_movie(L->order[i]) && L->mv[L->order[i]].open) {
                mu_gfx_layer_show(L,L->order[i],0);
                return 1;
            }
    }
    if (vk == 'D') return presentation_open(L,MU_GFX_COMMAND,0);
    return presentation_menu(L,vk == 'B' ? 11 : vk == 'N' ? 12 :
                              vk == 'Y' ? 13 : vk == 'K' ? 15 : -1);
}
