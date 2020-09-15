from ..files import download_file, upload_file, download_dir, upload_dir, split_agave_uri, make_agave_uri, ensure_path_on_system, file_exists_at_agave_uri
from ..jobs import launch_job
from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict
from reactors.runtime import Reactor, agaveutils
from .jobcompletionmessage import JobCompletionMessage
from xplan_utils.helpers import ensure_experiment_dir, get_design_file_name, get_experiment_design
import os
import json
import jsonpatch as jp
from xplan_design.experiment_design import ExperimentDesign
from xplan_submit.lab.strateos.submit import submit_experiment
from xplan_submit.lab.strateos.write_parameters import design_to_parameters
from xplan_utils import persist


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

    def clear_assigned_containers(self, r: Reactor, system, out_dir):
        state_uri = make_agave_uri(system, os.path.join(out_dir, 'state.json'))
        if not file_exists_at_agave_uri(r, state_uri, verbose=True):
            return
        r.logger.info("Downloading state.json...")
        resp = download_file(r, state_uri, verbose=True)
        if not resp.ok:
            raise XPlanDesignMessageError("Failed to download state json from {}".format(state_uri))
        state = resp.json()
        r.logger.info("Checking state.json for assigned_cotainers...")
        if 'assigned_containers' in state:
            r.logger.info("Clearing assigned_cotainers...")
            state['assigned_containers'] = []
            state_path = "state.json"
            with open(state_path, 'w') as f:
                f.write(json.dumps(state))
            state_dir = make_agave_uri(system, os.path.join(out_dir))
            upload_file(r, state_path, state_dir, verbose=True)
            # I was originally making a differently named file
            # and uploading it with the `fileName` keyword but
            # that keyword is not working as expected so just
            # make the file and delete it after upload
            os.remove(state_path)

    def ensure_state_json(self, r: Reactor, system, out_dir):
        state_uri = make_agave_uri(system, os.path.join(out_dir, 'state.json'))
        if file_exists_at_agave_uri(r, state_uri, verbose=True):
            return
        # this ensures the state json has the expected fields in it.
        # Our state merging during the finalize step need this to 
        # avoid issues when multiple jobs are run back to back on a
        # challenge problem with no initial state.
        preseed_state ={
            "experiment_requests": [],
            "experiment_submissions": {},
            "assigned_containers": [],
            "runs": {}
        }
        state_path = "state.json"
        with open(state_path, 'w') as f:
            f.write(json.dumps(preseed_state))
        state_dir = make_agave_uri(system, os.path.join(out_dir))
        upload_file(r, state_path, state_dir, verbose=True)
        os.remove(state_path)

    def process_message(self, r: Reactor, *, user_data=None):
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

        challenge_dir = self.get_challenge_dir(out_dir_path, msg_challenge_problem)
        is_production = r.settings['xplan_config'].get('is_production', False)
        if not is_production:
            r.logger.info("Not in production mode")
            self.clear_assigned_containers(r, out_dir_system, challenge_dir)
        # preseed the state.json if it does not exist in the challenge_dir
        self.ensure_state_json(r, out_dir_system, challenge_dir)

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

    def finalize_message(self, r: Reactor, job: JobCompletionMessage, *, user_data=None):
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

        state_diff_path = os.path.join(archive_path, 'state.diff')
        state_diff_uri = make_agave_uri(archive_system, state_diff_path)
        r.logger.info("state_diff_uri = {}".format(state_diff_uri))
        if file_exists_at_agave_uri(r, state_diff_uri, verbose=True):
            r.logger.info("Downloading state diff from: {}".format(state_diff_uri))
            resp = download_file(r, state_diff_uri)
            if not resp.ok:
                raise XPlanDesignMessageError("Failed to download state diff at {}".format(state_diff_uri))
            self.rectify_state(r, resp.text, local_out, upload_system, upload_out_dir, challenge_problem)
        else:
            r.logger.info("No state diff found. Continuing as though job made no state changes...")

        # Do final processing
        self.handle_design_output(r,
                                  experiment_id,
                                  challenge_problem,
                                  self.get_lab_configuration(r, msg),
                                  local_out)
                                  #test_mode=test_mode)

        # Upload the finished experiment files
        r.logger.info("Upload:\n  from: {}\n  to: {}".format(
            local_out, upload_uri))
        upload_dir(r, local_out, upload_uri, verbose=True)
        r.logger.info("Upload: Complete")

        r.logger.info("Finalize ended with success")

    def rectify_state(self, r: Reactor, diff_str: str, local_out: str, upload_system: str, upload_path: str, challenge_problem: str):
        r.logger.info("Rectifying state...")
        challenge_dir = self.get_challenge_dir(upload_path, challenge_problem)
        challenge_state_uri = make_agave_uri(upload_system, os.path.join(challenge_dir, 'state.json'))
        if not file_exists_at_agave_uri(r, challenge_state_uri, verbose=True):
            r.logger.info("No challenge state found at {}. Continuing as though job state is true state...".format(challenge_state_uri))
            return

        resp = download_file(r, challenge_state_uri, verbose=True)
        if not resp.ok:
            raise XPlanDesignMessageError("Failed to download challenge state file at {}".format(challenge_state_uri))
        challenge_state = resp.json()
        
        state_diff = jp.JsonPatch.from_string(diff_str)
        r.logger.info("Found diff: {}".format(diff_str))

        # blindly patch the state with the diff
        r.logger.info("Patching state: {}".format(challenge_state))
        final_state = state_diff.apply(challenge_state)

        # HACK custom patch rules to account for running the same job back to back.
        # This will likely need more attention in the future.
        if 'experiment_requests' in final_state:
            # It is technically possible for duplicates to make it in via the diff patching.
            # Ensure unique experiments_requests list by stripping any duplicates.
            final_state['experiment_requests'] = list(set(final_state['experiment_requests']))

        r.logger.info("Final state: {}".format(final_state))
        with open(os.path.join(local_out, challenge_problem, 'state.json'), 'w') as f:
            f.write(json.dumps(final_state))


    def get_challenge_dir(self, out_dir, challenge_problem):
        return os.path.join(out_dir, challenge_problem)


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

        mock = r.settings['xplan_config'].get('mock', False)
        r.logger.info("Mock = {}".format(mock))
        submit_experiment(experiment_id, challenge_problem, lab_cfg, transcriptic_params, input_dir=out_dir, out_dir=out_dir, mock=mock)


class XPlanDesignMessageError(AbacoMessageError):
    pass
