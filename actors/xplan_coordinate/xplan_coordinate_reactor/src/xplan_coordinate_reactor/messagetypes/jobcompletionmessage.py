from ..jobs import launch_job
from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict


class JobCompletionMessage(AbacoMessage):

    def process_message(self, r, *, user_data=None):
        pass

    def finalize_message(self, r, job, *, user_data=None):
        pass

    def get(self, prop):
        msg = getattr(self, 'body')
        return msg.get(prop)
