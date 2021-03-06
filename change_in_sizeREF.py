#!/cosma/home/dp004/dc-rope1/.conda/envs/flares-env/bin/python
import matplotlib as ml
ml.use('Agg')
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import matplotlib.gridspec as gridspec
import eagle_IO.eagle_IO as E
import h5py
import sys
import pickle
import seaborn as sns


sns.set_style('whitegrid')


def get_change_in_radius(snap, prog_snap, savepath, gal_data, gals):

    # Open graph file
    hdf = h5py.File(savepath + 'SubMgraph_' + snap + '.hdf5', 'r')

    # Initialise arrays for results
    delta_hmrs = np.zeros(len(gals))
    delta_ms = np.zeros(len(gals))

    print('There are', len(gals), 'Galaxies to test in snapshot', snap)

    # Loop over galaxies
    for ind, i in enumerate(gals):

        # Get this halo's stellar mass and half mass radius
        mass, hmr = gal_data[snap][i]['m'], gal_data[snap][i]['hmr']

        # Get progenitors
        try:
            progs = hdf[str(i)]['Prog_haloIDs'][...]
        except KeyError:
            # Define change in properties
            delta_hmrs[ind] = 2**30
            delta_ms[ind] = 2**30
            print(i, ind, "Galaxy has no dark matter")
            continue

        if len(progs) == 0:

            # Define change in properties
            delta_hmrs[ind] = 2**30
            delta_ms[ind] = 2**30

        else:

            # Get progenitor properties
            prog_cont = hdf[str(i)]['prog_npart_contribution'][...]
            prog_masses = hdf[str(i)]['prog_stellar_mass_contribution'][...] * 10**10
            prog_hmrs = np.array([gal_data[prog_snap][p]['hmr'] for p in progs])

            # Get main progenitor information
            main = np.argmax(prog_cont)
            try:
                main_mass = prog_masses[main]
            except IndexError:
                # Define change in properties
                delta_hmrs[ind] = 2 ** 30
                delta_ms[ind] = 2 ** 30
                print(i, ind, "Broken progenitors")
                continue
            main_hmr = prog_hmrs[main]

            # Define change in properties
            delta_hmrs[ind] = hmr / main_hmr
            delta_ms[ind] = mass / np.sum(prog_masses)

    hdf.close()

    return delta_hmrs[delta_ms < 2**30], delta_ms[delta_ms < 2**30]


