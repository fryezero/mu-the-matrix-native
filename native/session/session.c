/* SESSION-CORE-001: lifecycle, pump, barrier, submit, revisions, status, the world port. */
#include "session_internal.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_lang.h"

const mu_client_build MU_PINNED_BUILD = {
    "3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a", {0}, {0}};

static mu_proof_status proof_not_required(void *user, uint32_t field_tag, mu_login_proof *out)
{
    (void)user;
    (void)field_tag;
    out->length = 0;
    return MU_PROOF_NOT_REQUIRED;
}

static mu_proof_status proof_unavailable(void *user, uint32_t field_tag, mu_login_proof *out)
{
    (void)user;
    (void)field_tag;
    out->length = 0;
    return MU_PROOF_UNAVAILABLE;
}

static const mu_login_proof_source PROOF_NOT_REQUIRED = {NULL, proof_not_required};
static const mu_login_proof_source PROOF_UNAVAILABLE = {NULL, proof_unavailable};
const mu_login_proof_source *mu_proof_not_required(void) { return &PROOF_NOT_REQUIRED; }
const mu_login_proof_source *mu_proof_unavailable(void) { return &PROOF_UNAVAILABLE; }

void mu_secret_set(mu_secret *s, const char *utf8)
{
    memset(s, 0, sizeof *s);
    size_t n = utf8 ? strlen(utf8) : 0;
    if (n > sizeof s->opaque_)
        n = sizeof s->opaque_;
    memcpy(s->opaque_, utf8, n);
    s->length_ = (uint8_t)n;
}

void mu_secret_wipe(mu_secret *s)
{
    volatile uint8_t *p = (volatile uint8_t *)s;
    for (size_t i = 0; i < sizeof *s; ++i)
        p[i] = 0;
}

static const char *const KIND_NAMES[] = MU_INTENT_KIND_NAMES;

const char *mu_intent_kind_name(mu_intent_kind kind)
{
    return (int)kind >= 0 && (size_t)kind < sizeof KIND_NAMES / sizeof KIND_NAMES[0] ? KIND_NAMES[kind] : "?";
}

mu_intent_kind mu_intent_kind_by_name(const char *name)
{
    for (size_t i = 1; name && i < sizeof KIND_NAMES / sizeof KIND_NAMES[0]; ++i)
        if (!strcmp(KIND_NAMES[i], name))
            return (mu_intent_kind)i;
    return MU_INTENT_NONE;
}

static const char *const DOMAIN_NAMES[] = MU_DOMAIN_NAMES;

const char *mu_domain_name(mu_domain d)
{
    return (int)d >= 0 && d < MU_DOMAIN_COUNT ? DOMAIN_NAMES[d] : "?";
}

const char *mu_phase_name(mu_phase p)
{
    static const char *const N[] = {"connecting", "server_list", "hopping", "account", "logging_in", "logged_in",
                                    "characters", "joining", "in_world", "leaving", "closed"};
    return (int)p >= 0 && (size_t)p < sizeof N / sizeof N[0] ? N[p] : "?";
}

const char *mu_close_reason_name(mu_close_reason r)
{
    static const char *const N[] = {"none", "logout", "net_refused", "net_lost", "receive_overflow", "decrypt_error",
                                    "login_refused", "client_outdated", "already_connected", "needs_operator_contract"};
    return (int)r >= 0 && (size_t)r < sizeof N / sizeof N[0] ? N[r] : "?";
}

const char *mu_submit_status_name(mu_submit_status st)
{
    static const char *const N[] = {"sent", "refused", "throttled", "not_now", "unrecovered"};
    return (int)st >= 0 && (size_t)st < sizeof N / sizeof N[0] ? N[st] : "?";
}

/* ---- lifecycle ---------------------------------------------------------------------------- */

static mu_session *session_new(const mu_session_config *cfg, char *error, size_t error_size)
{
    if (!cfg || !cfg->transport) {
        snprintf(error, error_size, "mu_session_open: no transport");
        return NULL;
    }
    mu_session *s = calloc(1, sizeof *s);
    if (!s) {
        snprintf(error, error_size, "mu_session_open: out of memory");
        return NULL;
    }
    s->cfg = *cfg;
    s->build = cfg->build ? cfg->build : &MU_PINNED_BUILD;
    s->waiting_world = -1;
    s->place.world = -1;
    s->conn_main = MU_CONN_CONNECT;
    if (mu_net_init(&s->net, cfg->transport, error, error_size) != 0) {
        free(s);
        return NULL;
    }
#define MU_DOMAIN(name) mu_dom_##name##_init(s);
#include "domains_all.def"
#undef MU_DOMAIN
    mu_journal_start(cfg->journal, s->build->main_exe_sha256);
    return s;
}

