#!/usr/bin/env python3

import os
from os import path
import gdal
import argparse


# argparse creates command-line access to the script
# we create a --step flag which tells us which function we want to run

parser = argparse.ArgumentParser(description='Tools to help in the process of geotransforming urban atlases.')
parser.add_argument('--step', metavar='{check, mask-transform, build-vrt}', type=str, 
                    help='steps to execute (default: check)', default='check', dest='step')
args = parser.parse_args()


# the check function checks all the input to make sure it looks correct

def check():

	import osr
	import fiona

	print('➡️  Beginning check step')

	# we begin by looking into Boundary.geojson
	try:
		with fiona.open('./footprint/Boundary.geojson') as footprintFile:

			errorCounter = 0

			for feature in footprintFile:

				identifier = feature['properties']['identifier']

				sourceIdentifier = parseInset(identifier)

				print('👀 Checking identifier {}'.format(identifier))

				if path.isfile('./gcps/{}.tif.points'.format(identifier)):
					print('✅ GCPS for {} exists'.format(identifier))
				else:
					print('⚠️ Could not find GCPS for {}'.format(identifier))
					errorCounter = errorCounter + 1


				if path.isfile('./archival_imagery/{}.tif'.format(sourceIdentifier)):
					print('✅ Archival TIFF for {} exists'.format(identifier))

					sourceTiff = gdal.Open('./archival_imagery/{}.tif'.format(sourceIdentifier))

					# check if it opened successfully
					if sourceTiff is None:
						print('⚠️ Could not read file {}'.format(file))
						errorCounter = errorCount + 1
					else:
						print('✅ Archival TIFF for {} is readable'.format(identifier))

				# check if there are 3 bands
						if sourceTiff.RasterCount != 3:	
							print('⚠️ Incorrect number of bands in {}'.format(sourceIdentifier))
							errorCounter = errorCount + 1
						else:
							print('✅ Archival TIFF for {} has 3 bands'.format(identifier))

				else:
					print('⚠️ Cound not find archival TIFF for {}'.format(identifier))
					errorCounter = errorCounter + 1

			if errorCounter == 0:
				print('🎉 Checks look good! You can go to the mask-transform step.')
			else:
				print('🛑 Found {} errors above. Please correct them first.'.format(errorCounter))

	except:
		print("🛑 Couldn't open the footprint file")


# transformFromSource function takes archival imagery, ground control points, and the boundary file and creates the pieces of the mosaic

def transformFromSource():

	import csv
	from pyproj import Transformer
	import numpy as np

	transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857")

	print('➡️  Beginning to build mosaic pieces')

	if not os.path.exists('./tmp'):
		os.mkdir('./tmp')

	if not os.path.exists('./masked'):
		os.mkdir('./masked')

	for r, d, f in os.walk('./gcps'):

		for file in f:

			# skip non tif or tiff filenames
			if file.split('.')[-1] != 'points':
				print('× Skipping non-GCPS file {}'.format(file))

			else:

				basename = file.split('.')[0] # this is equivalent to identifier
				gcps = []

				with open('./gcps/{}'.format(file),'r') as gcpsFile:

					print('⛰  Using ground control points {}'.format(basename))

					reader = csv.DictReader(gcpsFile)
					for row in reader:

						xt, yt = transformer.transform(row['mapY'],row['mapX'])

						g = gdal.GCP(xt, yt, 0, float(row['pixelX']), -float(row['pixelY']))
						gcps.append(g)

				translateOptions = gdal.TranslateOptions(
					format = 'GTiff',
					GCPs = gcps,
					outputSRS = 'EPSG:3857'
					)

				print('🧮  Creating temporary translate file for {}'.format(basename))

				sourceIdentifier = parseInset(basename)

				archivalImage = gdal.Open('./archival_imagery/{}.tif'.format(sourceIdentifier))

				for b in [1,2,3]:
					band = archivalImage.GetRasterBand(b)
					readableBand = band.ReadAsArray()
					readableBand[np.where( readableBand == 0)] = 1

				gdal.Translate('./tmp/{}-translated.tif'.format(basename),archivalImage,options=translateOptions)


				warpOptions = gdal.WarpOptions(
							format = 'GTiff',
							copyMetadata = True,
							multithread = True,
							cutlineDSName = './footprint/Boundary.geojson',
							cutlineLayer = 'Boundary',
							cutlineWhere = "identifier='{}'".format(basename),
							cropToCutline = True,
							dstSRS = "EPSG:3857",
							creationOptions = ['COMPRESS=LZW'],
							resampleAlg = 'cubic',
							dstAlpha = False,
							dstNodata = 0,
							xRes=0.2,
							yRes=0.2,
							targetAlignedPixels=True
							)

				print('🤿  Creating masked mosaic TIFF in EPSG:3857 for {}'.format(file))
				gdal.Warp('./masked/{}.tif'.format(basename),'./tmp/{}-translated.tif'.format(basename), options=warpOptions)

				print('🚮  Deleting temporary translate file for {}'.format(file))
				os.remove('./tmp/{}-translated.tif'.format(basename))

	print('🎉 Completed creating mosaic pieces from archival imagery. You can go to the vrt-mosaic step.')


# buildVRT function creates a vrt from mosaic pieces suitable for feeding to gdal2tiles

def buildVRT():

	print('➡️  Beginning to create VRT')

	for r, d, f in os.walk('./masked'):

		pieceList = []
		for file in f:
			if file.split('.')[-1] != 'tif':
				print('× Skipping non-TIFF file {}'.format(file))

			else:
				pieceList.append('./masked/{}'.format(file))

		vrtOptions = gdal.BuildVRTOptions(
			resolution = 'highest',
			outputSRS = 'EPSG:3857',
			separate = False,
			srcNodata = 0
			)

		gdal.BuildVRT('./mosaic.vrt',pieceList, options=vrtOptions)

		print('🎉 Completed creating the VRT. You can now feed this directly to gdal2tiles!')


def parseInset(identifier):
	if len(identifier.split('_inset')) > 1:
		return identifier.split('_inset')[0]
	else:
		return identifier


if __name__ == "__main__":

	if args.step == '':
		print("😩 You didn't pass any function to the --step flag")
		exit()
	
	if args.step == 'check':

		check()

	if args.step == 'mask-transform':

		transformFromSource()

	if args.step == 'vrt-mosaic':

		buildVRT()



