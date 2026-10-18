#ifndef MU_CHARSEL_H
#define MU_CHARSEL_H

/* Character-select scene (scene state 5) of the client (NATIVE-CHARSEL-001).
 * Authored names; client addresses in the comments. See
 * docs/research/client-character-select.md.
 *
 * Characters are client-layout records (0x3670 bytes, CHARACTER with the
 * OBJECT at +0x3254), handled as raw little-endian byte images so that the
 * reconstruction reads and writes exactly the fields the client does. The
 * character table CharactersClient (manager +8, 400 entries, getter
 * 0x0095f6db + 0x009a13f4) is supplied by the caller as a lookup function.
 *
 * Calls the client makes into other subsystems are not executed here: each
 * one is appended to an event log (mu_charsel_log) with its arguments, and
 * the values such calls return are explicit inputs. The Unicorn validator
 * (scripts/validate_charsel.py) compares this log with the calls the client's
 * instructions make. */

#include <stdint.h>

#define MU_CHARSEL_WORLD 0x5d          /* 0x01cf15fc: world index; folder World94 */
#define MU_CHARSEL_SCENE 5             /* 0x01d1df70 */
#define MU_CHARSEL_MARKERS 5           /* CGMCharacterScene_Ex position/angle slots */
#define MU_CHARSEL_LIST 10             /* CharactersClient entries the scene walks */
#define MU_CHARSEL_CHARACTERS 400      /* bound of 0x009a13f4 */
#define MU_CHARSEL_RECORD 0x3670       /* CHARACTER size */
#define MU_CHARSEL_OBJECT 0x3254       /* OBJECT inside CHARACTER */
#define MU_CHARSEL_PLAYER_MODEL 0xa91

/* Character record fields used here (CHARACTER offsets). */
enum {
    MU_CHAR_FLAG_E = 0x0e, MU_CHAR_CLASS = 0x12, MU_CHAR_SKIN = 0x13, MU_CHAR_FLAG_14 = 0x14,
    MU_CHAR_KEY = 0x3e, MU_CHAR_PARTS = 0x1c4, MU_CHAR_PART_SIZE = 0x3fc, MU_CHAR_WEAPONS = 0x19ac,
    MU_CHAR_WING = 0x21a4, MU_CHAR_HELPER = 0x299c, MU_CHAR_BYTE_322C = 0x322c, MU_CHAR_MOUNT = 0x322e,
    /* OBJECT offsets (add MU_CHARSEL_OBJECT) */
    MU_OBJ_LIVE = 0x00, MU_OBJ_VISIBLE = 0x0b, MU_OBJ_TYPE = 0x5c, MU_OBJ_SCALE = 0xa0, MU_OBJ_LIGHT = 0xec,
    MU_OBJ_POSITION = 0x158, MU_OBJ_ANGLE = 0x164, MU_OBJ_BUFFS = 0x358
};

typedef uint8_t *(*mu_charsel_character_fn)(void *context, int32_t index);

/* ---- event log ---- */

#define MU_CHARSEL_EVENT_ARGS 16
typedef struct mu_charsel_event {
    uint32_t call;                         /* client address of the callee (or an import tag below) */
    int32_t count;
    uint32_t args[MU_CHARSEL_EVENT_ARGS];  /* words; floats as bits; see each call for pointer encodings */
} mu_charsel_event;

#define MU_CHARSEL_LOG_MAX 96
typedef struct mu_charsel_log {
    int32_t count;
    int32_t overflow;
    mu_charsel_event events[MU_CHARSEL_LOG_MAX];
} mu_charsel_log;

/* Import calls in the log (opengl32 slots). */
#define MU_CHARSEL_GL_COLOR3F 0x01a7c76cu
#define MU_CHARSEL_GL_CLEAR_COLOR 0x01a7c6ccu

/* Pointer arguments are logged as stable identifiers: a pointer `offset`
 * bytes into character record `index` as MU_CHARSEL_REF(index, offset);
 * objects returned by stubbed getters as MU_CHARSEL_ID(n) (the validator's
 * stubs return these addresses); vectors passed by pointer are logged by
 * value (three words) in place of the pointer. */
