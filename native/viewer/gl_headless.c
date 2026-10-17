/* Offscreen OpenGL context with a framebuffer object for headless renders.
 * macOS: CGL legacy (2.1) context without any window or display connection.
 * Elsewhere: a hidden SDL window's 2.1 context. Both render into an
 * RGBA8 + 24-bit depth FBO of the requested size. */
#include "gl_headless.h"

#include <stdio.h>
#include <string.h>

#ifdef __APPLE__
#include <OpenGL/OpenGL.h>
#include <OpenGL/gl.h>
#include <OpenGL/glext.h>
static CGLContextObj context;
#define GEN_FRAMEBUFFERS glGenFramebuffersEXT
#define BIND_FRAMEBUFFER glBindFramebufferEXT
#define GEN_RENDERBUFFERS glGenRenderbuffersEXT
#define BIND_RENDERBUFFER glBindRenderbufferEXT
#define RENDERBUFFER_STORAGE glRenderbufferStorageEXT
#define FRAMEBUFFER_RENDERBUFFER glFramebufferRenderbufferEXT
#define CHECK_FRAMEBUFFER glCheckFramebufferStatusEXT
#define DELETE_FRAMEBUFFERS glDeleteFramebuffersEXT
#define DELETE_RENDERBUFFERS glDeleteRenderbuffersEXT
#else
#include <SDL.h>
#include <GL/gl.h>
#include <GL/glext.h>
static SDL_Window *window;
static SDL_GLContext sdl_context;
static PFNGLGENFRAMEBUFFERSEXTPROC gen_framebuffers;
static PFNGLBINDFRAMEBUFFEREXTPROC bind_framebuffer;
static PFNGLGENRENDERBUFFERSEXTPROC gen_renderbuffers;
static PFNGLBINDRENDERBUFFEREXTPROC bind_renderbuffer;
static PFNGLRENDERBUFFERSTORAGEEXTPROC renderbuffer_storage;
static PFNGLFRAMEBUFFERRENDERBUFFEREXTPROC framebuffer_renderbuffer;
static PFNGLCHECKFRAMEBUFFERSTATUSEXTPROC check_framebuffer;
static PFNGLDELETEFRAMEBUFFERSEXTPROC delete_framebuffers;
static PFNGLDELETERENDERBUFFERSEXTPROC delete_renderbuffers;
#define GEN_FRAMEBUFFERS gen_framebuffers
#define BIND_FRAMEBUFFER bind_framebuffer
#define GEN_RENDERBUFFERS gen_renderbuffers
#define BIND_RENDERBUFFER bind_renderbuffer
#define RENDERBUFFER_STORAGE renderbuffer_storage
#define FRAMEBUFFER_RENDERBUFFER framebuffer_renderbuffer
#define CHECK_FRAMEBUFFER check_framebuffer
#define DELETE_FRAMEBUFFERS delete_framebuffers
#define DELETE_RENDERBUFFERS delete_renderbuffers
#endif

static GLuint framebuffer, color_buffer, depth_buffer;

static int report(char *error, size_t size, const char *message)
{
    if (error && size)
        snprintf(error, size, "%s", message);
    return 1;
}

