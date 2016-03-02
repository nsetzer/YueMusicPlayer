
/**

file: hook.cpp
author: nsetzer
description: This file implements a keyboard listener
The code is based off of the pyHook library.
a bug in the existing pyHook module prevents its use with pyinstaller.

*/

#define _WIN32_WINNT 0x400
#include "windows.h"

#include <stdio.h>
#include <stdlib.h>
#include <mutex>

#include "hook.h"

HHOOK key_hook=NULL;
KEYHOOKPROC key_hook_proc = NULL;
UINT_PTR timerId = 0;
int alive = 1;
std::mutex hook_mutex;
BYTE key_state[256];

void SetKeyState(unsigned int vkey, int down) {
    switch (vkey) {
        case VK_MENU:
        case VK_LMENU:
        case VK_RMENU:
            key_state[vkey] = (down) ? 0x80 : 0x00;
            key_state[VK_MENU] = key_state[VK_LMENU] | key_state[VK_RMENU];
        case VK_SHIFT:
        case VK_LSHIFT:
        case VK_RSHIFT:
            key_state[vkey] = (down) ? 0x80 : 0x00;
            key_state[VK_SHIFT] = key_state[VK_LSHIFT] | key_state[VK_RSHIFT];
            break;
        case VK_CONTROL:
        case VK_LCONTROL:
        case VK_RCONTROL:
            key_state[vkey] = (down) ? 0x80 : 0x00;
            key_state[VK_CONTROL] = key_state[VK_LCONTROL] | key_state[VK_RCONTROL];
            break;
        // toggle these values on press
        case VK_NUMLOCK:
            if (!down)
                key_state[VK_NUMLOCK] = !key_state[VK_NUMLOCK];
        case VK_CAPITAL:
            if (!down)
                key_state[VK_CAPITAL] = !key_state[VK_CAPITAL];
        case VK_SCROLL:
            if (!down)
                key_state[VK_SCROLL] = !key_state[VK_SCROLL];
    }
}

void UpdateKeyState(unsigned int vkey, int msg) {
    if (msg == WM_KEYDOWN || msg == WM_SYSKEYDOWN) {
            SetKeyState(vkey, 1);
    } else if (msg == WM_KEYUP || msg == WM_SYSKEYUP) {
            SetKeyState(vkey, 0);
    }
}

unsigned short ConvertToASCII(unsigned int keycode, unsigned int scancode) {
    int r;
    unsigned short c = 0;

    r = ToAscii(keycode, scancode, key_state, &c, 0);
    if(r < 0) {
        return 0;
    }
    return c;
}

LRESULT CALLBACK cLLKeyboardCallback(int code, WPARAM wParam, LPARAM lParam) {
    long result=1;
    PKBDLLHOOKSTRUCT kbd;
    int pass=1;
    unsigned short ascii;
    DWORD flags;

    kbd = (PKBDLLHOOKSTRUCT)lParam;
    ascii = ConvertToASCII(kbd->vkCode, kbd->scanCode);
    flags = kbd->flags;
    flags |= (key_state[VK_SHIFT]>0)?KEY_SHIFT:0;
    flags |= (key_state[VK_CONTROL]>0)?KEY_CTRL:0;

    //printf("%vk:%x scan:%x flags:%x\n",kbd->vkCode, kbd->scanCode,kbd->flags);

    if (key_hook_proc!=NULL)
        pass = key_hook_proc(kbd->vkCode, kbd->scanCode, flags, kbd->time, ascii);

    if (code <0 || pass) {
        UpdateKeyState(kbd->vkCode, wParam);
        result = CallNextHookEx(key_hook, code, wParam, lParam);
    }
    return result;
}

int print_key_code(DWORD vkCode, DWORD scanCode, DWORD flags, DWORD time, unsigned short ascii) {
    // https://msdn.microsoft.com/en-us/library/windows/desktop/ms644967%28v=vs.85%29.aspx
    printf("0x%X 0x%X 0x%X %d ascii:%d\n", vkCode, scanCode, flags, time, ascii);
    return 1;
}

int HOOK_DLL listen_keyboard(KEYHOOKPROC proc) {
    HINSTANCE hMod;
    MSG message;
    BOOL bRet;
    UINT timeout = 500; // milliseconds
    memset(key_state, 0, 256);
    key_state[VK_NUMLOCK] = (GetKeyState(VK_NUMLOCK)&0x0001) ? 0x01 : 0x00;
    key_state[VK_CAPITAL] = (GetKeyState(VK_CAPITAL)&0x0001) ? 0x01 : 0x00;
    key_state[VK_SCROLL] = (GetKeyState(VK_SCROLL)&0x0001) ? 0x01 : 0x00;

    hMod = GetModuleHandle(NULL);

    key_hook_proc = (proc==NULL)?print_key_code:proc;

    if (hMod!=NULL) {
        key_hook = SetWindowsHookEx(WH_KEYBOARD_LL, cLLKeyboardCallback, (HINSTANCE) hMod, 0);

        alive = 1;
        if (timerId!=0) {
            printf("kill timer\n");
            KillTimer(NULL, timerId);
            timerId = 0;
        }

        timerId = SetTimer(NULL, (UINT_PTR)NULL, timeout, NULL);

        while ( (bRet = GetMessage(&message,NULL,0,0))!=0 ) {

            if (bRet == -1) {
                printf("error retrieving message\n");
            }
            else if (message.message != WM_TIMER) {
                TranslateMessage( &message );
                DispatchMessage( &message );
            }

            hook_mutex.lock();
            if (!alive) {
                hook_mutex.unlock();
                break;
            }
            hook_mutex.unlock();
        }

        if (key_hook!=NULL) {
            printf("unhook\n");
            UnhookWindowsHookEx(key_hook);
            key_hook = NULL;
        }

        if (timerId!=0) {
            printf("kill timer\n");
            KillTimer(NULL, timerId);
            timerId = 0;
        }

    }
    else
        printf("error setting keyboard hook\n");
    return 0;
}

void HOOK_DLL unhook(void) {
    hook_mutex.lock();
    printf("unhook %d\n",timerId);
    alive = 0;
    hook_mutex.unlock();
}
