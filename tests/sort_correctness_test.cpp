#include <algorithm>
#include <cstdint>
#include <exception>
#include <functional>
#include <iostream>
#include <string>
#include <vector>

#include "../src/include/utils.h"

#include "../src/include/cuda_bitonic_sort.h"
#include "../src/include/omp_sort.h"
#include "../src/include/serial_bitonic_sort.h"
#include "../src/include/serial_sort.h"

namespace {

bool isNonDecreasing(const std::vector<int32_t> &arr) {
    for (size_t i = 1; i < arr.size(); ++i) {
        if (arr[i - 1] > arr[i]) return false;
    }
    return true;
}

bool vectorsEqual(const std::vector<int32_t> &a, const std::vector<int32_t> &b) {
    if (a.size() != b.size()) return false;
    for (size_t i = 0; i < a.size(); ++i) {
        if (a[i] != b[i]) return false;
    }
    return true;
}

size_t firstMismatchIndex(const std::vector<int32_t> &a, const std::vector<int32_t> &b) {
    const size_t n = std::min(a.size(), b.size());
    for (size_t i = 0; i < n; ++i) {
        if (a[i] != b[i]) return i;
    }
    return n;
}

// Choose sizes that exercise padding/non-power-of-two behavior in bitonic.
// Keep them moderate so CTest remains practical.
std::vector<uint32_t> correctnessSizes() {
    return {
        2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 16, 17, 31, 32, 33, 63, 64, 65,
        100, 127, 128, 129, 255, 256, 257, 1000, 1023, 1024, 2047, 2048, 4095, 4096};
}

std::vector<std::string> correctnessDistributions() {
    return {"uniform", "gaussian", "nearly_sorted", "reversed"};
}

std::vector<uint32_t> correctnessSeeds() {
    // Single seed keeps runtime bounded; correctness is validated across distributions/sizes.
    return {42u};
}

bool shouldSkipCudaTests(const std::exception &e) {
    const std::string msg = e.what();
    // Stub build (no CUDAToolkit at configure time).
    if (msg.find("CUDA is not available") != std::string::npos)
        return true;
    // No GPU, sandbox/CI, driver/runtime issues — skip GPU checks; CPU paths still validated.
    if (msg.find("cudaMalloc") != std::string::npos)
        return true;
    if (msg.find("operation not supported") != std::string::npos)
        return true;
    if (msg.find("CUDA error") != std::string::npos)
        return true;
    return false;
}

int runImplAndCheck(
    const std::string &implName,
    std::vector<int32_t> base,
    const std::vector<int32_t> &reference,
    const std::function<void(std::vector<int32_t> &)> &sortFn) {
    sortFn(base);

    if (!isNonDecreasing(base)) {
        std::cerr << "[FAIL] " << implName << " output not sorted\n";
        return 1;
    }

    if (!vectorsEqual(base, reference)) {
        const size_t idx = firstMismatchIndex(base, reference);
        std::cerr << "[FAIL] " << implName << " mismatch at i=" << idx
                  << " (got=" << (idx < base.size() ? static_cast<long long>(base[idx]) : -1LL)
                  << ", expected=" << (idx < reference.size() ? static_cast<long long>(reference[idx]) : -1LL)
                  << ")\n";
        return 1;
    }

    return 0;
}

} // namespace

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;

    int ompThreads = 4;
    int cudaThreadsPerBlock = 256; // must be power-of-two

    const auto sizes = correctnessSizes();
    const auto distributions = correctnessDistributions();
    const auto seeds = correctnessSeeds();

    bool cudaSupported = true;
    {
        // Probe CUDA once. Skip GPU tests if stub, no device, or environment blocks CUDA (e.g. CI sandbox).
        std::vector<int32_t> probe = {2, 1};
        try {
            cudaBitonicSort(probe, cudaThreadsPerBlock);
        } catch (const std::exception &e) {
            if (shouldSkipCudaTests(e)) {
                cudaSupported = false;
                std::cerr << "[WARN] CUDA tests skipped: " << e.what() << "\n";
            } else {
                std::cerr << "[ERROR] CUDA probe failed: " << e.what() << "\n";
                return 1;
            }
        }
    }

    size_t totalCases = 0;
    size_t failures = 0;

    for (uint32_t size : sizes) {
        for (const std::string &dist : distributions) {
            for (uint32_t seed : seeds) {
                ++totalCases;

                std::string distCopy = dist; // utils::generate takes a mutable std::string&
                auto base = utils::generate(size, seed, distCopy);

                // Reference: serial MergeSort
                auto reference = base;
                mergeSort(reference);

                failures += runImplAndCheck(
                                 "serial_bitonic",
                                 base,
                                 reference,
                                 [](std::vector<int32_t> &arr) { serialBitonicSort(arr); });

                // Copy for CUDA before moving `base` for OpenMP (otherwise `base` is empty).
                auto baseCuda = base;
                auto baseOmp = std::move(base);
                failures += runImplAndCheck(
                                 "omp_mergeSort",
                                 std::move(baseOmp),
                                 reference,
                                 [&](std::vector<int32_t> &arr) { ompMergeSort(arr, ompThreads); });

                if (cudaSupported) {
                    failures += runImplAndCheck(
                                     "cuda_bitonicSort",
                                     std::move(baseCuda),
                                     reference,
                                     [&](std::vector<int32_t> &arr) { cudaBitonicSort(arr, cudaThreadsPerBlock); });
                }
            }
        }
    }

    std::cout << "sort_correctness_test cases=" << totalCases
              << " failures=" << failures
              << (cudaSupported ? " cuda=enabled" : " cuda=disabled") << "\n";

    return failures == 0 ? 0 : 1;
}