#define MU_CHARSEL_REF(index, offset) (0x40000000u + ((uint32_t)(index) << 16) + (uint32_t)(offset))
#define MU_CHARSEL_ID(n) (0x7e000000u + ((uint32_t)(n) << 12))
enum {
    MU_CHARSEL_ID_UI_HELPER = 1,   /* 0x009c104e() */
    MU_CHARSEL_ID_QUEST_MGR,       /* 0x00b990b0() */
    MU_CHARSEL_ID_QUEST,           /* 0x00eb1309() when frame->quest_object */
    MU_CHARSEL_ID_NAME_MGR,        /* 0x0121d4c9() */
    MU_CHARSEL_ID_INPUT,           /* CInput 0x00cc3564() */
    MU_CHARSEL_ID_UIMNG,           /* CUIMng 0x011e228b() */
    MU_CHARSEL_ID_UI_9C2AEA,       /* 0x009c2aea() */
    MU_CHARSEL_ID_GFX,             /* GFx manager 0x00ac3bf7() */
    MU_CHARSEL_ID_GFX_MOVIE,       /* its +0x90 */
    MU_CHARSEL_ID_GFX_22C,         /* its +0x22c */
    MU_CHARSEL_ID_MENU,            /* [0x01d22c7c] */
    MU_CHARSEL_ID_MENU_HANDLE      /* *0x009a5792(...) */
};

/* ---- CGMCharacterScene_Ex (vtable 0x01aa7338, 0x8c bytes) ---- */

typedef struct mu_charsel_scene {
    float position[MU_CHARSEL_MARKERS][3];   /* +0x14 */
    float angle[MU_CHARSEL_MARKERS][3];      /* +0x50 */
} mu_charsel_scene;

/* Marker yaw (OBJECT +0x164 z) of slot k, stored by CreateObject. */
extern const float mu_charsel_marker_yaw[MU_CHARSEL_MARKERS];

/* Constructor 0x00daa127 (after the BaseMap constructor): zero vectors. */
void mu_charsel_scene_init(mu_charsel_scene *scene);

/* 0x00da9ff3 (thiscall, ret 4) SetCharacterPosition(slot): when the table
 * gives a character for `slot` (0 <= slot < 400), its OBJECT position and
 * angles take position[1] and angle[1] -- the client indexes the constant
 * marker 1 for every slot. Returns 1, else 0. */
int mu_charsel_set_character_position(const mu_charsel_scene *scene, int32_t slot, mu_charsel_character_fn character,
                                      void *context);

/* Map-object fields CreateObject touches (OBJECT layout of a static object). */
typedef struct mu_charsel_map_object {
    int32_t type;          /* +0x5c */
    float position[3];     /* +0x158 */
    int32_t field_64;      /* +0x64, written 0 */
    int32_t field_68;      /* +0x68, -2 for markers and hidden types */
    float field_c0;        /* +0xc0, -428.571 for types 0x3c/0x3d */
} mu_charsel_map_object;

/* Vtable slot 11, 0x00daa2b2 (thiscall, ret 4) CreateObject(object). Returns
 * 0 outside world 0x5d. Types 13..17 are the slot markers 0..4: the marker's
 * position and (0, 0, mu_charsel_marker_yaw[k]) are stored and
 * SetCharacterPosition(k) runs; the object's +0x68 becomes -2. */
int mu_charsel_create_object(mu_charsel_scene *scene, int32_t world, mu_charsel_map_object *object,
                             mu_charsel_character_fn character, void *context);

/* ---- character scale 0x01394f6f ---- */

typedef struct mu_charsel_scale_inputs {
    int32_t scene;          /* 0x01d1df70 */
    int32_t world;          /* 0x01cf15fc (argument of the event-world query) */
    uint8_t event_world;    /* 0x009dacb8(world) */
    uint8_t buff_1a8;       /* (c+0x35ac).0x01295ade(0x1a8) */
    uint8_t buff_1a9;       /* (c+0x35ac).0x01295ade(0x1a9) */
} mu_charsel_scale_inputs;

/* SetCharacterScale(c): helmet-dependent head part (slot 0), part scales
 * (part record +0xc4) and the OBJECT scale (+0xa0): 1.7 in scene 5, else per
 * base class. Returns at once when c+0xe is set. Logs 0x009dacb8 and
 * 0x01295ade queries. */
void mu_charsel_character_scale(uint8_t *character, uint32_t ref, const mu_charsel_scale_inputs *inputs,
                                mu_charsel_log *log);   /* ref: MU_CHARSEL_REF of the record (log identity) */

/* ---- CreateHero 0x0137f824 ---- */

