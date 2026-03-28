#!/usr/bin/env python3

import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

TIMING_OMP_ORDER = [2, 4, 8, 16]
TIMING_CUDA_ORDER = [128, 256, 512, 1024]


def _i(s: str | None, d: int = 0) -> int:
    if not s:
        return d
    return int(float(s))


def _f(s: str | None) -> float:
    if not s:
        return float("nan")
    return float(s)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="raw_trials.csv → summary.csv, plots, report.md")
    p.add_argument("--raw", required=True)
    p.add_argument("--out_dir", required=True)
    p.add_argument("--plot_dir", required=True)
    p.add_argument("--category", choices=("full", "merge_omp", "bitonic"), default="full")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--no-plots", action="store_true", dest="no_plots")
    return p.parse_args()


def load_rows(raw_path: Path, seed_filter: int | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with raw_path.open(newline="", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            if seed_filter is not None and _i(r.get("seed"), -1) != seed_filter:
                continue
            rows.append(r)
    return rows


def build_trial_serial_map(rows: list[dict[str, str]]) -> dict[tuple[int, int, str, int], float]:
    m: dict[tuple[int, int, str, int], float] = {}
    for r in rows:
        if r.get("impl") != "serial" or _i(r.get("threads")) != 1 or _i(r.get("block_size"), -1) != 0:
            continue
        k = (_i(r.get("size")), _i(r.get("seed")), str(r.get("dist", "")), _i(r.get("trial")))
        m[k] = _f(r.get("avg_ms"))
    return m


def per_trial_speedups(
    rows: list[dict[str, str]],
    trial_serial: dict[tuple[int, int, str, int], float],
) -> dict[tuple[int, int, str, str, int, int], list[float]]:
    out: dict[tuple[int, int, str, str, int, int], list[float]] = defaultdict(list)
    for r in rows:
        tk = (_i(r.get("size")), _i(r.get("seed")), str(r.get("dist", "")), _i(r.get("trial")))
        if tk not in trial_serial:
            continue
        base = trial_serial[tk]
        if base <= 0 or not math.isfinite(base):
            continue
        t = _f(r.get("avg_ms"))
        if t <= 0 or not math.isfinite(t):
            continue
        gk = (tk[0], tk[1], tk[2], str(r.get("impl", "")), _i(r.get("threads")), _i(r.get("block_size")))
        out[gk].append(base / t)
    return out


def group_stats(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    groups: dict[tuple[int, int, str, str, int, int], list[float]] = defaultdict(list)
    run_ids: dict[tuple[int, int, str, str, int, int], str] = {}
    for r in rows:
        key = (
            _i(r.get("size")),
            _i(r.get("seed")),
            str(r.get("dist", "")),
            str(r.get("impl", "")),
            _i(r.get("threads")),
            _i(r.get("block_size")),
        )
        groups[key].append(_f(r.get("avg_ms")))
        run_ids.setdefault(key, str(r.get("run_id", "")))

    out: list[dict[str, Any]] = []
    for key, times in groups.items():
        finite = [x for x in times if math.isfinite(x)]
        mean_ms = float(statistics.mean(finite)) if finite else float("nan")
        stdev_ms = float(statistics.stdev(finite)) if len(finite) >= 2 else 0.0
        out.append(
            {
                "run_id": run_ids[key],
                "size": key[0],
                "seed": key[1],
                "dist": key[2],
                "impl": key[3],
                "threads": key[4],
                "block_size": key[5],
                "n_trials": len(times),
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
        out[(int(r["size"]), int(r["seed"]), str(r["dist"]))] = float(r["mean_ms"])
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
            su, th = r["speedup_vs_serial"], int(r["threads"])
            r["parallel_efficiency"] = float(su) / th if th > 0 and math.isfinite(su) else float("nan")
        else:
            r["parallel_efficiency"] = float("nan")
    return summary


def write_summary_csv(path: Path, summary: list[dict[str, Any]]) -> None:
    cols = [
        "run_id", "size", "seed", "dist", "impl", "threads", "block_size",
        "n_trials", "mean_ms", "stdev_ms", "speedup_vs_serial", "speedup_stdev", "parallel_efficiency",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in summary:
            w.writerow({c: r[c] for c in cols})


def _impl_allowed(category: str) -> set[str] | None:
    if category == "merge_omp":
        return {"serial", "omp"}
    if category == "bitonic":
        return {"serial", "serial_bitonic", "cuda"}
    return None


def _label(impl: str, threads: int, block_size: int) -> str:
    if impl == "serial":
        return "merge_serial"
    if impl == "omp":
        return f"omp{threads}"
    if impl == "serial_bitonic":
        return "bitonic_serial"
    if impl == "cuda":
        return f"cuda_bitonic(bs={block_size})"
    return f"{impl}_t{threads}_b{block_size}"


def _config_label(r: dict[str, Any]) -> str:
    impl = str(r["impl"])
    if impl == "omp":
        return f"OpenMP, {int(r['threads'])} threads"
    if impl == "cuda":
        return f"CUDA, block size {int(r['block_size'])}"
    if impl == "serial_bitonic":
        return "Serial bitonic"
    return "Serial merge"


def write_report_md(
    out_dir: Path, category: str, summary: list[dict[str, Any]], seed: int, raw_name: str
) -> None:
    allowed = _impl_allowed(category)
    sub = [
        r for r in summary
        if int(r["seed"]) == seed and (allowed is None or str(r["impl"]) in allowed)
        and (str(r["impl"]) != "serial" or int(r["threads"]) == 1)
    ]
    if not sub:
        return

    groups: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for r in sub:
        groups[(int(r["size"]), str(r["dist"]))].append(r)

    lines = [
        "# Experiment report",
        "",
        f"Run `{sub[0].get('run_id', '')}` · seed {seed} · `{raw_name}` → `summary.csv`",
        "",
        "| n | Distribution | Fastest | Mean (ms) | vs serial merge |",
        "|---|--------------|---------|------------|-----------------|",
    ]
    for (n, dist) in sorted(groups):
        rs = groups[(n, dist)]
        best = min(rs, key=lambda x: float(x["mean_ms"]))
        serial = next(
            (x for x in rs if str(x["impl"]) == "serial" and int(x["threads"]) == 1 and int(x["block_size"]) == 0),
            None,
        )
        mean_ms = float(best["mean_ms"])
        if serial and math.isfinite(mean_ms) and mean_ms > 0:
            base = float(serial["mean_ms"])
            vs = f"{base / mean_ms:.2f}×" if math.isfinite(base) and base > 0 else "—"
        else:
            vs = "—"
        lines.append(f"| {n:,} | {dist} | {_config_label(best)} | {mean_ms:.2f} | {vs} |")

    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_plots(
    plt: Any,
    summary: list[dict[str, Any]],
    plot_dir: Path,
    seed: int,
    dists: list[str],
    category: str,
) -> None:
    for dist in dists:
        if category in ("full", "merge_omp"):
            sub = [r for r in summary if str(r["dist"]) == dist and str(r["impl"]) == "omp" and int(r["seed"]) == seed]
            if sub:
                fig, ax = plt.subplots(figsize=(9, 5))
                for th in sorted({int(r["threads"]) for r in sub}):
                    s = sorted([r for r in sub if int(r["threads"]) == th], key=lambda x: int(x["size"]))
                    x, y = [int(r["size"]) for r in s], [float(r["speedup_vs_serial"]) for r in s]
                    ye = [float(r["speedup_stdev"]) if float(r["speedup_stdev"]) > 0 else 0.0 for r in s]
                    kw = dict(marker="o", linestyle="-", label=_label("omp", th, 0))
                    if any(ye):
                        ax.errorbar(x, y, yerr=ye, capsize=3, **kw)
                    else:
                        ax.plot(x, y, **kw)
                for th in sorted({int(r["threads"]) for r in sub}):
                    ax.axhline(y=float(th), linestyle=":", color="0.55", alpha=0.65)
                ax.axhline(y=1.0, color="k", linestyle="-", linewidth=1.0)
                ax.set_xscale("log", base=2)
                ax.set_xlabel("Array size")
                ax.set_ylabel("Speedup vs merge-serial")
                ax.set_title(f"OpenMP merge — {dist} (seed={seed})")
                ax.legend(fontsize=8)
                ax.grid(True, alpha=0.3)
                fig.tight_layout()
                plot_dir.mkdir(parents=True, exist_ok=True)
                fig.savefig(plot_dir / f"speedup_merge_omp_{dist}.png", dpi=150)
                plt.close(fig)

        if category in ("full", "bitonic"):
            sub = [
                r for r in summary
                if str(r["dist"]) == dist and str(r["impl"]) in ("serial_bitonic", "cuda") and int(r["seed"]) == seed
            ]
            if sub:
                fig, ax = plt.subplots(figsize=(9, 5))
                for impl, th, bs in sorted({(str(r["impl"]), int(r["threads"]), int(r["block_size"])) for r in sub}):
                    g = sorted(
                        [r for r in sub if str(r["impl"]) == impl and int(r["threads"]) == th and int(r["block_size"]) == bs],
                        key=lambda x: int(x["size"]),
                    )
                    x, y = [int(r["size"]) for r in g], [float(r["speedup_vs_serial"]) for r in g]
                    ye = [float(r["speedup_stdev"]) if float(r["speedup_stdev"]) > 0 else 0.0 for r in g]
                    kw = dict(marker="o", linestyle="-", label=_label(impl, th, bs))
                    if any(ye):
                        ax.errorbar(x, y, yerr=ye, capsize=3, **kw)
                    else:
                        ax.plot(x, y, **kw)
                ax.axhline(y=1.0, color="k", linestyle="-", linewidth=1.0)
                ax.set_xscale("log", base=2)
                ax.set_xlabel("Array size")
                ax.set_ylabel("Speedup vs merge-serial")
                ax.set_title(f"Bitonic / CUDA — {dist} (seed={seed})")
                ax.legend(fontsize=8)
                ax.grid(True, alpha=0.3)
                fig.tight_layout()
                plot_dir.mkdir(parents=True, exist_ok=True)
                fig.savefig(plot_dir / f"speedup_bitonic_{dist}.png", dpi=150)
                plt.close(fig)

    allowed = _impl_allowed(category)
    omp_th = [x for x in TIMING_OMP_ORDER if x in {int(r["threads"]) for r in summary if str(r["impl"]) == "omp"}]
    omp_th += sorted(x for x in {int(r["threads"]) for r in summary if str(r["impl"]) == "omp"} if x not in omp_th)
    cuda_bs = [x for x in TIMING_CUDA_ORDER if x in {int(r["block_size"]) for r in summary if str(r["impl"]) == "cuda"}]
    cuda_bs += sorted(x for x in {int(r["block_size"]) for r in summary if str(r["impl"]) == "cuda"} if x not in cuda_bs)

    series: list[tuple[str, str, int | None, int | None, str]] = []
    if allowed is None or "serial" in allowed:
        series.append(("Serial Merge", "serial", None, None, "C0"))
    if allowed is None or "serial_bitonic" in allowed:
        series.append(("Serial Bitonic", "serial_bitonic", None, None, "C1"))
    if allowed is None or "omp" in allowed:
        for i, th in enumerate(omp_th):
            series.append((f"OMP {th}T", "omp", th, None, f"C{(i + 2) % 10}"))
    if allowed is None or "cuda" in allowed:
        for i, bs in enumerate(cuda_bs):
            series.append((f"CUDA B={bs}", "cuda", None, bs, f"C{(i + 6) % 10}"))

    if not series:
        return

    subdir = plot_dir / "timing_comparison"
    subdir.mkdir(parents=True, exist_ok=True)

    for dist in dists:
        sizes = sorted({int(r["size"]) for r in summary if str(r["dist"]) == dist and int(r["seed"]) == seed})
        if not sizes:
            continue
        fig, ax = plt.subplots(figsize=(12, 6))
        n_bars, bar_w = len(series), 0.72 / max(len(series), 1)
        x0 = list(range(len(sizes)))

        def curve(impl: str, th: int | None, bs: int | None) -> dict[int, float]:
            d: dict[int, float] = {}
            for r in summary:
                if str(r["dist"]) != dist or int(r["seed"]) != seed or str(r["impl"]) != impl:
                    continue
                t, b = int(r["threads"]), int(r["block_size"])
                if impl in ("serial", "serial_bitonic") and (t != 1 or b != 0):
                    continue
                if impl == "omp" and (th is None or t != th or b != 0):
                    continue
                if impl == "cuda" and (bs is None or b != bs):
                    continue
                d[int(r["size"])] = float(r["mean_ms"])
            return d

        for bi, (disp, impl, th, bs, color) in enumerate(series):
            data = curve(impl, th, bs)
            offset = (bi - n_bars / 2 + 0.5) * bar_w
            heights = [data.get(sz, float("nan")) for sz in sizes]
            ph, col = [], []
            for h in heights:
                if math.isfinite(h) and h > 0:
                    ph.append(h)
                    col.append(color)
                else:
                    ph.append(1e-6)
                    col.append("#ddd")
            ax.bar([x + offset for x in x0], ph, width=bar_w * 0.92, label=disp, color=col, edgecolor="white", linewidth=0.5)

        ax.set_yscale("log")
        ax.set_xlabel("Array size")
        ax.set_ylabel("Mean time (ms)")
        ax.set_title(f"Timing — {dist} (seed={seed})")
        ax.set_xticks(x0)
        ax.set_xticklabels([str(s) for s in sizes])
        ax.legend(loc="upper left", fontsize=8, ncol=2)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        fig.tight_layout()
        safe = dist.replace("/", "_").replace(" ", "_")
        fig.savefig(subdir / f"timing_{safe}_bars.png", dpi=150)
        plt.close(fig)


def main() -> None:
    args = parse_args()
    raw_path = Path(args.raw).resolve()
    out_dir, plot_dir = Path(args.out_dir), Path(args.plot_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(raw_path, args.seed)
    if not rows:
        raise SystemExit("No rows after loading/filtering.")

    trial_serial = build_trial_serial_map(rows)
    gs = group_stats(rows)
    summary = attach_speedup_columns(gs, per_trial_speedups(rows, trial_serial), baseline_map_from_summary(gs))

    write_summary_csv(out_dir / "summary.csv", summary)

    seeds_in_data = sorted({_i(r.get("seed")) for r in rows})
    effective_seed = args.seed if args.seed is not None else seeds_in_data[0]
    write_report_md(out_dir, args.category, summary, effective_seed, raw_path.name)

    dists = sorted({str(r.get("dist", "")) for r in rows})
    if not args.no_plots:
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            run_plots(plt, summary, plot_dir, effective_seed, dists, args.category)
        except ImportError:
            pass


if __name__ == "__main__":
    main()
