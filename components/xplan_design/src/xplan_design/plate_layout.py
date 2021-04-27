import json
import numpy as np
import math
import pysmt.shortcuts
from pysmt.typing import INT, REAL
from pysmt.rewritings import conjunctive_partition
from functools import reduce

import xplan_design.plate_layout_utils

from xplan_utils.container_data_conversion import get_strain_count

import pandas as pd

import logging

l = logging.getLogger(__file__)
l.setLevel(logging.INFO)


def generate_variables1(inputs):
    """
    Encoding variables and values
    """

    samples = inputs['samples']
    factors = inputs['factors']
    containers = inputs['containers']
    aliquot_factor_map = inputs['aliquot_factor_map']
    aliquot_symmetry_samples = inputs['aliquot_symmetry_samples']
    aliquots = [a for c in containers for a in containers[c]['aliquots']]

    variables = {}
    variables['reverse_index'] = {}

    def get_factor_symbols(factor, prefix, var=None, constraints=None, map=None):
        if factor['dtype'] == "str":
            if var is not None and constraints and var in constraints and constraints[var]:
                # l.debug("setting levels of %s %s %s", var, factor['name'],  constraints[var][factor['name']])
                if map:
                    levels = [map[factor['name']][l] for l in [constraints[var][factor['name']]]]
                else:
                    levels = [constraints[var][factor['name']]]
            else:
                if map:
                    levels = [map[factor['name']][l] for l in factor['domain']]
                else:
                    levels = factor['domain']
            return {
                level: pysmt.shortcuts.Symbol("{}={}".format(prefix, level))
                for level in levels
            }

        else:
            # Cannot filter values here because its an real that is yet to be assigned
            return pysmt.shortcuts.Symbol(prefix, REAL)

    variables['aliquot_factors'] = {}
    for c in containers:
        c_factors = {}
        for a in samples[c]:
            a_factors = {}
            for factor_id, factor in factors.items():
                if factor['ftype'] == "aliquot":
                    if factor_id in containers[c]['aliquots'][a]:
                        a_factors[factor_id] = get_factor_symbols(factor, "{}({}_{})".format(factor_id, a, c),
                                                                  var=a, constraints=containers[c]['aliquots'],
                                                                  map=aliquot_factor_map)
                    else:
                        a_factors[factor_id] = get_factor_symbols(factor, "{}({}_{})".format(factor_id, a, c))
            c_factors[a] = a_factors
        variables['aliquot_factors'][c] = c_factors

    # l.info( variables['aliquot_factors'])

    variables['sample_factors'] = \
        {
            c: {
                a: {
                    sample: {
                        factor_id: get_factor_symbols(factor,
                                                      "{}(x{}_{}_{})".format(factor_id, sample, a, c),
                                                      var=sample,
                                                      constraints=inputs['sample_types'])
                        for factor_id, factor in factors.items() if factor['ftype'] == "sample"
                    }
                    for sample in samples[c][a]
                }
                for a in samples[c]
            }
            for c in samples
        }

    ## Variables used when choose to ignore a measurement
    variables['na_sample_factors'] = \
        {
            c: {
                a: {
                    sample: {
                        factor_id: pysmt.shortcuts.Symbol("{}_is_na(x{}_{}_{})".format(factor_id, sample, a, c))
                        for factor_id, factor in factors.items() if factor['ftype'] == "sample"
                    }
                    for sample in samples[c][a]
                }
                for a in samples[c]
            }
            for c in samples
        }

    for container in variables['sample_factors']:
        for aliquot in variables['na_sample_factors'][container]:
            for sample in variables['na_sample_factors'][container][aliquot]:
                for factor_id in variables['na_sample_factors'][container][aliquot][sample]:
                    var = str(variables['na_sample_factors'][container][aliquot][sample][factor_id])
                    if var not in variables['reverse_index']:
                        variables['reverse_index'][var] = {}
                    variables['reverse_index'][var].update({"type": "na_sample_factor",
                                                            "aliquot": aliquot,
                                                            "sample": "x{}_{}_{}".format(sample, aliquot,
                                                                                         container),
                                                            "container": container,
                                                            factor_id: "NA"})

        for aliquot in variables['sample_factors'][container]:
            for sample in variables['sample_factors'][container][aliquot]:
                for factor_id in variables['sample_factors'][container][aliquot][sample]:
                    if factors[factor_id]['dtype'] == "str":
                        for level in variables['sample_factors'][container][aliquot][sample][factor_id]:
                            var = str(variables['sample_factors'][container][aliquot][sample][factor_id][level])
                            if var not in variables['reverse_index']:
                                variables['reverse_index'][var] = {}
                            variables['reverse_index'][var].update({"type": "sample", "aliquot": aliquot,
                                                                    "sample": "x{}_{}_{}".format(sample, aliquot,
                                                                                                 container),
                                                                    "container": container, factor_id: level})
                    else:
                        var = str(variables['sample_factors'][container][aliquot][sample][factor_id])
                        if var not in variables['reverse_index']:
                            variables['reverse_index'][var] = {}
                        variables['reverse_index'][var].update({"type": "sample", "aliquot": aliquot,
                                                                "sample": "x{}_{}_{}".format(sample, aliquot,
                                                                                             container),
                                                                "container": container, factor_id: None})

            for factor_id in variables['aliquot_factors'][container][aliquot]:
                if factors[factor_id]['dtype'] == "str":
                    for level in variables['aliquot_factors'][container][aliquot][factor_id]:
                        var = str(variables['aliquot_factors'][container][aliquot][factor_id][level])
                        if var not in variables['reverse_index']:
                            variables['reverse_index'][var] = {}
                        column = \
                            [col for col, aliquots in containers[container]['columns'].items() if aliquot in aliquots][
                                0]
                        row = [row for row, aliquots in containers[container]['rows'].items() if aliquot in aliquots][0]
                        variables['reverse_index'][var].update(
                            {"type": "aliquot", "aliquot": aliquot, "container": container, factor_id: level,
                             "column": xplan_design.plate_layout_utils.get_column_name(column, container), "row": xplan_design.plate_layout_utils.get_row_name(row, container)})
                else:
                    var = str(variables['aliquot_factors'][container][aliquot][factor_id])
                    if var not in variables['reverse_index']:
                        variables['reverse_index'][var] = {}
                    column = [col for col, aliquots in containers[container]['columns'].items() if aliquot in aliquots][
                        0]
                    row = [row for row, aliquots in containers[container]['rows'].items() if aliquot in aliquots][0]
                    variables['reverse_index'][var].update(
                        {"type": "aliquot", "aliquot": aliquot, "container": container, factor_id: level,
                         "column": xplan_design.plate_layout_utils.get_column_name(column, container), "row": xplan_design.plate_layout_utils.get_row_name(row, container)})

    values = {}

    variables['exp_factor'] = \
        {
            factor_id: get_factor_symbols(factor, "{}()".format(factor_id))
            for factor_id, factor in factors.items() if factor['ftype'] == "experiment"
        }
    for exp_factor in variables['exp_factor']:
        if factors[exp_factor]['dtype'] == "str":
            for level in variables['exp_factor'][exp_factor]:
                var = str(variables['exp_factor'][exp_factor][level])
                if var not in variables['reverse_index']:
                    variables['reverse_index'][var] = {}
                variables['reverse_index'][var].update({"type": "experiment", exp_factor: level})
        else:
            var = str(variables['exp_factor'][exp_factor])
            if var not in variables['reverse_index']:
                variables['reverse_index'][var] = {}
            variables['reverse_index'][var].update({"type": "experiment", exp_factor: None})

    container_assignment = inputs['container_assignment']
    l.debug("container_assignment: %s", container_assignment)

    container_assignment_dict = json.loads(container_assignment.groupby(["batch"]).apply(
        lambda x: {k: set(v.values()) for k, v in json.loads(x.to_json()).items()}).to_json())

    variables['batch_factor'] = \
        {
            batch: {
                factor_id: get_factor_symbols(factor, "{}(batch_{})".format(factor_id, batch), batch,
                                              container_assignment_dict[batch])
                # factor_id : get_factor_symbols(factor, "{}({})".format(factor_id, container))
                for factor_id, factor in factors.items() if factor['ftype'] == "batch" and factor_id != "batch"
            }
            for batch in container_assignment_dict
        }
    """
    variables['batch_containers'] = {
        batch : {
            container : Symbol(f"assign({container}, batch_{str(batch)})")
            for container in batch_levels['container']
        }
        for batch, batch_levels in container_assignment_dict.items()
    }
    l.debug("batch_factors %s", variables['batch_factor'])
    """
    for batch in variables['batch_factor']:
        """
        for container  in variables['batch_containers'][batch]:
            var = str(variables['batch_containers'][batch][container])
            if var not in variables['reverse_index']:
                variables['reverse_index'][var] = {}
            variables['reverse_index'][var].update({"type" : "batch", "container" : container, "batch" : batch})
        """
        for batch_factor in variables['batch_factor'][batch]:
            if factors[batch_factor]['dtype'] == "str":
                for level in variables['batch_factor'][batch][batch_factor]:
                    var = str(variables['batch_factor'][batch][batch_factor][level])
                    if var not in variables['reverse_index']:
                        variables['reverse_index'][var] = {}
                    variables['reverse_index'][var].update({"type": "batch", "batch": batch, batch_factor: level})
            else:
                var = str(variables['batch_factor'][batch][batch_factor])
                if var not in variables['reverse_index']:
                    variables['reverse_index'][var] = {}
                variables['reverse_index'][var].update({"type": "batch", "batch": batch, batch_factor: None})

    ## Variables used when choose to ignore the column factor
    variables['na_column_factors'] = \
        {
            xplan_design.plate_layout_utils.get_column_name(col, container_id): {
                factor_id: pysmt.shortcuts.Symbol("{}_is_na({}_{})".format(factor_id, col, container_id))
                for factor_id, factor in factors.items() if factor['ftype'] == "column"
            }
            for container_id, container in containers.items()
            for col in container['columns']
        }
    for column in variables['na_column_factors']:
        # l.debug("Reversing: %s", column)
        for column_factor in variables['na_column_factors'][column]:
            var = str(variables['na_column_factors'][column][column_factor])
            if var not in variables['reverse_index']:
                variables['reverse_index'][var] = {}
            container = [c for c in containers if c in column][0]  ## assumes container_id is in column name
            variables['reverse_index'][var].update(
                {"type": "na_column", "column": column, "container": container, column_factor: "NA"})

    variables['column_factor'] = \
        {
            xplan_design.plate_layout_utils.get_column_name(col, container_id): {
                factor_id: get_factor_symbols(factor, "{}({}_{})".format(factor_id, col, container_id))
                for factor_id, factor in factors.items() if factor['ftype'] == "column"
            }
            for container_id, container in containers.items()
            for col in container['columns']
        }
    # l.info("column_factors variables: %s", variables['column_factor'])
    for column in variables['column_factor']:
        # l.debug("Reversing: %s", column)
        for column_factor in variables['column_factor'][column]:
            # l.debug("Reversing factor: %s %s", column_factor,  factors[column_factor]['dtype'])
            if factors[column_factor]['dtype'] == "str":
                for level in variables['column_factor'][column][column_factor]:
                    var = str(variables['column_factor'][column][column_factor][level])
                    if var not in variables['reverse_index']:
                        variables['reverse_index'][var] = {}
                    # container = [ c for c in containers if column in containers[c]['columns']][0]
                    container = [c for c in containers if c in column][0]  ## assumes container_id is in column name
                    variables['reverse_index'][var].update(
                        {"type": "column", "column": column, "column_id": xplan_design.plate_layout_utils.get_column_id(column.split("_")[0]),
                         "container": container, column_factor: level})
            else:
                var = str(variables['column_factor'][column][column_factor])
                if var not in variables['reverse_index']:
                    variables['reverse_index'][var] = {}
                # container = [ c for c in containers if column in containers[c]['columns']][0]
                container = [c for c in containers if c in column][0]  ## assumes container_id is in column name
                if column_factor == "column_id":
                    variables['reverse_index'][var].update(
                        {"type": "column", "column": column, "column_id": xplan_design.plate_layout_utils.get_column_id(column.split("_")[0]),
                         "container": container})
                else:
                    variables['reverse_index'][var].update(
                        {"type": "column", "column": column, "column_id": xplan_design.plate_layout_utils.get_column_id(column.split("_")[0]),
                         "container": container, column_factor: None})
                # l.debug("Reverse %s %s", var, variables['reverse_index'][var])

    variables['row_factor'] = \
        {
            xplan_design.plate_layout_utils.get_row_name(row, container_id): {
                factor_id: get_factor_symbols(factor, "{}({}_{})".format(factor_id, row, container_id))
                for factor_id, factor in factors.items() if factor['ftype'] == "row"
            }
            for container_id, container in containers.items()
            for row in container['rows']
        }
    # l.debug("row_factors variables: %s", variables['row_factor'])
    for row in variables['row_factor']:
        # l.debug("Reversing: %s", row)
        for row_factor in variables['row_factor'][row]:
            # l.debug("Reversing factor: %s %s", row_factor,  factors[row_factor]['dtype'])
            if factors[row_factor]['dtype'] == "str":
                for level in variables['row_factor'][row][row_factor]:
                    var = str(variables['row_factor'][row][row_factor][level])
                    if var not in variables['reverse_index']:
                        variables['reverse_index'][var] = {}
                    # container = [ c for c in containers if row in containers[c]['rows']][0]
                    container = [c for c in containers if c in row][0]  ## assumes container_id is in row name
                    variables['reverse_index'][var].update(
                        {"type": "row", "row": row, "container": container, row_factor: level})
            else:
                var = str(variables['row_factor'][row][row_factor])
                if var not in variables['reverse_index']:
                    variables['reverse_index'][var] = {}
                # container = [ c for c in containers if row in containers[c]['rows']][0]
                container = [c for c in containers if c in row][0]  ## assumes container_id is in row name
                variables['reverse_index'][var].update(
                    {"type": "row", "row": row, "container": container, row_factor: None})
                # l.debug("Reverse %s %s", var, variables['reverse_index'][var])

    # l.debug("Variables: %s", variables)
    # l.debug("Values: %s", values)
    return variables, values


