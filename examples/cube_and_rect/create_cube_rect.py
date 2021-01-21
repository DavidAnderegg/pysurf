"""
This is an example script to show the entire process of creating overset
meshes using the MDOlab's tools. Here, we have a cube that is intersecting
a rectangular prism with one of the cube's edges being a symmetry plane.

|
|---------------+
|               |
|               +---------------------+
|               |                     |
|               +---------------------+
|               |          rect
|---------------+
|         cube
sym

We defined functions to call individual tools from the group to create
these meshes. Each will be explained in its docstring.

John Jasa 2017-01

"""

# IMPORTS
import pysurf
from mpi4py import MPI
import numpy as np
import os
from pyhyp import pyHyp
from pywarpustruct import USMesh
from scipy.spatial import cKDTree
import subprocess


def extrude_cube_volume_mesh():
    """
    First we need to create a primary volume mesh for the cube.
    We already have a structured surface mesh in `cube_struct.cgns`.
    Next, we use pyHyp to hyperbollicaly extrude a volume mesh.
    Note that we need to set the symmetry boundary condition in the options.
    """

    # Input filename for pyHyp
    fileName = "../inputs/cube_struct.cgns"

    options = {
        # ---------------------------
        #        Input Parameters
        # ---------------------------
        "inputFile": fileName,
        "fileType": "CGNS",
        "unattachedEdgesAreSymmetry": True,
        "outerFaceBC": "overset",
        "autoConnect": True,
        "families": "wall",
        # ---------------------------
        #        Grid Parameters
        # ---------------------------
        "N": 9,
        "s0": 1.0e-1,
        "marchDist": 1.2,
        "splay": 0.2,
        # ---------------------------
        #   Pseudo Grid Parameters
        # ---------------------------
        "ps0": -1,
        "pGridRatio": -1,
        "cMax": 50,
        # ---------------------------
        #   Smoothing parameters
        # ---------------------------
        "epsE": 0.10,
        "epsI": 2.0,
        "theta": 3.0,
        "volCoef": 0.25,
        "volBlend": 0.01,
        "volSmoothIter": 400,
    }

    hyp = pyHyp(options=options)
    hyp.run()
    hyp.writeCGNS("cube_vol.cgns")


def extrude_rect_volume_mesh():
    """
    Next we need to create a primary volume mesh for the rectangular prism.
    We already have a structured surface mesh in `rect_struct.cgns`.
    Next, we use pyHyp to hyperbollicaly extrude a volume mesh.
    Note that we need to set the symmetry boundary condition in the options.
    """
    fileName = "../inputs/rect_struct.cgns"

    options = {
        # ---------------------------
        #        Input Parameters
        # ---------------------------
        "inputFile": fileName,
        "fileType": "CGNS",
        "unattachedEdgesAreSymmetry": True,
        "outerFaceBC": "overset",
        "autoConnect": True,
        "BC": {},
        "families": "wall",
        # ---------------------------
        #        Grid Parameters
        # ---------------------------
        "N": 9,
        "s0": 1.0e-1,
        "marchDist": 1.2,
        "splay": 0.2,
        # ---------------------------
        #   Pseudo Grid Parameters
        # ---------------------------
        "ps0": -1,
        "pGridRatio": -1,
        "cMax": 50,
        # ---------------------------
        #   Smoothing parameters
        # ---------------------------
        "epsE": 0.10,
        "epsI": 1.0,
        "theta": 3.0,
        "volCoef": 0.25,
        "volBlend": 0.01,
        "volSmoothIter": 400,
    }

    hyp = pyHyp(options=options)
    hyp.run()
    hyp.writeCGNS("rect_vol.cgns")

    print(rectTranslation)
    # Translate wing primary mesh
    subprocess.call(["cp rect_vol.cgns rect_vol_temp.cgns"], shell=True)
    subprocess.call(
        [
            "cgns_utils translate rect_vol_temp.cgns {} {} {}".format(
                rectTranslation[0], rectTranslation[1], rectTranslation[2]
            )
        ],
        shell=True,
    )