def main_change(masslim=1e8, hmrcut=False, load=False):

    # Define snapshots
    snaps = ['004_z008p075', '008_z005p037', '010_z003p984',
             '013_z002p478', '017_z001p487', '018_z001p259',
             '019_z001p004', '020_z000p865', '024_z000p366']
    prog_snaps = ['003_z008p988', '007_z005p487', '009_z004p485',
                  '012_z003p017', '016_z001p737', '017_z001p487',
                  '018_z001p259', '019_z001p004', '023_z000p503']

    if load:

        with open('changeinsizeREF.pck', 'rb') as pfile1:
            save_dict = pickle.load(pfile1)
        delta_hmr_dict = save_dict['hmr']
        delta_ms_dict = save_dict['ms']

    else:

        delta_hmr_dict = {}
        delta_ms_dict = {}

        for snap, prog_snap in zip(snaps, prog_snaps):

            savepath = '/cosma/home/dp004/dc-rope1/FLARES/FLARES-1/MergerGraphs/REF/'

            path = '/cosma7/data//Eagle/ScienceRuns/Planck1/L0100N1504/PE/REFERENCE/data'

            # Get halo IDs and halo data
            try:
                subgrp_ids = E.read_array('SUBFIND', path, snap, 'Subhalo/SubGroupNumber', numThreads=8)
                grp_ids = E.read_array('SUBFIND', path, snap, 'Subhalo/GroupNumber', numThreads=8)
                gal_hmrs = E.read_array('SUBFIND', path, snap, 'Subhalo/HalfMassRad', noH=True,
                                        physicalUnits=True, numThreads=8)[:, 4]
                gal_ms = E.read_array('SUBFIND', path, snap, 'Subhalo/ApertureMeasurements/Mass/030kpc',
                                      noH=False, physicalUnits=False, numThreads=8)[:, 4] * 10**10

                # Get halo IDs and halo data
                prog_subgrp_ids = E.read_array('SUBFIND', path, prog_snap, 'Subhalo/SubGroupNumber', numThreads=8)
                prog_grp_ids = E.read_array('SUBFIND', path, prog_snap, 'Subhalo/GroupNumber', numThreads=8)
                prog_gal_hmrs = E.read_array('SUBFIND', path, prog_snap, 'Subhalo/HalfMassRad', noH=True,
                                        physicalUnits=True, numThreads=8)[:, 4]
                prog_gal_ms = E.read_array('SUBFIND', path, prog_snap, 'Subhalo/ApertureMeasurements/Mass/030kpc',
                                           noH=False, physicalUnits=False, numThreads=8)[:, 4] * 10**10
            except ValueError:
                continue
            except OSError:
                continue
            except KeyError:
                continue

            z_str = snap.split('z')[1].split('p')
            z = float(z_str[0] + '.' + z_str[1])

            # Convert inputs to physical kpc
            convert_pMpc = 1 / (1 + z)

            # Define comoving softening length in kpc
            csoft = 0.001802390 / 0.677 * convert_pMpc

            # Remove particles not associated to a subgroup
            if hmrcut:
                okinds = np.logical_and(subgrp_ids != 1073741824, np.logical_and(gal_ms > 0, gal_hmrs / csoft < 1.2))
            else:
                okinds = np.logical_and(subgrp_ids != 1073741824, gal_ms > 0)
            gal_hmrs = gal_hmrs[okinds]
            gal_ms = gal_ms[okinds]
            grp_ids = grp_ids[okinds]
            subgrp_ids = subgrp_ids[okinds]
            halo_ids = np.zeros(grp_ids.size, dtype=float)
            for (ind, g), sg in zip(enumerate(grp_ids), subgrp_ids):
                halo_ids[ind] = float(str(int(g)) + '.%05d'%int(sg))

            # Remove particles not associated to a subgroup
            okinds = prog_subgrp_ids != 1073741824
            prog_gal_hmrs = prog_gal_hmrs[okinds]
            prog_gal_ms = prog_gal_ms[okinds]
            prog_grp_ids = prog_grp_ids[okinds]
            prog_subgrp_ids = prog_subgrp_ids[okinds]
            prog_ids = np.zeros(prog_grp_ids.size, dtype=float)
            for (ind, g), sg in zip(enumerate(prog_grp_ids), prog_subgrp_ids):
                prog_ids[ind] = float(str(int(g)) + '.%05d'%int(sg))

            # Initialise galaxy data
            gal_data = {snap: {}, prog_snap: {}}
            for m, hmr, i in zip(gal_ms, gal_hmrs, halo_ids):
                gal_data[snap][i] = {'m': m, 'hmr': hmr}
            for m, hmr, i in zip(prog_gal_ms, prog_gal_hmrs, prog_ids):
                gal_data[prog_snap][i] = {'m': m, 'hmr': hmr}

            # Get change in stellar mass and half mass radius
            delta_hmr_dict[snap], delta_ms_dict[snap] = get_change_in_radius(snap, prog_snap, savepath, gal_data,
                                                                             halo_ids[gal_ms > masslim])

        with open('changeinsizeREF.pck', 'wb') as pfile1:
            pickle.dump({'hmr' : delta_hmr_dict, 'ms': delta_ms_dict}, pfile1)

    delta_hmr = np.concatenate(delta_hmr_dict.values())
    delta_mass = np.concatenate(delta_ms_dict.values())

    # Set up plot
    fig = plt.figure()
    ax = fig.add_subplot(111)

    # Plot results
    cbar = ax.hexbin(delta_mass, delta_hmr, gridsize=100, mincnt=1, xscale='log', yscale='log',
                     norm=LogNorm(), linewidths=0.2, cmap='viridis')

    # Label axes
    ax.set_xlabel(r'$M_{\star}/M_{\star, \mathrm{from progs}}$')
    ax.set_ylabel('$R_{1/2,\mathrm{\star}}/R_{1/2,\mathrm{\star},\mathrm{main prog}}$')

    fig.colorbar(cbar, ax=ax)

    fig.savefig('plots/change_in_halfmassradiusREF.png', bbox_inches='tight')

    plt.close()

    axlims_x = []
    axlims_y = []

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

        xs_plt = delta_ms_dict[snap]
        delta_hmr_plt = delta_hmr_dict[snap]

        okinds = np.logical_and(np.logical_and(xs_plt > 0, ~np.isnan(xs_plt)), delta_hmr_plt > 0)
        xs_plt = xs_plt[okinds]
        delta_hmr_plt = delta_hmr_plt[okinds]

        if len(xs_plt) > 0:
            cbar = ax.hexbin(xs_plt, delta_hmr_plt, gridsize=100, mincnt=1, xscale='log', yscale='log',
                             linewidths=0.2, cmap='viridis')

            # Add colorbars
            cax1 = ax.inset_axes([0.5, 0.1, 0.47, 0.03])
            cbar1 = fig.colorbar(cbar, cax=cax1, orientation="horizontal")

            # Label colorbars
            cbar1.ax.set_xlabel(r'$N$', labelpad=1.5, fontsize=9)
            cbar1.ax.xaxis.set_label_position('top')
            cbar1.ax.tick_params(axis='x', labelsize=8)

        ax.text(0.8, 0.9, f'$z={z}$', bbox=dict(boxstyle="round,pad=0.3", fc='w', ec="k", lw=1, alpha=0.8),
                transform=ax.transAxes, horizontalalignment='right', fontsize=8)

        axlims_x.extend(ax.get_xlim())
        axlims_y.extend(ax.get_ylim())

        # Label axes
        if i == 2:
            ax.set_xlabel(r'$M_{\star}/M_{\star, \mathrm{from progs}}$')
        if j == 0:
            ax.set_ylabel('$R_{1/2,\mathrm{\star}}/R_{1/2,\mathrm{\star},\mathrm{main prog}}$')

    for ax in [ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9]:
        ax.set_xlim(np.min(axlims_x), np.max(axlims_x))
        ax.set_ylim(np.min(axlims_y), np.max(axlims_y))
        for spine in ax.spines.values():
            spine.set_edgecolor('k')

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

    # fig.colorbar(cbar, ax=ax)

    fig.savefig('plots/change_in_halfmassradiusredshiftREF.png', bbox_inches='tight')


regions = []
for reg in range(0, 40):
    if reg < 10:
        regions.append('0' + str(reg))
    else:
        regions.append(str(reg))

main_change(masslim=10**9.5)

