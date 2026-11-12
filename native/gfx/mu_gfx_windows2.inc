/* UI-WINDOWS-002: original display methods over authored, empty fixtures.
 * The allowlist below is the only callback exit. No request or configuration
 * save is forwarded, including calls forged for disabled controls. */
static int presentation_open(mu_gfx_layer *, int, int);

static void presentation_set(mu_gfx_layer *L, int m, const char *field, const char *value)
{
    char path[256];
    snprintf(path,sizeof path,"%s.%s",L->mv[m].path,field);
    L->api.set_variable(L->mv[m].g,path,value);
}

static void presentation_fixture(mu_gfx_layer *L, int m)
{
    movie *w=&L->mv[m];
    switch(m) {
    case MU_GFX_MACRO:
        invokef(L,m,w->path,"SetMacroMainInfo","[{\"Title\":\"MU Helper - offline preview\",\"TapHunt\":\"Hunting\",\"TapItem\":\"Obtaining\",\"TapEtc\":\"Other\",\"BtnInit\":\"Reset\",\"BtnSave\":\"Save\",\"HuntArea\":\"Hunt area\",\"NormalAtt\":\"Normal attack\",\"DenseMonsterTarget\":\"Dense targets\",\"CloseSkill\":\"Close skill\",\"Counter\":\"Counter\",\"Return\":\"Return\",\"AutoPotion\":\"Auto potion\",\"SupportParty\":\"Support party\",\"AutoHeal\":\"Auto heal\",\"DrainLife\":\"Drain life\",\"BasicSkill\":\"Basic skill\",\"Skill1\":\"Skill1\",\"Skill2\":\"Skill2\",\"ReturnTimeUnit\":\"sec\",\"Condition\":\"Condition\",\"Combo\":\"Combo\",\"DarkSpirit\":\"Dark spirit\",\"DSAutoAtt\":\"Auto attack\",\"DSNoneAtt\":\"No attack\",\"DSWithAtt\":\"Attack together\",\"BatFlockDebuff\":\"Bat flock debuff\",\"BatFlockExplain\":\"Bat flock explain\",\"Buff\":\"Buff\",\"BuffItem\":\"Buff item\",\"GetArea\":\"Get area\",\"Repair\":\"Repair\",\"RepairMuun\":\"Repair muun\",\"RepairGuardian\":\"Repair guardian\",\"ItemGetAll\":\"Item get all\",\"ItemGetSelect\":\"Item get select\",\"GetJewel\":\"Get jewel\",\"GetSet\":\"Get set\",\"GetZen\":\"Get zen\",\"GetExcel\":\"Get excel\",\"GetEventInven\":\"Get event inven\",\"GetEtc\":\"Get etc\",\"BtnAdd\":\"Btn add\",\"BtnDel\":\"Btn del\",\"GetItemList\":\"Get item list\",\"PartyFriend\":\"Party friend\",\"PartyGuild\":\"Party guild\",\"EliteMana\":\"Elite mana\",\"Facebook\":\"Facebook\",\"BtnFacebook\":\"Btn facebook\"}]");
        invokef(L,m,w->path,"SetMacroOption","[[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],[]]");
        invokef(L,m,w->path,"SetFaceBookVisible","[false]");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.btnInit.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.btnSave.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.cbNormalAttack.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.cbDenseMonsterTarget.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.cbCloseRangeSkill.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.cbLongRangeCounter.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.cbReturnPoint.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.tiReturn_delayInput.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.cbAutoPotion.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.mcBuffSkillSlots.cbBuff.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.mcBuffItemSlots.cbBuffItem.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.cbSupportParty.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.cbAutoHeal.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.cbDrainLife.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.mcSubSkill.cbCombo.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.mcDarkSpirit.cbUseDarkSpirit.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.mcDarkSpirit.rbAutoAttack.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.mcDarkSpirit.rbNoneAttack.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.mcDarkSpirit.rbWithAttack.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.mcSlayer.cbBatFlockDebuff.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapItem.cbItemRepair.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapItem.cbRepairMuun.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapItem.cbRepairGuardian.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapItem.cbGetAllItem.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapItem.cbSelectiveGetItem.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapItem.cbJewelItem.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapItem.cbSetItem.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapItem.cbZen.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapItem.cbExcellentItem.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapItem.cbEventInvenItem.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapItem.cbEtcGetItem.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapItem.tiItemName.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapItem.btnRegItem.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapItem.btnUnRegItem.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapItem.mcRegList.slRegList.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapEtc.cbAcceptParty_friend.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapEtc.cbAcceptParty_guild.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapEtc.cbUseEliteManaPotion.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapEtc.btnConnect.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.cbTemporaryForcedLongRangeCounter.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcMacroMain.mcTapHunt.cbTemporaryForcedReturnPoint.disabled","true");
        for (int i=1;i<=8;i++) {
            char field[160];
            snprintf(field,sizeof field,"mcMacroMain.mcTapHunt.mcHuntArea.btnArea%d.disabled",i);
            presentation_set(L,m,field,"true");
            snprintf(field,sizeof field,"mcMacroMain.mcTapItem.mcGetArea.btnArea%d.disabled",i);
            presentation_set(L,m,field,"true");
        }
        break;
    case MU_GFX_MACRO_SUB:
        invokef(L,m,w->path,"InitWindow","[{\"HealTitle\":\"Potion settings - preview\",\"AutoPotion\":\"Auto potion\",\"Ment\":\"No settings are saved.\",\"AutoHeal\":\"Auto heal\",\"DrainLife\":\"Drain life\",\"PartyTitle\":\"Party settings - preview\",\"PartyBuff\":\"Party buff\",\"UsePartyBuff\":\"Use party buff\",\"UsePartyBuffRange\":\"Use party buff range\",\"PartyBuffInterval\":\"Party buff interval\",\"PartyBuffTimeUnit\":\"Party buff time unit\",\"PartyHeal\":\"Party heal\",\"PartyMent\":\"Party ment\",\"PartyMent2\":\"Party ment2\",\"PartyHealFirst\":\"Party heal first\",\"SkillTitle\":\"Skill conditions - preview\",\"SkillOption1\":\"Skill option1\",\"Option1_1\":\"Option1_1\",\"Option1_2\":\"Option1_2\",\"SkillOption2\":\"Skill option2\",\"Option2_1\":\"Option2_1\",\"Option2_2\":\"Option2_2\",\"Option2_3\":\"Option2_3\",\"Option2_4\":\"Option2_4\",\"Skill3Title\":\"Skill3title\",\"tfBasicSkill\":\"Basic skill\",\"tfSkill1\":\"Skill1\",\"cbBuffRange\":\"Cb buff range\",\"tiReturn_delayInput\":\"Ti return_delay input\",\"tfReturn_timeUnit\":\"Return_time unit\",\"Reset\":\"Reset\",\"Save\":\"Save\",\"Close\":\"Close\",\"DelayCondition\":\"Delay condition\",\"SkillDelay\":\"Skill delay\",\"MonsterCondition\":\"Monster condition\",\"ExplosionCondition\":\"Explosion condition\",\"InstantExplosion\":\"Instant explosion\",\"DelayExplosion\":\"Delay explosion\"}]");
        presentation_set(L,m,"m_mcMovie.mcHeal.btnReset.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcHeal.btnSave.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcParty.cbBuff.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcParty.tiBuffValue.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcParty.cbBuffRange.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcParty.mcHeal.cbHealFirst.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcParty.mcHeal.btnSupportPartyMenu.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcParty.btnReset.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcParty.btnSave.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill1.rbInTheRange.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill1.rbHitMe.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill1.rbTwoMonsters.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill1.rbThreeMonsters.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill1.rbFourMonsters.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill1.rbFiveMonsters.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill1.btnReset.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill1.btnSave.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill1.cbDelayCondition.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill1.tiAttack_Delay.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill1.cbMonsterCondition.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill1.cbExplosionCondition.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill1.rbInstantExplosion.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill1.rbDelayExplosion.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill1.tiExplosionDelay.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill2.rbInTheRange.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill2.rbHitMe.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill2.rbTwoMonsters.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill2.rbThreeMonsters.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill2.rbFourMonsters.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill2.rbFiveMonsters.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill2.btnReset.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill2.btnSave.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill2.cbDelayCondition.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill2.tiAttack_Delay.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill2.cbMonsterCondition.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill2.cbExplosionCondition.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill2.rbInstantExplosion.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill2.rbDelayExplosion.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcSkill2.tiExplosionDelay.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcskill3.cbBuffRange.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcskill3.tiReturn_delayInput.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcskill3.btnReset.disabled","true");
        presentation_set(L,m,"m_mcMovie.mcskill3.btnSave.disabled","true");
        break;
    case MU_GFX_HUNT_RECORD:
        invokef(L,m,w->path,"noTest","[]");
        presentation_set(L,m,"_TestController.visible","false");
        presentation_set(L,m,"_TestController._visible","false");
        invokef(L,m,w->path,"setCharInfo","[{\"titleLabel\":\"Hunt record - offline preview\",\"label\":\"Demo class\",\"classInfo\":\"Dark Knight\"}]");
        invokef(L,m,w->path,"initWindow","[{\"myInfoLabel\":\"Demo record\",\"tableTabLabel\":\"Table\",\"graphTabLabel\":\"Graph\",\"accureInfo\":\"Total\",\"perSecInfo\":\"Per second\",\"DateLabel\":\"Date\",\"LevelLabel\":\"Level\",\"HuntTimeLabel\":\"Time\",\"NorDmg\":\"Normal\",\"AttDmg\":\"Skill\",\"heal\":\"Healing\",\"MonCnt\":\"Monsters\",\"Exp\":\"Experience\",\"miniWndTitle\":\"Demo record\",\"NorDmgPerSec\":\"Normal / sec\",\"AttDmgPerSec\":\"Skill / sec\",\"healPerSec\":\"Healing / sec\",\"MonCntPerSec\":\"Monsters / sec\",\"ExpPerSec\":\"Exp / sec\",\"mapInfo\":[{\"label\":\"Offline preview\",\"index\":0}]}]");
        invokef(L,m,w->path,"setPastInfo","[[]]");
        invokef(L,m,w->path,"setCurInfo","[{\"date\":{\"year\":2026,\"month\":1,\"date\":1},\"time\":{\"hour\":0,\"minute\":0,\"second\":0},\"level\":0,\"norDmg\":0,\"attDmg\":0,\"heal\":0,\"killCnt\":0,\"exp\":0}]");
        presentation_set(L,m,"_Wnd._checkBoxMyInfo.disabled","true");
        break;
    case MU_GFX_STORAGE_EXT:
        invokef(L,m,w->path,"InitTitle","[\"Expanded storage - offline preview\"]");
        invokef(L,m,w->path,"SetExtend","[true]");
        invokef(L,m,w->path,"SetKeepZen","[\"0\"]");
        invokef(L,m,w->path,"InitText","[\"Stored zen\",\"Charge\"]");
        invokef(L,m,w->path,"InitButton","[\"Unavailable\",\"Unavailable\",\"Unavailable\",\"Unavailable\"]");
        invokef(L,m,w->path,"SetExtendButtonDisable","[true]");
        presentation_set(L,m,"btnDeposit.disabled","true");
        break;
    case MU_GFX_MATCH_PARTY:
        invokef(L,m,w->path,"InitPartyInfoText","[{\"PartyInfoTitle\":\"Offline preview\"}]");
        invokef(L,m,w->path,"InitRecruitText","[{\"recruitTitle\":\"Offline preview\",\"recruitMent\":\"Recruit ment\",\"waitingListTitle\":\"Offline preview\",\"mentInput\":\"Ment input\",\"levelMin\":\"Level min\",\"levelMax\":\"Level max\",\"usePW\":\"Use pw\",\"autoJoin\":\"Auto join\",\"energyElf\":\"Energy elf\",\"recruitLevel\":\"Recruit level\",\"levelMent\":\"Level ment\",\"energyElfMent\":\"Energy elf ment\",\"category1\":\"Category1\",\"category2\":\"Category2\",\"category3\":\"Category3\",\"category4\":\"Category4\",\"btnRecruitOK\":\"Recruit ok\",\"btnRecruitCancel\":\"Recruit cancel\"}]");
        invokef(L,m,w->path,"InitSearchText","[{\"title\":\"Party matching - offline preview\",\"searchTab\":\"Search\",\"recruitTab\":\"Recruit\",\"partyInfoTab\":\"Party info\",\"partyMemberTitle\":\"Party member title\",\"tfRole\":\"Role\",\"tfName\":\"Name\",\"tfClass\":\"Class\",\"tfLevel\":\"Level\",\"join\":\"Join\",\"joinCancel\":\"Join cancel\",\"autoMacro\":\"Auto macro\",\"btnRandomParty\":\"Random party\",\"searchMent\":\"Empty demo catalogue\",\"searchdInput\":\"Searchd input\",\"btnSearch\":\"Unavailable\",\"recruitList\":\"No parties\",\"btnShowPossible\":\"Show possible\",\"btnInfoCheck\":\"Info check\",\"tfTitleRequestWait\":\"Title request wait\",\"btnRefresh\":\"Unavailable\"}]");
        invokef(L,m,w->path,"ClearAllPartyList","[]");
        invokef(L,m,w->path,"SetPageSelect","[1,1]");
        invokef(L,m,w->path,"ShowWindow","[0]");
        presentation_set(L,m,"btnSearch.disabled","true");
        presentation_set(L,m,"btnRefresh.disabled","true");
        presentation_set(L,m,"btnRecruitOK.disabled","true");
        presentation_set(L,m,"btnRecruitCancel.disabled","true");
        presentation_set(L,m,"btnJoin.disabled","true");
        presentation_set(L,m,"btnJoinCancel.disabled","true");
        presentation_set(L,m,"tiSearchInput.disabled","true");
        presentation_set(L,m,"tiPassword.disabled","true");
        break;
    case MU_GFX_MATCH_GUILD:
        invokef(L,m,w->path,"InitRecruitText","[{\"title\":\"Offline preview\",\"mentInput\":\"Ment input\",\"guildMent\":\"Guild ment\",\"recruitInterest\":\"Recruit interest\",\"recruitLevel\":\"Recruit level\",\"recruitClass\":\"Recruit class\",\"cbLevelUp\":\"Cb level up\",\"cbEventMap\":\"Cb event map\",\"cbPvP\":\"Cb pv p\",\"arkaBattle\":\"Arka battle\",\"siegeWar\":\"Siege war\",\"cbLevel01\":\"Cb level01\",\"cbLevel02\":\"Cb level02\",\"cbLevel03\":\"Cb level03\",\"cbLevel04\":\"Cb level04\",\"cbLevel05\":\"Cb level05\",\"btnRecruitOK\":\"Recruit ok\",\"btnRecruitCancel\":\"Recruit cancel\",\"btnEntryList\":\"Entry list\"}]");
        invokef(L,m,w->path,"InitSearch","[\"Guild matching - offline preview\",\"Empty demo catalogue\",\"\",\"No guilds\",\"Search\",\"Recruit\",\"Unavailable\",\"Unavailable\",\"Join state\",\"Unavailable\"]");
        invokef(L,m,w->path,"ClearAllGuildList","[]");
        invokef(L,m,w->path,"SetPageSelect","[1,1]");
        invokef(L,m,w->path,"ShowWindow","[0]");
        presentation_set(L,m,"btnSearch.disabled","true");
        presentation_set(L,m,"btnRefresh.disabled","true");
        presentation_set(L,m,"btnRecruitOK.disabled","true");
        presentation_set(L,m,"btnRecruitCancel.disabled","true");
        presentation_set(L,m,"btnJoin.disabled","true");
        presentation_set(L,m,"btnJoinCancel.disabled","true");
        presentation_set(L,m,"tiSearchInput.disabled","true");
        presentation_set(L,m,"tiPassword.disabled","true");
        break;
    case MU_GFX_GUILD_MATCH:
        invokef(L,m,w->path,"InitTexts","[{\"tfTitle\":\"Guild matching - offline preview\",\"searchTab\":\"Search\",\"recruitTab\":\"Recruit\",\"infoTab\":\"Info\",\"lbGuildRecruitInfoTextTitle\":\"Guild recruit info text title\",\"lbGuildName\":\"Guild name\",\"lbGuildUserCount\":\"Guild user count\",\"lbGuildMaster\":\"Guild master\",\"lbLevelLimit\":\"Level limit\",\"lbGuildLevelAverage\":\"Guild level average\",\"joinStateMent\":\"Join state ment\",\"joinStateText1\":\"Join state text1\",\"joinStateText2\":\"Join state text2\",\"joinStateText3\":\"Join state text3\",\"joinStateBack\":\"Join state back\",\"joinStateLetter\":\"Join state letter\",\"joinStateCancel\":\"Join state cancel\",\"searchMent\":\"Empty demo catalogue\",\"recruitList\":\"No guilds\",\"searchdInput\":\"Searchd input\",\"btnSearch\":\"Unavailable\",\"btnJoin\":\"Join\",\"btnJoinStat\":\"Join stat\",\"btnRefresh\":\"Unavailable\",\"lbRecruitText0\":\"Recruit text0\",\"lbRecruitText1\":\"Recruit text1\",\"lbRecruitText2\":\"Recruit text2\",\"lbRecruitText3\":\"Recruit text3\",\"lbRecruitText4\":\"Recruit text4\",\"lbRecruitText5\":\"Recruit text5\",\"lbRecruitText6\":\"Recruit text6\",\"lbRecruitText7\":\"Recruit text7\",\"lbRecruitText8\":\"Recruit text8\",\"lbRecruitText9\":\"Recruit text9\",\"lbRecruitText10\":\"Recruit text10\",\"lbRecruitText11\":\"Recruit text11\",\"lbRecruitText12\":\"Recruit text12\",\"btnRecruitRegister\":\"Recruit register\",\"btnRecruitStop\":\"Recruit stop\"}]");
        invokef(L,m,w->path,"ClearAllGuildList","[]");
        invokef(L,m,w->path,"ClearRecruitListInfo","[]");
        invokef(L,m,w->path,"ClearJoinStateScrollListData","[]");
        invokef(L,m,w->path,"SetVisiblePopup","[false]");
        invokef(L,m,w->path,"SetPageSelect","[1,1]");
        invokef(L,m,w->path,"SetTab","[0]");
        break;
    case MU_GFX_PLAY_GUIDE:
        invokef(L,m,w->path,"InitText","[\"Play guide - offline preview\"]");
        break;
    }
}

