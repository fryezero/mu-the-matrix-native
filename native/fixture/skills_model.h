#ifndef MU_SKILLS_MODEL_H
#define MU_SKILLS_MODEL_H
#include "../core/mu_skill.h"
#include "../core/mu_skill_tree4.h"
typedef int (*mu_skill_output)(void *, const uint8_t *, size_t);
int mu_skill_book_demo_login_emit(mu_skill_demo *model, mu_skill_book *b, int32_t class_byte, mu_skill_output output, void *user);
int mu_skill_book_demo_learn_emit(mu_skill_book *b, int32_t skill, int forget, mu_skill_output output, void *user);
int mu_skill_book_demo_master_login_emit(mu_skill_book *b, mu_skill_output output, void *user);
int mu_skill_book_demo_master_request_emit(mu_skill_book *b, const uint8_t *p, size_t size, mu_skill_output output, void *user);
int mu_skill_tree4_demo_login_emit(mu_skill_tree4 *t, int32_t points, mu_skill_output output, void *user);
int mu_skill_tree4_demo_request_emit(mu_skill_tree4 *t, const uint8_t *packet, size_t size, mu_skill_output output, void *user);
int mu_skill_tree4_demo_side_emit(mu_skill_tree4 *t, mu_skill_output output, void *user);
int mu_skill_tree4_demo_side_request_emit(mu_skill_tree4 *t, const uint8_t *packet, size_t size, mu_skill_output output, void *user);
#endif
