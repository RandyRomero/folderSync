#! python3

# Program that can sync all files and folders between two chosen folders.
# I need it to keep my photo-backup updated.
# But script should be able to sync in both ways.
# And keep track of changes in both folders.'''

import logging, math, os, re, shutil, send2trash, shelve, sys, time 
# import platform

firstFolder = ''
secondFolder = ''

logFile = logging.getLogger('fs1') 
# create logger for this specific module for logging to file

logFile.setLevel(logging.DEBUG)
# set level of messages to be logged to file

logConsole = logging.getLogger('fs2')
logConsole.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(levelname)s %(asctime)s line %(lineno)s: %(message)s') 
# define format of logging messages

timestr = time.strftime('%Y-%m-%d__%Hh%Mm')
newLogName = os.path.join('log', 'log_' + timestr + '.txt')

if os.path.exists('.\log'):
    ''' create new log every time when script starts instead of writing in the same file '''

    if os.path.exists(newLogName):
        i = 2
        while os.path.exists(os.path.join('log', 'log ' + timestr + '(' + str(i) + ').txt')):
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
# set format to both handlers


logFile.addHandler(file_handler)
logConsole.addHandler(stream_handler)
# apply handler to this module (folderSync.py)


def choose_folder():
    # used to check validity of file's path given by user
    while True:
        path_to_folder = input('Path: ')
        if not os.path.exists(path_to_folder):
            print('This folder doesn\'t exist. Write another one.')
            logFile.info('This folder doesn\'t exist. Write another one.')
            continue
        if not os.path.isdir(path_to_folder):
            print('You should denote path to folder, not to file. Try again.')
            logFile.info('You should denote path to folder, not to file. Try again.')
            continue
        elif os.path.exists(path_to_folder) and os.path.isdir(path_to_folder):
            print('Got it!')
            logFile.info('Got it!')
            return path_to_folder

def menu_choose_folders():
    # let user choose folders and check them not to have the same path

    global firstFolder
    global secondFolder

    while True:
        print('Please, choose first folder to sync.')
        logFile.info('Please, choose first folder to sync.')
        firstFolder = choose_folder()
        print('Please, choose second folder to sync.')
        logFile.info('Please, choose second folder to sync.')
        secondFolder = choose_folder()
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

    startTime = time.time()
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
            #math.ceil for rounding float because otherwise it is to precise for our purpose
            filesNumber += 1

    print('There are ' + str(foldersNumber) + ' folders and ' +
        str(filesNumber) + ' files in ' + pathToRootFolder)
    logFile.info('There are ' + str(foldersNumber) + ' folders and ' +
        str(filesNumber) + ' files in ' + pathToRootFolder)
    print('Total size of ' + pathToRootFolder + ' is ' +
        str("{0:.0f}".format(totalSize / 1024 /1024)) + ' MB.')
    logFile.info('Total size of ' + pathToRootFolder + ' is ' +
        str("{0:.0f}".format(totalSize / 1024 /1024)) + ' MB.\n')

    print('--- {0:.3f} seconds ---\n'.format(time.time() - startTime))
    logFile.info('--- {0:.3f} seconds ---\n'.format(time.time() - startTime))
    return currentSnapshot

