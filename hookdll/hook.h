#ifndef PY_KEY_HOOK_H
#define PY_KEY_HOOK_H

#ifdef BUILD_HOOK_DLL
#define HOOK_DLL __declspec(dllexport)
#else
#define HOOK_DLL __declspec(dllimport)
#endif

typedef int (*KEYHOOKPROC)(DWORD vkCode,DWORD scanCode, DWORD flags, DWORD time);

int HOOK_DLL listen_keyboard(KEYHOOKPROC proc);
void HOOK_DLL unhook(void);

#endif
