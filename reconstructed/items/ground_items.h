#ifndef MU_GROUND_ITEMS_H
#define MU_GROUND_ITEMS_H

/* NATIVE-ITEMS-001: the client's dropped items (docs/research/client-ground-items.md).
 *
 * The client keeps dropped items in a pool of 1000 ITEM_t records of 0x560
 * bytes at 0x0b4780c8: a word key, an ITEM (the item instance, +0x04), an
 * OBJECT (+0x130), the label view byte (+0x508), the label text (+0x509) and
 * the label colour class (+0x55c). This library reproduces, from the client's
 * instructions:
 *
 *   ReceiveCreateItemViewport 0x0122c216 (packet 0x20)    mu_gi_viewport_parse
 *   CreateItem 0x016daa27                                  mu_gi_create
 *   ItemObjectAttribute 0x016da00b                         mu_gi_object_attribute
 *   ItemAngle 0x01802a66 (lifted, item_angle_table.h)      mu_gi_item_angle
 *   the name builder 0x017ea422 (lifted, item_name_table.h) mu_gi_name_build
 *   MoveItems 0x017ea1aa and the sparkle 0x017f7290        mu_gi_move_item
 *   RenderItems 0x017e9495 (the per-item plan)             mu_gi_render_plan
 *   SelectItem 0x016b4fc0                                  mu_gi_select
 *   the label colour 0x00c84f00                            mu_gi_label_color
 *   the label anchor of addItem 0x00c83e2a / the per-frame
 *   position loop of 0x00c81d1e (static readings)          mu_gi_label_anchor
 *   the pick-up result and drop sounds                     mu_gi_pickup_sound
 *
 * Each function names its client address; scripts/validate_items.py compares
 * them with the client's instructions executed under Unicorn. Engine services
 * (terrain height and light, rand(), sin, sqrt, the Item.bmd record lookup,
 * GlobalText, sounds, the label window) come from the caller through mu_gi_host.
 *
 * Field comments give the client offset inside the ITEM (it->data), the
 * OBJECT (it->object) or the pool record. Names are authored. */

#include <stddef.h>
#include <stdint.h>

#define MU_GI_ITEMS 1000            /* pool size (loops of 0x3e8) */
#define MU_GI_RECORD_BYTES 0x560    /* pool stride */
#define MU_GI_POOL 0x0b4780c8u      /* pool address in the client */
#define MU_GI_MODEL_ITEM 0xae6      /* model index of item code 0 */
#define MU_GI_CODE_ZEN 0x1c0f       /* group 14 index 15 */
#define MU_GI_NAME_BYTES 0x53       /* +0x509 .. +0x55b */
#define MU_GI_VIEWPORT_MAX 75       /* packet 0x20 count cap (0x4b) */
#define MU_GI_ENTRY_BYTES 19        /* key 2, x, y, item 15 */

/* ---- record lookup (Item.bmd, NATIVE-DATA-002 names) ---- */
typedef struct mu_gi_record {
    int32_t present;                /* the item script has a record for the code */
    uint8_t kind_a, kind_b, type;   /* +0x250, +0x251, +0x252 */
    uint8_t pc_room;                /* +0x2b0 */
    const char *name;               /* +0x210 */
} mu_gi_record;

/* ---- item instance (ITEM at pool +4; offsets relative to the ITEM) ---- */
typedef struct mu_gi_item_data {
    int32_t code;                   /* +0x10 group*512 + index (-1 after the reset) */
    int32_t level;                  /* +0x14 level byte (bits 3..6 level, 7 skill, 2 luck, 0..1 option); zen amount */
    uint8_t durability;             /* +0x38 */
    uint8_t excellent;              /* +0x3a option byte & 0x7f */
    uint8_t ancient;                /* +0x3b */
    uint8_t flag_72;                /* +0x72 (packet byte 5 bit 3) */
    uint8_t sockets[5];             /* +0x73 .. +0x77 */
    int32_t element;                /* +0x84 (pentagram/errtel kinds 8, 0x19, 0x1a) */
    uint8_t flag_92;                /* +0x92 period item (0x00cd0995(2)) */
    uint8_t flag_98;                /* +0x98 (0x00cd0995(1)) */
} mu_gi_item_data;

