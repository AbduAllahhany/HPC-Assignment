cmake_minimum_required(VERSION 3.20)
project(Assingment LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)

find_package(OpenMP REQUIRED)
find_package(CUDAToolkit QUIET)

set(ASSIGNMENT_SOURCES
        src/main.cpp
        src/utils/array_gen.cpp
        src/serial_sort.cpp
        src/serial_bitonic_sort.cpp
        src/omp_sort.cpp
)

if(CUDAToolkit_FOUND)
    enable_language(CUDA)
    set(CMAKE_CUDA_STANDARD 20)
    list(APPEND ASSIGNMENT_SOURCES src/cuda_bitonic_sort.cu)
else()
    list(APPEND ASSIGNMENT_SOURCES src/cuda_bitonic_sort_stub.cpp)
endif()

add_executable(Assingment ${ASSIGNMENT_SOURCES}
        src/include/utils.h
        src/include/serial_bitonic_sort.h
        src/include/cuda_bitonic_sort.h
)

target_include_directories(Assingment PRIVATE src/include)
target_link_libraries(Assingment PRIVATE OpenMP::OpenMP_CXX)

if(CUDAToolkit_FOUND)
    target_link_libraries(Assingment PRIVATE CUDA::cudart)
endif()
