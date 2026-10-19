#ifndef MU_CHARSEL_WORLD_H
#define MU_CHARSEL_WORLD_H

/* The character-select scene's world handler CGMCharacterScene_Ex (NATIVE-CHARSEL-002,
 * docs/research/client-character-select.md section 9).
 *
 * World 0x5d (Data/World94) is the 3D scene behind the character list. Its
 * handler class CGMCharacterScene_Ex (RTTI .?AVCGMCharacterScene_Ex@@, vtable
 * 0x01aa7338, base BaseMap) overrides five slots of the world-handler
 * interface, the same five as the login world's CGMLogInScene_Ex; each one
 * first tests [0x01cf15fc] == 0x5d (0x00daa1f5):
 *
 *   slot 0x2c 0x00daa2b2  CreateObject hook (slot markers, hidden emitters, ranges)
 *   slot 0x30 0x00daa82b  MoveObject hook (texture scroll, the lamps' terrain light)
 *   slot 0x34 0x00daa9dd  RenderObjectVisual hook (sprites, particles, effects)
 *   slot 0x38 0x00dab4d7  custom render (the after-character flag +0xa)
 *   slot 0x3c 0x00dab5ed  after-character render (RenderBody, the pedestal's glow mesh)
 *
 * RenderObjects_AfterCharacter 0x016d6949 lists world 0x5d next to 0x5e: the
 * login world's reconstruction (mu_login_after_pass) serves both.
 *
 * Same conventions as object_render.h and login_world.h: objects are raw
 * 0x3d8-byte OBJECT images, calls into other subsystems are logged with their
 * arguments, their results are explicit inputs. scripts/validate_charsel_world.py
 * compares everything with the client's instructions in Unicorn. */

#include "login_world.h"

#define MU_CSW_WORLD 0x5d
#define MU_CSW_MARKERS 5

/* Callees that appear in the logs (client addresses) besides those of object_render.h / login_world.h. */
#define MU_OBJ_CALL_SET_CHARACTER_POSITION 0x00da9ff3u /* CGMCharacterScene_Ex::SetCharacterPosition(slot) */
#define MU_OBJ_CALL_EFFECT 0x013c0eaau               /* CreateEffect wrapper (type, pos, angle, light, sub, owner, ...) */

/* Bitmaps and effect models the handler names (LoadBitmap / AccessModel call sites). */
#define MU_CSW_BITMAP_SPARK04 0x8155        /* Effect\Spark04.jpg (0x0182261b) */
#define MU_CSW_BITMAP_SHINY02 0x7f67        /* Effect\Shiny02.jpg */
#define MU_CSW_BITMAP_MAGIC_GROUND13 0x8145 /* Effect\magic_ground1_3.jpg (0x018360d0) */
#define MU_CSW_BITMAP_CLOUDS 0x7f89         /* Effect\clouds.jpg */
#define MU_CSW_BITMAP_WATERFALL1 0x801a     /* Effect\WATERFALL1.jpg */
#define MU_CSW_BITMAP_WATERFALL2 0x801b     /* Effect\WATERFALL2.jpg */
#define MU_CSW_BITMAP_WATERFALL3 0x801c     /* Effect\WATERFALL3.jpg */
#define MU_CSW_BITMAP_WATER 0x802a          /* effect\water.jpg (0x0182301b) */
#define MU_CSW_BITMAP_FANTA_B 0x8017        /* Effect\fantaB.jpg (0x01820fef) */
#define MU_CSW_BITMAP_SMOKE01 0x7f5a        /* Effect\smoke01.jpg */
#define MU_CSW_EFFECT_STARDR 0x5ac          /* Data\Effect\stardr01.bmd (0x018363e8) */
#define MU_CSW_EFFECT_SEALEAF 0x59a         /* zu_sealeaf04.bmd (loaded only by other worlds' model passes) */

/* The handler's marker vectors (this +0x14: five positions, +0x50: five angles). */
typedef struct mu_csw_scene {
    float position[MU_CSW_MARKERS][3];
    float angle[MU_CSW_MARKERS][3];
} mu_csw_scene;

