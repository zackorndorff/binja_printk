cmake_minimum_required(VERSION 3.12 FATAL_ERROR)

project(binja_printk)

if(NOT BNAPI_DIR)
	set(BNAPI_DIR "vendor/api"
		CACHE PATH "binaryninja-api root dir")
endif()

# Build fat Mach-O for macOS
if(NOT CMAKE_OSX_ARCHITECTURES)
	set(CMAKE_OSX_ARCHITECTURES "x86_64;arm64")
endif()

# Reasonable MSVC flags
if(MSVC)
	set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} /Zi /Gy /DNDEBUG /O2")
	set(CMAKE_SHARED_LINKER_FLAGS_RELEASE "${CMAKE_SHARED_LINKER_FLAGS_RELEASE} /DEBUG /OPT:REF /OPT:ICF")
endif()

# Set headless to avoid trying to link against the UI library
set(HEADLESS ON CACHE BOOL "")

# We don't have the binaryninjacore library in CI (that's the paid product!), so
# make a fake one so we can link against it
# This does have some issues, involving SONAMEs, dependency versions, etc.
# However, BN has its own versioning system, so hopefully that'll catch any
# issues.
# Of course, our header parser could also fail to find all the symbols... it's
# not very advanced. But it seems to work.
option(FAKE_BN_CORE "Should build fake BN core for linking" OFF)
if(FAKE_BN_CORE)
	# Figure out what to call it
	# I'm sure there's a CMake command to do this, but I couldn't find it in
	# 10 minutes of looking
	if(UNIX)
		if(APPLE)
			set(BN_CORE_NAME "libbinaryninjacore.dylib")
			set(GEN_PLATFORM "macos")
		else()
			# If SONAME changes, this will need a change
			set(BN_CORE_NAME "libbinaryninjacore.so.1")
			set(GEN_PLATFORM "linux")
		endif()
	endif()
	if(MSVC)
		set(BN_CORE_NAME "binaryninjacore.dll")
		set(GEN_PLATFORM "windows")

		# Find lib.exe
		get_filename_component(my_vs_bin_path "${CMAKE_LINKER}" DIRECTORY)
		set(CMAKE_MSVCIDE_RUN_PATH ${CMAKE_MSVCIDE_RUN_PATH};${my_vs_bin_path})
	endif()

	# Gives us the Python3_EXECUTABLE variable
	find_package(Python3 COMPONENTS Interpreter)

	# I hacked together something like this until it worked
	# https://stackoverflow.com/a/60073596
	# PRs welcome to tidy this up
	add_custom_command(
		OUTPUT ${BN_CORE_NAME}
		COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/gen_lib.py -i ${BNAPI_DIR}/binaryninjacore.h -o ${CMAKE_CURRENT_BINARY_DIR}/${BN_CORE_NAME} -p ${GEN_PLATFORM}
		DEPENDS ${BNAPI_DIR}/binaryninjacore.h
		WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
		VERBATIM)
	add_custom_target(FAKEBNCORE_TARGET DEPENDS ${BN_CORE_NAME})
	add_library(FAKEBNCORE STATIC IMPORTED GLOBAL)
	add_dependencies(FAKEBNCORE FAKEBNCORE_TARGET)
	set_target_properties(FAKEBNCORE
	    PROPERTIES
	    IMPORTED_LOCATION ${BN_CORE_NAME})

	# Tell the API repo about it... I thought this had to be a filename but
	# apparently not
	set(BN_CORE_LIBRARY FAKEBNCORE)
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
