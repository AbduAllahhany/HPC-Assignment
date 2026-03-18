#ifndef ASSINMENT_SERIAL_SORT_H
#define ASSINMENT_SERIAL_SORT_H

#include <vector>
#include <cstdint>

void mergeSort(std::vector<int32_t> &arr);

void merge(std::vector<int32_t> &arr, std::vector<int32_t> &buf,
           size_t left, size_t mid, size_t right);
#endif //ASSINMENT_SERIAL_SORT_H
