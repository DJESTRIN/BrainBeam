""" BrainBeamAPI
The purpose of this script is to allow users to interface with back-end software via a simple programming interface.
Designating --headless will trigger the API instead of the GUI.

Every pipeline stage can be run either directly on the local workstation
(computertype='local') or submitted to a SLURM cluster (computertype='slurm').
AWS execution (computertype='aws') is reserved for future use and is not
implemented yet; calling any stage with computertype='aws' raises
NotImplementedError.
"""
import glob
import os
import platform
import subprocess
import tarfile
import time

# Root of the BrainBeam repository (this file lives at <repo_root>/BrainBeam/gui/BrainBeamCLI.py)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BRAINBEAM_DIR = os.path.join(REPO_ROOT, 'BrainBeam')

VALID_COMPUTERTYPES = ('local', 'slurm', 'aws')


class PipelineError(RuntimeError):
    """ Raised when a pipeline stage script fails to run or exits with an error. """


class DigestData():
    def __init__(self):
        self.wd = os.getcwd()

    def directorytype(self, path):
        """ Classify a selected directory as containing a batch of samples ('batch'),
        a single sample ('single'), or neither ('neither'), following BrainBeam's
        `<project>/lightsheet/raw/<sample>` and `*Ex*` sample naming conventions. """
        if os.path.isdir(os.path.join(path, 'lightsheet', 'raw')):
            return 'batch'
        if 'ex' in os.path.basename(os.path.normpath(path)).lower():
            return 'single'
        return 'neither'

    def show_progress(self):
        pass


