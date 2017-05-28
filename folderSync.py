#! python3

'''Program that can sync all files and folders between two chosen folders. 
	I need it to keep my photo-backup updated. 
	But script should be able to sync in both ways. 
	And keep track of changes in both folders.'''

from __future__ import with_statement
import logging, math, os, platform, shutil, time, send2trash, sys, re


logFile = logging.getLogger('fs1') 
#create logger for this specific module for logging to file

logFile.setLevel(logging.DEBUG)
#set level of messages to be logged to file

logConsole = logging.getLogger('fs2')
logConsole.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(levelname)s %(asctime)s line %(lineno)s: %(message)s') 
#define format of logging messages

if os.path.exists('.\log'):
	''' create new log every time when script starts instead of writing in the same file '''
	timestr = time.strftime('%Y-%m-%d__%Hh%Mm')
	newLogName = os.path.join('log', 'log_' + timestr + '.txt')
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
	timestr = time.strftime('%Y-%m-%d__%H-%M-%S')
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
			prlog('This folder doesn\'t exist. Write another one.')
			continue
		if not os.path.isdir(pathToFolder):
			prlog('You should denote path to folder, not to file. Try again.')
			continue	
		elif os.path.exists(pathToFolder) and os.path.isdir(pathToFolder):
			print('Got it!')
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
	if os.path.exists(os.path.join(pathToRootFolder, '.folderSync')):
		return True
	else:
		return False	

def getSnapshot(pathToRootFolder, rootFolder):
	# get all file and folder paths, 
	# and collect file size and file time of modification
	print('Getting snapshot of ' + pathToRootFolder + '...')
	logFile.info('Getting snapshot of ' + pathToRootFolder + '...')

	foldersNumber = 0
	filesNumber = 0
	totalSize = 0

	currentSnapshot = {}

	for root, folders, files in os.walk(pathToRootFolder):
		# files = [x for x in files if not x[0] == '.']
		# folders[:] = [x for x in folders if not x[0] == '.']
		
		for folder in folders:
			allMatches = re.search(r'(.*)(\\({s})\\(.*))'.format(s=rootFolder), os.path.join(root, folder))
			fullPath = allMatches.group(0)
			rootFolder = allMatches.group(3)
			pathWithRoot = allMatches.group(2)
			pathWOutRoot = allMatches.group(4)
			allPaths = [fullPath, rootFolder, pathWithRoot, pathWOutRoot]
 
			currentSnapshot[pathWithRoot] = ['folder', allPaths]
			foldersNumber += 1
		
		for file in files:
			allMatches = re.search(r'(.*)\\(({s})\\(.*))'.format(s=rootFolder), os.path.join(root, file))
			fullPath = allMatches.group(0)
			rootFolder = allMatches.group(3)
			pathWithRoot = allMatches.group(2)
			pathWOutRoot = allMatches.group(4)
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
		str("{0:.0f}".format(totalSize / 1024 /1024)) + ' MB.\n')
	logFile.info('Total size of ' + pathToRootFolder + ' is ' + 
		str("{0:.0f}".format(totalSize / 1024 /1024)) + ' MB.\n')

	return currentSnapshot


