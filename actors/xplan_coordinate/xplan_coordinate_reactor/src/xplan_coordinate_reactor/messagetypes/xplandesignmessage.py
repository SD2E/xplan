from ..files import download_file, download_dir, upload_dir, split_agave_uri, make_agave_uri
from ..jobs import launch_job
from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict
from reactors.runtime import Reactor, agaveutils
from .jobcompletionmessage import JobCompletionMessage
from xplan_utils.helpers import ensure_experiment_dir
import os


class XPlanDesignMessage(AbacoMessage):

    JOB_SPEC = AttrDict({
        "app_id": "jladwig_xplan_design-0.0.1",
        "base_name": "jladwig_xplan_design_job-",
        "batchQueue": "all",
        "max_run_time": "01:00:00",
        "memoryPerNode": "1GB",
        "nodeCount": 1,
        "processorsPerNode": 1,
        "archive": True,
        "inputs": [
            "invocation",
            "lab_configuration",
            "out_dir"
        ],
        "parameters": []
    })

    def process_message(self, r: Reactor):
        msg = getattr(self, 'body')
        input_invocation = msg.get('invocation')
        input_lab_configuration = msg.get('lab_configuration')
        input_out_dir = msg.get('out_dir')
        r.logger.info(
            "Process xplan design message \n  Invocation: {}\n  Lab Configuration: {}\n  OutDir: {}"
            .format(input_invocation, input_lab_configuration, input_out_dir))

        job_id = launch_job(r, msg, self.JOB_SPEC)
        if (job_id is None):
            r.logger.error("Failed to launch job.")
            return None

        r.logger.info("Launched job {} in {} usec".format(
            job_id, r.elapsed()))
        return job_id

    def finalize_message(self, r: Reactor, job: JobCompletionMessage):
        msg = getattr(self, 'body')
        r.logger.info("Finalize xplan design message: {}".format(msg))

        # TODO adjust output of design app to always output to /out
        # This assumes the design app mounts the out_dir agave path as 
        # just the basename of the given out_dir path
        out_uri = msg.get('out_dir')
        upload_system, out_path = split_agave_uri(out_uri)
        out_basename = os.path.basename(out_path.rstrip('/'))

        archive_system = job.get("archiveSystem")
        archive_path = job.get("archivePath")

        invocation_uri = msg.get('invocation')
        invocation_resp = download_file(r, invocation_uri)
        if not invocation_resp.ok:
            raise XPlanDesignMessageError("Failed to download invocation file")
        invocation = invocation_resp.json()

        # TODO move this to the helper so it only needs to be changed
        # in one place if edited need to be made (see design.py)
        base_dir = invocation.get('base_dir', ".")
        challenge_problem = invocation.get('challenge_problem')

        if base_dir == ".":
            archive_out_dir = os.path.join(archive_path, out_basename, challenge_problem)
            upload_out_dir = os.path.join(out_path, challenge_problem)
        else:
            archive_out_dir = os.path.join(archive_path, out_basename, base_dir, challenge_problem)
            upload_out_dir = os.path.join(out_path, base_dir, challenge_problem)

        r.logger.info("challenge_problem = " + challenge_problem)

        archive_uri = make_agave_uri(archive_system, archive_out_dir)
        r.logger.info("archive_uri = {}".format(archive_uri))

        upload_uri = make_agave_uri(upload_system, upload_out_dir)
        r.logger.info("upload_uri = {}".format(upload_uri))

        local_out = os.path.abspath(out_basename)
        download_dir(r, archive_uri, local_out)
        r.logger.info("Download:\n  to: {}\n  from: {}".format(local_out, archive_uri))

        upload_dir(r, local_out, upload_uri)
        r.logger.info("Upload:\n  from: {}\n  to: {}".format(local_out, upload_uri))

class XPlanDesignMessageError(AbacoMessageError):
    pass
