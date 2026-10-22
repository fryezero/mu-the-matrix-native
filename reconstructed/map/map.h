/* The client's maps and travel (NATIVE-MAP-001, docs/research/client-maps.md).
 *
 * Pinned inputs: restored text capture09 (2bd5f2e9...3724) at 0x00401000 and
 * the second image section run10 (c985e2e6...a0672f) at 0x01a7c000.
 *
 * Four client pieces, restated in C:
 *
 *   - the map overlay (Tab): the game side of the GFx movie hudMap (window
 *     object methods 0x00c6aba6 / 0x00c6af22 and the routines below them):
 *     the world image file, the tile -> map pixel transform, the hero's
 *     marker, the server's minimap records (opcode 0xE7) and the show/hide
 *     rule with its request packet;
 *   - the Move window (MoveCommand movie, "M"): the move manager built from
 *     the movereq(kor) Lang table (0x00d3b4cb), its three sort orders
 *     (0x00d3b325 over MSVC std::sort), the availability pass 0x00bdc0c7
 *     (level, zen, the name rules), the list rows 0x00bdd08d and the click
 *     0x00bdc813 with the move request (C1 8E 02, 0x00b3b866);
 *   - gates: the per-frame entrance test 0x016a4608 over the Gate table (the
 *     client sends the gate number, C3 1C, and the server teleports);
 *   - the teleport answer (C3 1C, 0x0128136d): position, direction, the
 *     world change and the notice.
 *
 * The network side (sending, the C3 cipher) stays outside: the module returns
 * the bytes the client's packet builder is given.  Every routine says whether
 * it was run in Unicorn against the client's instructions (verified,
 * scripts/validate_map.py) or is a reading of them (static). */
#ifndef MU_MAP_H
#define MU_MAP_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---- map overlay (hudMap) ------------------------------------------------------------------------ */

/* The world image: sprintf("navimap%02d.ozp", world + 1) under
 * "./Data/Interface/GFx/Navimap/" (LoadWorldMap 0x00c6b116, verified).  The
 * movie loads "NaviMap/" + name; the window's "map available" byte +0x4e is 1
 * when the file exists.  Returns the length written (snprintf). */
int mu_map_navimap_name(int32_t world, char *out, size_t cap);
#define MU_MAP_NAVIMAP_DIR "./Data/Interface/GFx/Navimap/"

/* Tile coordinates -> map image pixels (0x00c6ba5c, 0x00c6ba7d, verified):
 * x' = x * 2, y' = (256 - y) * 2, in float.  The movie rotates the whole map
 * by -45 degrees (mcRot) and scales it (mcWideScale 225 x 150 %). */
float mu_map_px_x(float tile_x);
float mu_map_px_y(float tile_y);

/* The window's per-frame update 0x00c6af22 (verified).  The client keeps the
 * last values it sent; NaN-safe comparisons as the client's ucomiss. */
typedef struct mu_map_hud {
    uint8_t shown;          /* +0x4c (setShowMap) */
    uint8_t available;      /* +0x4e (the world image exists) */
    float last_x, last_y;   /* +0x40, +0x44: hero position last sent (world units) */
    float last_rotation;    /* +0x48 */
} mu_map_hud;

typedef struct mu_map_hud_frame {
    int set_rotation;       /* hero marker: SetDisplayInfo(_rotation = rotation) */
    double rotation;        /* 225 - hero angle z (float, widened) */
    int set_position;       /* map: SetDisplayInfo(_x, _y) */
    double map_x, map_y;    /* -(px_x(x / 100)), -(px_y(y / 100)) */
} mu_map_hud_frame;

/* hero_valid / map_valid: the movie's hero and map values are defined
 * (0x00aad348); hero_pos: object +0x33ac (x, y), hero_angle_z: +0x33b8[2]. */
void mu_map_hud_update(mu_map_hud *h, int hero_valid, int map_valid, const float hero_pos[2], float hero_angle_z,
                       mu_map_hud_frame *out);

/* The movie's units (addUnit / delUnit): type 0 portal, 1 NPC (state 6: Cursed
 * Temple stone), 2 user, 3 monster (AddDetectedUnit), party icons apart. */
typedef struct mu_map_unit {
    int32_t type, key, state;
    float x, y;             /* map pixels */
    char text[64];
} mu_map_unit;

