#!/usr/bin/env bash
set -e

if command -v apt-get &>/dev/null; then
    sudo apt-get update -y
    sudo apt-get install -y libomp-dev cmake build-essential
elif command -v dnf &>/dev/null; then
    sudo dnf install -y libomp-devel cmake gcc-c++
elif command -v pacman &>/dev/null; then
    sudo pacman -Sy --noconfirm openmp cmake base-devel
else
    echo "Unsupported package manager. Install libomp-dev manually." >&2
    exit 1
fi

mkdir -p build
cd build
cmake ..
cmake --build . -j"$(nproc)"
echo "Build complete. Binary: build/Assignment"
