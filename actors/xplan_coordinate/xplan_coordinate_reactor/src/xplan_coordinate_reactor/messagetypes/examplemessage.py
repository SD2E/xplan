from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict
from ..jobs import launch_job
import json
import os
from ..files import upload_file, download_file
from reactors.runtime import Reactor, agaveutils
from .jobcompletionmessage import JobCompletionMessage


class ExampleMessage(AbacoMessage):

    JOB_SPEC = AttrDict({
        "app_id": "jladwig-test-app-0.0.1",
        "base_name": "job-jladwig-test-app-",
        "batchQueue": "normal",
        "max_run_time": "00:30:00",
        "memoryPerNode": "1GB",
        "nodeCount": 1,
        "processorsPerNode": 1,
        "archive": False,
        "inputs": [
            "out_dir"
        ],
        "parameters": [
            "payload"
        ]
    })

    def process_message(self, r: Reactor):
        msg = getattr(self, 'body')
        input_out_dir = msg.get('out_dir')
        input_payload = msg.get('payload')
        r.logger.info(
            "Process example message out_dir: {} payload: {}".format(
                input_out_dir, input_payload))

        # test file download
        # downloadPath = os.path.join(input_out_dir, "download_file.txt")
        # download = download_file(r, downloadPath)
        # r.logger.info("Downloaded: {}".format(download.text))
        # if json
        # res = AttrDict(download.json())

        job_id = launch_job(r, msg, self.JOB_SPEC)
        if (job_id is None):
            r.logger.error("Failed to launch job.")
            return None

        r.logger.info("Launched job {} in {} usec".format(
            job_id, r.elapsed()))
        return job_id

    def finalize_message(self, r: Reactor, job: JobCompletionMessage):
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
        upload_file(r, filePath, msg_out_dir, name="example_out_file.json")

        r.logger.info("Finished finalize")


class ExampleMessageError(AbacoMessageError):
    pass
