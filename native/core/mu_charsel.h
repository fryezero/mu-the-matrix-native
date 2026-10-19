#ifndef MU_CHARSEL_SESSION_H
#define MU_CHARSEL_SESSION_H

/* Native character-select scene (NATIVE-CHARSEL-001).
 *
 * One session of scene state 5 built from the reconstructed client routines
 * (docs/research/client-character-select.md):
 *
 *   - world 0x5d (Data/World94) terrain through mu_terrain, its camera record
 *     through MoveMainCamera's scene-5 record path (reconstructed/camera);
 *   - a synthetic character list (the server's data in the client): each
 *     entry becomes a client-layout CHARACTER record through CreateHero
 *     0x0137f824 (scale 1.7 in scene 5) and is placed by
 *     SetCharacterPosition 0x00da9ff3, i.e. on slot marker 1;
 *   - the selection as the GFx list sets it (SelectedHero 0x01cf1864 and the
 *     shown character 0x01cf1154 take the slot);
 *   - per logic step the scene tick (Enter starts the game: reported, the
 *     loading scene is not part of this) and the stand animation;
 *   - per frame RenderCharacterScene 0x018576b3: light reset, the selected
 *     character's terrain light, heights 169.5/194.5, the one character the
 *     client draws (the shown one) and the selection highlight (two rotating
 *     ground decals Skill\gmmzine.jpg and particle 0x8022).
 *
 * Placeholders (not client data):
 *   - the slot markers live in EncTerrain94.obj, which the captured client
 *     code does not decode (docs/research/client-objects.md); the marker
 *     positions are inputs (default: mu_charsel_default_marker1, marker 1 as
 *     read from the running client's object list; the front end takes the
 *     markers of a local decoded EncTerrain94.plain with --objects-dir);
 *   - static map objects are drawn only from a local decoded file
 *     (mu-charsel --objects-dir);
 *   - the CHARACTER fields CreateCharacter 0x0137d8a1 initialises are set to
 *     the values the scene reads (live, visible, Player type);
 *   - the particle 0x8022 is reported, not drawn (effect system).
 *
 * NATIVE-CHARSEL-002 (docs/research/client-character-select.md section 9):
 *   - World94's objects run the client's lifecycle with the scene's handler
 *     CGMCharacterScene_Ex (mu_charsel_attach_objects: CreateObject per
 *     record, MoveObjects per logic step, RenderObjects / RenderObjectVisual /
 *     RenderObjects_AfterCharacter per frame, reconstructed/objects/charsel_world);
 *   - the session keeps the reconstructed particle module (mu_world_particles,
 *     scene 5): the handler's sprites, particles and effects, and
 *     RenderCharacterScene's selection light CreateParticle(0x8022, ..., 5),
 *     moved each logic step (MoveEffects, MoveJoints, MoveParticles) and drawn
 *     by RenderSprites(0) / RenderParticles(0);
 *   - the frame light of a logic step is the primary light over the last
 *     frustum box grown by 3 tiles (0x016ca4fa, as the login scene);
 *   - the drawn character casts its parts' shadows (RenderBodyShadow through
 *     the item render's shadow block, mu_world_particles_character_shadow).
 */

#include <stdint.h>

#include "../../reconstructed/charsel/charsel.h"
#include "mu_character.h"
#include "mu_frame.h"
#include "mu_objects.h"
#include "mu_particles.h"
#include "mu_terrain.h"
#include "mu_walk.h"

#define MU_CHARSEL_MAX_ENTRIES 5
#define MU_CHARSEL_PATH 1024

typedef struct mu_charsel_entry {
    int32_t slot;                  /* CharactersClient index 0..9 (the list's slot byte) */
    uint8_t class_byte;            /* CHARACTER +0x12 */
    uint16_t level;                /* CHARACTER +0x144 */
    char name[16];                 /* CHARACTER +0x3658 (std::string in the client) */
    /* optional item files: index 1..5 replace the class body parts, 6/7 are
     * the weapon slots (link bones 33/42), 8 the wing (bone 47) */
    char items[MU_CHARACTER_ITEMS][MU_CHARSEL_PATH];
} mu_charsel_entry;

typedef struct mu_charsel_list {
    int32_t count;
    mu_charsel_entry entries[MU_CHARSEL_MAX_ENTRIES];
} mu_charsel_list;

/* Five synthetic characters (classes 0x00, 0x01, 0x02, 0x03, 0x04; levels and
 * names invented). */
void mu_charsel_list_default(mu_charsel_list *list);
/* Text list: one character per line, "slot class level name [item=PATH ...]"
 * with item = helm|armor|pants|gloves|boots|weapon0|weapon1|wing; '#' comments.
 * Relative item paths are taken under ROOT/Data. Returns 0 on success. */
