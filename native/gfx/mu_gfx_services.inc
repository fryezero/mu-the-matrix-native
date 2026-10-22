/* Personal-store movies and repair transactions, NATIVE-MIX-001.
 * Included by the layer so all item ownership uses one inventory.
 * Predicate/price callbacks are reconstructed; delayed replies, listing
 * capacity and the sample remote product are authored offline policy. */
static int service_reserved(const mu_gfx_layer *L,int index)
{
    const struct item_services *s=&L->services;
    for(int k=0;k<SERVICE_PRODUCTS;k++)for(int j=0;j<s->products[k].n;j++)
        if(s->products[k].ids[j]==index)return 1;
    if(s->draft_active)for(int j=0;j<s->draft.n;j++)if(s->draft.ids[j]==index)return 1;
    return 0;
}
static void service_list(mu_gfx_layer *L)
{
    struct item_services *s=&L->services;movie *mv=&L->mv[MU_GFX_STORE_LIST];
    invokef(L,mv->id,mv->path,"SetText","[{\"Title\":\"Personal store (offline demo)\",\"ShopTitle\":\"Store title\",\"ItemName\":\"Item\",\"ProductType\":\"Type\",\"ItemCount\":\"Count\",\"Price\":\"Price\",\"OpenShop\":\"Open store\",\"CloseShop\":\"Close store\"}]");
    invokef(L,mv->id,mv->path,"SetMaxShopTitle","[44]");
    invokef(L,mv->id,mv->path,"SetOpenType","[%d]",s->browsing?1:0);
    invokef(L,mv->id,mv->path,"SetState","[%d]",s->shop_open);
    char title[160];json_quote(title,sizeof title,s->browsing?"Demo trader":s->title);
    invokef(L,mv->id,mv->path,"SetShopTitle","[%s]",title);
    if(s->browsing) {
        invokef(L,mv->id,mv->path,"SetProductInfoList","[[{\"bItemRegistered\":true,\"ProductID\":0,\"ItemName\":\"Demo healing potion\",\"ProductType\":\"Single\",\"ItemCount\":\"1\",\"PriceZen\":\"1,000\",\"PriceBless\":\"0\",\"PriceSoul\":\"0\"}]]");return;
    }
    char rows[8192];size_t at=0;rows[0]=0;
    for(int k=0;k<SERVICE_PRODUCTS;k++) {
        struct service_product *p=&s->products[k];char name[256];
        json_quote(name,sizeof name,p->n?L->items[p->ids[0]].name:"");
        at+=(size_t)snprintf(rows+at,sizeof rows-at,"%s{\"bItemRegistered\":%s,\"ProductID\":%d,\"Desc\":\"Click to register items\",\"ItemName\":%s,\"ProductType\":\"%s\",\"ItemCount\":\"%d\",\"PriceZen\":\"%u\",\"PriceBless\":\"%u\",\"PriceSoul\":\"%u\"}",
            k?",":"",p->n?"true":"false",k,name,p->n>1?"Bundle":"Single",p->n,p->price[0],p->price[1],p->price[2]);
    }
    invokef(L,mv->id,mv->path,"SetProductInfoList","[[%s]]",rows);
}
static void service_register(mu_gfx_layer *L)
{
    struct item_services *s=&L->services;movie *mv=&L->mv[MU_GFX_STORE_REGISTER];
    invokef(L,mv->id,mv->path,"SetText","[{\"SingleItem\":\"Single item\",\"Bundle\":\"Bundle\",\"Desc\":\"Click inventory items to register. Offline demo only.\",\"Confirm\":\"Set a price, then Register.\",\"OkButton\":\"Register\",\"CancelButton\":\"Cancel\"}]");
    invokef(L,mv->id,mv->path,"SetState","[{\"State\":%d,\"CancelLabel\":\"%s\"}]",s->products[s->selected].n?1:0,s->products[s->selected].n?"Remove listing":"Cancel");
    invokef(L,mv->id,mv->path,"SetProductType","[%d]",s->bundle);
    invokef(L,mv->id,mv->path,"SetSlotCount","[%d]",s->bundle?5:1);
    invokef(L,mv->id,mv->path,"SetJewelPriceEnabled","[{\"EnabledPriceBless\":true,\"EnabledPriceSoul\":true}]");
    invokef(L,mv->id,mv->path,"SetPurchasePrice","[{\"Zen\":%u,\"Bless\":%u,\"Soul\":%u}]",s->draft.price[0],s->draft.price[1],s->draft.price[2]);
    char names[512]="",q[1100];size_t at=0;
    for(int j=0;j<s->draft.n;j++)at+=(size_t)snprintf(names+at,sizeof names-at,"%s%s +%d",j?", ":"Selected: ",L->items[s->draft.ids[j]].name,L->items[s->draft.ids[j]].level);
    json_quote(q,sizeof q,names[0]?names:"Click an item in your inventory.");
    /* The movie's description is plain text; no invented movie method. */
    char path[192];snprintf(path,sizeof path,"%s.taDescription.text",mv->path);
    if(L->api.set_variable)L->api.set_variable(mv->g,path,q);
}
static int service_inventory(mu_gfx_layer *L,int cell)
{
    struct item_services *s=&L->services;
    if(s->repair_mode) {
        mu_gfx_layer_service_action(L,"repair",cell,0);return 1;
    }
    if(s->draft_active) {
        mu_gfx_layer_service_action(L,"storeput",cell,0);return 1;
    }
    return 0;
}
static void service_tooltip(mu_gfx_layer *L,item *it,char *html,size_t cap)
{
    struct item_services *s=&L->services;
    if(!s->repair_mode || !L->cfg.repair_quote)return;
    int npc=L->mv[MU_GFX_NPC_SHOP].open && s->npc_repair;
    int32_t cost=0,max=0;mu_mix_item snap=mix_snapshot(it);
    int allowed=L->cfg.repair_quote(L->cfg.tooltip_user,&snap,npc,&cost,&max);
    size_t n=strlen(html);
    if(allowed) {
        if(L->cfg.tooltip_snapshot)snprintf(html+n,cap-n,"<br>Repair: %d Zen",cost);
        else snprintf(html+n,cap-n,"<br>Durability: %d/%d<br>Repair: %d Zen",it->durability,max,cost);
    }
    else snprintf(html+n,cap-n,"<br>Repair unavailable or durability full.");
}
static int service_start(mu_gfx_layer *L,int kind)
{
    L->services.pending=kind;L->services.due=L->time_ms+160;
    npc_last(L,"Item service request %d; waiting for offline demo answer",kind);
    hide_tooltip(L);return 1;
}
static int service_repair(mu_gfx_layer *L,int cell)
{
    struct item_services *s=&L->services;
    int npc=L->mv[MU_GFX_NPC_SHOP].open && s->npc_repair;
    if(!L->cfg.repair_quote || (L->mv[MU_GFX_NPC_SHOP].open && !npc) || L->held>=0)return 0;
    s->nrepair=0;s->cost=0;
    for(int k=0;k<L->grid.item_count;k++) {
        item *it=(item *)L->grid.items[k];int index=(int)(it-L->items);
        if(cell>=0 && mu_grid_item_at(&L->grid,cell)!=&it->grid)continue;
        if(item_reserved(L,index))continue;
        int32_t cost=0,max=0;mu_mix_item snap=mix_snapshot(it);
        if(!L->cfg.repair_quote(L->cfg.tooltip_user,&snap,npc,&cost,&max) || cost<0 || max<1 || max>255)continue;
        s->repair_ids[s->nrepair]=index;s->repair_max[s->nrepair++]=max;s->cost+=cost;
    }
    if(!s->nrepair || s->cost>L->hero.zen || s->cost>2000000000)return 0;
    if(L->cfg.repair_request)L->cfg.repair_request(L->cfg.tooltip_user,cell,npc);
    npc_last(L,"Repair quote: %lld Zen for %d item(s)",(long long)s->cost,s->nrepair);
    return service_start(L,1);
}
static void service_step(mu_gfx_layer *L)
{
    struct item_services *s=&L->services;
    if(!s->pending || L->time_ms<s->due)return;
    int kind=s->pending;s->pending=0;
    if(!s->outcome) { npc_last(L,"Item service rejected by offline demo server; inventory and zen unchanged");return; }
    if(kind==1) {
        for(int k=0;k<s->nrepair;k++)L->items[s->repair_ids[k]].durability=s->repair_max[k];
        L->hero.zen-=s->cost;
    } else if(kind==2)s->shop_open=1;
    else if(kind==3)s->shop_open=0;
    else if(kind==4) {
        /* Sample remote offer is a single, nonstacked potion at 1,000 zen.
         * Space and money are checked again before either changes. */
        if(L->hero.zen<1000 || mu_gfx_layer_add_item(L,7171,0,1,1,"Demo healing potion")<0) {
            npc_last(L,"Purchase rejected: inventory full or insufficient zen");return;
        }
        L->hero.zen-=1000;
        mu_gfx_layer_show(L,MU_GFX_STORE_PURCHASE,0);
    } else if(kind==5) {
        struct service_product *p=&s->products[s->request_product];
        for(int k=0;k<p->n;k++){mu_grid_remove(&L->grid,&L->items[p->ids[k]].grid);L->items[p->ids[k]].grid.code=-1;}
        L->hero.zen+=p->price[0];memset(p,0,sizeof *p);
    }
    zen_text(L);slot_states(L);hide_tooltip(L);service_list(L);
    npc_last(L,"Item service %d accepted (offline demo answer)",kind);
}
void mu_gfx_layer_service_state(const mu_gfx_layer *L,int *pending,int *opened,int *products,int *draft)
{
    if(pending)*pending=L?L->services.pending:0;
    if(opened)*opened=L?L->services.shop_open:0;
    if(products){*products=0;for(int k=0;L && k<SERVICE_PRODUCTS;k++)*products+=L->services.products[k].n!=0;}
    if(draft)*draft=L && L->services.draft_active?L->services.draft.n:0;
}
int mu_gfx_layer_service_action(mu_gfx_layer *L,const char *verb,int a,int b)
{
    if(!L || !verb || inventory_busy(L))return 0;
    struct item_services *s=&L->services;
    if(!strcmp(verb,"serviceresult")) { if(a<0 || a>1)return 0;s->outcome=a;return 1; }
    if(!strcmp(verb,"repairmode") || !strcmp(verb,"selfrepair")) {
        if(L->held>=0 || L->mv[MU_GFX_MIX].open || s->draft_active)return 0;
        if(!strcmp(verb,"repairmode") && (!L->mv[MU_GFX_NPC_SHOP].open || !s->npc_repair))return 0;
        if(!strcmp(verb,"selfrepair") && L->mv[MU_GFX_NPC_SHOP].open)return 0;
        s->repair_mode=!s->repair_mode;
        invokef(L,MU_GFX_INVENTORY,L->mv[MU_GFX_INVENTORY].path,"SetRepairMode","[%s]",s->repair_mode?"true":"false");return 1;
    }
    if(!strcmp(verb,"repair") || !strcmp(verb,"repairall")) {
        if(L->mv[MU_GFX_MIX].open || L->mv[MU_GFX_TRADE].open || s->draft_active)return 0;
        if(!strcmp(verb,"repair") && (a<0 || a>=64))return 0;
        return service_repair(L,!strcmp(verb,"repairall")?-1:a);
    }
    if(!strcmp(verb,"damage")) {
        /* Explicit offline fixture, never sent to a real server. */
        if(a<0 || a>=64 || b<0 || b>255)return 0;
        item *it=(item *)mu_grid_item_at(&L->grid,a);
        if(!it || item_reserved(L,(int)(it-L->items)))return 0;
        it->durability=b;return 1;
    }
    if(!strcmp(verb,"store") || !strcmp(verb,"storebrowse")) {
        if(!L->mv[MU_GFX_STORE_LIST].g || L->held>=0 || L->mv[MU_GFX_TRADE].open || L->mv[MU_GFX_MIX].open)return 0;
        s->browsing=!strcmp(verb,"storebrowse");s->repair_mode=0;
        invokef(L,MU_GFX_INVENTORY,L->mv[MU_GFX_INVENTORY].path,"SetRepairMode","[false]");
        mu_gfx_layer_npc_close(L);mu_gfx_layer_show(L,MU_GFX_STORE_REGISTER,0);
        if(!s->title[0])snprintf(s->title,sizeof s->title,"My demo store");
        service_list(L);mu_gfx_layer_show(L,MU_GFX_STORE_LIST,1);mu_gfx_layer_show(L,MU_GFX_INVENTORY,1);return 1;
    }
    if(!strcmp(verb,"storebuy")) {
        if(!s->browsing || !L->mv[MU_GFX_STORE_PURCHASE].open || L->held>=0 || L->hero.zen<1000)return 0;
        return service_start(L,4);
    }
    if(!strcmp(verb,"storepurchase")) {
        if(!s->browsing || !L->mv[MU_GFX_STORE_LIST].open || a!=0 || !L->mv[MU_GFX_STORE_PURCHASE].g)return 0;
        movie *mv=&L->mv[MU_GFX_STORE_PURCHASE];
        invokef(L,mv->id,mv->path,"SetText","[{\"Desc\":\"Demo healing potion\",\"Confirm\":\"Buy from offline demo trader?\",\"OkButton\":\"Buy\",\"CancelButton\":\"Cancel\"}]");
        invokef(L,mv->id,mv->path,"SetSlotCount","[1]");
        invokef(L,mv->id,mv->path,"SetPurchasePrice","[{\"Zen\":1000,\"Bless\":0,\"Soul\":0}]");
        mu_gfx_layer_show(L,mv->id,1);return 1;
    }
    if(!strcmp(verb,"storeopen") || !strcmp(verb,"storeclose")) {
        if(s->browsing || s->draft_active || L->held>=0)return 0;
        int open=!strcmp(verb,"storeopen");if(open==s->shop_open)return 0;
        int n=0;for(int k=0;k<SERVICE_PRODUCTS;k++)n+=s->products[k].n;
        if(open && !n)return 0;
        return service_start(L,open?2:3);
    }
    if(!strcmp(verb,"storesale")) {
        if(!s->shop_open || a<0 || a>=SERVICE_PRODUCTS || !s->products[a].n)return 0;
        struct service_product *p=&s->products[a];
        /* Jewel settlement awaits a server currency feed; never silently
         * turn a mixed-currency price into a zen-only transaction. */
        if(p->price[1] || p->price[2] || L->hero.zen>2000000000-(int64_t)p->price[0])return 0;
        s->request_product=a;return service_start(L,5);
    }
    if(s->browsing || s->shop_open)return 0;
    if(!strcmp(verb,"storereg")) {
        if(a<0 || a>=SERVICE_PRODUCTS || !L->mv[MU_GFX_STORE_LIST].open || !L->mv[MU_GFX_STORE_REGISTER].g || L->held>=0)return 0;
        s->selected=a;s->draft=s->products[a];s->draft_active=1;s->bundle=s->draft.n>1;
        service_register(L);mu_gfx_layer_show(L,MU_GFX_STORE_REGISTER,1);return 1;
    }
    if(!strcmp(verb,"storeunlist")) {
        if(a<0 || a>=SERVICE_PRODUCTS || s->draft_active)return 0;
        memset(&s->products[a],0,sizeof s->products[a]);service_list(L);return 1;
    }
    if(!s->draft_active)return 0;
    if(!strcmp(verb,"storeremove")) {
        memset(&s->products[s->selected],0,sizeof s->products[s->selected]);
        mu_gfx_layer_show(L,MU_GFX_STORE_REGISTER,0);service_list(L);return 1;
    }
    if(!strcmp(verb,"storecancel")) { mu_gfx_layer_show(L,MU_GFX_STORE_REGISTER,0);return 1; }
    if(!strcmp(verb,"storebundle")) {
        if(a!=0 && a!=1)return 0;
        if(!a && s->draft.n>1)return 0;
        s->bundle=a;service_register(L);return 1;
    }
    if(!strcmp(verb,"storeprice")) {
        if(a<0 || a>2 || b<0 || b>(a?9999:999999999))return 0;
        s->draft.price[a]=(uint32_t)b;service_register(L);return 1;
    }
    if(!strcmp(verb,"storeput")) {
        if(a<0 || a>=64 || L->held>=0 || s->draft.n>=(s->bundle?5:1))return 0;
        item *it=(item *)mu_grid_item_at(&L->grid,a);if(!it)return 0;
        int index=(int)(it-L->items);if(item_reserved(L,index))return 0;
        mu_mix_item snap=mix_snapshot(it);
        if(!L->cfg.store_check || !L->cfg.store_check(L->cfg.tooltip_user,&snap))return 0;
        s->draft.ids[s->draft.n++]=index;service_register(L);return 1;
    }
    if(!strcmp(verb,"storeconfirm")) {
        if(!s->draft.n || (!s->draft.price[0] && !s->draft.price[1] && !s->draft.price[2]))return 0;
        s->products[s->selected]=s->draft;s->draft_active=0;
        mu_gfx_layer_show(L,MU_GFX_STORE_REGISTER,0);service_list(L);return 1;
    }
    return 0;
}
static void service_call(movie *mv,const char *name,const char *args,const double *v,int n)
{
    mu_gfx_layer *L=mv->L;struct item_services *s=&L->services;
    if(!strcmp(name,"SetSlotUIInfo") && n>=5 && mv->id>=MU_GFX_STORE_REGISTER) {
        int w=mv->id-MU_GFX_STORE_REGISTER,k=(int)v[0];
        if(w>=0 && w<2 && k>=0 && k<5 && v[3]>0 && v[4]>0) {
            for(int j=0;j<4;j++)s->slots[w][k][j]=(float)v[j+1];s->have_slot[w][k]=1;
        }
        return;
    }
    if(!strncmp(name,"Product_requestItemSlot",23) && n>=1 && s->draft_active) {
        int k=(int)v[0];
        if(k>=0 && k<s->draft.n) {
            if(!strcmp(name,"Product_requestItemSlotClickR") && !inventory_busy(L)) {
                for(int j=k+1;j<s->draft.n;j++)s->draft.ids[j-1]=s->draft.ids[j];
                s->draft.n--;service_register(L);
            } else if(!strcmp(name,"Product_requestItemSlotOver")) {
                item *it=&L->items[s->draft.ids[k]];show_item_tooltip(L,it->grid.row*8+it->grid.col);
            } else if(!strcmp(name,"Product_requestItemSlotOut"))hide_tooltip(L);
        }
        return;
    }
    if(mv->id==MU_GFX_STORE_LIST) {
        if(!strcmp(name,"OnClickProduct") && n>=1)mu_gfx_layer_service_action(L,s->browsing?"storepurchase":"storereg",(int)v[0],0);
        else if(!strcmp(name,"OnClickOpenShop"))mu_gfx_layer_service_action(L,"storeopen",0,0);
        else if(!strcmp(name,"OnClickCloseShop"))mu_gfx_layer_service_action(L,"storeclose",0,0);
        else if(!strcmp(name,"OnShopTitleChanged") && !inventory_busy(L) && !s->shop_open && !s->browsing)
            json_string_decoded(args,0,s->title,45);
    } else if(mv->id==MU_GFX_STORE_REGISTER) {
        if(!strcmp(name,"OnClickProductType") && n>=1)mu_gfx_layer_service_action(L,"storebundle",(int)v[0],0);
        else if(!strcmp(name,"OnClickCancel"))mu_gfx_layer_service_action(L,s->products[s->selected].n?"storeremove":"storecancel",0,0);
        else if(!strcmp(name,"OnClickOk") && n>=3 && !inventory_busy(L)) {
            /* Validate all currencies together before updating the draft. */
            if(!isfinite(v[0]) || !isfinite(v[1]) || !isfinite(v[2]) || v[0]<0 || v[0]>999999999 || v[1]<0 || v[1]>9999 || v[2]<0 || v[2]>9999)return;
            for(int j=0;j<3;j++)if(v[j]!=floor(v[j]))return;
            for(int j=0;j<3;j++)s->draft.price[j]=(uint32_t)v[j];
            mu_gfx_layer_service_action(L,"storeconfirm",0,0);
        }
    } else if(mv->id==MU_GFX_STORE_PURCHASE) {
        if(!strcmp(name,"OnClickOk"))mu_gfx_layer_service_action(L,"storebuy",0,0);
        else if(!strcmp(name,"OnClickCancel"))mu_gfx_layer_show(L,mv->id,0);
    }
}

