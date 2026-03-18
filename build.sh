#!/usr/bin/env bash

mkdir -p build
cd build
cmake ..
cmake --build . -j"$(nproc)"
echo "Build complete. Binary: build/Assignment"
