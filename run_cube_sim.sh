#!/bin/bash

set -e

IMAGE="registry.gitlab.com/yade-dev/docker-prod:ubuntu22.04"

export BOX_SIZE="0.1,0.1,0.1"

runs=(
    "_fine 0.003 700"
    "_medium 0.005 150"
    "_coarse 0.01 20"
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
        -e R_MEAN="$R_MEAN" \
        -e R_REL_FUZZ=0 \
        -e NUM_PARTICLES="$NUM_PARTICLES" \
        -e BOX_SIZE="$BOX_SIZE" \
        -v "$PWD/scripts:/scripts" \
        -v "$PWD/output:/output" \
        "$IMAGE" \
        yade -n -x /scripts/cube_granules.py

    python analysis/make_gif_cube.py $RUN_NAME
done

echo "All simulations completed."