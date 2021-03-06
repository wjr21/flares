#!/cosma/home/dp004/dc-rope1/.conda/envs/flares-env/bin/python
import matplotlib
matplotlib.use('Agg')
import numpy as np
import sphviewer as sph
from sphviewer.tools import cmaps
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.spatial import ConvexHull
import eagle_IO as E
import sys


def _sphere(coords, a, b, c, r):

    # Equation of a sphere
    x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]

    return (x - a) ** 2 + (y - b) ** 2 + (z - c) ** 2 - r ** 2


def spherical_region(sim, snap):
    """
    Inspired from David Turner's suggestion
    """

    dm_cood = E.read_array('PARTDATA', sim, snap, '/PartType1/Coordinates',
                           noH=True, physicalUnits=False, numThreads=8)  # dm particle coordinates

    hull = ConvexHull(dm_cood)

    cen = [np.median(dm_cood[:, 0]), np.median(dm_cood[:, 1]), np.median(dm_cood[:,2])]
    pedge = dm_cood[hull.vertices]  #edge particles
    y_obs = np.zeros(len(pedge))
    p0 = np.append(cen, 15 / 0.677)

    popt, pcov = curve_fit(_sphere, pedge, y_obs, p0, method='lm', sigma=np.ones(len(pedge)) * 0.001)
    dist = np.sqrt(np.sum((pedge-popt[:3])**2, axis=1))
    centre, radius, mindist = popt[:3], popt[3], np.min(dist)

    return centre, radius, mindist


def get_sphere_data(path, snap, part_type, soft):

    # Get positions masses and smoothing lengths
    poss = E.read_array('SNAP', path, snap, 'PartType' + str(part_type) + '/Coordinates',
                        noH=True, numThreads=8)
    masses = E.read_array('SNAP', path, snap, 'PartType' + str(part_type) + '/Mass',
                          noH=True, numThreads=8) * 10**10
    if part_type != 1:
        smls = E.read_array('SNAP', path, snap, 'PartType' + str(part_type) + '/SmoothingLength',
                            noH=True, numThreads=8)
    else:
        smls = np.full_like(masses, soft)

    return poss, masses, smls


def single_sphere(reg, snap, part_type, soft, t=0, p=0, num=0):

    # Define path
    path = '/cosma/home/dp004/dc-rope1/FLARES/FLARES-1/G-EAGLE_' + reg + '/data'

    # Get plot data
    poss, masses, smls = get_sphere_data(path, snap, part_type, soft)

    # Get the spheres centre
    centre, radius, mindist = spherical_region(path, snap)

    # Centre particles
    poss -= centre

    # Remove boundary particles
    r = np.linalg.norm(poss, axis=1)
    okinds = r < 14 / 0.677
    poss = poss[okinds, :]
    masses = masses[okinds]
    smls = smls[okinds]

    print('There are', len(masses), 'in the region')

    fig = plt.figure(1, figsize=(7, 7))

    Particles = sph.Particles(poss, masses, smls)

    lbox = (15/0.677) * 2
    Camera = sph.Camera(r=lbox / 2., t=t, p=p, roll=0, xsize=500, ysize=500, x=0, y=0, z=0,
                        extent=[-lbox / 2., lbox / 2., -lbox / 2., lbox / 2.])
    Scene = sph.Scene(Particles, Camera)
    Render = sph.Render(Scene)
    extent = Render.get_extent()
    img = Render.get_image()

    plt.imshow(np.log10(img), cmap=cmaps.twilight(), extent=extent, origin='lower')
    plt.axis('off')

    if len(str(num)) == 1:
        save_num = '00000' + str(num)
    elif len(str(num)) == 2:
        save_num = '0000' + str(num)
    elif len(str(num)) == 3:
        save_num = '000' + str(num)
    elif len(str(num)) == 4:
        save_num = '00' + str(num)
    elif len(str(num)) == 5:
        save_num = '0' + str(num)

    fig.savefig('plots/spheres/single_sphere_reg' + reg + '_snap' + snap + '_PartType' + str(part_type)
                    + '_angle' + save_num + '.png',
                    bbox_inches='tight')


# Define softening lengths
csoft = 0.001802390 / 0.677

# # Define region list
# regions = []
# for reg in range(0, 40):
#     if reg < 10:
#         regions.append('0' + str(reg))
#     else:
#         regions.append(str(reg))
#
# # Define snapshots
# snaps = ['000_z015p000', '001_z014p000', '002_z013p000', '003_z012p000', '004_z011p000', '005_z010p000',
#          '006_z009p000', '007_z008p000', '008_z007p000', '009_z006p000', '010_z005p000', '011_z004p770']
#
# # Define a list of regions and snapshots
# reg_snaps = []
# for snap in snaps:
#
#     for reg in regions:
#
#         reg_snaps.append((reg, snap))

ind = int(sys.argv[1])
# print(reg_snaps[ind])
# reg, snap = reg_snaps[ind]
reg, snap = '00', '011_z004p770'
ps = np.linspace(0, 360, 360)
single_sphere(reg, snap, part_type=0, soft=csoft, p=ps[ind], num=ind)
