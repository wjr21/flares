#!/cosma/home/dp004/dc-rope1/.conda/envs/flares-env/bin/python
import matplotlib as ml
ml.use('Agg')
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.gridspec as gridspec
from matplotlib.colors import LogNorm
import eagle_IO.eagle_IO as E
import h5py
import sys
import multiprocessing
import pickle
import time
import seaborn as sns


sns.set_style('whitegrid')


def get_forest(z0halo, treepath):
    """ A funciton which traverses a tree including all halos which have interacted with the tree
    in a 'forest/mangrove'.

    :param tree_data: The tree data dictionary produced by the Merger Graph.
    :param z0halo: The halo ID of a z=0 halo for which the forest/mangrove plot is desired.

    :return: forest_dict: The dictionary containing the forest. Each key is the snapshot ID and
             the value is a list of halos in this snapshot of the forest.
             massgrowth: The mass history of the forest.
             tree: The dictionary containing the tree. Each key is the snapshot ID and
             the value is a list of halos in this snapshot of the tree.
             main_growth: The mass history of the main branch.
    """

    # Initialise dictionary instances
    forest_dict = {}
    mass_dict = {}
    main_branch = {'011_z004p770': z0halo}

    # Create snapshot list in reverse order (present day to past) for the progenitor searching loop
    snaplist = ['000_z015p000', '001_z014p000', '002_z013p000', '003_z012p000',
                '004_z011p000', '005_z010p000', '006_z009p000', '007_z008p000',
                '008_z007p000', '009_z006p000', '010_z005p000', '011_z004p770']
    snaplist.reverse()

    # Initialise the halo's set for tree walking
    halos = {(z0halo, '011_z004p770')}

    # Initialise the forest dictionary with the present day halo as the first entry
    forest_dict[snaplist[0]] = halos

    # Initialise the set of new found halos used to loop until no new halos are found
    new_halos = halos

    # Initialise the set of found halos used to check if the halo has been found or not
    found_halos = set()

    # =============== Progenitors ===============

    count = 0

    # Loop until no new halos are found
    while len(new_halos) != 0:

        count += 1

        # Overwrite the last set of new_halos
        new_halos = set()

        # =============== Progenitors ===============

        # Loop over snapshots and progenitor snapshots
        for prog_snap, snap in zip(snaplist[1:], snaplist[:-1]):

            # Assign the halos variable for the next stage of the tree
            halos = forest_dict[snap]

            # Open this snapshots root group
            snap_tree_data = h5py.File(treepath + 'SubMgraph_' + snap + '.hdf5', 'r')

            # Loop over halos in this snapshot
            for halo in halos:

                if halo in found_halos:
                    continue

                # Assign progenitors adding the snapshot * 100000 to the ID to keep track of the snapshot ID
                # in addition to the halo ID
                forest_dict.setdefault(prog_snap, set()).update({(p, prog_snap) for p in
                                                                 snap_tree_data[str(halo[0])]['Prog_haloIDs'][...]})
            snap_tree_data.close()

            # Add any new halos not found in found halos to the new halos set
            if prog_snap in forest_dict:
                new_halos.update(forest_dict[prog_snap] - found_halos)

        # =============== Descendants ===============

        # Loop over halos found during the progenitor step
        snapshots = list(reversed(list(forest_dict.keys())))
        for desc_snap, snap in zip(snapshots[1:], snapshots[:-1]):

            # Assign the halos variable for the next stage of the tree
            halos = forest_dict[snap]

            # Open this snapshots root group
            snap_tree_data = h5py.File(treepath + 'SubMgraph_' + snap + '.hdf5', 'r')

            # Loop over the progenitor halos
            for halo in halos:

                if halo in found_halos:
                    continue

                # Load descendants adding the snapshot * 100000 to keep track of the snapshot ID
                # in addition to the halo ID
                forest_dict.setdefault(desc_snap, set()).update({(d, desc_snap) for d in
                                                                 snap_tree_data[str(halo[0])]['Desc_haloIDs'][...]})

            snap_tree_data.close()

            # Redefine the new halos set to have any new halos not found in found halos
            new_halos.update(forest_dict[desc_snap] - found_halos)

        # Add the new_halos to the found halos set
        found_halos.update(new_halos)

    forest_snaps = list(forest_dict.keys())

    for snap in forest_snaps:

        if len(forest_dict[snap]) == 0:
            del forest_dict[snap]
            continue

        forest_dict[snap] = np.array([float(halo[0]) for halo in forest_dict[snap]])

        # Open this snapshots root group
        snap_tree_data = h5py.File(treepath + 'SubMgraph_' + snap + '.hdf5', 'r')

        mass_dict[snap] = np.array([snap_tree_data[str(halo)].attrs['current_halo_nPart']
                                    for halo in forest_dict[snap]])

        snap_tree_data.close()

    gen0 = forest_dict['011_z004p770']
    root = gen0[np.argmax(mass_dict['011_z004p770'])]

    # Define the main branch start
    main = root

    # Loop over snapshots to get main branch
    for snap, prog_snap in zip(snaplist[:-1], snaplist[1:]):

        # Open this snapshots root group
        snap_tree_data = h5py.File(treepath + 'SubMgraph_' + snap + '.hdf5', 'r')
        try:
            main_branch[prog_snap] = snap_tree_data[str(main)]['Prog_haloIDs'][0]
            main = main_branch[prog_snap]
        except ValueError:
            snap_tree_data.close()
            break
        snap_tree_data.close()

    return forest_dict, main_branch, gen0, root

