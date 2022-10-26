import os
import pandas as pd
import numpy as np
from collections import deque

import logging
logger =  logging.getLogger(__file__)
logger.setLevel(logging.INFO)

logging.getLogger('matplotlib').setLevel(logging.INFO)

#from xplan_models.model import FrequentistModel
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm
from matplotlib.collections import PatchCollection
from matplotlib.patches import Circle

import seaborn as sns



def convert_row_name(row_name, row_factors):
    #logger.debug("row_name: " + str(row_name))
    #logger.debug("row_factors: " + str(row_factors))
    row_label=""
    row = deque(row_name)
    for factor in row_factors:
        cols = factor.get_discretization_names()
        factor_label = factor['name'] + ": [" 
        for col in cols:
            factor_label = factor_label + str(row.popleft()) + " " 
        factor_label = factor_label + "]"
        row_label = row_label + factor_label
    return row_label

#def get_data_from_model(model_id='dan_cs', model_dir = '..', all_conditions=False):
#    m = FrequentistModel(model_dir = model_dir, model_id = model_id)
#    cs = m['condition_space'].data
#    return get_data(cs, all_conditions=all_conditions)
    


def plot_data(matrices, titles, norms, xtics, ytics, out_dir='.', samples=None):
    norm = {'log' : LogNorm(vmin=0.0001, vmax=1),
            'log1' : LogNorm(vmin=0.01, vmax=1),
            'log2' : LogNorm(vmin=1, vmax=100),
            'lin' : None
           }
    logger.debug("Plotting Condition Space ...")

    #ytics = [convert_row_name(y) for y in ytics]

    circles = []
    if 'iteration' in titles and len(matrices['iteration']) > 0:
        ## Overlay the max iteration on top of the other plots
        iteration = np.nanmax([np.nanmax(x) if len(x) > 0 else np.nan for x in matrices['iteration']])
        if not np.isnan(iteration):
            matrices['iteration'] = [[ 1.0  if not np.isnan(y) and int(y) == iteration else 0.0 for y in x ] for x in matrices['iteration']]
            logger.debug(matrices['iteration'])
            for row in range(0, len(matrices['iteration'])):
                for col in range(0, len(matrices['iteration'][row])):
                    if matrices['iteration'][row][col] == 1.0:
                        circles.append(Circle([col, row], radius=0.25, color='red'))

    #fig, ax = plt.subplots(dpi=300)
    for stat, matrix in matrices.items():
        logger.debug("len(" + stat + ") = " + str(len(matrix)))
        if len(matrix) > 0:
            #matrix = [np.ma.array (x, mask=np.isnan(x)) for x in matrix]
            #logger.debug(matrix)
            fig, ax = plt.subplots(dpi=200)

             
            e = ax.imshow(matrix, norm=norm[norms[stat]]) 
#            e = plt.matshow(matrix,norm=norm[norms[stat]])
            cbar = ax.figure.colorbar(e, ax=ax)
            
            plt.gca().set_xticklabels(xtics, fontdict={'fontsize' : 4})
            plt.gca().set_yticklabels(ytics, fontdict={'fontsize' : 4})
            plt.gca().set_yticks(range(0, len(ytics)))
            plt.gca().set_xticks(range(0, len(xtics)))
            plt.gca().set_ylim(len(matrix)-0.5, -0.5)
            plt.gca().tick_params(axis='x', labelrotation=90.0)
            plt.title(titles[stat], pad=125)
            #plt.colorbar(e)
            #plt.figure(figsize=(80,40))
            #plt.draw()

            ax.add_collection(PatchCollection(circles, match_original=True))

            fname = os.path.join(out_dir, stat + '.png')
            fname_dat = os.path.join(out_dir, stat + '.dat')
            with open(fname_dat, 'w') as f:
                f.write(str(matrix))
            logger.debug("Saving Figure: " + fname)
            plt.savefig(fname, dpi=200)
            plt.close()
