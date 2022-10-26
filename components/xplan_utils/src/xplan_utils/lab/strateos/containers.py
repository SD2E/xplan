import json
import logging
import os
import requests
import transcriptic
from autoprotocol import Protocol, container_type
from attrdict import AttrDict
from transcriptic.jupyter import objects
from xplan_utils.lab.strateos.submission import submit_to_transcriptic
from xplan_utils.lab.strateos.utils import TranscripticApiError, get_transcriptic_api, TranscripticRunStatus


l = logging.getLogger(__file__)
l.setLevel(logging.DEBUG)

MAKE_CONTAINERS_PROTOCOL = 'pr1eu2avrq8bznx'


def _get_headers(tx_cfg):
    # Setup API call
    tx_email = tx_cfg.get('email')
    tx_token = tx_cfg.get('token')

    return {"X-User-Email": tx_email,  # user-account-email
            "X-User-Token": tx_token,  # Regular-mode API key
            "Content-Type": "application/json",
            "Accept": "application/json"}


def _prepare_query_protocols(tx_cfg):
    tx_org_id = tx_cfg.get('organization_id')
    return ("https://secure.transcriptic.com/{}/protocols.json".format(tx_org_id),
            _get_headers(tx_cfg))


def query_protocol(tx_cfg, proto_id):
    """
    Search all protocols for the given id
    """
    (url, headers) = _prepare_query_protocols(tx_cfg)
    l.info("Querying protocols...")
    response = requests.get(url, headers=headers)
    protocols = json.loads(response.content)
    for protocol in protocols:
        if protocol['id'] == proto_id:
            l.debug("Found protocol:\n%s\n", json.dumps(protocol, indent=2))
            return protocol
    return None


def make_containers(project_id, tx_cfg, containers, *, title='make_containers', out_dir='.', test_mode=True):
    tx_proj_id = project_id
    # Protocol inputs
    params = {
        "parameters": {
            "containers": containers
        }
    }
    submit_to_transcriptic(tx_proj_id, MAKE_CONTAINERS_PROTOCOL, params,
                           title, out_dir, tx_cfg, test_mode=test_mode)
