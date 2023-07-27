#!/usr/bin/env python3

import argparse
import requests
import os
import json
import subprocess
from osgeo import gdal, ogr
from shapely import wkt
import shapely as geom
import pandas as pd
import numpy as np
import geopandas as gpd
from pyproj import Transformer
from os import path
import traceback
import glob

#########################################
#####                               #####
#####    STEP 0: set arguments      #####
#####    so script can be run       #####
#####    from the command line      #####
#####                               #####
#########################################

parser = argparse.ArgumentParser(description='Tools to help in the process of geotransforming urban atlases.')
parser.add_argument('--step', metavar='{download-inputs, create-footprint, warp-plates, mosaic-plates, create-xyz}', type=str, 
                    help='steps to execute (default: download-inputs)', default='download-inputs', dest='step')
parser.add_argument('--identifier', type=str, 
                    help='commonwealth id', dest='identifier')
parser.add_argument('--skip-exist', type=str,
                    help='skip if exists', dest='')
args = parser.parse_args()

#########################################
#####                               #####
#####    STEP 1: `downloadInputs`   #####
#####    to retrieve all georef     #####
#####    annotations and images     #####
#####                               #####
#########################################

def downloadInputs(identifier):

    # get Allmaps manifest as JSON
    # create empty list to hold image filenames

    allmapsAPIRequest = requests.get(f'https://annotations.allmaps.org/?url=https://www.digitalcommonwealth.org/search/{identifier}/manifest.json')
    allmapsManifest = allmapsAPIRequest.json()
    imagesList = []

    # download each map in the manifest

    print(len((allmapsManifest)['items']))
    for item in allmapsManifest['items']:
        allmapsMapID = item['id']
        mapURL = f'https://annotations.allmaps.org/maps/{allmapsMapID}'
        print(f'⤵️ Downloading annotation {mapURL}')
        annoRequest = requests.get(mapURL, stream=True)
        allmapsAnnotation = annoRequest.json()

        # add Allmaps map ID, suffixed with .tif, to image filename list

        for item in allmapsAnnotation["items"]:
            if item["target"]["source"].replace(".jpg", ".tif") not in imagesList:
                imagesList.append( item["target"]["source"].replace(".jpg", ".tif") )
        
        # save each map's georef annotation as JSON file

        with open(f'./tmp/annotations/{allmapsMapID}.json', 'w') as f:
            json.dump(allmapsAnnotation, f)
    
    print("✅   All annotations downloaded!")

    # loop through image filename list

    for image in imagesList:

        imgFile = f'./tmp/img/{image.split("commonwealth:")[1][0:9] }.tif'
        isFile = os.path.isfile(imgFile)
        
        # download any images not present in directory

        if isFile == True:
            print(f'⏭️ Skipping {imgFile}, already exists...')
        else:
            print(f'⤵️ Downloading image {image}')
            imageRequest = requests.get(image, stream=True)
            with open(imgFile, 'wb') as fd:
                for chunk in imageRequest.iter_content(chunk_size=128):
                    fd.write(chunk)

    print("✅   All images downloaded!")
    
    # create template tileJSON file

    print("Creating template `tileset.json` file...")

    template = {
        "tilejson": "2.2.0",
        "name": "place year",
        "description": "Title (Author, Year)",
        "version": "1.0.0",
        "attribution": "<a href=\"https://leventhalmap.org\">Leventhal Map & Education Center</a> at the <a href=\"https://bpl.org\">Boston Public Library</a>",
        "scheme": "xyz",
        "tiles": [
            "https://s3.us-east-2.wasabisys.com/urbanatlases/ARK_ID/tiles/{z}/{x}/{y}.png"
        ],
        "data": [
            "https://s3.us-east-2.wasabisys.com/urbanatlases/ARK_ID/plates.geojson"
        ],
        "minzoom": "13",
        "maxzoom": "20",
        "bounds": []
    }
    
    tileset = open('output/tileset.json', 'w+')
    tileset.write(json.dumps(template, indent=2))
    tileset.close()

    print("✅   Template `tileset.json` file created in `output` directory!")
    print("You can now proceed to the `allmaps-transform` step.")
    print(" ")

