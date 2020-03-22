#!/cosma/home/dp004/dc-rope1/.conda/envs/flares-env/bin/python
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib
import astropy.units as u
import eagle_IO as E
from astropy.cosmology import Planck13 as cosmo
from numba import njit
import pickle
import os
os.environ['FLARE'] = '/cosma7/data/dp004/dc-wilk2/flare'
import FLARE.filters
from SynthObs.SED import models
matplotlib.use('Agg')


# Define SED model
model = models.define_model('BPASSv2.2.1.binary/ModSalpeter_300',
                            path_to_SPS_grid = FLARE.FLARE_dir + '/data/SPS/nebular/3.0/') # DEFINE SED GRID -
model.dust_ISM = ('simple', {'slope': -1.0})
model.dust_BC = ('simple', {'slope': -1.0})

# Define the filters: FAKE.FAKE are just top-hat filters using for extracting rest-frame quantities.
filters = ['FAKE.TH.'+f for f in ['FUV','NUV','V']]
F = FLARE.filters.add_filters(filters, new_lam = model.lam)

# --- create new L grid for each filter. In units of erg/s/Hz
model.create_Lnu_grid(F)


def calc_ages(z, a_born):

    # Convert scale factor into redshift
    z_born = 1 / a_born - 1

    # Convert to time in Gyrs
    t = cosmo.age(z)
    t_born = cosmo.age(z_born)

    # Calculate the VR
    ages = (t - t_born).to(u.Myr)

    return ages.value


@njit(nogil=True)
def get_Z_LOS(s_cood, g_cood, g_mass, g_Z, g_sml, dimens, lkernel, kbins, conv):

    """

    Compute the los metal surface density (in g/cm^2) for star particles inside the galaxy taking
    the z-axis as the los.
    Args:
        s_cood (3d array): stellar particle coordinates
        g_cood (3d array): gas particle coordinates
        g_mass (1d array): gas particle mass
        g_Z (1d array): gas particle metallicity
        g_sml (1d array): gas particle smoothing length

    """
    n = s_cood.shape[0]
    Z_los_SD = np.zeros(n)
    #Fixing the observer direction as z-axis. Use make_faceon() for changing the
    #particle orientation to face-on
    xdir, ydir, zdir = dimens
    for ii in range(n):

        thisspos = s_cood[ii, :]
        ok = (g_cood[:,zdir] > thisspos[zdir])
        thisgpos = g_cood[ok]
        thisgsml = g_sml[ok]
        thisgZ = g_Z[ok]
        thisgmass = g_mass[ok]
        x = thisgpos[:,xdir] - thisspos[xdir]
        y = thisgpos[:,ydir] - thisspos[ydir]

        b = np.sqrt(x*x + y*y)
        boverh = b/thisgsml

        ok = (boverh <= 1.)

        kernel_vals = np.array([lkernel[int(kbins*ll)] for ll in boverh[ok]])

        Z_los_SD[ii] = np.sum((thisgmass[ok]*thisgZ[ok]/(thisgsml[ok]*thisgsml[ok]))*kernel_vals) #in units of Msun/Mpc^2

    Z_los_SD *= conv  # in units of Msun/pc^2

    return Z_los_SD


