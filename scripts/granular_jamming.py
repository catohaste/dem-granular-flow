# -*- coding: utf-8 -*-
"""
Gravity deposition in a box: spheres settle under gravity. Adapted from 
Yade's own gravity_tutorial.py example, but running headlessly (no
interactive plot window) and configurable via environment variables.

Run inside the official YADE Docker image (YADE has no native macOS build):
    docker run --rm -v "$PWD/scripts:/scripts" -v "$PWD/output:/output" \
        registry.gitlab.com/yade-dev/docker-prod:ubuntu22.04 \
        yade -n -x /scripts/granular_jamming.py

-n runs headless (no GUI) and -x exits automatically once the script finishes,
rather than dropping into YADE's interactive console.

Particle size is configurable via environment variables so you can compare
runs, e.g.:
    docker run --rm -e RUN_NAME=fine -e R_MEAN=0.003 -e R_REL_FUZZ=0.1 \
        -v "$PWD/scripts:/scripts" -v "$PWD/output:/output" \
        registry.gitlab.com/yade-dev/docker-prod:ubuntu22.04 \
        yade -n -x /scripts/granular_jamming.py

Each run writes per-frame particle snapshots (for GIF rendering), a packing
fraction time series, and an appended row to output/summary.csv (for
comparing packing density across particle sizes).
"""

import csv
import math
import os

from yade import pack, plot

BOX_SIZE = tuple(map(float, os.environ["BOX_SIZE"].split(",")))
BOX_VOLUME = BOX_SIZE[0] * BOX_SIZE[1] * BOX_SIZE[2]
NUM_PARTICLES = int(os.environ.get("NUM_PARTICLES", 500))
R_MEAN = float(os.environ.get("R_MEAN", 0.005))  # mean sphere radius, meters
R_REL_FUZZ = float(os.environ.get("R_REL_FUZZ", 0.3))  # relative size spread
RUN_NAME = os.environ.get("RUN_NAME", "default")
MAX_ITER = int(os.environ.get("MAX_ITER", 200000))  # safety cap; usually stops earlier

OUTPUT_DIR = "/output"
FRAMES_DIR = os.path.join(OUTPUT_DIR, "frames", RUN_NAME)
os.makedirs(FRAMES_DIR, exist_ok=True)

BOX_CENTER = tuple(s / 2.0 for s in BOX_SIZE)
BOX_EXTENTS = tuple(s / 2.0 for s in BOX_SIZE)

# create rectangular box from facets; wallMask=31 omits the top (+z) facet
# so the pack has a free surface, instead of a sealed box
O.bodies.append(geom.facetBox(BOX_CENTER, BOX_EXTENTS, wallMask=31))

# create empty sphere packing
# sphere packing is not equivalent to particles in simulation, it contains only the pure geometry
sp = pack.SpherePack()
# generate randomly spheres with uniform radius distribution, filling the box
sp.makeCloud((0, 0, 0), BOX_SIZE, rMean=R_MEAN, rRelFuzz=R_REL_FUZZ, num=NUM_PARTICLES)
# add the sphere pack to the simulation
sp.toSimulation()

O.engines = [
    ForceResetter(),
    InsertionSortCollider([Bo1_Sphere_Aabb(), Bo1_Facet_Aabb()]),
    InteractionLoop(
        # handle sphere+sphere and facet+sphere collisions
        [Ig2_Sphere_Sphere_ScGeom(), Ig2_Facet_Sphere_ScGeom()],
        [Ip2_FrictMat_FrictMat_FrictPhys()],
        [Law2_ScGeom_FrictPhys_CundallStrack()],
    ),
    NewtonIntegrator(gravity=(0, 0, -9.81), damping=0.4),
    # call the checkUnbalanced function (defined below) every 2 seconds
    PyRunner(command="checkUnbalanced()", realPeriod=2),
    # call the track function every 0.01 seconds to record the packing fraction
    PyRunner(command="track()", virtPeriod=0.01),
    # call the snapshot function every 0.025 seconds to save a GIF frame
    PyRunner(command="snapshot()", virtPeriod=0.025),
]
O.dt = 0.5 * PWaveTimeStep()


def current_packing_fraction():
    # Fraction of the container's volume occupied by sphere centers that have
    # actually settled inside it (rises and plateaus once the pack jams).
    solid_volume = 0.0
    for b in O.bodies:
        if isinstance(b.shape, Sphere):
            x, y, z = b.state.pos
            if 0 <= x <= BOX_SIZE[0] and 0 <= y <= BOX_SIZE[1] and 0 <= z <= BOX_SIZE[2]:
                solid_volume += (4.0 / 3.0) * math.pi * b.shape.radius**3
    return solid_volume / BOX_VOLUME


# if the unbalanced forces goes below .05, the packing
# is considered stabilized, therefore we stop early instead
# of always running to MAX_ITER
def checkUnbalanced():
    if unbalancedForce() < 0.05:
        O.pause()


# collect history of data which will be saved to packing_<run_name>.txt
def track():
    plot.addData(i=O.time, packingFraction=current_packing_fraction())


def snapshot():
    # x y z r per sphere, one file per frame, for rendering a GIF later
    path = os.path.join(FRAMES_DIR, "t_%.4f.txt" % O.time)
    with open(path, "w") as f:
        for b in O.bodies:
            if isinstance(b.shape, Sphere):
                x, y, z = b.state.pos
                f.write("%.6f %.6f %.6f %.6f\n" % (x, y, z, b.shape.radius))


O.saveTmp()
O.run(MAX_ITER, True)
plot.saveDataTxt(os.path.join(OUTPUT_DIR, "packing%s.txt" % RUN_NAME))

# Append this run's final packing fraction for cross-run comparison
summary_path = os.path.join(OUTPUT_DIR, "summary.csv")
is_new = not os.path.exists(summary_path)
with open(summary_path, "a", newline="") as f:
    writer = csv.writer(f)
    if is_new:
        writer.writerow(["run_name", "r_mean", "r_rel_fuzz", "num_particles", "final_packing_fraction"])
    writer.writerow([RUN_NAME, R_MEAN, R_REL_FUZZ, NUM_PARTICLES, current_packing_fraction()])

