#!/cosma/home/dp004/dc-rope1/.conda/envs/flares-env/bin/python
import numpy as np
import matplotlib
import h5py
from eagle_IO import eagle_IO as E
import os
import gc
import sys
matplotlib.use('Agg')


def dmgetLinks(current_halo_pids, prog_snap_haloIDs, desc_snap_haloIDs,
             prog_counts, desc_counts, part_type):
    """

    :param current_halo_pids:
    :param prog_snap_haloIDs:
    :param desc_snap_haloIDs:
    :param prog_counts:
    :param desc_counts:
    :param part_threshold:
    :return:
    """

    # =============== Find Progenitor IDs ===============

    # If any progenitor halos exist (i.e. The current snapshot ID is not 000, enforced in the main function)
    if prog_snap_haloIDs.size != 0:

        # Find the halo IDs of the current halo's particles in the progenitor snapshot by indexing the
        # progenitor snapshot's particle halo IDs array with the halo's particle IDs, this can be done
        # since the particle halo IDs array is sorted by particle ID.
        prog_haloids = prog_snap_haloIDs[current_halo_pids]

        # Find the unique halo IDs and the number of times each appears
        uniprog_haloids, uniprog_counts = np.unique(prog_haloids, return_counts=True)

        # Remove single particle halos (ID=-2), since np.unique returns a sorted array this can be
        # done by removing the first value.
        if uniprog_haloids[0] == -2:
            uniprog_haloids = uniprog_haloids[1:]
            uniprog_counts = uniprog_counts[1:]

        if part_type == 1:
            uniprog_haloids = uniprog_haloids[np.where(uniprog_counts >= 10)]
            uniprog_counts = uniprog_counts[np.where(uniprog_counts >= 10)]

        # Find the number of progenitor halos from the size of the unique array
        nprog = uniprog_haloids.size

        # Assign the corresponding number of particles in each progenitor for sorting and storing
        # This can be done simply by using the ID of the progenitor since again np.unique returns
        # sorted results.
        prog_npart = prog_counts[uniprog_haloids]

        # Sort the halo IDs and number of particles in each progenitor halo by their contribution to the
        # current halo (number of particles from the current halo in the progenitor or descendant)
        sorting_inds = uniprog_counts.argsort()[::-1]
        prog_npart = prog_npart[sorting_inds]
        prog_haloids = uniprog_haloids[sorting_inds]
        prog_mass_contribution = uniprog_counts[sorting_inds]

    # If there is no progenitor store Null values
    else:
        nprog = -1
        prog_npart = np.array([], copy=False, dtype=int)
        prog_haloids = np.array([], copy=False, dtype=int)
        prog_mass_contribution = np.array([], copy=False, dtype=int)

    # =============== Find Descendant IDs ===============

    # If descendant halos exist (i.e. The current snapshot ID is not 061, enforced in the main function)
    if desc_snap_haloIDs.size != 0:

        # Find the halo IDs of the current halo's particles in the descendant snapshot by indexing the
        # descendant snapshot's particle halo IDs array with the halo's particle IDs, this can be done
        # since the particle halo IDs array is sorted by particle ID.
        desc_haloids = desc_snap_haloIDs[current_halo_pids]

        # Find the unique halo IDs and the number of times each appears
        unidesc_haloids, unidesc_counts = np.unique(desc_haloids, return_counts=True)

        # Remove single particle halos (ID=-2) for the counts, since np.unique returns a sorted array this can be
        # done by removing the first value.
        if unidesc_haloids[0] == -2:
            unidesc_haloids = unidesc_haloids[1:]
            unidesc_counts = unidesc_counts[1:]

        if part_type == 1:
            unidesc_haloids = unidesc_haloids[np.where(unidesc_counts >= 10)]
            unidesc_counts = unidesc_counts[np.where(unidesc_counts >= 10)]

        # Find the number of descendant halos from the size of the unique array
        ndesc = unidesc_haloids.size

        # Assign the corresponding number of particles in each descendant for storing.
        # Could be extracted later from halo data but make analysis faster to save it here.
        # This can be done simply by using the ID of the descendant since again np.unique returns
        # sorted results.
        desc_npart = desc_counts[unidesc_haloids]

        # Sort the halo IDs and number of particles in each progenitor halo by their contribution to the
        # current halo (number of particles from the current halo in the progenitor or descendant)
        sorting_inds = unidesc_counts.argsort()[::-1]
        desc_npart = desc_npart[sorting_inds]
        desc_haloids = unidesc_haloids[sorting_inds]
        desc_mass_contribution = unidesc_counts[sorting_inds]

    # If there is no descendant snapshot store Null values
    else:
        ndesc = -1
        desc_npart = np.array([], copy=False, dtype=int)
        desc_haloids = np.array([], copy=False, dtype=int)
        desc_mass_contribution = np.array([], copy=False, dtype=int)

    return (nprog, prog_haloids, prog_npart, prog_mass_contribution,
            ndesc, desc_haloids, desc_npart, desc_mass_contribution,
            current_halo_pids)


