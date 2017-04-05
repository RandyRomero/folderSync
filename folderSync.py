#! python3

'''Program that can sync all files and folders between two chosen folders. I need it to keep my photo-backup updated. But script should be able to sync in both ways. And keep track of changes in both folders.'''

import logging, os, time

logging.basicConfig(
	format = "%(levelname) -1s %(asctime)s line %(lineno)s: %(message)s",
	level = logging.DEBUG
	)

if os.path.exists('.\log'):
	timestr = time.strftime('%Y-%m-%d__%H-%M')
	newLogName = os.path.join('log', 'log_' + timestr + '.txt')
	if os.path.exists(newLogName):
		i = 2
		if os.path.exists(os.path.join('log', 'log ' + timestr + '(' + str(i) + ').txt')):
			while os.path.exists(os.path.join('log', 'log ' + timestr + '(' + str(i) + ').txt')):
				i += 1
				continue
			logFile = open(os.path.join('log', 'log ' + timestr + '(' + str(i) + ').txt'), 'w')
		else:
			logFile = open(os.path.join('log', 'log ' + timestr + '(' + str(i) + ').txt'), 'w')
	else:
		logFile = open(newLogName, 'w')
else:
	os.mkdir('.\log')
	timestr = time.strftime('%Y-%m-%d__%H-%M-%S')
	logFile = open(os.path.join('log', 'log_' + timestr + '.txt'), 'w')

# def prlog(message):
# 	print(message)


# def getSnapshot():

def hasItEverBeenSynced(rootFolder):
	if os.path.exists(os.path.join(rootFolder, '.folderSync')):
		return True
	else:
		return False



#TODO make menu to let user choose folders to sync
# ubtil then I am gonna set it manually at code to save some time while checking

firstFolder = ('.\\A')
secondFolder = ('.\\B')

firstFolderSynced = hasItEverBeenSynced(firstFolder)
logging.info(firstFolderSynced)
secondFolderSynced = hasItEverBeenSynced(secondFolder)
logging.info(secondFolderSynced)

