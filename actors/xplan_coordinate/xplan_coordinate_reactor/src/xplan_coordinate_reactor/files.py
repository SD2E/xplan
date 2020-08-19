"""Functions for uploading files to an agave path"""
from agavepy.actors import update_state
from attrdict import AttrDict
from .messagetypes import AbacoMessage
from reactors.runtime import Reactor, agaveutils
from requests.exceptions import HTTPError

# split an agave uri into (system_id, path)
def split_agave_uri(agave_uri: str) -> (str, str):
    if "agave://" not in agave_uri:
        raise Exception("agaveURI is not an agave URI")
    # split the system id from the path
    return agave_uri.split("agave://")[1].split("/", 1)


def download_file(r: Reactor, downloadURI: str):
    system_id, path = split_agave_uri(downloadURI)

    r.logger.info("Downloading {} from {}".format(path, system_id))
    return r.client.files.download(filePath=path, systemId=system_id)

def upload_file(r: Reactor, name: str, sourcePath: str, destinationURI: str):
    system_id, path = split_agave_uri(destinationURI)

    r.logger.info("Uploading {} to {} on {}".format(sourcePath, path, system_id))
    with open(sourcePath, 'rb') as f:
        r.client.files.importData(
            filePath=path, systemId=system_id, fileName=name, fileToUpload=f)
