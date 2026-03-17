#ifndef ASSINMENT_UTILS_H
#define ASSINMENT_UTILS_H
#include <cstdint>
#include <string>
#include <vector>

namespace utils {
    std::vector<int32_t> generate(uint32_t size, uint32_t seed, std::string &distribution);
}

#endif //ASSINMENT_UTILS_H
