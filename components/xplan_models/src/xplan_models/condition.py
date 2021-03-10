import os
import pandas as pd
import json
import numpy as np
import logging
import random
import math
import copy
from xplan_models.utility import Utility, UtilityFunction
from xplan_models.plotting import plot_data, convert_row_name

l = logging.getLogger(__file__)
l.setLevel(logging.INFO)

# this is the value that will be filled in as standard deviation
# for rows with no observations.
MAX_ERROR = 0.5

class Conditions:
    OD = "od"
    TEMPERATURE = "temperature"
    MEDIA = "media"
    STRAIN = "strain"
    GATE = "gate"
    INPUT = "input"
    DURATION = "duration"

    SCORE = "score"
    RANK_ERROR = "rank_error"
    ENTROPY = "entropy"
    CORRECTNESS = "correctness"
    BAYES_CORRECTNESS = "bayes_correctness"
    STANDARD_ERROR = "standard_error"
    PROBABILITY_CORRECT_LIVE_MEAN = "probability_correct_live_mean"
    COUNT = "count"
    SUM_SQ_DIFF = 'sum_sq_diff'
    STANDARD_DEV = 'standard_dev'
    ITERATION = 'iteration'


class Factor(dict):
    def __init__(self, **kwargs):
        super(Factor, self).__init__(**kwargs)
        self['otype'] = self.__class__.__name__
        self.set_utility_obj()

    def set_utility_obj(self):
        ## Represent utility functions as objects to encapsulate evaluation.
        if 'utility' in self:
            self['utility_obj'] = Utility.createUtility(factor=self)

    def del_utility_obj(self):
        ## Represent utility functions as objects to encapsulate evaluation.
        if 'utility_obj' in self:
            del self['utility_obj']

    def weight(self):
        if 'weight' in self:
            return self['weight']
        return 1.0

    def get_attribute_descriptions(self):
        if 'attributes' in self:
            cols = set([])
            for _, attrs in self['attributes'].items():
                for attr in attrs:
                    cols.add(attr)
            return list(cols)
        return []

    def get_lb_region(self, value):
        """
        Return the lower bound for the region containing value.
        """
        if math.isnan(value):
            return None
        if 'discretization' in self:
            for r in self['discretization']:
                if r[0] <= value and value < r[1]:
                    return r[0]
        else:
            return self['domain'][0]

    def get_ub_region(self, value):
        """
        Return the upper bound for the region containing value.
        """
        if math.isnan(value):
            return None
        if 'discretization' in self:
            for r in self['discretization']:
                if r[0] <= value < r[1]:
                    return r[1]
        else:
            return self['domain'][1]

    def get_discretization_names(self):
        if self['dtype'] == 'float':
            return [ self['name'] + '_lb', self['name'] + '_ub' ]
        return [self['name']]

    def sample(self):
        if self['dtype'] == 'float':
            return random.uniform(self['domain'][0], self['domain'][1])
        else:
            return random.sample(self['domain'],1)[0]

    def __repr__(self):
        return self.__class__.__name__ + "()"

    def __str__(self):
        return self.__class__.__name__ + "(" + self['name'] + ":" + str(self['dtype']) + str(self['domain']) + ")"

class Condition(Factor):
    pass


class DesignElement(Factor):
    pass


class Experimental(Factor):
    pass

class Statistic(dict):
    def __repr__(self):
        return f"Statistic({self['name']}:{str(self['dtype'])})"

    def __str__(self):
        return "Statistic(" + self['name'] + ":" + str(self['dtype']) + ")"


class Record(dict):
    def __repr__(self):
        return "Record()"
    def __str__(self):
        return "Record(" + str(self['factors']) + ":" + str(self['statistics']) + ")"
    def to_dict(self):
        d = {}
        d.update(self['factors'])
        d.update(self['statistics'])
        return d


