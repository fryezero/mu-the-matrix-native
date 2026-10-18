#ifndef MU_LOGIN_GL_H
#define MU_LOGIN_GL_H

/* OpenGL 2.1 drawing of the native login scene (NATIVE-LOGIN-001, core/mu_login): the same passes as
 * mu_login_draw_soft (RenderTerrain, RenderObjects, RenderObjects_AfterCharacter, the sprites and
 * particles of the reconstructed particle module) through the fixed-function GL backend. Used by mu-client. */

#include <stdint.h>

#include "../core/mu_login.h"

typedef struct mu_login_gl mu_login_gl;

/* Uploads the terrain, object and billboard textures (current GL context). */
mu_login_gl *mu_login_gl_setup(mu_login_session *s);
void mu_login_gl_teardown(mu_login_gl *g);
/* Draws the 3D part into the current framebuffer (width x height pixels). Returns terrain faces. */
long mu_login_gl_draw(mu_login_gl *g, mu_login_session *s, int32_t width, int32_t height);

#endif
