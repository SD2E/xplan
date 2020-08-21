from ..jobs import launch_job
from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict
from reactors.runtime import Reactor, agaveutils
from .jobcompletionmessage import JobCompletionMessage


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

        # input_invocation = msg.get('invocation')
        # input_lab_configuration = msg.get('lab_configuration')
        # input_out_dir = msg.get('out_dir')
        archiveSystem = job.get("archiveSystem")
        archivePath = job.get("archivePath")
        r.logger.info("xplan design archived at agave://{}/{}".format(archiveSystem, archivePath))



class XPlanDesignMessageError(AbacoMessageError):
    pass