/* ---- the OBJECT of a dropped item (pool +0x130; offsets relative to the OBJECT) ---- */
typedef struct mu_gi_object {
    uint8_t live;                   /* +0x00 (SetLive 0x0129f4a5, getter 0x0095f977) */
    uint8_t field_04;               /* +0x04 */
    uint8_t light_enable;           /* +0x05 */
    uint8_t visible;                /* +0x0b TestFrustrum2D result */
    uint8_t field_0c;               /* +0x0c */
    int32_t field_14, field_18, field_1c; /* +0x14 element copy; +0x18/+0x1c pentagram lookups (render args) */
    uint16_t action, prior_action;  /* +0x2a, +0x2c */
    int16_t screen_x, screen_y;     /* +0x50, +0x52 (RenderItems: projection of position + 30 z, 640x480) */
    int32_t type;                   /* +0x5c model index */
    int32_t sparkle;                /* +0x60 step counter of the sparkle (1 at creation) */
    int32_t hidden_mesh;            /* +0x68 */
    int32_t blend_mesh;             /* +0x74 */
    float scale;                    /* +0xa0 */
    float blend_light, blend_u, blend_v; /* +0xa8, +0xac, +0xb0 */
    float field_bc, field_c0;       /* +0xbc, +0xc0 */
    float gravity;                  /* +0xc8 */
    float frame, prior_frame;       /* +0xd0, +0xd4 */
    float alpha;                    /* +0xdc */
    float light[3];                 /* +0xec */
    float bbox_min[3], bbox_max[3]; /* +0x128, +0x134 */
    float position[3];              /* +0x158 */
    float angle[3];                 /* +0x164 */
    float head_angle[3];            /* +0x170 */
} mu_gi_object;

typedef struct mu_gi_item {
    uint16_t key;                   /* pool +0x000 */
    mu_gi_item_data data;           /* pool +0x004 */
    mu_gi_object object;            /* pool +0x130 */
    uint8_t label_view;             /* pool +0x508 copy of the label window's view flag at creation */
    char name[MU_GI_NAME_BYTES];    /* pool +0x509 label text */
    int32_t name_class;             /* pool +0x55c label colour class (mu_gi_label_color) */
} mu_gi_item;

/* ---- engine services ---- */
typedef struct mu_gi_host {
    void *context;
    const mu_gi_record *(*record)(void *context, int32_t code);   /* item script; NULL when absent */
    float (*terrain_height)(void *context, float x, float y);    /* RequestTerrainHeight 0x016cc9e2 */
    void (*terrain_light)(void *context, float x, float y, float out[3]); /* RequestTerrainLight 0x016cb08d */
    int32_t (*rand)(void *context);                               /* rand() 0x01989721 */
    float (*sin)(void *context, float x);                         /* 0x009681bd */
    float (*sqrt)(void *context, float x);                        /* 0x00961a07 */
    void (*play_sound)(void *context, int32_t id);                /* SND_Play 0x00a6ac96(id, object, 0) */
    /* Opaque predicates: 0x00cd1534 is runtime-patched (jump into an unanalysed
     * module), so its answer is an input (socket-like item). */
    int32_t (*socket_like)(void *context, const mu_gi_item_data *item);
    float world_time;               /* [0x06fce370] ms */
    int32_t world;                  /* [0x01cf15fc] */
} mu_gi_host;

/* ---- packet 0x20 (ReceiveCreateItemViewport 0x0122c216, verified) ----
 * count = packet[4] capped at 75; entries of 19 bytes from +5: key big-endian
 * (bit 15 = drop flag, key & 0x7fff, keys >= 1000 become 0), tile x, y, then
 * the 15 item bytes. Position = ((x + 0.5) * 100, (y + 0.5) * 100); z is left
 * to CreateItem. The handler resets the ITEM (0x00ccc144), stores the key and
 * the label view flag (the label window's +0x5c, 1 without a window), then
 * calls CreateItem. */
typedef struct mu_gi_viewport_entry {
    int32_t index;                  /* pool slot = key */
    int32_t drop;                   /* CreateItem's create flag */
    float x, y;
    const uint8_t *item;            /* 15 bytes */
} mu_gi_viewport_entry;
int32_t mu_gi_viewport_parse(const uint8_t *packet, mu_gi_viewport_entry *out, int32_t capacity);

