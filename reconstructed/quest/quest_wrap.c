/* The client's text wrap 0x011ff794 and its line cutter 0x01193941 (NATIVE-QUEST-002); see quest.h.
 *
 * 0x011ff794(lines, max_lines, stride, text, width, bullet, delimiters, indent, indent_from): the text is copied,
 * cut into pieces with strtok at the delimiters (the caller passes up to four characters by value), every piece
 * (" %s" with the bullet flag) is cut into lines by 0x01193941: a line keeps the characters whose prefix measures
 * (GetTextExtentPointA on the interface font) less than width * [0x06fbcd94] (the screen rate) and at most
 * stride - 1 bytes; a piece filling every line it may use reports one line more.  With indent > 0 the lines from
 * indent_from on get indent spaces in front (strcat_s / strcpy_s on 0x104-byte buffers). */
#include "quest_internal.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int32_t measure(const mu_quest_client *c, const char *text, int32_t n)
{
    return c && c->host.measure ? c->host.measure(c->host.user, text, n) : n * 6;
}

/* 0x01193941(text, dst, width, max_lines, stride, flag 0) */
static int cut_lines(const mu_quest_client *c, const char *text, char *dst, int32_t width, int max_lines, int stride,
                     float scale)
{
    if (!text)
        return 0;
    const char *p = text;
    int32_t total = (int32_t)strlen(text) + 1, cut = 0;
    int32_t wpx = (int32_t)((float)width * (MU_QUEST_MUTATION == 10 ? 1.0f : scale));
    int line, done = 0;
    for (line = 0; line < max_lines; line++) {
        int32_t n = 0, w = 0, k = 0;
        do {
            if (stride <= n)
                break;
            k = 1;                       /* _mbclen 0x01994240: the client's text is single-byte here */
            n += k;
            cut += k;
            w = measure(c, p, n);
            if (total <= cut) {
                done = 1;
                break;
            }
        } while (w < wpx);
        n -= k;
        cut -= k;
        memcpy(dst, p, (size_t)n);
        dst[n] = 0;
        if (done)
            break;
        p += n;
        dst += stride;
    }
    return line + 1;
}

int mu_quest_wrap(const mu_quest_client *c, char *lines, int max_lines, int stride, const char *text, int32_t width,
                  int bullet, const char *delimiters, int indent, int indent_from, float scale)
{
    if (!lines || max_lines < 1 || stride < 1 || !text || width < 0x10)
        return 0;
    size_t length = strlen(text);
    if (length < 1)
        return 0;
    char *buf = malloc(length + 1);
    if (!buf)
        return 0;
    memcpy(buf, text, length + 1);
    int count = 0;
    char *save = NULL;
    for (char *tok = strtok_r(buf, delimiters ? delimiters : "", &save); tok && count < max_lines;
         tok = strtok_r(NULL, delimiters ? delimiters : "", &save)) {
        if (!bullet) {
            count += cut_lines(c, tok, lines + (size_t)count * (size_t)stride, width, max_lines - count, stride, scale);
        } else {
            char piece[1024];
            snprintf(piece, sizeof piece, " %s", tok);
            count += cut_lines(c, piece, lines + (size_t)count * (size_t)stride, width, max_lines - count, stride,
                               scale);
        }
    }
    if (indent != 0) {
        char pad[0x104], keep[0x104];
        memset(pad, 0, sizeof pad);
        for (int i = 0; i < indent && strlen(pad) + 1 < sizeof pad; i++)
            strcat(pad, " ");
        memcpy(keep, pad, sizeof keep);
        for (int i = indent_from < 0 ? 0 : indent_from; i < count && i < max_lines; i++) {
            char *line = lines + (size_t)i * (size_t)stride;
            size_t room = sizeof pad - strlen(pad) - 1;
            strncat(pad, line, room);
            snprintf(line, (size_t)stride, "%s", pad);   /* strcpy_s: the client stops on an overflow */
            memcpy(pad, keep, sizeof pad);
        }
    }
    free(buf);
    return count;
}