class ConditionSpace():
    def __init__(self, *args, **kwargs):
        if len(args) == 1:
            self.deserialize(args[0])
        else:
            self.factors = self._dict_to_factors(kwargs['factors'])
            if 'statistics' in kwargs:
                self.statistics = kwargs['statistics']
            self.data = self.initialize_data()

    def _dict_to_factors(self, factor_dict):
        factor_objects = {}
        for name, factor in factor_dict.items():
            if issubclass(type(factor), Factor):
                factor_objects[name] = factor
            else:
                factor_objects[name] = eval(factor['otype'])(**factor)
        return factor_objects


    def initialize_data(self) -> pd.DataFrame:
        pd_header = {}
        dtypes = {}

        # Setup condition columns
        for name, factor in self.factors.items():
            pd_header[name] = {}
            dtypes[name] = factor['dtype']

            if 'attributes' in factor:
                cols = set([])
                for value in factor['attributes']:
                    for attr in value:
                        cols.add(attr)
                for col in cols:
                    pd_header[col] = {}
                    ## FIXME assumes dtype of attributes are strings
                    dtypes[col] = str

        # Setup statistic columns
        if hasattr(self, 'statistics'):
            for name, statistic in self.statistics.items():
                pd_header[name] = {}
                dtypes[name] = statistic['dtype']

        # Setup Utility
        pd_header['utility'] = {}
        dtypes['utility'] = float

        d = pd.DataFrame(pd_header)
        d = d.astype(dtype=dtypes)

        return d

    def __repr__(self):
        return "ConditionSpace()"
    def __str__(self):
        return "ConditionSpace(factors=" + str([str(x) for x in self.factors]) + ")"

    def get_region_descriptions(self, use_values=False):
        """
        Return names for conditions using lb/ub for floats
        """
        descs = []
        for fname, factor in self.factors.items():
            if factor['dtype'] == 'float':
                descs.extend(factor.get_discretization_names())
                if use_values:
                    descs.append(fname)
            else:
                descs.append(fname)
            if 'attributes' in factor:
                descs.extend(factor.get_attribute_descriptions())
        return descs

    def serialize(self, filename):
        """
        Write factors as JSON and data as CSV
        """

        ## Cannot serialize utility objects as json
        for _, factor in self.factors.items():
            factor.del_utility_obj()

        with open(filename + '.json', 'w') as f:
            json.dump({ "factors" : self.factors, "statistics" : self.statistics}, f, sort_keys=True, indent=2, separators=(',', ': '))
        if hasattr(self, 'data'):
            self.data.to_csv(filename + '.csv', index=False)

        for _, factor in self.factors.items():
            factor.set_utility_obj()

        if not os.path.exists(filename):
            os.mkdir(filename)
        plot_data(*self.get_data(all_conditions=False), out_dir=filename)


    def deserialize(self, condition_file) -> None:
        """
        Read factors and data from ``condition_file``, a CSV file.
        Helper function to ``ConditionSpace.__init__``.
        """
        filename = ".".join(condition_file.split('.')[:-1])
        data_file = filename+'.csv'
        with open(condition_file, 'r') as f:
            cs = json.load(f)
            self.factors = { k:eval(v['otype'])(**v) for k,v in cs['factors'].items()}
            self.statistics = { k:Statistic(**v) for k,v in cs['statistics'].items()}
            if 'utility' in cs:
                self.utility = UtilityFunction.createUtilityFunction(utility=cs['utility'],
                                                                     factors=self.factors)

        dtypes = {name: factor['dtype'] for name, factor in self.factors.items()}
        if os.path.exists(data_file):
            self.data = pd.read_csv(filename+'.csv', dtype=dtypes, index_col=False)
        else:
            self.data = self.initialize_data()

    def set_prior(self, bins=10):
        """
        For each possible condition, set default value for each statistic
        """
        def discretize_domain(factor, bins=10):
            if factor['dtype'] == 'float':
                domain = factor['domain']
                if 'discretization' in factor:
                    d = factor['discretization']

                    discrete_domain = {
                        factor['name'] + "_lb" : [x[0] for x in d ],
                        factor['name'] + "_ub" : [x[1] for x in d ]
                    }
                else:
                    width = domain[1] - domain[0]
                    increment = width/bins
                    discrete_domain = {
                        factor['name'] + "_lb" : [domain[0] + (x * increment) for x in range(0,bins) ],
                        factor['name'] + "_ub" : [domain[0] + ((x+1)*increment) for x in range(0,bins) ]
                    }
            else:
                discrete_domain = { factor['name'] : factor['domain'] }
            return discrete_domain


        cp = pd.DataFrame()
        for name, factor in self.factors.items():
            if len(cp) == 0:
                cp = pd.DataFrame(discretize_domain(factor, bins=bins))
            else:
                cp.loc[:, 'key'] = 0
                fdf = pd.DataFrame(discretize_domain(factor, bins=bins))
                #l.info(fdf)
                fdf.loc[:, 'key'] = 0
                cp = cp.merge(fdf, how='left', on='key')

            if 'attributes' in factor:
                attr_df = pd.DataFrame()
                for value, attrs in factor['attributes'].items():
                    attributes = copy.deepcopy(attrs)
                    attributes[name] = value
                    attr_df = attr_df.append(attributes, ignore_index=True)
                cp = cp.merge(attr_df, how='left', on=name)

        l.debug("Setting prior with statistics: " + str(self.statistics))
        for name, statistic in self.statistics.items():
            sdf = pd.DataFrame({name : [statistic['default']]})
            sdf.loc[:,'key'] = 0
            cp.loc[:,'key'] = 0
            cp = cp.merge(sdf, on='key')
        cp = cp.drop(columns=['key'])
        #self.data = self.data.append(cp, ignore_index=True)
        self.data = cp
        if hasattr(self, 'utility'):
            ## Compute Utility Function
            self.data.loc[:, 'utility'] = self.data.apply(self.utility.value_of, axis=1)
        self.data.to_csv('dan.csv')

    def get_regions(self, columns):
        """
        Return all regions of condition space
        """
        l.debug("Getting Regions from: %s", str(self.data.columns))
        l.debug("For conditions: %s", str(columns))
        return self.data[columns]
        
    def decrement_data_cache(self, group):
        #l.debug("Decrement cache: " + str(group))
        record = { 'factors' : self.group_to_factors(group) }
        #l.debug("Record: " + str(record))
        matches = self.find_match(record)
        #l.debug("Matches: " + str(matches))
        if len(matches) > 0:
            #l.debug( self.data.ix[matches.index.tolist()[0], 'have_data'])
            num_points = self.data.at[matches.index.tolist()[0], 'have_data'] - 1
            self.data.at[matches.index.tolist()[0], 'have_data'] = num_points
            #l.debug( self.data.ix[matches.index.tolist()[0], 'have_data'])


    def group_to_factors(self, group):
        group_dict = {}
        groupd = {k:v for (k, v) in group}
        for fname in self.factors:
            group_dict[fname] = groupd[fname]
        return group_dict

    def update_data_cache(self, data_groups):
        """
        If drawing samples from cached data, record in condition
        space which regions have data.
        """

        self.data.loc[:, 'have_data'] = 0
        for group, group_data in data_groups.items():
            record = { 'factors' : self.group_to_factors(group) }
            matches = self.find_match(record)
            if len(matches) > 0:
                l.debug("Adding %d samples to region", len(group_data))
                num_points = self.data.at[matches.index.tolist()[0], 'have_data'] + len(group_data)
                self.data.at[matches.index.tolist()[0], 'have_data'] = num_points



    def get_factor_values(self, factor):
        return self.data[factor].unique()

    def marginalize(self, grouping, metric, using_data_cache=False, conditioned_factors=None):
        """
        """
        l.debug("Marginalizing: " + str(self.data) + " on " + str(grouping))
        l.debug("Conditioning: on " + str(conditioned_factors))
        discretized_grouping = []
        for k, v in grouping.items():
            if v['dtype'] == 'float':
                discretized_grouping.append(v['name'] + '_lb')
                discretized_grouping.append(v['name'] + '_ub')
            else:
                discretized_grouping.append(v['name'])
        #l.debug("Grouping: " + str(discretized_grouping))
        if using_data_cache:
            # Restrict marginal to data we have
            if conditioned_factors is not None:
                ## Condition condition_space< upon conditioned_factors
                marginal = self.data.merge(conditioned_factors).loc[self.data['have_data'] > 0].groupby(discretized_grouping).agg({metric: [np.sum]})
            else:
                marginal = self.data.loc[self.data['have_data'] > 0].groupby(discretized_grouping).agg({metric: [np.sum]})
        else:
            if conditioned_factors is not None:
                ## Condition condition_space upon conditioned_factors
                marginal = self.data.merge(conditioned_factors).groupby(discretized_grouping).agg({metric: [np.sum]})
            else:
                marginal = self.data.groupby(discretized_grouping).agg({metric: [np.sum]})
        marginal = marginal.fillna(1.0)
        marginal = marginal.apply(lambda x : x + random.random()/1000.0 , axis = 0)

        return marginal


    def get_statistics(self):
        if hasattr(self, 'statistics'):
            return self.statistics.keys()
        return []

    def union(cs1, cs2):
        """
        Union the domains of two condition spaces.
        TODO Figure out how to union other aspects.
        """
        pass
        
    def validate_record(self, record):
        for factor, value in record['factors'].items():
            if factor not in self.factors:
                raise Exception("Unknown factor: " + str(factor))
            elif self.factors[factor]['dtype'] == "str":
                if value is not None and value not in self.factors[factor]['domain']:
                    raise Exception("Factor: " + str(factor) + " value: " +  str(value) + " is not in the domain")
            elif self.factors[factor]['dtype'] == "float":
                if value is not None and value < self.factors[factor]['domain'][0] or value is not None and value > self.factors[factor]['domain'][1]:
                    raise Exception("Factor: \"" + str(factor) + "\" value: " +  str(value) + " is not in the domain")

    def _match_query(self, record) -> str:
        q = ""
        for f, fv in record['factors'].items():
            if self.factors[f]['dtype'] == 'float':
                lb = f + '_lb'
                ub = f + '_ub'
                quote = ""
                q = q + ' (' + lb + ' <= ' + quote +  str(fv) + quote + ') & (' + ub + ' > ' + quote +  str(fv) + quote + ') &'
            elif self.factors[f]['dtype'] == 'str':
                quote = "\""
                q = q + ' (' + f + ' == ' + quote +  str(fv) + quote + ') & '
        q = q + ' True'
        return q


    def find_match(self, record) -> pd.DataFrame:
        q = self._match_query(record)
        l.debug("Query: " + q)
        matches = self.data.query(q)
        l.debug("Matches:" + str(matches))
        return matches

    def merge_stats(self, row, record):
        """
        For every column in row that corresponds to a statistic,
        compute the mean with the record.


        Frequentist model needs the following statistics:
        - Mean(Correctness_n): Mean correctness of samples (\bar{x}_n)
        - Standard Error: SE of mean correctness of samples
        - Count: Number of samples (n)

        This model computes the frequentist statistics incrementally using Welford's algorithm.

        \bar{x}_n = \bar{x}_{n-1} + ((x_n - \bar{x}_{n-1})/n)

        M_{2,n} = M_{2,n-1} + (x_n - \bar{x}_{n-1})(x_n - \bar{x}_n)

        s^2_n = M_{2,n}/n

        SE_n = s^2_n/\sqrt(n)

        """
