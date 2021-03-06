#!/cosma/home/dp004/dc-rope1/.conda/envs/flares-env/bin/python
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.gridspec as gridspec
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy.spatial import cKDTree
import astropy.units as u
import astropy.constants as cons
from astropy.cosmology import Planck13 as cosmo
from matplotlib.colors import LogNorm
import eagle_IO.eagle_IO as E
import seaborn as sns
import h5py
import os
from unyt import mh, cm, Gyr, g, Msun, Mpc
matplotlib.use('Agg')

sns.set_style('whitegrid')


regions = []
for reg in range(0, 40):

    if reg < 10:
        regions.append('0' + str(reg))
    else:
        regions.append(str(reg))

snaps = ['000_z015p000', '001_z014p000', '002_z013p000', '003_z012p000', '004_z011p000', '005_z010p000',
         '006_z009p000', '007_z008p000', '008_z007p000', '009_z006p000', '010_z005p000', '011_z004p770']

subgrps = []
dists = []
shmrs = []
ghmrs = []

for reg in regions:

    for snap in snaps:

        print(reg, snap)

        path = '/cosma/home/dp004/dc-rope1/FLARES/FLARES-1/G-EAGLE_' + reg + '/data'

        try:
            subfind_grp_ids = E.read_array('SUBFIND', path, snap, 'Subhalo/GroupNumber', numThreads=8)
            subfind_subgrp_ids = E.read_array('SUBFIND', path, snap, 'Subhalo/SubGroupNumber', numThreads=8)
            gal_hmrs = E.read_array('SUBFIND', path, snap, 'Subhalo/HalfMassRad', numThreads=8,
                                    noH=True, physicalUnits=True) * 1e3
            coms = E.read_array('SUBFIND', path, snap, 'Subhalo/CentreOfMass', numThreads=8,
                                noH=True, physicalUnits=True) * 1e3
            grp_coms = E.read_array('FOF', path, snap, 'FOF/CentreOfMass', numThreads=8,
                                    noH=True, physicalUnits=True) * 1e3
            ms = E.read_array('SUBFIND', path, snap, 'Subhalo/ApertureMeasurements/Mass/030kpc',
                              noH=True, numThreads=8) * 10**10
        except ValueError:
            continue
        except KeyError:
            continue
        except OSError:
            continue

        tree = cKDTree(grp_coms)

        for (ind, grp), subgrp in zip(enumerate(subfind_grp_ids), subfind_subgrp_ids):

            if ms[ind, 4] < 1e9 or ms[ind, 1] == 0 or ms[ind, 0] == 0:
                continue

            com = coms[ind, :]

            d, i = tree.query(com, k=1)

            subgrps.append(subgrp)
            dists.append(d)
            shmrs.append(gal_hmrs[ind, 4])
            ghmrs.append(gal_hmrs[ind, 1])


fig = plt.figure(figsize=(8, 6))
gs = gridspec.GridSpec(1, 2)
gs.update(wspace=0.0, hspace=0.0)
ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[0, 1])

im1 = ax1.hexbin(shmrs, ghmrs, C=np.array(np.array(subgrps) == 0, dtype=int), gridsize=100, mincnt=1, cmap="coolwarm",
                 vmin=0, vmax=1, linewidths=0.2, reduce_C_function=np.mean, xscale='log', yscale='log')
im2 = ax2.hexbin(shmrs, ghmrs, C=dists, gridsize=100, mincnt=1, cmap="plasma", linewidths=0.2, norm=LogNorm(),
                 reduce_C_function=np.median, xscale='log', yscale='log')

ax1.set_xlabel('$R_{1/2,*}/ [\mathrm{pkpc}]$')
ax2.set_xlabel('$R_{1/2,*}/ [\mathrm{pkpc}]$')
ax1.set_ylabel('$R_{1/2,Gas}/ [\mathrm{pkpc}]$')

divider = make_axes_locatable(ax1)
cax = divider.append_axes('top', size='5%', pad=0.05)
cbar1 = fig.colorbar(im1, cax=cax, orientation='horizontal')
divider = make_axes_locatable(ax2)
cax = divider.append_axes('top', size='5%', pad=0.05)
cbar2 = fig.colorbar(im2, cax=cax, orientation='horizontal')
cbar2.set_label('$\Delta D_{\mathrm{Group}-\mathrm{Galaxy}} /$ [pkpc]')
cbar1.ax.xaxis.set_ticks_position('top')
cbar1.ax.xaxis.set_label_position('top')
cbar2.ax.xaxis.set_ticks_position('top')
cbar2.ax.xaxis.set_label_position('top')
cbar1.set_ticks([0.25, 0.75])
cbar1.set_ticklabels(["Satellite", "Central"])