def getLinks(current_halo_pids, prog_snap_haloIDs, desc_snap_haloIDs,
             progpart_masses, descpart_masses, prog_ms, prog_ids, desc_ms, desc_ids):
    """

    :param current_halo_pids:
    :param prog_snap_haloIDs:
    :param desc_snap_haloIDs:
    :param prog_counts:
    :param desc_counts:
    :param part_threshold:
    :return:
    """

    # =============== Find Progenitor IDs ===============

    # If any progenitor halos exist (i.e. The current snapshot ID is not 000, enforced in the main function)
    if prog_snap_haloIDs.size != 0:

        # Find the halo IDs of the current halo's particles in the progenitor snapshot by indexing the
        # progenitor snapshot's particle halo IDs array with the halo's particle IDs, this can be done
        # since the particle halo IDs array is sorted by particle ID.
        prog_haloids = prog_snap_haloIDs[current_halo_pids]

        # Find the unique halo IDs and the number of times each appears
        uniprog_haloids, uniprog_counts = np.unique(prog_haloids, return_counts=True)
        
        # Remove single particle halos (ID=-2), since np.unique returns a sorted array this can be
        # done by removing the first value.
        if uniprog_haloids[0] == -2:
            uniprog_haloids = uniprog_haloids[1:]
            uniprog_counts = uniprog_counts[1:]
        
        # Get progenitor halo masses
        prog_masses = np.array([prog_ms[prog_ids == p] for p in uniprog_haloids]).flatten()
        
        # Get progenitor particle masses
        prog_partmass_contributed = progpart_masses[current_halo_pids]
        
        # Combine contribution to entire halo
        prog_mass_contribution = np.array([np.sum(prog_partmass_contributed[prog_haloids == p]) 
                                           for p in uniprog_haloids])
        prog_mass_contribution = prog_mass_contribution[np.where(prog_mass_contribution > 0.0)]

        # Find the number of progenitor halos from the size of the unique array
        nprog = uniprog_haloids.size

        # Sort the halo IDs and number of particles in each progenitor halo by their contribution to the
        # current halo (number of particles from the current halo in the progenitor or descendant)
        sorting_inds = prog_mass_contribution.argsort()[::-1]
        prog_npart = prog_masses[sorting_inds]
        prog_haloids = uniprog_haloids[sorting_inds]
        prog_mass_contribution = prog_mass_contribution[sorting_inds]

    # If there is no progenitor store Null values
    else:
        nprog = -1
        prog_npart = np.array([], copy=False, dtype=int)
        prog_haloids = np.array([], copy=False, dtype=int)
        prog_mass_contribution = np.array([], copy=False, dtype=int)

    # =============== Find Descendant IDs ===============

    # If descendant halos exist (i.e. The current snapshot ID is not 061, enforced in the main function)
    if desc_snap_haloIDs.size != 0:

        # Find the halo IDs of the current halo's particles in the descenitor snapshot by indexing the
        # descenitor snapshot's particle halo IDs array with the halo's particle IDs, this can be done
        # since the particle halo IDs array is sorted by particle ID.
        desc_haloids = desc_snap_haloIDs[current_halo_pids]

        # Find the unique halo IDs and the number of times each appears
        unidesc_haloids, unidesc_counts = np.unique(desc_haloids, return_counts=True)

        # Remove single particle halos (ID=-2), since np.unique returns a sorted array this can be
        # done by removing the first value.
        if unidesc_haloids[0] == -2:
            unidesc_haloids = unidesc_haloids[1:]
            unidesc_counts = unidesc_counts[1:]

        # Get descenitor halo masses
        desc_masses = np.array([desc_ms[desc_ids == d] for d in unidesc_haloids]).flatten()

        # Get descenitor particle masses
        desc_partmass_contributed = descpart_masses[current_halo_pids]

        # Combine contribution to entire halo
        desc_mass_contribution = np.array([np.sum(desc_partmass_contributed[desc_haloids == p])
                                           for p in unidesc_haloids])
        desc_mass_contribution = desc_mass_contribution[np.where(desc_mass_contribution > 0.0)]

        # Find the number of descenitor halos from the size of the unique array
        ndesc = unidesc_haloids.size

        # Sort the halo IDs and number of particles in each descenitor halo by their contribution to the
        # current halo (number of particles from the current halo in the descenitor or descendant)
        sorting_inds = desc_mass_contribution.argsort()[::-1]
        desc_npart = desc_masses[sorting_inds]
        desc_haloids = unidesc_haloids[sorting_inds]
        desc_mass_contribution = desc_mass_contribution[sorting_inds]

    # If there is no descendant snapshot store Null values
    else:
        ndesc = -1
        desc_npart = np.array([], copy=False, dtype=int)
        desc_haloids = np.array([], copy=False, dtype=int)
        desc_mass_contribution = np.array([], copy=False, dtype=int)

    return (nprog, prog_haloids, prog_npart, prog_mass_contribution,
            ndesc, desc_haloids, desc_npart, desc_mass_contribution,
            current_halo_pids)


