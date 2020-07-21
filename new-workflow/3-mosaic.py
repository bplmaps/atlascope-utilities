import os
import gdal


# use os.walk() generates lists of root, directory, and files
for r, d, f in os.walk('./masked'):
    vrtOptions = gdal.BuildVRTOptions(
        resolution = 'highest',
        separate = False,
        outputSRS = "EPSG:4326",
        allowProjectionDifference = False
    )


    gdal.BuildVRT('mosaic.vrt', ['./masked/{}'.format(source) for source in f], options = vrtOptions)