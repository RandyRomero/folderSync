#! python3

# Program that can sync all files and folders between two chosen folders.
# I need it to keep my photo-backup updated.
# But script should be able to sync in both ways.
# And keep track of changes in both folders.'''

import logging
import math
import os
import re
import shutil
import send2trash
import shelve
import sys
import time
# import platform

firstFolder = ''
secondFolder = ''


def set_loggers():
    log_file = logging.getLogger('fs1')
    # create logger for this specific module for logging to file

    log_file.setLevel(logging.DEBUG)
    # set level of messages to be logged to file

    log_console = logging.getLogger('fs2')
    log_console.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(levelname)s %(asctime)s line %(lineno)s: %(message)s')
    # define format of logging messages

    timestr = time.strftime('%Y-%m-%d__%Hh%Mm')
    new_log_name = os.path.join('log', 'log_' + timestr + '.txt')

    if os.path.exists('.\log'):
        ''' create new log every time when script starts instead of writing in the same file '''

        if os.path.exists(new_log_name):
            i = 2
            while os.path.exists(os.path.join('log', 'log ' + timestr + '(' + str(i) + ').txt')):
                i += 1
                continue
            file_handler = logging.FileHandler(os.path.join('log', 'log ' + timestr + '(' +
                                                            str(i) + ').txt'), encoding='utf8')
        else:
            file_handler = logging.FileHandler(new_log_name, encoding='utf8')
    else:
        os.mkdir('.\log')
        file_handler = logging.FileHandler(new_log_name, encoding='utf8')

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    # set format to both handlers

    log_file.addHandler(file_handler)
    log_console.addHandler(stream_handler)
    # apply handler to this module (folderSync.py)

    return log_file, log_console

logFile, logConsole = set_loggers()


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


def has_it_ever_been_synced(path_to_root_folder):
    # check if there is already snapshot from previous sync
    if os.path.exists(os.path.join(path_to_root_folder, '.folderSyncSnapshot')):
        return True
    else:
        return False


def get_snapshot(path_to_root_folder, root_folder):
    # get all file and folder paths,
    # and collect file size and file time of modification

    start_time = time.time()

    logFile.info('\nGetting snapshot of ' + path_to_root_folder + '...')

    folders_number = 0
    files_number = 0
    total_size = 0

    current_snapshot = {}

    for root, folders, files in os.walk(path_to_root_folder):
        folders[:] = [x for x in folders if not x == '.folderSyncSnapshot']
        files = [x for x in files if not x.startswith('~$')]
        # only add to list folders that not '.folderSyncSnapshot'

        for folder in folders:

            full_path = os.path.join(root, folder)
            path_wout_root = full_path.split(path_to_root_folder + '\\')[1]
            # subtract path to root folder from full path whereby get path to folder/file without root folder
            path_with_root = os.path.join(root_folder, path_wout_root)

            all_paths = [full_path, root_folder, path_with_root, path_wout_root]
 
            current_snapshot[path_with_root] = ['folder', all_paths]
            folders_number += 1

        for file in files:
            full_path = os.path.join(root, file)
            path_wout_root = full_path.split(path_to_root_folder + '\\')[1]
            path_with_root = os.path.join(root_folder, path_wout_root)
            all_paths = [full_path, root_folder, path_with_root, path_wout_root]

            size_of_current_file = os.path.getsize(all_paths[0])
            total_size += size_of_current_file
            current_snapshot[path_with_root] = \
                ['file', all_paths, size_of_current_file, math.ceil(os.path.getmtime(all_paths[0]))]
            # math.ceil for rounding float because otherwise it is to precise for our purpose
            files_number += 1

    logFile.info('There are ' + str(folders_number) + ' folders and ' +
                 str(files_number) + ' files in ' + path_to_root_folder)
    logFile.info('Total size of ' + path_to_root_folder + ' is ' +
                 str("{0:.0f}".format(total_size / 1024 / 1024)) + ' MB.\n')
    logFile.info('--- {0:.3f} seconds ---\n'.format(time.time() - start_time))

    return current_snapshot


