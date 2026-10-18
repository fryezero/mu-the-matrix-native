/* Dropped items in the walk-around world (NATIVE-ITEMS-001, docs/research/client-ground-items.md).
 *
 * The client side of items on the ground, joined to the mu_walk session:
 *
 *   - the item pool of 1000 ITEM_t records and CreateItem 0x016daa27 with
 *     ItemObjectAttribute, ItemAngle and the name builder (reconstructed/items,
 *     verified against the client in Unicorn);
 *   - every logic step MoveItems 0x017ea1aa (the fall from 180 units with
 *     gravity 20 - 6 per step, the spin, the landing pose) and the sparkle
 *     0x017f7290 (particles 0x7f66 every 48 steps, handed to the legacy
 *     particle module, which counts the kind as unsupported);
 *   - every frame RenderItems 0x017e9495 (the zen pile, the light from the
 *     terrain plus the selection light, the item render passes of
 *     NATIVE-RENDERCHAR-001 through a caller callback) and SelectItem
 *     0x016b4fc0 (light 0.2, 1.5 for the item under the mouse ray);
 *   - the labels of the hudPlayerName movie (addItem): the name and colour
 *     class from the name builder, the colour string of 0x00c84f00, the
 *     anchor (position + 35 projected through 0x0184a3ce; the hovered item's
 *     label follows the cursor) and the ItemNameMC layout; Alt toggles the
 *     view (setItemView, default on);
 *   - picking up: a click on the selected item walks the hero to its tile
 *     and, within 1.5 tiles (0x016a52a6), sends the request; the space bar
 *     takes the nearest item within 300 units (0x00efd9ab); the answer
 *     removes the item and plays the pick-up sound (0x012424bd).
 *
 * DEMO, not client behaviour (there is no server): which items drop, when
 * (a fixed latency after a monster's death), where (the monster's position
 * plus a small offset), the zen amounts, the pick-up answer and its latency,
 * the despawn time. Viewer choices: the mouse ray test is a box of the
 * object's +-30 bounding box (the client tests its OBB +0x31c); label text uses mu_ui_font (CoreText) with a stand-in face and
 * the GlobalText strings the names need are English stand-ins (Lang.mpr is
 * not decoded); the label background is a translucent black box. */
#ifndef MU_ITEMS_NATIVE_H
#define MU_ITEMS_NATIVE_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include "../../reconstructed/items/ground_items.h"
#include "mu_bmd.h"
#include "mu_character.h"
#include "mu_data.h"
#include "mu_model.h"
#include "mu_scene.h"
#include "mu_textures.h"
#include "mu_ui_font.h"
#include "mu_walk.h"
#include "mu_world_actors.h"

struct mu_combat;
struct mu_world_particles;

#define MU_WORLD_ITEM_MODELS 64
#define MU_WORLD_ITEM_EVENTS 64
#define MU_WORLD_ITEM_TABLE 24
#define MU_WORLD_ITEM_LABELS 96

typedef struct mu_world_items_config {
    uint32_t seed;              /* demo drop choices; also the client rand() state (the client seeds it with time()) */
    int32_t drop_latency;       /* demo: steps from the death message to the drop (item viewport) message */
    int32_t pickup_latency;     /* demo: steps from the pick-up request to the answer */
    int32_t despawn_steps;      /* demo: the server removes an item after this many steps (0: never) */
    int32_t drop_chance;        /* demo: percent of kills that drop something */
    int32_t quality;            /* graphics option of the item render (glow level cap) */
    float glow_color[3];        /* EnchantEffect colour (NATIVE-RENDERCHAR-001 viewer parameter) */
    const char *font_face;      /* label font (viewer choice) */
    int32_t font_height;
} mu_world_items_config;

void mu_world_items_default_config(mu_world_items_config *config);

