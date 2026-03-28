#!/usr/bin/env python3

import argparse
import csv
import math
import statistics
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _parse_int(s: str | None, default: int = 0) -> int:
    if s is None or s == "":
        return default
    return int(float(s))


def _parse_float(s: str | None) -> float:
    if s is None or s == "":
        return float("nan")
    return float(s)


def impl_label_plot(impl: str, threads: int, block_size: int) -> str:
    if impl == "serial":
        return "merge_serial"
    if impl == "omp":
        return f"omp{threads}"
    if impl == "serial_bitonic":
        return "bitonic_serial"
    if impl == "cuda":
        return f"cuda_bitonic(bs={block_size})"
    return f"{impl}_t{threads}_b{block_size}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze raw_trials.csv into summary.csv, plots, optional report.")
    p.add_argument("--raw", required=True, help="Path to raw_trials.csv")
    p.add_argument("--out_dir", required=True, help="Directory for summary.csv")
    p.add_argument("--plot_dir", required=True, help="Directory for PNG plots")
    p.add_argument(
        "--category",
        choices=("full", "merge_omp", "bitonic"),
        default="full",
        help="Which plot families to emit.",
    )
    p.add_argument(
        "--report_name",
        default=None,
        help="Markdown under project report/ (default: performance_analysis.md or _<category>.md).",
    )
    p.add_argument("--seed", type=int, default=None, help="Only load rows for this RNG seed.")
    p.add_argument("--no-plots", action="store_true", dest="no_plots", help="Skip PNG plots.")
    p.add_argument(
        "--no-report",
        action="store_true",
        dest="no_report",
        help="Skip project report/ Markdown only; out_dir/report.md is still written.",
    )
    return p.parse_args()


def default_report_filename(category: str) -> str:
    if category == "full":
        return "performance_analysis.md"
    return f"performance_analysis_{category}.md"


