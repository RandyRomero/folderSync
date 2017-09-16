import logging
import os
import time
import send2trash
import datetime


def set_loggers():
    log_file = logging.getLogger('fs1')  # create logger for this specific module for logging to file

    log_file.setLevel(logging.DEBUG)  # set level of messages to be logged to file

    log_console = logging.getLogger('fs2')
    log_console.setLevel(logging.DEBUG)

    # define format of logging messages
    formatter = logging.Formatter('%(levelname)s %(asctime)s line %(lineno)s: %(message)s')

    timestr = time.strftime('%Y-%m-%d__%Hh%Mm')
    new_log_name = os.path.join('log', 'log_' + timestr + '.txt')

    if os.path.exists('.\log'):  # create new log every time when script starts instead of writing in the same file
        if os.path.exists(new_log_name): # if log file with this date already exists, make new one with (i) in the name
            i = 2
            while os.path.exists(os.path.join('log', 'log_' + timestr + '(' + str(i) + ').txt')):
                i += 1
                continue
            file_handler = logging.FileHandler(os.path.join('log', 'log_' + timestr + '(' +
                                                            str(i) + ').txt'), encoding='utf8')
        else:
            file_handler = logging.FileHandler(new_log_name, encoding='utf8')
    else:
        os.mkdir('.\log')
        file_handler = logging.FileHandler(new_log_name, encoding='utf8')

    # set format to both handlers
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # apply handler to this module (folderSync.py)
    log_file.addHandler(file_handler)
    log_console.addHandler(stream_handler)

    return log_file, log_console


def clean_log_folder(max_size, log_file, log_console):
    # clean log files from log folder when their total size is more than max_size
    logfile_list = []

    def check_logs_size():  # count size of all already existing logs and create a list of them
        nonlocal logfile_list
        total_size = 0

        for root, subfolders, logfiles in os.walk('log'):
            for logfile in logfiles:
                path_to_logfile = os.path.join(os.getcwd(), root, logfile)
                size_of_log = os.path.getsize(path_to_logfile)
                logfile_list.append([path_to_logfile, os.path.getctime(path_to_logfile), size_of_log])
                total_size += size_of_log

        log_file.info('There is {0:.02f} MB of logs.\n'.format(total_size / 1024**2))
        return total_size

    total_log_size = check_logs_size()

    while total_log_size > max_size * 1024**2:
        # if log files weighs more than max_size in megabytes - recursively remove oldest one one by one
        logfile_to_delete = ''
        oldest = time.time()

        # recursively check all log files to find out the oldest one
        for index, val in enumerate(logfile_list):  # enumerate to extract not only values, but their indexes also
            if val[1] < oldest:  # if file older than previous one
                oldest = val[1]
                logfile_to_delete = val[0]
                index_to_remove = index
        log_file.info('Removing old log file: ' + logfile_to_delete + ', ' +
                      str(datetime.datetime.fromtimestamp(oldest)))
        log_console.debug('Removing old log file: ' + logfile_to_delete + ', ' +
                          str(datetime.datetime.fromtimestamp(oldest)))
        send2trash.send2trash(logfile_to_delete)
        # remove item from from list and subtract it's size from total size
        total_log_size -= logfile_list[index_to_remove][2]
        logfile_list.pop(index_to_remove)
