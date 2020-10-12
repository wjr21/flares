#!/cosma/home/dp004/dc-rope1/.conda/envs/flares-env/bin/python
"""
Creates the plot of metallicity against birth density, with
the background coloured by f_th.
"""

import matplotlib.pyplot as plt
import numpy as np
import pickle
import eagle_IO.eagle_IO as E
import matplotlib.gridspec as gridspec
from unyt import mh, cm, Gyr, g, Msun, Mpc
from matplotlib.colors import LogNorm


def plot_meidan_stat(xs, ys, ax, lab, color, bins=None, ls='-'):

    if bins == None:
        bin = np.logspace(np.log10(xs.min()), np.log10(xs.max()), 20)
    else:
        zs = np.float64(xs)

        uniz = np.unique(zs)
        bin_wids = uniz[1:] - uniz[:-1]
        low_bins = uniz[:-1] - (bin_wids / 2)
        high_bins = uniz[:-1] + (bin_wids / 2)
        low_bins = list(low_bins)
        high_bins = list(high_bins)
        low_bins.append(high_bins[-1])
        high_bins.append(uniz[-1] + 1)
        low_bins = np.array(low_bins)
        high_bins = np.array(high_bins)

        bin = np.zeros(uniz.size + 1)
        bin[:-1] = low_bins
        bin[1:] = high_bins

    # Compute binned statistics
    y_stat, binedges, bin_ind = binned_statistic(xs, ys, statistic='median',
                                                 bins=bin)

    # Compute bincentres
    bin_wid = binedges[1] - binedges[0]
    bin_cents = binedges[1:] - bin_wid / 2

    okinds = np.logical_and(~np.isnan(bin_cents), ~np.isnan(y_stat))

    ax.plot(bin_cents[okinds], y_stat[okinds], color=color, linestyle=ls,
            label=lab)


def plot_spread_stat(zs, ys, ax, color):
    zs = np.float64(zs)

    uniz = np.unique(zs)
    bin_wids = uniz[1:] - uniz[:-1]
    low_bins = uniz[:-1] - (bin_wids / 2)
    high_bins = uniz[:-1] + (bin_wids / 2)
    low_bins = list(low_bins)
    high_bins = list(high_bins)
    low_bins.append(high_bins[-1])
    high_bins.append(uniz[-1] + 1)
    low_bins = np.array(low_bins)
    high_bins = np.array(high_bins)

    bin = np.zeros(uniz.size + 1)
    bin[:-1] = low_bins
    bin[1:] = high_bins

    # Compute binned statistics
    y_stat_16, binedges, bin_ind = binned_statistic(zs, ys, statistic=lambda
        y: np.percentile(y, 16), bins=bin)
    y_stat_84, binedges, bin_ind = binned_statistic(zs, ys, statistic=lambda
        y: np.percentile(y, 84), bins=bin)

    # Compute bincentres
    bin_cents = uniz

    okinds = np.logical_and(~np.isnan(bin_cents),
                            np.logical_and(~np.isnan(y_stat_16),
                                           ~np.isnan(y_stat_84)))

    ax.fill_between(bin_cents[okinds], y_stat_16[okinds], y_stat_84[okinds],
                    alpha=0.3, color=color)


def get_part_ids(sim, snapshot, part_type, all_parts=False):

    # Get the particle IDs
    if all_parts:
        part_ids = E.read_array('SNAP', sim, snapshot, 'PartType' + str(part_type) + '/ParticleIDs', numThreads=8)
    else:
        part_ids = E.read_array('PARTDATA', sim, snapshot, 'PartType' + str(part_type) + '/ParticleIDs',
                                numThreads=8)

    # Extract the halo IDs (group names/keys) contained within this snapshot
    group_part_ids = E.read_array('PARTDATA', sim, snapshot, 'PartType' + str(part_type) + '/ParticleIDs',
                                  numThreads=8)
    grp_ids = E.read_array('PARTDATA', sim, snapshot, 'PartType' + str(part_type) + '/GroupNumber',
                           numThreads=8)
    subgrp_ids = E.read_array('PARTDATA', sim, snapshot, 'PartType' + str(part_type) + '/SubGroupNumber',
                              numThreads=8)

    # Remove particles not associated to a subgroup
    okinds = subgrp_ids != 1073741824
    group_part_ids = group_part_ids[okinds]
    grp_ids = grp_ids[okinds]
    subgrp_ids = subgrp_ids[okinds]

    # Convert IDs to float(groupNumber.SubGroupNumber) format, i.e. group 1 subgroup 11 = 1.00011
    halo_ids = np.zeros(grp_ids.size, dtype=float)
    for (ind, g), sg in zip(enumerate(grp_ids), subgrp_ids):
        halo_ids[ind] = float(str(int(g)) + '.%05d' % int(sg))

    # Sort particle IDs
    unsort_part_ids = np.copy(part_ids)
    sinds = np.argsort(part_ids)
    part_ids = part_ids[sinds]

    # Get the index of particles in the snapshot array from the in group array
    sorted_index = np.searchsorted(part_ids, group_part_ids)
    yindex = np.take(sinds, sorted_index, mode="raise")
    mask = unsort_part_ids[yindex] != group_part_ids
    result = np.ma.array(yindex, mask=mask)

    # Apply mask to the id arrays
    part_groups = halo_ids[np.logical_not(result.mask)]
    parts_in_groups = result.data[np.logical_not(result.mask)]

    # Produce a dictionary containing the index of particles in each halo
    halo_part_inds = {}
    for ind, grp in zip(parts_in_groups, part_groups):
        halo_part_inds.setdefault(grp, set()).update({ind})

    return halo_part_inds