def march_surface_meshes():
    """
    Now we will march the surface meshes on both the cube and the rectangle
    using the intersection curve as the starting curve.
    We do this using hypsurf, the included surface meshing tool.
    """

    # Load components
    comp1 = pysurf.TSurfGeometry("../inputs/cube_uns.cgns", ["geom"])
    comp2 = pysurf.TSurfGeometry("../inputs/rect_uns.cgns", ["geom"])

    name1 = comp1.name
    name2 = comp2.name

    # ADDING GUIDE CURVES
    # Create curve dictionary based on imported curves
    # !!! Make sure to call `extract_curves.py` before running this script
    curves = []
    curves.append(pysurf.tsurf_tools.read_tecplot_curves("extracted_curve_000.plt"))
    curves.append(pysurf.tsurf_tools.read_tecplot_curves("extracted_curve_001.plt"))
    curves.append(pysurf.tsurf_tools.read_tecplot_curves("extracted_curve_002.plt"))
    curves.append(pysurf.tsurf_tools.read_tecplot_curves("extracted_curve_003.plt"))

    # Create an empty list in which we'll store the long (longitudinal) edges of
    # the rect
    long_curves = []
    counter = 0

    # Examine each of the imported curves
    for ext_curve in curves:

        # Split these curves based on sharpness to get all edges of the rect
        split_curve = pysurf.tsurf_tools.split_curve_single(ext_curve[ext_curve.keys()[0]], "int", criteria="sharpness")

        # Loop over these split curves
        for name in split_curve:

            # Give the curves new names so they do not conflict with each other
            split_curve[name].name = "int_" + "{}".format(counter).zfill(3)
            counter += 1

            # Extract the curve points and compute the length
            pts = split_curve[name].get_points()
            length = pts[2, 0] - pts[2, -1]

            # Hardcoded logic here based on the length of edges
            if np.abs(length) > 1:

                # Flip the long curve if it's facing the 'wrong' direction
                if length > 0:
                    split_curve[name].flip()

                # Add the long curve to the list
                long_curves.append(split_curve[name])

    # Create a list of guideCurves based on the extracted long curves
    # Note here we need the strings, not the curve objects.
    # We use the same loop to add the guide curves to the rectangle object
    guideCurves = []
    for ext_curve in long_curves:
        print(ext_curve.name)
        comp2.add_curve(ext_curve)
        # if ext_curve.name != 'int_011':
        guideCurves.append(ext_curve.name)

    # Rotate the rectangle in 5 degrees
    # comp2.rotate(5,2)

    # Create manager object and add the geometry objects to it
    manager0 = pysurf.Manager()
    manager0.add_geometry(comp1)
    manager0.add_geometry(comp2)

    distTol = 1e-7

    # Set up integer to export different meshes
    mesh_pass = 0

    # ======================================================
    # FORWARD PASS

    def forward_pass(manager):

        """
        This function will apply all geometry operations to the given manager.
        """

        # INTERSECT

        # Call intersection function
        intCurveNames = manager.intersect(distTol=distTol)
        intCurveName = intCurveNames[0]

        # Split the intersection curve based on sharpness
        curveNames = manager.split_intCurve(intCurveName)

        # Set the remesh options
        optionsDict = {"nNewNodes": 21, "spacing": "linear"}

        # Remesh each side of the intersection curve
        remeshed_curves = []
        for curveName in curveNames:
            remeshed_curves.append(manager.remesh_intCurve(curveName, optionsDict))

        # Merge the four split curves back into one intersection curve
        manager.merge_intCurves(remeshed_curves, "intersection")

        # This isn't the most elegant way to shift the nodes, but this allows
        # us to use all four of the extracted curves as guide curves
        manager.intCurves["intersection"].shift_end_nodes(criteria="startPoint", startPoint=np.array([1.5, 1.5, 1.5]))

        manager.intCurves["intersection"].export_tecplot("intersection")

        # MARCH SURFACE MESHES
        meshName = "mesh"

        options_rect = {
            "bc1": "continuous",
            "bc2": "continuous",
            "dStart": 0.03,
            "numLayers": 17,
            "extension": 3.5,
            "epsE0": 4.5,
            "theta": -0.5,
            "alphaP0": 0.25,
            "numSmoothingPasses": 0,
            "nuArea": 0.16,
            "numAreaPasses": 20,
            "sigmaSplay": 0.3,
            "cMax": 10000.0,
            "ratioGuess": 1.5,
            "guideCurves": guideCurves,
        }

        options_cube = {
            "bc1": "continuous",
            "bc2": "continuous",
            "dStart": 0.02,
            "numLayers": 17,
            "extension": 2.5,
            "epsE0": 4.5,
            "theta": -0.5,
            "alphaP0": 0.25,
            "numSmoothingPasses": 0,
            "nuArea": 0.16,
            "numAreaPasses": 20,
            "sigmaSplay": 0.3,
            "cMax": 10000.0,
            "ratioGuess": 1.5,
        }

        meshName = "mesh"
        meshNames = manager.march_intCurve_surfaceMesh(
            "intersection", options0=options_cube, options1=options_rect, meshName=meshName
        )

        # EXPORT
        for meshName in meshNames:
            print(meshName + ".xyz")
            manager.meshes[meshName].exportPlot3d(meshName + ".xyz")

        return meshNames

    # END OF forward_pass
    # ======================================================

    # Call the forward pass function to the original manager
    meshNames = forward_pass(manager0)
    mesh_pass = mesh_pass + 1

    """
    This function takes the two blocks that define the collar mesh
    and joins them so that we can run pyHyp
    """

    manager0.merge_meshes(meshNames, [[1, 0, 0], [0, 1, 0]])
    # manager0.merge_meshes(meshNames, [[0, 0, 0], [0, 0, 0]])

    # Copy the numpy array containing coordinate info from the surface mesh
    # of the collar so we can access it later without recreating the mesh.
    subprocess.call(["cp merged.npy merged_" + str(i).zfill(2) + ".npy"], shell=True)

    return name1, name2, manager0


