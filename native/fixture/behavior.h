/* FIXTURE-001: a fixture behaviour - one former demo server.
 *
 * native/fixture/behaviors/<name>.c defines one `const mu_fixture_behavior mu_fx_<name>`; the list is
 * generated from the directory (scripts/gen_domains.py -> build/gen/fixture_behaviors.def; two
 * behaviours with one name fail the build). A scenario line `use progress latency=2` instantiates it.
 *
 *   former demo                              behaviour       speaks (as real frames)
 *   core/mu_progress.c demo queue            progress        0x16, A0 06/11/22/60/30, 0x55 57/94  (FIXTURE-001)
 *   client/offline-session.c + demo-*.txt    account         F4 06/03, F1 01, list, create/delete, join
 *   core/mu_combat.c demo_damage etc.        combat          damage, die, action
 *   core/mu_npc.c mu_npc_demo                npc             talk answer 0xdf, shop list, vault
 *   core/mu_map.c demo travel + town         map             C3 1C, E7 03, respawn
 *   ...                                      (one per domain migration, plan section C)
 */
#ifndef MU_FIXTURE_BEHAVIOR_H
#define MU_FIXTURE_BEHAVIOR_H

#include <stddef.h>
#include <stdint.h>

#include "../net/mu_conn.h"
#include "mu_fixture.h"

typedef struct mu_fixture_ctx mu_fixture_ctx;   /* fixture internals: connections, clock, rng */

/* A client request after the server side's decode (XorData undone): the client's layout. */
typedef struct mu_fixture_request {
    mu_conn_kind conn;
    uint8_t head, opcode;
    uint16_t sub;                    /* the byte after the opcode, 0x100 when the frame has none */
    int encrypted;
    const uint8_t *bytes;            /* the whole frame, header included */
    size_t length;
} mu_fixture_request;

typedef struct mu_fixture_behavior {
    const char *name;
    void *(*open)(mu_fixture_ctx *ctx, const char *args, char *error, size_t error_size);
    /* returns 1 when it consumed the request (several behaviours may watch one request; the first wins) */
    int (*on_request)(void *self, mu_fixture_ctx *ctx, const mu_fixture_request *rq);
    /* timers: latency, respawns, events; called once per fixture step after the requests and commands */
    void (*on_step)(void *self, mu_fixture_ctx *ctx, uint32_t now_ms);
    /* a scenario command `at TICK <name> COMMAND...`; returns 0, or -1 with a message */
    int (*on_command)(void *self, mu_fixture_ctx *ctx, const char *command, char *error, size_t error_size);
    void (*close)(void *self);
    /* Optional fixture-only plaintext request lane, before the legacy XorData decode.
     * Return 1 only for the behaviour's explicitly supported opcodes. */
    int (*on_plain_request)(void *self, mu_fixture_ctx *ctx, const mu_fixture_request *rq);
} mu_fixture_behavior;

void *mu_fixture_behavior_state(mu_fixture *f, const char *name);
/* Compose independent server models without consulting client/session records. */
void *mu_fx_behavior_state(mu_fixture_ctx *ctx, const char *name);
int mu_fx_progress_resources(void *state, int32_t resources[4]);
/* Emit a composed combat reward immediately, preserving exp/drop/quest order. */
void mu_fx_items_reward(mu_fixture_ctx *ctx, int32_t code, float x, float y);

/* Services for behaviours. Frames are built with the verified mu_packet builder (plain adds: the
 * server does not XorData its answers). encrypted != 0 is refused (-2) until the mirror
 * CryptoModule exists; -1 when no client link of that kind is open. */
int mu_fx_send(mu_fixture_ctx *ctx, mu_conn_kind conn, mu_packet *p, int encrypted);
uint32_t mu_fixture_rand(mu_fixture_ctx *ctx);
uint32_t mu_fx_now(const mu_fixture_ctx *ctx);
uint32_t mu_fx_step(const mu_fixture_ctx *ctx);

#endif
