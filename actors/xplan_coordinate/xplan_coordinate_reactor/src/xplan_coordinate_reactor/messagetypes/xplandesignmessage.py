from ..files import download_file, upload_file, download_dir, upload_dir, split_agave_uri, make_agave_uri, ensure_path_on_system, file_exists_at_agave_uri
from ..jobs import launch_job
from ..logs import log_info, log_error
from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict
import base64
from reactors.runtime import Reactor, agaveutils
from .jobcompletionmessage import JobCompletionMessage
from xplan_utils.helpers import ensure_experiment_dir, get_design_file_name, get_experiment_design, get_experiment_request
import arrow
import logging
import os
import shutil
import sys
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
        "max_run_time": "04:00:00",
        "memoryPerNode": "1GB",
        "nodeCount": 1,
        "processorsPerNode": 1,
        "archive": True,
        "archiveSystem": "data-tacc-work-jladwig",
        "archivePath": "xplan2/archive/jobs/job-${JOB_ID}",
        "inputs": [
            "experiment_dir",
            "state_json"
        ],
        "parameters": [
            "out_path",
            "lab_configuration",
            "experiment_id",
            "challenge_problem"
        ]
    })

    def ensure_state_json(self, r: Reactor, system, out_dir):
        state_uri = make_agave_uri(system, os.path.join(out_dir, 'state.json'))
        if file_exists_at_agave_uri(r, state_uri, verbose=True):
            return state_uri
        # this ensures the state json has the expected fields in it.
        # Our state merging during the finalize step need this to
        # avoid issues when multiple jobs are run back to back on a
        # challenge problem with no initial state.
        preseed_state = {
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
        return state_uri

    def upload_reactor_logs(self, r: Reactor, upload_system, upload_dir, upload_name):
        archive_uri = make_agave_uri(upload_system, upload_dir)
        # flush all logger handlers
        handlers = r.logger.handlers
        [h.flush() for h in handlers]
        for h in handlers:
            if isinstance(h, logging.FileHandler):
                h.flush()
                # FIXME
                # upload_file fileName field does not appear to
                # work as expected so just copy the file to the
                # desired name and upload that instead...
                shutil.copyfile(h.baseFilename, upload_name)
                upload_file(r, upload_name, archive_uri)
                os.remove(upload_name)

    def process_message(self, r: Reactor, timestamp, *, user_data=None):
        job_id = None
        try:
            msg = getattr(self, 'body')
            log_info(r, "Process xplan design message: {}".format(msg))

            msg_experiment_id = msg.get('experiment_id')
            msg_challenge_problem = msg.get('challenge_problem')
            msg_lab_configuration = msg.get('lab_configuration')
            msg_out_dir = msg.get('out_dir')
            (out_dir_system, out_dir_path) = split_agave_uri(msg_out_dir)
            archive_system = out_dir_system

            ensure_path_on_system(r, out_dir_system, out_dir_path, verbose=True)

            archive_name = "{}_{}".format(timestamp, msg_experiment_id)
            archive_base = os.path.join(out_dir_path, "archive", archive_name)
            ensure_path_on_system(r, archive_system, archive_base, verbose=True)
            archive_path = os.path.join(archive_base, "design_job")

            challenge_dir = self.get_challenge_dir(out_dir_path, msg_challenge_problem)
            # preseed the state.json if it does not exist in the challenge_dir
            state_uri = self.ensure_state_json(r, out_dir_system, challenge_dir)
            msg['state_json'] = state_uri

            # create the path that we will send as input to the design app
            experiments_dir = os.path.join(challenge_dir, 'experiments')
            experiment_path = os.path.join(experiments_dir, msg_experiment_id)
            ensure_path_on_system(r, out_dir_system, experiment_path, verbose=True)
            msg['experiment_dir'] = make_agave_uri(out_dir_system, experiment_path)
            # tell the app where to output the data that the finalize step
            # will merge with the actual out_dir agave uri
            msg['out_path'] = os.path.basename(out_dir_path.rstrip('/'))

            custom_job_spec = AttrDict(self.JOB_SPEC.copy())
            custom_job_spec['archiveSystem'] = archive_system
            custom_job_spec['archivePath'] = archive_path

            is_production = r.settings['xplan_config'].get('is_production', False)
            if not is_production:
                log_info(r, "Not in production mode. Setting test flag...")
                msg['xplan_test'] = True
                custom_job_spec['parameters'].append('xplan_test')

            if isinstance(msg_lab_configuration, str):
                # store this in the message in case we want to find it later
                msg['lab_configuration_uri'] = msg_lab_configuration
                # Force the lab_configuration to a dictionary
                msg_lab_configuration = self.get_lab_config_as_dict(r, msg)

            if not isinstance(msg_lab_configuration, dict):
                raise Exception("lab_configuration did not resolve to a dictionary")

            msg['lab_configuration'] = self.lab_config_to_base64(msg_lab_configuration)

            log_info(r, "Process xplan design message \n  Experiment ID: {}\n  Challenge Problem: {}\n  OutDir: {}\n  Data Path: {}\n  Archive Path: {}\n  Archive System: {}"
                .format(msg_experiment_id, msg_challenge_problem, msg_out_dir, out_dir_path, archive_path, archive_system))

            job_id = launch_job(r, msg, custom_job_spec, {
                "archive_system": archive_system,
                "archive_base": archive_base,
            })
            if (job_id is None):
                log_error(r, "Failed to launch job.")
                return None

            log_info(r, "Launched job {} in {} usec".format(job_id, r.elapsed()))
        except Exception as e:
            exc_info = sys.exc_info()
            log_error(r, e, exc_info=exc_info)
        finally:
            # write logs to archive
            self.upload_reactor_logs(r, archive_system, archive_base, 'process.log')
        return job_id

    def finalize_message(self, r: Reactor, job: JobCompletionMessage, process_data, *, user_data=None):
        try:
            msg = getattr(self, 'body')
            log_info(r, "Finalize xplan design message: {}".format(msg))

            out_uri = msg.get('out_dir')
            upload_system, out_path = split_agave_uri(out_uri)
            out_basename = os.path.basename(out_path.rstrip('/'))

            archive_system = job.get("archiveSystem")
            archive_path = job.get("archivePath")

            experiment_id = msg.get('experiment_id')
            challenge_problem = msg.get('challenge_problem')
            log_info(r, "challenge_problem = " + challenge_problem)
            archive_out_dir = os.path.join(archive_path, out_basename)
            upload_out_dir = os.path.join(out_path)

            archive_uri = make_agave_uri(archive_system, archive_path)
            log_info(r, "archive_uri = {}".format(archive_uri))

            upload_uri = make_agave_uri(upload_system, upload_out_dir)
            log_info(r, "upload_uri = {}".format(upload_uri))

            local_out = os.path.abspath(os.path.join(out_basename, challenge_problem))

            # Download the archived challenge directory
            log_info(r, "Download:\n  to: {}\n  from: {}".format(local_out, archive_uri))
            download_dir(r, archive_uri, local_out, verbose=True)

            state_diff_path = os.path.join(archive_path, 'state.diff')
            state_diff_uri = make_agave_uri(archive_system, state_diff_path)
            log_info(r, "state_diff_uri = {}".format(state_diff_uri))
            if file_exists_at_agave_uri(r, state_diff_uri, verbose=True):
                log_info(r, "Downloading state diff from: {}".format(state_diff_uri))
                resp = download_file(r, state_diff_uri)
                if not resp.ok:
                    raise XPlanDesignMessageError("Failed to download state diff at {}".format(state_diff_uri))
                self.rectify_state(r, resp.text, local_out, upload_system, upload_out_dir, challenge_problem)
            else:
                log_info(r, "No state diff found. Continuing as though job made no state changes...")

            lab_secrets = self.lab_config_from_base64(msg.get('lab_configuration'))
            # Do final processing
            self.handle_design_output(r,
                                    experiment_id,
                                    challenge_problem,
                                    lab_secrets,
                                    local_out)

            # Upload the finished experiment files
            log_info(r, "Upload:\n  from: {}\n  to: {}".format(local_out, upload_uri))
            upload_dir(r, local_out, upload_uri, verbose=True)
            log_info(r, "Upload: Complete")

            experiment_request = get_experiment_request(
                experiment_id, os.path.join(local_out, challenge_problem))
            if 'test_mode' in experiment_request['defaults']:
                test_mode = experiment_request['defaults']['test_mode']
            else:
                test_mode = False

            log_info(r, "Is Reactor Local? {}, Is test_mode? {}".format(r.local, test_mode))

            if not r.local and not test_mode:
                self.notify_control_annotator(r, experiment_id, challenge_problem, upload_uri)

            log_info(r, "Finalize ended with success")
        except Exception as e:
            exc_info = sys.exc_info()
            log_error(r, e, exc_info=exc_info)
        finally:
            # get log output from the original process step data
            d_archive_system = process_data['archive_system']
            d_archive_base = process_data['archive_base']
            # write logs to archive
            self.upload_reactor_logs(r, d_archive_system, d_archive_base, 'finalize.log')

    def rectify_state(self, r: Reactor, diff_str: str, local_out: str, upload_system: str, upload_path: str, challenge_problem: str):
        log_info(r, "Rectifying state...")
        challenge_dir = self.get_challenge_dir(upload_path, challenge_problem)
        challenge_state_uri = make_agave_uri(upload_system, os.path.join(challenge_dir, 'state.json'))
        if not file_exists_at_agave_uri(r, challenge_state_uri, verbose=True):
            log_info(r, "No challenge state found at {}. Continuing as though job state is true state...".format(challenge_state_uri))
            return

        resp = download_file(r, challenge_state_uri, verbose=True)
        if not resp.ok:
            raise XPlanDesignMessageError("Failed to download challenge state file at {}".format(challenge_state_uri))
        challenge_state = resp.json()

        state_diff = jp.JsonPatch.from_string(diff_str)
        log_info(r, "Found diff: {}".format(diff_str))

        # blindly patch the state with the diff
        log_info(r, "Patching state: {}".format(challenge_state))
        final_state = state_diff.apply(challenge_state)

        # HACK custom patch rules to account for running the same job back to back.
        # This will likely need more attention in the future.
        if 'experiment_requests' in final_state:
            # It is technically possible for duplicates to make it in via the diff patching.
            # Ensure unique experiments_requests list by stripping any duplicates.
            final_state['experiment_requests'] = list(set(final_state['experiment_requests']))

        log_info(r, "Final state: {}".format(final_state))
        with open(os.path.join(local_out, challenge_problem, 'state.json'), 'w') as f:
            f.write(json.dumps(final_state))

    def get_challenge_dir(self, out_dir, challenge_problem):
        return os.path.join(out_dir, challenge_problem)

    # TODO resolve how multiple labs work in this system

    def lab_config_to_base64(self, lab_config):
        lc_payload = json.dumps(lab_config, separators=(',', ':'))
        return base64.b64encode(lc_payload.encode('ascii')).decode('ascii')

    def lab_config_from_base64(self, lc_str):
        return json.loads(base64.b64decode(lc_str.encode('ascii')).decode('ascii'))

    def get_lab_config_as_dict(self, r: Reactor, msg):
        lab_config = msg.get('lab_configuration')
        if isinstance(lab_config, str):
            cfg_uri = lab_config
        elif isinstance(lab_config, dict):
            return lab_config
        else:
            raise XPlanDesignMessageError("invalid lab_configuration")

        cfg_resp = download_file(r, cfg_uri)
        if not cfg_resp.ok:
            raise XPlanDesignMessageError("Failed to download lab_configuration from {}".format(cfg_uri))
        return cfg_resp.json()

    def handle_design_output(self, r: Reactor, experiment_id, challenge_problem, lab_cfg, out_dir: str):

        params = design_to_parameters(experiment_id,
                             challenge_problem,
                             lab_cfg,
                             input_dir=out_dir,
                             out_dir=out_dir,
                             logger=r.logger)
        log_info(r, "design_to_parameters:\n{}\n{}\n".format(experiment_id, params))

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
        log_info(r, "Mock = {}".format(mock))
        submit_experiment(experiment_id,
                          challenge_problem,
                          lab_cfg,
                          transcriptic_params,
                          input_dir=out_dir,
                          out_dir=out_dir,
                          mock=mock,
                          logger=r.logger)

    def notify_control_annotator(self, r: Reactor, experiment_id, challenge_problem, upload_uri):
        # Send SR Reactor a response with path to design
        design_path = "{}/{}/experiments/{}/design_{}.json".format(upload_uri, challenge_problem, experiment_id, experiment_id)
        log_info(r, "Sending design to SRR: {}".format(design_path))
        ag = r.client  # Agave client
        ag.token = os.getenv('_abaco_access_token')

        resp = ag.actors.sendMessage(
            actorId="control-annotator.prod",
            body={'message': {
                "xplan_uri": design_path,
                "set_submit": True
            }},
            environment={'x-session': ''})
        exid = resp.get('executionId', 'Message Failed')
        log_info(r, "control-annotator.prod Execution Id: {}".format(exid))


class XPlanDesignMessageError(AbacoMessageError):
    pass