def generate_constraints1(inputs, batch):
    """
    Generate constraints for plate layout encoding.
    """
    variables, values = generate_variables1(inputs)

    constraints = {}

    # bounds = generate_bounds(inputs, variables, values)
    # constraints.append(bounds)

    samples = inputs['samples']
    factors = inputs['factors']
    containers = inputs['containers']
    containers_df = inputs['containers_df']
    requirements = inputs['requirements']
    requirments_df = inputs["requirements_df"]
    sample_types = inputs['sample_types']
    aliquot_symmetry_samples = inputs['aliquot_symmetry_samples']
    aliquots = [a for c in containers for a in containers[c]['aliquots']]

    #    tau_symbols = variables['tau_symbols']
    aliquot_factors = variables['aliquot_factors']
    sample_factors = variables['sample_factors']
    exp_factor = variables['exp_factor']
    batch_factor = variables['batch_factor']
    column_factor = variables['column_factor']
    na_sample_factors = variables['na_sample_factors']
    na_column_factors = variables['na_column_factors']
    row_factor = variables['row_factor']
    aliquot_factor_map = inputs["aliquot_factor_map"]

    container_assignment = inputs['container_assignment']
    # query = " & ".join([f"`{var}`== '{val}'" for var, val in batch.items() if type(val) == str] + [f"`{var}`=={val}" for var, val in batch.items() if type(val) != str])
    # batch_containers = list(container_assignment.query(query).container.unique())
    batch_containers = container_assignment.merge(batch.to_frame().transpose(),
                                                  on=['batch'] + [factor_id for factor_id, factor in factors.items() if
                                                                  factor['ftype'] == "batch"])
    batch_containers_df = containers_df.merge(batch_containers)

    #    l.debug(f"container_assignment: {container_assignment}")
    #    l.debug(f"batch: {batch}")
    #    l.debug(f"query: {query}")
    #    l.debug(f"batch_containers: {batch_containers}")

    def cs_factor_level(levels):
        return pysmt.shortcuts.ExactlyOne(levels)

    def cs_factor_bounds(factor_id, symbol, levels):
        return pysmt.shortcuts.And(pysmt.shortcuts.GE(symbol, pysmt.shortcuts.Real(levels[0])),
                                   pysmt.shortcuts.LE(symbol, pysmt.shortcuts.Real(levels[1])))

    def cs_factors_level(factor_symbols, var=None, constraints=None, na_factors=None):
        factor_clauses = []
        for factor_id, symbols in factor_symbols.items():

            ## Get symbol for case where factor is not applicable.
            na_level = None
            if na_factors is not None and factor_id in na_factors:
                na_level = na_factors[factor_id]

            if factors[factor_id]['dtype'] == "str":
                # Already filtered the levels for Bools
                if na_level:
                    levels = [y for x, y in symbols.items()] + [na_level]
                else:
                    levels = [y for x, y in symbols.items()]
                factor_clauses.append(cs_factor_level(levels))
            else:
                # Need to filter levels for ints
                if var is not None and constraints and var in constraints and constraints[var]:
                    # l.debug("setting levels of %s %s %s", var, factor_id,  constraints[var][factor_id])
                    levels = [constraints[var][factor_id], constraints[var][factor_id]]
                else:
                    levels = factors[factor_id]['domain']
                if na_level:
                    factor_clauses.append(
                        pysmt.shortcuts.ExactlyOne(na_level, cs_factor_bounds(factor_id, symbols, levels)))
                else:
                    factor_clauses.append(cs_factor_bounds(factor_id, symbols, levels))

        return pysmt.shortcuts.And(factor_clauses)

    def cs_experiment_factors(exp_factor):
        return cs_factors_level(exp_factor)

    def cs_sample_factors(sample_factor, container_id, container, aliquot):
        return pysmt.shortcuts.And([cs_factors_level(sample_factor[container_id][aliquot][sample],
                                                     var=sample,
                                                     constraints=sample_types,
                                                     na_factors=na_sample_factors[container_id][aliquot][sample])
                                    for sample in samples[container_id][aliquot]])

    def cs_aliquot_factors(aliquot_factors, container_id, container, column):
        return pysmt.shortcuts.And([pysmt.shortcuts.And(cs_factors_level(aliquot_factors[container_id][aliquot]),
                                                        cs_sample_factors(sample_factors, container_id, container,
                                                                          aliquot))
                                    for aliquot in column])

    def cs_column_factors(column_factor, container_id, container):

        clause = pysmt.shortcuts.And(
            ## Each Column has factors with values in their domain or are NA
            pysmt.shortcuts.And([cs_factors_level(xplan_design.plate_layout_utils.get_column_factors(column_factor, column, container_id)
                                                  ,
                                                  na_factors=na_column_factors[xplan_design.plate_layout_utils.get_column_name(column, container_id)]
                                                  )
                                 for column in container['columns']])
            ,
            ## For each factor, either all columns in container are NA or not (e.g., cannot induce at different times)
            pysmt.shortcuts.And([pysmt.shortcuts.Or(
                pysmt.shortcuts.And([na_column_factors[xplan_design.plate_layout_utils.get_column_name(column, container_id)][factor_id]
                                     for column in container['columns']]),
                pysmt.shortcuts.And(
                    [pysmt.shortcuts.Not(na_column_factors[xplan_design.plate_layout_utils.get_column_name(column, container_id)][factor_id])
                     for column in container['columns']]))
                for factor_id, factor in factors.items() if factor['ftype'] == "column"])
        )
        # l.debug("column clause: %s", clause)
        return clause

    def cs_row_factors(row_factor, container_id, container):

        clause = pysmt.shortcuts.And([cs_factors_level(xplan_design.plate_layout_utils.get_row_factors(row_factor, row, container_id))
                                      for row in container['rows']])
        # l.debug("column clause: %s", clause)
        return clause

    def cs_batch_factors(batch_factors, containers, batch):

        return pysmt.shortcuts.And(cs_factors_level(batch_factors[str(batch['batch'])]),
                                   pysmt.shortcuts.And([
                                       pysmt.shortcuts.And(
                                           # cs_factors_level(get_batch_factors(batch_factors, container_id), container_id, container_assignment),
                                           cs_column_factors(column_factor, container_id, container),
                                           cs_row_factors(row_factor, container_id, container),
                                           cs_aliquot_factors(aliquot_factors, container_id, container,
                                                              container['aliquots'])
                                       )
                                       for container_id, container in containers.items() if
                                       container_id in batch_containers]))

    condition_space_constraint = \
        pysmt.shortcuts.And(
            cs_experiment_factors(exp_factor),
            cs_batch_factors(batch_factor, containers, batch)
        )
    # l.debug("CS: %s", condition_space_constraint)
    constraints["condition_space_constraint"] = condition_space_constraint

    # l.info(containers)
    # ALQ


    assert (xplan_design.plate_layout_utils.containers_have_known_contents(containers, factors, aliquot_factor_map))

    aliquot_properties_constraint = get_aliquot_properties_constraint(containers, batch_containers, factors, batch,
                                                                      column_factor, row_factor, aliquot_factors,
                                                                      aliquot_factor_map)
    # l.debug("aliquot_properties_constraint: %s", aliquot_properties_constraint)
    constraints["aliquot_properties_constraint"] = aliquot_properties_constraint

    l.info("Encoding %s requirements", len(requirements))
    satisfy_every_requirement = satisfy_every_requirement_constraint_df(requirements, batch_containers_df, factors,
                                                                        variables, inputs,
                                                                        sample_types,
                                                                        sample_factors, na_sample_factors,
                                                                        batch_containers, aliquot_factors,
                                                                        column_factor,
                                                                        row_factor, samples, batch_factor,
                                                                        na_column_factors, aliquot_symmetry_samples,
                                                                        batch,
                                                                        aliquot_factor_map, requirments_df)
    #    satisfy_every_requirement = satisfy_every_requirement_constraint_df(requirements, containers, factors, sample_types,
    #                                                                     sample_factors, na_sample_factors,
    #                                                                     batch_containers, aliquot_factors, column_factor,
    #                                                                     row_factor, samples, batch_factor,
    #                                                                     na_column_factors, aliquot_symmetry_samples, batch,
    #                                                                     aliquot_factor_map, requirments_df)

    # l.debug("satisfy_every_requirement: %s", satisfy_every_requirement)
    constraints["satisfy_every_requirement_constraint"] = satisfy_every_requirement

    def get_aliquot_replicates(container_id, aliquot):
        reps = aliquot_symmetry_samples.loc[(aliquot_symmetry_samples.aliquot == aliquot) &
                                            (aliquot_symmetry_samples.container == container_id)]
        if len(reps) > 0:
            reps = reps.drop(columns=['aliquot', 'container', "column"]).drop_duplicates()
            rep_records = json.loads(reps.to_json(orient='records'))
            # l.debug("rep_records for %s %s: %s", container_id, aliquot, rep_records)
            return rep_records
        else:
            return []

    def get_factor_vars(factor, container_id, aliquot):
        ftype = factors[factor]['ftype']
        if ftype == "experiment":
            return exp_factor
        elif ftype == "batch":
            return batch_factor[container_id]
        elif ftype == "aliquot":
            return aliquot_factors[container_id][aliquot]
        elif ftype == "column":
            column = xplan_design.plate_layout_utils.get_aliquot_col(aliquot, containers[container_id])
            return column_factor[xplan_design.plate_layout_utils.get_column_name(column, container_id)]
        elif ftype == "row":
            row = xplan_design.plate_layout_utils.get_aliquot_row(aliquot, containers[container_id])
            return row_factor[xplan_design.plate_layout_utils.get_row_name(row, container_id)]

    ## Replicate symmetry
    if aliquot_symmetry_samples is not None and False:
        replicate_symmetry_constraint = \
            pysmt.shortcuts.And([  # For Every Container, Every Aliquot
                pysmt.shortcuts.ExactlyOne([  # There is a set of possible replicates
                    pysmt.shortcuts.And([  # That has the following assignments
                        get_req_const(get_factor_vars(factor, container_id, aliquot), factor, level, factors)
                        for factor, level in case.items() if
                        (type(level) == str or not math.isnan(level)) and level != "None" and level != "nan"])
                    for case in get_aliquot_replicates(container_id, aliquot)])
                for container_id, container in containers.items() if
                container_consistent_with_batch(container_id, container_assignment, batch)
                for aliquot in container['aliquots']])

        # l.debug(replicate_symmetry_constraint)
        # constraints.append(replicate_symmetry_constraint)

    ## Column reagents are set to zero if every aliquot in the column is empty
    if "None" in factors['strain']['domain']:
        no_reagents_for_empty_columns = \
            pysmt.shortcuts.And([pysmt.shortcuts.And(
                [pysmt.shortcuts.Implies(pysmt.shortcuts.And([aliquot_factors[container_id][aliquot]['strain']["None"]
                                                              for aliquot in column_aliquots]),
                                         pysmt.shortcuts.And(
                                             [pysmt.shortcuts.Equals(col_factor_var, pysmt.shortcuts.Real(0.0))
                                              for col_factor_id, col_factor_var in
                                              column_factor[xplan_design.plate_layout_utils.get_column_name(column_id, container_id)].items()]))
                 for column_id, column_aliquots in container['columns'].items()])
                for container_id, container in containers.items() if
                container_consistent_with_batch(container_id, container_assignment, batch)])
        constraints['no_reagents_for_empty_columns_constraint'] = no_reagents_for_empty_columns

        ## Row reagents are set to zero if every aliquot in the row is empty
        no_reagents_for_empty_rows = \
            pysmt.shortcuts.And([pysmt.shortcuts.And(
                [pysmt.shortcuts.Implies(pysmt.shortcuts.And([aliquot_factors[container_id][aliquot]['strain']["None"]
                                                              for aliquot in row_aliquots]),
                                         pysmt.shortcuts.And(
                                             [pysmt.shortcuts.Equals(row_factor_var, pysmt.shortcuts.Real(0.0))
                                              for row_factor_id, row_factor_var in
                                              row_factor[xplan_design.plate_layout_utils.get_row_name(row_id, container_id)].items()]))
                 for row_id, row_aliquots in container['rows'].items()])
                for container_id, container in containers.items() if
                container_consistent_with_batch(container_id, container_assignment, batch)])
        constraints['no_reagents_for_empty_rows_constraint'] = no_reagents_for_empty_rows

    # f = And(constraints)
    # l.debug("Constraints: %s", f)

    return variables, constraints


