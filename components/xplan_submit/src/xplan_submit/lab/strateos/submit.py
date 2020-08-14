import json
import os
import time

import arrow
import pandas as pd
import requests
from tenacity import retry, stop_after_delay, wait_exponential

from xplan_utils.helpers import put_experiment_submission, put_experiment_design, get_params_file_name, \
    get_params_file_path
import logging

from xplan_utils.lab.strateos.utils import TranscripticApiError, get_transcriptic_api, TranscripticRunStatus

l = logging.getLogger(__file__)
l.setLevel(logging.INFO)

def  submit_experiment(request, design, xplan_config, tx_cfg, tx_params, out_dir=".", parameters=None, batches=None, mock=False):
    experiment_id = request['experiment_id']
    base_dir = request.get('base_dir', ".")
    challenge_problem = request.get('challenge_problem')
    if base_dir == ".":
        challenge_out_dir = os.path.join(out_dir, challenge_problem)
    else:
        challenge_out_dir = os.path.join(out_dir, base_dir, challenge_problem)
    protocol_id = request['defaults']['protocol_id']
    test_mode = request['defaults']['test_mode']

    tx_test_mode = test_mode
    tx_proj_key = tx_params.get('default')
    tx_proj = tx_params.get('projects').get(tx_proj_key)
    tx_proj_id = tx_proj.get('id')
    tx_proj_nick = tx_proj.get('nick')


    for batch in request['batches']:
        if batches is not None:
            if batch['id'] not in batches:
                continue

        (submit_id, params_file_name) = submit_plate(experiment_id,
                                                     batch['id'],
                                                     challenge_problem,
                                                     challenge_out_dir,
                                                     mock,
                                                     tx_proj_id,
                                                     protocol_id,
                                                     tx_test_mode,
                                                     tx_cfg,
                                                     parameters=parameters)

        #slack_post('Submitted {} plan to Transcriptic'.format(
        #    tx_proj_nick), robj.settings)

        put_experiment_submission(experiment_id,
                                  batch['id'],
                                  submit_id,
                                  params_file_name,
                                  challenge_out_dir,
                                  xplan_config)

        def assign_run_id(x):
            if str(x['batch']) == batch['id']:
                return submit_id
            elif 'lab_id' in x:
                return x['lab_id']
            else:
                return None

        design_df = pd.read_json(design['design'])
        design_df['lab_id'] = design_df.apply(assign_run_id, axis=1)

    design['design'] = design_df.to_json()
    put_experiment_design(design, challenge_out_dir)

    if test_mode:
        ## complete the experiment
        for batch in request['batches']:
            if batches is not None:
                if batch['id'] not in batches:
                    continue
            try:
                run_id = design_df.loc[design_df.batch.astype(str) == batch['id']]['lab_id'].unique()[0]
            except Exception as e:
                l.exception("Could not get run_id for batch: %s", batch['id'])
            complete_tx_test_run(tx_proj_id, run_id, tx_cfg)


def submit_plate(experiment_id, plate_id, challenge_problem, out_dir,
                 tx_mock, tx_proj_id, tx_proto_id, tx_test_mode, tx_cfg, parameters=None):
    l.info("Handling plate: " + plate_id)

    if parameters is None:
        params_file_name = get_params_file_path(experiment_id, plate_id, out_dir)
        l.info("Submitting param file: " + params_file_name)
        params_for_plate = json.load(open(params_file_name, 'r'))
    else:
        params_for_plate = parameters[plate_id]
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
                                                 test_mode=tx_test_mode)
            submit_id = submit_resp['id']
        else:
            l.info("Submitting Mock TX Experiment")
            submit_id = 'mock_submission'
    except Exception as exc:
        l.info("Failed to submit " + params_file_name + " to Transcriptic")
        submit_id = "failed_submission_" + str(arrow.utcnow().timestamp)
    return (submit_id, params_file_name)


def submit_to_transcriptic(project_id, protocol_id,
                           params, challenge_problem, out_dir, tx_cfg, test_mode=True):
    """Submit to transcriptic and record response"""

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
        launch_request = _create_launch_request(params, test_mode=test_mode, out_dir=out_dir)
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
        protocol_name = [x['name'] for x in conn.get_protocols() if x['id'] == protocol_id][0]
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
            test_mode=test_mode)

        l.info("submit_launch_request.response.id: {}".format(
            request_response['id']))
        return TranscripticRunStatus(request_response)

    except Exception as exc:
        l.exception(exc)
        raise TranscripticApiError(exc)


def _create_launch_request(params, bsl=1, test_mode=False, out_dir='.'):
    """Creates launch_request from input params"""
    params_dict = dict()
    params_dict["launch_request"] = params
    params_dict["launch_request"]["bsl"] = bsl
    params_dict["launch_request"]["test_mode"] = test_mode

    with open(os.path.join(out_dir, 'launch_request.json'), 'w') as lr:
        json.dump(params_dict, lr, sort_keys=True,
                  indent=2, separators=(',', ': '))
    return json.dumps(params_dict)


# Commenting out tenacity decorator as we expect this to fail until
# the real protocol is available at Transcriptic
@retry(stop=stop_after_delay(70), wait=wait_exponential(multiplier=1, max=16))
def __submit_launch_request(conn, launch_request_id, protocol_id=None,
                            project_id=None, title=None, test_mode=False):
    try:
        print("Launching: launch_request_id = " + launch_request_id)
        print("Launching: protocol_id = " + protocol_id)
        print("Launching: project_id = " + project_id)
        print("Launching: title = " + title)
        print("Launching: test_mode = " + str(test_mode))
        lr = conn.submit_launch_request(launch_request_id,
                                        protocol_id=protocol_id,
                                        project_id=project_id,
                                        title=title,
                                        test_mode=test_mode)
        return lr
    except Exception as exc:
        print(exc.args)
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
