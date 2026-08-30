"""
Compare final packing fraction across runs with different particle sizes.

Run locally (venv), after generating one or more runs via docker (each with a
different RUN_NAME/R_MEAN, see README):
    python analysis/compare_packing.py
"""

import csv
from pathlib import Path

import matplotlib.pyplot as plt

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def main():
    summary_path = OUTPUT_DIR / "summary.csv"
    with open(summary_path, newline="") as f:
        rows = list(csv.DictReader(f))

    rows.sort(key=lambda r: float(r["r_mean"]))
    r_means = [float(r["r_mean"]) for r in rows]
    fractions = [float(r["final_packing_fraction"]) for r in rows]
    labels = [r["run_name"] for r in rows]

    fig, ax = plt.subplots()
    ax.plot(r_means, fractions, "o-")
    for x, y, label in zip(r_means, fractions, labels):
        ax.annotate(label, (x, y), textcoords="offset points", xytext=(5, 5))
    ax.set_xlabel("mean particle radius (m)")
    ax.set_ylabel("final packing fraction")
    ax.set_title("Packing density vs. particle size")

    out_path = OUTPUT_DIR / "packing_vs_size.png"
    fig.savefig(out_path, dpi=150)
    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
