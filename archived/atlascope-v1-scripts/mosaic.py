import os
import sys
import shutil
import subprocess


#gets the root directory
rootdir = os.getcwd()

#creates a folder to store imagery with homogenous imagery properties
reprojected_path=os.path.join(rootdir,"reprojected")
if not os.path.exists(reprojected_path):
    os.makedirs(reprojected_path)

#creates a folder to store imagery with homogenous imagery properties
bands_consistent_path=os.path.join(rootdir,"consistent_bands")
if not os.path.exists(bands_consistent_path):
    os.makedirs(bands_consistent_path)

#creates a folder to store masked geotifs
masked_path=os.path.join(rootdir,"masked")
if not os.path.exists(masked_path):
    os.makedirs(masked_path)

#creates a folder to store cleaned plates ready to merge
to_merge_path=os.path.join(rootdir,"merge_input")
if not os.path.exists(to_merge_path):
    os.makedirs(to_merge_path)

#creates a folder to store mosaicing materials, including final mosaic.tif
mosaic_path=os.path.join(rootdir,"mosaic")
if not os.path.exists(mosaic_path):
    os.makedirs(mosaic_path)




#defines location of footprint
footprint_path = os.path.join(rootdir, "footprint", "Boundary.geojson")



#ask user which steps they want to accomplish -- there may be cases where one wishes
#to complete process start to finish -- other times, they need to simply reclip & save one plate
#prompts are designed to add flexibility
print("\n")
band_const = input("Have you already ensured that band properties are consistent? y/n \n")
print("\n")
mask = input("Do you need to mask the images? y/n \n")
print("\n")
mosaic = input("Would you like to create the mosaic at the end? y/n \n")
print("\n")



if band_const == "n":

    print("Great! To get started, where is your spatial imagery?")
    imagery_input = input("Please enter just the folder name (not the full path): \n")
    imagery_path = os.path.join(rootdir, imagery_input)


    #loops through the consistent band files
    for f in os.listdir(imagery_path):
        if f.endswith(".tif"):

            #isolates identifier name from file extension
            file_basename = f.rsplit( ".", 1 )[ 0 ]

            #define inputs and outputs
            reproject_input_file = os.path.join(imagery_path, f)
            reproject_output_file = os.path.join(reprojected_path, f)


            print("\n")
            print("Projecting " + file_basename + " to EPSG: 3857")
            project_command = ("gdalwarp", "-of", "GTiff", "-r", "cubic", "-co", "PREDICTOR=2", "-co", "zlevel=9","-t_srs", "EPSG:3857", reproject_input_file, reproject_output_file)
            subprocess.call(project_command)



    #loops through the original imagery files
    for f in os.listdir(reprojected_path):
        if f.endswith(".tif"):

            #isolates identifier name from file extension
            file_basename = f.rsplit( ".", 1 )[ 0 ]

            #define inputs and outputs
            band_const_input_file = os.path.join(reprojected_path, f)
            bands_const_output_file= os.path.join(bands_consistent_path, f)


            #define & run command to fix projection issues with plates
            print("\n")
            print("Ensuring band consistency: " + file_basename)
            band_command = ("gdal_translate", "-of", "GTiff", "-r", "cubic", "-b", "1", "-b", "2", "-b", "3", "-co", "PREDICTOR=2", "-co", "zlevel=9","-a_nodata", "0",  band_const_input_file, bands_const_output_file)
            subprocess.call(band_command)



elif band_const == "y":
    pass
else:
    print("Please type either y or n")


#masking
if mask == "y":


    #loops through the original imagery files
    for f in os.listdir(bands_consistent_path):
        if f.endswith(".tif"):

            #isolates identifier name from file extension
            file_basename = f.rsplit( ".", 1 )[ 0 ]

            #defines full path to each output file with new projection & band settings
            input = os.path.join(bands_consistent_path, file_basename + ".tif")
            #defines full path to new output file that has been masked
            output = os.path.join(masked_path, file_basename + ".tif")


            #define & call masking command
            print("\n")
            print("Performing mask of: " + file_basename + "...")
            mask_command = ("gdalwarp", "-cutline", footprint_path, "-csql", "select * from Boundary where identifier='{}'".format(file_basename), "-crop_to_cutline", "-co", "PREDICTOR=2", "-co", "zlevel=9", input, output)
            subprocess.call(mask_command)

    #applies nearblack
    for f in os.listdir(masked_path):
        if f.endswith(".tif"):

            #isolates basename from file extension
            file_basename = f.rsplit( ".", 1 )[ 0 ]
            #defines newly masked tifs as the cleaning process input
            input = os.path.join(masked_path, file_basename + ".tif")
            #defines ./to_merge_path as the cleaning process output
            output = os.path.join(to_merge_path, file_basename + ".tif")

            #defines & calls command to compress & set nodata as nearblack
            print("\n")
            print("\n")
            print ("Apply nearblack to " + file_basename + "...")
            clean_command = ("nearblack", "-of", "GTiff", "-setalpha", "-co", "PREDICTOR=2", "-co", "zlevel=9","-near", "15", "-o", output, input)
            subprocess.call(clean_command)


elif mask == "n":
    pass
else:
    print("Please type either y or n")

print("\n")
print("\n")
print("All plates have been successfully masked and are located in ./masked")




if mosaic == "y":
    #check to see if buildvrt input already exists, and if so remove
    if os.path.exists(os.path.join(mosaic_path, "input.txt")):
        os.remove(os.path.join(mosaic_path, "input.txt"))
    #create buildvrt input txt file containing path names to all clipped mosaics
    with open(os.path.join(mosaic_path, "input.txt"),"w+") as txt_file:
        for f in os.listdir(masked_path):
            if f.endswith(".tif"):
                input_rasters = os.path.join(to_merge_path, f)
                txt_file.write(input_rasters + "\n")
    vrt = os.path.join(mosaic_path, "merge.vrt")
    input = os.path.join(mosaic_path, "input.txt")

    print("\n")
    print("Building mosaic...")
    #create the command to buildvrt
    buildvrt_command = ("gdalbuildvrt", "-resolution","highest", "-a_srs", "EPSG:3857",  "-srcnodata", "0", "-input_file_list", input, vrt)
    #call the command to buildvrt
    subprocess.call(buildvrt_command)


    print("\n")
    print("Exporting buildvrt to tif...")
    #create the command to translate the vrt to .tif
    mosaic_command = ("gdal_translate", "-r", "cubic", "-of", "GTiff", "-co", "COMPRESS=LZW", "-co", "BIGTIFF=YES", "-a_srs", "EPSG:3857", vrt , os.path.join(mosaic_path, "mosaic.tif"))
    #call the process to translate vrt to tif, creating mosaic
    subprocess.call(mosaic_command)

elif mosaic == "n":
    pass
else:
    print("Please type either y or n")


print("Mosaic complete!")
