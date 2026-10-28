#ifndef MU_WORLD_PLAYERS_H
#define MU_WORLD_PLAYERS_H

/* Player presentation caches for session/domains/characters records.
 * SESSION-VIEWPORT-001: --players is a loopback fixture. Its specification parser,
 * equipment/viewport encodings and scheduler live in native/fixture. Core owns
 * model loading, movement services, animation, fade, plates and draw inputs.
 * q->c is a presentation copy refreshed from the session; motion is written back
 * during leases. Helpers use the same record feed, including render-time poses.
 * The retained spec is synthetic choreography/label metadata, never a packet feed.
 * See docs/research/client-session-viewport.md for evidence and limits. */

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include "../../reconstructed/combat/combat.h"
#include "../../reconstructed/players/remote_players.h"
#include "mu_character.h"
#include "mu_data.h"
#include "mu_walk.h"

#define MU_WORLD_PLAYERS_MAX 80 /* offline stress capacity, not a server viewport claim */
#define MU_WORLD_PLAYER_ROUTE 16
#define MU_WORLD_PLAYER_GUILDS 4

/* The demo server's knowledge of one player (the players file). */
typedef struct mu_world_player_spec {
    char name[MU_RP_NAME];
    uint8_t class_byte;            /* the character's class byte (c + 0x12 form) */
    uint8_t pk;
    uint16_t level;
    int16_t guild;                 /* -1 none, else an index of the demo guild table */
    uint8_t party;
    int32_t item_type[MU_RP_SLOTS];   /* client item types (0xae6 + 512 * group + index), -1 none */
    uint8_t item_level[MU_RP_SLOTS], excellent[MU_RP_SLOTS], ancient[MU_RP_SLOTS];
    uint16_t ride;                 /* helper item type (0xffff none) */
    uint8_t pet;                   /* NATIVE-HELPERS-001: e[4] & 3 (0 Guardian Angel, 1 Imp, 2 Uniria, 3 none) */
    uint8_t pet_ext;               /* NATIVE-HELPERS-002: e[0xf] & 0xe0, the pet process's pets (0x20 Demon, 0x40 Spirit of
                                    * Guardian, 0x60 Skeleton, 0x80 Rudolph, 0xa0 Panda; 0 none) */
    uint8_t ride_state;            /* NATIVE-HELPERS-001: e[0xf] & 3, 4 = e[0x10] bit 0 (Fenrir's colour) */
    uint8_t raven;                 /* NATIVE-HELPERS-002: the pet byte 0x00c92bea (1 / 2 / 3 Dark Raven; 0 none) */
    int32_t start[2];
    uint8_t direction;
    int32_t route[MU_WORLD_PLAYER_ROUTE][2], route_count;
    int32_t idle_steps;
    int32_t die_step, respawn_steps, store_step;
    char store_title[0x2e];
} mu_world_player_spec;

typedef struct mu_world_player {
    mu_world_player_spec spec;
    mu_rp_character c;             /* the CHARACTER record (reconstructed fields) */
    mu_character model;            /* Player.bmd, class/item parts, weapons, wing */
    int loaded, has_model;
    int in_view;                   /* created by the viewport, not yet destroyed */
    int32_t key;
    uint8_t run;                   /* c + 0x24 */
    uint8_t safe_zone;             /* c + 4 */
    float frame, prior_frame, play_speed, timer;
    uint8_t action_changed, step_result;
    int32_t weapon_kind;           /* MU_WEAPON_* of the right hand (demo inference) */
    int32_t next_leg, wait;        /* demo route */
    mu_fade_state fade;
    float voice_3324;              /* c + 0x3324 */
    int32_t respawn_in;
    uint8_t store_open;
    uint32_t moves, arrivals, creates, destroys, deaths, position_steps;
    uint32_t session_generation, session_equipment_revision;
    int32_t session_slot;
    uint8_t equipment[MU_RP_EQUIP_BYTES];   /* the last viewport record's equipment bytes */
    /* NATIVE-HELPERS-001: ChangeCharacterExt's engine calls of the last viewport record (the angel effect, DeleteBug,
     * the mount manager's reset / set) and their count; the mount manager's predicates for the player (riding
     * 0x0106bdb7, keeps_run 0x0106bd76) and the rider lift 0x0103da5c added at placement. */
    mu_rp_calls equip_calls;
    uint32_t equip_events;
    uint8_t riding, keeps_run;
    float place_offset[3];
} mu_world_player;

struct mu_world_names;
struct mu_combat;
struct mu_social_session;

