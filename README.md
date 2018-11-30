# folderSync
Program that can sync all files and folders between two chosen directories (for Windows).

Program that can sync all files and folders between two chosen folders.
Purpose of that script is to make exact duplicates of two folders.
For example, you can back up and update your backups with this script.
During first sync script assumes all files which do not exist in one folder are new for the other folder and vice versa.
During second and other syncs script can delete files from folder if they were deleted from the other one.
It can also detected and handle updated files.
For file comparison it uses timestamps, size of file and binary comparison - depend on a situation.
Script also writes logs to .\log folder and clear the oldest ones, when size of log folder is more than 20 Mb.
