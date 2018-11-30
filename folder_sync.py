# -*- coding: utf-8 -*-

# folder_sync is a program that can sync all files and folders between two chosen folders.
# Purpose of that script is to make exact duplicates of two folders.
# For example, you can back up and update your backups with this script.
# During first sync script assumes all files that do not exist in one folder are new for the
# second folder and vice versa.
# During second and other syncs script can delete files from folder if they were deleted in the other one.
# It can also detect and manage updated files.
# For file comparison it uses timestamps, size of file and binary comparison - it depends on a situation.
# Script also write logs to .\log folder and clear the oldest ones, when size of logs folder is more than 20 Mb.

# Written by Aleksandr Mikheev
# https://github.com/RandyRomero/folderSync

import math
import os
import shutil
import send2trash
import shelve
import sys
import time
import handle_logs
import traceback

# files that were not removed last time
remove_from_a_next_time = []
remove_from_b_next_time = []

# set up logging via my module
log_file, log_console = handle_logs.set_loggers()


def choose_folder():  # used to check validity of file's path given by user

    while True:
        path_to_folder = input('Path: ')
        if not os.path.exists(path_to_folder):
            print('This folder doesn\'t exist. Write another one.')
            log_file.info('This folder doesn\'t exist. Write another one.')
            continue
        if not os.path.isdir(path_to_folder):
            print('You should denote path to folder, not to file. Try again.')
            log_file.info('You should denote path to folder, not to file. Try again.')
            continue
        elif os.path.exists(path_to_folder) and os.path.isdir(path_to_folder):
            print('Got it!')
            log_file.info('Got it!')
            return path_to_folder


def menu_choose_folders():  # let a user choose folders and assure they do not have the same path

    while True:
        print('Please, choose first folder to sync.')
        log_file.info('Please, choose first folder to sync.')
        first_folder = choose_folder()

        print('Please, choose second folder to sync.')
        log_file.info('Please, choose second folder to sync.')
        second_folder = choose_folder()

        if first_folder == second_folder:
            print('\nPaths can\'t be equal. Start over')
            log_file.info('\nPaths can\'t be equal. Start over')
            continue
        else:
            print('\nPaths accepted. Start analyzing...\n')
            log_file.info('\nPaths accepted. Start analyzing...\n')
            break

    return first_folder, second_folder


def get_snapshot(path_to_root_folder, root_folder):
    # Get all paths of every file and folder,
    # and collect file size and file time of modification.
    # Returns all paths with information as a single snapshot-dictionary.

    start_time = time.time()

    log_file.info('Getting snapshot of %s...', path_to_root_folder)

    folders_number = 0  # total number of all folders in given folder
    files_number = 0  # total number of files in given folder
    total_size = 0  # total size of all files in given folder

    current_snapshot = {}  # dictionary for all paths to files and folders

    # subtract path to root folder from full path in order to get path to folder/file without root folder
    # this is necessary to compare files from different folders
    def get_path_without_root_folder(entire_path, path_to_root):
        if 'win' in sys.platform.lower():
            return entire_path.split(path_to_root + '\\')[1]
        else:
            return entire_path.split(path_to_root + '/')[1]

    for root, folders, files in os.walk(path_to_root_folder):  # recursively get paths of all files and folders
        # only add to list folders that not '.folderSyncSnapshot' and files that don't start with '~$'
        folders[:] = [x for x in folders if not x == '.folderSyncSnapshot']
        files = [x for x in files if not x.startswith('~$')]

        for folder in folders:
            full_path = os.path.join(root, folder)
            path_wout_root = get_path_without_root_folder(full_path, path_to_root_folder)
            path_with_root = os.path.join(root_folder, path_wout_root)
            all_paths = [full_path, root_folder, path_with_root, path_wout_root]
            current_snapshot[path_with_root] = ['folder', all_paths]
            folders_number += 1

        for file in files:
            full_path = os.path.join(root, file)
            path_wout_root = get_path_without_root_folder(full_path, path_to_root_folder)
            path_with_root = os.path.join(root_folder, path_wout_root)
            all_paths = [full_path, root_folder, path_with_root, path_wout_root]

            size_of_current_file = os.path.getsize(all_paths[0])
            total_size += size_of_current_file
            current_snapshot[path_with_root] = ['file', all_paths, size_of_current_file,
                                                math.ceil(os.path.getmtime(all_paths[0]))]
            # math.ceil for rounding float because otherwise it is to precise for our purpose
            files_number += 1

    log_file.info("There are %d folders and %d files in '%s'.", folders_number, files_number, path_to_root_folder)
    log_file.info("Total size of %s is %.2f MB.", path_to_root_folder, total_size / 1024 ** 2)
    log_file.info('--- %.3f seconds ---\n', time.time() - start_time)

    return current_snapshot


