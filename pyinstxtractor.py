"""
PyInstaller Extractor v2.0 (Supports pyinstaller 4.2, 4.1, 4.0, 3.6, 3.5, 3.4, 3.3, 3.2, 3.1, 3.0, 2.1, 2.0)
Author : Extreme Coders
E-mail : extremecoders(at)hotmail(dot)com
Web    : https://0xec.blogspot.com
Date   : 26-March-2020
Url    : https://github.com/extremecoders-re/pyinstxtractor
For any suggestions, leave a comment on
https://forum.tuts4you.com/topic/34455-pyinstaller-extractor/
This script extracts a pyinstaller generated executable file.
Pyinstaller installation is not needed. The script has it all.
For best results, it is recommended to run this script in the
same version of python as was used to create the executable.
This is just to prevent unmarshalling errors(if any) while
extracting the PYZ archive.
Usage : Just copy this script to the directory where your exe resides
        and run the script with the exe file name as a parameter
C:\path\to\exe\>python pyinstxtractor.py <filename>
$ /path/to/exe/python pyinstxtractor.py <filename>
Licensed under GNU General Public License (GPL) v3.
You are free to modify this source.
CHANGELOG
================================================
Version 1.1 (Jan 28, 2014)
-------------------------------------------------
- First Release
- Supports only pyinstaller 2.0
Version 1.2 (Sept 12, 2015)
-------------------------------------------------
- Added support for pyinstaller 2.1 and 3.0 dev
- Cleaned up code
- Script is now more verbose
- Executable extracted within a dedicated sub-directory
(Support for pyinstaller 3.0 dev is experimental)
Version 1.3 (Dec 12, 2015)
-------------------------------------------------
- Added support for pyinstaller 3.0 final
- Script is compatible with both python 2.x & 3.x (Thanks to Moritz Kroll @ Avira Operations GmbH & Co. KG)
Version 1.4 (Jan 19, 2016)
-------------------------------------------------
- Fixed a bug when writing pyc files >= version 3.3 (Thanks to Daniello Alto: https://github.com/Djamana)
Version 1.5 (March 1, 2016)
-------------------------------------------------
- Added support for pyinstaller 3.1 (Thanks to Berwyn Hoyt for reporting)
Version 1.6 (Sept 5, 2016)
-------------------------------------------------
- Added support for pyinstaller 3.2
- Extractor will use a random name while extracting unnamed files.
- For encrypted pyz archives it will dump the contents as is. Previously, the tool would fail.
Version 1.7 (March 13, 2017)
-------------------------------------------------
- Made the script compatible with python 2.6 (Thanks to Ross for reporting)
Version 1.8 (April 28, 2017)
-------------------------------------------------
- Support for sub-directories in .pyz files (Thanks to Moritz Kroll @ Avira Operations GmbH & Co. KG)
Version 1.9 (November 29, 2017)
-------------------------------------------------
- Added support for pyinstaller 3.3
- Display the scripts which are run at entry (Thanks to Michael Gillespie @ malwarehunterteam for the feature request)
Version 2.0 (March 26, 2020)
-------------------------------------------------
- Project migrated to github
- Supports pyinstaller 3.6
- Added support for Python 3.7, 3.8
- The header of all extracted pyc's are now automatically fixed
"""

from __future__ import print_function
import os
import struct
import marshal
import zlib
import sys
from uuid import uuid4 as uniquename

logging = True
print_or = print


def print(str):
    global logging
    if logging:
        print_or(str)


class PYInstxtractorError(Exception):
    def __init__(self, message):
        self.message = "PYInstxtractorError " + message
        return super().__init__(self.message)


class CTOCEntry:
    def __init__(self, position, cmprsdDataSize, uncmprsdDataSize, cmprsFlag, typeCmprsData, name):
        self.position = position
        self.cmprsdDataSize = cmprsdDataSize
        self.uncmprsdDataSize = uncmprsdDataSize
        self.cmprsFlag = cmprsFlag
        self.typeCmprsData = typeCmprsData
        self.name = name


