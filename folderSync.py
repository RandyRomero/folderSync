#! python3

'''Program that can sync all files and folders between two chosen folders. 
	I need it to keep my photo-backup updated. 
	But script should be able to sync in both ways. 
	And keep track of changes in both folders.'''

from __future__ import with_statement
import logging, math, os, re, shutil, shelve, sys, time 
#import platform
#import send2trash

############################ Set loggers ####################################

logFile = logging.getLogger('fs1') 
#create logger for this specific module for logging to file

logFile.setLevel(logging.DEBUG)
#set level of messages to be logged to file

logConsole = logging.getLogger('fs2')
logConsole.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(levelname)s %(asctime)s line %(lineno)s: %(message)s') 
#define format of logging messages

timestr = time.strftime('%Y-%m-%d__%Hh%Mm')
newLogName = os.path.join('log', 'log_' + timestr + '.txt')

if os.path.exists('.\log'):
	''' create new log every time when script starts instead of writing in the same file '''
	
	if os.path.exists(newLogName):
		i = 2
		while os.path.exists(os.path.join('log', 'log ' + timestr + 
			'(' + str(i) + ').txt')):
			i += 1
			continue
		file_handler = logging.FileHandler(os.path.join('log', 'log ' + timestr + '(' + str(i) + ').txt'), encoding='utf8')	
	else:
		file_handler = logging.FileHandler(newLogName, encoding='utf8')
else:
	os.mkdir('.\log')
	file_handler = logging.FileHandler(os.path.join(newLogName, encoding='utf8'))

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
#set format to both handlers


logFile.addHandler(file_handler)
logConsole.addHandler(stream_handler)
#apply handler to this module (folderSync.py)



def chooseFolder():
	# used to check validity of file's path given by user
	while True:
		pathToFolder = input('Path: ')
		if not os.path.exists(pathToFolder):
			print('This folder doesn\'t exist. Write another one.')
			logFile.info('This folder doesn\'t exist. Write another one.')
			continue
		if not os.path.isdir(pathToFolder):
			print('You should denote path to folder, not to file. Try again.')
			logFile.info('You should denote path to folder, not to file. Try again.')
			continue	
		elif os.path.exists(pathToFolder) and os.path.isdir(pathToFolder):
			print('Got it!')
			logFile.info('Got it!')
			return pathToFolder

def menuChooseFolders():
	# let user choose folders and check them not to have the same path
	while True:
		print('Please, choose first folder to sync.')
		logFile.info('Please, choose first folder to sync.')
		firstFolder = chooseFolder()
		print('Please, choose second folder to sync.')
		logFile.info('Please, choose second folder to sync.')
		secondFolder = chooseFolder()
		if firstFolder == secondFolder:
			print('\nPaths can\'t be equal. Start over')
			logFile.info('\nPaths can\'t be equal. Start over')
			continue
		else:
			print('\nPaths accepted. Start analyzing...\n')
			logFile.info('\nPaths accepted. Start analyzing...\n')
			break

	return firstFolder, secondFolder			

def hasItEverBeenSynced(pathToRootFolder):
	# check if there is already snapshot from previous sync
	if os.path.exists(os.path.join(pathToRootFolder, '.folderSyncSnapshot')):
		return True
	else:
		return False	

def getSnapshot(pathToRootFolder, rootFolder):
	# get all file and folder paths, 
	# and collect file size and file time of modification
	print('\nGetting snapshot of ' + pathToRootFolder + '...')
	logFile.info('\nGetting snapshot of ' + pathToRootFolder + '...')

	foldersNumber = 0
	filesNumber = 0
	totalSize = 0

	currentSnapshot = {}

	for root, folders, files in os.walk(pathToRootFolder):

		folders[:] = [x for x in folders if not x == '.folderSyncSnapshot']
		#only add to list folders that not '.folderSyncSnapshot'

		for folder in folders:
				
			fullPath = os.path.join(root, folder)
			pathWOutRoot = fullPath.split(pathToRootFolder + '\\')[1]
			#subtract path to root folder from full path whereby get path to folder/file without root folder 
			pathWithRoot = os.path.join(rootFolder, pathWOutRoot)
			
			allPaths = [fullPath, rootFolder, pathWithRoot, pathWOutRoot]
 
			currentSnapshot[pathWithRoot] = ['folder', allPaths]
			foldersNumber += 1
		
		for file in files:
			fullPath = os.path.join(root, file)
			pathWOutRoot = fullPath.split(pathToRootFolder + '\\')[1]
			pathWithRoot = os.path.join(rootFolder, pathWOutRoot)
			allPaths = [fullPath, rootFolder, pathWithRoot, pathWOutRoot]
			
			sizeOfCurrentFile = os.path.getsize(allPaths[0])
			totalSize += sizeOfCurrentFile
			currentSnapshot[pathWithRoot] = ['file', allPaths, sizeOfCurrentFile, math.ceil(os.path.getmtime(allPaths[0]))]
			#math.ceil for rounding float
			filesNumber += 1

	print('There are ' + str(foldersNumber) + ' folders and ' + 
		str(filesNumber) + ' files in ' + pathToRootFolder)
	logFile.info('There are ' + str(foldersNumber) + ' folders and ' + 
		str(filesNumber) + ' files in ' + pathToRootFolder)
	print('Total size of ' + pathToRootFolder + ' is ' + 
		str("{0:.0f}".format(totalSize / 1024 /1024)) + ' MB.')
	logFile.info('Total size of ' + pathToRootFolder + ' is ' + 
		str("{0:.0f}".format(totalSize / 1024 /1024)) + ' MB.\n')

	return currentSnapshot