def getChangesBetweenStatesOfFolders(pathToFolder, rootOfPath):
    '''Compare folder's snapshot that was stored in .folderSyncSnapshot
    folder during last syncing with fresh snashot that is going to be taken within this function. It needs to figure out which files were removed in order not to acquire it from not yet updated folder again'''

    try:
        shelFile = shelve.open(os.path.join(pathToFolder, '.folderSyncSnapshot', 'snapshot'))
    except:
        print('Can\'t open stored snapshot. Exit.')
        sys.exit()

    currentFolderSnapshot = getSnapshot(pathToFolder, rootOfPath)
    # analyse current state of folder
    previousSnapshot = shelFile['snapshot']
    # load previous state of folder from shelve db

    itemsFromPrevSnapshot = []
    itemsFromCurrentSnapshot = []
    itemsWereRemoved = []
    newItems = []

    for key in currentFolderSnapshot.keys():
        itemsFromCurrentSnapshot.append(key)
        # get current list of paths of files/folders
        # in order to check it against previous list

    for key in previousSnapshot.keys():
        itemsFromPrevSnapshot.append(previousSnapshot[key])
        # get list of paths of files from previous folder snapshot

        if key not in itemsFromCurrentSnapshot:
            logFile.info(key + ' WAS REMOVED')
            itemsWereRemoved.append(key)

    for path in itemsFromCurrentSnapshot:
        if path not in itemsFromPrevSnapshot:
            logFile.info(path + ' IS NEW ITEM')
            newItems.append(path)

    print('\n' + pathToFolder)
    logFile.info('\n' + pathToFolder)
    print(str(len(itemsWereRemoved)) + ' items were removed')
    logFile.info(str(len(itemsWereRemoved)) + ' items were removed')

    print('There are ' + str(len(newItems)) + ' new items')
    logFile.info('There are ' + str(len(newItems)) + ' new items')
    print()
    logFile.info('\n')

    return itemsWereRemoved, currentFolderSnapshot

# def highComparison(firstFolder, secondFolder, rootFirstFolder, rootSecondFolder):

    # 1. Compare files that were not removed
    # Compare by modification time and size
    # 3. If size is equal, but mtime is different, check byte-by-byte

