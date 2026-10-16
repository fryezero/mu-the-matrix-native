/* fpbench: MU-like float transform loop (matrix * vertex), compiled for x87 or SSE. */
#include <windows.h>
#include <stdio.h>
int main(void) {
    static float m[3][4] = {{0.9f,0.1f,0.2f,1},{-0.1f,0.95f,0.05f,2},{0.2f,-0.05f,0.97f,3}};
    static float v[4096][3], o[4096][3];
    for (int i = 0; i < 4096; i++) { v[i][0] = i * 0.01f; v[i][1] = i * 0.02f; v[i][2] = i * 0.03f; }
    LARGE_INTEGER f, a, b; QueryPerformanceFrequency(&f); QueryPerformanceCounter(&a);
    for (int it = 0; it < 4000; it++)
        for (int i = 0; i < 4096; i++) {
            o[i][0] = m[0][0]*v[i][0] + m[0][1]*v[i][1] + m[0][2]*v[i][2] + m[0][3];
            o[i][1] = m[1][0]*v[i][0] + m[1][1]*v[i][1] + m[1][2]*v[i][2] + m[1][3];
            o[i][2] = m[2][0]*v[i][0] + m[2][1]*v[i][1] + m[2][2]*v[i][2] + m[2][3];
            v[i][0] = o[i][1] * 0.999f; /* dependency to defeat hoisting */
        }
    QueryPerformanceCounter(&b);
    double s = (double)(b.QuadPart - a.QuadPart) / f.QuadPart;
    printf("%s: %.3fs  %.1f Mverts/s  (chk %f)\n", MODE, s, 4096.0 * 4000 / s / 1e6, o[17][2]);
    return 0;
}
