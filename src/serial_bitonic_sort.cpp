#include "include/serial_bitonic_sort.h"

#include <algorithm>
#include <cstddef>
#include <limits>

namespace {
    size_t nextPowerOfTwo(size_t n) {
        size_t p = 1;
        while (p < n) p <<= 1;
        return p;
    }

    void compAndSwap(std::vector<int32_t> &arr, size_t i, size_t j, bool ascending) {
        if ((ascending && arr[i] > arr[j]) || (!ascending && arr[i] < arr[j])) {
            std::swap(arr[i], arr[j]);
        }
    }
}

void serialBitonicSort(std::vector<int32_t> &arr) {
    if (arr.empty()) return;

    const size_t originalSize = arr.size();
    const size_t paddedSize = nextPowerOfTwo(originalSize);
    arr.resize(paddedSize, std::numeric_limits<int32_t>::max());

    for (size_t len = 2; len <= paddedSize; len <<= 1) {
        for (size_t start = 0; start < paddedSize; start += len) {
            const bool ascending = ((start / len) % 2) == 0;

            for (size_t distance = len >> 1; distance > 0; distance >>= 1) {
                for (size_t i = start; i + distance < start + len; ++i) {
                    compAndSwap(arr, i, i + distance, ascending);
                }
            }
        }
    }

    arr.resize(originalSize);
}
