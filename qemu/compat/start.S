.text
.global _start
.type _start, %function
_start:
    mov x29, xzr
    mov x30, xzr
    bl main
    mov x8, #93
    svc #0