def get_changes_between_folder_states(path_to_folder, root_of_path):
    # Compare folder's snapshot that was stored in .folderSyncSnapshot
    # folder during last syncing with fresh snapshot that is going to be taken within this function.
    # This is necessary to figure out which files were removed in order not to
    # acquire it from not yet updated folder again.

    try:
        shel_file = shelve.open(os.path.join(path_to_folder, '.folderSyncSnapshot', 'snapshot'))
    except:
        print("Can't open stored snapshot. Exit.")
        log_file.error(traceback.format_exc())
        return -1

    current_folder_snapshot = get_snapshot(path_to_folder, root_of_path)  # make currant snapshot of the given folder
    try:
        previous_snapshot = shel_file['snapshot']  # load previous snapshot
    except KeyError:
        message = ('Error: Unfortunately, database with previous state of folder is corrupted.\n' 
                   'Program will assume that folder has never been synchronized before.')
        print(message)
        log_file.error(message)
        log_file.error(traceback.format_exc())
        return -1

    store_date = shel_file['date']  # load date when previous snapshot has been done

    if shel_file['to_remove_from_a'][0] == root_of_path:
        # Figure out which list of files that were not removed last time
        # program should load this time due to folder name.
        were_not_removed_last_time = shel_file['to_remove_from_a']
    else:
        if shel_file['to_remove_from_b'][0] == root_of_path:
            were_not_removed_last_time = shel_file['to_remove_from_b']
        else:
            log_console.error('ERROR: Can not load list of files that program could not remove last time.')
            log_file.error('ERROR: Can not load list of files that program could not remove last time')
            sys.exit()

    items_with_changed_mtime = []  # List of files that have been modified since last sync.
    items_from_prev_snapshot = []
    items_from_current_snapshot = []
    items_were_removed = []  # files and folders that were removed since last sync
    new_items = []  # files and folder that were added since last sync

    if len(were_not_removed_last_time) > 1:
        message = 'There are {} file(s) that were not removed last time'.format(len(were_not_removed_last_time) - 1)
        print(message)
        log_file.info(message)

        # add files that were not removed last time to the list of files that were removed since last sync in order
        # to remove them this time
        for i in range(1, len(were_not_removed_last_time)):
            items_were_removed.append(were_not_removed_last_time[i][1][3])

    # make a list of paths of current files/folders in order to check them against previous list
    for key in current_folder_snapshot.keys():
        items_from_current_snapshot.append(key)

    for key in previous_snapshot.keys():  # get list of paths of files from previous folder snapshot
        items_from_prev_snapshot.append(key)

        # if item from previous snapshot not in current snapshot
        if key not in items_from_current_snapshot:
            log_file.info('%s WAS REMOVED', key)
            # add path without root folder to list because we should compare them later
            # against path with another root folder
            items_were_removed.append(previous_snapshot[key][1][3])
        else:
            # check whether file has been modified since last time or not
            if current_folder_snapshot[key][0] == 'file':
                if current_folder_snapshot[key][3] != previous_snapshot[key][3]:
                    items_with_changed_mtime.append(current_folder_snapshot[key][1][3])
                    log_file.info('Modification time of %s has changed.', current_folder_snapshot[key][1][0])

    # check whether some new files have been added since last time
    for path in items_from_current_snapshot:
        if path not in items_from_prev_snapshot and path not in items_were_removed:
            log_file.info('%s IS NEW ITEM', path)
            new_items.append(path)

    log_file.info('\n%s', path_to_folder)
    log_file.info('%d items were removed', len(items_were_removed))
    log_file.info('There are %d new items', len(new_items))
    log_file.info('\n')

    return items_were_removed, new_items, items_with_changed_mtime, current_folder_snapshot, store_date


