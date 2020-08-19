"""Functions for uploading files to an agave path"""
from agavepy.actors import update_state
from attrdict import AttrDict
from .messagetypes import AbacoMessage
from reactors.runtime import Reactor, agaveutils
from requests.exceptions import HTTPError


def upload_file(r: Reactor, name: str, sourcePath: str, destinationURI: str):
    if "agave://" not in destinationURI:
        r.logger.error("destinationURI must be an agave URI")
        return

    # split the system id from the path
    system_id, path = destinationURI.split("agave://")[1].split("/", 1)

    r.logger.info("Uploading {} to {} on {}".format(sourcePath, path, system_id))
    with open(sourcePath, 'rb') as f:
        r.client.files.importData(
            filePath=path, systemId=system_id, fileName=name, fileToUpload=f)
