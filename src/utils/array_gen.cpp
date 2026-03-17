#include <algorithm>
#include <cmath>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

std::vector<int32_t> generate(uint32_t size, uint32_t seed, std::string &distribution) {
    if (size == 0)
        throw std::invalid_argument("Size must be greater than 0");

    std::transform(distribution.begin(), distribution.end(), distribution.begin(), ::tolower);
    std::vector<int32_t> result(size);
    std::mt19937 generator(seed);

    const int32_t range_from = INT32_MIN;
    const int32_t range_to = INT32_MAX;
    const uint64_t urange = (uint64_t) range_to - (uint64_t) range_from;

    if (distribution == "uniform") {
        std::uniform_int_distribution<int32_t> distr(range_from, range_to);
        for (size_t i = 0; i < size; ++i)
            result[i] = distr(generator);
    } else if (distribution == "gaussian" || distribution == "normal") {
        std::normal_distribution<double> distr(0.0, range_to / 4.0);
        for (size_t i = 0; i < size; ++i) {
            double val = distr(generator);
            if (val < (double) range_from) val = (double) range_from;
            if (val > (double) range_to) val = (double) range_to;
            result[i] = (int32_t) val;
        }
    } else if (distribution == "nearly_sorted") {
        for (size_t i = 0; i < size; ++i)
            result[i] = (int32_t) ((uint64_t) range_from + (uint64_t) i * urange / (size - 1));
        std::sort(result.begin(), result.end());

        const uint32_t num_swaps = std::max(1u, (uint32_t) std::sqrt((double) size));
        std::uniform_int_distribution<uint32_t> idx_distr(0, size - 1);
        for (uint32_t s = 0; s < num_swaps; ++s)
            std::swap(result[idx_distr(generator)], result[idx_distr(generator)]);
    } else if (distribution == "nearly_sorted_k") {
        for (size_t i = 0; i < size; ++i)
            result[i] = (int32_t) ((uint64_t) range_from + (uint64_t) i * urange / (size - 1));
        std::sort(result.begin(), result.end());

        const uint32_t k_max = std::max(3u, size / 5u);
        std::uniform_int_distribution<uint32_t> k_distr(2, k_max);
        const uint32_t k = k_distr(generator);

        const uint32_t swaps_per_window = 1;
        for (size_t i = 0; i + k <= size; i += k) {
            std::uniform_int_distribution<uint32_t> win_distr(
                (uint32_t) i, (uint32_t) (i + k - 1));
            for (uint32_t s = 0; s < swaps_per_window; ++s)
                std::swap(result[win_distr(generator)], result[win_distr(generator)]);
        }
    }
    if (distribution == "reversed") {
        for (size_t i = 0; i < size; ++i)
            result[i] = (int32_t) ((uint64_t) range_from + (uint64_t) i * urange / (size - 1));
        std::sort(result.rbegin(), result.rend());
    } else {
        throw std::invalid_argument("Unknown distribution: " + distribution);
    }

    return result;
}

template<typename T>
T random(T range_from, T range_to, uint32_t seed) {
    std::mt19937 generator(seed);
    std::uniform_int_distribution<T> distr(range_from, range_to);
    return distr(generator);
}
