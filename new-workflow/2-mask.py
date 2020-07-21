import os
import gdal



# use os.walk() generates lists of root, directory, and files
for r, d, f in os.walk('./spatial_imagery'):


	# loop through every file in the spatial_imagery directory
	# note that this does not filter for only *.tif images
	# if there are other non-tif images in that directory, they'll get tested too
	for file in f:

		basename = file.split('.')[0]

		warpOptions = gdal.WarpOptions(
		format = 'GTiff',
		cutlineDSName = './footprint/Boundary.geojson',
		cutlineLayer = 'Boundary',
		cutlineWhere = "identifier='{}'".format(basename),
		cropToCutline = True,
		copyMetadata = False,
		dstAlpha = False,
		multithread = True,
		dstNodata = -1
		)


		print('🤿 Beginning mask of {}'.format(basename))

		ds = gdal.Warp('./masked/{}-masked.tif'.format(basename),'./spatial_imagery/{}'.format(file),
		options = warpOptions
		)

		del ds

		print('✅ Done')