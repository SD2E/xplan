import random
from ast import literal_eval as make_tuple
import logging
import shutil
from collections import Counter
import time
import uuid
import os
from typing import Dict, List, Any, Optional, Iterable
import warnings
import gc
import copy
import tempfile


import json
import numpy as np
from scipy import stats
import pandas as pd


l = logging.getLogger(__file__)
#l.setLevel(logging.DEBUG)


from xplan_models.condition import (
    Conditions, ConditionSpace, Record, Statistic
)

from xplan_models.model_utils import get_old_sub_model, keyin
from pysd2cat.analysis import correctness
from xplan_experiment_analysis import read_sd2_dataframe
try:
    from xplan_train_bayesian_model_helper import bayes
except ImportError as e:
    l.exception("Could not import bayes.py")
    raise e



def get_model_file_name(model_id):
    return "model_" + model_id + ".json"

class Model(dict):
    """
    A model used to generate experiment requests.

    Attributes
    ~~~~~~~~~~
        models: list of submodels
        condition_space: ConditionSpace
        data_used: List[]
        id: str
    """

    # Question: wouldn't it have been possible to have model_dir,
    # model_id, and condition_space be normal keyword arguments that
    # default to None, and check for none, instead of using **kwargs?

    # Another: pylint complains that we are not calling
    # __super__.init().  is this a problem? If not, we could disable
    # this check, and add a comment to explain why we didn't.
    # [2019/09/24:rpg]
    def __init__(self, *args, **kwargs): # pylint: disable=unused-argument
        """
        Initialize from either a serialized set of objects from a directory,
        or as a new model.

        Parameters
        ~~~~~~~~~~
            model_dir: str (pathname)
                Location from which to deserialize the model.
           model_id: string-able
                An identifier that can be embedded in a string.

            condition_space:
                Alternative means of initializing the data structure.
        """
        if 'model_dir' in kwargs:
            self.deserialize(kwargs['model_dir'], kwargs['model_id'])
        else:
            if isinstance(kwargs['condition_space'], ConditionSpace):
                condition_space = copy.deepcopy(kwargs['condition_space'])
            else:
                condition_space = ConditionSpace(kwargs['condition_space'])
            ## Add statistics tracked to condition space
            condition_space.statistics = self.declare_statistics()

            condition_space.set_prior(bins=1)
            kwargs['condition_space'] = condition_space
            self.initialize(kwargs)

    def declare_statistics(self):
        """
        Return statistics declarations for condition space.
        """
        return {}

    # AFAICT, this is only called when the Model is being
    # deserialized, and never if it's a new object.
    def initialize(self, kwargs):
        """
        If kwargs has an id, then this is an object being deserialized,
        otherwise it is a new object.  It will have a condition_space
        if it is a top-level model.
        """
        super().__init__(**kwargs)
        if 'id' not in kwargs:
            self['id'] = time.strftime("%Y_%m_%d_%H_%M_%S") + '_' \
                         +  self.__class__.__name__ + '_' + uuid.uuid1().hex

        #print("Initializing " + str(self['id']))

        self['type'] = self.__class__.__name__
        if 'data_used' not in self:
            self['data_used'] = []


    def _set_distribution(self):
        pass


    def decrement_data_cache(self, group):
        self['condition_space'].decrement_data_cache(group)

    def update_data_cache(self, data_groups):
        """
        If drawing samples from cached data, record in condition
        space which regions have data.
        """
        self['condition_space'].update_data_cache(data_groups)

    # Request: could you amplify the documentation? I don't really
    # understand the return description in the docstring. [2019/09/24:rpg]
    # pylint: disable=redefined-outer-name
    def draw_samples(self, num_samples, random, factors,
                     logger, using_data_cache=False):
        """
        Sample gates, but return a list of constituent strains
        """
        cs = self['condition_space']
        logger.debug("Marginalizing over " + str(factors))
        distribution = self.normalize(cs.marginalize(factors, self.sampling_metric,
                                                     using_data_cache=using_data_cache),
                                      self.sampling_metric).reset_index()
        logger.debug("Sampling Conditions: " + str(distribution))


        if distribution is None or len(distribution) == 0:
            raise Exception("Cannot sample from an empty distribution")

        conds = distribution.iloc[:,:-1]
        dist = distribution.iloc[:,-1]

        l.debug(self.__class__.__name__)
        if dist.isnull().all() or self.__class__.__name__ == 'RandomModel':
            l.debug("Sampling Uniformly")
            weights = [1.0/len(conds) for x in range(len(conds))]
        else:
            weights = dist

        if self.__class__.__name__ == 'DeterministicModel':
            samples = conds.loc[0:0, :]
        else:
            l.debug("Sample weights: %s", str(weights))
            samples = conds.sample(n=num_samples, replace=True, weights=weights)
        logger.debug("Samples: %s", str(samples))
        return samples

    def extend_strain_to_od_strain(self, strain, ods) -> List[Dict[str, Any]]:
        """
        Return a list of new dictionaries with all combinations of strain and ods.
        """
        return [ {"od" : od, "strain" : strain} for od in ods]



    def serialize(self, out_dir: str) -> str:
        """
        Model is JSON, except for the Panda for data in condition space.
        Model may also be hierarchical.  Save each model as JSON.  For
        condition space, save it as a JSON and CSV.  Replace submodels by their
        ids.
        """
        model_file_stash = os.path.join(out_dir, "model_" + self['id']+".json")

        # Recurse models and replace with id
        if 'models' in self:
            models = {}
            for model in self['models']:
                #print("Serializing submodel: " + model['type'])
                model.serialize(out_dir)
                models[model['id']] = model
            self['models'] = { k : v['type'] for k,v in models.items() }

        # Serialize condition space separately
        cs = self['condition_space']
        cs.serialize(os.path.join(out_dir, self['id']))
        del self['condition_space']

        # Serialize test_set space separately
        ts: Optional[pd.DataFrame]
        try:
            ts = self['test_set']
            if ts is None:
                raise KeyError("No test set.")
            ts.to_csv(os.path.join(out_dir, "%s_test_set.csv"%self['id']))
            del self['test_set']
        except KeyError:
            l.warning("No test set in this model object.")
            ts = None
            warnings.warn("No test_set in this model object.")

        # Serialize JSON elements
        with open(model_file_stash, 'w') as f:
            json.dump(self, f, sort_keys=True, indent=2, separators=(',', ': '))

        # Rebuild model
        self['condition_space'] = cs
        self['test_set'] = ts
        if 'models' in self:
            self['models'] = models

        return model_file_stash

    def deserialize(self, model_dir: str, model_id) -> None:
        """
        Rebuild model top down by replacing submodel ids by objects and attaching
        condition space.
        """
        #print("Deserializing " + str(model_id))
        model_file_stash: str = os.path.join(model_dir, get_model_file_name(model_id))
        condition_space = ConditionSpace(os.path.join(model_dir, model_id + '.json'))
        with open(model_file_stash, 'r') as f:
            kwargs = json.load(f)
            kwargs['condition_space'] = condition_space
            self.initialize(kwargs)

        #print("Deserializing submodels of " + str(model_id))
        if 'models' in self:
            models = []
            for submodel_id, submodel_type in self['models'].items():
                #print("submodel_type: " + str(submodel_type))
                submodel = eval(submodel_type)(model_dir=model_dir, model_id=submodel_id)
                models.append(submodel)
            self['models'] = models


        #self.set_id(model_id)

    def select_data_files(self, data: Iterable[str]) -> List[str]:
        """Return a list of data files.

        Used to handle the difference between models that use the 
        raw, versus the aggregated (accuracy) files.

        """
        def get_accuracy_file(x: str) -> str:
            """
            Add accuracy directory to path (``x``), and return it.
            """
            data_path = "/".join(x.split("/")[0:-1])
            data_file = x.split("/")[-1]
            acc_file = os.path.join(data_path, 'correctness', data_file)
            if not os.path.exists(acc_file):
                FrequentistModel.compute_accuracy(x)

            return acc_file

        ## Peek at first file to see if it is raw or summary data
        df = pd.read_csv(data[0])
        if 'mean_correct_classifier_live' in df.columns:
            # it is summary data, use as is
            return data
        else:
            # compute the summary from raw data and use that 
            data = [ get_accuracy_file(x) for x in data]
            return data

    # pylint: disable=too-many-arguments
    def train(self,
              new_data,
              conditions,
              old_model,
              app_id=None,
              analysis_config=None,
              is_local=False,
              out_dir: Optional[str]=None, # FIXME: This is not used!
              webhook = None,
              client = None,
              logger=l,
              iteration=None, 
              **kwargs):
        model_name = self.__class__.__name__
        logger.info("Training %s", model_name)
        logger.debug("analysis_conifig = %s", str(analysis_config))
        model_config = analysis_config
        logger.debug("Retrieved model_config = %s", str(model_config))

        if analysis_config:
            app_id = analysis_config.get('appId', None)
            work_dir = analysis_config.get('work_dir', None)
        if app_id is None:
            if logger is not None:
                logger.error("%s app id is not configured", model_name)
            return
        if work_dir is None:
            if logger is not None:
                logger.error("%s work_dir is not configured", model_name)
            return

        del analysis_config['work_dir']

        new_data = self.select_data_files(new_data)

        if old_model is not None:
            old_model_id = old_model['id']
            logger.debug("old model uses data: %s", str(old_model['data_used']))
            new_data = [d for d in new_data if d not in old_model['data_used']]
            self['data_used'] = old_model['data_used'].copy()
            self['old_model'] = old_model_id
            self['condition_space'].data = old_model['condition_space'].data
        else:
            old_model_id = None
            self['old_model'] = None
            
        logger.debug("model already trained on old data: %s", str(self['data_used']))

        if not new_data:
            logger.info("Skipping Training, no new data ...")
            return


        logger.debug("training model on new data: %s", str(new_data))
        self['data_used'].extend(new_data)

        logger.debug("old_id: %s new_id: %s", str(old_model_id), self['id'])
        assert old_model_id != self['id']

        # Create a run ID in case this needs to be linked with anything
        # when the results are returned
        run_id = uuid.uuid1().hex
        self['training'] = run_id
        if not is_local:
            #webhook = robj.create_webhook(permission='EXECUTE', maxuses=1)
            #webhook = 'https://webhook.site/af14b665-c8a9-4c59-8667-3e5cdf6017d6'

            model_config['inputs'] = {}
            model_config['parameters'] = {
                'model' : self['id'],
                'conditions' : ",".join(conditions),
                'data' : ",".join(new_data),
                'webhook': webhook,
                'run_id': run_id,
                'work_dir' : work_dir
            }
            if old_model_id is not None:
                model_config['parameters']['prior_model'] = old_model_id

           
            logger.info("Submitting job {}".format(model_config))
            job_info = client.jobs.submit(body=model_config)
            logger.info("Job info {}".format(job_info))

        else:
            logger.warn("Cannot Train via Reactor Locally (Run Manually).")


    def update_from_training(self, robj, training_output, out_dir):
        pass

    def normalize(self, df: pd.DataFrame, norm_column: str) -> pd.DataFrame:
        "Normalize column of dataframe."
        return df[norm_column].apply(lambda x: x/x.sum(), axis=0)


    def __hash__(self):
        return 1


    def add_regions(self, data: List[str], logger=l) -> List[str]:
        """
        for each file in data list, add the region to each point.
        Writes set of new files, and returns list of the file names.
        """
        def get_region_file_name(data_file):
            path = "/".join(data_file.split("/")[:-1])
            filename = data_file.split("/")[-1]
            new_path = os.path.join(path, self.__class__.__name__)
            if not os.path.exists(new_path):
                os.mkdir(new_path)
            new_filename = os.path.join(new_path, filename)
            return new_filename

        condition_map = {
#            Conditions.TEMPERATURE : 'inc_temp',
            Conditions.CORRECTNESS : 'mean_correct_classifier_live',
#            Conditions.STRAIN : 'strain_name',
#            Conditions.DURATION : 'inc_time_2'
        }
        logger.debug(data)
        new_files = []
        for d in data:
            new_filename = get_region_file_name(d)
            logger.debug("Adding regions to create new file: " + new_filename)
            if not os.path.exists(new_filename):
                df = pd.read_csv(d, dtype={'od': float, 'input' : str, 'output' : str}, index_col=0)
                logger.debug("Opened: " + d)
                try:
                    logger.debug("Processing factors: " + str(self['condition_space'].factors))
                    for fname, factor in self['condition_space'].factors.items():
                        if fname in condition_map:
                            df.loc[:,fname] = df[condition_map[fname]].apply(map_value)
                            df.loc[:,condition_map[fname]] = df[condition_map[fname]].apply(map_value)


                        bounds = factor.get_discretization_names()
                        if len(bounds) > 1:
                            df.loc[:, bounds[0]] = df[fname].apply(lambda x: factor.get_lb_region(x))
                            df.loc[:, bounds[1]] = df[fname].apply(lambda x: factor.get_ub_region(x))
                    logger.debug("Added Regions ..." )
                except Exception as e:
                    logger.exception("Failed to add regions: " + str(e))
                    raise
                
                # Drop controls
                df = df.dropna(subset=['gate'])
                df.to_csv(new_filename)
                df = None
                logger.debug("Wrote " + new_filename)
                gc.collect()
            else:
                logger.warn("File exists ...")
            new_files.append(new_filename)
            logger.debug(new_files)
        return new_files

    def get_records(self, df, correctness='mean_correct_classifier_live', iteration=None):
        """

        Each record corresponds to a sample, so don't need to aggregate them here.  They will
        be aggregated when added to the condition space.

        """

        records = []
        factors = self['condition_space'].factors
        statistics = self['condition_space'].statistics
        condition_map = {
#            Conditions.TEMPERATURE : 'inc_temp',
            Conditions.CORRECTNESS : correctness,
#            Conditions.STRAIN : 'strain_name',
#            Conditions.DURATION : 'inc_time_2',
            }
        condition_value_map = {
            "warm_30" : 30,
            "warm_37" : 37
            }

        for i, row in df.iterrows():
            #print(row)
            record_factors = {}
            record_statistics = {}
            for name, factor in factors.items():
                #print("Getting factor value " + str(factor))

                if name in condition_map:
                    mapped_name = condition_map[name]
                elif name in df.columns:
                    mapped_name = name
                elif factor['dtype'] == 'float':
                    mapped_name = name
                else:
                    mapped_name = None

                value = None
                if mapped_name is not None and mapped_name in df.columns:
                    value = row[mapped_name]
                    if value in condition_value_map:
                        value = condition_value_map[value]
                    elif name == Conditions.DURATION:
                        if isinstance(value, str):
                            value = float(value.split(':')[0])
                elif mapped_name is not None and factor['dtype'] == 'float':
                    # Take mean value of upper and lower to make sure its in region
                    discretized_names = factor.get_discretization_names()
                    value = np.mean([ row[n] for n in discretized_names])

                record_factors[name] = value

            #record_factors['strain'] = 'UWBF_' + record_factors['gate'] + '_' + record_factors['input']
            for name, stat in statistics.items():
                #print("Getting factor value " + str(factor))

                if name == Conditions.COUNT:
                    # Count samples only once, and ignore 'count' in df which is count of events
                    record_statistics[name] = 1
                    continue
                if name == Conditions.ITERATION:
                    # Count samples only once, and ignore 'count' in df which is count of events
                    record_statistics[name] = iteration
                    continue

                
                if name in condition_map:
                    mapped_name = condition_map[name]
                elif name in df.columns:
                    mapped_name = name
                else:
                    mapped_name = None

                value = None
                if mapped_name is not None and mapped_name in df.columns:
                    value = row[mapped_name]
                    if value in condition_value_map:
                        value = condition_value_map[value]
                record_statistics[name] = value

            records.append(Record(factors = record_factors, statistics = record_statistics))

        return records

    

