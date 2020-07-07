#!/usr/bin/env python

from agavepy.agave import Agave
from agavepy.actors import get_client
from reactors.runtime import Reactor, agaveutils
from requests.exceptions import HTTPError


def main():
    r = Reactor()

    m = r.context.message_dict
    r.logger.info("message: {}".format(m))
    r.logger.info("raw message: {}".format(r.context.raw_message))

    r.on_success("Sink received message {} in {} usec".format(m, r.elapsed()))

if __name__ == '__main__':
    main()
