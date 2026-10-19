/* Deterministic test host of the environment module (not client code). */
#ifndef MU_ENV_TEST_HOST_H
#define MU_ENV_TEST_HOST_H

#include <stdint.h>

#include "env.h"

enum {
    MU_ENV_EVENT_SOUND = 1, MU_ENV_EVENT_SET_ACTION = 2, MU_ENV_EVENT_ANIMATE = 3, MU_ENV_EVENT_PARTICLE = 4,
    MU_ENV_EVENT_KILL = 5, MU_ENV_EVENT_INIT = 6, MU_ENV_EVENT_EFFECT = 7,
    MU_ENV_EVENT_FRUSTUM = 20, MU_ENV_EVENT_OBJECT = 21, MU_ENV_EVENT_SPRITE = 22, MU_ENV_EVENT_BONE = 23,
    MU_ENV_EVENT_ALPHA_TEST = 24, MU_ENV_EVENT_ALPHA_BLEND = 25, MU_ENV_EVENT_COLOR4 = 26, MU_ENV_EVENT_COLOR3 = 27,
    MU_ENV_EVENT_SHADOW = 28, MU_ENV_EVENT_BIND = 29, MU_ENV_EVENT_PLANE = 30, MU_ENV_EVENT_BILLBOARD = 31,
    MU_ENV_TEST_EVENTS = 8192
};

typedef struct mu_env_event {
    int32_t kind, a, b, c;
    float f[16];
} mu_env_event;

typedef struct mu_env_test_host {
    mu_env *env;
    float height_base;
    int32_t height_span, height_shift;
    int32_t frustum_mask;
    int32_t missing_models, missing_model[8];
    int32_t missing_bitmaps, missing_bitmap[8];
    int32_t count, overflow;
    mu_env_event events[MU_ENV_TEST_EVENTS];
    mu_env_event scratch;
} mu_env_test_host;

uint32_t mu_env_test_mix(uint32_t a, uint32_t b);
float mu_env_test_height(const mu_env_test_host *t, float x, float y);
int32_t mu_env_test_index(const mu_env_test_host *t, const mu_env_object *o);
void mu_env_test_host_init(mu_env_test_host *t, mu_env *env);
void mu_env_test_host_bind(mu_env_test_host *t, mu_env_host *h);
void mu_env_test_render_bind(mu_env_test_host *t, mu_env_render_host *r);

void *mu_env_test_new(uint32_t seed);
void mu_env_test_free(void *session);
mu_env *mu_env_test_env(void *session);
mu_env_test_host *mu_env_test_host_of(void *session);
mu_env_inputs *mu_env_test_inputs(void *session);
void mu_env_test_run(void *session, int32_t step);
void mu_env_test_clear_events(void *session);
void mu_env_test_store(void *session, uint8_t *boids, uint8_t *fishs, uint8_t *leaves);
int32_t mu_env_test_offset(int32_t which);
void mu_env_test_load(void *session, const uint8_t *boids, const uint8_t *fishs, const uint8_t *leaves);
void mu_env_test_body_light(void *session, int32_t which, int32_t index, const float frame_light[3], float color[3],
                            uint8_t *lighting);

#endif
