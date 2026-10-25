/* Sketch helper: every body in this package that is not yet written. */
#ifndef MU_NOT_IMPLEMENTED_H
#define MU_NOT_IMPLEMENTED_H
#include <stdio.h>
#include <stdlib.h>
#define MU_NOT_IMPLEMENTED() \
    (fprintf(stderr, "%s:%d %s: not implemented\n", __FILE__, __LINE__, __func__), abort())
#endif
