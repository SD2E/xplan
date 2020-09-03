from ..files import download_file, upload_file, download_dir, upload_dir, split_agave_uri, make_agave_uri, ensure_path_on_system
from ..jobs import launch_job
from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict
from reactors.runtime import Reactor, agaveutils
from .jobcompletionmessage import JobCompletionMessage
from xplan_utils.helpers import ensure_experiment_dir, get_design_file_name, get_experiment_design
import os
import json
from xplan_design.experiment_design import ExperimentDesign
from xplan_submit.lab.strateos.submit import submit_experiment
from xplan_submit.lab.strateos.write_parameters import design_to_parameters


class XPlanDesignMessage(AbacoMessage):

    JOB_SPEC = AttrDict({
        "app_id": "jladwig_xplan2_design-0.0.1",
        "base_name": "xplan_design_job-",
        "batchQueue": "all",
        "max_run_time": "01:00:00",
        "memoryPerNode": "1GB",
        "nodeCount": 1,
        "processorsPerNode": 1,
        "archive": True,
        "archiveSystem": "data-tacc-work-jladwig",
        "archivePath": "xplan2/archive/jobs/job-${JOB_ID}",
        "inputs": [
            "lab_configuration",
            "out_dir"
        ],
        "parameters": [
            "experiment_id",
            "challenge_problem"
        ]
    })

    def process_message(self, r: Reactor):
        msg = getattr(self, 'body')
        msg_experiment_id = msg.get('experiment_id')
        msg_challenge_problem = msg.get('challenge_problem')
        msg_lab_configuration = msg.get('lab_configuration')
        msg_out_dir = msg.get('out_dir')
        (out_dir_system, out_dir_path) = split_agave_uri(msg_out_dir)
        archive_system = out_dir_system

        archive_path = os.path.join(out_dir_path, "archive", "jobs")
        ensure_path_on_system(r, archive_system, archive_path, verbose=True)
        archive_path = os.path.join(archive_path, "job-${JOB_ID}")

        # TODO this is a bit of a hack in that I change the
        # message the is seen my the process stage to something
        # slightly different for the finalize stage. But it should
        # resolve issues with consecutive runes massively increasing
        # storage use (due to pulling in archive data)
        ensure_path_on_system(r, out_dir_system, out_dir_path, verbose=True)
        msg['out_dir'] = make_agave_uri(out_dir_system, out_dir_path)

        custom_job_spec = AttrDict(self.JOB_SPEC.copy())
        custom_job_spec['archiveSystem'] = archive_system
        custom_job_spec['archivePath'] = archive_path

        r.logger.info(
            "Process xplan design message \n  Experiment ID: {}\n Challenge Problem: {}\n  Lab Configuration: {}\n  OutDir: {}\n  Data Path: {}\n  Archive Path: {}\n  Archive System: {}"
            .format(msg_experiment_id, msg_challenge_problem, msg_lab_configuration, msg_out_dir, out_dir_path, archive_path, archive_system))

        job_id = launch_job(r, msg, custom_job_spec)
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

        #invocation_uri = msg.get('invocation')
        #invocation_resp = download_file(r, invocation_uri)
        #if not invocation_resp.ok:
        #    raise XPlanDesignMessageError("Failed to download invocation file")
        #invocation = invocation_resp.json()

        experiment_id = msg.get('experiment_id')
        challenge_problem = msg.get('challenge_problem')
        r.logger.info("challenge_problem = " + challenge_problem)
        archive_out_dir = os.path.join(archive_path, out_basename)
        upload_out_dir = os.path.join(out_path)

        archive_uri = make_agave_uri(archive_system, archive_out_dir)
        r.logger.info("archive_uri = {}".format(archive_uri))

        upload_uri = make_agave_uri(upload_system, upload_out_dir)
        r.logger.info("upload_uri = {}".format(upload_uri))

        local_out = os.path.abspath(out_basename)

        # Download the archived challenge directory
        r.logger.info("Download:\n  to: {}\n  from: {}".format(
            local_out, archive_uri))
        download_dir(r, archive_uri, local_out, verbose=True)
        r.logger.info("Download: Complete")

        # Do final processing
        self.handle_design_output(r,
                                  experiment_id,
                                  challenge_problem,
                                  self.get_lab_configuration(r, msg),
                                  local_out,
                                  test_mode=test_mode)

        # Upload the finished experiment files
        r.logger.info("Upload:\n  from: {}\n  to: {}".format(
            local_out, upload_uri))
        upload_dir(r, local_out, upload_uri, verbose=True)
        r.logger.info("Upload: Complete")

        r.logger.info("Finalize ended with success")

    # TODO move to files as a generic download to disk function
    def download_state(self, r: Reactor, source_uri, dest_path):
        resp = download_file(r, source_uri)
        if not resp.ok:
            raise XPlanDesignMessageError("Failed to download state.json file")
        with open(dest_path, 'wb') as f:
            f.write(resp.content)

    # TODO make helper
    def get_challenge_dir(self, experiment_id, challenge_problem, out_dir):
        return os.path.join(out_dir, challenge_problem, 'experiments', experiment_id)

    # TODO resolve how multiple labs work in this system
    def get_lab_configuration(self, r: Reactor, msg):
        cfg_uri = msg.get('lab_configuration')
        cfg_resp = download_file(r, cfg_uri)
        if not cfg_resp.ok:
            raise XPlanDesignMessageError(
                "Failed to download lab_configuration file")
        return cfg_resp.json()

    def handle_design_output(self, r: Reactor, experiment_id, challenge_problem, lab_cfg, out_dir: str):

        design_to_parameters(experiment_id,
                             challenge_problem,
                             lab_cfg,
                             input_dir=out_dir,
                             out_dir=out_dir)
        r.logger.info("design_to_parameters:\n{}\n".format(experiment_id))

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

        submit_experiment(experiment_id, challenge_problem, lab_cfg, transcriptic_params, input_dir=out_dir, out_dir=out_dir)


class XPlanDesignMessageError(AbacoMessageError):
    pass