static void session_connect(mu_session *s, mu_conn_kind k)
{
    char text[400];
    snprintf(text, sizeof text, "open %s %s:%u build %s", k == MU_CONN_GAME ? "game" : "connect",
             s->cfg.connect_server.host, (unsigned)s->cfg.connect_server.port, s->build->main_exe_sha256);
    mu_journal_text(s->cfg.journal, MU_JNL_OPEN, s->tick, s->now, text);
    s->conn_main = k;
    if (mu_net_connect(&s->net, k, &s->cfg.connect_server) != 0)
        mu_session_fail(s, MU_CLOSE_NET_REFUSED, 0);
}

mu_session *mu_session_open(const mu_session_config *cfg, char *error, size_t error_size)
{
    mu_session *s = session_new(cfg, error, error_size);
    if (!s)
        return NULL;
    s->phase = MU_PHASE_CONNECTING;
    session_connect(s, MU_CONN_CONNECT);
    return s;
}

#ifdef MU_SESSION_SEED
#include "mu_session_seed.h"

mu_session *mu_session_open_seeded(const mu_session_config *cfg, const mu_session_seed *seed, char *error,
                                   size_t error_size)
{
    if (!seed) {
        snprintf(error, error_size, "mu_session_open_seeded: no seed");
        return NULL;
    }
    mu_session *s = session_new(cfg, error, error_size);
    if (!s)
        return NULL;
    session_connect(s, MU_CONN_GAME);
    if (s->phase == MU_PHASE_CLOSED)
        return s;
    mu_place place = seed->place;
    place.seq = 0;
    mu_session_set_place(s, &place);
#define MU_DOMAIN(name) mu_dom_##name##_seed(s, seed);
#include "domains_all.def"
#undef MU_DOMAIN
    mu_session_set_phase(s, MU_PHASE_IN_WORLD);
    return s;
}
#endif

void mu_session_close(mu_session *s)
{
    if (!s)
        return;
#define MU_DOMAIN(name) mu_dom_##name##_free(s);
#include "domains_all.def"
#undef MU_DOMAIN
    mu_journal_set_ticks(s->cfg.journal, s->tick);
    mu_net_free(&s->net);
    free(s->audit_snapshot);
    free(s);
}

/* ---- services ----------------------------------------------------------------------------- */

void mu_session_touch(mu_session *s, mu_domain d)
{
    if ((int)d >= 0 && d < MU_DOMAIN_COUNT)
        s->rev[d]++;
}

uint32_t mu_session_rev(const mu_session *s, mu_domain d)
{
    return s && (int)d >= 0 && d < MU_DOMAIN_COUNT ? s->rev[d] : 0;
}

void mu_session_set_phase(mu_session *s, mu_phase phase)
{
    if (s->phase == phase)
        return;
    char text[96];
    snprintf(text, sizeof text, "phase %s -> %s", mu_phase_name(s->phase), mu_phase_name(phase));
    mu_journal_text(s->cfg.journal, MU_JNL_EVENT, s->tick, s->now, text);
    s->phase = phase;
}

void mu_session_set_place(mu_session *s, const mu_place *place)
{
    uint32_t seq = s->place.seq + 1u;
    s->place = *place;
    s->place.seq = seq;
    char text[128];
    snprintf(text, sizeof text, "place world %d tile %d,%d angle %.1f seq %u", (int)place->world, (int)place->tile[0],
             (int)place->tile[1], (double)place->angle, (unsigned)seq);
    mu_journal_text(s->cfg.journal, MU_JNL_EVENT, s->tick, s->now, text);
}

mu_place mu_session_place(const mu_session *s)
{
    mu_place none = {-1, {0, 0}, 0.0f, 0};
    return s ? s->place : none;
}

void mu_session_fail(mu_session *s, mu_close_reason reason, int32_t code)
{
    if (s->phase == MU_PHASE_CLOSED)
        return;
    char text[96];
    snprintf(text, sizeof text, "close %s code %d", mu_close_reason_name(reason), (int)code);
    mu_journal_text(s->cfg.journal, MU_JNL_EVENT, s->tick, s->now, text);
    s->reason = reason;
    s->reason_code = code;
    s->phase = MU_PHASE_CLOSED;
    for (int k = 0; k < MU_CONN_KINDS; ++k)
        mu_net_close(&s->net, (mu_conn_kind)k);
}

