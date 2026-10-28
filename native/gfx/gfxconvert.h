/* DATA-ACQ-003. Internal helpers for the local GFx-to-SWF converter.
 * Inputs and outputs contain the user's data and must remain outside Git. */
#ifndef MU_GFXCONVERT_H
#define MU_GFXCONVERT_H
#include <stdint.h>
#include <stddef.h>
typedef struct { unsigned char *p; size_t n, cap; } Buf;
typedef struct { const unsigned char *p; size_t n, pos; } Read;
typedef struct { int code; Read data; } Tag;
typedef struct { Buf body; size_t tags; unsigned char version; } Movie;
typedef struct { int w, h; unsigned char *px; } Image;
void fail(const char *fmt, ...);
void *mem(size_t n);
void *grow(void *p, size_t n);
void add(Buf *b, const void *p, size_t n);
void byte(Buf *b, unsigned v);
void word(Buf *b, unsigned v);
void dword(Buf *b, uint32_t v);
void strz(Buf *b, const char *s);
unsigned u8(Read *r);
unsigned u16(Read *r);
uint32_t u32(Read *r);
Read take(Read *r, size_t n);
char *cstring(Read *r);
char *pstring(Read *r);
size_t rect_size(Read *r);
int next_tag(Read *r, Tag *t);
void tag(Buf *b, int code, Buf data, int force_long);
Buf deflate_buf(const void *p, size_t n, int level);
Buf container(const char *path);
Movie movie(const char *path);
int gfx_try_movie(const char *path);
Buf gfx_read_text(const char *path);
int gfx_file_exists(const char *path);
char *path_join(const char *a, const char *b);
Image decode_dds(Buf data);
Image crop(Image src, int x1, int y1, int x2, int y2);
Image resize(Image src, int w, int h);
Buf lossless(unsigned id, Image im);
int inline_fonts(Buf *out, Tag t, const char *dir, const char *config, int subset);
Buf host_actions(char **vars, int count, int bridge);
#endif
