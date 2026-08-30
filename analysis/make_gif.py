"""
Render an animated GIF from a run's per-frame particle snapshots.

Run locally (venv), not in Docker:
    python analysis/make_gif.py [run_name]
"""

import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import PillowWriter

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
BOX_SIZE = (0.1, 0.1, 0.1)  # keep in sync with scripts/granular_jamming.py


def load_frame(path):
    xs, zs, rs = [], [], []
    with open(path) as f:
        for line in f:
            x, _y, z, r = (float(v) for v in line.split())
            xs.append(x)
            zs.append(z)
            rs.append(r)
    return xs, zs, rs


def main():
    run_name = sys.argv[1] if len(sys.argv) > 1 else "default"
    frames_dir = OUTPUT_DIR / "frames" / run_name
    frame_paths = sorted(frames_dir.glob("frame_*.txt"))
    if not frame_paths:
        raise SystemExit(f"No frames found in {frames_dir}")

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.set_xlim(0, BOX_SIZE[0])
    ax.set_ylim(0, BOX_SIZE[2])
    ax.set_aspect("equal")

    def radius_to_marker_size(r):
        # convert a data-space radius to a scatter `s` (marker area in points^2)
        # so particle sizes on the GIF actually match their simulated radius
        px_per_unit = ax.transData.transform((1, 0))[0] - ax.transData.transform((0, 0))[0]
        points_per_px = 72.0 / fig.dpi
        radius_points = r * px_per_unit * points_per_px
        return math.pi * radius_points**2

    def draw(i):
        ax.clear()
        ax.set_xlim(0, BOX_SIZE[0])
        ax.set_ylim(0, BOX_SIZE[2])
        xs, zs, rs = load_frame(frame_paths[i])
        sizes = [radius_to_marker_size(r) for r in rs]
        ax.scatter(xs, zs, s=sizes, c=rs, cmap="viridis")
        ax.set_xlabel("x (m)")
        ax.set_ylabel("z (m)")
        ax.set_title(f"{run_name} — frame {i + 1}/{len(frame_paths)}")

    writer = PillowWriter(fps=12)
    out_path = OUTPUT_DIR / f"{run_name}.gif"
    with writer.saving(fig, out_path, dpi=100):
        for i in range(len(frame_paths)):
            draw(i)
            writer.grab_frame()

    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
