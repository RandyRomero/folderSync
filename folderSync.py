#! python3

'''Program that can sync all files and folders between two chosen folders. I need it to keep my photo-backup updated. But script should be able to sync in both ways. And keep track of changes in both folders.'''

import logging, os, time, send2trash

logging.basicConfig(
	format = "%(levelname) -1s %(asctime)s line %(lineno)s: %(message)s",
	level = logging.DEBUG
	)

# make log file with date and time // if file has already been ctreated, make file(2) and so on
if os.path.exists('.\log'):
	timestr = time.strftime('%Y-%m-%d__%Hh%Mm')
	newLogName = os.path.join('log', 'log_' + timestr + '.txt')
	if os.path.exists(newLogName):
		i = 2
		while os.path.exists(os.path.join('log', 'log ' + timestr + '(' + str(i) + ').txt')):
			i += 1
			continue
		logFile = open(os.path.join('log', 'log ' + timestr + '(' + str(i) + ').txt'), 'w', encoding='UTF-8')
	else:
		logFile = open(newLogName, 'w', encoding='UTF-8')
else:
	os.mkdir('.\log')
	timestr = time.strftime('%Y-%m-%d__%H-%M-%S')
	logFile = open(os.path.join('log', 'log_' + timestr + '.txt'), 'w', encoding='UTF-8')

# def prlog(message):
# 	print(message)


# def getSnapshot():

def hasItEverBeenSynced(rootFolder):
	if os.path.exists(os.path.join(rootFolder, '.folderSync')):
		return True
	else:
		return False

firstFolder = ('.\\A')
secondFolder = ('.\\B')

firstFolderSynced = hasItEverBeenSynced(firstFolder)
logging.info(firstFolderSynced)
secondFolderSynced = hasItEverBeenSynced(secondFolder)
logging.info(secondFolderSynced)


def getSnapshot(rootFolder):
	
	currentSnapshot = []
	for root, folders, files in os.walk(rootFolder):
		# files = [x for x in files if not x[0] == '.']
		# folders[:] = [x for x in folders if not x[0] == '.']
		
		for folder in folders:
			folderPath = os.path.join(root, folder)
			currentSnapshot.append([folderPath, 'folder'])
		
		for file in files:
			filePath = os.path.join(root, file)
			currentSnapshot.append([filePath, 'file', os.path.getsize(filePath), os.path.getmtime(filePath)])

	
	logging.info('There are ' + str(len(currentSnapshot)) + ' files and folders.')

getSnapshot('C:\\yandex.disk\\Studies\\Python\\Chapter 9')


#TODO make menu to let user choose folders to sync
# ubtil then I am gonna set it manually at code to save some time while checking



