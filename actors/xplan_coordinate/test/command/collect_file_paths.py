#!/usr/bin/env python3

from reactors.runtime import Reactor, agaveutils
from xplan_coordinate_reactor.files import collect_file_paths
from attrdict import AttrDict


def main():
    r = Reactor()
    files = collect_file_paths(r, "agave://data-tacc-work-jladwig/jladwig/archive/jobs/job-bfe47ab9-cae3-4fb5-add9-44cf7c31d116-007/out/YEAST_STATES")
    for file in files:
        print(file)


if __name__ == '__main__':
    main()
