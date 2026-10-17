/* Replacement bodies for hot unoptimized helpers in Mu The Matrix main.exe.
   Each matches the original's results, memory effects and final eax/ecx/edx. */
    .text
    .globl _hp_vrot, _hp_vrot_end, _hp_vtrans, _hp_vtrans_end
    .globl _hp_store8, _hp_store8_end
    .globl _hp_self, _hp_self_end, _hp_index, _hp_index_end, _hp_deref16, _hp_deref16_end, _hp_eq, _hp_eq_end
/* 0x00d000ad: void VectorRotate(const float in[3], const float m[3][4], float out[3]) (cdecl) */
_hp_vrot:
    mov 4(%esp),%edx; mov 8(%esp),%eax; mov 12(%esp),%ecx
    movss (%edx),%xmm0;  mulss (%eax),%xmm0;   movss 4(%edx),%xmm1; mulss 4(%eax),%xmm1;  addss %xmm1,%xmm0; movss 8(%edx),%xmm1; mulss 8(%eax),%xmm1;  addss %xmm1,%xmm0; movss %xmm0,(%ecx)
    movss (%edx),%xmm0;  mulss 16(%eax),%xmm0; movss 4(%edx),%xmm1; mulss 20(%eax),%xmm1; addss %xmm1,%xmm0; movss 8(%edx),%xmm1; mulss 24(%eax),%xmm1; addss %xmm1,%xmm0; movss %xmm0,4(%ecx)
    movss (%edx),%xmm0;  mulss 32(%eax),%xmm0; movss 4(%edx),%xmm1; mulss 36(%eax),%xmm1; addss %xmm1,%xmm0; movss 8(%edx),%xmm1; mulss 40(%eax),%xmm1; addss %xmm1,%xmm0; movss %xmm0,8(%ecx)
    mov $8,%eax; mov $8,%edx
    ret
_hp_vrot_end:
/* 0x00d002b2: void VectorTransform(const float in[3], const float m[3][4], float out[3]) (cdecl) */
_hp_vtrans:
    mov 4(%esp),%edx; mov 8(%esp),%eax; mov 12(%esp),%ecx
    movss (%edx),%xmm0;  mulss (%eax),%xmm0;   movss 4(%edx),%xmm1; mulss 4(%eax),%xmm1;  addss %xmm1,%xmm0; movss 8(%edx),%xmm1; mulss 8(%eax),%xmm1;  addss %xmm1,%xmm0; addss 12(%eax),%xmm0; movss %xmm0,(%ecx)
    movss (%edx),%xmm0;  mulss 16(%eax),%xmm0; movss 4(%edx),%xmm1; mulss 20(%eax),%xmm1; addss %xmm1,%xmm0; movss 8(%edx),%xmm1; mulss 24(%eax),%xmm1; addss %xmm1,%xmm0; addss 28(%eax),%xmm0; movss %xmm0,4(%ecx)
    movss (%edx),%xmm0;  mulss 32(%eax),%xmm0; movss 4(%edx),%xmm1; mulss 36(%eax),%xmm1; addss %xmm1,%xmm0; movss 8(%edx),%xmm1; mulss 40(%eax),%xmm1; addss %xmm1,%xmm0; addss 44(%eax),%xmm0; movss %xmm0,8(%ecx)
    mov $8,%eax; mov $8,%edx
    ret
_hp_vtrans_end:
/* 0x00cfc94a: thiscall T *get() { return this; } */
_hp_self:
    mov %ecx,%eax
    ret
_hp_self_end:
/* 0x00cfc922: thiscall float *at(int i) { return &((float *)this)[i]; } */
_hp_index:
    mov 4(%esp),%eax
    lea (%ecx,%eax,4),%eax
    ret $4
_hp_index_end:
/* 0x00c9b276: thiscall char *f() { return *(char **)this + 0x10; } */
_hp_deref16:
    mov (%ecx),%eax
    add $0x10,%eax
    ret
_hp_deref16_end:
/* 0x00c9b0e4: thiscall bool operator==(const It *o) { return *(int *)this == *(int *)o; } (ecx ends = o) */
_hp_eq:
    mov (%ecx),%eax
    mov 4(%esp),%ecx
    cmp (%ecx),%eax
    sete %al
    movzbl %al,%eax
    ret $4
_hp_eq_end:
/* 0x00c9aa15 / 0x00c9a992 / 0x00c9a9af: thiscall It *init(T v, U unused) { *(T *)this = v; return this; } (ret 8, ecx ends = this) */
_hp_store8:
    mov 4(%esp),%eax
    mov %eax,(%ecx)
    mov %ecx,%eax
    ret $8
_hp_store8_end:
