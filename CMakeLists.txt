cmake_minimum_required(VERSION 4.1)
project(Assinment)

set(CMAKE_CXX_STANDARD 20)

add_executable(Assinment src/main.cpp
        src/utils/array_gen.cpp
        src/serial_sort.cpp
        src/include/serial_sort.h
        src/include/serial_sort.h)
