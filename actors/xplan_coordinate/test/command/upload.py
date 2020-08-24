#!/usr/bin/env python3

from reactors.runtime import Reactor, agaveutils
from xplan_coordinate_reactor.files import upload_dir, download_dir
from attrdict import AttrDict
import os


def main():
    r = Reactor()
    out_dir = "/out"
    download_dir(r, "agave://data-tacc-work-jladwig/jladwig/archive/jobs/job-bfe47ab9-cae3-4fb5-add9-44cf7c31d116-007/out", out_dir)
    upload_dir(r, "/out", "agave://data-tacc-work-jladwig/xplan2/out")

if __name__ == '__main__':
    main()
