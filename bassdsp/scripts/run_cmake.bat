
@echo off

:: Run this once to generate a cache, you will get a number of errors
:: related tot he variables defined below
:: Once the cache has been generated run this script again to generate the
:: make files.

set CMAKE_C_COMPILER_ENV_VAR="%CMAKE_C_COMPILER_ENV_VAR%"
set CMAKE_CXX_COMPILER_ENV_VAR="%CMAKE_CXX_COMPILER_ENV_VAR%"

set CMAKE_C_COMPILER="C:\\mingw64\\bin\\gcc.exe"
set CMAKE_CXX_COMPILER="C:\\mingw64\\bin\\gcc.exe"

:: out-of-source build design pattern came from
:: http://stackoverflow.com/questions/7724569/debug-vs-release-in-cmake

if not exist Debug mkdir Debug
if not exist Release mkdir Release

cd Debug
cmake -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Debug ..

cd ../Release
cmake -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release ..

cd ..

pause

:: mkdir vs && cd vs
::set CMAKE_C_COMPILER="C:\MicrosoftVisualStudio11.0\VC\bin\x86_amd64\cl.exe"
::set CMAKE_CXX_COMPILER="C:\MicrosoftVisualStudio11.0\VC\bin\x86_amd64\cl.exe"
::cmake -G "Visual Studio 11 2012" -DCMAKE_BUILD_TYPE=Release ..