def lowSnapshotComparison(firstFolder, secondFolder, rootFirstFolder, rootSecondFolder, level):
    '''compare files in binary mode if folders haven't been synced before'''

    startTime = time.time()
    notExistInA = []
    notExistInB = []
    samePathAndName = []
    equalFiles = []
    toBeUpdatedFromBtoA = []
    toBeUpdatedFromAtoB = []
    removeFromA = []
    removeFromB = []
    totalSizeToTransfer = 0
    ''' in each list script adds two version of path to file: 
    first (key) with root folder, second (snapA[key][1][0]]) with full path.
    First is shorter and for logs, 
    second is full and for operations of copying etc
    Below it looks like samePathAndName.append([key, snapA[key][1][0]])
    '''

    pathsOfSnapA = []
    pathsOfSnapB = []

    if level == 'low':
        snapA = getSnapshot(firstFolder, rootFirstFolder)
        snapB = getSnapshot(secondFolder, rootSecondFolder)
    elif level == 'high':
        removedFrom1Folder, snapA = getChangesBetweenStatesOfFolders(firstFolder, rootFirstFolder)
        removedFrom2Folder, snapB = getChangesBetweenStatesOfFolders(secondFolder, rootSecondFolder)


    for key in snapB.keys():
        pathsOfSnapB.append(snapB[key][1][3])
        #create list of paths from second folder's snapshot
        #get rid of name of root folder in the path to compare only what is inside folders: get '\somefolder\somefile.ext' instead of 'rootfolder\somefolder\somefile.ext'


    print() # this print() is needed to make offset

    def checkAgeFiles():
        nonlocal totalSizeToTransfer

        if snapA[key][3] > snapB[correspondingFileInB][3]:
            #file in A newer than file in B -> add it to list to be copied from A to B
            toBeUpdatedFromAtoB.append([snapA[key][1][0], snapB[correspondingFileInB][1][0], snapA[key][2]])
            # add to list another list with full paths of both files
            totalSizeToTransfer += snapA[key][2]
        elif snapA[key][3] < snapB[correspondingFileInB][3]:
            #file in A older than file in B -> add it to list to be copied from B to A
            toBeUpdatedFromBtoA.append([snapB[correspondingFileInB][1][0], snapA[key][1][0], snapB[correspondingFileInB][2]])
            # add to list another list with full paths of both files
            totalSizeToTransfer += snapB[correspondingFileInB][2]

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
                if snapA[key][2] != snapB[correspondingFileInB][2]:
                    # if sizes of files are not equal, skip binary comparison
                    checkAgeFiles()
                else:
                    if snapA[key][2] > 1024**3:
                        print('It\'s gonna take some time, be patiet.')
                    with open(snapA[key][1][0], 'rb') as f1, open(snapB[correspondingFileInB][1][0], 'rb') as f2:
                        while True:
                            # byte-to-byte comparison with buffer
                            b1 = f1.read(8192)
                            b2 = f2.read(8192)
                            if b1 != b2:
                                checkAgeFiles()
                                break
                            if not b1:
                                equalFiles.append(snapA[key])
                                break

        else:
            if level == 'high':
                if snapA[key][1][3] in removedFrom2Folder:
                    removeFromA.append(snapA[key])
                    # if item was removed from B - add it to list of items
                    # which will be removed from A
                else:
                    print('Hello! Anybody home?')
            elif level == 'low':
                notExistInB.append(snapA[key])
                 # if file doesn't exist in B -> add it in list to be copied from A
                if [snapA[key][1]] == 'file':
                    totalSizeToTransfer += snapA[key][2]

    for key in snapB.keys():
        #check which files from B exist in A
        if not snapB[key][1][3] in pathsOfSnapA:
            if level == 'high':
                if snapB[key][1][3] in removedFrom1Folder:
                    removeFromB.append(snapB[key])
            elif level == 'low':
                notExistInA.append(snapB[key])
                if snapB[key][0] == 'file':
                    totalSizeToTransfer += snapB[key][2]

    ######### result messages to console and log file##########
    print('')
    print('###########################')
    print(firstFolder)
    logFile.info(firstFolder)
    print('###########################')

    print(str(len(samePathAndName)) + ' file(s) that exist in both folders.')
    logFile.info(str(len(samePathAndName)) +  ' file(s) that exist in both folders.')
    for path in samePathAndName:
        logFile.info(path[1][0])
    logFile.info('\n')

    print(str(len(equalFiles)) + ' file(s) don\'t need update.')
    logFile.info(str(len(equalFiles)) + ' file(s) don\'t need update.')
    for path in equalFiles:
        logFile.info(path[1][0])
    logFile.info('\n')

    print(str(len(notExistInB)) + ' items from  ' + firstFolder + ' don\'t exist in \'' + secondFolder + '\'')
    logFile.info(str(len(notExistInB)) + ' items from  ' + firstFolder + ' don\'t exist in \'' + secondFolder + '\'')
    for path in notExistInB:
        logFile.info(path[1][0])
    logFile.info('\n')

    print(str(len(notExistInA)) + ' item(s) from  ' + secondFolder + ' don\'t exist in \'' + firstFolder + '\'')
    logFile.info(str(len(notExistInA)) + ' item(s) from  ' + secondFolder + ' don\'t exist in \'' + firstFolder + '\'')
    for path in notExistInA:
        logFile.info(path[1][0])
    logFile.info('\n')

    print(str(len(toBeUpdatedFromAtoB)) + ' item(s) need to update in \'' + secondFolder + '\'')
    logFile.info(str(len(toBeUpdatedFromAtoB)) + ' item(s) need to update in \'' + secondFolder + '\'')
    for path in toBeUpdatedFromAtoB:
        logFile.info(path[1][0])
    logFile.info('\n')

    print(str(len(toBeUpdatedFromBtoA)) + ' item(s) need to update in \'' + firstFolder + '\'')
    logFile.info(str(len(toBeUpdatedFromBtoA)) + ' item(s) need to update in \'' + firstFolder + '\'')
    for path in toBeUpdatedFromBtoA:
        logFile.info(path[1][0])
    logFile.info('\n')

    if level == 'high':
        print(str(len(removedFrom1Folder)) + ' items were removed from \'' + firstFolder)
        logFile.info(str(len(removedFrom1Folder)) + ' items were removed from \'' + firstFolder + '\n')
        for path in removedFrom1Folder:
            logFile.info(path[1][0])
        logFile.info('\n')

        print(str(len(removedFrom2Folder)) + ' items were removed from \'' + secondFolder + '\n')
        logFile.info(str(len(removedFrom2Folder)) + ' items were removed from \'' + secondFolder + '\n')
        for path in removedFrom2Folder:
            logFile.info(path[1][0])
        logFile.info('\n')


    totalNumberToTransfer = len(notExistInA) + len(notExistInB) + len(toBeUpdatedFromAtoB) + len(toBeUpdatedFromBtoA)
    print('Total number items to transfer: ' + str(totalNumberToTransfer))
    logFile.info('Total number items to transfer: ' + str(totalNumberToTransfer) + '\n')

    print('Total size of files to transfer is ' + str("{0:.0f}".format(totalSizeToTransfer / 1024 / 1024)) + ' MB.')
    logFile.info('Total size of files to transfer is ' + str("{0:.0f}".format(totalSizeToTransfer / 1024 / 1024)) + ' MB.')

    print('--- {0:.3f} --- seconds\n'.format(time.time() - startTime))
    logFile.info('--- {0:.3f} --- seconds'.format(time.time() - startTime))
    # for path in pathsOfSnapB:
    # 	logFile.debug('ITEM IN B: ' + path)
    # for path in pathsOfSnapA:
    # 	logFile.debug('ITEM IN A: ' + path)

    return notExistInA, notExistInB, toBeUpdatedFromBtoA, toBeUpdatedFromAtoB