def run_pyhyp_for_collar():
    """
    Now that we have the merged surface mesh for the collar between the
    cube and rect, we need to run pyHyp to extrude a volume mesh for the collar.
    """

    print()
    print("Now running pyHyp on the merged mesh")
    print()

    fileName = "merged.xyz"
    fileType = "plot3d"

    options = {
        # ---------------------------
        #        Input Parameters
        # ---------------------------
        "inputFile": fileName,
        "fileType": fileType,
        "unattachedEdgesAreSymmetry": False,
        "outerFaceBC": "overset",
        "autoConnect": True,
        "BC": {},
        "families": "wall",
        # ---------------------------
        #        Grid Parameters
        # ---------------------------
        "N": 35,
        "s0": 1e-2,
        "marchDist": 1.3,
        "splay": 0.7,
        # ---------------------------
        #   Pseudo Grid Parameters
        # ---------------------------
        "ps0": -1,
        "pGridRatio": -1,
        "cMax": 5,
        # ---------------------------
        #   Smoothing parameters
        # ---------------------------
        "epsE": 5.0,
        "epsI": 10.0,
        "theta": 3.0,
        "volCoef": 0.25,
        "volBlend": 0.01,
        "volSmoothIter": 400,
    }

    hyp = pyHyp(options=options)
    hyp.run()
    hyp.writeCGNS("collar.cgns")

    subprocess.call(["cp collar.cgns collar_master.cgns"], shell=True)

    # Set options for the pywarpustruct instance
    options = {
        "gridFile": "collar_master.cgns",
        "fileType": "CGNS",
        "specifiedSurfaces": None,
        "symmetrySurfaces": None,
        "symmetryPlanes": [],
        "aExp": 3.0,
        "bExp": 5.0,
        "LdefFact": 100.0,
        "alpha": 0.25,
        "errTol": 0.0001,
        "evalMode": "fast",
        "useRotations": True,
        "zeroCornerRotations": True,
        "cornerAngle": 30.0,
        "bucketSize": 8,
    }

    # Create the mesh object using pywarpustruct
    mesh = USMesh(options=options, comm=MPI.COMM_WORLD)

    # Get the initial coordinates in the order that the mesh object
    # uses them
    warp_coords = mesh.getSurfaceCoordinates()

    # Load the coordinates from the collar surface mesh we marched
    # earlier. Note that here in the first iteration the coordinate
    # points between this and the warp coords should be exactly the same.
    #
    # However, their order is not the same, so we must match the
    # coordinate points and save the indices so that we can reorder
    # our future surface marched points into the order that
    # pywarpustruct expects.
    march_coords = np.load("merged.npy")

    # To do this, we set up a KDTree using the pySurf generated
    # surface mesh coordinates.
    tree = cKDTree(march_coords)

    # We then query this tree with the warp coordinates to obtain
    # `pySurf2pyWarp`, the mapping of the coordinate points.
    d, pySurf2pyWarp = tree.query(warp_coords)

    tree = cKDTree(warp_coords)
    d, pyWarp2pySurf = tree.query(march_coords)

    return mesh, pySurf2pyWarp, pyWarp2pySurf


