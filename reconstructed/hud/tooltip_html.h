/* Reconstructed GFx tooltip assembly (NATIVE-HUD-001).
 *
 * The game builds an item tooltip as the classic MU text list: up to N lines
 * of 0xff bytes (TextList), a colour index (TextListColor), a bold flag
 * (TextBold) and a raw-HTML flag per line.  In this client the arrays sit at
 * 0x10c76988 / 0x10c7b938 / 0x10c7ba78 / 0x10c7bbb8, outside the image (a
 * runtime module relocated them).  The InfoPopup window (GFx movie
 * "InfoPopup", handler 0x00b8d94b) turns the list into HTML and invokes
 * SetInfoPopup("%d %d %d %d %s", x, y, w, h, html) on the movie, after an
 * ANSI to UTF-8 conversion (0x00a99d93, MultiByteToWideChar(CP_ACP) then
 * WideCharToMultiByte(CP_UTF8)).
 */
#ifndef MU_HUD_TOOLTIP_HTML_H
#define MU_HUD_TOOLTIP_HTML_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Colour index -> "#RRGGBB" (the switch in 0x00ab4dc0; indices above 21 give #FFFFFF). */
const char *mu_tooltip_color_hex(int32_t color);

/* 0x00ab4dc0(out, text, color, bold): empty for "" and "\n"; every '<'
 * becomes "&lt;"; then "<font color='%s'><b>%s</b></font><br>" when bold is
 * 1, else "<font color='%s'>%s</font><br>".  Writes at most cap-1 bytes and
 * a terminator; returns the full length. */
size_t mu_tooltip_html_line(char *out, size_t cap, const char *text, int32_t color, int32_t bold);

typedef struct mu_tooltip_line {
    const char *text;
    int32_t color;
    int32_t bold;               /* not used by the InfoPopup path (it passes 0) */
    uint8_t raw;                /* 0x10c7bbb8: the text is appended as is */
} mu_tooltip_line;

/* The HTML body of 0x00b8d94b(count) before the UTF-8 conversion: lines
 * whose first byte is 0 are skipped, "\n" lines give "<BR>", raw lines are
 * copied, others go through mu_tooltip_html_line with bold 0; a line that
 * contains "starGrade*" is replaced by " " + n filled and 5-n empty star
 * images + " <br>", n being its last character read as a decimal digit
 * (*bad_star is set when that character is not a digit: the client's stoi
 * throws).  Returns the full length. */
size_t mu_tooltip_html(char *out, size_t cap, const mu_tooltip_line *lines, int32_t count, int *bad_star);

/* The popup rectangle words of the SetInfoPopup call: popup state +0x9c/+0xa0
 * (position) and the int rectangle +0x7c..+0x88, each divided by the GFx
 * manager rates 640/W and 480/H and truncated. */
void mu_tooltip_popup_rect(float px, float py, const int32_t rect[4], float rate_x, float rate_y, int32_t out[4]);

/* ANSI -> UTF-8 as the client's conversion does it under a Latin-1 code page
 * (a platform choice; CP_ACP is the boundary).  Returns the full length. */
size_t mu_latin1_to_utf8(char *out, size_t cap, const char *text);

#ifdef __cplusplus
}
#endif

#endif