/* addUnit 0x00c6baa6(type, key, state, text, x, y) (verified): tile ints to pixels. */
void mu_map_unit_make(int32_t type, int32_t key, int32_t state, const char *text, int32_t tile_x, int32_t tile_y,
                      mu_map_unit *out);

/* The server's minimap record, opcode 0xE7 sub 3 (0x00c6b550) and sub 4
 * (0x00c6b5c5, the same without the name), verified.  Offsets from the packet
 * start: [4] key, [5] type, [6] state, [7] 0 add / 1 remove, [8] x, [9] y,
 * [10..] name (sub 3).  Returns MU_MAP_UNIT_ADD, _DEL or _NONE. */
enum { MU_MAP_UNIT_NONE = 0, MU_MAP_UNIT_ADD = 1, MU_MAP_UNIT_DEL = 2 };
int mu_map_unit_packet(const uint8_t *packet, size_t length, int with_name, mu_map_unit *out);

/* AddDetectedUnit 0x00c6b6c2 (verified): element i of the detector's list
 * {kind, x, y} becomes {type kind + 1, key i, state 0, text "", pixels}. */
void mu_map_detected_unit(int32_t index, int32_t kind, int32_t tile_x, int32_t tile_y, mu_map_unit *out);

/* The world/tile ranges where the map refuses to open (0x00c6bc46, verified):
 * returns 1 when blocked; *notice = 1 when the client also prints
 * GlobalText[MU_MAP_TEXT_UNAVAILABLE] (world 0x73 refuses silently). */
int mu_map_blocked(int32_t world, int32_t tile_x, int32_t tile_y, int *notice);
#define MU_MAP_TEXT_UNAVAILABLE 0x1076

/* The movie's showMap event (0x00c6aba6, verified).  Out: what the client
 * does.  packet: C1 E7 01 (shown) / C1 E7 02 (hidden), 4 bytes. */
typedef struct mu_map_show_result {
    int ignored;            /* blocked (no change) */
    int notice;             /* a chat notice with GlobalText[0x1076] */
    int set_show;           /* invoke setShowMap(shown) */
    int shown;
    uint8_t packet[4];
    int packet_length;
} mu_map_show_result;
void mu_map_show(mu_map_hud *h, int show, int32_t world, int32_t tile_x, int32_t tile_y, mu_map_show_result *out);

/* InitData on the movie's onLoad (0x00c6b89f, verified): MaxPartyCount 5 and
 * ten GlobalText numbers for the key help (member order below). */
#define MU_MAP_MAX_PARTY 5
extern const char *const mu_map_init_members[10];
extern const int32_t mu_map_init_text[10];

/* ---- Move window ---------------------------------------------------------------------------------- */

/* A movereq(kor) record as the window reads it (Lang table 0x06fbb84c,
 * lookup 0x0113c3f5; NATIVE-LANG-001 names). */
typedef struct mu_move_record {
    int32_t key;            /* the map key */
    int32_t id;             /* +0x00 */
    const char *name;       /* +0x04 (the window's map name, used by the name rules) */
    const char *server_name;/* +0x1c */
    int32_t zen, min_level, max_level, gate, x44, x48, x4c;   /* +0x34 .. +0x4c */
} mu_move_record;

/* The move manager's entry (0x18 bytes, vector at manager +4). */
typedef struct mu_move_entry {
    int32_t key;            /* +0x00 */
    int32_t x44;            /* +0x04 the record's +0x44 (sort order 1) */
    int32_t order;          /* +0x08 position in the table's key list (sort order 0) */
    int32_t x48;            /* +0x0c the record's +0x48 (sort order 2) */
    int32_t key2;           /* +0x10 the key again (the lookups use this one) */
    uint8_t enabled;        /* +0x14 */
    uint8_t strife;         /* +0x15 */
    uint8_t clicked;        /* +0x16 */
    uint8_t pad;
} mu_move_entry;

/* The record lookup the module uses (key -> record, NULL when absent: the
 * client then uses the table's default record, all zero). */
typedef const mu_move_record *(*mu_move_lookup_fn)(void *user, int32_t key);

/* The manager's constructor 0x00d3b4cb (verified): one entry per key of the
 * table's key list, in that order.  Returns the count (<= cap). */
int mu_move_build(const int32_t *keys, int n, mu_move_lookup_fn lookup, void *user, mu_move_entry *out, int cap);

/* 0x00d3b325(order) (verified): std::sort (MSVC) by +8 (0), +4 (1) or +0xc
 * (2); other values leave the list. */