def getChangesBetweenStatesOFFolders(pathToFolder, rootOfPath):
	'''Compare folder's snapshot that was stored in .folderSyncSnapshot 
	folder during last syncing with fresh snashot that is going to be taken within this function. It needs to figure out which files were removed in order not to acquire it from not yet updated folder again'''


	try:
		shelFile = shelve.open(os.path.join(pathToFolder, '.folderSyncSnapshot', 'snapshot'))
	except:
		print('Can\'t open stored snapshot. Exit.')
		sys.exit()

	folderSnapshot = getSnapshot(pathToFolder, rootOfPath)
	previousSnapshot = shelFile['snapshot']

	pathOfPrevSnapshot = []
	pathOfCurrentSnapshot = []
	itemWasRemoved = []
	itemWasRemovedCount = 0
	newItem = []
	newItemCount = 0

	for key in folderSnapshot.keys():
		pathOfCurrentSnapshot.append(folderSnapshot[key][1][3])

	for key in previousSnapshot.keys():
		pathOfPrevSnapshot.append(previousSnapshot[key][1][3])

		if previousSnapshot[key][1][3] not in pathOfCurrentSnapshot:
			logFile.info(key + ' WAS REMOVED')
			itemWasRemoved.append(key)
			itemWasRemovedCount += 1

	for path in pathOfCurrentSnapshot:
		if path not in pathOfPrevSnapshot:
			# print(path + ' IS NEW ITEM')
			logFile.info(path + ' IS NEW ITEM')
			newItem.append(path)
			newItemCount += 1

	print('\n' + pathToFolder)
	logFile.info('\n' + pathToFolder)
	print(str(itemWasRemovedCount) + ' items were removed')
	logFile.info(str(itemWasRemovedCount) + ' items were removed')
	
	print('There are ' + str(newItemCount) + ' new items')
	logFile.info('There are ' + str(newItemCount) + ' new items')
	print()
	logFile.info('\n')