def get_aliquot_properties_constraint(containers, batch_containers, factors, batch, column_factor, row_factor,
                                      aliquot_factors, aliquot_factor_map):
    aliquot_properties_constraints = []
    for container_id, c in containers.items():
        if container_id in batch_containers.container.values:
            container_constraints = []
            for aliquot, aliquot_properties in c['aliquots'].items():
                aliquot_col = xplan_design.plate_layout_utils.get_aliquot_col(aliquot, c)
                aliquot_col_name = xplan_design.plate_layout_utils.get_column_name(aliquot_col, container_id)
                aliquot_col_id = xplan_design.plate_layout_utils.get_column_id(aliquot_col)
                aliquot_row = xplan_design.plate_layout_utils.get_aliquot_row(aliquot, c)
                aliquot_row_name = xplan_design.plate_layout_utils.get_row_name(aliquot_row, container_id)
                aliquot_row_id = xplan_design.plate_layout_utils.get_row_id(aliquot_row)

                aliquot_factor_constraint = pysmt.shortcuts.And([
                    # get_req_const(aliquot_factors[container_id][aliquot], factor, map_aliquot_property_level(level), factors)
                    get_req_const(aliquot_factors[container_id][aliquot], factor, aliquot_factor_map[factor][level],
                                  factors)
                    for factor, level in aliquot_properties.items() if
                    factor in aliquot_factors[container_id][aliquot]])
                column_factor_constraint = pysmt.shortcuts.And([get_req_const(column_factor[aliquot_col_name],
                                                                              factor, level, factors)
                                                                for factor, level in aliquot_properties.items() if
                                                                factor in column_factor[aliquot_col_name]])
                if 'column_id' in column_factor[aliquot_col_name]:
                    column_id_constraint = pysmt.shortcuts.Equals(column_factor[aliquot_col_name]['column_id'],
                                                                  pysmt.shortcuts.Real(aliquot_col_id))
                else:
                    column_id_constraint = pysmt.shortcuts.And()
                if 'row_id' in row_factor[aliquot_row_name]:
                    row_id_constraint = pysmt.shortcuts.Equals(row_factor[aliquot_row_name]['row_id'],
                                                               pysmt.shortcuts.Real(aliquot_row_id))
                else:
                    row_id_constraint = pysmt.shortcuts.And()
                row_factor_constraint = pysmt.shortcuts.And([get_req_const(row_factor[aliquot_row_name], factor,
                                                                           level, factors)
                                                             for factor, level in aliquot_properties.items() if
                                                             factor in row_factor[aliquot_row_name]])
                ## TODO row and column constraints don't need to be stated for each aliquot
                aliquot_constraint = pysmt.shortcuts.And(
                    ## Every aliquot must satisfy the aliquot factors defined by the container
                    aliquot_factor_constraint,
                    ## Every column factor implied by the container aliquots is satisfied
                    column_factor_constraint,
                    ## Every row factor implied by the container aliquots is satisfied
                    row_factor_constraint,
                    ## If column_id is a factor, then assert the column_id of each aliquot
                    column_id_constraint,
                    ## If row_id is a factor, then assert the row_id of each aliquot
                    row_id_constraint
                )
                container_constraints.append(aliquot_constraint)
            aliquot_properties_constraints.append(pysmt.shortcuts.And(container_constraints))
    aliquot_properties_constraint = pysmt.shortcuts.And(aliquot_properties_constraints)
    return aliquot_properties_constraint


def container_consistent_with_batch(container_id, container_assignment, batch):
    if container_assignment is not None:
        query = "&".join([f"{var}=='{val}'" for var, val in batch.items()]) + f" & container == \'{container_id}\'"
        result = container_assignment.query(query)
        return len(result) > 8
    return True


def batch_can_satisfy_requirement(r, batch, factors):
    """
    Is every batch requirement in r satisfied by batch
    :param r:
    :param batch:
    :return:
    """
    req_batch_factors = r_batch_factors(r, factors)
    for f in req_batch_factors:
        if f['factor'] in batch:
            batch_level = batch[f['factor']]
            if batch_level in f['values']:
                pass  # batch can satisfy req
            else:
                return False
        else:
            # requirment not specified in batch
            pass
    return True


def get_req_constraint(cases, factors, variables, inputs):
    r_aliquot_factors_ids = [ x for x in cases.columns if x in factors and factors[x]['ftype'] == "aliquot"]
    r_batch_factor_ids = [ x for x in cases.columns if x in factors and factors[x]['ftype'] == "batch"]
    r_column_factor_ids =[ x for x in cases.columns if x in factors and factors[x]['ftype'] == "column"]
    r_row_factor_ids = [ x for x in cases.columns if x in factors and factors[x]['ftype'] == "row"]
    r_sample_factor_ids = [ x for x in cases.columns if x in factors and factors[x]['ftype'] == "sample"]

    column_factors = [f for name, f in factors.items() if name in r_column_factor_ids]
    row_factors = [f for name, f in factors.items() if name in r_row_factor_ids]
    sample_factors = [f for name, f in factors.items() if name in r_sample_factor_ids]


    def constraint_for_row(requirement):
        container_id = requirement['container']
        aliquot = requirement['aliquot']
        batch = requirement['batch']
        column = requirement['column']
        row = requirement['row']
        # possible_aliquots.append(aliquot)
        aliquot_clause = pysmt.shortcuts.And(
            ## Satisfy aliquot factors
            pysmt.shortcuts.And([get_req_const(variables['aliquot_factors'][container_id][aliquot],
                                               factor_id, level, factors)
                                 for factor_id, level in requirement.items() if factor_id in r_aliquot_factors_ids]),
            ## Batch factors for container of aliquot
            pysmt.shortcuts.And([get_req_const(variables['batch_factor'][str(batch)], factor_id, level, factors)
                                 for factor_id, level in requirement.items() if
                                 factor_id in r_batch_factor_ids and factor_id != "batch"]),
            ## Column factors for column of aliquot
            req_column_factors_df(requirement, column_factors, container_id,
                                  [column], variables, factors),
            ## Row factors for row of aliquot
            req_row_factors_df(requirement, row_factors, container_id,
                               [row], variables, factors),
            ## Sample factors for aliquot
            req_sample_factors_df(requirement, sample_factors, inputs, variables, aliquot,
                                  container_id, factors)
        )
        return aliquot_clause
    clauses = cases.apply(lambda x: constraint_for_row(x), axis=1).values

    return pysmt.shortcuts.Or(clauses)


def satisfy_every_requirement_constraint_df(requirements, batch_containers_df, factors, variables, inputs,
                                            sample_types, sample_factors,
                                            na_sample_factors, batch_containers, aliquot_factors, column_factor,
                                            row_factor, samples, batch_factor, na_column_factors,
                                            aliquot_symmetry_samples,
                                            batch, aliquot_factor_map, requirements_df):
    """

    :param requirements:
    :param batch_containers_df:
    :param factors:
    :param variables:
    :param inputs:
    :param sample_types:
    :param sample_factors:
    :param na_sample_factors:
    :param batch_containers:
    :param aliquot_factors:
    :param column_factor:
    :param row_factor:
    :param samples:
    :param batch_factor:
    :param na_column_factors:
    :param aliquot_symmetry_samples:
    :param batch:
    :param aliquot_factor_map:
    :param requirements_df:
    :return:
    """
    batch_requirements = requirements_df.merge(batch.to_frame().transpose(),
                                               on=[factor_id for factor_id, factor in factors.items() if
                                                   factor['ftype'] == "batch"])
    cases = batch_requirements.merge(batch_containers_df)
    cases = cases.merge(inputs['sample_types_df'])
    if aliquot_symmetry_samples is not None:
        cases = cases.merge(aliquot_symmetry_samples)

    req_groups = cases.fillna("dummy").groupby(list(batch_requirements.columns))
    req_constraints_df = req_groups.apply(lambda x: get_req_constraint(x, factors, variables, inputs))
    req_constraints = list(req_constraints_df.values)

    exp_factors = [fname for fname, f in factors.items() if f['ftype'] == "experiment"]
    if len(exp_factors) > 0:
        exp_requirements = batch_requirements[exp_factors].drop_duplicates()
        req_exp = req_experiment_factors_df(exp_requirements)
        req_constraints.append(req_exp)

    return pysmt.shortcuts.And(req_constraints)


def satisfy_every_requirement_constraint(requirements, containers, factors, sample_types, sample_factors,
                                         na_sample_factors, batch_containers, aliquot_factors, column_factor,
                                         row_factor, samples, batch_factor, na_column_factors, aliquot_symmetry_samples,
                                         batch, aliquot_factor_map, requirements_df):
    req_constraints = []
    for r in requirements:
        if batch_can_satisfy_requirement(r, batch, factors):
            req_batch = req_batch_factors(r, r_batch_factors(r, factors), containers, sample_types, sample_factors,
                                          na_sample_factors, batch_containers, aliquot_factors, column_factor,
                                          row_factor,
                                          factors, samples, batch_factor, na_column_factors, aliquot_symmetry_samples,
                                          batch,
                                          aliquot_factor_map)
            if req_batch != None:
                req_exp = req_experiment_factors(r_exp_factors(r, factors), factors)
                req_constraints.append(pysmt.shortcuts.And(req_batch, req_exp))
    return pysmt.shortcuts.And(req_constraints)


def r_exp_factors(r, factors):
    return [f for f in r['factors'] if factors[f['factor']]['ftype'] == "experiment"]


def r_factors_of_type(r, factors, ftype):
    if type(r) == pd.Series:
        return [f for f, _ in r.items() if f in factors and factors[f]['ftype'] == ftype]
    else:
        return [f for f in r['factors'] if factors[f['factor']]['ftype'] == ftype]


def r_batch_factors(r, factors):
    if type(r) == Series:
        return [f for f in r if factors[f['factor']]['ftype'] == "batch"]
    else:
        return [f for f in r['factors'] if factors[f['factor']]['ftype'] == "batch"]


def r_column_factors(r, factors):
    return [f for f in r['factors'] if factors[f['factor']]['ftype'] == "column"]


def r_row_factors(r, factors):
    return [f for f in r['factors'] if factors[f['factor']]['ftype'] == "row"]


def r_aliquot_factors(r, factors):
    if type(r) == Series:
        return [f for f in r if factors[f['factor']]['ftype'] == "aliquot"]
    else:
        return [f for f in r['factors'] if factors[f['factor']]['ftype'] == "aliquot"]


def r_sample_factors(r, factors):
    return [f for f in r['factors'] if factors[f['factor']]['ftype'] == "sample"]


