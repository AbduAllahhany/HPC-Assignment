#!/usr/bin/env bash
# Benchmarks (see scripts/analyze_performance.py for labels):
#   serial | serial_bitonic | omp | cuda (if built with CUDA)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

pick_python_bin() {
  local py="${ROOT_DIR}/.venv/bin/python3"
  if [[ -x "${py}" ]] && "${py}" -c "import sys" >/dev/null 2>&1; then
    echo "${py}"
    return 0
  fi
  [[ -d "${ROOT_DIR}/.venv" ]] && echo "[WARN] .venv unusable; use ./scripts/setup_python_env.sh" >&2
  echo "python3"
}

PYTHON_BIN="$(pick_python_bin)"

ensure_matplotlib() {
  "${PYTHON_BIN}" -c "import matplotlib" >/dev/null 2>&1 && return 0

  local req="${ROOT_DIR}/requirements.txt"
  local venv="${ROOT_DIR}/.venv"
  echo "[INFO] matplotlib missing; installing for plots..."

  if [[ -x "${venv}/bin/python3" ]] && "${venv}/bin/python3" -c "import sys" >/dev/null 2>&1; then
    if "${venv}/bin/pip" install -q -r "${req}" 2>/dev/null || "${venv}/bin/pip" install -q matplotlib 2>/dev/null; then
      PYTHON_BIN="${venv}/bin/python3"
      "${PYTHON_BIN}" -c "import matplotlib" >/dev/null 2>&1 && echo "[INFO] matplotlib OK in ${venv}" && return 0
    fi
  fi

  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
    if python3 -m pip install --user --break-system-packages -q matplotlib 2>/dev/null; then
      "${PYTHON_BIN}" -c "import matplotlib" >/dev/null 2>&1 &&
        echo "[INFO] matplotlib installed for system python3 (--user)." && return 0
    fi
  fi

  if [[ ! -d "${venv}" ]] && command -v python3 >/dev/null 2>&1 && python3 -m venv "${venv}" 2>/dev/null; then
    if "${venv}/bin/pip" install -q -r "${req}" 2>/dev/null || "${venv}/bin/pip" install -q matplotlib 2>/dev/null; then
      PYTHON_BIN="${venv}/bin/python3"
      "${PYTHON_BIN}" -c "import matplotlib" >/dev/null 2>&1 && echo "[INFO] Created ${venv} with matplotlib" && return 0
    fi
  fi

  echo "[WARN] matplotlib install failed. Try: sudo apt install python3-venv && ./scripts/setup_python_env.sh" >&2
  return 1
}

# Defaults (override with --sizes, --dists, --omp-threads, --cuda-blocks)
SIZES_CSV="1000000,1048576,2097152,4194304"
DISTS_CSV="uniform,gaussian,nearly_sorted,reversed"
OMP_THREADS_CSV="2,4,8,16"
CUDA_BLOCKS_CSV="128,256,512,1024"

TRIALS=5
SEED=42
RUN_ID=""

usage() {
  cat <<EOF
Usage: ./scripts/run_experiments.sh [options]

Options:
  --trials N           Trials per (size, dist) (default: ${TRIALS})
  --seed S             RNG seed (default: ${SEED})
  --run-id ID          Output folder under experiments/ (default: timestamp)
  --sizes CSV          Array sizes, comma-separated (default: ${SIZES_CSV})
  --dists CSV          Distributions, comma-separated (default: ${DISTS_CSV})
  --omp-threads CSV    OpenMP thread counts (default: ${OMP_THREADS_CSV})
  --cuda-blocks CSV    CUDA threads per block, comma-separated (default: ${CUDA_BLOCKS_CSV})
  -h, --help           Show this help

Output: experiments/<run_id>/raw_trials.csv, merge_omp/, bitonic/, summaries, plots, and report.md in each of those three directories (from analyze_performance.py).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --trials) TRIALS="${2}"; shift 2 ;;
    --seed) SEED="${2}"; shift 2 ;;
    --run-id) RUN_ID="${2}"; shift 2 ;;
    --sizes) SIZES_CSV="${2}"; shift 2 ;;
    --dists) DISTS_CSV="${2}"; shift 2 ;;
    --omp-threads) OMP_THREADS_CSV="${2}"; shift 2 ;;
    --cuda-blocks) CUDA_BLOCKS_CSV="${2}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

