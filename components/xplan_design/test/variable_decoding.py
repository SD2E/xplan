import pandas as pd
import time

class combine_test():
    def __init__(self):
        self.dur_merge = 0
        self.dur_combine = 0

    def do_merge(self, agg, row, on):
        start = time.perf_counter()

        do_append = True
        existing_row = None
        if len(agg) != 0:
            agg = agg.set_index(on)
            index =tuple(row[on].T.values)
            existing_row = agg.loc[index]
            if len(existing_row) != 0:
                do_append = False
#        mer = agg[on].merge(row[on])
        if do_append:
            agg = agg.append(row, ignore_index=True)
        else:
            existing_row = existing_row.join(row.set_index(on))
            agg.loc[index] = existing_row.loc[index]
            #agg = agg.drop(index)
            #agg = agg.append(existing_row, ignore_index=True)
            #agg = agg.merge(row, on=on)
        agg.reset_index()
        end = time.perf_counter()
        self.dur_merge += end - start
        return agg

    def do_combine(self, agg, row, on):
        start = time.perf_counter()
        res = agg.set_index(on).combine_first(row.set_index(on)).reset_index()
        end = time.perf_counter()
        self.dur_combine += end - start
        return res

def test_variable_decode():
    agg1 = pd.DataFrame({"sample" : []})
    agg2 = pd.DataFrame({"sample" : []})

    on = ["sample"]

    c = combine_test()

    dfs = [
        pd.DataFrame({"sample" : ["sample1"], "factor1" : ["value1"]}),
        pd.DataFrame({"sample" : ["sample1"], "factor2" : ["value2"]}),
        pd.DataFrame({"sample": ["sample2"], "factor1": ["value1"]}),
        pd.DataFrame({"sample": ["sample2"], "factor2": ["value2"]})
    ]

    for df in dfs:
        agg1 = c.do_combine(agg1, df, on)


    for df in dfs:
        agg2 = c.do_merge(agg2, df, on)


    print(f"Time to Combine: {c.dur_combine}")
    print(f"Time to Merge: {c.dur_merge}")
    pass

