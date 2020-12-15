"""Functions for launch jobs"""
from agavepy.actors import update_state
from attrdict import AttrDict
from .messagetypes import AbacoMessage
from reactors.runtime import Reactor, agaveutils
from requests.exceptions import HTTPError
from xplan_utils import persist
from .logs import log_debug, log_info, log_error


JOB_STATE = "jobs"


def get_state(r: Reactor):
    state = r.client.actors.getState(actorId=r.uid).get('state')
    log_info(r, "Raw state: {}".format(state))

    if not isinstance(state, dict):
        log_info(r, "Initializing state...")
        state = {}
    if JOB_STATE not in state:
        log_info(r, "Initializing job map...")
        state.update({JOB_STATE: {}})

    return state

def set_state(state):
    update_state(state)

def num_jobs(r :Reactor):
    state = get_state(r)
    job_map = state[JOB_STATE]
    return len(job_map)

def register_job(r :Reactor, job_id, data):
    state = get_state(r)
    # log_info(r, "Before register: {}".format(state))
    state[JOB_STATE].update({job_id: data})
    log_info(r, "After register: {}".format(state))
    set_state(state)

def deregister_job(r: Reactor, job_id):
    state = get_state(r)
    job_map = state[JOB_STATE]
    log_info(r, "Before deregister: {}".format(state))
    result = job_map.pop(job_id, None)
    log_info(r, "After deregister: {}".format(state))
    set_state(state)
    return result


def create_job_definition(r: Reactor, msg, job_spec):
    log_info(r, "Creating job from message: {}".format(msg))

    inputs = {}
    for i in job_spec.inputs:
        if i not in msg:
            log_info(r, "Input missing: {}".format(i))
        else:
            inputs[i] = msg.get(i)

    parameters = {}
    for i in job_spec.parameters:
        if i not in msg:
            log_info(r, "Parameter missing: {}".format(i))
        else:
            parameters[i] = msg.get(i)

    user_email = r.settings['xplan_config']['jobs']['email']

    webhooks = {}
    job_def = {
        "appId": job_spec.app_id,
        "name": job_spec.base_name + r.nickname,
        "inputs": inputs,
        "parameters": parameters,
        "batchQueue": job_spec.batchQueue,
        "maxRunTime": job_spec.max_run_time,
        "memoryPerNode": job_spec.memoryPerNode,
        "nodeCount": job_spec.nodeCount,
        "processorsPerNode": job_spec.processorsPerNode,
        "archive": job_spec.archive,
        "archivePath" : job_spec.archivePath,
        "archiveSystem" : job_spec.archiveSystem
    }
    if user_email is None:
        log_info(r, "No email notifications")
        job_def["notifications"] = []
    else:
        log_info(r, "User email for job notifications: {}".format(user_email))
        job_def["notifications"] = [
            {
                "event": "RUNNING",
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
        finished_webhook = r.create_webhook()
        job_def["notifications"].append({
            "event": "FINISHED",
            "persistent": True,
            "url": finished_webhook + "&id=${JOB_ID}"
        })
        webhooks['finished'] = finished_webhook
    else:
        log_debug(r, "Skipping webhook notification because we are in local mode")

    return (job_def, webhooks)


def submit_job(r: Reactor, job_def):
    if (r.local):
        return "mock-job-id"

    try:
        resp = r.client.jobs.submit(body=job_def)
        log_debug(r, "resp: {}".format(resp))
        if "id" in resp:
            return resp["id"]
        else:
            raise Exception("Response did not contain a job id")

    except HTTPError as h:
        # Report what is likely to be an Agave-specific error
        raise Exception("Failed to submit job", h)

    except Exception as exc:
        # Report what is likely to be an error with this Reactor, the Data
        # Catalog, or the PipelineJobs system components
        raise Exception("Failed to launch job {}".format(job_def["name"]), exc)

    return None


def launch_job(r: Reactor, msg :AbacoMessage, job_spec, data):
    (job_def, webhooks) = create_job_definition(r, msg, job_spec)
    log_info(r, 'Job Def: {}'.format(job_def))
    job_id = submit_job(r, job_def)
    if job_id is not None:
        register_job(r, job_id, {
            "msg": msg,
            "webhooks": webhooks,
            "data": data
        })
    return job_id