ax2.tick_params(axis='y', left=False, right=False, labelleft=False, labelright=False)

fig.savefig("plots/central_status.png", bbox_inches="tight")

plt.close(fig)

fig = plt.figure(figsize=(8, 6))
gs = gridspec.GridSpec(1, 2)
gs.update(wspace=0.0, hspace=0.0)
ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[0, 1])

okinds = np.array(subgrps) != 0

im1 = ax1.hexbin(np.array(shmrs)[okinds], np.array(ghmrs)[okinds], C=np.array(np.array(subgrps)[okinds] == 0, dtype=int), gridsize=100, mincnt=1, cmap="coolwarm",
                 vmin=0, vmax=1, linewidths=0.2, reduce_C_function=np.mean, xscale='log', yscale='log')
im2 = ax2.hexbin(np.array(shmrs)[okinds], np.array(ghmrs)[okinds], C=np.array(dists)[okinds], gridsize=100, mincnt=1, cmap="plasma", linewidths=0.2, norm=LogNorm(),
                 reduce_C_function=np.median, xscale='log', yscale='log')

ax1.set_xlabel('$R_{1/2,*}/ [\mathrm{pkpc}]$')
ax2.set_xlabel('$R_{1/2,*}/ [\mathrm{pkpc}]$')
ax1.set_ylabel('$R_{1/2,Gas}/ [\mathrm{pkpc}]$')

divider = make_axes_locatable(ax1)
cax = divider.append_axes('top', size='5%', pad=0.05)
cbar1 = fig.colorbar(im1, cax=cax, orientation='horizontal')
divider = make_axes_locatable(ax2)
cax = divider.append_axes('top', size='5%', pad=0.05)
cbar2 = fig.colorbar(im2, cax=cax, orientation='horizontal')
cbar2.set_label('$\Delta D_{\mathrm{Group}-\mathrm{Galaxy}} /$ [pkpc]')
cbar1.ax.xaxis.set_ticks_position('top')
cbar1.ax.xaxis.set_label_position('top')
cbar2.ax.xaxis.set_ticks_position('top')
cbar2.ax.xaxis.set_label_position('top')
cbar1.set_ticks([0.25, 0.75])
cbar1.set_ticklabels(["Satellite", "Central"])

ax2.tick_params(axis='y', left=False, right=False, labelleft=False, labelright=False)

fig.savefig("plots/central_status_sat_only.png", bbox_inches="tight")

plt.close(fig)

fig = plt.figure(figsize=(8, 6))
gs = gridspec.GridSpec(1, 2)
gs.update(wspace=0.0, hspace=0.0)
ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[0, 1])

okinds = np.array(subgrps) == 0

im1 = ax1.hexbin(np.array(shmrs)[okinds], np.array(ghmrs)[okinds], C=np.array(np.array(subgrps)[okinds] == 0, dtype=int), gridsize=100, mincnt=1, cmap="coolwarm",
                 vmin=0, vmax=1, linewidths=0.2, reduce_C_function=np.mean, xscale='log', yscale='log')
im2 = ax2.hexbin(np.array(shmrs)[okinds], np.array(ghmrs)[okinds], C=np.array(dists)[okinds], gridsize=100, mincnt=1, cmap="plasma", linewidths=0.2, norm=LogNorm(),
                 reduce_C_function=np.median, xscale='log', yscale='log')

ax1.set_xlabel('$R_{1/2,*}/ [\mathrm{pkpc}]$')
ax2.set_xlabel('$R_{1/2,*}/ [\mathrm{pkpc}]$')
ax1.set_ylabel('$R_{1/2,Gas}/ [\mathrm{pkpc}]$')

divider = make_axes_locatable(ax1)
cax = divider.append_axes('top', size='5%', pad=0.05)
cbar1 = fig.colorbar(im1, cax=cax, orientation='horizontal')
divider = make_axes_locatable(ax2)
cax = divider.append_axes('top', size='5%', pad=0.05)
cbar2 = fig.colorbar(im2, cax=cax, orientation='horizontal')
cbar2.set_label('$\Delta D_{\mathrm{Group}-\mathrm{Galaxy}} /$ [pkpc]')
cbar1.ax.xaxis.set_ticks_position('top')
cbar1.ax.xaxis.set_label_position('top')
cbar2.ax.xaxis.set_ticks_position('top')
cbar2.ax.xaxis.set_label_position('top')
cbar1.set_ticks([0.25, 0.75])
cbar1.set_ticklabels(["Satellite", "Central"])

ax2.tick_params(axis='y', left=False, right=False, labelleft=False, labelright=False)

fig.savefig("plots/central_status_cent_only.png", bbox_inches="tight")



