#!/usr/bin/env python3

import os
from os import path
from osgeo import gdal
import argparse
import requests
from pyproj import Transformer
import numpy as np


# argparse creates command-line access to the script

parser = argparse.ArgumentParser(
    description='Tools to process Allmaps annotations from ')
parser.add_argument('-a', '--annotation-type', metavar='{image, manifest}', type=str,
                    help='whether we are consuming an image or manifest annotation (default: image)', default='image', dest='annoType', required=True)
parser.add_argument('-u', '--annotation-url', metavar='url', type=str,
                    help='url to annotation', default='image', dest="annoURL", required=True)
args = parser.parse_args()



def processImageAnnotation(url):
	if not os.path.exists('./tmp'):
		os.mkdir('./tmp')

	annoRequest = requests.get(url)
	anno = annoRequest.json()

	imageId = anno['items'][0]['id']
	imageEndpoint = anno['items'][0]['target']['service'][0]["@id"]
	sourceImage = f'{imageEndpoint}/full/full/0/default.tif'

	print(f'⤵️ Downloading image {imageId}')

	imageRequest = requests.get(sourceImage, stream=True)

	with open(f'./tmp/{imageId}.tif', 'wb') as fd:
		for chunk in imageRequest.iter_content(chunk_size=128):
			fd.write(chunk)

	print(f'🏔 Registering GCPs from annotation')

	transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

	gcps = []
	for gcp in anno['items'][0]['body']['features']:

			xt, yt = transformer.transform(
			    gcp['geometry']['coordinates'][0], gcp['geometry']['coordinates'][1])
			line = float(gcp['properties']['pixelCoords'][1])
			pixel = float(gcp['properties']['pixelCoords'][0])
			g = gdal.GCP(xt, yt, 0, pixel, line)
			gcps.append(g)

	archivalImage = gdal.Open(f'./tmp/{imageId}.tif')

	# for b in [1, 2, 3]:
	# 	band = archivalImage.GetRasterBand(b)
	# 	readableBand = band.ReadAsArray()
	# 	readableBand[np.where(readableBand == 0)] = 1

	translateOptions = gdal.TranslateOptions(
	format='GTiff',
	GCPs=gcps,
	outputSRS='EPSG:3857'
	)

	gdal.Translate(f'./tmp/{imageId}-translated.tif', archivalImage, options = translateOptions)

	warpOptions = gdal.WarpOptions(
							format='GTiff',
							copyMetadata=True,
							multithread=True,
							dstSRS="EPSG:3857",
							creationOptions=['COMPRESS=LZW', 'BIGTIFF=YES'],
							resampleAlg='cubic',
							dstAlpha=False,
							dstNodata=0,
							xRes=1,
							yRes=1,
							targetAlignedPixels=True
							)

	print(f'💫 Creating warped TIFF in EPSG:3857 for {imageId}')

	gdal.Warp(f'./{imageId}-warped.tif',
				f'./tmp/{imageId}-translated.tif', options=warpOptions)

	print(f'🚮 Deleting temporary translate file for {imageId}')
	os.remove(f'./tmp/{imageId}-translated.tif')


if __name__ == "__main__":

	if args.annoType == 'image':
		processImageAnnotation(args.annoURL)
