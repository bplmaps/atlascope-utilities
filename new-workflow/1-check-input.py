import os
import gdal
import osr # needed for testing projection systems

# use os.walk() generates lists of root, directory, and files
for r, d, f in os.walk('./spatial_imagery'):

	# set error counter to zero to start and list for error files
	errorCount = 0
	errorFiles = []

	# loop through every file in the spatial_imagery directory
	# note that this does not filter for only *.tif images
	# if there are other non-tif images in that directory, they'll get tested too
	for file in f:
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
	else:
		print('😱 There were errors in the folowing files')
		for ef in errorFiles:
			print(' ⬩{}'.format(ef))


