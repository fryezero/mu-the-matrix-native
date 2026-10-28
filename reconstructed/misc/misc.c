#include "misc.h"
#include <limits.h>
#include <math.h>

void mu_misc_boss_init(mu_misc_boss_bar *bar)
{
    *bar = (mu_misc_boss_bar){0, 10, 10, 0, 1};
}

int32_t mu_misc_boss_colour(int32_t index)
{
    return index == 0 ? 3 : index;
}

int mu_misc_boss_set_maximum(mu_misc_boss_bar *bar, int32_t maximum)
{
    if (maximum <= 0 || bar->segments <= 0 || maximum < bar->segments)
        return 0;
    bar->unit = maximum / bar->segments;
    return 1;
}

int32_t mu_misc_boss_gauge(const mu_misc_boss_bar *bar, int32_t hp, int32_t maximum)
{
    if (bar->unit <= 0)
        return -1;
    int32_t gauge = 0;
    if (hp == maximum)
        gauge = 100;
    else
        gauge = (int32_t)((double)(hp % bar->unit) / (double)bar->unit * 100.0);
    if (hp < 1)
        gauge = 0;
    return gauge;
}

int mu_misc_boss_update(mu_misc_boss_bar *bar, int32_t hp)
{
    if (bar->unit <= 0 || bar->segments <= 0)
        return 0;
    double count = ceil((double)hp / (double)bar->unit);
    if (count < INT32_MIN || count > INT32_MAX)
        return 0;
    bar->remaining = (int32_t)count;
    if (bar->remaining >= bar->segments || bar->remaining <= 1) {
        bar->current_colour = 0;
        bar->next_colour = 1;
    } else {
        int32_t index = (bar->segments - bar->remaining) % 3;
        bar->current_colour = mu_misc_boss_colour(index);
        bar->next_colour = mu_misc_boss_colour(index + 1);
        if (bar->remaining == 2)
            bar->next_colour = 0;
    }
    return 1;
}
