#!/usr/bin/env python

from agavepy.agave import Agave
from agavepy.actors import get_client
from reactors.runtime import Reactor, agaveutils
from requests.exceptions import HTTPError


def main():
    r = Reactor()

    m = r.context.message_dict
    r.logger.info("message: {}".format(m))
    r.logger.info("raw message: {}".format(r.context.raw_message))

    job_spec = r.settings.job_spec

    inputs = {}
    for i in job_spec.inputs:
        if i not in m:
            r.logger.info("Input missing: {}".format(i))
        else:
            inputs[i] = m.get(i)

    r.logger.info("Inputs: {}".format(inputs))

    job_app_id = job_spec.app_id
    job_base_name = job_spec.base_name
    job_max_run_time = job_spec.max_run_time
    user_email = job_spec.user_email

    job_def = {
        "appId": job_app_id,
        "name": job_base_name + r.nickname,
        "inputs": inputs,
        "maxRunTime": job_max_run_time,
    }
    job_def["archive"] = False
    job_def["notifications"] = [
        {
            "event": "PENDING",
            "persistent": True,
            "url": user_email
        },
        {
            "event": "FINISHED",
            "persistent": True,
            "url": user_email
        },
        {
            "event": "FAILED",
            "persistent": True,
            "url": user_email
        }
    ]

    # When the job finishes have it send a message to the sink actor and
    # provide the job id so that it can pull in any required data
    if "finished_sink_id" in job_spec:
        job_def["notifications"].append({
            "event": "FINISHED",
            "persistent": True,
            "url": r.create_webhook(maxuses=1, actorId=job_spec.finished_sink_id) + "&id=${JOB_ID}"
        })

    r.logger.info('Job Def: {}'.format(job_def))

    job_id = None
    try:
        resp = r.client.jobs.submit(body=job_def)
        r.logger.debug("resp: {}".format(resp))
        if "id" in resp:
            job_id = resp["id"]
        else:
            raise Exception("Response did not contain a job id")

    except HTTPError as h:
        # Report what is likely to be an Agave-specific error
        raise Exception("Failed to submit job", h)

    except Exception as exc:
        # Report what is likely to be an error with this Reactor, the Data
        # Catalog, or the PipelineJobs system components
        raise Exception("Failed to launch job {}".format(job_def["name"]), exc)

    r.on_success("Launched Agave job {} in {} usec".format(
        job_id, r.elapsed()))


if __name__ == '__main__':
    main()