class MCMCBayesianModel(Model):
    """
    Bayesian model trained by MCMC using PyMC3.

    Attributes
    ~~~~~~~~~~
        sampling_metric: str
            Defaults to ``Conditions.ENTROPY``
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sampling_metric = Conditions.ENTROPY

    def declare_statistics(self) -> Dict[str, Statistic]:
        """
        Return statistics declarations for condition space.
        """
        statistics = {
            Conditions.COUNT : Statistic(name=Conditions.COUNT, default=0.0, dtype="float"),
            Conditions.ENTROPY : Statistic(name=Conditions.ENTROPY, default=1.0, dtype="float"),
            Conditions.BAYES_CORRECTNESS : Statistic(name=Conditions.CORRECTNESS, default=None, dtype="float"),
            Conditions.CORRECTNESS : Statistic(name=Conditions.CORRECTNESS, default=None, dtype="float"),
            Conditions.STANDARD_ERROR : Statistic(name=Conditions.STANDARD_ERROR, default=None, dtype="float"),
            Conditions.COUNT : Statistic(name=Conditions.COUNT, default=0.0, dtype="float"),
            Conditions.SUM_SQ_DIFF : Statistic(name=Conditions.SUM_SQ_DIFF, default = None, dtype="float"),
            Conditions.STANDARD_DEV : Statistic(name=Conditions.STANDARD_DEV, default = None, dtype="float"),
            Conditions.ITERATION : Statistic(name=Conditions.ITERATION, default=None, dtype="float")
            }
        return statistics

    def train(self,
              new_data: List[str],
              out_dir: str,
              old_model: Optional[str] = None, 
              in_process=False,
              is_local=False,
              iteration: Optional[int]=None, 
              **kwargs):
        """
        Parameters
        ~~~~~~~~~~
        new_data : List[str]
            A list of names of files containing either raw data or summary data
        old_model : str, optional
            Filename containing previous MCMCBayesianModel information, including previous
            scores.  Allows us to track accumulation of information.
        in_process : bool
            Run this locally, or do something with reactors (?)
        is_local : bool
            Not sure about the relationship with `in_process`
        iteration : int, optional
            Used to index training records over time.
        out_dir : str
            Where do we write the xplan_experiment_analysis model information?
        """
        l.info("Training MCMC Model")
        conditions = self['condition_space'].get_region_descriptions(use_values=True) #+ ['gate', 'input']
        l.debug("Using Conditions: %s", str(conditions))

        new_data = self.select_data_files(new_data)

        if not in_process and not is_local:
            super().train(new_data,
                          conditions,
                          old_model,
                          is_local=is_local,
                          out_dir=out_dir,
                          iteration=iteration,
                          **kwargs)
        else:
            new_data = self.add_regions(new_data) # add region info to the data files.
            self.train_in_process(new_data, conditions, out_dir=out_dir, iteration=iteration, **kwargs)

    def train_in_process(self, new_data, conditions, out_dir, do_train=True, iteration=None, **kwargs):
        """
        Parameters
        ~~~~~~~~~~
        new_data : List[str]
            Files containing new data for training.
        conditions : ?
            Condition space, I think
        out_dir : str
            Where do we write the xplan_experiment_analysis models (they will
            be written in ``cache`` and ``cache-prior`` subdirectories).
        do_train : bool, optional
            Debugging flag that can be used to disable actual training.
        iteration : int, optional
            Counter for storing.
        """
        metadata = self.get_metadata_for_data(new_data, factors=conditions)

        assert out_dir
        if not os.path.exists(out_dir):
            os.mkdir(out_dir)
        model = 'cache'
        model_pathname= os.path.join(out_dir, model)
        prior_model = "{}-prior".format(model)
        prior_model_path = "{}-prior".format(model_pathname)

        if do_train or not os.path.exists(model_pathname):
            try:
                l.debug("Removing: " + prior_model_path)
                shutil.rmtree(prior_model_path)
            except FileNotFoundError:
                pass

            if  os.path.exists(model_pathname) and len(os.listdir(model_pathname)) == 0:
                shutil.rmtree(model_pathname)

            try:
                if os.path.exists(model_pathname):
                    l.debug("Moving: " + model_pathname + " to " + prior_model_path)
                    shutil.move(model_pathname, prior_model_path)
                else:
                    prior_model = None
            except FileNotFoundError:
                os.mkdir(prior_model_path)

        train_data: str
        if len(new_data) == 1:
            train_data = new_data[0]
        else:
            dfs = [read_sd2_dataframe(data) for data in new_data]
            df = pd.concat(dfs, 0)
            train_data = tempfile.mkstemp(suffix=".csv")
            df.to_csv(train_data)
 
        bayes.train(train_data, base_dir=out_dir, prior_model=prior_model, model=model,
                    conditions=conditions)

        regions = self['condition_space'].get_region_descriptions(use_values=False) # + ['gate', 'input']

        query = self['condition_space'].get_regions(regions)

        l.debug("Query: " + str(query))
        result = bayes.evaluate(query, model=model, base_dir=out_dir)
        l.debug("result: " + str(result))


        ## Push result into the condition space
        rows = pd.read_csv(result, dtype={'od': float, 'input' : str, 'output' : str}, index_col=0).to_dict("records")

        for row in rows:
            records = self.get_records(row)
            for record in records:
                l.debug("Adding Record: " + str(record))
                try:
                    self['condition_space'].add_record(record)
                except Exception as e:
                    l.debug("Failed to add record: " + str(e))

        ## Track data point stats
        for data_file in new_data:
            correctness_df = pd.read_csv(data_file,  dtype={'od': float, 'input' : object, 'output' : object})
            records = super().get_records(correctness_df, correctness='mean_correct_classifier_live')
            for record in records:
                l.debug("Adding record: " + str(record))
                try:
                    self['condition_space'].add_record(record)
                except Exception as e:
                    l.debug("Failed to add record: " + str(e))
            


    def update_from_training(self, robj, training_output, out_dir):
        robj.logger.debug("MC:" + str(self))
        run_id = training_output['run_id']
        robj.logger.debug("run_id: " + str(run_id))
        if 'training' in self:
            robj.logger.debug("expected run_id: " + str(self['training']))
            if run_id != self['training']:
                return
        else:
            return

        robj.logger.debug("Updating based upon Training MCMC Model")
        scores = training_output['scores']
        #self['scores'] = {}

        records = self.get_records(scores)
        for record in records:
            try:
                self['condition_space'].add_record(record)
            except Exception as e:
                    robj.logger.exception("Failed to add record: " + str(e))                

        if 'training' in self:
            robj.logger.debug("Removing training tag: " + str(self['training']))
            del self['training']

    def get_metadata_for_data(self, data: List[str], factors=None) -> pd.DataFrame:
        metadata = pd.DataFrame()
        l.debug(data)
        for d in data:
            df = pd.read_csv(d, dtype={'od': float, 'input' : str, 'output' : str})
            l.debug(df)
            metadata = metadata.append(bayes.get_metadata_for_data(df, factors=factors), ignore_index=True)
        return metadata

    def get_records(self, row):
        """
        Convert learner output for region to a record for the condition space.
        """
        
        condition_map = {
            #Conditions.GATE : 'gate',
            #Conditions.TEMPERATURE : 'inc_temp',
            #Conditions.DURATION : 'inc_time_2',
            Conditions.BAYES_CORRECTNESS : 'bayes_est_prob_correct',
            Conditions.ENTROPY : 'bayes_est_ent_p_correct'
            }
        condition_value_map = {
            
            }

        records = []
        #print("Condition Space: " + str(self['condition_space']))
        factors = self['condition_space'].factors
        #print("Condition Space: " + str(self['condition_space']))
        #print("Checking factors " + str(factors))

        l.debug("Input Row: " + str(row))

        record_factors = {}
        record_statistics = {}
        for name, factor in factors.items():
            #l.info("Getting factor value " + str(factor))

            if name in condition_map:
                mapped_name = condition_map[name]
            else:
                mapped_name = name

            value = None
            if mapped_name is not None and factor['dtype'] != 'float':
                value = row[mapped_name]
                if value in condition_value_map:
                    value = condition_value_map[value]
            elif mapped_name is not None and factor['dtype'] == 'float':
                #  Take mean value of upper and lower to make sure its in region
                discretized_names = factor.get_discretization_names()
                value = np.mean([ row[n] for n in discretized_names])

            record_factors[name] = value

            #record_statistics[Conditions.COUNT] = 1
        record_statistics[Conditions.BAYES_CORRECTNESS] = row[condition_map[Conditions.BAYES_CORRECTNESS]]
        record_statistics[Conditions.ENTROPY] = row[condition_map[Conditions.ENTROPY]]
                #record_statistics[Conditions.STANDARD_ERROR] = stats.sem(v['truthtable_correct'])
            #if 'correct_rankings' in v:
            #    record_statistics['rank_mean'] = np.mean(v['correct_rankings'])
            #    record_statistics['rank_error'] = stats.sem(v['correct_rankings'])
            #l.info("Factors:  " + str(record_factors))
            #l.info("Statistics: " + str(record_statistics))
        record = Record(factors = record_factors, statistics = record_statistics)
        records.append(record)

        return records


    def _set_distribution(self) -> None:
        """
        Get distibution over gates to drive sample selection. Marginalizes
        over everything except the gate
        """
        cs = self['condition_space']
        #print(cs)
        gates = self['condition_space'].get_factor_values(Conditions.GATE)
        if len(gates) > 0 and Conditions.ENTROPY in cs.get_statistics():
            self['dist_gates'] = gates
            self['probability'] = self.normalize(cs.marginalize([Conditions.GATE], Conditions.ENTROPY), Conditions.ENTROPY)['sum']
        else:
            self['dist_gates'] = gates
            self['probability'] = [ 1.0/len(gates) for x in gates]

    def serialize(self, out_dir: str) -> str:
        """
        If xplan_experiment_analysis model information is available in ``'cache_dir'``
        key, serialize it as a zipfile.
        """
        if 'cache_dir' not in self or self['cache_dir'] is None:
            raise ValueError("There should be a cache_dir stored in this model: %s"%str(self))
        cache_dir: str = self['cache_dir']
        cache_name: str = os.path.basename(os.path.normpath(cache_dir))
        shutil.make_archive(os.path.join(out_dir, "%s-%s"%(self['id'], cache_name)), # dest
                            'zip',
                            # parent of cache
                            os.path.abspath(os.path.join(cache_dir, '../')),
                            # relative name
                            cache_name)
        return super().serialize(out_dir)

class ScoreModel(Model):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sampling_metric = Conditions.RANK_ERROR
        l.debug("ScoreModel Statistics: " + str(self['condition_space'].statistics))

    def declare_statistics(self):
        """
        Return statistics declarations for condition space.
        """
        statistics = {
            Conditions.CORRECTNESS : Statistic(name=Conditions.CORRECTNESS, default=None, dtype="float"),
            Conditions.STANDARD_ERROR : Statistic(name=Conditions.STANDARD_ERROR, default=None, dtype="float"),
            Conditions.COUNT : Statistic(name=Conditions.COUNT, default=0.0, dtype="float"),
            Conditions.SCORE : Statistic(name=Conditions.SCORE, default=None, dtype="float"),
            Conditions.RANK_ERROR : Statistic(name=Conditions.RANK_ERROR, default=None, dtype="float"),
            Conditions.SUM_SQ_DIFF : Statistic(name=Conditions.SUM_SQ_DIFF, default = None, dtype="float"),
            Conditions.STANDARD_DEV : Statistic(name=Conditions.STANDARD_DEV, default = None, dtype="float"),
            Conditions.ITERATION : Statistic(name=Conditions.ITERATION, default=None, dtype="float")
            }
        return statistics
    
        



    # pylint complains that this method's arguments are not the same
    # as the superclass's. I don't know if that's just a style thing
    # or if it's a real problem. [2019/09/24:rpg]
    def train(self,
              new_data,
              compute_accuracy=False,
              old_model=None,
              logger=l,
              is_local=False,
              analysis_config=None,
              in_process=False,
              webhook=None,
              client=None,
              out_dir=None,
              iteration=None):
        logger.info("Training Score Model")
        logger.debug("out_dir = %s", str(out_dir))
        conditions = self['condition_space'].get_region_descriptions(use_values=False)
        l.debug("Using Conditions: " + str(conditions))
        l.debug("Using Statistics: " + str(self['condition_space'].statistics))

        # Need to add region information to the data
        if not in_process and not is_local:
            # Need to add region information to the data
            new_data = self.add_regions(new_data)

            super().train(new_data,
                          conditions,
                          old_model,
                          is_local=is_local,
                          analysis_config=analysis_config,
                          out_dir=out_dir,
                          webhook=webhook,
                          client = client,
                          logger=logger,
                          iteration=None)
        else:
            summary_data = self.select_data_files(new_data)
            summary_data = self.add_regions(summary_data)
            
            # Need to add region information to the data
            new_data = self.add_regions(new_data)

            #new_data = self.add_regions(new_data)
            self.train_in_process(new_data, summary_data, conditions, logger=logger, out_dir=out_dir, iteration=iteration)



    def add_histograms(self, new_data, out_dir='scores', logger=l, conditions=None):
        try:
            from xplan_train_circuit_scoring_model_helper import scores
        except ImportError as e:
            l.warn("Could not import scores.py")
            raise e
        
        logger.debug("Adding histograms: " + str(new_data))
        #l.info("out_dir = " + str(out_dir))
        logger.debug("Using Conditions: " + str(conditions))
        scores.update_histograms_from_files(new_data, out_dir, out_dir, conditions=conditions)

    def compute_scores(self, new_data, metadata, out_dir='scores', logger=l, conditions=None):
        try:
            from xplan_train_circuit_scoring_model_helper import scores
        except ImportError as e:
            l.warn("Could not import scores.py")
            raise e

        
        logger.debug("Computing scores ...")
        #gates = metadata.gate.dropna().unique() #scores.get_circuits_from_data(new_data)
        # Resample scores and get paths to files storing scores, use metadata to limit cases considered
        logger.debug("Scoring: " + str(metadata))
        score_files = scores.score_circuits(out_dir, metadata, conditions)
        return score_files

    def train_on_scores(self, new_data, summary_data, score_files, metadata, iteration=None):
        l.debug("Training on Scores ...")
        l.debug("new_data: " + str(new_data))
        
        ## Add correctness and count for data points in new_data
        for data_file in summary_data:
            correctness_df = pd.read_csv(data_file,  dtype={'od': float, 'input' : object, 'output' : object})
            #if 'mean_correct_classifier_live' in correctness_df:
            records = super().get_records(correctness_df, correctness='mean_correct_classifier_live', iteration=iteration)
            for record in records:
                l.debug("Adding record: " + str(record))
                try:
                    self['condition_space'].add_record(record)
                except Exception as e:
                    l.exception("Failed to add record: " + str(e))
        
        ## Add score info for each region in metadata      
        for gate, savefile in score_files.items():

            ## Get record for each data point
            records = self.get_records(savefile, metadata)
            l.debug("records: " + str(records))
            l.debug("statistics: " + str(self['condition_space'].statistics))
            for record in records:
                try:
                    self['condition_space'].add_record(record)
                except Exception as e:
                    l.exception("Failed to add record: " + str(e))


    def train_in_process(self, new_data, summary_data, conditions, logger=l, iteration=None, out_dir=None):
        logger.debug("Training in process ... " )
        
        
        self.add_histograms(new_data, logger=logger, out_dir=out_dir, conditions=conditions)

        ## Get score files with the scores for each case.  The metadata includes all cases
        ## where new_data updated the scores.
        
        metadata = self.get_metadata_for_data(new_data, factors=conditions)
        logger.debug("metadata: " + str(metadata))
        
        score_files = self.compute_scores(new_data, metadata, out_dir=out_dir, logger=logger, conditions=conditions)
        
        self.train_on_scores(new_data, summary_data, score_files, metadata, iteration=iteration)


    def get_metadata_for_data(self, data, factors=None):
        """
        Extract metadata needed by Scoring from the data.
        Use factors to select the right columns from data.
        """
        try:
            from xplan_train_circuit_scoring_model_helper import scores
        except ImportError as e:
            l.warn("Could not import scores.py")
            raise e

        metadata = pd.DataFrame()
        for d in data:
            df = pd.read_csv(d, dtype={'od': float, 'input' : str, 'output' : str})
            metadata = metadata.append(scores.get_metadata_for_data(df, factors=factors), ignore_index=True)
        return metadata


    def update_from_training(self, robj, training_output, out_dir):
        robj.logger.debug("Score: " + str(self))
        run_id = training_output['run_id']
        robj.logger.debug("run_id: " + str(run_id))
        if 'training' in self:
            robj.logger.debug("expected run_id: " + str(self['training']))
            robj.logger.warn("Are run_ids equal: " + str(run_id == self['training']))
            if run_id != self['training']:
                robj.logger.warn("Got mismatched run_id: " + str(run_id))
                return
        else:
            robj.logger.warn("Got unexpected run_id: " + str(run_id))
            return

        robj.logger.debug("Updating based upon Training Score Model")
        scores = training_output['scores']
        #self['scores'] = {}
        for gate, savefile in scores.items():
            robj.logger.debug("Updating score for gate: " + gate)

            if robj.local:
                # Need to access file relative to local storage
                score_file = os.path.join(out_dir, savefile)
            else:
                score_file = savefile


            #Score file might not exist yet b/c need to copy from another system
            timeouts = 0
            while not os.path.exists(score_file):
                if timeouts > 5:
                    raise Exception("Timed out waiting for file to copy over: " + score_file)
                time.sleep(60)
                timeouts = timeouts + 1
                
            records = self.get_records(score_file)
            robj.logger.debug("Have all records")
            for record in records:
                self['condition_space'].add_record(record)

            #self['scores'][gate] = self.compute_score(score_file)
        if 'training' in self:
            robj.logger.debug("Removing training tag: " + str(self['training']))
            del self['training']

    def decode_key(key):
        return { tup[0]:tup[1] for tup in key }

    def _map_score_data_to_regions(self,
                    score_file,
                    metadata=None
                    ):
        score_data = json.load(open(score_file))
        l.debug("Score file data: " + str(score_data))
        
        raw_scores = score_data['data']
        strain_to_gate = score_data['strains']

        factors = self['condition_space'].factors
        
        #print("Condition Space: " + str(self['condition_space']))
        #print("Checking factors " + str(factors))
        #l.debug("Input Scores: " + str(raw_scores))
        #l.debug(metadata)

        ## output region to data map
        data = {} #pd.DataFrame()
        
        raw_keys = [dict(eval(x)) for x in raw_scores.keys()]
        if metadata is None:
            
            ## If no metadata, then update from all scores
            ## Scores does not refer to input, but condition space does
            for k in list(raw_scores.keys()):
                l.debug("Score File key: " + str(k))
                for strain in list(strain_to_circuit.keys()):#list(raw_scores[k]['strain_rankings'].keys()):
                    l.debug("Score file strain to gate: " + str(strain))
                    kd = dict(eval(str(k)))
                    kd['strain'] = strain
                    kd['input'] = strains_to_gate[strain]['input']
                    kd['output'] = strains_to_gate[strain]['output']
                    ski = str(tuple(sorted([tuple([k1, v1]) for k1, v1 in kd.items()])))
                    data[ski] = raw_scores[k]['strain_rankings'][kd['input']]
            #l.debug(data)
        else:
            ## If have metadata then only update from scores that match a metadata
            ## row.
            for i, m in metadata.iterrows():
                mk =  m.to_dict()
                input = mk.pop('input', None)
                output = mk.pop('output', None)
                #if 'strain' in mk:
                strain = mk.pop('strain', None)


                l.debug("meta key: " + str(mk))

                if keyin(mk, raw_keys):
                    sk = str(tuple(sorted([tuple([k, v]) for k, v in mk.items()])))
                    l.debug(sk)
                    mk['input'] = input
                    mk['output'] = output
                    mk['strain'] = strain
                    ski = str(tuple(sorted([tuple([k, v]) for k, v in mk.items()])))
                    l.debug(ski)
                    l.debug(raw_scores[sk])
                    data[ski] = raw_scores[sk]['strain_rankings'][input]
        return data
                
    def get_records(self,
                    score_file,
                    metadata
                    ):
        """
        Get Statistics for each row in metadata that appears in score_file.
        If new_data exists, then grab the correctness measure from it.

        """

        condition_map = {            
#            Conditions.GATE : 'gate',
 #           Conditions.TEMPERATURE : 'inc_temp',
 #           Conditions.DURATION : 'inc_time_2'
             Conditions.CORRECTNESS : 'mean_correct_classifier_live'

            }
        condition_value_map = {
            'SC0x20Media' : 'SC Media',
            "warm_30" : 30,
            "warm_37" : 37

            }

        data = self._map_score_data_to_regions(
                    score_file,
                    metadata=metadata
                    )
            
        #l.debug(raw_scores.keys())
        #l.debug(metadata)
        l.debug("Data for Records: " + str(data))
        records = []
        for k,v in data.items():
            kt = make_tuple(k)
            key_dict = ScoreModel.decode_key(kt)
            #l.debug(key_dict)

            record_factors = {}
            record_statistics = {}
            for name, factor in self['condition_space'].factors.items():
                #l.debug("Getting factor value " + str(factor))

                if name in condition_map:
                    mapped_name = condition_map[name]
                elif name in key_dict:
                    mapped_name = name
                elif factor['dtype'] == 'float':
                    mapped_name = name
                else:
                    mapped_name = None

                value = None
                if mapped_name is not None and mapped_name in key_dict:
                    value = key_dict[mapped_name]
                    if value in condition_value_map:
                        value = condition_value_map[value]
#                    elif name == Conditions.DURATION:
#                        value = float(value.split(':')[0])
                elif mapped_name is not None and factor['dtype'] == 'float':
                    # Take mean value of upper and lower to make sure its in region
                    discretized_names = factor.get_discretization_names()
                    value = np.mean([ key_dict[n] for n in discretized_names])

                record_factors[name] = value

            l.debug("Values for record: " + str(v))
            record_statistics[Conditions.SCORE] = np.mean(v) + random.random()/100.0
            record_statistics[Conditions.RANK_ERROR] = stats.sem(v)  + random.random()/100.0
                #record_statistics[Conditions.STANDARD_ERROR] = stats.sem(v['truthtable_correct'])
            #if 'correct_rankings' in v:
            #    record_statistics['rank_mean'] = np.mean(v['correct_rankings'])
            #    record_statistics['rank_error'] = stats.sem(v['correct_rankings'])
            #l.debug("Factors:  " + str(record_factors))
            #l.debug("Statistics: " + str(record_statistics))
            record = Record(factors = record_factors, statistics = record_statistics)
            records.append(record)

        return records



class MixtureModel(Model):
    """
    Model that mixes scores and entropy
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'models' not in self:
            #self['models'] = [ ScoreModel(**kwargs), MCMCBayesianModel(**kwargs), FrequentistModel(**kwargs)]
            self['probability'] = [
                # 0.33,
                                    0.33,
                                    0.33
                
                                        ]
            self['models'] = [
                ScoreModel(*args, **kwargs),
                #MCMCBayesianModel(*args, **kwargs),
                FrequentistModel(*args, **kwargs)
                ]
            #self['probability'] = [ 0.5, 0.5 ]

    def draw_samples(self, num_samples, random, strains, logger):
        model_choices = random.choices(self['models'],
                                               self['probability'],
                                               k = num_samples)

        model_samples = Counter(model_choices)
        #print(model_samples)
        samples = []
        for k, v in model_samples.items():
            logger.debug(k.__class__.__name__ + " " + str(v))
            ss = k.draw_samples(v, random, strains, logger)
            l.debug("Mixture got samples: " + str(ss))
            #print(ss)
            samples.append(ss)


        ## if 'samples' not in self:
        ##     self['samples'] = []
        ## self['samples'].append(samples)
        #print(samples)
        return samples

    def get_strains_and_ods(self, ods, strains, num_choices, random, logger):
        ## Make choices on the basis of a gate (comprising four strains)
        num_choices = int(num_choices/len(ods))
        factors = self['condition_space'].factors
        gate_samples = self.draw_samples(num_choices, random, {Conditions.STRAIN : factors[Conditions.STRAIN]}, logger)

        #l.debug("Strains: " + str(strains))
        l.debug("Sampled: " + str(gate_samples))


        all_strains=[]
        for cs in gate_samples:
            for i, s in cs.iterrows():
                all_strains.extend(self.extend_strain_to_od_strain({"gate" : s[Conditions.STRAIN]}, ods))
        #print(all_strains)
        l.debug("Sampled: " + str(all_strains))
        return all_strains


    def train(self,
              new_data,
              logger=None,
              old_model=None,
              is_local=False,
              out_dir=None,
              webhook=None,
              client=None,
              analysis_config=None,
              iteration=None):
        logger.info("Training Mixture Model")
        self['training'] = False

        if old_model is not None:
            self['old_model'] = old_model['id']
        else:
            self['old_model'] = None
        
        for model in self['models']:
            # find old model corresponding to model
            old_sub_model = get_old_sub_model(model, old_model)
            sub_analysis_config = None
            if analysis_config and model.__class__.__name__ in analysis_config:
                sub_analysis_config = analysis_config[model.__class__.__name__]

            model.train(new_data, logger=logger,
                        old_model=old_sub_model,
                        is_local=is_local,
                        webhook = webhook,
                        client=client,
                        analysis_config=sub_analysis_config,
                        out_dir=os.path.join(out_dir, model.__class__.__name__))
            if 'training' in model and model['training'] is not False:
                self['training'] = True

    def update_from_training(self, robj, training_output, out_dir):
        robj.logger.debug("Updating based upon Training Mixture Model")
        done_training = True
        for model in self['models']:
            model.update_from_training(robj, training_output, out_dir)
            if 'training' in model:
                done_training = False
        self['training'] = not done_training

