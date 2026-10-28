/* Maps and travel in the native client (NATIVE-MAP-001, docs/research/client-maps.md).
 *
 * The session side of reconstructed/map: the Tab map overlay's state and
 * minimap units, the Move window ("M": the move manager, its availability
 * and list rows), the per-step gate entrance test, and an OFFLINE DEMO
 * server that answers the move and gate requests with the teleport packet
 * (C3 1C) the real server sends.  What the client does is reconstructed
 * (verified in Unicorn, scripts/validate_map.py); the server's answers are
 * the demo's choices, labelled:
 *
 *   - a move request for movereq key K is accepted when the hero's level and
 *     zen reach the record's (the zen is taken); the hero lands on a tile of
 *     the record's target gate rectangle (the live server does so: Lorencia
 *     and Noria warps landed inside gates 17 and 27);
 *   - a gate request for an entrance gate lands on its target gate;
 *   - SESSION-MAP-001a moves marker policy to the plaintext fixture and the
 *     collection to the session; this object borrows only its public view.
 *
 * Quests and other callers travel through mu_map_travel_to / mu_map_travel_move
 * (the "Go Now" hook, see the note at the end).  The host polls
 * mu_map_take_teleport each step and changes the world when it returns 1. */
#ifndef MU_MAP_CORE_H
#define MU_MAP_CORE_H

#include <stddef.h>
#include <stdint.h>

#include "../../reconstructed/map/map.h"

#ifdef __cplusplus
extern "C" {
#endif

struct mu_lang;
struct mu_session;

#define MU_MAP_MOVES_MAX 256
#define MU_MAP_GATES_MAX 1024

typedef struct mu_map_session {
    char text_ring[4][48];
    unsigned text_next;
    const struct mu_lang *lang;
    /* hero */
    int32_t world, tile_x, tile_y;
    int64_t zen;                   /* demo inventory zen (the demo server takes the warp cost) */
    mu_move_hero hero;             /* level = level + master level (the getter the window reads; live check) */
    /* move window */
    mu_move_record records[MU_MAP_MOVES_MAX];
    int32_t keys[MU_MAP_MOVES_MAX];   /* the table's key list: record id order (observed live) */
    int nrecords;
    mu_move_entry entries[MU_MAP_MOVES_MAX];
    int nentries;
    int32_t sort_order;
    mu_move_favourite favourites[5];
    int move_open;
    /* gates (key order) */
    mu_gate gates[MU_MAP_GATES_MAX];
    int ngates;
    uint32_t gate_last_ms;         /* the request throttle's time (0x0095f75d +8) */
    uint8_t gate_sent;             /* its flag (+6) */
    int32_t loading_world;         /* LoadingWorld [0x0b437c14] */
    /* map overlay */
    mu_map_hud hud;
    uint32_t overlay_epoch;
    const struct mu_session *overlay; /* borrowed; session owns all marker and dot records */
    /* demo server */
    uint32_t rng;
    int pending;
    mu_teleport teleport;
    char last[192];                /* last event, for logs and tests */
    char notice[192];              /* last chat notice (GlobalText) */
} mu_map_session;

/* lang may be NULL (no tables: the window stays empty, gates do nothing). */
void mu_map_session_init(mu_map_session *s, const struct mu_lang *lang, int32_t world, int32_t tile_x, int32_t tile_y);
/* The hero's tile each logic step (also after a teleport). */
void mu_map_set_position(mu_map_session *s, int32_t world, int32_t tile_x, int32_t tile_y);
/* Text helper over the session's tables (GlobalText; "" when absent). */
const char *mu_map_text(const mu_map_session *s, int32_t index);
const char *mu_map_world_name(const mu_map_session *s, int32_t world);

/* ---- map overlay ---- */
/* The world image file name (navimapNN.ozp) and whether it exists under game_root's
 * Data/Interface/GFx/NaviMap (the window's +0x4e byte). */
int mu_map_session_load_map(mu_map_session *s, const char *game_root, char *name, size_t cap);
/* Bind a read-only overlay view. Detach before closing its session. */
void mu_map_bind_overlay(mu_map_session *s, const struct mu_session *overlay);
/* Tab / showMap: the client's rule; returns the result (notice, setShowMap, E7 request). */
void mu_map_toggle(mu_map_session *s, int show, mu_map_show_result *out);

/* ---- move window ---- */
/* Opens the window: strife flags, availability and the rows in the current sort order; returns the count. */
int mu_map_move_rows(mu_map_session *s, mu_move_row *rows, int max);
void mu_map_move_sort(mu_map_session *s, int32_t order);
/* A row click (orderIdx): the client's click and the demo server's answer.  Returns 1 when a teleport is
 * pending. */
int mu_map_move_click(mu_map_session *s, int32_t index, mu_move_click_result *out);

/* ---- gates ---- */
/* Once per logic step: LoadingWorld's count-down. */
void mu_map_step(mu_map_session *s);
/* The entrance test at this step (now in ms); returns 1 when a teleport is pending. */
int mu_map_gate_step(mu_map_session *s, uint32_t now_ms, mu_gate_result *out);

/* ---- travel API (NATIVE-QUEST-002's "Go Now", scripts, tests) ---- */
/* Teleport the hero to (world, tile) as the server would answer a warp (DEMO: no checks). */
int mu_map_travel_to(mu_map_session *s, int32_t world, int32_t tile_x, int32_t tile_y);
/* A move request for a movereq key without the window (the server's checks: level, zen). */
int mu_map_travel_move(mu_map_session *s, int32_t key);
/* NATIVE-PROGRESS-001: the DEMO server's respawn town for a death in `world` (gate 22 Devias for 2, 27 Noria
 * for 3, 267 Elbeland for 51, else 17 Lorencia: the town gates of the classic servers' respawn rule) and a
 * tile in its rectangle; the teleport is pending like a warp's.  Returns 1 with the target, 0 without
 * the gate table. */
int mu_map_respawn(mu_map_session *s, int32_t world, int32_t *out_world, int32_t *tile_x, int32_t *tile_y);
/* The pending teleport (the C3 1C answer as the client parses it); 1 when there was one. */
int mu_map_take_teleport(mu_map_session *s, mu_teleport *out);
/* The demo server's teleport bytes for a target (tests). */
int mu_map_teleport_packet(int32_t world, int32_t x, int32_t y, int32_t dir, uint16_t number, uint8_t *out,
                           size_t cap);

#ifdef __cplusplus
}
#endif

#endif