/* Item code of the 15 packet bytes (0x00f09ddc): b0 | (b3 & 0x80) << 1 | (b5 & 0xf0) << 5 | (b5 & 1) << 13. */
int32_t mu_gi_item_code(const uint8_t *bytes);

/* ---- CreateItem 0x016daa27 ----
 * The sub-routines it calls are hooks so that a validator can record them;
 * mu_gi_default_hooks binds the reconstructions below. */
typedef struct mu_gi_create_hooks {
    void *context;
    void (*reset)(void *context, mu_gi_item_data *item);                 /* 0x00ccc144 */
    void (*set_live)(void *context, mu_gi_object *o, int32_t live);       /* 0x0129f4a5 */
    void (*object_attribute)(void *context, mu_gi_object *o);             /* 0x016da00b */
    void (*item_angle)(void *context, mu_gi_object *o);                   /* 0x01802a66 */
    void (*name_build)(void *context, mu_gi_item *it);                    /* 0x017ea422 */
    /* CreateEffect 0x013c0eaa for the firecracker boxes (types 0x3898/0x3899) */
    void (*create_effect)(void *context, int32_t type, const float position[3], mu_gi_object *owner,
                          int32_t sub);
    /* the pentagram/errtel lookups for kinds 8, 0x19, 0x1a with element 0..5
     * (0x010d2013 on 0x06fbb330 and a std::map; not reconstructed): returns 1
     * and fills object +0x18 / +0x1c, or 0 to leave them */
    int32_t (*pentagram)(void *context, const mu_gi_item_data *item, int32_t *field_18, int32_t *field_1c);
} mu_gi_create_hooks;

enum { MU_GI_CREATE_NO_RECORD = 0, MU_GI_CREATE_OK = 1 };
/* Returns MU_GI_CREATE_NO_RECORD when the code has no record (the client
 * returns before SetLive: the slot keeps its previous object). */
int32_t mu_gi_create(mu_gi_item *it, const uint8_t bytes[15], const float position[3], int32_t drop,
                     const mu_gi_host *host, const mu_gi_create_hooks *hooks);
void mu_gi_default_hooks(mu_gi_create_hooks *hooks, const mu_gi_host *host);

/* The drop sound of CreateItem (static note: the first jewel test is a
 * runtime-patched instruction at 0x016dad9b; its code 0x1c0d is inferred from
 * the same list in the pick-up handler 0x012424bd). -1: no sound (no drop flag). */
int32_t mu_gi_drop_sound(int32_t code, int32_t drop);
/* The pick-up result sound (0x012424bd, static): jewels 0x45, 0x1c29 0x2d3, else 0x1d. */
int32_t mu_gi_pickup_sound(int32_t code);

/* ---- ItemObjectAttribute 0x016da00b ----
 * Defaults (light 0.3, alpha 1, scale 0.8, blend mesh -1, ...) then the
 * type's case (blend mesh, blend light from sin(time) or rand(), UV scroll,
 * scale). The sub-object reset 0x01295f18(o + 0x358) is not modelled. */
void mu_gi_object_attribute(mu_gi_object *o, const mu_gi_host *host);

/* ---- ItemAngle 0x01802a66 (lifted; generated item_angle_table.h) ---- */
typedef struct mu_gi_angle_env {
    mu_gi_record record;            /* record of o->type - 0xae6 (present 0: none) */
    struct {
        int32_t present;            /* per-index table entry (0x009c2aea / 0x01807c32) */
        uint32_t scale_bits;        /* +0x25c */
        uint32_t angle_z_bits;      /* +0x260 */
    } pet;
} mu_gi_angle_env;
int32_t mu_gi_item_angle(mu_gi_object *o, const mu_gi_angle_env *env);

/* ---- the name builder 0x017ea422 (lifted; generated item_name_table.h) ----
 * Sets it->name_class and it->name. GlobalText and the other text tables come
 * from the environment (Lang.mpr is not decoded: callers pass stand-ins). */