const char *mu_session_global_text(const mu_session *s, int32_t index)
{
    const char *t = s->cfg.lang ? mu_lang_text(s->cfg.lang, index) : NULL;
    return t ? t : "";
}

void mu_session_hero_motion(const mu_session *s, int32_t tile[2], float position[3], float angle[3])
{
    if (s->has_port && s->port.hero_motion) {
        s->port.hero_motion(s->port.context, tile, position, angle);
        return;
    }
    /* no world: the server-acknowledged tile, the rest 0 */
    tile[0] = s->place.tile[0];
    tile[1] = s->place.tile[1];
    position[0] = position[1] = position[2] = 0.0f;
    angle[0] = angle[1] = angle[2] = 0.0f;
}

int mu_session_send(mu_session *s, mu_packet *p, int encrypted)
{
    mu_conn_kind k = s->conn_main;
    int rc = mu_net_send(&s->net, k, p, encrypted);
    uint32_t size = mu_packet_len(p);
    mu_journal_frame_out(s->cfg.journal, s->tick, s->now, k, &p->obj[2], size, rc, encrypted);
    if (rc == MU_SEND_OK)
        s->frames_out++;
    else
        s->unsent++;
    return rc;
}

mu_submit mu_session_unrecovered(mu_session *s, const mu_intent *in, const char *what)
{
    char text[160];
    snprintf(text, sizeof text, "unrecovered %s: %s", mu_intent_kind_name(in->kind), what);
    mu_journal_text(s->cfg.journal, MU_JNL_EVENT, s->tick, s->now, text);
    mu_submit r = {MU_SUBMIT_UNRECOVERED, -1};
    return r;
}

void mu_session_status_get(const mu_session *s, mu_session_status *out)
{
    memset(out, 0, sizeof *out);
    if (!s) {
        out->phase = MU_PHASE_CLOSED;
        out->waiting_for_world = -1;
        return;
    }
    out->phase = s->phase;
    out->reason = s->reason;
    out->code = s->reason_code;
    /* derived here and nowhere else: LOGGED_IN -> 0x14; character list and later -> 0x33
     * (NET-ACCOUNT-001 confirms the values against F1 01 and the list's arrival) */
    switch (s->phase) {
    case MU_PHASE_LOGGED_IN:
        out->protocol_state = 0x14;
        break;
    case MU_PHASE_CHARACTERS:
    case MU_PHASE_JOINING:
    case MU_PHASE_IN_WORLD:
    case MU_PHASE_LEAVING:
        out->protocol_state = 0x33;
        break;
    default:
        out->protocol_state = 0;
        break;
    }
    out->waiting_for_world = s->waiting_world;
    out->frames_in = s->frames_in;
    out->frames_out = s->frames_out;
    out->unhandled = s->unhandled;
    out->undecodable = s->undecodable;
    out->unsent = s->unsent;
    out->tick = s->tick;
}

/* ---- the pump ----------------------------------------------------------------------------- */

static void apply_frame(mu_session *s, mu_frame *f)
{
    memset(&s->route, 0, sizeof s->route);
    uint64_t cues_before = s->cues.next_seq;
    mu_journal_begin_frame(s->cfg.journal);
    mu_apply r = mu_session_dispatch(s, f);
    s->frames_in++;
    uint32_t cues = (uint32_t)(s->cues.next_seq - cues_before);
    mu_journal_count_cues(s->cfg.journal, cues);
    mu_journal_frame_in(s->cfg.journal, s->tick, s->now, f, MU_DECODE_OK, &s->route, (int)r, 0, cues);
    mu_journal_end_frame(s->cfg.journal);
    if (r == MU_APPLY_WORLD_CHANGE && s->phase != MU_PHASE_CLOSED) {
        s->waiting_world = s->place.world;
        char text[64];
        snprintf(text, sizeof text, "barrier: waiting for world %d", (int)s->waiting_world);
        mu_journal_text(s->cfg.journal, MU_JNL_EVENT, s->tick, s->now, text);
    }
}