#            if row is None:
#                row = record.to_dict()

        if row is None:
            row = record.to_dict()
            row.loc[:,Conditions.COUNT] = 0

        l.debug("Getting stats from: " + str(row))
        if Conditions.CORRECTNESS in self.statistics and \
          Conditions.CORRECTNESS in record['statistics'] and \
          Conditions.CORRECTNESS in row.columns:

            #assert(not pd.isnull(row[Conditions.CORRECTNESS].unique()[0]) or \
            #       row[Conditions.COUNT].unique()[0] > 0)
            # if there is no data for this row...
            if row[Conditions.COUNT].unique()[0] == 0:
            # could this be the following? it might be faster? [2019/10/21:rpg]
            # if row.at[0, Conditions.COUNT] == 0:
                x_n_1 = None
                n = 1
                m_2_n_1 = None

            else:
                x_n_1 = row[Conditions.CORRECTNESS].unique()[0]
                n = row[Conditions.COUNT].unique()[0] + 1
                m_2_n_1 = row[Conditions.SUM_SQ_DIFF].unique()[0]

            x = record['statistics'][Conditions.CORRECTNESS]

            if x_n_1 is not None:
                x_n = x_n_1 + ((x - x_n_1)/n)
                m_2_n = m_2_n_1 + ((x - x_n_1)*(x - x_n))
                s_2_n = m_2_n / n
            else:
                x_n = x
                m_2_n = 0
                s_2_n = MAX_ERROR

            #print("ROW: " + str(row))
            #print("Mean: " + str(x_n_1) + " " + str(x_n))
            #print("Var: " + str(s_2_n))
            #print("SE: " + str(np.sqrt(s_2_n)/np.sqrt(n)))
            #print("N: " + str(n))

            row.loc[:,Conditions.CORRECTNESS] = x_n
            row.loc[:,Conditions.SUM_SQ_DIFF] = m_2_n
            row.loc[:,Conditions.STANDARD_DEV] = s_2_n
            row.loc[:,Conditions.STANDARD_ERROR] = (np.sqrt(s_2_n)/np.sqrt(n))
            assert not np.isnan(np.sqrt(n))

            if x_n is None:
                l.debug(row.to_string())
                l.debug(record)
                raise Exception("Mean became zero")
        else:
            raise TypeError("Some record that does not have correctness in it.")

        if Conditions.ENTROPY in self.statistics and record['statistics'][Conditions.ENTROPY] is not None:
            row.loc[:, Conditions.ENTROPY] = record['statistics'][Conditions.ENTROPY]
        if Conditions.BAYES_CORRECTNESS in self.statistics and record['statistics'][Conditions.BAYES_CORRECTNESS] is not None:
            row.loc[:, Conditions.BAYES_CORRECTNESS] = record['statistics'][Conditions.BAYES_CORRECTNESS]            
        if Conditions.SCORE in self.statistics and record['statistics'][Conditions.SCORE] is not None:
            row.loc[:, Conditions.SCORE] = record['statistics'][Conditions.SCORE]
            row.loc[:, Conditions.RANK_ERROR] = record['statistics'][Conditions.RANK_ERROR]

        if Conditions.COUNT in record['statistics'] and \
           record['statistics'][Conditions.COUNT] is not None:
            row.loc[:,Conditions.COUNT] = row[Conditions.COUNT].unique()[0] + \
                                          record['statistics'][Conditions.COUNT]

        if Conditions.ITERATION in record['statistics'] and \
          record['statistics'][Conditions.ITERATION] is not None:
          row.loc[:, Conditions.ITERATION] = record['statistics'][Conditions.ITERATION]
            
                                          
        l.debug(row.to_string())

        ## if 'count' in row.columns:
        ##     rw_count = row['count'].unique()[0]
        ##     rc_count = record['statistics']['count']
        ##     for stat in record['statistics'].keys():
        ##         row[stat] = ((row[stat] * rw_count) + (record['statistics'][stat] * rc_count)) / (rw_count + rc_count)
        ##     row['count'] = rw_count + rc_count
        ## else:
        ##     raise Exception("Cannot merge statistics via mean if don't know the 'count' of data points")
        return row

    def add_record(self, record):
        try:
            #print("Validating Record ...")
            #print(self.data)
            l.debug("Adding: " + str(record.to_dict()))
            #print("Adding: " + str(record.to_dict()))
            self.validate_record(record)

            match = self.find_match(record)
            if len(match) > 1:
                #print(record)
                #print(match)
                l.debug("Match: " + str(match))
                raise Exception("Record matches more than one row")
            elif len(match) == 1:
                l.debug("Found match: " + str(match))
                index=match.index.tolist()[0]
                self.data.loc[index:index, :] = self.merge_stats(match, record)
            else:
                #print(record)
                #print("No match: " + str(match))
                #self.data = self.data.append(merge_stats(None), ignore_index=True)
                raise Exception("Do not have existing region for sample")

        except Exception as e:
            raise Exception("Could not add record to condition space: " + str(e))

    def compute_value(self, distribution = 'count'):
        self.data.loc[:, 'value'] = self.data[distribution]/self.data[distribution].sum() *self.data['utility']


    def get_data(self,
             all_conditions=False,
             stats = ['standard_dev', 'standard_error', 'correctness',
                      'count', 'have_data', 'entropy', 'rank_error', 'utility', 'score',
                      'value', 'iteration'],
             norms = {
                 'standard_dev' : 'log',
                 'standard_error' : 'log',
                 'correctness' : 'lin',
                 'count' : 'lin',
                 'have_data' : 'log2',
                 'entropy' : 'lin',
                 'rank_error': 'log',
                 'score': 'log',
                 'utility' : 'lin',
                 'value' : 'lin',
                 'iteration' : 'lin'
                 }
            ):

        l.debug("Attempting to extract stats: " + str(stats))
        # Plot conditions on rows
        # Plot designs on columns
        rows = []
        row_factors = []
        columns = []
        for _, factor in self.factors.items():
            if factor['otype'] == 'Condition':
                rows.extend(factor.get_discretization_names())
                row_factors.append(factor)
            elif factor['otype'] == 'DesignElement':
                columns.extend(factor.get_discretization_names())
            else:
                raise Exception("Cannot plot factor " + factor['name'] +
                                "of type: " + factor['otype'])

        l.debug("Rows: " + str(rows))
        l.debug("Cols: " + str(columns))

        row_groups = self.data.groupby(rows)
        ytics=[]
        titles = { x : x for x in stats}
        matrices = { s : [] for s in stats}              
        
        for row_name, row_group in row_groups:
            #l.debug("Row: " + str(row_name))
            rows = { s : [] for s in stats}
            column_groups = row_group.groupby(columns)
            xtics=[]
            for column_name, column_group in column_groups:

                column_group_dict = column_group.iloc[0,:].to_dict()
                for stat in stats:
                    if stat in column_group_dict:
                        rows[stat].append(column_group_dict[stat])
                xtics.append(column_name)
            if all_conditions or len([x for x in rows['count'] if x > 0]) > 0:
                #l.debug("Adding stats: " + str(stats))
                for stat in stats:
                    if len(rows[stat]) > 0:
                        matrices[stat].append([x if x is not None else np.nan for x in rows[stat] ] )
                ytics.append(convert_row_name(row_name, row_factors))
        #l.debug("xtics: " + str(xtics))
        #l.debug("ytics: " + str(ytics))
        return (matrices, titles, norms, xtics, ytics)