#########################################
#####                               #####
#####   STEP 2: `allmapsTransform`  #####
#####   to transform pixel mask     #####
#####       into a .geojson         #####
#####                               #####
#########################################

def allmapsTransform():
    
    # define path variables

    path = "./tmp/annotations/"
    outPath = path+"transformed/"
    topoCheck = []

    # loop through directory and 
    # transform each JSON into GeoJSON
    # using Allmaps CLI as subprocess
    
    for f in os.listdir(path):
        isFile = os.path.isfile(path+f)
        if not f.startswith('.') and isFile == True:
            print(f'⤵️ Transforming {f} into a geojson...')
            name = os.path.splitext(f)[0]+'-transformed.geojson'
            footprint = open(outPath+name, "w")
            cmd = ["allmaps", "transform", "pixel-mask", f]
            subprocess.run(cmd, cwd=path, stdout=footprint)
            plateSchema = {"geometry": "Polygon", "properties": {"imageUri": "str"}}
            gdf = gpd.read_file(outPath+name)

            # check topology of geojson

            topoValid = gdf.is_valid
            topoCheck.append(topoValid)

            # save geojson to file

            gdf.to_file(outPath+name, driver="GeoJSON", schema=plateSchema)
    
    print("✅   All pixel masks transformed!")
    print(" ")
    print("Generating `plates.geojson` file...")
    print(" ")

    # merge masks using geopandas

    masks = glob.iglob(outPath+'*.geojson')
    gdfs = [gpd.read_file(mask) for mask in masks]
    plates = gpd.pd.concat(gdfs)
    fields = ['identifier', 'name', 'allmapsMapID', 'digitalCollectionsPermalinkPlate']
    plates[fields] = ''
    polySchema = {"geometry": "Polygon", "properties": {"imageUri": "str", "identifier": "str", "name": "str", "allmapsMapID": "str", "digitalCollectionsPermalinkPlate": "str"}}
    multipolySchema = {"geometry": "MultiPolygon", "properties": {"imageUri": "str", "identifier": "str", "name": "str", "allmapsMapID": "str", "digitalCollectionsPermalinkPlate": "str"}}
    plates.to_file("output/plates.geojson", driver="GeoJSON", schema=polySchema)

    print("✅   `plates.geojson` file generated")

    # dissolve plates file and
    # save according to geometry type

    diss = plates.dissolve()
    multiPolyCheck = 'MultiPolygon' in diss['geometry'].geom_type.values
    if multiPolyCheck == True:
        diss.to_file("tmp/plates-dissolved.geojson", driver="GeoJSON", schema=multipolySchema)
    else:
        diss.to_file("tmp/plates-dissolved.geojson", driver="GeoJSON", schema=polySchema)

    print("✅   `plates-dissolved.geojson` file saved to `output` directory")
    print(" ")
    print("‼️‼️   Before proceeding to the `warp-plates` step, check the `plates-dissolved.geojson` file for small holes.")
    print("‼️‼️   If you find any, edit the masks in Allmaps to remove them.")

    return

#########################################
#####                               #####
#####       STEP 3: `warpPlates`    #####
#####       to turn map images      #####
#####         into GeoTIFFs         #####
#####                               #####
#########################################

