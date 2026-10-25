/* SESSION-CORE-001: the server-authoritative session core.
 *
 * One mu_session is one login to the service: from the connect-server connection through the
 * game-server hop to logout or disconnect. It is the ONLY owner of replicated game state and the
 * ONLY caller of the reconstructed receive handlers and of the request builders. SESSION-CORE-001
 * has one domain, the hero (reconstructed/progress); the others arrive one migration at a time.
 *
 * Everything else (scene shell, world runtime, GFx windows, renderers, audio) is a VIEW: it reads
 * typed state through the getters below, watches per-domain revision counters, consumes one-shot
 * cues through its own cursor, and asks for change only by submitting typed intents.
 *
 * Public surface (all a view or front end may include):
 *   lifecycle   mu_session_open / mu_session_close
 *   time        mu_session_pump           network in  -> state (+ cues)
 *   change      mu_session_submit         intent      -> request bytes out (or a typed refusal)
 *   read        mu_session_status_get, mu_session_rev, the domain getters (domains/<d>.h), mu_session_cues
 *   world       mu_session_attach_world / mu_session_detach_world, mu_session_sim_begin / _end
 *
 * Not on this surface, by design: frames, opcodes, heads, serials, channels, CryptoModule
 * contexts, packet builders, client addresses. Those live in session_internal.h and native/net/,
 * which the include audit (scripts/audit_includes.py) keeps unreachable from outside
 * native/session, native/net and native/fixture.
 *
 * Threading: single-threaded, like the client (WSAAsyncSelect delivery on the UI thread).
 * Includers need -I native/session and -I native/build/gen (the generated domain list).
 */
#ifndef MU_SESSION_H
#define MU_SESSION_H

#include <stddef.h>
#include <stdint.h>

#include "../net/mu_transport.h"   /* mu_transport, mu_endpoint: a byte medium, no MU framing */
#include "mu_intent.h"
#include "mu_cue.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct mu_session mu_session;
struct mu_lang;            /* native/core/mu_lang.h (GlobalText for the handlers' env) */
struct mu_journal;         /* mu_journal.h: optional session recording */

/* ---- configuration: everything a session needs that is not on the wire ------------------ */

/* The pinned client build the session speaks for (docs/evidence-index.json). */
typedef struct mu_client_build {
    const char *main_exe_sha256;    /* hex */
    uint8_t version[8];             /* NET-ACCOUNT-001: the login body's version field, from the builder */
    uint8_t serial[16];             /* NET-ACCOUNT-001: the login body's client serial, if any */
} mu_client_build;
extern const mu_client_build MU_PINNED_BUILD;

/* Launcher-session material: behind the protection boundary, never recovered, forged or replayed.
 * The operator answered NET-CONTRACT-001 (2026-10-25): a login needs only account and password,
 * so the live configuration uses mu_proof_not_required(). */
typedef enum mu_proof_status {
    MU_PROOF_OK = 0,
    MU_PROOF_NOT_REQUIRED,
    MU_PROOF_UNAVAILABLE
} mu_proof_status;
typedef struct mu_login_proof {
    uint8_t bytes[256];
    size_t length;
} mu_login_proof;
typedef struct mu_login_proof_source {
    void *user;
    mu_proof_status (*fetch)(void *user, uint32_t field_tag, mu_login_proof *out);
} mu_login_proof_source;
const mu_login_proof_source *mu_proof_not_required(void);
const mu_login_proof_source *mu_proof_unavailable(void);

typedef struct mu_session_config {
    mu_endpoint connect_server;          /* from settings; never from the install */
    mu_transport *transport;             /* sockets (product), fixture loopback (tests), replay (gate 3); not owned */
    const mu_client_build *build;        /* NULL: MU_PINNED_BUILD */
    const mu_login_proof_source *proof;
    const struct mu_lang *lang;          /* NULL: GlobalText lookups give "" */
    const char *game_root;
    struct mu_journal *journal;          /* NULL: no recording; not owned */
} mu_session_config;

/* ---- lifecycle ------------------------------------------------------------------------- */

/* Opens the session and starts connecting to cfg->connect_server (phase CONNECTING). The shell
 * owns exactly one session pointer and only opens when it is NULL (the scene manager's connect
 * call 0x0121c055 may run more than once per visit to scene 3). */
mu_session *mu_session_open(const mu_session_config *cfg, char *error, size_t error_size);
/* Sends nothing; closes every connection; frees all state. Safe on NULL. */
void mu_session_close(mu_session *s);

/* ---- phase and status ------------------------------------------------------------------ */

