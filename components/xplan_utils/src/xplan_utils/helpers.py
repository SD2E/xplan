import os
import pathlib
import stat
import json
import arrow
import numpy as np

from xplan_utils import persist
from xplan_design.experiment_design import ExperimentDesign
import xplan_utils.lab.strateos.utils as strateos

import logging

l = logging.getLogger(__file__)
l.setLevel(logging.INFO)

# drwxrws--x
STICKY_GROUP_RW = stat.S_IRWXU | stat.S_IRWXG | stat.S_ISGID | stat.S_IXOTH

raw_dtypes = {
    "input": str,
    "repliciate": int,
    "output": str
}




def get_run_data_file_name(experiment_id, batch_id):
    return "data_" + experiment_id + "_" + batch_id + ".csv"


def get_params_file_name(experiment_id, batch_id):
    return "params_" + experiment_id + "_" + batch_id + ".json"


def get_request_file_name(experiment_id):
    return "request_" + experiment_id + ".json"


def get_design_file_name(experiment_id):
    return "design_" + experiment_id + ".json"


def get_experiment_design(robj, experiment_id, out_dir):
    robj.logger.info("Getting Experiment Design ... " + experiment_id)
    state = persist.get_state(out_dir)

    if 'experiment_requests' not in state:
        raise Exception("Cannot retreive experiment design: " + str(experiment_id))
    if experiment_id not in state['experiment_requests']:
        raise Exception("Cannot retreive experiment design: " + str(experiment_id))

    design_file_name = get_design_file_name(experiment_id)
    experiment_dir = ensure_experiment_dir(experiment_id, out_dir)
    robj.logger.info("experiment_dir: " + experiment_dir)
    design_file_stash = os.path.join(experiment_dir, design_file_name)
    design = ExperimentDesign(**json.load(open(os.path.join(out_dir, design_file_stash))))
    robj.logger.info("Retrieved Experiment: " + experiment_id)
    return design


def get_experiment_request(robj, experiment_id, out_dir):
    robj.logger.info("Getting Experiment Request ... " + experiment_id)
    state = persist.get_state(out_dir)

    if 'experiment_requests' not in state:
        raise Exception("Cannot retreive experiment request: " + str(experiment_id))
    if experiment_id not in state['experiment_requests']:
        raise Exception("Cannot retreive experiment request: " + str(experiment_id))

    request_file_name = get_request_file_name(experiment_id)
    experiment_dir = ensure_experiment_dir(experiment_id, out_dir)
    robj.logger.info("experiment_dir: " + experiment_dir)
    request_file_stash = os.path.join(experiment_dir, request_file_name)
    request = json.load(open(os.path.join(out_dir, request_file_stash)))
    robj.logger.info("Retrieved Experiment: " + experiment_id)
    return request


def get_params_file_path(experiment_id, batch_id, out_dir):
    name = get_params_file_name(experiment_id, batch_id)
    experiment_dir = ensure_experiment_dir(experiment_id, out_dir)
    path = os.path.join(experiment_dir, name)
    return path

def do_convert_ftypes(factors):
    for factor_id, factor in factors.items():
        if factor_id == "strain" or factor_id == "replicate":
            factor['ftype'] = 'aliquot'
        elif factor_id == "timepoint" or factor_id == "measurement_type":
            factor['ftype'] = 'sample'

    return factors

def get_container_id(params_file_name):
    with open(params_file_name, 'r') as f:
        params_file = json.load(f)
        attr = None
        if 'src_info' in params_file['parameters']:
            attr = "src_info"
        elif "exp_info" in params_file['parameters']:
            attr = "exp_info"
        if attr:
            if 'src_samples' in params_file['parameters'][attr]:
                samples = params_file['parameters'][attr]['src_samples']
                ## Get the first container
                if len(samples) > 0:
                    container = samples[0]['containerId']
                    return container
                else:
                    raise Exception("Cannot find container for protocol with no src_samples")
        elif 'parameters' in params_file:
            return params_file['parameters']['exp_params']['source_plate']

        else:
            raise Exception("Don't know how to get container id from this params file: %s", params_file_name)


def put_aliquot_properties(experiment_id, aliquot_properties, out_dir):
    l.info("Saving Aliquot Properties Files ...")

    experiment_dir = ensure_experiment_dir(experiment_id, out_dir)
    for container_id, container_df in aliquot_properties.items():
        container_file_name = "container_{}.csv".format(container_id)
        container_file_stash = os.path.join(experiment_dir, container_file_name)
        l.info("Writing: %s", container_file_stash)
        container_df.to_csv(container_file_stash, index=False)


