#!/bin/bash

set -e

IMAGE="registry.gitlab.com/yade-dev/docker-prod:ubuntu22.04"

export TOP_DIAMETER="0.13"       # approx matches cube_granules.py's BOX_SIZE
export APERTURE_DIAMETER="0.05" # fixed aperture: chosen so fine/medium/coarse particle
                                 # sizes span no-jamming/jamming/no-jamming behavior
export HOPPER_HEIGHT="0.08"

export SIM_DURATION="1.5"

# name r_mean num_particles, same particle sizes/counts as run_cube_sim.sh
runs=(
    "_fine 0.003 370"
    "_medium 0.006 80"
    "_coarse 0.01 10"
)

for run in "${runs[@]}"; do
    read -r RUN_NAME R_MEAN NUM_PARTICLES <<< "$run"

    echo "========================================"
    echo "Running: $RUN_NAME"
    echo "R_MEAN:  $R_MEAN"
    echo "NUM_PARTICLES:  $NUM_PARTICLES"
    echo "========================================"

    docker run --rm \
        --platform linux/amd64 \
        -e RUN_NAME="$RUN_NAME" \
        -e APERTURE_DIAMETER="$APERTURE_DIAMETER" \
        -e R_MEAN="$R_MEAN" \
        -e R_REL_FUZZ=0 \
        -e NUM_PARTICLES="$NUM_PARTICLES" \
        -e TOP_DIAMETER="$TOP_DIAMETER" \
        -e HOPPER_HEIGHT="$HOPPER_HEIGHT" \
        -e SIM_DURATION="$SIM_DURATION" \
        -v "$PWD/scripts:/scripts" \
        -v "$PWD/output:/output" \
        "$IMAGE" \
        yade -n -x /scripts/hopper_granules.py

    python analysis/make_gif_hopper.py $RUN_NAME
done

echo "All simulations completed."
