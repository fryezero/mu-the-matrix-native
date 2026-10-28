#ifndef MU_SKILLS_STATE_H
#define MU_SKILLS_STATE_H
#include "skills.h"
typedef struct mu_dom_skills {
    mu_skill_book *book;
    mu_skill_tree4 *tree4;
    int class_byte, received, last_cast;
    uint32_t last_tick;
} mu_dom_skills;
#endif
