import click
import logging
import sys

from pathlib import Path

from ch_pipeline.core import containers as ccontainers
from draco.core import containers

dir = "/project/rpp-chime/chime/chime_processed/daily"
out_dir = "/project/rpp-chime/chime/chime_processed/validation_preprocess"
force = False

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@click.command(help="Just print number of files that would get processed.")
def dryrun():
    total = list_files()
    print(f"Would have processed {total} files.")
    if total == 0:
        sys.exit(1)


@click.command()
@click.option(
    "--force/--noforce",
    help="Overwrite existing files.",
    default=False,
    show_default=True,
)
def run():
    todo_list = list_files()
    for d in todo_list:
        process(**d)
    print(f"Processed {len(todo_list)} files.")


def list_files():
    rev_dirs = Path(dir).glob("rev_*")
    todo_list = []
    for rev_dir in rev_dirs:
        if not rev_dir.is_dir():
            logger.debug(f"Skipping {rev_dir} because it's not a (revision) directory.")
            continue
        rev = rev_dir.parts[-1]

        lsd_dirs = sorted(rev_dir.glob("*"))

        index = {}
        for lsd_dir in lsd_dirs:
            try:
                lsd = int(lsd_dir.name)
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
                out = check_file(
                    rev,
                    lsd,
                    lsd_dir,
                    "ringmap",
                    "ringmap_lsd_*.h5",
                    "ringmap_validation_freqs_lsd",
                )
                if out is not None:
                    out.update(
                        {
                            "container": ccontainers.RingMap,
                            "freq_sel": ringmap_freqs,
                            "pol_sel": ringmap_pols,
                        }
                    )
                    todo_list.append(out)
                out = check_file(
                    rev,
                    lsd,
                    lsd_dir,
                    "ringmap_intercyl",
                    "ringmap_intercyl_lsd_*.h5",
                    "ringmap_intercyl_validation_freqs_lsd",
                )
                if out is not None:
                    out.update(
                        {
                            "container": ccontainers.RingMap,
                            "freq_sel": ringmap_freqs,
                            "pol_sel": ringmap_pols,
                        }
                    )
                    todo_list.append(out)
                out = check_file(
                    rev,
                    lsd,
                    lsd_dir,
                    "sensitivity",
                    "sensitivity_lsd_*.h5",
                    "sensitivity_validation_lsd",
                )
                if out is not None:
                    out.update(
                        {"container": containers.SystemSensitivity, "pol_sel": [0, 2]}
                    )
                    todo_list.append(out)
        return todo_list


def check_file(rev, lsd, path, name, file_name, file_out_name):
    in_file = path.glob(file_name)
    if not in_file:
        logger.info(f"Found 0 {name} files in {path} (Expected 1).")
        return None
    elif len(in_file) > 1:
        logger.info(f"Found {len(in_file)} {name} files in {path} (Expected 1).")
        sys.exit(1)

    in_file = in_file[0]

    lsd_from_filename = int(in_file.stem[-4:])
    if lsd != lsd_from_filename:
        logger.error(
            f"Found file for LSD {lsd} when expecting LSD {lsd_from_filename}: {in_file}"
        )
        sys.exit(1)

    full_out_dir = Path(out_dir) / rev / str(lsd)
    out_file = full_out_dir / f"{file_out_name}_{lsd}.h5"
    if out_file.is_file() and not force:
        logger.debug(
            f"Skipping {rev} {name} file for lsd {lsd}: {in_file}, outfile: {out_file}_{lsd}.h5"
        )
        return None
    logger.info(
        f"Processing {rev} {name} file for lsd {lsd}: {in_file}, outfile: {out_file}_{lsd}.h5"
    )
    return {"in_file": in_file, "full_out_dir": full_out_dir, "out_file": out_file}


def process(in_file, full_out_dir, out_file, container, **kwargs):
    Path(full_out_dir).mkdir(parents=True, exist_ok=True)
    rm = container.from_file(in_file, **kwargs)
    rm.to_disk(out_file)


if __name__ == "__main__":
    run()
