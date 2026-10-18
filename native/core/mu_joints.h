#ifndef MU_JOINTS_NATIVE_H
#define MU_JOINTS_NATIVE_H

/* The client's joint pool in the native session (NATIVE-JOINT-001, docs/research/client-joints.md).
 *
 * One implementation for every owner of joints: the world objects' pool (mu_particles: Tormenta Island's
 * lightning) and the skills' pool (mu_combat: Heal, Evil Spirit, Twisting Slash) both run these helpers
 * over reconstructed/joints:
 *   - CreateJoint's slot search 0x0153b058 (the first record that is not live) and the record part;
 *   - MoveJoints 0x01589b06: MoveJoint for every live record, a record of a kind that is not reconstructed
 *     ends at once (a native choice: the client moves every kind);
 *   - RenderJoints 0x01589b56(mode): the GL stream turned into quads with the colour in effect (glColor3f
 *     before glBegin; 0x7fd5 sets none and keeps the previous record's), the bitmap and the render type.
 *
 * Viewer choices: the colour at the start of the pass is white (the client's is whatever the previous
 * draw left); each owner keeps its own 500 records where the client has one pool. */

#include <stdint.h>

#include "mu_meshdraw.h"
#include "../../reconstructed/joints/joints.h"

typedef struct mu_joint_quad {
    float position[4][3];      /* world space */
    float uv[4][2];
    float color[3];            /* glColor3f in effect (GL clamps it to 0..1) */
    int32_t bitmap;            /* the record's +8 */
    uint8_t render_type;       /* the record's +0x10 */
} mu_joint_quad;

/* CreateJoint 0x0153b02c on the first free record: returns its index, -1 when all are live, -2 when the
 * kind is not reconstructed (the record is released again). */
int32_t mu_joints_create(mu_jt_joint *pool, int32_t count, int32_t type, const float position[3],
                         const float target_position[3], const float angle[3], int32_t subtype, int32_t target,
                         float scale, uint16_t key, uint16_t skill, uint8_t byte10, uint16_t word13, int32_t arg14,
                         const mu_jt_env *env);

/* Per-record MoveJoint inputs (wall attribute under the head, hero target); NULL: zero. */
typedef void (*mu_joints_inputs_fn)(void *context, const mu_jt_joint *joint, mu_jt_move_inputs *inputs);

/* MoveJoints: one logic step of every live record. Returns the number moved. */
int32_t mu_joints_move_all(mu_jt_joint *pool, int32_t count, const mu_jt_env *env, float time_step,
                           mu_joints_inputs_fn inputs, void *inputs_context);

/* RenderJoints(mode) as quads. Returns the number written (at most max). */
int32_t mu_joints_quads(const mu_jt_joint *pool, int32_t count, uint8_t mode, float world_time, mu_joint_quad *quads,
                        int32_t max);

/* The GL state of a render type (RenderJoints' wrappers 0x0184aa2b / 0x0184a990(1) / 0x0184aab7 /
 * 0x0184ab46): blend factors, depth mask, alpha test. */
void mu_joints_state(uint8_t render_type, mu_meshdraw_state *state);

/* Live records. */
int32_t mu_joints_live(const mu_jt_joint *pool, int32_t count);

#endif
