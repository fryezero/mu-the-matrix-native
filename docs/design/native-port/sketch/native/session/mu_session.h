/* SESSION-CORE-001 (sketch): the server-authoritative session core.
 *
 * One mu_session is one login to the service: from the connect-server connection
 * through the game-server hop to logout or disconnect. It is the ONLY owner of
 * replicated game state (account, hero records, money, inventory, skills, quests,
 * social, the CharactersClient viewport, ground items, the current place). It is the
 * ONLY caller of the reconstructed receive handlers and of the request builders.
 *
 * Everything else (scene shell, world runtime, GFx windows, renderers, audio) is a
 * VIEW: it reads typed state through the getters below, watches per-domain revision
 * counters, consumes one-shot cues through its own cursor, and asks for change only
 * by submitting typed intents.
 *
 * Public surface (all a view or front end may include):
 *   lifecycle   mu_session_open / mu_session_close
 *   time        mu_session_pump           network in  -> state (+ cues)
 *   change      mu_session_submit         intent      -> request bytes out (or a typed refusal)
 *   read        mu_session_status, mu_session_rev, the domain getters (domains/<d>.h), mu_session_cues
 *   world       mu_session_attach_world / mu_session_detach_world, mu_session_sim_begin / _end
 *
 * Not on this surface, by design: frames, opcodes, heads, serials, channels,
 * CryptoModule contexts, packet builders, client addresses. Those live in
 * session_internal.h and native/net/, which an include audit keeps unreachable
 * from outside native/session, native/net and native/fixture.
 *
 * Threading: single-threaded, like the client (WSAAsyncSelect delivery on the UI
 * thread). Every call happens on the main thread.
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
struct mu_lang;            /* native/core/mu_lang.h (text tables; no longer a process singleton) */
struct mu_journal;         /* mu_journal.h: optional session recording for replay and comparison */

/* ---- configuration: everything a session needs that is not on the wire ------------------ */

/* The pinned client build the session speaks for (docs/evidence-index.json). The version
 * bytes the login body carries come from here, recovered from the restored text, never typed
 * by hand. A server that refuses this build closes the session with MU_CLOSE_CLIENT_OUTDATED. */
typedef struct mu_client_build {
    const char *main_exe_sha256;    /* "3cf91f3c...5527a" */
    uint8_t version[8];             /* TODO(NET-ACCOUNT-001): the login body's version field, from the builder */
    uint8_t serial[16];             /* TODO(NET-ACCOUNT-001): the login body's client serial, if any */
} mu_client_build;

/* Launcher-session material. The original receives something from the official launcher /
 * IGC.dll over localhost:55232; its content is behind the protection boundary and is NOT
 * recovered, forged or replayed here. If NET-ACCOUNT-001 shows the login body carries such a
 * field, the session asks this source for it. This repository ships exactly two
 * implementations: mu_proof_not_required() and mu_proof_unavailable(). Anything else must come
 * from a recorded operator contract (NET-CONTRACT-001). */
typedef enum mu_proof_status {
    MU_PROOF_OK = 0,            /* out filled by an operator-sanctioned source */
    MU_PROOF_NOT_REQUIRED,      /* the service accepts a login without launcher material */
    MU_PROOF_UNAVAILABLE        /* no contract: the session closes with MU_CLOSE_NEEDS_OPERATOR_CONTRACT */
} mu_proof_status;

typedef struct mu_login_proof {
    uint8_t bytes[256];
    size_t length;
} mu_login_proof;

typedef struct mu_login_proof_source {
    void *user;
    /* field_tag names the login-body field (from the reconstructed builder) the material fills. */
    mu_proof_status (*fetch)(void *user, uint32_t field_tag, mu_login_proof *out);
} mu_login_proof_source;

const mu_login_proof_source *mu_proof_not_required(void);
const mu_login_proof_source *mu_proof_unavailable(void);

typedef struct mu_session_config {
    mu_endpoint connect_server;          /* from settings / the operator contract; never from the install */
    mu_transport *transport;             /* sockets (product), fixture loopback (tests), replay (gate 3) */
    const mu_client_build *build;
    const mu_login_proof_source *proof;
    const struct mu_lang *lang;          /* GlobalText etc. for the handlers' env */
    const char *game_root;               /* Item.bmd / skill tables the handlers' lookups read */
    struct mu_journal *journal;          /* NULL: no recording */
} mu_session_config;

/* ---- lifecycle ------------------------------------------------------------------------- */