/* Slot 0x2c on a created object (o: CreateObject's result):
 *   +0x64 = 0 for every object;
 *   types 0x0d..0x11, the slot markers 0..4: scene position k = the object's position, scene angle
 *     k = (0, 0, {115, 90, 75, 60, 35}[k]), SetCharacterPosition(k) (logged), HiddenMesh -2;
 *   types 0x26..0x28, 0x36..0x39, 0x45, 0x50: HiddenMesh -2 (emitters drawn only by their visuals);
 *   types 0x3c, 0x3d: TestFrustrum2D range -428.571.
 * scene may be NULL. */
void mu_csw_create(uint8_t *object, int32_t index, mu_csw_scene *scene, mu_obj_log *log);

/* Slot 0x30 (MoveObject's world case, after the tick):
 *   type 0x18: blend v -= 0.02; types 0x19, 0x1a: blend v -= 0.03;
 *   type 0x49: l = (rand() % 4 + 3) * 0.1, AddTerrainLight(x, y, (0.2 l, 0.6 l, l), 3, frame light).
 * Returns 1 when the type has a case (the slot's return value). */
int mu_csw_move(uint8_t *object, int32_t index, mu_obj_rand_fn rand_fn, void *context, mu_obj_log *log);

/* Slot 0x34 (RenderObjectVisual's world case; the model's bones are those of this frame's RenderObject):
 *   type 0x1f: Spark04 sprites at bones 6, 7, 8 (scales 1, 1.2, 0.8);
 *   type 0x26: on rand() % 6 == 0, clouds 0x14 with the object as owner (the login world's mist);
 *   types 0x27 / 0x28: on rand() % 100 / % 200 == 0, the effect stardr01 0x5ac subtype 0 / 1;
 *   type 0x36: on rand() % 2 == 0, WATERFALL1 2; type 0x37: always WATERFALL3 0xe at twice the scale;
 *   type 0x38: on rand() % 3 == 0, WATERFALL2 2; type 0x39: on rand() % 100 == 0, the effect 0x59a 3;
 *   type 0x45: on rand() % 3 == 0, water 0x802a 1; type 0x50: on rand() % 8 == 0, smoke01 0x45;
 *   type 0x49: at bone 1 a Shiny02 sprite (light (0.4, sin(WorldTime * 0.7) * 0.2 + 0.8, 0.4), scale
 *     1.2 + (rand() % 30) / 90, rotation -((int)WorldTime % 3600) * 0.1) and a magic_ground1_3 sprite
 *     (0.2, light (0.5, 1, 0.98), the opposite rotation), and on rand() % 3 == 0 a fantaB 0 particle 15
 *     units above the bone at 1.8 times the object's scale.
 * Event layouts: sprites and particles as in login_world.h; effects MU_OBJ_CALL_EFFECT with type,
 * position[3], angle[3], light[3], subtype, owner (1: the object). sine NULL uses the host's sin.
 * Returns 1 when the type has a case. */
int mu_csw_visual(const uint8_t *object, int32_t index, float world_time, mu_obj_rand_fn rand_fn,
                  mu_login_bone_fn bone, mu_login_sin_fn sine, void *context, mu_obj_log *log);

/* Slot 0x38 (the custom render 0x017f76ec asks it): types 4, 7, 8, 0xc, 0x18, 0x19, 0x1a, 0x1f, 0x21, 0x24,
 * 0x3d, 0x47: +0xa = 1 and nothing drawn; type 0x3c: RenderMesh(1, 2, alpha, blend mesh, blend light, u, v,
 * -1) and +0xa = 1. Returns 1 (handled) for those types, 0 otherwise (RenderObject draws the body). */
int mu_csw_custom_render(uint8_t *object, int32_t index, mu_obj_log *log);

/* Slot 0x3c (the after-character draw 0x016d67c7 calls it): the types of slot 0x38 draw
 * RenderBody(2, alpha, blend mesh, blend light, u, v, hidden mesh, -1); type 0x3c draws
 * RenderMesh(0, 2, alpha, -2, blend light, u, v, -1). Returns 1 when the type has a case. */
int mu_csw_after_render(const uint8_t *object, int32_t index, mu_obj_log *log);

#endif