def compare_snapshot(first_folder, second_folder, root_first_folder, root_second_folder, both_synced,
                     first_folder_synced, second_folder_synced):

    start_time = time.time()  # to measure how long it's gonna take to compare snapshots
    equal_files = []  # Files from both folders to compare that are exact duplicate
    num_files_in_a = 0  # List of files of folder that user chose first
    num_files_in_b = 0  # List of files of folder that user chose second
    num_folders_in_a = 0  # Number of folders in the 1st folder
    num_folders_in_b = 0  # Number of folder in the 2nd folder
    must_remove_from_a = []  # Items to remove from 1st folder
    must_remove_from_b = []  # Items to remove from 2nd folder
    not_exist_in_a = []  # File that exist in 2nd folder but do not exist in 1st folder
    not_exist_in_b = []  # Vice versa
    paths_of_snap_a = []  # List of paths of items from 1st folder
    paths_of_snap_b = []  # Ditto for 2nd folder
    same_path_and_name = []  # List of items that exist in both folders that user chose
    size_copy_from_a_to_b = 0  # Size of files that need to be copied from 1st folder to 2nd
    size_copy_from_b_to_a = 0  # Ditto for 2nd folder
    size_update_from_a_to_b = 0  # Size of files that need to be updated from 1st folder to 2nd
    size_update_from_b_to_a = 0  # Ditto for 2nd folder
    size_of_items_in_a = 0  # Total of all files in 1st folder
    size_of_items_in_b = 0  # Ditto for 2nd folder
    skipped_files = []  # Files to skip (because both were changed since last sync)
    store_date_a = 0  # Time when snapshot of 1st folder was saved to storage
    store_date_b = 0  # Ditto for 2nd folder
    to_be_updated_from_a_to_b = []  # Files in 1st folder that will be replaced by their newer versions from 2nd folder
    to_be_updated_from_b_to_a = []  # Vice versa
    updated_items_a = []  # Files from 1st folder that have been changed since last sync
    updated_items_b = []  # Ditto for 2nd folder
    were_removed_from_a = []  # File that were removed from 1st folder since last sync
    were_removed_from_b = []  # Ditto for second folder

    # Count how many files will be transferred from one folder to the other
    def count_items_to_be_transferred(roster_to_be_copied, roster_to_be_updated):
        return len(roster_to_be_copied) + len(roster_to_be_updated)

    def print_and_log_what_will_be_synced():
        # Right before ask user whether he wants to start manipulating files this function will show him
        # which files are going to be deleted or copied

        def get_size_of_files_to_remove(files_to_delete):
            total_size = 0
            for item in files_to_delete:
                total_size += item[2]
            return total_size

        def get_size_files_to_transfer(files_to_copy, files_to_update):
            total_size = 0
            # Loop two lists at once to get size of all files to be copied or updated
            for item_a in files_to_copy:
                if item_a[0] == 'file':
                    total_size += item_a[2]

            for item_b in files_to_update:
                if item_b[0] == 'file':
                    total_size += item_b[2]

            return total_size

        def show_stat_to_be_transferred(num_files_to_transfer, path1, path2, files_to_copy, files_to_update):
            """
             Log and print message how many files will be copied from one folder to another and total size of files
            :param num_files_to_transfer: total number of files to be transferred
            :param path1: source folder
            :param path2: destination folder
            :param files_to_copy: list of files that will be copied from source folder to destination folder
            :param files_to_update: list of files to be updated due to changes
            :return: None
            """
            message2 = "\nNumber of items to transfer from '{}' to '{}' is {}.".format(path1, path2,
                                                                                       num_files_to_transfer)
            print(message2)
            log_file.info(message2 + '\n')

            size_files_to_be_copied = get_size_files_to_transfer(files_to_copy, files_to_update)

            message2 = ("Total size of files to transfer from '{}' to '{}' is "
                        "{:.2f} MB.".format(path1, path2, size_files_to_be_copied / 1024 ** 2))
            print(message2)
            log_file.info(message2)

        def show_stat_to_be_deleted(path, num_files_to_delete, files_to_remove):
            message2 = "\nNumber of item to delete from '{}' is {}.".format(path, num_files_to_delete)
            print(message2)
            log_file.info(message2)
            size_files_to_be_deleted = get_size_of_files_to_remove(files_to_remove)
            message2 = ("Size of items to delete from '{}' is "
                        "{:.2f} MB".format(path, size_files_to_be_deleted / 1024 ** 2))
            print(message2)
            log_file.info(message2)

        num_to_transfer_from_a_to_b = count_items_to_be_transferred(not_exist_in_b, to_be_updated_from_a_to_b)
        if num_to_transfer_from_a_to_b > 0:
            # Show user (and log) number of files and total size of what will be copied
            show_stat_to_be_transferred(num_to_transfer_from_a_to_b, first_folder, second_folder, not_exist_in_b,
                                        to_be_updated_from_a_to_b)

        num_to_transfer_from_b_to_a = count_items_to_be_transferred(not_exist_in_a, to_be_updated_from_b_to_a)
        if num_to_transfer_from_b_to_a > 0:
            show_stat_to_be_transferred(num_to_transfer_from_b_to_a, second_folder, first_folder, not_exist_in_a,
                                        to_be_updated_from_b_to_a)

        if len(must_remove_from_a) > 0:
            show_stat_to_be_deleted(first_folder, len(must_remove_from_a), must_remove_from_a)

        if len(must_remove_from_b) > 0:
            show_stat_to_be_deleted(second_folder, len(must_remove_from_b), must_remove_from_b)

    def get_users_opinion_reverse_copy_or_delete(operation):
        # Menu that ask user whether he sure or not about copying/deleting files
        while True:
            question = 'Are you sure you want {} these files? y/n: '.format(operation)  # transfer or delete
            sure_or_not = input(question)
            log_file.info('%s\n', question)
            if sure_or_not.lower() == 'n':
                return True
            elif sure_or_not.lower() == 'y':
                return False
            else:
                print('It is wrong input, try again.')
                log_file.info('It is wrong input, try again.\n')

    def reverse_decision_copy_or_delete(operation, path_from, path_to, files_to_decide, list_to_add_files):
        # Add ability to delete files from folder instead of copying or to copy instead of deleting
        while True:
            if operation != 'delete':
                question = ('Would you like to delete these files from {0} instead of copying '
                            'from {0} to {1} ? y/n: '.format(path_from, path_to))
            else:
                question = ('Would you like to copy these files from {0} to {1} instead of deleting '
                            'from {0}? y/n: ' .format(path_from, path_to))
            yes_or_no = input(question)
            log_file.info('%s\n', question)
            if yes_or_no.lower() == 'y':
                list_to_add_files += files_to_decide
                files_to_decide[:] = []
                return True
            elif yes_or_no.lower() == 'n':
                files_to_decide[:] = []
                print('The list of files to be deleted was cleared.')
                return False
            else:
                print('It is wrong input, try again.')
                log_file.info('It is wrong input, try again.\n')

    def print_files_to_be_managed(operation, list_of_files, path_from, path_to):
        # Show list of files to be copied if needed
        while True:
            if operation != 'deleted':
                question = 'Do you want to SEE the list of files to be {} from {} ' \
                           'to {}? y/n: '.format(operation, path_from, path_to)
            else:
                question = 'Do you want to SEE the list of files to be {}? y/n: '.format(operation)
            see_list = input(question)
            log_file.info('%s\n', question)
            if see_list.lower() == 'y':
                for item in list_of_files:
                    print(item[1][0])
                break
            elif see_list.lower() == 'n':
                break
            else:
                print('It is wrong input, try again.')
                log_file.info('It is wrong input, try again.\n')

    def show_files_to_remove(folder, files_to_delete, path_from, path_to, list_to_copy):
        # Function that shows you files to be deleted and gives an opportunity to reset the list or
        # to copy files where them were deleted to instead of deleting
        message2 = "\nNumber of items to remove from '{}' is {}.".format(folder, len(files_to_delete))
        print(message2)
        log_file.info(message2)
        print_files_to_be_managed('deleted', files_to_delete, None, None)
        if get_users_opinion_reverse_copy_or_delete('delete'):
            reverse_decision_copy_or_delete('delete', path_from, path_to, files_to_delete, list_to_copy)
        # else:
        #     size1 = get_size_of_files_to_remove(files_to_delete) / 1024**2
        #     # size1 = size_files_to_delete / 1024 ** 2  # convert in** megabytes
        #     print('Size of items to remove from \'{}\' is {:.2f} MB.'.format(folder, size1))
        #     logFile.info('Size of items to remove from \'{}\' is {:.2f} MB.'.format(folder, size1))

    def show_files_to_transfer(number_to_transfer, path_from, path_to, files_to_copy, files_to_update,
                               size_to_copy, size_to_update, files_to_delete):
        # Function that prints and logs files to be copied and to be updated und allows to reset these lists
        message2 = "Number of items to transfer from '{}' to '{}' is {}.".format(path_from, path_to,
                                                                                 number_to_transfer)
        print('\n' + message2)
        log_file.info(message2)

        if len(files_to_copy) > 0:
            print_files_to_be_managed('copied', files_to_copy, path_from, path_to)
            if get_users_opinion_reverse_copy_or_delete('copy'):
                reverse_decision_copy_or_delete('copy', path_from, path_to, files_to_copy, files_to_delete)

        if len(files_to_update) > 0:
            print_files_to_be_managed('updated', files_to_update, path_from, path_to)
            if get_users_opinion_reverse_copy_or_delete('update'):
                reverse_decision_copy_or_delete('update', path_from, path_to, files_to_copy, files_to_delete)

        # Not sure yet whether I need this message or not.
        # if (len(files_to_copy) + len(files_to_update)) > 0:
        #     size1 = (size_to_copy + size_to_update) / 1024 ** 2
        #     message1 = 'Total size of files to be transferred from \'{}\' to \'{}\' is {:.2f} MB.'\
        #         .format(path_from, path_to, size1)
        #     print(message1)
        #     logFile.info(message1)

    def compare_files_mtime(file_from_a, file_from_b):
        # Compare time when files were changed last time
        nonlocal both_updated
        nonlocal skipped_files

        # do not update file if it has been updated in both folders since last sync
        if both_synced and len(both_updated) > 0 and file_from_a[1][3] in both_updated:
            message2 = file_from_a[1][3] + ' has changed in both folders, so you need to choose ' \
                                          'right version manually. Program will not manage it.'
            print(message2)
            log_file.warning(message2)
            skipped_files.append(file_from_a[1][3])

        else:
            if file_from_a[3] > file_from_b[3]:
                return 'firstNewer'
            elif file_from_a[3] < file_from_b[3]:
                return 'secondNewer'
            else:
                return 'equal'

    def compare_binary(file_from_a, file_from_b):
        # Compare files in binary mode with buffer
        if file_from_a[2] > 1024 ** 3:
            print('It\'s gonna take some time, be patient.')
        with open(file_from_a[1][0], 'rb') as f1, open(file_from_b[1][0], 'rb') as f2:
            while True:
                b1 = f1.read(8192)
                b2 = f2.read(8192)
                if b1 != b2:
                    # content is not equal
                    return False
                if not b1:
                    # content is equal
                    return True

    if first_folder_synced and get_changes_between_folder_states(first_folder, root_first_folder) != -1:
        # If 1st folder have been synced before, compare it's current and previous snapshot and get changes
        were_removed_from_a, new_in_a, updated_items_a, snap_a, store_date_a = \
            get_changes_between_folder_states(first_folder, root_first_folder)
    else:
        # Load current state of folder (path to every ite inside with size and modification time)
        snap_a = get_snapshot(first_folder, root_first_folder)

    if second_folder_synced and get_changes_between_folder_states(second_folder, root_second_folder) != -1:
        were_removed_from_b, new_in_b, updated_items_b, snap_b, store_date_b = \
            get_changes_between_folder_states(second_folder, root_second_folder)
    else:
        snap_b = get_snapshot(second_folder, root_second_folder)

    # Check if the same files were changed in both folder (which means, if true, script can't
    # decide automatically which one to remove and which one to update).
    if both_synced:
        both_updated = [item for item in updated_items_a if item in updated_items_b]

    # Create list of paths to items from 2nd folder's snapshot.
    # Path like this '\somefolder\somefile.ext' - to be able to compare them to each other
    for key in snap_b.keys():
        paths_of_snap_b.append(snap_b[key][1][3])

    print()  # this print() is needed to make offset

    # Compare 1st folder to 2nd folder
    for key in snap_a.keys():
        # Create list of paths to items from 2nd folder's snapshot.
        path_to_file_in_a_without_root = snap_a[key][1][3]
        paths_of_snap_a.append(path_to_file_in_a_without_root)

        if snap_a[key][0] == 'file':
            # count number and size of files in 1st folder
            num_files_in_a += 1
            size_of_items_in_a += snap_a[key][2]
            message1 = ('Comparing files {}'.format(path_to_file_in_a_without_root))
            print(message1)
            log_file.info(message1)
        else:
            # count number of subfolders in the 1st folder
            num_folders_in_a += 1

        # if item with same path exists in both folders to be synced
        if path_to_file_in_a_without_root in paths_of_snap_b:
            # if item is file - compare them
            if snap_a[key][0] == 'file':
                same_path_and_name.append(snap_a[key])
                # merge root of 2nd folder with path of file/folder from 1st folder
                # to get a probability to compare files
                corresponding_file_in_b = os.path.join(root_second_folder, path_to_file_in_a_without_root)

                # check if both files have the same modification time that they have before
                if both_synced:
                    if path_to_file_in_a_without_root not in updated_items_a \
                            and path_to_file_in_a_without_root not in updated_items_b:
                        print('= Files are equal.')
                        log_file.info('= Files are equal.')
                        equal_files.append(snap_a[key])
                        continue

                which_file_is_newer = compare_files_mtime(snap_a[key], snap_b[corresponding_file_in_b])
                # file in A newer than file in 2nd folder -> check if files have indeed different content
                if which_file_is_newer == 'firstNewer':
                    # if content of files the same - time doesn't matter. Files are equal.
                    if compare_binary(snap_a[key], snap_b[corresponding_file_in_b]):
                        print('= Files are equal.')
                        log_file.info('= Files are equal.')
                        equal_files.append(snap_a[key])
                    # files have different content - add them to list to be copied from 1st to 2nd folder
                    else:
                        message1 = "-> File in '{}' is newer".format(first_folder)
                        print(message1)
                        log_file.info(message1)
                        # add to list another list with full paths of both files and size of file to be copied
                        to_be_updated_from_a_to_b.append([snap_a[key][1][0], snap_b[corresponding_file_in_b][1][0],
                                                          snap_a[key][2]])
                        size_update_from_a_to_b += snap_a[key][2]
                elif which_file_is_newer == 'secondNewer':
                    # if content of files the same - time doesn't matter. Files are equal.
                    if compare_binary(snap_a[key], snap_b[corresponding_file_in_b]):
                        print('= Files are equal.')
                        log_file.info('= Files are equal.')
                        equal_files.append(snap_a[key])

                    # file in A older than file in B -> add it to list to be copied from B to A
                    else:
                        message1 = "<- File in '{}' is newer".format(second_folder)
                        print(message1)
                        log_file.info(message1)
                        # add to list another list with full paths of both files and size of file in B
                        to_be_updated_from_b_to_a.append([snap_b[corresponding_file_in_b][1][0], snap_a[key][1][0],
                                                          snap_b[corresponding_file_in_b][2]])
                        size_update_from_b_to_a += snap_b[corresponding_file_in_b][2]
                elif which_file_is_newer == 'equal':
                    if snap_a[key][2] == snap_b[corresponding_file_in_b][2]:
                        print('= Files are equal.')
                        log_file.info('= Files are equal.')
                        equal_files.append(snap_a[key])

                    # If modification time is equal, bit size is not
                    # then add it to list to tell to user to check manually.
                    else:
                        print("! You should check it manually.")
                        log_file.info("! You should check it manually.")
                        skipped_files.append(path_to_file_in_a_without_root)

        else:  # if file from first folder has not been found in the second folder
            # if item was removed from 2nd folder then add it to list of items which will be removed from 1st folder
            if path_to_file_in_a_without_root in were_removed_from_b:
                must_remove_from_a.append(snap_a[key])
                if snap_a[key][0] == 'file':
                    message1 = "- Will be removed from {}".format(first_folder)
                    print(message1)
                    log_file.info(message1)
                continue

            else:  # if file doesn't exist in 2nd folder -> add it in list to be copied from 1st folder
                not_exist_in_b.append(snap_a[key])
                if snap_a[key][0] == 'file':
                    message1 = "-> Doesn\'t exist in '{}' and will be copied there.".format(second_folder)
                    print(message1)
                    log_file.info(message1)
                    size_copy_from_a_to_b += snap_a[key][2]

    for key in snap_b.keys():  # check which files from B exist in A
        if snap_b[key][0] == 'file':
            # count number and size of files in the first folder
            num_files_in_b += 1
            size_of_items_in_b += snap_b[key][2]
        else:  # count number of folder in the second folder
            num_folders_in_b += 1

        # if item from 1st folder doesn't exist in 2nd folder
        if not snap_b[key][1][3] in paths_of_snap_a:
            message1 = "Comparing files... '{}'".format(snap_b[key][1][3])
            print(message1)
            log_file.info(message1)

            # if item was removed from 1st folder - add it to list of items
            # which will be removed from 2nd folder
            if snap_b[key][1][3] in were_removed_from_a:
                message1 = "- Will be removed from {}".format(second_folder)
                print(message1)
                log_file.info(message1)
                must_remove_from_b.append(snap_b[key])

            else:  # if file doesn't exists in 1st folder -> add it in list to be copied from 2nd folder
                message1 = "<- Doesn't exist in '{}' and will be copied there.".format(first_folder)
                print(message1)
                log_file.info(message1)
                not_exist_in_a.append(snap_b[key])
                if snap_b[key][0] == 'file':
                    size_copy_from_b_to_a += snap_b[key][2]

    '''result messages to console and log file'''

    print('')
    print('###########################')
    log_file.info('\n')
    log_file.info('###########################')

    size = size_of_items_in_a / 1024**2
    message = "There are {} folders and {} files in '{}' with total size of {:.2f} MB."\
              .format(num_folders_in_a, num_files_in_a, first_folder, size)
    print(message)
    log_file.info(message)

    size = size_of_items_in_b / 1024 ** 2
    message = "There are {} folders and {} files in '{}' with total size of {:.2f} MB."\
              .format(num_folders_in_b, num_files_in_b, second_folder, size)
    print(message)
    log_file.info(message)

    message = '{} file(s) that are common for both folders.'.format(len(same_path_and_name))
    print(message)
    log_file.info(message)

    message = '{} file(s) are equal.'.format(len(equal_files))
    print(message)
    log_file.info(message)

    if both_synced:
        if len(not_exist_in_b) > 0:
            message = "{} new item(s) in '{}'".format(len(not_exist_in_b), first_folder)
            print(message)
            log_file.info(message)

        if len(not_exist_in_a) > 0:
            message = "{} new item(s) in '{}'".format(len(not_exist_in_a), second_folder)
            print(message)
            log_file.info(message)

    else:
        if len(not_exist_in_b) > 0:
            message = "{} item(s) from '{}' don't exist in '{}'.".format(len(not_exist_in_b), first_folder,
                                                                         second_folder)
            print(message)
            log_file.info(message)

        if len(not_exist_in_a) > 0:
            message = "{} item(s) from '{}' don't exist in '{}'.".format(len(not_exist_in_a), second_folder,
                                                                         first_folder)
            print(message)
            log_file.info(message)

    if len(to_be_updated_from_a_to_b) > 0:
        message = "{} item(s) has newer version in '{}'".format(len(to_be_updated_from_a_to_b), first_folder)
        print(message)
        log_file.info(message)

    if len(to_be_updated_from_b_to_a) > 0:
        message = "{} item(s) has newer version in '{}'".format(len(to_be_updated_from_a_to_b), second_folder)
        print(message)
        log_file.info(message)

    if len(were_removed_from_a) > 0:
        message = "{} item(s) have been removed from '{}' since {}".format(len(were_removed_from_a), first_folder,
                                                                           store_date_a)
        print(message)
        log_file.info(message)

    if len(were_removed_from_b) > 0:
        message = "{} item(s) have been removed from '{}' since {}".format(len(were_removed_from_b), second_folder,
                                                                           store_date_b)
        print(message)
        log_file.info(message)

    if len(skipped_files) > 0:
        message = "There are {} items that you should check manually.".format(len(skipped_files))
        print(message)
        log_file.info(message)
        if len(skipped_files) > 0:
            print('These are: ')
            log_file.warning('These are: ')
            for file in skipped_files:
                print('- ' + file)
                log_file.warning('- %s', file)

    message = '--- {0:.3f} --- seconds\n'.format(time.time() - start_time)
    print(message)
    log_file.info('%s\n', message)

    number_to_transfer_from_a_to_b = count_items_to_be_transferred(not_exist_in_b, to_be_updated_from_a_to_b)
    if number_to_transfer_from_a_to_b > 0:
        show_files_to_transfer(number_to_transfer_from_a_to_b, first_folder, second_folder, not_exist_in_b,
                               updated_items_a, size_copy_from_a_to_b, size_update_from_a_to_b, must_remove_from_a)

    number_to_transfer_from_b_to_a = count_items_to_be_transferred(not_exist_in_a, to_be_updated_from_b_to_a)
    if number_to_transfer_from_b_to_a > 0:
        show_files_to_transfer(number_to_transfer_from_b_to_a, second_folder, first_folder, not_exist_in_a,
                               updated_items_b, size_copy_from_b_to_a, size_update_from_b_to_a, must_remove_from_b)

    if len(must_remove_from_a) > 0:
        show_files_to_remove(first_folder, must_remove_from_a, first_folder, second_folder, not_exist_in_b)

    if len(must_remove_from_b) > 0:
        show_files_to_remove(second_folder, must_remove_from_b, second_folder, first_folder, not_exist_in_a)

    print_and_log_what_will_be_synced()

    result = [not_exist_in_a, not_exist_in_b, to_be_updated_from_b_to_a, to_be_updated_from_a_to_b, must_remove_from_a,
              must_remove_from_b]

    number_files_to_transfer = 0
    for array in result:  # count how many files script should transfer in total
        number_files_to_transfer += len(array)

    result.append(number_files_to_transfer)
    return result


