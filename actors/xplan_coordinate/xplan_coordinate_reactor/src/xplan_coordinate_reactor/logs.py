from reactors.runtime import Reactor
import re

## FIXME this is a quick hack to keep log_config data out of the logs files.
# It could surely be improved
def redact_log_msg(msg):
    res = msg
    if not isinstance(msg, str):
        # TODO
        return res
    res = re.sub(r"'lab_configuration': '[^']*'", "'lab_configuration': '*****'", res)
    res = re.sub(r"'lab_configuration': {[^}]*}", "'lab_configuration': '*****'", res)
    return res

def log_debug(r: Reactor, msg):
    r.logger.debug(redact_log_msg(msg))

def log_info(r: Reactor, msg):
    r.logger.info(redact_log_msg(msg))
    
def log_error(r: Reactor, msg, *, exc_info=False):
    r.logger.error(redact_log_msg(msg), exc_info=exc_info)