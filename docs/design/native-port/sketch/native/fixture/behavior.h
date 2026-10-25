/* FIXTURE-001 (sketch): a fixture behavior - one former demo server.
 *
 * native/fixture/behaviors/<name>.c defines one `const mu_fixture_behavior mu_fx_<name>`; the
 * list is generated from the directory like the session's domains. A scenario line
 * `use combat monster_hp=60 latency=2` instantiates it.
 *
 *   former demo                              behavior        speaks (as real frames)
 *   client/offline-session.c + demo-*.txt    account         F4 06/03, F1 01, list, create/delete, join
 *   core/mu_combat.c demo_damage etc.        combat          damage, die, action (0x01224455, 0x01234585, 0x78)
 *   core/mu_npc.c mu_npc_demo                npc             talk answer 0xdf, shop list, vault
 *   core/mu_progress.c demo queue            progress        0x16, A0 06/11/22/60/30, 0x55 57/94
 *   core/mu_map.c demo travel + town         map             C3 1C, E7 03, respawn
 *   core/mu_quest.c text-log sink            quest           F6 subs, C0/A1/A4/86
 *   core/mu_skill_demo.c, mu_skill_tree4.c   skills          A0 20/03/10/14, FE/FF, 0x7E
 *   core/mu_social.c local echo              social          party 40-44, trade, friends, whisper, rooms, mail
 *   core/mu_world_players.c players file     players         0x12/0x3d/0x14/0x17/0x3f
 *   core/mu_items.c direct mu_gi_create      ground          0x20
 *   world/lorencia-demo-placement.txt        monsters        0x13 - ABSENT until VIEWPORT-MONSTER-001
 *   core/mu_mix.c delayed snapshots          mix             mix answers (bodies: SESSION-ITEMS-002)
 */
#ifndef MU_FIXTURE_BEHAVIOR_H
#define MU_FIXTURE_BEHAVIOR_H

#include <stddef.h>
#include <stdint.h>

#include "../net/mu_conn.h"

typedef struct mu_fixture_ctx mu_fixture_ctx;   /* fixture internals: connections, clock, rng, the fixture's own world */

/* A client request after the server side's decode: the client's layout, its connection. */
typedef struct mu_fixture_request {
    mu_conn_kind conn;
    uint8_t head, opcode;
    uint16_t sub;                    /* MU_SUB_NONE when not sub-dispatched */
    int encrypted;
    const uint8_t *bytes;
    size_t length;
} mu_fixture_request;

typedef struct mu_fixture_behavior {
    const char *name;
    void *(*open)(mu_fixture_ctx *ctx, const char *args, char *error, size_t error_size);
    /* returns 1 when it consumed the request (several behaviors may watch one request; the first wins) */
    int (*on_request)(void *self, mu_fixture_ctx *ctx, const mu_fixture_request *rq);
    void (*on_step)(void *self, mu_fixture_ctx *ctx, uint32_t now_ms);   /* timers: respawns, latency, events */
    void (*close)(void *self);
} mu_fixture_behavior;

/* Services for behaviors. Frames are built with the verified mu_packet builder and sent through
 * the server half of the CryptoModule when `encrypted`. */
int mu_fx_send(mu_fixture_ctx *ctx, mu_conn_kind conn, mu_packet *p, int encrypted);
uint32_t mu_fx_rand(mu_fixture_ctx *ctx);
uint32_t mu_fx_now(const mu_fixture_ctx *ctx);

#endif
