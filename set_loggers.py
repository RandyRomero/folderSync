import logging
import os
import time


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

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    # set format to both handlers

    log_file.addHandler(file_handler)
    log_console.addHandler(stream_handler)
    # apply handler to this module (folderSync.py)

    return log_file, log_console
