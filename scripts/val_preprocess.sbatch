#!/bin/bash
#SBATCH --account=rpp-chime
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1 # number of MPI processes
#SBATCH --cpus-per-task=1 # number of OpenMP processes
#SBATCH --mem=4G # memory per node
#SBATCH --time=0-04:00:00
#SBATCH --job-name=chp/validation-preprocessing

source /project/rpp-krs/chime/chime_processed/daily/rev_03/venv/bin/activate

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

srun python /project/rpp-chime/chime/chime_env/daily_validation_preprocessing/val_preprocess.py run &> /project/rpp-chime/chime/chime_processed/validation_preprocess/jobout.log
