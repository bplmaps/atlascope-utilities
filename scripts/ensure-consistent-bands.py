﻿gdal_translate -of GTiff -r cubic -b 1 -b 2 -b 3 -co PREDICTOR=2 -co zlevel=9 -a_nodata 0 input.tif output.tif