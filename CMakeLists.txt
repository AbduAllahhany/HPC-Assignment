cmake_minimum_required(VERSION 3.20)
project(Assingment LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)

include(CTest)

find_package(OpenMP REQUIRED)
find_package(CUDAToolkit QUIET)

# CMake does not always put CUDAToolkit_FOUND in CMakeCache.txt; this mirrors it for `grep` / scripts.
set(ASSIGNMENT_CUDA_ENABLED "${CUDAToolkit_FOUND}" CACHE BOOL "find_package(CUDAToolkit) succeeded" FORCE)

set(ASSIGNMENT_SOURCES
        src/main.cpp
        src/utils/array_gen.cpp
        src/serial_sort.cpp
        src/serial_bitonic_sort.cpp
        src/omp_sort.cpp
)

set(SORT_SOURCES
        src/utils/array_gen.cpp
        src/serial_sort.cpp
        src/serial_bitonic_sort.cpp
        src/omp_sort.cpp
)

if(CUDAToolkit_FOUND)
    enable_language(CUDA)
    set(CMAKE_CUDA_STANDARD 20)
    list(APPEND ASSIGNMENT_SOURCES src/cuda_bitonic_sort.cu)
    list(APPEND SORT_SOURCES src/cuda_bitonic_sort.cu)
else()
    list(APPEND ASSIGNMENT_SOURCES src/cuda_bitonic_sort_stub.cpp)
    list(APPEND SORT_SOURCES src/cuda_bitonic_sort_stub.cpp)
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

add_executable(sort_correctness_test
        tests/sort_correctness_test.cpp
        ${SORT_SOURCES}
)

target_include_directories(sort_correctness_test PRIVATE src/include)
target_link_libraries(sort_correctness_test PRIVATE OpenMP::OpenMP_CXX)

if(CUDAToolkit_FOUND)
    target_link_libraries(sort_correctness_test PRIVATE CUDA::cudart)
endif()

enable_testing()
add_test(NAME sort_correctness_test COMMAND sort_correctness_test)
