#! python3

'''Program that can sync all files and folders between two chosen folders. I need it to keep my photo-backup updated. But script should be able to sync in both ways. And keep track of changes in both folders.'''

import logging, os

logging.basicConfig(
	format = "%(levelname) -1s %(asctime)s line %(lineno)s: %(message)s",
	level = logging.DEBUG
	)

#TODO make menu to let user choose folders to sync
# ubtil then I am gonna set it manually at code to save some time while checking

firstFolder = ('.\\A')
secondFolder = ('.\\B')

