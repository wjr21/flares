#!/cosma/home/dp004/dc-rope1/.conda/envs/flares-env/bin/python
"""
Creates the plot of metallicity against birth density, with
the background coloured by f_th.
"""

import matplotlib.pyplot as plt
import numpy as np
import pickle
from matplotlib.colors import LogNorm
import matplotlib.gridspec as gridspec
import eagle_IO.eagle_IO as E
from scipy.stats import binned_statistic
from astropy.cosmology import Planck13 as cosmo
import astropy.units as u
from unyt import mh, cm, Gyr, g, Msun, Mpc
import seaborn as sns

sns.set_style("whitegrid")

def plot_meidan_stat(xs, ys, ax, lab, color, bins=None, ls='-', xy=True):

    # bin_lims = [0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4, 1.6,
    #             1.8, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5,
    #             6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 20.0]

    bin_lims = np.linspace(0, 25.0, 30)

    bin_cents = []
    y_stat = []
    for low, up in zip(bin_lims[:-1], bin_lims[1:]):

        okinds = np.logical_and(xs > low, xs <= up)

        bin_cents.append(np.median(xs[okinds]))
        y_stat.append(np.nanmedian(ys[okinds]))

    bin_cents = np.array(bin_cents)
    y_stat = np.array(y_stat)

    okinds = np.logical_and(~np.isnan(bin_cents), ~np.isnan(y_stat))

    if xy:
        ax.plot(bin_cents[okinds], y_stat[okinds], color=color, linestyle=ls,
                label=lab)
    else:
        sinds = np.argsort(bin_cents[okinds])
        ax.plot(y_stat[okinds][sinds], bin_cents[okinds][sinds], color=color,
                linestyle=ls,
                label=lab)


def plot_meidan_statyx(xs, ys, ax, lab, color, ls='-'):

    zs_binlims = np.linspace(0, 15, 31)

    zs_plt = np.zeros(50)
    rs_plt = np.zeros(50)
    for ind, (low, up) in enumerate(zip(zs_binlims[:-1], zs_binlims[1:])):
        okinds = np.logical_and(ys >= low, ys < up)
        rs_plt[ind] = np.median(xs[okinds])
        zs_plt[ind] = np.median(ys[okinds])

    ax.plot(rs_plt, zs_plt, color=color, linestyle=ls, label=lab)


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