def put_experiment_submission(experiment_id, batch_id, submit_id, params_file_name, out_dir, xplan_config):
    l.info("Saving Experiment Submission Record ...")
    state = persist.get_state(out_dir)
    ## if robj.local is True:
    # persist.preview_dict(state)
    # session = robj.nickname
    ts = arrow.utcnow().timestamp
    my_submission = {'experiment_id': str(experiment_id),
                     'batch_id': batch_id,
                     'run': submit_id,
                     'params': params_file_name,
                     'created': ts,
                     'updated': ts}
    if 'experiment_submissions' in state:
        if experiment_id not in state['experiment_submissions']:
            state['experiment_submissions'][experiment_id] = {}
        state['experiment_submissions'][experiment_id][batch_id] = my_submission
    else:
        state['experiment_submissions'] = {experiment_id: {batch_id: my_submission}}

    if 'assigned_containers' not in state:
        state['assigned_containers'] = []
    container_id = get_container_id(params_file_name)
    state['assigned_containers'].append(container_id)

    if 'runs' not in state:
        state['runs'] = {submit_id: {"experiment_id": experiment_id, "batch_id": batch_id}}
    else:
        state['runs'][submit_id] = {"experiment_id": experiment_id, "batch_id": batch_id}

    new_state = persist.set_state(state, out_dir)
    # persist.save_state(robj, os.path.join(out_dir, robj.settings['xplan_config']['state_file']))
    l.info("Saved Experiment Submission Record ...")


def put_model(robj, model, out_dir):
    robj.logger.info("Saving Model ...")
    top_model_dir = os.path.join(out_dir, 'model')
    if not os.path.exists(top_model_dir):
        os.mkdir(top_model_dir)

    model_dir = os.path.join(out_dir, 'model', model['id'])
    if not os.path.exists(model_dir):
        os.mkdir(model_dir)
    model.serialize(model_dir)


def put_tx_parameters(experiment_id, batch_id, param, out_dir):
    # print(batch_id + " " + str(param))
    experiment_dir = ensure_experiment_dir(experiment_id, out_dir)
    params_file_name = get_params_file_name(experiment_id, batch_id)
    params_file_stash = os.path.join(experiment_dir, params_file_name)
    with open(params_file_stash, 'w') as f:
        f.write(param)


def ensure_dir_permissions(target_dir, permission=STICKY_GROUP_RW):
    try:
        l.info("Setting %s permissions ...", target_dir)
        os.chmod(target_dir, permission)
    except Exception:
        pass

def ensure_experiment_dir(experiment_id, out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    experiments_dir = os.path.join(out_dir, 'experiments')
    if not os.path.exists(experiments_dir):
        os.makedirs(experiments_dir)
        ensure_dir_permissions(experiments_dir)
    experiment_dir = os.path.join(experiments_dir, experiment_id)
    if not os.path.exists(experiment_dir):
        os.mkdir(experiment_dir)
        ensure_dir_permissions(experiment_dir)
    return experiment_dir


def put_experiment_request(experiment_request, out_dir):
    experiment_id = experiment_request['experiment_id']
    experiment_dir = ensure_experiment_dir(experiment_id, out_dir)

    request_file_name = get_request_file_name(experiment_id)
    request_file_stash = os.path.join(experiment_dir, request_file_name)
    l.info("request stash file: {}".format(request_file_stash))
    with open(request_file_stash, 'w') as f:
        l.info("Saving Experiment Request as: " + request_file_stash)
        f.write(json.dumps(experiment_request))


def put_experiment_design(experiment_design, out_dir):
    experiment_id = experiment_design['experiment_id']
    experiment_dir = ensure_experiment_dir(experiment_id, out_dir)

    request_file_name = get_design_file_name(experiment_id)
    request_file_stash = os.path.join(experiment_dir, request_file_name)
    l.info("design stash file: {}".format(request_file_stash))
    with open(request_file_stash, 'w') as f:
        l.info("Saving Experiment Design as: " + request_file_stash)
        f.write(json.dumps(experiment_design))

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.int64):
            return int(obj)
        else:
            return super(NpEncoder, self).default(obj)