def load_rows(raw_path: Path, seed_filter: int | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with raw_path.open(newline="", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            if seed_filter is not None and _parse_int(r.get("seed"), -1) != seed_filter:
                continue
            rows.append(r)
    return rows


def build_trial_serial_map(rows: list[dict[str, str]]) -> dict[tuple[int, int, str, int], float]:
    m: dict[tuple[int, int, str, int], float] = {}
    for r in rows:
        if r.get("impl") != "serial" or _parse_int(r.get("threads"), 0) != 1 or _parse_int(r.get("block_size"), -1) != 0:
            continue
        key = (
            _parse_int(r.get("size"), 0),
            _parse_int(r.get("seed"), 0),
            str(r.get("dist", "")),
            _parse_int(r.get("trial"), 0),
        )
        m[key] = _parse_float(r.get("avg_ms"))
    return m


def per_trial_speedups(
    rows: list[dict[str, str]],
    trial_serial: dict[tuple[int, int, str, int], float],
) -> dict[tuple[int, int, str, str, int, int], list[float]]:
    speedup_trials: dict[tuple[int, int, str, str, int, int], list[float]] = defaultdict(list)
    for r in rows:
        tk = (
            _parse_int(r.get("size"), 0),
            _parse_int(r.get("seed"), 0),
            str(r.get("dist", "")),
            _parse_int(r.get("trial"), 0),
        )
        if tk not in trial_serial:
            continue
        base = trial_serial[tk]
        if base <= 0 or not math.isfinite(base):
            continue
        t = _parse_float(r.get("avg_ms"))
        if t <= 0 or not math.isfinite(t):
            continue
        gkey = (tk[0], tk[1], tk[2], str(r.get("impl", "")), _parse_int(r.get("threads"), 0), _parse_int(r.get("block_size"), 0))
        speedup_trials[gkey].append(base / t)
    return speedup_trials


def group_stats(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    groups: dict[tuple[int, int, str, str, int, int], list[float]] = defaultdict(list)
    run_ids: dict[tuple[int, int, str, str, int, int], str] = {}
    for r in rows:
        key = (
            _parse_int(r.get("size"), 0),
            _parse_int(r.get("seed"), 0),
            str(r.get("dist", "")),
            str(r.get("impl", "")),
            _parse_int(r.get("threads"), 0),
            _parse_int(r.get("block_size"), 0),
        )
        groups[key].append(_parse_float(r.get("avg_ms")))
        if key not in run_ids:
            run_ids[key] = str(r.get("run_id", ""))

    out: list[dict[str, Any]] = []
    for key, times in groups.items():
        n = len(times)
        finite = [x for x in times if math.isfinite(x)]
        if not finite:
            mean_ms = float("nan")
            stdev_ms = 0.0
        else:
            mean_ms = float(statistics.mean(finite))
            stdev_ms = float(statistics.stdev(finite)) if len(finite) >= 2 else 0.0
        out.append(
            {
                "run_id": run_ids.get(key, ""),
                "size": key[0],
                "seed": key[1],
                "dist": key[2],
                "impl": key[3],
                "threads": key[4],
                "block_size": key[5],
                "n_trials": n,
                "mean_ms": mean_ms,
                "stdev_ms": stdev_ms,
            }
        )
    return out


def baseline_map_from_summary(summary: list[dict[str, Any]]) -> dict[tuple[int, int, str], float]:
    out: dict[tuple[int, int, str], float] = {}
    for r in summary:
        if str(r["impl"]) != "serial" or int(r["threads"]) != 1 or int(r["block_size"]) != 0:
            continue
        k = (int(r["size"]), int(r["seed"]), str(r["dist"]))
        out[k] = float(r["mean_ms"])
    return out


def attach_speedup_columns(
    summary: list[dict[str, Any]],
    speedup_trials: dict[tuple[int, int, str, str, int, int], list[float]],
    base_map: dict[tuple[int, int, str], float],
) -> list[dict[str, Any]]:
    for r in summary:
        bkey = (int(r["size"]), int(r["seed"]), str(r["dist"]))
        base_mean = base_map.get(bkey, float("nan"))
        mean_ms = float(r["mean_ms"])
        if math.isfinite(base_mean) and base_mean > 0 and math.isfinite(mean_ms) and mean_ms > 0:
            r["speedup_vs_serial"] = base_mean / mean_ms
        else:
            r["speedup_vs_serial"] = float("nan")

        gkey = (int(r["size"]), int(r["seed"]), str(r["dist"]), str(r["impl"]), int(r["threads"]), int(r["block_size"]))
        ratios = speedup_trials.get(gkey, [])
        nr = len(ratios)
        if nr >= 2:
            r["speedup_stdev"] = float(statistics.stdev(ratios))
        elif nr == 1:
            r["speedup_stdev"] = 0.0
        else:
            r["speedup_stdev"] = float("nan")

        if str(r["impl"]) == "omp":
            su = r["speedup_vs_serial"]
            th = int(r["threads"])
            r["parallel_efficiency"] = float(su) / th if th > 0 and math.isfinite(su) else float("nan")
        else:
            r["parallel_efficiency"] = float("nan")
    return summary


def write_summary_csv(path: Path, summary: list[dict[str, Any]]) -> None:
    cols = [
        "run_id",
        "size",
        "seed",
        "dist",
        "impl",
        "threads",
        "block_size",
        "n_trials",
        "mean_ms",
        "stdev_ms",
        "speedup_vs_serial",
        "speedup_stdev",
        "parallel_efficiency",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in summary:
            w.writerow({c: r[c] for c in cols})


def _import_plt():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def plot_speedup_merge_omp(
    summary: list[dict[str, Any]],
    dist: str,
    out_path: Path,
    effective_seed: int,
) -> None:
    try:
        plt = _import_plt()
    except Exception:
        print(traceback.format_exc())
        return

    sub = [r for r in summary if str(r["dist"]) == dist and str(r["impl"]) == "omp" and int(r["seed"]) == effective_seed]
    if not sub:
        return

    threads_list = sorted({int(r["threads"]) for r in sub})
    fig, ax = plt.subplots(figsize=(9, 5))
    for th in threads_list:
        s = sorted([r for r in sub if int(r["threads"]) == th], key=lambda x: int(x["size"]))
        x = [int(r["size"]) for r in s]
        y = [float(r["speedup_vs_serial"]) for r in s]
        yerr = [float(r["speedup_stdev"]) if float(r["speedup_stdev"]) > 0 else 0.0 for r in s]
        lbl = impl_label_plot("omp", th, 0)
        if any(ye > 0 for ye in yerr):
            ax.errorbar(x, y, yerr=yerr, marker="o", capsize=3, label=lbl, linestyle="-")
        else:
            ax.plot(x, y, marker="o", label=lbl, linestyle="-")

    for th in threads_list:
        ax.axhline(y=float(th), linestyle=":", color="0.55", alpha=0.65, linewidth=1.0)
    ax.axhline(y=1.0, color="k", linestyle="-", linewidth=1.0, label="baseline y=1")
    ax.set_xscale("log", base=2)
    ax.set_xlabel("Array size")
    ax.set_ylabel("Speedup vs merge-serial")
    ax.set_title(f"OpenMP merge vs merge-serial — {dist} (seed={effective_seed})")
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_speedup_bitonic(
    summary: list[dict[str, Any]],
    dist: str,
    out_path: Path,
    effective_seed: int,
) -> None:
    try:
        plt = _import_plt()
    except Exception:
        print(traceback.format_exc())
        return

    sub = [
        r
        for r in summary
        if str(r["dist"]) == dist and str(r["impl"]) in ("serial_bitonic", "cuda") and int(r["seed"]) == effective_seed
    ]
    if not sub:
        return

    fig, ax = plt.subplots(figsize=(9, 5))
    keys = sorted({(str(r["impl"]), int(r["threads"]), int(r["block_size"])) for r in sub})
    for impl, th, bs in keys:
        g = sorted(
            [r for r in sub if str(r["impl"]) == impl and int(r["threads"]) == th and int(r["block_size"]) == bs],
            key=lambda x: int(x["size"]),
        )
        x = [int(r["size"]) for r in g]
        y = [float(r["speedup_vs_serial"]) for r in g]
        yerr = [float(r["speedup_stdev"]) if float(r["speedup_stdev"]) > 0 else 0.0 for r in g]
        lbl = impl_label_plot(impl, th, bs)
        if any(ye > 0 for ye in yerr):
            ax.errorbar(x, y, yerr=yerr, marker="o", capsize=3, label=lbl, linestyle="-")
        else:
            ax.plot(x, y, marker="o", label=lbl, linestyle="-")
    ax.axhline(y=1.0, color="k", linestyle="-", linewidth=1.0, label="baseline y=1")
    ax.set_xscale("log", base=2)
    ax.set_xlabel("Array size")
    ax.set_ylabel("Speedup vs merge-serial")
    ax.set_title(f"Bitonic / CUDA vs merge-serial — {dist} (seed={effective_seed})")
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def _experiment_config_label(r: dict[str, Any]) -> str:
    impl = str(r["impl"])
    th = int(r["threads"])
    bs = int(r["block_size"])
    if impl == "omp":
        return f"OpenMP, {th} threads"
    if impl == "cuda":
        return f"CUDA, block size {bs}"
    if impl == "serial_bitonic":
        return "Serial bitonic"
    return "Serial merge"


def _allowed_impls_for_category(category: str) -> set[str] | None:
    if category == "merge_omp":
        return {"serial", "omp"}
    if category == "bitonic":
        return {"serial", "serial_bitonic", "cuda"}
    return None


def _filter_summary_for_experiment_report(
    summary: list[dict[str, Any]], category: str, effective_seed: int
) -> list[dict[str, Any]]:
    allowed = _allowed_impls_for_category(category)
    out: list[dict[str, Any]] = []
    for r in summary:
        if int(r["seed"]) != effective_seed:
            continue
        impl = str(r["impl"])
        if allowed is not None and impl not in allowed:
            continue
        if impl == "serial" and int(r["threads"]) != 1:
            continue
        out.append(r)
    return out


def _winner_rows_by_size_dist(sub: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
    """For each (size, dist), return (best_row, serial_merge_row_or_none)."""
    groups: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for r in sub:
        groups[(int(r["size"]), str(r["dist"]))].append(r)

    out: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
    for key in sorted(groups.keys()):
        rs = groups[key]
        best = min(rs, key=lambda x: float(x["mean_ms"]))
        serial = next(
            (
                x
                for x in rs
                if str(x["impl"]) == "serial" and int(x["threads"]) == 1 and int(x["block_size"]) == 0
            ),
            None,
        )
        out.append((best, serial))
    return out


def write_experiment_report_md(
    out_dir: Path,
    category: str,
    summary: list[dict[str, Any]],
    effective_seed: int,
    raw_path: Path,
) -> None:
    """Write experiments/<run>/report.md (or merge_omp/bitonic/report.md) from summary stats."""
    sub = _filter_summary_for_experiment_report(summary, category, effective_seed)
    if not sub:
        return

    run_id = str(sub[0].get("run_id", ""))
    n_trials_vals = {int(r["n_trials"]) for r in sub}
    n_trials_lo = min(n_trials_vals)
    n_trials_hi = max(n_trials_vals)
    trials_note = f"{n_trials_lo}" if n_trials_lo == n_trials_hi else f"{n_trials_lo}–{n_trials_hi}"

    if category == "full":
        title = "Experiment report (full matrix)"
        intro = (
            "Compares **serial merge**, **serial bitonic**, **OpenMP merge** (varying threads), "
            "and **CUDA bitonic** (varying block size). Fastest = lowest mean wall time per configuration."
        )
    elif category == "merge_omp":
        title = "Experiment report: merge vs OpenMP"
        intro = "Compares **serial merge** and **OpenMP parallel merge** only."
    else:
        title = "Experiment report: merge vs bitonic vs CUDA"
        intro = "Compares **serial merge**, **serial bitonic**, and **CUDA bitonic** only."

    lines: list[str] = [
        f"# {title}",
        "",
        f"- **Run ID:** `{run_id}` · **Seed:** {effective_seed} · **Trials per config:** {trials_note}",
        f"- **Raw trials:** `{raw_path.name}` · **Summary:** `summary.csv`",
        "",
        intro,
        "",
        "## Fastest configuration per array size and distribution",
        "",
        "| n | Distribution | Fastest | Mean (ms) | vs serial merge |",
        "|---|--------------|---------|------------|-----------------|",
    ]

    winners = _winner_rows_by_size_dist(sub)
    impl_counts: dict[str, int] = defaultdict(int)

    for best, serial in winners:
        n = int(best["size"])
        dist = str(best["dist"])
        label = _experiment_config_label(best)
        mean_ms = float(best["mean_ms"])
        impl_key = str(best["impl"])
        if impl_key == "omp":
            impl_key = f"omp:{int(best['threads'])}"
        elif impl_key == "cuda":
            impl_key = f"cuda:{int(best['block_size'])}"
        impl_counts[impl_key] = impl_counts.get(impl_key, 0) + 1

        if serial is not None and math.isfinite(mean_ms) and mean_ms > 0:
            base = float(serial["mean_ms"])
            if math.isfinite(base) and base > 0:
                su = base / mean_ms
                vs_ser = f"{su:.2f}×"
            else:
                vs_ser = "—"
        else:
            vs_ser = "—"

        lines.append(
            f"| {n:,} | {dist} | {label} | {mean_ms:.2f} | {vs_ser} |",
        )

    lines.extend(
        [
            "",
            "## Quick counts (how often each implementation wins)",
            "",
        ]
    )
    for k in sorted(impl_counts.keys(), key=lambda x: (-impl_counts[x], x)):
        lines.append(f"- **{k}:** {impl_counts[k]} / {len(winners)} cells")
    if category == "full":
        lines.extend(
            [
                "",
                "## Notes",
                "",
                "- **vs serial merge** is the ratio of mean serial-merge time to mean time of the winning row (same `n`, distribution, seed).",
                "- At smaller `n`, OpenMP often wins; CUDA can dominate at large `n` for uniform/gaussian data on GPU-equipped runs.",
                "- **Serial bitonic** is expected to be much slower than merge-sort baselines; see `speedup_vs_serial` in `summary.csv`.",
            ]
        )
    elif category == "merge_omp":
        lines.extend(
            [
                "",
                "## Notes",
                "",
                "- Speedups vs serial merge match the `speedup_vs_serial` column in `summary.csv` for the winning OpenMP row.",
                "- If OpenMP wins every cell, scaling is still limited by memory bandwidth; check `parallel_efficiency` in the CSV.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## Notes",
                "",
                "- **Serial merge** can beat CUDA at small `n` or when input is **nearly sorted** / **reversed** (CPU merge advantages + GPU launch overhead).",
                "- Compare with the OpenMP merge track in the parent run’s `merge_omp/report.md` when available.",
            ]
        )

    out_path = out_dir / "report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(
    args: argparse.Namespace,
    raw_path: Path,
    rows: list[dict[str, str]],
    summary: list[dict[str, Any]],
    report_path: Path,
    effective_seed: int,
) -> None:
    seeds = sorted({_parse_int(r.get("seed"), 0) for r in rows})
    if summary:
        nmin = min(int(r["n_trials"]) for r in summary)
        nmax = max(int(r["n_trials"]) for r in summary)
    else:
        nmin, nmax = 0, 0

    lines = [
        "# Performance analysis",
        "",
        f"- Raw: `{raw_path}` · category `{args.category}` · seed **{effective_seed}** · trials/config **{nmin}–{nmax}** · seeds {seeds}",
        "",
        "Speedup = mean(merge-serial) / mean(row); `speedup_stdev` from per-trial ratios; OpenMP `parallel_efficiency` = speedup/threads.",
        "",
        "## Highlights",
        "",
    ]

    omp = [r for r in summary if str(r["impl"]) == "omp"]
    if omp:
        largest_n = max(int(r["size"]) for r in omp)
        omp_at_max = [r for r in omp if int(r["size"]) == largest_n]
        best_omp = max(
            omp_at_max,
            key=lambda r: float(r["parallel_efficiency"]) if math.isfinite(float(r["parallel_efficiency"])) else float("-inf"),
        )
        lines.append(
            f"- **Best OpenMP** (largest n={largest_n}, by efficiency): `{impl_label_plot('omp', int(best_omp['threads']), 0)}` "
            f"dist={best_omp['dist']} eff={float(best_omp['parallel_efficiency']):.4f} speedup={float(best_omp['speedup_vs_serial']):.4f}"
        )
    else:
        lines.append("- **OpenMP**: (none)")

    bit = [r for r in summary if str(r["impl"]) == "serial_bitonic"]
    if bit:
        mx = max(bit, key=lambda r: float(r["speedup_vs_serial"]) if math.isfinite(float(r["speedup_vs_serial"])) else float("-inf"))
        lines.append(
            f"- **Bitonic (serial)** best: dist={mx['dist']} n={int(mx['size'])} speedup={float(mx['speedup_vs_serial']):.4f}"
        )
    else:
        lines.append("- **Bitonic (serial)**: (none)")

    cuda = [r for r in summary if str(r["impl"]) == "cuda"]
    if cuda:
        lines.append("- **Best CUDA** (max n per dist, best speedup among blocks):")
        for dist in sorted({str(r["dist"]) for r in cuda}):
            d = [r for r in cuda if str(r["dist"]) == dist]
            max_sz = max(int(r["size"]) for r in d)
            d2 = [r for r in d if int(r["size"]) == max_sz]
            best = max(d2, key=lambda r: float(r["speedup_vs_serial"]) if math.isfinite(float(r["speedup_vs_serial"])) else float("-inf"))
            lines.append(
                f"  - `{dist}` n={max_sz}: `{impl_label_plot('cuda', int(best['threads']), int(best['block_size']))}` "
                f"speedup={float(best['speedup_vs_serial']):.4f}"
            )
    else:
        lines.append("- **CUDA**: (none)")

    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    raw_path = Path(args.raw).resolve()
    out_dir = Path(args.out_dir)
    plot_dir = Path(args.plot_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(raw_path, args.seed)
    if not rows:
        raise SystemExit("No rows after loading/filtering.")

    trial_serial = build_trial_serial_map(rows)
    speedup_trials = per_trial_speedups(rows, trial_serial)
    summary = group_stats(rows)
    base_map = baseline_map_from_summary(summary)
    summary = attach_speedup_columns(summary, speedup_trials, base_map)

    write_summary_csv(out_dir / "summary.csv", summary)

    seeds_in_data = sorted({_parse_int(r.get("seed"), 0) for r in rows})
    effective_seed = args.seed if args.seed is not None else seeds_in_data[0]
    cat = args.category

    try:
        write_experiment_report_md(out_dir, cat, summary, effective_seed, raw_path)
    except Exception:
        print(traceback.format_exc())
    dists = sorted({str(r.get("dist", "")) for r in rows})

    if not args.no_plots:
        for dist in dists:
            if cat in ("full", "merge_omp"):
                try:
                    plot_speedup_merge_omp(summary, dist, plot_dir / f"speedup_merge_omp_{dist}.png", effective_seed)
                except Exception:
                    print(traceback.format_exc())
            if cat in ("full", "bitonic"):
                try:
                    plot_speedup_bitonic(summary, dist, plot_dir / f"speedup_bitonic_{dist}.png", effective_seed)
                except Exception:
                    print(traceback.format_exc())

    if not args.no_report:
        rname = args.report_name if args.report_name else default_report_filename(args.category)
        report_path = _PROJECT_ROOT / "report" / rname
        try:
            write_report(args, raw_path, rows, summary, report_path, effective_seed)
        except Exception:
            print(traceback.format_exc())


if __name__ == "__main__":
    main()
