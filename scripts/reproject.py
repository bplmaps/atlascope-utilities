# reprojects ground control points from EPSG: 3857 to 4326
# created by Map Center intern Victoria Mak, Github: @viymak
import pandas as pd
import geopandas as gp 
from geopandas import GeoDataFrame
from shapely.geometry import Point 
import fiona
from os import listdir

# user input - the user must rename the file
replace_string = input('You will need to rename these files. Which part of the filename should be replaced?\n')

new_filename = input('What would you like it replaced with?\n')


for text_file in listdir('.'):
    if text_file.endswith('.py') | text_file.startswith('.'):
        pass
    else:
        
        print('converting ' + text_file)
        gcps = pd.read_csv(text_file)

        geometry = [Point(xy) for xy in zip(gcps.mapX, gcps.mapY)]
        crs = {'init': 'epsg:3857'}

        geo_df = GeoDataFrame(gcps, crs=crs, geometry=geometry)

        #for debugging:
        #print(geo_df.crs)

        # convert coordinates to epsg:4326
        points_4326 = geo_df.to_crs({'init': 'epsg:4326'})

        points_4326.mapX = [point.x for point in points_4326.geometry]
        points_4326.mapY = [point.y for point in points_4326.geometry]
        points_4326.enable = points_4326['enable'].astype(int)

        # convert to pandas dataframe (exporting a csv with geodataframe created a new directory for each file)
        # geometry column is dropped to match original formatting
        pandas_data = pd.DataFrame(points_4326).drop(['geometry'], axis=1)
        #(mapX: points_4326.map)

        #for debugging:
        #print(pandas_data)

        new_fn = text_file.replace(replace_string, new_filename)
        pandas_data.to_csv(new_fn, index=False)
