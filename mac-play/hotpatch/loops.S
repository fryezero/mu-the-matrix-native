    .text
    .globl _loop_direct, _loop_indirect
_loop_direct:
    push %esi; push %edi
    mov 12(%esp),%esi; mov 16(%esp),%edi
1:  push %edi
    call _vtx@4
    dec %esi; jnz 1b
    pop %edi; pop %esi; ret
_loop_indirect:
    push %esi; push %edi
    mov 12(%esp),%esi; mov 16(%esp),%edi
1:  push %edi
    call *_slot
    dec %esi; jnz 1b
    pop %edi; pop %esi; ret