def get_changes_between_states_of_folders(path_to_folder, root_of_path):
    # Compare folder's snapshot that was stored in .folderSyncSnapshot
    # folder during last syncing with fresh snapshot that is going to be taken within this function.
    # It needs to figure out which files were removed in order not to acquire it from not yet updated folder again

    try:
        shel_file = shelve.open(os.path.join(path_to_folder, '.folderSyncSnapshot', 'snapshot'))
    except:
        print('Can\'t open stored snapshot. Exit.')
        sys.exit()

    current_folder_snapshot = get_snapshot(path_to_folder, root_of_path)
    # analyse current state of folder
    previous_snapshot = shel_file['snapshot']
    store_date = shel_file['date']
    # load previous state of folder from shelve db

    items_with_changed_mtime = []
    items_from_prev_snapshot = []
    items_from_current_snapshot = []
    items_were_removed = []
    new_items = []

    for key in current_folder_snapshot.keys():
        items_from_current_snapshot.append(key)
        # get current list of paths of files/folders
        # in order to check it against previous list

    for key in previous_snapshot.keys():
        items_from_prev_snapshot.append(key)
        # get list of paths of files from previous folder snapshot

        if key not in items_from_current_snapshot:
            # if item from previous snapshot not in current snapshot
            logFile.info(key + ' WAS REMOVED')
            items_were_removed.append(previous_snapshot[key][1][3])
            # add path without root folder to list because we should compare it later
            # against path with another root folder
        else:
            # check if mtime of file was changed
            if current_folder_snapshot[key][0] == 'file':
                if current_folder_snapshot[key][3] != previous_snapshot[key][3]:
                    items_with_changed_mtime.append(current_folder_snapshot[key][1][3])
                    logConsole.debug('Modification time of ' + current_folder_snapshot[key][1][0] + ' has changed.')
                    # check if it works
                    logFile.info('Modification time of ' + current_folder_snapshot[key][1][0] + ' has changed.')

    for path in items_from_current_snapshot:
        if path not in items_from_prev_snapshot:
            logFile.info(path + ' IS NEW ITEM')
            new_items.append(path)

    logFile.info('\n' + path_to_folder)
    logFile.info(str(len(items_were_removed)) + ' items were removed')
    logFile.info('There are ' + str(len(new_items)) + ' new items')
    logFile.info('\n')

    return items_were_removed, new_items, items_with_changed_mtime, current_folder_snapshot, store_date

# def highComparison(firstFolder, secondFolder, rootFirstFolder, rootSecondFolder):

    # 1. Compare files that were not removed
    # Compare by modification time and size
    # 3. If size is equal, but mtime is different, check byte-by-byte