def run_pywarp_for_collar(mesh, pySurf2pyWarp, pyWarp2pySurf):

    print("Using previously created volume mesh and warping it to the new surface.\n")
    coords = np.load("merged.npy")

    # Here we use the remapped coordinate points to pass in to
    # pywarpustruct.
    mesh.setSurfaceCoordinates(coords[pySurf2pyWarp])

    # Actually warp the mesh and then write out the new volume mesh.
    mesh.warpMesh()
    mesh.writeGrid("collar.cgns")

    np.random.seed(314)

    dXsd = np.random.random((mesh.nSurf, 3))
    dXvWarpd = mesh.warpDerivFwd(dXsd, solverVec=False)

    dXvWarpb = np.random.random(mesh.warp.griddata.warpmeshdof)
    mesh.warpDeriv(dXvWarpb, solverVec=False)
    dXsb = mesh.getdXs()

    dotProd = 0.0
    dotProd += np.sum(dXvWarpd * dXvWarpb)
    dotProd -= np.sum(dXsb * dXsd)
    print("pyWarp dot-product:", dotProd)
    print()


def create_OCart_mesh_and_merge():
    """
    Now that we have two primary meshes and the collar mesh, we only need a
    background mesh to complete our overset mesh system.
    To create this background mesh, we use cgns_utils to create an OCart mesh,
    which has a uniformly sized cartesian mesh overlapping the existing bodies,
    then calls pyHyp to extrude an O mesh around this block.
    """

    print()
    print("Now creating OCart mesh")
    print()

    subprocess.call(["cgns_utils combine cube_vol.cgns rect_vol_temp.cgns collar.cgns half_full.cgns"], shell=True)

    # Now create the background mesh
    # positional arguments:
    #  gridFile    Name of input CGNS file
    #  dh          Uniform cartesian spacing size
    #  hExtra      Extension in "O" dimension
    #  nExtra      Number of nodes to use for extension
    #  sym         Normal for possible sym plane
    #  mgcycle     Minimum MG cycle to enforce
    #  outFile     Name of output CGNS file
    subprocess.call(["cgns_utils simpleOCart half_full.cgns 0.1 5. 9 z 1 background.cgns"], shell=True)

    # Now combine everything in a single file
    subprocess.call(["cgns_utils combine half_full.cgns background.cgns full.cgns"], shell=True)

    # Use cgns_utils to merge contiguous blocks
    subprocess.call(["cgns_utils merge full.cgns"], shell=True)

    # Check block-to-block connectivities
    subprocess.call(["cgns_utils connect full.cgns"], shell=True)


def run_ADflow_to_check_connections():
    """
    Lastly, we run ADflow to check the domain connectivity between the overset
    meshes. Note that it doesn't make sense to actually run CFD on these
    bodies, but this serves as a simple example case to create a collar mesh.
    """

    # ======================================================================
    #         Import modules
    # ======================================================================
    import numpy
    import argparse
    from mpi4py import MPI
    from baseclasses import AeroProblem
    from tripan import TRIPAN
    from adflow import ADFLOW
    from repostate import saveRepositoryInfo

    # ======================================================================
    #         Input Information
    # ======================================================================

    outputDirectory = "./"
    saveRepositoryInfo(outputDirectory)

    # Default to comm world
    comm = MPI.COMM_WORLD

    # Common aerodynamic problem description and design variables
    ap = AeroProblem(
        name="fc", alpha=1.4, mach=0.1, altitude=10000, areaRef=45.5, chordRef=3.25, evalFuncs=["cl", "cd"]
    )

    AEROSOLVER = ADFLOW

    CFL = 1.0
    MGCYCLE = "sg"
    MGSTART = 1
    useNK = False

    aeroOptions = {
        # Common Parameters
        "gridFile": "full.cgns",
        "outputDirectory": outputDirectory,
        # Physics Parameters
        "equationType": "rans",
        "smoother": "dadi",
        "liftIndex": 2,
        # Common Parameters
        "CFL": CFL,
        "CFLCoarse": CFL,
        "MGCycle": MGCYCLE,
        "MGStartLevel": MGSTART,
        "nCyclesCoarse": 250,
        "nCycles": 1000,
        "monitorvariables": ["resrho", "cl", "cd"],
        "volumevariables": ["resrho", "blank"],
        "surfacevariables": ["cp", "vx", "vy", "vz", "mach", "blank"],
        "nearWallDist": 0.1,
        "nsubiterturb": 3,
        "useNKSolver": useNK,
        # Debugging parameters
        "debugzipper": True,
        "writeTecplotSurfaceSolution": True,
    }

    # Create solver
    CFDSolver = AEROSOLVER(options=aeroOptions, comm=comm, debug=True)

    # Here we just want to check flooding
    CFDSolver.setAeroProblem(ap)
    CFDSolver.writeSolution()

    subprocess.call(["cp fc_-001_surf.plt fc_surf_" + str(i).zfill(2) + ".plt"], shell=True)


