#!/bin/bash
source /project/rpp-chime/chime/chime_processed/daily/rev_03/venv/bin/activate

# Only submit if no slurm job already queued.
JOB_NAME="chp/validation"
squeue -u $USER | grep $JOB_NAME
if [ ${PIPESTATUS[1]} -eq 0 ]
then
  echo "There already is a slurm job with name $JOB_NAME"
  exit 1
fi

# Only submit if there are files waiting to be processed.
set -e
python /project/rpp-chime/chime/chime_env/daily_validation_preprocessing/val_preprocess.py tryrun &> /project/rpp-chime/chime/chime_processed/validation_preprocess/jobout.log

sbatch /project/rpp-chime/chime/chime_env/daily_validation_preprocessing/val_preprocess.sbatch
