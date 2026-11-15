/* RENDER-ACTORS-008: which recorded caller/link request ids have a native consumer today.
 * stdin: "<service> <id> <subtype>" per line; stdout: 1, 0, or -1 (no query for that service). */
#include <stdio.h>
#include <string.h>
#include "../core/mu_particles.h"
#include "../core/mu_renderchar.h"
int main(void)
{
    char service[32]; int id, subtype;
    while (scanf("%31s %i %i", service, &id, &subtype) == 3) {
        int answer = -1;
        if (!strcmp(service, "sprite")) answer = mu_world_particles_bitmap_slot(id) >= 0;
        else if (!strcmp(service, "particle")) answer = mu_pt_kind_supported(id, subtype);
        else if (!strcmp(service, "joint")) answer = mu_jt_kind_supported(id, subtype);
        else if (!strcmp(service, "link")) answer = mu_rc_link_supported(id);
        printf("%d\n", answer);
    }
    return 0;
}