def snapshot_comparison(first_folder, second_folder, root_first_folder, root_second_folder, level):
    # compare files in binary mode if folders haven't been synced before

    start_time = time.time()
    equal_files = []
    num_files_in_a = 0
    num_files_in_b = 0
    num_folders_in_a = 0
    num_folders_in_b = 0
    must_remove_from_a = []
    must_remove_from_b = []
    new_in_a = []
    new_in_b = []
    not_exist_in_a = []
    not_exist_in_b = []
    number_to_transfer_from_a_to_b = 0
    number_to_transfer_from_b_to_a = 0
    paths_of_snap_a = []
    paths_of_snap_b = []
    same_path_and_name = []
    size_from_a_to_b = 0
    size_from_b_to_a = 0
    size_of_items_in_a = 0
    size_of_items_in_b = 0
    size_to_remove_from_a = 0
    size_to_remove_from_b = 0
    skipped_files = []
    snap_a = {}
    snap_b = {}
    store_date_a = 0
    store_date_b = 0
    to_be_updated_from_a_to_b = []
    to_be_updated_from_b_to_a = []
    were_removed_from_a = []
    were_removed_from_b = []

    ''' in each list script adds two version of path to file: 
    first (key) with root folder, second (snap_a[key][1][0]]) with full path.
    First is shorter and for logs, 
    second is full and for operations of copying etc
    Below it looks like same_path_and_name.append([key, snap_a[key][1][0]])
    '''

    if level == 'low':
        snap_a = get_snapshot(first_folder, root_first_folder)
        snap_b = get_snapshot(second_folder, root_second_folder)
    elif level == 'high':
        were_removed_from_a, new_in_a, updated_items_a, snap_a, store_date_a = \
            get_changes_between_states_of_folders(first_folder, root_first_folder)
        were_removed_from_b, new_in_b, updated_items_b, snap_b, store_date_b = \
            get_changes_between_states_of_folders(second_folder, root_second_folder)

        both_updated = [item for item in updated_items_a if item in updated_items_b]
        # check if the same file were changed in both folder (which mean you can't
        # decide automatically which one to remove and which one to update)

    for key in snap_b.keys():
        paths_of_snap_b.append(snap_b[key][1][3])
        # create list of paths from second folder's snapshot
        # get rid of name of root folder in the path to compare only what is inside folders:
        # get '\somefolder\somefile.ext' instead of 'rootfolder\somefolder\somefile.ext'

    print()  # this print() is needed to make offset

    def check_age_files(file_from_a, file_from_b):
        nonlocal size_from_a_to_b
        nonlocal size_from_b_to_a
        nonlocal number_to_transfer_from_a_to_b
        nonlocal number_to_transfer_from_b_to_a
        nonlocal updated_items_a
        nonlocal updated_items_b
        nonlocal both_updated
        nonlocal skipped_files

        if level == 'high' and len(both_updated) > 0 and file_from_a[1][3] in both_updated:
            # do not update file if it has been updated in both folders since last time
            print(file_from_a[1][3] + ' has changed in both folders, so you need to choose right version manually. '
                                      'Program will not manage it.')
            logFile.warning(file_from_a[1][3] + ' has changed in both folders, so you need to choose right version '
                                                'manually. Program will not manage it.')
            skipped_files.append(file_from_a[1][3])

        else:
            if file_from_a[3] > file_from_b[3]:
                # file in A newer than file in B -> add it to list to be copied from A to B
                to_be_updated_from_a_to_b.append([file_from_a[1][0], file_from_b[1][0], file_from_a[2]])
                # add to list another list with full paths of both files
                number_to_transfer_from_a_to_b += 1
                size_from_a_to_b += file_from_a[2]
            elif file_from_a[3] < file_from_b[3]:
                # file in A older than file in B -> add it to list to be copied from B to A
                to_be_updated_from_b_to_a.append([file_from_b[1][0], file_from_a[1][0], file_from_b[2]])
                # add to list another list with full paths of both files
                number_to_transfer_from_b_to_a += 1
                size_from_b_to_a += file_from_b[2]

    # check A against B
    for key in snap_a.keys():
        paths_of_snap_a.append(snap_a[key][1][3])
        # --//--

        if snap_a[key][1][3] in paths_of_snap_b:
            # if item with same path exists in both folders to be synced

            if snap_a[key][0] == 'file':
                # if item is file - compare them
                num_files_in_a += 1
                size_of_items_in_a += snap_a[key][2]
                # count files in the first folder
                same_path_and_name.append(snap_a[key])
                corresponding_file_in_b = os.path.join(root_second_folder, snap_a[key][1][3])
                # merge root of second folder with path of file/folder from first folder
                # to get a probability compare files

                print('Comparing files... ' + snap_a[key][1][3])
                if snap_a[key][2] != snap_b[corresponding_file_in_b][2]:
                    # if sizes of files are not equal, skip binary comparison
                    check_age_files(snap_a[key], snap_b[corresponding_file_in_b])
                    # check which file is newer
                else:
                    if snap_a[key][2] > 1024**3:
                        print('It\'s gonna take some time, be patient.')
                    with open(snap_a[key][1][0], 'rb') as f1, open(snap_b[corresponding_file_in_b][1][0], 'rb') as f2:
                        while True:
                            # byte-to-byte comparison with buffer
                            b1 = f1.read(8192)
                            b2 = f2.read(8192)
                            if b1 != b2:
                                check_age_files(snap_a[key], snap_b[corresponding_file_in_b])
                                # if files are not the same - check which one is newer
                                break
                            if not b1:
                                # if no difference found till the end of files
                                # add file to list of equal files
                                equal_files.append(snap_a[key])
                                break
            else:
                num_folders_in_a += 1
                # count folders in the first folder

        else:
            # if file in first folder has not been found in the second folder
            if level == 'high' and snap_a[key][1][3] in were_removed_from_b:
                must_remove_from_a.append(snap_a[key])
                if snap_a[key][0] == 'file':
                    size_to_remove_from_a += snap_a[key][2]
                # if item was removed from B - add it to list of items
                # which will be removed from A
                continue
            else:
                not_exist_in_b.append(snap_a[key])
                # if file doesn't exist in B -> add it in list to be copied from A
                number_to_transfer_from_a_to_b += 1
                if snap_a[key][0] == 'file':
                    size_from_a_to_b += snap_a[key][2]

    for key in snap_b.keys():
        # check which files from B exist in A
        if snap_b[key][0] == 'file':
            # count number of files in the first folder
            num_files_in_b += 1
            size_of_items_in_b += snap_b[key][2]
        else:
            # count number of folder in the second folder
            num_folders_in_b += 1

        if not snap_b[key][1][3] in paths_of_snap_a:
            if level == 'high' and snap_b[key][1][3] in were_removed_from_a:
                # if item was removed from A - add it to list of items
                # which will be removed from B
                must_remove_from_b.append(snap_b[key])
                if snap_b[key][0] == 'file':
                    size_to_remove_from_b += snap_b[key][2]
            else:
                not_exist_in_a.append(snap_b[key])
                # if file doesn't exists in A -> add it in list to be copied from B
                number_to_transfer_from_b_to_a += 1
                if snap_b[key][0] == 'file':
                    size_from_b_to_a += snap_b[key][2]

    if len(not_exist_in_b) != len(new_in_a):
        # should not happened but just in case
        print('Warning! Number of new files in ' + first_folder + ' does not match number of absent items in ' +
              second_folder)
        logFile.warning('Warning! Number of new files in ' + first_folder +
                        ' does not match number of absent items in ' + second_folder)

    if len(not_exist_in_a) != len(new_in_b):
        # should not happened but just in case
        print('Warning! Number of new items in ' + second_folder + ' does not match number of absent items in ' +
              first_folder)
        logFile.warning('Warning! Number of new items in ' + second_folder +
                        ' does not match number of absent items in ' + first_folder)

    '''result messages to console and log file'''

    print('')
    print('###########################')
    print('There are ' + str(num_folders_in_a) + ' folders and ' + str(num_files_in_a) + ' files in ' + first_folder +
          ' with total size of ' + str("{0:.0f}".format(size_of_items_in_a / 1024**2)) + ' MB.')
    logFile.info('There are ' + str(num_folders_in_a) + ' folders and ' + str(num_files_in_a) + ' files in ' +
                 first_folder + ' with total size of ' +
                 str("{0:.0f}".format(size_of_items_in_a / 1024 ** 2)) + ' MB.')

    print('There are ' + str(num_folders_in_b) + ' folders and ' + str(num_files_in_b) + ' files in ' + second_folder +
          ' with total size of ' + str("{0:.0f}".format(size_of_items_in_b / 1024 ** 2)) + ' MB.')
    logFile.info('There are ' + str(num_folders_in_b) + ' folders and ' + str(num_files_in_b) + ' files in ' +
                 second_folder + ' with total size of ' +
                 str("{0:.0f}".format(size_of_items_in_b / 1024 ** 2)) + ' MB.')

    print(str(len(same_path_and_name)) + ' file(s) that are common for both folders.')
    logFile.info(str(len(same_path_and_name)) + ' file(s) that are common for both folders.')
    for path in same_path_and_name:
        logFile.info(path[1][0])
    logFile.info('\n')

    print(str(len(equal_files)) + ' file(s) are equal.')
    logFile.info(str(len(equal_files)) + ' file(s) are equal.')
    for path in equal_files:
        logFile.info(path[1][0])
    logFile.info('\n')

    if len(to_be_updated_from_a_to_b) > 0:
        print(str(len(to_be_updated_from_a_to_b)) + ' item(s) has newer version in \'' + first_folder + '\'')
        logFile.info(str(len(to_be_updated_from_a_to_b)) + ' item(s) has newer version in \'' + first_folder + '\'')
        for path in to_be_updated_from_a_to_b:
            logFile.info(path[1][0])
        logFile.info('\n')

    if len(to_be_updated_from_b_to_a) > 0:
        print(str(len(to_be_updated_from_b_to_a)) + ' item(s) has newer version in ' + second_folder + '\'')
        logFile.info(str(len(to_be_updated_from_b_to_a)) + ' item(s) has newer version in ' + second_folder + '\'')
        for path in to_be_updated_from_b_to_a:
            logFile.info(path[1][0])
        logFile.info('\n')

    if level == 'low':
        if len(not_exist_in_b) > 0:
            print(str(len(not_exist_in_b)) + ' item(s) from  ' + first_folder + ' don\'t exist in \'' +
                  second_folder + '\'')
            logFile.info(str(len(not_exist_in_b)) + ' item(s) from  ' + first_folder +
                         ' don\'t exist in \'' + second_folder + '\'')
            for path in not_exist_in_b:
                logFile.info(path[1][0])
            logFile.info('\n')

        if len(not_exist_in_a) > 0:
            print(str(len(not_exist_in_a)) + ' item(s) from  ' + second_folder + ' don\'t exist in \'' +
                  first_folder + '\'')
            logFile.info(str(len(not_exist_in_a)) + ' item(s) from  ' +
                         second_folder + ' don\'t exist in \'' + first_folder + '\'')
            for path in not_exist_in_a:
                logFile.info(path[1][0])
            logFile.info('\n')

    if level == 'high':
        if len(were_removed_from_a) > 0:
            print(str(len(were_removed_from_a)) + ' item(s) have been removed from \'' + first_folder + ' since ' +
                  store_date_a + '.')
            logFile.info(str(len(were_removed_from_a)) + ' item(s) have been removed from \'' + first_folder +
                         ' since ' + store_date_a + '.')
            for item in were_removed_from_a:
                logFile.info(item)
            logFile.info('\n')

        if len(were_removed_from_b) > 0:
            print(str(len(were_removed_from_b)) + ' item(s) have been removed from \'' + second_folder + ' since ' +
                  store_date_b + '.')
            logFile.info(str(len(were_removed_from_b)) + ' item(s) have been removed from \'' + second_folder +
                         ' since ' + store_date_b + '.')
            for item in were_removed_from_b:
                logFile.info(item)
            logFile.info('\n')

        if len(not_exist_in_b) > 0:
            print(str(len(not_exist_in_b)) + ' new item(s) in ' + first_folder)
            logFile.info(str(len(not_exist_in_b)) + ' new item(s) in ' + first_folder + '\n')
            for item in not_exist_in_b:
                logFile.info(item)
            logFile.info('\n')

        if len(not_exist_in_a) > 0:
            print(str(len(not_exist_in_a)) + ' new item(s) in ' + second_folder)
            logFile.info(str(len(not_exist_in_a)) + ' new item(s) in ' + second_folder)
            for item in not_exist_in_a:
                logFile.info(item)
            logFile.info('\n')

        if len(skipped_files) > 0:
            print('There are ' + str(len(skipped_files)) + ' items that you should check manually.')
            logFile.info('There are ' + str(len(skipped_files)) + ' items that you should check manually\n.')
            if len(skipped_files) > 0:
                print('These are: ')
                logFile.warning('These are: ')
                for file in skipped_files:
                    print('- ' + file)
                    logFile.warning('- ' + file)

    if number_to_transfer_from_a_to_b > 0:
        print('Number of item(s) to transfer from ' + first_folder + ' to ' + second_folder + ' is ' +
              str(number_to_transfer_from_a_to_b) + '.')
        logFile.info('Number of item(s) to transfer from ' + first_folder + ' to ' + second_folder + ' is ' +
                     str(number_to_transfer_from_a_to_b) + '.\n')

        print('Total size of file(s) to transfer from ' + first_folder + '  to ' + second_folder + ' is ' +
              str("{0:.0f}".format(size_from_a_to_b / 1024 / 1024)) + ' MB.')
        logFile.info('Total size of file(s) to transfer from ' + first_folder + '  to ' + second_folder + ' is ' +
                     str("{0:.0f}".format(size_from_a_to_b / 1024 / 1024)) + ' MB.')

    if number_to_transfer_from_b_to_a > 0:
        print('Number item(s) to transfer from ' + second_folder + ' to ' + first_folder + ' is ' +
              str(number_to_transfer_from_b_to_a) + '.')
        logFile.info('Number item(s) to transfer from ' + second_folder + ' to ' + first_folder + ' is ' +
                     str(number_to_transfer_from_b_to_a) + '.\n')

        print('Total size of file(s) to transfer from ' + second_folder + '  to ' + first_folder + ' is ' +
              str("{0:.0f}".format(size_from_b_to_a / 1024 / 1024)) + ' MB.')
        logFile.info('Total size of file(s) to transfer from ' + second_folder + '  to ' + first_folder + ' is ' +
                     str("{0:.0f}".format(size_from_b_to_a / 1024 / 1024)) + ' MB.')

    if level == 'high':
        if len(must_remove_from_a) > 0:
            print('\nNumber of item(s) to remove from ' + first_folder + ' is ' + str(len(must_remove_from_a)) + '.')
            logFile.info('\nTotal size of item(s) to remove from ' + first_folder + ' is ' +
                         str(len(must_remove_from_a)) + '.')
            print('Size of item(s) to remove from ' + first_folder + ' is ' +
                  str("{0:.0f}".format(size_to_remove_from_a / 1024 ** 2)) + ' MB.')
            logFile.info('Size of item(s) to remove from ' + first_folder + ' is ' +
                         str("{0:.0f}".format(size_to_remove_from_a / 1024 ** 2)) + ' MB.')

        if len(must_remove_from_b) > 0:
            print('Number of item(s) to remove from ' + second_folder + ' is ' + str(len(must_remove_from_b)) + '.')
            logFile.info('Total size of item(s) to remove from ' + second_folder + ' is ' +
                         str(len(must_remove_from_b)) + '.')

            print('Size of item(s) to remove from ' + second_folder + ' is ' +
                  str("{0:.0f}".format(size_to_remove_from_b / 1024 ** 2)) + ' MB.')
            logFile.info('Size of item(s) to remove from ' + second_folder + ' is ' +
                         str("{0:.0f}".format(size_to_remove_from_b / 1024 ** 2)) + ' MB.')

    print('--- {0:.3f} --- seconds\n'.format(time.time() - start_time))
    logFile.info('--- {0:.3f} --- seconds'.format(time.time() - start_time))

    result = [not_exist_in_a, not_exist_in_b, to_be_updated_from_b_to_a, to_be_updated_from_a_to_b, must_remove_from_a,
              must_remove_from_b, level]

    number_files_to_transfer = 0
    for index in range(len(result) - 1):
        number_files_to_transfer += len(result[index])
    # count how many files script should transfer in total

    result.append(number_files_to_transfer)
    return result


