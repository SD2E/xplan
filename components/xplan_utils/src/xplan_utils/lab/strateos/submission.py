import arrow
import json
import logging
import os
import requests
import time
from autoprotocol import Protocol, container_type
from attrdict import AttrDict
from tenacity import retry, stop_after_delay, wait_exponential
from transcriptic.jupyter import objects
from xplan_utils.lab.strateos.utils import TranscripticApiError, get_transcriptic_api, TranscripticRunStatus

l = logging.getLogger(__file__)
l.setLevel(logging.INFO)


def _create_launch_request(params, local_name, bsl=1, test_mode=True, out_dir='.'):
    """Creates launch_request from input params"""
    params_dict = dict()
    params_dict["launch_request"] = params
    params_dict["launch_request"]["bsl"] = bsl
    params_dict["launch_request"]["test_mode"] = test_mode

    with open(os.path.join(out_dir, 'launch_request_{}.json'.format(local_name)), 'w') as lr:
        json.dump(params_dict, lr, sort_keys=True,
                  indent=2, separators=(',', ': '))
    return json.dumps(params_dict)


@retry(stop=stop_after_delay(70), wait=wait_exponential(multiplier=1, max=16))
def __submit_launch_request(conn, launch_request_id, protocol_id=None,
                            project_id=None, title=None, test_mode=True):
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
        l.exception(exc.args)
        raise Exception(exc)

# a slightly more generic submit_to_transcriptic
def submit_to_transcriptic(project_id, protocol_id, params, title, out_dir, tx_cfg, test_mode=True):
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
        launch_request = _create_launch_request(
            params, title, test_mode=test_mode, out_dir=out_dir)
        l.debug("get launch_protocol " + str(launch_request))
        try:
            launch_protocol = conn.launch_protocol(
                launch_request, protocol_id=protocol_id)
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
        protocol_name = next(x['name']
                             for x in protocols if x['id'] == protocol_id)
        req_title = "{}_{}_{}".format(
            arrow.utcnow().format('YYYY-MM-DDThh:mm:ssTZD'),
            title,
            protocol_name
        )
        l.info("Launch Title: %s", req_title)

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
