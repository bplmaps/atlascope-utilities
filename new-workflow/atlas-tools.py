#!/usr/bin/env python3

import os
from os import path
import gdal
import gdalconst
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
					# outputType = gdalconst.GDT_Int16,
					# dstNodata = -1,
					multithread = True,
					srcSRS = "EPSG:4326",
					dstSRS = "EPSG:3857",
					creationOptions = ['COMPRESS=LZW'],
					resampleAlg = 'cubic'
					)

				gdal.Warp('./masked/{}-masked.tif'.format(basename),'./spatial_imagery/{}'.format(file), options = warpOptions)

		print('🎉 Completed masking and transforming')


def buildMosaic():

	print('➡️  Beginning Mosaic')

	warpOptions = gdal.WarpOptions(
				format = 'GTiff',
				copyMetadata = True,
				srcAlpha = True,
				dstAlpha = True,
				multithread = True,
				srcSRS = "EPSG:3857",
				dstSRS = "EPSG:3857",
				creationOptions = ['COMPRESS=LZW'],
				resampleAlg = 'average'
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
					print('🖼 Mosaicing files {} and {}'.format(firstFile,file))
					gdal.Warp('./mosaic/temp.tif',['./masked/{}'.format(firstFile),'./masked/{}'.format(file)], options = warpOptions)
				else:
					print('🖼 Mosaicing file {}'.format(file))
					gdal.Warp('./mosaic/temp.tif',['./mosaic/temp.tif','./masked/{}'.format(file)], options = warpOptions)

				iterator = iterator + 1
		print('🎉 Congrats, you now have a giant mosaic')


if __name__ == "__main__":
	
	if args.step == 'check':

		checkStep = check()

	if args.step == 'mask-transform':

		maskTransform()

	if args.step == 'mosaic':

		buildMosaic()
		