def expand_requirement(factors):
    # factors = requirement['factors']
    if len(factors) == 0:
        return []
    else:
        expansion = factor_cross_product(factors.copy(), [{}])
        return expansion


def factor_cross_product(factors, cross_product):
    if len(factors) == 0:
        return cross_product
    else:
        result = []
        factor = factors.pop(0)
        for elt in cross_product:
            for value in factor['values']:
                expansion = elt.copy()
                expansion.update({factor['factor']: value})
                result.append(expansion)
        return factor_cross_product(factors, result)


def get_req_const(factors_of_type, factor_id, level, factors):
    if factors[factor_id]['dtype'] == "str":
        pred = factors_of_type[factor_id][level]
    else:
        # l.debug(level)
        # l.debug(type(level))
        pred = pysmt.shortcuts.Equals(factors_of_type[factor_id], pysmt.shortcuts.Real(float(level)))
    return pred


def req_experiment_factors_df(requirements):
    return pysmt.shortcuts.And([pysmt.shortcuts.And([get_req_const(exp_factor, factor['factor'], level, factors)
                                                     for level in factor['values']])
                                for factor in r_exp_factors])


def req_experiment_factors(r_exp_factors, factors):
    return pysmt.shortcuts.And([pysmt.shortcuts.And([get_req_const(exp_factor, factor['factor'], level, factors)
                                                     for level in factor['values']])
                                for factor in r_exp_factors])


def sample_consistent_with_case(sample, case, sample_types, container):
    # l.debug("sample: %s case: %s sample_types %s", sample, case, inputs['sample_types'])
    if sample in sample_types and sample_types[sample]:
        for factor_id, level in case.items():
            if factor_id in sample_types[sample] and sample_types[sample][factor_id] != level:
                return False
    return True


def req_sample_factors_df(case, r_sample_factors, inputs, variables, aliquot, container,
                          factors):
    # cases = expand_requirement(r_sample_factors)
    # l.debug("factors: %s, aliquots: %s", r_sample_factors, samples)
    # l.debug("|cases| = %s, |samples| = %s", len(cases), len(samples))
    # assert (len(cases) <= len(samples))
    samples = inputs['samples'][container][aliquot]
    sample_factors = variables['sample_factors']
    na_sample_factors = variables['na_sample_factors']
    sample_types = inputs['sample_types']

    sample = case['sample']
    sample_factor_ids = r_factors_of_type(case, factors, "sample")
    if 'is_NA' in case and case['is_NA']:
        clause = \
                pysmt.shortcuts.And([  ## Every factor-level in case is co-satisfied
                    na_sample_factors[container][aliquot][sample][factor_id]
                    for factor_id, level in case.items() if factor_id in sample_factor_ids])



    else:

        clause = \
                pysmt.shortcuts.And([  ## Every factor-level in case is co-satisfied
                    pysmt.shortcuts.And(
                        get_req_const(sample_factors[container][aliquot][sample], factor_id, level, factors),
                        pysmt.shortcuts.Not(na_sample_factors[container][aliquot][sample][factor_id]))
                    for factor_id, level in case.items() if factor_id in sample_factor_ids])


    #        if not get_model(clause):
    return clause


def req_sample_factors(r, r_sample_factors, samples, aliquot, container, sample_types, sample_factors,
                       na_sample_factors, factors):
    cases = expand_requirement(r_sample_factors)
    # l.debug("factors: %s, aliquots: %s", r_sample_factors, samples)
    # l.debug("|cases| = %s, |samples| = %s", len(cases), len(samples))
    assert (len(cases) <= len(samples))

    if 'is_NA' in r and r['is_NA']:
        clause = pysmt.shortcuts.And([
            pysmt.shortcuts.And([  ## Exactly one sample satisfies the case
                pysmt.shortcuts.And([  ## Every factor-level in case is co-satisfied
                    na_sample_factors[container][aliquot][sample][factor_id]
                    for factor_id, level in case.items()])
                for sample in samples if sample_consistent_with_case(sample, case, sample_types, container)])
            for case in cases])

    else:

        clause = pysmt.shortcuts.And([  ## Every case of requirment is satisfied
            pysmt.shortcuts.ExactlyOne([  ## Exactly one sample satisfies the case
                pysmt.shortcuts.And([  ## Every factor-level in case is co-satisfied
                    pysmt.shortcuts.And(
                        get_req_const(sample_factors[container][aliquot][sample], factor_id, level, factors),
                        pysmt.shortcuts.Not(na_sample_factors[container][aliquot][sample][factor_id]))
                    for factor_id, level in case.items()])
                for sample in samples if sample_consistent_with_case(sample, case, sample_types, container)])
            for case in cases])
    #        if not get_model(clause):
    return clause


def case_consistent_with_container(case, container_id, container_assignment):
    """
    If using a container_assignment, indicate whether the case is consistent with it
    """
    if container_assignment:
        if container_id not in container_assignment:
            return False
        container_levels = container_assignment[container_id]
        for factor, level in case.items():
            if factor in container_levels:
                if level != container_levels[factor]:
                    return False
        return True
    else:
        return True


def req_aliquot_factors(r, r_aliquot_factors, containers, sample_types, sample_factors, na_sample_factors,
                        batch_containers, aliquot_factors, column_factor, row_factor, factors, samples,
                        batch_factor, na_column_factors, aliquot_symmetry_samples, batch,
                        aliquot_factor_map):
    """
    Disjunction over aliquots, conjunction over factors and levels
    """
    req_batch_factors = r_batch_factors(r, factors)
    reqs = r_aliquot_factors + r_column_factors(r, factors) + r_row_factors(r, factors) + req_batch_factors
    cases = expand_requirement(reqs)
    r_aliquot_factors_ids = [x['factor'] for x in r_aliquot_factors]
    r_batch_factor_ids = [x['factor'] for x in req_batch_factors]

    ## Is it an unsatisfiable requirement?
    case_clauses = []
    for case in cases:
        # possible_aliquots = []
        container_clauses = []
        for container_id, container in containers.items():
            if container_id in batch_containers:
                aliquot_clauses = []
                for aliquot in container['aliquots']:
                    # case_sample = expand_requirement(r_sample_factors(r, factors))[0]
                    if aliquot_can_satisfy_requirement(aliquot, container_id, container,
                                                       [{"factor": factor, "values": [level]} for factor, level in
                                                        case.items()],
                                                       aliquot_symmetry_samples,
                                                       aliquot_factor_map):
                        # possible_aliquots.append(aliquot)
                        aliquot_clause = pysmt.shortcuts.And(
                            ## Satisfy aliquot factors
                            pysmt.shortcuts.And(
                                [get_req_const(aliquot_factors[container_id][aliquot], factor_id, level, factors)
                                 for factor_id, level in case.items() if factor_id in r_aliquot_factors_ids]),
                            ## Batch factors for container of aliquot
                            pysmt.shortcuts.And(
                                [get_req_const(batch_factor[str(batch['batch'])], factor_id, level, factors)
                                 for factor_id, level in case.items() if
                                 factor_id in r_batch_factor_ids and factor_id != "batch"]),
                            ## Column factors for column of aliquot
                            req_column_factors(r, r_column_factors(r, factors), [case], container_id,
                                               [xplan_design.plate_layout_utils.get_aliquot_col(aliquot, container)], column_factor, factors,
                                               na_column_factors),
                            ## Row factors for row of aliquot
                            req_row_factors(r, r_row_factors(r, factors), [case], container_id,
                                            [xplan_design.plate_layout_utils.get_aliquot_row(aliquot, container)], row_factor, factors),
                            ## Sample factors for aliquot
                            req_sample_factors(r, r_sample_factors(r, factors), samples[container_id][aliquot], aliquot,
                                               container_id, sample_types, sample_factors, na_sample_factors, factors)
                        )
                        aliquot_clauses.append(aliquot_clause)
                if len(aliquot_clauses) > 0:
                    # req_measurment = next(iter([next(iter(f['values']))  for f in r['factors']  if f['factor'] == "measurement_type"]))
                    container_clauses.append(pysmt.shortcuts.ExactlyOne(aliquot_clauses))
            else:
                l.debug(f"Container id: {container_id} is not in batch_containers: {batch_containers}")
        if len(container_clauses) == 0:
            # pass
            l.warning("Requirement cannot be satisfied with containers in batch: %s %s", case, batch)
            # case_clauses.append(Or())
        else:
            # l.debug(f"Satisfying Requirement: {case}")
            case_clauses.append(pysmt.shortcuts.ExactlyOne(container_clauses))

        # assert(len(possible_aliquots) > 0)
    if len(case_clauses) == 0:
        clause = None
    else:
        clause = pysmt.shortcuts.And(case_clauses)
    """
    clause = \
      And([ ## Must satisfy all cases
          ExactlyOne([ ## A container must satisfy the case
              ExactlyOne([ ## An aliquot in the container must satisfy case
                  ## Aliquot must satisfy:
                  And(
                      ## Satisfy aliquot factors
                      And([get_req_const(aliquot_factors[container_id][aliquot], factor_id, level, factors)
                               for factor_id, level in case.items() if factor_id in r_aliquot_factors_ids]),
                      ## Batch factors for container of aliquot
                      And([get_req_const(batch_factor[container_id], factor_id, level, factors)
                               for factor_id, level in case.items() if factor_id in r_batch_factor_ids]),
                      ## Column factors for column of aliquot
                      req_column_factors(r, r_column_factors(r, factors), [case], container_id, [get_aliquot_col(aliquot, container)], column_factor, factors, na_column_factors),
                      ## Row factors for row of aliquot
                      req_row_factors(r, r_row_factors(r, factors), [case], container_id, [get_aliquot_row(aliquot, container)], row_factor, factors),
                      ## Sample factors for aliquot
                      req_sample_factors(r, r_sample_factors(r, factors), samples[container_id][aliquot], aliquot, container_id, sample_types, sample_factors, na_sample_factors, factors)
                     )
                    for aliquot in container['aliquots'] \
                          if aliquot_can_satisfy_requirement(aliquot, container_id, container, [{"factor" : factor, "values" : [level]}
                                                                           for factor, level in case.items()], aliquot_symmetry_samples)])
                    for container_id, container in containers.items() if case_consistent_with_container(case, container_id, container_assignment)])
            for case in cases])
    """
    return clause


def req_column_factors_df(case, r_column_factors, container_id, columns, variables, factors):
    """
    At least one of the columns must satisfy the factors in each case.
    """
    if len(r_column_factors) > 0:
        # cases = expand_requirement(r_column_factors)
        # assert(len(cases) <= len(columns))
        r_column_factors_ids = [x['name'] for x in r_column_factors]
        clause = pysmt.shortcuts.Or([
            pysmt.shortcuts.And([pysmt.shortcuts.And(
                get_req_const(variables['column_factor'][xplan_design.plate_layout_utils.get_column_name(column, container_id)], factor_id, level,
                              factors),
                pysmt.shortcuts.Not(variables['na_column_factors'][xplan_design.plate_layout_utils.get_column_name(column, container_id)][factor_id]))
                                    for factor_id, level in case.items() if
                                    factor_id in r_column_factors_ids and level != "dummy" and level != "NA" and not math.isnan(level)]
                                +
                                [variables['na_column_factors'][xplan_design.plate_layout_utils.get_column_name(column, container_id)][factor_id]
                                 for factor_id, level in case.items() if
                                 factor_id in r_column_factors_ids and level != "dummy" and  level == "NA"]
                                )
            for column in columns])

        return clause
    else:
        return pysmt.shortcuts.And()


def req_row_factors_df(case, r_row_factors, container_id, rows, variables, factors):
    if len(r_row_factors) > 0:
        # cases = expand_requirement(r_row_factors)
        # assert(len(cases) <= len(rows))
        r_row_factors_ids = [x['name'] for x in r_row_factors]
        clause = pysmt.shortcuts.Or([pysmt.shortcuts.And(pysmt.shortcuts.And(
            [get_req_const(variables['row_factor'][xplan_design.plate_layout_utils.get_row_name(row, container_id)], factor_id, level, factors)
             for factor_id, level in case.items() if factor_id in r_row_factors_ids])

        )
            for row in rows])

        return clause
    else:
        return pysmt.shortcuts.And()


