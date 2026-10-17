#ifndef MU_GL_HEADLESS_H
#define MU_GL_HEADLESS_H

#include <stddef.h>
#include <stdint.h>

/* Creates a current offscreen GL 2.1 context with a width x height FBO bound.
 * Returns 0 on success. */
int mu_gl_headless_begin(int32_t width, int32_t height, char *error, size_t error_size);
void mu_gl_headless_end(void);
const char *mu_gl_renderer(void);

#endif