int mu_gl_headless_begin(int32_t width, int32_t height, char *error, size_t error_size)
{
#ifdef __APPLE__
    CGLPixelFormatAttribute attributes[] = {kCGLPFAColorSize, (CGLPixelFormatAttribute)24,
                                            kCGLPFAAlphaSize, (CGLPixelFormatAttribute)8,
                                            kCGLPFADepthSize, (CGLPixelFormatAttribute)24,
                                            kCGLPFAAllowOfflineRenderers, (CGLPixelFormatAttribute)0};
    CGLPixelFormatObj format = NULL;
    GLint count = 0;
    if (CGLChoosePixelFormat(attributes, &format, &count) != kCGLNoError || !format)
        return report(error, error_size, "CGLChoosePixelFormat failed");
    CGLError status = CGLCreateContext(format, NULL, &context);
    CGLDestroyPixelFormat(format);
    if (status != kCGLNoError || CGLSetCurrentContext(context) != kCGLNoError)
        return report(error, error_size, "CGLCreateContext failed");
#else
    if (SDL_Init(SDL_INIT_VIDEO) != 0)
        return report(error, error_size, SDL_GetError());
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
    window = SDL_CreateWindow("mu-viewer", 0, 0, 16, 16, SDL_WINDOW_OPENGL | SDL_WINDOW_HIDDEN);
    if (!window || !(sdl_context = SDL_GL_CreateContext(window)))
        return report(error, error_size, SDL_GetError());
    gen_framebuffers = (PFNGLGENFRAMEBUFFERSEXTPROC)SDL_GL_GetProcAddress("glGenFramebuffersEXT");
    bind_framebuffer = (PFNGLBINDFRAMEBUFFEREXTPROC)SDL_GL_GetProcAddress("glBindFramebufferEXT");
    gen_renderbuffers = (PFNGLGENRENDERBUFFERSEXTPROC)SDL_GL_GetProcAddress("glGenRenderbuffersEXT");
    bind_renderbuffer = (PFNGLBINDRENDERBUFFEREXTPROC)SDL_GL_GetProcAddress("glBindRenderbufferEXT");
    renderbuffer_storage = (PFNGLRENDERBUFFERSTORAGEEXTPROC)SDL_GL_GetProcAddress("glRenderbufferStorageEXT");
    framebuffer_renderbuffer = (PFNGLFRAMEBUFFERRENDERBUFFEREXTPROC)SDL_GL_GetProcAddress("glFramebufferRenderbufferEXT");
    check_framebuffer = (PFNGLCHECKFRAMEBUFFERSTATUSEXTPROC)SDL_GL_GetProcAddress("glCheckFramebufferStatusEXT");
    delete_framebuffers = (PFNGLDELETEFRAMEBUFFERSEXTPROC)SDL_GL_GetProcAddress("glDeleteFramebuffersEXT");
    delete_renderbuffers = (PFNGLDELETERENDERBUFFERSEXTPROC)SDL_GL_GetProcAddress("glDeleteRenderbuffersEXT");
    if (!gen_framebuffers || !bind_framebuffer || !gen_renderbuffers || !bind_renderbuffer || !renderbuffer_storage ||
        !framebuffer_renderbuffer || !check_framebuffer || !delete_framebuffers || !delete_renderbuffers)
        return report(error, error_size, "GL_EXT_framebuffer_object unavailable");
#endif
    GEN_FRAMEBUFFERS(1, &framebuffer);
    BIND_FRAMEBUFFER(GL_FRAMEBUFFER_EXT, framebuffer);
    GEN_RENDERBUFFERS(1, &color_buffer);
    BIND_RENDERBUFFER(GL_RENDERBUFFER_EXT, color_buffer);
    RENDERBUFFER_STORAGE(GL_RENDERBUFFER_EXT, GL_RGBA8, width, height);
    FRAMEBUFFER_RENDERBUFFER(GL_FRAMEBUFFER_EXT, GL_COLOR_ATTACHMENT0_EXT, GL_RENDERBUFFER_EXT, color_buffer);
    GEN_RENDERBUFFERS(1, &depth_buffer);
    BIND_RENDERBUFFER(GL_RENDERBUFFER_EXT, depth_buffer);
    RENDERBUFFER_STORAGE(GL_RENDERBUFFER_EXT, GL_DEPTH_COMPONENT24, width, height);
    FRAMEBUFFER_RENDERBUFFER(GL_FRAMEBUFFER_EXT, GL_DEPTH_ATTACHMENT_EXT, GL_RENDERBUFFER_EXT, depth_buffer);
    if (CHECK_FRAMEBUFFER(GL_FRAMEBUFFER_EXT) != GL_FRAMEBUFFER_COMPLETE_EXT)
        return report(error, error_size, "Incomplete framebuffer object");
    return 0;
}

const char *mu_gl_renderer(void)
{
    const GLubyte *renderer = glGetString(GL_RENDERER);
    return renderer ? (const char *)renderer : "unknown";
}

void mu_gl_headless_end(void)
{
    BIND_FRAMEBUFFER(GL_FRAMEBUFFER_EXT, 0);
    DELETE_RENDERBUFFERS(1, &color_buffer);
    DELETE_RENDERBUFFERS(1, &depth_buffer);
    DELETE_FRAMEBUFFERS(1, &framebuffer);
#ifdef __APPLE__
    CGLSetCurrentContext(NULL);
    CGLDestroyContext(context);
#else
    SDL_GL_DeleteContext(sdl_context);
    SDL_DestroyWindow(window);
    SDL_Quit();
#endif
}