def store_snapshot_before_exit(folder_to_take_snapshot, root_folder, folder_synced):
    # Store state of folder on storage after this folder was was synced

    if folder_synced:
        shel_file = shelve.open(os.path.join(folder_to_take_snapshot, '.folderSyncSnapshot', 'snapshot'))
    else:
        os.mkdir(os.path.join(folder_to_take_snapshot, '.folderSyncSnapshot'))
        shel_file = shelve.open(os.path.join(folder_to_take_snapshot, '.folderSyncSnapshot', 'snapshot'))

    # Scan folder to get a snapshot
    snapshot = get_snapshot(folder_to_take_snapshot, root_folder)

    store_time = time.strftime('%Y-%m-%d %Hh-%Mm')
    shel_file['path'] = folder_to_take_snapshot
    shel_file['snapshot'] = snapshot
    shel_file['date'] = store_time
    shel_file['to_remove_from_a'] = remove_from_a_next_time
    shel_file['to_remove_from_b'] = remove_from_b_next_time

    log_file.info('Snapshot of %s was stored in %s at %s\n', root_folder, folder_to_take_snapshot, store_time)
    shel_file.close()


def sync_files(difference_between_folders, first_folder, second_folder, root_first_folder, first_folder_synced,
               root_second_folder, second_folder_synced):
    # This function takes lists with items to copy and/or delete them

    start_time = time.time()
    not_exist_in_a, not_exist_in_b, to_be_updated_from_b_to_a, to_be_updated_from_a_to_b, \
        remove_from_a, remove_from_b, number_files_to_handle = difference_between_folders

    total_size_copied_updated = 0
    total_size_removed = 0
    were_copied = 0
    were_created = 0
    were_updated = 0
    were_removed = 0

    log_file.info('Start syncing files...')
    print('Start syncing files...')

    def delete(file_to_delete):
        # Function that tries to remove one specific file and return true if it was removed.
        # Used in remove_items() and update_files().

        user_decision = ''
        while user_decision != 'n':
            try:
                send2trash.send2trash(file_to_delete)

            # ask user to close program that is using file that should be removed and try to perform removing again
            except OSError:
                log_file.error(traceback.format_exc())
                message2 = ("'{}' has been opened in another app. Close all apps that can use this file "
                            "and try again.".format(file_to_delete))
                print(message2)
                log_file.warning(message2)
                user_decision = input('Try again? y/n: ').lower()
                if user_decision == 'n':
                    return False
                elif user_decision == 'y':
                    print('Trying one more time...')
                    log_file.info('Trying one more time...')
                    continue
                else:
                    print('You should type in "y" or "n". Try again.')
                    log_file.info('You should type in "y" or "n". Try again.')
                    continue
            return True

    def remove_items(items_to_remove, folder):  # function that recursively removes files from list

        nonlocal were_removed  # list of removed files
        nonlocal total_size_removed  # number of removed files
        remove_state = True  # used to count removed files

        print('Removing files...')
        log_file.info('Removing files...')

        for item in range(len(items_to_remove)):  # recursively sends items from list to delete() function
            full_path = items_to_remove[item][1][0]
            if os.path.exists(full_path):
                if delete(full_path):
                    message2 = "'{}' was removed".format(full_path)
                    print(message2)
                    log_file.info(message2)
                    were_removed += 1
                else:
                    message2 = "'{}' was not removed".format(full_path)
                    print(message1)
                    log_file.warning(message2)
                    if folder == 'first':  # check and log from which folder were file that wasn't removed
                        remove_from_b_next_time.append(items_to_remove[item])
                    elif folder == 'second':
                        remove_from_a_next_time.append(items_to_remove[item])
                    remove_state = False
                    continue
            else:  # item was removed with its folder before
                message2 = "'{}' was removed".format(full_path)
                print(message2)
                log_file.info(message2)
                were_removed += 1

            if items_to_remove[item][0] == 'file' and remove_state:  # count size of removed files
                total_size_removed += items_to_remove[item][2]

    def copy_items(items_to_copy, path_to_root):  # Copy files that don't exist in one of folders

        # in order to use a variable from nearest outer scope
        nonlocal were_copied
        nonlocal were_created
        nonlocal total_size_copied_updated

        for item in items_to_copy:

            # create path where copy items to
            path_without_root = item[1][3]
            full_path_item_in_this_folder = item[1][0]  # full path of item
            full_path_item_that_not_exits_yet = os.path.join(path_to_root, path_without_root)

            if item[0] == 'folder':
                os.mkdir(full_path_item_that_not_exits_yet)  # create empty folder instead of copying full directory
                were_created += 1
                message2 = "- '{}' was created".format(full_path_item_that_not_exits_yet)
                print(message2)
                log_file.info(message2)

            elif item[0] == 'file':
                if os.path.exists(full_path_item_that_not_exits_yet):  # it shouldn't happened, but just in case
                    log_console.warning("WARNING: '%s' already exists!", full_path_item_that_not_exits_yet)
                    log_file.warning("WARNING: '%s' already exists!", full_path_item_that_not_exits_yet)
                    continue
                else:
                    message2 = "'{}' is copying to '{}'...".format(item[1][0], full_path_item_that_not_exits_yet)
                    print(message2)
                    log_file.info(message2)
                    if item[2] > 1024**3:  # if size of file more than 1 Gb
                        message2 = "'{} is heavy. Please be patient.'".format(item[1][0])
                        print(message2)
                        log_file.info(message2)

                    # copy file
                    shutil.copy2(full_path_item_in_this_folder, full_path_item_that_not_exits_yet)

                    were_copied += 1
                    total_size_copied_updated += item[2]
                    print('Done.')
                    log_file.info('Done.')

    def update_files(to_be_updated):  # recursively update files by deleting old one and copying new one instead of it

        nonlocal total_size_copied_updated
        nonlocal were_updated

        # array contains list three items: full path of item to be copied, full path where copy to, size of file to copy
        for array in to_be_updated:
            if os.path.exists(array[0]) and os.path.exists(array[1]):
                if delete(array[1]):  # if item was successfully removed
                    shutil.copy2(array[0], array[1])  # copy newer version instead of one that was removed
                    message2 = "'{}' was updated.".format(array[1])
                    print(message2)
                    log_file.info(message2)
                    total_size_copied_updated += array[2]
                    were_updated += 1
                else:
                    message2 = "'{}' was not updated.".format(array[1])
                    print(message2)
                    log_file.warning(message2)
                    # Script will try to updated it next time, there is nothing to be worried about
                    continue

            elif not os.path.exists(array[0]):
                message2 = "'{}' hasn't been found! Can't handle it.".format(array[0])
                print(message2)
                log_file.warning(message2)
            elif not os.path.exists(array[1]):
                message2 = "'{}' hasn't been found! Can't handle it.".format(array[1])
                print(message1)
                log_file.warning(message2)

    if len(remove_from_a) > 0:
        remove_items(remove_from_a, 'first')

    if len(remove_from_b) > 0:
        remove_items(remove_from_b, 'second')

    if len(to_be_updated_from_a_to_b) > 0:
        update_files(to_be_updated_from_a_to_b)

    if len(to_be_updated_from_b_to_a) > 0:
        update_files(to_be_updated_from_b_to_a)

    if len(not_exist_in_a) > 0:
        copy_items(not_exist_in_a, first_folder)

    if len(not_exist_in_b) > 0:
        copy_items(not_exist_in_b, second_folder)

    if were_created > 0:
        message1 = "\n{} folders were created.".format(were_created)
        print(message1)
        log_file.info(message1)

    if were_copied > 0:
        message1 = "\n{} file(s) were copied.".format(were_copied)
        print(message1)
        log_file.info(message1)

    if were_updated > 0:
        message1 = "\n{} file(s) were updated.".format(were_updated)
        print(message1)
        log_file.info(were_updated)

    if were_removed > 0:
        message1 = "\n{} file(s) were removed.".format(were_removed)
        print(message1)
        log_file.info(message1)

    if total_size_copied_updated > 0:
        message = 'Total size of files were copied or updated is {0:.2f} MB.'\
            .format(total_size_copied_updated / 1024**2)
        print(message)
        log_file.info(message)

    if total_size_removed > 0:
        message1 = 'Total size of files were removed in {0:.2f} MB'.format(total_size_removed / 1024**2)
        print(message1)
        log_file.info(message1)

    message1 = '--- {0:.3f} seconds ---\n'.format(time.time() - start_time)
    print(message1)
    log_file.info(message1)

    store_snapshot_before_exit(first_folder, root_first_folder, first_folder_synced)
    store_snapshot_before_exit(second_folder, root_second_folder, second_folder_synced)