/* A model the items draw (Data/Item/..., resolved through Item.bmd like the getter 0x00eaa8cf). */
typedef struct mu_world_item_model {
    int32_t type;
    int loaded, failed;
    mu_bmd bmd;
    mu_model model;
    mu_textures textures;
} mu_world_item_model;

typedef struct mu_world_item_drop {      /* one entry of the demo drop table */
    int32_t code, level_max, weight;
    uint8_t excellent_chance, ancient_chance;   /* percent */
    int32_t zen_min, zen_max;
} mu_world_item_drop;

typedef struct mu_world_item_event {
    int32_t step, kind;         /* 1 drop, 2 pick-up answer */
    int32_t code, level, zen, slot;
    uint8_t excellent, ancient;
    float x, y;
} mu_world_item_event;

typedef struct mu_world_item_label {
    int32_t index;
    char text[MU_GI_NAME_BYTES + 8];
    const char *color;          /* "#RRGGBB" (0x00c84f00) */
    float rgb[3];
    float anchor[2];            /* window pixels */
    mu_gi_label_box box;        /* relative to the anchor */
    int32_t text_width, text_height;
    int hovered;
} mu_world_item_label;

typedef struct mu_world_items_stats {
    uint32_t drops, creates, no_record, lands, sparkles, sparkle_particles, picks_requested, picks_done, despawns;
    uint32_t space_picks, hover_frames, labels, models_drawn, model_missing, sounds, alt_toggles, kills_seen;
    uint32_t render_calls, zen_coins;
} mu_world_items_stats;

typedef struct mu_world_items {
    mu_world_items_config config;
    mu_gi_item pool[MU_GI_ITEMS];
    int32_t created_step[MU_GI_ITEMS];
    mu_walk *walk;
    const mu_world *map;
    struct mu_world_particles *particles;
    mu_data_table item_table;
    int has_table;
    mu_gi_record *records;      /* per code 0..0x2c00, lazily filled */
    uint8_t *record_state;      /* 0 unknown, 1 present, 2 absent */
    char (*record_names)[65];
    int32_t random_table[100];  /* 0x06fc9cb8: rand() % 360 at WinMain */
    uint32_t crt_seed;          /* rand() 0x01989721 state */
    uint32_t demo_seed;
    mu_gi_host host;
    int32_t view;               /* hudPlayerName +0x5c: label view (Alt toggles, starts 1) */
    int32_t selected;           /* SelectedItem 0x01cf114c */
    int32_t pickup_target;      /* MoveHero's pick-up mode: the item walked to, -1 none */
    int32_t pickup_force;       /* 0x0b43656d: the space bar's pick-up skips the range test */
    int32_t pickup_wait;        /* the request was sent; waiting for the answer */
    mu_world_item_event events[MU_WORLD_ITEM_EVENTS];
    int32_t event_count;
    uint8_t prev_dead[MU_WORLD_ACTORS_MAX];
    mu_world_item_model models[MU_WORLD_ITEM_MODELS];
    int32_t model_count;
    mu_character *mannequin;    /* the Player skeleton armour parts are posed with (RenderItems poses model 0xa91) */
    int mannequin_failed;
    mu_world_item_drop table[MU_WORLD_ITEM_TABLE];
    int32_t table_count, table_weight;
    mu_ui_font font;
    int has_font;
    char game_root[1024];
    void (*play_sound)(void *context, int32_t id);
    void *sound_context;
    int32_t step;
    mu_world_items_stats stats;
    char log[32][112];
    int32_t log_count;
} mu_world_items;

/* Loads Item.bmd (Data/Local/item.bmd) and the label font; binds the session
 * (walk may not be NULL). Returns 0, or 1 with a message. */
int mu_world_items_open(mu_world_items *items, const char *game_root, mu_walk *walk, const mu_world_items_config *config,
                        char *error, size_t error_size);
void mu_world_items_close(mu_world_items *items);