typedef struct mu_gi_name_env {
    void *context;
    const mu_gi_record *(*record)(void *context, int32_t code);
    const char *(*text)(void *context, int32_t id);           /* GlobalText 0x0095f027 on 0x06fbab48 */
    const char *(*prefix)(void *context, const mu_gi_item_data *item); /* plain-item prefix 0x009953ef */
    int32_t (*set_tier)(void *context, int32_t code);         /* 0x011447ac on 0x06fbae4c, record +0x24 */
    const char *(*table_1e)(void *context, int32_t key);      /* 0x00961620 on 0x06fbb138, entry +8 */
    const char *(*text_string)(void *context, int32_t id);    /* 0x011753c3 on 0x06fbab48 */
    int32_t (*level_key)(void *context, int32_t level);       /* int table 0x01cf15bc[level] */
    const char *(*level_table_text)(void *context, int32_t key); /* 0x011427c7 on 0x06fbb664 */
    int32_t label_window;           /* the hudPlayerName window exists (addItem is called) */
} mu_gi_name_env;

#define MU_GI_NAME_LOG 24
typedef struct mu_gi_name_call {
    int32_t kind;                   /* 1 sprintf, 2 strcat, 3 strcpy, 4 strncpy, 5 memset, 6 glColor3f, 7 addItem */
    char text[96];                  /* the destination after the call (sprintf/strcat/strcpy), or the arguments */
} mu_gi_name_call;
typedef struct mu_gi_name_sink {
    mu_gi_name_call calls[MU_GI_NAME_LOG];
    int32_t count;
    int32_t label_add;              /* addItem was called */
    float gl_color[3];
} mu_gi_name_sink;
void mu_gi_name_build(mu_gi_item *it, const mu_gi_name_env *env, mu_gi_name_sink *sink);

/* ---- MoveItems 0x017ea1aa, one record (verified) ----
 * z += gravity; gravity -= 6; floor = RequestTerrainHeight + 30 (+40 for types
 * 0xae6..0x16e5); when floor >= z: z = floor and ItemAngle; else the falling
 * spin: Angle[1] (shields 0x16e6..0x18e5) or Angle[0] = -gravity * 10. Then
 * the sparkle 0x017f7290: every 48th step (counter +0x60 % 48 == 0 before its
 * increment) two particles 0x7f66 (subtypes 0 and 1) at position +
 * VectorRotate((rand%32+16, 0, rand%32+16), AngleMatrix(Angle)). */
typedef struct mu_gi_move_hooks {
    void *context;
    void (*item_angle)(void *context, mu_gi_object *o);
    /* CreateParticle 0x0168fafd(type, position, angle, light, subtype, scale, 0, 0) */
    void (*create_particle)(void *context, int32_t type, const float position[3], const float angle[3],
                            const float light[3], int32_t subtype, float scale);
} mu_gi_move_hooks;
/* Returns 1 when the item landed this step (ItemAngle ran), 0 while falling, -1 when not live. */
int32_t mu_gi_move_item(mu_gi_object *o, const mu_gi_host *host, const mu_gi_move_hooks *hooks);

/* ---- RenderItems 0x017e9495, the plan of one record (verified) ---- */
typedef struct mu_gi_render_call {
    int32_t type;                   /* RenderPartObject 0x017e63f4 arguments */
    float position[3];              /* the object's position at the call (zen piles move it) */
    float light[3];
    float alpha;
    int32_t item_level;             /* ITEM +0x14 */
    int32_t option;                 /* ITEM +0x3a != 0 */
    int32_t ext;                    /* ITEM +0x3b */
    int32_t a12, a13;               /* object +0x18/+0x1c for kinds 8/0x19/0x1a, else -1, -1 */
} mu_gi_render_call;

#define MU_GI_RENDER_CALLS 80
typedef struct mu_gi_render_plan_t {
    int32_t visible;                /* TestFrustrum2D(x/100, y/100, 400): o->visible */
    int32_t pose_model;             /* model posed by Animation 0x012b5064 (Player 0xa91 for armour) */
    int32_t pose_skin;              /* GetBaseClass(hero class) 0x0095f5cc -> model +0xa4 (input) */
    float pose_head_offset;         /* 0x01805f6e(type, model): model +0x90 */
    int32_t render_model;           /* model the calls draw */
    int32_t abort;                  /* the model getter returned NULL: the client leaves RenderItems */
    mu_gi_render_call calls[MU_GI_RENDER_CALLS];
    int32_t call_count;
    int16_t screen_x, screen_y;     /* o +0x50/+0x52 after the calls */
} mu_gi_render_plan_t;

