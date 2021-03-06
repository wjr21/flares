#!/cosma/home/dp004/dc-rope1/.conda/envs/flares-env/bin/python
"""
Creates the plot of metallicity against birth density, with
the background coloured by f_th.
"""

import matplotlib.pyplot as plt
import numpy as np
import pickle
import eagle_IO.eagle_IO as E
from scipy.stats import binned_statistic
from astropy.cosmology import Planck13 as cosmo
from astropy.cosmology import z_at_value
import astropy.units as u
import seaborn as sns

sns.set_style("whitegrid")


def calc_ages(z, a_born):

    # Convert scale factor into redshift
    z_borns = 1 / a_born - 1

    # Convert to time in Gyrs
    t = cosmo.age(z).value
    t_born = np.zeros(len(a_born))
    for ind, z_born in enumerate(z_borns):
        t_born[ind] = cosmo.age(z_born).value

    # Calculate the VR
    ages = (t - t_born)

    return ages


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


def get_data(masslim=1e8, eagle=False):

    if eagle:
        regions = ["EAGLE", ]
    else:
        regions = []
        for reg in range(0, 1):
            if reg < 10:
                regions.append('0' + str(reg))
            else:
                regions.append(str(reg))

    # Define snapshots
    if eagle:
        pre_snaps = ['000_z020p000', '003_z008p988', '006_z005p971',
                     '009_z004p485', '012_z003p017', '015_z002p012',
                     '018_z001p259', '021_z000p736', '024_z000p366',
                     '027_z000p101', '001_z015p132', '004_z008p075',
                     '007_z005p487', '010_z003p984', '013_z002p478',
                     '016_z001p737', '019_z001p004', '022_z000p615',
                     '025_z000p271', '028_z000p000', '002_z009p993',
                     '005_z007p050', '008_z005p037', '011_z003p528',
                     '014_z002p237', '017_z001p487', '020_z000p865',
                     '023_z000p503', '026_z000p183']

        snaps = np.zeros(29, dtype=object)
        for s in pre_snaps:
            ind = int(s.split('_')[0])
            snaps[ind] = s

        snaps = list(snaps)
    else:
        snaps = ['001_z014p000', '002_z013p000', '003_z012p000',
                 '004_z011p000', '005_z010p000',
                 '006_z009p000', '007_z008p000', '008_z007p000', '009_z006p000',
                 '010_z005p000', '011_z004p770']

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

        for snap in snaps:
            
            if eagle:
                path = '/cosma7/data//Eagle/ScienceRuns/Planck1/L0050N0752/PE/AGNdT9/data/'
            else:
                path = '/cosma/home/dp004/dc-rope1/FLARES/FLARES-1/G-EAGLE_' + reg + '/data'

            # Get particle IDs
            try:
                halo_part_inds = get_part_ids(path, snap, 4, all_parts=False)
            except ValueError:
                print(reg, snap, "No data")
                continue
            except OSError:
                print(reg, snap, "No data")
                continue
            except KeyError:
                print(reg, snap, "No data")
                continue

            print(reg, snap)

            z_str = snap.split('z')[1].split('p')
            z = float(z_str[0] + '.' + z_str[1])

            # Get halo IDs and halo data
            try:
                subgrp_ids = E.read_array('SUBFIND', path, snap,
                                          'Subhalo/SubGroupNumber',
                                          numThreads=8)
                grp_ids = E.read_array('SUBFIND', path, snap,
                                       'Subhalo/GroupNumber',
                                       numThreads=8)
                gal_ms = E.read_array('SUBFIND', path, snap,
                                      'Subhalo/ApertureMeasurements/Mass/030kpc',
                                      noH=True, physicalUnits=True,
                                      numThreads=8)[:, 4] * 10**10
                gal_hmr = E.read_array('SUBFIND', path, snap,
                                       'Subhalo/HalfMassRad',
                                       noH=True, physicalUnits=True,
                                       numThreads=8)[:, 4]
                gal_cop = E.read_array('SUBFIND', path, snap,
                                       'Subhalo/CentreOfPotential',
                                       noH=True, physicalUnits=True,
                                       numThreads=8)
                gal_bd = E.read_array('PARTDATA', path, snap,
                                      'PartType4/BirthDensity', noH=True,
                                        physicalUnits=True, numThreads=8)
                gal_met = E.read_array('PARTDATA', path, snap,
                                       'PartType4/Metallicity', noH=True,
                                       physicalUnits=True, numThreads=8)
                gal_aborn = E.read_array('PARTDATA', path, snap,
                                         'PartType4/StellarFormationTime',
                                         noH=True, physicalUnits=True,
                                         numThreads=8)
                gal_coords = E.read_array('PARTDATA', path, snap,
                                          'PartType4/Coordinates',
                                          noH=True, physicalUnits=True,
                                          numThreads=8)
            except ValueError:
                print(reg, snap, "No data")
                continue
            except OSError:
                print(reg, snap, "No data")
                continue
            except KeyError:
                print(reg, snap, "No data")
                continue

            # Remove particles not associated to a subgroup
            okinds = np.logical_and(subgrp_ids != 1073741824, gal_ms > masslim)
            grp_ids = grp_ids[okinds]
            subgrp_ids = subgrp_ids[okinds]
            gal_hmr = gal_hmr[okinds]
            gal_cop = gal_cop[okinds]
            halo_ids = np.zeros(grp_ids.size, dtype=float)
            for (ind, g), sg in zip(enumerate(grp_ids), subgrp_ids):
                halo_ids[ind] = float(str(int(g)) + '.%05d' % int(sg))

            for halo, hmr, cop in zip(halo_ids, gal_hmr, gal_cop):

                # Add stars from these galaxies
                part_inds = list(halo_part_inds[halo])
                pos = gal_coords[part_inds, :] - cop
                rs = np.linalg.norm(pos, axis=1)
                parts_bd = gal_bd[part_inds]
                parts_met = gal_met[part_inds]
                parts_aborn = gal_aborn[part_inds]

                z100Myr = z_at_value(cosmo.age, (cosmo.age(z).value - 0.1) * u.Gyr)

                stellar_bd.append(np.mean(parts_bd[(1 / parts_aborn) - 1 >= z100Myr]))
                stellar_met.append(np.mean(parts_met[(1 / parts_aborn) - 1 >= z100Myr]))
                stellar_bd_inside.append(np.mean(parts_bd[np.logical_and((1 / parts_aborn) - 1 >= z100Myr,
                                                                 rs <= hmr)]))
                stellar_met_inside.append(np.mean(parts_met[np.logical_and((1 / parts_aborn) - 1 >= z100Myr,
                                                                   rs <= hmr)]))
                stellar_bd_outside.append(np.mean(parts_bd[np.logical_and((1 / parts_aborn) - 1 >= z100Myr,
                                                                  rs > hmr)]))
                stellar_met_outside.append(np.mean(parts_met[np.logical_and((1 / parts_aborn) - 1 >= z100Myr,
                                                                    rs > hmr)]))
                zs.append(z)
                zs_inside.append(z)
                zs_outside.append(z)

    return stellar_bd, stellar_met, \
           stellar_bd_inside, stellar_met_inside, \
           stellar_bd_outside, stellar_met_outside, \
           zs, zs_inside, zs_outside