def get_current_part_ind_dict(path, snap, part_type, part_ids):
    
    # Extract the halo IDs (group names/keys) contained within this snapshot
    group_part_ids = E.read_array('PARTDATA', path, snap, 'PartType' + str(part_type) + '/ParticleIDs',
                                  numThreads=8)
    grp_ids = E.read_array('PARTDATA', path, snap, 'PartType' + str(part_type) + '/GroupNumber', numThreads=8)
    subgrp_ids = E.read_array('PARTDATA', path, snap, 'PartType' + str(part_type) + '/SubGroupNumber', numThreads=8)

    # Convert to group.subgroup ID format
    halo_ids = np.zeros(grp_ids.size, dtype=float)
    for (ind, g), sg in zip(enumerate(grp_ids), subgrp_ids):
        halo_ids[ind] = float(str(int(g)) + '.%05d'%int(sg))

    unsort_part_ids = np.copy(part_ids)
    sinds = np.argsort(part_ids)
    part_ids = part_ids[sinds]

    sorted_index = np.searchsorted(part_ids, group_part_ids)

    yindex = np.take(sinds, sorted_index, mode="clip")
    mask = unsort_part_ids[yindex] != group_part_ids

    result = np.ma.array(yindex, mask=mask)

    part_groups = halo_ids[np.logical_not(result.mask)]
    parts_in_groups = result.data[np.logical_not(result.mask)]

    halo_id_part_inds = {}
    for ind, grp in zip(parts_in_groups, part_groups):
        halo_id_part_inds.setdefault(grp, set()).update({ind})

    return halo_id_part_inds


def get_progdesc_part_ind_dict(path, snap, part_type, part_ids):

    # Extract the halo IDs (group names/keys) contained within this snapshot
    group_part_ids = E.read_array('PARTDATA', path, snap, 'PartType' + str(part_type) + '/ParticleIDs',
                                  numThreads=8)
    grp_ids = E.read_array('PARTDATA', path, snap, 'PartType' + str(part_type) + '/GroupNumber', numThreads=8)
    subgrp_ids = E.read_array('PARTDATA', path, snap, 'PartType' + str(part_type) + '/SubGroupNumber', numThreads=8)

    # Convert to group.subgroup ID format
    halo_ids = np.zeros(grp_ids.size, dtype=float)
    for (ind, g), sg in zip(enumerate(grp_ids), subgrp_ids):
        halo_ids[ind] = float(str(int(g)) + '.%05d' % int(sg))

    uni_haloids = np.unique(halo_ids)
    sim_halo_ids = np.zeros(uni_haloids.size)
    internal_halo_ids = {}
    for num, halo in enumerate(uni_haloids):
        sim_halo_ids[num] = halo
        internal_halo_ids[halo] = num

    unsort_part_ids = np.copy(part_ids)
    sinds = np.argsort(part_ids)
    part_ids = part_ids[sinds]

    sorted_index = np.searchsorted(part_ids, group_part_ids)

    yindex = np.take(sinds, sorted_index, mode="clip")
    mask = unsort_part_ids[yindex] != group_part_ids

    result = np.ma.array(yindex, mask=mask)

    part_groups = halo_ids[np.logical_not(result.mask)]
    parts_in_groups = result.data[np.logical_not(result.mask)]

    snap_haloIDs = np.full(len(part_ids), -2, dtype=int)
    for ind, halo in zip(parts_in_groups, part_groups):
        snap_haloIDs[ind] = internal_halo_ids[halo]

    return snap_haloIDs, sim_halo_ids


