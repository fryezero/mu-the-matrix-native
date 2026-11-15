#ifndef MU_LINK_SELECTOR_H
#define MU_LINK_SELECTOR_H
#include <stdint.h>
/* RENDER-EFFECTS-035: the general equipment-link selector.
 *
 * A CHARACTER has two weapon link slots, 0x3fc apart; the link bone of slot n is
 * the byte at +0x19b1 + n * 0x3fc. The character setup's type switch
 * 0x0137eefc..0x0137f5f4 writes those bytes from the OBJECT model type alone:
 * no item, class or skill word is read. The skill step, the buff auras and the
 * bow sparks then read the byte of one slot. */
enum {
    MU_LINK_SLOT0 = 1, MU_LINK_SLOT1 = 2,   /* which link bytes the routine writes */
    MU_LINK_OTHER = 4                       /* the second setter 0x00d9013e claims the type: not recovered */
};
/* The link bones of a model type. Returns the mask of written slots (a slot the
 * routine leaves alone keeps its earlier byte and is not reported), or
 * MU_LINK_OTHER. Types without their own case get the Player defaults 33 / 42. */
int mu_link_bones(int32_t type, uint8_t bones[2]);
/* Which slot an attack step reads, 0x013a5658: slot 1 for the Player actions
 * 0x73 and 0x74, else slot 0. */
int mu_link_index(int32_t model, int32_t action);
#endif