typedef enum mu_phase {
    MU_PHASE_CONNECTING = 0,    /* connect server */
    MU_PHASE_SERVER_LIST,       /* F4 06 arrived: the server window can show */
    MU_PHASE_HOPPING,           /* F4 03 arrived: connecting to the chosen game server */
    MU_PHASE_ACCOUNT,           /* game server connected: the account dialog can submit LOGIN */
    MU_PHASE_LOGGING_IN,        /* LOGIN sent, F1 01 not yet answered */
    MU_PHASE_LOGGED_IN,         /* F1 01 accepted (protocol state 0x14) */
    MU_PHASE_CHARACTERS,        /* character list present (protocol state 0x33) */
    MU_PHASE_JOINING,           /* JOIN sent */
    MU_PHASE_IN_WORLD,          /* join answer applied (or a seeded session); place valid */
    MU_PHASE_LEAVING,           /* back to character select requested */
    MU_PHASE_CLOSED             /* terminal; see mu_session_status.reason */
} mu_phase;

typedef enum mu_close_reason {
    MU_CLOSE_NONE = 0,
    MU_CLOSE_LOGOUT,
    MU_CLOSE_NET_REFUSED,               /* endpoint refused / not allowed by the transport */
    MU_CLOSE_NET_LOST,                  /* link closed by the peer or failed */
    MU_CLOSE_RECEIVE_OVERFLOW,          /* the client's 0x2000 receive guard (0x012907a8) */
    MU_CLOSE_DECRYPT_ERROR,             /* "Decrypt error : g_byPacketSerialRecv" path of 0x01221b94 */
    MU_CLOSE_LOGIN_REFUSED,
    MU_CLOSE_CLIENT_OUTDATED,
    MU_CLOSE_ALREADY_CONNECTED,         /* one client at a time; no retry */
    MU_CLOSE_NEEDS_OPERATOR_CONTRACT
} mu_close_reason;

typedef struct mu_session_status {
    mu_phase phase;
    mu_close_reason reason;
    int32_t code;                /* reason-specific (errno, ...) */
    int32_t protocol_state;      /* DERIVED from phase: the client's 0x06fca2c4 (0, 0x14, 0x33) */
    int32_t waiting_for_world;   /* -1, or the world the apply barrier waits for (see attach_world) */
    uint32_t frames_in, frames_out, unhandled;
    uint32_t undecodable, unsent;
    uint32_t tick;
} mu_session_status;

void mu_session_status_get(const mu_session *s, mu_session_status *out);
const char *mu_phase_name(mu_phase phase);
const char *mu_close_reason_name(mu_close_reason reason);

/* ---- time: network in -> state ---------------------------------------------------------- */

/* Drains every complete frame the transport has buffered, in arrival order per connection (connect,
 * game, chat), through the dechunker, the decode stage and the ONE dispatcher, applying each to
 * session state. Emits cues, bumps revisions, may send the answers the client sends from inside
 * handlers (0x16's report). Call it once per frame at the client's queue-drain point.
 *
 * World-change barrier: a frame that changes the world (respawn elsewhere; later the join answer and
 * teleports) is applied, then application STOPS; later frames stay in the connection's dechunk queue
 * and the transport until mu_session_attach_world is called for that world, as the client's loading
 * blocks its message pump. Pumping while waiting applies nothing. */
void mu_session_pump(mu_session *s, uint32_t now_ms);

/* ---- change: intent -> request ---------------------------------------------------------- */

typedef enum mu_submit_status {
    MU_SUBMIT_SENT = 0,          /* the request bytes are queued on the transport */
    MU_SUBMIT_REFUSED,           /* the client's own local refusal (notice = its GlobalText index, or -1) */
    MU_SUBMIT_THROTTLED,         /* a client throttle (the stat request's 100 ms, 0x00b48aca) */
    MU_SUBMIT_NOT_NOW,           /* invalid in the current phase, during a pump, or the link is not open */
    MU_SUBMIT_UNRECOVERED        /* the request body is not reconstructed yet: nothing is sent; journaled */
} mu_submit_status;

typedef struct mu_submit {
    mu_submit_status status;
    int32_t notice;
} mu_submit;

/* Runs the client's local checks for the intent, builds the request with the reconstructed
 * builder, wraps it and queues it. Synchronous: request order is call order. Not from a pump. */
mu_submit mu_session_submit(mu_session *s, const mu_intent *intent);
const char *mu_submit_status_name(mu_submit_status status);

/* ---- read: revisions and cues ------------------------------------------------------------ */

#include "session_domains.h"   /* generated: enum mu_domain + #include of every domains/<d>.h getter header */

