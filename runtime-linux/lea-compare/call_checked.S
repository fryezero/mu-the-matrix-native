/* GCC/MinGW i386 cdecl bridge. Call only the pinned, bounded decoder.
 * Records its callee-saved registers, DF and stack pointer before restoring
 * the runner's frame/flags. A broken stack may fault, which fails the run.
 */
.text
.globl _mu_lea_call_checked
_mu_lea_call_checked:
    pushl %ebp
    movl %esp, %ebp
    pushl %ebx
    pushl %esi
    pushl %edi
    subl $4, %esp
    pushfl
    popl %eax
    movl %eax, -16(%ebp)
    movl 32(%ebp), %ecx
    movl %ebp, 28(%ecx)
    pushl %ecx
    pushl 24(%ebp)
    pushl 20(%ebp)
    pushl 16(%ebp)
    pushl 12(%ebp)
    movl %esp, 24(%ecx)
    movl 8(%ebp), %eax
    cmpl $0, 28(%ebp)
    je 1f
    std
    jmp 2f
1:  cld
2:  movl $0x12345678, %ebx
    movl $0x23456789, %esi
    movl $0x3456789a, %edi
    movl $0x456789ab, %ebp
    call *%eax
    pushfl
    popl %edx
    movl 16(%esp), %eax
    movl %ebx, 0(%eax)
    movl %esi, 4(%eax)
    movl %edi, 8(%eax)
    movl %ebp, 12(%eax)
    movl %edx, 16(%eax)
    movl %esp, 20(%eax)
    movl 28(%eax), %ebp
    pushl -16(%ebp)
    popfl
    leal -12(%ebp), %esp
    popl %edi
    popl %esi
    popl %ebx
    popl %ebp
    ret

/* Authored negative control for the bridge's own register/DF checks. */
.globl _mu_lea_bad_callee
_mu_lea_bad_callee:
    xorl %ebx, %ebx
    std
    ret
