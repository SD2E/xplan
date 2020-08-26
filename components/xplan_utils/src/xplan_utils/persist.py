import arrow
from attrdict import AttrDict
import json
import os
import pathlib

import logging


l = logging.getLogger(__file__)
l.setLevel(logging.INFO)

def get_state(out_dir, recovery_file="state.json"):
    try:
        if recovery_file is not None:
            full_recovery_file = os.path.join(out_dir, recovery_file)
            if os.path.exists(full_recovery_file):
                data = open(full_recovery_file).read()
                # MAD 20190910 -- Default to empty object if state file is empty.
                if len(data) == 0:
                    data = "{}"
                state = AttrDict(json.loads(data))
            else:
                l.info("State file does not exist.")
                if not os.path.exists(out_dir):
                    os.makedirs(out_dir)
                state = AttrDict()
                with open(full_recovery_file, 'w') as f:
                    l.info("Creating new file.")
                    json.dump({}, f)
        return state
    except Exception as exc:
        raise exc


def set_state(state, out_dir, recovery_file="state.json"):
    try:
        #print(recovery_file)

        if recovery_file is not None:
            full_recovery_file = os.path.join(out_dir, recovery_file)
            l.info('Saving state to: {}'.format(full_recovery_file))
            #state = get_state(robj, recovery_file=dest)
            with open(full_recovery_file, 'w') as f:
                json.dump(state, f)
            return state
    except Exception as exc:
        raise exc


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

