#!/usr/bin/env python

from attrdict import AttrDict
from xplan_coordinate_reactor import typed_message_from_context, typed_message_from_dict, as_job_completion_message
from xplan_coordinate_reactor.jobs import deregister_job, num_jobs
from xplan_coordinate_reactor.messages import JobCompletionMessage
from reactors.runtime import Reactor
from xplan_utils import persist
import os


def process_job_message(r: Reactor, job: JobCompletionMessage):
    job_id = job.get('id')
    status = job.get('status')

    if status == "FINISHED":
        r.logger.debug("Processing completed job with id " + job_id)
        job_data = deregister_job(r, job_id)
        if job_data is None:
            r.logger.debug(
                "Failed to find data associated with job id: " + job_id)
            return

        webhooks = job_data['webhooks']
        # deregister all webhooks
        if webhooks is not None:
            for key in webhooks:
                webhook = webhooks[key]
                r.logger.info("Deregister webhook: {}".format(webhook))
                r.delete_webhook(webhook)

        raw_msg = job_data['msg']
        if raw_msg is None:
            r.logger.error(
                "Failed to find message associated with job id: " + job_id)
            return

        msg = typed_message_from_dict(raw_msg)
        r.logger.debug("Finalizing message of type " + type(msg).__name__)
        msg.finalize_message(r, job)
    elif status == "BLOCKED":
        # TODO it seems that jobs will respond to FINISHED webhooks with BLOCKED events.
        # Catch that case here so I can debug if it happens again. It may require
        # that a fresh webhook be registered for the job that blocked.
        # For now do the same as any other unexpected status message...
        r.logger.error(
            "Received {} message for job {}.".format(status, job_id))
    else:
        # Similar to BLOCKED but just in case we get any other status
        r.logger.error(
            "Received {} message for job {}.".format(status, job_id))


def main():
    r = Reactor()
    job = as_job_completion_message(r.context)
    if job is not None:
        process_job_message(r, job)
    else:
        msg = typed_message_from_context(r.context)
        r.logger.debug("Processing message of type " + type(msg).__name__)
        msg.process_message(r)


if __name__ == '__main__':
    main()
