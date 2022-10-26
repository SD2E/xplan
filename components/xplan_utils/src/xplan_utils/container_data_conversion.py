"""
Converts container data received from strateos api into format expected
by the SAT problem generator.
"""

import string
import math
import numpy as np

import logging


l = logging.getLogger(__file__)
l.setLevel(logging.INFO)



class ColumnNotExistError(Exception):
    pass


def well_column(col_count, well_idx):
    """
    Zero-based column number of the given zero-based well index
    for a container with the given number of columns
    """
    return well_idx % col_count

def well_row(row_length, well_idx):
    """
    Zero-based row number of the given zero-based well index
    for a container with the given the row length
    """
    return well_idx // row_length 

def container_well_idx_name(col_count, well_idx):
    """
    Convert a container well index integer to a string name


    examples for 96 well plate:
    12, 0 -> a1
    12, 1 -> a2
    12, 12 -> b1

    Letter is the row. Number is the column.
    """
    row_idx = well_idx // col_count
    row = string.ascii_lowercase[row_idx]
    col = well_column(col_count, well_idx) + 1

    return "{}{}".format(row, col)


def custom_map_values(aliquot_dict):
    def value_map(k, v):
        if k == "Ethanol_concentration":
            if "%" in v:
                return float(v.split("%")[0])
            elif "No" in v:
                return 0.0
        elif k == "Sytox_concentration":
            if v == "Sytox":
                return 5.0
            else:
                return 0.0
        elif k == "strain":
            if v == "E. Coli MG1655":
                return "MG1655_WT"
        return v
        
    return { k : value_map(k, v) for k, v in aliquot_dict.items()}

def aliquot_dict(well_map, aliquots_df, well_idx, strain_name="Name"):
    """
    Create a dictionary of aliquot info for the given well in the container.
    """
    # aliquot_info = aliquots_df.loc[well_idx]

    if not well_idx in aliquots_df.index:
        return { "strain" : "None"}
    
    ## Handle case where other factors are embedded in the strain_name
    if ":" in strain_name and ";" in strain_name:
        aliquot_property = strain_name.split(":")[0].strip()
        factor_ids = [x.strip() for x in strain_name.split(":")[1].split(";")]
        property_value = aliquots_df.at[well_idx,aliquot_property]
        property_values = [x.strip() for x in property_value.split(";")]
        return custom_map_values(dict(zip(factor_ids, property_values)))
        
    else:
        strain = aliquots_df.at[well_idx,strain_name]
        l.debug("strain: %s, strain_property: %s", strain, strain_name)
        rdict = {}

#        if 'replicate' in aliquots_df.columns:
#            replicate = aliquots_df.at[well_idx, "replicate"]
#            if replicate and  ( type(replicate) is not float or ~np.isnan(replicate) ):
#                rdict["replicate"] = replicate
        
        if strain and (type(strain) is not float or  ~np.isnan(strain)):
            rdict["strain"] =  strain
        else:
            rdict["strain"] = "None"

        return rdict

def column_dict(col_count, well_idxs):
    """
    Create a dictionary of the columns in the container
    """
    result = {col: [] for col in range(col_count)}

    for well_idx in well_idxs:
        col = well_column(col_count, well_idx)
        result[col].append(container_well_idx_name(col_count, well_idx))

    return {
        "col{}".format(col + 1): wells
        for col, wells in result.items()
        if len(wells) > 0
    }


def row_dict(row_length, well_idxs):
    """
    Create a dictionary of the rows in the container
    """
    result = {row: [] for row in range(row_length)}

    for well_idx in well_idxs:
        row = well_row(row_length, well_idx)
        result[row].append(container_well_idx_name(row_length, well_idx))

    return {
        "row{}".format(row + 1): wells
        for row, wells in result.items()
        if len(wells) > 0
    }

def drop_nan_strain_aliquots(c2d):
    """
    Remove aliquots whose strain is nan
    """
    aliquots = {}
    dropped_aliquots = []
    for aliquot_id, aliquot in c2d['aliquots'].items():
        #print(str(type(aliquot['strain'])) + " " + str(aliquot['strain']))
        if 'strain' in aliquot and type(aliquot['strain']) is float and math.isnan(aliquot['strain']):
            #dropped_aliquots.append(aliquot_id)
            aliquots[aliquot_id] = aliquot
            del aliquots[aliquot_id]
        else:
            aliquots[aliquot_id] = aliquot
    columns = {}
    for col_id, col in c2d['columns'].items():
        col_aliquots = []
        for aliquot in col:
            if not aliquot in dropped_aliquots:
                col_aliquots.append(aliquot)
        if len(col_aliquots) > 0:
            columns[col_id] = col_aliquots
    rows = {}
    for row_id, row in c2d['rows'].items():
        row_aliquots = []
        for aliquot in row:
            if not aliquot in dropped_aliquots:
                row_aliquots.append(aliquot)
        if len(row_aliquots) > 0:
            rows[row_id] = row_aliquots
    return {
        "aliquots" : aliquots,
        "columns" : columns,
        "rows" : rows
        }

