from ..jobs import launch_job
from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict


class JobCompletionMessage(AbacoMessage):

    def process_message(self, r, work_dir, out_dir):
        pass

    def finalize_message(self, r):
        pass

    def get(self, prop):
        msg = getattr(self, 'body')
        return msg.get(prop)
