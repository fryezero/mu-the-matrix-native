#ifndef MU_SKILL_TREE4_INTERNAL_H
#define MU_SKILL_TREE4_INTERNAL_H
#include "mu_skill_tree4.h"
#include "mu_skill.h"
#define DEMO_NODES 1024

typedef struct demo_node { int32_t group, index, level; } demo_node;

struct mu_skill_tree4 {
    mu_t4_table table;
    size_t records;
    mu_t4_tip *tips;                  /* tree4_tips.tsv, sorted by skill */
    int ntips;
    mu_t4_side_table side;            /* tree4_side.tsv */
    mu_t4_window window;
    mu_t4_env env;
    mu_skill_book *book;
    int32_t cls;
    mu_skill_tree4_host host;
    demo_node demo[DEMO_NODES];
    int ndemo;
    int32_t points;
};

#endif