uint32_t mu_session_rev(const mu_session *s, mu_domain d);
const char *mu_domain_name(mu_domain d);

/* One-shot presentation events. Each consumer owns its cursor. Copies up to cap cues after
 * *cursor into out and advances it. A consumer that fell behind the ring (1024 cues) gets the
 * number skipped in *lost (cues are cosmetic; state is always in the domains). */
size_t mu_session_cues(const mu_session *s, mu_cue_cursor *cursor, mu_cue *out, size_t cap, uint32_t *lost);
/* A cursor positioned at "now" (a view opened mid-session does not replay old cues). */
mu_cue_cursor mu_session_cue_cursor(const mu_session *s);

/* ---- the world: services the handlers need, and the simulation lease --------------------- */

/* The current place: the server-acknowledged world and hero tile. Kept by the session core until
 * the map domain (SESSION-MAP-001) takes it over. */
typedef struct mu_place {
    int32_t world;               /* client world index ([0x01cf15fc]) */
    int32_t tile[2];
    float angle;
    uint32_t seq;                /* increases on every server placement (join/seed, teleport, respawn) */
} mu_place;
mu_place mu_session_place(const mu_session *s);

struct mu_rp_character;          /* reconstructed/players/remote_players.h: the CHARACTER record subset */
struct mu_rp_path;
struct mu_gi_item;               /* reconstructed/items/ground_items.h */

/* What the reconstructed receive handlers call into the world for, at apply time. Without a port
 * (character select, loading) the session uses the client's no-world answers (the place's tile,
 * position and angle 0). */
typedef struct mu_world_port {
    void *context;
    int32_t world;               /* the world this port serves */
    void (*hero_motion)(void *context, int32_t tile[2], float position[3], float angle[3]);
    void (*place_hero)(void *context, const mu_place *place);
    void (*hero_path_reset)(void *context);
    int (*hero_path_start)(void *context, int32_t flag, int32_t sx, int32_t sy, int32_t tx, int32_t ty, int32_t mode,
                           int32_t error_check);
    int (*path_finding2)(void *context, int32_t sx, int32_t sy, int32_t tx, int32_t ty, struct mu_rp_path *path,
                         int32_t mode);
    int (*move_path)(void *context, struct mu_rp_character *c);
    void (*move_character_position)(void *context, struct mu_rp_character *c);
    void (*set_player_walk)(void *context, struct mu_rp_character *c);
    void (*set_player_stop)(void *context, struct mu_rp_character *c);
    void (*set_action)(void *context, struct mu_rp_character *c, int32_t action);
    float (*terrain_height)(void *context, float x, float y);
    void (*terrain_light)(void *context, float x, float y, float out[3]);
} mu_world_port;

/* Registers the port and, when the session waits for port->world, releases the barrier and applies
 * the held frames immediately (before returning). Attaching the same world again is a no-op.
 * Detach before the world is freed. */
void mu_session_attach_world(mu_session *s, const mu_world_port *port);
void mu_session_detach_world(mu_session *s);
/* 1 while a port is attached (its world in *world when non-NULL). */
int mu_session_attached_world(const mu_session *s, int32_t *world);

/* The simulation lease: write access to the MOTION zones of session-owned records for one 40 ms
 * logic step. The world gets these pointers only between begin and end. Replicated fields must not
 * change during a lease: audit builds (MU_SESSION_AUDIT) snapshot them in begin and abort in end,
 * naming the field, if anything wrote one. In SESSION-CORE-001 the leased records are the hero
 * CHARACTER record (motion zone: the tile +0x180..+0x187); the CharactersClient table and Items[]
 * pool arrive with the viewport and ground domains. */
typedef struct mu_sim {
    struct mu_rp_character *characters;   /* CharactersClient: NULL until SESSION-VIEWPORT-001 */
    const uint8_t *used;
    int32_t character_count;
    int32_t hero_index;
    struct mu_gi_item *ground;            /* Items[]: NULL until SESSION-ITEMS-001 */
    int32_t ground_count;
    uint8_t *hero_record;                 /* the hero CHARACTER record (0x400 bytes); write the motion zone only */
    uint32_t epoch;                       /* 0: no lease (misuse outside audit builds) */
} mu_sim;

mu_sim mu_session_sim_begin(mu_session *s);
void mu_session_sim_end(mu_session *s, const mu_sim *sim);

/* One logic step of a domain's own handler state, called by the world part that holds that step's
 * place in the client's tick order. Only valid inside a lease. */
void mu_session_step(mu_session *s, mu_domain d, const mu_sim *sim);

#ifdef __cplusplus
}
#endif

#endif /* MU_SESSION_H */
