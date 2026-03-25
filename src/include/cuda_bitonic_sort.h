#ifndef ASSINMENT_CUDA_BITONIC_SORT_H
#define ASSINMENT_CUDA_BITONIC_SORT_H

#include <cstdint>
#include <vector>

void cudaBitonicSort(std::vector<int32_t> &arr, int threadsPerBlock = 512);

#endif // ASSINMENT_CUDA_BITONIC_SORT_H
