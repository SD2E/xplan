import arrow
from attrdict import AttrDict
import json
import os
import pathlib

import logging


l = logging.getLogger(__file__)
l.setLevel(logging.INFO)

class ReactorsPersistError(Exception):
    pass


def get_state(recovery_file):
    try:
        if recovery_file is not None:
            if os.path.exists(recovery_file):
                data = open(recovery_file).read()
                # MAD 20190910 -- Default to empty object if state file is empty.
                if len(data) == 0:
                    data = "{}"
                state = AttrDict(json.loads(data))
            else:
                l.info("State file does not exist.")
                p = pathlib.Path(recovery_file)
                # Create the state directory if it does not exist already
                p.parent.mkdir(parents=True, exist_ok=True)
                state = AttrDict()
                recovery_dir = "/".join(recovery_file.split('/')[:-1])
                if not os.path.exists(recovery_dir):
                    os.makedirs(recovery_dir)
                with open(recovery_file, 'w') as f:
                    l.info("Creating new file.")
                    json.dump({}, f)
        return state
    except Exception as exc:
        raise ReactorsPersistError(exc)


def set_state(state, recovery_file):
    try:
        #print(recovery_file)

        if recovery_file is not None:
            l.info('Saving state to: {}'.format(recovery_file))
            #state = get_state(robj, recovery_file=dest)
            with open(recovery_file, 'w') as f:
                json.dump(state, f)
            return state
    except Exception as exc:
        raise ReactorsPersistError(exc)


def preview_dict(d, depth=0):
    # Generates a representation of a dict,
    # showing key names and classes in a
    # relative structure.
    for k, v in d.items():
        if isinstance(v, dict):
            spacer = "--" * depth
            print("{}{}: {}".format(spacer, k, type(v)))
            preview_dict(v, depth + 1)
        else:
            spacer = "--" * depth
            print("{}{}: {}".format(spacer, k, type(v)))


def new_empty_state():
    return {'reset': arrow.utcnow().timestamp}

