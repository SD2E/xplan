#!/usr/bin/env python

from attrdict import AttrDict
from xplan_coordinate_reactor import typed_message_from_context, typed_message_from_dict, as_job_completion_message
from xplan_coordinate_reactor.jobs import deregister_job, num_jobs
from xplan_coordinate_reactor.logs import log_debug, log_info, log_error
from xplan_coordinate_reactor.messages import JobCompletionMessage
from reactors.runtime import Reactor
from xplan_utils import persist
import arrow
import os


def process_job_message(r: Reactor, job: JobCompletionMessage):
    job_id = job.get('id')
    status = job.get('status')

    if status == "FINISHED":
        log_debug(r, "Processing completed job with id " + job_id)
        job_data = deregister_job(r, job_id)
        if job_data is None:
            log_debug(r, 
                "Failed to find data associated with job id: " + job_id)
            return

        webhooks = job_data['webhooks']
        # deregister all webhooks
        if webhooks is not None:
            for key in webhooks:
                webhook = webhooks[key]
                log_info(r, "Deregister webhook: {}".format(webhook))
                r.delete_webhook(webhook)

        raw_msg = job_data['msg']
        if raw_msg is None:
            log_error(r, 
                "Failed to find message associated with job id: " + job_id)
            return

        process_data = job_data['data']
        msg = typed_message_from_dict(raw_msg)
        log_debug(r, "Finalizing message of type " + type(msg).__name__)
        msg.finalize_message(r, job, process_data)
    elif status == "BLOCKED":
        # TODO it seems that jobs will respond to FINISHED webhooks with BLOCKED events.
        # Catch that case here so I can debug if it happens again. It may require
        # that a fresh webhook be registered for the job that blocked.
        # For now do the same as any other unexpected status message...
        log_error(r, 
            "Received {} message for job {}.".format(status, job_id))
    else:
        # Similar to BLOCKED but just in case we get any other status
        log_error(r, 
            "Received {} message for job {}.".format(status, job_id))


def main():
    timestamp = arrow.utcnow().format('YYYY-MM-DD_hh-mm-ss')
    r = Reactor()
    job = as_job_completion_message(r.context)
    if job is not None:
        process_job_message(r, job)
    else:
        msg = typed_message_from_context(r.context)
        log_debug(r, "Processing message of type " + type(msg).__name__)
        msg.process_message(r, timestamp)


if __name__ == '__main__':
    main()
