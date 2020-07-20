"""Functions for launch jobs"""
from attrdict import AttrDict
from reactors.runtime import Reactor, agaveutils
from requests.exceptions import HTTPError


def create_job_definition(r: Reactor, msg, job_spec):
    r.logger.info("Creating job from message: {}".format(msg))

    inputs = {}
    for i in job_spec.inputs:
        if i not in msg:
            r.logger.info("Input missing: {}".format(i))
        else:
            inputs[i] = msg.get(i)

    job_app_id = job_spec.app_id
    job_base_name = job_spec.base_name
    job_max_run_time = job_spec.max_run_time
    user_email = r.settings['xplan_config']['jobs']['email']

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

    if r.local is not True:
        job_def["notifications"].append({
            "event": "FINISHED",
            "persistent": True,
            "url": r.create_webhook(maxuses=1, actorId=r.uid) + "&id=${JOB_ID}"
        })
    else:
        r.logger.debug("Skipping webhook notification because we are in local mode")

    return job_def


def submit_job(r: Reactor, job_def):
    if (r.local):
        return "mock-job-id"
    return None

    # try:
    #     resp = r.client.jobs.submit(body=job_def)
    #     r.logger.debug("resp: {}".format(resp))
    #     if "id" in resp:
    #         return resp["id"]
    #     else:
    #         raise Exception("Response did not contain a job id")

    # except HTTPError as h:
    #     # Report what is likely to be an Agave-specific error
    #     raise Exception("Failed to submit job", h)

    # except Exception as exc:
    #     # Report what is likely to be an error with this Reactor, the Data
    #     # Catalog, or the PipelineJobs system components
    #     raise Exception("Failed to launch job {}".format(job_def["name"]), exc)

    # return None


def launch_job(r: Reactor, msg, job_spec):
    job_def = create_job_definition(r, msg, job_spec)
    r.logger.info('Job Def: {}'.format(job_def))
    return submit_job(r, job_def)
