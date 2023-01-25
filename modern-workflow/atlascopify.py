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

# here we download the TIFFs from Digital Commonwealth

    digitalCommonwealthManifestRequest = requests.get(f'https://collections.leventhalmap.org/search/{identifier}/manifest')
    manifestJSON = digitalCommonwealthManifestRequest.json()

    counter = 0

    # use digital commonwealth API to get all map images associated with a manifest/commonwealth ID

    for sequence in manifestJSON['sequences']:
        for canvas in sequence['canvases']:
            for image in canvas['images']:
                if counter > 4:
                    break
                else:
                    imageURL = image['resource']['service']['@id']
                    tiffURL = f'{imageURL}/full/full/0/default.tif'

                    print(f'⤵️ Downloading image {tiffURL}')

                    #  download the image for each atlas plate

                    imageRequest = requests.get(tiffURL, stream=True)

                    # right now we're naming them with a ordinal counter, fix this later

                    with open(f'./tmp/img/{counter}.tif', 'wb') as fd:
                        for chunk in imageRequest.iter_content(chunk_size=128):
                            fd.write(chunk)

                    counter = counter+1

    print("✅ All images downloaded!")
# here we download the allmaps georeference annotations for each plate inside an atlas

    # ask allmaps API what the Allmaps ID is for the Commonwealth Manifest ID we sent over

    allmapsAPIRequest = requests.get(f'https://annotations.allmaps.org/?url=https://www.digitalcommonwealth.org/search/{identifier}/manifest.json')
    allmapsManifest = allmapsAPIRequest.json()
    
    counter = 0

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

        with open(f'./tmp/annotations/{counter}.json', 'w') as f:
            json.dump(allmapsAnnotation, f)

        counter = counter+1
    
    print("✅ All annotations downloaded!")

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