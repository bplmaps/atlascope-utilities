#!/usr/bin/env python3

import argparse
import requests
import os
import json
import subprocess
from osgeo import gdal
import shapely as geom
import pandas as pd
import numpy as np
import geopandas as gpd
from pyproj import Transformer
from os import path
import traceback
import glob
import csv

#########################################
#####                               #####
#####    STEP 0: set arguments      #####
#####    so script can be run       #####
#####    from the command line      #####
#####                               #####
#########################################

parser = argparse.ArgumentParser(description='Tools to help in the process of geotransforming urban atlases.')
parser.add_argument('--step', metavar='{download-inputs, allmaps-transform, warp-plates, mosaic-plates, create-xyz}', type=str, 
                    help='steps to execute (default: download-inputs)', default='download-inputs', dest='step')
parser.add_argument('--identifier', type=str, 
                    help='commonwealth id', dest='identifier')

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

    allmapsManifest = requests.get(f'https://annotations.allmaps.org/?url=https://www.digitalcommonwealth.org/search/{identifier}/manifest.json').json()

    # download each map in the manifest
    # and save as .json file

    print(" ")
    print(f"Beginning to download {len((allmapsManifest)['items'])} annotations...")
    print(" ")
    for item in allmapsManifest['items']:
        allmapsMapURL = item['id']
        print(f'⤵️ Downloading annotation {allmapsMapURL}')
        allmapsAnnotation = requests.get(allmapsMapURL, stream=True).json()
        with open(f'./tmp/annotations/{allmapsMapURL[-16:]}.json', 'w') as f:
            json.dump(allmapsAnnotation, f)
    
    print("✅   All annotations downloaded!")

    # download any images not present in directory

    for item in allmapsManifest["items"]:
        imgManifest = item["target"]["source"]["id"]
        imgID = imgManifest.split("commonwealth:")[1][0:9]
        imgURL=f"https://curator.digitalcommonwealth.org/api/filestreams/image/commonwealth:{imgID}?show_primary_url=true"      
        imgFile = f'./tmp/img/{imgID}.tif'
        if os.path.isfile(imgFile) == True:
            print(f'⏭️ Skipping {imgFile}, already exists...')
        else:
            print(f'⤵️ Downloading image {imgManifest}')
            imageRequest = requests.get(imgURL, stream=True)
            response = imageRequest.json()
            img = requests.get(response['file_set']['image_primary_url'])
            with open(imgFile, 'wb') as fd:
                for chunk in img.iter_content(chunk_size=128):
                    fd.write(chunk)

    print("✅   All images downloaded!")
    
    # create template tileJSON file

    print("Creating template `tileset.json` file...")

    template = requests.get("https://raw.githubusercontent.com/bplmaps/atlascope-utilities/master/modern-workflow/template.json").json()
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
    
    # define path variables and lists for error handling

    path = "./tmp/annotations/"
    outPath = path+"transformed/"
    invalid = []
    invalidIDs = []

    # re-download annotations if error files exist

    errorFiles = ["tmp/errors/invalidMasks.csv", "tmp/errors/invalidPoints.csv"]
    for e in errorFiles:
        errorFileExists = os.path.isfile(e)
        if errorFileExists == True:
            with open(e, 'r') as file:
                reader = csv.reader(file)
                next(reader)
                for r in reader:
                    mapURL = f'https://annotations.allmaps.org/maps/{r[1]}'
                    print(f'⤵️ Re-downloading annotation {mapURL}')
                    annoRequest = requests.get(mapURL, stream=True)
                    allmapsAnnotation = annoRequest.json()               
                    with open(f'./tmp/annotations/{r[1]}.json', 'w') as f:
                        json.dump(allmapsAnnotation, f)


    # loop through `path` and 
    # transform each JSON into GeoJSON
    # using Allmaps CLI as subprocess
    
    for f in os.listdir(path):
        mapId = os.path.splitext(f)[0]
        isFile = os.path.isfile(path+f)
        
        if not f.startswith('.') and isFile == True:
            
            d=json.load(open(path+f))
            if ((d['body']['features'])):
                
                print(f'⤵️ Transforming {f} into a geojson...')
                name = os.path.splitext(f)[0]+'-transformed.geojson'
                footprint = open(outPath+name, "w")
                cmd = ["allmaps", "transform", "resource-mask", f]  # use this to transform strictly from annotation
                # cmd = ["allmaps", "transform", "--transformation-type", "thinPlateSpline", "resource-mask", f]  # use this for TPS
                subprocess.run(cmd, cwd=path, stdout=footprint)
                plateSchema = {"geometry": "Polygon", "properties": {"imageId": "str"}}
                
                try:
                    gdf = gpd.read_file(outPath+name)
                    request = requests.get(f'https://api.allmaps.org/maps/{mapId}')
                    response = request.json()
                    uri = response['_allmaps']['id'][-16:]
                    gdf.to_file(outPath+name, driver="GeoJSON", schema=plateSchema)
                except:
                    invalid.append(f'https://editor.allmaps.org/#/mask?url={uri}/info.json')
                    invalidIDs.append(mapId)

            # save geojson to file

    if (invalid):
        print(" ")
        print("‼️   Errors were encountered. Fix the following.")
        print("‼️   Hold down `command` and double-click the links to open them in your browser.")
        print("‼️   When you're done, rerun this step.")
        print(" ")
        if os.path.exists("tmp/errors") == False:
            os.mkdir("tmp/errors")
        pd.set_option('display.max_colwidth', None)
        
        if not invalid:
            pass
        else:
            maskData = {'Allmaps Map ID': invalidIDs, 'Fix Bad Masks': invalid}
            maskDf = pd.DataFrame(data=maskData)
            print("Fix Bad Masks")
            print(" ")
            print(maskDf)
            print(" ")
            maskDf.to_csv("tmp/errors/invalidMasks.csv")
        
    # merge, dissolve, specify precision

    else:
        print("✅   All pixel masks transformed!\n")
        print("Generating `plates.geojson` file...\n")


        # merge masks using geopandas

        masks = glob.iglob(outPath+'*.geojson')
        plates = gpd.pd.concat([gpd.read_file(mask) for mask in masks])
        fields = ['identifier', 'name', 'allmapsMapID', 'digitalCollectionsPermalinkPlate']
        plates[fields] = ''
        polySchema = {"geometry": "Polygon", "properties": {"imageId": "str", "identifier": "str", "name": "str", "allmapsMapID": "str", "digitalCollectionsPermalinkPlate": "str"}}
        multipolySchema = {"geometry": "MultiPolygon", "properties": {"imageId": "str", "identifier": "str", "name": "str", "allmapsMapID": "str", "digitalCollectionsPermalinkPlate": "str"}}
        plates.to_file("output/plates.geojson", driver="GeoJSON", schema=polySchema)

        # dissolve plates file and
        # save according to geometry type
       
        try:
            diss = plates.dissolve()
            multiPolyCheck = 'MultiPolygon' in diss['geometry'].geom_type.values
            if multiPolyCheck == True:
                diss.to_file("tmp/plates-dissolved.geojson", driver="GeoJSON", schema=multipolySchema)
            else:
                diss.to_file("tmp/plates-dissolved.geojson", driver="GeoJSON", schema=polySchema)
            if os.path.exists("tmp/errors") == True:
                print("You can delete the `tmp/errors` directory.\n")
            print("✅   All `plates` files have been created!\n")
            print("You can now proceed to the `warp-plates` step.\n")
        except RuntimeError as e:
            print(e)
        
        # trim to 4 decimal pts

        out=open("plates-precise.geojson", "w")
        cmd=["mapshaper", "plates-dissolved.geojson", "-o", "precision=0.0001", "plates-precise.geojson"]
        subprocess.run(cmd, cwd="tmp/", stdout=out)
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
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    path="./tmp/annotations/"

    # loop through annotations and
    # perform GDAL warp

    for file in os.listdir(path):
        isFile = os.path.isfile(path+file)
        if not file.startswith('.') and isFile == True:

            print(f'🏔   Registering GCPs from annotation...')
            annotation = json.load(open(path+file))
            # print(annotation)
            commonwealthUrl = annotation['target']['source']['partOf'][0]['id']
            commId = (commonwealthUrl[-9:])
            
            # correlate pixel and spatial coordinates
            
            gcps = []
            for gcp in annotation['body']['features']:
                    # print(gcp['properties']['resourceCoords'])
                    xt, yt = transformer.transform(
                        gcp['geometry']['coordinates'][0], gcp['geometry']['coordinates'][1])
                    line = float(gcp['properties']['resourceCoords'][1])
                    pixel = float(gcp['properties']['resourceCoords'][0])
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
                                    polynomialOrder=1,  # comment this out for TPS
                                    resampleAlg='cubic',
                                    dstAlpha=True,
                                    dstNodata=0,
                                    xRes=0.1,
                                    yRes=0.1,
                                    targetAlignedPixels=True,
                                    cutlineDSName=cutline,
                                    cropToCutline=True,
                                    # tps=True    # comment this out for polynomial
                                    )
            warpedPlate = f'./tmp/warped/{mapId}-warped.tif'
            isFile = os.path.isfile(warpedPlate)

            if isFile == True:
                print(f'⏭️   Skipping {warpedPlate}, already exists...')
                os.remove(f'./tmp/img/{mapId}-translated.tif')
            else:
                print(f'💫 Creating warped TIFF in EPSG:3857 for {mapId}.json')
                gdal.Warp(f'./tmp/warped/{mapId}-warped.tif',
                            f'./tmp/img/{mapId}-translated.tif', options=warpOptions)

                print(f'🚮   Deleting temporary translate file for {mapId}.json')
                os.remove(f'./tmp/img/{mapId}-translated.tif')

