/* The class-upgrade quests (NATIVE-QUEST-002); see quest.h. */
#include "quest_internal.h"

#include <stdlib.h>

void mu_classic_free(mu_quest_client *c)
{
    if (!c)
        return;
    free(c->classic);
    c->classic = NULL;
}

void mu_classic_tab_init(mu_quest_client *c)
{
    (void)c;
}
