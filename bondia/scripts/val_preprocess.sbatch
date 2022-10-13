#!/bin/bash
#SBATCH --account=rpp-chime
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1 # number of MPI processes
#SBATCH --cpus-per-task=6 # number of OpenMP processes
#SBATCH --mem=192000M # memory per node
#SBATCH --time=0-04:00:00
#SBATCH --job-name=chp/validation-preprocessing
#SBATCH --export=ALL

CHIME="/project/rpp-chime/chime"
PROCESSED="$CHIME"/chime_processed
ENV="$CHIME"/chime_env

module use "$ENV"/modules/modulefiles/
module load chime/python/2022.06

REVISION="${REVISION:-$(ls "$PROCESSED"/daily | tail -n 1)}"
# source "$PROCESSED"/daily/"$REVISION"/venv/bin/activate
source "$ENV"/daily_validation_preprocessing/.bondia_preprocess/venv/bin/activate

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

srun python "$ENV"/daily_validation_preprocessing/val_preprocess.py run &> "$PROCESSED"/validation_preprocess/jobout.log