class FrequentistModel(Model):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sampling_metric = Conditions.STANDARD_ERROR

    def declare_statistics(self):
        """
        Return statistics declarations for condition space.
        """
        statistics = {
            Conditions.CORRECTNESS : Statistic(name=Conditions.CORRECTNESS, default=None, dtype="float"),
            Conditions.STANDARD_ERROR : Statistic(name=Conditions.STANDARD_ERROR, default=None, dtype="float"),
            Conditions.COUNT : Statistic(name=Conditions.COUNT, default=0.0, dtype="float"),
            Conditions.SUM_SQ_DIFF : Statistic(name=Conditions.SUM_SQ_DIFF, default = None, dtype="float"),
            Conditions.STANDARD_DEV : Statistic(name=Conditions.STANDARD_DEV, default = None, dtype="float"),
            Conditions.ITERATION : Statistic(name=Conditions.ITERATION, default=None, dtype="float")
            }
        return statistics

    def update_from_training(self, robj, training_output, out_dir):
        pass

    def compute_accuracy(data_file, logger = l):
        data_dir = "/".join(data_file.split('/')[0:-1])
        out_path = os.path.join(data_dir, 'correctness')
        out_file = os.path.join(out_path, data_file.split('/')[-1])

        if not os.path.exists(out_path):
            os.makedirs(out_path)

        if not os.path.isfile(out_file):
            logger.debug("Creating accuracy file: " + out_file)
            try:
                data_df = pd.read_csv(data_file,dtype={'od': float, 'input' : object, 'output' : float}, index_col=0)
                logger.debug(data_df.columns)
                accuracy_df = correctness.compute_correctness_all(data_df, out_dir=out_path)
                #logger.debug(accuracy_df)
                #logger.debug(accuracy_df.columns)
                logger.debug("Writing accuracy file: " + out_file)
                accuracy_df.to_csv(out_file)


            except Exception as e:
                logger.exception("Could not add accuracy to: " + out_file + " because: " + str(e))
                raise e
        else:
            logger.debug("Accuracy file exists: " + out_file)
            accuracy_df = pd.read_csv(out_file,memory_map=True ,dtype={'od': float, 'input' : str, 'output' : str})
        return accuracy_df


    def train(self, new_data, compute_accuracy=True, old_model=None,
                logger=None, out_dir=None, iteration=None, **kwargs):
        if logger:
            logger.debug("Training Frequentist Model with: " + str(new_data))

        #def compute_accuracy(robj, experiment_ids, data_dir):

        if old_model is not None:
            logger.debug("old model uses data: " + str(old_model['data_used']))
            new_data = [ d for d in new_data if d not in old_model['data_used']]
            self['data_used'] = old_model['data_used'].copy()
            self['old_model'] = old_model['id']
            self['condition_space'].data = old_model['condition_space'].data
        else:
            self['old_model'] = None
            
        #logger.debug("model already trained on old data: " + str(self['data_used']))

        if len(new_data) == 0:
            logger.debug("Skipping Training, no new data ...")
            return
        self['data_used'].extend(new_data)

        
        for data_file in new_data:
            if compute_accuracy:
                accuracy_df = FrequentistModel.compute_accuracy(data_file, logger=logger)

                #accuracy_df.to_csv(os.path.join(out_dir, 'correctness', data_file.split('/')[-1]))
            else:
                accuracy_df = pd.read_csv(data_file,  dtype={'od': float, 'input' : object, 'output' : object})

            logger.debug("Getting Records from " + str(accuracy_df))
            records = self.get_records(accuracy_df, iteration=iteration)


            for record in records:
                #if logger:
                logger.debug("Adding record: " + str(record))
                try:
                    self['condition_space'].add_record(record)
                except Exception as e:
                    logger.exception("Failed to add record: " + str(e))


class RandomModel(FrequentistModel):
    def __init__(self, *args, **kwargs):
        l.debug(self.__class__.__name__)
        super().__init__(*args, **kwargs)

class DeterministicModel(FrequentistModel):
    def __init__(self, *args, **kwargs):
        l.debug(self.__class__.__name__)
        super().__init__(*args, **kwargs)
