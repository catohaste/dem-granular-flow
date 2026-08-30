# dem-granular-flow
DEM simulations of granular flow, exploring how particle size affects jamming. Built for a public outreach demo.

## Running simulations (YADE via Docker)
[YADE](https://yade-dem.org/) has no native macOS build, so simulations run
inside its official Linux Docker image.

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
   and launch it once to finish its first-run setup.
2. From the repo root, run a script in `scripts/`

```
docker run --rm -v "$PWD/scripts:/scripts" -v "$PWD/output:/output" \
       registry.gitlab.com/yade-dev/docker-prod:ubuntu22.04 \
       yade -n -x /scripts/granular_jamming.py
```

`scripts/granular_jamming.py` drops a cloud of spheres into a box under
gravity so you can explore how particle size/spread affects jamming. Each run
writes to several files to the `output/` folder
- `packing_<run_name>.txt` - packing fraction vs. iteration
- `frames/<run_name>/frame_*.txt` — per-particle x/y/z/radius snapshots
- `summary.csv` — one row per run (particle size + final packing fraction)

Set `RUN_NAME`, `R_MEAN`, `R_REL_FUZZ`, or `NUM_PARTICLES` env vars to compare
particle sizes, e.g. a finer pack:

```
    docker run --rm -e RUN_NAME=fine -e R_MEAN=0.003 -e R_REL_FUZZ=0.1 \
        -v "$PWD/scripts:/scripts" -v "$PWD/output:/output" \
        registry.gitlab.com/yade-dev/docker-prod:ubuntu22.04 \
        yade -n -x /scripts/granular_jamming.py
```

On Apple Silicon you'll see a `platform (linux/amd64) does not match ...`
warning. YADE has no arm64 image, so Docker runs it emulated (works fine,
just slower). Add `--platform linux/amd64` after `docker run --rm` to silence
the warning: it doesn't change performance.

## Analyzing results (local venv)
The venv is only used for post-processing/plotting outside the container.

    python3.13 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

    python analysis/plot_packing.py <run_name>     # packing fraction vs. time
    python analysis/make_gif.py <run_name>         # animated GIF of the run
    python analysis/compare_packing.py             # packing density vs. particle size,
                                                   # across all rows in output/summary.csv