def store_snapshot_before_exit(folder_to_take_snapshot, root_folder, folder_synced):

    # Store state of folder to be synced after it was synced on storage
    if folder_synced:
        shel_file = shelve.open(os.path.join(folder_to_take_snapshot, '.folderSyncSnapshot', 'snapshot'))
    else:
        os.mkdir(os.path.join(folder_to_take_snapshot, '.folderSyncSnapshot'))
        shel_file = shelve.open(os.path.join(folder_to_take_snapshot, '.folderSyncSnapshot', 'snapshot'))

    snapshot = get_snapshot(folder_to_take_snapshot, root_folder)

    store_time = time.strftime('%Y-%m-%d %Hh-%Mm')
    shel_file['path'] = folder_to_take_snapshot
    shel_file['snapshot'] = snapshot
    shel_file['date'] = store_time

    # print('Snapshot of ' + root_folder + ' was stored in ' + folder_to_take_snapshot + ' at ' + store_time)
    logFile.info('Snapshot of ' + root_folder + ' was stored in ' + folder_to_take_snapshot + ' at ' + store_time)

    shel_file.close()


def sync_files(compare_result, first_folder, second_folder):
    # take lists with files to copy and copy them

    start_time = time.time()
    not_exist_in_a, not_exist_in_b, to_be_updated_from_b_to_a, to_be_updated_from_a_to_b, \
        remove_from_a, remove_from_b, level, number_files_to_handle = compare_result

    total_size_copied_updated = 0
    total_size_removed = 0
    were_copied = 0
    were_created = 0
    were_updated = 0
    were_removed = 0

    logFile.info('Start syncing files...')
    print('Start syncing files...')

    def delete(file_to_delete):
        # Function that tries to remove one specific file and return true if it was removed.
        # Used in remove_items() and update_files().

        user_decision = ''
        while user_decision != 'n':
            try:
                send2trash.send2trash(file_to_delete)
            except OSError:
                print(file_to_delete + ' have been opened in another app. Close all apps that can use this file and '
                                       'start sync over.')
                logFile.warning(file_to_delete + ' have been opened in another app. Close all apps that can use '
                                                 'this file and start sync over.')
                user_decision = input('Try again? y/n: ').lower()
                if user_decision == 'n':
                    return False
                elif user_decision == 'y':
                    print('Trying one more time...')
                    logFile.info('Trying one more time...')
                    continue
                else:
                    print('You should type in "y" or "n". Try again.')
                    logFile.info('You should type in "y" or "n". Try again.')
                    continue
            return True

    def remove_items(items_to_remove):
        # function that recursively removes files from list

        nonlocal were_removed
        nonlocal total_size_removed
        remove_state = True

        print('Removing files...')
        logFile.info('Removing files...')

        for item in range(len(items_to_remove)):
            full_path = items_to_remove[item][1][0]
            if os.path.exists(full_path):
                if delete(full_path):
                    print(full_path + ' was removed.')
                    logFile.info(full_path + ' was removed.')
                    were_removed += 1
                else:
                    print(full_path + ' was not removed.')
                    logFile.warning(full_path + ' was not removed.')
                    # TODO handle files that were not removed somehow to prevent script to think that
                    # it is a new one while next sync
                    remove_state = False
                    continue
            else:
                # item was removed with its folder before
                were_removed += 1

            if items_to_remove[item][0] == 'file' and remove_state:
                # count size of removed files
                total_size_removed += items_to_remove[item][2]

    def copy_items(not_exist_items, path_to_root):
        # Copy files that don't exist in one of folders

        nonlocal were_copied
        nonlocal were_created
        nonlocal total_size_copied_updated
        # in order to use a variable from nearest outer scope

        for file in not_exist_items:
            path_without_root = file[1][3]
            # path of file in b from without root folder and all the other previous folders
            full_path_item_in_this_folder = file[1][0]  # full path of file in b
            full_path_item_that_not_exits_yet = os.path.join(path_to_root, path_without_root)  # path where copy item to
            if file[0] == 'folder':
                os.mkdir(full_path_item_that_not_exits_yet)
                # create empty folder instead of copying full directory
                were_created += 1
                print('- ' + full_path_item_that_not_exits_yet + ' was created.')
                logFile.info('- ' + full_path_item_that_not_exits_yet + ' was created.')

            elif file[0] == 'file':
                if os.path.exists(full_path_item_that_not_exits_yet):
                    # it shouldn't happened, but just in case
                    logConsole.warning('WARNING: ' + full_path_item_that_not_exits_yet + ' already exists!')
                    logFile.warning('WARNING: ' + full_path_item_that_not_exits_yet + ' already exists!')
                    continue
                else:
                    shutil.copy2(full_path_item_in_this_folder, full_path_item_that_not_exits_yet)
                    # copy file
                    were_copied += 1
                    total_size_copied_updated += file[2]
                    print('- ' + os.path.basename(full_path_item_that_not_exits_yet + ' was copied.'))
                    logFile.info('- ' + os.path.basename(full_path_item_that_not_exits_yet + ' was copied.'))

    def update_files(to_be_updated):
        # recursively update files by deleting old one and copying new one instead of it

        nonlocal total_size_copied_updated
        nonlocal were_updated

        for array in to_be_updated:
            # array contains list with two items: full path of item to be copied and full path of file to be copied
            if os.path.exists(array[0]) and os.path.exists(array[1]):
                if delete(array[1]):
                    shutil.copy2(array[0], array[1])
                    print('- ' + array[1] + ' was updated.')
                    logFile.info('- ' + array[1] + ' was updated.')
                    total_size_copied_updated += array[2]
                    were_updated += 1
                else:
                    print(array[1] + ' was not removed.')
                    logFile.warning(array[1] + ' was not removed.')
                    # TODO handle files that were not removed somehow to prevent script to think that
                    # it is a new one while next sync
                    continue

            elif not os.path.exists(array[0]):
                print(array[0] + ' hasn\'t been found! Can\'t handle it.')
                logFile.warning(array[0] + ' hasn\'t been found! Can\'t handle it.')
            elif not os.path.exists(array[1]):
                print(array[1] + ' hasn\'t been found! Can\'t handle it.')
                logFile.warning(array[1] + ' hasn\'t been found! Can\'t handle it.')

    if len(to_be_updated_from_a_to_b) > 0:
        update_files(to_be_updated_from_a_to_b)

    if len(to_be_updated_from_b_to_a) > 0:
        update_files(to_be_updated_from_b_to_a)

    if len(not_exist_in_a) > 0:
        copy_items(not_exist_in_a, first_folder)

    if len(not_exist_in_b) > 0:
        copy_items(not_exist_in_b, second_folder)

    if level == 'high':
        if len(remove_from_a) > 0:
            remove_items(remove_from_a)

        if len(remove_from_b) > 0:
            remove_items(remove_from_b)

    if were_created > 0:
        print('\n' + str(were_created) + ' folders were created.')
        logFile.info('\n' + str(were_created) + ' folder were created.')

    if were_copied > 0:
        print(str(were_copied) + ' file(s) were copied.')
        logFile.info(str(were_copied) + ' files were copied.')

    if were_updated > 0:
        print(str(were_updated) + ' file(s) were updated.')
        logFile.info(str(were_updated) + ' files were updated.')

    if were_removed > 0:
        print(str(were_removed) + ' file(s) were removed.')
        logFile.info(str(were_removed) + ' file(s) were removed.')

    if total_size_copied_updated > 0:
        print('Total size of files were copied or updated is {0:.2f} MB.'.format(total_size_copied_updated / 1024**2))
        logFile.info('Total size of files were copied or updated is {0:.2f} MB.'
                     .format(total_size_copied_updated / 1024**2))

    if total_size_removed > 0:
        print('Total size of files were removed in {0:.2f} MB'.format(total_size_removed / 1024**2))
        logFile.info('Total size of files were removed in {0:.2f} MB'.format(total_size_removed / 1024**2))

    print('--- {0:.3f} seconds ---\n'.format(time.time() - start_time))
    logFile.info('--- {0:.3f} seconds ---\n'.format(time.time() - start_time))

    store_snapshot_before_exit(firstFolder, rootFirstFolder, firstFolderSynced)
    store_snapshot_before_exit(secondFolder, rootSecondFolder, secondFolderSynced)
    # uncomment two lines above for testing without it / don't delete it

