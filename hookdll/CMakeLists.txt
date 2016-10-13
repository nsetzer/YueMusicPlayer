cmake_minimum_required(VERSION 2.8)
project (HOOK)

message("build type is: ${CMAKE_BUILD_TYPE}")

set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

set(BASE_PATH "${PROJECT_SOURCE_DIR}/src")
set(TARGET_PATH "${PROJECT_SOURCE_DIR}/../lib/win32/x86_64")

set(src_hook
        ${BASE_PATH}/hook.cpp
        ${BASE_PATH}/hook.h
    )
include_directories( ${BASE_PATH} )

#------------------------------------------------------------------------------
# Lib

add_library(hook SHARED ${src_hook})

install(TARGETS hook
        DESTINATION ${TARGET_PATH})