/* Applies every frame connection k has, until the barrier stops application or the session closes. */
static void drain_conn(mu_session *s, mu_conn_kind k)
{
    mu_decode_status ds;
    mu_frame *f = &s->frame;
    while (s->phase != MU_PHASE_CLOSED && s->waiting_world < 0 && mu_net_next(&s->net, k, f, &ds)) {
        f->tick = s->tick;
        if (ds == MU_DECODE_OK) {
            apply_frame(s, f);
            continue;
        }
        /* not applied: journaled with its decode status */
        memset(&s->route, 0, sizeof s->route);
        s->route.head = f->head;
        s->route.opcode = f->opcode;
        s->route.sub = 0x100u;
        mu_journal_frame_in(s->cfg.journal, s->tick, s->now, f, ds, &s->route, (int)MU_APPLY_IGNORED, 0, 0);
        s->undecodable++;
        if (ds == MU_DECODE_SERIAL)
            mu_session_fail(s, MU_CLOSE_DECRYPT_ERROR, 0);
    }
    if (s->phase != MU_PHASE_CLOSED && s->net.conns[k].stopped)
        mu_session_fail(s, MU_CLOSE_RECEIVE_OVERFLOW, MU_RECV_CAP);
}

static void drain_all(mu_session *s)
{
    for (int k = 0; k < MU_CONN_KINDS && s->phase != MU_PHASE_CLOSED; ++k) {
        if (s->net.conns[k].link < 0)
            continue;
        int err = 0;
        mu_link_state st = mu_net_state(&s->net, (mu_conn_kind)k, &err);
        if (st == MU_LINK_REFUSED) {
            mu_session_fail(s, MU_CLOSE_NET_REFUSED, err);
            return;
        }
        if (st == MU_LINK_CONNECTING)
            continue;
        drain_conn(s, (mu_conn_kind)k);
        if (st == MU_LINK_CLOSED && s->phase != MU_PHASE_CLOSED && s->waiting_world < 0) {
            /* the peer closed (or the connect failed); everything it sent before is applied above */
            mu_session_fail(s, MU_CLOSE_NET_LOST, err);
            return;
        }
    }
}

void mu_session_pump(mu_session *s, uint32_t now_ms)
{
    if (!s)
        return;
    s->now = now_ms;
    s->tick++;
    mu_journal_set_ticks(s->cfg.journal, s->tick);
    if (s->phase == MU_PHASE_CLOSED)
        return;
    s->pumping = 1;
    drain_all(s);
    if (mu_journal_wants_snapshot(s->cfg.journal, s->tick)) {
        mu_audit_zones zs;
        mu_session_zones(s, &zs);
        mu_journal_snapshot(s->cfg.journal, s->tick, s->now, &zs);
    }
    s->pumping = 0;
}

/* ---- the world port and the barrier ------------------------------------------------------- */

void mu_session_attach_world(mu_session *s, const mu_world_port *port)
{
    if (!s || !port)
        return;
    if (s->has_port && s->port.world == port->world && s->waiting_world < 0)
        return;   /* attaching the same world again: no-op */
    s->port = *port;
    s->has_port = 1;
    char text[80];
    snprintf(text, sizeof text, "attach world %d", (int)port->world);
    mu_journal_text(s->cfg.journal, MU_JNL_EVENT, s->tick, s->now, text);
    if (s->waiting_world >= 0 && s->waiting_world == port->world) {
        s->waiting_world = -1;
        mu_journal_text(s->cfg.journal, MU_JNL_EVENT, s->tick, s->now, "barrier: released");
        if (s->phase != MU_PHASE_CLOSED && !s->pumping) {
            /* the held frames apply now, in order; another world change among them holds the rest */
            s->pumping = 1;
            drain_all(s);
            s->pumping = 0;
        }
    }
}

void mu_session_detach_world(mu_session *s)
{
    if (!s || !s->has_port)
        return;
    s->has_port = 0;
    memset(&s->port, 0, sizeof s->port);
    mu_journal_text(s->cfg.journal, MU_JNL_EVENT, s->tick, s->now, "detach world");
}

int mu_session_attached_world(const mu_session *s, int32_t *world)
{
    if (!s || !s->has_port)
        return 0;
    if (world)
        *world = s->port.world;
    return 1;
}

/* ---- change ------------------------------------------------------------------------------- */

mu_submit mu_session_submit(mu_session *s, const mu_intent *in)
{
    mu_submit r = {MU_SUBMIT_REFUSED, -1};
    if (!s || !in)
        return r;
    if (s->pumping || s->phase == MU_PHASE_CLOSED) {
        r.status = MU_SUBMIT_NOT_NOW;
    } else if ((int)in->kind <= (int)MU_INTENT_NONE || (int)in->kind >= (int)MU_INTENT_KINDS ||
               !mu_session_submit_routes[in->kind]) {
        r.status = MU_SUBMIT_REFUSED;
    } else {
        r = mu_session_submit_routes[in->kind](s, in);
    }
    mu_journal_intent(s->cfg.journal, s->tick, s->now, (uint32_t)in->kind, (int32_t)r.status, r.notice);
    return r;
}