void mu_move_sort(mu_move_entry *entries, int n, int32_t order);

/* The strife (PvP) flags 0x00bdbf82 (static: its branch choice jumps into a
 * runtime-patched region): clears every flag, then sets those of the listed
 * movereq keys by record id (entry +8).  The three lists the code holds: */
extern const int32_t mu_move_strife_keys_5[5];   /* {0x1c, 0x1d, 0x21, 0x2a, 0x2d} */
void mu_move_set_strife(mu_move_entry *entries, int n, const int32_t *keys, int nkeys, mu_move_lookup_fn lookup,
                        void *user);

/* The availability pass 0x00bdc0c7 (verified) over the hero's state. */
typedef struct mu_move_hero {
    int32_t level;          /* 0x00a00367([0x01d1df1c]) */
    int32_t zen;            /* [[0x01d1df18] + 0x2d70] */
    uint8_t pk_level;       /* hero +0x1f (> 4: zen x 50) */
    uint8_t strife_ok;      /* hero +0x1e (0: strife maps refused) */
    uint8_t wings_slot;     /* inventory slot 7's 0x0095fc2e(6) */
    int32_t helper_type;    /* 0x0106c5e9(hero): the ridden/helper item type */
    uint8_t helper_flies;   /* item kind check 0x00cd6017(helper, 0x4f) */
    int32_t flying;         /* 0x00b9b476(hero) (> 0 enables Icarus) */
    uint8_t kalima;         /* the window's +0x7c */
    uint8_t server_flag;    /* 0x01072a7f() */
    uint8_t event_a, event_b; /* 0x00b3b42e / 0x00a9698b (the GlobalText[0x3a]%d maps) */
} mu_move_hero;

/* GlobalText for the name rules (0x37, 0x25, 0x29d, 0xa7e, 0x3a). */
typedef const char *(*mu_move_text_fn)(void *user, int32_t index);

/* Required zen of a record for the hero (x 50 when pk_level > 4). */
int32_t mu_move_required_zen(const mu_move_record *r, const mu_move_hero *hero);
/* Sets +0x14 (and clears +0x16) for every entry. */
void mu_move_availability(mu_move_entry *entries, int n, const mu_move_hero *hero, mu_move_lookup_fn lookup,
                          mu_move_text_fn text, void *user);

/* One list row as SetMoveMapList receives it (0x00bdd08d, verified). */
typedef struct mu_move_row {
    int32_t order_idx;      /* the row's position (orderIdx) */
    char strife[64];        /* GlobalText[0xbab] when strife, else "" */
    char map[64];           /* record name */
    char level[16], zen[16];/* _itoa(min level), _itoa(required zen) */
    int checked;            /* favourite (0x00bdcaf3) */
    int disabled;           /* !enabled */
    int32_t map_idx;        /* entry key */
} mu_move_row;
#define MU_MOVE_TEXT_STRIFE 0xbab
/* The favourites (window +0x8c: five {u16 flag, u16 key} pairs, 0xffff = empty).
 * 0x00bdcaf3(0xffff, key) (verified): 1 when a slot holds the key. */
typedef struct mu_move_favourite { uint16_t flag, key; } mu_move_favourite;
int mu_move_is_favourite(const mu_move_favourite favs[5], int32_t key);
void mu_move_row_make(const mu_move_entry *e, int32_t index, const mu_move_hero *hero, int checked,
                      mu_move_lookup_fn lookup, mu_move_text_fn text, void *user, mu_move_row *out);

/* The special worlds rule 0x00bdc7bd (verified): current world 30, 34 or 79,
 * or target key 24, 44 or 48: the click stops the MU Helper first. */
int mu_move_special(int32_t current_world, int32_t key);

/* The click 0x00bdc813(index) (verified for its decision and packets). */
typedef struct mu_move_click_result {
    int accepted;           /* 0: the entry is not enabled (nothing happens) */
    int helper_stop;        /* MU Helper stopped (special rule) */
    int helper_packet;      /* C1 BF 51 01 sent (the helper was running) */
    uint8_t packet[16];     /* the move request: C1 len 8E 02, key dword, key word, 0xff */
    int packet_length;
} mu_move_click_result;
/* move_key: the window's +0x84 after 0x00cda52b (the server's key, 0x8E 01;
 * the transform is opaque, the caller passes its result). */
