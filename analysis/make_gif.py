"""
Render an animated GIF from a run's per-frame particle snapshots.

Run locally (venv), not in Docker:
    python analysis/make_gif.py [run_name]
"""

import sys
from pathlib import Path
import os

import matplotlib.pyplot as plt
from matplotlib.animation import PillowWriter

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
BOX_SIZE = tuple(map(float, os.environ["BOX_SIZE"].split(",")))

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
    run_name = sys.argv[1] if len(sys.argv) > 1 else "default"
    frames_dir = OUTPUT_DIR / "frames" / run_name

    # limit to first 100 frames to reduce output filesize
    # and cut uninteresting frames
    frame_paths = sorted(frames_dir.glob("frame_*.txt"))[:100]

    if not frame_paths:
        raise SystemExit(f"No frames found in {frames_dir}")

    fig = plt.figure(figsize=(5, 5))
    ax = fig.add_subplot(111, projection="3d")

    def draw(i):
        ax.clear()

        # Set the simulation box
        ax.set_xlim(0, BOX_SIZE[0])
        ax.set_ylim(0, BOX_SIZE[1])
        ax.set_zlim(0, BOX_SIZE[2])

        ax.set_box_aspect(BOX_SIZE)
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
            # alpha=1,
            depthshade=True,
            edgecolors="black",
        )

        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.set_zticklabels([])

        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])

        # ax.set_xlabel("x")
        # ax.set_ylabel("y")
        # ax.set_zlabel("z")
        ax.set_title(
            f"{run_name}\nframe {i + 1}/{len(frame_paths)}"
        )

    writer = PillowWriter(fps=12)
    out_path = OUTPUT_DIR / f"{run_name}.gif"

    with writer.saving(fig, out_path, dpi=80):
        for i in range(len(frame_paths)):
            draw(i)
            writer.grab_frame()

    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
