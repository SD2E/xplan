from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict
from json import load
from ..files import download_file, make_agave_uri
import os


class FileMessage(AbacoMessage):
    def __init__(self, typed_message_from_context, **kwargs):
        super().__init__(**kwargs)
        self.typed_message_from_context = typed_message_from_context

    def process_message(self, r, *, user_data=None):
        r.logger.info("Found file message")

        body = getattr(self, 'body')
        fileToDownload = body.get('file')

        lab_configuration = None
        if 'lab_configuration' in body:
            lab_configuration = body.get('lab_configuration')
        if lab_configuration is None:
            lc_settings = r.settings['xplan_config']['lab_configuration']
            lc_system = lc_settings['system']
            lc_path = lc_settings['path']
            lab_configuration = make_agave_uri(lc_system, lc_path)

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
            # r.logger.info("Json: %s", fileJson)

            # send along the extra data so that messages down the
            # chain can search for and use the properties sourced
            # from the original message
            user_data = {
                'file': fileToDownload,
                'lab_configuration': lab_configuration
            }
            r.logger.info("Sending extra user data: %s", user_data)
            return fmsg.process_message(r, user_data=user_data)

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

    def finalize_message(self, r, job, *, user_data=None):
        pass


class FileMessageError(AbacoMessageError):
    pass
