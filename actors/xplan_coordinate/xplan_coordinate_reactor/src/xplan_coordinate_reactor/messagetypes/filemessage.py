from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict
from json import load
from ..files import download_file, make_agave_uri
from ..logs import log_info, log_error
import os


class FileMessage(AbacoMessage):
    def __init__(self, typed_message_from_context, **kwargs):
        super().__init__(**kwargs)
        self.typed_message_from_context = typed_message_from_context

    def process_message(self, r, timestamp, *, user_data=None):
        log_info(r, "Found file message")

        body = getattr(self, 'body')
        fileToDownload = body.get('file')

        lab_configuration = None
        if 'lab_configuration' in body:
            # load the lab_configuation in from the message
            lab_configuration = body.get('lab_configuration')
        if lab_configuration is None:
            # Read the fallback lab_configuration out of the config.yml
            lc_settings = r.settings['xplan_config']['lab_configuration']
            lc_system = lc_settings['system']
            lc_path = lc_settings['path']
            lab_configuration = make_agave_uri(lc_system, lc_path)

        # if we get a non-agave path print an error
        if 'agave://' not in fileToDownload:
            log_error(r, 
                "Failed to process FileMessage. File must be a agave path: {}".format(fileToDownload))
            return None

        log_info(r, "Downloading file: {}".format(fileToDownload))
        fileRequest = download_file(r, fileToDownload)
        if fileRequest.ok:
            log_info(r, "Parsing file as json: {}".format(fileToDownload))
            fileJson = fileRequest.json()
            fmsg = self.typed_message_from_context(
                AttrDict({"message_dict": fileJson}))
            # log_info(r, "Json: %s", fileJson)

            # send along the extra data so that messages down the
            # chain can search for and use the properties sourced
            # from the original message
            user_data = {
                'file': fileToDownload,
                'lab_configuration': lab_configuration
            }
            log_info(r, "Sending extra user data: {}".format(user_data))
            return fmsg.process_message(r, timestamp, user_data=user_data)

        # log_info(r, "Reading file: %s", fileToParse)
        # with open(fileToParse, 'r') as f:
        #     # log_info(r, f.read())
        #     fileJson = load(f)
        #     #log_info(r, "fileJson: %s", fileJson)
        #     fmsg = self.typed_message_from_context(
        #         AttrDict({"message_dict": fileJson}))
        #     #log_info(r, "fmsg; %s", fmsg)
        #     return fmsg.process_message(r, work_dir, out_dir)
        log_error(r, 
            "Failed to process FileMessage: {}".format(fileRequest.text))
        return None

    def finalize_message(self, r, job, process_data, *, user_data=None):
        pass


class FileMessageError(AbacoMessageError):
    pass
