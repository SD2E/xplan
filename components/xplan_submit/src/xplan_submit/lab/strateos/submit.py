import json
import os
import time

import arrow
import pandas as pd
import requests
from tenacity import retry, stop_after_delay, wait_exponential

from xplan_utils.helpers import put_experiment_submission, put_experiment_design, get_params_file_name, \
    get_params_file_path, get_experiment_request, get_experiment_design
import logging

from xplan_utils.lab.strateos.utils import TranscripticApiError, get_transcriptic_api, TranscripticRunStatus

l = logging.getLogger(__file__)
l.setLevel(logging.INFO)

def  submit_experiment(experiment_id, challenge_problem,
                       tx_cfg, tx_params,
                       input_dir=".", out_dir=".", batches=None, mock=False, logger=l):
    l = logger
    challenge_in_dir = os.path.join(input_dir, challenge_problem)
    challenge_out_dir = os.path.join(out_dir, challenge_problem)
    experiment_out_dir = os.path.join(challenge_out_dir, 'experiments', experiment_id)
    experiment_design = get_experiment_design(experiment_id, challenge_in_dir)
    experiment_request = get_experiment_request(experiment_id, challenge_in_dir)

    experiment_id = experiment_request['experiment_id']
    base_dir = experiment_request.get('base_dir', ".")
    protocol_id = experiment_request['defaults']['protocol_id']

    if 'test_mode' in experiment_request['defaults']:
        test_mode = experiment_request['defaults']['test_mode']
    else:
        test_mode = False

    tx_test_mode = test_mode
    tx_proj_key = tx_params.get('default')
    tx_proj = tx_params.get('projects').get(tx_proj_key)
    tx_proj_id = tx_proj.get('id')

    design_df = pd.read_json(experiment_design['design'])

    if "batch" in design_df.columns:
        if "lab_id" in design_df.columns:
            ## only submit batches w/o a lab_id
            planned_batches = design_df.loc[design_df.lab_id.isna()].batch.unique()
        else:
            planned_batches = design_df.batch.unique()
    else:
        planned_batches = [b['id'] for b in batches]



    for batch in planned_batches:
        if batches is not None:
            if str(batch) not in batches:
                continue
        declared_protocol_name = next(iter(design_df.loc[design_df.batch == batch]['protocol'].unique()))
        (submit_id, params_file_name) = submit_plate(experiment_id,
                                                     str(batch),
                                                     challenge_problem,
                                                     challenge_in_dir,
                                                     experiment_out_dir,
                                                     mock,
                                                     tx_proj_id,
                                                     protocol_id,
                                                     tx_test_mode,
                                                     tx_cfg,
                                                     logger=l,
                                                     declared_protocol_name=declared_protocol_name)

        put_experiment_submission(experiment_id, str(batch), submit_id, params_file_name, challenge_out_dir)

        def assign_run_id(x):
            if str(x['batch']) == str(batch):
                return submit_id
            elif 'lab_id' in x:
                return x['lab_id']
            else:
                return None


        design_df['lab_id'] = design_df.apply(assign_run_id, axis=1)
    design_df['protocol_id'] = protocol_id
    experiment_design['design'] = design_df.to_json()
    put_experiment_design(experiment_design, challenge_out_dir)

    if test_mode:
        ## complete the experiment
        for batch in experiment_request['batches']:
            if batches is not None:
                if batch['id'] not in batches:
                    continue
            try:
                run_id = design_df.loc[design_df.batch.astype(str) == batch['id']]['lab_id'].unique()[0]
            except Exception as e:
                l.exception("Could not get run_id for batch: %s", batch['id'])
            complete_tx_test_run(tx_proj_id, run_id, tx_cfg)


def submit_plate(experiment_id, plate_id, challenge_problem, in_dir, out_dir,
                 tx_mock, tx_proj_id, tx_proto_id, tx_test_mode, tx_cfg, logger=l,
                 declared_protocol_name=None):
    l = logger
    l.info("Handling plate: " + plate_id)

    params_file_name = get_params_file_path(experiment_id, plate_id, in_dir)
    l.info("Submitting param file: " + params_file_name)
    params_for_plate = json.load(open(params_file_name, 'r'))
    submit_resp = None
    submit_id = None

    try:
        if not tx_mock:
            submit_resp = submit_to_transcriptic(tx_proj_id,
                                                 tx_proto_id,
                                                 params_for_plate,
                                                 challenge_problem,
                                                 out_dir,
                                                 tx_cfg,
                                                 plate_id,
                                                 test_mode=tx_test_mode,
                                                 logger=l,
                                                 declared_protocol_name=declared_protocol_name)
            submit_id = submit_resp['id']
        else:
            l.info("Submitting Mock TX Experiment")
            submit_id = 'mock_submission'
    except Exception as exc:
        l.info("Failed to submit " + params_file_name + " to Transcriptic")
        submit_id = "failed_submission_" + str(arrow.utcnow().timestamp)
    return (submit_id, params_file_name)