# SLOW SLOW SLOW
# def get_forest2(z0halo, treepath):
#     """ A funciton which traverses a tree including all halos which have interacted with the tree
#     in a 'forest/mangrove'.
#
#     :param tree_data: The tree data dictionary produced by the Merger Graph.
#     :param z0halo: The halo ID of a z=0 halo for which the forest/mangrove plot is desired.
#
#     :return: forest_dict: The dictionary containing the forest. Each key is the snapshot ID and
#              the value is a list of halos in this snapshot of the forest.
#              massgrowth: The mass history of the forest.
#              tree: The dictionary containing the tree. Each key is the snapshot ID and
#              the value is a list of halos in this snapshot of the tree.
#              main_growth: The mass history of the main branch.
#     """
#
#     # Initialise dictionary instances
#     forest_dict = {}
#     mass_dict = {}
#     main_branch = {'011_z004p770': z0halo}
#
#     # Create snapshot list in reverse order (present day to past) for the progenitor searching loop
#     snaplist = ['000_z015p000', '001_z014p000', '002_z013p000', '003_z012p000',
#                 '004_z011p000', '005_z010p000', '006_z009p000', '007_z008p000',
#                 '008_z007p000', '009_z006p000', '010_z005p000', '011_z004p770']
#
#     # Initialise the halo's set for tree walking
#     halos = {(z0halo, 11)}
#
#     # Initialise the forest dictionary with the present day halo as the first entry
#     forest_dict[snaplist[0]] = halos
#
#     # Initialise the set of new found halos used to loop until no new halos are found
#     halos_to_test = halos
#
#     # Initialise the set of found halos used to check if the halo has been found or not
#     tested_halos = set()
#
#     # =============== Progenitors ===============
#
#     # count = 0
#
#     # Loop until no new halos are found
#     while len(halos_to_test) != 0:
#
#         # count += 1
#
#         halo_tup = halos_to_test.pop()
#         halo, snap_ind = halo_tup
#         snap = snaplist[snap_ind]
#         if snap_ind - 1 < 0:
#             prog_snap = None
#         else:
#             prog_snap = snaplist[snap_ind - 1]
#         if snap_ind + 1 >= len(snaplist):
#             desc_snap = None
#         else:
#             desc_snap = snaplist[snap_ind + 1]
#
#         # Open this snapshots root group
#         snap_tree_data = h5py.File(treepath + 'SubMgraph_' + snap + '.hdf5', 'r')
#
#         # Assign progenitors and descendents including the snapshot to keep track of the snapshot
#         # in addition to the halo ID
#         if prog_snap != None:
#             progs = snap_tree_data[str(halo)]['Prog_haloIDs'][...]
#             forest_dict.setdefault(prog_snap, set()).update({(p, int(prog_snap.split('_')[0])) for p in progs})
#         if desc_snap != None:
#             descs = snap_tree_data[str(halo)]['Desc_haloIDs'][...]
#             forest_dict.setdefault(desc_snap, set()).update({(d, int(desc_snap.split('_')[0])) for d in descs})
#         snap_tree_data.close()
#
#         # Add any new halos not found in found halos to the new halos set
#         if prog_snap != None:
#             halos_to_test.update(forest_dict[prog_snap] - tested_halos)
#         if desc_snap != None:
#             halos_to_test.update(forest_dict[desc_snap] - tested_halos)
#
#         tested_halos.update({halo_tup})
#         halos_to_test = halos_to_test - tested_halos
#
#     forest_snaps = list(forest_dict.keys())
#
#     for snap in forest_snaps:
#
#         if len(forest_dict[snap]) == 0:
#             del forest_dict[snap]
#             continue
#
#         forest_dict[snap] = np.array([float(halo[0]) for halo in forest_dict[snap]])
#
#         # Open this snapshots root group
#         snap_tree_data = h5py.File(treepath + 'SubMgraph_' + snap + '.hdf5', 'r')
#
#         mass_dict[snap] = np.array([snap_tree_data[str(halo)].attrs['current_halo_nPart']
#                                     for halo in forest_dict[snap]])
#
#         snap_tree_data.close()
#
#     gen0 = forest_dict['011_z004p770']
#     root = gen0[np.argmax(mass_dict['011_z004p770'])]
#
#     # Define the main branch start
#     main = root
#
#     # Loop over snapshots to get main branch
#     for snap, prog_snap in zip(snaplist[:-1], snaplist[1:]):
#
#         # Open this snapshots root group
#         snap_tree_data = h5py.File(treepath + 'SubMgraph_' + snap + '.hdf5', 'r')
#         try:
#             main_branch[prog_snap] = snap_tree_data[str(main)]['Prog_haloIDs'][0]
#             main = main_branch[prog_snap]
#         except ValueError:
#             snap_tree_data.close()
#             break
#         snap_tree_data.close()
#
#     return forest_dict, main_branch, gen0, root