def partDirectProgDesc(snap, prog_snap, desc_snap, path, part_type):
    """ A function which cycles through all halos in a snapshot finding and writing out the
    direct progenitor and descendant data.

    :param snapshot: The snapshot ID.
    :param halopath: The filepath to the halo finder HDF5 file.
    :param savepath: The filepath to the directory where the Merger Graph should be written out to.
    :param part_threshold: The mass (number of particles) threshold defining a halo.

    :return: None
    """

    # Extract particle IDs
    snap_part_ids = E.read_array('PARTDATA', path, snap, 'PartType' + str(part_type) + '/ParticleIDs', numThreads=8)

    if prog_snap != None:
        progsnap_part_ids = E.read_array('PARTDATA', path, prog_snap, 'PartType' + str(part_type) + '/ParticleIDs',
                                         numThreads=8)
    else:
        progsnap_part_ids = []

    if desc_snap != None:
        descsnap_part_ids = E.read_array('PARTDATA', path, desc_snap, 'PartType' + str(part_type) + '/ParticleIDs',
                                         numThreads=8)
    else:
        descsnap_part_ids = []

    # Combine the particle id arrays and only take unique values
    part_ids = np.unique(np.concatenate([snap_part_ids, progsnap_part_ids, descsnap_part_ids]))

    part_ids = np.sort(part_ids)

    # if prog_snap != None:
    #
    #     progpart_masses = E.read_array('PARTDATA', path, prog_snap, 'PartType' + str(part_type) + '/Mass',
    #                                       numThreads=8) / 0.6777
    # else:
    #     progpart_masses = np.array([])
    #
    # if desc_snap != None:
    #
    #     descpart_masses = E.read_array('PARTDATA', path, prog_snap, 'PartType' + str(part_type) + '/Mass',
    #                                       numThreads=8) / 0.6777
    # else:
    #     descpart_masses = np.array([])

    # =============== Current Snapshot ===============

    halo_id_part_inds = get_current_part_ind_dict(path, snap, part_type, part_ids)

    # =============== Progenitor Snapshot ===============

    # Only look for descendant data if there is a descendant snapshot
    if prog_snap != None:

        prog_snap_haloIDs, prog_sim_halo_ids = get_progdesc_part_ind_dict(path, prog_snap, part_type, part_ids)
            
        # Get all the unique halo IDs in this snapshot and the number of times they appear
        prog_unique, prog_counts = np.unique(prog_snap_haloIDs, return_counts=True)

        # Remove single particle halos (ID=-2), since np.unique returns a sorted array this can be
        # done by removing the first value
        prog_unique = prog_unique[1:]
        prog_counts = prog_counts[1:]

    else:  # Assign an empty array if the snapshot is less than the earliest (000)
        prog_snap_haloIDs = np.array([], copy=False)
        prog_sim_halo_ids = np.array([], copy=False)
        prog_counts = np.array([], copy=False)

    # =============== Descendant Snapshot ===============

    # Only look for descendant data if there is a descendant snapshot
    if desc_snap != None:

        desc_snap_haloIDs, desc_sim_halo_ids = get_progdesc_part_ind_dict(path, desc_snap, part_type, part_ids)

        # Get all the unique halo IDs in this snapshot and the number of times they appear
        desc_unique, desc_counts = np.unique(desc_snap_haloIDs, return_counts=True)

        # Remove single particle halos (ID=-2), since np.unique returns a sorted array this can be
        # done by removing the first value
        desc_unique = desc_unique[1:]
        desc_counts = desc_counts[1:]

    else:  # Assign an empty array if the snapshot is less than the earliest (000)
        desc_snap_haloIDs = np.array([], copy=False)
        desc_sim_halo_ids = np.array([], copy=False)
        desc_counts = np.array([], copy=False)

    # =============== Find all Direct Progenitors And Descendant Of Halos In This Snapshot ===============

    # Initialise the progress
    progress = -1

    # Assign the number of halos for progress reporting
    size = len(halo_id_part_inds.keys())
    results = {}

    # Loop through all the halos in this snapshot
    for num, haloID in enumerate(halo_id_part_inds.keys()):

        # Print progress
        previous_progress = progress
        progress = int(num / size * 100)
        if progress != previous_progress:
            print('Graph progress: ', progress, '%', haloID)

        # =============== Current Halo ===============

        current_halo_pids = np.array(list(halo_id_part_inds[haloID]))

        # =============== Run The Direct Progenitor and Descendant Finder ===============

        # Run the progenitor/descendant finder
        if part_type == 1:
            results[haloID] = dmgetLinks(current_halo_pids, prog_snap_haloIDs, desc_snap_haloIDs,
                              prog_counts, desc_counts, part_type)
        # else:
        #     results[haloID] = getLinks(current_halo_pids, prog_snap_haloIDs, desc_snap_haloIDs,
        #                                progpart_masses, descpart_masses, prog_gal_ms, prog_sub_ids,
        #                                desc_gal_ms, desc_sub_ids)
            
    print('Processed', len(results.keys()), 'halos in snapshot', snap, 'of particle type', part_type)

    return results, desc_sim_halo_ids, prog_sim_halo_ids, part_ids


