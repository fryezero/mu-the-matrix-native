    .text
    .globl _cap_cdecl3, _cap_this, _cap_this2
/* void cap_cdecl3(void *fn, void *a, void *b, void *c) -> regs[0..2] = eax, ecx, edx after call */
_cap_cdecl3:
    push %ebx
    mov 8(%esp),%ebx
    pushl 20(%esp)
    pushl 20(%esp)
    pushl 20(%esp)
    call *%ebx
    add $12,%esp
    mov %eax,_regs
    mov %ecx,_regs+4
    mov %edx,_regs+8
    pop %ebx
    ret
/* void cap_this(void *fn, void *thisp, int nargs, void *arg)  (callee pops its stack arg) */
_cap_this:
    push %ebx
    mov 8(%esp),%ebx
    mov 12(%esp),%ecx
    cmpl $0,16(%esp)
    je 1f
    pushl 20(%esp)
1:  call *%ebx
    mov %eax,_regs
    mov %ecx,_regs+4
    mov %edx,_regs+8
    pop %ebx
    ret
/* void cap_this2(void *fn, void *thisp, int a0, int a1)  (callee pops 8) */
_cap_this2:
    push %ebx
    mov 8(%esp),%ebx
    mov 12(%esp),%ecx
    mov $0x5a5a5a5a,%edx
    pushl 20(%esp)
    pushl 20(%esp)
    call *%ebx
    mov %eax,_regs
    mov %ecx,_regs+4
    mov %edx,_regs+8
    pop %ebx
    ret
