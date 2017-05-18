#! python3

'''Program that can sync all files and folders between two chosen folders. 
	I need it to keep my photo-backup updated. 
	But script should be able to sync in both ways. 
	And keep track of changes in both folders.'''

import logging, os, platform, time, send2trash, re

logging.basicConfig(
	format = "%(levelname) -1s %(asctime)s line %(lineno)s: %(message)s",
	level = logging.DEBUG
	)

def prlog(message):
	#both print and log messages
	print(message)
	logFile.write(message + '\n')

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
		prlog('Please, choose first folder to sync.')
		firstFolder = chooseFolder()
		prlog('Please, choose second folder to sync.')
		secondFolder = chooseFolder()
		if firstFolder == secondFolder:
			prlog('\nPaths can\'t be equal. Start over')
			continue
		else:
			prlog('\nPaths accepted. Start analyzing...\n')
			break

	return firstFolder, secondFolder			

def hasItEverBeenSynced(rootFolder):
	# check if there is already snapshot from previous sync
	if os.path.exists(os.path.join(rootFolder, '.folderSync')):
		return True
	else:
		return False

def makeLogFile():

# make log file with date and time
# if file has already been ctreated, make file(2) and so on

	if os.path.exists('.\log'):
		timestr = time.strftime('%Y-%m-%d__%Hh%Mm')
		newLogName = os.path.join('log', 'log_' + timestr + '.txt')
		if os.path.exists(newLogName):
			i = 2
			while os.path.exists(os.path.join('log', 'log ' + timestr + 
				'(' + str(i) + ').txt')):
				i += 1
				continue
			logFile = open(os.path.join('log', 'log ' + timestr + 
				'(' + str(i) + ').txt'), 'w', encoding='UTF-8')
		else:
			logFile = open(newLogName, 'w', encoding='UTF-8')
	else:
		os.mkdir('.\log')
		timestr = time.strftime('%Y-%m-%d__%H-%M-%S')
		logFile = open(os.path.join('log', 'log_' + timestr + '.txt'), 
			'w', encoding='UTF-8')

	return logFile		

def getSnapshot(rootFolder):
	# get all file and folder paths, 
	# and collect file size and file time of modification
	prlog('Getting snapshot of ' + rootFolder + '...')

	foldersNumber = 0
	filesNumber = 0
	totalSize = 0

	currentSnapshot = {}

	for root, folders, files in os.walk(rootFolder):
		# files = [x for x in files if not x[0] == '.']
		# folders[:] = [x for x in folders if not x[0] == '.']
		
		for folder in folders:
			folderPath = os.path.relpath(os.path.join(root, folder))
			currentSnapshot[folderPath] = ['folder']
			foldersNumber += 1
		
		for file in files:
			filePath = os.path.relpath(os.path.join(root, file))
			sizeOfCurrentFile = os.path.getsize(filePath)
			totalSize += sizeOfCurrentFile
			currentSnapshot[filePath] = ['file', sizeOfCurrentFile, os.path.getmtime(filePath)]
			filesNumber += 1

	prlog('There are ' + str(foldersNumber) + ' folders and ' + 
		str(filesNumber) + ' files in ' + rootFolder)
	prlog('Total size of ' + rootFolder + ' is ' + 
		str("{0:.0f}".format(totalSize / 1024 /1024)) + ' MB.\n')

	return currentSnapshot


def compareSnapshots(snapA, rootA, snapB, rootB):
	#check A against B

	notExistInB = []
	sameNameAndTimeItems = []
	sameNameDiffTimeItems = []
	
	pathsOfSnapB = [] 
	for key in snapB.keys():
		#create list of paths from second folder's snapshot
		path_B_File_wo_Root = re.search(r'^([^\\]*)(\\.*)', key).group(2)
		#get rid of name of root folder in the path to compare only what is inside folders: get '\somefolder\somefile.ext' instead of 'rootfolder\somefolder\somefile.ext'

		pathsOfSnapB.append(path_B_File_wo_Root)

	for key in snapA:
		path_A_File_wo_Root = re.search(r'^([^\\]*)(\\.*)', key).group(2)
		#get rid of root folder in path

		if path_A_File_wo_Root in pathsOfSnapB:
			# prlog(key + ' --- EXISTS.')
			if snapA[key][0] == 'file':
				#compare time of creation of same files
				correspondigFileInB = rootB + path_A_File_wo_Root
				if snapA[key][2] == snapB[correspondigFileInB][2]:
					prlog(key + ' and ' + correspondigFileInB + ' are completely the same.')
				
			else:
				print('folder')
		else:
			# prlog(key + ' --- MISSING')
			notExistInB.append(key)

	#show files that don't exist in A but exists in B
	prlog('')
	prlog(str(len(notExistInB)) + ' files ain\'t exist in ' + secondFolder + ':')
	for path in notExistInB:
		prlog(path)

logFile = makeLogFile()

#paths hardcoded for the sake of speed of testing
# Scrip gets the name of PC in order to work on my several laptops without
# typing paths for folders to sync

if platform.node() == 'ZenBook3':
	print('You are on dev laptop. Using default adressess for test.')
	firstFolder = 'D:\\YandexDisk\\Studies\\Python\\folderSync\\A'
	secondFolder = 'D:\\YandexDisk\\Studies\\Python\\folderSync\\B'
elif platform.node() == 'AcerVNitro':
	print('You are on dev laptop. Using default adressess for test.')	
	firstFolder = 'C:\\yandex.disk\\Studies\\Python\\folderSync\\A'
	secondFolder = 'C:\\yandex.disk\\Studies\\Python\\folderSync\\B'
elif platform.node() == 'ASUSG751':
	print('You are on dev laptop. Using default adressess for test.')	
	firstFolder = 'C:\\YandexDisk\\Studies\\Python\\folderSync\\A'
	secondFolder = 'C:\\YandexDisk\\Studies\\Python\\folderSync\\B'
else:
	print('Unknown computer.')
	firstFolder, secondFolder = menuChooseFolders()

firstFolderSynced = hasItEverBeenSynced(firstFolder)
logging.info(firstFolderSynced)
secondFolderSynced = hasItEverBeenSynced(secondFolder)
logging.info(secondFolderSynced)


snapshostFirstFolder = getSnapshot(firstFolder)
snapshostSecondFolder = getSnapshot(secondFolder)
rootFirstFolder = re.search(r'(\w+$)', firstFolder).group(0)
rootSecondFolder = re.search(r'(\w+$)', secondFolder).group(0)
print(rootSecondFolder)
compareSnapshots(snapshostFirstFolder, rootFirstFolder, snapshostSecondFolder, rootSecondFolder)



#TODO make menu to let user choose folders to sync
# until then I am gonna set it manually at code to save some time while checking