def mainDirectProgDesc(snap, prog_snap, desc_snap, path, savepath='MergerGraphs/'):

    # ========================================== ID extraction ==========================================

    # # Get the group and subgroup IDs for each snapshot
    # subgrp_ids = E.read_array('SUBFIND', path, snap, 'Subhalo/SubGroupNumber', numThreads=8)
    # grp_ids = E.read_array('SUBFIND', path, snap, 'Subhalo/GroupNumber', numThreads=8)
    # masses = E.read_array('SUBFIND', path, snap, 'Subhalo/ApertureMeasurements/Mass/030kpc', numThreads=8) / 0.6777
    #
    # # Remove groups without subgroups
    # okinds = subgrp_ids != 2**30
    # subgrp_ids = subgrp_ids[okinds]
    # grp_ids = grp_ids[okinds]
    # masses = masses[okinds]
    #
    # halo_ids = np.zeros(grp_ids.size, dtype=float)
    # for (ind, g), sg in zip(enumerate(grp_ids), subgrp_ids):
    #     halo_ids[ind] = float(str(int(g)) + '.%05d' % int(sg))
    #
    # internal_halo_ids = np.arange(grp_ids.size, dtype=int)
    #
    # if prog_snap != None:
    #     prog_subgrp_ids = E.read_array('SUBFIND', path, prog_snap, 'Subhalo/SubGroupNumber', numThreads=8)
    #     prog_grp_ids = E.read_array('SUBFIND', path, prog_snap, 'Subhalo/GroupNumber', numThreads=8)
    #     prog_masses = E.read_array('SUBFIND', path, prog_snap, 'Subhalo/ApertureMeasurements/Mass/030kpc',
    #                                numThreads=8) / 0.6777
    #     # Remove groups without subgroups
    #     okinds = prog_subgrp_ids != 2 ** 30
    #     prog_subgrp_ids = prog_subgrp_ids[okinds]
    #     prog_grp_ids = prog_grp_ids[okinds]
    #     prog_masses = prog_masses[okinds]
    #
    #     prog_ids = np.zeros(prog_grp_ids.size, dtype=float)
    #     for (ind, g), sg in zip(enumerate(prog_grp_ids), prog_subgrp_ids):
    #         prog_ids[ind] = float(str(int(g)) + '.%05d' % int(sg))
    #
    #     internal_prog_ids = np.arange(prog_grp_ids.size, dtype=int)
    #
    # else:
    #     prog_subgrp_ids = []
    #     prog_grp_ids = []
    #     prog_masses = []
    #     prog_ids = []
    #     internal_prog_ids = []
    #
    # if desc_snap != None
    #     desc_subgrp_ids = E.read_array('SUBFIND', path, desc_snap, 'Subhalo/SubGroupNumber', numThreads=8)
    #     desc_grp_ids = E.read_array('SUBFIND', path, desc_snap, 'Subhalo/GroupNumber', numThreads=8)
    #     desc_masses = E.read_array('SUBFIND', path, desc_snap, 'Subhalo/ApertureMeasurements/Mass/030kpc',
    #                                numThreads=8) / 0.6777
    #     # Remove groups without subgroups
    #     okinds = desc_subgrp_ids != 2 ** 30
    #     desc_subgrp_ids = desc_subgrp_ids[okinds]
    #     desc_grp_ids = desc_grp_ids[okinds]
    #     desc_masses = desc_masses[okinds]
    #
    #     desc_ids = np.zeros(desc_grp_ids.size, dtype=float)
    #     for (ind, g), sg in zip(enumerate(desc_grp_ids), desc_subgrp_ids):
    #         desc_ids[ind] = float(str(int(g)) + '.%05d' % int(sg))
    #
    #     internal_desc_ids = np.arange(desc_grp_ids.size, dtype=int)
    #
    # else:
    #     desc_subgrp_ids = []
    #     desc_grp_ids = []
    #     desc_masses = []
    #     desc_ids = []
    #     internal_desc_ids = []

    # ====================================================================================================

    dm_results_tup = partDirectProgDesc(snap, prog_snap,desc_snap, path, part_type=1)
    results_dm, internal_to_sim_haloID_desc_dm, internal_to_sim_haloID_prog_dm, part_ids = dm_results_tup
    # stars_results_tup = partDirectProgDesc(snap, prog_snap, desc_snap, path, part_type=4)
    # results_stars, internal_to_sim_haloID_desc_st, internal_to_sim_haloID_prog_st, star_ids = stars_results_tup
    # bh_results_tup = partDirectProgDesc(snap, prog_snap, desc_snap, path, part_type=5)
    # results_bh, internal_to_sim_haloID_desc_bh, internal_to_sim_haloID_prog_bh, bh_ids = bh_results_tup
    # gas_results_tup = partDirectProgDesc(snap, prog_snap, desc_snap, path, part_type=0)
    # results_gas, internal_to_sim_haloID_desc_gas, internal_to_sim_haloID_prog_gas, gas_ids = gas_results_tup

    # Set up arrays to store host results
    nhalo = len(results_dm.keys())
    index_haloids = np.arange(nhalo, dtype=int)
    sim_haloids = np.full(nhalo, -2, dtype=int)
    halo_nparts = np.full(nhalo, -2, dtype=int)
    nprogs = np.full(nhalo, -2, dtype=int)
    ndescs = np.full(nhalo, -2, dtype=int)
    prog_start_index = np.full(nhalo, -2, dtype=int)
    desc_start_index = np.full(nhalo, -2, dtype=int)

    progs = []
    descs = []
    prog_mass_conts = []
    desc_mass_conts = []
    prog_nparts = []
    desc_nparts = []

    for num, simhaloID in enumerate(results_dm.keys()):

        sim_haloids[num] = simhaloID

        haloID = num

        (nprog, prog_haloids, prog_npart, prog_mass_contribution,
         ndesc, desc_haloids, desc_npart, desc_mass_contribution, current_halo_pids) = results_dm[simhaloID]

        sim_prog_haloids = np.zeros(len(prog_haloids), dtype=float)
        for ind, prog in enumerate(prog_haloids):
            sim_prog_haloids[ind] = internal_to_sim_haloID_prog_dm[prog]

        sim_desc_haloids = np.zeros(len(desc_haloids), dtype=float)
        for ind, desc in enumerate(desc_haloids):
            sim_desc_haloids[ind] = internal_to_sim_haloID_desc_dm[desc]

        # nprog = 0
        # okinds = sim_desc_haloids >= 0
        # sim_desc_haloids

        # Write out the data produced
        nprogs[haloID] = nprog  # number of progenitors
        ndescs[haloID] = ndesc  # number of descendants
        halo_nparts[int(haloID)] = current_halo_pids.size  # mass of the halo

        if nprog > 0:
            prog_start_index[haloID] = len(progs)
            progs.extend(sim_prog_haloids)
            prog_mass_conts.extend(prog_mass_contribution)
            prog_nparts.extend(prog_npart)
        else:
            prog_start_index[haloID] = 2**30

        if ndesc > 0:
            desc_start_index[haloID] = len(descs)
            descs.extend(sim_desc_haloids)
            desc_mass_conts.extend(desc_mass_contribution)
            desc_nparts.extend(desc_npart)
        else:
            desc_start_index[haloID] = 2**30

        # # Αssign dark matter haloids for comparison to other particle types
        # dm_sim_desc_haloids = np.copy(sim_desc_haloids)
        # dm_sim_prog_haloids = np.copy(sim_prog_haloids)

    progs = np.array(progs)
    descs = np.array(descs)
    prog_mass_conts = np.array(prog_mass_conts)
    desc_mass_conts = np.array(desc_mass_conts)
    prog_nparts = np.array(prog_nparts)
    desc_nparts = np.array(desc_nparts)

    # Create file to store this snapshots graph results
    hdf = h5py.File(savepath + 'SubMgraph_' + snap + '.hdf5', 'w')

    hdf.create_dataset('mega_halo_IDs', shape=index_haloids.shape, dtype=int, data=index_haloids, compression='gzip')
    hdf.create_dataset('sim_halo_IDs', shape=sim_haloids.shape, dtype=float, data=sim_haloids, compression='gzip')
    hdf.create_dataset('nProgs', shape=nprogs.shape, dtype=int, data=nprogs, compression='gzip')
    hdf.create_dataset('nDescs', shape=ndescs.shape, dtype=int, data=ndescs, compression='gzip')
    hdf.create_dataset('nparts', shape=halo_nparts.shape, dtype=int, data=halo_nparts, compression='gzip')
    hdf.create_dataset('prog_start_index', shape=prog_start_index.shape, dtype=int, data=prog_start_index,
                       compression='gzip')
    hdf.create_dataset('desc_start_index', shape=desc_start_index.shape, dtype=int, data=desc_start_index,
                       compression='gzip')

    hdf.create_dataset('Prog_haloIDs', shape=progs.shape, dtype=int, data=progs, compression='gzip')
    hdf.create_dataset('Desc_haloIDs', shape=descs.shape, dtype=int, data=descs, compression='gzip')
    hdf.create_dataset('Prog_Mass_Contribution', shape=prog_mass_conts.shape, dtype=int, data=prog_mass_conts,
                       compression='gzip')
    hdf.create_dataset('Desc_Mass_Contribution', shape=desc_mass_conts.shape, dtype=int, data=desc_mass_conts,
                       compression='gzip')
    hdf.create_dataset('Prog_nPart', shape=prog_nparts.shape, dtype=int, data=prog_nparts, compression='gzip')
    hdf.create_dataset('Desc_nPart', shape=desc_nparts.shape, dtype=int, data=desc_nparts, compression='gzip')

    hdf.close()

    print(np.unique(nprogs[sim_haloids >= 0], return_counts=True))
    print(np.unique(ndescs[sim_haloids >= 0], return_counts=True))

    # # Write out star data
    # if haloID in results_stars:
    #
    #     (nprog, prog_haloids, prog_npart, prog_mass_contribution,
    #      ndesc, desc_haloids, desc_npart, desc_mass_contribution, current_halo_pids) = results_stars[haloID]
    #
    #     sim_prog_haloids = np.zeros(len(prog_haloids), dtype=float)
    #     for ind, prog in enumerate(prog_haloids):
    #         sim_prog_haloids[ind] = internal_to_sim_haloID_prog_st[prog]
    #
    #     sim_desc_haloids = np.zeros(len(desc_haloids), dtype=float)
    #     for ind, desc in enumerate(desc_haloids):
    #         sim_desc_haloids[ind] = internal_to_sim_haloID_desc_st[desc]
    #
    #     # Assign values to the corresponding index for the dark matter progenitors
    #     star_prog_mass_contribution = np.zeros(len(dm_sim_prog_haloids), dtype=float)
    #     star_prog_mass = np.zeros(len(dm_sim_prog_haloids), dtype=float)
    #     for p, cont, mass in zip(sim_prog_haloids, prog_mass_contribution, prog_npart):
    #         if not p in dm_sim_prog_haloids:
    #             continue
    #         ind = np.where(dm_sim_prog_haloids == p)
    #         star_prog_mass_contribution[ind] = cont
    #         star_prog_mass[ind] = mass
    #
    #     # Assign values to the corresponding index for the dark matter descendents
    #     star_desc_mass_contribution = np.zeros(len(dm_sim_desc_haloids), dtype=float)
    #     star_desc_mass = np.zeros(len(dm_sim_desc_haloids), dtype=float)
    #     for p, cont, mass in zip(sim_desc_haloids, desc_mass_contribution, desc_npart):
    #         if not p in dm_sim_desc_haloids:
    #             continue
    #         ind = np.where(dm_sim_desc_haloids == p)
    #         star_desc_mass_contribution[ind] = cont
    #         star_desc_mass[ind] = mass
    #
    #     # Get IDs
    #     pids = star_ids[current_halo_pids]
    #
    #     halo.create_dataset('stellar_part_ids', data=pids, dtype=int)  # particle ids in this halo
    #     halo.create_dataset('prog_stellar_mass_contribution', data=star_prog_mass_contribution,
    #                         dtype=float)  # Mass contribution
    #     halo.create_dataset('desc_stellar_mass_contribution', data=star_desc_mass_contribution,
    #                         dtype=float)  # Mass contribution
    #     halo.create_dataset('Prog_stellar_mass', data=star_prog_mass,
    #                         dtype=float)  # number of particles in each progenitor
    #     halo.create_dataset('Desc_stellar_mass', data=star_desc_mass,
    #                         dtype=float)  # number of particles in each descendant
    # else:
    #
    #     halo.create_dataset('stellar_part_ids', data=np.array([]), dtype=int)  # particle ids in this halo
    #     halo.create_dataset('prog_stellar_mass_contribution', data=np.array([]), dtype=float)  # Mass contribution
    #     halo.create_dataset('desc_stellar_mass_contribution', data=np.array([]), dtype=float)  # Mass contribution
    #     halo.create_dataset('Prog_stellar_mass', data=np.array([]),
    #                         dtype=float)  # number of particles in each progenitor
    #     halo.create_dataset('Desc_stellar_mass', data=np.array([]),
    #                         dtype=float)  # number of particles in each descendant
    #
    # # Write out gas data
    # if haloID in results_gas:
    #
    #     (nprog, prog_haloids, prog_npart, prog_mass_contribution,
    #      ndesc, desc_haloids, desc_npart, desc_mass_contribution, current_halo_pids) = results_gas[haloID]
    #
    #     sim_prog_haloids = np.zeros(len(prog_haloids), dtype=float)
    #     for ind, prog in enumerate(prog_haloids):
    #         sim_prog_haloids[ind] = internal_to_sim_haloID_prog_gas[prog]
    #
    #     sim_desc_haloids = np.zeros(len(desc_haloids), dtype=float)
    #     for ind, desc in enumerate(desc_haloids):
    #         sim_desc_haloids[ind] = internal_to_sim_haloID_desc_gas[desc]
    #
    #     # Assign values to the corresponding index for the dark matter progenitors
    #     gas_prog_mass_contribution = np.zeros(len(dm_sim_prog_haloids), dtype=float)
    #     gas_prog_mass = np.zeros(len(dm_sim_prog_haloids), dtype=float)
    #     for p, cont, mass in zip(sim_prog_haloids, prog_mass_contribution, prog_npart):
    #         if not p in dm_sim_prog_haloids:
    #             continue
    #         ind = np.where(dm_sim_prog_haloids == p)
    #         gas_prog_mass_contribution[ind] = cont
    #         gas_prog_mass[ind] = mass
    #
    #     # Assign values to the corresponding index for the dark matter descendents
    #     gas_desc_mass_contribution = np.zeros(len(dm_sim_desc_haloids), dtype=float)
    #     gas_desc_mass = np.zeros(len(dm_sim_desc_haloids), dtype=float)
    #     for p, cont, mass in zip(sim_desc_haloids, desc_mass_contribution, desc_npart):
    #         if not p in dm_sim_desc_haloids:
    #             continue
    #         ind = np.where(dm_sim_desc_haloids == p)
    #         gas_desc_mass_contribution[ind] = cont
    #         gas_desc_mass[ind] = mass
    #
    #     # Get IDs
    #     pids = gas_ids[current_halo_pids]
    #
    #     halo.create_dataset('gas_part_ids', data=pids, dtype=int)  # particle ids in this halo
    #     halo.create_dataset('prog_gas_mass_contribution', data=gas_prog_mass_contribution,
    #                         dtype=float)  # Mass contribution
    #     halo.create_dataset('desc_gas_mass_contribution', data=gas_desc_mass_contribution,
    #                         dtype=float)  # Mass contribution
    #     halo.create_dataset('Prog_gas_mass', data=gas_prog_mass,
    #                         dtype=float)  # number of particles in each progenitor
    #     halo.create_dataset('Desc_gas_mass', data=gas_desc_mass,
    #                         dtype=float)  # number of particles in each descendant
    # else:
    #
    #     halo.create_dataset('gas_part_ids', data=np.array([]), dtype=int)  # particle ids in this halo
    #     halo.create_dataset('prog_gas_mass_contribution', data=np.array([]),
    #                         dtype=int)  # Mass contribution
    #     halo.create_dataset('desc_gas_mass_contribution', data=np.array([]),
    #                         dtype=int)  # Mass contribution
    #     halo.create_dataset('Prog_gas_mass', data=np.array([]),
    #                         dtype=int)  # number of particles in each progenitor
    #     halo.create_dataset('Desc_gas_mass', data=np.array([]),
    #                         dtype=int)  # number of particles in each descendant
    #
    # # Write out black hole data
    # if haloID in results_bh:
    #
    #     (nprog, prog_haloids, prog_npart, prog_mass_contribution,
    #      ndesc, desc_haloids, desc_npart, desc_mass_contribution, current_halo_pids) = results_bh[haloID]
    #
    #     sim_prog_haloids = np.zeros(len(prog_haloids), dtype=float)
    #     for ind, prog in enumerate(prog_haloids):
    #         sim_prog_haloids[ind] = internal_to_sim_haloID_prog_bh[prog]
    #
    #     sim_desc_haloids = np.zeros(len(desc_haloids), dtype=float)
    #     for ind, desc in enumerate(desc_haloids):
    #         sim_desc_haloids[ind] = internal_to_sim_haloID_desc_bh[desc]
    #
    #     # Assign values to the corresponding index for the dark matter progenitors
    #     bh_prog_mass_contribution = np.zeros(len(dm_sim_prog_haloids), dtype=float)
    #     bh_prog_mass = np.zeros(len(dm_sim_prog_haloids), dtype=float)
    #     for p, cont, mass in zip(sim_prog_haloids, prog_mass_contribution, prog_npart):
    #         if not p in dm_sim_prog_haloids:
    #             continue
    #         ind = np.where(dm_sim_prog_haloids == p)
    #         bh_prog_mass_contribution[ind] = cont
    #         bh_prog_mass[ind] = mass
    #
    #     # Assign values to the corresponding index for the dark matter descendents
    #     bh_desc_mass_contribution = np.zeros(len(dm_sim_desc_haloids), dtype=float)
    #     bh_desc_mass = np.zeros(len(dm_sim_desc_haloids), dtype=float)
    #     for p, cont, mass in zip(sim_desc_haloids, desc_mass_contribution, desc_npart):
    #         if not p in dm_sim_desc_haloids:
    #             continue
    #         ind = np.where(dm_sim_desc_haloids == p)
    #         bh_desc_mass_contribution[ind] = cont
    #         bh_desc_mass[ind] = mass
    #
    #     # Get IDs
    #     pids = bh_ids[current_halo_pids]
    #
    #     halo.create_dataset('bh_part_ids', data=pids, dtype=int)  # particle ids in this halo
    #     halo.create_dataset('prog_bh_mass_contribution', data=bh_prog_mass_contribution,
    #                         dtype=float)  # Mass contribution
    #     halo.create_dataset('desc_bh_mass_contribution', data=bh_desc_mass_contribution,
    #                         dtype=float)  # Mass contribution
    #     halo.create_dataset('Prog_bh_mass', data=bh_prog_mass,
    #                         dtype=float)  # number of particles in each progenitor
    #     halo.create_dataset('Desc_bh_mass', data=bh_desc_mass,
    #                         dtype=float)  # number of particles in each descendant
    # else:
    #
    #     halo.create_dataset('bh_part_ids', data=np.array([]), dtype=int)  # particle ids in this halo
    #     halo.create_dataset('prog_bh_mass_contribution', data=np.array([]),
    #                         dtype=int)  # Mass contribution
    #     halo.create_dataset('desc_bh_mass_contribution', data=np.array([]),
    #                         dtype=int)  # Mass contribution
    #     halo.create_dataset('Prog_bh_mass', data=np.array([]),
    #                         dtype=int)  # number of particles in each progenitor
    #     halo.create_dataset('Desc_bh_mass', data=np.array([]),
    #                         dtype=int)  # number of particles in each descendant


