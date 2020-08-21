from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict
from json import load
from ..files import download_file
import os


class FileMessage(AbacoMessage):
    def __init__(self, typed_message_from_context, **kwargs):
        super().__init__(**kwargs)
        self.typed_message_from_context = typed_message_from_context

    def process_message(self, r):
        r.logger.info("Found file message")

        fileToDownload = getattr(self, 'body').get('file')

        # if we get a non-agave path print an error
        if 'agave://' not in fileToDownload:
            r.logger.error(
                "Failed to process FileMessage. File must be a agave path: %s", fileToDownload)
            return None

        r.logger.info("Downloading file: %s", fileToDownload)
        fileRequest = download_file(r, fileToDownload)
        if fileRequest.ok:
            r.logger.info("Parsing file as json: %s", fileToDownload)
            fileJson = fileRequest.json()
            fmsg = self.typed_message_from_context(
                AttrDict({"message_dict": fileJson}))
            r.logger.info("Json: %s", fileJson)
            return fmsg.process_message(r)

        # r.logger.info("Reading file: %s", fileToParse)
        # with open(fileToParse, 'r') as f:
        #     # r.logger.info(f.read())
        #     fileJson = load(f)
        #     #r.logger.info("fileJson: %s", fileJson)
        #     fmsg = self.typed_message_from_context(
        #         AttrDict({"message_dict": fileJson}))
        #     #r.logger.info("fmsg; %s", fmsg)
        #     return fmsg.process_message(r, work_dir, out_dir)
        r.logger.error(
            "Failed to process FileMessage: %s", fileRequest.text)
        return None

    def finalize_message(self, r, job):
        pass


class FileMessageError(AbacoMessageError):
    pass