typedef struct mu_gi_render_env {
    int32_t visible;                /* TestFrustrum2D answer (input) */
    int32_t pose_model_exists, render_model_exists; /* model getter non-NULL */
    int32_t world_float;            /* 0x009b0418(world) == 1 (input) */
    int32_t world_39_state;         /* world 0x27: the [[0x009a6ef3]+0x78] predicate 0x009a645f (input) */
    float special_height;           /* 0x00deeb4e(x, y) for world_float */
    const int32_t *random_table;    /* 100 ints at 0x06fc9cb8 (rand() % 360 at WinMain after srand(time)) */
    /* 0x0184a244: world -> 640x480 screen (camera matrix, perspective, centre) */
    void (*project)(void *context, const float world[3], int32_t *x, int32_t *y);
    void *context;
    int32_t kind_option;            /* item kind A 8/0x19/0x1a (predicates 0x0095fc2e) */
} mu_gi_render_env;
void mu_gi_render_plan(const mu_gi_item *it, int32_t index, const mu_gi_host *host, const mu_gi_render_env *env,
                       mu_gi_render_plan_t *plan);
/* The zen pile: number of coins min(max(sqrt(amount)/2, 3), 80) (truncation as the client's cvttss2si/cdq/sar). */
int32_t mu_gi_zen_coins(int32_t amount, const mu_gi_host *host);

/* ---- TestFrustrum 0x016ccc14(position, range) (verified) ----
 * RenderItems' visibility: for the five planes of CreateFrustrum (normals
 * 0x0bdb546c, distances 0x0b6b53e4) d = ((x*nx + y*ny) + z*nz) + dist; 0 as
 * soon as -range > d (comiss), else 1. RenderItems passes range 400. */
int32_t mu_gi_test_frustum(const float normal[5][3], const float distance[5], const float position[3], float range);

/* ---- SelectItem 0x016b4fc0 (verified) ----
 * Every live, visible item gets LightEnable 1 and light 0.2; the first whose
 * OBB (+0x31c) the mouse ray hits (0x018500bf) gets LightEnable 0, light 1.5
 * and is returned; -1 when none. */
typedef int32_t (*mu_gi_ray_test)(void *context, int32_t index);
int32_t mu_gi_select(mu_gi_item *items, int32_t count, mu_gi_ray_test hit, void *context);

/* ---- the label ----
 * The labels are the hudPlayerName GFx movie's item list (addItem/removeItem/
 * clearAllItem/setItemView). Colour: class -> "#RRGGBB" (0x00c84f00, verified);
 * text: "<font color='%s'>%s</font>" with the name. */
const char *mu_gi_label_color(int32_t name_class);
/* The label anchor in screen pixels (static reading of 0x00c83e2a and the
 * per-frame loop in 0x00c81d1e): the hovered item (SelectedItem 0x01cf114c)
 * follows the cursor (x = mouse x * sx, y = (mouse y - 5) * sy); the others
 * project position + (0, 0, 35) through 0x0184a3ce. */
typedef struct mu_gi_label_env {
    void (*project)(void *context, const float world[3], float *x, float *y);  /* 0x0184a3ce */
    void *context;
    int32_t selected;               /* 0x01cf114c */
    int32_t mouse_x, mouse_y;       /* 0x0bdc5ad8 / 0x0bdc5adc */
    float scale_x, scale_y;         /* 0x06fbcd94 / 0x06fbcd98 */
} mu_gi_label_env;
#define MU_GI_LABEL_HEIGHT 35       /* window +0x1c (constructor 0x00afaff8) */
#define MU_GI_LABEL_MOUSE_DY 5      /* window +0x20 */
void mu_gi_label_anchor(const mu_gi_item *it, int32_t index, const mu_gi_label_env *env, float *x, float *y);

/* ItemNameMC.text (hudPlayerName ActionScript, static reading): the text
 * field is autoSize html, width = textWidth + 6, height = textHeight + 4,
 * placed at x = -floor(width / 2), y = -floor(height + 14) from the anchor;
 * the background is 3 px wider on each side and 2 px taller above and below. */
typedef struct mu_gi_label_box {
    float text_x, text_y, text_w, text_h;
    float bg_x, bg_y, bg_w, bg_h;
} mu_gi_label_box;
void mu_gi_label_layout(float text_width, float text_height, mu_gi_label_box *box);

#endif
