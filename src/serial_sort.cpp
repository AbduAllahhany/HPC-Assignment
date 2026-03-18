//
// Created by abdallah-hany on 3/17/26.
//

#include "include/serial_sort.h"

#include <algorithm>


// using buffer to enhance cache locality  and don't allocate L and R vectors
void merge(std::vector<int32_t> &arr, std::vector<int32_t> &buf,
           size_t left, size_t mid, size_t right) {
    for (size_t i = left; i <= mid; i++)
        buf[i] = arr[i];

    size_t i = left, j = mid + 1, k = left;
    while (i <= mid && j <= right) {
        if (buf[i] <= arr[j]) arr[k++] = buf[i++];
        else arr[k++] = arr[j++];
    }
    while (i <= mid)
        arr[k++] = buf[i++];
}

void mergeSort(std::vector<int32_t> &arr, std::vector<int32_t> &buf, size_t left, size_t right) {
    if (left >= right)
        return;
    size_t mid = left + ((right - left) >> 1);
    mergeSort(arr, buf, left, mid);
    mergeSort(arr, buf, mid + 1, right);
    merge(arr, buf, left, mid, right);
}

void mergeSort(std::vector<int32_t> &arr) {
    std::vector<int32_t> buf(arr.size());
    mergeSort(arr, buf, 0, arr.size() - 1);
}
