"""
Render an animated GIF from a hopper run's per-frame particle snapshots.

Run locally (venv), not in Docker:
    python analysis/make_gif_hopper.py [run_name]
"""

import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import PillowWriter

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# geometry env vars, matching the defaults in scripts/hopper_granules.py, used
# to fix the plot bounds so the funnel doesn't jump around between frames
TOP_RADIUS = float(os.environ.get("TOP_DIAMETER", 0.1)) / 2
HOPPER_HEIGHT = float(os.environ.get("HOPPER_HEIGHT", 0.08))

XY_HALF = TOP_RADIUS * 1.5  # a bit wider than the top opening, purely for framing
Z_TOP = HOPPER_HEIGHT
# there's no catch plate anymore, so pick a viewing depth below the aperture
# (one hopper-height) that's just enough to show particles discharging
Z_BOTTOM = -HOPPER_HEIGHT


def load_frame(path):
    xs, ys, zs, rs = [], [], [], []

    with open(path) as f:
        for line in f:
            x, y, z, r = (float(v) for v in line.split())
            xs.append(x)
            ys.append(y)
            zs.append(z)
            rs.append(r)

    return xs, ys, zs, rs


def main():
    run_name = sys.argv[1] if len(sys.argv) > 1 else "_default"
    # hopper_granules.py writes frames under "_hopper<run_name>" (no separator)
    frames_dir = OUTPUT_DIR / "frames" / f"_hopper{run_name}"

    frame_paths = sorted(frames_dir.glob("t_*.txt"))

    if not frame_paths:
        raise SystemExit(f"No frames found in {frames_dir}")

    fig = plt.figure(figsize=(5, 5))
    ax = fig.add_subplot(111, projection="3d")

    def draw(i):
        ax.clear()

        # Fixed bounds spanning the wide top opening down to the catch plate
        ax.set_xlim(-XY_HALF, XY_HALF)
        ax.set_ylim(-XY_HALF, XY_HALF)
        ax.set_zlim(Z_BOTTOM, Z_TOP)

        ax.set_box_aspect((2 * XY_HALF, 2 * XY_HALF, Z_TOP - Z_BOTTOM))
        ax.grid(False)

        ax.view_init(elev=15, azim=-60)

        # Load particle positions
        xs, ys, zs, rs = load_frame(frame_paths[i])

        sizes = [r * 1000 * 100 for r in rs]  # scale radii for visualization
        ax.scatter(
            xs,
            ys,
            zs,
            s=sizes,
            color="steelblue",
            depthshade=True,
            edgecolors="black",
        )

        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.set_zticklabels([])

        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])

        time_str = frame_paths[i].stem.split("_")[1]
        ax.set_title(f"{run_name}\nt = {time_str} s")

    writer = PillowWriter(fps=12)
    out_path = OUTPUT_DIR / f"_hopper{run_name}.gif"

    with writer.saving(fig, out_path, dpi=80):
        for i in range(len(frame_paths)):
            draw(i)
            writer.grab_frame()

    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
