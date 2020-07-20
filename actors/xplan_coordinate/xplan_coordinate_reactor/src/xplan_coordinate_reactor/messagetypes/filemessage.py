from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict
from json import load

class FileMessage(AbacoMessage):
    def __init__(self, typed_message_from_context, **kwargs):
        super().__init__(**kwargs)
        self.typed_message_from_context = typed_message_from_context

    def process_message(self, r, out_dir):
        r.logger.info("Found file message")
        fileToParse = getattr(self, 'body').get('file')

        if 'agave://' in fileToParse:
            #fileToParse = "".join(fileToParse.split('//')[1])
            fileToParse = out_dir + fileToParse.split('xplan-reactor')[1]

        r.logger.info("Reading file: %s", fileToParse)

        with open(fileToParse, 'r') as f:
            # r.logger.info(f.read())
            fileJson = load(f)
            #r.logger.info("fileJson: %s", fileJson)
            fmsg = self.typed_message_from_context(
                AttrDict({"message_dict": fileJson}))
            #r.logger.info("fmsg; %s", fmsg)
            return fmsg.process_message(r, out_dir)
        
        return None

    def finalize_message(self, r):
        pass


class FileMessageError(AbacoMessageError):
    pass