def req_column_factors(r, r_column_factors, cases, container_id, columns, column_factor, factors, na_column_factors):
    """
    At least one of the columns must satisfy the factors in each case.
    """
    if len(r_column_factors) > 0:
        # cases = expand_requirement(r_column_factors)
        # assert(len(cases) <= len(columns))
        r_column_factors_ids = [x['factor'] for x in r_column_factors]
        clause = pysmt.shortcuts.And([pysmt.shortcuts.Or([
            pysmt.shortcuts.And([pysmt.shortcuts.And(
                get_req_const(column_factor[xplan_design.plate_layout_utils.get_column_name(column, container_id)], factor_id, level, factors),
                pysmt.shortcuts.Not(na_column_factors[xplan_design.plate_layout_utils.get_column_name(column, container_id)][factor_id]))
                                    for factor_id, level in case.items() if
                                    factor_id in r_column_factors_ids and level != "NA"]
                                +
                                [na_column_factors[xplan_design.plate_layout_utils.get_column_name(column, container_id)][factor_id]
                                 for factor_id, level in case.items() if
                                 factor_id in r_column_factors_ids and level == "NA"]
                                )
            for column in columns])
            for case in cases])
        return clause
    else:
        return pysmt.shortcuts.And()


def req_row_factors(r, r_row_factors, cases, container_id, rows, row_factor, factors):
    if len(r_row_factors) > 0:
        # cases = expand_requirement(r_row_factors)
        # assert(len(cases) <= len(rows))
        r_row_factors_ids = [x['factor'] for x in r_row_factors]
        clause = pysmt.shortcuts.And([pysmt.shortcuts.Or([pysmt.shortcuts.And(
            pysmt.shortcuts.And([get_req_const(row_factor[xplan_design.plate_layout_utils.get_row_name(row, container_id)], factor_id, level, factors)
                                 for factor_id, level in case.items() if factor_id in r_row_factors_ids])

        )
            for row in rows])
            for case in cases])
        return clause
    else:
        return pysmt.shortcuts.And()


def req_batch_factors(r, r_batch_factors, containers, sample_types, sample_factors, na_sample_factors,
                      batch_containers, aliquot_factors, column_factor, row_factor, factors, samples, batch_factor,
                      na_column_factors, aliquot_symmetry_samples, batch,
                      aliquot_factor_map):
    """
    Satisfying a batch requirement requires having enough containers to
    satisfy each combination
    """
    clause = req_aliquot_factors(r, r_aliquot_factors(r, factors), containers, sample_types, sample_factors,
                                 na_sample_factors, batch_containers, aliquot_factors, column_factor, row_factor,
                                 factors, samples, batch_factor, na_column_factors, aliquot_symmetry_samples, batch,
                                 aliquot_factor_map
                                 )
    return clause


def requirement_to_frame(requirement):
    return pd.DataFrame({factor_levels['factor']: factor_levels['values'] for factor_levels in requirement})


def aliquot_can_satisfy_requirement(aliquot, container_id, container, requirement, aliquot_symmetry_samples,
                                    aliquot_factor_map):
    """
    Are the aliquot properties consistent with requirement?
    Both are a conjunction of factor assignments, so make
    sure that aliquot is a subset of the requirement.

    """

    requirement_factors = [f['factor'] for f in requirement]
    requirement_levels = {f['factor']: [str(x) for x in f['values']] for f in requirement}

    # l.debug("Can sat? %s %s %s", container_id, aliquot, requirement)
    aliquot_properties = container['aliquots'][aliquot]

    if aliquot_symmetry_samples is not None:
        aliquot_samples = aliquot_symmetry_samples.loc[(aliquot_symmetry_samples.aliquot == aliquot) &
                                                       (aliquot_symmetry_samples.container == container_id)]
        aliquot_factors = aliquot_samples[requirement_factors].drop_duplicates()
        requirement_frame = requirement_to_frame(requirement).astype(object)
        merged = requirement_frame.merge(aliquot_factors.astype(object))
        if len(merged) == 0:
            return False

    req_cols = [int(l) for f in requirement for l in f['values'] if f['factor'] == 'column_id']
    if len(req_cols) > 0:
        aliquot_col_id = xplan_design.plate_layout_utils.get_column_id(xplan_design.plate_layout_utils.get_aliquot_col(aliquot, container))
        if aliquot_col_id not in req_cols:
            return False
        # l.debug("Column_id matches")
    req_rows = [int(l) for f in requirement for l in f['values'] if f['factor'] == 'row_id']
    if len(req_rows) > 0:
        aliquot_row_id = xplan_design.plate_layout_utils.get_row_id(xplan_design.plate_layout_utils.get_aliquot_row(aliquot, container))
        if aliquot_row_id not in req_rows:
            return False

    for factor, level in aliquot_properties.items():
        # l.debug("checking: %s %s", factor, level)
        if factor in requirement_factors:
            # l.debug("Is %s in %s", level, requirement_levels[factor])

            if aliquot_factor_map[factor][level] not in requirement_levels[factor]:
                # l.debug("no")
                return False

    # l.debug("yes")
    return True
    # l.debug("no")
    # return False ## Couldn't find a container with the aliquot satisfying requirement


def is_na_sample(sample):
    return pysmt.shortcuts.And([sample_is_na for _, sample_is_na in sample.items()])


def sample_satisfies_requirement(container_id, aliquot, sample, requirement, factors, sample_types, sample_factors,
                                 na_sample_factors):
    """
    Create a constraint that is satisfied if the factors associated with the sample satisfy the requirement.
    There exists
    """

    clause = \
        req_sample_factors(r_sample_factors(requirement, factors), sample, aliquot, container_id, sample_types,
                           sample_factors, na_sample_factors, factors)
    return clause


def get_sample_types(sample_factors, requirements):
    """
    Get the number of unique assignments to the sample factors in the requirements
    """
    experiment_design = pd.DataFrame()

    rows = []
    for condition_set in requirements:
        samples = xplan_design.plate_layout_utils.get_samples_from_condition_set(sample_factors, condition_set)
        # l.info("Condition set resulted in %s samples", len(samples))
        rows.append(samples)
    # experiment_design = experiment_design.append(samples, ignore_index=True)
    if len(rows) > 0:
        experiment_design = pd.concat(rows)

    return experiment_design.drop_duplicates()


def container_can_service_batch(container, batch_samples, aliquot_factor_map):
    container_df = xplan_design.plate_layout_utils.container_dict_to_df(container, aliquot_factor_map)
    intersection = container_df.merge(batch_samples)
    return len(intersection) > 0


def get_container_assignment(input, sample_types, strain_counts, aliquot_factor_map):
    """
    Pick a container for each combination of batch factors to avoid search
    """
    containers = input['containers']
    batch_factors = {x: y for x, y in input['factors'].items() if y['ftype'] == 'batch'}
    ## Hack to dropna, really need to determine which groups are consistent and use that as a lower bound on
    ## the container set.  Using dropna assumes that rows with nan will subsume another row.
    if 'batch' in batch_factors:
        batch_types = sample_types[list(batch_factors.keys())].drop_duplicates().dropna()
    else:
        batch_types = sample_types[list(batch_factors.keys())].drop_duplicates().dropna().reset_index(drop=True)
        batch_types['batch'] = batch_types.index
    l.debug("batch_types: %s", batch_types)

    assert (len(batch_types) <= len(containers))

    protocol = input['protocol']

    # container_assignment = batch_types.reset_index(drop=True).to_dict('index')

    if protocol == "cell_free_riboswitches":
        # Container assigment is not a partition like other protocols.
        # Map each container that has a DNA that is in the batch to the batch

        batch_strains = sample_types[["strain", "batch"]].drop_duplicates()

        def get_strain_container(x):
            strain_containers = [c for c in strain_counts if
                                 x['strain'] in strain_counts[c] and strain_counts[c][x['strain']] > 0]
            if len(strain_containers) == 0:
                l.exception(f"No container in {strain_counts} with {x['strain']}")
            container = next(iter(strain_containers))
            return container

        batch_strains['container'] = batch_strains.apply(get_strain_container, axis=1)
        container_assignment = batch_strains.drop(columns=["strain"])  # .set_index("container").to_dict('index')
        container_assignment = container_assignment.merge(batch_types)
    else:
        ## Set keys to str
        aliquot_factors = {x: y for x, y in input['factors'].items() if y['ftype'] != 'sample'}
        batch_aliquots = sample_types[
            list(aliquot_factors.keys())].drop_duplicates()  # get_sample_types(aliquot_factors, input['requirements'])
        batch_size = batch_aliquots.groupby(list(batch_factors.keys())).size().to_frame().reset_index()
        container_assignment = {}
        for batch_type_id, batch_type in batch_types.iterrows():
            batch_frame = batch_type.to_frame().transpose()
            this_batch_size = batch_frame.merge(batch_size).loc[0, 0]
            batch_samples = batch_aliquots.merge(batch_frame)
            if this_batch_size <= 0:
                continue
            ## Assign containers to this batch until covered
            for container_id, container in containers.items():
                if container_id in container_assignment:
                    continue
                container_size = len(container['aliquots'])
                if container_can_service_batch(container, batch_samples, aliquot_factor_map):
                    container_assignment[container_id] = json.loads(batch_type.to_json())
                    if 'batch' not in container_assignment[container_id]:
                        container_assignment[container_id]['batch'] = batch_type_id
                    this_batch_size -= container_size
                    if this_batch_size <= 0:
                        break

        ## Add remaining containers to first batch
        ## FIXME ensure that each container is compatible with batch
        for container_id, container in containers.items():
            if container_id in container_assignment:
                continue
            container_assignment[container_id] = json.loads(batch_types.loc[0, ].to_json())
        container_assignment = pd.read_json(json.dumps(container_assignment), orient="index").reset_index().rename(
            columns={"index": "container"})

    #    container_assignment = { str(list(containers.keys())[k]):v for k,v in container_assignment.items() }

    l.debug("container_assignment: %s", container_assignment)
    return container_assignment, batch_types


def fill_empty_aliquots(factors, requirements, sample_types):
    none_samples = sample_types.loc[sample_types.strain == "None"]
    none_replicates = none_samples.replicate.max()
    batch_factors = [x for x, y in factors.items() if y['ftype'] == 'batch']
    new_requirements = requirements
    if len(none_samples) > 0:
        for i, row in none_samples.iterrows():
            constraint = {"factors": [{"factor": x, "values": [y]}
                                      for x, y in row.items()
                                      if x != "is_NA"], "is_NA": row['is_NA']}
            new_requirements += [constraint]
            l.debug("new_requirement: %s", constraint)

        new_factors = factors.copy()
        if "None" not in new_factors['strain']['domain']:
            new_factors['strain']['domain'].append("None")
        if 'attributes' in factors['strain'] and "None" not in new_factors['strain']['attributes']:
            factor_attributes = list(set([key for _, v in factors['strain']['attributes'].items()
                                          for key in v.keys()]))
            new_factors['strain']['attributes']["None"] = {k: "None" for k in factor_attributes}
        new_factors['replicate']['domain'] = [1.0, max(factors['replicate']['domain'][1], float(none_replicates))]

        l.debug("new_factors: %s", new_factors['strain']['domain'])
        l.debug("replicate_domain: %s", new_factors['replicate']['domain'])
    else:
        new_factors = factors

    return new_factors, new_requirements


def _get_container_assignment_df(container_assignment):
    ca_df = pd.read_json(json.dumps(container_assignment), orient='index').reset_index().rename(
        columns={"level_0": "container"}).drop(columns=["index"])
    ca_df["container"] = ca_df["container"].astype(str)
    return ca_df