def create_img(res, gal_poss, mean, dim, gal_ms, gal_ages, gal_mets, gas_mets, gas_poss, gas_ms, gas_sml,
               lkernel, kbins, conv):

    # Set up dictionaries to store images
    galimgs = {}
    extents = {}

    for (i, j) in [(0, 1), (0, 2), (1, 2)]:

        # Define dimensions array
        if i == 0 and j == 1:
            k = 2
        elif i == 0 and j == 2:
            k = 1
        else:
            k = 0
        dimens = np.array([i, j, k])

        gal_met_surfden = get_Z_LOS(gal_poss, gas_poss, gas_ms, gas_mets, gas_sml, dimens, lkernel, kbins, conv)

        galimgs[str(i) + '-' + str(j)] = {}

        for f in ['mass', 'FAKE.TH.V', 'FAKE.TH.NUV', 'FAKE.TH.FUV', 'metals']:

            print((i, j), f)

            # Compute luminosities
            if f == 'mass':
                lumins = gal_ms
            elif f == 'metals':
                lumins = gal_met_surfden
            else:
                tauVs_ISM = (10 ** 5.2) * gal_met_surfden
                tauVs_BC = 2.0 * (gal_mets / 0.01)
                lumins = models.generate_Lnu_array(model, gal_ms, gal_ages, gal_mets, tauVs_ISM, tauVs_BC, F,
                                                   f=f, fesc=0.0)

            # Compute extent for the 2D square image
            extents[str(i) + '-' + str(j)] = [-dim, dim, -dim, dim]
            posrange = ((-dim, dim), (-dim, dim))

            # Create images
            galimgs[str(i) + '-' + str(j)][f], gxbins, gybins = np.histogram2d(gal_poss[:, i] - mean[i],
                                                                               gal_poss[:, j] - mean[j],
                                                                               bins=int(dim / res), weights=lumins,
                                                                               range=posrange)

    return galimgs, extents


