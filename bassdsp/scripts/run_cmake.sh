
# run cmake for MSVS:
#D:\Dropbox\Code\packages\EBFS2\libebfs\MSVS-Debug>"C:\Program Files (x86)\Microsoft Visual Studio 14.0\Common7\Tools\vsvars32.bat"
#D:\Dropbox\Code\packages\EBFS2\libebfs\MSVS-Debug>"C:\Program Files (x86)\CMake\bin\cmake.exe" -G  "Visual Studio 14 2015 Win64" ..

export CMAKE_C_COMPILER_ENV_VAR="%CMAKE_C_COMPILER_ENV_VAR%"
export CMAKE_CXX_COMPILER_ENV_VAR="%CMAKE_CXX_COMPILER_ENV_VAR%"

export CMAKE_C_COMPILER="`which gcc`"
export CMAKE_CXX_COMPILER="`which g++`"

export CC="$CMAKE_C_COMPILER"
export CXX="$CMAKE_CXX_COMPILER"

CMAKE_LEGACY_CYGWIN_WIN32=0
#export CMAKE_LEGACY_CYGWIN_WIN32=0

echo $CC
echo $CXX
# out-of-source build design pattern came from
# http://stackoverflow.com/questions/7724569/debug-vs-release-in-cmake

# change the directory name when running under cygwin,
# so that mingw and cygwim can live side by side
platname=
[[ "$(uname)" = "CYGWIN"* ]] && platname=Cygwin-
[[ "$(uname)" = "MSYS"* ]] && platname=MSYS-
[[ "$(uname)" = "MINGW"* ]] && platname=MINGW-

[ -d ./${platname}Debug   ] || mkdir ${platname}Debug
[ -d ./${platname}Release ] || mkdir ${platname}Release

cd ./${platname}Debug
cmake -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Debug \
                          -DCMAKE_MACOSX_RPATH=NEW \
                          -DCMAKE_C_COMPILER="$CC" \
                          -DCMAKE_CXX_COMPILER="$CXX" \
                          ..

cd ../${platname}Release
cmake -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release \
                          -DCMAKE_MACOSX_RPATH=NEW \
                          -DCMAKE_C_COMPILER="$CC" \
                          -DCMAKE_CXX_COMPILER="$CXX" \
                          ..

cd ..

#D:\Dropbox\Code\packages\EBFS2\libebfs