cmake_minimum_required(VERSION 2.8)
project (BASSDSP)

enable_testing()

#include(CMakeCover.txt)

message("build type is: ${CMAKE_BUILD_TYPE}")

set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

set(BASE_PATH "${PROJECT_SOURCE_DIR}/src")
if(${APPLE})
  set(BASS_PLATFORM "darwin")
  set(BASS_LIB "libbass.dylib")
elseif (${WIN32})
  set(BASS_PLATFORM "win32")
  set(BASS_LIB "bass.lib")
else()
  set(BASS_PLATFORM "linux")
  set(BASS_LIB "libbass.so")
endif()
set(TARGET_PATH "${PROJECT_SOURCE_DIR}/../lib/${BASS_PLATFORM}/x86_64")

set(src_alien
        ${BASE_PATH}/alien/bass/bass_util.c
    )

set(src_other
        ${BASE_PATH}/core/oFloatVector.c
        ${BASE_PATH}/filter/zbfilter.c
        ${BASE_PATH}/filter/oMovingAvg.c
        ${BASE_PATH}/filter/oDF2.c
    )

set(src_dsp
        ${BASE_PATH}/bassdsp/dsp_VolEQ.c
        ${BASE_PATH}/bassdsp/dsp_ZBLOG.c
        ${BASE_PATH}/bassdsp/dsp_ZBPEQ.c
        ${BASE_PATH}/bassdsp/dsp_ZBVEQ.c
        ${BASE_PATH}/bassdsp/dsp_ZBVIS.c
        ${BASE_PATH}/bassdsp.c
    )

set(src_all
        ${src_alien}
        ${src_other}
        ${src_dsp}
    )

include_directories( ${BASE_PATH} )

if(NOT ${MSVC})
  add_definitions("-Wall")
  #add_definitions("-Werror")
  add_definitions("-Wno-attributes")
  add_definitions("-Wno-unused-label")
  add_definitions("-Wno-unused-parameter")
  add_definitions("-Wno-unused-variable")
  add_definitions("-Wno-unused-function")
  add_definitions("-Wno-sequence-point")
endif()

# TODO: use find_package(Threads)
if(${WIN32})
  message("Multi Threading not supported.")
  set(SUPPORT_THREADING FALSE)
else()
  # MSYS, UNIX, possibly mingw
  add_definitions("-DHAVE_PTHREAD")
  set(SUPPORT_THREADING TRUE)
endif()

if("${CMAKE_BUILD_TYPE}" MATCHES "Release")
    add_definitions("-s")
    add_definitions("-O2")
else()
  if(NOT ${MSVC})
    #add_definitions("-ftest-coverage")
    #add_definitions("-fprofile-arcs")
  endif()
endif()

message("Platform: ${CMAKE_SYSTEM_NAME} : supports threading ${SUPPORT_THREADING}")
#------------------------------------------------------------------------------
# Lib

add_library(bassdsp SHARED ${src_all})

install(TARGETS bassdsp
        DESTINATION ${TARGET_PATH})

if(NOT ${MSVC})
set_target_properties(bassdsp
                      PROPERTIES COMPILE_FLAGS "-std=c11")
endif()

# TARGET_LINK_LIBRARIES(bassdsp ${LIBBASS})
TARGET_LINK_LIBRARIES(bassdsp ${TARGET_PATH}/${BASS_LIB})