def submit_to_transcriptic(project_id, protocol_id,
                           params, challenge_problem, out_dir, tx_cfg, plate_id,
                           test_mode=True, logger=l,
                           declared_protocol_name=None):
    """Submit to transcriptic and record response"""
    l = logger
    launch_request_id = None
    launch_protocol = None

    l.info("Launch Transcriptic project: {} / protocol: {}".format(
        project_id, protocol_id))

    l.info("Connect to Transcriptic API")
    try:
         conn = get_transcriptic_api(tx_cfg)
    except Exception as exc:
        l.error("Failed connecting to Transcriptic")
        raise TranscripticApiError(exc)

    try:
        l.info("Transcriptic.launch_protocol")

        # print(params)
        launch_request = _create_launch_request(params, plate_id, test_mode=test_mode, out_dir=out_dir)
        l.debug("get launch_protocol " + str(launch_request))
        try:
            launch_protocol = conn.launch_protocol(launch_request,
                                                   protocol_id=protocol_id)
            # print(launch_protocol)
        except Exception as exc:
            raise TranscripticApiError(exc)

        launch_request_id = launch_protocol["id"]
        l.info('launch_protocol.id: {}'.format(
            launch_request_id))
    except Exception as exc:
        l.debug('launch_protocol_resp: {}'.format(exc))
        raise TranscripticApiError(exc)

    # Delay needed because it takes Transcriptic a few seconds to
    # complete launch_protocol()
    time.sleep(30)

    l.info("Transcriptic.submit_launch_request")
    request_response = {}
    try:
        protocols = conn.get_protocols()
        protocol_names = [x['name'] for x in protocols if x['id'] == protocol_id]
        if len(protocol_names) > 0:
            protocol_name = next(iter(protocol_names))
        else:
            protocol_name = declared_protocol_name
        req_title = "{}_{}_{}".format(
            arrow.utcnow().format('YYYY-MM-DDThh:mm:ssTZD'),
            challenge_problem,
            protocol_name
        )
        l.info("Experiment Title: %s", req_title)

        # req_title = "{}-{}".format(
        #    robj.get_attr('name'),
        #    arrow.utcnow().format('YYYY-MM-DDThh:mm:ssTZD'))
        # Retry submission up to timeout, with exponential backoff
        request_response = __submit_launch_request(
            conn,
            launch_request_id,
            protocol_id=protocol_id,
            project_id=project_id,
            title=req_title,
            test_mode=test_mode,
            logger=l)

        l.info("submit_launch_request.response.id: {}".format(
            request_response['id']))
        return TranscripticRunStatus(request_response)

    except Exception as exc:
        l.exception(exc)
        raise TranscripticApiError(exc)


def _create_launch_request(params, plate_id, bsl=1, test_mode=False, out_dir='.'):
    """Creates launch_request from input params"""
    params_dict = dict()
    params_dict["launch_request"] = params
    params_dict["launch_request"]["bsl"] = bsl
    params_dict["launch_request"]["test_mode"] = test_mode

    with open(os.path.join(out_dir, 'launch_request_{}.json'.format(plate_id)), 'w') as lr:
        json.dump(params_dict, lr, sort_keys=True,
                  indent=2, separators=(',', ': '))
    return json.dumps(params_dict)


# Commenting out tenacity decorator as we expect this to fail until
# the real protocol is available at Transcriptic
@retry(stop=stop_after_delay(70), wait=wait_exponential(multiplier=1, max=16))
def __submit_launch_request(conn, launch_request_id, protocol_id=None,
                            project_id=None, title=None, test_mode=False,
                            logger=l):
    l = logger
    try:
        l.info("Launching: launch_request_id = " + launch_request_id)
        l.info("Launching: protocol_id = " + protocol_id)
        l.info("Launching: project_id = " + project_id)
        l.info("Launching: title = " + title)
        l.info("Launching: test_mode = " + str(test_mode))
        lr = conn.submit_launch_request(launch_request_id,
                                        protocol_id=protocol_id,
                                        project_id=project_id,
                                        title=title,
                                        test_mode=test_mode)
        return lr
    except Exception as exc:
        l.exception(exc.args)
        raise Exception(exc)


def complete_tx_test_run(project_id, run_id, transcriptic_config, logger=None):
    """
    Complete a test run via the endpoint: https://secure.transcriptic.com/sd2org/{project_id}/runs/{run_id}/complete_all_instructions
    """
    url = "https://secure.transcriptic.com/sd2org/{}/runs/{}/complete_all_instructions".format(project_id, run_id)
    if logger:
        logger.info("Completing run: %s", run_id)

    try:
        tx_api = get_transcriptic_api(transcriptic_config)
    except Exception as exc:
        l.error("Failed connecting to Transcriptic: ", exc)
        raise TranscripticApiError(exc)

    email = tx_api.email
    token = tx_api.token
    json_api_root = "{}/api".format(tx_api.api_root)
    tx_api.organization_id = 'transcriptic'
    headers = {'X-User-Email': email, 'X-User-Token': token}
    response = requests.post(url, headers=headers).json

    if logger:
        logger.info("Response from %s: %s", url, response)
