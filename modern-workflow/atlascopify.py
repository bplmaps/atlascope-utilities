#!/usr/bin/env python3

import argparse
import fiona
import requests
import os
import json
import subprocess
from osgeo import gdal
import geopandas as gpd
from pyproj import Transformer
import numpy as np
from os import path
import traceback
import sys
import glob

parser = argparse.ArgumentParser(description='Tools to help in the process of geotransforming urban atlases.')
parser.add_argument('--step', metavar='{download-inputs, create-footprint, warp-plates, mosaic-plates, create-xyz}', type=str, 
                    help='steps to execute (default: download-inputs)', default='download-inputs', dest='step')
parser.add_argument('--identifier', type=str, 
                    help='commonwealth id', dest='identifier')

args = parser.parse_args()

# we run the `downloadInputs` function
# to pull all of the necessary georeference annotations
# and TIFF images onto our local machine

def downloadInputs(identifier):

    # ask allmaps API what the Allmaps ID is for the Commonwealth Manifest ID we sent over

    allmapsAPIRequest = requests.get(f'https://annotations.allmaps.org/?url=https://www.digitalcommonwealth.org/search/{identifier}/manifest.json')
    allmapsManifest = allmapsAPIRequest.json()
    
    counter = 0

    # create an empty list to hold the images we're going to later download
    imagesList = []

    # use the Allmaps API to
    # iterate through images in a 
    # get all the Map IDs

    for item in allmapsManifest['items']:

        allmapsMapID = item['id']
        mapURL = f'https://annotations.allmaps.org/maps/{allmapsMapID}'
        print(f'⤵️ Downloading annotation {mapURL}')
            
        # download each JSON annotation for each of those Map IDs

        annoRequest = requests.get(mapURL, stream=True)
        allmapsAnnotation = annoRequest.json()

        # write all the images we're later going to need to download into an array,
        # but skip if image already appears in array
        # so we don't download multiple times.
        # then rewrite the jpg suffix to tif

        for item in allmapsAnnotation["items"]:
            if item["target"]["source"].replace(".jpg", ".tif") not in imagesList:
                imagesList.append( item["target"]["source"].replace(".jpg", ".tif") )

        with open(f'./tmp/annotations/{allmapsMapID}.json', 'w') as f:
            json.dump(allmapsAnnotation, f)

        counter = counter+1
    
    print("✅ All annotations downloaded!")

    # now walk through all the images that were mentioned in annotations

    for image in imagesList:

        imgFile = f'./tmp/img/{image.split("commonwealth:")[1][0:9] }.tif'
        isFile = os.path.isfile(imgFile)
        print(image)

        # check if image file already exists
        # if so, skip; otherwise, download
        
        if isFile == True:
            print(f'⏭️ Skipping {imgFile}, already exists...')
        else:
            print(f'⤵️ Downloading image {image}')

            imageRequest = requests.get(image, stream=True)

            with open(imgFile, 'wb') as fd:
                for chunk in imageRequest.iter_content(chunk_size=128):
                    fd.write(chunk)

    print("✅ All images downloaded!")
    print(" ")
    print("You can now proceed to the `allmaps-transform` step.")
    print(" ")

# we run the `allmapsTransform` function
# to transform the Allmaps pixel mask
# into a .geojson

def allmapsTransform():
    
    if not os.path.exists('./tmp/annotations/transformed'):
        os.mkdir('./tmp/annotations/transformed') 

    path = "./tmp/annotations/"
    outPath = path+"transformed/"

    mergeArray = []
    
    for f in os.listdir(path):
        isFile = os.path.isfile(path+f)
        if not f.startswith('.') and isFile == True:
            print(f'⤵️ Transforming {f} into a geojson...')
            name = os.path.splitext(f)[0]+'-transformed.geojson'
            footprint = open(outPath+name, "w")
            
            cmd = [
                "allmaps", "transform", "pixel-mask", f
            ]

            subprocess.run(
                cmd,
                cwd=path,
                stdout=footprint
            )

            # just to be safe,
            # close geojsons using geopandas

            schema = {"geometry": "Polygon", "properties": {"imageUri": "str"}}
            gdf = gpd.read_file(outPath+name)
            gdf.to_file(outPath+name, driver="GeoJSON", schema=schema)
    
    print("✅ All pixel masks transformed!")
    print(" ")
    print("Generating boundary file...")
    print(" ")

    masks = glob.iglob(outPath+'*.geojson')
    gdfs = [gpd.read_file(mask) for mask in masks]
    # print(gdfs)

    merged = gpd.pd.concat(gdfs)
    dissolved = merged.dissolve()
    dissolved.to_file("output/footprint.geojson", driver="GeoJSON", schema=schema)

    # for l in os.listdir(outPath):
    #     mergeArray.append(l)
    
    # mergeLayers = gpd.read_file(mergeArray)
    # merged = gpd.pd.concat(mergeLayers)
    # merged.to_file(outPath+"boundry.geojson", driver="GeoJSON", schema=schema)

    print("✅ Boundary file generated!")
    print("You can now proceed to the `warp-plates` step.")
    print(" ")

    return

