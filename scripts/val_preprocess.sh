#!/bin/bash
source /project/rpp-krs/chime/chime_processed/daily/rev_02/venv/bin/activate

set -e
python /home/rickn/chime_pipeline/code/bondia/scripts/val_preprocess.py --tryrun &> /project/rpp-krs/chime/chime_processed/validation_preprocess/jobout.log

sbatch /home/rickn/chime_pipeline/code/bondia/scripts/val_preprocess.sbatch
