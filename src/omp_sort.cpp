#include "include/omp_sort.h"
#include "include/serial_sort.h"
#include <omp.h>


void ompMergeSortHelper(std::vector<int32_t> &arr, size_t left, size_t right) {
    if (left >= right) return;
    size_t mid = left + (right - left) / 2;
    #pragma omp task shared(arr)
    ompMergeSortHelper(arr, left, mid);
    #pragma omp task shared(arr)
    ompMergeSortHelper(arr, mid + 1, right);

    // wait for all child tasks
    #pragma omp taskwait
    merge(arr, left, mid, right);
}

void ompMergeSort(std::vector<int32_t> &arr, int threads) {
    if (arr.empty()) return;
    omp_set_num_threads(threads);
    #pragma omp parallel
    {
        #pragma omp single
        ompMergeSortHelper(arr, 0, arr.size() - 1);
    }
}
