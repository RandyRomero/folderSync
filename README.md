# folderSync
Program that can sync all files and folders between two chosen directoties (for Windows).

Program that can sync all files and folders between two chosen folders.
Dedicated for Windows.
Purpose of that script is to make exact duplicates of two folders.
For example, you can back up and update your backups with this script.
During first sync script assumes all files do not exist in one folder as new for the other folder and vice versa.
During second and other syncs script can delete files from folder if they were deleted in the other.
It can also detected and hadle updated files.
For file comparison it uses timestamps, size of file and binary comparison - depend on a situation.
Script also writes logs to .\log folder and clear the oldest, when size of log folder is more than 20 Mb.