def get_data(masslim=1e8, eagle=False, ref=False):

    if eagle or ref:
        regions = ["EAGLE", ]
    else:
        regions = []
        for reg in range(0, 40):
            if reg < 10:
                regions.append('0' + str(reg))
            else:
                regions.append(str(reg))

    # Define snapshots
    if eagle or ref:
        snaps = ['027_z000p101']

    else:
        snaps = ['011_z004p770', ]

    bd_in = []
    bd_out = []
    met_in = []
    met_out = []
    zs_in = []
    mass_in = []
    zs_out = []
    mass_out = []

    for reg in regions:

        for snap in snaps:
            
            if eagle:
                path = "/cosma7/data//Eagle/ScienceRuns/Planck1/" \
                       "L0050N0752/PE/AGNdT9/data/"
            elif ref:
                path = "/cosma7/data//Eagle/ScienceRuns/Planck1/" \
                       "L0100N1504/PE/REFERENCE/data"
            else:
                path = "/cosma/home/dp004/dc-rope1/FLARES/FLARES-1/" \
                       "G-EAGLE_" + reg + "/data"

            print(reg, snap)

            z_str = snap.split('z')[1].split('p')
            z = float(z_str[0] + '.' + z_str[1])

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

            # Get halo IDs and halo data
            try:
                grp_ids = E.read_array('SUBFIND', path, snap,
                                       'Subhalo/GroupNumber',
                                       numThreads=8)
                subgrp_ids = E.read_array('SUBFIND', path, snap,
                                          'Subhalo/SubGroupNumber',
                                          numThreads=8)
                gal_ms = E.read_array('SUBFIND', path, snap,
                                      'Subhalo/ApertureMeasurements/Mass/030kpc',
                                      noH=True, physicalUnits=True,
                                      numThreads=8)[:, 4] * 10**10
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
                gal_coords = E.read_array('PARTDATA', path, snap,
                                          'PartType4/Coordinates',
                                          noH=True, physicalUnits=True,
                                          numThreads=8)
                gal_aborn = E.read_array('PARTDATA', path, snap,
                                         'PartType4/StellarFormationTime',
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
            gal_cop = gal_cop[okinds]
            gal_ms = gal_ms[okinds]
            halo_ids = np.zeros(grp_ids.size, dtype=float)
            for (ind, g), sg in zip(enumerate(grp_ids), subgrp_ids):
                halo_ids[ind] = float(str(int(g)) + '.%05d' % int(sg))

            for halo, cop, m in zip(halo_ids, gal_cop, gal_ms):

                # Add stars from these galaxies
                part_inds = list(halo_part_inds[halo])
                pos = gal_coords[part_inds, :] - cop
                rs = np.linalg.norm(pos, axis=1) * 10**3
                parts_bd = (gal_bd[part_inds] * 10**10
                            * Msun / Mpc ** 3 / mh).to(1 / cm ** 3).value
                parts_met = gal_met[part_inds]
                parts_aborn = gal_aborn[part_inds]

                okinds1 = rs <= 1
                okinds30 = np.logical_and(rs <= 30, rs > 1)

                bd_in.extend(parts_bd[okinds1])
                bd_out.extend(parts_bd[okinds30])
                met_in.extend(parts_met[okinds1])
                met_out.extend(parts_met[okinds30])

                zs_in.extend((1 / parts_aborn[okinds1]) - 1)
                zs_out.extend((1 / parts_aborn[okinds30]) - 1)

                mass_in.extend(np.full_like(parts_met[okinds1], m))
                mass_out.extend(np.full_like(parts_met[okinds30], m))

    return np.array(bd_in), np.array(bd_out), \
           np.array(met_in), np.array(met_out), \
           np.array(zs_in), np.array(zs_out), \
           np.array(mass_in), np.array(mass_out)

bd_in, bd_out, met_in, met_out, zs_in, zs_out, mass_in, mass_out = get_data(masslim=10**8)

agndt9_bd_in, agndt9_bd_out, agndt9_met_in, agndt9_met_out, agndt9_zs_in, agndt9_zs_out, agndt9_mass_in, agndt9_mass_out = get_data(masslim=10**8, eagle=True)

ref_bd_in, ref_bd_out, ref_met_in, ref_met_out, ref_zs_in, ref_zs_out, ref_mass_in, ref_mass_out = get_data(masslim=10**8, ref=True)

bd_in_all = np.concatenate((bd_in,
                            agndt9_bd_in,
                            ref_bd_in))
bd_out_all = np.concatenate((bd_out,
                             agndt9_bd_out,
                             ref_bd_out))
bd_all = np.concatenate((bd_out_all, bd_in_all))

met_in_all = np.concatenate((met_in,
                            agndt9_met_in,
                            ref_met_in))
met_out_all = np.concatenate((met_out,
                             agndt9_met_out,
                             ref_met_out))
met_all = np.concatenate((met_out_all, met_in_all))

zs_in_all = np.concatenate((zs_in,
                            agndt9_zs_in,
                            ref_zs_in))
zs_out_all = np.concatenate((zs_out,
                             agndt9_zs_out,
                             ref_zs_out))
zs_all = np.concatenate((zs_out_all, zs_in_all))

mass_in_all = np.concatenate((mass_in,
                            agndt9_mass_in,
                            ref_mass_in))
mass_out_all = np.concatenate((mass_out,
                             agndt9_mass_out,
                             ref_mass_out))
mass_all = np.concatenate((mass_out_all, mass_in_all))

fig = plt.figure(figsize=(5, 9))
ax = fig.add_subplot(111)

ax.hexbin(zs_all, bd_all,
          gridsize=100, mincnt=1, yscale="log",
          norm=LogNorm(), linewidths=0.2,
          cmap='Greys', alpha=0.4)

okinds1in = np.logical_and(mass_in_all > 10**8, mass_in_all <= 10**9)
okinds2in = np.logical_and(mass_in_all > 10**9, mass_in_all <= 10**9.5)
okinds3in = np.logical_and(mass_in_all > 10**9.5, mass_in_all <= 10**10)
okinds4in = mass_in_all > 10**10
okinds1out = np.logical_and(mass_out_all > 10**8, mass_out_all <= 10**9)
okinds2out = np.logical_and(mass_out_all > 10**9, mass_out_all <= 10**9.5)
okinds3out = np.logical_and(mass_out_all > 10**9.5, mass_out_all <= 10**10)
okinds4out = mass_out_all > 10**10

plot_meidan_stat(zs_out_all[okinds1out], bd_out_all[okinds1out],
                 ax, lab="Out: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1, ls="dashed")

plot_meidan_stat(zs_out_all[okinds2out], bd_out_all[okinds2out],
                 ax, lab="Out: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1, ls="dashed")

plot_meidan_stat(zs_out_all[okinds3out], bd_out_all[okinds3out],
                 ax, lab="Out: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1, ls="dashed")

plot_meidan_stat(zs_out_all[okinds4out], bd_out_all[okinds4out],
                 ax, lab="Out: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1, ls="dashed")

plot_meidan_stat(zs_in_all[okinds1in], bd_in_all[okinds1in],
                 ax, lab="In: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1)

plot_meidan_stat(zs_in_all[okinds2in], bd_in_all[okinds2in],
                 ax, lab="In: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1)

plot_meidan_stat(zs_in_all[okinds3in], bd_in_all[okinds3in],
                 ax, lab="In: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1)

plot_meidan_stat(zs_in_all[okinds4in], bd_in_all[okinds4in],
                 ax, lab="In: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1)

ax.set_xlabel("$z$")
ax.set_ylabel(r"$\rho_{\mathrm{birth}}$ / [cm$^{-3}$]")

handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)

fig.savefig("plots/aperture_bd_evolution_split.png", bbox_inches="tight")

plt.close(fig)

fig = plt.figure(figsize=(5, 9))
ax = fig.add_subplot(111)

okinds = met_all > 0

ax.hexbin(zs_all[okinds], met_all[okinds],
          gridsize=100, mincnt=1, yscale="log",
          norm=LogNorm(), linewidths=0.2,
          cmap='Greys', alpha=0.4)

okinds1in = np.logical_and(mass_in_all > 10**8, mass_in_all <= 10**9)
okinds2in = np.logical_and(mass_in_all > 10**9, mass_in_all <= 10**9.5)
okinds3in = np.logical_and(mass_in_all > 10**9.5, mass_in_all <= 10**10)
okinds4in = mass_in_all > 10**10
okinds1out = np.logical_and(mass_out_all > 10**8, mass_out_all <= 10**9)
okinds2out = np.logical_and(mass_out_all > 10**9, mass_out_all <= 10**9.5)
okinds3out = np.logical_and(mass_out_all > 10**9.5, mass_out_all <= 10**10)
okinds4out = mass_out_all > 10**10

plot_meidan_stat(zs_out_all[okinds1out], met_out_all[okinds1out],
                 ax, lab="Out: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1, ls="dashed")

plot_meidan_stat(zs_out_all[okinds2out], met_out_all[okinds2out],
                 ax, lab="Out: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1, ls="dashed")

plot_meidan_stat(zs_out_all[okinds3out], met_out_all[okinds3out],
                 ax, lab="Out: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1, ls="dashed")

plot_meidan_stat(zs_out_all[okinds4out], met_out_all[okinds4out],
                 ax, lab="Out: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1, ls="dashed")

plot_meidan_stat(zs_in_all[okinds1in], met_in_all[okinds1in],
                 ax, lab="In: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1)

plot_meidan_stat(zs_in_all[okinds2in], met_in_all[okinds2in],
                 ax, lab="In: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1)

plot_meidan_stat(zs_in_all[okinds3in], met_in_all[okinds3in],
                 ax, lab="In: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1)

plot_meidan_stat(zs_in_all[okinds4in], met_in_all[okinds4in],
                 ax, lab="In: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1)

ax.set_xlabel("$z$")
ax.set_ylabel(r"$Z$")

handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels)

ax.set_ylim(10**-10, None)

fig.savefig("plots/aperture_met_evolution_split.png", bbox_inches="tight")

plt.close(fig)

fig = plt.figure(figsize=(8, 8))
gs = gridspec.GridSpec(nrows=2, ncols=2)
gs.update(wspace=0.0, hspace=0.0)
ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[1, 0])
ax3 = fig.add_subplot(gs[0, 1])
ax4 = fig.add_subplot(gs[1, 1])

ax1.hexbin(zs_all, bd_all, gridsize=100, mincnt=1, yscale="log",
           norm=LogNorm(), linewidths=0.2, cmap='Greys', alpha=0.4)

okinds1in = np.logical_and(mass_in_all > 10**8, mass_in_all <= 10**9)
okinds2in = np.logical_and(mass_in_all > 10**9, mass_in_all <= 10**9.5)
okinds3in = np.logical_and(mass_in_all > 10**9.5, mass_in_all <= 10**10)
okinds4in = mass_in_all > 10**10
okinds1out = np.logical_and(mass_out_all > 10**8, mass_out_all <= 10**9)
okinds2out = np.logical_and(mass_out_all > 10**9, mass_out_all <= 10**9.5)
okinds3out = np.logical_and(mass_out_all > 10**9.5, mass_out_all <= 10**10)
okinds4out = mass_out_all > 10**10

plot_meidan_stat(zs_out_all[okinds1out], bd_out_all[okinds1out],
                 ax1, lab="Out: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1, ls="dashed")

plot_meidan_stat(zs_out_all[okinds2out], bd_out_all[okinds2out],
                 ax1, lab="Out: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1, ls="dashed")

plot_meidan_stat(zs_out_all[okinds3out], bd_out_all[okinds3out],
                 ax1, lab="Out: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1, ls="dashed")

plot_meidan_stat(zs_out_all[okinds4out], bd_out_all[okinds4out],
                 ax1, lab="Out: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1, ls="dashed")

plot_meidan_stat(zs_in_all[okinds1in], bd_in_all[okinds1in],
                 ax1, lab="In: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1)

plot_meidan_stat(zs_in_all[okinds2in], bd_in_all[okinds2in],
                 ax1, lab="In: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1)

plot_meidan_stat(zs_in_all[okinds3in], bd_in_all[okinds3in],
                 ax1, lab="In: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1)

plot_meidan_stat(zs_in_all[okinds4in], bd_in_all[okinds4in],
                 ax1, lab="In: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1)

ax1.text(0.8, 0.9, "All",
        bbox=dict(boxstyle="round,pad=0.3", fc='w', ec="k", lw=1, alpha=0.8),
        transform=ax1.transAxes, horizontalalignment='right', fontsize=8)

ax2.hexbin(np.concatenate((zs_in, zs_out)), np.concatenate((bd_in, bd_out)),
           gridsize=100, mincnt=1, yscale="log",
           norm=LogNorm(), linewidths=0.2, cmap='Greys', alpha=0.4)

okinds1in = np.logical_and(mass_in > 10**8, mass_in <= 10**9)
okinds2in = np.logical_and(mass_in > 10**9, mass_in <= 10**9.5)
okinds3in = np.logical_and(mass_in > 10**9.5, mass_in <= 10**10)
okinds4in = mass_in > 10**10
okinds1out = np.logical_and(mass_out > 10**8, mass_out <= 10**9)
okinds2out = np.logical_and(mass_out > 10**9, mass_out <= 10**9.5)
okinds3out = np.logical_and(mass_out > 10**9.5, mass_out <= 10**10)
okinds4out = mass_out > 10**10

plot_meidan_stat(zs_out[okinds1out], bd_out[okinds1out],
                 ax2, lab="Out: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1, ls="dashed")

plot_meidan_stat(zs_out[okinds2out], bd_out[okinds2out],
                 ax2, lab="Out: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1, ls="dashed")

plot_meidan_stat(zs_out[okinds3out], bd_out[okinds3out],
                 ax2, lab="Out: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1, ls="dashed")

plot_meidan_stat(zs_out[okinds4out], bd_out[okinds4out],
                 ax2, lab="Out: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1, ls="dashed")

plot_meidan_stat(zs_in[okinds1in], bd_in[okinds1in],
                 ax2, lab="In: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1)

plot_meidan_stat(zs_in[okinds2in], bd_in[okinds2in],
                 ax2, lab="In: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1)

plot_meidan_stat(zs_in[okinds3in], bd_in[okinds3in],
                 ax2, lab="In: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1)

plot_meidan_stat(zs_in[okinds4in], bd_in[okinds4in],
                 ax2, lab="In: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1)

ax2.text(0.8, 0.9, "FLARES",
        bbox=dict(boxstyle="round,pad=0.3", fc='w', ec="k", lw=1, alpha=0.8),
        transform=ax2.transAxes, horizontalalignment='right', fontsize=8)

ax3.hexbin(np.concatenate((agndt9_zs_in, agndt9_zs_out)),
           np.concatenate((agndt9_bd_in, agndt9_bd_out)),
           gridsize=100, mincnt=1, yscale="log",
           norm=LogNorm(), linewidths=0.2, cmap='Greys', alpha=0.4)

okinds1in = np.logical_and(agndt9_mass_in > 10**8, agndt9_mass_in <= 10**9)
okinds2in = np.logical_and(agndt9_mass_in > 10**9, agndt9_mass_in <= 10**9.5)
okinds3in = np.logical_and(agndt9_mass_in > 10**9.5, agndt9_mass_in <= 10**10)
okinds4in = agndt9_mass_in > 10**10
okinds1out = np.logical_and(agndt9_mass_out > 10**8, agndt9_mass_out <= 10**9)
okinds2out = np.logical_and(agndt9_mass_out > 10**9, agndt9_mass_out <= 10**9.5)
okinds3out = np.logical_and(agndt9_mass_out > 10**9.5, agndt9_mass_out <= 10**10)
okinds4out = agndt9_mass_out > 10**10

plot_meidan_stat(agndt9_zs_out[okinds1out], agndt9_bd_out[okinds1out],
                 ax3, lab="Out: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1, ls="dashed")

plot_meidan_stat(agndt9_zs_out[okinds2out], agndt9_bd_out[okinds2out],
                 ax3, lab="Out: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1, ls="dashed")

plot_meidan_stat(agndt9_zs_out[okinds3out], agndt9_bd_out[okinds3out],
                 ax3, lab="Out: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1, ls="dashed")

plot_meidan_stat(agndt9_zs_out[okinds4out], agndt9_bd_out[okinds4out],
                 ax3, lab="Out: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1, ls="dashed")

plot_meidan_stat(agndt9_zs_in[okinds1in], agndt9_bd_in[okinds1in],
                 ax3, lab="In: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1)

plot_meidan_stat(agndt9_zs_in[okinds2in], agndt9_bd_in[okinds2in],
                 ax3, lab="In: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1)

plot_meidan_stat(agndt9_zs_in[okinds3in], agndt9_bd_in[okinds3in],
                 ax3, lab="In: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1)

plot_meidan_stat(agndt9_zs_in[okinds4in], agndt9_bd_in[okinds4in],
                 ax3, lab="In: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1)

ax3.text(0.8, 0.9, "AGNdT9",
        bbox=dict(boxstyle="round,pad=0.3", fc='w', ec="k", lw=1, alpha=0.8),
        transform=ax3.transAxes, horizontalalignment='right', fontsize=8)

ax4.hexbin(np.concatenate((ref_zs_in, ref_zs_out)),
           np.concatenate((ref_bd_in, ref_bd_out)),
           gridsize=100, mincnt=1, yscale="log",
           norm=LogNorm(), linewidths=0.2, cmap='Greys', alpha=0.4)

okinds1in = np.logical_and(ref_mass_in > 10**8, ref_mass_in <= 10**9)
okinds2in = np.logical_and(ref_mass_in > 10**9, ref_mass_in <= 10**9.5)
okinds3in = np.logical_and(ref_mass_in > 10**9.5, ref_mass_in <= 10**10)
okinds4in = ref_mass_in > 10**10
okinds1out = np.logical_and(ref_mass_out > 10**8, ref_mass_out <= 10**9)
okinds2out = np.logical_and(ref_mass_out > 10**9, ref_mass_out <= 10**9.5)
okinds3out = np.logical_and(ref_mass_out > 10**9.5, ref_mass_out <= 10**10)
okinds4out = ref_mass_out > 10**10

plot_meidan_stat(ref_zs_out[okinds1out], ref_bd_out[okinds1out],
                 ax4, lab="Out: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1, ls="dashed")

plot_meidan_stat(ref_zs_out[okinds2out], ref_bd_out[okinds2out],
                 ax4, lab="Out: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1, ls="dashed")

plot_meidan_stat(ref_zs_out[okinds3out], ref_bd_out[okinds3out],
                 ax4, lab="Out: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1, ls="dashed")

plot_meidan_stat(ref_zs_out[okinds4out], ref_bd_out[okinds4out],
                 ax4, lab="Out: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1, ls="dashed")

plot_meidan_stat(ref_zs_in[okinds1in], ref_bd_in[okinds1in],
                 ax4, lab="In: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1)

plot_meidan_stat(ref_zs_in[okinds2in], ref_bd_in[okinds2in],
                 ax4, lab="In: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1)

plot_meidan_stat(ref_zs_in[okinds3in], ref_bd_in[okinds3in],
                 ax4, lab="In: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1)

plot_meidan_stat(ref_zs_in[okinds4in], ref_bd_in[okinds4in],
                 ax4, lab="In: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1)

ax4.text(0.8, 0.9, "REFERENCE",
        bbox=dict(boxstyle="round,pad=0.3", fc='w', ec="k", lw=1, alpha=0.8),
        transform=ax4.transAxes, horizontalalignment='right', fontsize=8)

ax2.set_xlabel("$z$")
ax4.set_xlabel("$z$")
ax1.set_ylabel(r"$\rho_{\mathrm{birth}}$ / [cm$^{-3}$]")
ax2.set_ylabel(r"$\rho_{\mathrm{birth}}$ / [cm$^{-3}$]")

handles, labels = ax3.get_legend_handles_labels()
ax3.legend(handles, labels, fontsize=6)

for ax in [ax1, ax2, ax3, ax4]:
    ax.set_xlim(0, 35)
    ax.set_ylim(10**-2, 10**5.5)

# Remove axis labels
ax1.tick_params(axis='x', top=False, bottom=False, labeltop=False,
                labelbottom=False)
ax3.tick_params(axis='both', left=False, top=False, right=False,
                bottom=False,
                labelleft=False, labeltop=False,
                labelright=False, labelbottom=False)
ax4.tick_params(axis='y', left=False, right=False, labelleft=False,
                labelright=False)

fig.savefig("plots/aperture_bd_evolution_split_sim.png", bbox_inches="tight")

plt.close(fig)

fig = plt.figure(figsize=(8, 8))
gs = gridspec.GridSpec(nrows=2, ncols=2)
gs.update(wspace=0.0, hspace=0.0)
ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[1, 0])
ax3 = fig.add_subplot(gs[0, 1])
ax4 = fig.add_subplot(gs[1, 1])

okinds = met_all > 0

ax1.hexbin(zs_all[okinds], met_all[okinds], gridsize=100, mincnt=1, yscale="log",
           norm=LogNorm(), linewidths=0.2, cmap='Greys', alpha=0.4)

okinds1in = np.logical_and(mass_in_all > 10**8, mass_in_all <= 10**9)
okinds2in = np.logical_and(mass_in_all > 10**9, mass_in_all <= 10**9.5)
okinds3in = np.logical_and(mass_in_all > 10**9.5, mass_in_all <= 10**10)
okinds4in = mass_in_all > 10**10
okinds1out = np.logical_and(mass_out_all > 10**8, mass_out_all <= 10**9)
okinds2out = np.logical_and(mass_out_all > 10**9, mass_out_all <= 10**9.5)
okinds3out = np.logical_and(mass_out_all > 10**9.5, mass_out_all <= 10**10)
okinds4out = mass_out_all > 10**10

plot_meidan_stat(zs_out_all[okinds1out], met_out_all[okinds1out],
                 ax1, lab="Out: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1, ls="dashed")

plot_meidan_stat(zs_out_all[okinds2out], met_out_all[okinds2out],
                 ax1, lab="Out: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1, ls="dashed")

plot_meidan_stat(zs_out_all[okinds3out], met_out_all[okinds3out],
                 ax1, lab="Out: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1, ls="dashed")

plot_meidan_stat(zs_out_all[okinds4out], met_out_all[okinds4out],
                 ax1, lab="Out: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1, ls="dashed")

plot_meidan_stat(zs_in_all[okinds1in], met_in_all[okinds1in],
                 ax1, lab="In: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1)

plot_meidan_stat(zs_in_all[okinds2in], met_in_all[okinds2in],
                 ax1, lab="In: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1)

plot_meidan_stat(zs_in_all[okinds3in], met_in_all[okinds3in],
                 ax1, lab="In: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1)

plot_meidan_stat(zs_in_all[okinds4in], met_in_all[okinds4in],
                 ax1, lab="In: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1)

ax1.text(0.8, 0.9, "All",
        bbox=dict(boxstyle="round,pad=0.3", fc='w', ec="k", lw=1, alpha=0.8),
        transform=ax1.transAxes, horizontalalignment='right', fontsize=8)

flares_zs_all = np.concatenate((zs_in, zs_out))
flares_met_all = np.concatenate((met_in, met_out))

okinds = flares_met_all > 0

ax2.hexbin(flares_zs_all[okinds], flares_met_all[okinds],
           gridsize=100, mincnt=1, yscale="log",
           norm=LogNorm(), linewidths=0.2, cmap='Greys', alpha=0.4)

okinds1in = np.logical_and(mass_in > 10**8, mass_in <= 10**9)
okinds2in = np.logical_and(mass_in > 10**9, mass_in <= 10**9.5)
okinds3in = np.logical_and(mass_in > 10**9.5, mass_in <= 10**10)
okinds4in = mass_in > 10**10
okinds1out = np.logical_and(mass_out > 10**8, mass_out <= 10**9)
okinds2out = np.logical_and(mass_out > 10**9, mass_out <= 10**9.5)
okinds3out = np.logical_and(mass_out > 10**9.5, mass_out <= 10**10)
okinds4out = mass_out > 10**10

plot_meidan_stat(zs_out[okinds1out], met_out[okinds1out],
                 ax2, lab="Out: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1, ls="dashed")

plot_meidan_stat(zs_out[okinds2out], met_out[okinds2out],
                 ax2, lab="Out: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1, ls="dashed")

plot_meidan_stat(zs_out[okinds3out], met_out[okinds3out],
                 ax2, lab="Out: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1, ls="dashed")

plot_meidan_stat(zs_out[okinds4out], met_out[okinds4out],
                 ax2, lab="Out: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1, ls="dashed")

plot_meidan_stat(zs_in[okinds1in], met_in[okinds1in],
                 ax2, lab="In: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1)

plot_meidan_stat(zs_in[okinds2in], met_in[okinds2in],
                 ax2, lab="In: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1)

plot_meidan_stat(zs_in[okinds3in], met_in[okinds3in],
                 ax2, lab="In: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1)

plot_meidan_stat(zs_in[okinds4in], met_in[okinds4in],
                 ax2, lab="In: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1)

ax2.text(0.8, 0.9, "FLARES",
        bbox=dict(boxstyle="round,pad=0.3", fc='w', ec="k", lw=1, alpha=0.8),
        transform=ax2.transAxes, horizontalalignment='right', fontsize=8)

agndt9_zs_all = np.concatenate((agndt9_zs_in, agndt9_zs_out))
agndt9_met_all = np.concatenate((agndt9_met_in, agndt9_met_out))

okinds = agndt9_met_all > 0

ax3.hexbin(agndt9_zs_all[okinds],
           agndt9_met_all[okinds],
           gridsize=100, mincnt=1, yscale="log",
           norm=LogNorm(), linewidths=0.2, cmap='Greys', alpha=0.4)

okinds1in = np.logical_and(agndt9_mass_in > 10**8, agndt9_mass_in <= 10**9)
okinds2in = np.logical_and(agndt9_mass_in > 10**9, agndt9_mass_in <= 10**9.5)
okinds3in = np.logical_and(agndt9_mass_in > 10**9.5, agndt9_mass_in <= 10**10)
okinds4in = agndt9_mass_in > 10**10
okinds1out = np.logical_and(agndt9_mass_out > 10**8, agndt9_mass_out <= 10**9)
okinds2out = np.logical_and(agndt9_mass_out > 10**9, agndt9_mass_out <= 10**9.5)
okinds3out = np.logical_and(agndt9_mass_out > 10**9.5, agndt9_mass_out <= 10**10)
okinds4out = agndt9_mass_out > 10**10

plot_meidan_stat(agndt9_zs_out[okinds1out], agndt9_met_out[okinds1out],
                 ax3, lab="Out: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1, ls="dashed")

plot_meidan_stat(agndt9_zs_out[okinds2out], agndt9_met_out[okinds2out],
                 ax3, lab="Out: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1, ls="dashed")

plot_meidan_stat(agndt9_zs_out[okinds3out], agndt9_met_out[okinds3out],
                 ax3, lab="Out: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1, ls="dashed")

plot_meidan_stat(agndt9_zs_out[okinds4out], agndt9_met_out[okinds4out],
                 ax3, lab="Out: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1, ls="dashed")

plot_meidan_stat(agndt9_zs_in[okinds1in], agndt9_met_in[okinds1in],
                 ax3, lab="In: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1)

plot_meidan_stat(agndt9_zs_in[okinds2in], agndt9_met_in[okinds2in],
                 ax3, lab="In: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1)

plot_meidan_stat(agndt9_zs_in[okinds3in], agndt9_met_in[okinds3in],
                 ax3, lab="In: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1)

plot_meidan_stat(agndt9_zs_in[okinds4in], agndt9_met_in[okinds4in],
                 ax3, lab="In: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1)

ax3.text(0.8, 0.9, "AGNdT9",
        bbox=dict(boxstyle="round,pad=0.3", fc='w', ec="k", lw=1, alpha=0.8),
        transform=ax3.transAxes, horizontalalignment='right', fontsize=8)

ref_zs_all = np.concatenate((ref_zs_in, ref_zs_out))
ref_met_all = np.concatenate((ref_met_in, ref_met_out))

okinds = ref_met_all > 0

ax4.hexbin(ref_zs_all[okinds],
           ref_met_all[okinds],
           gridsize=100, mincnt=1, yscale="log",
           norm=LogNorm(), linewidths=0.2, cmap='Greys', alpha=0.4)

okinds1in = np.logical_and(ref_mass_in > 10**8, ref_mass_in <= 10**9)
okinds2in = np.logical_and(ref_mass_in > 10**9, ref_mass_in <= 10**9.5)
okinds3in = np.logical_and(ref_mass_in > 10**9.5, ref_mass_in <= 10**10)
okinds4in = ref_mass_in > 10**10
okinds1out = np.logical_and(ref_mass_out > 10**8, ref_mass_out <= 10**9)
okinds2out = np.logical_and(ref_mass_out > 10**9, ref_mass_out <= 10**9.5)
okinds3out = np.logical_and(ref_mass_out > 10**9.5, ref_mass_out <= 10**10)
okinds4out = ref_mass_out > 10**10

plot_meidan_stat(ref_zs_out[okinds1out], ref_met_out[okinds1out],
                 ax4, lab="Out: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1, ls="dashed")

plot_meidan_stat(ref_zs_out[okinds2out], ref_met_out[okinds2out],
                 ax4, lab="Out: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1, ls="dashed")

plot_meidan_stat(ref_zs_out[okinds3out], ref_met_out[okinds3out],
                 ax4, lab="Out: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1, ls="dashed")

plot_meidan_stat(ref_zs_out[okinds4out], ref_met_out[okinds4out],
                 ax4, lab="Out: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1, ls="dashed")

plot_meidan_stat(ref_zs_in[okinds1in], ref_met_in[okinds1in],
                 ax4, lab="In: $10^8 < M/M_\odot \leq 10^9$",
                 color='darkorange', bins=1)

plot_meidan_stat(ref_zs_in[okinds2in], ref_met_in[okinds2in],
                 ax4, lab="In: $10^9 < M/M_\odot \leq 10^{9.5}$",
                 color='royalblue', bins=1)

plot_meidan_stat(ref_zs_in[okinds3in], ref_met_in[okinds3in],
                 ax4, lab="In: $10^{9.5} < M/M_\odot \leq 10^{10}$",
                 color='limegreen', bins=1)

plot_meidan_stat(ref_zs_in[okinds4in], ref_met_in[okinds4in],
                 ax4, lab="In: $10^{10} < M/M_\odot$",
                 color='magenta', bins=1)

ax4.text(0.8, 0.9, "REFERENCE",
        bbox=dict(boxstyle="round,pad=0.3", fc='w', ec="k", lw=1, alpha=0.8),
        transform=ax4.transAxes, horizontalalignment='right', fontsize=8)

ax2.set_xlabel("$z$")
ax4.set_xlabel("$z$")
ax1.set_ylabel(r"$Z$")
ax2.set_ylabel(r"$Z$")

handles, labels = ax3.get_legend_handles_labels()
ax3.legend(handles, labels, fontsize=6)

for ax in [ax1, ax2, ax3, ax4]:
    ax.set_xlim(0, 35)
    ax.set_ylim(10**-6, 10**-0.5)

# Remove axis labels
ax1.tick_params(axis='x', top=False, bottom=False, labeltop=False,
                labelbottom=False)
ax3.tick_params(axis='both', left=False, top=False, right=False, bottom=False,
                labelleft=False, labeltop=False,
                labelright=False, labelbottom=False)
ax4.tick_params(axis='y', left=False, right=False, labelleft=False,
                labelright=False)

fig.savefig("plots/aperture_met_evolution_split_sim.png", bbox_inches="tight")

plt.close(fig)

