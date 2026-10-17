#include <windows.h>
#include <stdio.h>
volatile float sink;
__declspec(noinline) void __stdcall vtx(const float *v) { sink = v[0]; }
void (__stdcall *volatile slot)(const float *) = vtx;
extern void loop_direct(int n, const float *v);
extern void loop_indirect(int n, const float *v);
int main(void) {
    freopen("C:\\mutools\\cb.log", "w", stdout);
    float v[3] = {1, 2, 3}; LARGE_INTEGER f, a, b; QueryPerformanceFrequency(&f);
    for (int r = 0; r < 3; r++) {
        QueryPerformanceCounter(&a); loop_direct(20000000, v); QueryPerformanceCounter(&b);
        printf("direct   %.2f ns/call\n", (b.QuadPart - a.QuadPart) * 1e9 / f.QuadPart / 2e7);
        QueryPerformanceCounter(&a); loop_indirect(20000000, v); QueryPerformanceCounter(&b);
        printf("indirect %.2f ns/call\n", (b.QuadPart - a.QuadPart) * 1e9 / f.QuadPart / 2e7);
    }
    return 0;
}