def warpPlates():

    # create empty lists for error handling and
    # set transformation and path variables

    gdal.UseExceptions()
    badMaskIDs = []
    badMasks = []
    noCutlineIDs = []
    noCutlines = []
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    path="./tmp/annotations/"

    # loop through annotations and
    # perform GDAL warp

    for file in os.listdir(path):
        isFile = os.path.isfile(path+file)
        if not file.startswith('.') and isFile == True:

            print(f'🏔   Registering GCPs from annotation...')
            anno = open(path+file)
            annoJson = json.load(anno)
            commonwealthUrl = annoJson['items'][0]['target']['source']
            commId = (commonwealthUrl[57:-24])
            
            # correlate pixel and spatial coordinates
            
            gcps = []
            for gcp in annoJson['items'][0]['body']['features']:
                    xt, yt = transformer.transform(
                        gcp['geometry']['coordinates'][0], gcp['geometry']['coordinates'][1])
                    line = float(gcp['properties']['pixelCoords'][1])
                    pixel = float(gcp['properties']['pixelCoords'][0])
                    g = gdal.GCP(xt, yt, 0, pixel, line)
                    gcps.append(g)
            sourceImg = gdal.Open(f'./tmp/img/{commId}.tif')
            
            # # nearblack hack

            # for b in [1, 2, 3]:
            # 	band = archivalImage.GetRasterBand(b)
            # 	readableBand = band.ReadAsArray()
            # 	readableBand[np.where(readableBand == 0)] = 1

            # set variables for GDAL translate and
            # execute

            translateOptions = gdal.TranslateOptions(
                format='GTiff',
                GCPs=gcps,
                outputSRS='EPSG:3857'
            )
            
            mapId = os.path.splitext(file)[0]

            gdal.Translate(
                f'./tmp/img/{mapId}-translated.tif',
                sourceImg,
                options = translateOptions
            )
                        
            # set options for GDAL warp and
            # execute

            cutline = f'./tmp/annotations/transformed/{mapId}-transformed.geojson'
            warpOptions = gdal.WarpOptions(
                                    format='GTiff',
                                    copyMetadata=True,
                                    multithread=True,
                                    dstSRS="EPSG:3857",
                                    creationOptions=['COMPRESS=LZW', 'BIGTIFF=YES'],
                                    polynomialOrder=1,
                                    resampleAlg='cubic',
                                    dstAlpha=True,
                                    dstNodata=0,
                                    xRes=0.1,
                                    yRes=0.1,
                                    targetAlignedPixels=True,
                                    cutlineDSName=cutline,
                                    cropToCutline=True
                                    )
            warpedPlate = f'./tmp/warped/{mapId}-warped.tif'
            isFile = os.path.isfile(warpedPlate)

            if isFile == True:
                print(f'⏭️   Skipping {warpedPlate}, already exists...')
                os.remove(f'./tmp/img/{mapId}-translated.tif')
            else:
                try:
                    print(f'💫 Creating warped TIFF in EPSG:3857 for {mapId}.json')
                    gdal.Warp(f'./tmp/warped/{mapId}-warped.tif',
                                f'./tmp/img/{mapId}-translated.tif', options=warpOptions)

                    print(f'🚮   Deleting temporary translate file for {mapId}.json')
                    os.remove(f'./tmp/img/{mapId}-translated.tif')

                # if warp fails, detect why

                except RuntimeError as e:
                    error = str(e)
                    cutlineMissing = "cutline features"
                    
                    # get LMEC URI of this image using Allmaps API
                    # to be printed at the end of runtime
                    
                    request = requests.get(f'https://api.allmaps.org/maps/{mapId}')
                    response = request.json()
                    uri = response['image']['uri']

                    # detect `no cutline` errors
                    # this sucks though. fix later

                    if cutlineMissing in error:
                        print("⁉️   Did not get any cutline features.")
                        noCutlines.append(f'https://editor.allmaps.org/#/mask?url={uri}/info.json')
                        noCutlineIDs.append(mapId)
                        os.remove(f'./tmp/img/{mapId}-translated.tif')

                    # otherwise, detect bad masks

                    else:
                        print("❌   Warp failed due to bad mask.")

                        badMasks.append(f'https://editor.allmaps.org/#/mask?url={uri}/info.json')
                        badMaskIDs.append(mapId)
                        os.remove(f'./tmp/img/{mapId}-translated.tif')

    # print any plates that need fixing
    # as pandas dataframe

    if not (badMasks or noCutlines):
        print(" ")
        print("✅   All maps have been warped!")
        print(" ")
        print("You can now proceed to the `mosaic-plates` step.")
        print(" ")
    else:
        print(" ")
        print(f"‼️   Errors were encountered. Fix the following and then re-run steps 1-3 for this atlas.")
        print(" ")
        pd.set_option('display.max_colwidth', None)

        if not badMasks:
            pass
        else:
            maskdata = {'Allmaps Map ID': badMaskIDs, 'Fix Bad Masks': badMasks}
            maskdf = pd.DataFrame(data=maskdata)
            print("Fix Bad Masks")
            print(" ")
            print(maskdf)
            print(" ")
        if not noCutlines:
            pass
        else:
            cutlinedata = {'Allmaps Map ID': noCutlineIDs, 'Fix No Cutline': noCutlines}
            cutlinedf = pd.DataFrame(data=cutlinedata)
            print("Fix No Cutlines:")
            print(" ")
            print(cutlinedf)
            print(" ")

