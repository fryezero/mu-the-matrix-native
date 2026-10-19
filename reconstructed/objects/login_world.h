#ifndef MU_LOGIN_WORLD_H
#define MU_LOGIN_WORLD_H

/* The login scene's world handler CGMLogInScene_Ex (NATIVE-LOGIN-001,
 * docs/research/client-login-scene.md).
 *
 * World 0x5e (Data/World95) is the 3D scene behind the login and server-select
 * screens. Its handler class CGMLogInScene_Ex (RTTI .?AVCGMLogInScene_Ex@@,
 * vtable 0x01aaa874, base BaseMap) overrides five slots of the world-handler
 * interface; each one first tests [0x01cf15fc] == 0x5e (0x00e24993):
 *
 *   slot 0x2c 0x00e24a4d  CreateObject hook (type defaults)
 *   slot 0x30 0x00e24acd  MoveObject hook (texture scroll, pulsing blend light)
 *   slot 0x34 0x00e24be1  RenderObjectVisual hook (ship lanterns, mist particles)
 *   slot 0x38 0x00e254bb  custom render (RenderBody, the after-character flag +0xa)
 *   slot 0x3c 0x00e25639  after-character render (the ship's glow meshes)
 *
 * plus RenderObjects_AfterCharacter 0x016d6949, which draws the +0xa objects
 * after the characters in this world. Same conventions as object_render.h:
 * objects are raw 0x3d8-byte OBJECT images, calls into other subsystems are
 * logged with their arguments and their results are explicit inputs.
 * scripts/validate_login_world.py compares everything with the client's
 * instructions in Unicorn. */

#include "object_render.h"

#define MU_LOGIN_WORLD 0x5e

/* Callees that appear in the logs (client addresses). */
#define MU_OBJ_CALL_PLAY_SPEED 0x00eaaa44u      /* model action table: PlaySpeed of (type, action) = value */
#define MU_OBJ_CALL_BONE_POSITION 0x012b6ef1u   /* BMD::TransformPosition(bone matrix, local, out, 0) */
#define MU_OBJ_CALL_SPRITE 0x01692eb7u          /* CreateSprite(bitmap, pos, scale, light, owner, rotation, 0, 4, {1,1,1.0}) */
#define MU_OBJ_CALL_MESH 0x00966e4au            /* RenderMesh(mesh, flags, alpha, blend mesh, blend light, u, v, texture) */
#define MU_OBJ_CALL_COLOR 0x00000054u           /* pseudo call: model +0x54 (body colour) written */
#define MU_OBJ_CALL_AFTER_DRAW 0x016d6791u      /* the after-character draw of one object (setup + slot 0x3c) */

/* Bitmaps (LoadBitmap call sites in the startup loader and OpenWorld). */
#define MU_LOGIN_BITMAP_SHINY02 0x7f67     /* Effect\Shiny02.jpg */
#define MU_LOGIN_BITMAP_FLARE01 0x7ef7     /* Effect\flare01.jpg */
#define MU_LOGIN_BITMAP_CLOUDS 0x7f89      /* Effect\clouds.jpg */
#define MU_LOGIN_BITMAP_WATERFALL 0x801a   /* Effect\WATERFALL1.jpg */
#define MU_LOGIN_BITMAP_SAILBOAT 0x817c    /* Object95\HSSailboat04_R.jpg (OpenWorld, world 0x5e only) */
#define MU_LOGIN_BITMAP_CHROME01 0x7f1f    /* Effect\Chrome01.jpg */

/* 0x00cfec8d(lo, hi, speed): a pulse between lo and hi,
 *   t = (float)(double)timeGetTime()   (unsigned, through cvtsi2sd + 2^32)
 *   s = |sin(t * speed)|               (0x009681bd: the C runtime sin on the widened value; 0x0098a647 fabs)
 *   return (1 - s) * (hi - lo) + lo
 * sine NULL uses the host's sin(double). */
typedef double (*mu_login_sin_fn)(void *context, double x);
float mu_login_pulse(float lo, float hi, float speed, uint32_t now_ms, mu_login_sin_fn sine, void *context);

/* Slot 0x2c on a created object (o: CreateObject's result; the generic fields are written):
 *   type 5: PlaySpeed of model 5 action 0 = 0.23 (logged, the caller stores it)
 *   types 0x26 and 0x36: HiddenMesh -2
 *   every other type: TestFrustrum2D range -428.571 */