def lowSnapshotComparison(firstFolder, secondFolder, rootFirstFolder, rootSecondFolder):
	'''compare files in binary mode if folders haven't been synced before'''

	notExistInA = []
	notExistInB = []
	samePathAndName = []
	equalFiles = []
	toBeUpdatedFromBtoA = []
	toBeUpdatedFromAtoB = []
	''' in each list script adds two version of path to file: 
	first (key) with root folder, second (snapA[key][1][0]]) with full path.
	First is shorter and for logs, 
	second is full and for operations of copying etc
	Below it looks like samePathAndName.append([key, snapA[key][1][0]])
	'''
	
	pathsOfSnapA = []
	pathsOfSnapB = [] 
	
	snapA = getSnapshot(firstFolder, rootFirstFolder)
	snapB = getSnapshot(secondFolder, rootSecondFolder)

	
	for key in snapB.keys():
		pathsOfSnapB.append(snapB[key][1][3])
		#create list of paths from second folder's snapshot
		#get rid of name of root folder in the path to compare only what is inside folders: get '\somefolder\somefile.ext' instead of 'rootfolder\somefolder\somefile.ext' 	

	#check A against B	
	for key in snapA.keys():
		pathsOfSnapA.append(snapA[key][1][3])
		# --//-- 	

		if snapA[key][1][3] in pathsOfSnapB:
			#if item with same path exists in both folders to be synced
			
			if snapA[key][0] == 'file': #if item is file - compare them
				samePathAndName.append(snapA[key])
				correspondingFileInB = os.path.join(rootSecondFolder, snapA[key][1][3])
				# logConsole.debug('CORRESPONDING FILE IN B IS: ' + correspondingFileInB)
				#put back root folder to path of file/folder in B
				print('Comparing files... ' + snapA[key][1][3])
				with open(snapA[key][1][0], 'rb') as f1:
					with open(snapB[correspondingFileInB][1][0], 'rb') as f2:
						if f1.read() == f2.read():
							equalFiles.append(snapA[key])
						else:
							if snapA[key][3] < snapB[correspondingFileInB][3]:
								#file in A newer than file in B -> add it to list to be copied from A to B
								toBeUpdatedFromAtoB.append(snapA[key])
							elif snapA[key][3] > snapB[correspondingFileInB][3]:
								#file in A older than file in B -> add it to list to be copied from B to A
								toBeUpdatedFromBtoA.append(snapA[key])
		else:
            # if file doesn't exist in B -> add it in list to be copied from A
			notExistInB.append(snapA[key])

	for path in pathsOfSnapB:
		if not path in pathsOfSnapA:
			notExistInA.append([os.path.join(rootSecondFolder, path), os.path.join(rootSecondFolder, path)]) #FIX!
	#check which files from B exist in A		


	######### result messages to console and log file########## 		
	print('')
	print('###########################')
	print(firstFolder)
	logFile.info(firstFolder)
	print('###########################')
	
	print(str(len(samePathAndName)) + ' item(s) that exist in both folders.')
	logFile.info(str(len(samePathAndName)) +  ' files that exist in both folders.')
	for path in samePathAndName:
		logFile.info(path[0])
	logFile.info('\n')	

	print(str(len(equalFiles)) + ' item(s) don\'t need update.')
	logFile.info(str(len(equalFiles)) + ' files don\'t need update.')
	for path in equalFiles:
		logFile.info(path[0])
	logFile.info('\n')	

	print(str(len(notExistInB)) + ' item(s) from  ' + firstFolder + ' don\'t exist in ' + secondFolder)
	logFile.info(str(len(notExistInB)) + ' items from  ' + firstFolder + ' don\'t exist in ' + secondFolder)
	for path in notExistInB:
		logFile.info(path[0])
	logFile.info('\n')

	print(str(len(notExistInA)) + ' item(s) from  ' + secondFolder + ' don\'t exist in ' + firstFolder)
	logFile.info(str(len(notExistInA)) + ' item(s) from  ' + secondFolder + ' don\'t exist in ' + firstFolder)
	for path in notExistInA:
		logFile.info(path[0])
	logFile.info('\n')	

	print(str(len(toBeUpdatedFromAtoB)) + ' item(s) need to update in ' + secondFolder)
	logFile.info(str(len(toBeUpdatedFromAtoB)) + ' item(s) need to update in ' + secondFolder)
	for path in toBeUpdatedFromAtoB:
		logFile.info(path[0])
	logFile.info('\n')	

	print(str(len(toBeUpdatedFromBtoA)) + ' item(s) need to update in ' + firstFolder)
	logFile.info(str(len(toBeUpdatedFromBtoA)) + ' item(s) need to update in ' + firstFolder)
	for path in toBeUpdatedFromBtoA:
		logFile.info(path[0])
	logFile.info('\n')

	# for path in pathsOfSnapB:
	# 	logFile.debug('ITEM IN B: ' + path)
	# for path in pathsOfSnapA:
	# 	logFile.debug('ITEM IN A: ' + path)			

	return notExistInA, notExistInB, toBeUpdatedFromBtoA, toBeUpdatedFromAtoB

def syncFiles(compareResult, firstFolder, secondFolder):
	#take lists with files to copy and copy them
	notExistInA, notExistInB, toBeUpdatedFromBtoA, toBeUpdatedFromAtoB = compareResult

	logFile.info('Start syncing files...')
	logConsole.info('Start syncing files...')

	for file in notExistInA:
		pathWithoutRoot = file[1][3] # path of file in b from without root folder and all the other previous folders
		fullPathItemInB = file[1][0] # full path of file in b
		fullPathItemInA = os.path.join(firstFolder, pathWithoutRoot) #path where copy item to
		if file[0] == 'folder':
			os.mkdir(fullPathItemInA)
			logConsole.info(fullPathItemInA + ' is created.')
			logFile.info(fullPathItemInA + ' is created.')
		elif file[0] == 'file':
			if os.path.exists(fullPathItemInA):
				#it shouldn't happened, but just in case
				logConsole.warning('WARNING: ' + fullPathItemInA + ' already exists!')
				logFile.warning('WARNING: ' + fullPathItemInA + ' already exists!')
				continue
			else:
				shutil.copy2(fullPathItemInB, fullPathItemInA)
				logConsole.info(os.path.basename(fullPathItemInA + ' were copied.'))


	# for file in notExistInA:
	# 	pathToCopy = (rootFirstFolder + re.search(r'^([^\\]*)(\\.*)', file).group(2))
	# 	shutil.copy(file, pathToCopy)

def devLap():

	logConsole.debug('You are on dev laptop. Using default adressess for test.')
	logFile.debug('You are on dev laptop. Using default adressess for test.')