n = 3
for i in range(1):

    # These settings are known to be probably incorrect for valid overset
    # mesh generation, but we are using them primarily to check derivative
    # seed passing in and out of pySurf.
    extent = 0.0011
    trans = i * extent / (n - 1)
    rectTranslation = np.array([trans, trans, trans])

    extrude_cube_volume_mesh()
    extrude_rect_volume_mesh()

    # Here we actually run all the functions we just defined.
    name1, name2, manager0 = march_surface_meshes()

    if i == 0:
        surface_mesh, pySurf2pyWarp, pyWarp2pySurf = run_pyhyp_for_collar()
    else:
        run_pywarp_for_collar(surface_mesh, pySurf2pyWarp, pyWarp2pySurf)

    create_OCart_mesh_and_merge()
    run_ADflow_to_check_connections()

    # Generate random seeds
    coor1d, curveCoor1d = manager0.geoms[name1].set_randomADSeeds(mode="forward")
    coor2d, curveCoor2d = manager0.geoms[name2].set_randomADSeeds(mode="forward")
    meshb = []
    for mesh in manager0.meshes.itervalues():
        meshb.append(mesh.set_randomADSeeds(mode="reverse"))

    mergedDerivs_b = np.random.random((manager0.mergedMeshes["collar"].n, 3))

    # Need to convert pywarpustruct input
    # mergedDerivs_b = mergedDerivs_b[pyWarp2pySurf]

    manager0.mergedMeshes["collar"].set_reverseADSeeds(mergedDerivs_b)

    # FORWARD AD

    # Call AD code
    manager0.forwardAD()

    # Get relevant seeds
    meshd = []
    for mesh in manager0.meshes.itervalues():
        meshd.append(mesh.get_forwardADSeeds())
    mergedDerivs_d = manager0.mergedMeshes["collar"].mergedDerivs_d

    # REVERSE AD

    # Call AD code
    manager0.reverseAD()

    # Get relevant seeds
    coor1b, curveCoor1b = manager0.geoms[name1].get_reverseADSeeds()
    coor2b, curveCoor2b = manager0.geoms[name2].get_reverseADSeeds()

    # Dot product test
    dotProd = 0.0
    for ii in range(len(meshd)):
        dotProd = dotProd + np.sum(meshd[ii] * meshb[ii])
    dotProd = dotProd - np.sum(coor1b * coor1d)
    dotProd = dotProd - np.sum(coor2b * coor2d)
    for curveName in curveCoor1b:
        dotProd = dotProd - np.sum(curveCoor1d[curveName] * curveCoor1b[curveName])
    for curveName in curveCoor2b:
        dotProd = dotProd - np.sum(curveCoor2d[curveName] * curveCoor2b[curveName])

    print("no merged dot-product here")
    print(dotProd)
    print()

    # Dot product test
    dotProd = 0.0
    for ii in range(len(meshd)):
        dotProd = dotProd + np.sum(mergedDerivs_d * mergedDerivs_b)
    dotProd = dotProd - np.sum(coor1b * coor1d)
    dotProd = dotProd - np.sum(coor2b * coor2d)
    for curveName in curveCoor1b:
        dotProd = dotProd - np.sum(curveCoor1d[curveName] * curveCoor1b[curveName])
    for curveName in curveCoor2b:
        dotProd = dotProd - np.sum(curveCoor2d[curveName] * curveCoor2b[curveName])

    print("Full dot-product here")
    print(dotProd)
    print()

    print("fwd seeds pysurf ordering")
    print(manager0.mergedMeshes["collar"].mergedDerivs_d)

    # This is what we'd give to pywarpustruct
    meshd = manager0.mergedMeshes["collar"].mergedDerivs_d[pySurf2pyWarp]
    print("fwd seeds pywarp ordering")
    print(meshd)

    for entry in sorted(pySurf2pyWarp):
        print(entry)
    for entry in sorted(pyWarp2pySurf):
        print(entry)