def get_column_symmetry(samples, factors, containers, container_assignment, aliquot_symmetry):
    # l.debug("Getting Symmetry Groups from: %s", samples)

    ## Symmetry for Columns.  It doesn't matter what column factors are applied to a column, so preselect

    ## Get the columns of the containers

    column_factors = [x for x, y in factors.items() if y['ftype'] == "column"]
    batch_factors = [x for x, y in factors.items() if y['ftype'] == "batch"]
    container_columns = pd.DataFrame()
    for container_id, container in containers.items():
        container_df = pd.DataFrame({"column": list(container['columns'].keys())})
        container_df.loc[:, 'container'] = container_id
        container_columns = container_columns.append(container_df, ignore_index=True)

    ## Get the number of columns needed for each combination of column factors

    aliquots_per_column_levels = samples.groupby(batch_factors + column_factors).apply(len)
    column_size = 8
    columns_per_column_levels = aliquots_per_column_levels.apply(
        lambda x: int(np.ceil(x / column_size))).reset_index().rename(columns={0: "count"})

    ## columns_per_column_levels will have one row per batch and column factor combination

    ## convert container_assignment to dataframe
    ca_df = _get_container_assignment_df(container_assignment)

    ## Do one batch at a time to ensure that columns come from assigned containers
    possible_column_levels = pd.DataFrame()
    batches_of_columns_per_column_levels = columns_per_column_levels.groupby(batch_factors)
    for batch, batch_columns_per_column_levels in batches_of_columns_per_column_levels:
        ## Get containers that can fulfill batch
        batch_container_columns = container_columns.merge(ca_df, on='container', how="inner").drop(
            columns=batch_factors)
        column_index = 0
        for _, level in batch_columns_per_column_levels.astype(str).iterrows():
            ## filter batch_container_columns columns on the basis of whether they can fulfill aliquots with level
            possible_columns_for_level = aliquot_symmetry.merge(level.to_frame().transpose().astype(str))[
                ['column', 'container']].drop_duplicates()
            possible_unused_columns_for_level = batch_container_columns.reset_index().merge(
                possible_columns_for_level).set_index('index')
            # next_column_index = int(column_index+level['count'])
            # level_columns = batch_container_columns.loc[container_columns.index[column_index:next_column_index]]
            level_columns = possible_unused_columns_for_level.iloc[:int(level['count'])]
            batch_container_columns = batch_container_columns.drop(level_columns.index)

            for factor in column_factors:
                level_columns.loc[:, factor] = level[factor]
            possible_column_levels = possible_column_levels.append(level_columns, ignore_index=True)
            # column_index = next_column_index

    return possible_column_levels


def _is_compatible(replicate_group, aliquot_and_container_properties):
    """
    Are the replicate group properties a superset of the aliquot and container properties?
    """
    common_cols = [x for x in replicate_group.columns if x in aliquot_and_container_properties.columns]
    if len(common_cols) > 0:
        compatible = aliquot_and_container_properties.merge(replicate_group, on=common_cols)
        return len(compatible) > 0
    else:
        return True


def _get_compatible_replicate_groups(aliquot, samples, non_replicate_factors, container_assignment_df,
                                     aliquot_factor_map):
    """
    Return a groupby object with only groups of replicates that are compatible with the aliquot.
    """

    aliquot_property_cols = [x for x in aliquot.columns if x not in ['container', 'aliquot', 'column', 'row']]
    assigned_container_properties = container_assignment_df.loc[
        container_assignment_df.container == aliquot.iloc[0].container]
    if len(aliquot_property_cols) == 0:
        aliquot_and_container_properties = assigned_container_properties
    else:
        aliquot_and_container_properties = pd.concat([assigned_container_properties.reset_index(drop=True),
                                                      aliquot[aliquot_property_cols].reset_index(drop=True)], axis=1)

    ## Get rid of non-properties
    for x in ['container', 'index']:
        if x in aliquot_and_container_properties.columns:
            aliquot_and_container_properties = aliquot_and_container_properties.drop(columns=[x])

    aliquot_samples = samples.merge(aliquot_and_container_properties)
    compatible_replicate_groups = aliquot_samples.groupby(non_replicate_factors)

    ## Need to find groups that are consistent
    #    compatible_replicate_groups = replicate_groups.apply(lambda x: _is_compatible(x, aliquot_and_container_properties))
    #    compatible_replicate_groups = compatible_replicate_groups.to_frame().reset_index()
    #    compatible_replicate_groups = compatible_replicate_groups.loc[compatible_replicate_groups[0] == True].drop(columns=[0])
    return compatible_replicate_groups


def get_containers_df(containers, factors, aliquot_factor_map):
    container_aliquots = pd.DataFrame()
    for container_id, container in containers.items():
        container_df = pd.read_json(json.dumps(container['aliquots']), orient='index')
        if len(container_df) == 0:
            container_df = pd.DataFrame(index=container['aliquots'])
        container_df.loc[:, 'container'] = container_id
        container_df = container_df.reset_index()
        container_df = container_df.rename(columns={"index": "aliquot"})
        container_df['column'] = container_df.apply(lambda x: xplan_design.plate_layout_utils.get_aliquot_col(x['aliquot'], containers[x['container']]),
                                                    axis=1)
        container_df['row'] = container_df.apply(lambda x: xplan_design.plate_layout_utils.get_aliquot_row(x['aliquot'], containers[x['container']]),
                                                 axis=1)
        container_aliquots = container_aliquots.append(container_df, ignore_index=True)

    for factor in factors:
        if factor in container_aliquots.columns:
            container_aliquots[factor] = container_aliquots[factor].apply(lambda x: aliquot_factor_map[factor][x])

    return container_aliquots


def get_aliquot_symmetry(samples, factors, container_aliquots, container_assignment, aliquot_factor_map):
    """
    For each aliquot, pick the possible replicates of each strain that can be placed in that aliquot.
    """

    non_replicate_factors = [x for x in samples.columns if x != "replicate"]
    column_factors = [x for x, y in factors.items() if y['ftype'] == "column"]
    non_replicate_non_column_factors = [x for x in non_replicate_factors if x not in column_factors]

    # replicate_groups = samples.drop_duplicates().groupby(non_replicate_factors)
    # replicate_groups_dict = dict(list(replicate_groups))

    na_replicate_group = samples[samples.isnull().any(axis=1)].merge(container_assignment)
    for x in ['container', 'index']:
        if x in na_replicate_group.columns:
            na_replicate_group = na_replicate_group.drop(columns=[x])

    ## For each aliquot, pick a member of each compatible replicate group.  Need to make sure that
    ## all replicates are represented, so we also need to keep an index into each group to pick the next
    ## replicate deterministically.
    replicate_group_index = samples.groupby(non_replicate_factors).apply(lambda x: 0)
    na_replicate_group_index = 0

    symmetry_break = pd.DataFrame()
    for _, aliquot in container_aliquots.iterrows():
        #        try:
        compatible_replicate_groups = _get_compatible_replicate_groups(aliquot.to_frame().transpose(), samples,
                                                                       non_replicate_factors, container_assignment,
                                                                       aliquot_factor_map)
        #        except Exception as e:

        aliquot_symmetry_break = pd.DataFrame()
        for group_key, replicate_group in compatible_replicate_groups:
            ## Get replicate from group
            # group_key = tuple(compatible_group.to_list())
            # replicate_group = replicate_groups_dict[group_key]
            replicate_idx = replicate_group_index[group_key]
            replicate = replicate_group.iloc[replicate_idx].to_frame().transpose()  # .infer_objects()

            ## update replicate index
            if replicate_group_index[group_key] + 1 == len(replicate_group):
                replicate_group_index[group_key] = 0
            else:
                replicate_group_index[group_key] += 1

            ## Add replicate to symmetry break
            aliquot_replicate = pd.concat(
                [aliquot.to_frame().transpose().reset_index(drop=True), replicate.reset_index(drop=True)], axis=1)
            # aliquot_replicate = aliquot_replicate.groupby(level=0, axis=1).min()
            aliquot_replicate = aliquot_replicate.loc[:, ~aliquot_replicate.columns.duplicated()]

            aliquot_symmetry_break = aliquot_symmetry_break.append(aliquot_replicate, ignore_index=True)

        ## Add NaN group replicates
        if len(na_replicate_group) > 0 and len(
                aliquot.to_frame().transpose().reset_index(drop=True).merge(na_replicate_group)) > 0:
            replicate_idx = na_replicate_group_index
            replicate = na_replicate_group.iloc[replicate_idx].to_frame().transpose().infer_objects()

            ## update replicate index
            if na_replicate_group_index + 1 == len(na_replicate_group):
                na_replicate_group_index = 0
            else:
                na_replicate_group_index += 1

            ## Add replicate to symmetry break
            aliquot_replicate = pd.concat(
                [aliquot.to_frame().transpose().reset_index(drop=True), replicate.reset_index(drop=True)], axis=1)
            aliquot_replicate = aliquot_replicate.loc[:, ~aliquot_replicate.columns.duplicated()]
            aliquot_symmetry_break = aliquot_symmetry_break.append(aliquot_replicate, ignore_index=True)

        symmetry_break = symmetry_break.append(aliquot_symmetry_break, ignore_index=True)

    return symmetry_break


def require_na_samples(requirements, sample_types, common_samples):
    """
    Augment requirements to be closed-world.  I.e., state what samples are not desired and thus not applicable.
    """

    non_na_cols = list(sample_types.columns)
    non_sample_cols = list(set(sample_types.columns) - set(common_samples.columns))

    sample_types = sample_types.fillna("dummy")

    # Get the cases where no measurements were specified and add NA to them
    dummy_samples = sample_types.query(" and ".join([f"`{col}` == \'dummy\'" for col in common_samples.columns])).drop(
        columns=common_samples.columns)

    desc = sample_types.drop(columns=common_samples.columns).drop_duplicates()

    # Addtional samples are NA
    na_samples = common_samples
    na_samples['is_NA'] = True
    na_samples['key'] = 0

    ## desc = dummy_samples
    desc['key'] = 0
    na_samples = na_samples.merge(desc, on='key').drop(columns=['key'])

    def subsumes(y, x):
        # Do y subsume x?  Is y more general than x? is y subseteq x
        for col in y.keys():
            if y[col] != "dummy" and y[col] != x[col]:
                return False
        return True

    def subsumed(x, df):
        # A row is subsumed if there is another row that is less specific that covers it

        # get all rows that subsume this row
        subsumes_df = df.apply(lambda y: subsumes(y, x), axis=1)
        return subsumes_df.sum() > 1

    # na_samples['subsumed'] = na_samples.apply(lambda x: subsumed(x, na_samples), axis=1)
    # na_samples = na_samples[na_samples.subsumed].drop(columns=['subsumed'])

    # Existing samples are not NA
    sample_types['is_NA'] = False

    # Assumes all None strain are NA
    sample_types = sample_types.loc[sample_types.strain != "None"].set_index(non_na_cols).combine_first(
        na_samples.set_index(non_na_cols)).reset_index().replace('dummy', np.nan)

    na_sample_types = sample_types.loc[sample_types['is_NA'] == True]
    na_records = json.loads(na_sample_types.to_json(orient='records'))

    # l.debug(f"na_samples: {na_sample_types}")

    def record_to_requirement(record):
        factors = []
        is_NA = False
        for k, v in record.items():
            if k == "is_NA":
                is_NA = v
            elif v is not None:
                factors.append({"factor": k, "values": [v]})
        requirement = {"factors": factors, "is_NA": is_NA}
        return requirement

    na_requirements = [record_to_requirement(x) for x in na_records]

    requirements += na_requirements

    return requirements


def get_symmetry(samples, factors, containers, container_assignment, aliquot_factor_map):
    """
    For each aliquot, pick representative from each symmetry group to use.
    """
    # l.debug("Getting Symmetry Groups from: %s", samples)

    aliquot_symmetry = get_aliquot_symmetry(samples, factors, containers, container_assignment, aliquot_factor_map)
    # column_symmetry = get_column_symmetry(samples, factors, containers, container_assignment, aliquot_symmetry)
    na_aliquot_symmetry = aliquot_symmetry[aliquot_symmetry.isnull().any(axis=1)]
    # symmetry = aliquot_symmetry.merge(column_symmetry)
    symmetry = aliquot_symmetry
    symmetry = symmetry.append(na_aliquot_symmetry, ignore_index=True)

    return symmetry


