#This file downloads all tifs for a given barcode
#output can be found in root/arch_tif
#make copy of get-tiffs-from-dc.py into root folder
#be sure to change barcode before running
#to run, enter 'sudo python3 get-tiffs-from-dc.py' into terminal
#enter password for user
#*** If running on windows:
#			Run in OSGEO shell and without sudo
#			Program will not be able to delete unnecessary files itself, but all tiffs will be downloaded 
#if error when importing something, enter 'pip3 [package name]' (e.g. pip3 requests) and try again

import requests
from bs4 import BeautifulSoup
import os
import zipfile
import shutil


print('imports complete')

barcode = "39999059010775"  #########CHANGE THIS FOR EACH ATLAS#######################
r = requests.get('https://collections.leventhalmap.org/search?page=1&per_page=100&q={}'.format(barcode))
htmlSource = BeautifulSoup(r.text, "html.parser")
os.mkdir('arch_tif')

#From html, find each download url and identifier
for d in htmlSource.find_all("div", class_="document"):
    #Get download url
    dcId = d["data-layer-id"]
    downloadUrl = "https://collections.leventhalmap.org/start_download/{}?datastream_id=productionMaster".format(dcId)

	#Get identifier
    imageUrl = "https://collections.leventhalmap.org/search/{}".format(dcId)
    imagePage = requests.get(imageUrl)
    imagePageSoup = BeautifulSoup(imagePage.text, 'html.parser')
    identifier = str(imagePageSoup.find('dt', string='Identifier:').find_next_sibling('dd')).split('>')[1].split('<')[0].strip()

	#Download the image and save as identifier
    download = requests.get(downloadUrl)
    zippath = 'arch_tif/' + identifier + '.zip'
    with open(zippath, 'wb') as f:
        f.write(download.content)
    print(identifier + ' downloaded')

    #extract from zipped folder
    extractedpath = 'arch_tif/' + identifier
    with zipfile.ZipFile(zippath, 'r') as zip_ref:
        zip_ref.extractall(extractedpath)
    downloadname = extractedpath + '/' + os.listdir(extractedpath)[0]
    tifname = identifier + '.tif'
    os.rename(downloadname, 'arch_tif/' + tifname)


    print(identifier + ' extracted')
#Finish looping through

#Delete intermediate files
print('cleaning up...')
for item in os.listdir('arch_tif/'):
    if not item.endswith('.tif'):
        path = 'arch_tif/'+item
        try:
            shutil.rmtree(path)
        except NotADirectoryError:
            os.remove(path)
        else:
            pass

print('done!')
