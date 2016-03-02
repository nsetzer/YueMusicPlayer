::#! call $this

::gcc -O3 hook_main.c hook.c -o hook_main.exe

gcc -DBUILD_HOOK_DLL -c hook.c -o hook.o -lws2_32 -lwsock32
gcc -shared -Wl,--out-implib,libhook.a -o hook.dll hook.o -lws2_32 -lwsock32