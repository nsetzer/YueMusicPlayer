::#! call $this

::gcc -O3 hook_main.c hook.c -o hook_main.exe

g++ -std=c++11 -DBUILD_HOOK_DLL -c hook.cpp -o hook.o
g++ -std=c++11 -shared -Wl,--out-implib,libhook.a -o hook.dll hook.o