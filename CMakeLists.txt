cmake_minimum_required(VERSION 3.9 FATAL_ERROR)

project(binja_printk)

if(NOT BNAPI_DIR)
	set(BNAPI_DIR "vendor/api"
		CACHE PATH "binaryninja-api root dir")
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
