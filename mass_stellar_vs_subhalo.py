#!/cosma/home/dp004/dc-rope1/.conda/envs/flares-env/bin/python
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.colors import LogNorm
import eagle_IO as E
import seaborn as sns
matplotlib.use('Agg')

sns.set_style('whitegrid')

regions = []
for reg in range(0, 1):

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

    starmass_dict[reg] = E.read_array('SUBFIND', path, snap, 'Subhalo/ApertureMeasurements/Mass/010kpc', noH=True)[:, 4]
    submass_dict[reg] = E.read_array('SUBFIND', path, snap, 'Subhalo/Mass', noH=True)

submass = np.concatenate(list(submass_dict.values())) * 10**10
starmass = np.concatenate(list(starmass_dict.values())) * 10**10

fig = plt.figure()
ax = fig.add_subplot(111)

# submass = submass[starmass > 0]
# starmass = starmass[starmass > 0]
# starmass = starmass[submass > 0]
# submass = submass[submass > 0]

cbar = ax.hexbin(submass+1, starmass+1, gridsize=100, mincnt=1, xscale='log', norm=LogNorm(),
                 yscale='log', linewidths=0.2, cmap='viridis')

ax.plot(np.linspace(submass.min(), submass.max(), 100), np.linspace(submass.min(), submass.max(), 100), linestyle='--')

ax.set_xlabel('$M_{\mathrm{sub}}/M_\odot+1$')
ax.set_ylabel('$M_{*}/M_\odot+1$')

cax = fig.colorbar(cbar, ax=ax)
cax.ax.set_ylabel(r'$N$')

fig.savefig('plots/starvssubhalo_mass_' + snap + '.png', bbox_inches='tight')

plt.close(fig)

