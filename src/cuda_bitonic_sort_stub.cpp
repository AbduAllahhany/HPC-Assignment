#include "cuda_bitonic_sort.h"

#include <stdexcept>

void cudaBitonicSort(std::vector<int32_t> &arr, int threadsPerBlock) {
    (void) arr;
    (void) threadsPerBlock;
    throw std::runtime_error(
        "CUDA is not available (CUDAToolkit not found at configure time). "
        "Install CUDA toolkit and reconfigure CMake to build GPU bitonic sort.");
}
