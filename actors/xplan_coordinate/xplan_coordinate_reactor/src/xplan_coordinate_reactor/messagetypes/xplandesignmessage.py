from ..files import download_file, download_dir, upload_dir, split_agave_uri, make_agave_uri
from ..jobs import launch_job
from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict
from reactors.runtime import Reactor, agaveutils
from .jobcompletionmessage import JobCompletionMessage
from xplan_utils.helpers import ensure_experiment_dir, get_design_file_name
import os
import json
from xplan_design.experiment_design import ExperimentDesign
from xplan_submit.lab.strateos.submit import submit_experiment
from xplan_submit.lab.strateos.write_parameters import design_to_parameters


class XPlanDesignMessage(AbacoMessage):

    JOB_SPEC = AttrDict({
        "app_id": "jladwig_xplan_design-0.0.1",
        "base_name": "jladwig_xplan_design_job-",
        "batchQueue": "all",
        "max_run_time": "01:00:00",
        "memoryPerNode": "1GB",
        "nodeCount": 1,
        "processorsPerNode": 1,
        "archive": True,
        "inputs": [
            "invocation",
            "lab_configuration",
            "out_dir"
        ],
        "parameters": []
    })

    def process_message(self, r: Reactor):
        msg = getattr(self, 'body')
        input_invocation = msg.get('invocation')
        input_lab_configuration = msg.get('lab_configuration')
        input_out_dir = msg.get('out_dir')
        r.logger.info(
            "Process xplan design message \n  Invocation: {}\n  Lab Configuration: {}\n  OutDir: {}"
            .format(input_invocation, input_lab_configuration, input_out_dir))

        job_id = launch_job(r, msg, self.JOB_SPEC)
        if (job_id is None):
            r.logger.error("Failed to launch job.")
            return None

        r.logger.info("Launched job {} in {} usec".format(
            job_id, r.elapsed()))
        return job_id

    def finalize_message(self, r: Reactor, job: JobCompletionMessage):
        msg = getattr(self, 'body')
        r.logger.info("Finalize xplan design message: {}".format(msg))

        # TODO adjust output of design app to always output to /out
        # This assumes the design app mounts the out_dir agave path as
        # just the basename of the given out_dir path
        out_uri = msg.get('out_dir')
        upload_system, out_path = split_agave_uri(out_uri)
        out_basename = os.path.basename(out_path.rstrip('/'))

        archive_system = job.get("archiveSystem")
        archive_path = job.get("archivePath")

        invocation_uri = msg.get('invocation')
        invocation_resp = download_file(r, invocation_uri)
        if not invocation_resp.ok:
            raise XPlanDesignMessageError("Failed to download invocation file")
        invocation = invocation_resp.json()

        # TODO move this to the helper so it only needs to be changed
        # in one place if edited need to be made (see design.py)
        base_dir = invocation.get('base_dir', ".")
        challenge_problem = invocation.get('challenge_problem')

        if base_dir == ".":
            archive_out_dir = os.path.join(
                archive_path, out_basename, challenge_problem)
            upload_out_dir = os.path.join(out_path, challenge_problem)
        else:
            archive_out_dir = os.path.join(
                archive_path, out_basename, base_dir, challenge_problem)
            upload_out_dir = os.path.join(
                out_path, base_dir, challenge_problem)

        r.logger.info("challenge_problem = " + challenge_problem)

        archive_uri = make_agave_uri(archive_system, archive_out_dir)
        r.logger.info("archive_uri = {}".format(archive_uri))

        upload_uri = make_agave_uri(upload_system, upload_out_dir)
        r.logger.info("upload_uri = {}".format(upload_uri))

        local_out = os.path.abspath(out_basename)
        download_dir(r, archive_uri, local_out)
        r.logger.info("Download:\n  to: {}\n  from: {}".format(
            local_out, archive_uri))

        self.handle_design_output(r,
                                  invocation,
                                  self.get_lab_configuration(r, msg),
                                  local_out)

        upload_dir(r, local_out, upload_uri)
        r.logger.info("Upload:\n  from: {}\n  to: {}".format(
            local_out, upload_uri))

    # TODO resolve how multiple labs work in this system
    def get_lab_configuration(self, r: Reactor, msg):
        cfg_uri = msg.get('lab_configuration')
        cfg_resp = download_file(r, cfg_uri)
        if not cfg_resp.ok:
            raise XPlanDesignMessageError(
                "Failed to download lab_configuration file")
        return cfg_resp.json()

    def handle_design_output(self, r: Reactor, invocation, lab_cfg, out_dir: str):
        xplan_config = r.settings['xplan_config']
        experiment_id = invocation.get('experiment_id')
        design = self.get_experiment_design(r, experiment_id, out_dir)

        parameters = design_to_parameters(invocation,
                                          design,
                                          lab_cfg,
                                          out_dir=out_dir)
        r.logger.info("design_to_parameters:\n{}\n".format(parameters))

        # FIXME don't hardcode this?
        transcriptic_params = {
            "default": "XPlanAutomatedExecutionTest",
            "projects": {
                "XPlanAutomatedExecutionTest": {
                    "id": "p1bqm3ehqzgum",
                    "nick": "Yeast Gates"
                }
            }
        }

        # If submit is present and True then we are not doing
        # a mock submission. If submit is False or not present
        # then do a mock submission.
        mock = not invocation.get('submit', False)

        # completed_design = submit_experiment(invocation,
        #                                      design,
        #                                      xplan_config,
        #                                      lab_cfg,
        #                                      transcriptic_params,
        #                                      parameters=parameters,
        #                                      out_dir=out_dir,
        #                                      mock=mock)
        # return completed_design

    # TODO Figure out where to place this function (helpers?)
    # Modified version of the version found in xplan_utils.helpers that
    # does not use the state.json file since the only available experiment
    # in the reactor scratch space is the relevant
    def get_experiment_design(self, r: Reactor, experiment_id: str, out_dir: str):
        r.logger.info("Getting Experiment Design ... " + experiment_id)

        design_file_name = get_design_file_name(experiment_id)
        experiment_dir = ensure_experiment_dir(experiment_id, out_dir)
        r.logger.info("experiment_dir: " + experiment_dir)
        design_file_stash = os.path.join(experiment_dir, design_file_name)
        design = ExperimentDesign(
            **json.load(open(os.path.join(out_dir, design_file_stash))))
        r.logger.info("Retrieved Experiment: " + experiment_id)
        return design


class XPlanDesignMessageError(AbacoMessageError):
    pass
