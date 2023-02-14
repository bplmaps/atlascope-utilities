#!/usr/bin/env python3

import argparse
import requests
import os
import json
import subprocess
from subprocess import Popen, PIPE
from os import path


parser = argparse.ArgumentParser(description='Tools to help in the process of geotransforming urban atlases.')
parser.add_argument('--step', metavar='{download-inputs, create-footprint, warp-plates}', type=str, 
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

    # use the Allmaps API to get all the Map IDs from that Manifest

    for item in allmapsManifest['items']:
        # if counter > 4:
        #     break
        allmapsMapID = item['id']
        mapURL = f'https://annotations.allmaps.org/maps/{allmapsMapID}'
        print(f'⤵️ Downloading annotation {mapURL}')
            
        # download each JSON annotation for each of those Map IDs

        annoRequest = requests.get(mapURL, stream=True)
        allmapsAnnotation = annoRequest.json()

        # write out all the images we're later going to need to download into an array,
        # but skip if image already appears in array
        # so we don't download multiple times later on.
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

        print(f'⤵️ Downloading image {image}')

        imageRequest = requests.get(image, stream=True)

        with open(f'./tmp/img/{ image.split("commonwealth:")[1][0:9] }.tif', 'wb') as fd:
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
    
    for f in os.listdir(path):
        isFile = os.path.isfile(path+f)
        if not f.startswith('.') and isFile == True:
            print(f'⤵️ Transforming {f} into a geojson...')
            name = os.path.splitext(f)[0]+'-transformed.geojson'
            file = open(outPath+name, "w")
            
            cmd = [
                "allmaps", "transform", "pixel-mask", f
            ]

            subprocess.run(
                cmd,
                cwd=path,
                stdout=file
            )
    
    print("✅ All pixel masks transformed!")
    print(" ")
    print("You can now proceed to the `mosaic-plates` step.")
    print(" ")

    return

def mosaicPlates():
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
        print("😩 You didn't pass any function to the --step flag")
        exit()

    else:
        
        # no matter what step we're running
        # first run the directory structure function
        # to ensure that the right subdirectories exist

        createDirectoryStructure()
    
        if args.step == 'download-inputs':
            downloadInputs(args.identifier)

        elif args.step == 'allmaps-transform':
            allmapsTransform()
        
        elif args.step == 'mosaic-plates':
            mosaicPlates()

        else:
            print("We haven't made this step do anything yet")