regions = []
for reg in range(0, 40):
    if reg < 10:
        regions.append('0' + str(reg))
    else:
        regions.append(str(reg))

snaps = ['000_z015p000', '001_z014p000', '002_z013p000', '003_z012p000', '004_z011p000', '005_z010p000',
         '006_z009p000', '007_z008p000', '008_z007p000', '009_z006p000', '010_z005p000', '011_z004p770']
prog_snaps = [None, '000_z015p000', '001_z014p000', '002_z013p000', '003_z012p000', '004_z011p000', '005_z010p000',
              '006_z009p000', '007_z008p000', '008_z007p000', '009_z006p000', '010_z005p000']
desc_snaps = ['001_z014p000', '002_z013p000', '003_z012p000', '004_z011p000', '005_z010p000',
              '006_z009p000', '007_z008p000', '008_z007p000', '009_z006p000', '010_z005p000', '011_z004p770', None]

reg_snaps = []
for reg in reversed(regions):

    try:
        os.mkdir('/cosma/home/dp004/dc-rope1/FLARES/FLARES-1/MergerGraphs/GEAGLE_' + reg)
    except OSError:
        pass

    for snap, prog_snap, desc_snap in zip(snaps, prog_snaps, desc_snaps):

        reg_snaps.append((reg, prog_snap, snap, desc_snap))

if __name__ == '__main__':

    ind = int(sys.argv[1])
    print(ind)
    print(reg_snaps[ind])

    mainDirectProgDesc(snap=reg_snaps[ind][2], prog_snap=reg_snaps[ind][1], desc_snap=reg_snaps[ind][3],
                       path='/cosma/home/dp004/dc-rope1/FLARES/FLARES-1/G-EAGLE_' + reg_snaps[ind][0] + '/data',
                       savepath='/cosma/home/dp004/dc-rope1/FLARES/FLARES-1/MergerGraphs/GEAGLE_'
                                + reg_snaps[ind][0] + '/')
