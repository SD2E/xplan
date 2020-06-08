import json
# from xplan_api.autoprotocol import xplan_to_params
import uuid
import pandas as pd
#from .experiment_request_utils import get_role
#from .experiment_request_utils import get_source_for_strain, generate_well_parameters, get_container_aliquots, gate_info
#from pysd2cat.data.pipeline import get_xplan_data_and_metadata_df, handle_missing_data
#from pysd2cat.analysis.Names import Names


class ExperimentDesign(dict):
    """
    An experiment design for automating conversion to Transcriptic params.json
    """

    def __init__(self, **kwargs):
        dict.__init__(self, **kwargs)
        self.uuid = str(uuid.uuid1())

    #        self.samples = []
    #        self.id = experiment_id

    def __str__(self):
        return json.dumps(self, indent=4, sort_keys=True, separators=(',', ': '))

    def __get_refs_for_samples(self):
        """
        Deprecated: no longer need refs for design
        """
        keys = set([])
        refs = {}
        for sample in self['samples']:

            # print(sample['source_container'])
            key = sample['source_container']['label']
            if not key in keys:
                # print("Adding ref for container: " + str(key))
                keys.add(key)
                container_type = sample['source_container']['container_type_id']
                store = sample['source_container']['storage_condition']
                aliquots = sample['source_container_aliquots']
                value = {"type": container_type,
                         "name": key,
                         "store": store,
                         "aliquots": aliquots
                         }
                # print(value)
                refs.update({key: value})
        return refs

    def __get_inputs_for_plate(self, plate):
        # samples = []
        # ods = [ "0.0003", "0.00075" ]
        # print("getting inputs for plate")
        src_wells = {}
        for well, well_properties in self['plates'][plate]['wells'].items():
            src_well = well_properties['src_well']

            if src_well in src_wells:
                dest_ods = src_wells[src_well]['dest_od']
            else:
                dest_ods = []
                src_wells[src_well] = {'source_well': src_well, 'dest_od': dest_ods}

            # for idx,od in enumerate(ods):
            well_od = {
                "targ_od": well_properties['od'],
                "dest_well": well  # map_dest(well, idx)
            }
            dest_ods.append(well_od)

        samples = [v for k, v in src_wells.items()]

        inputs = {"specify_locations": {"samples": samples}}
        return inputs

    def __get_experiment_set_parameters(self):
        return {
            "inc_time_1": self['inc_time_1'],
            "inc_time_2": self['inc_time_2'],
            "inc_temp": self['inc_temp'],
        }

    def __get_experiment_plate_parameters(self, plate_id):
        return {
            "inducer": self['plates'][plate_id]["inducer"],
            "inducer_conc": self['plates'][plate_id]["inducer_conc"],
            "inducer_unit": self['plates'][plate_id]["inducer_unit"],
            "fluor_ex": self['plates'][plate_id]["fluor_ex"],
            "fluor_em": self['plates'][plate_id]["fluor_em"],
            "growth_media_1": self['plates'][plate_id]["growth_media_1"],
            "growth_media_2": self['plates'][plate_id]["growth_media_2"],
            "gfp_control": self['plates'][plate_id]['gfp_control'],
            "wt_control": self['plates'][plate_id]['wt_control'],
            "source_plate": self['plates'][plate_id]['source_container']['id'],
            "store_growth_plate2": self['plates'][plate_id]['store_growth_plate2'],
            #            "od_cutoff" : self['plates'][plate_id]['od_cutoff']
        }

    def to_params(self):
        """
        Convert to Transcriptic params.json format
        """
        params_set = {}
        exp_set_params = self.__get_experiment_set_parameters()
        # print(exp_set_params)
        for plate_id, plate in self['plates'].items():
            # print(self['plates'][plate_id])
            tx_params = {}
            # tx_params['refs'] = self.__get_refs_for_samples() #xplan_to_params.generate_refs(self['resources'])
            inputs = self.__get_inputs_for_plate(plate_id)
            exp_plate_params = self.__get_experiment_plate_parameters(plate_id)
            # print(exp_plate_params)
            exp_params = {}
            exp_params.update(exp_set_params)
            exp_params.update(exp_plate_params)
            tx_params['parameters'] = {
                'exp_params': exp_params,
                'sample_selection': {
                    "inputs": inputs,
                    "value": "specify_locations"
                }
            }
            params_set[str(plate_id)] = json.dumps(tx_params, indent=4, sort_keys=True, separators=(',', ': '))
        # print(params_set)
        return params_set




    def assign_replicate(self, strain, od, replicates):
        if strain not in replicates:
            replicates[strain] = {}
        strain_replicates = replicates[strain]

        if od not in strain_replicates:
            strain_replicates[od] = 0
        replicate = strain_replicates[od]
        strain_replicates[od] = strain_replicates[od] + 1
        return replicate

    def _fulfill_panda(self, logger, measurement_files, plate_id, lab_id, overwrite_request=False,
                       controls={"A12": {"strain": "WT-Live-Control"},
                                 "B12": {"strain": "WT-Dead-Control"},
                                 "C12": {"strain": "NOR-00-Control"}}
                       ):
        design = pd.read_json(self['design'], dtype={'experiment_id': str})
        logger.debug(design.batch)
        logger.debug(plate_id)

        batch_design = design.loc[design['batch'] == int(plate_id)]
        batch_design.loc[:, 'lab_id'] = lab_id
        batch_index = batch_design.index
        replicates = {}

        if measurement_files is None:
            logger.warn("Fulfilling Request with no FCS files")

        measurements = pd.DataFrame()
        for laliquot, record in measurement_files['aliquots'].items():
            mfile = record['file']
            measurements = measurements.append({"output_id": laliquot.upper(),
                                                "measurements": mfile},
                                               ignore_index=True)
        batch_design = batch_design.drop(columns=['measurements']).merge(measurements, on='output_id', how='right')

        logger.debug(batch_design)

        design = pd.concat([design.drop(index=batch_index), batch_design], ignore_index=True)
        logger.debug(design)
        self['design'] = design.to_json()


    def fulfill(self, logger, measurement_files, plate_id, lab_id, overwrite_request=False):
        """
        Associate filename for FCS measurement to each sample
        """
        if "design" in self:
            ## Use new format for design based upon pandas
            self._fulfill_panda(logger, measurement_files, plate_id, lab_id, overwrite_request=False)
        else:
            raise Exception("Cannot fulfill an experiment design with no design attribute")
        return self


class Sample(dict):
    """
    A desired sample for an experiment request.
    """

    def __init__(self):
        dict.__init__(self)

    def __str__(self):
        return json.dumps(self, indent=4, sort_keys=True, separators=(',', ': '))