def img_main(path, snap, reg, res, npart_lim=10**3, dim=0.1, load=True, conv=1, scale=0.01):

    # Get the redshift
    z_str = snap.split('z')[1].split('p')
    z = float(z_str[0] + '.' + z_str[1])

    # Define stellar particle type
    part_type = 4

    kinp = np.load('/cosma/home/dp004/dc-rope1/cosma7/FLARES/flares/los_extinction/kernel_sph-anarchy.npz',
                   allow_pickle=True)
    lkernel = kinp['kernel']
    header = kinp['header']
    kbins = header.item()['bins']

    if load:

        with open('UVimg_data/stellardata_reg' + reg + '_snap'
                  + snap + '_npartgreaterthan' + str(npart_lim) + '.pck', 'rb') as pfile1:
            save_dict = pickle.load(pfile1)

        gal_ages = save_dict['gal_ages']
        gal_mets = save_dict['gal_mets']
        gal_ms = save_dict['gal_ms']
        gas_mets = save_dict['gas_mets']
        gas_ms = save_dict['gas_ms']
        gas_smls = save_dict['gas_smls']
        all_gas_poss = save_dict['all_gas_poss']
        all_gal_poss = save_dict['all_gal_poss']
        means = save_dict['means']

    else:

        # Initialise galaxy position dictionaries
        all_gal_poss = {}
        means = {}

        # Load all necessary arrays
        subgrp_ids = E.read_array('PARTDATA', path, snap, 'PartType' + str(part_type) + '/SubGroupNumber', numThreads=8)
        all_poss = E.read_array('SNAP', path, snap, 'PartType' + str(part_type) + '/Coordinates', noH=True, numThreads=8)
        part_ids = E.read_array('SNAP', path, snap, 'PartType' + str(part_type) + '/ParticleIDs', numThreads=8)
        group_part_ids = E.read_array('PARTDATA', path, snap, 'PartType' + str(part_type) + '/ParticleIDs', numThreads=8)
        grp_ids = E.read_array('PARTDATA', path, snap, 'PartType' + str(part_type) + '/GroupNumber', numThreads=8)
        gal_ids = E.read_array('SUBFIND', path, snap, 'Subhalo/SubGroupNumber', numThreads=8)
        gal_gids = E.read_array('SUBFIND', path, snap, 'Subhalo/GroupNumber', numThreads=8)
        gal_cops = E.read_array('SUBFIND', path, snap, 'Subhalo/CentreOfPotential', noH=True, numThreads=8)
        halo_ids = np.zeros_like(grp_ids, dtype=float)
        for (ind, g), sg in zip(enumerate(grp_ids), subgrp_ids):
            halo_ids[ind] = float(str(g) + '.' + str(sg + 1))

        # Get centre of potentials
        gal_cop = {}
        for cop, g, sg in zip(gal_cops, gal_gids, gal_ids):
            gal_cop[float(str(g) + '.' + str(sg + 1))] = cop

        # Translate ID into indices
        ind_to_pid = {}
        pid_to_ind = {}
        for ind, pid in enumerate(part_ids):
            ind_to_pid[ind] = pid
            pid_to_ind[pid] = ind

        # Get the IDs above the npart threshold
        ids, counts = np.unique(halo_ids, return_counts=True)
        ids = set(ids[counts > npart_lim])

        # Get the particles in the halos
        halo_id_part_inds = {}
        for pid, simid in zip(group_part_ids, halo_ids):
            if simid not in ids:
                continue
            if int(str(simid).split('.')[1]) == 2**30:
                continue
            try:
                halo_id_part_inds.setdefault(simid, set()).update({pid_to_ind[pid]})
            except KeyError:
                ind_to_pid[len(part_ids) + 1] = pid
                pid_to_ind[pid] = len(part_ids) + 1
                halo_id_part_inds.setdefault(simid, set()).update({pid_to_ind[pid]})

        print('There are', len(ids), 'galaxies above the cutoff')

        # If there are no galaxies exit
        if len(ids) == 0:
            return

        # Load data for luminosities
        a_born = E.read_array('SNAP', path, snap, 'PartType4/StellarFormationTime', noH=True, numThreads=8)
        metallicities = E.read_array('SNAP', path, snap, 'PartType4/SmoothedMetallicity', noH=True, numThreads=8)
        masses = E.read_array('SNAP', path, snap, 'PartType4/Mass', noH=True, numThreads=8) * 10**10

        # Get gas particle information
        gsubgrp_ids = E.read_array('PARTDATA', path, snap, 'PartType0/SubGroupNumber', numThreads=8)
        gas_all_poss = E.read_array('SNAP', path, snap, 'PartType0/Coordinates', noH=True, numThreads=8)
        gpart_ids = E.read_array('SNAP', path, snap, 'PartType0/ParticleIDs', numThreads=8)
        ggroup_part_ids = E.read_array('PARTDATA', path, snap, 'PartType0/ParticleIDs', numThreads=8)
        ggrp_ids = E.read_array('PARTDATA', path, snap, 'PartType0/GroupNumber', numThreads=8)
        gas_metallicities = E.read_array('SNAP', path, snap, 'PartType0/SmoothedMetallicity', noH=True, numThreads=8)
        gas_smooth_ls = E.read_array('SNAP', path, snap, 'PartType0/SmoothingLength', noH=True, numThreads=8)
        gas_masses = E.read_array('SNAP', path, snap, 'PartType0/Mass', noH=True, numThreads=8) * 10**10
        ghalo_ids = np.zeros_like(ggrp_ids, dtype=float)
        for (ind, g), sg in zip(enumerate(ggrp_ids), gsubgrp_ids):
            ghalo_ids[ind] = float(str(g) + '.' + str(sg + 1))

        # Translate ID into indices
        gind_to_pid = {}
        gpid_to_ind = {}
        for ind, pid in enumerate(gpart_ids):
            gind_to_pid[ind] = pid
            gpid_to_ind[pid] = ind

        # Get the particles in the halos
        ghalo_id_part_inds = {}
        for pid, simid in zip(ggroup_part_ids, ghalo_ids):
            if simid not in ids:
                continue
            if int(str(simid).split('.')[1]) == 2**30:
                continue
            try:
                ghalo_id_part_inds.setdefault(simid, set()).update({gpid_to_ind[pid]})
            except KeyError:
                gind_to_pid[len(gpart_ids) + 1] = pid
                gpid_to_ind[pid] = len(gpart_ids) + 1
                ghalo_id_part_inds.setdefault(simid, set()).update({gpid_to_ind[pid]})

        # Calculate ages
        ages = calc_ages(z, a_born)

        # Get the position of each of these galaxies
        gal_ages = {}
        gal_mets = {}
        gal_ms = {}
        gas_mets = {}
        gas_ms = {}
        gas_smls = {}
        all_gas_poss = {}
        for id in ids:

            all_gal_poss[id] = all_poss[list(halo_id_part_inds[id]), :]
            all_gas_poss[id] = gas_all_poss[list(ghalo_id_part_inds[id]), :]
            gal_ages[id] = ages[list(halo_id_part_inds[id])]
            gal_mets[id] = metallicities[list(halo_id_part_inds[id])]
            gal_ms[id] = masses[list(halo_id_part_inds[id])]
            gas_mets[id] = gas_metallicities[list(ghalo_id_part_inds[id])]
            gas_ms[id] = gas_masses[list(ghalo_id_part_inds[id])]
            gas_smls[id] = gas_smooth_ls[list(ghalo_id_part_inds[id])]

            means[id] = all_gal_poss[id].mean(axis=0)

        save_dict = {'gal_ages': gal_ages, 'gal_mets': gal_mets, 'gal_ms': gal_ms, 'gas_mets': gas_mets,
                     'gas_ms': gas_ms, 'gas_smls': gas_smls, 'all_gas_poss': all_gas_poss,
                     'all_gal_poss': all_gal_poss, 'means': means}

        with open('UVimg_data/stellardata_reg' + reg + '_snap'
                  + snap + '_npartgreaterthan' + str(npart_lim) + '.pck', 'wb') as pfile1:
            pickle.dump(save_dict, pfile1)

    print('Extracted galaxy positions')

    axlabels = [r'$x$', r'$y$', r'$z$']

    # Create images for these galaxies
    for id in gal_ages.keys():

        print('Computing images for', id)

        # Get the images
        galimgs, extents = create_img(res, all_gal_poss[id], means[id], dim, gal_ms[id], gal_ages[id], gal_mets[id],
                                      gas_mets[id], all_gas_poss[id], gas_ms[id], gas_smls[id], lkernel, kbins, conv)

        # Loop over dimensions
        for key in galimgs.keys():

            i, j = key.split('-')

            # Set up figure
            widths = [1, 1, 1, 1, 1]
            heights = [10, 1]
            fig = plt.figure()
            gs = gridspec.GridSpec(2, 5, width_ratios=widths, height_ratios=heights)
            gs.update(wspace=0.0, hspace=0.0)
            gsc = gridspec.GridSpec(2, 5, width_ratios=widths, height_ratios=heights)
            gsc.update(wspace=0.1, hspace=0.0)
            cax1 = fig.add_subplot(gsc[0, 0])
            cax2 = fig.add_subplot(gsc[0, 1])
            cax3 = fig.add_subplot(gsc[0, 2])
            cax4 = fig.add_subplot(gsc[0, 3])
            cax5 = fig.add_subplot(gsc[0, 4])
            ax1 = fig.add_subplot(gs[1, 0])
            ax2 = fig.add_subplot(gs[1, 1])
            ax3 = fig.add_subplot(gs[1, 2])
            ax4 = fig.add_subplot(gs[1, 3])
            ax5 = fig.add_subplot(gs[1, 4])

            # Draw images
            im1 = ax1.imshow(np.arcsinh(galimgs[key]['mass']), extent=extents[key], cmap='Greys_r')
            im2 = ax2.imshow(np.arcsinh(galimgs[key]['metals']), extent=extents[key], cmap='Greys_r')
            im3 = ax3.imshow(np.arcsinh(galimgs[key]['FAKE.TH.V']), extent=extents[key], cmap='Greys_r')
            im4 = ax4.imshow(np.arcsinh(galimgs[key]['FAKE.TH.NUV']), extent=extents[key], cmap='Greys_r')
            im5 = ax5.imshow(np.arcsinh(galimgs[key]['FAKE.TH.FUV']), extent=extents[key], cmap='Greys_r')

            # Draw scale line
            right_side = dim - (dim * 0.1)
            vert = - dim + (dim * 0.1)
            lab_vert = vert + (dim * 0.1) / 2
            lab_horz = right_side - scale / 2
            ax1.plot([right_side - scale, right_side], [vert, vert], color='w')
            ax2.plot([right_side - scale, right_side], [vert, vert], color='w')
            ax3.plot([right_side - scale, right_side], [vert, vert], color='w')
            ax4.plot([right_side - scale, right_side], [vert, vert], color='w')
            ax5.plot([right_side - scale, right_side], [vert, vert], color='w')

            # Label scale
            ax1.text(lab_horz, lab_vert, str(scale) + ' kpc', horizontalalignment='center', fontsize=4, color='w')
            ax2.text(lab_horz, lab_vert, str(scale) + ' kpc', horizontalalignment='center', fontsize=4, color='w')
            ax3.text(lab_horz, lab_vert, str(scale) + ' kpc', horizontalalignment='center', fontsize=4, color='w')
            ax4.text(lab_horz, lab_vert, str(scale) + ' kpc', horizontalalignment='center', fontsize=4, color='w')
            ax5.text(lab_horz, lab_vert, str(scale) + ' kpc', horizontalalignment='center', fontsize=4, color='w')

            # # Draw text
            # ax1.text(0.8, 0.9, 'Mass', bbox=dict(boxstyle="round,pad=0.3", fc='w', ec="k", lw=1, alpha=0.8),
            #         transform=ax1.transAxes, horizontalalignment='right', fontsize=4)
            # ax2.text(0.8, 0.9, 'LOS Metals', bbox=dict(boxstyle="round,pad=0.3", fc='w', ec="k", lw=1, alpha=0.8),
            #         transform=ax2.transAxes, horizontalalignment='right', fontsize=4)
            # ax3.text(0.8, 0.9, 'FAKE.TH.V', bbox=dict(boxstyle="round,pad=0.3", fc='w', ec="k", lw=1, alpha=0.8),
            #         transform=ax3.transAxes, horizontalalignment='right', fontsize=4)
            # ax4.text(0.8, 0.9, 'FAKE.TH.NUV', bbox=dict(boxstyle="round,pad=0.3", fc='w', ec="k", lw=1, alpha=0.8),
            #         transform=ax4.transAxes, horizontalalignment='right', fontsize=4)
            # ax5.text(0.8, 0.9, 'FAKE.TH.FUV', bbox=dict(boxstyle="round,pad=0.3", fc='w', ec="k", lw=1, alpha=0.8),
            #         transform=ax5.transAxes, horizontalalignment='right', fontsize=4)

            # Remove ticks
            ax1.tick_params(axis='both', left=False, top=False, right=False, bottom=False, labelleft=False,
                            labeltop=False, labelright=False, labelbottom=False)
            ax2.tick_params(axis='both', left=False, top=False, right=False, bottom=False, labelleft=False,
                            labeltop=False, labelright=False, labelbottom=False)
            ax3.tick_params(axis='both', left=False, top=False, right=False, bottom=False, labelleft=False,
                            labeltop=False, labelright=False, labelbottom=False)
            ax4.tick_params(axis='both', left=False, top=False, right=False, bottom=False, labelleft=False,
                            labeltop=False, labelright=False, labelbottom=False)
            ax5.tick_params(axis='both', left=False, top=False, right=False, bottom=False, labelleft=False,
                            labeltop=False, labelright=False, labelbottom=False)

            # Label axes
            ax1.set_xlabel(axlabels[int(i)])
            ax2.set_xlabel(axlabels[int(i)])
            ax3.set_xlabel(axlabels[int(i)])
            ax4.set_xlabel(axlabels[int(i)])
            ax5.set_xlabel(axlabels[int(i)])
            ax1.set_ylabel(axlabels[int(j)])

            # Add colorbars
            cbar1 = fig.colorbar(im1, cax=cax1, orientation="horizontal")
            cbar2 = fig.colorbar(im2, cax=cax2, orientation="horizontal")
            cbar3 = fig.colorbar(im3, cax=cax3, orientation="horizontal")
            cbar4 = fig.colorbar(im4, cax=cax4, orientation="horizontal")
            cbar5 = fig.colorbar(im5, cax=cax5, orientation="horizontal")

            # Label colorbars
            cbar1.ax.set_xlabel(r'$M_{\star}/M_{\odot}$')
            cbar1.ax.xaxis.set_ticks_position('top')
            cbar1.ax.xaxis.set_label_position('top')
            cbar2.ax.set_xlabel(r'$L_{\mathrm{V}}/[\mathrm{erg}/\mathrm{s}]$')
            cbar2.ax.xaxis.set_ticks_position('top')
            cbar2.ax.xaxis.set_label_position('top')
            cbar3.ax.set_xlabel(r'$L_{\mathrm{NUV}}/[\mathrm{erg}/\mathrm{s}]$')
            cbar3.ax.xaxis.set_ticks_position('top')
            cbar3.ax.xaxis.set_label_position('top')
            cbar4.ax.set_xlabel(r'$L_{\mathrm{FUV}}/[\mathrm{erg}/\mathrm{s}]$')
            cbar4.ax.xaxis.set_ticks_position('top')
            cbar4.ax.xaxis.set_label_position('top')
            cbar5.ax.set_xlabel(r'$Z_{\mathrm{los}}/[M_{\odot}/\mathrm{cpc}^{2}]$')
            cbar5.ax.xaxis.set_ticks_position('top')
            cbar5.ax.xaxis.set_label_position('top')

            fig.savefig('plots/UVimages/UV_reg' + str(reg) + '_snap' + snap +
                        '_gal' + str(id).split('.')[0] + 'p' + str(id).split('.')[1] + '_coords' + key + '.png',
                        bbox_inches='tight', dpi=300)

            plt.close(fig)


