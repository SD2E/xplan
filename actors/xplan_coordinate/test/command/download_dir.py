#!/usr/bin/env python3

from reactors.runtime import Reactor, agaveutils
from xplan_coordinate_reactor.files import download_dir
from attrdict import AttrDict
import os


def main():
    r = Reactor()
    out_dir = "/out/recursive"
    download_dir(r, "agave://data-tacc-work-jladwig/jladwig/archive/jobs/job-bfe47ab9-cae3-4fb5-add9-44cf7c31d116-007/out/YEAST_STATES", out_dir)
    out_dir = "/out/nonrecursive"
    download_dir(r, "agave://data-tacc-work-jladwig/jladwig/archive/jobs/job-bfe47ab9-cae3-4fb5-add9-44cf7c31d116-007/out/YEAST_STATES", out_dir, recursive=False)

if __name__ == '__main__':
    main()