struct mu_session;
typedef struct mu_world_players {
    struct mu_session *session; /* dev runtime session, owned by the characters part */
    void (*record_action)(void *context, int32_t slot, uint16_t action, uint16_t prior);
    void *record_context;
    mu_rp_character *leased_records; /* set only while a simulation lease is open */
    struct mu_social_session *social; /* NATIVE-SOCIAL-001 authoritative offline membership */
    mu_world_player list[MU_WORLD_PLAYERS_MAX];
    int32_t count;
    char root[1024];
    mu_walk *walk;
    const mu_world *map;
    struct mu_world_names *names;  /* optional */
    const struct mu_combat *combat;   /* optional: the hero's death state (plates only) */
    mu_data_table item_table;
    int has_table, no_textures;
    int32_t view_range;            /* DEMO: the server's viewport range in tiles */
    int32_t key0;
    int32_t hero_guild;            /* DEMO: the hero's guild index (-1 none) */
    uint32_t rng, steps;
    uint32_t audio_rng;
    uint64_t audio_receive_cursor;
    uint32_t audio_receive_lost;
    char guild_names[MU_WORLD_PLAYER_GUILDS][32];
    mu_rp_calls calls;             /* the last step's engine calls (reports) */
    uint32_t viewport_packets, move_packets, destroy_packets, die_packets, store_packets, path_calls, teleports,
        addinfo, removeinfo;
    char log[64][112];
    int32_t log_count;
    /* NATIVE-HELPERS-001: the rider action 0x0106c382 SetPlayerStop / SetPlayerWalk ask while a player rides
     * (returns 1 when it set the action through mu_world_players_set_action). */
    int (*ride_hook)(void *context, int32_t player, int32_t how);
    void *ride_context;
} mu_world_players;

/* Loads the players file (textures unless no_textures). Lines that fail to parse or players whose Player.bmd
 * is missing make the call fail with a message. The hero_guild is the demo hero's guild index. */
int mu_world_players_load(mu_world_players *p, const char *root, mu_walk *walk, const mu_world *map, const char *file,
                          int no_textures, char *error, size_t error_size);
int mu_world_players_load_text(mu_world_players *p, const char *root, mu_walk *walk, const mu_world *map,
                               const char *text, int no_textures, char *error, size_t error_size);
void mu_world_players_free(mu_world_players *p);
/* The overhead plates (addInfo / removeInfo / setStore go through it) and the hero's death state. */
void mu_world_players_attach(mu_world_players *p, struct mu_world_names *names, const struct mu_combat *combat);

/* One leased character step, called only by the characters part's table walk. */
struct mu_world_port;
struct mu_characters_view;
void mu_world_players_port(mu_world_players *p, struct mu_world_port *port);
void mu_world_players_combat_audio(mu_world_players *p);
void mu_world_players_sync(mu_world_players *p, const struct mu_characters_view *view);
void mu_world_players_step_one(mu_world_players *p, int32_t index, mu_rp_character *record);
/* Every rendered frame: places and poses the created players' models. */
void mu_world_players_frame(mu_world_players *p);
/* NATIVE-HELPERS-001: SetAction with the Player model's play speed (the rider actions). */
void mu_world_players_set_action(mu_world_players *p, int32_t i, int32_t action);
/* Object alpha of a player (0 when not drawn). */
float mu_world_players_alpha(const mu_world_players *p, int32_t i);
/* The glow inputs of a part (NATIVE-RENDERCHAR-001's RenderObjDraw passes): type, level, option, ext, the
 * Item.bmd kinds when the table is loaded. item = mu_character item index. */
void mu_world_players_glow(const mu_world_players *p, int32_t i, int item, int32_t *type, int32_t *level,
                           int32_t *option, int32_t *ext, int *has_record, uint8_t *kind_a, uint8_t *kind_b,
                           uint8_t *item_kind);

/* The demo server's encoding of a player into the viewport's equipment bytes (the inverse of
 * ChangeCharacterExt's decode; DEMO, not a client routine). */
void mu_world_players_encode_equipment(const mu_world_player_spec *s, uint8_t e[MU_RP_EQUIP_BYTES]);
/* The viewport record of a player (0x44 bytes, no buffs). */
int32_t mu_world_players_encode_viewport(const mu_world_players *p, const mu_world_player *q, int created,
                                         uint8_t *out, int32_t cap);

void mu_world_players_report_frame(const mu_world_players *p, FILE *out, int32_t frame);
void mu_world_players_report_summary(const mu_world_players *p, FILE *out, int quiet);

#endif