# Menu to ask user if he wants to start transferring files
def menu_before_sync(difference_between_folders, first_folder, second_folder, root_first_folder, first_folder_synced,
                     root_second_folder, second_folder_synced):
    while True:
        start_syncing = input('\nDo you want to sync these files? y/n: ').lower()
        log_file.info('Do you want to sync these files? y/n: ')
        if start_syncing == 'y':
            log_file.info('User agreed to sync files.')
            sync_files(difference_between_folders, first_folder, second_folder, root_first_folder, first_folder_synced,
                       root_second_folder, second_folder_synced)
            break
        elif start_syncing == 'n':  # continue without copy/remove files
            log_file.info('User denied to sync files.')
            break
        else:
            print('Error of input. Try again.')
            log_file.info('Error of input. Try again.')
            continue


def main():
    hello_message = ('Hello. This is folder_sync.py written by Aleksandr Mikheev.\nIt is a program that can '
                     'sync all files and folders between two chosen directories.\n')
    print(hello_message)
    log_file.info(hello_message)

    # first argument is max size of folder with logs in megabytes
    # if there are more than that - remove oldest logs
    handle_logs.clean_log_folder(20, log_file, log_console)

    # let user choose folders to sync - here program starts
    first_folder, second_folder = menu_choose_folders()

    # check if there is snapshot of previous sync inside root directory
    first_folder_synced = os.path.exists(os.path.join(first_folder, '.folderSyncSnapshot'))
    log_file.info("Has '{%s}' been synced before? %s", first_folder, first_folder_synced)
    second_folder_synced = os.path.exists(os.path.join(second_folder, '.folderSyncSnapshot'))
    log_file.info("Has '{%s}' been synced before? %s \n", second_folder, second_folder_synced)

    # check if both folders were synced before
    both_synced = (first_folder_synced and second_folder_synced) or False

    # get names of root folders to be compared
    if 'win' in sys.platform.lower():
        root_first_folder = first_folder.split('\\')[-1]
        root_second_folder = second_folder.split('\\')[-1]
    else:
        root_first_folder = first_folder.split('/')[-1]
        root_second_folder = second_folder.split('/')[-1]

    # add root of folders as first elements in these list in case if script would not be able to remove file;
    # to distinguish which not removed files belongs to which folder
    remove_from_a_next_time.append(root_first_folder)
    remove_from_b_next_time.append(root_second_folder)

    # start to compare folders that user has chosen
    difference_between_folders = compare_snapshot(first_folder, second_folder, root_first_folder, root_second_folder,
                                                  both_synced, first_folder_synced, second_folder_synced)

    if difference_between_folders[6] > 0:  # call sync function if there is something to sync
        menu_before_sync(difference_between_folders, first_folder, second_folder, root_first_folder,
                         first_folder_synced, root_second_folder, second_folder_synced)
    else:
        # store snapshots of folders if they have been synced but no differences have been found
        if not first_folder_synced:
            store_snapshot_before_exit(first_folder, root_first_folder, first_folder_synced)
        if not second_folder_synced:
            store_snapshot_before_exit(second_folder, root_second_folder, second_folder_synced)

        print('There is nothing to copy or remove.')
        log_file.info('There is nothing to copy or remove.')

    print('Goodbye.')
    log_file.info('Goodbye.')


if __name__ == '__main__':
    main()

