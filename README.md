# HPC Assignment — Sorting Benchmarks (Serial / OpenMP / CUDA)

C++20 sorting implementations with:

- **Serial merge sort** (`serial`)
- **Serial bitonic sort** (`serial_bitonic`)
- **OpenMP merge sort** (`omp`)
- **CUDA bitonic sort** (`cuda`, only when CUDA toolkit is found at configure time)

The repository also includes a repeatable experiment runner that writes CSV results, generates speedup plots (optional), and writes a **`report.md` inside each experiment output folder** (full matrix, `merge_omp/`, and `bitonic/`). Optional highlights can also be written under `report/` if you enable that path in the analysis step.

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

The experiment runner builds (if needed), runs multiple trials across sizes/distributions/threads (and CUDA block sizes if CUDA is enabled), then aggregates results, writes **`report.md`** under each output directory, and generates plots when matplotlib is available.

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
- `experiments/<run_id>/report.md`: **auto-generated** summary (fastest config per size/distribution, win counts, notes)
- `experiments/<run_id>/plots/`: PNG plots (if matplotlib is available), including `plots/timing_comparison/timing_<distribution>_bars.png` (grouped mean-time bars per implementation, log scale)
- `experiments/<run_id>/system_info.txt`: system + build info snapshot
- `experiments/<run_id>/commands_executed.txt`: the exact commands run
- `experiments/<run_id>/merge_omp/`: subset CSVs, plots, and **`merge_omp/report.md`** (serial merge vs OpenMP only)
- `experiments/<run_id>/bitonic/`: subset CSVs, plots, and **`bitonic/report.md`** (merge vs serial bitonic vs CUDA)

The analysis script is `scripts/analyze_performance.py`. It **always** writes `report.md` into the directory passed as `--out_dir`. The experiment runner invokes it with `--no-report`, which **only** skips the optional project-level Markdown files under `report/`:

- `report/performance_analysis.md`
- `report/performance_analysis_merge_omp.md`
- `report/performance_analysis_bitonic.md`

To emit those as well, remove `--no-report` from the three `analyze_performance.py` invocations in `scripts/run_experiments.sh`, or run the analyzer manually without that flag.

## Python plotting (optional)

Plots are generated only if `matplotlib` is importable.

- `requirements.txt` contains:
  - `matplotlib>=3.8`

If `matplotlib` is missing, the runner still writes CSVs and `report.md` files; PNGs may be absent.

## Project layout

- `src/`: implementations (serial, OpenMP, CUDA/stub) + utilities
- `tests/`: correctness test (`sort_correctness_test.cpp`)
- `scripts/`: experiment runner + CSV/plot/report generator
- `report/`: optional generated Markdown summaries (only if analysis is run without `--no-report`)
- `experiments/`: generated run artifacts (CSV, plots, `report.md`, system info)