def syncFiles(compareResult, firstFolder, secondFolder):
    #take lists with files to copy and copy them

    startTime = time.time()
    notExistInA, notExistInB, toBeUpdatedFromBtoA, toBeUpdatedFromAtoB = compareResult

    wereCopied = 0
    totalSize = 0
    wereCreated = 0

    logFile.info('Start syncing files...')
    print('Start syncing files...')


    def copyNotExistItems(notExistItems, pathToRoot):
        '''Copy files that don't exist in one of folders'''

        nonlocal wereCopied
        nonlocal wereCreated
        nonlocal totalSize

        '''in order to use a variable from nearest outer scope'''

        for file in notExistItems:
            pathWithoutRoot = file[1][3] # path of file in b from without root folder and all the other previous folders
            fullPathItemInThisFolder = file[1][0] # full path of file in b
            fullPathItemThatNotExitsYet = os.path.join(pathToRoot, pathWithoutRoot) #path where copy item to
            if file[0] == 'folder':
                os.mkdir(fullPathItemThatNotExitsYet)
                #create empty folder instead of copying full directory
                wereCreated += 1
                print('- ' + fullPathItemThatNotExitsYet + ' was created.')
                logFile.info('- ' + fullPathItemThatNotExitsYet + ' was created.')


            elif file[0] == 'file':
                if os.path.exists(fullPathItemThatNotExitsYet):
                    #it shouldn't happened, but just in case
                    logConsole.warning('WARNING: ' + fullPathItemThatNotExitsYet + ' already exists!')
                    logFile.warning('WARNING: ' + fullPathItemThatNotExitsYet + ' already exists!')
                    continue
                else:
                    shutil.copy2(fullPathItemInThisFolder, fullPathItemThatNotExitsYet)
                    #copy file
                    wereCopied += 1
                    totalSize += file[2]
                    print('- ' + os.path.basename(fullPathItemThatNotExitsYet + ' was copied.'))
                    logFile.info('- ' + os.path.basename(fullPathItemThatNotExitsYet + ' was copied.'))

    def updateFiles(toBeUpdated):
        '''Update file by deleting old one and copying new one instead of it'''

        nonlocal totalSize

        for array in toBeUpdated:
            if os.path.exists(array[0]) and os.path.exists(array[1]):
                send2trash.send2trash(array[1])
                shutil.copy2(array[0], array[1])
                print('- ' + array[1] + ' was updated.')
                logFile.info('- ' + array[1] + ' was updated.')
                totalSize += array[2]
            elif not os.path.exists(array[0]):
                print(array[0] + ' hasn\'t been found! Can\'t handle it.')
                logFile.warning(array[0] + ' hasn\'t been found! Can\'t handle it.')
            elif not os.path.exists(array[1]):
                print(array[1] + ' hasn\'t been found! Can\'t handle it.')
                logFile.warning(array[1] + ' hasn\'t been found! Can\'t handle it.')


    if len(notExistInA) > 0:
        copyNotExistItems(notExistInA, firstFolder)

    if len(notExistInB) > 0:
        copyNotExistItems(notExistInB, secondFolder)

    if len(toBeUpdatedFromAtoB) > 0:
        updateFiles(toBeUpdatedFromAtoB)

    if len(toBeUpdatedFromBtoA) > 0:
        updateFiles(toBeUpdatedFromBtoA)

    print('\n' + str(wereCreated) + ' folders were created.')
    logFile.info('\n' + str(wereCreated) + ' folder were created.')

    print(str(wereCopied) + ' files were copied.')
    logFile.info(str(wereCopied) + ' files were copied.')

    print('Total size of files were copied or updated is {0:.2f} MB.'.format(totalSize / 1024 / 1024))
    logFile.info('Total size of files were copied or updated is {0:.2f} MB.'.format(totalSize / 1024 / 1024))

    print('--- {0:.3f} seconds ---\n'.format(time.time() - startTime))
    logFile.info('--- {0:.3f} seconds ---\n'.format(time.time() - startTime))
    # TODO make printing and logging how many files were copied and what is their total size

