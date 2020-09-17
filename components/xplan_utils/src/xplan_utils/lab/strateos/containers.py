import json
import logging
import requests
import transcriptic
from attrdict import AttrDict
from transcriptic.jupyter import objects
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
    (url, headers) = _prepare_query_protocols(tx_cfg)
    l.info("Querying protocols...")
    response = requests.get(url, headers=headers)
    protocols = json.loads(response.content)
    for protocol in protocols:
        if protocol['id'] == proto_id:
            l.debug("Found protocol:\n%s\n", json.dumps(protocol, indent=2))
            return protocol
    return None


def generate_containers(containers, tx_cfg, test_mode=False):
    """
    Create a set of containers.
    """

    l.info("Connect to Transcriptic API")
    try:
         conn = get_transcriptic_api(tx_cfg)
    except Exception as exc:
        l.error("Failed connecting to Transcriptic")
        raise TranscripticApiError(exc)

    preview = conn.preview_protocol(MAKE_CONTAINERS_PROTOCOL)
    l.info("%s", preview)

    # # Setup API call
    # tx_org_id = tx_cfg.get('organization_id')
    # tx_email = tx_cfg.get('email')
    # tx_token = tx_cfg.get('token')

    # # url = "https://secure.transcriptic.com/{}/inventory/samples/create_with_shipment".format(
    # #     tx_org_id)
    # # headers = {"X-User-Email": tx_email,  # user-account-email
    # #            "X-User-Token": tx_token,  # Regular-mode API key
    # #            "Content-Type": "application/json",
    # #            "Accept": "application/json"}

    # # Setup Containers
    # if test_mode is True:
    #     for container in containers:
    #         container['test_mode'] = True

    # # Submit container
    # body = json.dumps({"containers": containers})
    # l.info("Creating new containers...")
    # l.debug("Sending: %s", body)
    # # response = requests.post(url, body, headers=headers)
    # # resp = json.loads(response.content)
    # # l.debug("Received Response: %s", resp)

    # # container_id = resp['containers'][0]['id']
    # # l.info("Created container: %s", container_id)

    # # return container_id