/* Parent teardown is local and cannot leave an orphaned child over gameplay. */
static void presentation_shown(mu_gfx_layer *L, int m, int open)
{
    if (open && m==MU_GFX_MACRO) {
        L->macro_tab=0;
        invokef(L,m,L->mv[m].path,"ShowTap","[0,1]");
    }
    if (!open && m==MU_GFX_MACRO) mu_gfx_layer_show(L,MU_GFX_MACRO_SUB,0);
    if (!open && m==MU_GFX_STORAGE) mu_gfx_layer_show(L,MU_GFX_STORAGE_EXT,0);
    if (!open && m==MU_GFX_MACRO_SUB) L->macro_sub_type=0;
    if (m==MU_GFX_HUNT_RECORD) L->hunt_mini=0;
}

/* -1 means the original 001 allowlist still applies. */
static int presentation_call2(movie *w, const char *name, const char *args, const double *v, int n)
{
    mu_gfx_layer *L=w->L;
    (void)args;
    if (w->id==MU_GFX_HUNT_RECORD && !strcmp(name,"closeWindow")) {
        mu_gfx_layer_show(L,w->id,0);
        return 1;
    }
    if (!w->open) return -1;
    if (w->id==MU_GFX_MATCHING && (!strcmp(name,"onClickbtnParty") || !strcmp(name,"onClickbtnGuild"))) {
        int child=!strcmp(name,"onClickbtnParty") ? MU_GFX_MATCH_PARTY : MU_GFX_MATCH_GUILD;
        if (!presentation_open(L,child,0)) return 0;
        mu_gfx_layer_show(L,w->id,0);
        return 1;
    }
    if (w->id==MU_GFX_MACRO && !strcmp(name,"btnTap") && n==1 && v[0]>=0 && v[0]<=2 && v[0]==(int)v[0]) {
        L->macro_tab=(int)v[0]; /* the original movie already selected the local tab */
        return 1;
    }
    if (w->id==MU_GFX_MACRO && !strcmp(name,"btnMenu") && n==1 && v[0]>=0 && v[0]<=3 && v[0]==(int)v[0]) {
        /* Authored base-DK fixture: potion 1, party 5, skill conditions 7/8.
         * Party support is hidden in that class; reject a forged party callback. */
        if (v[0]==1) return 0;
        int type=v[0]==0 ? 1 : v[0]==2 ? 7 : 8;
        if (!L->mv[MU_GFX_MACRO_SUB].open || L->macro_sub_type==type) {
            if (!presentation_open(L,MU_GFX_MACRO_SUB,0)) return 0;
        }
        if (L->mv[MU_GFX_MACRO_SUB].open) {
            L->macro_sub_type=type;
            invokef(L,MU_GFX_MACRO_SUB,L->mv[MU_GFX_MACRO_SUB].path,"HideWindow","[]");
            invokef(L,MU_GFX_MACRO_SUB,L->mv[MU_GFX_MACRO_SUB].path,"ShowWindow","[%d,[]]",type);
        }
        return 1;
    }
    if ((w->id==MU_GFX_MATCH_PARTY || w->id==MU_GFX_MATCH_GUILD) &&
        (!strcmp(name,"onClickbtnSearchTab") || !strcmp(name,"onClickbtnRecruitTab") ||
         (w->id==MU_GFX_MATCH_PARTY && !strcmp(name,"onClickbtnPartyInfoTab")))) {
        int tab=!strcmp(name,"onClickbtnSearchTab") ? 0 : !strcmp(name,"onClickbtnRecruitTab") ? 1 : 4;
        invokef(L,w->id,w->path,"ShowWindow","[%d]",tab);
        return 1;
    }
    if (w->id==MU_GFX_GUILD_MATCH && !strcmp(name,"onTabChange") && n==1 && v[0]>=0 && v[0]<=2 && v[0]==(int)v[0]) {
        L->guild_tab=(int)v[0];
        invokef(L,w->id,w->path,"SetTab","[%d]",L->guild_tab);
        return 1;
    }
    if (w->id==MU_GFX_HUNT_RECORD && (!strcmp(name,"onBigWnd") || !strcmp(name,"onMiniWnd"))) {
        L->hunt_mini=!strcmp(name,"onMiniWnd");
        return 1;
    }
    return -1;
}
