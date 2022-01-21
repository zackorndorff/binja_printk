cmake_minimum_required(VERSION 3.9 FATAL_ERROR)

project(binja_printk)

if(NOT BNAPI_DIR)
	set(BNAPI_DIR "vendor/api"
		CACHE PATH "binaryninja-api root dir")
endif()

# Build fat Mach-O for macOS
if(NOT CMAKE_OSX_ARCHITECTURES)
	set(CMAKE_OSX_ARCHITECTURES "x86_64;arm64")
endif()

# Set headless to avoid trying to link against the UI library
set(HEADLESS ON CACHE BOOL "")
# We don't have libbinaryninjacore in CI, as it's part of the paid product.
# We have the headers, so tell the linker everything's ok.
# At the moment this requires a patch to binaryninja-api's CMakeLists.txt to
# stop trying to find_library the core. In CI, I use a sed command to patch it
# :/
if(CIBUILD)
	if(UNIX)
		if(APPLE)
			set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -Wl,-undefined,dynamic_lookup")
		else()
			set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -Wl,--unresolved-symbols=ignore-in-object-files")
		endif()
	endif()
	if(MSVC)
		set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} /FORCE:UNRESOLVED")
	endif()
endif()

file(GLOB SOURCES
	*.cpp
	*.h)

add_library(binja_printk SHARED ${SOURCES})

add_subdirectory(${BNAPI_DIR} binaryninja-api)

target_include_directories(binja_printk PUBLIC ${BNAPI_DIR})
target_link_libraries(binja_printk binaryninjaapi)

set_target_properties(binja_printk PROPERTIES
	CXX_STANDARD 17
	CXX_VISIBILITY_PRESET hidden
	CXX_STANDARD_REQUIRED ON
	VISIBILITY_INLINES_HIDDEN ON
	POSITION_INDEPENDENT_CODE ON)
