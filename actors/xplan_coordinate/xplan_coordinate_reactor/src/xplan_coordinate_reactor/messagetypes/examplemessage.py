from ..jobs import launch_job
from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict
from xplan_utils.helpers import persist


class ExampleMessage(AbacoMessage):

    JOB_SPEC = AttrDict({
        "app_id": "jladwig-test-app-0.0.1",
        "base_name": "job-jladwig-test-app-",
        "max_run_time": "00:30:00",
        "inputs": [
            "path",
            "payload"
        ]
    })

    def process_message(self, r, work_dir, out_dir):
        msg = getattr(self, 'body')
        input_path = msg.get('path')
        input_payload = msg.get('payload')
        r.logger.info(
            "Process example message Path: {} Payload: {}".format(
                input_path, input_payload))

        job_id = launch_job(r, msg, self.JOB_SPEC, out_dir)
        if (job_id is None):
            r.logger.error("Failed to launch job.")
            return None

        r.logger.info("Launched job {} in {} usec".format(
            job_id, r.elapsed()))
        return job_id

    def finalize_message(self, r):
        r.logger.info("Finalize example message")


class ExampleMessageError(AbacoMessageError):
    pass
