"""
Plot packing fraction vs. iteration for a run.

Run locally (venv), not in Docker:
    python analysis/plot_packing.py [run_name]
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def load(run_name):
    path = OUTPUT_DIR / f"packing_{run_name}.txt"
    iters, fractions = [], []
    with open(path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            i, frac = line.split()
            iters.append(int(i))
            fractions.append(float(frac))
    return iters, fractions


def main():
    run_name = sys.argv[1] if len(sys.argv) > 1 else "_default"
    iters, fractions = load(run_name)

    fig, ax = plt.subplots()
    ax.plot(iters, fractions)
    ax.set_xlabel("iteration")
    ax.set_ylabel("packing fraction")
    ax.set_title(f"Packing fraction over time ({run_name})")

    out_path = OUTPUT_DIR / f"packing_{run_name}.png"
    fig.savefig(out_path, dpi=150)
    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