/* The demo server's item viewport message for one item (CreateItem with the
 * drop flag: the fall from 180 units and the drop sound). code = group*512 +
 * index; level_byte as the client's packet byte 1 (level << 3 | skill 0x80 |
 * luck 4 | option 0..3); zen is the amount for code 0x1c0f. Returns the pool
 * slot, or -1 (no free slot or no Item.bmd record). */
int32_t mu_world_items_drop(mu_world_items *items, int32_t code, int32_t level_byte, uint8_t excellent, uint8_t ancient,
                            int32_t zen, float x, float y, int32_t drop_flag);

/* Watches the combat monsters (call after mu_combat_step): a death message
 * schedules a demo drop. combat may be NULL. */
void mu_world_items_watch_combat(mu_world_items *items, const struct mu_combat *combat);
/* One logic step: the demo server's messages, MoveItems with the sparkle, the
 * hero's pick-up mode and the despawn. */
void mu_world_items_step(mu_world_items *items);
/* Before MoveHero's walk and click code: a left click while an item is
 * selected starts the pick-up walk and consumes the click (returns 1). */
int mu_world_items_pre_step(mu_world_items *items);
/* Render pass, before drawing: SelectItem over the mouse ray (alt: items are
 * selected first; otherwise only when no_character is set, i.e. no monster
 * is under the cursor). Returns SelectedItem. */
int32_t mu_world_items_select(mu_world_items *items, int alt, int no_character);
/* Keys: Alt press toggles the label view, space takes the nearest item. */
void mu_world_items_alt(mu_world_items *items);
int mu_world_items_space(mu_world_items *items);

/* Drawing: per RenderPartObject call of RenderItems, the posed model with
 * the call's light, alpha and item glow. The callback draws before returning. */
typedef struct mu_world_item_draw {
    const mu_model *model;
    const mu_textures *textures;
    int32_t slot;               /* model cache slot (GL texture sets) */
    int32_t type;
    int32_t level;              /* 0..15 */
    int32_t option1, ext;
    float light[3];
    float alpha;
    int32_t has_record;         /* the Item.bmd record of type - 0xae6 (glow kinds) */
    uint8_t kind_a, kind_b, item_kind;
} mu_world_item_draw;
typedef void (*mu_world_item_draw_fn)(void *context, const mu_world_item_draw *draw);
int32_t mu_world_items_draw(mu_world_items *items, mu_world_item_draw_fn draw, void *context);

/* The labels to draw this frame (view on: every live, visible item; view off: none). */
int32_t mu_world_items_labels(mu_world_items *items, mu_world_item_label *labels, int32_t max);
/* RGBA bitmap of a label's text (white glyphs, alpha from coverage), width x height = text extent. */
int mu_world_items_label_bitmap(mu_world_items *items, const mu_world_item_label *label, uint8_t *rgba, int32_t width,
                                int32_t height);
/* Composites a label (background and text) into an RGBA frame (software renders). */
void mu_world_items_label_blit(mu_world_items *items, const mu_world_item_label *label, uint8_t *frame, int32_t width,
                               int32_t height);

/* Scripted items for headless runs: "F:drop:CODE[:LEVELBYTE[:X,Y]] F:alt F:space F:pick:N F:hover:N" (hover
 * moves the mouse onto item N's label anchor, pick clicks it). */
#define MU_WORLD_ITEM_SCRIPT 32
typedef struct mu_world_item_script_entry {
    int32_t frame;
    char verb[8];
    int32_t a, b;
    float x, y;
    int has_xy;
} mu_world_item_script_entry;
typedef struct mu_world_item_script {
    mu_world_item_script_entry items[MU_WORLD_ITEM_SCRIPT];
    int32_t count;
} mu_world_item_script;
int mu_world_items_script_parse(mu_world_item_script *script, const char *text);

int32_t mu_world_items_live(const mu_world_items *items);
void mu_world_items_report_frame(const mu_world_items *items, FILE *out, int32_t frame);
void mu_world_items_report_summary(const mu_world_items *items, FILE *out);

#endif