class PyInstArchive:
    PYINST20_COOKIE_SIZE = 24           # For pyinstaller 2.0
    PYINST21_COOKIE_SIZE = 24 + 64      # For pyinstaller 2.1+
    MAGIC = b'MEI\014\013\012\013\016'  # Magic number which identifies pyinstaller

    def __init__(self, path, log_enable=False):
        global logging
        logging = log_enable
        self.filePath = path

    def open(self):

        self.fPtr = open(self.filePath, 'rb')
        self.fileSize = os.stat(self.filePath).st_size

        return True

    def close(self):
        try:
            self.fPtr.close()
        except:
            pass

    def checkFile(self):
        print('[+] Processing {0}'.format(self.filePath))
        # Check if it is a 2.0 archive
        self.fPtr.seek(self.fileSize - self.PYINST20_COOKIE_SIZE, os.SEEK_SET)
        magicFromFile = self.fPtr.read(len(self.MAGIC))

        if magicFromFile == self.MAGIC:
            self.pyinstVer = 20     # pyinstaller 2.0
            print('[+] Pyinstaller version: 2.0')
            return True

        # Check for pyinstaller 2.1+ before bailing out
        self.fPtr.seek(self.fileSize - self.PYINST21_COOKIE_SIZE, os.SEEK_SET)
        magicFromFile = self.fPtr.read(len(self.MAGIC))

        if magicFromFile == self.MAGIC:
            print('[+] Pyinstaller version: 2.1+')
            self.pyinstVer = 21     # pyinstaller 2.1+
            return True
        self.fPtr.seek(0)
        magic_offset = self.fPtr.read().find(self.MAGIC, int(self.fileSize/2))
        if magic_offset > 0:
            self.fPtr.seek(magic_offset + self.PYINST20_COOKIE_SIZE)
            if (self.fPtr.read(6).upper() == b"PYTHON"):
                self.pyinstVer = 21
                self.fileSize = magic_offset + self.PYINST21_COOKIE_SIZE
            else:
                self.pyinstVer = 20
                self.fileSize = magic_offset + self.PYINST20_COOKIE_SIZE
            return True
        raise PYInstxtractorError(
            'Unsupported pyinstaller version or not a pyinstaller archive')

    def getCArchiveInfo(self):
        try:
            if self.pyinstVer == 20:
                self.fPtr.seek(self.fileSize -
                               self.PYINST20_COOKIE_SIZE, os.SEEK_SET)

                # Read CArchive cookie
                (magic, lengthofPackage, toc, tocLen, self.pyver) = \
                    struct.unpack('!8siiii', self.fPtr.read(
                        self.PYINST20_COOKIE_SIZE))

            elif self.pyinstVer == 21:
                self.fPtr.seek(self.fileSize -
                               self.PYINST21_COOKIE_SIZE, os.SEEK_SET)

                # Read CArchive cookie
                (magic, lengthofPackage, toc, tocLen, self.pyver, pylibname) = \
                    struct.unpack('!8siiii64s', self.fPtr.read(
                        self.PYINST21_COOKIE_SIZE))

        except:
            raise PYInstxtractorError('The file is not a pyinstaller archive')

        print('[+] Python version: {0}'.format(self.pyver))

        # Overlay is the data appended at the end of the PE
        self.overlaySize = lengthofPackage
        self.overlayPos = self.fileSize - self.overlaySize
        self.tableOfContentsPos = self.overlayPos + toc
        self.tableOfContentsSize = tocLen

        print('[+] Length of package: {0} bytes'.format(self.overlaySize))
        return True

    def parseTOC(self):
        # Go to the table of contents
        self.fPtr.seek(self.tableOfContentsPos, os.SEEK_SET)

        self.tocList = []
        parsedLen = 0

        # Parse table of contents
        while parsedLen < self.tableOfContentsSize:
            (entrySize, ) = struct.unpack('!i', self.fPtr.read(4))
            nameLen = struct.calcsize('!iiiiBc')

            (entryPos, cmprsdDataSize, uncmprsdDataSize, cmprsFlag, typeCmprsData, name) = \
                struct.unpack(
                '!iiiBc{0}s'.format(entrySize - nameLen),
                self.fPtr.read(entrySize - 4))

            name = name.decode('utf-8').rstrip('\0')
            if len(name) == 0:
                name = str(uniquename())
                print(
                    '[!] Warning: Found an unamed file in CArchive. Using random name {0}'.format(name))

            self.tocList.append(
                CTOCEntry(
                    self.overlayPos + entryPos,
                    cmprsdDataSize,
                    uncmprsdDataSize,
                    cmprsFlag,
                    typeCmprsData,
                    name
                ))

            parsedLen += entrySize
        print('[+] Found {0} files in CArchive'.format(len(self.tocList)))

    def _writeRawData(self, filepath, data):
        nm = filepath.replace('\\', os.path.sep).replace(
            '/', os.path.sep).replace('..', '__')
        nmDir = os.path.dirname(nm)
        # Check if path exists, create if not
        if nmDir != '' and not os.path.exists(nmDir):
            os.makedirs(nmDir)

        with open(nm, 'wb') as f:
            f.write(data)

    def extractFiles(self, custom_dir=None):
        print('[+] Beginning extraction...please standby')
        entryPoints = []
        original_cwd = os.getcwd()
        if custom_dir is None:
            extractionDir = os.path.join(
                os.getcwd(), os.path.basename(self.filePath) + '_extracted')

            if not os.path.exists(extractionDir):
                os.mkdir(extractionDir)

            os.chdir(extractionDir)
        else:
            if not os.path.exists(custom_dir):
                os.makedirs(custom_dir)
            os.chdir(custom_dir)

        for entry in self.tocList:
            basePath = os.path.dirname(entry.name)

            if basePath != '':
                # Check if path exists, create if not
                if not os.path.exists(basePath):
                    os.makedirs(basePath)

            self.fPtr.seek(entry.position, os.SEEK_SET)
            data = self.fPtr.read(entry.cmprsdDataSize)

            if entry.cmprsFlag == 1:
                data = zlib.decompress(data)
                # Malware may tamper with the uncompressed size
                # Comment out the assertion in such a case
                assert len(data) == entry.uncmprsdDataSize  # Sanity Check

            if entry.typeCmprsData == b's':
                # s -> ARCHIVE_ITEM_PYSOURCE
                # Entry point are expected to be python scripts
                print('[+] Possible entry point: {0}.pyc'.format(entry.name))
                entryPoints.append(entry.name)
                self._writePyc(entry.name + '.pyc', data)

            elif entry.typeCmprsData == b'M' or entry.typeCmprsData == b'm':
                # M -> ARCHIVE_ITEM_PYPACKAGE
                # m -> ARCHIVE_ITEM_PYMODULE
                # packages and modules are pyc files with their header's intact
                self._writeRawData(entry.name + '.pyc', data)

            else:
                self._writeRawData(entry.name, data)

                if entry.typeCmprsData == b'z' or entry.typeCmprsData == b'Z':
                    self._extractPyz(entry.name)
        os.chdir(original_cwd)
        return (self.pyver, entryPoints)

    def _writePyc(self, filename, data):
        with open(filename, 'wb') as pycFile:
            #            pycFile.write(pyc_magic)            # pyc magic
            #
            #            if self.pyver >= 37:                # PEP 552 -- Deterministic pycs
            #                pycFile.write(b'\0' * 4)        # Bitfield
            #                pycFile.write(b'\0' * 8)        # (Timestamp + size) || hash

            #            else:
            #                pycFile.write(b'\0' * 4)      # Timestamp
            #                if self.pyver >= 33:
            #                    pycFile.write(b'\0' * 4)  # Size parameter added in Python 3.3

            pycFile.write(data)

    def _extractPyz(self, name):
        return
        dirName = name + '_extracted'
        # Create a directory for the contents of the pyz
        if not os.path.exists(dirName):
            os.mkdir(dirName)

        with open(name, 'rb') as f:
            pyzMagic = f.read(4)
            assert pyzMagic == b'PYZ\0'  # Sanity Check

            pycHeader = f.read(4)  # Python magic value

            (tocPosition, ) = struct.unpack('!i', f.read(4))
            f.seek(tocPosition, os.SEEK_SET)

            try:
                toc = marshal.load(f)
            except:
                return

            print('[+] Found {0} files in PYZ archive'.format(len(toc)))

            # From pyinstaller 3.1+ toc is a list of tuples
            if type(toc) == list:
                toc = dict(toc)

            for key in toc.keys():
                (ispkg, pos, length) = toc[key]
                f.seek(pos, os.SEEK_SET)
                fileName = key

                try:
                    # for Python > 3.3 some keys are bytes object some are str object
                    fileName = fileName.decode('utf-8')
                except:
                    pass

                # Prevent writing outside dirName
                fileName = fileName.replace(
                    '..', '__').replace('.', os.path.sep)

                if ispkg == 1:
                    filePath = os.path.join(dirName, fileName, '__init__.pyc')

                else:
                    filePath = os.path.join(dirName, fileName + '.pyc')

                fileDir = os.path.dirname(filePath)
                if not os.path.exists(fileDir):
                    os.makedirs(fileDir)

                try:
                    data = f.read(length)
                    data = zlib.decompress(data)
                except:
                    open(filePath + '.encrypted', 'wb').write(data)
                else:
                    self._writePyc(filePath, data)


def main():
    if len(sys.argv) < 2:
        print('[+] Usage: pyinstxtractor.py <filename>')

    else:
        arch = PyInstArchive(sys.argv[1])
        if arch.open():
            if arch.checkFile():
                if arch.getCArchiveInfo():
                    arch.parseTOC()
                    arch.extractFiles()
                    arch.close()
                    print(
                        '[+] Successfully extracted pyinstaller archive: {0}'.format(sys.argv[1]))
                    print('')
                    print(
                        'You can now use a python decompiler on the pyc files within the extracted directory')
                    return

            arch.close()


if __name__ == '__main__':
    main()