IFS=',' read -r -a SIZES <<< "${SIZES_CSV}"
IFS=',' read -r -a DISTS <<< "${DISTS_CSV}"
IFS=',' read -r -a OMP_THREADS_LIST <<< "${OMP_THREADS_CSV}"
IFS=',' read -r -a CUDA_BLOCK_SIZES <<< "${CUDA_BLOCKS_CSV}"
for __i in "${!SIZES[@]}"; do SIZES[__i]="${SIZES[__i]//[[:space:]]/}"; done
for __i in "${!DISTS[@]}"; do DISTS[__i]="${DISTS[__i]//[[:space:]]/}"; done
for __i in "${!OMP_THREADS_LIST[@]}"; do OMP_THREADS_LIST[__i]="${OMP_THREADS_LIST[__i]//[[:space:]]/}"; done
for __i in "${!CUDA_BLOCK_SIZES[@]}"; do CUDA_BLOCK_SIZES[__i]="${CUDA_BLOCK_SIZES[__i]//[[:space:]]/}"; done
unset __i

[[ -z "${RUN_ID}" ]] && RUN_ID="$(date +%Y%m%d_%H%M%S)"

OUT_DIR="${ROOT_DIR}/experiments/${RUN_ID}"
PLOTS_DIR="${OUT_DIR}/plots"
mkdir -p "${OUT_DIR}" "${PLOTS_DIR}"

raw_trials_csv="${OUT_DIR}/raw_trials.csv"
system_info_txt="${OUT_DIR}/system_info.txt"
commands_executed_txt="${OUT_DIR}/commands_executed.txt"

echo "run_id,trial,size,seed,dist,impl,threads,block_size,avg_ms" > "${raw_trials_csv}"
: > "${commands_executed_txt}"

echo "Run ID: ${RUN_ID}"

if [[ -x "${ROOT_DIR}/build/Assingment" ]]; then
  BIN="${ROOT_DIR}/build/Assingment"
elif [[ -x "${ROOT_DIR}/build/Assignment" ]]; then
  BIN="${ROOT_DIR}/build/Assignment"
else
  echo "Binary not found; running build.sh..."
  "${ROOT_DIR}/build.sh"
  if [[ -x "${ROOT_DIR}/build/Assingment" ]]; then
    BIN="${ROOT_DIR}/build/Assingment"
  elif [[ -x "${ROOT_DIR}/build/Assignment" ]]; then
    BIN="${ROOT_DIR}/build/Assignment"
  else
    echo "Could not find built binary after build.sh" >&2
    exit 1
  fi
fi

CUDA_AVAILABLE=0
if [[ -f "${ROOT_DIR}/build/CMakeCache.txt" ]]; then
  grep -qE "ASSIGNMENT_CUDA_ENABLED:BOOL=(ON|TRUE)" "${ROOT_DIR}/build/CMakeCache.txt" && CUDA_AVAILABLE=1
fi

{
  echo "run_id=${RUN_ID} timestamp=$(date -Is)"
  echo "uname: $(uname -a)"
  echo "nproc: $(nproc 2>/dev/null || echo '?')"
  command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L || echo "nvidia-smi: not found"
  echo "c++: $(c++ --version 2>/dev/null | head -1 || echo n/a)"
  echo "cmake: $(cmake --version 2>/dev/null | head -1 || echo n/a)"
  command -v nvcc >/dev/null 2>&1 && nvcc --version | head -1 || true
  echo "CUDA_available_by_cmake_cache=${CUDA_AVAILABLE}"
  if git -C "${ROOT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "git_HEAD=$(git -C "${ROOT_DIR}" rev-parse HEAD) dirty=$(git -C "${ROOT_DIR}" diff --quiet && echo false || echo true)"
  fi
  echo
  echo "matrix: TRIALS=${TRIALS} SEED=${SEED}"
  echo "SIZES=${SIZES[*]}"
  echo "DISTS=${DISTS[*]}"
  echo "OMP_THREADS=${OMP_THREADS_LIST[*]}"
  echo "CUDA_BLOCK_SIZES=${CUDA_BLOCK_SIZES[*]}"
  echo "binary=${BIN}"
} > "${system_info_txt}"

parse_avg_ms() {
  local line="$1" tok avg_ms=""
  for tok in ${line}; do
    [[ "${tok}" == avg_ms=* ]] && avg_ms="${tok#avg_ms=}"
  done
  if [[ -z "${avg_ms}" ]]; then
    echo "Failed to parse avg_ms from: ${line}" >&2
    return 1
  fi
  echo "${avg_ms}"
}

