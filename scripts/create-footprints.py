#!/usr/bin/env python3

import csv
import requests
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
import json



# SETTINGS

# URL for AirTable API
airtable_url = "https://api.airtable.com/v0/appfoecBxrOudOHVh/CLIR-Progress?api_key=key10KeIIPJpM8npJ"

# debug = True
# i = 0

input_airtable_src = requests.get(airtable_url)
input_airtable_json = input_airtable_src.json()["records"]


geojson_template = {"type": "FeatureCollection", "features": []}


for layer in input_airtable_json:

	if layer['fields']['status']!= "complete": continue

	geojson_url = "https://s3.us-east-2.wasabisys.com/urbanatlases/" + layer['fields']['barcode'] + "/src/footprint/Boundary.geojson"

	# make an HTTP request for that geojson file
	remote_geojson = requests.get(geojson_url)

	# if we don't get a successful HTTP request, something went wrong
	if remote_geojson.status_code != 200:
		print("‼️ Something went wrong loading the GeoJSON")
		continue
	else:
		print("Loaded GeoJSON for " + layer['fields']["barcode"])

	plates_geojson = remote_geojson.json()

	plates = [shape(f['geometry']) for f in plates_geojson['features']]

	full_outline = unary_union(plates).buffer(0.0005).simplify(0.0003)

	geojson_template["features"].append({"type": "Feature", "geometry": mapping(full_outline), "properties": {"barcode": layer['fields']["barcode"],  "bibliocommons_control": layer['fields']["bibliocommons_control"], "publisher": layer['fields']["publisher"], "publisher_full": layer['fields']['publisher_full'], "year": layer['fields']["year"], "title": layer['fields']["title"], "geo_extent": layer['fields']['geo_extent']}})


	### This section creates a new plates boundary file for EACH atlas, simplifying it somewhat to ease processing
	### Outputs it to the ./atlas-footprints directory, naming each json filename with the call number

	if 'plate' in plates_geojson['features'][0]['properties']:
		geojson_for_plates = {"type": "FeatureCollection", "features": []}
		for f in plates_geojson['features']:
			plate_geometry = shape(f['geometry']).simplify(0.0003)
			geojson_for_plates["features"].append({"type": "Feature", "geometry": mapping(plate_geometry), "properties": {"plate": f["properties"]["plate"]}})
		with open("../atlas-footprints/plates-" + layer['fields']["barcode"] + ".geojson", "w+") as plateOutFile:
			plateOutFile.write(json.dumps(geojson_for_plates))
	else:
		print("‼️ Did not create plate footprints; unable to find plate field in input file for " + layer['fields']["barcode"])


with open("../atlas-footprints/volume-extents.geojson","w+") as outFile:
	outFile.write(json.dumps(geojson_template))