# #paths hardcoded for the sake of speed of testing
# # Scrip gets the name of PC in order to work on my several laptops without
# # typing paths for folders to sync

# if platform.node() == 'ZenBook3':
# 	devLap()
# 	firstFolder = 'D:\\YandexDisk\\Studies\\Python\\folderSync\\A'
# 	secondFolder = 'D:\\YandexDisk\\Studies\\Python\\folderSync\\B'
# elif platform.node() == 'AcerVNitro':
# 	devLap()
# 	firstFolder = 'C:\\yandex.disk\\Studies\\Python\\folderSync\\A'
# 	secondFolder = 'C:\\yandex.disk\\Studies\\Python\\folderSync\\B'
# elif platform.node() == 'ASUSG751':
# 	devLap()
# 	firstFolder = 'C:\\YandexDisk\\Studies\\Python\\folderSync\\A'
# 	secondFolder = 'C:\\YandexDisk\\Studies\\Python\\folderSync\\B'
# else:
# 	logConsole.debug('Unknown computer.')
# 	logFile.debug('Unknown computer.')
# 	firstFolder, secondFolder = menuChooseFolders()

firstFolder, secondFolder = menuChooseFolders()

firstFolderSynced = hasItEverBeenSynced(firstFolder)
logFile.debug(firstFolder + ' Has been synced before? ' + str(firstFolderSynced))
logConsole.debug(firstFolder + ' Has been synced before? ' + str(firstFolderSynced))

secondFolderSynced = hasItEverBeenSynced(secondFolder)
logFile.debug(secondFolder + ' Has been synced before? ' + str(secondFolderSynced))
logConsole.debug(secondFolder + ' Has been synced before? ' + str(secondFolderSynced))

rootFirstFolder = re.search(r'(\w+$)', firstFolder).group(0)
rootSecondFolder = re.search(r'(\w+$)', secondFolder).group(0)
#get names of root folders to be compared
# snapshotFirstFolder = getSnapshot(firstFolder, rootFirstFolder)
# snapshotSecondFolder = getSnapshot(secondFolder, rootSecondFolder)
#get all paths of all files and folders with properties from folders to be compared 

if firstFolderSynced:
	getChangesBetweenStatesOFFolders(firstFolder, rootFirstFolder)

if secondFolderSynced:
	getChangesBetweenStatesOFFolders(secondFolder, rootSecondFolder)

if firstFolderSynced and secondFolderSynced:
	print('There should be function that compare folders if they have already been compared')
else:
	compareResult = lowSnapshotComparison(firstFolder, secondFolder, rootFirstFolder, rootSecondFolder)			




################### Syncing section: copy and delete items ###################

while True:
	startSyncing = input('Do you want to sync these files? y/n: ').lower()
	logFile.info('Do you want to sync these files? y/n: ')
	if startSyncing == 'y':
		if firstFolderSynced and secondFolderSynced:
			logConsole.debug('Call function that syncing folders that have already been synced')
		else:
			#if one or neither of two folders have been synced already	
			syncFiles(compareResult, firstFolder, secondFolder)
		break
	elif startSyncing == 'n':
		#continue without copy/remove files
		break
	else:
		print('Error of input. Try again.')
		logFile.info('Error of input. Try again.')
		continue	


def storeSnapshotBerofeExit(folderToTakeSnapshot, rootFolder, folderSynced):
	'''Store state of folder to be synced after it was synced on storage'''

	if folderSynced:
		shelFile = shelve.open(os.path.join(folderToTakeSnapshot, '.folderSyncSnapshot', 'snapshot'))
	else:
		os.mkdir(os.path.join(folderToTakeSnapshot, '.folderSyncSnapshot'))
		shelFile = shelve.open(os.path.join(folderToTakeSnapshot, '.folderSyncSnapshot', 'snapshot'))

	snapshot = getSnapshot(folderToTakeSnapshot, rootFolder)
	
	shelFile['path'] = folderToTakeSnapshot
	shelFile['snapshot'] = snapshot
	shelFile['date'] = timestr

	print('Snapshot of ' + rootFolder + ' was stored in ' + folderToTakeSnapshot + ' at ' + timestr)
	logFile.info('Snapshot of ' + rootFolder + ' was stored in ' + folderToTakeSnapshot + ' at ' + timestr)

	shelFile.close()


storeSnapshotBerofeExit(firstFolder, rootFirstFolder, firstFolderSynced)
storeSnapshotBerofeExit(secondFolder, rootSecondFolder, secondFolderSynced)

print('Goodbye.')
logFile.info('Goodbye.')



########## crap ##############

# 	getattr(logFile, level)(message)
# 	#what is above means "logFile.level(message)" where level is method's name which is known only by runtime. For example "logFile.info(message)" where 'info' is coming from variable 