void mu_move_click(mu_move_entry *entries, int n, int32_t index, int32_t current_world, int helper_running,
                   uint32_t move_key, mu_move_click_result *out);
/* The move request bytes alone (0x00b3b866, verified). */
int mu_move_request_packet(uint32_t move_key, uint16_t key, uint8_t tail, uint8_t *out, size_t cap);

/* ---- gates ----------------------------------------------------------------------------------------- */

typedef struct mu_gate {   /* Gate record (0x34 bytes, Lang table 0x06fbabac, lookup 0x0110cbaf) */
    int32_t index;          /* +0x04 (the map key) */
    int32_t flag;           /* +0x08 (1: entrance) */
    int32_t world;          /* +0x0c */
    int32_t x1, y1, x2, y2; /* +0x10.. */
    int32_t target;         /* +0x20 */
    int32_t dir;            /* +0x24 */
    int32_t min_level, max_level;   /* +0x28, +0x2c */
} mu_gate;

typedef struct mu_gate_hero {
    int32_t world, tile_x, tile_y, level;
    int32_t loading_world;  /* [0x0b437c14] (LoadingWorld) */
    uint8_t busy;           /* hero +0x2c, +0x31c8, the window/state predicates the test checks first */
    uint8_t wings_kind6;    /* inventory slot 7 holds an item whose +0x250 kind is 6 (wings) */
    int32_t helper_type;    /* 0x0106c5e9(hero) */
    uint8_t helper_flies;   /* 0x00c92e9a(helper) == 1 or the item kind check 0x4f */
    int32_t hero_3230;      /* hero +0x3230 (> 0 lets the hero enter Icarus) */
    uint8_t throttle;       /* the 3 s throttle (0x0095f75d +6 / +8) or [0x06fca01c] stops the request */
} mu_gate_hero;

typedef struct mu_gate_result {
    int gate;               /* the entrance gate found, -1 none */
    int target;             /* its target gate */
    int refused;            /* 1 level (GlobalText[350] with %d), 2 Icarus without wings (GlobalText[263]) */
    int32_t loading_world;  /* the value LoadingWorld gets (50 refused, 9999999 sent), else unchanged */
    uint8_t packet[8];      /* C1 00 1C 00 gate(lo) gate(hi) 00 00: the request struct (the builder XORs bytes
                               3..7 and sends it with the C3 flag) */
    int packet_length;
    int helper_stop;        /* the request leaves or enters world 30/31: MU Helper stopped, Data\Macro.txt loaded */
} mu_gate_result;
#define MU_GATE_TEXT_LEVEL 350
#define MU_GATE_TEXT_WINGS 263

typedef const mu_gate *(*mu_gate_lookup_fn)(void *user, int32_t index);

/* The per-frame entrance test 0x016a4608 (verified for the gate, refusal and
 * request decisions; the event-world early exits are static).  gates: the
 * table in key order. */
void mu_gate_check(const mu_gate *gates, int n, mu_gate_lookup_fn lookup, void *user, const mu_gate_hero *hero,
                   mu_gate_result *out);
/* A tile inside a gate's rectangle (inclusive). */
int mu_gate_contains(const mu_gate *g, int32_t tile_x, int32_t tile_y);

/* ---- teleport answer -------------------------------------------------------------------------------- */

typedef struct mu_teleport {
    uint16_t number;        /* [4] (0: same-map reposition) */
    uint16_t world;         /* [6] */
    uint8_t x, y, dir;      /* [8], [9], [10] */
} mu_teleport;

/* The packet's fields (0x0128136d reads them at these offsets, static). */
int mu_teleport_parse(const uint8_t *packet, size_t length, mu_teleport *out);
/* Hero position in world units: ((float)x + 0.5) * 100 (static). */
void mu_teleport_position(const mu_teleport *t, float out[2]);
/* Hero angle z from the direction byte: ((float)dir - 1) * 45 (static). */
float mu_teleport_angle(const mu_teleport *t);
/* The world changes when the number is not 0 and the world differs (static). */
int mu_teleport_changes_world(const mu_teleport *t, int32_t current_world);
#define MU_TELEPORT_TEXT_MOVED 484        /* "%s%s": GlobalText[484] + map name */
#define MU_TELEPORT_LOADING_WORLD 30      /* LoadingWorld after a world change: the render skips while >= 30 */

#ifdef __cplusplus
}
#endif

#endif
