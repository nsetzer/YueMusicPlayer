
@echo off

:: this is intended as a template of what needs to be done to
:: run cmake for MSVC 2015. you may need to change binary paths

:: Run this once to generate a cache, you will get a number of errors
:: related tot he variables defined below
:: Once the cache has been generated run this script again to generate the
:: make files.

cd %~dp0

:: out-of-source build design pattern came from
:: http://stackoverflow.com/questions/7724569/debug-vs-release-in-cmake

if not exist MSVC mkdir MSVC

if not exist "C:\Program Files (x86)\CMake\bin\cmake.exe" goto CmakeError
if not exist "C:\Program Files (x86)\Microsoft Visual Studio 14.0\Common7\Tools\vsvars32.bat" goto VarsError

cd MSVC

call "C:\Program Files (x86)\Microsoft Visual Studio 14.0\Common7\Tools\vsvars32.bat"

"C:\Program Files (x86)\CMake\bin\cmake.exe" -G  "Visual Studio 14 2015 Win64" ..

pause

exit;

CmakeError:
echo "CMAKE not found"
pause
exit 1;

VarsError:
echo "vsvars32.bat not found"
pause
exit 1;