void mu_login_create(uint8_t *object, int32_t index, mu_obj_log *log);

/* Slot 0x30 (MoveObject's world case, after the tick):
 *   type 1: blend v -= 0.005 per step
 *   type 0xd: blend light = pulse(0.2, 0.6, 0.001)
 * Returns 1 when the type has a case (the slot's return value). */
int mu_login_move(uint8_t *object, uint32_t now_ms, mu_login_sin_fn sine, void *context);

/* Bone positions: out = TransformPosition(the model's bone `bone` in the shared bone buffer, local). */
typedef void (*mu_login_bone_fn)(void *context, int32_t bone, const float local[3], float out[3]);

/* Slot 0x34 (RenderObjectVisual's world case; the model's bones are those of this frame's RenderObject):
 *   type 5: lantern glows, six blocks of rand()-jittered points on bones 37 and 98, each a CreateSprite of
 *           Shiny02 or flare01 (light (1, 0.3, 0) on bone 37, (0.2, 0.5, 0.8) on bone 98)
 *   type 0x26: on rand() % 6 == 0, CreateParticle(clouds, position, angle, (0.02, 0.02, 0.05), 0x14, scale, owner)
 *   type 0x36: on rand() % 2 == 0, CreateParticle(WATERFALL1, position, angle, (0.22, 0.15, 0.15), 2, scale, none)
 * Particle events: MU_OBJ_CALL_PARTICLE with 13 arguments (the 12 of object_render.h plus 1 when the object
 * is passed as owner). Sprite events: bitmap, position[3], scale, light[3], rotation, owner (1/0), 0, 4.
 * Returns 1 when the type has a case. */
int mu_login_visual(const uint8_t *object, int32_t index, mu_obj_rand_fn rand_fn, mu_login_bone_fn bone,
                    void *context, mu_obj_log *log);

/* Slot 0x38 (the custom render 0x017f76ec asks it): for types 1, 2, 3, 7, 8, 0xa, 0xb, 0xc, 0x12, 0x13, 0x14,
 * 0x1d, 0x37, 0x38 RenderBody(2, alpha, blend mesh, blend light, u, v, hidden mesh, -1) and +0xa = 0; for
 * types 5 and 0xd the same RenderBody and +0xa = 1. Returns 1 (handled) for those types, 0 otherwise. */
int mu_login_custom_render(uint8_t *object, int32_t index, mu_obj_log *log);

/* Slot 0x3c (the after-character draw 0x016d67c7 calls it): the glow meshes of type 5 (RenderMesh calls with
 * the sail texture 0x817c and Chrome01, the model colour (0.8, 0.7, 0.3) and alpha 0.7 for the lantern
 * meshes 0x18..0x1c, both restored after) and type 0xd (mesh 0x16 with blend mesh -2). model: MU_MDL_SIZE
 * bytes (its colour +0x54 is written). Returns 1 when the type has a case. */
int mu_login_after_render(uint8_t *object, uint8_t *model, int32_t index, uint32_t now_ms, mu_login_sin_fn sine,
                          void *context, mu_obj_log *log);

/* RenderObjects_AfterCharacter 0x016d6949 in world 0x5e. The counter 0x06fc9c90 (reset above 40, then +1);
 * for each sector i, j: sector visible (+0xc) = TestFrustrum2D(i*16+8, j*16+8, -180); for each object in list
 * order that is live with +0xa == 1, while the sector is visible or in top view: visible (+0xb) =
 * TestFrustrum2D(x*0.01, y*0.01, range), and when visible or in top view the draw 0x016d6791 is logged
 * (MU_OBJ_CALL_AFTER_DRAW). The world-group predicates before the world test are taken as answering no for
 * world 0x5e; the option 0x009a645f answers no outside world 0x27 and the first-draw predicate 0x017fe909
 * has no world 0x5e case. World 0x5d (the character select, NATIVE-CHARSEL-002) takes the same path: it is
 * in the world list and the predicate has no case for it either. Returns MU_OBJ_UNSUPPORTED for other
 * worlds. */
int mu_login_after_pass(mu_obj_world *w, const mu_obj_render_inputs *inputs, int32_t *counter, mu_obj_log *log);

#endif
