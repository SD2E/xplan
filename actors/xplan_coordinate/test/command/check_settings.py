#!/usr/bin/env python3

from reactors.runtime import Reactor, agaveutils
from xplan_coordinate_reactor.files import list_dir
from attrdict import AttrDict


def main():
    r = Reactor()
    cfg = r.settings["xplan_config"]
    print("Xplan Config")
    print(cfg)
    print("Email")
    print(cfg["jobs"]["email"])
    print((cfg["jobs"]["email"] is None))


if __name__ == '__main__':
    main()
