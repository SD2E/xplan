from ..files import download_file, upload_file
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

        out_dir = "out"

        # input_invocation = msg.get('invocation')
        # input_lab_configuration = msg.get('lab_configuration')
        # input_out_dir = msg.get('out_dir')
        archiveSystem = job.get("archiveSystem")
        archivePath = job.get("archivePath")

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
            challenge_out_dir = os.path.join(out_dir, challenge_problem)
        else:
            challenge_out_dir = os.path.join(
                out_dir, base_dir, challenge_problem)
        r.logger.info("challenge_problem = " + challenge_problem)

        # TODO adjust output of design app to always output to /out
        challenge_uri = "agave://{}/{}/{}".format(
            archiveSystem, archivePath, challenge_out_dir)

        r.logger.info("challenge_uri {}".format(challenge_uri))

        challenge_resp = download_file(r, challenge_uri)
        if not challenge_resp.ok:
            raise XPlanDesignMessageError("Failed to download challenge dir")
        r.logger.info("response {}".format(challenge_resp))
        r.logger.info("json {}".format(challenge_resp.json()))

class XPlanDesignMessageError(AbacoMessageError):
    pass