static int service_draws(mu_gfx_layer *L,int m,mu_gfx_item_draw *out,int max)
{
    if(m<MU_GFX_STORE_REGISTER || m>MU_GFX_STORE_PURCHASE || !L->mv[m].open)return 0;
    int w=m-MU_GFX_STORE_REGISTER,n=0;struct item_services *s=&L->services;
    int count=w?1:(s->draft_active?s->draft.n:0);
    float sc=L->applied_scale[m];if(sc<=0)sc=1;
    for(int k=0;k<count && n<max;k++) {
        if(!s->have_slot[w][k])continue;
        item *it=w?NULL:&L->items[s->draft.ids[k]];
        mu_gfx_item_draw *d=&out[n++];memset(d,0,sizeof *d);
        d->code=it?it->grid.code:7171;d->level=it?it->level:0;d->excellent=it?it->excellent:0;
        d->item=it?s->draft.ids[k]:-1;d->alpha=1;d->frame_scale=sc;
        float *r=s->slots[w][k];
        d->rect[0]=L->mv[m].win_x+r[0]*sc;d->rect[1]=L->mv[m].win_y+r[1]*sc;
        d->rect[2]=r[2]*sc;d->rect[3]=r[3]*sc;
        for(int j=0;j<4;j++)d->slot[j]=d->rect[j]*(j%2?480.0f/(float)L->h:640.0f/(float)L->w);
    }
    return n;
}
