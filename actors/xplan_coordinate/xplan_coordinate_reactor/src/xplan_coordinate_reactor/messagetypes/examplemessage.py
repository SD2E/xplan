from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict
from ..jobs import launch_job
import json
import os
from ..files import upload_file


class ExampleMessage(AbacoMessage):

    JOB_SPEC = AttrDict({
        "app_id": "jladwig-test-app-0.0.1",
        "base_name": "job-jladwig-test-app-",
        "max_run_time": "00:30:00",
        "inputs": [
            "out_dir"
        ],
        "parameters": [
            "payload"
        ]
    })

    def process_message(self, r, work_dir, out_dir):
        msg = getattr(self, 'body')
        input_out_dir = msg.get('out_dir')
        input_payload = msg.get('payload')
        r.logger.info(
            "Process example message out_dir: {} payload: {}".format(
                input_out_dir, input_payload))

        job_id = launch_job(r, msg, self.JOB_SPEC, out_dir)
        if (job_id is None):
            r.logger.error("Failed to launch job.")
            return None

        r.logger.info("Launched job {} in {} usec".format(
            job_id, r.elapsed()))
        return job_id

    def finalize_message(self, r):
        msg = getattr(self, 'body')
        r.logger.info("Finalize example message: {}".format(msg))

        msg_out_dir = msg.get('out_dir')

        # write a test file to disk 
        data = {
            "data": "some example data"
        }
        filePath = "./example_out_file.json"

        r.logger.info("Writing file: %s", filePath)
        with open(filePath, 'w') as f:
            json.dump(data, f)

        r.logger.info("Uploading results to " + msg_out_dir)
        upload_file(r, "example_out_file.json", filePath, msg_out_dir)

        r.logger.info("Finished finalize")


class ExampleMessageError(AbacoMessageError):
    pass
