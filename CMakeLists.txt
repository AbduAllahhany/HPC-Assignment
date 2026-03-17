cmake_minimum_required(VERSION 3.20)
project(Assinment)

set(CMAKE_CXX_STANDARD 20)

add_executable(Assinment
        src/main.cpp
        src/utils/array_gen.cpp
        src/serial_sort.cpp
        src/include/utils.h
)

target_include_directories(Assinment PRIVATE src/include)