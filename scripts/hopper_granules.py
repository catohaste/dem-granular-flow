# -*- coding: utf-8 -*-
"""
Granular flow under gravity into a hopper: spheres poured into a funnel-shaped hopper and drained through a narrow aperture, falling out of frame below it. Adapted from cube_granules.py (same headless/env-var/Docker conventions) but with the box geometry swapped for a converging hopper, adapted from the `clump-hopper-viscoelastic` example in the YADE documentation.

The hopper walls are built from N_SIDES flat trapezoidal facets arranged in
a ring (a "prism frustum"), rather than the 4 flat walls of a square funnel.
With N_SIDES=6 the aperture is a hexagon, which is a closer approximation to
a circular orifice than a square one -- useful because most hopper-flow
theory (e.g. the Beverloo correlation) assumes a circular or near-circular
outlet.

Run inside the official YADE Docker image (YADE has no native macOS build):
    docker run --rm -v "$PWD/scripts:/scripts" -v "$PWD/output:/output" \
        registry.gitlab.com/yade-dev/docker-prod:ubuntu22.04 \
        yade -n -x /scripts/hopper_granules.py

Each run simulates a fixed SIM_DURATION (default 1 simulated second, overridable
via env var) regardless of whether the flow finishes discharging or jams, so
runs with different particle sizes/counts are directly comparable. Each run
writes per-frame particle snapshots (for GIF rendering), a
discharged-particle-count time series, and an appended row to
output/hopper_summary.csv.
"""

import csv
import math
import os

from yade import pack, plot

# --- Geometry parameters (all overridable via env vars, like cube_granules.py) ---
N_SIDES = int(os.environ.get("N_SIDES", 6))  # 6 = hexagonal aperture
TOP_DIAMETER = float(os.environ.get("TOP_DIAMETER", 0.1))  # width of the wide top opening, matches cube_granules.py's BOX_SIZE
APERTURE_DIAMETER = float(os.environ.get("APERTURE_DIAMETER", 0.05))  # width of the narrow bottom opening
HOPPER_HEIGHT = float(os.environ.get("HOPPER_HEIGHT", 0.08))  # vertical drop from top opening to aperture

# ring_vertices() below works in circumradii (center to vertex), so halve the diameters once here
TOP_RADIUS = TOP_DIAMETER / 2
APERTURE_RADIUS = APERTURE_DIAMETER / 2

NUM_PARTICLES = int(os.environ.get("NUM_PARTICLES", 500))
R_MEAN = float(os.environ.get("R_MEAN", 0.003))  # mean sphere radius, meters
R_REL_FUZZ = float(os.environ.get("R_REL_FUZZ", 0.3))  # relative size spread
RUN_NAME = os.environ.get("RUN_NAME", "_default")
SIM_DURATION = float(os.environ.get("SIM_DURATION", 1.0))  # simulated seconds; fixed so runs are directly comparable
MAX_ITER = int(os.environ.get("MAX_ITER", 2000000))  # hard safety cap in case SIM_DURATION/dt is unexpectedly large
JAM_TIMEOUT = float(os.environ.get("JAM_TIMEOUT", 2.0))  # sim seconds with no new discharge = considered jammed

OUTPUT_DIR = "/output"
FRAMES_DIR = os.path.join(OUTPUT_DIR, "frames", "_hopper" + RUN_NAME)
os.makedirs(FRAMES_DIR, exist_ok=True)

# Vertical coordinates: aperture sits at z=0, the wide opening is above it;
# there's nothing below the aperture, so discharged spheres fall indefinitely.
Z_APERTURE = 0.0
Z_TOP = Z_APERTURE + HOPPER_HEIGHT

# facets use plain friction contact; spheres get their own material too, so
# each Ip2/Law2 pairing below only ever sees FrictMat-FrictMat interactions
facetMat = O.materials.append(FrictMat(frictionAngle=radians(35)))
sphereMat = O.materials.append(FrictMat(frictionAngle=radians(35), density=2700))

# Alternative: linear viscoelastic contact (matches a target collision time
# and restitution coefficient instead of relying on NewtonIntegrator damping).
# Swap in these two lines instead of the FrictMat ones above, and swap the
# Ip2/Law2 pair in O.engines below (see comments there) to match.
# tc, en, et = 0.001, 0.3, 0.3
# facetMat = O.materials.append(ViscElMat(frictionAngle=radians(35), tc=tc, en=en, et=et))
# sphereMat = O.materials.append(ViscElMat(frictionAngle=radians(35), tc=tc, en=en, et=et, density=2700))


def ring_vertices(radius, z):
    # N_SIDES points evenly spaced around a circle of given radius, at height z
    return [
        Vector3(radius * math.cos(2 * math.pi * i / N_SIDES), radius * math.sin(2 * math.pi * i / N_SIDES), z)
        for i in range(N_SIDES)
    ]


bottom_ring = ring_vertices(APERTURE_RADIUS, Z_APERTURE)
top_ring = ring_vertices(TOP_RADIUS, Z_TOP)

