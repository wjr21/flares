#!/cosma/home/dp004/dc-rope1/.conda/envs/flares-env/bin/python
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import astropy.units as u
from matplotlib.colors import LogNorm
import matplotlib.gridspec as gridspec
import eagle_IO.eagle_IO as E
import seaborn as sns
import pickle
import itertools
matplotlib.use('Agg')

sns.set_style('whitegrid')


regions = []
for reg in range(0, 40):

    if reg < 10:
        regions.append('000' + str(reg))
    else:
        regions.append('00' + str(reg))

snaps = ['003_z012p000', '004_z011p000', '005_z010p000',
         '006_z009p000', '007_z008p000', '008_z007p000',
         '009_z006p000', '010_z005p000', '011_z004p770']
axlims_x = []
axlims_y = []

# Define comoving softening length in kpc
csoft = 0.001802390/0.677*1e3

hmr_star_dict = {}
hmr_gas_dict = {}
subgrps_dict = {}
ms = {}
for snap in snaps:

    hmr_star_dict[snap] = {}
    subgrps_dict[snap] = {}
    hmr_gas_dict[snap] = {}
    ms[snap] = {}

for reg in regions:

    for snap in snaps:

        print(reg, snap)

        path = '/cosma7/data/dp004/dc-love2/data/G-EAGLE/geagle_' + reg + '/data/'
        try:
            subgrps_dict[snap][reg] = E.read_array('SUBFIND', path, snap, 'Subhalo/SubGroupNumber', noH=True,
                                                          numThreads=8)
            hmrs = E.read_array('SUBFIND', path, snap, 'Subhalo/HalfMassRad', noH=True,
                                                          numThreads=8) * 1e3
            hmr_star_dict[snap][reg] = hmrs[:, 4]
            hmr_gas_dict[snap][reg] = hmrs[:, 0]
            ms[snap][reg] = E.read_array('SUBFIND', path, snap, 'Subhalo/ApertureMeasurements/Mass/030kpc',
                                                 noH=True, numThreads=8)[:, 4] * 10**10
        except OSError:
            continue
        except ValueError:
            continue

norm = LogNorm(vmin=10**9, vmax=10**11.25)

# Set up plot
fig = plt.figure(figsize=(18, 10))
gs = gridspec.GridSpec(3, 6)
gs.update(wspace=0.0, hspace=0.0)
ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[0, 1])
ax3 = fig.add_subplot(gs[0, 2])
ax4 = fig.add_subplot(gs[1, 0])
ax5 = fig.add_subplot(gs[1, 1])
ax6 = fig.add_subplot(gs[1, 2])
ax7 = fig.add_subplot(gs[2, 0])
ax8 = fig.add_subplot(gs[2, 1])
ax9 = fig.add_subplot(gs[2, 2])

for ax, snap, (i, j) in zip([ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9], snaps,
                            [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)]):

    z_str = snap.split('z')[1].split('p')
    z = float(z_str[0] + '.' + z_str[1])

    hmr_gas = np.concatenate(list(hmr_gas_dict[snap].values()))
    hmr_star_plt = np.concatenate(list(hmr_star_dict[snap].values()))
    m = np.concatenate(list(ms[snap].values()))
    sgrps = np.concatenate(list(subgrps_dict[snap].values()))

    okinds = np.logical_and(m > 1e9, np.logical_and(hmr_star_plt > 0, np.logical_and(hmr_gas > 0, sgrps > 0)))
    hmr_star_plt = hmr_star_plt[okinds]
    hmr_gas_plt = hmr_gas[okinds]
    m = m[okinds]

    try:
        im = ax.hexbin(hmr_star_plt / (csoft / (1 + z)), hmr_gas_plt / (csoft / (1 + z)), C=m, gridsize=100,
                       mincnt=1, hmr_gascale='log', yscale='log', norm=norm, linewidths=0.2, cmap='viridis',
                       reduce_C_function=np.mean)
    except ValueError:
        continue

    ax.text(0.8, 0.9, f'$z={z}$', bbox=dict(bohmr_gastyle="round,pad=0.3", fc='w', ec="k", lw=1, alpha=0.8),
            transform=ax.transAxes, horizontalalignment='right', fontsize=8)

    axlims_x.extend(ax.get_xlim())
    axlims_y.extend(ax.get_ylim())

    # Label axes
    if i == 2:
        ax.set_xlabel('$R_{1/2,*}/\epsilon$')
    if j == 0:
        ax.set_ylabel('$R_{1/2,gas}/\epsilon$')

for ax in [ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9]:

    ax.set_xlim(np.min(axlims_x), np.max(axlims_x))
    ax.set_ylim(np.min(axlims_y), np.max(axlims_y))

    ax.plot((np.min(axlims_x), np.max(axlims_x)), (np.min(axlims_y), np.max(axlims_y)),
            linestyle='--', color='k', zorder=0)

