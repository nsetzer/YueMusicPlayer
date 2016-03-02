//#! gcc -O3 hook_main.c hook.c -o $bin && $bin

#define _WIN32_WINNT 0x400
#include "windows.h"

#include <stdio.h>
#include <stdlib.h>

#include "hook.h"

int main(void) {

    listen_keyboard(NULL);

    return 0;
}