# Build the funnel one trapezoidal wall at a time: each wall connects one
# edge of the bottom ring to the corresponding edge of the top ring. This is
# the same approach as the 4-wall square funnel, just repeated N_SIDES times
# instead of hardcoding 4 quads.
for i in range(N_SIDES):
    j = (i + 1) % N_SIDES
    wall = pack.sweptPolylines2gtsSurface(
        [[bottom_ring[i], top_ring[i], top_ring[j], bottom_ring[j]]], capStart=True, capEnd=True
    )
    O.bodies.append(pack.gtsSurface2Facets(wall, material=facetMat, color=(0, 1, 0)))

# Fill the hopper from above the wide opening, using a square spawn
# footprint. A square of half-width `fill_half` has its *corners* at
# fill_half * sqrt(2), so we divide by sqrt(2) to keep those corners inside
# the hexagon's apothem (its inscribed circle) -- otherwise corner spheres
# spawn outside the top opening entirely and fall past the funnel walls.
apothem = TOP_RADIUS * math.cos(math.pi / N_SIDES)
fill_half = (apothem / math.sqrt(2)) * 0.85
fill_height = HOPPER_HEIGHT  # stack particles in a column as tall as the hopper itself

sp = pack.SpherePack()
sp.makeCloud(
    (-fill_half, -fill_half, Z_TOP + R_MEAN),
    (fill_half, fill_half, Z_TOP + R_MEAN + fill_height),
    rMean=R_MEAN,
    rRelFuzz=R_REL_FUZZ,
    num=NUM_PARTICLES,
)
sp.toSimulation(material=sphereMat)

# used by checkStopped() below to know when every sphere has discharged
TOTAL_SPHERES = sum(1 for b in O.bodies if isinstance(b.shape, Sphere))

O.engines = [
    ForceResetter(),
    InsertionSortCollider([Bo1_Sphere_Aabb(), Bo1_Facet_Aabb()]),
    InteractionLoop(
        [Ig2_Sphere_Sphere_ScGeom(), Ig2_Facet_Sphere_ScGeom()],
        [Ip2_FrictMat_FrictMat_FrictPhys()],
        [Law2_ScGeom_FrictPhys_CundallStrack()],
        # ViscElMat alternative: replace the two lines above with
        # [Ip2_ViscElMat_ViscElMat_ViscElPhys()],
        # [Law2_ScGeom_ViscElPhys_Basic()],
    ),
    NewtonIntegrator(gravity=(0, 0, -9.81), damping=0.4),
    PyRunner(command="checkStopped()", virtPeriod=0.05),
    PyRunner(command="track()", virtPeriod=0.01),
    PyRunner(command="snapshot()", virtPeriod=0.025),
]
O.dt = 0.5 * PWaveTimeStep()


def discharged_count():
    # spheres that have fallen through the aperture
    return sum(1 for b in O.bodies if isinstance(b.shape, Sphere) and b.state.pos[2] < Z_APERTURE)


# tracks the discharge count/time of the last new sphere to pass the aperture,
# so checkStopped() can log a stalled (jammed) flow
_progress = {"count": 0, "time": 0.0, "jam_logged": False, "done_logged": False}


# logs discharge completion/jamming for visibility, but doesn't stop the run
# early -- every run simulates the same SIM_DURATION so GIFs/results are
# directly comparable across particle sizes instead of some finishing early
def checkStopped():
    n = discharged_count()
    if n >= TOTAL_SPHERES:
        if not _progress["done_logged"]:
            print(f"All {TOTAL_SPHERES} spheres discharged by t={O.time:.3f}s")
            _progress["done_logged"] = True
        return
    if n > _progress["count"]:
        _progress["count"] = n
        _progress["time"] = O.time
    elif not _progress["jam_logged"] and O.time - _progress["time"] > JAM_TIMEOUT:
        print(f"Flow jammed: {n}/{TOTAL_SPHERES} discharged, no progress for {JAM_TIMEOUT}s")
        _progress["jam_logged"] = True


# collect history of data which will be saved to hopper_<run_name>.txt
def track():
    plot.addData(i=O.time, discharged=discharged_count())


def snapshot():
    # x y z r per sphere, one file per frame, for rendering a GIF later
    path = os.path.join(FRAMES_DIR, "t_%.4f.txt" % O.time)
    with open(path, "w") as f:
        for b in O.bodies:
            if isinstance(b.shape, Sphere):
                x, y, z = b.state.pos
                f.write("%.6f %.6f %.6f %.6f\n" % (x, y, z, b.shape.radius))


O.saveTmp()
# run for a fixed number of simulated seconds (capped by MAX_ITER as a hard safety valve)
n_iters = min(MAX_ITER, math.ceil(SIM_DURATION / O.dt))
O.run(n_iters, True)
# plot.saveDataTxt(os.path.join(OUTPUT_DIR, "hopper%s.txt" % RUN_NAME))

# Append this run's final discharge count for cross-run comparison
summary_path = os.path.join(OUTPUT_DIR, "hopper_summary.csv")
is_new = not os.path.exists(summary_path)
with open(summary_path, "a", newline="") as f:
    writer = csv.writer(f)
    if is_new:
        writer.writerow(
            ["run_name", "n_sides", "top_diameter", "aperture_diameter", "num_particles", "discharged", "jammed"]
        )
    final_discharged = discharged_count()
    writer.writerow(
        [RUN_NAME, N_SIDES, TOP_DIAMETER, APERTURE_DIAMETER, NUM_PARTICLES, final_discharged, final_discharged < TOTAL_SPHERES]
    )
