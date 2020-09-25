from reactors.runtime import Reactor
import re

## FIXME this is a quick hack to keep log_config data out of the logs files.
# It could surely be improved
def redact_log_msg(msg):
    if not isinstance(msg, str):
        # TODO
        return msg
    return re.sub(r"'lab_configuration': '[^']*'", "'lab_configuration': '*****'", msg)

def log_debug(r: Reactor, msg):
    r.logger.debug(redact_log_msg(msg))

def log_info(r: Reactor, msg):
    r.logger.info(redact_log_msg(msg))
    
def log_error(r: Reactor, msg):
    r.logger.error(redact_log_msg(msg))