def container_to_dict(container, strain_name="Name", drop_nan_strain=True, convert_none_strain_to_mediacontrol=False):
    """
    Convert a transcriptic container object into a dict format
    expected by SAT problem generator
    """
    col_count = container.attributes['container_type']['col_count']
    well_map = container.well_map
    if container.container_type != None:
        well_count = container.container_type.well_count
    elif "container_type_id" in container.attributes:
        id = container.attributes["container_type_id"]
        if id == "96-pcr":
            well_count = 96
        else:
            raise Exception(f"Cannot determine number of aliquots in container {container}")
    else:
        raise Exception(f"Cannot determine number of aliquots in container {container}")

    for i in range(0, well_count):
        if i not in well_map:
            well_map[i] = None
    
    c2d = {
        "aliquots": {
            container_well_idx_name(col_count, well_idx): aliquot_dict(well_map, container.aliquots, well_idx, strain_name=strain_name)
            for well_idx in well_map.keys()
        },
        "columns": column_dict(col_count, well_map.keys()),
        "rows": row_dict(col_count, well_map.keys())
    }
    #l.info(c2d)
    if drop_nan_strain:
        c2d = drop_nan_strain_aliquots(c2d)
    if convert_none_strain_to_mediacontrol:
        for aliquot_id, aliquot in c2d['aliquots'].items():
            #if 'strain' in aliquot and not aliquot['strain']:
            if aliquot_id == "a11" or aliquot_id == "a12":
                aliquot['strain'] = "MediaControl"
                #else:
                #aliquot['strain'] = "None"
    return c2d

def generate_container(num_aliquots, batch_id, strain_name="Name", dimensions=(8, 12)):
    well_map = { i : {} for i in range(0, num_aliquots)  }
    col_count = dimensions[1]
    row_count = dimensions[0]

    aliquots = {
            container_well_idx_name(col_count, well_idx): {}
            for well_idx in well_map.keys()
        }

    use_aliquot_cheats = False
    if use_aliquot_cheats:
        none_replicate = (int(batch_id)  * 46)+1

        def key_in_cols(key, cols):
            return len([x for x in cols if x in key]) > 0

        def get_row_replicate(key, replicates):
            return [v for k, v in replicates.items() if k in key ][0]
        
        strain_cols = ["3", "4", "5", "6", "7", "8"]
        #strain_cols = ["3", "4", "5"]
        row_replicates = {"a" : 1, "b" : 2, "c" : 3, "d" : 4,
                         "e" : 1, "f" : 2, "g" : 3, "h" : 4
                         }
            
        for k, v in aliquots.items():
            if not key_in_cols(k, strain_cols) and k != "a1" and k != "b1":
                pass
#    #        if  "11" in k or "12" in k:
#                v['strain'] = "None"
#                v['replicate'] = none_replicate
                none_replicate += 1
            elif key_in_cols(k, strain_cols):
#                v['replicate'] = get_row_replicate(k, row_replicates)
#                pass

                if batch_id == "1":
                    v['strain'] = "Bacillus subtilis 168 Marburg"
                else:
                    v['strain'] = "MG1655_WT"
#            elif "1" in k and "a" in k:
#                v['strain'] = "MediaControl"
#                v['replicate'] = 1
#            elif "1" in k and "b" in k:
#                v['strain'] = "MediaControl"
#                v['replicate'] = 2


    #l.info(aliquots)
            
    return {
        "aliquots" : aliquots,
        "columns" : column_dict(col_count, well_map.keys()),
        "rows" : row_dict(col_count, well_map.keys())
        }

def get_strain_count(container, strain_map):
    strain_counts = { None : 0 }
    for aliquot, properties in container['aliquots'].items():
        if 'strain' in properties:
            if properties['strain'] in strain_map:
                strain = strain_map[properties['strain']]
            else:
                strain = properties['strain']
            if strain in strain_counts:
                strain_counts[strain] += 1
            else:
                strain_counts[strain] = 1
        else:
            strain_counts[None] += 1
    return strain_counts