#########################################
#####                               #####
#####     STEP 4: `mosaicPlates`    #####
#####      to create virtually      #####
#####        mosaiqued raster       #####
#####                               #####
#########################################

def mosaicPlates():

    # define empty dict/list for holding warped plates
    # and set path

    warpedPlates = {}
    platesForMosaic = []
    path = "tmp/warped/"

    # create dict of k/v pairs with filepath: size

    for f in os.listdir(path):
        isFile = os.path.isfile(path+f)
        if not f.startswith('.') and isFile == True and f.endswith('.tif'):
            plate = path+f
            size = os.path.getsize(plate)
            warpedPlates[plate] = size
    
    # sort the dict from small to large size

    sortedPlates = sorted(warpedPlates.items(), key=lambda x:x[1], reverse=True)

    # append files to new list to be mosaiqued
    # from largest to smallest

    for f in sortedPlates:
        platesForMosaic.append(f[0])

    print('➡️  Beginning to create VRT')

    vrtOptions = gdal.BuildVRTOptions(
        resolution = 'highest',
        outputSRS = 'EPSG:3857',
        separate = False,
        srcNodata = 0
        )

    gdal.BuildVRT('tmp/mosaic.vrt', platesForMosaic, options=vrtOptions)

    print('🎉 Completed creating the VRT. You can now run the final command, `create-xyz`!')

    return

#########################################
#####                               #####
#####       STEP 5: `createXYZ`     #####
#####         to create final       #####
#####           XYZ tileset         #####
#####                               #####
#########################################

def createXYZ():
    
    path="./"
    cmd = [
        "gdal2tiles.py", "--xyz", "-z", "13-20", "--exclude", "--processes", "4", "tmp/mosaic.vrt", "output/tiles"
    ]
    print("Beginning to generate XYZ tiles...")
    subprocess.run(
        cmd,
        cwd=path
    )

    print('🎉 XYZ tiles have been created. All files are in the `output` directory, ready to be ingested into Atlascope!')

    return

#########################################
#####                               #####
#####  `createDirectoryStructure`   #####
#####   is run at every step to     #####
#####    avoid funny business       #####
#####                               #####
#########################################

def createDirectoryStructure():
    d = os.path.exists
    if not d('./tmp'):
        os.mkdir('./tmp')
    if not d('./tmp/img'):
        os.mkdir('./tmp/img')
    if not d('./tmp/annotations'):
        os.mkdir('./tmp/annotations')
    if not d('./tmp/warped'):
        os.mkdir('./tmp/warped')
    if not d('./output'):
        os.mkdir('./output')
    if not d('./tmp/annotations/transformed'):
        os.mkdir('./tmp/annotations/transformed') 

#########################################
#####                               #####
#####     define which functions    #####
#####       are associated with     #####
#####          which step           #####
#####                               #####
#########################################

if __name__ == "__main__":

    if args.step == '':
        print("😩 You didn't pass any function to the --step flag, ya ninny! Try:")
        print("\tatlascopify.py --step download-inputs")
        print("\tatlascopify.py --step allmaps-transform")
        print("\tatlascopify.py --step warp-plates")
        print("\tatlascopify.py --step mosaic-plates")
        print("\tatlascopify.py --step createXYZ")
        exit()

    else:
        
        # no matter what step we're running
        # first run the directory structure function
        # to ensure that the right subdirectories exist

        createDirectoryStructure()
    
        if args.step == 'download-inputs':
            try:
                downloadInputs(args.identifier)
            except KeyError:
                print("🚩 This collection of the manifest you entered contains no georeference annotations.")
                print(f"Begin georeferencing it at: https://editor.allmaps.org/#/collection?url=https://www.digitalcommonwealth.org/search/{args.identifier}/manifest")
                print("Read the full error below:")
                print(" ")
                print(traceback.format_exc())

        elif args.step == 'allmaps-transform':
            allmapsTransform()
        
        elif args.step == 'warp-plates':
            warpPlates()
        
        elif args.step == 'mosaic-plates':
            mosaicPlates()

        elif args.step =='create-xyz':
            createXYZ()

        else:
            print("We haven't made this step do anything yet")