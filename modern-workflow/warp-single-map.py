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

parser = argparse.ArgumentParser(description='Tools to help in the process of geotransforming urban atlases.')
parser.add_argument('--step', metavar='{download-inputs, create-footprint, warp-plates, mosaic-plates, create-xyz}', type=str, 
                    help='steps to execute (default: download-inputs)', default='download-inputs', dest='step')
parser.add_argument('--identifier', type=str, 
                    help='commonwealth id', dest='identifier')
parser.add_argument('--skip-exist', type=str,
                    help='skip if exists', dest='')

args = parser.parse_args()

def downloadInputs(identifier):

    # ask allmaps API what the Allmaps ID is for the Commonwealth Manifest ID we sent over
    allmapsAPIRequest = requests.get(f'https://annotations.allmaps.org/?url=https://www.digitalcommonwealth.org/search/{identifier}/manifest.json')
    allmapsManifest = allmapsAPIRequest.json()

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
    
    print("✅   All annotations downloaded!")

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

    print("✅   All images downloaded!")
    
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

# we run the `allmapsTransform` function
# to transform the Allmaps pixel mask
# into a .geojson






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