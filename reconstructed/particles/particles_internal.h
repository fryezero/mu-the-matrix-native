#ifndef MU_PARTICLES_INTERNAL_H
#define MU_PARTICLES_INTERNAL_H

#include <stdint.h>

#include "particles.h"

int32_t mu_pt_rand(const mu_pt_host *host);

/* cvttss2si: INT32_MIN for NaN and out-of-range values. */
static inline int32_t mu_pt_cvttss2si(float value)
{
    if (!(value > -2147483904.0f && value < 2147483648.0f))
        return INT32_MIN;
    return (int32_t)value;
}

/* C % on int32 with the client's idiv semantics for INT32_MIN % -1 avoided
 * (the divisors here are positive constants). */

void mu_pt_elbeland_create(mu_pt_particle *, const mu_pt_host *);
void mu_pt_elbeland_move(mu_pt_particle *, const mu_pt_host *);

#endif