int mu_charsel_list_parse(const char *text, const char *root, mu_charsel_list *list, char *error, size_t error_size);

/* Default position of marker 1 (live read, docs/research/client-objects.md). */
extern const float mu_charsel_default_marker1[3];

typedef struct mu_charsel_decal {
    float x, y, size, rotation;
    float light[3];
} mu_charsel_decal;

typedef struct mu_charsel_session {
    mu_frame_world frame;          /* clock, camera, view, input */
    mu_world *map;
    mu_camera_info info;
    mu_charsel_scene scene;        /* CGMCharacterScene_Ex */
    uint8_t *records;              /* CharactersClient: 400 client-layout records */
    mu_charsel_list list;
    mu_character characters[MU_CHARSEL_MAX_ENTRIES];
    int character_loaded[MU_CHARSEL_MAX_ENTRIES];
    int32_t selected, shown;       /* 0x01cf1864, 0x01cf1154 */
    mu_charsel_tick tick;
    uint8_t initialised;           /* 0x0bdc5ca2 */
    mu_charsel_log log;            /* last render's calls */
    /* per frame, from the render log */
    int32_t draw_entry;            /* list entry drawn this frame, -1 none */
    mu_charsel_decal decals[2];
    int32_t decal_count;
    int32_t particles_created;     /* CreateParticle calls of the last render (the selection light 0x8022) */
    int32_t enter_requests;        /* 0x0185a75a calls seen (Enter / double click) */
    uint32_t steps, frames;
    char error[256];
    /* NATIVE-CHARSEL-002 */
    mu_objects *objects;           /* World94's objects (the caller's, see mu_charsel_attach_objects), NULL none */
    int has_objects;
    mu_world_particles particles;  /* sprites, particles, joints, effects of the scene (scene 5) */
    int has_particles;
    mu_terrain_frustum frustum;    /* the last render's frustum (the frame light box of the next step) */
    int32_t frame_sprites;         /* CreateSprite calls of the last RenderObjects pass */
    long objects_drawn, after_meshes, billboards, shadows;
} mu_charsel_session;

/* Loads World94, its camera record, Player.bmd and the list's models, creates
 * the records and places them. markers may be NULL (default marker 1, other
 * markers equal to it). window_* are drawable pixels. near_plane 20 is the
 * client's CameraViewNear. Returns 0 on success (error text in s->error). */
int mu_charsel_init(mu_charsel_session *s, const char *game_root, const mu_charsel_list *list,
                    const float markers[MU_CHARSEL_MARKERS][3], uint32_t window_width, uint32_t window_height,
                    float near_plane);
void mu_charsel_free(mu_charsel_session *s);

/* The GFx list's selection (SelectIndex 0x00b4bed3): SelectedHero and the
 * shown character take `slot`. */
void mu_charsel_select(mu_charsel_session *s, int32_t slot);
/* Index of the list entry with `slot`, or -1. */
int32_t mu_charsel_entry_of(const mu_charsel_session *s, int32_t slot);

/* Window messages and keys in Win32 form (forwarded to mu_frame). */
void mu_charsel_message(mu_charsel_session *s, uint32_t message, uint32_t wparam, uint32_t lparam);
void mu_charsel_key(mu_charsel_session *s, int vk, int down);

/* Due logic steps: the scene tick and the characters' animation step. */
int32_t mu_charsel_update(mu_charsel_session *s, uint32_t now);
/* Render pass: frame tick, MoveMainCamera (record path), BeginOpengl, mouse
 * ray, then RenderCharacterScene's logic; fills draw_entry, decals and the
 * frame light. */
void mu_charsel_begin_render(mu_charsel_session *s, uint32_t now);
int32_t mu_charsel_end_render(mu_charsel_session *s);

/* Terrain frustum of the render (CreateFrustrum(width/640, record position, 0)). */
int mu_charsel_frustum(const mu_charsel_session *s, mu_terrain_frustum *frustum);

/* NATIVE-CHARSEL-002: starts the object lifecycle of World94 on objects (loaded records and models, kept
 * by the caller and freed after the session): CreateObject per record with CGMCharacterScene_Ex's hook, the
 * particle module attached for the handler's sprites, particles and effects. Returns 0 on success. */
int mu_charsel_attach_objects(mu_charsel_session *s, const char *game_root, mu_objects *objects);

/* A frame without drawing (headless frames that are not saved): RenderObjects with RenderObject and
 * RenderObjectVisual per drawn object, the after-character visibility, the frame's sprites killed. Call
 * after mu_charsel_begin_render. */
void mu_charsel_frame_objects(mu_charsel_session *s);

#endif