def compareSnapshots(snapA, snapB, rootA, rootB):
	#check A against B

	notExistInA = []
	notExistInB = []
	samePathAndName = []
	sameNameAndTimeItems = []
	equalFiles = []
	toBeUpdatedFromBtoA = []
	toBeUpdatedFromAtoB = []
	
	pathsOfSnapA = []
	pathsOfSnapB = [] 
	for key in snapB.keys():
		pathsOfSnapB.append(snapB[key][1][3])
		#create list of paths from second folder's snapshot
		#get rid of name of root folder in the path to compare only what is inside folders: get '\somefolder\somefile.ext' instead of 'rootfolder\somefolder\somefile.ext' 	

	for key in snapA.keys():
		pathsOfSnapA.append(snapA[key][1][3])
		#create list of paths from second folder's snapshot
		#get rid of name of root folder in the path to compare only what is inside folders: get '\somefolder\somefile.ext' instead of 'rootfolder\somefolder\somefile.ext' 	

		if snapA[key][1][3] in pathsOfSnapB:
			#if item with same path exists in both folders to be synced
			
			if snapA[key][0] == 'file': #if item is file - compare them
				samePathAndName.append(key)
				# logConsole.debug('ROOT B IS: ' + rootB)
				# logConsole.debug('snapA[key][1][3] IS: ' + snapA[key][1][3])
				correspondingFileInB = os.path.join(rootB, snapA[key][1][3])
				# logConsole.debug('CORRESPONDING FILE IN B IS: ' + correspondingFileInB)
				#put back root folder to path of file/folder in B
				logConsole.debug('KEY IS ' + key)
				with open(snapA[key][1][0], 'rb') as f1:
					with open(snapB[correspondingFileInB][1][0], 'rb') as f2:
						if f1.read() == f2.read():
							equalFiles.append(key)
						else:
							if snapA[key][3] < snapB[correspondingFileInB][3]:
								#file in A newer than file in B -> add it to list to be copied from A to B
								toBeUpdatedFromAtoB.append(key)
							elif snapA[key][3] > snapB[correspondingFileInB][3]:
								#file in A older than file in B -> add it to list to be copied from B to A
								toBeUpdatedFromBtoA.append(key)
		else:
            # if file doesn't exist in B -> add it in list to be copied from A
			notExistInB.append(key)

	for path in pathsOfSnapB:
		if not path in pathsOfSnapA:
			notExistInA.append(rootB + path)
	#check which files from B exist in A		


	######### result messages to console and log file########## 		
	print('')
	print('###########################')
	print(firstFolder)
	logFile.info(firstFolder)
	print('###########################')
	
	print(str(len(samePathAndName)) + ' files that exist in both folders.')
	logFile.info(str(len(samePathAndName)) +  ' files that exist in both folders.')
	for path in samePathAndName:
		logFile.info(path)
	logFile.info('\n')	

	print(str(len(equalFiles)) + ' files don\'t need update.')
	logFile.info(str(len(equalFiles)) + ' files don\'t need update.')
	for path in equalFiles:
		logFile.info(path)
	logFile.info('\n')	

	print(str(len(notExistInB)) + ' files from  ' + firstFolder + ' don\'t exist in ' + secondFolder)
	logFile.info(str(len(notExistInB)) + ' files from  ' + firstFolder + ' don\'t exist in ' + secondFolder)
	for path in notExistInB:
		logFile.info(path)
	logFile.info('\n')

	print(str(len(notExistInA)) + ' files from  ' + secondFolder + ' don\'t exist in ' + firstFolder)
	logFile.info(str(len(notExistInA)) + ' files from  ' + secondFolder + ' don\'t exist in ' + firstFolder)
	for path in notExistInA:
		logFile.info(path)
	logFile.info('\n')	

	print(str(len(toBeUpdatedFromAtoB)) + ' files need to update in ' + secondFolder)
	logFile.info(str(len(toBeUpdatedFromAtoB)) + ' files need to update in ' + secondFolder)
	for path in toBeUpdatedFromAtoB:
		logFile.info(path)
	logFile.info('\n')	

	print(str(len(toBeUpdatedFromBtoA)) + ' files need to update in ' + firstFolder)
	logFile.info(str(len(toBeUpdatedFromBtoA)) + ' files need to update in ' + firstFolder)
	for path in toBeUpdatedFromBtoA:
		logFile.info(path)
	logFile.info('\n')

	for path in pathsOfSnapB:
		logFile.debug('ITEM IN B: ' + path)
	for path in pathsOfSnapA:
		logFile.debug('ITEM IN A: ' + path)			

	return notExistInA, notExistInB, toBeUpdatedFromBtoA, toBeUpdatedFromAtoB

def syncFiles(compareResult, rootFirstFolder, rootSecondFolder):
	#take lists with files to copy and copy them
	notExistInA, notExistInB, toBeUpdatedFromBtoA, toBeUpdatedFromAtoB = compareResult

	logFile.info('Strat syncing files...')
	logConsole.info('Strat syncing files...')

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
snapshostFirstFolder = getSnapshot(firstFolder, rootFirstFolder)
snapshostSecondFolder = getSnapshot(secondFolder, rootSecondFolder)
#get all paths of all files and folders with properties from folders to be compared 

compareResult = compareSnapshots(snapshostFirstFolder, snapshostSecondFolder, rootFirstFolder, rootSecondFolder)

while True:
	startSyncing = input('Do you want to sync these files? y/n: ').lower()
	logFile.info('Do you want to sync these files? y/n: ')
	if startSyncing == 'y':
		#call function that handles syncing
		break
	elif startSyncing == 'n':
		#exit script
		print('Goodbye.')
		logFile.info('Goodbye.')
		sys.exit()
	else:
		print('Error of input. Try again.')
		logFile.info('Error of input. Try again.')
		continue	











########## crap ##############

# 	getattr(logFile, level)(message)
# 	#what is above means "logFile.level(message)" where level is method's name which is known only by runtime. For example "logFile.info(message)" where 'info' is coming from variable 
