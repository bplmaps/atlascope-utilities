import os
import json

#gets the root directory
rootdir = os.getcwd()
os.chdir(rootdir)


def getIrregularPlateValue(identifier,num,offset,excs):
    #get ending of identifier e.g. 0024 from G1234_B6_B7_0024
	splits = identifier.split('_')
	plateval = splits.pop()
	inset = None
	if ('inset' in plateval):
		plateval = splits.pop()
		inset = True 
	plateval = int(plateval)
	#offset = int(offset)

	#Check to see if there are any irregularities for values
	for i in range(len(excs)):
		if plateval == int(excs[i][0]):
			val = 'plate ' + excs[i][1]
			if isinstance(excs[i][2], int):	
				if not inset:
					offset = offset - excs[i][2]
				ret = (val, offset)
				return ret
			else:
				ret = (val, offset)
				return ret
	
	#If this plate is normal...
	#If the plates are numbered
	if (num):
		plateval = 'plate ' + str(plateval - offset)
		ret = (plateval, offset)
		return ret
	#If the plates are lettered
	else:
		alph = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
		temp = offset + 1
		plateval = plateval - temp
		plateval = 'plate ' + alph[plateval]
		ret = (plateval, offset)
		return ret

		
def getPlateValue(identifier,num,offset):
	#get ending of identifier e.g. 0024 from G1234_B6_B7_0024
	splits = identifier.split('_')
	plateval = splits.pop()
	if ('inset' in plateval):
		plateval = splits.pop()
	plateval = int(plateval)
	
	#If the plates are numbered
	if (num):
		plateval = 'plate ' + str(plateval - offset)
		return plateval
	#If the plates are lettered
	else:
		alph = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
		offset += 1
		plateval = plateval - offset
		plateval = 'plate ' + alph[plateval]
		return plateval


###get information###
#Where to start
print('Enter ending of identifier for first plate\ne.g. if plate 1 is G1234_B6_B7_1890_0004, please enter "4"')
first_plate = int(input('Please enter identifier: '))
offset = first_plate-1

#Numbered or lettered
is_numbered = input('Are the plates are numbered, [y/n]: ' ).lower()
if is_numbered == 'y':
    num = True
else:
    num = False
	
#Irregularities
print('Are there any irregularities in the plate values\nAnything that is not only a number or letter?\ne.g. Is there a plate "4k" or plate "B and C"')
irreg = input('[y/n]: ').lower()
irregs = []
while irreg == 'y':
	whichplate = int(input('Please enter the ending of the identifier for the irregular plate: '))
	whatis = input('Please enter the exact value for this plate: ')
	#after = input('What is the value for the following plate?: ')
	#irregs.append({'identifier' : whichplate, 'value' : whatis, 'followingval' : after})
	shift = input('Is the value of the following plate shifted because of this irregularity \n(e.g. This plate "B and C" causes the next plate to be plate "D") [y/n]: ').lower()
	if shift == 'y':
		shift = int(input('Please indicate the value of the shift (in this example -- 1): ').strip())
	irregs.append((whichplate, whatis, shift))
	irreg = input('If there are any more irregular plate values, please enter "y": ')
	
#Open footprint get data	
with open('Boundary.geojson', 'r') as file:
    data = json.load(file)
	
#iterate through each plate and make changes
#If there are no exceptions to values, run regularly

plates = [plate for plate in data['features']]
"""for i in range(len(plates)):
	if 'inset' in plates[i]['properties']['identifier'].split('_').pop():
		plates[i]['properties']['identifier'] = plates[i]['properties']['identifier'].split('_')[:-1]"""
plates = sorted(plates, key = lambda i: i['properties']['identifier'] if 'inset' not in i['properties']['identifier'].split('_')[-1] else i['properties']['identifier']) 

if not irregs:
	for plate in plates:
		identifier = plate['properties']['identifier']
		plate['properties']['plate'] = getPlateValue(identifier, num, offset)

if irregs:
	for plate in plates:
		identifier = plate['properties']['identifier']
		ret = getIrregularPlateValue(identifier, num, offset, irregs)
		plate['properties']['plate'] = ret[0]
		offset = ret[1]
"""if not irregs:
	for plate in data['features']:
		if 'plate' not in plate['properties'].keys():
			identifier = plate['properties']['identifier']
			plate['properties']['plate'] = getPlateValue(identifier, num, offset)


#if there are exceptions...
if irregs:
	for plate in data['features']:
		if 'plate' not in plate['properties'].keys():
			identifier = plate['properties']['identifier']
			#print(identifier)
			ret = getIrregularPlateValue(identifier, num, offset, irregs)
			#print(ret)
			plate['properties']['plate'] = ret[0]
			offset = ret[1]


"""
data['features'] = plates
with open('Boundary.geojson', 'w') as file:
	json.dump(data, file)
print('finished')

#print sorted(lis, key = lambda i: i['age']) 