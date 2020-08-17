#!/usr/bin/env python

from attrdict import AttrDict
from xplan_coordinate_reactor import typed_message_from_context
from reactors.runtime import Reactor
from xplan_utils import persist
import os

MOCK_STATE = AttrDict({"message_dict": {
    "path": "out",
    "payload": "Example payload"
}})


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

    # # TODO check the msg to see if a job completion
    job_completion_id = None

    if job_completion_id is not None:
        r.logger.debug("Processing completed job with id " + job_completion_id)
        # msg = typed_message_from_context(MOCK_STATE)
        # TODO remove job_id from state
        # TODO check if the job_completion_id is in the state
        # msg.finalize_message(r, out_dir)
    else:
        msg = typed_message_from_context(r.context)
        r.logger.debug("Processing message of type " + type(msg).__name__)
        msg.process_message(r, posix_work_dir, out_dir)


if __name__ == '__main__':
    main()
