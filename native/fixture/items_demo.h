#ifndef MU_FIXTURE_ITEMS_DEMO_H
#define MU_FIXTURE_ITEMS_DEMO_H
#include <stdint.h>
struct mu_fixture;
void *mu_items_demo_state(struct mu_fixture *fixture);
/* Synthetic server commands. No request success or inventory acceptance inferred. */
int32_t mu_items_demo_drop(void *state, int32_t code, int32_t level, uint8_t excellent,
                           uint8_t ancient, int32_t zen, float x, float y, int drop);
int mu_items_demo_remove(void *state, int32_t slot);
#endif