/* CreateHero(slot, class, skin, x, y, angle): CreateCharacter 0x0137d8a1 (logged), light 0.3, key, position,
 * class and skin bytes, buff reset 0x01295f18 (logged); login-scene (3) preset equipment or class body parts
 * (0x3700.. + skin index) and empty weapons/wing/helper; 0x0128ed7d (logged); flag +0x14 = 0; SetCharacterScale
 * (reconstructed, its queries take `scale`); SetPlayerStop 0x0138fe69 (logged). Returns the record or NULL. */
uint8_t *mu_charsel_create_hero(int32_t slot, uint8_t class_byte, uint8_t skin, float x, float y, float angle,
                                const mu_charsel_scale_inputs *scale, mu_charsel_character_fn character, void *context,
                                mu_charsel_log *log);

/* ---- scene render 0x018576b3 ---- */

typedef struct mu_charsel_frame {
    uint8_t initialised;          /* 0x0bdc5ca2 InitCharacterScene */
    int32_t protocol;             /* 0x06fca2c4 (>= 0x33) */
    int32_t selected;             /* 0x01cf1864 SelectedHero */
    int32_t shown;                /* 0x01cf1154 */
    float world_time;             /* 0x06fce370 */
    int32_t mouse_x, mouse_y;     /* 0x0bdc5ad8 / 0x0bdc5adc */
    float record_position[3];     /* camera record +0xc */
    /* values returned by calls */
    int32_t pick;                 /* 0x016b47bf(1) */
    uint8_t input_byte_1f;        /* CInput (0x00cc3564) +0x1f */
    uint8_t enter_refused;        /* CCharSelMainWin 0x009a5029(SelectedHero) */
    int32_t screen_width;         /* 0x016bc355() */
    uint32_t quest_object;        /* 0x00eb1309 result (nonzero: 0x00eac4e0 runs) */
} mu_charsel_frame;

/* Selection highlight values (0x01857b66..0x01857e43). */
float mu_charsel_highlight_luminosity(float world_time);   /* sinf(t*0.0015)*0.3+0.5 through CRT sin */

/* RenderCharacterScene: returns the client's AL (0 before init or before the
 * character list), writes the object fields the client writes (fog byte is
 * not part of the records: *fog = 0) and logs every call. */
int mu_charsel_render(const mu_charsel_frame *frame, mu_charsel_character_fn character, void *context,
                      uint8_t *fog, mu_charsel_log *log);

/* Ground height of the scene's characters (0x01857a5c / 0x01857a7a). */
float mu_charsel_character_z(uint16_t mount);

/* ---- scene logic tick 0x01856e6c ---- */

typedef struct mu_charsel_tick {
    int32_t scene;                /* 0x01d1df70 (argument of the GFx update) */
    uint8_t initialised;          /* 0x0bdc5ca2 (in/out) */
    int32_t protocol;             /* 0x06fca2c4 */
    int32_t selected;             /* 0x01cf1864 (in/out) */
    int32_t shown;                /* 0x01cf1154 */
    /* inputs returned by calls and read through UI objects */
    uint8_t gfx_busy;             /* GFx manager +0x90 -> 0x00aae6f9() (first test) */
    uint8_t gfx_busy_enter;       /* same query in the Enter branch */
    uint8_t gfx_busy_escape;      /* same query in the Esc branch */
    uint8_t input_byte_31;        /* CInput +0x31: keys ignored */
    uint8_t key_enter;            /* 0x00ec53a7(0x0d) */
    uint8_t key_escape;           /* 0x00ec53a7(0x1b) */
    uint8_t gfx_flag_78, gfx_flag_79;   /* GFx manager +0x22c -> +0x78 / +0x79 */
    uint8_t global_1d22d1e, global_6fca007;
    uint8_t ui_byte_464;          /* CUIMng +0x464 */
    uint8_t gfx_menu_flag;        /* [0x01d22c7c] +0x1c */
    uint8_t enter_refused;        /* CCharSelMainWin 0x009a5029(SelectedHero) */
    uint8_t ui_byte_65b9;         /* CUIMng +0x65b9 (out: cleared when the Esc branch closes the GFx window) */
} mu_charsel_tick;

/* The out-pointer argument of 0x009a5792 points into the tick's stack frame. */
#define MU_CHARSEL_STACK_REF 0x5ac00000u

/* Scene-5 logic step; returns 1 when it reached the key handling. Logs the
 * calls (scene creation 0x01851540 on the first step, the movers, the GFx
 * update, MoveCharacterCamera 0x01854529, the Enter/Esc actions). */
int mu_charsel_tick_step(mu_charsel_tick *tick, mu_charsel_log *log);

#endif
