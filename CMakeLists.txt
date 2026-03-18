cmake_minimum_required(VERSION 3.20)
project(Assingment)

set(CMAKE_CXX_STANDARD 20)

find_package(OpenMP REQUIRED)

add_executable(Assingment
        src/main.cpp
        src/utils/array_gen.cpp
        src/serial_sort.cpp
        src/omp_sort.cpp
        src/include/utils.h
)

target_include_directories(Assingment PRIVATE src/include)
target_link_libraries(Assingment PRIVATE OpenMP::OpenMP_CXX)
