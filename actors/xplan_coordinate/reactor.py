#!/usr/bin/env python

from attrdict import AttrDict
from xplan_coordinate_reactor import typed_message_from_context, typed_message_from_dict, as_job_completion_message
from xplan_coordinate_reactor.jobs import deregister_job, num_jobs
from reactors.runtime import Reactor
from xplan_utils import persist
import os


def main():
    r = Reactor()
    job = as_job_completion_message(r.context)
    if job is not None:
        job_id = job.get('id')
        r.logger.debug("Processing completed job with id " + job_id)
        raw_msg = deregister_job(r, job_id)
        if raw_msg is None:
            r.logger.debug(
                "Failed to find message associated with job id: " + job_id)
        else:
            msg = typed_message_from_dict(raw_msg)
            r.logger.debug("Finalizing message of type " + type(msg).__name__)
            msg.finalize_message(r, job)
    else:
        msg = typed_message_from_context(r.context)
        r.logger.debug("Processing message of type " + type(msg).__name__)
        msg.process_message(r)


if __name__ == '__main__':
    main()
