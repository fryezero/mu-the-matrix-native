/* UI-WINDOWS-006. MapName (manager +0x128): the arrival banner.
 * Open method 0x00baee4a: nothing in world 0x28; InitText; lifetime timer
 * start; SetMapName(map-name function 0x016baaa6); SetStrife only when the
 * strife predicate 0x016bec9f holds; SetOccupyGuild only for a non-empty
 * occupying guild; base open. Update 0x00baf120 closes it once 5000 ms (the
 * double at 0x01a90948) have passed. The strife predicate depends on a
 * server-mode flag and the guild on a server answer: this provider leaves
 * both as InitText clears them. No sound, request or session owner. */
#define MAP_BANNER_LIFETIME_MS 5000.0

/* Registration 0x00ac8ade puts it in group 3 with InfoPopup: no pointer, Esc
 * or NPC close-all ownership is claimed for it. */
static int presentation_overlay6(int m)
{
    return m==MU_GFX_MAP_NAME;
}

static int map_banner_open(mu_gfx_layer *L, const char *name)
{
    movie *w=&L->mv[MU_GFX_MAP_NAME];
    char q[160];
    invokef(L,w->id,w->path,"InitText","[]");
    L->map_banner_start_ms=L->time_ms;            /* 0x00baee94 */
    logf_(L,"%s lifetime timer start",w->file);
    json_quote(q,sizeof q,name);
    invokef(L,w->id,w->path,"SetMapName","[%s]",q);
    mu_gfx_layer_show(L,w->id,1);                 /* 0x00baf0e2 */
    return 1;
}

int mu_gfx_layer_map_arrival(mu_gfx_layer *L, int kind, int number, int world, const char *name)
{
    if(!L || !L->mv[MU_GFX_MAP_NAME].g || !name || !name[0]) return 0;
    if(kind!=MU_GFX_ARRIVAL_JOIN && kind!=MU_GFX_ARRIVAL_RESPAWN && kind!=MU_GFX_ARRIVAL_TELEPORT) return 0;
    /* Teleport tail 0x01281e6e..0x01281eab: numbered answers only. */
    if(kind==MU_GFX_ARRIVAL_TELEPORT && !number) return 0;
    if(world==0x28) return 0;                     /* open method, 0x00baee6b */
    if(!presentation_available3(L,MU_GFX_MAP_NAME)) {
        /* Native load order: the offline join precedes the movie's UIInit.
         * The latest arrival is held and opens on the first ready frame. */
        L->map_banner_pending=1;
        snprintf(L->map_banner_name,sizeof L->map_banner_name,"%s",name);
        return 1;
    }
    L->map_banner_pending=0;
    return map_banner_open(L,name);
}

static void presentation_tick6(mu_gfx_layer *L)
{
    movie *w=&L->mv[MU_GFX_MAP_NAME];
    if(L->map_banner_pending && presentation_available3(L,MU_GFX_MAP_NAME)) {
        L->map_banner_pending=0;
        map_banner_open(L,L->map_banner_name);
        return;
    }
    /* 0x00baf120: loaded and open, elapsed >= 5000 ms: restart, close. */
    if(w->g && w->open && L->time_ms-L->map_banner_start_ms>=MAP_BANNER_LIFETIME_MS) {
        L->map_banner_start_ms=L->time_ms;
        mu_gfx_layer_show(L,w->id,0);
    }
}

/* The movie has no button or request. Only layout metadata is consumed. */
static int presentation_call6(movie *w, const char *name)
{
    if(w->id!=MU_GFX_MAP_NAME) return -1;
    return !strcmp(name,"TweenTimeSet") || !strcmp(name,"requestWindowPos");
}