menu_choose_folders()

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

def menuBeforeSync():
    ''' Menu to ask user if he wants to start transfering files '''
    while True:
        startSyncing = input('Do you want to sync these files? y/n: ').lower()
        logFile.info('Do you want to sync these files? y/n: ')
        if startSyncing == 'y':
            if firstFolderSynced and secondFolderSynced:
                logConsole.debug('Call function that syncing folders that have already been synced')
                break
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

if firstFolderSynced:
    getChangesBetweenStatesOfFolders(firstFolder, rootFirstFolder)

if secondFolderSynced:
    getChangesBetweenStatesOfFolders(secondFolder, rootSecondFolder)

if firstFolderSynced and secondFolderSynced:
    compareResult = lowSnapshotComparison(firstFolder, secondFolder, rootFirstFolder, rootSecondFolder, 'high')
elif firstFolderSynced or secondFolderSynced:
    compareResult = lowSnapshotComparison(firstFolder, secondFolder, rootFirstFolder, rootSecondFolder, 'middle')
else:
    compareResult = lowSnapshotComparison(firstFolder, secondFolder, rootFirstFolder, rootSecondFolder, 'low')

    numberFilesToTransfer = len(compareResult[0] + compareResult[1] + compareResult[2] + compareResult[3])
    # check how many files script should transfer in total
    if numberFilesToTransfer > 0:
        # call sync function if there is something to sync
        menuBeforeSync()

def storeSnapshotBerofeExit(folderToTakeSnapshot, rootFolder, folderSynced):
    '''Store state of folder to be synced after it was synced on storage'''
    if folderSynced:
        shelFile = shelve.open(os.path.join(folderToTakeSnapshot, '.folderSyncSnapshot', 'snapshot'))
    else:
        os.mkdir(os.path.join(folderToTakeSnapshot, '.folderSyncSnapshot'))
        shelFile = shelve.open(os.path.join(folderToTakeSnapshot, '.folderSyncSnapshot', 'snapshot'))

    snapshot = getSnapshot(folderToTakeSnapshot, rootFolder)

    storeTime = time.strftime('%Y-%m-%d %Hh-%Mm')
    shelFile['path'] = folderToTakeSnapshot
    shelFile['snapshot'] = snapshot
    shelFile['date'] = storeTime

    print('Snapshot of ' + rootFolder + ' was stored in ' + folderToTakeSnapshot + ' at ' + storeTime)
    logFile.info('Snapshot of ' + rootFolder + ' was stored in ' + folderToTakeSnapshot + ' at ' + storeTime)

    shelFile.close()

storeSnapshotBerofeExit(firstFolder, rootFirstFolder, firstFolderSynced)
storeSnapshotBerofeExit(secondFolder, rootSecondFolder, secondFolderSynced)
# uncomment two lines above for testing without it / don't delete it 

print('Goodbye.')
logFile.info('Goodbye.')


########## crap ##############

# 	getattr(logFile, level)(message)
# 	#what is above means "logFile.level(message)" where level is method's name which is known only by runtime. For example "logFile.info(message)" where 'info' is coming from variable 


# def devLap():

# 	logConsole.debug('You are on dev laptop. Using default adressess for test.')
# 	logFile.debug('You are on dev laptop. Using default adressess for test.')

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
