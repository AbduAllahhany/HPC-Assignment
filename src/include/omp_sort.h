#ifndef ASSINMENT_OMP_SORT_H
#define ASSINMENT_OMP_SORT_H

#include <vector>
#include <cstdint>

void ompMergeSort(std::vector<int32_t> &arr, int threads);
void ompMergeSortHelper(std::vector<int32_t> &arr, size_t left, size_t right);

#endif //ASSINMENT_OMP_SORT_H
