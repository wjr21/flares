#!/cosma/home/dp004/dc-rope1/.conda/envs/flares-env/bin/python
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import matplotlib
import astropy.units as u
import astropy.constants as cons
from astropy.cosmology import Planck13 as cosmo
from matplotlib.colors import LogNorm
import eagle_IO.eagle_IO as E
import seaborn as sns
import h5py
matplotlib.use('Agg')


def calc_srf(z, a_born, mass, t_bin=100):

    # Convert scale factor into redshift
    z_born = 1 / a_born - 1

    # Convert to time in Gyrs
    t = cosmo.age(z)
    t_born = cosmo.age(z_born)

    # Calculate the VR
    age = (t - t_born).to(u.Myr)

    ok = np.where(age.value <= t_bin)[0]
    if len(ok) > 0:

        # Calculate the SFR
        sfr = np.sum(mass[ok]) / (t_bin * 1e6)

    else:
        sfr = 0.0

    return sfr


def get_part_inds(halo_ids, part_ids, group_part_ids, sorted):
    """ A function to find the indexes and halo IDs associated to particles/a particle producing an array for each

    :param halo_ids:
    :param part_ids:
    :param group_part_ids:
    :return:
    """

    # Sort particle IDs if required and store an unsorted version in an array
    if sorted:
        part_ids = np.sort(part_ids)
    unsort_part_ids = np.copy(part_ids)

    # Get the indices that would sort the array (if the array is sorted this is just a range form 0-Npart)
    if sorted:
        sinds = np.arange(part_ids.size)
    else:
        sinds = np.argsort(part_ids)
        part_ids = part_ids[sinds]

    # Get the index of particles in the snapshot array from the in particles in a group array
    sorted_index = np.searchsorted(part_ids, group_part_ids)  # find the indices that would sort the array
    yindex = np.take(sinds, sorted_index, mode="raise")  # take the indices at the indices found above
    mask = unsort_part_ids[yindex] != group_part_ids  # define the mask based on these particles
    result = np.ma.array(yindex, mask=mask)  # create a mask array

    # Apply the mask to the id arrays to get halo ids and the particle indices
    part_groups = halo_ids[np.logical_not(result.mask)]  # halo ids
    parts_in_groups = result.data[np.logical_not(result.mask)]  # particle indices

    return parts_in_groups, part_groups


lim = 40 / 1000
soft = 0.001802390 / 0.6777 / 4
scale = 10 / 1000

# Define resolution
res = int(np.floor(2 * lim / soft))

regions = []
for reg in range(3, 5):

    if reg < 10:
        regions.append('0' + str(reg))
    else:
        regions.append(str(reg))

snaps = ['000_z015p000', '001_z014p000', '002_z013p000', '003_z012p000', '004_z011p000', '005_z010p000',
         '006_z009p000', '007_z008p000', '008_z007p000', '009_z006p000', '010_z005p000', '011_z004p770']

# Define galaxy thresholds
ssfr_thresh = 0.1

star_img = np.zeros((res, res))
gas_img = np.zeros((res, res))