class API(DigestData):
    """ Programmatic interface into the BrainBeam pipeline stages. """

    def __init__(self, computertype='local'):
        super().__init__()
        self.set_computertype(computertype)

    def set_computertype(self, computertype):
        computertype = (computertype or 'local').strip().lower()
        if computertype not in VALID_COMPUTERTYPES:
            raise ValueError(f"computertype must be one of {VALID_COMPUTERTYPES}, got {computertype!r}")
        self.computertype = computertype

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _require_not_aws(self, action):
        if self.computertype == 'aws':
            raise NotImplementedError(
                f"AWS execution for '{action}' is not implemented yet. Please choose LOCAL or SLURM HPC.")

    def _run(self, command):
        """ Run a shell command, raising PipelineError on failure. Any command starting
        with 'sbatch' is expected to have been given --parsable (see call sites below),
        so its stdout is just the numeric SLURM job ID (optionally 'id;cluster') - this
        gets attached to the result as `.job_id` so callers can poll for real completion
        instead of treating "sbatch accepted the job" as "the pipeline stage finished". """
        shell_executable = None if platform.system() == 'Windows' else '/bin/bash'
        result = subprocess.run(command, shell=True, executable=shell_executable, capture_output=True, text=True)
        if result.returncode != 0:
            raise PipelineError(f"Command failed ({result.returncode}): {command}\n{result.stderr}")
        result.job_id = None
        if command.strip().startswith('sbatch'):
            first_line = (result.stdout or '').strip().splitlines()[0] if result.stdout.strip() else ''
            job_id_str = first_line.split(';')[0].strip()
            if job_id_str.isdigit():
                result.job_id = job_id_str
        return result

    def get_job_state(self, job_id):
        """ Best-effort SLURM job state lookup for `job_id`. Prefers `sacct` (gives a
        definitive terminal state like COMPLETED/FAILED once the job is done); falls
        back to `squeue` (only shows jobs still queued/running) if `sacct` is
        unavailable or returns nothing yet. Returns 'UNKNOWN' if neither command can
        tell us anything (e.g. sacct disabled and the job already left the queue) -
        callers must treat that as "can't confirm success", not as "failed". """
        sacct = subprocess.run(
            f'sacct -j {job_id} --format=State --noheader --parsable2',
            shell=True, capture_output=True, text=True)
        if sacct.returncode == 0 and sacct.stdout.strip():
            state = sacct.stdout.strip().splitlines()[0].strip()
            # sacct often reports sub-states like "CANCELLED by 12345" - keep the leading word
            return state.split()[0].rstrip('+') if state else 'UNKNOWN'
        squeue = subprocess.run(
            f'squeue -j {job_id} -h -o %T', shell=True, capture_output=True, text=True)
        if squeue.returncode == 0 and squeue.stdout.strip():
            return squeue.stdout.strip().splitlines()[0].strip()
        return 'UNKNOWN'

    SLURM_TERMINAL_STATES = {
        'COMPLETED': 'complete', 'FAILED': 'error', 'CANCELLED': 'error',
        'TIMEOUT': 'error', 'OUT_OF_MEMORY': 'error', 'NODE_FAIL': 'error',
        'UNKNOWN': 'unknown',
    }

    def wait_for_jobs(self, job_ids, poll_interval=15, timeout=None, on_poll=None, unknown_retries=2):
        """ Blocks (call this from a background thread, never the Tk main thread) until
        every job in `job_ids` reaches a terminal SLURM state, polling `get_job_state`
        every `poll_interval` seconds. `on_poll(states_dict)` is called after each poll
        so a caller can surface live status. Returns a {job_id: status} dict where
        status is one of 'complete', 'error', or 'unknown' (job left the queue but
        sacct couldn't confirm why - treat as needing manual log review, not a hard
        failure). `timeout` (seconds) gives up waiting (remaining jobs marked 'unknown')
        rather than blocking forever if the scheduler is unresponsive. A brand-new job
        may not show up in sacct/squeue yet on the very first poll, so an 'UNKNOWN'
        state is retried up to `unknown_retries` times before being treated as terminal,
        rather than immediately declaring the job "done, status unknown". """
        job_ids = [j for j in job_ids if j]
        pending = set(job_ids)
        final = {}
        unknown_counts = {job_id: 0 for job_id in job_ids}
        waited = 0
        while pending:
            for job_id in list(pending):
                state = self.get_job_state(job_id)
                if state in ('PENDING', 'RUNNING', 'CONFIGURING', 'COMPLETING', 'SUSPENDED'):
                    continue
                if state == 'UNKNOWN' and unknown_counts[job_id] < unknown_retries:
                    unknown_counts[job_id] += 1
                    continue
                final[job_id] = self.SLURM_TERMINAL_STATES.get(state, 'error')
                pending.discard(job_id)
            if on_poll:
                on_poll(dict(final))
            if not pending:
                break
            if timeout is not None and waited >= timeout:
                for job_id in pending:
                    final[job_id] = 'unknown'
                break
            time.sleep(poll_interval)
            waited += poll_interval
        return final

    def _script(self, *parts):
        path = os.path.join(BRAINBEAM_DIR, *parts)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Expected script not found: {path}")
        return path

    def _sbatch_flags(self, after_job_id=None):
        """ Common sbatch flags: --parsable (so _run can capture the job ID for
        polling) plus an optional --dependency=afterok so this job only starts
        once a prior stage's job has finished successfully - the building block
        for chaining multiple pipeline stages together unattended. """
        flags = '--parsable'
        if after_job_id:
            flags += f' --dependency=afterok:{after_job_id}'
        return flags

    def _find_samples(self, directory):
        """ Find per-sample sub-folders directly under `directory` (folders whose
        name contains 'ex', matching BrainBeam's sample naming convention, e.g. 'Ex1'). """
        if not os.path.isdir(directory):
            return []
        return sorted(
            entry for entry in glob.glob(os.path.join(directory, '*'))
            if os.path.isdir(entry) and 'ex' in os.path.basename(entry).lower()
        )

    # ------------------------------------------------------------------
    # Copy / Move / Compress / Decompress
    # ------------------------------------------------------------------
    def copy(self, input_dir, output_dir, after_job_id=None):
        """ Copy lightsheet raw data from input_dir into output_dir/lightsheet/raw/<sample>. """
        self._require_not_aws('copy')
        script = self._script('utils', 'copy.sh')
        command = f'bash "{script}" "{input_dir}" "{output_dir}"'
        if self.computertype == 'slurm':
            command = f'sbatch {self._sbatch_flags(after_job_id)} --job-name=gui_copy --mem=300G --partition=scu-cpu --wrap="{command}"'
        return self._run(command)

    def move(self, input_dir, output_dir, after_job_id=None):
        """ Move (rsync then delete source) a sample directory into output_dir/<sample_name>. """
        self._require_not_aws('move')
        script = self._script('utils', 'sendback.sh')
        sample_name = os.path.basename(os.path.normpath(input_dir))
        command = f'bash "{script}" "{input_dir}" "{sample_name}" "{output_dir}"'
        if self.computertype == 'slurm':
            command = f'sbatch {self._sbatch_flags(after_job_id)} --job-name=gui_move --mem=300G --partition=scu-cpu --wrap="{command}"'
        return self._run(command)

    def compress(self, input_dir, after_job_id=None):
        """ Compress every sub-directory of input_dir into a .tar.gz and remove the originals. """
        self._require_not_aws('compress')
        if self.computertype == 'slurm':
            script = self._script('utils', 'compress_dirs.sh')
            return self._run(f'sbatch {self._sbatch_flags(after_job_id)} "{script}" "{input_dir}"')
        script = self._script('utils', 'quick_zip.sh')
        return self._run(f'bash "{script}" "{input_dir}"')

    def decompress(self, input_dir, after_job_id=None):
        """ Decompress every .tar.gz directly inside input_dir and remove the archives. """
        self._require_not_aws('decompress')
        if self.computertype == 'slurm':
            script = self._script('utils', 'decompress_dirs.sh')
            return self._run(f'sbatch {self._sbatch_flags(after_job_id)} "{script}" "{input_dir}"')
        return self._local_decompress(input_dir)

    def _local_decompress(self, input_dir):
        archives = glob.glob(os.path.join(input_dir, '*.tar.gz'))
        if not archives:
            raise FileNotFoundError(f"No .tar.gz archives found directly inside {input_dir}")
        for archive in archives:
            with tarfile.open(archive, 'r:gz') as tar:
                tar.extractall(os.path.dirname(archive))
            os.remove(archive)
        return archives

    # ------------------------------------------------------------------
    # Denoise (PNG -> TIFF conversion + destriping)
    # ------------------------------------------------------------------
    def denoise(self, scratch_directory, store_finish_directory=None, after_job_id=None):
        """ Convert raw PNG stacks to TIFF, then remove striping artifacts.
        For SLURM, submits convert_tiff_spinup.sh, which automatically chains into
        destriping (and, further, stitching) once each stage completes.
        For LOCAL, each sample is converted then destriped directly, one at a time. """
        self._require_not_aws('denoise')
        store_finish_directory = store_finish_directory or scratch_directory
        if self.computertype == 'slurm':
            script = self._script('destripe', 'convert_tiff_spinup.sh')
            command = (f'sbatch {self._sbatch_flags(after_job_id)} --job-name=gui_denoise --mem=50G --partition=scu-cpu '
                       f'--wrap="bash \'{script}\' \'{BRAINBEAM_DIR}\' \'{scratch_directory}\' \'{store_finish_directory}\'"')
            return self._run(command)
        return self._denoise_local(scratch_directory)

    def _denoise_local(self, scratch_directory):
        convert_script = self._script('destripe', 'convert.sh')
        destripe_script = self._script('destripe', 'destripe.sh')
        results = []
        for sample_dir in self._find_samples(os.path.join(scratch_directory, 'lightsheet', 'raw')):
            results.append(self._run(f'bash "{convert_script}" "{BRAINBEAM_DIR}" "{sample_dir}"'))
        for sample_dir in self._find_samples(os.path.join(scratch_directory, 'lightsheet', 'converted')):
            results.append(self._run(f'bash "{destripe_script}" "{sample_dir}" "{scratch_directory}"'))
        return results

    # ------------------------------------------------------------------
    # Stitch
    # ------------------------------------------------------------------
    def stitch(self, scratch_directory, chain_next_stage=False, after_job_id=None):
        """ Stitch destriped tile images into a single volume per sample.
        chain_next_stage=True (SLURM only) lets the submitted job automatically
        continue on to whatever stage comes after stitching once it finishes. """
        self._require_not_aws('stitch')
        if self.computertype == 'slurm':
            script = self._script('stitch', 'stitch_spinup.sh')
            run_dependencies = 'true' if chain_next_stage else 'false'
            command = (f'sbatch {self._sbatch_flags(after_job_id)} --job-name=gui_stitch --mem=50G --partition=scu-cpu '
                       f'--wrap="bash \'{script}\' \'{BRAINBEAM_DIR}\' \'{scratch_directory}\' {run_dependencies}"')
            return self._run(command)
        script = self._script('stitch', 'stitch.sh')
        results = []
        for sample_dir in self._find_samples(os.path.join(scratch_directory, 'lightsheet', 'destriped')):
            results.append(self._run(f'bash "{script}" "{sample_dir}" "{scratch_directory}"'))
        return results

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register(self, image_path, output_path=None, atlas_path=None, parent_segmentation_path=None,
                 conda_environment_name=None, full_output_path=False,
                 force_orientation=None, force_flips=None, preview_only=False):
        """ Register lightsheet data to the reference atlas.
        LOCAL registers a single sample directly via runregistr.py.
        SLURM submits a batch of samples via multinoderegistration.py, which
        requires parent_segmentation_path and conda_environment_name.
        force_orientation/force_flips (each a list of 3 ints) let the caller
        override the automatically-detected brain orientation; preview_only=True
        (LOCAL only) generates the orientation-check GIFs and returns immediately,
        skipping the slow alignment step. """
        self._require_not_aws('register')
        if self.computertype == 'slurm':
            if not parent_segmentation_path:
                raise ValueError("parent_segmentation_path is required for SLURM batch registration")
            if not conda_environment_name:
                raise ValueError("conda_environment_name is required for SLURM batch registration")
            script = self._script('registration', 'multinoderegistration.py')
            command = (f'python "{script}" --parent_image_path "{image_path}" '
                       f'--parent_segmentation_path "{parent_segmentation_path}" '
                       f'--conda_environment_name "{conda_environment_name}"')
            if output_path:
                command += f' --parent_registration_output_path "{output_path}"'
            return self._run(command)
        script = self._script('registration', 'runregistr.py')
        command = f'python "{script}" --image_path "{image_path}" --output_path "{output_path}"'
        if atlas_path:
            command += f' --atlas_path "{atlas_path}"'
        if full_output_path:
            command += ' --full_output_path'
        if force_orientation:
            command += ' --force_orientation ' + ' '.join(str(int(v)) for v in force_orientation)
        if force_flips:
            command += ' --force_flips ' + ' '.join(str(int(v)) for v in force_flips)
        if preview_only:
            command += ' --preview_only'
        return self._run(command)

    # ------------------------------------------------------------------
    # Segmentation
    # ------------------------------------------------------------------
    def segment(self, scratch_directory, ilastik_project_file=None, after_job_id=None):
        """ Split stitched volumes into cubes, run the ilastik pixel classifier,
        parse its output, and concatenate per-cube cell counts into a single CSV.

        On SLURM, these 4 steps have a strict order dependency (e.g. ilastik must
        not start before cube splitting finishes) - each step is submitted with
        --dependency=afterok on the previous step's job id so they run in the
        correct order automatically instead of all firing at once. """
        self._require_not_aws('segment')
        ilastik_dir = os.path.join(scratch_directory, 'lightsheet', 'ilastik')
        if self.computertype == 'slurm':
            steps = [
                ('split_cubes_spinup.sh', [BRAINBEAM_DIR, scratch_directory]),
                ('headless_spinup.sh', [BRAINBEAM_DIR, ilastik_dir]),
                ('parse_ilastik_output_spinup.sh', [BRAINBEAM_DIR, ilastik_dir]),
                ('concat_csv_spinup.sh', [BRAINBEAM_DIR, ilastik_dir]),
            ]
            results = []
            previous_job_id = after_job_id
            for script_name, args in steps:
                script = self._script('segmentation', script_name)
                quoted_args = " ".join(f"'{arg}'" for arg in args)
                result = self._run(
                    f'sbatch {self._sbatch_flags(previous_job_id)} --job-name=gui_segment --mem=100G --partition=scu-cpu '
                    f'--wrap="bash \'{script}\' {quoted_args}"')
                results.append(result)
                previous_job_id = getattr(result, 'job_id', None)
            return results

        if not ilastik_project_file:
            raise ValueError("ilastik_project_file is required for local segmentation")
        results = []
        split_cubes_script = self._script('segmentation', 'split_cubes.sh')
        for sample_dir in self._find_samples(os.path.join(scratch_directory, 'lightsheet', 'stitched')):
            results.append(self._run(f'bash "{split_cubes_script}" "{BRAINBEAM_DIR}" "{sample_dir}" "{scratch_directory}"'))

        headless_script = self._script('segmentation', 'headless_ilastik.sh')
        results.append(self._run(f'bash "{headless_script}" "{ilastik_project_file}" "{ilastik_dir}"'))

        parse_script = self._script('segmentation', 'parse_ilastik_output.sh')
        results.append(self._run(f'bash "{parse_script}" "{BRAINBEAM_DIR}" "{ilastik_dir}"'))

        concat_script = self._script('segmentation', 'concat_csv.py')
        results.append(self._run(f'python "{concat_script}" --input_dir "{ilastik_dir}"'))
        return results

    # ------------------------------------------------------------------
    # Custom script
    # ------------------------------------------------------------------
    def custom(self, script_path, target_path):
        """ Run a user-supplied python script against a single sample or batch of samples. """
        self._require_not_aws('custom')
        if not os.path.isfile(script_path):
            raise FileNotFoundError(f"Custom script not found: {script_path}")
        command = f'python "{script_path}" --input_path "{target_path}"'
        if self.computertype == 'slurm':
            command = f'sbatch --job-name=gui_custom --mem=100G --partition=scu-cpu --wrap="{command}"'
        return self._run(command)
