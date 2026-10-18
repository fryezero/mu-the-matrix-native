/* Interface between mugl (windows.h side) and jpegdec.c (libjpeg-turbo side). Plain types only. */
#ifndef MUGL_JPEGDEC_H
#define MUGL_JPEGDEC_H
#include <stddef.h>
typedef struct { int width, height, ncomp, jcs_in, jcs_out, progressive; } MjWant;   /* from the client's header parse */
typedef struct { unsigned char *pix; size_t cap; int width, height, comps, out_comps, msg; } MjImg;
enum { MJ_OK = 0, MJ_FRAME = 1, MJ_HEADER = 2, MJ_ERROR = 3, MJ_WARNING = 4 };
int mj_decode(const unsigned char *buf, unsigned long n, const MjWant *want, MjImg *o);
#endif
