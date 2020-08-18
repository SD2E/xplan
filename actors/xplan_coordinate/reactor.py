#!/usr/bin/env python

from attrdict import AttrDict
from xplan_coordinate_reactor import typed_message_from_context, typed_message_from_dict, as_job_completion_message
from xplan_coordinate_reactor.jobs import deregister_job, num_jobs
from reactors.runtime import Reactor
from xplan_utils import persist
import os


def main():
    r = Reactor()

    if r.local is True:
        r.logger.debug("Running locally")
        # TODO actually mount the inputs here
        posix_work_dir = '/mnt/xplan/work'
        out_dir = '/mnt/ephemeral-01'
    else:
        posix_work_dir = r.settings['xplan_config']['posix_work_dir']
        out_dir = r.settings['xplan_config']['out_dir']
        out_dir = os.path.join(posix_work_dir, out_dir)

    r.logger.debug("Using posix_work_dir: " + posix_work_dir)
    r.logger.debug("Using out_dir: " + out_dir)

    job = as_job_completion_message(r.context)
    if job is not None:
        job_id = job.get('id')
        r.logger.debug("Processing completed job with id " + job_id)
        raw_msg = deregister_job(r, job_id)
        if raw_msg is None:
            r.logger.debug("Failed to find message associated with job id: " + job_id)
        else:
            msg = typed_message_from_dict(raw_msg)
            r.logger.debug("Finalizing message of type " + type(msg).__name__)
            msg.finalize_message(r)
    else:
        msg = typed_message_from_context(r.context)
        r.logger.debug("Processing message of type " + type(msg).__name__)
        msg.process_message(r, posix_work_dir, out_dir)


if __name__ == '__main__':
    main()
