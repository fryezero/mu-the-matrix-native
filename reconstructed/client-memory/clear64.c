#include "clear64.h"

#include <string.h>

void *mu_clear64(void *destination)
{
    return memset(destination, 0, 64);
}
