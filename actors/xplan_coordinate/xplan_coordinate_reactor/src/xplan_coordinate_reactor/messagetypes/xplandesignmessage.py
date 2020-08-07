from ..jobs import launch_job
from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict
from xplan_utils.helpers import persist


class XPlanDesignMessage(AbacoMessage):

    JOB_SPEC = AttrDict({
        "app_id": "xplan_design-0.0.1",
        "base_name": "xplan_design_job-",
        "max_run_time": "01:00:00",
        "inputs": [
            "invocation",
            "lab_configuration",
            "out_dir"
        ]
    })

    def process_message(self, r, in_dir, out_dir):
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

    def finalize_message(self, r):
        r.logger.info("Finalize example message")


class XPlanDesignMessageError(AbacoMessageError):
    pass
