#!/cosma/home/dp004/dc-rope1/.conda/envs/flares-env/bin/python
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.colors import LogNorm
import eagle_IO as E
import seaborn as sns
import pandas as pd
matplotlib.use('Agg')

sns.set_style('whitegrid')

regions = []
for reg in range(0, 40):

    if reg < 10:
        regions.append('000' + str(reg))
    else:
        regions.append('00' + str(reg))

snap = '010_z005p000'

submass_dict = {}
starmass_dict = {}
for reg in regions:

    print(reg)

    path = '/cosma7/data/dp004/dc-love2/data/G-EAGLE/geagle_' + reg + '/data/'

    submass_dict[reg] = E.read_array('SUBFIND', path, snap, 'Subhalo/Mass', noH=True, numThreads=8)
    starmass_dict[reg] = E.read_array('SUBFIND', path, snap,
                                      'Subhalo/ApertureMeasurements/Mass/030kpc', noH=True, numThreads=8)

submass = np.concatenate(list(submass_dict.values())) * 10**10
starmass = np.concatenate(list(starmass_dict.values())) * 10**10

def hexbin(x, y, max_series=None, min_series=None, **kwargs):
    ax = plt.gca()
    xmin, xmax = min_series[x.name], max_series[x.name]
    ymin, ymax = min_series[y.name], max_series[y.name]
    plt.hexbin(x, y, gridsize=100, mincnt=1, cmap="viridis", norm=LogNorm(1, 10**4.5), linewidths=0.2,
               extent=[xmin, xmax, ymin, ymax], **kwargs)

# Define pandas table
df = pd.DataFrame(np.vstack((np.log10(submass + 1), np.log10(starmass[:, 0] + 1), np.log10(starmass[:, 1] + 1),
                             np.log10(starmass[:, 4] + 1), np.log10(starmass[:, 5] + 1))).T,
                  columns=[r'$\log_{10}(M_{\mathrm{tot}}/M_\odot + 1)$', r'$\log_{10}(M_{\mathrm{gas}}/M_\odot + 1)$',
                           r'$\log_{10}(M_{\mathrm{DM}}/M_\odot + 1)$',
                           r'$\log_{10}(M_{*}/M_\odot + 1)$', r'$\log_{10}(M_{\mathrm{BH}}/M_\odot + 1)$'])

# Plot prior
g = sns.PairGrid(data=df, size=2.5, diag_sharey=False)
g.map_diag(plt.hist, color='Green', alpha=0.9, bins=50)
g.map_lower(hexbin, alpha=0.8, min_series=df.min(), max_series=df.max())

for i in range(5):
    for j in range(5):
        if j <= i:
            continue
        g.axes[i, j].set_axis_off()

# Save figure
plt.savefig('plots/mass_corner_plot_' + snap + '.png', dpi=300, bbox_inches='tight')