def forest_worker(z0halo, treepath):

    # Get the forest with this halo at it's root
    start = time.time()
    forest_dict = get_forest(z0halo, treepath)
    print("Completed", time.time() - start)

    print('Halo ' + str(z0halo) + '\'s Forest extracted...')

    return forest_dict


def get_evolution(path, snaps):

    # Set up dictionaries to store data
    hmrs = {}
    masses = {}
    ids = {}

    for snap in snaps:

        z_str = snap.split('z')[1].split('p')
        z = float(z_str[0] + '.' + z_str[1])

        # Define comoving softening length in kpc
        soft = 0.001802390 / 0.677 * 1 / (1 + z)

        # Get halo IDs and halo data
        subgrp_ids = E.read_array('SUBFIND', path, snap, 'Subhalo/SubGroupNumber', numThreads=8)
        grp_ids = E.read_array('SUBFIND', path, snap, 'Subhalo/GroupNumber', numThreads=8)
        gal_hmrs = E.read_array('SUBFIND', path, snap, 'Subhalo/HalfMassRad', noH=True,
                                physicalUnits=True, numThreads=8)[:, 4]
        gal_ms = E.read_array('SUBFIND', path, snap, 'Subhalo/ApertureMeasurements/Mass/030kpc',
                              noH=False, physicalUnits=False, numThreads=8)[:, 4] * 10 ** 10

        # Remove particles not associated to a subgroup
        okinds = subgrp_ids != 1073741824
        gal_hmrs = gal_hmrs[okinds]
        gal_ms = gal_ms[okinds]
        grp_ids = grp_ids[okinds]
        subgrp_ids = subgrp_ids[okinds]
        halo_ids = np.zeros(grp_ids.size, dtype=float)
        for (ind, g), sg in zip(enumerate(grp_ids), subgrp_ids):
            halo_ids[ind] = float(str(int(g)) + '.%05d' % int(sg))

        # Intialise dictionaries for each snap
        hmrs[snap] = gal_hmrs / soft
        masses[snap] = gal_ms
        ids[snap] = halo_ids

    return hmrs, masses, ids