# Remove axis labels
ax1.tick_params(axis='x', top=False, bottom=False, labeltop=False, labelbottom=False)
ax2.tick_params(axis='both', left=False, top=False, right=False, bottom=False, labelleft=False, labeltop=False,
                labelright=False, labelbottom=False)
ax3.tick_params(axis='both', left=False, top=False, right=False, bottom=False, labelleft=False, labeltop=False,
                labelright=False, labelbottom=False)
ax4.tick_params(axis='x', top=False, bottom=False, labeltop=False, labelbottom=False)
ax5.tick_params(axis='both', left=False, top=False, right=False, bottom=False, labelleft=False, labeltop=False,
                labelright=False, labelbottom=False)
ax6.tick_params(axis='both', left=False, top=False, right=False, bottom=False, labelleft=False, labeltop=False,
                labelright=False, labelbottom=False)
ax8.tick_params(axis='y', left=False, right=False, labelleft=False, labelright=False)
ax9.tick_params(axis='y', left=False, right=False, labelleft=False, labelright=False)

fig.colorbar(im)

fig.savefig('plots/HalfMassR_StellarvsGas_all_snaps_colormass_sat.png',
            bbox_inches='tight')

plt.close(fig)

# Set up plot
fig = plt.figure(figsize=(18, 10))
gs = gridspec.GridSpec(3, 6)
gs.update(wspace=0.0, hspace=0.0)
ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[0, 1])
ax3 = fig.add_subplot(gs[0, 2])
ax4 = fig.add_subplot(gs[1, 0])
ax5 = fig.add_subplot(gs[1, 1])
ax6 = fig.add_subplot(gs[1, 2])
ax7 = fig.add_subplot(gs[2, 0])
ax8 = fig.add_subplot(gs[2, 1])
ax9 = fig.add_subplot(gs[2, 2])

for ax, snap, (i, j) in zip([ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9], snaps,
                            [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)]):

    z_str = snap.split('z')[1].split('p')
    z = float(z_str[0] + '.' + z_str[1])

    hmr_gas = np.concatenate(list(hmr_gas_dict[snap].values()))
    hmr_star_plt = np.concatenate(list(hmr_star_dict[snap].values()))
    m = np.concatenate(list(ms[snap].values()))
    sgrps = np.concatenate(list(subgrps_dict[snap].values()))

    okinds = np.logical_and(m > 1e9, np.logical_and(hmr_star_plt > 0, np.logical_and(hmr_gas > 0, sgrps == 0)))
    hmr_star_plt = hmr_star_plt[okinds]
    hmr_gas_plt = hmr_gas[okinds]
    m = m[okinds]

    try:
        im = ax.hexbin(hmr_star_plt / (csoft / (1 + z)), hmr_gas_plt / (csoft / (1 + z)), C=m, gridsize=100,
                       mincnt=1, hmr_gascale='log', yscale='log', norm=norm, linewidths=0.2, cmap='viridis',
                       reduce_C_function=np.mean)
    except ValueError:
        continue

    ax.text(0.8, 0.9, f'$z={z}$', bbox=dict(bohmr_gastyle="round,pad=0.3", fc='w', ec="k", lw=1, alpha=0.8),
            transform=ax.transAxes, horizontalalignment='right', fontsize=8)

    axlims_x.extend(ax.get_xlim())
    axlims_y.extend(ax.get_ylim())

    # Label axes
    if i == 2:
        ax.set_xlabel('$R_{1/2,*}/\epsilon$')
    if j == 0:
        ax.set_ylabel('$R_{1/2,gas}/\epsilon$')

for ax in [ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9]:

    ax.set_xlim(np.min(axlims_x), np.max(axlims_x))
    ax.set_ylim(np.min(axlims_y), np.max(axlims_y))

    ax.plot((np.min(axlims_x), np.max(axlims_x)), (np.min(axlims_y), np.max(axlims_y)),
            linestyle='--', color='k', zorder=0)

# Remove axis labels
ax1.tick_params(axis='x', top=False, bottom=False, labeltop=False, labelbottom=False)
ax2.tick_params(axis='both', left=False, top=False, right=False, bottom=False, labelleft=False, labeltop=False,
                labelright=False, labelbottom=False)
ax3.tick_params(axis='both', left=False, top=False, right=False, bottom=False, labelleft=False, labeltop=False,
                labelright=False, labelbottom=False)
ax4.tick_params(axis='x', top=False, bottom=False, labeltop=False, labelbottom=False)
ax5.tick_params(axis='both', left=False, top=False, right=False, bottom=False, labelleft=False, labeltop=False,
                labelright=False, labelbottom=False)
ax6.tick_params(axis='both', left=False, top=False, right=False, bottom=False, labelleft=False, labeltop=False,
                labelright=False, labelbottom=False)
ax8.tick_params(axis='y', left=False, right=False, labelleft=False, labelright=False)
ax9.tick_params(axis='y', left=False, right=False, labelleft=False, labelright=False)

fig.colorbar(im)

fig.savefig('plots/HalfMassR_StellarvsGas_all_snaps_colormass_cent.png',
            bbox_inches='tight')

plt.close(fig)
