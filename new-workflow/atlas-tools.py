#!/usr/bin/env python3

import os
from os import path
import gdal
import argparse


# argparse creates command-line access to the script
parser = argparse.ArgumentParser(description='Tools to help in the process of geotransforming urban atlases.')
parser.add_argument('--step', metavar='{check, mask-transform, all}', type=str, 
                    help='steps to execute (default: all)', default='all', dest='step')
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
					resampleAlg = 'cubic'
					)

				gdal.Warp('./masked/{}-masked.tif'.format(basename),'./spatial_imagery/{}'.format(file), options = warpOptions)

		print('🎉 Everything looks good to go')


if __name__ == "__main__":
	
	if args.step == 'check' or args.step == 'all':

		checkStep = check()

	if args.step == 'mask-transform' or (args.step == 'all' and checkStep):

		maskTransform()
		
		



