/* SESSION-CORE-001 (sketch): the changed boundary in native/client/shell.c and main.c.
 *
 * The verified scene manager (reconstructed/scene) is unchanged: it still emits call
 * records by client routine address and reads/writes client-shaped records. What changes is
 * who answers: every network-shaped host call now goes to the session, and every record the
 * scene code reads (protocol state, CharactersClient lookup, Hero class) is filled FROM the
 * session at the same points. offline-session.{c,h} and demo-*.txt leave the client and
 * become native/fixture/behaviors/account.c and fixture scenarios.
 *
 * struct mu_shell changes:
 *   - mu_offline_session session;           removed
 *   + mu_session *session;                  one per login; NULL in scenes 2 and before connect
 *   + mu_session_config session_cfg;        endpoint, transport, build, proof (from mu_shell_config)
 *   - int join_answer; hero_class; hero_level;   derived from the session instead
 *   + uint32_t last_routine;                the previous call record (splits MU_SCENE_NET_SEND)
 *   - mu_world_embed *world;                replaced by mu_world_rt *world
 */

/* ---- host_call: the network-shaped cases ------------------------------------------------- */

static uint32_t host_call_session(mu_shell *s, const mu_scenemgr_call *c)
{
    switch (c->routine) {
    case 0x0121c055u:   /* connect(server_address, port) in the login creation (scene.c:194) */
        /* g.server_address is no longer a fake handle with port 0: the endpoint comes from the
         * shell config (settings / operator contract), so the record the scene passes is informational */
        if (!s->session)
            s->session = mu_session_open(&s->session_cfg, s->status, sizeof s->status);
        return s->session != NULL;
    case 0x00988d22u: { /* the character-list request */
        mu_intent in = {.kind = MU_INTENT_REQUEST_CHARACTERS};
        mu_session_submit(s->session, &in);
        return 0;
    }
    case 0x009a13f4u: { /* CharactersClient lookup of SelectedHero: the same pokes as today, from the session */
        const mu_charsel_entry *e = mu_session_character(s->session, (int32_t)c->args[0]);
        if (!e)
            return 0;
        /* TODO: memset record_mem; poke H_RECORD+0x12 class, +0x13/+0x14 flags, +0x144 level, +0x44 name */
        return H_RECORD;
    }
    case MU_SCENE_NET_SEND:
        /* One record id, two client sends. The scene number cannot tell them apart: the tail
         * (scene.c:125-127) is emitted in EVERY scene once SendCounter > 31, so a tail in scene 5
         * would be taken for a join. The preceding call record can: the join follows the
         * CharactersClient lookup 0x009a13f4 (scene.c:256-260), the tail follows the observer
         * notify 0x00ac9be9 (scene.c:124). reconstructed/scene stays unchanged; the 7,000 scene
         * cases are rerun to show it. */
        if (s->last_routine == 0x009a13f4u) {
            mu_intent in = {.kind = MU_INTENT_JOIN, .u.join = {.slot = s->g.selected_hero}};
            mu_session_submit(s->session, &in);   /* a second Enter while JOINING is NOT_NOW */
        } else if (s->last_routine == 0x00ac9be9u) {
            mu_intent in = {.kind = MU_INTENT_KEEPALIVE};
            mu_session_submit(s->session, &in);   /* UNRECOVERED until NET-ACCOUNT-001: journaled */
        } else {
            MU_NOT_IMPLEMENTED();                 /* a third emit site would be a scene-manager change */
        }
        return 0;
    default:
        return host_call_local(s, c);             /* the existing non-network cases, unchanged */
    }
}
/* host_call (the caller of host_call_session) records c->routine into s->last_routine after
 * every call, network-shaped or not. */

/* ---- the scene frames read the session ----------------------------------------------------- */

static void shell_sync_from_session(mu_shell *s)
{
    /* Runs at the start of every mu_shell_frame, after mu_session_pump. Derives, never stores:
     *   s->g.protocol = status.protocol_state            (the verified scene code reads 0x06fca2c4)
     *   scene 3: server window shown when phase >= SERVER_LIST (servers rev changed -> rebuild rows)
     *            account dialog (GFx, later) shown when phase == ACCOUNT
     *   scene 5: when phase == IN_WORLD and the scene is waiting: mu_scenemgr_start_loading(&host, &g, 1)
     *            Hero class for the loading/world: attr +0x187 from mu_session_hero (was peek(H_HERO+0x187))
     *   phase CLOSED: show the reason (login refused / outdated / needs operator contract / lost),
     *            close the session, return to scene 3 (a new session on the next connect)
     */
    (void)s;
    MU_NOT_IMPLEMENTED();
}

static void choose_server(mu_shell *s, int32_t group, int32_t slot)
{
    mu_intent in = {.kind = MU_INTENT_CHOOSE_SERVER, .u.choose_server = {group, slot}};
    mu_session_submit(s->session, &in);
}

static void login_accept(mu_shell *s, const char *account, const char *password)
{
    /* The placeholder panel today, the GFx account dialog's onLoginOkClick later (GFX-ACCOUNT-001). */
    mu_intent in = {.kind = MU_INTENT_LOGIN};
    /* TODO: strlcpy(in.u.login.account, account, ...); mu_secret_set(&in.u.login.password, password); */
    mu_session_submit(s->session, &in);           /* wipes the secret */
    (void)account; (void)password;
}

static void open_world(mu_shell *s)
{
    /* Scene 4 -> 6. No join table, no feature flags: the runtime opens on mu_session_place(). */
    /* TODO: s->world = mu_world_rt_open(s->session, &s->assets, &s->world_options, err, sizeof err); */
    (void)s;
}

/* ---- the front-end loop (client/main.c) ------------------------------------------------------
 *
 *   for (;;) {
 *       now = clock_ms();                          // before the pump, as the client's idle loop
 *       mu_transport_poll(transport, now);         // bytes in; applies nothing
 *       pump_sdl(shell);                           // SDL -> mu_input_msg -> mu_shell_input:
 *                                                  //   scene 6: mu_world_rt_input (GFx first refusal inside)
 *                                                  //   scenes 3/5: shell windows -> intents
 *       mu_shell_frame(shell, now);                // mu_session_pump at the client's queue-drain point,
 *                                                  // shell_sync_from_session, mu_scenemgr_dispatch, frames
 *       compose(shell);                            // 3D + GFx + 2D; views read const state
 *       mu_transport_flush(transport);             // bytes out
 *       present; audio; sleep(mu_shell_end_frame(shell));
 *   }
 *
 * world_gfx is no longer opened by client/main.c's on_opened/on_closing: it is the runtime's gfx
 * part, and the inventory/quests/HUD it shows come from the session, so nothing resets on the way
 * back to character select.
 */
