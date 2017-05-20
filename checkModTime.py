import os

firstFile = input('Please type path to file to compare: ')
mTimeFirstFile = os.path.getmtime(firstFile)
print(mTimeFirstFile)
secondFile = input('Please type path to other file: ')
mTimeSecFile = os.path.getmtime(secondFile)
print(os.path.getmtime(secondFile))

if mTimeSecFile == mTimeFirstFile:
	print('Files are equal')
elif mTimeFirstFile > mTimeSecFile:
	print('First file is older')
else:
	print('Second file is older')