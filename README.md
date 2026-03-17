## Assignment - Sorting Benchmark

This project is a C++ sorting benchmark with different implementations (serial, OpenMP, CUDA) and configurable input distributions.

### Prerequisites

- **CMake** (version 3.20 or newer)
- **C++ compiler** with C++20 support (e.g. `g++` 11+ or `clang++` 13+)
- (Optional) **OpenMP** support for the `omp` implementation
- (Optional) **CUDA toolkit** for the `cuda` implementation

All commands below are assumed to be run on Linux in a terminal.

### Build Instructions

1. **Clone or open the repository**

```bash
cd /media/D/Eduaction/College/HPC/Assinment
```

2. **Create a build directory**

```bash
mkdir -p build
cd build
```

3. **Configure the project with CMake**

```bash
cmake ..
```

4. **Compile the project**

```bash
cmake --build .
```

This will produce an executable named `Assinment` in the `build` directory.

### Run Instructions

From inside the `build` directory:

```bash
./Assinment [options]
```

#### Supported options

- `--help`, `-h`  
  Show help (to be implemented in code).

- `--impl <name>`  
  Select implementation. Expected values:
  - `serial`
  - `omp` (requires OpenMP)
  - `cuda` (requires CUDA)

- `--threads <n>`  
  Number of threads (only valid with `--impl omp`).

- `--block_size <n>`  
  CUDA block size (only valid with `--impl cuda`).

- `--grid_size <n>`  
  CUDA grid size (only valid with `--impl cuda`).

- `--repeats <n>`  
  Number of repeats for averaging (must be positive).

- `--size <n>`  
  Size of the generated array.

- `--seed <n>`  
  Seed for the random distribution.

- `--distribution <name>`  
  Distribution of the generated array. Expected values include:
  - `uniform`
  - `gaussian`
  - `nearly_sorted`
  - `reversed`

- `--output <path>`  
  Output path for CSV/plots (as implemented in the code).

### Example Commands

From `build`:

```bash
# Simple serial run with 1M elements
./Assinment --impl serial --size 1000000 --seed 42 --distribution uniform

# OpenMP run with 8 threads
./Assinment --impl omp --threads 8 --size 1000000 --seed 42 --distribution uniform

# CUDA run with custom grid/block
./Assinment --impl cuda --block_size 256 --grid_size 64 --size 1000000 --seed 42 --distribution uniform
```

### Notes

- The exact behavior (sorting algorithm, output format, etc.) is defined in the source files under `src/` and `src/utils/`.
- If CMake or the compiler cannot find CUDA or OpenMP, you can still build and use the `serial` implementation.