def main_evolve_graph(reg, root_snap='011_z004p770'):
    regions = []
    for reg in range(0, 40):
        if reg < 10:
            regions.append('0' + str(reg))
        else:
            regions.append(str(reg))

    median_hmrs_dict = {}
    root_hmrs_dict = {}

    snaplist = ['000_z015p000', '001_z014p000', '002_z013p000', '003_z012p000',
                '004_z011p000', '005_z010p000', '006_z009p000', '007_z008p000',
                '008_z007p000', '009_z006p000', '010_z005p000', '011_z004p770']

    for reg in regions:

        graphpath = '/cosma/home/dp004/dc-rope1/FLARES/FLARES-1/MergerGraphs/GEAGLE_' + reg + '/'

        path = '/cosma/home/dp004/dc-rope1/FLARES/FLARES-1/G-EAGLE_' + reg + '/data'

        hmrs, masses, ids = get_evolution(path, snaplist)

        # Get halo IDs and halo data
        subgrp_ids = E.read_array('SUBFIND', path, root_snap, 'Subhalo/SubGroupNumber', numThreads=8)
        grp_ids = E.read_array('SUBFIND', path, root_snap, 'Subhalo/GroupNumber', numThreads=8)
        gal_hmrs = E.read_array('SUBFIND', path, root_snap, 'Subhalo/HalfMassRad', noH=True,
                                physicalUnits=True, numThreads=8)[:, 4]
        gal_all_ms = E.read_array('SUBFIND', path, root_snap, 'Subhalo/ApertureMeasurements/Mass/030kpc',
                                  noH=True, physicalUnits=True, numThreads=8) * 10 ** 10
        gal_ms = gal_all_ms[:, 4]
        gal_dm_ms = gal_all_ms[:, 1]

        # Define comoving softening length in kpc
        soft = 0.001802390 / 0.677 * 1 / (1 + 4.77)

        # Remove particles not associated to a subgroup
        okinds = np.logical_and(subgrp_ids != 1073741824, np.logical_and(gal_ms > 10 ** 9., gal_dm_ms != 0))
        gal_hmrs = gal_hmrs[okinds]
        gal_ms = gal_ms[okinds]
        grp_ids = grp_ids[okinds]
        subgrp_ids = subgrp_ids[okinds]
        halo_ids = np.zeros(grp_ids.size, dtype=float)
        for (ind, g), sg in zip(enumerate(grp_ids), subgrp_ids):
            halo_ids[ind] = float(str(int(g)) + '.%05d' % int(sg))

        print(len(halo_ids), "halos to build forests for, in region", reg)

        done_halos = set()

        median_hmrs = np.zeros(len(halo_ids))
        root_hmrs = np.zeros(len(halo_ids))

        ind = 0

        for root, hr, m in zip(halo_ids, gal_hmrs, gal_ms):

            print(len(done_halos))

            if root in done_halos:
                continue

            # Get the graph
            forest, main_branch, gen0, root = forest_worker(root, graphpath)

            done_halos.update(gen0)

            root_hmrs[ind] = hr / soft

            # Loop over main branch getting hmr over evolution
            hmrs_mb = []
            for s in main_branch.keys():
                hmrs_mb.append(hmrs[s][ids[s] == main_branch[s]][0])

            median_hmrs[ind] = root_hmrs[ind] / np.median(hmrs_mb)

            ind += 1

        median_hmrs_dict[reg] = median_hmrs[:ind]
        root_hmrs_dict[reg] = root_hmrs[:ind]

    median_hmrs = np.concatenate(list(median_hmrs_dict.values()))
    root_hmrs = np.concatenate(list(root_hmrs_dict.values()))

    fig = plt.figure()
    ax = fig.add_subplot(111)

    cbar = ax.hexbin(root_hmrs, median_hmrs, gridsize=50, mincnt=1, xscale='log',
                     yscale='log', norm=LogNorm(), linewidths=0.2, cmap='viridis')

    ax.set_xlabel("$R_{1/2, \mathrm{root}} / \epsilon$")
    ax.set_ylabel("$R_{1/2, \mathrm{root}} / R_{1/2, 50^{\mathrm{th}}}$")

    fig.colorbar(cbar)

    fig.savefig("plots/Evolution/hmrevo_50thpcent.png", bbox_inches="tight")


main_evolve_graph('00', root_snap='011_z004p770')
