"""Functions for uploading files to an agave path"""
from agavepy.actors import update_state
from attrdict import AttrDict
from .messagetypes import AbacoMessage
from reactors.runtime import Reactor, agaveutils
from requests.exceptions import HTTPError


def upload(r: Reactor, name: str, sourcePath: str, destinationPath: str, systemId: str):
    with open(sourcePath, 'r') as f:
        r.client.files.importData(
            filePath=destinationPath, systemId=systemId, fileName=name, fileToUpload=f)
