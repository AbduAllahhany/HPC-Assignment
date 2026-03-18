## Assignment - Sorting Benchmark

This project is a C++ sorting benchmark with different implementations (serial, OpenMP, CUDA) and configurable input distributions.

### Prerequisites

- **CMake** (version 3.20 or newer)
- **C++ compiler** with C++20 support (e.g. `g++` 11+ or `clang++` 13+)
- **OpenMP** (`libomp-dev`) — required for the `omp` implementation
- **CUDA toolkit** for the `cuda` implementation

All commands below are assumed to be run on Linux in a terminal.

### Quick Start (install deps + build)

```bash
chmod +x install.sh
./install.sh
```

This will install `libomp-dev`, `cmake`, and `build-essential`, then build the project. The binary will be at `build/Assignment`.

### Run Instructions

From inside the `build` directory:

```bash
./Assignment [options]
```

#### Supported options

| Flag | Value | Description |
|---|---|---|
| `--help`, `-h` | — | Show help |
| `--impl` | `serial` \| `omp` \| `cuda` | Select implementation |
| `--threads` | `<n>` | Number of threads (only with `--impl omp`) |
| `--block_size` | `<n>` | CUDA block size (only with `--impl cuda`) |
| `--grid_size` | `<n>` | CUDA grid size (only with `--impl cuda`) |
| `--size` | `<n>` | Array length |
| `--seed` | `<n>` | RNG seed for reproducibility |
| `--distribution` | `uniform` \| `gaussian` \| `nearly_sorted` \| `reversed` | Input distribution |
| `--repeats` | `<n>` | Number of timed runs to average (default: 1) |
| `--output` | `<path>` | Output path for CSV/plots |

### Example Commands

From `build`:

```bash
# Serial — 1M elements, uniform distribution
./Assignment --impl serial --size 1000000 --seed 42 --distribution uniform

# OpenMP — 4M elements, 8 threads, averaged over 5 runs
./Assignment --impl omp --threads 8 --size 4194304 --seed 42 --distribution uniform --repeats 5

# Nearly-sorted input with 4 threads
./Assignment --impl omp --threads 4 --size 1048576 --seed 7 --distribution nearly_sorted

# Reversed input, serial baseline
./Assignment --impl serial --size 2097152 --seed 1 --distribution reversed --repeats 3
```

Output format:
```
impl=omp size=4194304 dist=uniform threads=8 avg_ms=38.42
```

### Notes

- The exact behavior (sorting algorithm, output format, etc.) is defined in the source files under src/ and src/utils/.
- If CMake or the compiler cannot find CUDA or OpenMP, you can still build and use the serial implementation.