def map_floats(input, precision=7):
    """
    To avoid problems in the solver with cases where rational representation
    of floats leads to difficulty comparing values, we map floats so that
    their rational representation is consistent.
    :param input:
    :return:
    """

    float_map = {}

    def is_mappable(factor):
        return factor['dtype'] == "float" and "_concentration" in factor['name']

    ## Map Requirements
    factors = input['factors']
    for _, factor in factors.items():
        if is_mappable(factor):
            possible_factor_values = set([])
            for requirement in input['requirements']:
                for factor_values in requirement['factors']:
                    if factor['name'] == factor_values['factor']:
                        possible_factor_values = possible_factor_values.union(set(factor_values['values']))
                        break
            possible_factor_values = set(round(x, precision) for x in possible_factor_values if x == x)
            possible_factor_values = list(possible_factor_values)
            possible_factor_values.sort()
            num_values = len(possible_factor_values)

            map = {"original_domain": factor['domain'],
                   "mapped_domain": [0.0, float(len(possible_factor_values) - 1)],
                   "values": {float(x): y for y, x in enumerate(possible_factor_values)},
                   "reverse_values": {y: float(x) for y, x in enumerate(possible_factor_values)}}
            float_map[factor['name']] = map

            factor['domain'] = map['mapped_domain']

            for requirement in input['requirements']:
                for factor_values in requirement['factors']:
                    if factor['name'] == factor_values['factor']:
                        new_values = []
                        for value in factor_values['values']:
                            if not math.isnan(value):
                                new_value = map["values"][round(value, precision)]
                            else:
                                new_value = value
                            new_values.append(new_value)
                        factor_values['values'] = new_values
            input['requirements_df'][factor['name']] = input['requirements_df'][factor['name']].apply(lambda x: map['values'][round(x, precision)] if not math.isnan(x) else x)
            if factor['ftype'] == "sample":
                input['sample_types_df'][factor['name']] = input['sample_types_df'][factor['name']].apply(
                    lambda x: map['values'][round(x, precision)]  if not math.isnan(x) else x)

    # Map sample_types
    for i, sample_type in input['sample_types'].items():
        for factor, level in sample_type.items():
            if factor in float_map:
                sample_type[factor] = float_map[factor]['values'][round(level, precision)]

    return float_map


def solve1(input, pick_container_assignment=True, hand_coded_constraints=None):
    """
    Convert input to encoding and invoke solver.  Return model if exists.
    """
    pd.set_option("display.max_rows", 200)

    sample_types = get_sample_types(input['factors'], input['requirements'])

    ## By default, every requirement specifies a sample that must be satisfied
    sample_types['is_NA'] = False

    l.debug("sample_types: %s", sample_types)
    containers = input['containers']
    l.debug(containers)

    input["aliquot_factor_map"] = get_aliquot_factor_map(containers, input['factors'])
    input['containers_df'] = get_containers_df(input['containers'], input['factors'], input['aliquot_factor_map'])

    strain_counts = {k: get_strain_count(v, input['aliquot_factor_map']['strain']) for k, v in containers.items()}
    l.debug("container strain count: %s", strain_counts)
    container_strains = set([x for _, s in strain_counts.items() for x in s])
    l.debug("container_strains %s", container_strains)

    input['container_assignment'], batch_types = get_container_assignment(input, sample_types, strain_counts,
                                                                          input["aliquot_factor_map"])
    assigned_containers = input['container_assignment'].container.unique()
    unused_containers = [container_id for container_id in input['containers'] if
                         container_id not in assigned_containers]
    for container_id in unused_containers:
        del input['containers'][container_id]

    sample_factors = {x: y for x, y in input['factors'].items() if y['ftype'] == 'sample'}
    non_sample_factors = {x: y for x, y in input['factors'].items() if y['ftype'] != 'sample'}
    l.debug("sample_factors: %s", sample_factors)

    ## Get the requirements for each sample in the experiment
    requirement_strains = set(list(sample_types.strain.unique()))
    l.debug("requirement strains: %s", requirement_strains)
    l.debug("strains unique to containers: %s", container_strains.difference(requirement_strains))
    requested_but_unsupplied_strains = requirement_strains.difference(container_strains)
    l.debug("strains unique to requirements: %s", requested_but_unsupplied_strains)

    ## Check whether containers have all the strains listed in the request
    if len(requested_but_unsupplied_strains) > 0:
        l.exception(f"Requested strains that are not present in containers: {requested_but_unsupplied_strains}")

    ## Strains in requirements need to be in the condition space
    for requirement in input['requirements']:
        for factor in requirement['factors']:
            if factor['factor'] == "strain":
                for level in factor["values"]:
                    if level not in input['factors']['strain']['domain']:
                        input['factors']['strain']['domain'].append(level)

    input, sample_types = preprocess_containers(input, sample_types, strain_counts, sample_factors,
                                                input['container_assignment'])
    common_samples = sample_types[list(sample_factors.keys())].drop_duplicates().replace("None",
                                                                                         np.nan).dropna()  # .reset_index()
    num_samples = len(common_samples)
    l.info("num_samples: %s", num_samples)

    input['samples'] = {
        c: {
            a: {
                x: "x{}_{}_{}".format(x, a, c) for x in range(0, num_samples)}
            for a in containers[c]['aliquots']}
        for c in containers}

    input['sample_types'] = {i: x for i, x in enumerate(common_samples.to_dict('records'))}
    input['sample_types_df'] = pd.DataFrame.from_dict(input['sample_types'], orient='index').reset_index().rename(
        columns={"index": "sample"})
    l.debug("sample_types: %s", input['sample_types'])

    non_samples = sample_types[list(non_sample_factors.keys())]
    non_samples = non_samples.drop_duplicates().reset_index(drop=True)

    # input['requirements'] = require_na_samples(input['requirements'], sample_types, common_samples)
    input['requirements_df'] = sample_types
    input['float_map'] = map_floats(input)

    input['aliquot_symmetry_samples'] = None #get_symmetry(non_samples, non_sample_factors, input['containers_df'],
                                             #        input['container_assignment'], input["aliquot_factor_map"])

    l.info("Generating Constraints ...")

    solutions = []
    # for batch in json.loads(batch_types.to_json(orient="records")):
    for _, batch in batch_types.iterrows():
        variables, constraints = generate_constraints1(input, batch)

        if hand_coded_constraints:
            for hc_c in hand_coded_constraints:
                l.info("hand coded constraint: %s", hc_c)
                constraints[hc_c] = eval(hc_c)

        l.info("Solving ...")
        model = pysmt.shortcuts.get_model(pysmt.shortcuts.And([v for k, v in constraints.items()]))

        if model is None:

            conj = conjunctive_partition(pysmt.shortcuts.And(constraints.values()))
            ucore = pysmt.shortcuts.get_unsat_core(conj)
            l.info("UNSAT-Core size '%d'" % len(ucore))
            for f in ucore:
                l.debug(f.serialize())

            for n1, c1 in constraints.items():
                for n2, c2 in constraints.items():
                    if n1 != n2:
                        m = pysmt.shortcuts.get_model(pysmt.shortcuts.And(c1, c2))
                        if m is None:
                            l.exception(f"Inconsistent Pair of constraints: {n1} {n2}")
                            conj = conjunctive_partition(pysmt.shortcuts.And(c1, c2))
                            ucore = pysmt.shortcuts.get_unsat_core(conj)
                            l.exception("UNSAT-Core size '%d'" % len(ucore))
                            for f in ucore:
                                l.exception(f.serialize())
        else:
            solutions.append((model, variables))

    return solutions


def get_aliquot_factor_map(c2ds, factors):
    """
    The containers sometimes use different values for their factors than those
    that are specified in the experiment request.  This function decides what values
    to use for a factor if the factor has additional attributes that will match with
    values in the container aliquot properties.
    :param c2ds: containers
    :param factors: experimental request factors
    :return: { factor : mapped_value}
    """
    ## Initialize map with all factors that don't have other possbible values
    aliquot_factor_map = {factor_id: {level: level for level in factor['domain']}
                          for factor_id, factor in factors.items() if 'attributes' not in factor}

    ## Get mapping for all mappable factors
    for factor in factors:
        if factor not in aliquot_factor_map:
            container_levels = set([aliquot_properties[factor]
                                    for container_id, container in c2ds.items()
                                    for aliquot_id, aliquot_properties in container['aliquots'].items()
                                    if factor in aliquot_properties])
            factor_attributes = list(set([key for _, v in factors[factor]['attributes'].items()
                                          for key in v.keys()]))
            factor_levels = {attribute: set([v[attribute] for _, v in factors[factor]['attributes'].items()])
                             for attribute in factor_attributes}
            level_intersection = {attribute: len(container_levels.intersection(factor_levels[attribute]))
                                  for attribute in factor_attributes}
            best_attribute = max(level_intersection, key=level_intersection.get)
            factor_map = {factors[factor]['attributes'][level][best_attribute]: level
                          for level in factors[factor]['domain']
                          if level in factors[factor]['attributes']}
            factor_unmap = {level: level
                            for level in factors[factor]['domain']
                            if level not in factors[factor]['attributes']}
            factor_map.update(factor_unmap)
            ## for container levels not found in factor, add them as a self map
            unmapped_levels = {level: level for level in container_levels if level not in factor_map}
            factor_map.update(unmapped_levels)
            aliquot_factor_map[factor] = factor_map

    # l.debug(f"aliquot_factor_map: {aliquot_factor_map}")
    return aliquot_factor_map