stellar_bd, stellar_met, stellar_bd_inside, stellar_met_inside, \
stellar_bd_outside, stellar_met_outside, zs, zs_inside, zs_outside \
    = get_data(masslim=10**9)

eagle_stellar_bd, eagle_stellar_met, \
eagle_stellar_bd_inside, eagle_stellar_met_inside, \
eagle_stellar_bd_outside, eagle_stellar_met_outside, \
eagle_zs, eagle_zs_inside, eagle_zs_outside \
    = get_data(masslim=10**9, eagle=True)

fig = plt.figure()
ax = fig.add_subplot(111)

plot_meidan_stat(eagle_zs, eagle_stellar_bd, ax, lab='Eagle: Total', color='orangered', bins=1, ls="--")
plot_spread_stat(eagle_zs, eagle_stellar_bd, ax, color='orangered')
plot_meidan_stat(eagle_zs_inside, eagle_stellar_bd_inside, ax, lab='Eagle: $R\leq R_{1/2}$', color='royalblue', bins=1, ls="--")
plot_spread_stat(eagle_zs_inside, eagle_stellar_bd_inside, ax, color='royalblue')
plot_meidan_stat(eagle_zs_outside, eagle_stellar_bd_outside, ax, lab='Eagle: $R > R_{1/2}$', color='limegreen', bins=1, ls="--")
plot_spread_stat(eagle_zs_outside, eagle_stellar_bd_outside, ax, color='limegreen')

plot_meidan_stat(zs, stellar_bd, ax, lab='FLARES: Total', color='orangered', bins=1)
plot_spread_stat(zs, stellar_bd, ax, color='orangered')
plot_meidan_stat(zs_inside, stellar_bd_inside, ax, lab='FLARES: $R\leq R_{1/2}$', color='royalblue', bins=1)
plot_spread_stat(zs_inside, stellar_bd_inside, ax, color='royalblue')
plot_meidan_stat(zs_outside, stellar_bd_outside, ax, lab='FLARES: $R > R_{1/2}$', color='limegreen', bins=1)
plot_spread_stat(zs_outside, stellar_bd_outside, ax, color='limegreen')

ax.set_xlabel("$z$")
ax.set_ylabel(r"$<\rho_{\mathrm{birth}}>$ / [cm$^{-3}$]")

handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)

ax.set_yscale("log")

fig.savefig("plots/stellarbd_z_evolution.png", bbox_inches="tight")

plt.close(fig)

fig = plt.figure()
ax = fig.add_subplot(111)

plot_meidan_stat(eagle_zs, eagle_stellar_met, ax, lab='Eagle: Total', color='orangered', bins=1, ls="--")
plot_spread_stat(eagle_zs, eagle_stellar_met, ax, color='orangered')
plot_meidan_stat(eagle_zs_inside, eagle_stellar_met_inside, ax, lab='Eagle: $R\leq R_{1/2}$', color='royalblue', bins=1, ls="--")
plot_spread_stat(eagle_zs_inside, eagle_stellar_met_inside, ax, color='royalblue')
plot_meidan_stat(eagle_zs_outside, eagle_stellar_met_outside, ax, lab='Eagle: $R > R_{1/2}$', color='limegreen', bins=1, ls="--")
plot_spread_stat(eagle_zs_outside, eagle_stellar_met_outside, ax, color='limegreen')

plot_meidan_stat(zs, stellar_met, ax, lab='Total', color='orangered', bins=1)
plot_spread_stat(zs, stellar_met, ax, color='orangered')
plot_meidan_stat(zs_inside, stellar_met_inside, ax, lab='$R\leq R_{1/2}$',
                 color='royalblue', bins=1)
plot_spread_stat(zs_inside, stellar_met_inside, ax, color='royalblue')
plot_meidan_stat(zs_outside, stellar_met_outside, ax, lab='$R > R_{1/2}$',
                 color='limegreen', bins=1)
plot_spread_stat(zs_outside, stellar_met_outside, ax, color='limegreen')

ax.set_xlabel("$z$")
ax.set_ylabel(r"$<Z>$")

handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)

fig.savefig("plots/stellarmet_z_evolution.png", bbox_inches="tight")