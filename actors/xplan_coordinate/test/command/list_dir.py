#!/usr/bin/env python3

from reactors.runtime import Reactor, agaveutils
from xplan_coordinate_reactor.files import list_dir
from attrdict import AttrDict


def list_dir_r(r, uri, spaces, depth=0):
    if depth > 3:
        print("Test depth exceeded")
        return

    pre = ' ' * spaces

    results = list_dir(r, uri)
    for file in results:
        f = AttrDict(file)
        if f.type != 'file':
            continue
        print("{}{}".format(pre, f.name))

    for dir in results:
        d = AttrDict(dir)
        if d.type != 'dir':
            continue
        if d.name == '.':
            continue
        if d.name == '..':
            continue
        print("{}[{}]".format(pre, d.name))
        next_uri = "{}/{}".format(uri, d.name)
        list_dir_r(r, next_uri, spaces + 2, depth + 1)


def main():
    r = Reactor()
    print("Listing directory contents")
    list_dir_r(r, "agave://data-tacc-work-jladwig/jladwig/archive/jobs/job-bfe47ab9-cae3-4fb5-add9-44cf7c31d116-007/out/YEAST_STATES", 2)


if __name__ == '__main__':
    main()