for reg in regions:

    for snap in snaps:

        print(reg, snap)

        z_str = snap.split('z')[1].split('p')
        z = float(z_str[0] + '.' + z_str[1])

        path = '/cosma/home/dp004/dc-rope1/FLARES/FLARES-1/G-EAGLE_' + reg + '/data'

        try:
            masses = E.read_array('PARTDATA', path, snap, 'PartType4/InitialMass', noH=True, numThreads=8) * 10**10
            form_t = E.read_array('PARTDATA', path, snap, 'PartType4/StellarFormationTime', noH=True, numThreads=8)
            part_ids = E.read_array('PARTDATA', path, snap, 'PartType4/ParticleIDs', numThreads=8)
            grp_ids = E.read_array('PARTDATA', path, snap, 'PartType4/GroupNumber', numThreads=8)
            subgrp_ids = E.read_array('PARTDATA', path, snap, 'PartType4/SubGroupNumber', numThreads=8)
            subfind_grp_ids = E.read_array('SUBFIND', path, snap, 'Subhalo/GroupNumber', numThreads=8)
            subfind_subgrp_ids = E.read_array('SUBFIND', path, snap, 'Subhalo/SubGroupNumber', numThreads=8)
            gal_cops = E.read_array('SUBFIND', path, snap, 'Subhalo/CentreOfPotential',
                                  numThreads=8) / 0.6777
            gal_appms = E.read_array('SUBFIND', path, snap, 'Subhalo/ApertureMeasurements/Mass/030kpc',
                                     numThreads=8)[:, 4] * 10**10

        except:
            continue

        # A copy of this array is needed for the extraction method
        group_part_ids = np.copy(part_ids)

        # Convert IDs to float(groupNumber.SubGroupNumber) format, i.e. group 1 subgroup 11 = 1.00011
        halo_ids = np.zeros(subfind_grp_ids.size, dtype=float)
        for (ind, g), sg in zip(enumerate(subfind_grp_ids), subfind_subgrp_ids):
            halo_ids[ind] = float(str(int(g)) + '.%05d' % int(sg))

        okinds = gal_appms > 1e9
        halo_ids = halo_ids[okinds]
        gal_cops = gal_cops[okinds]
        gal_appms = gal_appms[okinds]

        # Convert IDs to float(groupNumber.SubGroupNumber) format, i.e. group 1 subgroup 11 = 1.00011
        part_halo_ids = np.zeros(grp_ids.size, dtype=float)
        for (ind, g), sg in zip(enumerate(grp_ids), subgrp_ids):
            part_halo_ids[ind] = float(str(int(g)) + '.%05d' % int(sg))

        okinds = np.isin(part_halo_ids, halo_ids)
        part_halo_ids = part_halo_ids[okinds]
        part_ids = part_ids[okinds]
        group_part_ids = group_part_ids[okinds]
        masses = masses[okinds]
        form_t = form_t[okinds]

        print("There are", len(part_halo_ids), "particles")

        print("Got halo IDs")

        parts_in_groups, part_groups = get_part_inds(part_halo_ids, part_ids, group_part_ids, False)

        # Produce a dictionary containing the index of particles in each halo
        halo_part_inds = {}
        for ind, grp in zip(parts_in_groups, part_groups):
            halo_part_inds.setdefault(grp, set()).update({ind})

        # Now the dictionary is fully populated convert values from sets to arrays for indexing
        for key, val in halo_part_inds.items():
            halo_part_inds[key] = np.array(list(val))

        cops = []
        for key, cop, m in zip(halo_ids, gal_cops, gal_appms):
            parts = halo_part_inds[key]
            sfr = calc_srf(z, form_t[parts], masses[parts])
            grp_ssfr = sfr / m
            if grp_ssfr < ssfr_thresh and grp_ssfr != 0:
                cops.append(cop)

        print("There are", len(cops), "passive galaxies in", reg, snap)

        if len(cops) > 0:
            try:

                star_poss = E.read_array('PARTDATA', path, snap, 'PartType4/Coordinates', numThreads=8) / 0.6777
                gas_poss = E.read_array('PARTDATA', path, snap, 'PartType0/Coordinates', numThreads=8) / 0.6777
                stellar_masses = E.read_array('PARTDATA', path, snap, 'PartType4/Mass', numThreads=8) * 10 ** 10 / 0.6777
                gas_masses = E.read_array('PARTDATA', path, snap, 'PartType0/Mass', numThreads=8) * 10 ** 10 / 0.6777

            except ValueError:
                continue
            except OSError:
                continue

        for cop in cops:

            # Get only stars within the aperture
            star_okinds = np.logical_and(np.abs(star_poss[:, 0] - cop[0]) < lim,
                                         np.logical_and(np.abs(star_poss[:, 1] - cop[1]) < lim,
                                                        np.abs(star_poss[:, 2] - cop[2]) < lim))
            gas_okinds = np.logical_and(np.abs(gas_poss[:, 0] - cop[0]) < lim,
                                        np.logical_and(np.abs(gas_poss[:, 1] - cop[1]) < lim,
                                                       np.abs(gas_poss[:, 2] - cop[2]) < lim))
            this_star_poss = star_poss[star_okinds, :] - cop
            this_gas_poss = gas_poss[gas_okinds, :] - cop
            this_star_ms = stellar_masses[star_okinds]
            this_gas_ms = gas_masses[gas_okinds]

            # Histogram positions into images
            Hstar, _, _ = np.histogram2d(this_star_poss[:, 0], this_star_poss[:, 1], bins=res, range=((-lim, lim), (-lim, lim)),
                                         weights=this_star_ms)
            Hgas, _, _ = np.histogram2d(this_gas_poss[:, 0], this_gas_poss[:, 1], bins=res, range=((-lim, lim), (-lim, lim)),
                                        weights=this_gas_ms)

            star_img += Hstar
            gas_img += Hgas