def preprocess_containers(input, sample_types, strain_counts, sample_factors, container_assignment):
    """
    Update factors so that they can express what is in a container.
    Determine how many wells are to be occupied by MediaControl.
    Determine how many wells are to be empty.
    Update factors and requirements to ensure each well is assigned.
    """

    containers = input['containers']
    l.debug("containers: %s", containers)

    ### Update Factors and Requirements, (mostly) independent of containers ####

    ## Num MediaControl wells in requirements
    num_media_control_required = len(sample_types.loc[sample_types.strain == "MediaControl"].drop(
        columns=list(sample_factors.keys())).drop_duplicates())

    ## Add MediaControl to strain domain if it is part of a container, but not specifically required
    num_media_wells_allocated = sum([c["MediaControl"] for c_id, c in strain_counts.items() if "MediaControl" in c])
    if num_media_wells_allocated > 0 and "MediaControl" not in input['factors']['strain']['domain']:
        input['factors']['strain']['domain'].append("MediaControl")
    input['factors']['strain']['domain'].append("None")

    num_media_wells_needed = num_media_control_required - num_media_wells_allocated

    ## Convert blank well requirements to "None" strain
    for requirement in input['requirements']:
        for factor in requirement['factors']:
            if factor['factor'] == "strain" and "" in factor["values"]:
                factor["values"] = [x if x != "" else "None" for x in factor["values"]]

    if num_media_wells_needed < 0:
        ## For each batch
        ## Add enough media controls for all containers in batch
        ca_df = container_assignment
        batches = ca_df.drop(columns="container").drop_duplicates()
        for _, batch in batches.iterrows():
            batch_containers = batch.to_frame().transpose().merge(ca_df).container.unique()
            num_media_control = 0
            for container in batch_containers:
                if 'MediaControl' in strain_counts[container]:
                    num_media_control += strain_counts[container]['MediaControl']

            media_control_requirement = {"factors": [{"factor": "strain", "values": ["MediaControl"]},
                                                     {"factor": "replicate",
                                                      "values": [x for x in range(1, num_media_control + 1)]}] +
                                                    [{"factor": factor, "values": [value]} for factor, value in
                                                     batch.items()]
                                         }
            # input['requirements'].append(media_control_requirement)
            df_data = {"strain": ["MediaControl" for x in range(num_media_control)],
                       "replicate": [x for x in range(1, num_media_control + 1)]}
            for factor, value in batch.items():
                df_data.update({factor: [value for x in range(1, num_media_control + 1)]})
            media_control_df = pd.DataFrame(data=df_data)
            # sample_types = sample_types.append(media_control_df, ignore_index=True)
            ## Remove MediaControl from containers if not required
            for container_id, container in containers.items():
                aliquots_to_remove = []
                for aliquot in container['aliquots']:
                    if container['aliquots'][aliquot]['strain'] == "MediaControl":
                        if num_media_wells_needed < 0:
                            num_media_wells_needed += 1
                            aliquots_to_remove.append(aliquot)
                for aliquot in aliquots_to_remove:
                    del container['aliquots'][aliquot]
    elif num_media_wells_needed > 0:
        ## Have more media wells required than allocated
        ## Need to map media controls to empty wells
        ## Update strain for empty wells to be media control
        ca_df = container_assignment
        batches = ca_df.drop(columns="container").drop_duplicates()
        for _, batch in batches.iterrows():
            batch_containers = batch.to_frame().transpose().merge(ca_df).container.unique()
            num_media_control_for_batch = len(
                sample_types.loc[sample_types.strain == "MediaControl"].merge(batch.to_frame().transpose()).drop(
                    columns=list(sample_factors.keys())).drop_duplicates())
            if num_media_control_for_batch > 0:
                ## Assign empty wells in containers to be media control
                for container in batch_containers:
                    empty_aliquots = {k: v for k, v in containers[container]['aliquots'].items() if
                                      v['strain'] == "None"}
                    while num_media_control_for_batch > 0 and len(empty_aliquots) > 0:
                        aliquot_to_assign = next(iter(empty_aliquots))
                        containers[container]['aliquots'][aliquot_to_assign]['strain'] = "MediaControl"
                        del empty_aliquots[aliquot_to_assign]
                        num_media_control_for_batch -= 1

    batch_factors = [x for x, y in input['factors'].items() if y['ftype'] == 'batch']
    batches = sample_types[batch_factors].drop_duplicates().dropna()
    l.debug("Required batches: %s", batches)

    ## Check how many aliquots are needed and ensure that containers will provide that many
    #    l.info("# container aliquots = %s, num_aliquots needed = %s, empty = %s", num_container_aliquots, len(aliquot_samples), num_empty_for_none)
    #    assert(num_container_aliquots >= len(aliquot_samples))

    def compute_num_empty_per_batch(batch, batch_containers, sample_factors, batch_factors):
        """
        Num empty per batch is:
        (#aliquots in containers for batch) -  (num_required non empty)
        """
        l.debug("Computing empties for batch: %s", batch)
        ## Get the containers for the batch
        container_indices = batch_containers.merge(batch, how='inner').container.astype(str).unique()
        num_aliquots_for_batch = sum([len(containers[c]['aliquots']) for c in container_indices])

        batch_measurements = batch[sample_factors].drop_duplicates()
        batch_aliquots = batch.drop(columns=sample_factors).drop_duplicates()
        batch_desc = batch[batch_factors].drop_duplicates()

        ## Get num non empty required
        num_non_empty = len(batch_aliquots)
        num_empty = num_aliquots_for_batch - num_non_empty

        if num_empty > 0:
            empties = pd.DataFrame({"replicate": [x + 1 for x in range(0, num_empty)]})
            empties.loc[:, "strain"] = "None"
            empties["is_NA"] = True
            empties['key'] = 1
            batch_measurements['key'] = 1
            batch_desc['key'] = 1
            batch_measurements = batch_measurements.merge(batch_desc, on='key')
            na_samples = empties.merge(batch_measurements, on='key').drop(columns=['key'])
            # for factor in batch_factors:
            #    empties.loc[:, factor] = batch[factor].unique()[0]
            batch = batch.append(na_samples, ignore_index=True)

        l.debug("Done Computing empties for batch: %s", batch)
        return batch

    # batch_aliquots = sample_types.drop(columns=sample_factors).drop_duplicates().reset_index()
    # batch_containers = container_assignment
    # batch_containers['container'] = batch_containers.index
    # l.debug("batch_containers: %s", batch_containers)
    ## If there are multiple containers per batch, then need to
    # batch_aliquots = batch_aliquots.merge(batch_containers, on=batch_factors, how='inner')
    # l.debug("batch_aliquots: %s", batch_aliquots)
    # batch_aliquots = batch_aliquots.groupby(batch_factors)
    # l.debug("Batch aliquots:")
    # for g, ba in batch_aliquots:
    #   l.debug(g)
    #   l.debug(ba)

    sample_types = sample_types.groupby(batch_factors).apply(
        lambda x: compute_num_empty_per_batch(x, container_assignment, sample_factors, batch_factors))
    sample_types = sample_types.reset_index(drop=True)

    # l.debug("Batch aliquots: %s", batch_aliquots)
    #    for g, ba in batch_aliquots:
    #       l.debug(g)
    #       l.debug(ba)

    ## Fill requirements with empty samples to place in unused aliquots
    # num_empty_for_none = num_empty_wells - num_media_control_required - num_strain_unallocated
    # num_blank_required = len(sample_types.loc[sample_types.strain==""].drop(columns=list(sample_factors.keys())).drop_duplicates().dropna())
    # old_num_requirements = len(input['requirements'])
    input['factors'], input['requirements'] = fill_empty_aliquots(input['factors'],
                                                                  input['requirements'],
                                                                  sample_types
                                                                  # num_empty_for_none,
                                                                  # num_blank_required
                                                                  )
    # new_requiements = input['requirements'][old_num_requirements:]
    # new_sample_types = get_sample_types(input['factors'], new_requiements)
    # sample_types = sample_types.append(new_sample_types, ignore_index=True)

    return input, sample_types


def get_model_pd(model, variables, factors, float_map):
    if not model:
        l.info("No Solution Found!")
        return None

    experiment_df = pd.DataFrame()
    batch_df = pd.DataFrame()
    column_df = pd.DataFrame()
    na_column_df = pd.DataFrame()
    row_df = pd.DataFrame()
    aliquot_df = pd.DataFrame()
    sample_df = pd.DataFrame()
    na_sample_df = pd.DataFrame()

    experiment_dict = {}
    batch_dict = {}
    column_dict = {}
    na_column_dict = {}
    row_dict = {}
    aliquot_dict = {}
    sample_dict = {}
    na_sample_dict = {}

    def info_to_df(info, value):
        def sub_factor_value(x, value):
            for col in x.index:
                if col in factors:
                    # if col == "temperature":
                    # l.debug("Set %s = %s", col, value)
                    if value.is_int_constant():
                        x[col] = int(value.constant_value())
                    elif value.is_real_constant():
                        x[col] = float(value.constant_value())
            return x

        info_df = pd.DataFrame()
        df = info_df.append(info, ignore_index=True)
        if value.is_int_constant() or value.is_real_constant():
            df = df.apply(lambda x: sub_factor_value(x, value), axis=1)
        return df

    def merge_into_dict(d, info, value, on):

        def sub_factor_value(x, value):
            for col in x:
                if col in factors and col != "batch" and col != "column_id" and col != "row_id":
                    # if col == "temperature":
                    # l.debug("Set %s = %s", col, value)
                    if value.is_int_constant():
                        x[col] = int(value.constant_value())
                    elif value.is_real_constant():
                        x[col] = float(value.constant_value())
            return x

        key = tuple([v for k, v in info.items() if k in on])

        if value.is_int_constant() or value.is_real_constant():
            info = sub_factor_value(info, value)

        if key in d:
            d[key].update(info)
        else:
            d[key] = info.copy()

        return d

    def merge_info_df(df, info, value, on):
        if len(df) > 0:
            # l.debug("Merge L: %s", df)
            # l.debug("Merge R: %s", info_to_df(info))
            # onon = df.columns.intersection(info_to_df(info).columns)
            # l.debug("onon %s", onon.values)
            # df = df.merge(info_to_df(info),  how='outer', on=list(onon.values))#, suffixes=('', '_y'))
            def preserve_na(s1, s2):
                for i, v in s2.items():
                    if v == "NA" or pd.isnull(s1[i]):
                        s1[i] = v
                return s1

            if on:
                df = df.set_index(on).combine_first(info_to_df(info, value).set_index(on)).reset_index()
                # df = df.set_index(on).combine(info_to_df(info, value).set_index(on), preserve_na, overwrite=False).reset_index()
            else:
                df = df.combine_first(info_to_df(info, value))
                # df = df.combine(info_to_df(info, value), preserve_na, overwrite=False)
            # to_drop = [x for x in df if x.endswith('_y')]
            # df = df.drop(to_drop, axis=1)

            # l.debug("Merge O: %s", df)
        else:
            df = df.append(info_to_df(info, value), ignore_index=True)
        return df

    for var, value in model:
        if value.is_true() or value.is_int_constant() or value.is_real_constant():
            if str(var) in variables['reverse_index']:
                # l.debug("{} = {}".format(var, value))
                info = variables['reverse_index'][str(var)]

                # l.debug("info = %s", info)
                if info['type'] == 'aliquot':
                    # aliquot_df = merge_info_df(aliquot_df, info, value, ["aliquot", "container"])
                    aliquot_dict = merge_into_dict(aliquot_dict, info, value, ["container", "aliquot"])
                elif info['type'] == 'sample':
                    # sample_df = merge_info_df(sample_df, info, value, "sample")
                    sample_dict = merge_into_dict(sample_dict, info, value, "sample")
                elif info['type'] == 'batch':
                    # batch_df = merge_info_df(batch_df, info, value, "container")
                    batch_dict = merge_into_dict(batch_dict, info, value, "batch")
                elif info['type'] == 'column':
                    # column_df = merge_info_df(column_df, info, value, "column")
                    column_dict = merge_into_dict(column_dict, info, value, "column")
                elif info['type'] == 'na_sample_factor':
                    # na_sample_df = merge_info_df(na_sample_df, info, value, "sample")
                    na_sample_dict = merge_into_dict(na_sample_dict, info, value, "sample")
                elif info['type'] == 'na_column':
                    # na_column_df = merge_info_df(na_column_df, info, value, "column")
                    na_column_dict = merge_into_dict(na_column_dict, info, value, "column")
                elif info['type'] == 'row':
                    # row_df = merge_info_df(row_df, info, value, "row")
                    row_dict = merge_into_dict(row_dict, info, value, "row")
                elif info['type'] == 'experiment':
                    l.debug("info: %s", info)
                    # experiment_df = experiment_df(experiment_df, info, value, None)
                    experiment_dict = experiment_df(experiment_dict, info, value, None)

    experiment_df = pd.DataFrame.from_records(experiment_dict).T.reset_index(drop=True)
    batch_df = pd.DataFrame.from_records(batch_dict).T.reset_index(drop=True)
    column_df = pd.DataFrame.from_records(column_dict).T.reset_index(drop=True)
    na_column_df = pd.DataFrame.from_records(na_column_dict).T.reset_index(drop=True)
    row_df = pd.DataFrame.from_records(row_dict).T.reset_index(drop=True)
    aliquot_df = pd.DataFrame.from_records(aliquot_dict).T.reset_index(drop=True)
    sample_df = pd.DataFrame.from_records(sample_dict).T.reset_index(drop=True)
    na_sample_df = pd.DataFrame.from_records(na_sample_dict).T.reset_index(drop=True)

    l.debug("aliquot_df %s", aliquot_df)
    l.debug("sample_df %s", sample_df)
    l.debug("na_sample_df %s", na_sample_df)
    l.debug("column_df %s", column_df)
    l.debug("na_column_df %s", na_column_df)
    l.debug("row_df %s", row_df)
    l.debug("batch_df %s", batch_df)
    l.debug("experiment_df %s", experiment_df)

    if len(na_sample_df) > 0:
        ## Override values chosen for samples by NA if needed
        sample_df = na_sample_df.replace(np.nan, "NA").set_index("sample").combine_first(
            sample_df.set_index("sample")).reset_index()
        ## drop samples that are NA
        sample_df = sample_df.replace("NA", np.nan).dropna().reset_index()
        l.debug("sample_df after dropping NA: %s", sample_df)

    df = aliquot_df.drop(columns=['type']).merge(sample_df.drop(columns=['type']), on=["aliquot", "container"])
    if len(column_df) > 0:
        if len(na_column_df) > 0:
            ## Override values chosen for columns by NA if needed
            column_df = na_column_df.set_index("column").combine_first(column_df.set_index("column")).reset_index()
        merge_cols = ["container", "column"]
        if 'column_id' in df.columns:
            merge_cols.append('column_id')
        df = df.merge(column_df.drop(columns=['type']), on=merge_cols)
    if len(row_df) > 0:
        df = df.merge(row_df.drop(columns=['type']), on=["container", "row"])

    if len(batch_df) > 0:
        df['key'] = 0
        batch_df['key'] = 0
        df = df.merge(batch_df.drop(columns=['type']), on=['key']).drop(columns=['key'])

    if len(experiment_df) > 0:
        df['key'] = 0
        experiment_df['key'] = 0
        df = df.merge(experiment_df, on=['key']).drop(columns=['key'])

    ## map floats back to original values
    for factor_id, float_map in float_map.items():
        df[factor_id] = df[factor_id].map(float_map["reverse_values"], na_action="ignore")

    l.debug("df %s", df)
    # l.debug(aliquot_df.loc[aliquot_df.aliquot=='a5'])
    # l.debug(sample_df.loc[sample_df.aliquot=='a5'])
    # df = experiment_df
    # aliquot_df['key'] = 0
    # l.debug(aliquot_df)
    # l.debug(df)
    # df = df.merge(aliquot_df, on=['container'])

    #    df = aliquot_df
    #    l.debug(df)
    #    df = df.drop(columns=['type'])
    #    batch_df = batch_df.drop(columns=['type'])

    #    l.debug(batch_df)
    #    df = df.merge(batch_df, on='container')

    #    df = df.sort_values(by=['aliquot'])
    # l.debug(df.loc[df.aliquot=='a5'])
    # df.to_csv("dan.csv")
    return df
