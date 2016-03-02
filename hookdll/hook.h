#ifndef PY_KEY_HOOK_H
#define PY_KEY_HOOK_H

#ifdef BUILD_HOOK_DLL
#define HOOK_DLL __declspec(dllexport)
#else
#define HOOK_DLL __declspec(dllimport)
#endif

// bit mask for 'flags'
// if this flag is set then these buttons are held down
#define KEY_SHIFT   0x100
#define KEY_CTRL    0x200
// if this bit is true, key event is 'release', otherwise 'press'
#define KEY_RELEASE 0x80

extern "C"
{
typedef int (*KEYHOOKPROC)(DWORD vkCode,DWORD scanCode, DWORD flags, DWORD time, unsigned short ascii);

int HOOK_DLL listen_keyboard(KEYHOOKPROC proc);
void HOOK_DLL unhook(void);
}

#endif
