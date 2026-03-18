#include "include/omp_sort.h"

#include <algorithm>
#include "include/serial_sort.h"
#include <omp.h>
static const size_t TASK_CUTOFF = 1 << 12; // ~4096
static const size_t SORT_CUTOFF = 32;

void ompMergeSortHelper(std::vector<int32_t> &arr, std::vector<int32_t> &buf, size_t left, size_t right) {
    if (left >= right) return;

    if (right - left < SORT_CUTOFF) {
        std::sort(arr.begin() + left, arr.begin() + right + 1);
        return;
    }
    size_t mid = left + ((right - left) >> 1);

#pragma omp task default(none) shared(arr, buf) firstprivate(left, mid, right) if(right - left >= TASK_CUTOFF)
    ompMergeSortHelper(arr, buf, left, mid);
#pragma omp task default(none) shared(arr, buf) firstprivate(left, mid, right) if(right - left >= TASK_CUTOFF)
    ompMergeSortHelper(arr, buf, mid + 1, right);
#pragma omp taskwait

    merge(arr, buf, left, mid, right);
}


void ompMergeSort(std::vector<int32_t> &arr, int threads) {
    if (arr.empty()) return;
    omp_set_num_threads(threads);
    std::vector<int32_t> buf(arr.size());

#pragma omp parallel default(none) shared(arr, buf)
#pragma omp single nowait
    ompMergeSortHelper(arr, buf, 0, arr.size() - 1);
}