# Define comoving softening length in Mpc
csoft = 0.001802390/0.677

# Define resolution
res = csoft
print(100 / res, 'pixels in', '100 kpc')

npart_lim = 10**4

regions = []
for reg in range(0, 40):
    if reg < 10:
        regions.append('0' + str(reg))
    else:
        regions.append(str(reg))

snaps = ['000_z015p000', '001_z014p000', '002_z013p000', '003_z012p000', '004_z011p000', '005_z010p000',
         '006_z009p000', '007_z008p000', '008_z007p000', '009_z006p000', '010_z005p000', '011_z004p770']

reg_snaps = []
for reg in reversed(regions):

    for snap in snaps:

        reg_snaps.append((reg, snap))

for i in range(len(reg_snaps)):

    print(reg_snaps[i][0], reg_snaps[i][1])

    # Define region variables
    reg = reg_snaps[i][0]
    snap = reg_snaps[i][1]
    path = '/cosma/home/dp004/dc-rope1/FLARES/FLARES-1/G-EAGLE_' + reg + '/data/'

    files = os.listdir('UVimg_data/')
    print(files)

    if 'stellardata_reg' + reg + '_snap' + snap + '_npartgreaterthan' + str(npart_lim) + '.pck' in files:
        load = True
    else:
        # load = False
        continue

    try:
        img_main(path, snap, reg, res, npart_lim=npart_lim, dim=0.15, load=load,
                 conv=(u.solMass/u.Mpc**2).to(u.solMass/u.pc**2), scale=0.05)
    except ValueError:
        continue
    except KeyError:
        continue
    except OSError:
        continue