def get_data(masslim=1e8, load=False):

    regions = []
    for reg in range(0, 40):
        if reg < 10:
            regions.append('0' + str(reg))
        else:
            regions.append(str(reg))

    # Define snapshots
    snaps = ['003_z012p000', '004_z011p000', '005_z010p000',
             '006_z009p000', '007_z008p000', '008_z007p000',
             '009_z006p000', '010_z005p000', '011_z004p770']
    prog_snaps = ['002_z013p000', '003_z012p000', '004_z011p000',
                  '005_z010p000', '006_z009p000', '007_z008p000',
                  '008_z007p000', '009_z006p000', '010_z005p000']

    stellar_met = []
    stellar_bd = []
    stellar_met_inside = []
    stellar_bd_inside = []
    stellar_met_outside = []
    stellar_bd_outside = []
    zs = []
    zs_inside = []
    zs_outside = []

    for reg in regions:

        for snap, prog_snap in zip(snaps, prog_snaps):

            path = '/cosma/home/dp004/dc-rope1/FLARES/FLARES-1/G-EAGLE_' + reg + '/data'

            # Get particle IDs
            halo_part_inds = get_part_ids(path, snap, 4, all_parts=False)

            # Get halo IDs and halo data
            try:
                subgrp_ids = E.read_array('SUBFIND', path, snap, 'Subhalo/SubGroupNumber', numThreads=8)
                grp_ids = E.read_array('SUBFIND', path, snap, 'Subhalo/GroupNumber', numThreads=8)
                gal_ms = E.read_array('SUBFIND', path, snap, 'Subhalo/ApertureMeasurements/Mass/030kpc',
                                      noH=True, physicalUnits=True, numThreads=8)[:, 4] * 10**10
                gal_hmr =  E.read_array('SUBFIND', path, snap,
                                        'Subhalo/HalfMassRad',
                                        noH=True, numThreads=8)[:, 4] * 1e3
                gal_bd = E.read_array('PARTDATA', path, snap, 'PartType4/BirthDensity', noH=True,
                                        physicalUnits=True, numThreads=8)
                gal_met = E.read_array('PARTDATA', path, snap, 'PartType4/Metallicity', noH=True,
                                       physicalUnits=True, numThreads=8)
                gal_aborn = E.read_array('PARTDATA', path, snap, 'PartType4/StellarFormationTime', noH=True,
                                         physicalUnits=True, numThreads=8)
                gal_coords = E.read_array('PARTDATA', path, snap,
                                          'PartType4/Coordinates',
                                          noH=True,
                                          physicalUnits=True, numThreads=8)
            except ValueError:
                continue
            except OSError:
                continue
            except KeyError:
                continue

            z_str = snap.split('z')[1].split('p')
            z = float(z_str[0] + '.' + z_str[1])
            z_str = prog_snap.split('z')[1].split('p')
            prog_z = float(z_str[0] + '.' + z_str[1])

            # Remove particles not associated to a subgroup
            okinds = np.logical_and(subgrp_ids != 1073741824, gal_ms > masslim)
            grp_ids = grp_ids[okinds]
            subgrp_ids = subgrp_ids[okinds]
            gal_hmr = gal_hmr[okinds]
            halo_ids = np.zeros(grp_ids.size, dtype=float)
            for (ind, g), sg in zip(enumerate(grp_ids), subgrp_ids):
                halo_ids[ind] = float(str(int(g)) + '.%05d' % int(sg))

            for halo, hmr in zip(halo_ids, gal_hmr):

                # Add stars from these galaxies
                part_inds = list(halo_part_inds[halo])
                pos = gal_coords[part_inds, :]
                rs = np.linalg.norm(pos, axis=1)
                parts_bd = gal_bd[part_inds]
                parts_met = gal_met[part_inds]
                parts_aborn = gal_aborn[part_inds]
                stellar_bd.append(np.mean(parts_bd[(1 / parts_aborn) - 1 < prog_z]))
                stellar_met.append(np.mean(parts_met[(1 / parts_aborn) - 1 < prog_z]))
                stellar_bd_inside.append(np.mean(parts_bd[np.logical_and((1 / parts_aborn) - 1 < prog_z,
                                                                 rs <= hmr)]))
                stellar_met_inside.append(np.mean(parts_met[np.logical_and((1 / parts_aborn) - 1 < prog_z,
                                                                   rs <= hmr)]))
                stellar_bd_outside.append(np.mean(parts_bd[np.logical_and((1 / parts_aborn) - 1 < prog_z,
                                                                  rs > hmr)]))
                stellar_met_outside.append(np.mean(parts_met[np.logical_and((1 / parts_aborn) - 1 < prog_z,
                                                                    rs > hmr)]))
                zs.append(z)
                zs_inside.append(z)
                zs_outside.append(z)

    return stellar_bd, stellar_met, \
           stellar_bd_inside, stellar_met_inside, \
           stellar_bd_outside, stellar_met_outside, \
           zs, zs_inside, zs_outside


