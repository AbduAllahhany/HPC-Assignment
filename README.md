# HPC Assignment — Sorting Benchmarks (Serial / OpenMP / CUDA)

C++20 sorting implementations with:

- **Serial merge sort** (`serial`)
- **Serial bitonic sort** (`serial_bitonic`)
- **OpenMP merge sort** (`omp`)
- **CUDA bitonic sort** (`cuda`, only when CUDA toolkit is found at configure time)

The repository also includes a repeatable experiment runner that writes CSV results, generates speedup plots (optional), and emits short Markdown performance summaries under `report/`.

## Build

### Prerequisites

- **CMake** \(\>= 3.20\)
- **C++ compiler** with C++20 support
- **OpenMP** (required)
- **CUDA toolkit** (optional; enables the CUDA bitonic implementation if found)

### Build command

```bash
./build.sh
```

Outputs are placed in `build/`.

### Produced executables

- `build/Assingment`: main benchmark CLI (note the spelling)
- `build/sort_correctness_test`: correctness test binary (also runnable via CTest)

## Run a single benchmark (CLI)

The main binary prints one line including `avg_ms=...`, which is what the scripts parse.

### Usage

```bash
./build/Assingment --size N --seed S --distribution D \
  [--impl {serial,serial_bitonic,omp,cuda}] \
  [--threads T] \
  [--block_size B] \
  [--grid_size G] \
  [--repeats R]
```

### Examples

Serial merge sort:

```bash
./build/Assingment --impl serial --size 1048576 --seed 42 --distribution uniform --repeats 3
```

OpenMP merge sort:

```bash
./build/Assingment --impl omp --threads 8 --size 1048576 --seed 42 --distribution gaussian --repeats 3
```

CUDA bitonic sort (only if CUDA was enabled at build time):

```bash
./build/Assingment --impl cuda --block_size 512 --size 1048576 --seed 42 --distribution uniform --repeats 3
```

## Correctness tests

### Run via CTest

```bash
cd build
ctest --output-on-failure
```

### Run directly

```bash
./build/sort_correctness_test
```

Notes:

- If CUDA is not available (built without CUDA, no GPU, or runtime errors), CUDA tests are **skipped** while CPU paths are still validated.

## Run the full experiment matrix

The experiment runner builds (if needed), runs multiple trials across sizes/distributions/threads (and CUDA block sizes if CUDA is enabled), then aggregates results and generates plots/reports.

```bash
./scripts/run_experiments.sh
```

### Common options

```bash
./scripts/run_experiments.sh \
  --trials 5 \
  --seed 42 \
  --run-id my_run \
  --sizes "1000000,1048576,2097152,4194304" \
  --dists "uniform,gaussian,nearly_sorted,reversed" \
  --omp-threads "2,4,8,16" \
  --cuda-blocks "128,256,512,1024"
```

### Outputs

For a run id `<run_id>`, results are written under:

- `experiments/<run_id>/raw_trials.csv`: all raw timings (one row per trial)
- `experiments/<run_id>/summary.csv`: aggregated means/stdevs + speedup columns
- `experiments/<run_id>/plots/`: PNG plots (if matplotlib is available)
- `experiments/<run_id>/system_info.txt`: system + build info snapshot
- `experiments/<run_id>/commands_executed.txt`: the exact commands run
- `experiments/<run_id>/merge_omp/`: subset analysis for merge serial vs OpenMP
- `experiments/<run_id>/bitonic/`: subset analysis for bitonic/cuda vs merge-serial

The analysis script also writes short Markdown highlights into `report/`:

- `report/performance_analysis.md`
- `report/performance_analysis_merge_omp.md`
- `report/performance_analysis_bitonic.md`

## Python plotting (optional)

Plots are generated only if `matplotlib` is importable.

- `requirements.txt` contains:
  - `matplotlib>=3.8`

If `matplotlib` is missing, the runner still writes CSVs and reports; PNGs may be absent.

## Project layout

- `src/`: implementations (serial, OpenMP, CUDA/stub) + utilities
- `tests/`: correctness test (`sort_correctness_test.cpp`)
- `scripts/`: experiment runner + CSV/plot/report generator
- `report/`: generated Markdown summaries
- `experiments/`: generated run artifacts (CSV/plots/system info)

