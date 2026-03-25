#include "cuda_bitonic_sort.h"

#include <climits>
#include <cuda_runtime.h>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

size_t nextPowerOfTwo(size_t n) {
    size_t p = 1;
    while (p < n) p <<= 1;
    return p;
}

int floorLog2(size_t n) {
    int k = 0;
    while (n > 1) {
        n >>= 1;
        ++k;
    }
    return k;
}

__global__ void bitonicSortGlobal(int32_t *d_arr, int n, int stage, int pass) {
    unsigned int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n / 2) return;

    unsigned int pairDistance = 1U << (pass - 1);
    unsigned int blockSize = 1U << stage;

    unsigned int leftIdx = (i / pairDistance) * (2 * pairDistance) + (i % pairDistance);
    unsigned int rightIdx = leftIdx + pairDistance;

    if (rightIdx >= static_cast<unsigned int>(n)) return;

    bool ascending = ((leftIdx / blockSize) % 2 == 0);

    int32_t a = d_arr[leftIdx];
    int32_t b = d_arr[rightIdx];

    if ((ascending && a > b) || (!ascending && a < b)) {
        d_arr[leftIdx] = b;
        d_arr[rightIdx] = a;
    }
}

__global__ void bitonicSortShared(int32_t *d_arr, int n, int stage) {
    extern __shared__ int32_t sdata[];

    unsigned int tid = threadIdx.x;
    unsigned int i = blockIdx.x * blockDim.x * 2 + tid;

    sdata[tid] = (i < static_cast<unsigned int>(n)) ? d_arr[i] : INT32_MAX;
    sdata[tid + blockDim.x] =
        (i + blockDim.x < static_cast<unsigned int>(n)) ? d_arr[i + blockDim.x] : INT32_MAX;
    __syncthreads();

    unsigned int blockSize = 1U << stage;

    for (int pass = stage; pass >= 1; --pass) {
        unsigned int pairDistance = 1U << (pass - 1);

        for (int offset = 0; offset < 2; ++offset) {
            unsigned int localIdx = tid + static_cast<unsigned int>(offset) * blockDim.x;
            unsigned int globalIdx = blockIdx.x * blockDim.x * 2 + localIdx;

            unsigned int ixj = localIdx ^ pairDistance;
            if (ixj > localIdx && ixj < blockDim.x * 2) {
                bool ascending = ((globalIdx / blockSize) % 2 == 0);
                int32_t a = sdata[localIdx];
                int32_t b = sdata[ixj];
                if ((ascending && a > b) || (!ascending && a < b)) {
                    sdata[localIdx] = b;
                    sdata[ixj] = a;
                }
            }
        }
        __syncthreads();
    }

    if (i < static_cast<unsigned int>(n)) d_arr[i] = sdata[tid];
    if (i + blockDim.x < static_cast<unsigned int>(n)) d_arr[i + blockDim.x] = sdata[tid + blockDim.x];
}

void checkCuda(cudaError_t err, const char *what) {
    if (err != cudaSuccess)
        throw std::runtime_error(std::string(what) + ": " + cudaGetErrorString(err));
}

} // namespace

void cudaBitonicSort(std::vector<int32_t> &arr, int threadsPerBlock) {
    if (arr.empty()) return;
    if (threadsPerBlock <= 0 || (threadsPerBlock & (threadsPerBlock - 1)) != 0)
        throw std::invalid_argument("threadsPerBlock must be a positive power of 2");

    const size_t originalSize = arr.size();
    const size_t n = nextPowerOfTwo(originalSize);
    arr.resize(n, std::numeric_limits<int32_t>::max());

    int32_t *d_arr = nullptr;
    checkCuda(cudaMalloc(&d_arr, n * sizeof(int32_t)), "cudaMalloc");
    checkCuda(cudaMemcpy(d_arr, arr.data(), n * sizeof(int32_t), cudaMemcpyHostToDevice), "cudaMemcpy H2D");

    const int stages = static_cast<int>(floorLog2(n));
    const int globalBlocks = static_cast<int>((n / 2 + static_cast<size_t>(threadsPerBlock) - 1) /
                                            static_cast<size_t>(threadsPerBlock));
    const int sharedBlocks = globalBlocks;
    const size_t sharedMem = static_cast<size_t>(threadsPerBlock) * 2 * sizeof(int32_t);

    const int sharedPassCutoff = floorLog2(static_cast<size_t>(threadsPerBlock) * 2);

    for (int stage = 1; stage <= stages; ++stage) {
        for (int pass = stage; pass > sharedPassCutoff; --pass) {
            bitonicSortGlobal<<<globalBlocks, threadsPerBlock>>>(d_arr, static_cast<int>(n), stage, pass);
            checkCuda(cudaGetLastError(), "bitonicSortGlobal launch");
        }
        bitonicSortShared<<<sharedBlocks, threadsPerBlock, sharedMem>>>(d_arr, static_cast<int>(n), stage);
        checkCuda(cudaGetLastError(), "bitonicSortShared launch");
    }

    checkCuda(cudaDeviceSynchronize(), "cudaDeviceSynchronize");
    checkCuda(cudaMemcpy(arr.data(), d_arr, n * sizeof(int32_t), cudaMemcpyDeviceToHost), "cudaMemcpy D2H");
    cudaFree(d_arr);

    arr.resize(originalSize);
}