snaps = ['003_z012p000', '004_z011p000', '005_z010p000',
         '006_z009p000', '007_z008p000', '008_z007p000',
         '009_z006p000', '010_z005p000', '011_z004p770']

stellar_bd, stellar_met, stellar_bd_inside, stellar_met_inside, \
stellar_bd_outside, stellar_met_outside, zs, zs_inside, zs_outside \
    = get_data(masslim=10**9.5, load=False)

fig = plt.figure()
ax = fig.add_subplot(111)

# plot_meidan_stat(eagle_evo_zs_lm, eagle_evo_hmrs_lm, ax, lab='EAGLE-LM', color='darkorange', bins=1, ls="--")
# plot_spread_stat(eagle_evo_zs_lm, eagle_evo_hmrs_lm, ax, color='darkorange')
# plot_meidan_stat(eagle_evo_zs_hm, eagle_evo_hmrs_hm, ax, lab='EAGLE-HM', color='blueviolet', bins=1, ls="--")
# plot_spread_stat(eagle_evo_zs_hm, eagle_evo_hmrs_hm, ax, color='blueviolet')

plot_meidan_stat(zs, stellar_bd, ax, lab='Total', color='orangered', bins=1)
plot_spread_stat(zs, stellar_bd, ax, color='orangered')
plot_meidan_stat(zs_inside, stellar_bd_inside, ax, lab='R\leq R_{1/2}', color='royalblue', bins=1)
plot_spread_stat(zs_inside, stellar_bd_inside, ax, color='royalblue')
plot_meidan_stat(zs_outside, stellar_bd_outside, ax, lab='R > R_{1/2}', color='limegreen', bins=1)
plot_spread_stat(zs_outside, stellar_bd_outside, ax, color='limegreen')

ax.set_xlabel("$z$")
ax.set_ylabel(r"<\rho_{\mathrm{birth}}> / [cm$^{-3}$]")

handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)

fig.savefig("plots/stellarbd_z_evolution.png", bbox_inches="tight")

plt.close(fig)

fig = plt.figure()
ax = fig.add_subplot(111)

# plot_meidan_stat(eagle_evo_zs_lm, eagle_evo_hmrs_lm, ax, lab='EAGLE-LM', color='darkorange', bins=1, ls="--")
# plot_spread_stat(eagle_evo_zs_lm, eagle_evo_hmrs_lm, ax, color='darkorange')
# plot_meidan_stat(eagle_evo_zs_hm, eagle_evo_hmrs_hm, ax, lab='EAGLE-HM', color='blueviolet', bins=1, ls="--")
# plot_spread_stat(eagle_evo_zs_hm, eagle_evo_hmrs_hm, ax, color='blueviolet')

plot_meidan_stat(zs, stellar_met, ax, lab='Total', color='orangered', bins=1)
plot_spread_stat(zs, stellar_met, ax, color='orangered')
plot_meidan_stat(zs_inside, stellar_met_inside, ax, lab='R\leq R_{1/2}',
                 color='royalblue', bins=1)
plot_spread_stat(zs_inside, stellar_met_inside, ax, color='royalblue')
plot_meidan_stat(zs_outside, stellar_met_outside, ax, lab='R > R_{1/2}',
                 color='limegreen', bins=1)
plot_spread_stat(zs_outside, stellar_met_outside, ax, color='limegreen')

ax.set_xlabel("$z$")
ax.set_ylabel(r"$<Z>$")

handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)

fig.savefig("plots/stellarmet_z_evolution.png", bbox_inches="tight")