/* SPDX-License-Identifier: MIT
 * Synthetic framebuffer/state regression for mugl; no game inputs.
 * Run unchanged with builtin and native,builtin overrides and compare fbhash.
 */
#include <windows.h>
#include <GL/gl.h>
#include <stdio.h>
#include <math.h>
static LRESULT CALLBACK wp(HWND h, UINT m, WPARAM w, LPARAM l) { return DefWindowProcA(h,m,w,l); }
static void triangle(void) {
    glVertex2f(-.9f,-.9f); glVertex2f(.8f,-.9f); glVertex2f(0,.8f);
}
static unsigned hash(void) {
    unsigned char pixels[128*128*4]; unsigned h=2166136261u;
    glReadPixels(0,0,128,128,GL_RGBA,GL_UNSIGNED_BYTE,pixels);
    for (unsigned i=0;i<sizeof pixels;i++) h=(h^pixels[i])*16777619u;
    return h;
}
static int failures;
static void color_is(float r, float g, float b) {
    float c[4]; glGetFloatv(GL_CURRENT_COLOR,c);
    if (fabsf(c[0]-r)>.0001f || fabsf(c[1]-g)>.0001f || fabsf(c[2]-b)>.0001f) failures++;
}
int main(int argc, char **argv) {
    WNDCLASSA wc={0}; wc.lpfnWndProc=wp; wc.hInstance=GetModuleHandleA(0); wc.lpszClassName="glcheck";
    RegisterClassA(&wc);
    RECT rect={0,0,128,128}; AdjustWindowRect(&rect,WS_OVERLAPPEDWINDOW,FALSE);
    HWND w=CreateWindowA("glcheck","mugl synthetic checks",WS_OVERLAPPEDWINDOW|WS_VISIBLE,0,0,
        rect.right-rect.left,rect.bottom-rect.top,0,0,wc.hInstance,0);
    HDC dc=GetDC(w);
    PIXELFORMATDESCRIPTOR pfd={sizeof pfd,1,PFD_DRAW_TO_WINDOW|PFD_SUPPORT_OPENGL|PFD_DOUBLEBUFFER,PFD_TYPE_RGBA,32};
    int fmt=ChoosePixelFormat(dc,&pfd);
    if (!w || !fmt || !SetPixelFormat(dc,fmt,&pfd)) return 2;
    HGLRC rc=wglCreateContext(dc);
    if (!rc || !wglMakeCurrent(dc,rc)) return 2;
    glViewport(0,0,128,128); glDisable(GL_DITHER); glClearColor(.1f,.2f,.3f,1);
    glClear(GL_COLOR_BUFFER_BIT);
    glColor3f(1,0,0); glBegin(GL_TRIANGLES); triangle(); glEnd();
    glColor3f(0,1,0); glBegin(GL_TRIANGLES); triangle(); glEnd();
    color_is(0,1,0);  /* Attribute changed between merged blocks. */
    printf("between-blocks fbhash=%08x\n",hash());
    glClear(GL_COLOR_BUFFER_BIT);
    /* These incomplete blocks must not turn into a cross-block triangle. */
    glBegin(GL_TRIANGLES); glVertex2f(-1,-1); glEnd();
    glBegin(GL_TRIANGLES); glVertex2f(1,-1); glVertex2f(0,1); glEnd();
    printf("incomplete fbhash=%08x\n",hash());
    glBegin(GL_TRIANGLES); glColor3f(0,0,1); glEnd(); color_is(0,0,1);
    /* Server state saved/restored by attributes and by a display list. */
    glPushAttrib(GL_CURRENT_BIT|GL_LIGHTING_BIT);
    glColor3f(1,0,0); glShadeModel(GL_FLAT); glPopAttrib();
    glBegin(GL_TRIANGLES); triangle(); glEnd(); color_is(0,0,1);
    GLuint list=glGenLists(1);
    glNewList(list,GL_COMPILE);
    glColor3f(1,0,0); glBegin(GL_TRIANGLES); triangle(); glEnd();
    glEndList(); color_is(0,0,1);
    glCallList(list); color_is(1,0,0);
    glColor3us(0,65535,0); /* Unintercepted attribute invalidates cached current. */
    glBegin(GL_TRIANGLES); triangle(); glEnd(); color_is(0,1,0);
    printf("list-and-attributes fbhash=%08x\n",hash());
    /* Client array state survives batch submission. */
    static float v[9]; glVertexPointer(3,GL_FLOAT,0,v); glEnableClientState(GL_VERTEX_ARRAY);
    glBegin(GL_TRIANGLES); triangle(); glEnd();
    void *pointer=0; glGetPointerv(GL_VERTEX_ARRAY_POINTER,&pointer);
    if (pointer!=v || !glIsEnabled(GL_VERTEX_ARRAY)) failures++;
    glDisableClientState(GL_VERTEX_ARRAY);
    typedef void (WINAPI *Bind)(GLenum, GLuint);
    typedef void (WINAPI *Gen)(GLsizei, GLuint *);
    Bind bind=(Bind)wglGetProcAddress("glBindBuffer");
    Gen gen=(Gen)wglGetProcAddress("glGenBuffers");
    if (bind && gen) {
        GLuint buffers[2]={0,0}; gen(2,buffers);
        GLuint buffer=buffers[0]; bind(0x8892,buffer);
        glClear(GL_COLOR_BUFFER_BIT); glBegin(GL_TRIANGLES); triangle(); glEnd();
        printf("bound-array-buffer fbhash=%08x\n",hash());
        GLint current=0; glGetIntegerv(0x8894,&current);
        if ((GLuint)current!=buffer) failures++;
        glPushClientAttrib(GL_CLIENT_VERTEX_ARRAY_BIT);
        bind(0x8892,buffers[1]);
        glBegin(GL_TRIANGLES); triangle(); glEnd(); glFlush();
        glPopClientAttrib();
        glBegin(GL_TRIANGLES); triangle(); glEnd();
        printf("restored-array-buffer fbhash=%08x\n",hash());
        glGetIntegerv(0x8894,&current);
        if ((GLuint)current!=buffer) failures++;
        bind(0x8892,0);
    }
    typedef GLuint (WINAPI *CreateShader)(GLenum);
    typedef void (WINAPI *ShaderSource)(GLuint, GLsizei, const char *const *, const GLint *);
    typedef void (WINAPI *ShaderOp)(GLuint);
    typedef void (WINAPI *GetStatus)(GLuint, GLenum, GLint *);
    typedef GLuint (WINAPI *CreateProgram)(void);
    typedef void (WINAPI *Attach)(GLuint, GLuint);
    CreateShader create=(CreateShader)wglGetProcAddress("glCreateShader");
    ShaderSource source=(ShaderSource)wglGetProcAddress("glShaderSource");
    ShaderOp compile=(ShaderOp)wglGetProcAddress("glCompileShader");
    GetStatus status=(GetStatus)wglGetProcAddress("glGetShaderiv");
    CreateProgram program=(CreateProgram)wglGetProcAddress("glCreateProgram");
    Attach attach=(Attach)wglGetProcAddress("glAttachShader");
    ShaderOp link=(ShaderOp)wglGetProcAddress("glLinkProgram");
    ShaderOp use=(ShaderOp)wglGetProcAddress("glUseProgram");
    GetStatus linked=(GetStatus)wglGetProcAddress("glGetProgramiv");
    GLuint test_program=0, test_vertex=0;
    if (create && source && compile && status && program && attach && link && use && linked) {
        GLuint vs=create(0x8b31), fs=create(0x8b30), prog=program();
        test_program=prog; test_vertex=vs;
        const char *vsrc="#version 120\nvoid main(){gl_Position=ftransform();gl_FrontColor=gl_Color;}";
        const char *fsrc="#version 120\nvoid main(){gl_FragColor=gl_Color;}";
        GLint ok=0;
        source(vs,1,&vsrc,0); compile(vs); status(vs,0x8b81,&ok); if (!ok) failures++;
        source(fs,1,&fsrc,0); compile(fs); status(fs,0x8b81,&ok); if (!ok) failures++;
        attach(prog,vs); attach(prog,fs); link(prog); linked(prog,0x8b82,&ok); if (!ok) failures++;
        use(prog); glClear(GL_COLOR_BUFFER_BIT); glBegin(GL_TRIANGLES); triangle(); glEnd();
        printf("compatibility-shader fbhash=%08x\n",hash()); use(0);
    }
    Gen gen_vao=(Gen)wglGetProcAddress("glGenVertexArrays");
    ShaderOp bind_vao=(ShaderOp)wglGetProcAddress("glBindVertexArray");
    if (!gen_vao || !bind_vao) {
        gen_vao=(Gen)wglGetProcAddress("glGenVertexArraysAPPLE");
        bind_vao=(ShaderOp)wglGetProcAddress("glBindVertexArrayAPPLE");
    }
    if (gen_vao && bind_vao) {
        GLuint vao=0, vao_buffer=0; gen_vao(1,&vao); bind_vao(vao);
        if (bind && gen) {
            gen(1,&vao_buffer); bind(0x8892,vao_buffer);
            glVertexPointer(3,GL_FLOAT,0,0); glEnableClientState(GL_VERTEX_ARRAY);
        }
        glClear(GL_COLOR_BUFFER_BIT); glBegin(GL_TRIANGLES); triangle(); glEnd();
        printf("bound-vertex-array-object fbhash=%08x\n",hash());
        GLint bound=0; glGetIntegerv(0x85b5,&bound); if ((GLuint)bound!=vao) failures++;
        if (vao_buffer) {
            void *vp=(void *)1; glGetPointerv(GL_VERTEX_ARRAY_POINTER,&vp);
            glGetIntegerv(0x8896,&bound);
            if (vp || (GLuint)bound!=vao_buffer || !glIsEnabled(GL_VERTEX_ARRAY)) failures++;
        }
        bind_vao(0); if (bind) bind(0x8892,0);
    }
    /* glMaterialfv is legal inside Begin; foreign call forces immediate replay. */
    float material[4]={1,1,1,1};
    glBegin(GL_TRIANGLES); glVertex2f(-.5f,-.5f);
    glMaterialfv(GL_FRONT_AND_BACK,GL_AMBIENT,material);
    glVertex2f(.5f,-.5f); glVertex2f(0,.5f); glEnd();
    printf("foreign-in-block fbhash=%08x\n",hash());
    for (int mode=GL_TRIANGLE_STRIP;mode<=GL_POLYGON;mode++) {
        glClear(GL_COLOR_BUFFER_BIT); glShadeModel(GL_FLAT);
        glBegin((GLenum)mode);
        glColor3f(1,0,0); glVertex2f(-.7f,-.7f);
        glColor3f(0,1,0); glVertex2f(.7f,-.7f);
        glColor3f(0,0,1); glVertex2f(.7f,.7f);
        glColor3f(1,1,0); glVertex2f(-.7f,.7f);
        glEnd(); printf("flat-mode-%d fbhash=%08x\n",mode,hash());
    }
    typedef void (WINAPI *Provoking)(GLenum);
    Provoking provoking=(Provoking)wglGetProcAddress("glProvokingVertex");
    if (provoking) {
        provoking(0x8e4d); /* GL_FIRST_VERTEX_CONVENTION */
        for (int mode=GL_TRIANGLE_STRIP;mode<=GL_TRIANGLE_FAN;mode++) {
            glShadeModel(GL_FLAT); glClear(GL_COLOR_BUFFER_BIT); glBegin((GLenum)mode);
            glColor3f(1,0,0); glVertex2f(-.7f,-.7f); glColor3f(0,1,0); glVertex2f(.7f,-.7f);
            glColor3f(0,0,1); glVertex2f(.7f,.7f); glColor3f(1,1,0); glVertex2f(-.7f,.7f);
            glEnd(); printf("first-provoking-flat-%d fbhash=%08x\n",mode,hash());
        }
        glShadeModel(GL_SMOOTH); glClear(GL_COLOR_BUFFER_BIT);
        glBegin(GL_TRIANGLE_FAN); triangle(); glEnd();
        printf("first-provoking-smooth fbhash=%08x\n",hash()); provoking(0x8e4e);
    }
    (void)argv;
    if (argc == 1) {
    glShadeModel(GL_SMOOTH); glPolygonMode(GL_FRONT_AND_BACK,GL_LINE);
    glClear(GL_COLOR_BUFFER_BIT); glBegin(GL_QUADS);
    glVertex2f(-.7f,-.7f); glVertex2f(.7f,-.7f); glVertex2f(.7f,.7f); glVertex2f(-.7f,.7f);
    glEnd(); printf("wireframe-quad fbhash=%08x\n",hash());
    glPolygonMode(GL_FRONT_AND_BACK,GL_FILL);
    }
    typedef void (WINAPI *Active)(GLenum);
    Active active=(Active)wglGetProcAddress("glActiveTextureARB");
    if (active && argc > 1) {
        typedef void (WINAPI *Multi)(GLenum, GLfloat, GLfloat);
        Active client=(Active)wglGetProcAddress("glClientActiveTexture");
        Multi multi=(Multi)wglGetProcAddress("glMultiTexCoord2f");
        static float other_coords[8]={0,0,0,0,0,0,0,0};
        active(0x84c1);
        if (multi) multi(0x84c1,.25f,.75f);
        if (client) {
            client(0x84c1); glTexCoordPointer(2,GL_FLOAT,0,other_coords);
            glEnableClientState(GL_TEXTURE_COORD_ARRAY);
        }
        if (test_program) {
            const char *vsrc="#version 120\nvoid main(){gl_Position=ftransform();gl_FrontColor=vec4(gl_MultiTexCoord1.xy,0,1);}";
            source(test_vertex,1,&vsrc,0); compile(test_vertex); link(test_program); use(test_program);
        }
        /* Other-unit client arrays must be ignored by immediate submission;
           the shader must see the constant current coordinate, not zeros. */
        glClear(GL_COLOR_BUFFER_BIT); glBegin(GL_TRIANGLES); triangle(); glEnd();
        printf("other-unit-current fbhash=%08x\n",hash());
        GLint unit=0; glGetIntegerv(0x84e0,&unit); if (unit!=0x84c1) failures++;
        if (client) {
            glGetIntegerv(0x84e1,&unit); if (unit!=0x84c1) failures++;
            if (!glIsEnabled(GL_TEXTURE_COORD_ARRAY)) failures++;
            void *coords=0; glGetPointerv(GL_TEXTURE_COORD_ARRAY_POINTER,&coords);
            if (coords!=other_coords) failures++;
        }
        glClear(GL_COLOR_BUFFER_BIT); glBegin(GL_TRIANGLES);
        glVertex2f(-.9f,-.9f);
        if (multi) multi(0x84c1,.75f,.25f); /* Must replay this open block. */
        glVertex2f(.8f,-.9f); glVertex2f(0,.8f); glEnd();
        printf("in-block-multitexture fbhash=%08x\n",hash());
        if (test_program) use(0);
        if (client) { glDisableClientState(GL_TEXTURE_COORD_ARRAY); client(0x84c0); }
        active(0x84c0);
        glClear(GL_COLOR_BUFFER_BIT); glBegin(GL_TRIANGLES); triangle(); glEnd();
        printf("multitexture-fallback fbhash=%08x\n",hash());
    }
    GLenum error=glGetError();
    printf("state-failures=%d gl-error=%u\n",failures,error);
    wglMakeCurrent(0,0); wglDeleteContext(rc); ReleaseDC(w,dc); DestroyWindow(w);
    return failures || error ? 1 : 0;
}
