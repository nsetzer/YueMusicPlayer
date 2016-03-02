//#! gcc -O3 $this -o $bin && $bin
#define _WIN32_WINNT 0x400
#include "windows.h"

#include <stdio.h>
#include <stdlib.h>

#include "hook.h"

HHOOK key_hook=NULL;
KEYHOOKPROC key_hook_proc = NULL;
int alive = 1;

LRESULT CALLBACK cLLKeyboardCallback(int code, WPARAM wParam, LPARAM lParam) {
    long result=1;
    PKBDLLHOOKSTRUCT kbd;
    int pass=1;

    kbd = (PKBDLLHOOKSTRUCT)lParam;

    //printf("%vk:%x scan:%x flags:%x\n",kbd->vkCode, kbd->scanCode,kbd->flags);

    if (key_hook_proc!=NULL)
        pass = key_hook_proc(kbd->vkCode, kbd->scanCode, kbd->flags, kbd->time);

    if (code <0 || pass)
        result = CallNextHookEx(key_hook, code, wParam, lParam);
    return result;
}


int print_key_code(DWORD vkCode, DWORD scanCode, DWORD flags, DWORD time) {
    // https://msdn.microsoft.com/en-us/library/windows/desktop/ms644967%28v=vs.85%29.aspx
    printf("0x%X 0x%X 0x%X %d\n", vkCode, scanCode, flags, time);
    return 1;
}

int HOOK_DLL listen_keyboard(KEYHOOKPROC proc) {
    HINSTANCE hMod;
    MSG message;
    BOOL bRet;
    UINT timeout = 500; // milliseconds
    UINT_PTR timerId;

    hMod = GetModuleHandle(NULL);

    key_hook_proc = (proc==NULL)?print_key_code:proc;

    if (hMod!=NULL) {
        key_hook = SetWindowsHookEx(WH_KEYBOARD_LL, cLLKeyboardCallback, (HINSTANCE) hMod, 0);

        alive = 1;
        timerId = SetTimer(NULL, (UINT_PTR)NULL, timeout, NULL);
        while ( (bRet = GetMessage(&message,NULL,0,0))!=0 ) {

            if (bRet == -1) {
                printf("error retrieving message\n");
            }
            else if (message.message != WM_TIMER) {
                TranslateMessage( &message );
                DispatchMessage( &message );
            }

            if (!alive)
                break;
        }

        if (key_hook!=NULL)
            UnhookWindowsHookEx(key_hook);

        KillTimer(NULL, timerId);

    }
    else
        printf("error setting keyboard hook\n");
    return 0;
}

void HOOK_DLL unhook(void) {
    //HINSTANCE hMod;
    //hMod = GetModuleHandle(NULL);
    //SendMessage(NULL,WM_CHAR,0x20,0);
    //PostMessage(HWND_BROADCAST, WM_KEYDOWN, VK_RETURN, 0);
    printf("unhook\n");
    alive = 0;
    //if (key_hook!=NULL) {
    //    UnhookWindowsHookEx(key_hook);
    //    key_hook = NULL;
    //}
}