/* Opens the session and starts connecting to cfg->connect_server (phase CONNECTING).
 * Idempotency: the scene manager's connect call 0x0121c055 may run more than once per visit to
 * scene 3; the shell keeps one session and calling open again is the caller's bug, so the shell
 * owns exactly one pointer and only opens when it is NULL. */
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
    MU_PHASE_LOGGED_IN,         /* F1 01 accepted (protocol state 0x14): the scene asks for the character list */
    MU_PHASE_CHARACTERS,        /* character list present (protocol state 0x33) */
    MU_PHASE_JOINING,           /* JOIN sent */
    MU_PHASE_IN_WORLD,          /* join answer applied; place valid */
    MU_PHASE_LEAVING,           /* back to character select requested */
    MU_PHASE_CLOSED             /* terminal; see mu_session_status.reason */
} mu_phase;

typedef enum mu_close_reason {
    MU_CLOSE_NONE = 0,
    MU_CLOSE_LOGOUT,                    /* LOGOUT intent answered */
    MU_CLOSE_NET_REFUSED,               /* endpoint refused / not allowed by the transport */
    MU_CLOSE_NET_LOST,                  /* link closed by the peer */
    MU_CLOSE_RECEIVE_OVERFLOW,          /* the client's 0x2000 receive guard (0x012907a8) */
    MU_CLOSE_DECRYPT_ERROR,             /* "Decrypt error : g_byPacketSerialRecv" path of 0x01221b94 */
    MU_CLOSE_LOGIN_REFUSED,             /* F1 01 result != success; status.code holds the result byte */
    MU_CLOSE_CLIENT_OUTDATED,           /* the result code the server uses for a wrong version */
    MU_CLOSE_NEEDS_OPERATOR_CONTRACT    /* the login needs launcher material no sanctioned source provides */
} mu_close_reason;

typedef struct mu_session_status {
    mu_phase phase;
    mu_close_reason reason;
    int32_t code;                /* reason-specific (login result byte, errno, ...) */
    int32_t protocol_state;      /* DERIVED from phase: the client's 0x06fca2c4 (0, 0x14, 0x33); the shell copies it
                                  * into mu_scenemgr_globals.protocol every frame, nothing else writes that field */
    int32_t waiting_for_world;   /* -1, or the world the apply barrier waits for (see attach_world) */
    uint32_t frames_in, frames_out, unhandled;   /* counters for reports and tests */
} mu_session_status;

void mu_session_status_get(const mu_session *s, mu_session_status *out);

/* ---- time: network in -> state ---------------------------------------------------------- */

/* Drains every complete frame the transport has buffered, in arrival order, through the
 * dechunker, the decode stage (C3/C4 CryptoModule + serial check, 0x01221b94) and the ONE
 * dispatcher (0x01287ead's table), applying each to session state. Emits cues, bumps
 * revisions, may send answers the client sends from inside handlers (e.g. 0x16's report).
 *
 * Call it once per frame at the point where the client drains its packet queue (recovered
 * by NET-DISPATCH-001; until then: immediately before mu_scenemgr_dispatch).
 *
 * World-change barrier: a frame that changes the world (join answer, teleport to another
 * map, respawn elsewhere) is applied, then application STOPS; later frames stay queued until
 * mu_session_attach_world is called for that world, as the client's loading blocks its
 * message pump. Pumping while waiting applies nothing (idempotent). */
void mu_session_pump(mu_session *s, uint32_t now_ms);

/* ---- change: intent -> request ---------------------------------------------------------- */

typedef enum mu_submit_status {
    MU_SUBMIT_SENT = 0,          /* the request bytes are queued on the transport */
    MU_SUBMIT_REFUSED,           /* the client's own local refusal (notice = its GlobalText index) */
    MU_SUBMIT_THROTTLED,         /* a client throttle (e.g. the stat request's 100 ms, 0x00b48aca) */
    MU_SUBMIT_NOT_NOW,           /* invalid in the current phase (e.g. WALK before IN_WORLD) */
    MU_SUBMIT_UNRECOVERED        /* the request body is not reconstructed yet: nothing is invented, nothing is sent;
                                  * counted in the journal so the gap is visible */
} mu_submit_status;

typedef struct mu_submit {
    mu_submit_status status;
    int32_t notice;              /* GlobalText index of a REFUSED, else -1 */
} mu_submit;

/* Runs the client's local checks for the intent, builds the request with the reconstructed
 * builder, wraps it (serial, XorData, C3/C4) and queues it. Synchronous, so request order is
 * call order, as in the client. Must not be called from inside mu_session_pump. */
mu_submit mu_session_submit(mu_session *s, const mu_intent *intent);

/* ---- read: revisions and cues ------------------------------------------------------------ */

/* MU_DOMAIN_* is generated from the files in native/session/domains/ (one enum entry per
 * domain; see MODULES.md). A domain's revision increases whenever any of its state changes.
 * Views re-read a domain when its revision differs from the one they last rendered: re-reading
 * twice is harmless, so views are idempotent by construction. */
#include "session_domains.h"   /* generated: enum mu_domain + #include of every domains/<d>.h getter header */

uint32_t mu_session_rev(const mu_session *s, mu_domain d);