menu_choose_folders()

firstFolderSynced = has_it_ever_been_synced(firstFolder)
logFile.debug(firstFolder + ' Has been synced before? ' + str(firstFolderSynced))
logConsole.debug(firstFolder + ' Has been synced before? ' + str(firstFolderSynced))

secondFolderSynced = has_it_ever_been_synced(secondFolder)
logFile.debug(secondFolder + ' Has been synced before? ' + str(secondFolderSynced))
logConsole.debug(secondFolder + ' Has been synced before? ' + str(secondFolderSynced))

rootFirstFolder = re.search(r'(\w+$)', firstFolder).group(0)
rootSecondFolder = re.search(r'(\w+$)', secondFolder).group(0)
# get names of root folders to be compared
# snapshotFirstFolder = getSnapshot(firstFolder, rootFirstFolder)
# snapshotSecondFolder = getSnapshot(secondFolder, rootSecondFolder)
# get all paths of all files and folders with properties from folders to be compared


def menu_before_sync():
    # Menu to ask user if he wants to start transfering files
    while True:
        start_syncing = input('Do you want to sync these files? y/n: ').lower()
        logFile.info('Do you want to sync these files? y/n: ')
        if start_syncing == 'y':
            sync_files(compareResult, firstFolder, secondFolder)
            break
        elif start_syncing == 'n':
            # continue without copy/remove files
            break
        else:
            print('Error of input. Try again.')
            logFile.info('Error of input. Try again.')
            continue