def warpPlates():

    print(f'🏔 Registering GCPs from annotation')

    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    
    path="./tmp/annotations/"

    for file in os.listdir(path):
        isFile = os.path.isfile(path+file)
        if not file.startswith('.') and isFile == True:

            anno = open(path+file)

            annoJson = json.load(anno)
            commonwealthUrl = annoJson['items'][0]['target']['source']
            commId = (commonwealthUrl[57:-24])
            
            gcps = []
            for gcp in annoJson['items'][0]['body']['features']:
                    xt, yt = transformer.transform(
                        gcp['geometry']['coordinates'][0], gcp['geometry']['coordinates'][1])
                    line = float(gcp['properties']['pixelCoords'][1])
                    pixel = float(gcp['properties']['pixelCoords'][0])
                    g = gdal.GCP(xt, yt, 0, pixel, line)
                    gcps.append(g)

            sourceImg = gdal.Open(f'./tmp/img/{commId}.tif')

            # # for b in [1, 2, 3]:
            # # 	band = archivalImage.GetRasterBand(b)
            # # 	readableBand = band.ReadAsArray()
            # # 	readableBand[np.where(readableBand == 0)] = 1

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

            print(f'💫 Creating warped TIFF in EPSG:3857 for {mapId}.json')

            warpedPlate = f'./tmp/warped/{mapId}-warped.tif'
            isFile = os.path.isfile(warpedPlate)

            # check if warped map already exists
            # if so, skip; otherwise, warp
            
            if isFile == True:
                print(f'⏭️ Skipping {warpedPlate}, already exists...')
            else:

                gdal.Warp(f'./tmp/warped/{mapId}-warped.tif',
                            f'./tmp/img/{mapId}-translated.tif', options=warpOptions)

                print(f'🚮 Deleting temporary translate file for {mapId}.json')
                os.remove(f'./tmp/img/{mapId}-translated.tif')

    print("✅ All maps have been warped!")
    print(" ")
    print("You can now proceed to the final step, `mosaic-plates`.")
    print(" ")

def mosaicPlates():

    warpedPlates = []
    path = "./tmp/warped/"

    for f in os.listdir(path):
        isFile = os.path.isfile(path+f)
        if not f.startswith('.') and isFile == True and f.endswith('.tif'):
            warpedPlates.append(path+f)

    print('➡️  Beginning to create VRT')

    vrtOptions = gdal.BuildVRTOptions(
        resolution = 'highest',
        outputSRS = 'EPSG:3857',
        separate = False,
        srcNodata = 0
        )

    gdal.BuildVRT('output/mosaic.vrt', warpedPlates, options=vrtOptions)

    print('🎉 Completed creating the VRT. You can now run the final command, `create-xyz`!')

    return

def createXYZ():
    path="./"
    outPath="output"
    # tiles=open(outPath, "w")

    cmd = [
        "gdal2tiles.py", "--xyz", "-z", "13-20", "--exclude", "--processes", "4", "output/mosaic.vrt", "output/tiles"
    ]

    print("Beginning to generate XYZ tiles...")

    subprocess.run(
        cmd,
        cwd=path
        # stdout=tiles
    )

    print('🎉 XYZ tiles have been created. All files are in the `output` directory, ready to be ingested into Atlascope!')

    return

def createDirectoryStructure():
    if not os.path.exists('./tmp'):
        os.mkdir('./tmp')

    if not os.path.exists('./tmp/img'):
        os.mkdir('./tmp/img')

    if not os.path.exists('./tmp/annotations'):
        os.mkdir('./tmp/annotations')

    if not os.path.exists('./tmp/warped'):
        os.mkdir('./tmp/warped')

    if not os.path.exists('./output'):
        os.mkdir('./output')


if __name__ == "__main__":

    if args.step == '':
        print("😩 You didn't pass any function to the --step flag, ya ninny! Try:")
        print("\tatlascopify.py --step download-inputs")
        print("\tatlascopify.py --step allmaps-transform")
        print("\tatlascopify.py --step warp-plates")
        print("\tatlascopify.py --step mosaic-plates")
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