#########################################
#####                               #####
#####     STEP 4: `mosaicPlates`    #####
#####      to create virtually      #####
#####        mosaiqued raster       #####
#####                               #####
#########################################

def mosaicPlates():

    # define vrt options and orderFile exist variable

    vrtOptions = gdal.BuildVRTOptions(
        resolution = 'highest',
        outputSRS = 'EPSG:3857',
        separate = False,
        srcNodata = 0
        )
    orderFile = os.path.exists("tmp/sort-order.txt")

    if orderFile == True:
        platesForMosaic = open("tmp/sort-order.txt", "r")
        path = "tmp/warped/"
        print('➡️  Beginning to create VRT')
        gdal.BuildVRT('tmp/mosaic.vrt', platesForMosaic, options=vrtOptions)
        print('🎉 Created the VRT. You can now run the final command, `create-xyz`!')

    else:
        platesForMosaic = []
        warpedPlates = {}
        path = "tmp/warped/"

        # sort plates from small to large

        for f in os.listdir(path):
            isFile = os.path.isfile(path+f)
            if not f.startswith('.') and isFile == True and f.endswith('.tif'):
                plate = path+f
                size = os.path.getsize(plate)
                warpedPlates[plate] = size
        sortedPlates = sorted(warpedPlates.items(), key=lambda x:x[1], reverse=True)

        # append sorted files to new list to be mosaiqued

        for f in sortedPlates:
            platesForMosaic.append(f[0])

        print('➡️  Beginning to create VRT')

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
        
    # no matter what step we're running
    # first run the directory structure function
    # to ensure that the right subdirectories exist

    createDirectoryStructure()

    if args.step == 'download-inputs':
        downloadInputs(args.identifier)
    elif args.step == 'allmaps-transform':
        allmapsTransform()
    elif args.step == 'warp-plates':
        warpPlates()
    elif args.step == 'mosaic-plates':
        mosaicPlates()
    elif args.step =='create-xyz':
        createXYZ()
    else:
        print("ERROR: Step not recognized")