if firstFolderSynced and secondFolderSynced:
    compareResult = snapshot_comparison(firstFolder, secondFolder, rootFirstFolder, rootSecondFolder, 'high')
    if compareResult[7] > 0:
        # call sync function if there is something to sync
        menu_before_sync()
    else:
        print('There is nothing to copy or remove.')
        logFile.info('There is nothing to copy or remove.')

elif firstFolderSynced or secondFolderSynced:
    print('Ooops')
    # compareResult = snapshot_comparison(firstFolder, secondFolder, rootFirstFolder, rootSecondFolder, 'middle')
else:
    compareResult = snapshot_comparison(firstFolder, secondFolder, rootFirstFolder, rootSecondFolder, 'low')

    if compareResult[7] > 0:
        # call sync function if there is something to sync
        menu_before_sync()
    else:
        store_snapshot_before_exit(firstFolder, rootFirstFolder, firstFolderSynced)
        store_snapshot_before_exit(secondFolder, rootSecondFolder, secondFolderSynced)
        # store snapshots of folders if they have been synced but no differences have been found


print('Goodbye.')
logFile.info('Goodbye.')


''' crap '''

# getattr(logFile, level)(message)
# what is above means "logFile.level(message)" where level is method's name which is
# known only by runtime. For example "logFile.info(message)" where 'info' is coming from variable


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
