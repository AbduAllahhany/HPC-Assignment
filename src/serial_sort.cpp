//
// Created by abdallah-hany on 3/17/26.
//

#include "include/serial_sort.h"


void merge(std::vector<int32_t> &arr, size_t left,
           size_t mid, size_t right) {
    size_t n1 = mid - left + 1;
    size_t n2 = right - mid;

    std::vector<int32_t> L(n1), R(n2);

    // Copy data to temp vectors L[] and R[]
    for (size_t i = 0; i < n1; i++)
        L[i] = arr[left + i];
    for (size_t j = 0; j < n2; j++)
        R[j] = arr[mid + 1 + j];

    size_t i = 0, j = 0;
    size_t k = left;


    while (i < n1 && j < n2) {
        if (L[i] <= R[j]) {
            arr[k] = L[i];
            i++;
        } else {
            arr[k] = R[j];
            j++;
        }
        k++;
    }

    // Copy the remaining elements of L[],
    // if there are any
    while (i < n1) {
        arr[k] = L[i];
        i++;
        k++;
    }

    // Copy the remaining elements of R[],
    // if there are any
    while (j < n2) {
        arr[k] = R[j];
        j++;
        k++;
    }
}

void mergeSort(std::vector<int32_t> &arr, size_t left, size_t right) {
    if (left >= right)
        return;
    size_t mid = left + (right - left) / 2;
    mergeSort(arr, left, mid);
    mergeSort(arr, mid + 1, right);
    merge(arr, left, mid, right);
}

void mergeSort(std::vector<int32_t> &arr) {
    mergeSort(arr, 0, arr.size());
}