fig = plt.figure()
ax1 = fig.add_subplot(131)
ax2 = fig.add_subplot(132)
ax3 = fig.add_subplot(133)

ax1.imshow(np.zeros_like(star_img), cmap='magma', extent=(-lim, lim, -lim, lim))
ax2.imshow(np.zeros_like(star_img), cmap='magma', extent=(-lim, lim, -lim, lim))
ax3.imshow(np.zeros_like(star_img), cmap='magma', extent=(-lim, lim, -lim, lim))

im1 = ax1.imshow(np.log10(star_img), cmap='magma', extent=(-lim, lim, -lim, lim))
im2 = ax2.imshow(np.log10(gas_img), cmap='magma', extent=(-lim, lim, -lim, lim))
ax3.imshow(np.log10(gas_img), cmap='magma', extent=(-lim, lim, -lim, lim), alpha=0.8)
ax3.imshow(np.log10(star_img), cmap='Greys_r', extent=(-lim, lim, -lim, lim), alpha=0.5)

app1 = plt.Circle((0., 0.), 0.03, facecolor='none', edgecolor='r', linestyle='-')
app2 = plt.Circle((0., 0.), 0.03, facecolor='none', edgecolor='r', linestyle='-')
app3 = plt.Circle((0., 0.), 0.03, facecolor='none', edgecolor='r', linestyle='-')

ax1.add_artist(app1)
ax2.add_artist(app2)
ax3.add_artist(app3)

ax1.set_title("Stellar")
ax2.set_title("Gas")
ax3.set_title("Gas + Stellar")

# Remove ticks
ax1.tick_params(axis='both', left=False, top=False, right=False, bottom=False, labelleft=False,
                labeltop=False, labelright=False, labelbottom=False)
ax2.tick_params(axis='both', left=False, top=False, right=False, bottom=False, labelleft=False,
                labeltop=False, labelright=False, labelbottom=False)
ax3.tick_params(axis='both', left=False, top=False, right=False, bottom=False, labelleft=False,
                labeltop=False, labelright=False, labelbottom=False)

# Draw scale line
right_side = lim - (lim * 0.1)
vert = lim - (lim * 0.175)
lab_vert = vert + (lim * 0.1) * 5 / 8
lab_horz = right_side - scale / 2
ax1.plot([right_side - scale, right_side], [vert, vert], color='w', linewidth=0.5)
ax2.plot([right_side - scale, right_side], [vert, vert], color='w', linewidth=0.5)
ax3.plot([right_side - scale, right_side], [vert, vert], color='w', linewidth=0.5)

# Label scale
ax1.text(lab_horz, lab_vert, str(int(scale*1e3)) + ' ckpc', horizontalalignment='center',
         fontsize=4, color='w')
ax2.text(lab_horz, lab_vert, str(int(scale*1e3)) + ' ckpc', horizontalalignment='center',
         fontsize=4, color='w')
ax3.text(lab_horz, lab_vert, str(int(scale*1e3)) + ' ckpc', horizontalalignment='center',
         fontsize=4, color='w')

# Add colorbars
cax1 = inset_axes(ax1, width="50%", height="3%", loc='lower left')
cax2 = inset_axes(ax2, width="50%", height="3%", loc='lower left')
cbar1 = fig.colorbar(im1, cax=cax1, orientation="horizontal")
cbar2 = fig.colorbar(im2, cax=cax2, orientation="horizontal")

# Label colorbars
cbar1.ax.set_xlabel(r'$\log_{10}(M_{\star}/M_{\odot})$', fontsize=3, color='w', labelpad=1.0)
cbar1.ax.xaxis.set_label_position('top')
cbar1.outline.set_edgecolor('w')
cbar1.outline.set_linewidth(0.05)
cbar1.ax.tick_params(axis='x', length=1, width=0.2, pad=0.01, labelsize=2, color='w', labelcolor='w')
cbar2.ax.set_xlabel(r'$\log_{10}(M_{\mathrm{gas}}/M_{\odot})$', fontsize=3, color='w',
                    labelpad=1.0)
cbar2.ax.xaxis.set_label_position('top')
cbar2.outline.set_edgecolor('w')
cbar2.outline.set_linewidth(0.05)
cbar2.ax.tick_params(axis='x', length=1, width=0.2, pad=0.01, labelsize=2, color='w', labelcolor='w')

fig.savefig("plots/passive_stack.png", bbox_inches='tight', dpi=300)
