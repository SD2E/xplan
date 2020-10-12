import json

import requests
import transcriptic
from transcriptic.jupyter import objects

import logging

l = logging.getLogger(__file__)
l.setLevel(logging.INFO)


from attrdict import AttrDict

class TranscripticApiError(Exception):
    # TODO: Maybe we can make this a requests HTTPError
    pass

class TranscripticRunStatus(AttrDict):
    pass


def get_transcriptic_api(settings):
    """Connect (without validation) to Transcriptic.com"""
    try:
        return transcriptic.Connection(**settings)
    except Exception:
        raise


def get_tx_containers(transcriptic_api, container_search_strings):
    if type(container_search_strings) is str:
        container_search_strings = [container_search_strings]

    result = []
    for s in container_search_strings:
        result.extend(transcriptic_api.inventory(s)['results'])

    if len(result) == 0 and len(container_search_strings) > 0:
        ## Check if search strings are actually container ids
        for s in container_search_strings:
            try:
                result.append(objects.Container(s))
            except Exception as e:
                l.exception("Could not instantiate container: %s", s)

    l.info("Found containers for search strings " + str(container_search_strings) + ": " + str(result))
    return result

def get_usable_tx_containers(inputs):
    usable_containers = []
    for container in inputs['containers']:
#        print("container:")
#        print(json.dumps(container))
        if 'defaults' in inputs and \
          'source_plates' in inputs['defaults'] and \
          (inputs['defaults']['source_plates'] is None or \
           get_container_id(container) in inputs['defaults']['source_plates']):
            usable_containers.append(container)
 #       if (container['status'] != 'available' and container in usable_containers):
 #           # TODO: UNCOMMENT LINE BELOW
 #           #usable_containers.remove(container)
 #           pass
    return usable_containers


def generate_test_container(container, tx_cfg):
    """
    Create a test container with same properties as container.
    """

    ## Setup API call
    tx_org_id = tx_cfg.get('organization_id')
    tx_email = tx_cfg.get('email')
    tx_token = tx_cfg.get('token')

    url = "https://secure.transcriptic.com/{}/inventory/samples/create_with_shipment".format(tx_org_id)
    headers = {"X-User-Email": tx_email,  # user-account-email
               "X-User-Token": tx_token,  # Regular-mode API key
               "Content-Type": "application/json",
               "Accept": "application/json"}

    ## Setup Container
    test_container = copy_container(container)
    test_container["test_mode"] = True

    ## Submit container
    body = json.dumps({"containers": [test_container]})
    l.info("Submitting new test container...")
    l.debug("Sending: %s", body)
    response = requests.post(url, body, headers=headers)
    resp = json.loads(response.content)
    l.debug("Received Response: %s", resp)

    container_id = resp['containers'][0]['id']
    l.info("Created container: %s", container_id)

    return container_id


def copy_container(container):
    new_container = {}
    new_container["label"] = container.name
    new_container["container_type"] = container.container_type.shortname
    new_container["storage_condition"] = container.storage
    new_container["aliquots"] = copy_aliquots(container.aliquots)
    return new_container


def copy_aliquots(aliquots):
    col_map = {"Name": "name", "Volume": "volume_ul"}
    new_aliquots = json.loads(aliquots.astype("str").rename(columns=col_map).to_json(orient="index"))

    to_remove = []

    ## Map other cols into properties, and fix volume string
    for aliquot_id, aliquot in new_aliquots.items():
        aliquot["volume_ul"] = int(aliquot["volume_ul"].split(":")[0])

        ## If copied from used container, then volume may be zero, so set to some volume
        if aliquot["volume_ul"] == 0:
            aliquot["volume_ul"] = 0
        elif aliquot["volume_ul"] < 0:
            to_remove.append(aliquot_id)

        properties = {}
        for k, v in aliquot.items():
            if k not in ["name", "volume_ul"]:
                properties[k] = v
        for k in properties:
            del aliquot[k]
        aliquot["properties"] = properties

    for aliquot_id in to_remove:
        del new_aliquots[aliquot_id]

    return new_aliquots

def get_container_id(x):
    if type(x) is dict:
        return x['id']
    else:
        return x.id

def get_container_from_run_id(run_id, containers):
    try:
        run_obj = transcriptic.run(run_id)
    except Exception as e:
        run_obj = transcriptic.run(run_id)

    try:
        run_containers = run_obj.containers
    except Exception as e:
        run_containers = run_obj.containers
    run_container_ids = run_containers.ContainerId.unique()
    c = next(iter([container for container in containers if  get_container_id(container) in run_container_ids]))
    return c

def add_run_container_to_factor(lab_id_factor, containers):
    if 'attributes' not in lab_id_factor:
        lab_id_factor['attributes'] = { level : { } for level in lab_id_factor['domain']}

    for lab_id in lab_id_factor['domain']:
        container = get_container_from_run_id(lab_id, containers)
        lab_id_factor['attributes'][lab_id]['container'] = get_container_id(container)

    return lab_id_factor