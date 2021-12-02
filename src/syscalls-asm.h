#pragma once
#include <windows.h>

#if _WIN64

#define IsWoW64 IsWoW64
__asm__("IsWoW64: \n\
	mov rax, 0 \n\
	ret \n\
");

#define ZwProtectVirtualMemory NtProtectVirtualMemory
__asm__("NtProtectVirtualMemory: \n\
	push rcx \n\
	push rdx \n\
	push r8 \n\
	push r9 \n\
	sub rsp, 0x28 \n\
	call GetSyscallAddress \n\
	add rsp, 0x28 \n\
	push rax \n\
	sub rsp, 0x28 \n\
	mov ecx, 0x1784EDE7 \n\
	call SW2_GetSyscallNumber \n\
	add rsp, 0x28 \n\
	pop r11 \n\
	pop r9 \n\
	pop r8 \n\
	pop rdx \n\
	pop rcx \n\
	mov r10, rcx \n\
	jmp r11 \n\
");

#else

#define IsWoW64 IsWoW64
__asm__("IsWoW64: \n\
	mov eax, fs:[0xc0] \n\
	test eax, eax \n\
	jne wow64 \n\
	mov eax, 0 \n\
	ret \n\
	wow64: \n\
	mov eax, 1 \n\
	ret \n\
");

#define ZwProtectVirtualMemory NtProtectVirtualMemory
__asm__("NtProtectVirtualMemory: \n\
	call GetSyscallAddress \n\
	push eax \n\
	push 0x1784EDE7 \n\
	call SW2_GetSyscallNumber \n\
	add esp, 4 \n\
	pop ebx \n\
	mov edx, esp \n\
	sub edx, 4 \n\
	call ebx \n\
	ret \n\
");

#endif