/* One-shot presentation events (sounds, effects, damage numbers, chat lines, window calls).
 * Each consumer owns its cursor (per-reader state, merge at the read boundary). Copies up to
 * cap cues after *cursor into out and advances it. If the consumer fell behind the ring,
 * *lost receives the number skipped (cues are cosmetic; state is always in the domains). */
size_t mu_session_cues(const mu_session *s, mu_cue_cursor *cursor, mu_cue *out, size_t cap, uint32_t *lost);
/* A cursor positioned at "now" (a view opened mid-session does not replay old cues). */
mu_cue_cursor mu_session_cue_cursor(const mu_session *s);

/* ---- the world: services the handlers need, and the simulation lease --------------------- */

/* The current place (map domain): the server-acknowledged world and hero tile. */
typedef struct mu_place {
    int32_t world;               /* client world index ([0x01cf15fc]) */
    int32_t tile[2];
    float angle;
    uint32_t seq;                /* increases on every server placement (join, teleport, respawn) */
} mu_place;
mu_place mu_session_place(const mu_session *s);

struct mu_rp_character;          /* reconstructed/players/remote_players.h: the CHARACTER record subset */
struct mu_rp_path;
struct mu_gi_item;               /* reconstructed/items/ground_items.h */

/* What the reconstructed receive handlers call into the world for, at apply time. The world
 * runtime registers this while a world is loaded. Without a port (character select, loading)
 * the session uses the client's no-world answers (path not found, height 0) - but the barrier
 * guarantees no in-world frame is applied without the right port. */
typedef struct mu_world_port {
    void *context;
    int32_t world;               /* the world this port serves */
    /* hero motion is the world's (mu_walk): handlers that read Hero +0x180/+0x184 or o+0x158 get it here */
    void (*hero_motion)(void *context, int32_t tile[2], float position[3], float angle[3]);
    /* a server placement of the hero (teleport in the same world, respawn): the world moves its hero now, so the
     * handlers that follow in the same pump read the new tile, as in the client */
    void (*place_hero)(void *context, const mu_place *place);
    /* the hero's PATH_t services some handlers call (quest Go Now: mu_quest_host path_reset 0x0129c4d2 and
     * path_start 0x0129c6be); the world's mu_walk auto path performs them */
    void (*hero_path_reset)(void *context);
    int (*hero_path_start)(void *context, int32_t flag, int32_t sx, int32_t sy, int32_t tx, int32_t ty, int32_t mode,
                           int32_t error_check);
    /* mu_rp_env services (reconstructed/players) */
    int (*path_finding2)(void *context, int32_t sx, int32_t sy, int32_t tx, int32_t ty, struct mu_rp_path *path,
                         int32_t mode);
    int (*move_path)(void *context, struct mu_rp_character *c);
    void (*move_character_position)(void *context, struct mu_rp_character *c);
    void (*set_player_walk)(void *context, struct mu_rp_character *c);
    void (*set_player_stop)(void *context, struct mu_rp_character *c);
    void (*set_action)(void *context, struct mu_rp_character *c, int32_t action);
    /* mu_gi_host services (reconstructed/items) */
    float (*terrain_height)(void *context, float x, float y);
    void (*terrain_light)(void *context, float x, float y, float out[3]);
} mu_world_port;

/* Registers the port and, when the session waits for port->world, releases the barrier and
 * applies the held frames immediately (before returning). Attaching the same world twice is a
 * no-op. Detach before the world is freed. */
void mu_session_attach_world(mu_session *s, const mu_world_port *port);
void mu_session_detach_world(mu_session *s);

/* The simulation lease: write access to the MOTION fields of session-owned records for one
 * 40 ms logic step (MoveCharacters' remote step, MoveItems' sparkle, dead fade). The world
 * gets these pointers only between begin and end; outside that window it holds const views.
 * Replicated fields (key, class, equipment, hp, name, item data...) must not change during a
 * lease: debug builds snapshot them in begin and abort in end if a tick wrote one. */
typedef struct mu_sim {
    struct mu_rp_character *characters;   /* CharactersClient (MU_VIEWPORT_MAX) */
    const uint8_t *used;                  /* which entries are live */
    int32_t character_count;
    int32_t hero_index;                   /* skipped by MoveCharacters' remote step */
    struct mu_gi_item *ground;            /* the Items[] pool */
    int32_t ground_count;
    uint32_t epoch;
} mu_sim;

mu_sim mu_session_sim_begin(mu_session *s);
void mu_session_sim_end(mu_session *s, const mu_sim *sim);

/* One logic step of a domain's own handler state (quest timers, event countdowns), called by
 * the world part that holds that step's place in the client's tick order. Only valid inside a
 * lease; a domain without a step hook ignores it. */
void mu_session_step(mu_session *s, mu_domain d, const mu_sim *sim);

#ifdef __cplusplus
}
#endif

#endif /* MU_SESSION_H */
