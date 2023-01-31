#!/usr/bin/env python3

import argparse
import requests
import os
import json
from os import path


parser = argparse.ArgumentParser(description='Tools to help in the process of geotransforming urban atlases.')
parser.add_argument('--step', metavar='{download-inputs, create-footprint, warp-plates}', type=str, 
                    help='steps to execute (default: download-inputs)', default='download-inputs', dest='step')
parser.add_argument('--identifier', type=str, 
                    help='commonwealth id', dest='identifier')

args = parser.parse_args()

# 

def downloadInputs(identifier):


    # ask allmaps API what the Allmaps ID is for the Commonwealth Manifest ID we sent over

    allmapsAPIRequest = requests.get(f'https://annotations.allmaps.org/?url=https://www.digitalcommonwealth.org/search/{identifier}/manifest.json')
    allmapsManifest = allmapsAPIRequest.json()
    
    counter = 0

    # create an empty list to hold the images we're going to later download
    imagesList = []

    # use the Allmaps API to get all the Map IDs from that Manifest



    for item in allmapsManifest['items']:
        if counter > 4:
            break
        allmapsMapID = item['id']
        mapURL = f'https://annotations.allmaps.org/maps/{allmapsMapID}'
        print(f'⤵️ Downloading annotation {mapURL}')
            
        # download each JSON annotation for each of those Map IDs

        annoRequest = requests.get(mapURL, stream=True)
        allmapsAnnotation = annoRequest.json()

        # write out all the images we're later going to need to download into an array. 
        # rewrite the jpg suffix to tif
        for item in allmapsAnnotation["items"]:
            imagesList.append( item["target"]["source"].replace(".jpg", ".tif") )


        with open(f'./tmp/annotations/{counter}.json', 'w') as f:
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
        # no matter what step we're running, first run the directory structure function to ensure that the right subdirectories exist
        createDirectoryStructure()
    
        if args.step == 'download-inputs':
            downloadInputs(args.identifier)

        else:
            print("We haven't made this step do anything yet")