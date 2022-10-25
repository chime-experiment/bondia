#!/bin/bash

set -x

CHIME="/project/rpp-chime/chime"
PROCESSED="$CHIME"/chime_processed
ENV="$CHIME"/chime_env

# REVISION="${REVISION:-$(ls "$PROCESSED"/daily | tail -n 1)}"
# source "$PROCESSED"/daily/"$REVISION"/venv/bin/activate

module use "$ENV"/modules/modulefiles/
module load chime/python/2022.06

source "$ENV"/daily_validation_preprocessing/.bondia_preprocess/venv/bin/activate
# Only submit if no slurm job already queued.
JOB_NAME="chp/validation"

# squeue -u $USER | grep $JOB_NAME
squeue -A rpp-chime_cpu | grep $JOB_NAME
if [ ${PIPESTATUS[1]} -eq 0 ]
then
  echo "There already is a slurm job with name $JOB_NAME"
  exit 1
fi

set -e
# Only submit if there are files waiting to be processed.
python "$ENV"/daily_validation_preprocessing/val_preprocess.py dryrun &> "$PROCESSED"/validation_preprocess/jobout.log

sbatch "$ENV"/daily_validation_preprocessing/val_preprocess.sbatch
