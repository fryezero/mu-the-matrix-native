/* SESSION-CORE-001 (sketch): lifecycle, pump, barrier, submit, cues, lease. */
#include "session_internal.h"

mu_session *mu_session_open(const mu_session_config *cfg, char *error, size_t error_size)
{
    /* TODO
     *   s = calloc; s->cfg = *cfg; waiting_world = -1; held.frames = malloc(MU_HELD_FRAMES)
     *   mu_net_init(&s->net, cfg->transport)
     *   each domain's init (generated: MU_DOMAIN(name) -> mu_dom_<name>_init(s, &s->name))
     *   mu_net_connect(&s->net, MU_CONN_CONNECT, &cfg->connect_server)   -> phase CONNECTING
     *   journal "open" (endpoint, build sha; never credentials)
     */
    (void)cfg; (void)error; (void)error_size;
    MU_NOT_IMPLEMENTED();
}

void mu_session_close(mu_session *s)
{
    /* TODO: domain frees (generated), mu_net_free, free(held.frames), free(s). No bytes are sent:
     * an orderly logout is the LOGOUT intent, answered before the caller closes. */
    (void)s;
    MU_NOT_IMPLEMENTED();
}

void mu_session_pump(mu_session *s, uint32_t now_ms)
{
    /* TODO
     *   s->now = now_ms; s->pumping = 1
     *   for each connection kind k in MU_CONN_CONNECT, MU_CONN_GAME, MU_CONN_CHAT (fixed order):
     *       link state changes -> phase transitions (CONNECTING->wait list, HOPPING->ACCOUNT,
     *                             CLOSED -> MU_CLOSE_NET_LOST unless a hop closed it on purpose)
     *       while mu_net_next(&s->net, k, &frame, &status):
     *           status != OK          -> close with DECRYPT_ERROR / RECEIVE_OVERFLOW, stop (client behaviour)
     *           journal(frame, inbound)
     *           if s->waiting_world >= 0: hold(frame); continue          // barrier: keep arrival order
     *           r = mu_session_dispatch(s, &frame); s->frames_in++
     *           if r == MU_APPLY_WORLD_CHANGE: s->waiting_world = place.world
     *   s->pumping = 0
     *
     * Order across connections: the client receives each socket through its own window message
     * and queues frames in one packet queue (0x01291777) in arrival order. A pump cannot see the
     * cross-socket arrival order; it uses the fixed order above. Only the chat server can
     * interleave with the game server in practice, and their domains are disjoint (rooms vs
     * everything else), so the order is unobservable in state. Recorded as an assumption.
     */
    (void)s; (void)now_ms;
    MU_NOT_IMPLEMENTED();
}

void mu_session_attach_world(mu_session *s, const mu_world_port *port)
{
    /* TODO
     *   if has_port && port->world == s->port.world && waiting_world < 0: return    // idempotent
     *   s->port = *port; s->has_port = 1
     *   if waiting_world == port->world:
     *       waiting_world = -1
     *       drain held frames through mu_session_dispatch in order; a second WORLD_CHANGE among
     *       them sets the barrier again and the rest stay held (teleport chains)
     */
    (void)s; (void)port;
    MU_NOT_IMPLEMENTED();
}

void mu_session_detach_world(mu_session *s)
{
    (void)s;
    MU_NOT_IMPLEMENTED();   /* has_port = 0; viewport entries keep their records (the client keeps CharactersClient) */
}

extern const mu_submit_fn mu_session_submit_routes[MU_INTENT_KINDS];

mu_submit mu_session_submit(mu_session *s, const mu_intent *in)
{
    /* TODO
     *   assert(!s->pumping)                  // views never submit from inside apply
     *   if phase == CLOSED: NOT_NOW
     *   fn = mu_session_submit_routes[in->kind]   // every kind has exactly one owning domain
     *   r = fn(s, in)                         // local checks, reconstructed builder, mu_session_send
     *   journal(intent kind, r.status)        // never the payload of LOGIN / DELETE (mu_secret)
     *   return r
     */
    (void)s; (void)in;
    MU_NOT_IMPLEMENTED();
}

size_t mu_session_cues(const mu_session *s, mu_cue_cursor *cursor, mu_cue *out, size_t cap, uint32_t *lost)
{
    /* TODO
     *   oldest = next_seq > MU_CUE_RING ? next_seq - MU_CUE_RING : 0
     *   if cursor->next < oldest: *lost = oldest - cursor->next; cursor->next = oldest
     *   copy while cursor->next < next_seq && n < cap
     */
    (void)s; (void)cursor; (void)out; (void)cap; (void)lost;
    MU_NOT_IMPLEMENTED();
}

mu_sim mu_session_sim_begin(mu_session *s)
{
    /* TODO
     *   assert(!s->sim_open && !s->pumping)
     *   sim_open = 1; ++sim_epoch
     *   #ifdef MU_SESSION_AUDIT: snapshot the replicated fields of every used viewport record and
     *     ground item (key, class, equipment slots, hp, name, item data; the field list is
     *     domains/viewport.c's REPLICATED[] table, the same table the journal's record dump uses)
     *   return {viewport.chars, viewport.used, MU_VIEWPORT_MAX, viewport.hero_index, ground.items, ...}
     */
    (void)s;
    MU_NOT_IMPLEMENTED();
}

void mu_session_sim_end(mu_session *s, const mu_sim *sim)
{
    /* TODO: assert(sim->epoch == sim_epoch); MU_SESSION_AUDIT: compare snapshot, abort naming the
     * field on a difference; sim_open = 0; touch MU_DOMAIN_VIEWPORT only for creates/deletes the
     * tick made (the dead-fade removal), not for motion (motion has no revision: it changes
     * every tick and renderers read it every frame anyway) */
    (void)s; (void)sim;
    MU_NOT_IMPLEMENTED();
}

void mu_session_status_get(const mu_session *s, mu_session_status *out)
{
    /* protocol_state is derived here and nowhere else:
     *   LOGGED_IN -> 0x14; CHARACTERS and later -> 0x33; earlier phases -> 0
     *   TODO(NET-ACCOUNT-001): confirm the client's values per F1 01 / list arrival */
    (void)s; (void)out;
    MU_NOT_IMPLEMENTED();
}
