#!/usr/bin/env python3

import os
from os import path
import gdal
import gdalconst
import argparse


# argparse creates command-line access to the script
parser = argparse.ArgumentParser(description='Tools to help in the process of geotransforming urban atlases.')
parser.add_argument('--step', metavar='{check, mask-transform, mosaic}', type=str, 
                    help='steps to execute (default: check)', default='check', dest='step')
args = parser.parse_args()


# the script is divided into two functions, check() and maskTransform()
# it runs either bor both depending on the input of --step

def check():

	import osr

	print('➡️  Beginning check step')

	for r, d, f in os.walk('./spatial_imagery'):

		# set error counter to zero to start and list for error files
		errorCount = 0
		errorFiles = []


		# loop through every file in the spatial_imagery directory

		for file in f:

			# skip non tif or tiff filenames
			if file[-3:] not in ['tif','tiff']:
				print('× Skipping non-TIFF file {}'.format(file))

			else:

				print('👀 Checking input file {}'.format(file))

				# open with gdal
				sourceTiff = gdal.Open('./spatial_imagery/'+file)

				# check if it opened successfully
				if sourceTiff is None:
					print('🛑 Could not read file {}'.format(file))
					errorCount = errorCount + 1
					errorFiles.append(file)
					continue
				else:
					print('✅ File is readable')

				# check if there are 3 bands
				if sourceTiff.RasterCount != 3:	
					print('🛑 Incorrect number of bands in {}'.format(file))
					errorCount = errorCount + 1
					errorFiles.append(file)
					continue
				else:
					print('✅ File has 3 bands')

				# check if file is WGS 84
				if osr.SpatialReference(wkt=sourceTiff.GetProjection()).GetAttrValue('geogcs') != 'WGS 84':
					print('🛑 Incorrect SRS in {}'.format(file))
					errorCount = errorCount + 1
					errorFiles.append(file)
					continue
				else:
					print('✅ File is in WGS 84')


		if errorCount == 0:
			print('🎉 Everything looks good to go')
			return True
		else:
			print('😱 There were errors in the folowing files')
			for ef in errorFiles:
				print(' ⬩ {}'.format(ef))
			return False

def maskTransform():


	print('➡️  Beginning mask and transform step')

	if not os.path.exists('./masked'):
		os.mkdir('./masked')

	for r, d, f in os.walk('./spatial_imagery'):

		for file in f:

			# skip non tif or tiff filenames
			if file[-3:] not in ['tif','tiff']:
				print('× Skipping non-TIFF file {}'.format(file))

			else:

				print('🌀 Masking and transforming {}'.format(file))
				basename = file.split('.')[0]

				warpOptions = gdal.WarpOptions(
					format = 'GTiff',
					cutlineDSName = './footprint/Boundary.geojson',
					cutlineLayer = 'Boundary',
					cutlineWhere = "identifier='{}'".format(basename),
					cropToCutline = True,
					copyMetadata = True,
					dstAlpha = True,
					multithread = True,
					srcSRS = "EPSG:4326",
					dstSRS = "EPSG:3857",
					creationOptions = ['COMPRESS=LZW'],
					resampleAlg = 'cubic',
					xRes=0.2,
					yRes=0.2,
					targetAlignedPixels=True
					)

				gdal.Warp('./masked/{}-masked.tif'.format(basename),'./spatial_imagery/{}'.format(file), options = warpOptions)

		print('🎉 Completed masking and transforming')


def buildMosaic():

	print('➡️  Beginning Mosaic')

	if not os.path.exists('./mosaic'):
		os.mkdir('./mosaic')

	warpOptions = gdal.WarpOptions(
				format = 'GTiff',
				copyMetadata = True,
				srcAlpha = True,
				dstAlpha = True,
				multithread = True,
				srcSRS = "EPSG:3857",
				dstSRS = "EPSG:3857",
				creationOptions = ['COMPRESS=LZW'],
				resampleAlg = 'near',
				xRes=0.2,
				yRes=0.2,
				targetAlignedPixels=True
				)

	for r, d, f in os.walk('./masked'):

		iterator = 0

		for file in f:

			# skip non tif or tiff filenames
			if file[-3:] not in ['tif','tiff']:
				print('× Skipping non-TIFF file {}'.format(file))

			else:
				if iterator == 0:
					firstFile = file
				elif iterator == 1:
					print('🖼  Mosaicing files {} and {}'.format(firstFile,file))
					gdal.Warp('./mosaic/temp.tif',['./masked/{}'.format(firstFile),'./masked/{}'.format(file)], options = warpOptions)
				else:
					print('🖼  Mosaicing file {}'.format(file))
					gdal.Warp('./mosaic/temp.tif',['./mosaic/temp.tif','./masked/{}'.format(file)], options = warpOptions)

				iterator = iterator + 1
		print('🎉 Congrats, you now have a giant mosaic')


def transformFromSource():

	import csv
	from pyproj import Transformer

	transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857")

	print('➡️  Beginning to build mosaic pieces from archival imagery')

	if not os.path.exists('./tmp'):
		os.mkdir('./tmp')

	if not os.path.exists('./masked'):
		os.mkdir('./masked')

	for r, d, f in os.walk('./archival_imagery'):

		for file in f:

			# skip non tif or tiff filenames
			if file[-3:] not in ['tif','tiff']:
				print('× Skipping non-TIFF file {}'.format(file))

			else:

				basename = file.split('.')[0]
				gcps = []

				with open('./gcps/{}.tif.points'.format(basename),'r') as gcpsFile:

					print('⛰  Getting ground control points for {}'.format(file))

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

				print('🧮  Creating temporary translate file for {}'.format(file))

				if len(basename.split('_')) > 3:
					sourcefile = basename.split('_')[:1].join('_')
				else:
					sourcefile = basename

				gdal.Translate('./tmp/{}-translated.tif'.format(basename),'./archival_imagery/{}.tif'.format(sourcefile), options=translateOptions)


				warpOptions = gdal.WarpOptions(
							format = 'GTiff',
							copyMetadata = True,
							dstAlpha = True,
							multithread = True,
							cutlineDSName = './footprint/Boundary.geojson',
							cutlineLayer = 'Boundary',
							cutlineWhere = "identifier='{}'".format(basename),
							cropToCutline = True,
							dstSRS = "EPSG:3857",
							creationOptions = ['COMPRESS=LZW'],
							resampleAlg = 'cubic',
							xRes=0.2,
							yRes=0.2,
							targetAlignedPixels=True
							)

				print('🤿  Creating masked mosaic TIFF in EPSG:3857 for {}'.format(file))
				gdal.Warp('./masked/{}.tif'.format(basename),'./tmp/{}-translated.tif'.format(basename), options=warpOptions)

				print('🚮  Deleting temporary translate file for {}'.format(file))
				os.remove('./tmp/{}-translated.tif'.format(basename))

	print('🎉 Completed creating mosaic pieces from archival imagery')

if __name__ == "__main__":
	
	if args.step == 'check':

		checkStep = check()

	if args.step == 'mask-transform':

		maskTransform()

	if args.step == 'mosaic':

		buildMosaic()
		
	if args.step == 'src':

		transformFromSource()