def main():
    od = Condition(name=Conditions.OD,
                   domain=[0, 1],
                  dtype="float")
    media = Condition(name=Conditions.MEDIA,
                      domain=[
                          "SC Media",
                          "SC Slow",
                          "SC High Osm",
                          "YPAD"
                          ],
                      dtype="str")
    temperature = Condition(name=Conditions.TEMPERATURE,
                            domain = [0,100],
                            dtype="float")
    strain = DesignElement(name=Conditions.STRAIN,
                           domain=[ 'UWBF_' + g + '_' + i
                                for i in ['00', '01', '10', '11']
                                for g in ['OR', 'AND', 'NOR', 'NAND', 'XOR', 'XNOR']
                               ],
                           dtype="str")
    gate = DesignElement(name=Conditions.GATE,
                         domain = ['OR', 'AND', 'NOR', 'NAND', 'XOR', 'XNOR'],
                         dtype="str")
    input = DesignElement(name=Conditions.INPUT,
                          domain = ['00', '01', '10', '11'],

                          dtype="str")

    factors = [od, media, temperature, strain, gate, input]
    factors = { x['name'] : x for x in factors }

    s = Statistic(name=Conditions.SCORE,
                  dtype=float)
    statistics = [s]
    statistics = { x['name'] : x for x in statistics }

    cs = ConditionSpace(factors=factors, statistics=statistics)


    #print(d.dtypes)

    # Insert a few records
    r = Record(
        factors={
            Conditions.OD : 0.1,
            Conditions.MEDIA : "SC Media",
            Conditions.TEMPERATURE : 30,
            Conditions.STRAIN : "UWBF_NOR_11",
            Conditions.GATE : "NOR",
            Conditions.INPUT : "11"
        },
        statistics={
            Conditions.SCORE : 1.0
            })
    #d = d.append(r.to_dict(), ignore_index=True)

    r1 = Record(
        factors={
            Conditions.OD : 0.001,
            Conditions.MEDIA : "SC Slow",
            Conditions.TEMPERATURE : 37,
            Conditions.STRAIN : "UWBF_NOR_11",
            Conditions.GATE : "NOR",
            Conditions.INPUT : "11"
        },
        statistics={
            Conditions.SCORE : 2.0
            })
    #d = d.append(r1.to_dict(), ignore_index=True)



    cs.add_record(r)
    cs.add_record(r1)

    print(cs)
    print(cs.data)
    cs.serialize('my_cs')
    csd = ConditionSpace(filename = 'my_cs')
    print(csd)
    print(cs.data)


if __name__ == '__main__':
    main()
