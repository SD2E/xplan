"""Functions for reactor.py"""
from attrdict import AttrDict
from json import loads
from .messagetypes import *


def message_as_dict(context):
    """Extended form of message parser from agavepy.actors.get_context()"""
    # https://github.com/TACC/agavepy/blob/master/agavepy/actors.py#L57
    if context.get('message_dict', {}) != {}:
        message = context.get('message_dict')
        return message
    else:
        try:
            # Use JSON loads
            message = loads(context.get('raw_message', ''))
            if isinstance(message, dict):
                message = AttrDict(message)
                return message
            else:
                raise Exception
        except Exception:
            raise AbacoMessageError("Message cannot be parsed as JSON")


def typed_message_from_dict(message_dict):
    """Returns one of messagetypes based on schema validation"""

    if ExampleMessage.validate(message_dict) is True:
        return ExampleMessage(message=message_dict)
    elif XPlanDesignMessage.validate(message_dict) is True:
        return XPlanDesignMessage(message=message_dict)
    elif FileMessage.validate(message_dict) is True:
        return FileMessage(typed_message_from_context, message=message_dict)
    else:
        raise AbacoMessageError(
            "Unable to determine message type for: {}".format(message_dict))


def typed_message_from_context(context_dict):
    """Returns one of messagetypes based on schema validation"""
    message_dict = message_as_dict(context_dict)
    return typed_message_from_dict(message_dict)


def as_job_completion_message(context_dict):
    """Returns a job completion message based on schema validation"""
    message_dict = message_as_dict(context_dict)

    if JobCompletionMessage.validate(message_dict) is True:
        return JobCompletionMessage(message=message_dict)
    return None
