#include "world_visual_internal.h"
/* Noria 19 is selected explicitly by 0x017fece6, independently of +0xa.
 * No inferred write to +0xa: the capture's flag writer is outside this slice. */
int mu_noria_defer(uint8_t *o)
{
    return mu_obj_i32(o, MU_OBJF_TYPE) == 0x13;
}