echo "Starting experiments..."
for size in "${SIZES[@]}"; do
  for dist in "${DISTS[@]}"; do
    for ((t = 1; t <= TRIALS; t++)); do
      run_serial() {
        local implName="$1"
        local cmd=("${BIN}" --impl "${implName}" --size "${size}" --seed "${SEED}" --distribution "${dist}" --repeats 1)
        echo "${cmd[*]}" >> "${commands_executed_txt}"
        local line avg_ms
        line="$("${cmd[@]}")"
        avg_ms="$(parse_avg_ms "${line}")" || exit 1
        echo "${RUN_ID},${t},${size},${SEED},${dist},${implName},1,0,${avg_ms}" >> "${raw_trials_csv}"
      }

      run_omp() {
        local th="$1"
        local cmd=("${BIN}" --impl omp --threads "${th}" --size "${size}" --seed "${SEED}" --distribution "${dist}" --repeats 1)
        echo "${cmd[*]}" >> "${commands_executed_txt}"
        local line avg_ms
        line="$("${cmd[@]}")"
        avg_ms="$(parse_avg_ms "${line}")" || exit 1
        echo "${RUN_ID},${t},${size},${SEED},${dist},omp,${th},0,${avg_ms}" >> "${raw_trials_csv}"
      }

      run_cuda() {
        local bs="$1"
        local cmd=("${BIN}" --impl cuda --block_size "${bs}" --size "${size}" --seed "${SEED}" --distribution "${dist}" --repeats 1)
        echo "${cmd[*]}" >> "${commands_executed_txt}"
        local line avg_ms
        line="$("${cmd[@]}")"
        avg_ms="$(parse_avg_ms "${line}")" || exit 1
        echo "${RUN_ID},${t},${size},${SEED},${dist},cuda,1,${bs},${avg_ms}" >> "${raw_trials_csv}"
      }

      run_serial "serial"
      run_serial "serial_bitonic"
      for th in "${OMP_THREADS_LIST[@]}"; do
        run_omp "${th}"
      done
      if [[ "${CUDA_AVAILABLE}" -eq 1 ]]; then
        for bs in "${CUDA_BLOCK_SIZES[@]}"; do
          run_cuda "${bs}"
        done
      fi
    done
  done
done

echo "Raw trials written to: ${raw_trials_csv}"

MERGE_OMP_DIR="${OUT_DIR}/merge_omp"
BITONIC_DIR="${OUT_DIR}/bitonic"
mkdir -p "${MERGE_OMP_DIR}/plots" "${BITONIC_DIR}/plots"
awk -F, 'NR==1 || ($6=="serial" || $6=="omp")' "${raw_trials_csv}" > "${MERGE_OMP_DIR}/raw_trials.csv"
awk -F, 'NR==1 || ($6=="serial" || $6=="serial_bitonic" || $6=="cuda")' "${raw_trials_csv}" > "${BITONIC_DIR}/raw_trials.csv"

echo "Aggregating + plotting..."
ensure_matplotlib || true
if "${PYTHON_BIN}" -c "import matplotlib" >/dev/null 2>&1; then
  echo "[INFO] Plots: ${PYTHON_BIN} (matplotlib OK)."
else
  echo "[WARN] matplotlib unavailable — CSVs/reports still written; PNGs may be missing."
fi
{
  echo "analysis_python=${PYTHON_BIN}"
  "${PYTHON_BIN}" -c "import matplotlib; print('matplotlib_version='+matplotlib.__version__)" 2>/dev/null || echo "matplotlib_version=not_available"
} >> "${system_info_txt}"

FULL_ANALYZE=("${PYTHON_BIN}" "${ROOT_DIR}/scripts/analyze_performance.py" --raw "${raw_trials_csv}" --out_dir "${OUT_DIR}" --plot_dir "${PLOTS_DIR}" --category full --seed "${SEED}")
MERGE_ANALYZE=("${PYTHON_BIN}" "${ROOT_DIR}/scripts/analyze_performance.py" --raw "${MERGE_OMP_DIR}/raw_trials.csv" --out_dir "${MERGE_OMP_DIR}" --plot_dir "${MERGE_OMP_DIR}/plots" --category merge_omp --seed "${SEED}")
BITONIC_ANALYZE=("${PYTHON_BIN}" "${ROOT_DIR}/scripts/analyze_performance.py" --raw "${BITONIC_DIR}/raw_trials.csv" --out_dir "${BITONIC_DIR}" --plot_dir "${BITONIC_DIR}/plots" --category bitonic --seed "${SEED}")

{
  echo "${FULL_ANALYZE[*]}"
  echo "${MERGE_ANALYZE[*]}"
  echo "${BITONIC_ANALYZE[*]}"
} >> "${commands_executed_txt}"

"${FULL_ANALYZE[@]}"
"${MERGE_ANALYZE[@]}"
"${BITONIC_ANALYZE[@]}"

echo "Done. ${OUT_DIR}"
echo "  summary + plots + report.md: ${OUT_DIR}/  ${MERGE_OMP_DIR}/  ${BITONIC_DIR}/"
