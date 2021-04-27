import click
import logging
import glob
import os
import sys

from pathlib import Path

from ch_pipeline.core import containers as ccontainers
from ch_pipeline.processing.base import slurm_jobs
from draco.core import containers

d = "/project/rpp-chime/chime/chime_processed/daily"
out_dir = "/project/rpp-chime/chime/chime_processed/validation_preprocess"
force = False

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def process(
    rev, lsd, path, name, file_name, file_out_name, container, tryrun=False, **kwargs
):
    in_file = glob.glob(os.path.join(path, file_name))
    if not in_file:
        logger.info(f"Found 0 {name} files in {path} (Expected 1).")
        return 0
    elif len(in_file) > 1:
        logger.info(f"Found {len(in_file)} {name} files in {path} (Expected 1).")
        sys.exit(1)

    in_file = in_file[0]

    lsd_from_filename = int(os.path.splitext(os.path.basename(in_file))[0][-4:])
    if lsd != lsd_from_filename:
        logger.error(
            f"Found file for LSD {lsd} when expecting LSD {lsd_from_filename}: {in_file}"
        )
        sys.exit(1)

    full_out_dir = os.path.join(out_dir, rev, str(lsd))

    if not tryrun:
        Path(full_out_dir).mkdir(parents=True, exist_ok=True)
    out_file = os.path.join(full_out_dir, f"{file_out_name}_{lsd}.h5")
    if os.path.isfile(out_file) and not force:
        logger.debug(
            f"Skipping {rev} {name} file for lsd {lsd}: {in_file}, outfile: {out_file}_{lsd}.h5"
        )
        return 0
    logger.info(
        f"Processing {rev} {name} file for lsd {lsd}: {in_file}, outfile: {out_file}_{lsd}.h5"
    )

    if not tryrun:
        rm = container.from_file(in_file, **kwargs)
        rm.to_disk(out_file)
    return 1


@click.command()
@click.option(
    "--tryrun/--notryrun",
    help="Just print number of files that would get processed.",
    default=False,
    show_default=True,
)
def run(tryrun):
    rev_dirs = glob.glob(os.path.join(d, "rev_*"))
    processed_total = 0
    for rev_dir in rev_dirs:
        if not os.path.isdir(rev_dir):
            logger.debug(f"Skipping {rev_dir} because it's not a (revision) directory.")
            continue
        rev = os.path.split(rev_dir)[-1]

        lsd_dirs = sorted(glob.glob(os.path.join(rev_dir, "*")))

        index = {}
        for lsd_dir in lsd_dirs:
            try:
                lsd = int(os.path.basename(lsd_dir))
            except ValueError as err:
                logger.debug(f"Skipping dir {lsd_dir}: {err}")
            else:
                if rev not in index:
                    index[rev] = {}
                if lsd in index[rev]:
                    logger.error(f"Tried to add {lsd} twice")
                    sys.exit(1)

                ringmap_freqs = slice(399, 477, 969)
                ringmap_pols = [0, 3]
                processed_total = processed_total + process(
                    rev,
                    lsd,
                    lsd_dir,
                    "ringmap",
                    "ringmap_lsd_*.h5",
                    f"ringmap_validation_freqs_lsd",
                    ccontainers.RingMap,
                    freq_sel=ringmap_freqs,
                    pol_sel=ringmap_pols,
                )
                processed_total = processed_total + process(
                    rev,
                    lsd,
                    lsd_dir,
                    "ringmap_intercyl",
                    "ringmap_intercyl_lsd_*.h5",
                    f"ringmap_intercyl_validation_freqs_lsd",
                    ccontainers.RingMap,
                    freq_sel=ringmap_freqs,
                    pol_sel=ringmap_pols,
                )
                processed_total = processed_total + process(
                    rev,
                    lsd,
                    lsd_dir,
                    "sensitivity",
                    "sensitivity_lsd_*.h5",
                    f"sensitivity_validation_lsd",
                    containers.SystemSensitivity,
                    pol_sel=[0, 2],
                )

        if tryrun:
            print(f"Would have processed {processed_total} files.")
            if processed_total == 0:
                sys.exit(1)
        else:
            print(f"Processed {processed_total} files.")


if __name__ == "__main__":
    run()
